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

from . import settings as common_settings

Base = declarative_base()

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = common_settings.settings.postgres_dsn
        kwargs: dict[str, object] = {"future": True, "echo": False}
        connect_args: dict[str, object] = {}
        if url.startswith("sqlite") and ":memory:" in url:
            from sqlalchemy.pool import StaticPool

            kwargs["poolclass"] = StaticPool
            connect_args["check_same_thread"] = False
        _engine = create_async_engine(url, connect_args=connect_args, **kwargs)
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
    cfg.set_main_option("sqlalchemy.url", common_settings.settings.postgres_dsn)
    return cfg


def run_migrations() -> None:
    """Run Alembic migrations up to head."""

    command.upgrade(alembic_config(), "head")
