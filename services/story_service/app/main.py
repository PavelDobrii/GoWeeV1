from fastapi import FastAPI

from src.common.metrics import KAFKA_CONSUMER_LAG, JOB_DURATION, setup_metrics

from . import deps
from .api import router


app = FastAPI(title="story_service")
setup_metrics(app, "story_service")


@app.on_event("startup")
def on_startup() -> None:
    deps.init_db()
    KAFKA_CONSUMER_LAG.labels("story_service", "none").set(0)
    JOB_DURATION.labels("story_service", "startup").observe(0)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
