import logging

from fastapi import FastAPI, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from .api import router as api_router
from .deps import get_settings
from .kafka_loop import start_kafka_consumer

logger = logging.getLogger(__name__)


def setup_otel(app: FastAPI) -> None:
    """Configure basic OpenTelemetry for the service."""
    resource = Resource(attributes={SERVICE_NAME: "template_service"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


app = FastAPI(title="template_service")


@app.on_event("startup")
async def startup_event() -> None:
    setup_otel(app)
    settings = get_settings()
    await start_kafka_consumer(settings)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


app.include_router(api_router)
