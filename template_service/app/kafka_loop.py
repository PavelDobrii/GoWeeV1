import asyncio
import logging
from typing import Set

from aiokafka import AIOKafkaConsumer

from .deps import Settings

logger = logging.getLogger(__name__)

_processed: Set[bytes] = set()


async def _handle_message(message) -> None:
    key = message.key or str(message.offset).encode()
    if key in _processed:
        logger.info("Skipping processed message: %s", key)
        return
    _processed.add(key)
    logger.info("Consumed message: %s", message.value)


async def _consume(settings: Settings) -> None:
    assert settings.kafka_brokers is not None
    assert settings.kafka_topic_in is not None
    consumer = AIOKafkaConsumer(
        settings.kafka_topic_in,
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


async def start_kafka_consumer(settings: Settings) -> None:
    if not settings.kafka_brokers or not settings.kafka_topic_in:
        logger.info("Kafka configuration missing. Consumer loop not started")
        return

    async def runner() -> None:
        try:
            await _consume(settings)
        except Exception:  # noqa: BLE001
            logger.exception("Kafka consumer loop terminated")

    asyncio.create_task(runner())
