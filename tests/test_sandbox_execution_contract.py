import json
from pathlib import Path

from cli.dsl import load_schema, load_yaml, validate_dsl
from sandbox.execution_contract import build_sandbox_execution_request, build_sandbox_result_placeholder


ROOT = Path(__file__).resolve().parents[1]


def load_mixed_grading():
    grading = load_yaml(ROOT / "templates/grading/examples/mixed-checks.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    return grading


def test_sandbox_execution_contract_declares_future_request_and_result_boundary():
    with (ROOT / "sandbox/execution-contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    assert contract["phase"] == "Phase 3"
    assert contract["mode"] == "CONTRACT_ONLY"
    assert contract["builder"]["module"] == "sandbox.execution_contract"
    assert set(contract["supportedCheckTypes"]) == {
        "file_exists",
        "stdout_contains",
        "pytest",
        "notebook_cell",
        "json_field",
        "log_keyword",
    }
    assert "workspace" in contract["request"]["requiredTopLevelFields"]
    assert "limits" in contract["request"]["requiredTopLevelFields"]
    assert contract["request"]["mode"] == "REAL_SANDBOX_REQUIRED"
    assert contract["result"]["placeholderStatus"] == "NOT_EXECUTED"
    assert contract["result"]["placeholderErrorCode"] == "REAL_SANDBOX_NOT_IMPLEMENTED"
    assert contract["safetyAssertions"]["hostExecutionAllowed"] is False
    assert contract["safetyAssertions"]["networkEnabledByDefault"] is False
    assert "execute_unknown_shell" in contract["blockedOperations"]


def test_build_sandbox_execution_request_maps_all_supported_checks_without_execution():
    grading = load_mixed_grading()
    requests = [
        build_sandbox_execution_request(check, grading=grading, trace_id="trace_contract")
        for check in grading["spec"]["checks"]
    ]

    assert [request["checkType"] for request in requests] == [
        "file_exists",
        "stdout_contains",
        "pytest",
        "notebook_cell",
        "json_field",
        "log_keyword",
    ]
    assert [request["action"] for request in requests] == [
        "verify_file_exists",
        "run_command_and_match_stdout",
        "run_pytest_suite",
        "run_notebook_cell_and_match_output",
        "inspect_json_field",
        "inspect_log_keywords",
    ]
    assert all(request["mode"] == "REAL_SANDBOX_REQUIRED" for request in requests)
    assert all(request["workspace"]["hostPathAllowed"] is False for request in requests)
    assert all(request["workspace"]["writeOutsideWorkspaceAllowed"] is False for request in requests)
    assert all(request["network"]["enabled"] is False for request in requests)
    assert all(request["limits"]["network"] == "disabled_by_default" for request in requests)
    assert all(request["safety"]["hostExecutionAllowed"] is False for request in requests)
    assert all(request["safety"]["unknownShellAllowed"] is False for request in requests)
    assert all(request["safety"]["contestantCodeRequiresSandbox"] is True for request in requests)
    assert all(request["traceId"] == "trace_contract" for request in requests)

    notebook_request = next(request for request in requests if request["checkType"] == "notebook_cell")
    assert notebook_request["command"]["notebookPath"] == "notebooks/analysis.ipynb"
    assert notebook_request["command"]["cellIndex"] == 3
    assert notebook_request["command"]["expected"] == ["accuracy"]


def test_sandbox_result_placeholder_is_not_executed_and_traceable():
    grading = load_mixed_grading()
    request = build_sandbox_execution_request(grading["spec"]["checks"][0], grading=grading, trace_id="trace_contract")
    result = build_sandbox_result_placeholder(request)

    assert result["mode"] == "RESULT_PLACEHOLDER"
    assert result["status"] == "NOT_EXECUTED"
    assert result["gradingId"] == request["gradingId"]
    assert result["checkId"] == request["checkId"]
    assert result["traceId"] == "trace_contract"
    assert result["sandboxExecuted"] is False
    assert result["contestantCodeExecuted"] is False
    assert result["commandExecuted"] is False
    assert result["passed"] is None
    assert result["earnedScore"] is None
    assert result["error"]["code"] == "REAL_SANDBOX_NOT_IMPLEMENTED"
