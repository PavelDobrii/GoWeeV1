import json
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, HTTPException, status

from . import deps, schemas

router = APIRouter()

# Sample POI coordinates (lat, lon)
POIS: Dict[int, Tuple[float, float]] = {
    1: (55.751244, 37.618423),  # Moscow
    2: (59.9375, 30.308611),  # Saint Petersburg
    3: (56.838926, 60.605703),  # Yekaterinburg
    4: (55.030199, 82.92043),  # Novosibirsk
}

# Sample routes mapping route_id to ordered list of POI ids
ROUTES: Dict[int, List[int]] = {
    1: [1, 2, 3, 4],
}


@dataclass
class Session:
    route_id: int
    next_index: int = 0


_sessions: Dict[str, Session] = {}


def _haversine(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return 6371000 * c


async def _send_poi_approaching(session_id: str, poi_id: int, distance: float) -> None:
    settings = deps.get_settings()
    if not settings.kafka_brokers:
        return
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
    await producer.start()
    try:
        payload = {
            "session_id": session_id,
            "poi_id": poi_id,
            "distance_m": distance,
        }
        await producer.send_and_wait(
            "trip.poi.approaching",
            json.dumps(payload).encode(),
            key=session_id.encode(),
        )
    finally:
        await producer.stop()


@router.post("/trip/start", response_model=schemas.TripStartResponse)
async def start_trip(data: schemas.TripStartRequest) -> schemas.TripStartResponse:
    if data.route_id not in ROUTES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )
    session_id = str(uuid4())
    _sessions[session_id] = Session(route_id=data.route_id)
    return schemas.TripStartResponse(session_id=session_id)


@router.post("/trip/ping", response_model=schemas.TripPingResponse)
async def ping_trip(data: schemas.TripPingRequest) -> schemas.TripPingResponse:
    session = _sessions.get(data.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    route = ROUTES.get(session.route_id, [])
    if session.next_index >= len(route):
        return schemas.TripPingResponse(upcoming_poi=None, distance_m=None)
    poi_id = route[session.next_index]
    poi_coord = POIS[poi_id]
    last_point = (data.points[-1].lat, data.points[-1].lon)
    distance = _haversine(last_point, poi_coord)
    if distance < 60:
        await _send_poi_approaching(data.session_id, poi_id, distance)
        session.next_index += 1
    return schemas.TripPingResponse(upcoming_poi=poi_id, distance_m=distance)


@router.post("/trip/finish")
async def finish_trip(data: schemas.TripFinishRequest) -> dict[str, str]:
    _sessions.pop(data.session_id, None)
    return {"status": "ok"}
