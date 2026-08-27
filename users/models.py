from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

ROLE_READER = "reader"
ROLE_LIBRARIAN = "librarian"
ROLE_ADMIN = "admin"

ROLE_CHOICES = (
    (ROLE_READER, "Читатель"),
    (ROLE_LIBRARIAN, "Библиотекарь"),
    (ROLE_ADMIN, "Администратор"),
)


class UserManager(BaseUserManager):
    """Менеджер пользователей с авторизацией по email."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")

        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("is_email_verified", False)

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", ROLE_ADMIN)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True")

        if extra_fields.get("is_email_verified") is not True:
            raise ValueError("Email суперпользователя должен быть подтверждён")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    email = models.EmailField(
        "Электронная почта",
        unique=True,
    )
    role = models.CharField(
        "Роль",
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_READER,
    )
    is_active = models.BooleanField(
        "Активен",
        default=False,
    )
    is_email_verified = models.BooleanField(
        "Email подтверждён",
        default=False,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email
