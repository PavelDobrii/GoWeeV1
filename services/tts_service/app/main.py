import logging
from fastapi import FastAPI

from src.common.metrics import KAFKA_CONSUMER_LAG, JOB_DURATION, setup_metrics
from src.common.telemetry import setup_otel

from .api import router as api_router
from .deps import ensure_audio_dir, get_settings, init_db
from .kafka_loop import start_kafka_consumer

logger = logging.getLogger(__name__)


app = FastAPI(title="tts_service")
setup_metrics(app, "tts_service")
setup_otel(app, "tts_service")


@app.on_event("startup")
async def startup_event() -> None:
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
