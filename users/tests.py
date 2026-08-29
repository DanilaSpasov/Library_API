from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import TelegramConnectionCode, User
from users.telegram_connections import (
    InvalidConnectionCode,
    TelegramChatAlreadyConnected,
    connect_telegram_account,
    create_connection_code,
    get_user_by_telegram_chat_id,
)


class UserManagerTests(TestCase):
    """Тесты менеджера пользователей."""

    def test_create_user(self):
        """Тестирование создания обычного пользователя."""
        user = User.objects.create_user("Reader@Example.com", "StrongPass123!")

        self.assertEqual(user.email, "Reader@example.com")
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_create_user_without_email(self):
        """Тестирование запрета создания пользователя без email."""
        with self.assertRaises(ValueError):
            User.objects.create_user("", "StrongPass123!")


@override_settings(
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
)
class AuthenticationTests(APITestCase):
    """Тесты регистрации и авторизации пользователей."""

    def test_register_and_verify_email(self):
        """Тестирование регистрации и подтверждения email."""
        response = self.client.post(
            reverse("users:register"),
            {"email": "reader@example.com", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="reader@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        verify_response = self.client.get(
            reverse(
                "users:verify_email",
                kwargs={"uidb64": uid, "token": token},
            )
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)

    def test_invalid_verification_link(self):
        """Тестирование неправильной ссылки подтверждения email."""
        response = self.client.get(
            reverse(
                "users:verify_email",
                kwargs={"uidb64": "wrong", "token": "wrong"},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_active_user_can_get_token(self):
        """Тестирование получения JWT-токенов активным пользователем."""
        User.objects.create_user(
            "reader@example.com",
            "StrongPass123!",
            is_active=True,
            is_email_verified=True,
        )

        response = self.client.post(
            reverse("users:token_obtain_pair"),
            {"email": "reader@example.com", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_telegram_code_requires_authentication(self):
        """Тестирование запрета получения Telegram-кода без авторизации."""
        response = self.client.post(reverse("users:telegram_connection_code"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_gets_telegram_code(self):
        """Тестирование получения Telegram-кода авторизованным пользователем."""
        user = User.objects.create_user(
            "reader@example.com",
            "StrongPass123!",
            is_active=True,
            is_email_verified=True,
        )
        self.client.force_authenticate(user)

        response = self.client.post(reverse("users:telegram_connection_code"))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["code"]), 8)
        self.assertTrue(TelegramConnectionCode.objects.filter(user=user).exists())


class TelegramConnectionTests(TestCase):
    """Тесты привязки Telegram-аккаунта."""

    def setUp(self):
        """Создание пользователя перед каждым тестом привязки Telegram."""
        self.user = User.objects.create_user(
            "reader@example.com",
            "StrongPass123!",
            is_active=True,
            is_email_verified=True,
        )

    def test_connect_telegram_account(self):
        """Тестирование привязки Telegram-аккаунта по одноразовому коду."""
        code, _ = create_connection_code(self.user)

        connected_user = connect_telegram_account(12345, code)

        self.assertEqual(connected_user.telegram_chat_id, 12345)
        self.assertEqual(get_user_by_telegram_chat_id(12345), self.user)
        self.assertFalse(TelegramConnectionCode.objects.filter(user=self.user).exists())

    def test_wrong_code_is_rejected(self):
        """Тестирование отклонения неправильного Telegram-кода."""
        with self.assertRaises(InvalidConnectionCode):
            connect_telegram_account(12345, "wrong")

    def test_connected_chat_cannot_be_used_by_another_user(self):
        """Тестирование запрета повторной привязки одного Telegram-чата."""
        User.objects.create_user(
            "other@example.com",
            "StrongPass123!",
            is_active=True,
            is_email_verified=True,
            telegram_chat_id=12345,
        )
        code, _ = create_connection_code(self.user)

        with self.assertRaises(TelegramChatAlreadyConnected):
            connect_telegram_account(12345, code)
