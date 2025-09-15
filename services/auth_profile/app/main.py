from fastapi import FastAPI

from src.common.metrics import KAFKA_CONSUMER_LAG, JOB_DURATION, setup_metrics

from .api import router


app = FastAPI(title="auth_profile")
setup_metrics(app, "auth_profile")


@app.on_event("startup")
async def on_startup() -> None:
    KAFKA_CONSUMER_LAG.labels("auth_profile", "none").set(0)
    JOB_DURATION.labels("auth_profile", "startup").observe(0)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
