from faststream.rabbit import TestRabbitBroker
from sqlalchemy import select

from src.broker import broker
from src.consumer import main as consumer
from src.models import OutboxEvent
from src.outbox.relay import publish_pending
from src.services.payments import create_payment
from tests.test_payments_service import make_body


async def test_relay_publishes_and_marks_event(session_maker, session, monkeypatch):
    async def noop(payment_id):
        pass

    monkeypatch.setattr(consumer, 'process_payment', noop)
    payment = await create_payment(session, make_body(), 'key-relay')

    async with TestRabbitBroker(broker):
        sent = await publish_pending(session_maker, broker, limit=10)
        consumer.handle_payment.mock.assert_called_once_with({'payment_id': str(payment.id)})
        again = await publish_pending(session_maker, broker, limit=10)

    assert (sent, again) == (1, 0)
    session.expire_all()
    event = await session.scalar(select(OutboxEvent))
    assert event.published_at is not None
