"""Send a reviewed platform import dry-run payload to a configured platform API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationResourceType, create_operation_audit_event
from .agent_api_adapter import (
    AGENT_API_BASE_URL_ENV,
    AGENT_API_TOKEN_ENV,
    AgentApiAdapterError,
    build_agent_api_runtime_config,
    build_agent_api_url,
    normalize_agent_api_max_retries,
    send_agent_api_post_json,
)
from .store import JsonTaskStore


DEFAULT_AGENT_PUBLISH_REPORT_PATH = Path("examples/output/platform-entity-import-send-report.json")


class AgentPublishError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _require_text(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": field, "reason": "缺少参数"}],
        )
    return normalized


def _require_confirmed(value: bool, field: str) -> None:
    if value is not True:
        raise AgentPublishError(
            "PLATFORM_IMPORT_SEND_CONFIRMATION_REQUIRED",
            "真实平台导入请求需要显式确认",
            [{"field": field, "reason": "必须显式确认"}],
        )


def _read_dry_run(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 报告不存在",
            [{"field": "dryRun", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 报告不是合法 JSON",
            [{"field": "dryRun", "reason": str(exc)}],
        ) from exc
    if not isinstance(payload, dict):
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 报告必须是 JSON object",
            [{"field": "dryRun", "reason": "expected object"}],
        )
    return payload


def _validate_dry_run(payload: dict[str, Any]) -> None:
    if payload.get("component") != "AgentEntityImportDryRun":
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 类型不匹配",
            [{"field": "dryRun.component", "reason": "expected AgentEntityImportDryRun"}],
        )
    if payload.get("mode") != "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY":
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 模式不匹配",
            [{"field": "dryRun.mode", "reason": "expected REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"}],
        )
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else {}
    if safety.get("dryRunOnly") is not True or safety.get("requestSent") is not False:
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 安全标记不满足发送前要求",
            [{"field": "dryRun.safety", "reason": "expected dryRunOnly=true and requestSent=false"}],
        )
    if validation.get("sourceMockImportPresent") is not True:
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入发送前需要已有本地 mock-import 记录",
            [{"field": "dryRun.validation.sourceMockImportPresent", "reason": "expected true"}],
        )
    endpoint = payload.get("targetEndpoint") if isinstance(payload.get("targetEndpoint"), dict) else {}
    if endpoint.get("method") != "POST" or not isinstance(endpoint.get("path"), str):
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 缺少 POST targetEndpoint",
            [{"field": "dryRun.targetEndpoint", "reason": "expected POST path"}],
        )
    if not isinstance(payload.get("requestPreview"), dict):
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 缺少 requestPreview",
            [{"field": "dryRun.requestPreview", "reason": "expected object"}],
        )


def agent_internal_publish(
    store: JsonTaskStore,
    *,
    entity_id: str | None = None,
    dry_run_path: Path,
    reviewer: str,
    output_path: Path,
    trace_id: str,
    base_url: str | None = None,
    timeout_seconds: int = 30,
    max_retries: int | str | None = 0,
    explicit_platform_call_opt_in: bool = False,
    confirm_dry_run_reviewed: bool = False,
    confirm_manual_platform_review: bool = False,
    confirm_no_auto_publish: bool = False,
) -> dict[str, Any]:
    reviewer = _require_text(reviewer, "reviewer")
    _require_confirmed(explicit_platform_call_opt_in, "explicitPlatformCallOptIn")
    _require_confirmed(confirm_dry_run_reviewed, "confirmDryRunReviewed")
    _require_confirmed(confirm_manual_platform_review, "confirmManualPlatformReview")
    _require_confirmed(confirm_no_auto_publish, "confirmNoAutoPublish")
    if timeout_seconds <= 0:
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "timeoutSeconds", "reason": "必须大于 0"}],
        )
    try:
        max_retries = normalize_agent_api_max_retries(max_retries)
    except AgentApiAdapterError as exc:
        raise AgentPublishError(exc.code, exc.message, exc.errors) from exc

    dry_run = _read_dry_run(dry_run_path)
    _validate_dry_run(dry_run)
    expected_entity_id = str(entity_id or "").strip()
    dry_run_entity_id = str(dry_run.get("agentEntityId") or "")
    if expected_entity_id and dry_run_entity_id != expected_entity_id:
        raise AgentPublishError(
            "VALIDATION_ERROR",
            "真实平台导入 dry-run 与平台实体 id 不匹配",
            [{"field": "id", "reason": "与 dryRun.agentEntityId 不一致"}],
        )

    try:
        runtime = build_agent_api_runtime_config(base_url=base_url)
    except AgentApiAdapterError as exc:
        raise AgentPublishError(exc.code, exc.message, exc.errors) from exc
    endpoint = dry_run["targetEndpoint"]
    request_preview = dry_run["requestPreview"]
    request_body = dry_run.get("requestBody") if isinstance(dry_run.get("requestBody"), dict) else request_preview
    request_body_mapping = dry_run.get("requestBodyMapping") if isinstance(dry_run.get("requestBodyMapping"), dict) else {
        "mode": "DEFAULT_INTERNAL_DTO",
        "applied": False,
    }
    url = build_agent_api_url(runtime.base_url, endpoint["path"])
    try:
        response = send_agent_api_post_json(
            base_url=runtime.base_url,
            path=endpoint["path"],
            token=runtime.token,
            body=request_body,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
    except AgentApiAdapterError as exc:
        code = "PLATFORM_IMPORT_SEND_FAILED" if exc.code == "PLATFORM_API_REQUEST_FAILED" else exc.code
        message = "真实平台导入请求失败" if exc.code == "PLATFORM_API_REQUEST_FAILED" else exc.message
        raise AgentPublishError(code, message, exc.errors) from exc
    response_accepted = bool(response["ok"])
    agent_entity_id = str(dry_run.get("agentEntityId") or "")

    report = {
        "component": "AgentEntityImportSendResult",
        "mode": "REAL_PLATFORM_IMPORT_REQUEST_SENT",
        "agentEntityId": agent_entity_id,
        "entityType": dry_run.get("entityType"),
        "reviewer": reviewer,
        "dryRunPath": str(dry_run_path),
        "targetEndpoint": endpoint,
        "platformApiContract": dry_run.get("platformApiContract"),
        "requestBodyMapping": request_body_mapping,
        "request": {
            "method": "POST",
            "url": url,
            "idempotencyKey": request_body.get("idempotencyKey") or request_preview.get("idempotencyKey"),
            "entityType": request_body.get("entityType") or request_preview.get("entityType"),
            "bodySource": "requestBody" if isinstance(dry_run.get("requestBody"), dict) else "requestPreview",
            "maxRetries": max_retries,
        },
        "response": response,
        "env": runtime.env,
        "safety": {
            "dryRunReviewed": True,
            "manualPlatformReviewRequired": True,
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": False,
            "publishAttempted": True,
            "publishAccepted": response_accepted,
            "realAgentImportAttempted": True,
            "realAgentImportAccepted": response_accepted,
            "autoPublishAllowed": False,
            "realPublish": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
        "traceId": trace_id,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path=str(output_path),
        title="Platform Entity Import Send Result",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=dry_run.get("requestPreview", {}).get("source", {}).get("sourceTaskId"),
        source_ref=str(dry_run_path),
        metadata={
            "component": "AgentEntityImportSendResult",
            "agentEntityId": agent_entity_id,
            "entityType": dry_run.get("entityType"),
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": False,
            "publishAttempted": True,
            "publishAccepted": response_accepted,
            "realPublish": False,
            "attempts": response.get("attempts"),
            "maxRetries": max_retries,
        },
        mode="REAL_PLATFORM_IMPORT_REQUEST_SENT",
    )
    store.save_artifact(artifact)
    operation_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_SEND,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=agent_entity_id,
        actor=reviewer,
        trace_id=trace_id,
        before_state="IMPORT_DRY_RUN_PREPARED",
        after_state="REAL_PLATFORM_IMPORT_REQUEST_SENT",
        detail={
            "component": "AgentEntityImportSendResult",
            "artifactId": artifact.id,
            "outputPath": str(output_path),
            "targetEndpoint": endpoint,
            "statusCode": response["statusCode"],
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": False,
            "publishAttempted": True,
            "publishAccepted": response_accepted,
            "realPublish": False,
            "attempts": response.get("attempts"),
            "maxRetries": max_retries,
        },
    )
    operation_event.mode = "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    store.save_operation_audit_event(operation_event)
    return {
        "agentEntityImportSendResult": report,
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }
