import json

from backend.app import BackendApiApp, http_status_for_payload, json_response
from backend.mock_api import fail


def _payload(response):
    assert response.content_type.startswith("application/json")
    return json.loads(response.body.decode("utf-8"))


def test_backend_api_app_handles_api_and_static_root(tmp_path):
    app = BackendApiApp(store_path=tmp_path / "store.json")

    health = app.handle("GET", "/api/health")
    root = app.handle("GET", "/")

    health_payload = _payload(health)
    assert health.status == 200
    assert health_payload["success"] is True
    assert health_payload["data"]["mode"] == "MOCK_ONLY"
    assert root.status == 200
    assert root.content_type.startswith("text/html")
    assert b"review-center-data.js" in root.body


def test_backend_api_app_serves_one_click_generation_workspace(tmp_path):
    app = BackendApiApp(store_path=tmp_path / "store.json")

    page = app.handle("GET", "/generation-workspace.html")
    script = app.handle("GET", "/generation-workspace-data.js")

    assert page.status == 200
    assert page.content_type.startswith("text/html")
    assert b"generation-workspace-data.js" in page.body
    assert script.status == 200
    assert script.content_type.startswith("text/javascript")
    assert b"/api/phase2/workflows/content-generation/run" in script.body


def test_backend_api_app_blocks_static_path_traversal(tmp_path):
    app = BackendApiApp(store_path=tmp_path / "store.json")

    response = app.handle("GET", "/../AGENTS.md")

    payload = _payload(response)
    assert response.status == 404
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "path"


def test_backend_api_app_maps_auth_status_without_leaking_token(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_API_TOKEN", "local-backend-token")
    app = BackendApiApp(store_path=tmp_path / "store.json")

    missing = app.handle("GET", "/api/ai-tasks")
    authorized = app.handle("GET", "/api/ai-tasks", headers={"Authorization": "Bearer local-backend-token"})

    missing_payload = _payload(missing)
    authorized_payload = _payload(authorized)
    assert missing.status == 401
    assert missing_payload["code"] == "AUTH_REQUIRED"
    assert "local-backend-token" not in json.dumps(missing_payload, ensure_ascii=False)
    assert authorized.status == 200
    assert authorized_payload["success"] is True


def test_backend_api_app_invalid_json_and_non_api_post_responses(tmp_path):
    app = BackendApiApp(store_path=tmp_path / "store.json")

    invalid_json = app.invalid_json_response()
    non_api_post = app.handle("POST", "/review-center.html", body={})

    invalid_payload = _payload(invalid_json)
    non_api_payload = _payload(non_api_post)
    assert invalid_json.status == 400
    assert invalid_payload["code"] == "VALIDATION_ERROR"
    assert non_api_post.status == 404
    assert non_api_payload["code"] == "NOT_FOUND"


def test_backend_app_json_response_status_mapping():
    assert http_status_for_payload({"success": True, "code": "OK"}) == 200
    assert http_status_for_payload(fail("AUTH_INVALID", "bad")) == 401
    assert http_status_for_payload(fail("NOT_FOUND", "missing")) == 404
    assert http_status_for_payload(fail("METHOD_NOT_ALLOWED", "bad method")) == 405
    assert json_response(fail("VALIDATION_ERROR", "bad input")).status == 400
