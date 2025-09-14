"""OpenTelemetry helpers."""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .settings import settings


def setup_otel(app: FastAPI, service_name: str = "app") -> None:
    """Configure OpenTelemetry tracing and metrics for a FastAPI app."""

    resource = Resource.create({"service.name": service_name})

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_exporter = OTLPMetricExporter(
        endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
    )
    reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    FastAPIInstrumentor().instrument_app(app)
