import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.models import Currency, PaymentStatus


class PaymentCreate(BaseModel):
    amount: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
    currency: Currency
    description: str | None = Field(default=None, max_length=1000)
    meta: dict[str, Any] | None = None
    webhook_url: HttpUrl


class PaymentAccepted(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID = Field(validation_alias='id')
    status: PaymentStatus
    created_at: datetime


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str | None
    meta: dict[str, Any] | None = None
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None


class PaymentEvent(BaseModel):
    payment_id: uuid.UUID
