from fastapi import FastAPI

from . import deps
from .api import router

app = FastAPI(title="route_planner")

@app.on_event("startup")
async def on_startup() -> None:
    deps.init_db()

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}

app.include_router(router)
