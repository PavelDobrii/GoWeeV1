import json
from typing import Any

import asyncio
import pytest
from fastapi.testclient import TestClient

from services.tts_service.app import deps, kafka_loop, models
from services.tts_service.app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    class TestSettings(deps.Settings):
        database_url = "sqlite:///:memory:"
        kafka_brokers = "kafka:9092"
        audio_dir = str(tmp_path)

    monkeypatch.setattr(deps, "get_settings", lambda: TestSettings())
    deps._engine = None  # type: ignore[attr-defined]
    deps._SessionLocal = None  # type: ignore[attr-defined]
    deps.init_db()

    from services.tts_service.app import api, main as main_module

    messages: list[dict[str, Any]] = []

    class DummyProducer:
        async def start(self) -> None:
            pass

        async def stop(self) -> None:
            pass

        async def send_and_wait(self, topic: str, value: bytes, key: bytes) -> None:
            messages.append({"topic": topic, "value": value, "key": key})

    async def dummy_start_consumer(settings: deps.Settings) -> None:  # pragma: no cover - patched
        pass

    monkeypatch.setattr(api, "AIOKafkaProducer", lambda *a, **k: DummyProducer())
    monkeypatch.setattr(kafka_loop, "AIOKafkaProducer", lambda *a, **k: DummyProducer())
    monkeypatch.setattr(main_module, "start_kafka_consumer", dummy_start_consumer)

    kafka_loop._processed.clear()

    client = TestClient(app)
    client.kafka_messages = messages  # type: ignore[attr-defined]
    return client


def test_request_tts_publishes_event(client: TestClient) -> None:
    resp = client.post("/tts/request", json={"story_id": 1, "voice": "v1", "format": "mp3"})
    assert resp.status_code == 202
    assert resp.json()["job_id"]

    assert client.kafka_messages  # type: ignore[attr-defined]
    msg = client.kafka_messages[0]
    assert msg["topic"] == "tts.requested"
    payload = json.loads(msg["value"].decode())
    assert payload == {"story_id": 1, "voice": "v1", "format": "mp3"}


def test_handle_message_creates_file_and_event(client: TestClient, tmp_path) -> None:
    message_payload = {"story_id": 2, "voice": "v2", "format": "mp3"}

    class Message:
        def __init__(self, value: bytes) -> None:
            self.value = value
            self.key = b"k"
            self.offset = 0

    msg = Message(json.dumps(message_payload).encode())

    asyncio.run(kafka_loop._handle_message(msg))

    # Check DB entry
    SessionLocal = deps.get_sessionmaker()
    with SessionLocal() as db:
        audios = db.query(models.AudioFile).all()
    assert len(audios) == 1
    audio = audios[0]
    assert audio.story_id == 2
    assert audio.path.endswith(".mp3")

    # Check file exists
    from pathlib import Path

    assert Path(audio.path).exists()

    # Check Kafka message
    assert client.kafka_messages  # type: ignore[attr-defined]
    msg_out = client.kafka_messages[0]
    assert msg_out["topic"] == "tts.completed"
    payload_out = json.loads(msg_out["value"].decode())
    assert payload_out["story_id"] == 2
    assert payload_out["audio_id"] == audio.id
    assert payload_out["duration_sec"] == 0
