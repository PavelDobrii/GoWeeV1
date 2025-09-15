import asyncio
import json
import logging
from typing import Set

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.common.metrics import JOB_DURATION

from . import deps, models

logger = logging.getLogger(__name__)

_processed: Set[bytes] = set()


async def _handle_message(message) -> None:
    start = asyncio.get_event_loop().time()
    key = message.key or str(message.offset).encode()
    if key in _processed:
        logger.info("Skipping processed message: %s", key)
        return
    _processed.add(key)
    payload = json.loads(message.value.decode())
    story_id = payload["story_id"]
    voice = payload["voice"]
    fmt = payload["format"]

    deps.ensure_audio_dir()
    SessionLocal = deps.get_sessionmaker()
    db = SessionLocal()
    try:
        audio = models.AudioFile(story_id=story_id, voice=voice, format=fmt, path="", duration_sec=0)
        db.add(audio)
        db.commit()
        db.refresh(audio)
        settings = deps.get_settings()
        from pathlib import Path

        audio_path = Path(settings.audio_dir) / f"{audio.id}.{fmt}"
        audio.path = str(audio_path)
        db.commit()
        audio_path.touch()
    finally:
        db.close()

    settings = deps.get_settings()
    if settings.kafka_brokers:
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
        await producer.start()
        try:
            out = {"story_id": story_id, "audio_id": audio.id, "duration_sec": 0}
            await producer.send_and_wait(
                "tts.completed", json.dumps(out).encode(), key=str(story_id).encode()
            )
        finally:
            await producer.stop()
    duration = asyncio.get_event_loop().time() - start
    JOB_DURATION.labels("tts_service", "handle_message").observe(duration)


async def _consume(settings: deps.Settings) -> None:
    assert settings.kafka_brokers is not None
    consumer = AIOKafkaConsumer(
        "tts.requested",
        bootstrap_servers=settings.kafka_brokers.split(","),
        enable_auto_commit=False,
    )
    logger.info("Starting Kafka consumer loop")
    await consumer.start()
    logger.info("Kafka consumer loop started")
    try:
        async for msg in consumer:
            await _handle_message(msg)
            await consumer.commit()
    finally:
        await consumer.stop()


async def start_kafka_consumer(settings: deps.Settings) -> None:
    if not settings.kafka_brokers:
        logger.info("Kafka configuration missing. Consumer loop not started")
        return

    async def runner() -> None:
        try:
            await _consume(settings)
        except Exception:  # noqa: BLE001
            logger.exception("Kafka consumer loop terminated")

    asyncio.create_task(runner())
