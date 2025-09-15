from fastapi import FastAPI

from .api import router

app = FastAPI(title="trip_runtime")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
