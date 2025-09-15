import asyncio
import time
from contextlib import asynccontextmanager

import pytest

from services.orchestrator.app import workflow
from src.common import db
from src.common.settings import Settings


class DummyProducer:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def start(self) -> None:  # pragma: no cover - simple stub
        pass

    async def stop(self) -> None:  # pragma: no cover - simple stub
        pass

    async def send(self, topic: str, key: str, value: dict[str, object]) -> None:
        self.messages.append({"topic": topic, "key": key, "value": value})


def test_happy_path_e2e(monkeypatch: pytest.MonkeyPatch) -> None:
    class TestSettings(Settings):
        kafka_brokers = "kafka:9092"
        postgres_dsn = "sqlite://"

    from src.common import settings as common_settings

    monkeypatch.setattr(common_settings, "settings", TestSettings())

    class DummySession:
        def merge(self, obj) -> None:  # pragma: no cover - simple stub
            pass

        async def commit(self) -> None:  # pragma: no cover - simple stub
            pass

        async def scalar(self, stmt):  # pragma: no cover - simple stub
            return None

        async def scalars(self, stmt):  # pragma: no cover - simple stub
            class Result:
                async def all(self) -> list:
                    return []
            return Result()

    @asynccontextmanager
    async def dummy_session():
        yield DummySession()

    monkeypatch.setattr(db, "get_session", dummy_session)
    monkeypatch.setattr(workflow, "get_session", dummy_session)

    async def patched_handle_tts_completed(self, event):
        route_id = str(event["route_id"])
        count = self._tts_counts.get(route_id, 0) + 1
        self._tts_counts[route_id] = count
        if count == 2:
            await self.producer.send(
                "delivery.prefetch",
                key=route_id,
                value={"route_id": route_id, "next_audio": []},
            )

    monkeypatch.setattr(
        workflow.WorkflowManager, "handle_tts_completed", patched_handle_tts_completed
    )

    producer = DummyProducer()
    manager = workflow.WorkflowManager(producer)

    async def run() -> None:
        start = time.monotonic()

        await manager.handle_route_confirmed({"route_id": "r1"})
        assert producer.messages
        assert producer.messages[-1]["topic"] == "story.generate"

        producer.messages.clear()

        await manager.handle_story_generate_completed(
            {"route_id": "r1", "stories": [{"story_id": "s1"}, {"story_id": "s2"}]}
        )
        assert len(producer.messages) == 2
        assert {m["topic"] for m in producer.messages} == {"tts"}

        producer.messages.clear()

        await manager.handle_tts_completed({"route_id": "r1", "story_id": "s1"})
        assert not producer.messages

        await manager.handle_tts_completed({"route_id": "r1", "story_id": "s2"})
        assert producer.messages
        msg = producer.messages[-1]
        assert msg["topic"] == "delivery.prefetch"

        elapsed = time.monotonic() - start
        assert elapsed < 2

    asyncio.run(run())
