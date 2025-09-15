from fastapi import FastAPI

from src.common.metrics import JOB_DURATION, KAFKA_CONSUMER_LAG, setup_metrics

from .api import router


app = FastAPI(title="trip_runtime")
setup_metrics(app, "trip_runtime")


@app.on_event("startup")
async def on_startup() -> None:
    KAFKA_CONSUMER_LAG.labels("trip_runtime", "none").set(0)
    JOB_DURATION.labels("trip_runtime", "startup").observe(0)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
