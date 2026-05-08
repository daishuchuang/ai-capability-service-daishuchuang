from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_text_summary_success():
    body = {
        "capability": "text_summary",
        "input": {"text": "Hello world. Second sentence here.", "max_length": 120},
        "request_id": "req-1",
    }
    r = client.post("/v1/capabilities/run", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "result" in data["data"]
    assert data["meta"]["request_id"] == "req-1"
    assert data["meta"]["capability"] == "text_summary"
    assert data["meta"]["elapsed_ms"] >= 0


def test_text_summary_truncates():
    long = "A" * 200
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_summary", "input": {"text": long, "max_length": 20}},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]["result"]) <= 20


def test_text_echo_bonus():
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_echo", "input": {"text": "ping"}},
    )
    assert r.status_code == 200
    assert r.json()["data"]["result"] == "ping"


def test_unknown_capability():
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "not_real", "input": {}},
    )
    assert r.status_code == 400
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "UNKNOWN_CAPABILITY"
    assert "meta" in j
    assert j["meta"]["capability"] == "not_real"


def test_invalid_input_missing_text():
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_summary", "input": {"max_length": 10}},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INPUT"


def test_validation_error_shape():
    r = client.post("/v1/capabilities/run", json={"capability": ""})
    assert r.status_code == 422
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "VALIDATION_ERROR"
