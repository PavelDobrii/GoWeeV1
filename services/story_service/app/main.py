from fastapi import FastAPI

from . import deps
from .api import router

app = FastAPI(title="story_service")


@app.on_event("startup")
def on_startup() -> None:
    deps.init_db()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(router)
