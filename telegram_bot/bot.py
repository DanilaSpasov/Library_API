import logging

import requests
from django.db.models import Exists, OuterRef, Q

from library.models import (
    STATUS_AVAILABLE,
    AvailabilitySubscription,
    Book,
    BookCopy,
    Loan,
)
from telegram_bot.openrouter_ai import ask_openrouter
from telegram_bot.telegram_api import answer_callback, send_message
from users.telegram_connections import (
    InvalidConnectionCode,
    TelegramChatAlreadyConnected,
    connect_telegram_account,
    get_user_by_telegram_chat_id,
)

logger = logging.getLogger(__name__)
waiting_for_search = set()

MAIN_MENU = {
    "keyboard": [
        [{"text": "📚 Книги"}, {"text": "🔎 Поиск"}],
        [{"text": "⭐ Мои подписки"}, {"text": "📖 Мои выдачи"}],
        [{"text": "🔗 Привязать аккаунт"}, {"text": "ℹ️ Помощь"}],
    ],
    "resize_keyboard": True,
}


def reply(chat_id, text, markup=None):
    """Отправляет ответ с основным меню."""
    send_message(chat_id, text, markup or MAIN_MENU)


def connected_user(chat_id):
    """Возвращает привязанного пользователя или просит подключить аккаунт."""
    user = get_user_by_telegram_chat_id(chat_id=chat_id)
    if user is None:
        reply(chat_id, "Сначала привяжите аккаунт командой /connect КОД.")
    return user


def get_books(query=""):
    """Возвращает активные книги по поисковому запросу."""
    available_copy = BookCopy.objects.filter(
        book_id=OuterRef("pk"),
        status=STATUS_AVAILABLE,
    )
    books = Book.objects.filter(is_active=True).prefetch_related("authors")
    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(authors__full_name__icontains=query)
            | Q(isbn__icontains=query)
        )
    return books.annotate(is_available=Exists(available_copy)).distinct()[:10]


def show_books(chat_id, query=""):
    """Отправляет найденные книги и кнопки действий."""
    books = list(get_books(query))
    if not books:
        reply(chat_id, "Книги не найдены.")
        return

    lines = []
    buttons = []
    for book in books:
        authors = ", ".join(author.full_name for author in book.authors.all())
        lines.append(f"{book.title} — {authors or 'автор не указан'}")
        row = [
            {
                "text": f"Подробнее: {book.title}",
                "callback_data": f"book:detail:{book.id}",
            }
        ]
        if not book.is_available:
            row.append(
                {
                    "text": "Подписаться",
                    "callback_data": f"book:subscribe:{book.id}",
                }
            )
        buttons.append(row)
    send_message(chat_id, "\n".join(lines), {"inline_keyboard": buttons})


def start(chat_id, _text):
    """Показывает приветствие и основное меню."""
    reply(chat_id, "Добро пожаловать в Library API! Выберите действие.")


def connect(chat_id, text):
    """Привязывает Telegram-чат по команде с одноразовым кодом."""
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        reply(chat_id, "Используйте команду /connect КОД.")
        return
    try:
        connect_telegram_account(chat_id=chat_id, code=parts[1].strip())
        reply(chat_id, "Аккаунт успешно привязан.")
    except InvalidConnectionCode:
        reply(chat_id, "Код недействителен, истёк или уже использован.")
    except TelegramChatAlreadyConnected:
        reply(chat_id, "Этот Telegram-чат уже привязан к другому аккаунту.")


def books(chat_id, _text):
    """Показывает список книг."""
    show_books(chat_id)


def search(chat_id, _text):
    """Переводит чат в режим ожидания поискового запроса."""
    waiting_for_search.add(chat_id)
    reply(chat_id, "Напишите название книги, автора или ISBN.")


def subscriptions(chat_id, _text):
    """Показывает активные подписки пользователя."""
    user = connected_user(chat_id)
    if user is None:
        return
    items = AvailabilitySubscription.objects.filter(
        reader=user,
        notified_at__isnull=True,
    ).select_related("book")
    items = list(items)
    if not items:
        reply(chat_id, "Мои подписки\nСписок пуст.")
        return

    body = "\n".join(f"• {item.book.title}" for item in items)
    buttons = [
        [
            {
                "text": f"Отписаться: {item.book.title}",
                "callback_data": f"book:unsubscribe:{item.book.id}",
            }
        ]
        for item in items
    ]
    send_message(chat_id, f"Мои подписки\n{body}", {"inline_keyboard": buttons})


def loans(chat_id, _text):
    """Показывает активные выдачи пользователя."""
    user = connected_user(chat_id)
    if user is None:
        return
    items = Loan.objects.filter(
        reader=user,
        returned_at__isnull=True,
    ).select_related("book_copy__book")
    body = (
        "\n".join(
            f"• {item.book_copy.book.title} — вернуть до {item.due_at:%d.%m.%Y}"
            for item in items
        )
        or "Список пуст."
    )
    reply(chat_id, f"Мои выдачи\n{body}")


def connect_help(chat_id, _text):
    """Объясняет способ привязки Telegram-аккаунта."""
    reply(
        chat_id,
        "Получите одноразовый код в Library API и отправьте /connect КОД.",
    )


def help_message(chat_id, _text):
    """Показывает краткую справку по боту."""
    reply(
        chat_id,
        "Используйте кнопки меню или задайте вопрос о книгах обычным текстом.",
    )


MESSAGE_HANDLERS = {
    "/start": start,
    "📚 Книги": books,
    "🔎 Поиск": search,
    "⭐ Мои подписки": subscriptions,
    "📖 Мои выдачи": loans,
    "🔗 Привязать аккаунт": connect_help,
    "ℹ️ Помощь": help_message,
}


def handle_message(message):
    """Выбирает действие для входящего сообщения."""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    if chat_id is None or not text:
        return
    if text.startswith("/connect"):
        connect(chat_id, text)
        return
    handler = MESSAGE_HANDLERS.get(text)
    if handler:
        handler(chat_id, text)
        return
    if chat_id in waiting_for_search:
        waiting_for_search.discard(chat_id)
        show_books(chat_id, text)
        return
    handle_free_text(chat_id, text)


def handle_free_text(chat_id, text):
    """Обрабатывает обычный текст с помощью OpenRouter."""
    try:
        result = ask_openrouter(text)
    except (requests.RequestException, ValueError, KeyError, IndexError):
        logger.warning("OpenRouter request failed")
        reply(
            chat_id,
            "ИИ-помощник временно недоступен. Кнопки меню продолжают работать.",
        )
        return

    handler = AI_HANDLERS[result["intent"]]
    handler(chat_id, result)


def ai_search(chat_id, result):
    """Выполняет поиск книги по ответу OpenRouter."""
    show_books(chat_id, result["search_query"])


def ai_books(chat_id, _result):
    """Показывает каталог по ответу OpenRouter."""
    show_books(chat_id)


def ai_subscriptions(chat_id, _result):
    """Показывает подписки по ответу OpenRouter."""
    subscriptions(chat_id, "")


def ai_loans(chat_id, _result):
    """Показывает выдачи по ответу OpenRouter."""
    loans(chat_id, "")


def ai_answer(chat_id, result):
    """Отправляет обычный текстовый ответ OpenRouter."""
    reply(chat_id, result["answer"] or "Попробуйте уточнить вопрос.")


AI_HANDLERS = {
    "search_books": ai_search,
    "list_books": ai_books,
    "list_subscriptions": ai_subscriptions,
    "list_loans": ai_loans,
    "general_answer": ai_answer,
}


def book_detail(chat_id, book_id):
    """Показывает подробную информацию о книге."""
    book = (
        Book.objects.prefetch_related("authors")
        .filter(
            id=book_id,
            is_active=True,
        )
        .first()
    )
    if book is None:
        reply(chat_id, "Книга не найдена.")
        return "Книга не найдена"
    authors = ", ".join(author.full_name for author in book.authors.all())
    available = book.copies.filter(status=STATUS_AVAILABLE).exists()
    status = "доступна" if available else "сейчас недоступна"
    reply(chat_id, f"{book.title}\n{authors}\nКнига {status}.\n{book.description}")
    return "Готово"


def subscribe(chat_id, book_id):
    """Подписывает пользователя на недоступную книгу."""
    user = connected_user(chat_id)
    if user is None:
        return "Сначала привяжите аккаунт"
    book = Book.objects.filter(id=book_id, is_active=True).first()
    if book is None:
        return "Книга не найдена"
    if book.copies.filter(status=STATUS_AVAILABLE).exists():
        return "Книга уже доступна"
    _, created = AvailabilitySubscription.objects.get_or_create(
        reader=user,
        book=book,
        notified_at__isnull=True,
        defaults={"notified_at": None},
    )
    return "Подписка добавлена" if created else "Вы уже подписаны"


def unsubscribe(chat_id, book_id):
    """Отменяет подписку пользователя на книгу."""
    user = connected_user(chat_id)
    if user is None:
        return "Сначала привяжите аккаунт"
    deleted, _ = AvailabilitySubscription.objects.filter(
        reader=user,
        book_id=book_id,
        notified_at__isnull=True,
    ).delete()
    return "Подписка отменена" if deleted else "Подписка не найдена"


CALLBACK_HANDLERS = {
    "detail": book_detail,
    "subscribe": subscribe,
    "unsubscribe": unsubscribe,
}


def handle_callback(callback):
    """Обрабатывает нажатие inline-кнопки."""
    callback_id = callback.get("id")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    parts = callback.get("data", "").split(":")
    if callback_id is None or chat_id is None or len(parts) != 3:
        return
    namespace, action, raw_book_id = parts
    handler = CALLBACK_HANDLERS.get(action)
    if namespace != "book" or handler is None or not raw_book_id.isdigit():
        answer_callback(callback_id, "Неизвестное действие")
        return
    answer_callback(callback_id, handler(chat_id, int(raw_book_id)))


def handle_update(update):
    """Определяет тип обновления Telegram."""
    if "callback_query" in update:
        handle_callback(update["callback_query"])
    elif "message" in update:
        handle_message(update["message"])
