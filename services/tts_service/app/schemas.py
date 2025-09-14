from pydantic import BaseModel


class TTSRequest(BaseModel):
    story_id: int
    voice: str
    format: str


class JobResponse(BaseModel):
    job_id: str
