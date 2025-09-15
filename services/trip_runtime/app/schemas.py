from typing import List, Optional

from pydantic import BaseModel


class TripStartRequest(BaseModel):
    route_id: int


class TripStartResponse(BaseModel):
    session_id: str


class Point(BaseModel):
    lat: float
    lon: float


class TripPingRequest(BaseModel):
    session_id: str
    points: List[Point]


class TripPingResponse(BaseModel):
    upcoming_poi: Optional[int]
    distance_m: Optional[float]


class TripFinishRequest(BaseModel):
    session_id: str
    rating: Optional[int] = None
    feedback: Optional[str] = None
