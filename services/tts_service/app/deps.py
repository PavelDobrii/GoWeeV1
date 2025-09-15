from functools import lru_cache
from pathlib import Path
from typing import Generator

from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from src.common.settings import SettingsMeta


class Settings(BaseSettings, metaclass=SettingsMeta):
    database_url: str = "sqlite:///./tts_service.db"
    kafka_brokers: str | None = None
    audio_dir: str = "data/audio"


@lru_cache
def get_settings() -> Settings:
    return Settings()


_engine = None
_SessionLocal: sessionmaker | None = None


def get_sessionmaker() -> sessionmaker:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models

    _ = get_sessionmaker()
    assert _engine is not None
    models.Base.metadata.create_all(bind=_engine)


def ensure_audio_dir() -> Path:
    settings = get_settings()
    path = Path(settings.audio_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
