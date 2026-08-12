import json
from pathlib import Path

from cli.dsl import load_schema, load_yaml, validate_dsl
from sandbox.grade_runner import GradingRunner, GradingRunnerError, build_grading_audit_detail, build_grading_report_detail
from sandbox.mock_executor import MockSandboxExecutor, build_mock_grading_report
from sandbox.real_sandbox_precheck import build_real_sandbox_precheck_report


ROOT = Path(__file__).resolve().parents[1]


def load_grading():
    grading = load_yaml(ROOT / "templates/grading/examples/python-pytest.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    return grading


def load_mixed_grading():
    grading = load_yaml(ROOT / "templates/grading/examples/mixed-checks.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    return grading


def test_mock_sandbox_executor_returns_deterministic_safe_report():
    grading = load_grading()
    report = MockSandboxExecutor().run_grading(grading, "trace_test")

    assert report["mode"] == "MOCK_ONLY"
    assert report["phase"] == "Phase 3"
    assert report["gradingId"] == grading["metadata"]["id"]
    assert report["totalScore"] == grading["spec"]["totalScore"]
    assert report["earnedScore"] == grading["spec"]["totalScore"]
    assert report["passed"] is True
    assert report["runner"]["id"] == "mock_grading_runner"
    assert report["sandboxExecuted"] is False
    assert report["contestantCodeExecuted"] is False
    assert report["unknownShellExecuted"] is False
    assert report["commandExecuted"] is False
    assert report["networkEnabled"] is False
    assert report["filesystemIsolated"] is True
    assert report["traceId"] == "trace_test"


def test_mock_sandbox_executor_marks_each_check_as_not_executed():
    report = build_mock_grading_report(load_grading(), "trace_test")

    assert report["checks"]
    for check in report["checks"]:
        assert check["passed"] is True
        assert check["executionMode"] == "MOCK_ONLY"
        assert check["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY"
        assert check["sandboxExecuted"] is False
        assert check["contestantCodeExecuted"] is False
        assert check["commandExecuted"] is False
        assert check["unknownShellExecuted"] is False
        assert check["logs"] == []


def test_phase3_grading_runner_plans_six_check_types_without_execution():
    report = GradingRunner().run(load_mixed_grading(), "trace_phase3")

    assert report["mode"] == "MOCK_ONLY"
    assert report["phase"] == "Phase 3"
    assert report["runner"]["supportedCheckTypes"] == ["file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword"]
    assert report["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert report["sandboxPolicy"]["hostExecutionAllowed"] is False
    assert report["sandboxPolicy"]["filesystemIsolationRequired"] is True
    assert report["checkSummary"]["total"] == 6
    assert report["checkSummary"]["executed"] == 0
    assert report["checkSummary"]["plannedOnly"] == 6
    assert report["checkSummary"]["byType"] == {
        "file_exists": 1,
        "stdout_contains": 1,
        "pytest": 1,
        "notebook_cell": 1,
        "json_field": 1,
        "log_keyword": 1,
    }
    assert report["checkSummary"]["scoreTotalMatchesSpec"] is True
    assert report["assessmentPlanSummary"]["source"] == "grading.spec.assessmentPlan"
    assert report["assessmentPlanSummary"]["planTotal"] == 6
    assert report["assessmentPlanSummary"]["checkTotal"] == 6
    assert report["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert report["assessmentPlanSummary"]["missingPlanForChecks"] == []
    assert report["assessmentPlanSummary"]["orphanPlanCheckIds"] == []
    assert report["assessmentPlanSummary"]["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert report["assessmentPlanSummary"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert report["assessmentPlanSummary"]["riskLevels"] == ["high", "low", "medium"]
    assert report["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert report["explainability"]["eachCheckHasInputSummary"] is True
    assert report["explainability"]["eachCheckHasMockEvidencePlaceholder"] is True
    assert report["explainability"]["assessmentPlanSource"] == "grading.spec.assessmentPlan"
    assert report["explainability"]["assessmentPlanAlignedWithChecks"] is True
    assert {check["runner"] for check in report["checks"]} == {
        "FileExistsGrader",
        "StdoutContainsGrader",
        "PytestGrader",
        "NotebookGrader",
        "JsonFieldGrader",
        "LogKeywordGrader",
    }
    assert all(check["inputSummary"] for check in report["checks"])
    assert all(check["sandboxExecutionRequest"]["mode"] == "REAL_SANDBOX_REQUIRED" for check in report["checks"])
    assert all(check["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY" for check in report["checks"])
    assert all(check["containerSandboxPlan"]["status"] == "PLANNED" for check in report["checks"])
    assert all(check["containerSandboxPlan"]["safety"]["containerStarted"] is False for check in report["checks"])
    assert all(check["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for check in report["checks"])
    assert all(check["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default" for check in report["checks"])
    assert all(check["assessmentPlanSource"] == "grading.spec.assessmentPlan" for check in report["checks"])
    assert all(check["assessmentPlanSourceField"].startswith("spec.assessmentPlan[checkId=") for check in report["checks"])
    assert all(check["assessmentPlanAlignedWithCheck"] is True for check in report["checks"])
    assert all(check["assessmentPlanExecutionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for check in report["checks"])
    assert all(check["assessmentPlanMockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for check in report["checks"])
    assert all(check["sandboxExecuted"] is False for check in report["checks"])
    assert all(check["contestantCodeExecuted"] is False for check in report["checks"])
    assert all(check["commandExecuted"] is False for check in report["checks"])
    assert all(check["executionPlan"]["wouldRunInsideRealSandbox"] is True for check in report["checks"])


def test_phase3_grading_audit_detail_records_runner_plan_and_blocked_actions():
    report = GradingRunner().run(load_mixed_grading(), "trace_phase3")
    detail = build_grading_audit_detail(report)

    assert detail["gradingId"] == "grading_mixed_checks_demo"
    assert detail["phase"] == "Phase 3"
    assert detail["runner"]["id"] == "mock_grading_runner"
    assert detail["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert detail["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert detail["checkSummary"]["executed"] == 0
    assert detail["assessmentPlanSummary"]["source"] == "grading.spec.assessmentPlan"
    assert detail["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert len(detail["checkPlans"]) == 6
    assert {plan["type"] for plan in detail["checkPlans"]} == {
        "file_exists",
        "stdout_contains",
        "pytest",
        "notebook_cell",
        "json_field",
        "log_keyword",
    }
    assert all(plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in detail["checkPlans"])
    assert all(plan["inputSummary"] for plan in detail["checkPlans"])
    assert all(plan["sandboxExecutionRequest"]["mode"] == "REAL_SANDBOX_REQUIRED" for plan in detail["checkPlans"])
    assert all(plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY" for plan in detail["checkPlans"])
    assert all(plan["containerSandboxPlan"]["resultPlaceholder"]["status"] == "NOT_EXECUTED" for plan in detail["checkPlans"])
    assert all(plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for plan in detail["checkPlans"])
    assert all(plan["assessmentPlanSource"] == "grading.spec.assessmentPlan" for plan in detail["checkPlans"])
    assert all(plan["assessmentPlanAlignedWithCheck"] is True for plan in detail["checkPlans"])
    assert all(plan["assessmentPlanExecutionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in detail["checkPlans"])
    assert all(plan["assessmentPlanMockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for plan in detail["checkPlans"])
    assert all(plan["sandboxExecuted"] is False for plan in detail["checkPlans"])
    assert all(plan["contestantCodeExecuted"] is False for plan in detail["checkPlans"])
    assert all(plan["commandExecuted"] is False for plan in detail["checkPlans"])
    assert "runRealPytest" in detail["blockedActions"]
    assert detail["runRealPytestEnabled"] is False
    assert detail["hostExecutionAllowed"] is False


def test_phase3_grading_report_detail_is_canonical_source_for_ui_and_backend():
    report = GradingRunner().run(load_mixed_grading(), "trace_phase3")
    audit_detail = build_grading_audit_detail(report)
    audit_event = {"id": "op_audit_grading_demo", "action": "MOCK_GRADING_RUN", "detail": audit_detail}
    detail = build_grading_report_detail(report, audit_event)

    assert detail["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert detail["gradingId"] == "grading_mixed_checks_demo"
    assert detail["runner"]["id"] == "mock_grading_runner"
    assert detail["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert detail["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert detail["checkSummary"]["executed"] == 0
    assert detail["assessmentPlanSummary"]["source"] == "grading.spec.assessmentPlan"
    assert detail["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert [plan["type"] for plan in detail["checkPlans"]] == [
        "file_exists",
        "stdout_contains",
        "pytest",
        "notebook_cell",
        "json_field",
        "log_keyword",
    ]
    assert all(plan["inputSummary"] for plan in detail["checkPlans"])
    assert all(plan["sandboxExecutionRequest"]["mode"] == "REAL_SANDBOX_REQUIRED" for plan in detail["checkPlans"])
    assert all(plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY" for plan in detail["checkPlans"])
    assert all(plan["containerSandboxPlan"]["safety"]["commandExecuted"] is False for plan in detail["checkPlans"])
    assert all(plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for plan in detail["checkPlans"])
    assert all(plan["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default" for plan in detail["checkPlans"])
    assert all(plan["assessmentPlanSourceField"].startswith("spec.assessmentPlan[checkId=") for plan in detail["checkPlans"])
    assert all(plan["assessmentPlanAlignedWithCheck"] is True for plan in detail["checkPlans"])
    assert detail["safety"]["hostExecutionAllowed"] is False
    assert detail["audit"]["operationAuditEventId"] == "op_audit_grading_demo"
    assert detail["audit"]["action"] == "MOCK_GRADING_RUN"
    assert "runRealPytest" in detail["audit"]["blockedActions"]
    assert detail["audit"]["runRealPytestEnabled"] is False


def test_real_sandbox_precheck_report_marks_valid_plan_ready_without_execution():
    precheck = build_real_sandbox_precheck_report(load_mixed_grading(), "trace_precheck")

    assert precheck["mode"] == "REAL_SANDBOX_PRECHECK_ONLY"
    assert precheck["phase"] == "Phase 3"
    assert precheck["gradingId"] == "grading_mixed_checks_demo"
    assert precheck["readiness"]["status"] == "READY_FOR_MANUAL_SANDBOX_REVIEW"
    assert precheck["readiness"]["readyForRealSandboxImplementation"] is True
    assert precheck["readiness"]["readyForRealSandboxExecution"] is False
    assert precheck["readiness"]["manualReviewRequired"] is True
    assert precheck["readiness"]["blockers"] == []
    assert precheck["summary"]["checkTotal"] == 6
    assert precheck["summary"]["plannedOnly"] == 6
    assert precheck["summary"]["executed"] == 0
    assert precheck["summary"]["assessmentPlan"]["alignedWithChecks"] is True
    assert precheck["safety"]["sandboxExecuted"] is False
    assert precheck["safety"]["contestantCodeExecuted"] is False
    assert precheck["safety"]["commandExecuted"] is False
    assert precheck["safety"]["realPublish"] is False
    assert len(precheck["checkPreviews"]) == 6
    assert all(check["sandboxRequestMode"] == "REAL_SANDBOX_REQUIRED" for check in precheck["checkPreviews"])
    assert all(check["containerPlanMode"] == "CONTAINER_PLAN_ONLY" for check in precheck["checkPreviews"])
    assert all(check["realExecutionDeferred"] is True for check in precheck["checkPreviews"])
    assert precheck["gradingReport"]["sandboxExecuted"] is False


def test_real_sandbox_precheck_report_blocks_misaligned_assessment_plan():
    grading = load_mixed_grading()
    grading["spec"]["assessmentPlan"][0]["score"] = 999

    precheck = build_real_sandbox_precheck_report(grading, "trace_precheck_bad")

    assert precheck["readiness"]["status"] == "BLOCKED_BEFORE_REAL_SANDBOX"
    assert precheck["readiness"]["readyForRealSandboxImplementation"] is False
    blocker_codes = {blocker["code"] for blocker in precheck["readiness"]["blockers"]}
    assert "CHECK_PLAN_TRACE_MISMATCH" in blocker_codes
    assert precheck["safety"]["sandboxExecuted"] is False
    assert precheck["safety"]["commandExecuted"] is False


def test_real_sandbox_precheck_report_blocks_incomplete_runner_plan_as_report():
    grading = load_mixed_grading()
    stdout_check = next(check for check in grading["spec"]["checks"] if check["type"] == "stdout_contains")
    stdout_check.pop("command")
    stdout_check.pop("expected")

    precheck = build_real_sandbox_precheck_report(grading, "trace_precheck_incomplete")

    assert precheck["mode"] == "REAL_SANDBOX_PRECHECK_ONLY"
    assert precheck["readiness"]["status"] == "BLOCKED_BEFORE_REAL_SANDBOX"
    assert precheck["readiness"]["readyForRealSandboxImplementation"] is False
    assert precheck["readiness"]["readyForRealSandboxExecution"] is False
    assert precheck["sourceReportId"] is None
    assert precheck["gradingReport"] is None
    blocker_fields = {blocker["field"] for blocker in precheck["readiness"]["blockers"]}
    assert "checks.check_stdout_accuracy.command" in blocker_fields
    assert "checks.check_stdout_accuracy.expected" in blocker_fields
    assert precheck["summary"]["plannedOnly"] == 0
    assert precheck["safety"]["sandboxExecuted"] is False
    assert precheck["safety"]["commandExecuted"] is False


def test_phase3_grading_runner_rejects_incomplete_check_config():
    grading = load_mixed_grading()
    grading["spec"]["checks"][1].pop("expected")

    try:
        GradingRunner().run(grading, "trace_bad")
    except GradingRunnerError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "checks.check_stdout_accuracy.expected"
    else:
        raise AssertionError("expected GradingRunnerError")


def test_phase3_grading_runner_rejects_incomplete_json_field_config():
    grading = load_mixed_grading()
    json_check = next(check for check in grading["spec"]["checks"] if check["type"] == "json_field")
    json_check.pop("expectedValue")

    try:
        GradingRunner().run(grading, "trace_bad")
    except GradingRunnerError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "checks.check_metrics_json.expectedValue"
    else:
        raise AssertionError("expected GradingRunnerError")


def test_phase3_grading_runner_rejects_incomplete_notebook_cell_config():
    grading = load_mixed_grading()
    notebook_check = next(check for check in grading["spec"]["checks"] if check["type"] == "notebook_cell")
    notebook_check.pop("cellIndex")

    try:
        GradingRunner().run(grading, "trace_bad")
    except GradingRunnerError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "checks.check_notebook_accuracy.cellIndex"
    else:
        raise AssertionError("expected GradingRunnerError")


def test_sandbox_contract_declares_phase1_blocked_operations():
    with (ROOT / "sandbox/sandbox.contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["phase1Guarantees"]["sandboxExecuted"] is False
    assert contract["phase1Guarantees"]["contestantCodeExecuted"] is False
    assert contract["phase1Guarantees"]["unknownShellExecuted"] is False
    assert contract["futureExecutionBoundary"]["contract"] == "sandbox/execution-contract.json"
    assert contract["futureExecutionBoundary"]["mode"] == "CONTRACT_ONLY"
    assert contract["futureExecutionBoundary"]["realContainerExecuted"] is False
    assert contract["futureExecutionBoundary"]["dryRunAdapter"]["contract"] == "sandbox/container-executor.contract.json"
    assert contract["futureExecutionBoundary"]["dryRunAdapter"]["mode"] == "CONTAINER_PLAN_ONLY"
    assert contract["futureExecutionBoundary"]["dryRunAdapter"]["realContainerExecuted"] is False
    assert "execute_contestant_code_on_host" in contract["blockedOperations"]


def test_sandbox_contract_requires_future_real_sandbox_limits():
    with (ROOT / "sandbox/sandbox.contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    requirements = contract["futureRealSandboxRequirements"]
    assert requirements["cpuLimitRequired"] is True
    assert requirements["memoryLimitRequired"] is True
    assert requirements["timeoutRequired"] is True
    assert requirements["networkDisabledByDefault"] is True
    assert requirements["filesystemIsolationRequired"] is True
    assert requirements["auditLogRequired"] is True


def test_phase3_grade_runner_contract_is_mock_only_and_safe():
    with (ROOT / "sandbox/grade-runner.contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    assert contract["phase"] == "Phase 3"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["runner"]["id"] == "mock_grading_runner"
    assert contract["futureExecutionBoundary"]["contract"] == "sandbox/execution-contract.json"
    assert contract["futureExecutionBoundary"]["mode"] == "CONTRACT_ONLY"
    assert contract["futureExecutionBoundary"]["realContainerExecuted"] is False
    assert contract["futureExecutionBoundary"]["dryRunAdapter"]["contract"] == "sandbox/container-executor.contract.json"
    assert contract["futureExecutionBoundary"]["dryRunAdapter"]["mode"] == "CONTAINER_PLAN_ONLY"
    assert contract["futureExecutionBoundary"]["dryRunAdapter"]["realContainerExecuted"] is False
    assert {check["type"] for check in contract["supportedCheckTypes"]} == {
        "file_exists",
        "stdout_contains",
        "pytest",
        "notebook_cell",
        "json_field",
        "log_keyword",
    }
    assert contract["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert contract["sandboxPolicy"]["hostExecutionAllowed"] is False
    assert "executionPlan.requiredLimits" in contract["checkPlanFields"]
    assert "sandboxExecutionRequest" in contract["checkPlanFields"]
    assert "containerSandboxPlan" in contract["checkPlanFields"]
    assert "mockEvidence" in contract["checkPlanFields"]
    assert contract["assessmentPlanTrace"]["source"] == "grading.spec.assessmentPlan"
    assert "assessmentPlanAlignedWithCheck" in contract["assessmentPlanTrace"]["checkPlanFields"]
    assert contract["assessmentPlanTrace"]["realExecutionDeferred"] is True
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["commandExecuted"] is False
    assert contract["safety"]["hostExecutionAllowed"] is False
    assert "execute_pytest_on_host" in contract["blockedOperations"]


def test_phase3_grade_runner_contract_declares_report_detail_fields():
    with (ROOT / "sandbox/grade-runner.contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    report = GradingRunner().run(load_mixed_grading(), "trace_phase3")
    detail = build_grading_report_detail(
        report,
        {
            "id": "op_audit_grading_demo",
            "action": "MOCK_GRADING_RUN",
            "detail": build_grading_audit_detail(report),
        },
    )
    report_detail_output = next(output for output in contract["outputs"] if output["name"] == "reportDetail")
    detail_contract = contract["reportDetailContract"]

    assert report_detail_output["builder"] == "sandbox.grade_runner.build_grading_report_detail"
    assert detail_contract["source"] == detail["source"]
    assert detail_contract["sharedCheckPlanBuilder"] == "sandbox.grade_runner._build_check_plans"
    assert set(report_detail_output["requiredFields"]) == set(detail_contract["requiredTopLevelFields"])
    assert set(detail_contract["requiredTopLevelFields"]) <= set(detail)
    assert "assessmentPlanSummary" in detail_contract["requiredTopLevelFields"]
    assert detail["assessmentPlanSummary"]["source"] == "grading.spec.assessmentPlan"
    assert detail["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert set(detail_contract["scoreFields"]) <= set(detail["score"])
    assert set(detail_contract["safetyFields"]) <= set(detail["safety"])
    assert set(detail_contract["auditFields"]) <= set(detail["audit"])
    assert detail_contract["safetyAssertions"]["sandboxExecuted"] is False
    assert detail_contract["safetyAssertions"]["hostExecutionAllowed"] is False
    assert detail["safety"]["sandboxExecuted"] is False
    assert detail["safety"]["hostExecutionAllowed"] is False
    assert detail["safety"]["realSandboxRunEnabled"] is False
    assert detail["checkPlans"]
    for plan in detail["checkPlans"]:
        assert {"id", "type", "runner", "score", "earnedScore", "passed"} <= set(plan)
        assert "inputSummary" in plan
        assert "executionPlan" in plan
        assert "requiredLimits" in plan["executionPlan"]
        assert plan["sandboxExecutionRequest"]["mode"] == "REAL_SANDBOX_REQUIRED"
        assert plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY"
        assert plan["containerSandboxPlan"]["status"] == "PLANNED"
        assert plan["containerSandboxPlan"]["safety"]["sandboxExecuted"] is False
        assert "mockEvidence" in plan
        assert plan["mockEvidence"]["status"] == detail_contract["safetyAssertions"]["mockEvidenceStatus"]
        assert "riskLevel" in plan
        assert plan["assessmentPlanSource"] == "grading.spec.assessmentPlan"
        assert plan["assessmentPlanAlignedWithCheck"] is True
        assert plan["assessmentPlanExecutionPlan"]["strategy"] == "MOCK_PLAN_ONLY"
        assert plan["assessmentPlanMockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"
        assert plan["sandboxExecuted"] is False
        assert plan["contestantCodeExecuted"] is False
        assert plan["commandExecuted"] is False
    assert "POST /api/grading/run" in detail_contract["usedBy"]
    assert "GET /api/grading/report" in detail_contract["usedBy"]
