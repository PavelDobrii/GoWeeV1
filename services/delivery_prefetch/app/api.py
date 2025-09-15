import hashlib

from fastapi import APIRouter, Query

from . import deps, schemas, storage

router = APIRouter()


def _sign(audio_id: int, ttl: int, secret: str) -> str:
    data = f"{audio_id}:{ttl}:{secret}".encode()
    return hashlib.sha256(data).hexdigest()[:8]


@router.get("/delivery/prefetch", response_model=schemas.PrefetchResponse)
async def get_prefetch(
    route_id: str, next: int = Query(1, ge=1)
) -> schemas.PrefetchResponse:
    settings = deps.get_settings()
    ttl = settings.link_ttl_sec
    secret = settings.secret
    audios = storage.get_audios(route_id, next)
    items = []
    for audio_id in audios:
        sig = _sign(audio_id, ttl, secret)
        url = f"http://cdn.local/a/{audio_id}?sig={sig}&ttl={ttl}"
        items.append(schemas.PrefetchItem(audio_id=audio_id, url=url, ttl_sec=ttl))
    return schemas.PrefetchResponse(items=items)
