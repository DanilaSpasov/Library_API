from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.models import User


class EmailVerificationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password",
        )

    def validate(self, attrs):
        user = User(email=attrs["email"])
        validate_password(attrs["password"], user=user)

        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
