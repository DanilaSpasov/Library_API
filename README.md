# Library API

REST API для управления физической библиотекой. Проект поддерживает каталог
книг и экземпляров, выдачу и возврат книг, роли пользователей и email-уведомления
о появлении доступного экземпляра.

## Стек

- Python 3.14, Django 6.1, Django REST Framework
- PostgreSQL
- JWT-аутентификация через Simple JWT
- Redis и Celery
- drf-spectacular и Swagger UI
- Poetry

## Возможности

- регистрация по email с подтверждением почты;
- роли читателя, библиотекаря и администратора;
- каталог авторов, жанров, книг и физических экземпляров;
- поиск, фильтрация, сортировка и пагинация каталога;
- выдача и возврат книг по инвентарному номеру;
- контроль просрочек и ограничения на количество активных выдач;
- подписка читателя на недоступную книгу;
- фоновая email-рассылка при появлении доступного экземпляра.
- Telegram-бот с меню каталога, подписок и выдач;
- привязка Telegram к аккаунту библиотеки по одноразовому коду;
- библиотечный AI-помощник через OpenRouter.

## Роли

- **Читатель** просматривает каталог, свои выдачи и управляет своими подписками.
- **Библиотекарь** управляет каталогом и экземплярами, выдаёт и принимает книги.
- **Администратор** обладает всеми правами библиотекаря и управляет системой
  через Django Admin.

## Локальный запуск

Требуются PostgreSQL, Redis и Poetry.

Создайте файл окружения из примера и заполните его своими значениями:

```
cp .env_example .env
```

Установите зависимости и примените миграции:

```
poetry install
poetry run python manage.py migrate
```

Запустите Django:

```
poetry run python manage.py runserver
```

Для фоновой отправки писем запустите Redis и Celery worker в отдельном
терминале:

```
poetry run celery -A config worker --loglevel=info
```

## Переменные окружения

Основные переменные находятся в `.env_example`:

- `SECRET_KEY` — секретный ключ Django;
- `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD` — доступ к PostgreSQL;
- `DATABASE_HOST`, `DATABASE_PORT` — адрес PostgreSQL;
- `EMAIL_*` — настройки отправки почты;
- `CELERY_BROKER_URL` — адрес Redis для очереди задач;
- `CELERY_RESULT_BACKEND` — адрес Redis для результатов Celery.
- `TELEGRAM_BOT_TOKEN` — серверный токен Telegram-бота;
- `TELEGRAM_POLL_TIMEOUT` — время ожидания обновлений Telegram в секундах;
- `OPENROUTER_API_KEY` — серверный API-ключ OpenRouter;
- `OPENROUTER_MODEL` — модель OpenRouter, по умолчанию `openrouter/free`.

Токены Telegram и OpenRouter являются секретами. Храните их только в `.env`
на локальной машине или сервере и не добавляйте этот файл в Git.

## Telegram-бот и OpenRouter

Создайте бота через [@BotFather](https://t.me/BotFather): отправьте команду
`/newbot`, задайте имя и username, затем сохраните полученный токен в
`TELEGRAM_BOT_TOKEN`.

Для AI-помощника создайте API-ключ в OpenRouter и сохраните его в
`OPENROUTER_API_KEY`. В `OPENROUTER_MODEL` можно оставить `openrouter/free`:
этот маршрутизатор выбирает одну из доступных бесплатных моделей. Бесплатные
модели имеют ограничения по числу запросов и могут быть временно недоступны.
Ключ нужен только серверной части и не должен попадать в браузер, сообщения
бота или публичный репозиторий.

Пользователь получает одноразовый код привязки через Library API и отправляет
боту сообщение `/connect КОД`. После успешной привязки бот определяет аккаунт
по Telegram `chat_id`; повторно использовать одноразовый код нельзя.

Для запуска всех сервисов, включая Telegram-бота:

```
docker compose up -d --build
```

Проверить состояние и логи бота:

```
docker compose ps
docker compose logs -f telegram_bot
```

Бот использует long polling, поэтому webhook, домен и открытый входящий порт
для Telegram не требуются. Контейнер `library-api-tunnel`, если он запущен
отдельно, не входит в этот Compose-проект и этой командой не перезапускается.

## Демонстрационный каталог

Заполнить каталог 100 книгами и 300 физическими экземплярами можно командой:

```
poetry run python manage.py seed_demo_library
```

Команда удаляет только старые библиотечные данные. Пользователи при этом не
удаляются. Метаданные книг основаны на открытом наборе
[Goodbooks-10k](https://github.com/zygmuntz/goodbooks-10k), который опубликован
по лицензии [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Названия, имена авторов, жанры и краткие описания адаптированы для
русскоязычного каталога.


## Основные адреса

### Аутентификация

- `POST /api/auth/register/` — регистрация;
- `GET /api/auth/verify-email/{uidb64}/{token}/` — подтверждение email;
- `POST /api/auth/token/` — получение JWT-токенов;
- `POST /api/auth/token/refresh/` — обновление access-токена.
- `POST /api/auth/telegram/connection-code/` — одноразовый код для Telegram.

Для защищённых запросов передайте access-токен:

```
Authorization: Bearer <access_token>
```

### Библиотека

- `/api/catalog/authors/` — авторы;
- `/api/catalog/genres/` — жанры;
- `/api/catalog/books/` — книги;
- `/api/catalog/book-copies/` — физические экземпляры;
- `GET /api/loans/` — выдачи;
- `POST /api/loans/issue/` — выдача книги;
- `POST /api/loans/return/` — возврат книги;
- `/api/subscriptions/` — подписки на доступность.

Полное описание запросов, параметров и ответов доступно в Swagger.

## Документация API

После запуска проекта:

- `http://127.0.0.1:8000/api/docs/` — Swagger UI;
- `http://127.0.0.1:8000/api/schema/` — OpenAPI-схема;
- `http://127.0.0.1:8000/admin/` — Django Admin.
