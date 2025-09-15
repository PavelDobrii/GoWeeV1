from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_brokers: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
