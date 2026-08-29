import requests
from django.conf import settings


def _request(method, data, timeout=10):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
    response = requests.post(url, json=data, timeout=timeout)
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise requests.RequestException(result.get("description", "Telegram API error"))
    return result.get("result")


def get_updates(offset=None):
    data = {
        "timeout": settings.TELEGRAM_POLL_TIMEOUT,
        "allowed_updates": ["message", "callback_query"],
    }
    if offset is not None:
        data["offset"] = offset
    return _request("getUpdates", data, settings.TELEGRAM_POLL_TIMEOUT + 5)


def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    return _request("sendMessage", data)


def answer_callback(callback_id, text):
    return _request(
        "answerCallbackQuery",
        {"callback_query_id": callback_id, "text": text},
    )
