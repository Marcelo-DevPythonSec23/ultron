"""Gerenciamento de conexões assíncronas do banco de dados via SQLAlchemy 2.0."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.database.models import Base

logger = logging.getLogger("ultron.database")

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Retorna a engine assíncrona única configurada."""
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if "sqlite" in settings.DATABASE_URL:
            connect_args["check_same_thread"] = False

        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            connect_args=connect_args,
        )

        # Habilitar modo WAL e chaves estrangeiras no SQLite
        if "sqlite" in settings.DATABASE_URL:
            @event.listens_for(_engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retorna a fábrica de sessões assíncronas."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def init_db() -> None:
    """Inicializa as tabelas do banco de dados assincronamente."""
    engine = get_engine()
    async with engine.begin() as conn:
        logger.info("Criando tabelas do banco de dados se não existirem...")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Banco de dados inicializado com sucesso.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Gerador assíncrono para injeção de dependência de sessão de banco."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
