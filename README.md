# Payments service

Тестовое задание: асинхронный сервис обработки платежей.

Стек: FastAPI, Pydantic v2, SQLAlchemy 2 (async) + asyncpg, PostgreSQL, Alembic, RabbitMQ + FastStream, aiohttp для webhook.

## Как это работает

1. `POST /api/v1/payments` - создаётся платёж в таблице `payments` и запись в `outbox`, ответ `202`.
2. `outbox-relay` периодически забирает неопубликованные события из `outbox` (`SELECT ... FOR UPDATE SKIP LOCKED`), публикует их в очередь `payments.new` и проставляет `published_at`.
3. `consumer` читает `payments.new`: эмулирует платёжный шлюз (sleep 2-5 сек, ~90% success), обновляет статус платежа и отправляет webhook на `webhook_url`.
4. При ошибке (например webhook) сообщение возвращается в `payments.new` с заголовком `x-attempt` и задержкой 1с, 2с... После 3-й неудачи выполняется `reject`, сообщение уходит через exchange `payments.dlx` в очередь `payments.new.dlq`.

Повторная обработка допустима: если у платежа уже финальный статус, шлюз повторно не вызывается, отправляется только webhook. Доставка at-least-once, поэтому webhook может прийти больше одного раза.

Идемпотентность: заголовок `Idempotency-Key`, в таблице unique. Повторный запрос с тем же ключом возвращает тот же платёж (тот же `payment_id`), новый не создаётся.

Очереди в RabbitMQ:
- `payments.new` - основная, с `x-dead-letter-exchange=payments.dlx`
- `payments.dlx` - exchange для мертвых сообщений
- `payments.new.dlq` - DLQ

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Запускаются postgres, rabbitmq, api (сначала alembic upgrade head), outbox-relay и consumer.

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- RabbitMQ UI: http://localhost:15672 (guest / guest)

Для всех запросов к API нужен заголовок `X-API-Key` (значение из `API_KEY` в `.env`), иначе 401.

## Примеры

Создание платежа. Для webhook можно использовать URL с https://webhook.site либо свой сервер по адресу `http://host.docker.internal:<порт>/...`.

```bash
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: order-1" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "1500.00",
    "currency": "RUB",
    "description": "Оплата заказа #1",
    "meta": {"order_id": 1},
    "webhook_url": "https://webhook.site/your-id"
  }'
```

Ответ 202:

```json
{"payment_id": "1d6c...", "status": "pending", "created_at": "2026-10-27T10:01:07.557684Z"}
```

Повторный запрос с тем же `Idempotency-Key` вернёт тот же `payment_id`.

Получение платежа:

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> -H "X-API-Key: change-me"
```

Через несколько секунд статус станет `succeeded` или `failed`, на `webhook_url` придёт POST:

```json
{"payment_id": "1d6c...", "status": "succeeded", "amount": "1500.00", "currency": "RUB", "processed_at": "..."}
```

Проверить DLQ: необходимо создать платёж с `webhook_url`, который всегда отдаёт 500 (или недоступен), например `http://host.docker.internal:9/`. Consumer выполнит 3 попытки, после чего сообщение попадёт в `payments.new.dlq` (можно посмотреть в RabbitMQ UI).

## Локально без docker app

Если postgres и rabbitmq уже запущены (или только они в docker):

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn src.run:app --reload
uv run python -m src.outbox.relay
uv run faststream run src.consumer.main:app
```

В `.env` вместо хостов `postgres` / `rabbitmq` указать `localhost`.

Тесты (нужна доступная БД; по умолчанию используется `postgresql+asyncpg://payments:payments@localhost:5432/payments`, можно переопределить через `TEST_DATABASE_URL`; если БД недоступна - тесты будут пропущены):

```bash
uv run pytest
uv run ruff check .
```

## Переменные

Читаются из `.env` (см. `src/core/config.py`):

- `DATABASE_URL` - по умолчанию `postgresql+asyncpg://payments:payments@localhost:5432/payments`
- `RABBIT_URL` - по умолчанию `amqp://guest:guest@localhost:5672/`
- `API_KEY` - по умолчанию `change-me`
- `MAX_ATTEMPTS` - 3
- `RETRY_BASE_DELAY` - 1 (секунды, задержка `base * 2^(n-1)`)
- `WEBHOOK_TIMEOUT` - 10
- `OUTBOX_POLL_INTERVAL` - 1
- `OUTBOX_BATCH_SIZE` - 100
