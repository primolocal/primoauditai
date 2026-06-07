"""
Test configuration — override database to SQLite for tests.
"""
import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.models import Base

# Force SQLite for all tests before any imports happen
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(autouse=True)
async def _override_db(monkeypatch):
    """Override database to SQLite in-memory for tests."""
    from src.core import database

    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    test_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "async_session", test_session)

    async def _get_db():
        async with test_session() as session:
            try:
                yield session
            finally:
                await session.close()

    monkeypatch.setattr(database, "get_db", _get_db)

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
