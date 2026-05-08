"""HTTP 接口黑盒测试：覆盖成功路径、校验错误与 LLM 配置分支。"""

from __future__ import annotations

from unittest import mock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    """``GET /healthz`` 返回 200 与固定 JSON。"""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_text_summary_success():
    """mock 模式下 ``text_summary`` 成功并回传 ``request_id`` / ``meta``。"""
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
    """超长文本在 ``max_length`` 内被截断。"""
    long = "A" * 200
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_summary", "input": {"text": long, "max_length": 20}},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]["result"]) <= 20


def test_text_echo_bonus():
    """``text_echo`` 原样返回输入。"""
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_echo", "input": {"text": "ping"}},
    )
    assert r.status_code == 200
    assert r.json()["data"]["result"] == "ping"


def test_unknown_capability():
    """未知能力返回 400 与 ``UNKNOWN_CAPABILITY``。"""
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
    """缺 ``text`` 时 ``INVALID_INPUT``。"""
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_summary", "input": {"max_length": 10}},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INPUT"


def test_validation_error_shape():
    """非法请求体返回 422 与 ``VALIDATION_ERROR`` 结构。"""
    r = client.post("/v1/capabilities/run", json={"capability": ""})
    assert r.status_code == 422
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "VALIDATION_ERROR"


def test_openai_config_missing_key(monkeypatch):
    """OpenAI 模式未配置密钥时 ``CONFIG_ERROR`` / 503。"""
    monkeypatch.setenv("TEXT_SUMMARY_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_summary", "input": {"text": "hello", "max_length": 50}},
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "CONFIG_ERROR"


def test_unknown_summary_provider(monkeypatch):
    """非法 ``TEXT_SUMMARY_PROVIDER`` 返回 ``CONFIG_ERROR``。"""
    monkeypatch.setenv("TEXT_SUMMARY_PROVIDER", "other")
    r = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_summary", "input": {"text": "hello", "max_length": 50}},
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "CONFIG_ERROR"


def test_openai_upstream_success(monkeypatch):
    """Mock ``httpx.Client`` 时 OpenAI 分支成功并遵守 ``max_length``。"""
    monkeypatch.setenv("TEXT_SUMMARY_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = mock.Mock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "  摘要一行  "}}]}

    mock_http = mock.MagicMock()
    mock_http.post.return_value = mock_response
    mock_ctx = mock.MagicMock()
    mock_ctx.__enter__.return_value = mock_http
    mock_ctx.__exit__.return_value = None

    with mock.patch("app.capabilities.llm_summary.httpx.Client", return_value=mock_ctx):
        r = client.post(
            "/v1/capabilities/run",
            json={"capability": "text_summary", "input": {"text": "long text", "max_length": 10}},
        )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert len(r.json()["data"]["result"]) <= 10
