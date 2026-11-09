"""Configurações e fixtures globais de teste para o ULTRON."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models import Base
from app.intelligence.providers.mock import MockProvider
from app.intelligence.providers.registry import ProviderRegistry


@pytest_asyncio.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """Cria um banco SQLite em memória isolado para cada teste."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
def mock_registry() -> ProviderRegistry:
    """Retorna um ProviderRegistry configurado com MockProvider como padrão."""
    registry = ProviderRegistry(default_provider_id="mock")
    registry.register_provider(MockProvider())
    return registry
