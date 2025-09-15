import importlib

import pytest
from fastapi.testclient import TestClient

from services.paywall_billing.app.main import app


@pytest.fixture(autouse=True)
def reset_state() -> None:
    api = importlib.import_module("services.paywall_billing.app.api")
    api._usage_day = ""  # type: ignore[attr-defined]
    api._usage_count = 0  # type: ignore[attr-defined]
    api._subscription = {"status": "inactive", "expire_at": None}  # type: ignore[attr-defined]


def test_paywall_check_limit() -> None:
    client = TestClient(app)
    resp1 = client.get("/paywall/check", params={"action": "route"})
    assert resp1.status_code == 200
    assert resp1.json() == {"show": False}

    resp2 = client.get("/paywall/check", params={"action": "route"})
    assert resp2.status_code == 200
    assert resp2.json()["show"] is True


def test_iap_validate_and_status() -> None:
    client = TestClient(app)
    resp = client.get("/iap/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"

    resp_val = client.post(
        "/iap/validate", json={"platform": "ios", "receipt": "dummy"}
    )
    assert resp_val.status_code == 200
    data = resp_val.json()
    assert data["status"] == "active"
    assert data["expire_at"]

    resp_status = client.get("/iap/status")
    assert resp_status.status_code == 200
    data2 = resp_status.json()
    assert data2["status"] == "active"
    assert data2["expire_at"] == data["expire_at"]
