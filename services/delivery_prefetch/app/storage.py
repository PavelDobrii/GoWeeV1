"""In-memory storage for prefetched audio items."""

from typing import Dict, List

_store: Dict[str, List[int]] = {}


def add_audio(route_id: str, audio_id: int) -> None:
    items = _store.setdefault(route_id, [])
    items.append(audio_id)


def get_audios(route_id: str, limit: int) -> List[int]:
    return _store.get(route_id, [])[:limit]


def clear() -> None:
    _store.clear()
