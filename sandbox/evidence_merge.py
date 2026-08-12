"""Merge grading evidence reports without executing any sandbox action."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4


MERGE_MODE = "GRADING_EVIDENCE_MERGE_REPORT"


class EvidenceMergeError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def build_grading_evidence_merge_report(
    reports: list[dict[str, Any]],
    *,
    report_paths: list[Path | str] | None = None,
    trace_id: str,
) -> dict[str, Any]:
    if not reports:
        raise EvidenceMergeError("VALIDATION_ERROR", "At least one grading evidence report is required.", [{"field": "report", "reason": "required"}])

    paths = [str(path) for path in (report_paths or [])]
    source_reports = [_source_report_summary(report, paths[index] if index < len(paths) else None, index) for index, report in enumerate(reports)]
    selected_by_id: dict[str, dict[str, Any]] = {}
    collisions: list[dict[str, Any]] = []
    for index, report in enumerate(reports):
        source_path = paths[index] if index < len(paths) else None
        for check in _report_checks(report):
            check_id = str(check.get("id") or "")
            if not check_id:
                collisions.append({"reportIndex": index, "sourcePath": source_path, "reason": "missing_check_id"})
                continue
            candidate = _annotate_check(check, report=report, report_index=index, source_path=source_path)
            current = selected_by_id.get(check_id)
            if current is None or _check_rank(candidate) > _check_rank(current):
                if current is not None:
                    collisions.append(
                        {
                            "checkId": check_id,
                            "keptReportIndex": index,
                            "replacedReportIndex": current.get("evidenceSource", {}).get("reportIndex"),
                            "reason": "higher_evidence_rank_selected",
                        }
                    )
                selected_by_id[check_id] = candidate
            else:
                collisions.append(
                    {
                        "checkId": check_id,
                        "keptReportIndex": current.get("evidenceSource", {}).get("reportIndex"),
                        "ignoredReportIndex": index,
                        "reason": "lower_or_equal_evidence_rank_ignored",
                    }
                )

    checks = list(selected_by_id.values())
    total_score = sum(int(check.get("score", 0)) for check in checks)
    earned_score = sum(int(check.get("earnedScore", 0)) for check in checks)
    executed = [check for check in checks if _is_executed(check)]
    deferred = [check for check in checks if str(check.get("status")) == "DEFERRED" or not _is_executed(check)]
    failed = [check for check in executed if check.get("passed") is False]
    passed = [check for check in executed if check.get("passed") is True]
    controlled = [check for check in executed if check.get("evidenceSource", {}).get("reportMode") == "CONTROLLED_DOCKER_SANDBOX_POC"]
    readonly = [check for check in executed if check.get("evidenceSource", {}).get("reportMode") == "READONLY_REAL_SANDBOX_POC"]

    coverage = {
        "totalScore": total_score,
        "earnedScore": earned_score,
        "coveredScore": sum(int(check.get("score", 0)) for check in executed),
        "deferredScore": sum(int(check.get("score", 0)) for check in deferred),
        "coverageRatio": round((sum(int(check.get("score", 0)) for check in executed) / total_score), 4) if total_score else 0,
        "coveredCheckIds": [str(check.get("id")) for check in executed],
        "passedCheckIds": [str(check.get("id")) for check in passed],
        "failedCheckIds": [str(check.get("id")) for check in failed],
        "deferredCheckIds": [str(check.get("id")) for check in deferred],
        "controlledDocker": _coverage_bucket(controlled, "CONTROLLED_DOCKER_SANDBOX_POC"),
        "readonlyStatic": _coverage_bucket(readonly, "READONLY_REAL_SANDBOX_POC"),
    }
    score_preview = {
        "component": "GradingEvidenceAutoScorePreview",
        "source": "GRADING_EVIDENCE_MERGE_REPORT.checks",
        "status": "READY_FOR_HUMAN_SCORE_REVIEW"
        if coverage["coveredScore"] >= total_score and not deferred
        else "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE",
        "earnedScore": earned_score,
        "totalScore": total_score,
        "coveredScore": coverage["coveredScore"],
        "missingScore": max(total_score - coverage["coveredScore"], 0),
        "deferredScore": coverage["deferredScore"],
        "coverageRatio": coverage["coverageRatio"],
        "scoreRatio": round((earned_score / total_score), 4) if total_score else 0,
        "passRate": round((len(passed) / len(executed)), 4) if executed else 0,
        "readyForDecisionNote": coverage["coveredScore"] >= total_score and not deferred,
        "missingEvidenceTotal": len(deferred),
        "missingCheckIds": [str(check.get("id")) for check in deferred],
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }
    safety = _merge_safety(reports)
    return {
        "id": f"grading_evidence_merge_{uuid4().hex[:12]}",
        "mode": MERGE_MODE,
        "phase": "Phase 3",
        "sourceReportTotal": len(reports),
        "sourceReports": source_reports,
        "summary": {
            "checkTotal": len(checks),
            "executed": len(executed),
            "passedCheckTotal": len(passed),
            "failedCheckTotal": len(failed),
            "deferredCheckTotal": len(deferred),
            "passed": len(deferred) == 0 and len(failed) == 0 and earned_score >= total_score,
            "failed": len(failed),
            "deferred": len(deferred),
            "totalScore": total_score,
            "earnedScore": earned_score,
            "coveredScore": coverage["coveredScore"],
            "deferredScore": coverage["deferredScore"],
            "manualReviewRequired": True,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "evidenceCoverage": coverage,
        "scorePreview": score_preview,
        "checks": checks,
        "mergeWarnings": collisions,
        "safety": safety,
        "traceId": trace_id,
        "note": "Evidence merge only reads existing local reports; it does not execute Docker, pytest, notebooks, commands, or contestant code.",
    }


def _source_report_summary(report: dict[str, Any], path: str | None, index: int) -> dict[str, Any]:
    return {
        "index": index,
        "path": path,
        "id": report.get("id"),
        "mode": report.get("mode"),
        "gradingId": report.get("gradingId"),
        "checkSummary": report.get("checkSummary", {}),
        "executionSummary": report.get("executionSummary", {}),
        "score": report.get("score", {}),
        "safety": report.get("safety", {}),
    }


def _report_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    detail = report.get("reportDetail")
    if isinstance(detail, dict) and isinstance(detail.get("checkPlans"), list):
        return [check for check in detail["checkPlans"] if isinstance(check, dict)]
    checks = report.get("checks")
    if isinstance(checks, list):
        return [check for check in checks if isinstance(check, dict)]
    raise EvidenceMergeError(
        "VALIDATION_ERROR",
        "Grading evidence report does not contain reportDetail.checkPlans or checks.",
        [{"field": "reportDetail.checkPlans", "reason": "missing"}],
    )


def _annotate_check(check: dict[str, Any], *, report: dict[str, Any], report_index: int, source_path: str | None) -> dict[str, Any]:
    return {
        **check,
        "evidenceSource": {
            "reportIndex": report_index,
            "sourcePath": source_path,
            "reportId": report.get("id"),
            "reportMode": report.get("mode"),
            "runnerId": report.get("runner", {}).get("id") if isinstance(report.get("runner"), dict) else None,
        },
    }


def _check_rank(check: dict[str, Any]) -> tuple[int, int]:
    status = str(check.get("status"))
    passed = check.get("passed")
    mode = check.get("evidenceSource", {}).get("reportMode")
    executed_rank = 0 if status == "DEFERRED" or passed is None else 2
    mode_rank = 2 if mode == "CONTROLLED_DOCKER_SANDBOX_POC" else 1 if mode == "READONLY_REAL_SANDBOX_POC" else 0
    return (executed_rank, mode_rank)


def _is_executed(check: dict[str, Any]) -> bool:
    status = str(check.get("status"))
    return status in {"PASSED", "FAILED", "ERROR"} or check.get("passed") is not None


def _coverage_bucket(checks: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "checkTotal": len(checks),
        "checkIds": [str(check.get("id")) for check in checks],
        "checkTypes": sorted({str(check.get("type")) for check in checks}),
        "score": sum(int(check.get("score", 0)) for check in checks),
        "earnedScore": sum(int(check.get("earnedScore", 0)) for check in checks),
    }


def _merge_safety(reports: list[dict[str, Any]]) -> dict[str, Any]:
    source_safety = [report.get("safety", {}) for report in reports if isinstance(report.get("safety"), dict)]

    def any_flag(name: str) -> bool:
        return any(bool(item.get(name)) for item in source_safety)

    return {
        "sandboxExecuted": any_flag("sandboxExecuted"),
        "readonlyOnly": all(bool(item.get("readonlyOnly")) for item in source_safety) if source_safety else False,
        "contestantCodeExecuted": any_flag("contestantCodeExecuted"),
        "commandExecuted": any_flag("commandExecuted"),
        "unknownShellExecuted": any_flag("unknownShellExecuted"),
        "pytestExecuted": any_flag("pytestExecuted"),
        "notebookExecuted": any_flag("notebookExecuted"),
        "networkEnabled": any_flag("networkEnabled"),
        "hostExecutionAllowed": any_flag("hostExecutionAllowed"),
        "realPublish": any_flag("realPublish"),
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "manualReviewRequired": True,
        "mergeExecutedOnlyExistingReports": True,
    }
