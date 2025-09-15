import pytest
from sqlalchemy import select

from services.orchestrator.app import models, workflow
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


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_story_and_tts_flow(
    monkeypatch: pytest.MonkeyPatch, anyio_backend: str
) -> None:
    class TestSettings(Settings):
        kafka_brokers = "kafka:9092"
        postgres_dsn = "sqlite+aiosqlite:///:memory:"

    from src.common import settings as common_settings

    monkeypatch.setattr(common_settings, "settings", TestSettings())
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_sessionmaker", None)

    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.create_all)

    producer = DummyProducer()
    manager = workflow.WorkflowManager(producer)

    await manager.handle_route_confirmed({"route_id": "r1"})
    assert producer.messages
    msg = producer.messages[0]
    assert msg["topic"] == "story.generate"
    assert msg["value"]["route_id"] == "r1"

    producer.messages.clear()

    await manager.handle_story_generate_completed(
        {"route_id": "r1", "stories": [{"story_id": "s1"}, {"story_id": "s2"}]}
    )
    assert len(producer.messages) == 2
    topics = {m["topic"] for m in producer.messages}
    assert topics == {"tts"}
    story_ids = {m["value"]["story_id"] for m in producer.messages}
    assert story_ids == {"s1", "s2"}

    async with db.get_session() as session:
        steps = (
            await session.scalars(
                select(models.WorkflowStep).where(models.WorkflowStep.route_id == "r1")
            )
        ).all()
    assert any(s.step == "story" and s.status == "completed" for s in steps)
