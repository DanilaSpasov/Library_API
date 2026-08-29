from unittest.mock import patch

from django.test import TestCase

from library.models import STATUS_MAINTENANCE, Author, Book, BookCopy
from telegram_bot.bot import book_detail, handle_message, subscribe, unsubscribe
from telegram_bot.bot import waiting_for_search
from users.models import User


class TelegramBotTests(TestCase):
    """Тесты основных действий Telegram-бота."""

    def setUp(self):
        """Создание пользователя и книги перед тестами бота."""
        waiting_for_search.clear()
        self.user = User.objects.create_user(
            "reader@example.com",
            "StrongPass123!",
            is_active=True,
            is_email_verified=True,
            telegram_chat_id=12345,
        )
        self.author = Author.objects.create(full_name="Лев Толстой")
        self.book = Book.objects.create(
            title="Война и мир",
            description="Роман о войне 1812 года.",
        )
        self.book.authors.add(self.author)
        BookCopy.objects.create(
            book=self.book,
            inventory_number="BOOK-001",
            status=STATUS_MAINTENANCE,
        )

    @patch("telegram_bot.bot.send_message")
    def test_start_message(self, mocked_send_message):
        """Тестирование ответа бота на команду start."""
        handle_message({"chat": {"id": 12345}, "text": "/start"})

        text = mocked_send_message.call_args.args[1]
        self.assertIn("Добро пожаловать", text)

    @patch("telegram_bot.bot.send_message")
    def test_search_books(self, mocked_send_message):
        """Тестирование поиска книги через меню Telegram."""
        handle_message({"chat": {"id": 12345}, "text": "🔎 Поиск"})
        handle_message({"chat": {"id": 12345}, "text": "Толстой"})

        text = mocked_send_message.call_args.args[1]
        self.assertIn("Война и мир", text)

    @patch("telegram_bot.bot.send_message")
    def test_book_detail(self, mocked_send_message):
        """Тестирование показа подробной информации о книге."""
        result = book_detail(12345, self.book.id)

        self.assertEqual(result, "Готово")
        self.assertIn("сейчас недоступна", mocked_send_message.call_args.args[1])

    def test_subscribe_and_unsubscribe(self):
        """Тестирование подписки и отписки через Telegram."""
        self.assertEqual(subscribe(12345, self.book.id), "Подписка добавлена")
        self.assertEqual(subscribe(12345, self.book.id), "Вы уже подписаны")
        self.assertEqual(unsubscribe(12345, self.book.id), "Подписка отменена")
