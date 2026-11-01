import asyncio
import random


async def charge() -> bool:
    await asyncio.sleep(random.uniform(2, 5))
    return random.random() < 0.9
