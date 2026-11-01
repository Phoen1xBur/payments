import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from src.api.deps import SessionDep
from src.schemas.payment import PaymentAccepted, PaymentCreate, PaymentOut
from src.services import payments as service

router = APIRouter(prefix='/payments', tags=['payments'])


@router.post('/', status_code=status.HTTP_202_ACCEPTED, response_model=PaymentAccepted)
async def create_payment(
    body: PaymentCreate,
    session: SessionDep,
    idempotency_key: Annotated[str, Header(alias='Idempotency-Key', min_length=1, max_length=255)],
) -> PaymentAccepted:
    payment = await service.create_payment(session, body, idempotency_key)
    return PaymentAccepted.model_validate(payment)


@router.get('/{payment_id}', response_model=PaymentOut)
async def get_payment(payment_id: uuid.UUID, session: SessionDep) -> PaymentOut:
    payment = await service.get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Payment not found')
    return PaymentOut.model_validate(payment)
