import io
import json
from urllib.error import HTTPError, URLError

from cli import agent_api_adapter
from cli.agent_api_adapter import (
    AgentApiAdapterError,
    build_agent_api_runtime_config,
    normalize_agent_api_max_retries,
    send_agent_api_get_json,
    send_agent_api_post_json,
)


class FakeResponse:
    def __init__(self, *, status=200, reason="OK", headers=None, body=b"{}"):
        self.status = status
        self.reason = reason
        self.headers = headers or {"Content-Type": "application/json"}
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False

    def read(self):
        return self._body


def test_platform_api_runtime_config_redacts_token(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")

    config = build_agent_api_runtime_config(base_url="http://platform.local")

    assert config.base_url == "http://platform.local"
    assert config.token == "platform-secret-token"
    assert config.env["AGENT_API_BASE_URL"]["value"] == "http://platform.local"
    assert config.env["AGENT_API_TOKEN"]["present"] is True
    assert config.env["AGENT_API_TOKEN"]["valueReturned"] is False
    assert "platform-secret-token" not in json.dumps(config.env, ensure_ascii=False)


def test_platform_api_post_retries_network_error_then_returns_json(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append({"request": request, "timeout": timeout})
        if len(calls) == 1:
            raise URLError("temporary")
        assert request.get_method() == "POST"
        assert request.full_url == "http://platform.local/api/drafts"
        assert request.get_header("Authorization") == "Bearer token_1"
        assert json.loads(request.data.decode("utf-8")) == {"title": "Lab"}
        return FakeResponse(
            status=202,
            reason="Accepted",
            body=b'{"draftImportId":"draft_1","status":"PENDING"}',
        )

    monkeypatch.setattr(agent_api_adapter, "urlopen", fake_urlopen)

    response = send_agent_api_post_json(
        base_url="http://platform.local",
        path="/api/drafts",
        token="token_1",
        body={"title": "Lab"},
        timeout_seconds=5,
        max_retries=1,
    )

    assert len(calls) == 2
    assert response["ok"] is True
    assert response["statusCode"] == 202
    assert response["body"]["json"]["draftImportId"] == "draft_1"
    assert response["attempts"] == 2
    assert response["maxRetries"] == 1
    assert response["attemptLog"][0]["errorType"] == "URLError"


def test_platform_api_get_retries_5xx_http_error(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append({"request": request, "timeout": timeout})
        if len(calls) == 1:
            raise HTTPError(
                request.full_url,
                503,
                "Service Unavailable",
                {"Content-Type": "application/json"},
                io.BytesIO(b'{"error":"busy"}'),
            )
        assert request.get_method() == "GET"
        return FakeResponse(status=200, reason="OK", body=b'{"status":"ACCEPTED_FOR_DRAFT"}')

    monkeypatch.setattr(agent_api_adapter, "urlopen", fake_urlopen)

    response = send_agent_api_get_json(
        base_url="http://platform.local",
        path="api/drafts/draft_1",
        token="token_1",
        timeout_seconds=5,
        max_retries=1,
    )

    assert len(calls) == 2
    assert response["ok"] is True
    assert response["statusCode"] == 200
    assert response["attempts"] == 2
    assert response["attemptLog"][0]["statusCode"] == 503
    assert response["attemptLog"][0]["retryable"] is True


def test_platform_api_http_400_is_normalized_without_retry(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append({"request": request, "timeout": timeout})
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"code":"BAD_REQUEST"}'),
        )

    monkeypatch.setattr(agent_api_adapter, "urlopen", fake_urlopen)

    response = send_agent_api_get_json(
        base_url="http://platform.local",
        path="/api/drafts/draft_1",
        token="token_1",
        max_retries=2,
    )

    assert len(calls) == 1
    assert response["ok"] is False
    assert response["statusCode"] == 400
    assert response["errorType"] == "HTTPError"
    assert response["body"]["json"]["code"] == "BAD_REQUEST"
    assert response["attempts"] == 1
    assert response["maxRetries"] == 2


def test_platform_api_raises_after_retry_exhaustion(monkeypatch):
    def fake_urlopen(_request, timeout):
        assert timeout == 30
        raise URLError("unreachable")

    monkeypatch.setattr(agent_api_adapter, "urlopen", fake_urlopen)

    try:
        send_agent_api_get_json(
            base_url="http://platform.local",
            path="/api/drafts/draft_1",
            token="token_1",
            max_retries=1,
        )
    except AgentApiAdapterError as exc:
        assert exc.code == "PLATFORM_API_REQUEST_FAILED"
        assert exc.errors == [{"field": "platformApi", "reason": "URLError"}]
        assert exc.context["maxRetries"] == 1
        assert len(exc.context["attempts"]) == 2
    else:
        raise AssertionError("expected AgentApiAdapterError")


def test_platform_api_rejects_invalid_max_retries():
    for value, expected_reason in [("bad", "必须是整数"), (-1, "必须大于等于 0")]:
        try:
            normalize_agent_api_max_retries(value)
        except AgentApiAdapterError as exc:
            assert exc.code == "VALIDATION_ERROR"
            assert exc.errors == [{"field": "maxRetries", "reason": expected_reason}]
        else:
            raise AssertionError("expected AgentApiAdapterError")
