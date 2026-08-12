"""Local review decision note model for grading evidence review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationResourceType, create_operation_audit_event
from .review_detail import build_review_detail
from .store import JsonTaskStore


ALLOWED_REVIEW_DECISION_NOTES = ("approve-ready", "needs-revision", "needs-evidence")


class ReviewDecisionNoteError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _default_output_path(task_id: str) -> Path:
    return Path("examples/output") / f"{task_id}-review-decision-note.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _review_decision_hints_from_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    if not detail:
        return {}
    merged = detail.get("mergedGradingEvidence")
    if not isinstance(merged, dict):
        return {}
    hints = merged.get("reviewDecisionHints")
    return hints if isinstance(hints, dict) else {}


def create_review_decision_note(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    decision: str,
    reason: str | None = None,
    output_path: Path | None = None,
    trace_id: str,
) -> dict[str, Any]:
    reviewer = reviewer.strip()
    decision = decision.strip()
    reason = (reason or "").strip()
    if not reviewer:
        raise ReviewDecisionNoteError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    if decision not in ALLOWED_REVIEW_DECISION_NOTES:
        raise ReviewDecisionNoteError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "decision", "reason": "必须是 approve-ready、needs-revision 或 needs-evidence"}],
        )
    if decision in {"needs-revision", "needs-evidence"} and not reason:
        raise ReviewDecisionNoteError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reason", "reason": "needs-revision / needs-evidence 必须填写原因"}],
        )

    task = store.get(task_id)
    if task is None:
        raise ReviewDecisionNoteError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )

    before_status = task.status.value
    detail_before = build_review_detail(store, task_id)
    review_decision_hints = _review_decision_hints_from_detail(detail_before)
    output = output_path or _default_output_path(task_id)

    operation_event = create_operation_audit_event(
        action=OperationAction.REVIEW_DECISION_NOTE_RECORD,
        resource_type=OperationResourceType.AI_TASK,
        resource_id=task_id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=before_status,
        after_state=before_status,
        detail={
            "component": "ReviewDecisionNote",
            "decision": decision,
            "reason": reason,
            "outputPath": str(output),
            "reviewDecisionHintsSnapshot": review_decision_hints,
            "statusChanged": False,
            "taskStatusUnchanged": True,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
        },
    )
    store.save_operation_audit_event(operation_event)

    note = {
        "id": f"review_decision_note_{uuid4().hex[:12]}",
        "component": "ReviewDecisionNote",
        "taskId": task_id,
        "reviewer": reviewer,
        "decision": decision,
        "reason": reason,
        "taskStatusBefore": before_status,
        "taskStatusAfter": before_status,
        "statusChanged": False,
        "taskStatusUnchanged": True,
        "source": "reviewDetail.mergedGradingEvidence.reviewDecisionHints",
        "reviewDecisionHintsSnapshot": review_decision_hints,
        "operationAuditEvent": operation_event.to_dict(),
        "safety": {
            "readOnlyDecisionRecord": True,
            "statusChanged": False,
            "taskStatusUnchanged": True,
            "newLlmRequestSent": False,
            "realLlmCalled": False,
            "sandboxExecutedByDecisionNote": False,
            "contestantCodeExecuted": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }
    _write_json(output, note)

    artifact = create_artifact_record(
        kind=ArtifactKind.REVIEW_DECISION_NOTE,
        path=str(output),
        title=f"Review decision note for {task_id}",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=task_id,
        source_ref=task.finalResultPath or task.inputRef,
        metadata={
            "reportType": "REVIEW_DECISION_NOTE",
            "decision": decision,
            "reviewer": reviewer,
            "operationAuditEventId": operation_event.id,
            "statusChanged": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    )
    store.save_artifact(artifact)
    note["artifact"] = artifact.to_dict()
    _write_json(output, note)

    detail_after = build_review_detail(store, task_id)
    return {
        "decisionNote": note,
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
        "reviewDetail": detail_after,
    }
