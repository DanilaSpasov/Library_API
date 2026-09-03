from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.models import User


class EmailVerificationResponseSerializer(serializers.Serializer):
    """Сериализатор ответа при подтверждении email."""

    detail = serializers.CharField()


class TelegramConnectionCodeSerializer(serializers.Serializer):
    """Сериализатор одноразового Telegram-кода."""

    code = serializers.CharField()
    expires_at = serializers.DateTimeField()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор регистрации пользователя."""

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        """Поля пользователя, используемые при регистрации."""

        model = User
        fields = (
            "email",
            "password",
        )

    def validate(self, attrs):
        """Проверяет пароль нового пользователя."""
        user = User(email=attrs["email"])
        validate_password(attrs["password"], user=user)

        return attrs

    def create(self, validated_data):
        """Создаёт пользователя из проверенных данных."""
        return User.objects.create_user(**validated_data)
