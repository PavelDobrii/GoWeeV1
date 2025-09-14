from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_brokers: str | None = None
    kafka_topic_in: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return application settings."""
    return Settings()
