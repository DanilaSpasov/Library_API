import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from library.models import STATUS_AVAILABLE, AvailabilitySubscription, Book

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_availability_notifications(book_id):
    book = Book.objects.filter(id=book_id, is_active=True).first()

    if book is None:
        return 0

    if not book.copies.filter(status=STATUS_AVAILABLE).exists():
        return 0

    subscription_ids = list(
        AvailabilitySubscription.objects.filter(
            book=book,
            notified_at__isnull=True,
        ).values_list("id", flat=True)
    )
    sent_count = 0

    for subscription_id in subscription_ids:
        with transaction.atomic():
            subscription = (
                AvailabilitySubscription.objects.select_for_update()
                .select_related("reader", "book")
                .filter(
                    id=subscription_id,
                    notified_at__isnull=True,
                )
                .first()
            )

            if subscription is None:
                continue

            send_mail(
                subject="Книга снова доступна",
                message=(
                    f"Книга «{subscription.book.title}» снова доступна "
                    "в библиотеке.\n"
                    "Вы можете обратиться к библиотекарю, чтобы взять её."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=(subscription.reader.email,),
            )

            subscription.notified_at = timezone.now()
            subscription.save(update_fields=("notified_at",))
            sent_count += 1

    logger.info(
        "Уведомления о доступности отправлены: book_id=%s, count=%s",
        book_id,
        sent_count,
    )

    return sent_count
