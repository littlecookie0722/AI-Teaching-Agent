"""Record local final human review decisions before any platform publish."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationAuditEvent, OperationResourceType, create_operation_audit_event
from .agent_entity_readiness import build_agent_entity_readiness_report
from .store import JsonTaskStore


DEFAULT_AGENT_ENTITY_PUBLISH_REVIEW_DECISION_PATH = Path(
    "examples/output/platform-entity-final-publish-review-decision.json"
)
APPROVED_FOR_PUBLISH_PLANNING = "APPROVED_FOR_PUBLISH_PLANNING"
NEEDS_REVISION = "NEEDS_REVISION"
ALLOWED_FINAL_PUBLISH_REVIEW_DECISIONS = {APPROVED_FOR_PUBLISH_PLANNING, NEEDS_REVISION}


class AgentEntityPublishReviewError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _require_text(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentEntityPublishReviewError(
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


def _require_confirmations(
    *,
    confirm_no_auto_publish: bool,
    confirm_no_real_publish: bool,
    confirm_final_human_review: bool,
) -> None:
    missing: list[dict[str, str]] = []
    if not confirm_no_auto_publish:
        missing.append({"field": "confirmNoAutoPublish", "reason": "必须确认不会自动发布"})
    if not confirm_no_real_publish:
        missing.append({"field": "confirmNoRealPublish", "reason": "必须确认不会执行真实发布"})
    if not confirm_final_human_review:
        missing.append({"field": "confirmFinalHumanReview", "reason": "必须确认这是人工最终复核结论"})
    if missing:
        raise AgentEntityPublishReviewError("VALIDATION_ERROR", "缺少最终复核确认", missing)


def record_agent_entity_final_publish_review_decision(
    store: JsonTaskStore,
    *,
    entity_id: str,
    reviewer: str,
    decision: str,
    output_path: Path,
    trace_id: str,
    comment: str | None = None,
    confirm_no_auto_publish: bool = False,
    confirm_no_real_publish: bool = False,
    confirm_final_human_review: bool = False,
) -> dict[str, Any]:
    reviewer = _require_text(reviewer, "reviewer")
    decision = _require_text(decision, "decision").upper()
    if decision not in ALLOWED_FINAL_PUBLISH_REVIEW_DECISIONS:
        raise AgentEntityPublishReviewError(
            "VALIDATION_ERROR",
            "非法最终复核结论",
            [{"field": "decision", "reason": "必须是 APPROVED_FOR_PUBLISH_PLANNING 或 NEEDS_REVISION"}],
        )
    _require_confirmations(
        confirm_no_auto_publish=confirm_no_auto_publish,
        confirm_no_real_publish=confirm_no_real_publish,
        confirm_final_human_review=confirm_final_human_review,
    )

    entity = store.get_agent_entity(_require_text(entity_id, "id"))
    if entity is None:
        raise AgentEntityPublishReviewError("NOT_FOUND", "平台实体不存在", [{"field": "id", "reason": "未找到实体"}])

    readiness_report = build_agent_entity_readiness_report(store, source_task_id=entity.sourceTaskId)
    result = record_agent_entity_final_publish_review_decision_for_entity(
        entity,
        readiness_report=readiness_report,
        reviewer=reviewer,
        decision=decision,
        output_path=output_path,
        trace_id=trace_id,
        comment=comment,
        confirm_no_auto_publish=confirm_no_auto_publish,
        confirm_no_real_publish=confirm_no_real_publish,
        confirm_final_human_review=confirm_final_human_review,
    )
    store.save_artifact(ArtifactRecord.from_dict(result["artifact"]))
    store.save_operation_audit_event(OperationAuditEvent.from_dict(result["operationAuditEvent"]))
    return result


def record_agent_entity_final_publish_review_decision_for_entity(
    entity: Any,
    *,
    readiness_report: dict[str, Any],
    reviewer: str,
    decision: str,
    output_path: Path,
    trace_id: str,
    comment: str | None = None,
    confirm_no_auto_publish: bool = False,
    confirm_no_real_publish: bool = False,
    confirm_final_human_review: bool = False,
    database_written_by_local_system: bool = False,
) -> dict[str, Any]:
    reviewer = _require_text(reviewer, "reviewer")
    decision = _require_text(decision, "decision").upper()
    if decision not in ALLOWED_FINAL_PUBLISH_REVIEW_DECISIONS:
        raise AgentEntityPublishReviewError(
            "VALIDATION_ERROR",
            "非法最终复核结论",
            [{"field": "decision", "reason": "必须是 APPROVED_FOR_PUBLISH_PLANNING 或 NEEDS_REVISION"}],
        )
    _require_confirmations(
        confirm_no_auto_publish=confirm_no_auto_publish,
        confirm_no_real_publish=confirm_no_real_publish,
        confirm_final_human_review=confirm_final_human_review,
    )

    readiness_item = _find_readiness_item(readiness_report, entity.id)
    if readiness_item is None:
        raise AgentEntityPublishReviewError(
            "VALIDATION_ERROR",
            "平台实体未进入导入核查报告",
            [{"field": "readiness.agentEntityId", "reason": "未找到实体核查项"}],
        )
    checklist = readiness_item.get("postSignoffPrePublishChecklist")
    if not isinstance(checklist, dict):
        checklist = {}
    if checklist.get("status") != "READY_FOR_FINAL_HUMAN_PUBLISH_REVIEW":
        raise AgentEntityPublishReviewError(
            "FINAL_PUBLISH_REVIEW_NOT_READY",
            "平台实体尚未满足最终人工复核条件",
            [
                {
                    "field": "postSignoffPrePublishChecklist.status",
                    "reason": str(checklist.get("status") or "NEEDS_MANUAL_REVIEW"),
                }
            ],
        )

    entity_specific_review_focus = checklist.get("entitySpecificReviewFocus")
    if not isinstance(entity_specific_review_focus, dict):
        entity_specific_review_focus = {}
    approved = decision == APPROVED_FOR_PUBLISH_PLANNING
    needs_revision = decision == NEEDS_REVISION
    before_status = entity.status.value
    report = {
        "component": "FinalPublishReviewDecision",
        "mode": "LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION",
        "agentEntityId": entity.id,
        "entityType": entity.entityType.value,
        "sourceTaskId": entity.sourceTaskId,
        "reviewer": reviewer,
        "decision": decision,
        "comment": str(comment or "").strip() or None,
        "decisionState": decision,
        "postSignoffPrePublishStatus": checklist.get("status"),
        "entitySpecificReviewFocus": entity_specific_review_focus,
        "localEntityStatus": {"before": before_status, "after": before_status, "changed": False},
        "summary": {
            "decisionRecorded": True,
            "approvedForPublishPlanning": approved,
            "needsRevision": needs_revision,
            "realPublish": False,
            "autoPublishAllowed": False,
            "publishExecuted": False,
            "localEntityStatusChanged": False,
            "taskStatusChanged": False,
        },
        "safety": {
            "readOnlyToPlatform": True,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": database_written_by_local_system,
            "autoPublishAllowed": False,
            "realPublish": False,
            "publishExecuted": False,
            "requiresSeparatePublishAuthorization": True,
            "answerVisibleToCandidate": False,
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
        title="Platform Entity Final Publish Review Decision",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=entity.sourceTaskId,
        source_ref=entity.id,
        metadata={
            "component": "FinalPublishReviewDecision",
            "agentEntityId": entity.id,
            "entityType": entity.entityType.value,
            "sourceTaskId": entity.sourceTaskId,
            "decision": decision,
            "decisionRecorded": True,
            "approvedForPublishPlanning": approved,
            "needsRevision": needs_revision,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": database_written_by_local_system,
            "autoPublishAllowed": False,
            "realPublish": False,
            "publishExecuted": False,
        },
        mode="LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION",
    )

    operation_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_FINAL_PUBLISH_REVIEW_DECISION,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=before_status,
        after_state=decision,
        detail={
            "component": "FinalPublishReviewDecision",
            "artifactId": artifact.id,
            "outputPath": str(output_path),
            "decision": decision,
            "approvedForPublishPlanning": approved,
            "needsRevision": needs_revision,
            "localEntityStatusChanged": False,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": database_written_by_local_system,
            "autoPublishAllowed": False,
            "realPublish": False,
            "publishExecuted": False,
            "requiresSeparatePublishAuthorization": True,
        },
    )
    operation_event.mode = "LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION"

    return {
        "finalPublishReviewDecision": report,
        "agentEntityRecord": entity.to_dict(),
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }
