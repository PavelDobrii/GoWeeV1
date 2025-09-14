import json
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter

from . import deps, schemas

router = APIRouter()


@router.post("/tts/request", response_model=schemas.JobResponse, status_code=202)
async def request_tts(data: schemas.TTSRequest) -> schemas.JobResponse:
    job_id = str(uuid4())
    settings = deps.get_settings()
    if settings.kafka_brokers:
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
        await producer.start()
        try:
            await producer.send_and_wait(
                "tts.requested",
                json.dumps(data.model_dump()).encode(),
                key=str(data.story_id).encode(),
            )
        finally:
            await producer.stop()
    return schemas.JobResponse(job_id=job_id)
