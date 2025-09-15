from fastapi import FastAPI

from src.common.metrics import KAFKA_CONSUMER_LAG, JOB_DURATION, setup_metrics

from .api import router


app = FastAPI(title="paywall_billing")
setup_metrics(app, "paywall_billing")


@app.on_event("startup")
async def on_startup() -> None:
    KAFKA_CONSUMER_LAG.labels("paywall_billing", "none").set(0)
    JOB_DURATION.labels("paywall_billing", "startup").observe(0)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
