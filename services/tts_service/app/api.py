import json
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter
from opentelemetry import trace

from . import deps, schemas

router = APIRouter()


@router.post("/tts/request", response_model=schemas.JobResponse, status_code=202)
async def request_tts(data: schemas.TTSRequest) -> schemas.JobResponse:
    job_id = str(uuid4())
    settings = deps.get_settings()
    payload = data.model_dump()
    if not payload.get("voice"):
        payload["voice"] = settings.google_tts_voice
    if not payload.get("format"):
        payload["format"] = settings.google_tts_audio_encoding
    payload = {k: v for k, v in payload.items() if v is not None}
    if settings.kafka_brokers:
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
        await producer.start()
        try:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("event.produce:tts.requested"):
                await producer.send_and_wait(
                    "tts.requested",
                    json.dumps(payload).encode(),
                    key=str(data.story_id).encode(),
                )
        finally:
            await producer.stop()
    return schemas.JobResponse(job_id=job_id)
