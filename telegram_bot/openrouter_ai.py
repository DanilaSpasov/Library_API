import json

import requests
from django.conf import settings

SAFE_INTENTS = {
    "search_books",
    "list_books",
    "list_subscriptions",
    "list_loans",
    "general_answer",
}

SYSTEM_PROMPT = """Ты определяешь действие для Telegram-бота библиотеки.
Верни только JSON с полями intent, search_query и answer.

Разрешённые intent:
- search_books — пользователь просит показать или найти книгу либо книги автора;
- list_books — пользователь просит показать весь каталог;
- list_subscriptions — пользователь просит показать свои подписки;
- list_loans — пользователь просит показать свои выдачи;
- general_answer — пользователь задаёт обычный вопрос о книге или авторе.

Если пользователь пишет «покажи», «найди» или «есть ли» и называет книгу либо
автора, всегда выбирай search_books. В search_query оставляй только название
книги или фамилию автора. Данные каталога не придумывай: при search_books поле
answer должно быть пустым.

Примеры:
«Покажи книги Толстого» →
{"intent":"search_books","search_query":"Толстой","answer":""}
«Найди Войну и мир» →
{"intent":"search_books","search_query":"Война и мир","answer":""}
«Покажи каталог» →
{"intent":"list_books","search_query":"","answer":""}
«Кто написал Войну и мир?» →
{"intent":"general_answer","search_query":"","answer":"Лев Толстой"}

Не придумывай данные пользователя и не запрашивай базу данных самостоятельно."""


def ask_openrouter(text):
    """Отправляет текст в OpenRouter и возвращает действие для бота."""
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "X-Title": "Library API Telegram Bot",
    }
    data = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30,
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = "\n".join(content.splitlines()[1:-1])

    result = json.loads(content)
    if not isinstance(result, dict):
        raise ValueError("OpenRouter вернул ответ в неверном формате")
    if result.get("intent") not in SAFE_INTENTS:
        result["intent"] = "general_answer"
    result["search_query"] = str(result.get("search_query") or "").strip()
    result["answer"] = str(result.get("answer") or "").strip()
    return result
