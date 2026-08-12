"""Record manually reviewed platform draft import results."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from .ai_task import utc_now
from .artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationAuditEvent, OperationResourceType, create_operation_audit_event
from .agent_entity import AgentEntityRecord, AgentEntityStatus
from .store import JsonTaskStore


DEFAULT_AGENT_PUBLISH_RESULT_PATH = Path("examples/output/platform-entity-import-result-record.json")


class AgentPublishResultStatus(StrEnum):
    PENDING_MANUAL_PLATFORM_REVIEW = "PENDING_MANUAL_PLATFORM_REVIEW"
    ACCEPTED_FOR_DRAFT = "ACCEPTED_FOR_DRAFT"
    REJECTED_BY_PLATFORM = "REJECTED_BY_PLATFORM"
    FAILED = "FAILED"


class AgentPublishResultError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _require_text(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": field, "reason": "缺少参数"}],
        )
    return normalized


def _read_send_result(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入发送报告不存在",
            [{"field": "sendResult", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入发送报告不是合法 JSON",
            [{"field": "sendResult", "reason": str(exc)}],
        ) from exc
    if not isinstance(payload, dict):
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入发送报告必须是 JSON object",
            [{"field": "sendResult", "reason": "expected object"}],
        )
    if payload.get("component") != "AgentEntityImportSendResult":
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入发送报告类型不匹配",
            [{"field": "sendResult.component", "reason": "expected AgentEntityImportSendResult"}],
        )
    if payload.get("mode") != "REAL_PLATFORM_IMPORT_REQUEST_SENT":
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入发送报告模式不匹配",
            [{"field": "sendResult.mode", "reason": "expected REAL_PLATFORM_IMPORT_REQUEST_SENT"}],
        )
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    if safety.get("requestSent") is not True:
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入结果登记需要已发送请求报告",
            [{"field": "sendResult.safety.requestSent", "reason": "expected true"}],
        )
    return payload


def _infer_agent_draft_id(send_result: dict[str, Any]) -> str | None:
    response = send_result.get("response") if isinstance(send_result.get("response"), dict) else {}
    body = response.get("body") if isinstance(response.get("body"), dict) else {}
    parsed = body.get("json")
    if not isinstance(parsed, dict):
        return None
    for key in ("draftImportId", "draftId", "importId", "id"):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _entity_status_for_platform_status(platform_status: AgentPublishResultStatus) -> AgentEntityStatus:
    if platform_status == AgentPublishResultStatus.PENDING_MANUAL_PLATFORM_REVIEW:
        return AgentEntityStatus.REAL_IMPORT_PENDING_REVIEW
    if platform_status == AgentPublishResultStatus.ACCEPTED_FOR_DRAFT:
        return AgentEntityStatus.REAL_IMPORT_DRAFT_ACCEPTED
    if platform_status == AgentPublishResultStatus.REJECTED_BY_PLATFORM:
        return AgentEntityStatus.REAL_IMPORT_REJECTED
    return AgentEntityStatus.REAL_IMPORT_FAILED


def record_agent_entity_publish_result(
    store: JsonTaskStore,
    *,
    entity_id: str,
    send_result_path: Path,
    reviewer: str,
    platform_status: str,
    output_path: Path,
    trace_id: str,
    agent_draft_id: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    entity = store.get_agent_entity(_require_text(entity_id, "id"))
    if entity is None:
        raise AgentPublishResultError("NOT_FOUND", "平台实体不存在", [{"field": "id", "reason": "未找到实体"}])
    result = record_agent_entity_publish_result_for_entity(
        entity,
        send_result_path=send_result_path,
        reviewer=reviewer,
        platform_status=platform_status,
        output_path=output_path,
        trace_id=trace_id,
        agent_draft_id=agent_draft_id,
        message=message,
    )
    store.save_artifact(ArtifactRecord.from_dict(result["artifact"]))
    store.save_agent_entity(entity)
    store.save_operation_audit_event(OperationAuditEvent.from_dict(result["operationAuditEvent"]))
    return result


def record_agent_entity_publish_result_for_entity(
    entity: AgentEntityRecord,
    *,
    send_result_path: Path,
    reviewer: str,
    platform_status: str,
    output_path: Path,
    trace_id: str,
    agent_draft_id: str | None = None,
    message: str | None = None,
    mock_store_updated: bool = True,
    database_written_by_local_system: bool = False,
) -> dict[str, Any]:
    reviewer = _require_text(reviewer, "reviewer")
    send_result = _read_send_result(send_result_path)
    if str(send_result.get("agentEntityId") or "") != entity.id:
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入发送报告与平台实体 id 不匹配",
            [{"field": "sendResult.agentEntityId", "reason": "与 id 不一致"}],
        )
    try:
        normalized_platform_status = AgentPublishResultStatus(platform_status)
    except ValueError as exc:
        raise AgentPublishResultError(
            "VALIDATION_ERROR",
            "平台导入状态不支持",
            [{"field": "agentStatus", "reason": "不在允许枚举中"}],
        ) from exc

    before_status = entity.status.value
    after_status = _entity_status_for_platform_status(normalized_platform_status)
    agent_draft_id = (agent_draft_id or _infer_agent_draft_id(send_result) or "").strip() or None
    response = send_result.get("response") if isinstance(send_result.get("response"), dict) else {}
    source_request = send_result.get("request") if isinstance(send_result.get("request"), dict) else {}
    target_endpoint = send_result.get("targetEndpoint") if isinstance(send_result.get("targetEndpoint"), dict) else {}
    platform_side_reviewed = normalized_platform_status != AgentPublishResultStatus.PENDING_MANUAL_PLATFORM_REVIEW

    report = {
        "component": "AgentEntityImportResultRecord",
        "mode": "LOCAL_PLATFORM_IMPORT_RESULT_RECORD",
        "agentEntityId": entity.id,
        "entityType": entity.entityType.value,
        "reviewer": reviewer,
        "sendResultPath": str(send_result_path),
        "agentDraftId": agent_draft_id,
        "agentStatus": normalized_platform_status.value,
        "message": str(message or "").strip() or None,
        "localEntityStatus": {
            "before": before_status,
            "after": after_status.value,
        },
        "sourceSend": {
            "statusCode": response.get("statusCode"),
            "targetEndpoint": target_endpoint,
            "idempotencyKey": source_request.get("idempotencyKey"),
            "responseOk": response.get("ok"),
        },
        "summary": {
            "sourceRequestSent": True,
            "agentSideReviewed": platform_side_reviewed,
            "pendingManualPlatformReview": normalized_platform_status
            == AgentPublishResultStatus.PENDING_MANUAL_PLATFORM_REVIEW,
            "acceptedForDraft": normalized_platform_status == AgentPublishResultStatus.ACCEPTED_FOR_DRAFT,
            "rejectedByPlatform": normalized_platform_status == AgentPublishResultStatus.REJECTED_BY_PLATFORM,
            "failed": normalized_platform_status == AgentPublishResultStatus.FAILED,
        },
        "safety": {
            "readOnlyToPlatform": True,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "mockStoreUpdated": mock_store_updated,
            "databaseWrittenByLocalSystem": database_written_by_local_system,
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
        title="Platform Entity Import Result Record",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=entity.sourceTaskId,
        source_ref=str(send_result_path),
        metadata={
            "component": "AgentEntityImportResultRecord",
            "agentEntityId": entity.id,
            "entityType": entity.entityType.value,
            "agentDraftId": agent_draft_id,
            "agentStatus": normalized_platform_status.value,
            "sourceRequestSent": True,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "mockStoreUpdated": mock_store_updated,
            "databaseWrittenByLocalSystem": database_written_by_local_system,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
        mode="LOCAL_PLATFORM_IMPORT_RESULT_RECORD",
    )

    entity.status = after_status
    entity.updatedAt = utc_now()

    operation_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_RESULT_RECORD,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=before_status,
        after_state=after_status.value,
        detail={
            "component": "AgentEntityImportResultRecord",
            "artifactId": artifact.id,
            "outputPath": str(output_path),
            "sourceSendResultPath": str(send_result_path),
            "agentDraftId": agent_draft_id,
            "agentStatus": normalized_platform_status.value,
            "agentSideReviewed": platform_side_reviewed,
            "acceptedForDraft": normalized_platform_status == AgentPublishResultStatus.ACCEPTED_FOR_DRAFT,
            "rejectedByPlatform": normalized_platform_status == AgentPublishResultStatus.REJECTED_BY_PLATFORM,
            "failed": normalized_platform_status == AgentPublishResultStatus.FAILED,
            "requestSent": False,
            "sourceRequestSent": True,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "mockStoreUpdated": mock_store_updated,
            "databaseWrittenByLocalSystem": database_written_by_local_system,
            "manualPlatformReviewRequired": True,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    )
    operation_event.mode = "LOCAL_PLATFORM_IMPORT_RESULT_RECORD"
    return {
        "agentEntityImportResultRecord": report,
        "agentEntityRecord": entity.to_dict(),
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }
