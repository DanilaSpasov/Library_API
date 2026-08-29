import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from users.models import TelegramConnectionCode, User


class InvalidConnectionCode(Exception):
    pass


class TelegramChatAlreadyConnected(Exception):
    pass


def _get_code_hash(code: str) -> str:
    return salted_hmac(
        "telegram_connection_code",
        code,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def create_connection_code(user: User) -> tuple[str, datetime]:
    code = secrets.token_hex(4)
    expires_at = timezone.now() + timedelta(minutes=10)

    TelegramConnectionCode.objects.update_or_create(
        user=user,
        defaults={
            "code_hash": _get_code_hash(code),
            "expires_at": expires_at,
        },
    )

    return code, expires_at


@transaction.atomic
def connect_telegram_account(chat_id: int, code: str) -> User:
    try:
        connection = (
            TelegramConnectionCode.objects.select_for_update()
            .select_related("user")
            .get(code_hash=_get_code_hash(code))
        )
    except TelegramConnectionCode.DoesNotExist:
        raise InvalidConnectionCode

    if connection.expires_at <= timezone.now():
        connection.delete()
        raise InvalidConnectionCode

    user = connection.user
    other_user = User.objects.filter(telegram_chat_id=chat_id).exclude(pk=user.pk)
    if other_user.exists():
        raise TelegramChatAlreadyConnected

    user.telegram_chat_id = chat_id
    try:
        user.save(update_fields=("telegram_chat_id",))
    except IntegrityError:
        raise TelegramChatAlreadyConnected
    connection.delete()
    return user


def get_user_by_telegram_chat_id(chat_id: int) -> User | None:
    return User.objects.filter(telegram_chat_id=chat_id).first()
