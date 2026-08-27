import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from library.models import (
    STATUS_AVAILABLE,
    STATUS_BORROWED,
    STATUS_DAMAGED,
    BookCopy,
    Loan,
)
from users.models import ROLE_ADMIN, ROLE_LIBRARIAN, ROLE_READER, User

logger = logging.getLogger(__name__)

LOAN_PERIOD_DAYS = 14
MAX_ACTIVE_LOANS = 3
RETURN_STATUSES = (STATUS_AVAILABLE, STATUS_DAMAGED)


def _raise_loan_error(message):
    logger.warning("Операция с выдачей отклонена: %s", message)
    raise ValidationError({"detail": message})


def _validate_library_staff(user):
    if user.role not in (ROLE_LIBRARIAN, ROLE_ADMIN):
        _raise_loan_error(
            "Выдавать и принимать книги может только библиотекарь " "или администратор."
        )


def issue_book(*, reader_email, inventory_number, issued_by):
    with transaction.atomic():
        _validate_library_staff(issued_by)

        reader = (
            User.objects.select_for_update().filter(email__iexact=reader_email).first()
        )
        if reader is None:
            _raise_loan_error("Читатель с таким email не найден.")

        if reader.role != ROLE_READER:
            _raise_loan_error("Книгу можно выдать только читателю.")

        if not reader.is_active or not reader.is_email_verified:
            _raise_loan_error("Аккаунт читателя не активирован.")

        book_copy = (
            BookCopy.objects.select_for_update()
            .filter(inventory_number=inventory_number)
            .first()
        )
    if book_copy is None:
        _raise_loan_error("Экземпляр с таким инвентарным номером не найден.")

    if not book_copy.book.is_active:
        _raise_loan_error("Эта книга исключена из активного каталога.")

    if book_copy.status != STATUS_AVAILABLE:
        _raise_loan_error("Этот экземпляр сейчас недоступен для выдачи.")

        active_loans = Loan.objects.filter(
            reader=reader,
            returned_at__isnull=True,
        )
        now = timezone.now()

        if active_loans.filter(due_at__lt=now).exists():
            _raise_loan_error("У читателя есть просроченная книга.")

        if active_loans.count() >= MAX_ACTIVE_LOANS:
            _raise_loan_error("Читатель уже взял максимально допустимые три книги.")

        loan = Loan.objects.create(
            reader=reader,
            book_copy=book_copy,
            issued_by=issued_by,
            due_at=now + timedelta(days=LOAN_PERIOD_DAYS),
        )

        book_copy.status = STATUS_BORROWED
        book_copy.save(update_fields=("status",))

    logger.info(
        "Выдача создана: loan_id=%s, issued_by_id=%s",
        loan.pk,
        issued_by.pk,
    )

    return loan


def return_book(
    *,
    inventory_number,
    returned_by,
    return_status=STATUS_AVAILABLE,
):
    with transaction.atomic():
        _validate_library_staff(returned_by)

        if return_status not in RETURN_STATUSES:
            _raise_loan_error(
                "После возврата экземпляр может быть доступен или повреждён."
            )

        book_copy = (
            BookCopy.objects.select_for_update()
            .filter(inventory_number=inventory_number)
            .first()
        )
        if book_copy is None:
            _raise_loan_error("Экземпляр с таким инвентарным номером не найден.")

        loan = (
            Loan.objects.select_for_update()
            .filter(
                book_copy=book_copy,
                returned_at__isnull=True,
            )
            .first()
        )
        if loan is None:
            _raise_loan_error("Для этого экземпляра нет активной выдачи.")

        loan.returned_at = timezone.now()
        loan.returned_by = returned_by
        loan.save(update_fields=("returned_at", "returned_by"))

        book_copy.status = return_status
        book_copy.save(update_fields=("status",))

    logger.info(
        "Выдача закрыта: loan_id=%s, returned_by_id=%s",
        loan.pk,
        returned_by.pk,
    )

    return loan
