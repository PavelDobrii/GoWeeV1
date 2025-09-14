"""Database helpers using SQLAlchemy."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from alembic import command  # type: ignore[attr-defined]
from alembic.config import Config

from .settings import settings

Base = declarative_base()

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.postgres_dsn, future=True, echo=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope around a series of operations."""

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session


def alembic_config() -> Config:
    """Create Alembic configuration with runtime database DSN."""

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.postgres_dsn)
    return cfg


def run_migrations() -> None:
    """Run Alembic migrations up to head."""

    command.upgrade(alembic_config(), "head")
