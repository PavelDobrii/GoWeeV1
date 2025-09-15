from pydantic import BaseModel


class TTSRequest(BaseModel):
    story_id: int
    route_id: str | None = None
    text: str | None = None
    voice: str | None = None
    format: str | None = None
    lang: str | None = None


class JobResponse(BaseModel):
    job_id: str
