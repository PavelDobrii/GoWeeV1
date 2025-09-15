from __future__ import annotations

import time
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Number of HTTP requests",
    ["service", "method", "path", "status"],
)

HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "method", "path"],
)

KAFKA_CONSUMER_LAG = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag in messages",
    ["service", "topic"],
)

JOB_DURATION = Histogram(
    "job_duration_seconds",
    "Duration of background jobs in seconds",
    ["service", "job"],
)


def setup_metrics(app: FastAPI, service_name: str) -> None:
    """Attach /metrics endpoint and HTTP metrics middleware."""

    class MetricsMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            start = time.perf_counter()
            response = await call_next(request)
            duration = time.perf_counter() - start
            path = request.url.path
            HTTP_REQUESTS.labels(
                service_name, request.method, path, response.status_code
            ).inc()
            HTTP_LATENCY.labels(service_name, request.method, path).observe(duration)
            return response

    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics")
    async def metrics() -> Response:  # pragma: no cover - simple exposition
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
