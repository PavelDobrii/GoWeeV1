import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from services.route_planner.app import deps
from services.route_planner.app.main import app


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

    from services.route_planner.app import api

    class DummyProducer:
        async def start(self) -> None:  # pragma: no cover - simple stub
            pass

        async def stop(self) -> None:  # pragma: no cover - simple stub
            pass

        async def send_and_wait(self, topic: str, value: bytes, key: bytes) -> None:
            messages.append({"topic": topic, "value": value, "key": key})

    monkeypatch.setattr(api, "AIOKafkaProducer", lambda *a, **k: DummyProducer())

    client = TestClient(app)
    client.kafka_messages = messages  # type: ignore[attr-defined]
    return client


def test_preview_and_confirm(client: TestClient) -> None:
    resp = client.post(
        "/routes/preview",
        json={"poi_ids": [1, 2, 3], "mode": "car", "duration_target_min": 100},
    )
    assert resp.status_code == 200
    option_id = resp.json()["options"][0]["option_id"]

    resp2 = client.post("/routes/confirm", json={"option_id": option_id})
    assert resp2.status_code == 200
    route_id = resp2.json()["route_id"]

    assert client.kafka_messages  # type: ignore[attr-defined]
    msg = client.kafka_messages[0]  # type: ignore[index]
    assert msg["topic"] == "route.confirmed"
    payload = json.loads(msg["value"].decode())
    assert payload["route_id"] == route_id
