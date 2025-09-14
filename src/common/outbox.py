"""Outbox pattern implementation."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, get_session
from .kafka import KafkaProducer


class Outbox(Base):
    """Table storing messages to be published to Kafka."""

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


def _serialize_payload(payload: Any) -> str:
    return json.dumps(payload)


async def enqueue(topic: str, key: str | None, payload: Any) -> None:
    """Add a message to the outbox."""

    async with get_session() as session:
        session.add(
            Outbox(topic=topic, key=key, payload_json=_serialize_payload(payload))
        )
        await session.commit()


async def drain_outbox(producer: KafkaProducer, batch_size: int = 100) -> None:
    """Background task that sends pending outbox messages to Kafka."""

    while True:
        async with get_session() as session:
            result = await session.execute(
                select(Outbox).where(Outbox.sent_at.is_(None)).order_by(Outbox.id).limit(batch_size)
            )
            rows = result.scalars().all()
            if not rows:
                await asyncio.sleep(1)
                continue
            for row in rows:
                try:
                    await producer.send(
                        row.topic, row.key, json.loads(row.payload_json)
                    )
                    row.sent_at = datetime.utcnow()
                except Exception:  # pragma: no cover - log in real application
                    row.attempts += 1
            await session.commit()
