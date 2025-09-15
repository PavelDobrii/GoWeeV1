from fastapi import FastAPI

from src.common.metrics import JOB_DURATION, KAFKA_CONSUMER_LAG, setup_metrics
from src.common.telemetry import setup_otel

from . import deps
from .api import router
from .kafka_loop import start_kafka_consumer

app = FastAPI(title="delivery_prefetch")
setup_metrics(app, "delivery_prefetch")
setup_otel(app, "delivery_prefetch")


@app.on_event("startup")
async def on_startup() -> None:
    settings = deps.get_settings()
    await start_kafka_consumer(settings)
    KAFKA_CONSUMER_LAG.labels("delivery_prefetch", "tts.completed").set(0)
    JOB_DURATION.labels("delivery_prefetch", "startup").observe(0)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
