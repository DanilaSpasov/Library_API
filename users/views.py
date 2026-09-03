import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.serializers import (
    EmailVerificationResponseSerializer,
    TelegramConnectionCodeSerializer,
    UserRegistrationSerializer,
)
from users.telegram_connections import create_connection_code

logger = logging.getLogger(__name__)


class UserRegistrationView(CreateAPIView):
    """Регистрирует пользователя и отправляет письмо подтверждения."""

    serializer_class = UserRegistrationSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer):
        """Сохраняет пользователя и отправляет ссылку подтверждения."""
        user = None

        try:
            with transaction.atomic():
                user = serializer.save()
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                verification_url = self.request.build_absolute_uri(
                    reverse(
                        "users:verify_email",
                        kwargs={
                            "uidb64": uid,
                            "token": token,
                        },
                    )
                )

                send_mail(
                    subject="Подтверждение регистрации",
                    message=(
                        "Для подтверждения email перейдите по ссылке:\n"
                        f"{verification_url}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                )
        except Exception as error:
            logger.exception(
                "Не удалось отправить письмо подтверждения пользователю %s",
                getattr(user, "pk", None),
            )
            raise APIException(
                "Не удалось отправить письмо. Попробуйте зарегистрироваться позже."
            ) from error


class UserEmailVerificationView(APIView):
    """Подтверждает email пользователя по одноразовой ссылке."""

    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Подтверждение email",
        responses={
            200: EmailVerificationResponseSerializer,
            400: EmailVerificationResponseSerializer,
        },
    )
    def get(self, request, uidb64, token):
        """Проверяет токен и активирует пользователя."""
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
        except (
            TypeError,
            ValueError,
            OverflowError,
            UnicodeDecodeError,
            User.DoesNotExist,
        ):
            return Response(
                {"detail": "Ссылка подтверждения недействительна."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_email_verified or not default_token_generator.check_token(
            user,
            token,
        ):
            return Response(
                {"detail": "Ссылка подтверждения недействительна или истекла."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=("is_email_verified", "is_active"))

        return Response(
            {"detail": "Email подтверждён. Теперь вы можете войти."},
            status=status.HTTP_200_OK,
        )


class TelegramConnectionCodeView(APIView):
    """Возвращает код для привязки Telegram-аккаунта."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Получение кода подключения Telegram",
        responses={201: TelegramConnectionCodeSerializer},
    )
    def post(self, request):
        """Создаёт новый одноразовый код подключения."""
        code, expires_at = create_connection_code(request.user)
        serializer = TelegramConnectionCodeSerializer(
            {"code": code, "expires_at": expires_at}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
