import json
from pathlib import Path

from cli.dsl import load_schema, load_yaml, validate_dsl
from sandbox.container_executor import (
    EXECUTOR_ID,
    PLAN_MODE,
    ContainerSandboxExecutor,
    ContainerSandboxExecutorError,
    build_container_sandbox_plan,
)
from sandbox.execution_contract import build_sandbox_execution_request


ROOT = Path(__file__).resolve().parents[1]


def load_mixed_grading():
    grading = load_yaml(ROOT / "templates/grading/examples/mixed-checks.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    return grading


def test_container_sandbox_executor_plans_all_supported_checks_without_execution():
    grading = load_mixed_grading()
    requests = [
        build_sandbox_execution_request(check, grading=grading, trace_id="trace_container_plan")
        for check in grading["spec"]["checks"]
    ]
    plans = [build_container_sandbox_plan(request) for request in requests]

    assert [plan["request"]["checkType"] for plan in plans] == [
        "file_exists",
        "stdout_contains",
        "pytest",
        "notebook_cell",
        "json_field",
        "log_keyword",
    ]
    assert all(plan["mode"] == PLAN_MODE for plan in plans)
    assert all(plan["status"] == "PLANNED" for plan in plans)
    assert all(plan["executor"]["id"] == EXECUTOR_ID for plan in plans)
    assert all(plan["executor"]["dryRun"] is True for plan in plans)
    assert all(plan["containerPlan"]["image"] == "python:3.11-slim" for plan in plans)
    assert all(plan["containerPlan"]["workingDirectory"] == "/workspace/submission" for plan in plans)
    assert all(plan["containerPlan"]["mounts"][0]["mode"] == "read_only" for plan in plans)
    assert all(plan["containerPlan"]["network"]["enabled"] is False for plan in plans)
    assert all(plan["containerPlan"]["limits"]["network"] == "disabled_by_default" for plan in plans)
    assert all(plan["safety"]["containerStarted"] is False for plan in plans)
    assert all(plan["safety"]["sandboxExecuted"] is False for plan in plans)
    assert all(plan["safety"]["contestantCodeExecuted"] is False for plan in plans)
    assert all(plan["safety"]["commandExecuted"] is False for plan in plans)
    assert all(plan["resultPlaceholder"]["status"] == "NOT_EXECUTED" for plan in plans)
    assert all(plan["resultPlaceholder"]["commandExecuted"] is False for plan in plans)


def test_container_sandbox_executor_rejects_unsafe_request_shape():
    grading = load_mixed_grading()
    request = build_sandbox_execution_request(grading["spec"]["checks"][0], grading=grading, trace_id="trace_bad_plan")
    request["network"]["enabled"] = True
    request["safety"]["hostExecutionAllowed"] = True

    try:
        ContainerSandboxExecutor().plan(request)
    except ContainerSandboxExecutorError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert {error["field"] for error in exc.errors} == {"network.enabled", "safety.hostExecutionAllowed"}
    else:
        raise AssertionError("expected ContainerSandboxExecutorError")


def test_container_sandbox_executor_contract_declares_plan_only_output():
    with (ROOT / "sandbox/container-executor.contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    assert contract["phase"] == "Phase 3"
    assert contract["mode"] == PLAN_MODE
    assert contract["executor"]["id"] == EXECUTOR_ID
    assert contract["executor"]["entrypoint"] == "build_container_sandbox_plan"
    assert contract["executor"]["dryRun"] is True
    assert contract["input"]["sourceContract"] == "sandbox/execution-contract.json"
    assert contract["input"]["requestMode"] == "REAL_SANDBOX_REQUIRED"
    assert "containerPlan" in contract["output"]["requiredTopLevelFields"]
    assert "resultPlaceholder" in contract["output"]["requiredTopLevelFields"]
    assert contract["output"]["placeholderStatus"] == "NOT_EXECUTED"
    assert contract["safetyAssertions"]["containerStarted"] is False
    assert contract["safetyAssertions"]["sandboxExecuted"] is False
    assert contract["safetyAssertions"]["commandExecuted"] is False
    assert "invoke_docker_or_podman" in contract["blockedOperations"]


def test_container_sandbox_executor_source_has_no_runtime_invocation_dependencies():
    source = (ROOT / "sandbox/container_executor.py").read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "docker" not in source.lower()
    assert "podman" not in source.lower()
    assert "kubernetes" not in source.lower()
    assert "os.system" not in source
