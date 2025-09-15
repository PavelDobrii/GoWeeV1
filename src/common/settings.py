"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic._internal._model_construction import ModelMetaclass


class SettingsMeta(ModelMetaclass):
    """Metaclass to allow overriding fields without type annotations."""

    def __new__(mcls, name, bases, namespace, **kwargs):  # type: ignore[override]
        annotations = dict(namespace.get("__annotations__", {}))
        for base in bases:
            for field, ann in getattr(base, "__annotations__", {}).items():
                if field in namespace and field not in annotations:
                    annotations[field] = ann
        namespace["__annotations__"] = annotations
        return super().__new__(mcls, name, bases, namespace, **kwargs)


class Settings(BaseSettings, metaclass=SettingsMeta):
    """Base settings for all services."""

    # Provide sensible defaults so tests can import modules without having
    # the environment configured. Real deployments should override these
    # via environment variables.
    kafka_brokers: str = Field("kafka:9092", alias="KAFKA_BROKERS")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    postgres_dsn: str = Field("sqlite://", alias="POSTGRES_DSN")

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": False,
    }


settings = Settings()
"""Singleton instance of :class:`Settings`."""
