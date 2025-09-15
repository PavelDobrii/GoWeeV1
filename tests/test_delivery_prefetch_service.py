import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from services.delivery_prefetch.app import deps, kafka_loop, storage
from services.delivery_prefetch.app.main import app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    class TestSettings(deps.Settings):
        kafka_brokers: str | None = "kafka:9092"

    monkeypatch.setattr(deps, "get_settings", lambda: TestSettings())

    async def dummy_start(settings: deps.Settings) -> None:  # pragma: no cover
        """Patched consumer start used in tests."""
        pass

    from services.delivery_prefetch.app import main as main_module

    monkeypatch.setattr(main_module, "start_kafka_consumer", dummy_start)
    storage.clear()
    client = TestClient(app)
    return client


def _msg(payload: dict[str, int | str]):
    class Message:
        def __init__(self, value: bytes) -> None:
            self.value = value

    return Message(json.dumps(payload).encode())


def test_prefetch_returns_closest_audios(client: TestClient) -> None:
    asyncio.run(kafka_loop._handle_message(_msg({"route_id": "1", "audio_id": 10})))
    asyncio.run(kafka_loop._handle_message(_msg({"route_id": "1", "audio_id": 11})))
    asyncio.run(kafka_loop._handle_message(_msg({"route_id": "1", "audio_id": 12})))

    resp = client.get("/delivery/prefetch", params={"route_id": "1", "next": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert [item["audio_id"] for item in data["items"]] == [10, 11]

    resp_single = client.get("/delivery/prefetch", params={"route_id": "1", "next": 1})
    assert resp_single.status_code == 200
    data_single = resp_single.json()
    assert [item["audio_id"] for item in data_single["items"]] == [10]
