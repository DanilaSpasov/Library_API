from django.apps import AppConfig


class TelegramBotConfig(AppConfig):
    """Настройки приложения Telegram-бота."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "telegram_bot"
    verbose_name = "Telegram-бот"
