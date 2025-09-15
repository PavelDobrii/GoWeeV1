"""Логика оркестрации рабочего процесса."""

from __future__ import annotations

import inspect
import logging
import time
from typing import Any

from prometheus_client import Histogram
from sqlalchemy import func, select

from src.common.db import get_session
from src.common.kafka import KafkaProducer
from src.common.metrics import JOB_DURATION

from . import models

logger = logging.getLogger(__name__)

ROUTE_TO_AUDIO_SECONDS = Histogram(
    "route_to_first_audio_seconds",
    "Seconds from route.confirmed to first two audio ready",
    ["service"],
)


class WorkflowManager:
    """Управляет переходами состояний и отправкой сообщений в Kafka."""

    def __init__(self, producer: KafkaProducer) -> None:
        self.producer = producer
        self._route_start: dict[str, float] = {}
        self._tts_counts: dict[str, int] = {}

    async def handle_route_confirmed(self, event: dict[str, Any]) -> None:
        start = time.monotonic()
        route_id = str(event["route_id"])
        async with get_session() as session:
            workflow = models.Workflow(route_id=route_id, status="story")
            res = session.merge(workflow)
            if inspect.isawaitable(res):
                await res
            step = models.WorkflowStep(
                route_id=route_id, step="story", status="pending", retries=0
            )
            res = session.merge(step)
            if inspect.isawaitable(res):
                await res
            await session.commit()
        await self.producer.send(
            "story.generate",
            key=route_id,
            value={"route_id": route_id, "lang": "ru"},
        )
        JOB_DURATION.labels("orchestrator", "handle_route_confirmed").observe(
            time.monotonic() - start
        )
        self._route_start[route_id] = start
        self._tts_counts[route_id] = 0

    async def handle_story_generate_completed(self, event: dict[str, Any]) -> None:
        start = time.monotonic()
        route_id = str(event["route_id"])
        stories = event.get("stories", [])
        default_lang = event.get("lang", "ru")
        async with get_session() as session:
            stmt = select(models.WorkflowStep).where(
                models.WorkflowStep.route_id == route_id,
                models.WorkflowStep.step == "story",
            )
            step = await session.scalar(stmt)
            if step:
                step.status = "completed"
            for story in stories:
                story_id = str(story["story_id"])
                status = story.get("status", "completed")
                step_status = "pending" if status == "completed" else "skipped"
                res = session.merge(
                    models.WorkflowStep(
                        route_id=route_id,
                        step=f"tts:{story_id}",
                        status=step_status,
                        retries=0,
                    )
                )
                if inspect.isawaitable(res):
                    await res
            await session.commit()
        for story in stories:
            status = story.get("status", "completed")
            if status != "completed":
                logger.info(
                    "История %s по маршруту %s пропущена: статус %s",
                    story.get("story_id"),
                    route_id,
                    status,
                )
                continue
            story_id = str(story["story_id"])
            text = (story.get("markdown") or "").strip()
            payload: dict[str, Any] = {
                "route_id": route_id,
                "story_id": story_id,
                "text": text,
                "lang": story.get("lang", default_lang),
            }
            if not text:
                logger.warning(
                    "Пустой текст истории %s, "
                    "отправляется только совместимое сообщение",
                    story_id,
                )
            if story.get("voice"):
                payload["voice"] = story["voice"]
            if story.get("format"):
                payload["format"] = story["format"]
            if text:
                await self.producer.send(
                    "tts.requested",
                    key=story_id,
                    value=payload,
                )
            await self.producer.send(
                "tts",
                key=story_id,
                value={"route_id": route_id, "story_id": story_id},
            )
        JOB_DURATION.labels(
            "orchestrator", "handle_story_generate_completed"
        ).observe(time.monotonic() - start)

    async def handle_tts_completed(self, event: dict[str, Any]) -> None:
        start = time.monotonic()
        route_id = str(event["route_id"])
        story_id = str(event["story_id"])
        status = event.get("status", "completed")
        async with get_session() as session:
            stmt = select(models.WorkflowStep).where(
                models.WorkflowStep.route_id == route_id,
                models.WorkflowStep.step == f"tts:{story_id}",
            )
            step = await session.scalar(stmt)
            if step:
                step.status = status if status != "completed" else "completed"
            await session.commit()
            remaining_stmt = (
                select(func.count())
                .select_from(models.WorkflowStep)
                .where(
                    models.WorkflowStep.route_id == route_id,
                    models.WorkflowStep.step.like("tts:%"),
                    ~models.WorkflowStep.status.in_(["completed", "skipped", "failed"]),
                )
            )
            remaining = await session.scalar(remaining_stmt)
        if status == "completed":
            count = self._tts_counts.get(route_id, 0) + 1
            self._tts_counts[route_id] = count
            if count == 2:
                start_time = self._route_start.pop(route_id, start)
                ROUTE_TO_AUDIO_SECONDS.labels("orchestrator").observe(
                    time.monotonic() - start_time
                )
                self._tts_counts.pop(route_id, None)
        else:
            logger.warning(
                "Получен статус %s для истории %s по маршруту %s",
                status,
                story_id,
                route_id,
            )
        if not remaining:
            await self.producer.send(
                "delivery.prefetch",
                key=route_id,
                value={"route_id": route_id, "next_audio": []},
            )
        JOB_DURATION.labels("orchestrator", "handle_tts_completed").observe(
            time.monotonic() - start
        )
