import json

from backend.asgi_smoke import run_backend_asgi_mount_smoke


def test_asgi_mount_smoke_covers_core_api_mcp_and_auth(tmp_path):
    result = run_backend_asgi_mount_smoke(
        tmp_path,
        work_dir=tmp_path / "asgi-smoke",
        trace_id="trace_asgi_smoke_test",
    )

    assert result["mode"] == "BACKEND_ASGI_MOUNT_SMOKE"
    assert result["target"] == "backend.asgi_app:app"
    assert result["passed"] is True
    assert result["summary"]["failedStepTotal"] == 0
    assert result["summary"]["coveredApiGroups"] == [
        "health",
        "backend-core-db",
        "backend-core-readiness",
        "mcp-server",
        "ai-tasks-auth",
    ]
    assert result["safety"]["networkListenerStarted"] is False
    assert result["safety"]["externalDatabaseConnected"] is False
    assert result["safety"]["productionDatabaseWritten"] is False
    assert result["safety"]["realLlmCalled"] is False
    assert result["authBoundary"]["missingTokenRejected"] is True
    assert result["authBoundary"]["authorizedRequestAccepted"] is True
    assert result["authBoundary"]["secretValueReturned"] is False

    steps = {step["id"]: step for step in result["steps"]}
    assert steps["health"]["evidence"]["mode"] == "MOCK_ONLY"
    assert steps["backend_core_db_init"]["evidence"]["schemaVersion"] == "1"
    assert steps["backend_core_readiness"]["evidence"]["coreSqliteStagingEnabled"] is True
    assert steps["mcp_tool_call"]["evidence"]["toolMode"] == "MOCK_ONLY"
    assert steps["auth_missing_rejected"]["payloadCode"] == "AUTH_REQUIRED"
    assert steps["auth_authorized_ai_tasks"]["httpStatus"] == 200
    assert "local-asgi-smoke-token" not in json.dumps(result, ensure_ascii=False)
