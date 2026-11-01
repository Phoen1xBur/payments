import asyncio
import logging
from datetime import UTC, datetime

from faststream.rabbit import RabbitBroker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.broker import broker, declare_queues, payments_queue
from src.core.config import settings
from src.db.session import SessionLocal
from src.models import OutboxEvent

logger = logging.getLogger('outbox.relay')


async def publish_pending(
    session_maker: async_sessionmaker[AsyncSession], rabbit: RabbitBroker, limit: int
) -> int:
    async with session_maker() as session, session.begin():
        events = (
            await session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()

        for event in events:
            await rabbit.publish(
                event.payload,
                queue=payments_queue,
                message_id=str(event.id),
                message_type=event.event_type,
                persist=True,
            )
            event.published_at = datetime.now(UTC)

    return len(events)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    await broker.connect()
    await declare_queues(broker)
    logger.info('outbox relay started')
    try:
        while True:
            try:
                sent = await publish_pending(SessionLocal, broker, settings.outbox_batch_size)
            except Exception:
                logger.exception('outbox publish failed')
                sent = 0
            if sent:
                logger.info('published %s events', sent)
            else:
                await asyncio.sleep(settings.outbox_poll_interval)
    finally:
        await broker.stop()


if __name__ == '__main__':
    asyncio.run(main())
