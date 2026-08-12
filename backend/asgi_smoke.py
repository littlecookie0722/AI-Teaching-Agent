"""In-process Backend ASGI smoke runner.

This module turns the ASGI mount smoke into a reusable evidence producer for
tests and CLI runs. It does not start a network listener or connect to external
services.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from backend.asgi_app import create_asgi_app


class BackendAsgiSmokeError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


async def _run_asgi(app: Any, scope: dict[str, Any], messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    pending = list(messages)

    async def receive() -> dict[str, Any]:
        if pending:
            return pending.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await app(scope, receive, send)
    return sent


def _scope(
    method: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    query_string = urlencode(query or {}).encode("utf-8")
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": headers or [],
    }


def _json_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _request(
    app: Any,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict[str, Any]]:
    request_headers = list(headers or [])
    messages = [{"type": "http.request", "body": b"", "more_body": False}]
    if body is not None:
        request_headers.append((b"content-type", b"application/json"))
        messages = [{"type": "http.request", "body": _json_body(body), "more_body": False}]

    sent = asyncio.run(
        _run_asgi(
            app,
            _scope(method, path, query=query, headers=request_headers),
            messages,
        )
    )
    if len(sent) < 2 or sent[0].get("type") != "http.response.start" or sent[1].get("type") != "http.response.body":
        raise BackendAsgiSmokeError(
            "BACKEND_ASGI_SMOKE_INVALID_RESPONSE",
            "ASGI smoke 收到非法响应帧",
            [{"field": "asgiMessages", "reason": json.dumps(sent, ensure_ascii=False)}],
        )
    return int(sent[0]["status"]), json.loads(sent[1]["body"].decode("utf-8"))


def _step(
    step_id: str,
    *,
    method: str,
    path: str,
    status: int,
    payload: dict[str, Any],
    passed: bool,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": step_id,
        "method": method,
        "path": path,
        "httpStatus": status,
        "payloadSuccess": payload.get("success"),
        "payloadCode": payload.get("code"),
        "passed": passed,
        "evidence": evidence or {},
    }


def _require(condition: bool, *, field: str, reason: str) -> None:
    if not condition:
        raise BackendAsgiSmokeError(
            "BACKEND_ASGI_SMOKE_FAILED",
            "Backend ASGI in-process smoke 未通过",
            [{"field": field, "reason": reason}],
        )


def _restore_env(name: str, old_value: str | None) -> None:
    if old_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = old_value


def run_backend_asgi_mount_smoke(
    root: Path,
    *,
    work_dir: Path,
    trace_id: str,
) -> dict[str, Any]:
    """Run core Backend ASGI smoke and return JSON-serializable evidence."""

    run_dir = work_dir / trace_id
    run_dir.mkdir(parents=True, exist_ok=True)
    store_path = run_dir / "store.json"
    core_db_path = run_dir / "backend-core.sqlite3"
    material_path = run_dir / "source.md"
    material_path.write_text("# Backend ASGI smoke\n\nDemo material for MCP analyze_material.", encoding="utf-8")

    old_token = os.environ.get("LAB_BACKEND_API_TOKEN")
    steps: list[dict[str, Any]] = []
    try:
        os.environ.pop("LAB_BACKEND_API_TOKEN", None)
        app = create_asgi_app(store_path=store_path)

        health_status, health = _request(app, "GET", "/api/health")
        init_status, init_payload = _request(
            app,
            "POST",
            "/api/backend/core-db/init",
            body={"coreDbPath": str(core_db_path), "actor": "asgi_smoke"},
        )
        summary_status, summary_payload = _request(
            app,
            "GET",
            "/api/backend/core-db/summary",
            query={"coreDbPath": str(core_db_path)},
        )
        readiness_status, readiness_payload = _request(
            app,
            "GET",
            "/api/backend/core-readiness",
            query={"coreDbPath": str(core_db_path)},
        )
        mcp_info_status, mcp_info = _request(app, "GET", "/api/mcp/server/info")
        mcp_call_status, mcp_call = _request(
            app,
            "POST",
            "/api/mcp/server/call",
            body={"tool": "analyze_material", "arguments": {"input": str(material_path)}},
        )

        steps.extend(
            [
                _step(
                    "health",
                    method="GET",
                    path="/api/health",
                    status=health_status,
                    payload=health,
                    passed=health_status == 200 and health.get("success") is True,
                    evidence={"mode": health.get("data", {}).get("mode")},
                ),
                _step(
                    "backend_core_db_init",
                    method="POST",
                    path="/api/backend/core-db/init",
                    status=init_status,
                    payload=init_payload,
                    passed=init_status == 200
                    and init_payload.get("success") is True
                    and init_payload.get("data", {}).get("productionDatabaseWritten") is False,
                    evidence={
                        "schemaVersion": init_payload.get("data", {})
                        .get("backendCoreRepository", {})
                        .get("schemaVersion"),
                        "productionDatabaseWritten": init_payload.get("data", {}).get("productionDatabaseWritten"),
                    },
                ),
                _step(
                    "backend_core_db_summary",
                    method="GET",
                    path="/api/backend/core-db/summary",
                    status=summary_status,
                    payload=summary_payload,
                    passed=summary_status == 200
                    and summary_payload.get("success") is True
                    and summary_payload.get("data", {}).get("backendCoreRepository", {}).get("available") is True,
                    evidence={
                        "taskTotal": summary_payload.get("data", {})
                        .get("backendCoreRepository", {})
                        .get("taskTotal"),
                        "productionDatabaseWritten": summary_payload.get("data", {})
                        .get("backendCoreRepository", {})
                        .get("productionDatabaseWritten"),
                    },
                ),
                _step(
                    "backend_core_readiness",
                    method="GET",
                    path="/api/backend/core-readiness",
                    status=readiness_status,
                    payload=readiness_payload,
                    passed=readiness_status == 200
                    and readiness_payload.get("success") is True
                    and readiness_payload.get("data", {})
                    .get("backendCoreReadiness", {})
                    .get("safety", {})
                    .get("productionDatabaseWritten")
                    is False,
                    evidence={
                        "coreSqliteStagingEnabled": readiness_payload.get("data", {})
                        .get("backendCoreReadiness", {})
                        .get("coreSqliteStaging", {})
                        .get("enabled"),
                        "productionDatabaseWritten": readiness_payload.get("data", {})
                        .get("backendCoreReadiness", {})
                        .get("safety", {})
                        .get("productionDatabaseWritten"),
                    },
                ),
                _step(
                    "mcp_server_info",
                    method="GET",
                    path="/api/mcp/server/info",
                    status=mcp_info_status,
                    payload=mcp_info,
                    passed=mcp_info_status == 200
                    and mcp_info.get("data", {}).get("safety", {}).get("networkListenerStarted") is False,
                    evidence={
                        "networkListenerStarted": mcp_info.get("data", {})
                        .get("safety", {})
                        .get("networkListenerStarted"),
                        "realMcpServerStarted": mcp_info.get("data", {})
                        .get("safety", {})
                        .get("realMcpServerStarted"),
                    },
                ),
                _step(
                    "mcp_tool_call",
                    method="POST",
                    path="/api/mcp/server/call",
                    status=mcp_call_status,
                    payload=mcp_call,
                    passed=mcp_call_status == 200
                    and mcp_call.get("data", {}).get("response", {}).get("success") is True
                    and mcp_call.get("data", {}).get("networkListenerStarted") is False,
                    evidence={
                        "toolMode": mcp_call.get("data", {})
                        .get("response", {})
                        .get("data", {})
                        .get("analysis", {})
                        .get("mode"),
                        "actor": mcp_call.get("data", {})
                        .get("response", {})
                        .get("data", {})
                        .get("mcpToolCallRecord", {})
                        .get("actor"),
                    },
                ),
            ]
        )

        auth_token = "local-asgi-smoke-token"
        os.environ["LAB_BACKEND_API_TOKEN"] = auth_token
        auth_app = create_asgi_app(store_path=run_dir / "auth-store.json")
        auth_health_status, auth_health = _request(auth_app, "GET", "/api/health")
        auth_missing_status, auth_missing = _request(auth_app, "GET", "/api/ai-tasks")
        auth_ok_status, auth_ok = _request(
            auth_app,
            "GET",
            "/api/ai-tasks",
            headers=[(b"authorization", f"Bearer {auth_token}".encode("utf-8"))],
        )
        auth_serialized = json.dumps([auth_health, auth_missing, auth_ok], ensure_ascii=False)
        token_not_returned = auth_token not in auth_serialized
        steps.extend(
            [
                _step(
                    "auth_health_exempt",
                    method="GET",
                    path="/api/health",
                    status=auth_health_status,
                    payload=auth_health,
                    passed=auth_health_status == 200 and auth_health.get("success") is True,
                    evidence={"healthExemptFromBearerToken": True},
                ),
                _step(
                    "auth_missing_rejected",
                    method="GET",
                    path="/api/ai-tasks",
                    status=auth_missing_status,
                    payload=auth_missing,
                    passed=auth_missing_status == 401 and auth_missing.get("code") == "AUTH_REQUIRED",
                    evidence={"code": auth_missing.get("code")},
                ),
                _step(
                    "auth_authorized_ai_tasks",
                    method="GET",
                    path="/api/ai-tasks",
                    status=auth_ok_status,
                    payload=auth_ok,
                    passed=auth_ok_status == 200 and auth_ok.get("success") is True and token_not_returned,
                    evidence={"secretValueReturned": not token_not_returned},
                ),
            ]
        )
        _require(token_not_returned, field="LAB_BACKEND_API_TOKEN", reason="token leaked in ASGI smoke payload")
    finally:
        _restore_env("LAB_BACKEND_API_TOKEN", old_token)

    for item in steps:
        _require(bool(item["passed"]), field=item["id"], reason=f"HTTP {item['httpStatus']} {item['payloadCode']}")

    passed_total = sum(1 for item in steps if item["passed"])
    return {
        "id": f"backend_asgi_mount_smoke_{trace_id}",
        "mode": "BACKEND_ASGI_MOUNT_SMOKE",
        "target": "backend.asgi_app:app",
        "entrypoint": "backend.asgi_app:create_asgi_app",
        "traceId": trace_id,
        "runDir": str(run_dir),
        "storePath": str(store_path),
        "coreDbPath": str(core_db_path),
        "materialPath": str(material_path),
        "passed": passed_total == len(steps),
        "summary": {
            "stepTotal": len(steps),
            "passedStepTotal": passed_total,
            "failedStepTotal": len(steps) - passed_total,
            "coveredApiGroups": [
                "health",
                "backend-core-db",
                "backend-core-readiness",
                "mcp-server",
                "ai-tasks-auth",
            ],
        },
        "steps": steps,
        "authBoundary": {
            "enabledForSmoke": True,
            "healthExempt": True,
            "missingTokenRejected": True,
            "authorizedRequestAccepted": True,
            "secretEnv": "LAB_BACKEND_API_TOKEN",
            "usesEphemeralSmokeToken": True,
            "existingSecretEnvTemporarilyMasked": old_token is not None,
            "secretValueReturned": False,
        },
        "safety": {
            "inProcessOnly": True,
            "networkListenerStarted": False,
            "externalDatabaseConnected": False,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "realCloudResourceCreated": False,
            "realLlmCalled": False,
            "userSecretEnvTemporarilyMasked": old_token is not None,
            "secretValueReturned": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "contestantCodeExecutedWithoutSandbox": False,
        },
    }
