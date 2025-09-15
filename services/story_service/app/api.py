import asyncio
import json
from typing import Any
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, BackgroundTasks
from opentelemetry import trace
from sqlalchemy.orm import Session

from . import deps, models, qc, schemas

router = APIRouter()



def forbidden_words() -> list[str]:
    """Return forbidden words from settings."""
    settings = deps.get_settings()
    return [w.strip() for w in settings.forbidden_words.split(",") if w.strip()]


def _fake_llm(poi_id: int, lang: str, tags: list[str]) -> str:
    words = [
        "lorem",
        "ipsum",
        "dolor",
        "sit",
        "amet",
    ]
    text = " ".join(words * 60)  # 300 words
    return f"# Story for POI {poi_id}\n\n{text}"


def _store_story(db: Session, poi_id: int, lang: str, text: str, status: str) -> int:
    story = models.Story(poi_id=poi_id, lang=lang, markdown=text, status=status)
    db.add(story)
    db.commit()
    db.refresh(story)
    return story.id


def _generate_single(poi_id: int, lang: str, tags: list[str]) -> int:
    SessionLocal = deps.get_sessionmaker()
    db = SessionLocal()
    try:
        text = _fake_llm(poi_id, lang, tags)
        forbidden = forbidden_words()
        status = "completed" if qc.check_quality(text, forbidden) else "rejected"
        story_id = _store_story(db, poi_id, lang, text, status)
        return story_id
    finally:
        db.close()


async def _send_completed(route_id: str, stories: list[dict[str, Any]]) -> None:
    settings = deps.get_settings()
    if not settings.kafka_brokers:
        return
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
    await producer.start()
    try:
        payload = {"route_id": route_id, "stories": stories}
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("event.produce:story.generate.completed"):
            await producer.send_and_wait(
                "story.generate.completed",
                json.dumps(payload).encode(),
                key=route_id.encode(),
            )
    finally:
        await producer.stop()


def _process_batch(route_id: str, lang: str) -> None:
    poi_ids = [1, 2]
    stories: list[dict[str, Any]] = []
    for pid in poi_ids:
        story_id = _generate_single(pid, lang, [])
        stories.append({"poi_id": pid, "story_id": story_id})
    asyncio.run(_send_completed(route_id, stories))


@router.post(
    "/story/generate", response_model=schemas.JobResponse, status_code=202
)
def generate_story(
    data: schemas.GenerateRequest, background_tasks: BackgroundTasks
) -> schemas.JobResponse:
    job_id = str(uuid4())
    background_tasks.add_task(_generate_single, data.poi_id, data.lang, data.tags)
    return schemas.JobResponse(job_id=job_id)


@router.post(
    "/story/generate_batch", response_model=schemas.JobResponse, status_code=202
)
def generate_batch(
    data: schemas.GenerateBatchRequest, background_tasks: BackgroundTasks
) -> schemas.JobResponse:
    job_id = str(uuid4())
    background_tasks.add_task(_process_batch, data.route_id, data.lang)
    return schemas.JobResponse(job_id=job_id)
