"""Local grading record model derived from existing evidence reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class GradingRecordStatus(StrEnum):
    WAITING_REVIEW = "WAITING_REVIEW"
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    NEEDS_REVISION = "NEEDS_REVISION"


class GradingRecordDecision(StrEnum):
    APPROVE_READY = "approve-ready"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REVISION = "needs-revision"


@dataclass
class GradingRecord:
    submissionId: str
    gradingId: str | None
    reportPath: str
    reportMode: str
    status: GradingRecordStatus
    totalScore: int
    earnedScore: int
    coveredScore: int
    missingScore: int
    coverageRatio: float
    sourceReportId: str | None = None
    taskId: str | None = None
    candidateId: str | None = None
    reviewer: str | None = None
    reviewedBy: str | None = None
    reviewedAt: str | None = None
    reviewDecision: str | None = None
    reviewReason: str | None = None
    scorePreviewStatus: str | None = None
    decisionNoteRecommendation: str | None = None
    manualReviewChecklistStatus: str | None = None
    evidenceSummary: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"grading_record_{uuid4().hex[:12]}")
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    createdAt: str = field(default_factory=utc_now)
    updatedAt: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GradingRecord":
        payload = dict(data)
        payload["status"] = GradingRecordStatus(payload["status"])
        return cls(**payload)


class GradingRecordError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def load_grading_report(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise GradingRecordError(
            "VALIDATION_ERROR",
            "评分报告不存在",
            [{"field": "report", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GradingRecordError(
            "VALIDATION_ERROR",
            "评分报告 JSON 格式错误",
            [{"field": "report", "reason": exc.msg}],
        ) from exc
    if not isinstance(payload, dict):
        raise GradingRecordError(
            "VALIDATION_ERROR",
            "评分报告格式错误",
            [{"field": "report", "reason": "root must be object"}],
        )
    return payload


def apply_grading_record_review(
    record: GradingRecord,
    *,
    reviewer: str,
    decision: str,
    reason: str | None = None,
) -> GradingRecord:
    reviewer = reviewer.strip()
    if not reviewer:
        raise GradingRecordError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    try:
        review_decision = GradingRecordDecision(decision)
    except ValueError as exc:
        raise GradingRecordError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "decision", "reason": "不支持的复核决策"}],
        ) from exc
    reason_value = reason.strip() if isinstance(reason, str) else None
    if review_decision in {GradingRecordDecision.NEEDS_EVIDENCE, GradingRecordDecision.NEEDS_REVISION} and not reason_value:
        raise GradingRecordError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reason", "reason": "该复核决策必须填写原因"}],
        )
    if record.status == GradingRecordStatus.HUMAN_APPROVED and review_decision != GradingRecordDecision.APPROVE_READY:
        raise GradingRecordError(
            "STATE_TRANSITION_ERROR",
            "Grading 评分记录状态非法流转",
            [{"field": "status", "reason": "已确认记录不能直接改为补证据或修订"}],
        )

    next_status = {
        GradingRecordDecision.APPROVE_READY: GradingRecordStatus.HUMAN_APPROVED,
        GradingRecordDecision.NEEDS_EVIDENCE: GradingRecordStatus.NEEDS_EVIDENCE,
        GradingRecordDecision.NEEDS_REVISION: GradingRecordStatus.NEEDS_REVISION,
    }[review_decision]
    now = utc_now()
    record.status = next_status
    record.reviewedBy = reviewer
    record.reviewedAt = now
    record.reviewDecision = review_decision.value
    record.reviewReason = reason_value
    record.updatedAt = now
    record.safety = {
        **record.safety,
        "humanReviewRecorded": True,
        "taskStatusChangedByRecordReview": False,
        "recordReviewCreatesNewExecution": False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "realPublish": False,
    }
    return record


def build_grading_record_from_report(
    report: dict[str, Any],
    *,
    report_path: Path,
    submission_id: str,
    trace_id: str,
    task_id: str | None = None,
    candidate_id: str | None = None,
    reviewer: str | None = None,
) -> GradingRecord:
    submission_id = submission_id.strip()
    if not submission_id:
        raise GradingRecordError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "submissionId", "reason": "缺少参数"}],
        )
    score_preview = report.get("scorePreview") if isinstance(report.get("scorePreview"), dict) else {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    score = report.get("score") if isinstance(report.get("score"), dict) else {}
    manual_checklist = report.get("manualReviewChecklist") if isinstance(report.get("manualReviewChecklist"), dict) else {}
    recommendation = (
        manual_checklist.get("decisionNoteRecommendation")
        if isinstance(manual_checklist.get("decisionNoteRecommendation"), dict)
        else {}
    )
    evidence_coverage = report.get("evidenceCoverage") if isinstance(report.get("evidenceCoverage"), dict) else {}
    total_score = _int_first(
        score_preview.get("totalScore"),
        summary.get("totalScore"),
        report.get("totalScore"),
        score.get("totalScore"),
    )
    earned_score = _int_first(
        score_preview.get("earnedScore"),
        summary.get("earnedScore"),
        report.get("earnedScore"),
        score.get("earnedScore"),
    )
    covered_score = _int_first(
        score_preview.get("coveredScore"),
        summary.get("coveredScore"),
        evidence_coverage.get("coveredScore"),
        score.get("executableScore"),
    )
    missing_score = _int_first(
        score_preview.get("missingScore"),
        max(total_score - covered_score, 0),
    )
    coverage_ratio = _float_first(
        score_preview.get("coverageRatio"),
        summary.get("coverageRatio"),
        evidence_coverage.get("coverageRatio"),
        round(covered_score / total_score, 4) if total_score else 0,
    )
    decision = str(recommendation.get("decision") or summary.get("decisionNoteRecommendation") or "")
    status = _record_status(
        score_preview_status=str(score_preview.get("status") or summary.get("scorePreviewStatus") or ""),
        ready_for_decision=score_preview.get("readyForDecisionNote"),
        decision_note_recommendation=decision,
    )
    return GradingRecord(
        submissionId=submission_id,
        gradingId=report.get("gradingId") or summary.get("gradingId"),
        reportPath=str(report_path),
        reportMode=str(report.get("mode") or "UNKNOWN_GRADING_REPORT"),
        status=status,
        totalScore=total_score,
        earnedScore=earned_score,
        coveredScore=covered_score,
        missingScore=missing_score,
        coverageRatio=coverage_ratio,
        sourceReportId=report.get("id"),
        taskId=task_id,
        candidateId=candidate_id,
        reviewer=reviewer,
        scorePreviewStatus=str(score_preview.get("status") or summary.get("scorePreviewStatus") or ""),
        decisionNoteRecommendation=decision or None,
        manualReviewChecklistStatus=str(manual_checklist.get("status") or summary.get("manualReviewChecklistStatus") or ""),
        evidenceSummary={
            "source": "grading_report.scorePreview + grading_report.evidenceCoverage",
            "checkTotal": _int_first(summary.get("checkTotal"), evidence_coverage.get("checkTotal")),
            "executedTotal": _int_first(summary.get("executed"), summary.get("executedTotal")),
            "passedTotal": _int_first(summary.get("passedCheckTotal"), summary.get("passedTotal")),
            "failedTotal": _int_first(summary.get("failedCheckTotal"), summary.get("failed")),
            "deferredTotal": _int_first(summary.get("deferredCheckTotal"), summary.get("deferred")),
            "missingEvidenceTotal": _int_first(score_preview.get("missingEvidenceTotal"), summary.get("missingEvidenceTotal")),
            "missingCheckIds": list(score_preview.get("missingCheckIds") or []),
            "controlledDocker": evidence_coverage.get("controlledDocker", {}),
            "readonlyStatic": evidence_coverage.get("readonlyStatic", {}),
            "controlledExecutionProfile": report.get("controlledExecutionProfile", {}),
            "controlledExecutionDiagnostic": report.get("controlledExecutionDiagnostic", {}),
        },
        safety={
            **(report.get("safety") if isinstance(report.get("safety"), dict) else {}),
            "derivedFromExistingReport": True,
            "recordCreatesNewExecution": False,
            "sandboxExecutedByRecord": False,
            "contestantCodeExecutedByRecord": False,
            "controlledExecutionDiagnosticCode": (
                report.get("controlledExecutionDiagnostic", {}).get("code")
                if isinstance(report.get("controlledExecutionDiagnostic"), dict)
                else None
            ),
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
        traceId=trace_id,
    )


def _record_status(
    *,
    score_preview_status: str,
    ready_for_decision: Any,
    decision_note_recommendation: str,
) -> GradingRecordStatus:
    if ready_for_decision is True or score_preview_status == "READY_FOR_HUMAN_SCORE_REVIEW":
        return GradingRecordStatus.READY_FOR_HUMAN_REVIEW
    if decision_note_recommendation == "needs-revision":
        return GradingRecordStatus.NEEDS_REVISION
    if decision_note_recommendation == "needs-evidence":
        return GradingRecordStatus.NEEDS_EVIDENCE
    return GradingRecordStatus.WAITING_REVIEW


def _int_first(*values: Any) -> int:
    for value in values:
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _float_first(*values: Any) -> float:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0
