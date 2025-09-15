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

POLL_INTERVAL_SECONDS = 1.0
#: Русский комментарий: интервал ожидания между попытками опроса очереди.


class Outbox(Base):
    """Таблица для сообщений, ожидающих публикации в Kafka."""

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


def _serialize_payload(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


async def enqueue(topic: str, key: str | None, payload: Any) -> None:
    """Добавить сообщение в outbox."""

    # Русский комментарий: сохраняем событие в транзакции базы данных.
    async with get_session() as session:
        session.add(
            Outbox(topic=topic, key=key, payload_json=_serialize_payload(payload))
        )
        await session.commit()


async def drain_outbox(
    producer: KafkaProducer,
    batch_size: int = 100,
    poll_interval: float = POLL_INTERVAL_SECONDS,
) -> None:
    """Фоновая задача, публикующая сообщения из outbox в Kafka."""

    stmt = select(Outbox).where(Outbox.sent_at.is_(None)).order_by(Outbox.id)

    while True:
        async with get_session() as session:
            rows = list(await session.scalars(stmt.limit(batch_size)))
            if not rows:
                # Русский комментарий: делаем паузу, чтобы не нагружать CPU
                # пустыми циклами.
                await asyncio.sleep(poll_interval)
                continue
            for row in rows:
                try:
                    # Русский комментарий: отправляем уже сериализованный JSON
                    # без повторного парсинга.
                    await producer.send(row.topic, row.key, row.payload_json)
                    row.sent_at = datetime.utcnow()
                except Exception:  # pragma: no cover - логгирование в реальном сервисе
                    row.attempts += 1
            await session.commit()
            if len(rows) < batch_size:
                # Русский комментарий: если сообщений меньше лимита, можно
                # сделать паузу.
                await asyncio.sleep(poll_interval)
