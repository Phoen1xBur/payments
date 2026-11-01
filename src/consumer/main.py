import asyncio
import logging
import uuid
from datetime import UTC, datetime

from faststream import AckPolicy, FastStream
from faststream.rabbit import RabbitMessage
from sqlalchemy import update

from src.broker import broker, declare_queues, payments_queue
from src.consumer import gateway
from src.consumer.webhook import send_webhook, webhook_body
from src.core.config import settings
from src.db.session import SessionLocal
from src.models import Payment, PaymentStatus
from src.schemas.payment import PaymentEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger('consumer')

app = FastStream(broker)


@app.after_startup
async def setup() -> None:
    await declare_queues(broker)


async def process_payment(payment_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            logger.warning('payment %s not found, skip', payment_id)
            return

        if payment.status == PaymentStatus.PENDING:
            ok = await gateway.charge()
            await session.execute(
                update(Payment)
                .where(Payment.id == payment_id, Payment.status == PaymentStatus.PENDING)
                .values(
                    status=PaymentStatus.SUCCEEDED if ok else PaymentStatus.FAILED,
                    processed_at=datetime.now(UTC),
                )
            )
            await session.commit()
            await session.refresh(payment)
            logger.info('payment %s -> %s', payment_id, payment.status)

    await send_webhook(payment.webhook_url, webhook_body(payment))


def retry_delay(attempt: int) -> float:
    return settings.retry_base_delay * 2 ** (attempt - 1)


@broker.subscriber(payments_queue, ack_policy=AckPolicy.MANUAL)
async def handle_payment(event: PaymentEvent, msg: RabbitMessage) -> None:
    attempt = int(msg.headers.get('x-attempt', 1))
    try:
        await process_payment(event.payment_id)
    except Exception:
        if attempt >= settings.max_attempts:
            logger.exception('payment %s failed %s times, to DLQ', event.payment_id, attempt)
            await msg.reject(requeue=False)
            return

        delay = retry_delay(attempt)
        logger.warning(
            'payment %s attempt %s failed, retry in %.0fs',
            event.payment_id,
            attempt,
            delay,
            exc_info=True,
        )
        await asyncio.sleep(delay)
        await broker.publish(
            event,
            queue=payments_queue,
            headers={'x-attempt': attempt + 1},
            message_id=msg.message_id,
            persist=True,
        )
        await msg.ack()
        return

    await msg.ack()
