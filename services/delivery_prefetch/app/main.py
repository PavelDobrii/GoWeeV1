from fastapi import FastAPI

from . import deps
from .api import router
from .kafka_loop import start_kafka_consumer

app = FastAPI(title="delivery_prefetch")


@app.on_event("startup")
async def on_startup() -> None:
    settings = deps.get_settings()
    await start_kafka_consumer(settings)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
