"""Framework-neutral Backend API app boundary.

This module adapts the local mock API handler and static frontend serving into
a small request/response surface. It is still a local development boundary, but
keeps HTTP server mechanics separate from route behavior so a future FastAPI or
ASGI adapter can reuse the same contract.
"""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from backend.mock_api import fail, handle_request


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"

LEGACY_FRONTEND_ALIASES = {
    "platform-entities.html": "agent-entities.html",
    "/platform-entities.html": "/agent-entities.html",
}


@dataclass(frozen=True)
class BackendAppResponse:
    status: int
    content_type: str
    body: bytes
    payload: dict[str, Any] | None = None


def json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def http_status_for_payload(payload: dict[str, Any]) -> int:
    if payload.get("success") is True:
        return 200
    code = payload.get("code")
    if code in {"AUTH_REQUIRED", "AUTH_INVALID"}:
        return 401
    if code == "NOT_FOUND":
        return 404
    if code == "METHOD_NOT_ALLOWED":
        return 405
    return 400


def json_response(payload: dict[str, Any]) -> BackendAppResponse:
    return BackendAppResponse(
        status=http_status_for_payload(payload),
        content_type="application/json; charset=utf-8",
        body=json_bytes(payload),
        payload=payload,
    )


class BackendApiApp:
    def __init__(
        self,
        *,
        store_path: Path | None = None,
        frontend_root: Path = FRONTEND_ROOT,
    ) -> None:
        self.store_path = store_path
        self.frontend_root = frontend_root

    def handle(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> BackendAppResponse:
        method = method.upper()
        if path.startswith("/api/"):
            payload = handle_request(
                method,
                path,
                store_path=self.store_path,
                body=body or {},
                headers=headers or {},
            )
            return json_response(payload)
        if method == "GET":
            return self._static_get(path)
        if method == "POST":
            return json_response(
                fail("NOT_FOUND", "仅支持 /api/* POST", [{"field": "path", "reason": path}])
            )
        return json_response(
            fail("METHOD_NOT_ALLOWED", "仅支持 GET 或 POST", [{"field": "method", "reason": method}])
        )

    def invalid_json_response(self) -> BackendAppResponse:
        return json_response(
            fail("VALIDATION_ERROR", "请求体不是 JSON object", [{"field": "body", "reason": "invalid json"}])
        )

    def _static_get(self, raw_path: str) -> BackendAppResponse:
        static_path = self.resolve_frontend_path(raw_path)
        if static_path is None:
            return json_response(
                fail("NOT_FOUND", "静态文件不存在", [{"field": "path", "reason": raw_path}])
            )
        content_type = mimetypes.guess_type(static_path.name)[0] or "application/octet-stream"
        return BackendAppResponse(
            status=200,
            content_type=f"{content_type}; charset=utf-8",
            body=static_path.read_bytes(),
        )

    def resolve_frontend_path(self, raw_path: str) -> Path | None:
        path = unquote(raw_path.split("?", 1)[0])
        if path in {"", "/"}:
            path = "/review-center.html"
        if path in LEGACY_FRONTEND_ALIASES:
            path = LEGACY_FRONTEND_ALIASES[path]
        candidate = (self.frontend_root / path.lstrip("/")).resolve()
        try:
            candidate.relative_to(self.frontend_root.resolve())
        except ValueError:
            return None
        if candidate.is_dir():
            candidate = candidate / "index.html"
        return candidate if candidate.exists() and candidate.is_file() else None
