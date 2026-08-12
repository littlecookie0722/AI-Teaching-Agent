"""Mock-only grading runner interfaces for Phase 3.

The runner builds a deterministic grading report from a validated Grading DSL.
It plans supported check types but never executes commands, pytest, contestant
code, or host filesystem checks.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Protocol
from uuid import uuid4

from sandbox.container_executor import build_container_sandbox_plan
from sandbox.execution_contract import build_sandbox_execution_request


SUPPORTED_CHECK_TYPES = ("file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword")

SANDBOX_POLICY = {
    "executorBoundary": "SandboxExecutor",
    "mode": "MOCK_ONLY",
    "hostExecutionAllowed": False,
    "realSandboxRunEnabled": False,
    "networkEnabled": False,
    "filesystemIsolationRequired": True,
    "cpuLimitRequired": True,
    "memoryLimitRequired": True,
    "timeoutRequired": True,
    "processLimitRequired": True,
    "stdoutCapturedRequired": True,
    "stderrCapturedRequired": True,
    "auditLogRequired": True,
}

CHECK_RUNNERS = {
    "file_exists": "FileExistsGrader",
    "stdout_contains": "StdoutContainsGrader",
    "pytest": "PytestGrader",
    "notebook_cell": "NotebookGrader",
    "json_field": "JsonFieldGrader",
    "log_keyword": "LogKeywordGrader",
}

CHECK_REQUIRED_FIELDS = {
    "file_exists": ("path",),
    "stdout_contains": ("command", "expected"),
    "pytest": ("path",),
    "notebook_cell": ("notebookPath", "cellIndex", "expected"),
    "json_field": ("path", "jsonPath", "expectedValue"),
    "log_keyword": ("path", "expected"),
}


class GradingRunnerError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class SandboxExecutor(Protocol):
    mode: str
    executor_id: str

    def execute_check(self, check: dict[str, Any], *, grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
        ...


def _required_field_errors(check: dict[str, Any]) -> list[dict[str, str]]:
    check_type = str(check.get("type", ""))
    errors: list[dict[str, str]] = []
    for field in CHECK_REQUIRED_FIELDS.get(check_type, ()):
        value = check.get(field)
        if field == "expected":
            if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
                errors.append({"field": f"checks.{check.get('id', '<unknown>')}.{field}", "reason": "must be a non-empty string array"})
        elif field == "expectedValue":
            if value is None:
                errors.append({"field": f"checks.{check.get('id', '<unknown>')}.{field}", "reason": "must be present"})
        elif field == "cellIndex":
            if not isinstance(value, int) or value < 0:
                errors.append({"field": f"checks.{check.get('id', '<unknown>')}.{field}", "reason": "must be a non-negative integer"})
        elif not isinstance(value, str) or not value:
            errors.append({"field": f"checks.{check.get('id', '<unknown>')}.{field}", "reason": "must be a non-empty string"})
    return errors


def _input_summary(check: dict[str, Any]) -> dict[str, Any]:
    check_type = str(check["type"])
    if check_type == "file_exists":
        return {"path": check.get("path")}
    if check_type == "stdout_contains":
        return {
            "command": check.get("command"),
            "expectedTokenCount": len(check.get("expected", [])),
        }
    if check_type == "pytest":
        return {"path": check.get("path")}
    if check_type == "notebook_cell":
        return {
            "notebookPath": check.get("notebookPath"),
            "cellIndex": check.get("cellIndex"),
            "expectedTokenCount": len(check.get("expected", [])),
        }
    if check_type == "json_field":
        return {
            "path": check.get("path"),
            "jsonPath": check.get("jsonPath"),
            "expectedValueType": type(check.get("expectedValue")).__name__,
        }
    if check_type == "log_keyword":
        return {
            "path": check.get("path"),
            "expectedTokenCount": len(check.get("expected", [])),
        }
    return {}


def _mock_evidence(check: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "MOCK_EVIDENCE_NOT_COLLECTED",
        "reason": "Phase 3 Mock runner does not execute checks or inspect contestant submissions.",
        "stdout": None,
        "stderr": None,
        "filesInspected": [],
        "pytestNodeIds": [],
        "artifacts": [],
        "traceableWhenRealSandboxEnabled": True,
    }


def _risk_level(check: dict[str, Any]) -> str:
    check_type = str(check["type"])
    if check_type == "file_exists":
        return "LOW"
    if check_type == "json_field":
        return "LOW"
    if check_type == "notebook_cell":
        return "HIGH"
    return "MEDIUM"


def _assessment_plan_by_check_id(grading: dict[str, Any]) -> dict[str, dict[str, Any]]:
    plans = grading.get("spec", {}).get("assessmentPlan", [])
    if not isinstance(plans, list):
        return {}
    return {str(plan.get("checkId")): plan for plan in plans if isinstance(plan, dict) and plan.get("checkId")}


def _assessment_plan_summary(grading: dict[str, Any], check_reports: list[dict[str, Any]]) -> dict[str, Any]:
    plans = _assessment_plan_by_check_id(grading)
    check_ids = [str(check.get("id")) for check in check_reports]
    aligned = bool(plans) and set(plans) == set(check_ids)
    return {
        "source": "grading.spec.assessmentPlan",
        "planTotal": len(plans),
        "checkTotal": len(check_reports),
        "checkIds": sorted(plans),
        "alignedWithChecks": aligned,
        "missingPlanForChecks": [check_id for check_id in check_ids if check_id not in plans],
        "orphanPlanCheckIds": [check_id for check_id in sorted(plans) if check_id not in check_ids],
        "executionStrategies": sorted(
            {
                str(plan.get("executionPlan", {}).get("strategy"))
                for plan in plans.values()
                if isinstance(plan.get("executionPlan"), dict) and plan.get("executionPlan", {}).get("strategy")
            }
        ),
        "mockEvidenceStatuses": sorted(
            {
                str(plan.get("mockEvidence", {}).get("status"))
                for plan in plans.values()
                if isinstance(plan.get("mockEvidence"), dict) and plan.get("mockEvidence", {}).get("status")
            }
        ),
        "riskLevels": sorted({str(plan.get("riskLevel")) for plan in plans.values() if plan.get("riskLevel")}),
        "realSandboxEvidenceRequired": True,
        "sandboxRequiredBeforeRealExecution": True,
    }


def _apply_assessment_plan_trace(check_report: dict[str, Any], plan: dict[str, Any] | None) -> dict[str, Any]:
    if not plan:
        return {
            **check_report,
            "assessmentPlanSource": "grading.spec.assessmentPlan",
            "assessmentPlanSourceField": None,
            "assessmentPlanAlignedWithCheck": False,
        }

    check_id = str(check_report.get("id"))
    plan_type = plan.get("type")
    plan_runner = plan.get("runner")
    plan_score = plan.get("score")
    aligned = (
        plan.get("checkId") == check_id
        and plan_type == check_report.get("type")
        and plan_runner == check_report.get("runner")
        and int(plan_score) == int(check_report.get("score", 0))
    )
    return {
        **check_report,
        "assessmentPlanSource": "grading.spec.assessmentPlan",
        "assessmentPlanSourceField": f"spec.assessmentPlan[checkId={check_id}]",
        "assessmentPlanAlignedWithCheck": aligned,
        "assessmentPlanInputSummary": plan.get("inputSummary"),
        "assessmentPlanExecutionPlan": plan.get("executionPlan", {}),
        "assessmentPlanMockEvidence": plan.get("mockEvidence", {}),
        "assessmentPlanRiskLevel": plan.get("riskLevel"),
        "assessmentPlanSandboxRequiredBeforeRealExecution": plan.get("sandboxRequiredBeforeRealExecution", True),
    }


def build_grading_check_plan_fields(check: dict[str, Any], *, grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
    """Build canonical planning fields for one Grading DSL check without executing it."""

    check_type = str(check.get("type"))
    if check_type not in SUPPORTED_CHECK_TYPES:
        raise GradingRunnerError(
            "VALIDATION_ERROR",
            "Unsupported grading check type",
            [{"field": f"checks.{check.get('id', '<unknown>')}.type", "reason": check_type}],
        )
    sandbox_request = build_sandbox_execution_request(check, grading=grading, trace_id=trace_id)
    plan = _assessment_plan_by_check_id(grading).get(str(check.get("id")))
    return _apply_assessment_plan_trace(
        {
            "id": check.get("id"),
            "type": check_type,
            "runner": CHECK_RUNNERS[check_type],
            "score": int(check.get("score", 0)),
            "inputSummary": _input_summary(check),
            "executionPlan": _execution_plan(check),
            "sandboxExecutionRequest": sandbox_request,
            "containerSandboxPlan": build_container_sandbox_plan(sandbox_request),
            "mockEvidence": _mock_evidence(check),
            "riskLevel": _risk_level(check),
        },
        plan,
    )


def build_assessment_plan_summary(grading: dict[str, Any], check_reports: list[dict[str, Any]]) -> dict[str, Any]:
    return _assessment_plan_summary(grading, check_reports)


def _execution_plan(check: dict[str, Any]) -> dict[str, Any]:
    check_type = str(check["type"])
    base = {
        "strategy": "MOCK_PLAN_ONLY",
        "executorBoundary": SANDBOX_POLICY["executorBoundary"],
        "wouldRunInsideRealSandbox": True,
        "sandboxExecuted": False,
        "commandExecuted": False,
        "contestantCodeExecuted": False,
        "hostExecutionAllowed": False,
        "networkEnabled": False,
        "requiredLimits": {
            "cpu": "required_before_real_execution",
            "memory": "required_before_real_execution",
            "timeoutSeconds": "required_before_real_execution",
            "processCount": "required_before_real_execution",
            "filesystem": "isolated_submission_workspace_required",
            "network": "disabled_by_default",
        },
        "evidenceToCollectInRealSandbox": [
            "stdout",
            "stderr",
            "exitCode",
            "durationMs",
            "matchedEvidence",
            "auditLogRef",
        ],
    }
    if check_type == "file_exists":
        return {
            **base,
            "action": "verify_file_exists",
            "path": check.get("path"),
            "description": "Future real sandbox checks that the file exists inside the isolated submission workspace.",
        }
    if check_type == "stdout_contains":
        return {
            **base,
            "action": "run_command_and_match_stdout",
            "command": check.get("command"),
            "expected": list(check.get("expected", [])),
            "description": "Future real sandbox runs the command and matches stdout against expected tokens.",
        }
    if check_type == "pytest":
        return {
            **base,
            "action": "run_pytest_suite",
            "path": check.get("path"),
            "description": "Future real sandbox runs pytest against the referenced test path.",
        }
    if check_type == "notebook_cell":
        return {
            **base,
            "action": "run_notebook_cell_and_match_output",
            "notebookPath": check.get("notebookPath"),
            "cellIndex": check.get("cellIndex"),
            "expected": list(check.get("expected", [])),
            "description": "Future real sandbox executes the configured notebook cell in isolation and matches captured output tokens.",
        }
    if check_type == "json_field":
        return {
            **base,
            "action": "inspect_json_field",
            "path": check.get("path"),
            "jsonPath": check.get("jsonPath"),
            "expectedValue": check.get("expectedValue"),
            "description": "Future real sandbox reads JSON inside the isolated submission workspace and compares the configured field.",
        }
    if check_type == "log_keyword":
        return {
            **base,
            "action": "inspect_log_keywords",
            "path": check.get("path"),
            "expected": list(check.get("expected", [])),
            "description": "Future real sandbox reads the configured log file inside the isolated workspace and matches expected keywords.",
        }
    raise GradingRunnerError(
        "VALIDATION_ERROR",
        "Unsupported grading check type",
        [{"field": f"checks.{check.get('id', '<unknown>')}.type", "reason": check_type}],
    )


class MockCheckExecutor:
    mode = "MOCK_ONLY"
    executor_id = "mock_check_executor"

    def execute_check(self, check: dict[str, Any], *, grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
        errors = _required_field_errors(check)
        if errors:
            raise GradingRunnerError("VALIDATION_ERROR", "Grading check input is incomplete", errors)

        score = int(check["score"])
        check_type = str(check["type"])
        sandbox_execution_request = build_sandbox_execution_request(check, grading=grading, trace_id=trace_id)
        container_sandbox_plan = build_container_sandbox_plan(sandbox_execution_request)
        return {
            "id": check["id"],
            "type": check_type,
            "runner": CHECK_RUNNERS[check_type],
            "executor": self.executor_id,
            "score": score,
            "earnedScore": score,
            "passed": True,
            "mode": self.mode,
            "executionMode": self.mode,
            "executionPlan": _execution_plan(check),
            "sandboxExecutionRequest": sandbox_execution_request,
            "containerSandboxPlan": container_sandbox_plan,
            "inputSummary": _input_summary(check),
            "mockEvidence": _mock_evidence(check),
            "riskLevel": _risk_level(check),
            "explanation": "Mock runner awards configured score without inspecting a real submission; human review and real sandbox are required before production scoring.",
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
            "unknownShellExecuted": False,
            "networkEnabled": False,
            "filesystemIsolated": True,
            "traceId": trace_id,
            "logs": [],
        }


class GradingRunner:
    runner_id = "mock_grading_runner"
    mode = "MOCK_ONLY"

    def __init__(self, executor: SandboxExecutor | None = None) -> None:
        self.executor = executor or MockCheckExecutor()

    def run(self, grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
        checks = grading["spec"]["checks"]
        unsupported = [check for check in checks if check.get("type") not in SUPPORTED_CHECK_TYPES]
        if unsupported:
            raise GradingRunnerError(
                "VALIDATION_ERROR",
                "Unsupported grading check type",
                [{"field": f"checks.{check.get('id', '<unknown>')}.type", "reason": str(check.get("type"))} for check in unsupported],
            )

        assessment_plans = _assessment_plan_by_check_id(grading)
        check_reports = [
            _apply_assessment_plan_trace(
                self.executor.execute_check(check, grading=grading, trace_id=trace_id),
                assessment_plans.get(str(check.get("id"))),
            )
            for check in checks
        ]
        total_score = int(grading["spec"]["totalScore"])
        earned_score = sum(int(check["earnedScore"]) for check in check_reports)
        type_counts = Counter(check["type"] for check in check_reports)
        assessment_plan_summary = _assessment_plan_summary(grading, check_reports)

        return {
            "id": f"grading_report_{uuid4().hex[:12]}",
            "mode": self.mode,
            "phase": "Phase 3",
            "gradingId": grading["metadata"]["id"],
            "totalScore": total_score,
            "earnedScore": earned_score,
            "passed": earned_score >= total_score and all(check["passed"] for check in check_reports),
            "runner": {
                "id": self.runner_id,
                "mode": self.mode,
                "executor": self.executor.executor_id,
                "supportedCheckTypes": list(SUPPORTED_CHECK_TYPES),
                "strategy": "MOCK_PLAN_ONLY",
                "realSandboxExecuted": False,
                "hostExecutionAllowed": False,
            },
            "sandboxPolicy": dict(SANDBOX_POLICY),
            "checkSummary": {
                "total": len(check_reports),
                "passed": sum(1 for check in check_reports if check["passed"]),
                "executed": 0,
                "plannedOnly": len(check_reports),
                "byType": {check_type: type_counts.get(check_type, 0) for check_type in SUPPORTED_CHECK_TYPES},
                "scoreTotalMatchesSpec": sum(int(check["score"]) for check in check_reports) == total_score,
            },
            "assessmentPlanSummary": assessment_plan_summary,
            "explainability": {
                "status": "EXPLAINABLE_MOCK_PLAN",
                "eachCheckHasPlan": all(bool(check.get("executionPlan")) for check in check_reports),
                "eachCheckHasInputSummary": all(bool(check.get("inputSummary")) for check in check_reports),
                "eachCheckHasMockEvidencePlaceholder": all(bool(check.get("mockEvidence")) for check in check_reports),
                "assessmentPlanSource": assessment_plan_summary["source"],
                "assessmentPlanAlignedWithChecks": assessment_plan_summary["alignedWithChecks"],
                "realSandboxEvidenceRequired": True,
            },
            "checks": check_reports,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "unknownShellExecuted": False,
            "commandExecuted": False,
            "networkEnabled": False,
            "filesystemIsolated": True,
            "realSandboxRequiredBeforeExecution": True,
            "traceId": trace_id,
            "note": "Phase 3 Mock grading runner only plans checks; it does not execute contestant code.",
        }


def build_mock_grading_report(grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
    return GradingRunner().run(grading, trace_id)


def _build_check_plans(report: dict[str, Any]) -> list[dict[str, Any]]:
    check_plans = []
    for check in report.get("checks", []):
        check_plans.append(
            {
                "id": check.get("id"),
                "type": check.get("type"),
                "runner": check.get("runner"),
                "score": check.get("score"),
                "earnedScore": check.get("earnedScore"),
                "passed": check.get("passed"),
                "inputSummary": check.get("inputSummary", {}),
                "executionPlan": check.get("executionPlan", {}),
                "sandboxExecutionRequest": check.get("sandboxExecutionRequest", {}),
                "containerSandboxPlan": check.get("containerSandboxPlan", {}),
                "mockEvidence": check.get("mockEvidence", {}),
                "riskLevel": check.get("riskLevel"),
                "assessmentPlanSource": check.get("assessmentPlanSource"),
                "assessmentPlanSourceField": check.get("assessmentPlanSourceField"),
                "assessmentPlanAlignedWithCheck": check.get("assessmentPlanAlignedWithCheck", False),
                "assessmentPlanInputSummary": check.get("assessmentPlanInputSummary"),
                "assessmentPlanExecutionPlan": check.get("assessmentPlanExecutionPlan", {}),
                "assessmentPlanMockEvidence": check.get("assessmentPlanMockEvidence", {}),
                "assessmentPlanRiskLevel": check.get("assessmentPlanRiskLevel"),
                "assessmentPlanSandboxRequiredBeforeRealExecution": check.get(
                    "assessmentPlanSandboxRequiredBeforeRealExecution",
                    True,
                ),
                "status": check.get("status"),
                "mode": check.get("mode"),
                "evidence": check.get("evidence", {}),
                "readonlyEvidence": check.get("readonlyEvidence", {}),
                "isolation": check.get("isolation", {}),
                "sandboxExecuted": check.get("sandboxExecuted", False),
                "contestantCodeExecuted": check.get("contestantCodeExecuted", False),
                "commandExecuted": check.get("commandExecuted", False),
                "unknownShellExecuted": check.get("unknownShellExecuted", False),
            }
        )
    return check_plans


def build_grading_audit_detail(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "gradingId": report["gradingId"],
        "phase": report.get("phase"),
        "runner": report.get("runner", {}),
        "sandboxPolicy": report.get("sandboxPolicy", {}),
        "isolation": report.get("isolation", {}),
        "checkSummary": report.get("checkSummary", {}),
        "assessmentPlanSummary": report.get("assessmentPlanSummary", {}),
        "explainability": report.get("explainability", {}),
        "checkPlans": _build_check_plans(report),
        "blockedActions": [
            "realSandboxRun",
            "executeGradingCommand",
            "runRealPytest",
            "executeContestantCode",
            "unknownShellExecution",
            "realPublish",
        ],
        "sandboxExecuted": report.get("sandboxExecuted", False),
        "contestantCodeExecuted": report.get("contestantCodeExecuted", False),
        "commandExecuted": report.get("commandExecuted", False),
        "unknownShellExecuted": report.get("unknownShellExecuted", False),
        "realSandboxRunEnabled": False,
        "hostExecutionAllowed": False,
        "runRealPytestEnabled": False,
        "realPublish": False,
    }


def build_grading_report_detail(report: dict[str, Any], audit_event: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the canonical report detail used by backend, CLI-facing artifacts, and UI mocks."""

    audit_detail = audit_event.get("detail", {}) if isinstance(audit_event, dict) else {}
    sandbox_policy = report.get("sandboxPolicy", {})
    report_safety = report.get("safety", {}) if isinstance(report.get("safety"), dict) else {}
    return {
        "source": "sandbox.grade_runner.build_grading_report_detail",
        "mode": report.get("mode"),
        "phase": report.get("phase"),
        "gradingId": report.get("gradingId"),
        "passed": report.get("passed"),
        "score": {
            "total": report.get("totalScore"),
            "earned": report.get("earnedScore"),
            "scoreTotalMatchesSpec": report.get("checkSummary", {}).get("scoreTotalMatchesSpec"),
        },
        "runner": report.get("runner", {}),
        "sandboxPolicy": sandbox_policy,
        "isolation": report.get("isolation", {}),
        "isolationQuality": report.get("isolationQuality", {}),
        "imageSupplyChain": report.get("imageSupplyChain", {}),
        "checkSummary": report.get("checkSummary", {}),
        "assessmentPlanSummary": report.get("assessmentPlanSummary", {}),
        "explainability": report.get("explainability", {}),
        "checkPlans": _build_check_plans(report),
        "safety": {
            "sandboxExecuted": report.get("sandboxExecuted", report_safety.get("sandboxExecuted", False)),
            "contestantCodeExecuted": report.get(
                "contestantCodeExecuted",
                report_safety.get("contestantCodeExecuted", False),
            ),
            "commandExecuted": report.get("commandExecuted", report_safety.get("commandExecuted", False)),
            "unknownShellExecuted": report.get(
                "unknownShellExecuted",
                report_safety.get("unknownShellExecuted", False),
            ),
            "networkEnabled": report.get("networkEnabled", report_safety.get("networkEnabled", False)),
            "hostExecutionAllowed": sandbox_policy.get("hostExecutionAllowed", False),
            "realSandboxRunEnabled": sandbox_policy.get(
                "realSandboxRunEnabled",
                bool(report.get("sandboxExecuted", report_safety.get("sandboxExecuted", False))),
            ),
            "readonlyOnly": report_safety.get("readonlyOnly", False),
        },
        "audit": {
            "operationAuditEventId": audit_event.get("id") if isinstance(audit_event, dict) else None,
            "action": audit_event.get("action") if isinstance(audit_event, dict) else None,
            "blockedActions": audit_detail.get("blockedActions", []),
            "runRealPytestEnabled": audit_detail.get("runRealPytestEnabled", False),
            "hostExecutionAllowed": audit_detail.get("hostExecutionAllowed", False),
        },
    }
