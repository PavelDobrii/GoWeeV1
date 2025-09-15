import logging
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.common.metrics import KAFKA_CONSUMER_LAG, JOB_DURATION, setup_metrics

from .api import router as api_router
from .deps import ensure_audio_dir, get_settings, init_db
from .kafka_loop import start_kafka_consumer

logger = logging.getLogger(__name__)


def setup_otel(app: FastAPI) -> None:
    """Configure basic OpenTelemetry for the service."""
    resource = Resource(attributes={SERVICE_NAME: "tts_service"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


app = FastAPI(title="tts_service")
setup_metrics(app, "tts_service")


@app.on_event("startup")
async def startup_event() -> None:
    setup_otel(app)
    settings = get_settings()
    init_db()
    ensure_audio_dir()
    await start_kafka_consumer(settings)
    KAFKA_CONSUMER_LAG.labels("tts_service", "tts.requested").set(0)
    JOB_DURATION.labels("tts_service", "startup").observe(0)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(api_router)
