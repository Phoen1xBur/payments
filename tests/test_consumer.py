import uuid

import pytest
from faststream.rabbit import TestRabbitBroker

from src.broker import broker
from src.consumer import main as consumer
from src.core.config import settings


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(settings, 'retry_base_delay', 0)


def test_retry_delay_is_exponential(monkeypatch):
    monkeypatch.setattr(settings, 'retry_base_delay', 1)
    assert [consumer.retry_delay(n) for n in (1, 2, 3)] == [1, 2, 4]


async def test_success_processed_once(monkeypatch):
    calls = []

    async def fake_process(payment_id):
        calls.append(payment_id)

    monkeypatch.setattr(consumer, 'process_payment', fake_process)
    pid = uuid.uuid4()

    async with TestRabbitBroker(broker):
        await broker.publish({'payment_id': str(pid)}, queue='payments.new')

    assert calls == [pid]


async def test_three_attempts_then_reject(monkeypatch):
    calls = []

    async def failing_process(payment_id):
        calls.append(payment_id)
        raise RuntimeError('webhook is down')

    monkeypatch.setattr(consumer, 'process_payment', failing_process)

    async with TestRabbitBroker(broker):
        await broker.publish({'payment_id': str(uuid.uuid4())}, queue='payments.new')
        assert consumer.handle_payment.mock.call_count == settings.max_attempts

    assert len(calls) == settings.max_attempts
