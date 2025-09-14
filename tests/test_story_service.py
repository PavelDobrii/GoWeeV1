import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from services.story_service.app import deps
from services.story_service.app.main import app
from services.story_service.app import models


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    class TestSettings(deps.Settings):
        database_url = "sqlite:///:memory:"
        kafka_brokers = "kafka:9092"

    monkeypatch.setattr(deps, "get_settings", lambda: TestSettings())
    deps._engine = None  # type: ignore[attr-defined]
    deps._SessionLocal = None  # type: ignore[attr-defined]
    deps.init_db()

    messages: list[dict[str, Any]] = []

    from services.story_service.app import api

    class DummyProducer:
        async def start(self) -> None:
            pass

        async def stop(self) -> None:
            pass

        async def send_and_wait(self, topic: str, value: bytes, key: bytes) -> None:
            messages.append({"topic": topic, "value": value, "key": key})

    monkeypatch.setattr(api, "AIOKafkaProducer", lambda *a, **k: DummyProducer())

    client = TestClient(app)
    client.kafka_messages = messages  # type: ignore[attr-defined]
    return client


def test_generate_batch_creates_stories_and_event(client: TestClient) -> None:
    resp = client.post("/story/generate_batch", json={"route_id": "r1", "lang": "en"})
    assert resp.status_code == 202
    assert resp.json()["job_id"]

    # Check DB
    SessionLocal = deps.get_sessionmaker()
    with SessionLocal() as db:
        stories = db.query(models.Story).all()
    assert len(stories) == 2
    poi_ids = {s.poi_id for s in stories}
    assert poi_ids == {1, 2}

    # Check Kafka message
    assert client.kafka_messages  # type: ignore[attr-defined]
    msg = client.kafka_messages[0]  # type: ignore[index]
    assert msg["topic"] == "story.generate.completed"
    payload = json.loads(msg["value"].decode())
    assert payload["route_id"] == "r1"
    returned_poi_ids = {s["poi_id"] for s in payload["stories"]}
    assert returned_poi_ids == {1, 2}
