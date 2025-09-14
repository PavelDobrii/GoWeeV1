"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Base settings for all services."""

    kafka_brokers: str = Field(..., alias="KAFKA_BROKERS")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    postgres_dsn: str = Field(..., alias="POSTGRES_DSN")

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": False,
    }


settings = Settings()
"""Singleton instance of :class:`Settings`."""
