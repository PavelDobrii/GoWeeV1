"""Kafka helpers built around aiokafka."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Final

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from opentelemetry import trace


class KafkaProducer:
    """Простой Kafka-продюсер с JSON-сериализацией."""

    __slots__ = ("_producer", "_started")

    _tracer = trace.get_tracer(__name__)
    _empty_bytes: Final[bytes] = b""

    def __init__(self, brokers: str) -> None:
        # Русский комментарий: создаём продюсер один раз и переиспользуем соединение.
        self._producer = AIOKafkaProducer(
            bootstrap_servers=brokers,
            value_serializer=self._serialize,
            key_serializer=self._serialize_key,
        )
        self._started = False

    @staticmethod
    def _serialize(value: Any) -> bytes:
        """Сериализуем сообщение с минимальными копированиями."""

        # Русский комментарий: избегаем лишней сериализации — готовые байты и строки
        # отправляем как есть, а JSON собираем компактно.
        if value is None:
            return b"null"
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)
        if isinstance(value, str):
            return value.encode("utf-8")
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )

    @classmethod
    def _serialize_key(cls, value: Any) -> bytes:
        # Русский комментарий: ключи могут быть None, строкой или байтами.
        if value is None:
            return cls._empty_bytes
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)
        return str(value).encode("utf-8")

    async def start(self) -> None:
        """Запускаем клиент aiokafka только один раз."""

        if self._started:
            return
        await self._producer.start()
        self._started = True

    async def stop(self) -> None:
        """Останавливаем продюсер, если он активен."""

        if not self._started:
            return
        await self._producer.stop()
        self._started = False

    async def send(self, topic: str, key: Any, value: Any) -> None:
        """Отправить сообщение и записать трассировку."""

        if not self._started:
            raise RuntimeError("KafkaProducer must be started before sending messages")
        with self._tracer.start_as_current_span(f"event.produce:{topic}"):
            await self._producer.send_and_wait(topic, value=value, key=key)

    async def __aenter__(self) -> "KafkaProducer":
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()


class KafkaConsumer:
    """Kafka-консьюмер с JSON-десериализацией."""

    __slots__ = ("_consumer", "_started")

    def __init__(
        self,
        brokers: str,
        topic: str,
        group_id: str,
        *,
        auto_offset_reset: str = "earliest",
    ) -> None:
        # Русский комментарий: инициализируем клиента с единым десериализатором.
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=brokers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            value_deserializer=self._deserialize,
            key_deserializer=self._deserialize,
        )
        self._started = False

    @staticmethod
    def _deserialize(data: bytes | None) -> Any:
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return data

    async def start(self) -> None:
        """Запускаем чтение из Kafka только при первом вызове."""

        if self._started:
            return
        await self._consumer.start()
        self._started = True

    async def stop(self) -> None:
        """Безопасно остановить консьюмера."""

        if not self._started:
            return
        await self._consumer.stop()
        self._started = False

    async def __aenter__(self) -> "KafkaConsumer":
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()

    def __aiter__(self) -> AsyncIterator[Any]:
        if not self._started:
            raise RuntimeError("KafkaConsumer must be started before iteration")
        return self._consume()

    async def _consume(self) -> AsyncIterator[Any]:
        # Русский комментарий: отдаём сырой объект сообщения aiokafka.
        async for msg in self._consumer:
            yield msg
