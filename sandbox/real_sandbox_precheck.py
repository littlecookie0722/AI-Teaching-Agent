"""Real sandbox readiness precheck for Grading DSL reports.

This module summarizes whether a validated Grading DSL and its mock execution
plan are ready to hand to a future real sandbox implementation. It never starts
containers, executes commands, runs notebooks, or inspects contestant code.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import uuid4

from sandbox.grade_runner import SANDBOX_POLICY, SUPPORTED_CHECK_TYPES, GradingRunner, GradingRunnerError


PRECHECK_MODE = "REAL_SANDBOX_PRECHECK_ONLY"
PRECHECK_STATUS_READY = "READY_FOR_MANUAL_SANDBOX_REVIEW"
PRECHECK_STATUS_BLOCKED = "BLOCKED_BEFORE_REAL_SANDBOX"


def build_real_sandbox_precheck_report(grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
    """Build a readiness report without executing the real sandbox."""

    try:
        grading_report = GradingRunner().run(grading, trace_id)
    except GradingRunnerError as exc:
        return _build_blocked_report_from_runner_error(grading, trace_id, exc)

    blockers = _collect_blockers(grading_report)
    warnings = _collect_warnings(grading_report)
    ready = not blockers

    return {
        "id": f"real_sandbox_precheck_{uuid4().hex[:12]}",
        "mode": PRECHECK_MODE,
        "phase": "Phase 3",
        "gradingId": grading_report["gradingId"],
        "sourceReportId": grading_report["id"],
        "readiness": {
            "status": PRECHECK_STATUS_READY if ready else PRECHECK_STATUS_BLOCKED,
            "readyForRealSandboxImplementation": ready,
            "readyForRealSandboxExecution": False,
            "manualReviewRequired": True,
            "blockers": blockers,
            "warnings": warnings,
        },
        "summary": _build_summary(grading_report),
        "requiredBeforeRealExecution": _required_before_real_execution(),
        "checkPreviews": _build_check_previews(grading_report),
        "safety": {
            "sandboxExecuted": False,
            "realSandboxRunEnabled": False,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
            "unknownShellExecuted": False,
            "networkEnabled": False,
            "hostExecutionAllowed": False,
            "realPublish": False,
        },
        "gradingReport": grading_report,
        "traceId": trace_id,
        "note": "Precheck only validates the planned grading contract; no real sandbox or contestant code was executed.",
    }


def _build_blocked_report_from_runner_error(
    grading: dict[str, Any],
    trace_id: str,
    exc: GradingRunnerError,
) -> dict[str, Any]:
    checks = grading.get("spec", {}).get("checks", [])
    check_types = Counter(str(check.get("type")) for check in checks if isinstance(check, dict))
    blockers = [
        {
            "code": "GRADING_RUNNER_PLAN_INVALID",
            "field": error.get("field", "spec.checks"),
            "reason": error.get("reason", exc.message),
        }
        for error in exc.errors
    ]
    if not blockers:
        blockers.append({"code": exc.code, "field": "spec.checks", "reason": exc.message})

    total_score = grading.get("spec", {}).get("totalScore")
    score_sum = sum(int(check.get("score", 0)) for check in checks if isinstance(check, dict))
    assessment_plan = grading.get("spec", {}).get("assessmentPlan", [])
    assessment_plan_ids = {
        str(plan.get("checkId"))
        for plan in assessment_plan
        if isinstance(plan, dict) and plan.get("checkId")
    }
    check_ids = {str(check.get("id")) for check in checks if isinstance(check, dict) and check.get("id")}

    return {
        "id": f"real_sandbox_precheck_{uuid4().hex[:12]}",
        "mode": PRECHECK_MODE,
        "phase": "Phase 3",
        "gradingId": grading.get("metadata", {}).get("id"),
        "sourceReportId": None,
        "readiness": {
            "status": PRECHECK_STATUS_BLOCKED,
            "readyForRealSandboxImplementation": False,
            "readyForRealSandboxExecution": False,
            "manualReviewRequired": True,
            "blockers": blockers,
            "warnings": [
                {
                    "code": "MOCK_GRADING_PLAN_NOT_BUILT",
                    "field": "gradingReport",
                    "reason": "GradingRunner could not build a complete plan; fix blockers before real sandbox implementation.",
                }
            ],
        },
        "summary": {
            "totalScore": total_score,
            "checkTotal": len(checks) if isinstance(checks, list) else 0,
            "plannedOnly": 0,
            "executed": 0,
            "scoreTotalMatchesSpec": score_sum == total_score,
            "checkTypes": {check_type: check_types.get(check_type, 0) for check_type in SUPPORTED_CHECK_TYPES},
            "supportedCheckTypes": list(SUPPORTED_CHECK_TYPES),
            "riskLevels": [],
            "assessmentPlan": {
                "source": "grading.spec.assessmentPlan",
                "planTotal": len(assessment_plan) if isinstance(assessment_plan, list) else 0,
                "checkTotal": len(check_ids),
                "alignedWithChecks": bool(assessment_plan_ids) and assessment_plan_ids == check_ids,
                "missingPlanForChecks": sorted(check_ids - assessment_plan_ids),
                "orphanPlanCheckIds": sorted(assessment_plan_ids - check_ids),
                "realSandboxEvidenceRequired": True,
                "sandboxRequiredBeforeRealExecution": True,
            },
            "sandboxPolicy": dict(SANDBOX_POLICY),
        },
        "requiredBeforeRealExecution": _required_before_real_execution(),
        "checkPreviews": _build_raw_check_previews(grading),
        "safety": {
            "sandboxExecuted": False,
            "realSandboxRunEnabled": False,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
            "unknownShellExecuted": False,
            "networkEnabled": False,
            "hostExecutionAllowed": False,
            "realPublish": False,
        },
        "gradingReport": None,
        "traceId": trace_id,
        "note": "Precheck blocked before mock grading plan construction; no real sandbox or contestant code was executed.",
    }


def _collect_blockers(report: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    check_summary = report.get("checkSummary", {})
    plan_summary = report.get("assessmentPlanSummary", {})

    if check_summary.get("scoreTotalMatchesSpec") is not True:
        blockers.append(
            {
                "code": "SCORE_TOTAL_MISMATCH",
                "field": "spec.totalScore",
                "reason": "sum(checks[].score) must match spec.totalScore before real sandbox implementation.",
            }
        )

    if plan_summary.get("alignedWithChecks") is not True:
        blockers.append(
            {
                "code": "ASSESSMENT_PLAN_NOT_ALIGNED",
                "field": "spec.assessmentPlan",
                "reason": "assessmentPlan must contain one aligned plan for every grading check.",
            }
        )

    for check_id in plan_summary.get("missingPlanForChecks", []):
        blockers.append(
            {
                "code": "ASSESSMENT_PLAN_MISSING_CHECK",
                "field": f"spec.assessmentPlan[checkId={check_id}]",
                "reason": "missing assessment plan for grading check.",
            }
        )

    for check_id in plan_summary.get("orphanPlanCheckIds", []):
        blockers.append(
            {
                "code": "ASSESSMENT_PLAN_ORPHAN_CHECK",
                "field": f"spec.assessmentPlan[checkId={check_id}]",
                "reason": "assessment plan references a check that does not exist.",
            }
        )

    for check in report.get("checks", []):
        check_id = str(check.get("id"))
        if check.get("type") not in SUPPORTED_CHECK_TYPES:
            blockers.append(
                {
                    "code": "UNSUPPORTED_CHECK_TYPE",
                    "field": f"spec.checks[checkId={check_id}].type",
                    "reason": str(check.get("type")),
                }
            )
        if check.get("assessmentPlanAlignedWithCheck") is not True:
            blockers.append(
                {
                    "code": "CHECK_PLAN_TRACE_MISMATCH",
                    "field": f"spec.assessmentPlan[checkId={check_id}]",
                    "reason": "assessment plan type, runner, or score does not match the check report.",
                }
            )
        _append_request_blockers(blockers, check)
        _append_container_plan_blockers(blockers, check)
        _append_limit_blockers(blockers, check)

    return blockers


def _append_request_blockers(blockers: list[dict[str, str]], check: dict[str, Any]) -> None:
    check_id = str(check.get("id"))
    request = check.get("sandboxExecutionRequest", {})
    if request.get("mode") != "REAL_SANDBOX_REQUIRED":
        blockers.append(
            {
                "code": "SANDBOX_REQUEST_NOT_DECLARED",
                "field": f"checks.{check_id}.sandboxExecutionRequest.mode",
                "reason": "future real sandbox execution request must be declared.",
            }
        )
    safety = request.get("safety", {})
    if safety.get("hostExecutionAllowed") is not False:
        blockers.append(
            {
                "code": "HOST_EXECUTION_NOT_BLOCKED",
                "field": f"checks.{check_id}.sandboxExecutionRequest.safety.hostExecutionAllowed",
                "reason": "host execution must be blocked before real sandbox implementation.",
            }
        )


def _append_container_plan_blockers(blockers: list[dict[str, str]], check: dict[str, Any]) -> None:
    check_id = str(check.get("id"))
    container_plan = check.get("containerSandboxPlan", {})
    if container_plan.get("mode") != "CONTAINER_PLAN_ONLY" or container_plan.get("status") != "PLANNED":
        blockers.append(
            {
                "code": "CONTAINER_PLAN_MISSING",
                "field": f"checks.{check_id}.containerSandboxPlan",
                "reason": "container dry-run plan must exist before real sandbox implementation.",
            }
        )
    safety = container_plan.get("safety", {})
    if safety.get("containerStarted") is not False:
        blockers.append(
            {
                "code": "PRECHECK_STARTED_CONTAINER",
                "field": f"checks.{check_id}.containerSandboxPlan.safety.containerStarted",
                "reason": "precheck must not start containers.",
            }
        )


def _append_limit_blockers(blockers: list[dict[str, str]], check: dict[str, Any]) -> None:
    check_id = str(check.get("id"))
    limits = check.get("sandboxExecutionRequest", {}).get("limits", {})
    required_fields = ("timeoutSeconds", "cpuCores", "memoryMb", "processLimit", "network", "filesystem")
    for field in required_fields:
        if field not in limits:
            blockers.append(
                {
                    "code": "SANDBOX_LIMIT_MISSING",
                    "field": f"checks.{check_id}.sandboxExecutionRequest.limits.{field}",
                    "reason": "real sandbox limit must be declared before implementation.",
                }
            )


def _collect_warnings(report: dict[str, Any]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    risk_counts = Counter(str(check.get("riskLevel", "")).upper() for check in report.get("checks", []))
    if risk_counts.get("HIGH", 0) > 0:
        warnings.append(
            {
                "code": "HIGH_RISK_CHECK_REQUIRES_EXTRA_REVIEW",
                "field": "checks[].riskLevel",
                "reason": "high risk checks such as notebook execution need extra manual sandbox review.",
            }
        )
    if report.get("explainability", {}).get("realSandboxEvidenceRequired") is True:
        warnings.append(
            {
                "code": "REAL_EVIDENCE_NOT_COLLECTED",
                "field": "checks[].mockEvidence",
                "reason": "mock evidence placeholders are expected; collect real evidence only after sandbox implementation.",
            }
        )
    return warnings


def _build_summary(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks", [])
    return {
        "totalScore": report.get("totalScore"),
        "checkTotal": report.get("checkSummary", {}).get("total"),
        "plannedOnly": report.get("checkSummary", {}).get("plannedOnly"),
        "executed": report.get("checkSummary", {}).get("executed"),
        "scoreTotalMatchesSpec": report.get("checkSummary", {}).get("scoreTotalMatchesSpec"),
        "checkTypes": report.get("checkSummary", {}).get("byType", {}),
        "supportedCheckTypes": list(SUPPORTED_CHECK_TYPES),
        "riskLevels": sorted({str(check.get("riskLevel")) for check in checks if check.get("riskLevel")}),
        "assessmentPlan": report.get("assessmentPlanSummary", {}),
        "sandboxPolicy": dict(SANDBOX_POLICY),
    }


def _required_before_real_execution() -> list[dict[str, Any]]:
    return [
        {"id": "manual_review_approval", "label": "人工审核通过", "ready": False},
        {"id": "real_sandbox_executor_implementation", "label": "真实 SandboxExecutor 实现", "ready": False},
        {"id": "isolated_submission_workspace", "label": "隔离选手提交目录", "ready": True},
        {"id": "resource_limits", "label": "CPU / 内存 / 超时 / 进程限制", "ready": True},
        {"id": "network_disabled_by_default", "label": "网络默认关闭", "ready": True},
        {"id": "stdout_stderr_exitcode_capture", "label": "stdout / stderr / exitCode / durationMs 证据采集", "ready": True},
        {"id": "audit_log_ref", "label": "评分审计日志引用", "ready": True},
    ]


def _build_check_previews(report: dict[str, Any]) -> list[dict[str, Any]]:
    previews = []
    for check in report.get("checks", []):
        sandbox_request = check.get("sandboxExecutionRequest", {})
        container_plan = check.get("containerSandboxPlan", {})
        previews.append(
            {
                "id": check.get("id"),
                "type": check.get("type"),
                "runner": check.get("runner"),
                "score": check.get("score"),
                "riskLevel": check.get("riskLevel"),
                "assessmentPlanAlignedWithCheck": check.get("assessmentPlanAlignedWithCheck"),
                "executionStrategy": check.get("executionPlan", {}).get("strategy"),
                "sandboxRequestMode": sandbox_request.get("mode"),
                "containerPlanMode": container_plan.get("mode"),
                "containerPlanStatus": container_plan.get("status"),
                "requiredLimits": sandbox_request.get("limits", {}),
                "evidenceRequired": sandbox_request.get("evidenceRequired", []),
                "realExecutionDeferred": True,
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
            }
        )
    return previews


def _build_raw_check_previews(grading: dict[str, Any]) -> list[dict[str, Any]]:
    previews = []
    for check in grading.get("spec", {}).get("checks", []):
        if not isinstance(check, dict):
            continue
        previews.append(
            {
                "id": check.get("id"),
                "type": check.get("type"),
                "runner": None,
                "score": check.get("score"),
                "riskLevel": None,
                "assessmentPlanAlignedWithCheck": False,
                "executionStrategy": None,
                "sandboxRequestMode": None,
                "containerPlanMode": None,
                "containerPlanStatus": None,
                "requiredLimits": {},
                "evidenceRequired": [],
                "realExecutionDeferred": True,
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
            }
        )
    return previews
