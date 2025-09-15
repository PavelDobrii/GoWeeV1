"""Structured logging configuration."""

from __future__ import annotations

import logging
from typing import Any

import structlog
from opentelemetry.trace import get_current_span


def _add_trace_id(
    _logger: structlog.typing.WrappedLogger,
    _name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject ``trace_id`` from the current span into log records."""

    span = get_current_span()
    ctx = span.get_span_context()
    if ctx.trace_id:
        event_dict["trace_id"] = f"{ctx.trace_id:032x}"
    return event_dict


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structlog to emit JSON logs."""

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            timestamper,
            structlog.processors.add_log_level,
            _add_trace_id,
            structlog.processors.DictRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", level=level)


def get_logger(*args: Any, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger."""

    return structlog.get_logger(*args, **kwargs)
