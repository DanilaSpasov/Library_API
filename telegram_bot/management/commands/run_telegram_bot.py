import logging
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from telegram_bot.bot import handle_update
from telegram_bot.telegram_api import get_updates


class Command(BaseCommand):
    help = "Запускает Telegram-бота Library API в режиме long polling."

    def handle(self, *args, **options):
        required_settings = {
            "TELEGRAM_BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN,
            "OPENROUTER_API_KEY": settings.OPENROUTER_API_KEY,
            "OPENROUTER_MODEL": settings.OPENROUTER_MODEL,
        }
        missing = [name for name, value in required_settings.items() if not value]
        if missing:
            raise CommandError(
                "Не заданы обязательные настройки: " + ", ".join(missing)
            )

        offset = None
        self.stdout.write("Telegram-бот запущен")
        while True:
            try:
                for update in get_updates(offset):
                    handle_update(update)
                    offset = update["update_id"] + 1
            except requests.RequestException:
                logging.warning("Telegram polling failed; retrying")
                time.sleep(3)
            except Exception:
                logging.exception("Telegram update processing failed")
                time.sleep(1)
