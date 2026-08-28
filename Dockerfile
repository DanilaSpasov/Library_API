FROM python:3.14-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.2.1

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root --no-interaction --no-ansi

COPY . .

EXPOSE 8000

CMD ["poetry", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
