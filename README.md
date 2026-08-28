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


## Основные адреса

### Аутентификация

- `POST /api/auth/register/` — регистрация;
- `GET /api/auth/verify-email/{uidb64}/{token}/` — подтверждение email;
- `POST /api/auth/token/` — получение JWT-токенов;
- `POST /api/auth/token/refresh/` — обновление access-токена.

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
