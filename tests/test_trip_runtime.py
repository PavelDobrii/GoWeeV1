import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from services.trip_runtime.app import api, deps
from services.trip_runtime.app.main import app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    class TestSettings(deps.Settings):
        kafka_brokers: str | None = "kafka:9092"

    monkeypatch.setattr(deps, "get_settings", lambda: TestSettings())
    api._sessions.clear()

    messages: list[dict[str, Any]] = []

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


def test_ping_publishes_approaching(client: TestClient) -> None:
    resp = client.post("/trip/start", json={"route_id": 1})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    resp2 = client.post(
        "/trip/ping",
        json={
            "session_id": session_id,
            "points": [{"lat": 55.751244, "lon": 37.618423}],
        },
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["upcoming_poi"] == 1
    assert data["distance_m"] < 60

    assert client.kafka_messages  # type: ignore[attr-defined]
    msg = client.kafka_messages[0]  # type: ignore[index]
    assert msg["topic"] == "trip.poi.approaching"
    payload = json.loads(msg["value"].decode())
    assert payload["session_id"] == session_id
    assert payload["poi_id"] == 1
