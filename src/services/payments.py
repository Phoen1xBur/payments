import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import OutboxEvent, Payment
from src.schemas.payment import PaymentCreate, PaymentEvent

PAYMENT_CREATED = 'payment.created'


async def get_by_idempotency_key(session: AsyncSession, key: str) -> Payment | None:
    return await session.scalar(select(Payment).where(Payment.idempotency_key == key))


async def create_payment(
    session: AsyncSession, data: PaymentCreate, idempotency_key: str
) -> Payment:
    existing = await get_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        return existing

    payment = Payment(
        id=uuid.uuid4(),
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        meta=data.meta,
        idempotency_key=idempotency_key,
        webhook_url=str(data.webhook_url),
    )
    event = PaymentEvent(payment_id=payment.id)
    session.add_all(
        [payment, OutboxEvent(event_type=PAYMENT_CREATED, payload=event.model_dump(mode='json'))]
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_by_idempotency_key(session, idempotency_key)
        if existing is None:
            raise
        return existing

    await session.refresh(payment)
    return payment


async def get_payment(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return await session.get(Payment, payment_id)
