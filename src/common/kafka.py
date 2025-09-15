"""Kafka helpers built around aiokafka."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from opentelemetry import trace


class KafkaProducer:
    """Simple JSON serializing Kafka producer."""

    _tracer = trace.get_tracer(__name__)

    def __init__(self, brokers: str) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=brokers,
            value_serializer=self._serialize,
            key_serializer=self._serialize_key,
        )

    @staticmethod
    def _serialize(value: Any) -> bytes:
        return json.dumps(value).encode("utf-8")

    @staticmethod
    def _serialize_key(value: Any) -> bytes:
        if value is None:
            return b""
        if isinstance(value, bytes):
            return value
        return str(value).encode("utf-8")

    async def start(self) -> None:
        await self._producer.start()

    async def stop(self) -> None:
        await self._producer.stop()

    async def send(self, topic: str, key: Any, value: Any) -> None:
        with self._tracer.start_as_current_span(f"event.produce:{topic}"):
            await self._producer.send_and_wait(topic, value=value, key=key)

    async def __aenter__(self) -> "KafkaProducer":
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()


class KafkaConsumer:
    """JSON deserializing Kafka consumer."""

    def __init__(
        self,
        brokers: str,
        topic: str,
        group_id: str,
        *,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=brokers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            value_deserializer=self._deserialize,
            key_deserializer=self._deserialize,
        )

    @staticmethod
    def _deserialize(data: bytes | None) -> Any:
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return data

    async def start(self) -> None:
        await self._consumer.start()

    async def stop(self) -> None:
        await self._consumer.stop()

    async def __aenter__(self) -> "KafkaConsumer":
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()

    def __aiter__(self) -> AsyncIterator[Any]:
        return self._consume()

    async def _consume(self) -> AsyncIterator[Any]:
        async for msg in self._consumer:
            yield msg
