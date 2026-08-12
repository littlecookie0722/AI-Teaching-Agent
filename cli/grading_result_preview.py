"""Build a read-only grading result preview from an existing grading report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact import ArtifactKind
from .store import JsonTaskStore


DEFAULT_GRADING_RESULT_PREVIEW_PATH = Path("examples/output/grading-result-preview.json")


class GradingResultPreviewError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def _read_report(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise GradingResultPreviewError(
            "VALIDATION_ERROR",
            "评分报告不存在",
            [{"field": "report", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GradingResultPreviewError(
            "VALIDATION_ERROR",
            "评分报告 JSON 格式错误",
            [{"field": "report", "reason": str(exc)}],
        ) from exc
    if not isinstance(payload, dict):
        raise GradingResultPreviewError(
            "VALIDATION_ERROR",
            "评分报告 JSON 格式错误",
            [{"field": "report", "reason": "root must be object"}],
        )
    return payload


def _report_score(report: dict[str, Any]) -> dict[str, Any]:
    score = report.get("score") if isinstance(report.get("score"), dict) else {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    earned = score.get("earnedScore", report.get("earnedScore", summary.get("earnedScore", 0)))
    total = score.get("totalScore", report.get("totalScore", summary.get("totalScore", 0)))
    try:
        earned_value = float(earned or 0)
    except (TypeError, ValueError):
        earned_value = 0.0
    try:
        total_value = float(total or 0)
    except (TypeError, ValueError):
        total_value = 0.0
    passed = report.get("passed")
    if passed is None:
        passed = bool(total_value and earned_value >= total_value)
    return {
        "earnedScore": earned_value,
        "totalScore": total_value,
        "scoreRate": round(earned_value / total_value, 4) if total_value else 0,
        "passed": bool(passed),
    }


def _report_summary(report: dict[str, Any]) -> dict[str, Any]:
    if isinstance(report.get("summary"), dict):
        summary = dict(report["summary"])
    elif isinstance(report.get("executionSummary"), dict):
        summary = dict(report["executionSummary"])
    elif isinstance(report.get("checkSummary"), dict):
        summary = dict(report["checkSummary"])
    else:
        summary = {}
    return {
        "checkTotal": int(summary.get("checkTotal", summary.get("total", 0)) or 0),
        "executed": int(summary.get("executed", summary.get("executedTotal", 0)) or 0),
        "passed": _summary_count(summary, "passedCheckTotal", "passedTotal", "passed"),
        "failed": _summary_count(summary, "failedCheckTotal", "failedTotal", "failed"),
        "deferred": _summary_count(summary, "deferredCheckTotal", "deferredTotal", "deferred"),
        "manualReviewRequired": bool(summary.get("manualReviewRequired", True)),
    }


def _summary_count(summary: dict[str, Any], *keys: str) -> int:
    for key in keys:
        if key not in summary:
            continue
        value = summary.get(key)
        if isinstance(value, bool):
            continue
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            continue
    return 0


def _evidence_items(report: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    if isinstance(report.get("checkEvidenceReviewItems"), list):
        source_items = report["checkEvidenceReviewItems"]
    elif isinstance(report.get("executionMatrix"), dict) and isinstance(report["executionMatrix"].get("items"), list):
        source_items = report["executionMatrix"]["items"]
    elif isinstance(report.get("manualReviewChecklist"), dict) and isinstance(report["manualReviewChecklist"].get("items"), list):
        source_items = report["manualReviewChecklist"]["items"]
    elif isinstance(report.get("checks"), list):
        source_items = report["checks"]
    else:
        source_items = []
    items: list[dict[str, Any]] = []
    for item in source_items[:limit]:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "checkId": item.get("checkId") or item.get("id"),
                "checkType": item.get("checkType") or item.get("type"),
                "status": item.get("status"),
                "passed": item.get("passed") if "passed" in item else (item.get("selectedEvidence") or {}).get("passed"),
                "score": item.get("score"),
                "earnedScore": item.get("earnedScore")
                if "earnedScore" in item
                else (item.get("selectedEvidence") or {}).get("earnedScore"),
                "evidenceSourceKind": item.get("evidenceSourceKind")
                or item.get("selectedEvidenceMode")
                or (item.get("selectedEvidence") or {}).get("mode")
                or item.get("source"),
                "exitCode": item.get("exitCode") if "exitCode" in item else (item.get("selectedEvidence") or {}).get("exitCode"),
                "stdoutTail": item.get("stdoutTail")
                if "stdoutTail" in item
                else (item.get("selectedEvidence") or {}).get("stdoutTail"),
                "stderrTail": item.get("stderrTail")
                if "stderrTail" in item
                else (item.get("selectedEvidence") or {}).get("stderrTail"),
                "filesInspected": item.get("filesInspected")
                if "filesInspected" in item
                else (item.get("selectedEvidence") or {}).get("filesInspected", []),
                "errorCode": item.get("errorCode") if "errorCode" in item else (item.get("selectedEvidence") or {}).get("errorCode"),
                "errorReason": item.get("errorReason")
                if "errorReason" in item
                else (item.get("selectedEvidence") or {}).get("errorReason"),
                "reason": item.get("reason"),
                "recommendedAction": item.get("recommendedAction") or item.get("recommendedNextEvidence"),
                "manualReviewRequired": bool(item.get("manualReviewRequired", True)),
            }
        )
    return items


def _safety(report: dict[str, Any]) -> dict[str, Any]:
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    return {
        "readOnly": True,
        "sourceReportModified": False,
        "sandboxExecutedByPreview": False,
        "contestantCodeExecutedByPreview": False,
        "commandExecutedByPreview": False,
        "networkAccessByPreview": False,
        "sourceSandboxExecuted": bool(safety.get("sandboxExecuted", report.get("sandboxExecuted", False))),
        "sourceContestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False)),
        "sourceCommandExecuted": bool(safety.get("commandExecuted", False)),
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "realPublish": False,
    }


def _artifact_for_report(store: JsonTaskStore, report_path: Path) -> dict[str, Any] | None:
    report_path_str = str(report_path)
    for artifact in store.list_artifacts(kind=ArtifactKind.GRADING_REPORT.value):
        if artifact.path == report_path_str:
            return artifact.to_dict()
    return None


def build_grading_result_preview(
    store: JsonTaskStore,
    *,
    report_path: Path,
    task_id: str | None = None,
    candidate_id: str | None = None,
    max_items: int = 8,
) -> dict[str, Any]:
    if max_items < 1:
        raise GradingResultPreviewError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "maxItems", "reason": "必须大于等于 1"}],
        )
    if task_id and store.get(task_id) is None:
        raise GradingResultPreviewError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )
    report = _read_report(report_path)
    artifact = _artifact_for_report(store, report_path)
    report_type = (
        (artifact or {}).get("metadata", {}).get("reportType")
        or report.get("reportType")
        or report.get("mode")
        or "GRADING_REPORT"
    )
    summary = _report_summary(report)
    score = _report_score(report)
    evidence_items = _evidence_items(report, max_items)
    return {
        "component": "GradingResultPreview",
        "mode": "READ_EXISTING_GRADING_REPORT_ONLY",
        "source": "grade.report + artifact.metadata",
        "taskId": task_id or (artifact or {}).get("taskId") or report.get("taskId"),
        "candidateId": candidate_id,
        "reportPath": str(report_path),
        "reportId": report.get("id"),
        "reportType": report_type,
        "artifact": artifact,
        "summary": summary,
        "score": score,
        "resultStatus": "PASSED" if score["passed"] else "NOT_PASSED",
        "evidencePreview": {
            "source": "report.checkEvidenceReviewItems or report.checks",
            "totalVisible": len(evidence_items),
            "maxItems": max_items,
            "items": evidence_items,
        },
        "reviewHints": {
            "manualReviewRequired": summary["manualReviewRequired"],
            "recommendedAction": (
                "review_failed_or_deferred_checks"
                if summary["failed"] or summary["deferred"]
                else "review_score_and_evidence_before_platform_import"
            ),
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
        },
        "safety": _safety(report),
    }
