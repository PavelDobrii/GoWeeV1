"""Entrypoint for orchestrator service."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine

from fastapi import FastAPI

from src.common.kafka import KafkaConsumer, KafkaProducer
from src.common.metrics import KAFKA_CONSUMER_LAG, JOB_DURATION, setup_metrics
from src.common.telemetry import setup_otel
from src.common.settings import settings

from . import api, workflow

app = FastAPI()
setup_metrics(app, "orchestrator")
setup_otel(app, "orchestrator")
app.include_router(api.router)

_producer: KafkaProducer | None = None


async def _consume_route_confirmed(manager: workflow.WorkflowManager) -> None:
    consumer = KafkaConsumer(
        settings.kafka_brokers, "route.confirmed", group_id="orchestrator-route"
    )
    async with consumer:
        async for msg in consumer:
            await manager.handle_route_confirmed(msg.value)


def _start_consumer(coro: Coroutine[Any, Any, None]) -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(coro)


async def _consume_story(manager: workflow.WorkflowManager) -> None:
    consumer = KafkaConsumer(
        settings.kafka_brokers, "story.generate", group_id="orchestrator-story"
    )
    async with consumer:
        async for msg in consumer:
            value = msg.value
            if value.get("event") == "story.generate.completed":
                await manager.handle_story_generate_completed(value)


async def _consume_tts(manager: workflow.WorkflowManager) -> None:
    consumer = KafkaConsumer(settings.kafka_brokers, "tts", group_id="orchestrator-tts")
    async with consumer:
        async for msg in consumer:
            value = msg.value
            if value.get("event") == "tts.completed":
                await manager.handle_tts_completed(value)


@app.on_event("startup")
async def startup() -> None:
    global _producer
    _producer = KafkaProducer(settings.kafka_brokers)
    await _producer.start()
    manager = workflow.WorkflowManager(_producer)
    _start_consumer(_consume_route_confirmed(manager))
    _start_consumer(_consume_story(manager))
    _start_consumer(_consume_tts(manager))
    KAFKA_CONSUMER_LAG.labels("orchestrator", "route.confirmed").set(0)
    KAFKA_CONSUMER_LAG.labels("orchestrator", "story.generate").set(0)
    KAFKA_CONSUMER_LAG.labels("orchestrator", "tts").set(0)
    JOB_DURATION.labels("orchestrator", "startup").observe(0)


@app.on_event("shutdown")
async def shutdown() -> None:
    if _producer:
        await _producer.stop()
