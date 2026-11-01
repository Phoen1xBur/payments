from decimal import Decimal

import pytest
from sqlalchemy import func, select

from src.models import Currency, OutboxEvent, PaymentStatus
from src.schemas.payment import PaymentCreate
from src.services.payments import create_payment


def make_body(**kw) -> PaymentCreate:
    data = {
        'amount': '100.50',
        'currency': 'RUB',
        'description': 'test',
        'meta': {'order_id': 42},
        'webhook_url': 'http://example.com/hook',
    } | kw
    return PaymentCreate.model_validate(data)


async def test_create_writes_payment_and_outbox(session):
    payment = await create_payment(session, make_body(), 'key-1')

    assert payment.status == PaymentStatus.PENDING
    assert payment.amount == Decimal('100.50')
    assert payment.currency == Currency.RUB
    assert payment.meta == {'order_id': 42}

    events = (await session.scalars(select(OutboxEvent))).all()
    assert len(events) == 1
    assert events[0].payload == {'payment_id': str(payment.id)}
    assert events[0].published_at is None


async def test_same_idempotency_key_returns_same_payment(session):
    first = await create_payment(session, make_body(), 'key-1')
    second = await create_payment(session, make_body(amount='999'), 'key-1')

    assert second.id == first.id
    assert second.amount == Decimal('100.50')
    assert await session.scalar(select(func.count()).select_from(OutboxEvent)) == 1


def test_amount_must_be_positive():
    with pytest.raises(ValueError):
        make_body(amount='0')
