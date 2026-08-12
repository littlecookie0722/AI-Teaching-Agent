"""Build a read-only readiness summary from existing grading evidence reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4


READINESS_MODE = "GRADING_EVIDENCE_READINESS"


class EvidenceReadinessError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def load_evidence_report(path: Path | str) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists() or not report_path.is_file():
        raise EvidenceReadinessError(
            "VALIDATION_ERROR",
            "评分 evidence 报告不存在",
            [{"field": "report", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceReadinessError(
            "VALIDATION_ERROR",
            "评分 evidence 报告 JSON 格式错误",
            [{"field": "report", "reason": str(exc)}],
        ) from exc
    if not isinstance(payload, dict):
        raise EvidenceReadinessError(
            "VALIDATION_ERROR",
            "评分 evidence 报告 JSON 格式错误",
            [{"field": "report", "reason": "root must be object"}],
        )
    return payload


def build_grading_evidence_readiness(
    reports: list[dict[str, Any]],
    *,
    report_paths: list[Path | str] | None = None,
    trace_id: str,
) -> dict[str, Any]:
    if not reports:
        raise EvidenceReadinessError(
            "VALIDATION_ERROR",
            "至少需要一个评分 evidence 报告",
            [{"field": "report", "reason": "required"}],
        )

    paths = [str(path) for path in (report_paths or [])]
    checks_by_id: dict[str, dict[str, Any]] = {}
    for report_index, report in enumerate(reports):
        for check in _report_checks(report):
            check_id = str(check.get("checkId") or check.get("id") or "")
            if not check_id:
                continue
            item = _readiness_item(
                check,
                report=report,
                report_index=report_index,
                source_path=paths[report_index] if report_index < len(paths) else None,
            )
            current = checks_by_id.get(check_id)
            if current is None or _readiness_rank(item) > _readiness_rank(current):
                checks_by_id[check_id] = item

    items = list(checks_by_id.values())
    covered = [item for item in items if item["evidenceReady"]]
    missing = [item for item in items if not item["evidenceReady"]]
    controlled_missing = [item for item in missing if item["recommendedNextEvidence"] == "controlled_command_evidence"]
    readonly_missing = [item for item in missing if item["recommendedNextEvidence"] == "readonly_static_evidence"]
    manual_only = [item for item in missing if item["recommendedNextEvidence"] == "manual_review_only"]
    total_score = sum(int(item.get("score") or 0) for item in items)
    covered_score = sum(int(item.get("score") or 0) for item in covered)
    earned_score = sum(int(item.get("earnedScore") or 0) for item in covered)

    return {
        "id": f"grading_evidence_readiness_{uuid4().hex[:12]}",
        "mode": READINESS_MODE,
        "phase": "Phase 3",
        "source": "existing grading evidence reports",
        "sourceReportTotal": len(reports),
        "sourceReports": [
            {
                "index": index,
                "path": paths[index] if index < len(paths) else None,
                "id": report.get("id"),
                "mode": report.get("mode"),
                "summary": report.get("summary") or report.get("executionSummary") or report.get("checkSummary") or {},
                "safety": report.get("safety", {}),
            }
            for index, report in enumerate(reports)
        ],
        "summary": {
            "checkTotal": len(items),
            "evidenceReadyTotal": len(covered),
            "missingEvidenceTotal": len(missing),
            "controlledCommandMissingTotal": len(controlled_missing),
            "readonlyStaticMissingTotal": len(readonly_missing),
            "manualOnlyMissingTotal": len(manual_only),
            "totalScore": total_score,
            "coveredScore": covered_score,
            "earnedScore": earned_score,
            "coverageRatio": round(covered_score / total_score, 4) if total_score else 0,
            "readyForHumanReview": len(items) > 0,
            "readyForApprovalRecommendation": len(missing) == 0,
            "manualReviewRequired": True,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "items": items,
        "nextActions": _next_actions(readonly_missing, controlled_missing, manual_only, missing),
        "safety": {
            "readExistingReportsOnly": True,
            "sandboxExecutedByReadiness": False,
            "contestantCodeExecutedByReadiness": False,
            "commandExecutedByReadiness": False,
            "pytestExecutedByReadiness": False,
            "notebookExecutedByReadiness": False,
            "networkAccessByReadiness": False,
            "sourceSandboxExecuted": any(bool((report.get("safety") or {}).get("sandboxExecuted")) for report in reports),
            "sourceContestantCodeExecuted": any(bool((report.get("safety") or {}).get("contestantCodeExecuted")) for report in reports),
            "sourceCommandExecuted": any(bool((report.get("safety") or {}).get("commandExecuted")) for report in reports),
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
        "traceId": trace_id,
        "note": "Evidence readiness only reads existing local reports and recommends next evidence collection steps.",
    }


def _report_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(report.get("checkEvidenceReviewItems"), list):
        return [item for item in report["checkEvidenceReviewItems"] if isinstance(item, dict)]
    if isinstance(report.get("checks"), list):
        return [item for item in report["checks"] if isinstance(item, dict)]
    detail = report.get("reportDetail")
    if isinstance(detail, dict) and isinstance(detail.get("checkPlans"), list):
        return [item for item in detail["checkPlans"] if isinstance(item, dict)]
    raise EvidenceReadinessError(
        "VALIDATION_ERROR",
        "评分 evidence 报告缺少 check 列表",
        [{"field": "report.checks", "reason": "missing"}],
    )


def _readiness_item(
    check: dict[str, Any],
    *,
    report: dict[str, Any],
    report_index: int,
    source_path: str | None,
) -> dict[str, Any]:
    check_id = str(check.get("checkId") or check.get("id") or "")
    check_type = str(check.get("checkType") or check.get("type") or "unknown")
    status = str(check.get("status") or "")
    passed = check.get("passed")
    evidence_ready = status in {"PASSED", "FAILED", "ERROR"} or passed is not None
    report_mode = _report_mode(report, check)
    source_kind = _source_kind(report_mode, check)
    return {
        "checkId": check_id,
        "checkType": check_type,
        "status": status or ("COLLECTED" if evidence_ready else "MISSING"),
        "passed": passed,
        "score": int(check.get("score") or 0),
        "earnedScore": int(check.get("earnedScore") or 0),
        "evidenceReady": evidence_ready,
        "evidenceSourceKind": source_kind,
        "reportMode": report_mode,
        "sourceReportIndex": report_index,
        "sourcePath": source_path,
        "recommendedNextEvidence": _recommended_next_evidence(check_type, evidence_ready),
        "recommendedAction": _recommended_action(check_type, evidence_ready, source_kind),
        "manualReviewRequired": True,
    }


def _report_mode(report: dict[str, Any], check: dict[str, Any]) -> str:
    source = check.get("evidenceSource")
    if isinstance(source, dict) and source.get("reportMode"):
        return str(source["reportMode"])
    return str(report.get("mode") or report.get("reportType") or "UNKNOWN")


def _source_kind(report_mode: str, check: dict[str, Any]) -> str:
    explicit = check.get("evidenceSourceKind") or check.get("source")
    if explicit:
        return str(explicit)
    if report_mode == "CONTROLLED_DOCKER_SANDBOX_POC":
        return "controlledDocker"
    if report_mode == "READONLY_REAL_SANDBOX_POC":
        return "readonlyStatic"
    if report_mode in {"GRADING_EVIDENCE_MERGE_REPORT", "GRADING_EVIDENCE_AUTO_REPORT"}:
        return "mergedEvidence"
    return "unknown"


def _recommended_next_evidence(check_type: str, evidence_ready: bool) -> str:
    if evidence_ready:
        return "manual_review"
    if check_type in {"stdout_contains", "pytest"}:
        return "controlled_command_evidence"
    if check_type in {"file_exists", "json_field", "notebook_cell", "log_keyword"}:
        return "readonly_static_evidence"
    return "manual_review_only"


def _recommended_action(check_type: str, evidence_ready: bool, source_kind: str) -> str:
    if evidence_ready:
        if source_kind == "controlledDocker":
            return "verify_controlled_docker_output_and_score"
        if source_kind == "readonlyStatic":
            return "verify_static_evidence_and_score"
        return "verify_existing_evidence_and_score"
    if check_type in {"stdout_contains", "pytest"}:
        return "run_controlled_command_evidence_after_review"
    if check_type in {"file_exists", "json_field", "notebook_cell", "log_keyword"}:
        return "run_readonly_static_evidence"
    return "perform_manual_review"


def _readiness_rank(item: dict[str, Any]) -> tuple[int, int]:
    ready_rank = 2 if item["evidenceReady"] else 0
    source_kind = item["evidenceSourceKind"]
    source_rank = 2 if source_kind == "controlledDocker" else 1 if source_kind == "readonlyStatic" else 0
    return (ready_rank, source_rank)


def _next_actions(
    readonly_missing: list[dict[str, Any]],
    controlled_missing: list[dict[str, Any]],
    manual_only: list[dict[str, Any]],
    missing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if readonly_missing:
        actions.append(
            {
                "id": "run_readonly_static_evidence",
                "label": "Run read-only static evidence",
                "checkIds": [item["checkId"] for item in readonly_missing],
                "command": "python lab_cli.py grade sandbox-run --execution-mode readonly --grading <grading> --submission <submission> --output <report>",
            }
        )
    if controlled_missing:
        actions.append(
            {
                "id": "run_controlled_command_evidence_after_review",
                "label": "Run controlled command evidence after review",
                "checkIds": [item["checkId"] for item in controlled_missing],
                "command": "python lab_cli.py grade sandbox-run --execution-mode controlled-command --grading <grading> --submission <submission> --output <report>",
            }
        )
    if manual_only:
        actions.append(
            {
                "id": "perform_manual_review",
                "label": "Perform manual review",
                "checkIds": [item["checkId"] for item in manual_only],
            }
        )
    actions.append(
        {
            "id": "record_review_decision_note" if missing else "review_ready_score_and_evidence",
            "label": "Record review decision note" if missing else "Review ready score and evidence",
            "checkIds": [item["checkId"] for item in missing],
        }
    )
    return actions
