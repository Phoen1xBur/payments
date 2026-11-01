from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from src.core.config import settings

PAYMENTS_QUEUE: str = 'payments.new'
DLX_NAME: str = 'payments.dlx'
DLQ_NAME: str = 'payments.new.dlq'

broker = RabbitBroker(settings.rabbit_url)

dead_letter_exchange = RabbitExchange(DLX_NAME, type=ExchangeType.DIRECT, durable=True)
dead_letter_queue = RabbitQueue(DLQ_NAME, durable=True, routing_key=DLQ_NAME)

payments_queue = RabbitQueue(
    PAYMENTS_QUEUE,
    durable=True,
    arguments={
        'x-dead-letter-exchange': DLX_NAME,
        'x-dead-letter-routing-key': DLQ_NAME,
    },
)


async def declare_queues(rabbit: RabbitBroker) -> None:
    exchange = await rabbit.declare_exchange(dead_letter_exchange)
    dlq = await rabbit.declare_queue(dead_letter_queue)
    await dlq.bind(exchange, routing_key=DLQ_NAME)
    await rabbit.declare_queue(payments_queue)
