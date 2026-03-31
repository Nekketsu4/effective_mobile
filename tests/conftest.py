from typing import AsyncGenerator

import pytest

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.models.base import Base
from app.config import settings


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(settings.DATABASE_URL_TEST)
    return engine


@pytest.fixture(scope="session", autouse=True)
async def setup_db(test_engine):
    # Создаем и удаляем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    # каждый тест получает свою транзакцию, которая откатывается после теста
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()
