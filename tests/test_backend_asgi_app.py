import asyncio
import json

from backend.asgi_app import BackendAsgiApp, create_asgi_app
from backend.mock_api import handle_request


async def _run_asgi(app, scope, messages):
    sent = []
    pending = list(messages)

    async def receive():
        if pending:
            return pending.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    return sent


def _http_scope(method, path, *, query_string=b"", headers=None):
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": headers or [],
    }


def _response_payload(sent):
    start = sent[0]
    body = sent[1]
    assert start["type"] == "http.response.start"
    assert body["type"] == "http.response.body"
    return start, json.loads(body["body"].decode("utf-8"))


def test_create_asgi_app_returns_callable():
    app = create_asgi_app()

    assert isinstance(app, BackendAsgiApp)
    assert callable(app)


def test_backend_asgi_app_serves_get_api(tmp_path):
    app = create_asgi_app(store_path=tmp_path / "store.json")

    sent = asyncio.run(_run_asgi(
        app,
        _http_scope("GET", "/api/health"),
        [{"type": "http.request", "body": b"", "more_body": False}],
    ))

    start, payload = _response_payload(sent)
    assert start["status"] == 200
    assert payload["success"] is True
    assert payload["data"]["mode"] == "MOCK_ONLY"


def test_backend_asgi_app_serves_static_root(tmp_path):
    app = create_asgi_app(store_path=tmp_path / "store.json")

    sent = asyncio.run(_run_asgi(
        app,
        _http_scope("GET", "/"),
        [{"type": "http.request", "body": b"", "more_body": False}],
    ))

    assert sent[0]["status"] == 200
    assert any(name == b"content-type" and value.startswith(b"text/html") for name, value in sent[0]["headers"])
    assert b"review-center-data.js" in sent[1]["body"]


def test_backend_asgi_app_handles_post_json(tmp_path):
    app = create_asgi_app(store_path=tmp_path / "store.json")
    body = json.dumps({"input": "examples/input/demo-source.md"}).encode("utf-8")

    sent = asyncio.run(_run_asgi(
        app,
        _http_scope("POST", "/api/labs/generate", headers=[(b"content-type", b"application/json")]),
        [{"type": "http.request", "body": body, "more_body": False}],
    ))

    start, payload = _response_payload(sent)
    assert start["status"] == 200
    assert payload["success"] is True
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"


def test_backend_asgi_app_preserves_query_string(tmp_path):
    store_path = tmp_path / "store.json"
    handle_request("POST", "/api/labs/generate", store_path=store_path, body={"input": "examples/input/demo-source.md"})
    app = create_asgi_app(store_path=store_path)

    sent = asyncio.run(_run_asgi(
        app,
        _http_scope("GET", "/api/ai-tasks", query_string=b"status=WAITING_REVIEW"),
        [{"type": "http.request", "body": b"", "more_body": False}],
    ))

    start, payload = _response_payload(sent)
    assert start["status"] == 200
    assert payload["data"]["filters"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["total"] == 1


def test_backend_asgi_app_maps_auth_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_API_TOKEN", "local-backend-token")
    app = create_asgi_app(store_path=tmp_path / "store.json")

    missing = asyncio.run(_run_asgi(
        app,
        _http_scope("GET", "/api/ai-tasks"),
        [{"type": "http.request", "body": b"", "more_body": False}],
    ))
    authorized = asyncio.run(_run_asgi(
        app,
        _http_scope("GET", "/api/ai-tasks", headers=[(b"authorization", b"Bearer local-backend-token")]),
        [{"type": "http.request", "body": b"", "more_body": False}],
    ))

    missing_start, missing_payload = _response_payload(missing)
    authorized_start, authorized_payload = _response_payload(authorized)
    assert missing_start["status"] == 401
    assert missing_payload["code"] == "AUTH_REQUIRED"
    assert authorized_start["status"] == 200
    assert authorized_payload["success"] is True


def test_backend_asgi_app_rejects_invalid_json(tmp_path):
    app = create_asgi_app(store_path=tmp_path / "store.json")

    sent = asyncio.run(_run_asgi(
        app,
        _http_scope("POST", "/api/labs/generate", headers=[(b"content-type", b"application/json")]),
        [{"type": "http.request", "body": b"{not-json", "more_body": False}],
    ))

    start, payload = _response_payload(sent)
    assert start["status"] == 400
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "body"


def test_backend_asgi_app_lifespan():
    app = create_asgi_app()
    messages = [
        {"type": "lifespan.startup"},
        {"type": "lifespan.shutdown"},
    ]

    sent = asyncio.run(_run_asgi(app, {"type": "lifespan"}, messages))

    assert sent == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]
