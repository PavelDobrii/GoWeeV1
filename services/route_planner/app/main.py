from fastapi import FastAPI

from src.common.metrics import JOB_DURATION, KAFKA_CONSUMER_LAG, setup_metrics
from src.common.telemetry import setup_otel

from . import deps
from .api import router

app = FastAPI(title="route_planner")
setup_metrics(app, "route_planner")
setup_otel(app, "route_planner")


@app.on_event("startup")
async def on_startup() -> None:
    deps.init_db()
    KAFKA_CONSUMER_LAG.labels("route_planner", "none").set(0)
    JOB_DURATION.labels("route_planner", "startup").observe(0)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
