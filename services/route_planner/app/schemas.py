from __future__ import annotations

from pydantic import BaseModel, Field


class PreviewRequest(BaseModel):
    poi_ids: list[int]
    mode: str
    duration_target_min: int


class RouteOption(BaseModel):
    option_id: str
    eta_min: float
    distance_m: float
    order: list[int]


class PreviewResponse(BaseModel):
    options: list[RouteOption]


class ConfirmRequest(BaseModel):
    option_id: str = Field(alias="option_id")


class ConfirmResponse(BaseModel):
    route_id: int
