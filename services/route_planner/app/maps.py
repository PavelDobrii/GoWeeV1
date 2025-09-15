"""Интеграция с Google Maps Directions API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

try:
    import googlemaps
    from googlemaps.exceptions import ApiError, TransportError
except ImportError:  # pragma: no cover - библиотека ставится опционально
    googlemaps = None  # type: ignore[assignment]
    ApiError = TransportError = Exception  # type: ignore[assignment]

from . import deps

logger = logging.getLogger(__name__)

_MODE_MAPPING = {
    "car": "driving",
    "bike": "bicycling",
    "walk": "walking",
}


class GoogleMapsError(Exception):
    """Ошибка при работе с Google Maps."""


@dataclass
class RouteEstimate:
    """Результат расчёта маршрута в Google Maps."""

    order: list[int]
    distance_m: float
    duration_min: float


class GoogleMapsClient:
    """Обёртка над клиентом googlemaps с нужными настройками."""

    def __init__(self, settings: deps.Settings) -> None:
        if googlemaps is None:
            raise GoogleMapsError("Библиотека googlemaps не установлена")
        if not settings.google_maps_api_key:
            raise GoogleMapsError("Отсутствует API-ключ Google Maps")
        self._client = googlemaps.Client(
            key=settings.google_maps_api_key,
            timeout=settings.google_maps_timeout,
        )
        self._language = settings.google_maps_language
        self._region = settings.google_maps_region

    def estimate_route(
        self,
        poi_ids: Sequence[int],
        coordinates: Sequence[tuple[float, float]],
        mode: str,
    ) -> RouteEstimate:
        """Запросить маршрут и вернуть оценку дистанции и длительности."""

        if len(coordinates) < 2:
            return RouteEstimate(order=list(poi_ids), distance_m=0.0, duration_min=0.0)
        travel_mode = _MODE_MAPPING.get(mode, "driving")
        origin = coordinates[0]
        destination = coordinates[-1]
        waypoints_coords = coordinates[1:-1]
        waypoints = [f"{lat},{lon}" for lat, lon in waypoints_coords]
        optimize = bool(waypoints)
        try:
            response = self._client.directions(
                origin=f"{origin[0]},{origin[1]}",
                destination=f"{destination[0]},{destination[1]}",
                waypoints=waypoints or None,
                optimize_waypoints=optimize,
                mode=travel_mode,
                language=self._language,
                region=self._region,
            )
        except (ApiError, TransportError, ValueError) as exc:
            raise GoogleMapsError("Google Maps вернул ошибку") from exc
        if not response:
            raise GoogleMapsError("Google Maps не вернул маршруты")
        route = response[0]
        legs = route.get("legs", [])
        distance = float(
            sum(leg.get("distance", {}).get("value", 0) for leg in legs)
        )
        duration_sec = float(
            sum(leg.get("duration", {}).get("value", 0) for leg in legs)
        )
        ordered_pois = list(poi_ids)
        if optimize and route.get("waypoint_order"):
            order_indexes = route["waypoint_order"]
            middle_ids = [poi_ids[1:-1][idx] for idx in order_indexes]
            ordered_pois = [poi_ids[0], *middle_ids, poi_ids[-1]]
        return RouteEstimate(
            order=ordered_pois,
            distance_m=distance,
            duration_min=duration_sec / 60 if duration_sec else 0.0,
        )


@lru_cache
def get_maps_client() -> GoogleMapsClient | None:
    """Вернуть закешированный клиент Google Maps либо `None`."""

    settings = deps.get_settings()
    if not settings.google_maps_api_key:
        return None
    try:
        return GoogleMapsClient(settings)
    except GoogleMapsError as exc:
        logger.error("Не удалось инициализировать Google Maps: %s", exc)
        return None
