import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from src.common.metrics import JOB_DURATION

from . import deps, storage

logger = logging.getLogger(__name__)


async def _handle_message(message) -> None:
    start = asyncio.get_event_loop().time()
    payload = json.loads(message.value.decode())
    route_id = str(payload["route_id"])
    status = payload.get("status", "completed")
    if status != "completed":
        logger.warning(
            "Аудио по маршруту %s пропущено из-за статуса %s",
            route_id,
            status,
        )
        return
    audio_id = int(payload["audio_id"])
    storage.add_audio(route_id, audio_id)
    duration = asyncio.get_event_loop().time() - start
    JOB_DURATION.labels("delivery_prefetch", "handle_message").observe(duration)


async def _consume(settings: deps.Settings) -> None:
    assert settings.kafka_brokers is not None
    consumer = AIOKafkaConsumer(
        "tts.completed",
        bootstrap_servers=settings.kafka_brokers.split(","),
        group_id="delivery-prefetch",
        enable_auto_commit=True,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await _handle_message(msg)
    finally:
        await consumer.stop()


async def start_kafka_consumer(settings: deps.Settings) -> None:
    if not settings.kafka_brokers:
        logger.info("Kafka configuration missing. Consumer loop not started")
        return

    asyncio.create_task(_consume(settings))
