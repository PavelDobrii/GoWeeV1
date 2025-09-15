import asyncio
import json
import logging
from pathlib import Path
from typing import Set

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from opentelemetry import trace

from src.common.metrics import JOB_DURATION

from . import deps, models
from .tts import TextToSpeechError, get_tts_client

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
    story_id = int(payload["story_id"])
    route_id_raw = payload.get("route_id")
    route_id = str(route_id_raw) if route_id_raw is not None else ""
    voice = payload.get("voice")
    fmt = payload.get("format")
    text = payload.get("text", "")
    lang = payload.get("lang")

    deps.ensure_audio_dir()
    SessionLocal = deps.get_sessionmaker()
    db = SessionLocal()
    settings = deps.get_settings()
    tts_client = get_tts_client()
    status = "completed"
    if tts_client is None:
        logger.warning("Клиент Google TTS не инициализирован, используется заглушка")
        audio_bytes = b""
        duration_sec = 0
        status = "failed"
        extension = (fmt or settings.google_tts_audio_encoding).lower()
    else:
        try:
            audio_bytes, extension, duration_sec = tts_client.synthesize(
                text=text,
                voice=voice,
                audio_format=fmt,
                language=lang,
            )
        except TextToSpeechError:
            logger.exception("Не удалось синтезировать речь для истории %s", story_id)
            audio_bytes = b""
            duration_sec = 0
            status = "failed"
            extension = (fmt or settings.google_tts_audio_encoding).lower()
    try:
        audio = models.AudioFile(
            story_id=story_id,
            voice=voice or settings.google_tts_voice,
            format=extension,
            path="",
            duration_sec=duration_sec,
        )
        db.add(audio)
        db.commit()
        db.refresh(audio)
        audio_path = Path(settings.audio_dir) / f"{audio.id}.{extension}"
        audio.path = str(audio_path)
        db.commit()
    finally:
        db.close()

    audio_path = Path(settings.audio_dir) / f"{audio.id}.{extension}"
    if audio_bytes:
        audio_path.write_bytes(audio_bytes)
    else:
        audio_path.touch()

    if settings.kafka_brokers:
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
        await producer.start()
        try:
            out = {
                "route_id": route_id,
                "story_id": story_id,
                "audio_id": audio.id,
                "duration_sec": duration_sec,
                "status": status,
                "format": extension,
            }
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("event.produce:tts.completed"):
                await producer.send_and_wait(
                    "tts.completed",
                    json.dumps(out).encode(),
                    key=str(story_id).encode(),
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
