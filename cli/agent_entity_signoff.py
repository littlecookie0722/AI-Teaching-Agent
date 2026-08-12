"""Record local manual signoff for platform entity draft imports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationAuditEvent, OperationResourceType, create_operation_audit_event
from .agent_entity_readiness import build_agent_entity_readiness_report
from .store import JsonTaskStore


DEFAULT_AGENT_ENTITY_SIGNOFF_RECORD_PATH = Path("examples/output/platform-entity-signoff-record.json")


class AgentEntitySignoffError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _require_text(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentEntitySignoffError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": field, "reason": "缺少参数"}],
        )
    return normalized


def _find_readiness_item(readiness_report: dict[str, Any], entity_id: str) -> dict[str, Any] | None:
    items = readiness_report.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("agentEntityId") == entity_id:
            return item
    return None


def record_agent_entity_signoff(
    store: JsonTaskStore,
    *,
    entity_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
    comment: str | None = None,
) -> dict[str, Any]:
    reviewer = _require_text(reviewer, "reviewer")
    entity = store.get_agent_entity(_require_text(entity_id, "id"))
    if entity is None:
        raise AgentEntitySignoffError("NOT_FOUND", "平台实体不存在", [{"field": "id", "reason": "未找到实体"}])

    readiness_report = build_agent_entity_readiness_report(store, source_task_id=entity.sourceTaskId)
    result = record_agent_entity_signoff_for_entity(
        entity,
        readiness_report=readiness_report,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        comment=comment,
    )
    store.save_artifact(ArtifactRecord.from_dict(result["artifact"]))
    store.save_operation_audit_event(OperationAuditEvent.from_dict(result["operationAuditEvent"]))
    return result


def record_agent_entity_signoff_for_entity(
    entity: Any,
    *,
    readiness_report: dict[str, Any],
    reviewer: str,
    output_path: Path,
    trace_id: str,
    comment: str | None = None,
    mock_store_updated: bool = True,
    database_written_by_local_system: bool = False,
) -> dict[str, Any]:
    reviewer = _require_text(reviewer, "reviewer")
    readiness_item = _find_readiness_item(readiness_report, entity.id)
    if readiness_item is None:
        raise AgentEntitySignoffError(
            "VALIDATION_ERROR",
            "平台实体未进入导入核查报告",
            [{"field": "readiness.agentEntityId", "reason": "未找到实体核查项"}],
        )
    if readiness_item.get("signoffState") != "READY_FOR_PLATFORM_ENTITY_SIGNOFF":
        blockers = readiness_item.get("blockers") if isinstance(readiness_item.get("blockers"), list) else []
        unmatched = [
            str(check.get("id"))
            for check in readiness_item.get("manualSignoffChecklist", [])
            if isinstance(check, dict) and check.get("matched") is not True
        ]
        raise AgentEntitySignoffError(
            "PLATFORM_ENTITY_SIGNOFF_NOT_READY",
            "平台实体尚未满足人工签收条件",
            [
                {
                    "field": "readiness.signoffState",
                    "reason": str(readiness_item.get("signoffState") or "WAITING_PLATFORM_ENTITY_IMPORT_ACTIVITY"),
                },
                {
                    "field": "readiness.manualSignoffChecklist",
                    "reason": ",".join(unmatched or blockers or ["not ready"]),
                },
            ],
        )

    before_status = entity.status.value
    import_activity = (
        readiness_item.get("importActivity") if isinstance(readiness_item.get("importActivity"), dict) else {}
    )
    activity_summary = import_activity.get("summary") if isinstance(import_activity.get("summary"), dict) else {}
    manual_signoff_checklist = readiness_item.get("manualSignoffChecklist")
    if not isinstance(manual_signoff_checklist, list):
        manual_signoff_checklist = []

    report = {
        "component": "AgentEntitySignoffRecord",
        "mode": "LOCAL_PLATFORM_ENTITY_SIGNOFF_RECORD",
        "agentEntityId": entity.id,
        "entityType": entity.entityType.value,
        "sourceTaskId": entity.sourceTaskId,
        "reviewer": reviewer,
        "comment": str(comment or "").strip() or None,
        "signoffState": "PLATFORM_ENTITY_SIGNOFF_RECORDED",
        "readyStateBeforeSignoff": readiness_item.get("signoffState"),
        "manualSignoffChecklist": manual_signoff_checklist,
        "agentDraftId": activity_summary.get("latestPlatformDraftId"),
        "agentStatus": activity_summary.get("latestPlatformStatus"),
        "localEntityStatus": {
            "before": before_status,
            "after": before_status,
            "changed": False,
        },
        "summary": {
            "signoffRecorded": True,
            "readyForAgentEntitySignoff": True,
            "allChecklistMatched": all(bool(check.get("matched")) for check in manual_signoff_checklist),
            "agentSideReviewed": bool(activity_summary.get("agentSideReviewed")),
            "acceptedForDraft": bool(activity_summary.get("acceptedForDraft")),
            "localEntityStatusChanged": False,
            "taskStatusChanged": False,
            "realPublish": False,
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
        title="Platform Entity Signoff Record",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=entity.sourceTaskId,
        source_ref=entity.id,
        metadata={
            "component": "AgentEntitySignoffRecord",
            "agentEntityId": entity.id,
            "entityType": entity.entityType.value,
            "sourceTaskId": entity.sourceTaskId,
            "agentDraftId": activity_summary.get("latestPlatformDraftId"),
            "agentStatus": activity_summary.get("latestPlatformStatus"),
            "signoffRecorded": True,
            "readyForAgentEntitySignoff": True,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "mockStoreUpdated": mock_store_updated,
            "databaseWrittenByLocalSystem": database_written_by_local_system,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
        mode="LOCAL_PLATFORM_ENTITY_SIGNOFF_RECORD",
    )

    operation_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_SIGNOFF_RECORD,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=before_status,
        after_state="PLATFORM_ENTITY_SIGNOFF_RECORDED",
        detail={
            "component": "AgentEntitySignoffRecord",
            "artifactId": artifact.id,
            "outputPath": str(output_path),
            "agentDraftId": activity_summary.get("latestPlatformDraftId"),
            "agentStatus": activity_summary.get("latestPlatformStatus"),
            "signoffRecorded": True,
            "readyForAgentEntitySignoff": True,
            "localEntityStatusChanged": False,
            "requestSent": False,
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
    operation_event.mode = "LOCAL_PLATFORM_ENTITY_SIGNOFF_RECORD"

    return {
        "agentEntitySignoffRecord": report,
        "agentEntityRecord": entity.to_dict(),
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }
