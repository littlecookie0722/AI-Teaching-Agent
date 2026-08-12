"""Query agent publish status from platform API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .agent_api_adapter import (
    AGENT_API_BASE_URL_ENV,
    AGENT_API_TOKEN_ENV,
    AgentApiAdapterError,
    build_agent_api_runtime_config,
    build_agent_api_url,
    normalize_agent_api_max_retries,
    send_agent_api_get_json,
)
from .agent_api_contract import (
    AgentApiContractError,
    build_status_path,
    describe_agent_publish_contract,
    extract_agent_status,
    infer_agent_draft_id,
    load_agent_api_contract_config,
    suggest_publish_result_status,
)
from .agent_entity import AgentEntityStatus
from .artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationResourceType, create_operation_audit_event
from .store import JsonTaskStore

DEFAULT_AGENT_PUBLISH_STATUS_REPORT_PATH = Path("examples/output/platform-entity-import-status-report.json")


class AgentPublishStatusError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _require_text(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": field, "reason": "缺少参数"}],
        )
    return normalized


def _require_confirmed(value: bool, field: str) -> None:
    if value is not True:
        raise AgentPublishStatusError(
            "PLATFORM_IMPORT_STATUS_QUERY_CONFIRMATION_REQUIRED",
            "真实平台导入状态查询需要显式确认",
            [{"field": field, "reason": "必须显式确认"}],
        )


def _read_send_result(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "平台导入发送报告不存在",
            [{"field": "sendResult", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "平台导入发送报告不是合法 JSON",
            [{"field": "sendResult", "reason": str(exc)}],
        ) from exc
    if not isinstance(payload, dict):
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "平台导入发送报告必须是 JSON object",
            [{"field": "sendResult", "reason": "expected object"}],
        )
    if payload.get("component") != "AgentEntityImportSendResult":
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "平台导入发送报告类型不匹配",
            [{"field": "sendResult.component", "reason": "expected AgentEntityImportSendResult"}],
        )
    if payload.get("mode") != "REAL_PLATFORM_IMPORT_REQUEST_SENT":
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "平台导入发送报告模式不匹配",
            [{"field": "sendResult.mode", "reason": "expected REAL_PLATFORM_IMPORT_REQUEST_SENT"}],
        )
    return payload


def _infer_base_url_from_send_result(send_result: dict[str, Any]) -> str | None:
    request_block = send_result.get("request") if isinstance(send_result.get("request"), dict) else {}
    raw_url = str(request_block.get("url") or "").strip()
    if not raw_url:
        return None
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def query_agent_publish_status(
    store: JsonTaskStore,
    *,
    entity_id: str,
    send_result_path: Path,
    reviewer: str,
    output_path: Path,
    trace_id: str,
    agent_draft_id: str | None = None,
    status_path_template: str | None = None,
    contract_config_path: Path | None = None,
    base_url: str | None = None,
    timeout_seconds: int = 30,
    max_retries: int = 3,
    explicit_platform_query_opt_in: bool = False,
) -> dict[str, Any]:
    """Query agent publish status from the configured platform API."""
    reviewer = _require_text(reviewer, "reviewer")
    _require_confirmed(explicit_platform_query_opt_in, "explicitPlatformQueryOptIn")
    if timeout_seconds <= 0:
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "timeoutSeconds", "reason": "必须大于 0"}],
        )
    try:
        max_retries = normalize_agent_api_max_retries(max_retries)
    except AgentApiAdapterError as exc:
        raise AgentPublishStatusError(exc.code, exc.message, exc.errors) from exc

    entity = store.get_agent_entity(_require_text(entity_id, "id"))
    if entity is None:
        raise AgentPublishStatusError("NOT_FOUND", "智能体实体不存在", [{"field": "id", "reason": "未找到实体"}])

    send_result = _read_send_result(send_result_path)
    if str(send_result.get("agentEntityId") or "") != entity.id:
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "平台导入发送报告与平台实体 id 不匹配",
            [{"field": "sendResult.agentEntityId", "reason": "与 id 不一致"}],
        )

    try:
        contract_config = load_agent_api_contract_config(contract_config_path) if contract_config_path else None
        contract = describe_agent_publish_contract(entity.entityType.value, contract_config)
    except AgentApiContractError as exc:
        raise AgentPublishStatusError(exc.code, exc.message, exc.errors) from exc

    send_response = send_result.get("response") if isinstance(send_result.get("response"), dict) else {}
    send_result_contract = send_result.get("platformApiContract") if isinstance(send_result.get("platformApiContract"), dict) else {}
    if not contract_config_path and send_result_contract:
        for key in ("draftIdResponseKeys", "statusResponseKeys", "statusPathTemplate", "statusMapping"):
            if send_result_contract.get(key) and not contract.get("configApplied"):
                contract[key] = send_result_contract[key]
    resolved_draft_id = (agent_draft_id or infer_agent_draft_id(send_response, contract=contract) or "").strip()
    if not resolved_draft_id:
        raise AgentPublishStatusError(
            "VALIDATION_ERROR",
            "平台导入状态查询缺少平台 draft id",
            [{"field": "agentDraftId", "reason": "缺少参数"}],
        )

    target_endpoint = send_result.get("targetEndpoint") if isinstance(send_result.get("targetEndpoint"), dict) else {}
    target_endpoint_path = target_endpoint.get("path")
    try:
        status_path = build_status_path(
            target_endpoint_path,
            resolved_draft_id,
            status_path_template or contract.get("statusPathTemplate"),
        )
    except AgentApiContractError as exc:
        raise AgentPublishStatusError(exc.code, exc.message, exc.errors) from exc

    resolved_base_url = base_url or _infer_base_url_from_send_result(send_result)
    try:
        runtime = build_agent_api_runtime_config(base_url=resolved_base_url)
    except AgentApiAdapterError as exc:
        raise AgentPublishStatusError(exc.code, exc.message, exc.errors) from exc

    try:
        response = send_agent_api_get_json(
            base_url=runtime.base_url,
            path=status_path,
            token=runtime.token,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
    except AgentApiAdapterError as exc:
        code = "PLATFORM_IMPORT_STATUS_QUERY_FAILED" if exc.code == "PLATFORM_API_REQUEST_FAILED" else exc.code
        message = "真实平台导入状态查询失败" if exc.code == "PLATFORM_API_REQUEST_FAILED" else exc.message
        raise AgentPublishStatusError(code, message, exc.errors) from exc

    agent_status = extract_agent_status(response, contract=contract)
    suggested_import_result_status = suggest_publish_result_status(agent_status, contract)
    before_status = entity.status.value

    report = {
        "component": "AgentEntityImportStatusQuery",
        "mode": "REAL_PLATFORM_IMPORT_STATUS_QUERY",
        "agentEntityId": entity.id,
        "entityType": entity.entityType.value,
        "reviewer": reviewer,
        "sendResultPath": str(send_result_path),
        "agentDraftId": resolved_draft_id,
        "agentStatus": agent_status,
        "suggestedImportResultStatus": suggested_import_result_status,
        "platformApiContract": contract,
        "targetEndpoint": {"method": "GET", "path": status_path},
        "request": {
            "method": "GET",
            "url": build_agent_api_url(runtime.base_url, status_path),
            "maxRetries": max_retries,
        },
        "response": response,
        "localEntityStatus": {
            "before": before_status,
            "after": before_status,
            "changed": False,
        },
        "summary": {
            "localEntityStatusChanged": False,
            "manualPlatformReviewRequired": True,
        },
        "env": runtime.env,
        "safety": {
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "secretValueReturned": False,
            "mockStoreUpdated": False,
            "databaseWrittenByLocalSystem": False,
            "manualPlatformReviewRequired": True,
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
        title="Platform Entity Import Status Query",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=entity.sourceTaskId,
        source_ref=str(send_result_path),
        metadata={
            "component": "AgentEntityImportStatusQuery",
            "agentEntityId": entity.id,
            "entityType": entity.entityType.value,
            "agentDraftId": resolved_draft_id,
            "agentStatus": agent_status,
            "suggestedImportResultStatus": suggested_import_result_status,
            "requestSent": True,
            "networkAccess": True,
            "mockStoreUpdated": False,
            "databaseWrittenByLocalSystem": False,
            "realPublish": False,
        },
        mode="REAL_PLATFORM_IMPORT_STATUS_QUERY",
    )
    store.save_artifact(artifact)

    operation_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_STATUS_QUERY,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=before_status,
        after_state=before_status,
        detail={
            "component": "AgentEntityImportStatusQuery",
            "artifactId": artifact.id,
            "outputPath": str(output_path),
            "agentDraftId": resolved_draft_id,
            "agentStatus": agent_status,
            "suggestedImportResultStatus": suggested_import_result_status,
            "statusCode": response.get("statusCode"),
            "requestSent": True,
            "networkAccess": True,
            "mockStoreUpdated": False,
            "databaseWrittenByLocalSystem": False,
            "realPublish": False,
        },
    )
    operation_event.mode = "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    store.save_operation_audit_event(operation_event)

    return {
        "agentEntityImportStatusQuery": report,
        "agentEntityRecord": entity.to_dict(),
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }
