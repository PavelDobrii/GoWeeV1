import json
import math
from typing import Dict, Tuple
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, status
from opentelemetry import trace
from sqlalchemy.orm import Session

from . import deps, models, schemas

router = APIRouter()

# Sample POI coordinates (lat, lon)
POIS: Dict[int, tuple[float, float]] = {
    1: (55.751244, 37.618423),  # Moscow
    2: (59.9375, 30.308611),  # Saint Petersburg
    3: (56.838926, 60.605703),  # Yekaterinburg
    4: (55.030199, 82.92043),  # Novosibirsk
}

SPEED_M_PER_MIN = {
    "car": 1000.0,  # ~60 km/h
    "bike": 250.0,  # ~15 km/h
    "walk": 83.0,  # ~5 km/h
}

_options: Dict[str, Tuple[schemas.RouteOption, str]] = {}


def _haversine(p1: tuple[float, float], p2: tuple[float, float]) -> float:
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


def _plan_route(poi_ids: list[int]) -> list[int]:
    if not poi_ids:
        return []
    unvisited = poi_ids.copy()
    current = unvisited.pop(0)
    order = [current]
    while unvisited:
        next_poi = min(unvisited, key=lambda pid: _haversine(POIS[current], POIS[pid]))
        unvisited.remove(next_poi)
        order.append(next_poi)
        current = next_poi
    return order


def _route_distance(order: list[int]) -> float:
    if len(order) < 2:
        return 0.0
    return sum(_haversine(POIS[a], POIS[b]) for a, b in zip(order, order[1:]))


@router.post("/routes/preview", response_model=schemas.PreviewResponse)
async def preview_route(data: schemas.PreviewRequest) -> schemas.PreviewResponse:
    try:
        _ = [POIS[pid] for pid in data.poi_ids]
    except KeyError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="POI not found"
        ) from exc

    order = _plan_route(data.poi_ids)
    distance = _route_distance(order)
    speed = SPEED_M_PER_MIN.get(data.mode, 1000.0)
    eta = distance / speed if speed else 0.0
    option_id = str(uuid4())
    option = schemas.RouteOption(
        option_id=option_id,
        eta_min=eta,
        distance_m=distance,
        order=order,
    )
    _options[option_id] = (option, data.mode)
    return schemas.PreviewResponse(options=[option])


async def _send_route_confirmed(
    route: models.Route, snapshot: models.RouteSnapshot
) -> None:
    settings = deps.get_settings()
    if not settings.kafka_brokers:
        return
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
    await producer.start()
    try:
        payload = {
            "route_id": route.id,
            "mode": route.mode,
            "eta_min": route.eta_min,
            "distance_m": route.distance_m,
            "order": snapshot.order,
        }
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("event.produce:route.confirmed"):
            await producer.send_and_wait(
                "route.confirmed", json.dumps(payload).encode(), key=str(route.id).encode()
            )
    finally:
        await producer.stop()


@router.post("/routes/confirm", response_model=schemas.ConfirmResponse)
async def confirm_route(
    data: schemas.ConfirmRequest,
    db: Session = Depends(deps.get_db),
) -> schemas.ConfirmResponse:
    stored = _options.pop(data.option_id, None)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Option not found"
        )
    option, mode = stored

    route = models.Route(
        mode=mode,
        distance_m=int(option.distance_m),
        eta_min=int(option.eta_min),
    )
    db.add(route)
    db.flush()
    snapshot = models.RouteSnapshot(
        route_id=route.id,
        order=option.order,
        distance_m=int(option.distance_m),
        eta_min=int(option.eta_min),
    )
    db.add(snapshot)
    db.commit()
    await _send_route_confirmed(route, snapshot)
    return schemas.ConfirmResponse(route_id=route.id)
