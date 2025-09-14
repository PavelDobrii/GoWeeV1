"""Workflow orchestration logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from src.common.db import get_session
from src.common.kafka import KafkaProducer

from . import models


class WorkflowManager:
    """Handle workflow state transitions and Kafka messaging."""

    def __init__(self, producer: KafkaProducer) -> None:
        self.producer = producer

    async def handle_route_confirmed(self, event: dict[str, Any]) -> None:
        route_id = str(event["route_id"])
        async with get_session() as session:
            workflow = models.Workflow(route_id=route_id, status="story")
            session.merge(workflow)
            step = models.WorkflowStep(
                route_id=route_id, step="story", status="pending", retries=0
            )
            session.merge(step)
            await session.commit()
        await self.producer.send(
            "story.generate",
            key=route_id,
            value={"route_id": route_id, "lang": "ru"},
        )

    async def handle_story_generate_completed(self, event: dict[str, Any]) -> None:
        route_id = str(event["route_id"])
        stories = event.get("stories", [])
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
                session.merge(
                    models.WorkflowStep(
                        route_id=route_id,
                        step=f"tts:{story_id}",
                        status="pending",
                        retries=0,
                    )
                )
            await session.commit()
        for story in stories:
            story_id = str(story["story_id"])
            await self.producer.send(
                "tts",
                key=story_id,
                value={"route_id": route_id, "story_id": story_id},
            )

    async def handle_tts_completed(self, event: dict[str, Any]) -> None:
        route_id = str(event["route_id"])
        story_id = str(event["story_id"])
        async with get_session() as session:
            stmt = select(models.WorkflowStep).where(
                models.WorkflowStep.route_id == route_id,
                models.WorkflowStep.step == f"tts:{story_id}",
            )
            step = await session.scalar(stmt)
            if step:
                step.status = "completed"
            await session.commit()
            remaining_stmt = (
                select(func.count())
                .select_from(models.WorkflowStep)
                .where(
                    models.WorkflowStep.route_id == route_id,
                    models.WorkflowStep.step.like("tts:%"),
                    models.WorkflowStep.status != "completed",
                )
            )
            remaining = await session.scalar(remaining_stmt)
        if not remaining:
            await self.producer.send(
                "delivery.prefetch",
                key=route_id,
                value={"route_id": route_id, "next_audio": []},
            )
