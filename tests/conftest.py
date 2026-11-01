import os

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base

load_dotenv()

TEST_DB = os.getenv(
    'TEST_DATABASE_URL', 'postgresql+asyncpg://payments:payments@localhost:5432/payments'
)


@pytest.fixture
async def session_maker():
    engine = create_async_engine(TEST_DB)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f'postgres unavailable for tests: {exc}')

    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(session_maker):
    async with session_maker() as s:
        yield s