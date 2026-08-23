"""Framework-neutral Backend API app boundary.

This module adapts the local mock API handler and static frontend serving into
a small request/response surface. It is still a local development boundary, but
keeps HTTP server mechanics separate from route behavior so a future FastAPI or
ASGI adapter can reuse the same contract.
"""

from __future__ import annotations

from hashlib import sha256
import hmac
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from backend.mock_api import fail, handle_request, make_trace_id, validate_backend_api_auth
from cli.ai_task import TaskStatus
from cli.artifact import ArtifactKind
from cli.store import JsonTaskStore
from cli.workspace import resolve_cli_path, workspace_root


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
        if method == "GET" and path.split("?", 1)[0].startswith("/api/ppt-artifacts/"):
            return self._ppt_artifact_get(path, headers=headers)
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

    def _ppt_artifact_get(
        self,
        raw_path: str,
        *,
        headers: dict[str, str] | None,
    ) -> BackendAppResponse:
        path = unquote(raw_path.split("?", 1)[0])
        auth_error = validate_backend_api_auth(
            headers=headers,
            path=path.rstrip("/") or "/",
            trace_id=make_trace_id(),
        )
        if auth_error:
            return json_response(auth_error)
        parts = [part for part in path.split("/") if part]
        if len(parts) not in {4, 5} or parts[:2] != ["api", "ppt-artifacts"]:
            return json_response(fail("NOT_FOUND", "PPT Artifact 路由不存在", [{"field": "path", "reason": path}]))

        artifact_id = parts[2]
        store = JsonTaskStore(self.store_path)
        artifact = store.get_artifact(artifact_id)
        if artifact is None or artifact.kind != ArtifactKind.PPTX_FILE:
            return json_response(
                fail("NOT_FOUND", "PPTX Artifact 不存在", [{"field": "artifactId", "reason": "not found"}])
            )
        task = store.get(str(artifact.taskId or "")) if artifact.taskId else None
        metadata = artifact.metadata if isinstance(artifact.metadata, dict) else {}
        product_deck = (
            metadata.get("artifactProfile") == "presentation-deck"
            or (task is not None and task.inputType == "teaching_package_workflow")
        )
        route = parts[3]
        candidate_value: str | None = None
        expected_sha256: str | None = None
        content_type = "application/octet-stream"

        if route == "download" and len(parts) == 4:
            if task is None or task.status != TaskStatus.APPROVED:
                return json_response(
                    fail(
                        "PPT_ARTIFACT_DOWNLOAD_BLOCKED",
                        "PPTX 仅在课件人工批准后允许下载",
                        [{"field": "task.status", "reason": "must be APPROVED"}],
                    )
                )
            candidate_value = artifact.path
            expected_sha256 = metadata.get("sha256") if isinstance(metadata.get("sha256"), str) else None
            content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif route == "contact-sheet" and len(parts) == 4:
            contact_sheet = metadata.get("contactSheet")
            if isinstance(contact_sheet, dict):
                candidate_value = str(contact_sheet.get("path") or "")
                expected_sha256 = (
                    contact_sheet.get("sha256") if isinstance(contact_sheet.get("sha256"), str) else None
                )
            candidate_value = candidate_value or str(metadata.get("contactSheetPath") or "")
            content_type = "image/png"
        elif route == "previews" and len(parts) == 5:
            try:
                slide_index = int(parts[4])
            except ValueError:
                slide_index = 0
            slide_previews = metadata.get("slidePreviews")
            if not isinstance(slide_previews, list):
                preview = metadata.get("preview", {})
                slide_previews = preview.get("slidePreviews", []) if isinstance(preview, dict) else []
            item = None
            for position, slide in enumerate(slide_previews, start=1):
                if not isinstance(slide, dict):
                    continue
                try:
                    candidate_index = int(slide.get("index") or position)
                except (TypeError, ValueError):
                    continue
                if candidate_index == slide_index:
                    item = slide
                    break
            candidate_value = str(item.get("imagePath") or "") if isinstance(item, dict) else ""
            expected_sha256 = item.get("sha256") if isinstance(item, dict) and isinstance(item.get("sha256"), str) else None
            content_type = "image/png"
        else:
            return json_response(fail("NOT_FOUND", "PPT Artifact 路由不存在", [{"field": "path", "reason": path}]))

        candidate = self._resolve_registered_ppt_file(candidate_value)
        if candidate is None:
            return json_response(
                fail("NOT_FOUND", "PPT Artifact 文件不存在", [{"field": "artifactId", "reason": artifact_id}])
            )
        expected_suffix = ".pptx" if route == "download" else ".png"
        if candidate.suffix.lower() != expected_suffix:
            return json_response(
                fail("NOT_FOUND", "PPT Artifact 文件类型不受支持", [{"field": "artifactId", "reason": artifact_id}])
            )
        try:
            body = candidate.read_bytes()
        except OSError:
            return json_response(
                fail("NOT_FOUND", "PPT Artifact 文件不存在", [{"field": "artifactId", "reason": artifact_id}])
            )
        expected_digest = expected_sha256.strip().lower() if expected_sha256 else ""
        if product_deck and not expected_digest:
            return json_response(
                fail(
                    "PPT_ARTIFACT_INTEGRITY_ERROR",
                    "PPT Artifact 完整性元数据缺失",
                    [{"field": "artifactId", "reason": "registered SHA-256 is required"}],
                )
            )
        if expected_digest and not hmac.compare_digest(sha256(body).hexdigest(), expected_digest):
            return json_response(
                fail(
                    "PPT_ARTIFACT_INTEGRITY_ERROR",
                    "PPT Artifact 完整性校验失败",
                    [{"field": "artifactId", "reason": "registered SHA-256 mismatch"}],
                )
            )
        return BackendAppResponse(status=200, content_type=content_type, body=body)

    def _resolve_registered_ppt_file(self, value: str | None) -> Path | None:
        if not value:
            return None
        root = workspace_root(root=ROOT).resolve()
        candidate = resolve_cli_path(value, root=ROOT, workspace=root).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate if candidate.exists() and candidate.is_file() else None

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
