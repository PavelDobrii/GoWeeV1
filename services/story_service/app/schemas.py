from __future__ import annotations

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    poi_id: int
    lang: str
    tags: list[str] = []


class JobResponse(BaseModel):
    job_id: str


class GenerateBatchRequest(BaseModel):
    route_id: str
    lang: str
