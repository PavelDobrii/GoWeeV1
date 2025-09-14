from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    kafka_brokers: str | None = None
    link_ttl_sec: int = 3600
    secret: str = "secret"


@lru_cache
def get_settings() -> Settings:
    return Settings()
