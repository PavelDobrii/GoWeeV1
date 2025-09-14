from pydantic import BaseModel


class PrefetchItem(BaseModel):
    audio_id: int
    url: str
    ttl_sec: int


class PrefetchResponse(BaseModel):
    items: list[PrefetchItem]
