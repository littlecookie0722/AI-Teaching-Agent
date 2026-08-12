"""Automatic grading evidence orchestration.

This module composes the existing read-only sandbox, optional controlled
Docker sandbox, and evidence merge report. It does not define a new safety
gate; it only turns the already implemented grading tools into one command.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sandbox.controlled_command_executor import ControlledCommandSandboxError, build_controlled_command_sandbox_report
from sandbox.evidence_merge import build_grading_evidence_merge_report
from sandbox.readonly_sandbox_executor import build_readonly_sandbox_report


MODE = "GRADING_EVIDENCE_AUTO_REPORT"
DIAGNOSTIC_TAIL_CHARS = 300


class GradingEvidenceAutoError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def build_grading_evidence_auto_report(
    grading: dict[str, Any],
    submission_root: Path | str,
    *,
    trace_id: str,
    include_controlled_command: bool = False,
    image: str = "ai-grading-python:0.1",
    fail_on_controlled_unavailable: bool = False,
) -> dict[str, Any]:
    """Run available grading evidence collectors and return a merged report.

    The read-only collector always runs first. Controlled command evidence only
    runs when explicitly requested. If Docker/image is unavailable, the default
    behavior is to keep the read-only result and report the controlled failure as
    a non-fatal warning.
    """

    grading_checks = [check for check in grading.get("spec", {}).get("checks", []) if isinstance(check, dict)]
    readonly_report = build_readonly_sandbox_report(grading, submission_root, trace_id)
    source_reports = [readonly_report]
    controlled_report: dict[str, Any] | None = None
    controlled_warning: dict[str, Any] | None = None
    steps = [
        {
            "id": "readonly_static_evidence",
            "mode": readonly_report["mode"],
            "status": "COMPLETED",
            "executed": readonly_report["executionSummary"]["executed"],
            "passed": readonly_report["executionSummary"]["passed"],
            "safety": readonly_report["safety"],
        }
    ]
    warnings: list[dict[str, Any]] = []

    if include_controlled_command:
        try:
            controlled_report = build_controlled_command_sandbox_report(
                grading,
                submission_root,
                trace_id,
                image=image,
            )
            source_reports.append(controlled_report)
            steps.append(
                {
                    "id": "controlled_command_evidence",
                    "mode": controlled_report["mode"],
                    "status": "COMPLETED",
                    "executed": controlled_report["executionSummary"]["executed"],
                    "passed": controlled_report["executionSummary"]["passed"],
                    "image": image,
                    "safety": controlled_report["safety"],
                }
            )
        except ControlledCommandSandboxError as exc:
            warning = {
                "id": "controlled_command_evidence",
                "status": "SKIPPED",
                "code": exc.code,
                "message": exc.message,
                "errors": exc.errors,
                "image": image,
            }
            controlled_warning = warning
            warnings.append(warning)
            steps.append(warning)
            if fail_on_controlled_unavailable:
                raise GradingEvidenceAutoError(exc.code, exc.message, exc.errors) from exc
    else:
        steps.append(
            {
                "id": "controlled_command_evidence",
                "status": "SKIPPED",
                "reason": "includeControlledCommand=false",
                "contestantCodeExecuted": False,
                "commandExecuted": False,
            }
        )

    merge_report = build_grading_evidence_merge_report(source_reports, trace_id=trace_id)
    execution_matrix = _build_execution_matrix(
        grading_checks,
        readonly_report=readonly_report,
        controlled_report=controlled_report,
        controlled_requested=include_controlled_command,
        controlled_warning=controlled_warning,
    )
    next_core_action = _next_core_action(
        execution_matrix,
        controlled_requested=include_controlled_command,
        controlled_warning=controlled_warning,
    )
    manual_review_checklist = _build_manual_review_checklist(
        execution_matrix,
        next_core_action=next_core_action,
        controlled_warning=controlled_warning,
    )
    score_preview = _build_score_preview(execution_matrix)
    reviewer_safety_summary = _build_reviewer_safety_summary(
        execution_matrix,
        score_preview=score_preview,
        manual_review_checklist=manual_review_checklist,
        next_core_action=next_core_action,
        controlled_requested=include_controlled_command,
        controlled_report=controlled_report,
        controlled_warning=controlled_warning,
    )
    grading_dsl_coverage_summary = _build_grading_dsl_coverage_summary(
        execution_matrix,
        score_preview=score_preview,
        manual_review_checklist=manual_review_checklist,
        next_core_action=next_core_action,
    )
    merge_report["mode"] = MODE
    merge_report["sourceMode"] = "EVIDENCE_AUTO"
    merge_report["steps"] = steps
    merge_report["warnings"] = [*merge_report.get("mergeWarnings", []), *warnings]
    merge_report["executionMatrix"] = execution_matrix
    merge_report["controlledExecutionProfile"] = _controlled_execution_profile(controlled_report, controlled_warning, image)
    merge_report["controlledExecutionDiagnostic"] = _controlled_execution_diagnostic(controlled_report, controlled_warning, image)
    merge_report["scorePreview"] = score_preview
    merge_report["gradingDslCoverageSummary"] = grading_dsl_coverage_summary
    merge_report["nextCoreAction"] = next_core_action
    merge_report["manualReviewChecklist"] = manual_review_checklist
    merge_report["reviewerSafetySummary"] = reviewer_safety_summary
    merge_report["summary"] = {
        **merge_report["summary"],
        "sourceMode": "EVIDENCE_AUTO",
        "readonlyReportIncluded": True,
        "controlledCommandRequested": include_controlled_command,
        "controlledCommandIncluded": any(report.get("mode") == "CONTROLLED_DOCKER_SANDBOX_POC" for report in source_reports),
        "controlledCommandWarningTotal": len(warnings),
        "evidenceReadyTotal": execution_matrix["summary"]["evidenceReadyTotal"],
        "missingEvidenceTotal": execution_matrix["summary"]["missingEvidenceTotal"],
        "controlledCommandMissingTotal": execution_matrix["summary"]["controlledCommandMissingTotal"],
        "nextCoreActionId": next_core_action["id"],
        "manualReviewChecklistStatus": manual_review_checklist["status"],
        "manualReviewChecklistTotal": manual_review_checklist["summary"]["itemTotal"],
        "manualReviewChecklistReadyTotal": manual_review_checklist["summary"]["readyForDecisionTotal"],
        "decisionNoteRecommendation": manual_review_checklist["decisionNoteRecommendation"]["decision"],
        "gradingDslCoverageStatus": grading_dsl_coverage_summary["status"],
        "gradingDslEvidenceReadyTotal": grading_dsl_coverage_summary["evidenceReadyTotal"],
        "gradingDslMissingEvidenceTotal": grading_dsl_coverage_summary["missingEvidenceTotal"],
        "scorePreviewEarnedScore": score_preview["earnedScore"],
        "scorePreviewTotalScore": score_preview["totalScore"],
        "scorePreviewCoverageRatio": score_preview["coverageRatio"],
        "scorePreviewStatus": score_preview["status"],
        "reviewerSafetySummaryStatus": reviewer_safety_summary["status"],
        "reviewerSafetyReadyForApproveReadyDecision": reviewer_safety_summary[
            "readyForApproveReadyDecision"
        ],
        "reviewerSafetyBlockingReasonTotal": len(reviewer_safety_summary["blockingReasons"]),
        "controlledExecutionProfileId": merge_report["controlledExecutionProfile"]["id"],
        "controlledExecutionDiagnosticCode": merge_report["controlledExecutionDiagnostic"]["code"],
    }
    merge_report["safety"] = {
        **merge_report["safety"],
        "sourceMode": "EVIDENCE_AUTO",
        "readonlyAlwaysRunsFirst": True,
        "controlledCommandRequiresExplicitFlag": True,
        "controlledCommandRequested": include_controlled_command,
        "controlledCommandIncluded": merge_report["summary"]["controlledCommandIncluded"],
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }
    merge_report["note"] = (
        "Evidence auto runs read-only grading evidence and optionally controlled Docker command evidence, "
        "then merges existing reports into one reviewable grading report."
    )
    return merge_report


def _controlled_execution_profile(
    controlled_report: dict[str, Any] | None,
    controlled_warning: dict[str, Any] | None,
    image: str,
) -> dict[str, Any]:
    if controlled_report and isinstance(controlled_report.get("executionProfile"), dict):
        return controlled_report["executionProfile"]
    return {
        "id": "local-python-pytest-controlled-v1",
        "scope": "local controlled Docker grading only",
        "requested": controlled_warning is not None,
        "image": {"image": image, "metadataValidated": False},
        "network": {"enabled": False},
        "boundaries": {"hostExecutionAllowed": False, "autoApproveAllowed": False, "realPublish": False},
    }


def _controlled_execution_diagnostic(
    controlled_report: dict[str, Any] | None,
    controlled_warning: dict[str, Any] | None,
    image: str,
) -> dict[str, Any]:
    if controlled_report:
        return {
            "status": "COLLECTED",
            "code": "OK",
            "message": "Controlled Docker evidence was collected.",
            "image": image,
            "checkTotal": controlled_report.get("executionSummary", {}).get("total"),
            "executedTotal": controlled_report.get("executionSummary", {}).get("executed"),
            "failedCheckTotal": controlled_report.get("executionSummary", {}).get("failed"),
        }
    if controlled_warning:
        return {
            "status": "NOT_COLLECTED",
            "code": str(controlled_warning.get("code") or "CONTROLLED_EVIDENCE_UNAVAILABLE"),
            "message": str(controlled_warning.get("message") or "Controlled Docker evidence was unavailable."),
            "image": image,
            "errors": list(controlled_warning.get("errors") or []),
        }
    return {
        "status": "NOT_REQUESTED",
        "code": "CONTROLLED_EVIDENCE_NOT_REQUESTED",
        "message": "Controlled Docker evidence was not requested.",
        "image": image,
        "errors": [],
    }


def _build_reviewer_safety_summary(
    execution_matrix: dict[str, Any],
    *,
    score_preview: dict[str, Any],
    manual_review_checklist: dict[str, Any],
    next_core_action: dict[str, Any],
    controlled_requested: bool,
    controlled_report: dict[str, Any] | None,
    controlled_warning: dict[str, Any] | None,
) -> dict[str, Any]:
    """Fold score, evidence, and safety signals into one reviewer-facing block.

    This is intentionally derived from existing report fields. It does not add a
    new gate or change whether evidence is collected.
    """

    summary = execution_matrix["summary"]
    checklist_summary = manual_review_checklist.get("summary", {})
    controlled_safety = controlled_report.get("safety", {}) if isinstance(controlled_report, dict) else {}
    blocking_reasons: list[dict[str, Any]] = []
    if controlled_warning:
        blocking_reasons.append(
            {
                "id": "controlled_command_runtime_unavailable",
                "severity": "warning",
                "message": str(controlled_warning.get("message") or "Controlled command runtime is unavailable."),
                "nextCoreActionId": next_core_action["id"],
            }
        )
    if summary["controlledCommandMissingTotal"]:
        blocking_reasons.append(
            {
                "id": "controlled_command_evidence_missing",
                "severity": "warning",
                "missingTotal": summary["controlledCommandMissingTotal"],
                "message": "stdout_contains/pytest checks still need controlled Docker evidence.",
                "nextCoreActionId": next_core_action["id"],
            }
        )
    static_missing_total = max(
        int(summary["missingEvidenceTotal"] or 0) - int(summary["controlledCommandMissingTotal"] or 0),
        0,
    )
    if static_missing_total:
        blocking_reasons.append(
            {
                "id": "static_or_manual_evidence_missing",
                "severity": "warning",
                "missingTotal": static_missing_total,
                "message": "Some read-only/static checks still need evidence or manual review.",
                "nextCoreActionId": next_core_action["id"],
            }
        )
    if score_preview.get("readyForDecisionNote") is not True:
        blocking_reasons.append(
            {
                "id": "score_preview_not_ready_for_approve_ready",
                "severity": "info",
                "message": "Score preview is partial; record needs-evidence/needs-revision before approve-ready.",
                "nextCoreActionId": next_core_action["id"],
            }
        )

    ready_for_approve_ready = (
        score_preview.get("readyForDecisionNote") is True
        and manual_review_checklist.get("status") == "READY_FOR_DECISION_NOTE"
        and not controlled_warning
    )
    if controlled_warning:
        status = "NEEDS_CONTROLLED_RUNTIME_REVIEW"
    elif ready_for_approve_ready:
        status = "READY_FOR_HUMAN_APPROVE_READY_DECISION"
    elif summary["controlledCommandMissingTotal"]:
        status = "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    elif summary["missingEvidenceTotal"]:
        status = "NEEDS_EVIDENCE_REVIEW"
    else:
        status = "NEEDS_HUMAN_REVIEW"

    return {
        "component": "GradingEvidenceAutoReviewerSafetySummary",
        "mode": "GRADING_EVIDENCE_AUTO_REVIEWER_SAFETY_SUMMARY",
        "source": "scorePreview + executionMatrix + manualReviewChecklist + controlledReport.safety",
        "status": status,
        "readyForHumanReview": bool(summary["checkTotal"]),
        "readyForHumanScoreReview": score_preview.get("status") == "READY_FOR_HUMAN_SCORE_REVIEW",
        "readyForApproveReadyDecision": ready_for_approve_ready,
        "blockingReasons": blocking_reasons,
        "score": {
            "earnedScore": score_preview.get("earnedScore"),
            "totalScore": score_preview.get("totalScore"),
            "coveredScore": score_preview.get("coveredScore"),
            "missingScore": score_preview.get("missingScore"),
            "coverageRatio": score_preview.get("coverageRatio"),
            "scoreRatio": score_preview.get("scoreRatio"),
            "passRate": score_preview.get("passRate"),
        },
        "evidence": {
            "checkTotal": summary["checkTotal"],
            "evidenceReadyTotal": summary["evidenceReadyTotal"],
            "missingEvidenceTotal": summary["missingEvidenceTotal"],
            "controlledCommandRequested": controlled_requested,
            "controlledCommandIncluded": controlled_report is not None,
            "controlledCommandMissingTotal": summary["controlledCommandMissingTotal"],
            "controlledCommandRuntimeWarning": controlled_warning is not None,
            "manualChecklistReadyTotal": checklist_summary.get("readyForDecisionTotal", 0),
            "manualChecklistTotal": checklist_summary.get("itemTotal", 0),
        },
        "requiredManualChecks": [
            {
                "id": "verify_score_preview",
                "status": "READY" if score_preview.get("readyForDecisionNote") else "NEEDS_EVIDENCE",
                "description": "Review earned score, missing score, failed checks, and evidence coverage.",
            },
            {
                "id": "verify_controlled_command_evidence",
                "status": "READY" if summary["controlledCommandMissingTotal"] == 0 else "NEEDS_EVIDENCE",
                "description": "Confirm stdout_contains/pytest checks use controlled Docker evidence when applicable.",
            },
            {
                "id": "record_human_decision_note",
                "status": "READY" if ready_for_approve_ready else "NEEDS_DECISION",
                "description": "Record approve-ready, needs-evidence, or needs-revision manually.",
            },
        ],
        "decisionNoteRecommendation": manual_review_checklist.get("decisionNoteRecommendation", {}),
        "nextCoreAction": {
            "id": next_core_action.get("id"),
            "label": next_core_action.get("label"),
            "cli": next_core_action.get("cli"),
            "api": next_core_action.get("api"),
        },
        "safety": {
            "manualReviewRequired": True,
            "controlledCommandRequiresExplicitFlag": True,
            "contestantCodeExecutedInControlledSandbox": bool(
                controlled_safety.get("contestantCodeExecuted")
            ),
            "hostExecutionAllowed": False,
            "unknownShellExecuted": False,
            "networkEnabled": bool(controlled_safety.get("networkEnabled", False)),
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _build_grading_dsl_coverage_summary(
    execution_matrix: dict[str, Any],
    *,
    score_preview: dict[str, Any],
    manual_review_checklist: dict[str, Any],
    next_core_action: dict[str, Any],
) -> dict[str, Any]:
    summary = execution_matrix["summary"]
    items = execution_matrix.get("items", [])
    missing_items = [item for item in items if item.get("evidenceReady") is not True]
    controlled_missing = [
        item
        for item in missing_items
        if item.get("recommendedNextEvidence") == "run_evidence_auto_with_controlled_command"
    ]
    static_missing = [
        item
        for item in missing_items
        if item.get("recommendedNextEvidence") == "fix_submission_or_grading_static_evidence"
    ]
    manual_only = [
        item
        for item in missing_items
        if item.get("recommendedNextEvidence") == "manual_review_only"
    ]
    if not missing_items:
        status = "FULLY_COVERED_READY_FOR_HUMAN_DECISION"
    elif controlled_missing:
        status = "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    elif static_missing:
        status = "NEEDS_STATIC_EVIDENCE_REVIEW"
    else:
        status = "NEEDS_MANUAL_EVIDENCE_REVIEW"
    return {
        "component": "GradingDslCoverageSummary",
        "mode": "GRADING_DSL_COVERAGE_SUMMARY",
        "source": "grading.spec.checks + GRADING_EVIDENCE_AUTO_REPORT.executionMatrix",
        "status": status,
        "dslCheckTotal": summary["checkTotal"],
        "evidenceReadyTotal": summary["evidenceReadyTotal"],
        "missingEvidenceTotal": summary["missingEvidenceTotal"],
        "readonlyStaticCheckTotal": summary["readonlyStaticCheckTotal"],
        "readonlyStaticCoveredTotal": summary["readonlyStaticCoveredTotal"],
        "controlledCommandCheckTotal": summary["controlledCommandCheckTotal"],
        "controlledCommandCoveredTotal": summary["controlledCommandCoveredTotal"],
        "controlledCommandMissingTotal": summary["controlledCommandMissingTotal"],
        "missingCheckIds": [str(item.get("checkId")) for item in missing_items],
        "controlledCommandMissingCheckIds": [str(item.get("checkId")) for item in controlled_missing],
        "readonlyStaticMissingCheckIds": [str(item.get("checkId")) for item in static_missing],
        "manualReviewOnlyCheckIds": [str(item.get("checkId")) for item in manual_only],
        "scorePreviewStatus": score_preview["status"],
        "scorePreviewReadyForDecisionNote": score_preview["readyForDecisionNote"],
        "decisionNoteRecommendation": manual_review_checklist["decisionNoteRecommendation"]["decision"],
        "nextCoreActionId": next_core_action["id"],
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _build_score_preview(execution_matrix: dict[str, Any]) -> dict[str, Any]:
    items = execution_matrix.get("items", [])
    total_score = sum(int(item.get("score") or 0) for item in items)
    ready_items = [item for item in items if item.get("evidenceReady") is True]
    missing_items = [item for item in items if item.get("evidenceReady") is not True]
    earned_score = sum(int((item.get("selectedEvidence") or {}).get("earnedScore") or 0) for item in ready_items)
    covered_score = sum(int(item.get("score") or 0) for item in ready_items)
    passed_items = [item for item in ready_items if (item.get("selectedEvidence") or {}).get("passed") is True]
    failed_items = [item for item in ready_items if (item.get("selectedEvidence") or {}).get("passed") is False]
    status = "READY_FOR_HUMAN_SCORE_REVIEW" if not missing_items else "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE"
    return {
        "component": "GradingEvidenceAutoScorePreview",
        "mode": "GRADING_EVIDENCE_AUTO_SCORE_PREVIEW",
        "source": "GRADING_EVIDENCE_AUTO_REPORT.executionMatrix.selectedEvidence",
        "status": status,
        "totalScore": total_score,
        "earnedScore": earned_score,
        "coveredScore": covered_score,
        "missingScore": total_score - covered_score,
        "coverageRatio": round(covered_score / total_score, 4) if total_score else 0,
        "scoreRatio": round(earned_score / total_score, 4) if total_score else 0,
        "passRate": round(len(passed_items) / len(ready_items), 4) if ready_items else 0,
        "checkTotal": len(items),
        "evidenceReadyTotal": len(ready_items),
        "missingEvidenceTotal": len(missing_items),
        "passedCheckTotal": len(passed_items),
        "failedCheckTotal": len(failed_items),
        "missingCheckIds": [str(item.get("checkId")) for item in missing_items],
        "readyForDecisionNote": not missing_items,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _build_execution_matrix(
    grading_checks: list[dict[str, Any]],
    *,
    readonly_report: dict[str, Any],
    controlled_report: dict[str, Any] | None,
    controlled_requested: bool,
    controlled_warning: dict[str, Any] | None,
) -> dict[str, Any]:
    readonly_by_id = _checks_by_id(readonly_report)
    controlled_by_id = _checks_by_id(controlled_report) if controlled_report else {}
    controlled_types = {"stdout_contains", "pytest"}
    readonly_types = {"file_exists", "json_field", "notebook_cell", "log_keyword"}
    items: list[dict[str, Any]] = []

    for check in grading_checks:
        check_id = str(check.get("id") or "")
        check_type = str(check.get("type") or "unknown")
        readonly_check = readonly_by_id.get(check_id)
        controlled_check = controlled_by_id.get(check_id)
        selected = _selected_evidence(readonly_check, controlled_check)
        evidence_ready = selected["status"] in {"PASSED", "FAILED", "ERROR"}
        selected_mode = str(selected.get("mode") or "MISSING")
        selected_status = str(selected.get("status") or "MISSING")
        recommended_next = _recommended_next_evidence(
            check_type,
            evidence_ready=evidence_ready,
            controlled_requested=controlled_requested,
            controlled_warning=controlled_warning,
        )
        items.append(
            {
                "checkId": check_id,
                "checkType": check_type,
                "score": int(check.get("score") or 0),
                "status": selected_status,
                "passed": selected.get("passed"),
                "earnedScore": int(selected.get("earnedScore") or 0),
                "selectedEvidenceMode": selected_mode,
                "evidenceSourceKind": selected_mode,
                "exitCode": selected.get("exitCode"),
                "stdoutTail": selected.get("stdoutTail"),
                "stderrTail": selected.get("stderrTail"),
                "filesInspected": selected.get("filesInspected", []),
                "errorCode": selected.get("errorCode"),
                "errorReason": selected.get("errorReason"),
                "readonlyEvidence": _evidence_state(readonly_check, "READONLY_REAL_SANDBOX_POC"),
                "controlledCommandEvidence": _controlled_state(
                    controlled_check,
                    check_type=check_type,
                    controlled_requested=controlled_requested,
                    controlled_warning=controlled_warning,
                ),
                "selectedEvidence": selected,
                "evidenceReady": evidence_ready,
                "recommendedNextEvidence": recommended_next,
                "reason": _execution_matrix_reason(
                    selected_status=selected_status,
                    selected_mode=selected_mode,
                    recommended_next=recommended_next,
                ),
                "manualReviewRequired": True,
            }
        )

    evidence_ready_items = [item for item in items if item["evidenceReady"]]
    missing_items = [item for item in items if not item["evidenceReady"]]
    controlled_items = [item for item in items if item["checkType"] in controlled_types]
    readonly_items = [item for item in items if item["checkType"] in readonly_types]
    controlled_covered = [
        item
        for item in controlled_items
        if item["controlledCommandEvidence"]["status"] in {"PASSED", "FAILED", "ERROR"}
    ]
    readonly_covered = [
        item
        for item in readonly_items
        if item["readonlyEvidence"]["status"] in {"PASSED", "FAILED", "ERROR"}
    ]
    return {
        "mode": "GRADING_EVIDENCE_AUTO_EXECUTION_MATRIX",
        "source": "grading.spec.checks + readonly_report + optional_controlled_report",
        "summary": {
            "checkTotal": len(items),
            "evidenceReadyTotal": len(evidence_ready_items),
            "missingEvidenceTotal": len(missing_items),
            "readonlyStaticCheckTotal": len(readonly_items),
            "readonlyStaticCoveredTotal": len(readonly_covered),
            "controlledCommandCheckTotal": len(controlled_items),
            "controlledCommandCoveredTotal": len(controlled_covered),
            "controlledCommandMissingTotal": len(controlled_items) - len(controlled_covered),
            "controlledCommandRequested": controlled_requested,
            "controlledCommandRuntimeWarning": controlled_warning is not None,
            "readyForScorePreview": bool(items),
            "readyForApprovalRecommendation": bool(items) and not missing_items,
            "manualReviewRequired": True,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "items": items,
    }


def _checks_by_id(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    return {str(check.get("id")): check for check in report.get("checks", []) if isinstance(check, dict) and check.get("id")}


def _evidence_state(check: dict[str, Any] | None, mode: str) -> dict[str, Any]:
    if not check:
        return {
            "mode": mode,
            "status": "NOT_COLLECTED",
            "passed": None,
            "earnedScore": 0,
        }
    return {
        "mode": mode,
        "status": str(check.get("status") or "UNKNOWN"),
        "passed": check.get("passed"),
        "earnedScore": int(check.get("earnedScore") or 0),
        "sandboxExecuted": bool(check.get("sandboxExecuted")),
        "auditLogRef": (check.get("evidence") or {}).get("auditLogRef") if isinstance(check.get("evidence"), dict) else None,
    }


def _controlled_state(
    check: dict[str, Any] | None,
    *,
    check_type: str,
    controlled_requested: bool,
    controlled_warning: dict[str, Any] | None,
) -> dict[str, Any]:
    if check:
        return _evidence_state(check, "CONTROLLED_DOCKER_SANDBOX_POC")
    if check_type not in {"stdout_contains", "pytest"}:
        return {
            "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
            "status": "NOT_APPLICABLE",
            "passed": None,
            "earnedScore": 0,
        }
    if controlled_warning:
        return {
            "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
            "status": "RUNTIME_UNAVAILABLE",
            "passed": None,
            "earnedScore": 0,
            "warningCode": controlled_warning.get("code"),
        }
    return {
        "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
        "status": "NOT_REQUESTED" if not controlled_requested else "NOT_COLLECTED",
        "passed": None,
        "earnedScore": 0,
    }


def _selected_evidence(readonly_check: dict[str, Any] | None, controlled_check: dict[str, Any] | None) -> dict[str, Any]:
    if controlled_check and str(controlled_check.get("status")) in {"PASSED", "FAILED", "ERROR"}:
        return {
            "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
            "status": str(controlled_check.get("status")),
            "passed": controlled_check.get("passed"),
            "earnedScore": int(controlled_check.get("earnedScore") or 0),
            **_evidence_diagnostics(controlled_check),
        }
    if readonly_check and str(readonly_check.get("status")) in {"PASSED", "FAILED", "ERROR"}:
        return {
            "mode": "READONLY_REAL_SANDBOX_POC",
            "status": str(readonly_check.get("status")),
            "passed": readonly_check.get("passed"),
            "earnedScore": int(readonly_check.get("earnedScore") or 0),
            **_evidence_diagnostics(readonly_check),
        }
    return {
        "mode": "MISSING",
        "status": "MISSING",
        "passed": None,
        "earnedScore": 0,
    }


def _evidence_diagnostics(check: dict[str, Any]) -> dict[str, Any]:
    evidence = check.get("evidence") if isinstance(check.get("evidence"), dict) else {}
    error = check.get("error") if isinstance(check.get("error"), dict) else {}
    files = evidence.get("filesInspected") if isinstance(evidence.get("filesInspected"), list) else []
    return {
        "exitCode": evidence.get("exitCode"),
        "stdoutTail": _tail(evidence.get("stdout")),
        "stderrTail": _tail(evidence.get("stderr")),
        "filesInspected": [str(item) for item in files[:10]],
        "errorCode": error.get("code"),
        "errorReason": error.get("reason"),
    }


def _tail(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return ""
    return text[-DIAGNOSTIC_TAIL_CHARS:]


def _execution_matrix_reason(*, selected_status: str, selected_mode: str, recommended_next: str) -> str:
    if selected_mode == "CONTROLLED_DOCKER_SANDBOX_POC":
        return f"selected_controlled_docker_evidence_{selected_status.lower()}"
    if selected_mode == "READONLY_REAL_SANDBOX_POC":
        return f"selected_readonly_static_evidence_{selected_status.lower()}"
    return recommended_next


def _recommended_next_evidence(
    check_type: str,
    *,
    evidence_ready: bool,
    controlled_requested: bool,
    controlled_warning: dict[str, Any] | None,
) -> str:
    if evidence_ready:
        return "manual_review_ready_evidence"
    if check_type in {"stdout_contains", "pytest"}:
        if controlled_warning:
            return "prepare_controlled_docker_runtime_or_manual_review"
        if not controlled_requested:
            return "run_evidence_auto_with_controlled_command"
        return "review_controlled_command_failure"
    if check_type in {"file_exists", "json_field", "notebook_cell", "log_keyword"}:
        return "fix_submission_or_grading_static_evidence"
    return "manual_review_only"


def _next_core_action(
    execution_matrix: dict[str, Any],
    *,
    controlled_requested: bool,
    controlled_warning: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = execution_matrix["summary"]
    if summary["controlledCommandMissingTotal"] and not controlled_requested:
        return {
            "id": "run_evidence_auto_with_controlled_command",
            "label": "Run evidence-auto with controlled command evidence",
            "reason": "stdout_contains/pytest checks still need controlled Docker evidence.",
            "api": {
                "method": "POST",
                "path": "/api/grading/evidence-auto",
                "bodyPatch": {"includeControlledCommand": True},
            },
            "cli": "python lab_cli.py grade evidence-auto --include-controlled-command --grading <grading> --submission <submission> --output <output>",
            "safety": _next_action_safety(),
        }
    if controlled_warning:
        return {
            "id": "prepare_controlled_docker_runtime_or_manual_review",
            "label": "Prepare controlled Docker runtime or record manual review",
            "reason": str(controlled_warning.get("message") or "Controlled Docker evidence was unavailable."),
            "api": {
                "method": "POST",
                "path": "/api/grading/evidence-auto",
                "bodyPatch": {"includeControlledCommand": True, "failOnControlledUnavailable": True},
            },
            "cli": "python lab_cli.py grade evidence-auto --include-controlled-command --fail-on-controlled-unavailable --grading <grading> --submission <submission> --output <output>",
            "safety": _next_action_safety(),
        }
    if summary["missingEvidenceTotal"]:
        return {
            "id": "fix_submission_or_grading_static_evidence",
            "label": "Fix submission paths or grading static evidence",
            "reason": "Some read-only/static checks still have no collected evidence.",
            "api": {"method": "POST", "path": "/api/grading/evidence-auto"},
            "cli": "python lab_cli.py grade evidence-auto --grading <grading> --submission <submission> --output <output>",
            "safety": _next_action_safety(),
        }
    return {
        "id": "review_score_and_record_decision_note",
        "label": "Review score and record decision note",
        "reason": "All checks have collected evidence; human review is still required before approval.",
        "api": {"method": "POST", "path": "/api/review-tasks/{id}/decision-note"},
        "cli": "python lab_cli.py review decision-note --task-id <taskId> --note <note>",
        "safety": _next_action_safety(),
    }


def _build_manual_review_checklist(
    execution_matrix: dict[str, Any],
    *,
    next_core_action: dict[str, Any],
    controlled_warning: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = execution_matrix["summary"]
    items = [_manual_review_item(item) for item in execution_matrix["items"]]
    ready_items = [item for item in items if item["readyForDecision"]]
    missing_items = [item for item in items if not item["readyForDecision"]]
    if controlled_warning:
        status = "CONTROLLED_RUNTIME_UNAVAILABLE"
    elif not missing_items:
        status = "READY_FOR_DECISION_NOTE"
    elif summary["controlledCommandMissingTotal"]:
        status = "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    else:
        status = "NEEDS_STATIC_EVIDENCE_REVIEW"

    return {
        "component": "GradingEvidenceAutoManualReviewChecklist",
        "mode": "GRADING_EVIDENCE_AUTO_MANUAL_REVIEW_CHECKLIST",
        "source": "GRADING_EVIDENCE_AUTO_REPORT.executionMatrix",
        "status": status,
        "summary": {
            "itemTotal": len(items),
            "readyForDecisionTotal": len(ready_items),
            "missingEvidenceTotal": len(missing_items),
            "controlledCommandMissingTotal": summary["controlledCommandMissingTotal"],
            "readonlyStaticMissingTotal": sum(
                1
                for item in missing_items
                if item["recommendedDecision"] == "needs-revision"
            ),
            "readyForApprovalRecommendation": summary["readyForApprovalRecommendation"],
            "nextCoreActionId": next_core_action["id"],
        },
        "decisionNoteRecommendation": _decision_note_recommendation(status, next_core_action),
        "items": items,
        "safety": {
            "manualReviewRequired": True,
            "singleTaskDecisionNoteOnly": True,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "hostExecutionAllowedByChecklist": False,
            "networkEnabledByChecklist": False,
        },
    }


def _manual_review_item(item: dict[str, Any]) -> dict[str, Any]:
    selected = item.get("selectedEvidence", {})
    controlled = item.get("controlledCommandEvidence", {})
    readonly = item.get("readonlyEvidence", {})
    evidence_ready = item["evidenceReady"] is True
    recommended_next = str(item.get("recommendedNextEvidence") or "manual_review_only")
    if evidence_ready:
        if selected.get("mode") == "CONTROLLED_DOCKER_SANDBOX_POC":
            review_action = "verify_controlled_docker_output_and_score"
        elif selected.get("mode") == "READONLY_REAL_SANDBOX_POC":
            review_action = "verify_static_evidence_and_score"
        else:
            review_action = "verify_existing_evidence_and_score"
        decision = "approve-ready"
    elif recommended_next == "run_evidence_auto_with_controlled_command":
        review_action = "collect_controlled_command_evidence_before_decision_note"
        decision = "needs-evidence"
    elif recommended_next == "prepare_controlled_docker_runtime_or_manual_review":
        review_action = "prepare_controlled_docker_runtime_or_record_needs_evidence"
        decision = "needs-evidence"
    elif recommended_next == "fix_submission_or_grading_static_evidence":
        review_action = "request_static_submission_or_grading_revision"
        decision = "needs-revision"
    else:
        review_action = "perform_manual_review_before_decision_note"
        decision = "needs-evidence"

    return {
        "checkId": item["checkId"],
        "checkType": item["checkType"],
        "score": item["score"],
        "readyForDecision": evidence_ready,
        "selectedEvidenceMode": selected.get("mode"),
        "selectedEvidenceStatus": selected.get("status"),
        "readonlyEvidenceStatus": readonly.get("status"),
        "controlledCommandEvidenceStatus": controlled.get("status"),
        "recommendedReviewAction": review_action,
        "recommendedDecision": decision,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _decision_note_recommendation(status: str, next_core_action: dict[str, Any]) -> dict[str, Any]:
    if status == "READY_FOR_DECISION_NOTE":
        decision = "approve-ready"
        reason = "All checks have collected evidence and still require human score review."
    elif status == "NEEDS_STATIC_EVIDENCE_REVIEW":
        decision = "needs-revision"
        reason = "Static evidence is missing or does not match grading/submission expectations."
    else:
        decision = "needs-evidence"
        reason = "Controlled command evidence is missing or runtime is unavailable."
    return {
        "decision": decision,
        "reason": reason,
        "nextCoreActionId": next_core_action["id"],
        "api": {"method": "POST", "path": "/api/review-tasks/{id}/decision-note"},
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
    }


def _next_action_safety() -> dict[str, Any]:
    return {
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "hostExecutionAllowed": False,
        "networkEnabled": False,
    }
