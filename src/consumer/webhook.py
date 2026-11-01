from typing import Any

import aiohttp

from src.core.config import settings
from src.models import Payment


def webhook_body(payment: Payment) -> dict[str, Any]:
    return {
        'payment_id': str(payment.id),
        'status': payment.status.value,
        'amount': str(payment.amount),
        'currency': payment.currency.value,
        'processed_at': payment.processed_at.isoformat() if payment.processed_at else None,
    }


async def send_webhook(url: str, body: dict[str, Any]) -> None:
    timeout = aiohttp.ClientTimeout(total=settings.webhook_timeout)
    async with (
        aiohttp.ClientSession(timeout=timeout) as http,
        http.post(url, json=body) as resp,
    ):
        resp.raise_for_status()
