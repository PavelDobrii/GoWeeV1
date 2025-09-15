import logging
from functools import lru_cache
from typing import Generator

from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.common.settings import SettingsMeta

logger = logging.getLogger(__name__)


class Settings(BaseSettings, metaclass=SettingsMeta):
    database_url: str = "sqlite:///./story_service.db"
    kafka_brokers: str | None = None
    forbidden_words: str = "forbidden,bad"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 1200
    openai_response_language: str = "ru"


@lru_cache
def get_settings() -> Settings:
    return Settings()


_engine = None
_SessionLocal: sessionmaker | None = None


def get_sessionmaker() -> sessionmaker:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        settings = get_settings()
        connect_args: dict[str, object] = {}
        kwargs: dict[str, object] = {"future": True}
        if settings.database_url.endswith(":memory:"):
            kwargs["poolclass"] = StaticPool
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            settings.database_url, connect_args=connect_args, **kwargs
        )
        _SessionLocal = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    session_local = get_sessionmaker()
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models

    _ = get_sessionmaker()
    assert _engine is not None
    models.Base.metadata.create_all(bind=_engine)


@lru_cache
def get_story_generator():
    """Вернуть подходящий генератор историй."""

    from .llm import ChatGPTStoryGenerator, DummyStoryGenerator, StoryGenerationError

    settings = get_settings()
    if settings.openai_api_key:
        try:
            return ChatGPTStoryGenerator(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                max_tokens=settings.openai_max_tokens,
                base_url=settings.openai_base_url,
                response_language=settings.openai_response_language,
            )
        except StoryGenerationError as exc:
            logger.warning("ChatGPT недоступен: %s", exc)
    return DummyStoryGenerator()
