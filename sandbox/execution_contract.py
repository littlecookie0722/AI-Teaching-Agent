"""Sandbox execution request/result contract helpers.

These helpers define the data shape that a future real container executor
should consume and return. They do not start containers, run commands, execute
notebooks, or inspect contestant submissions.
"""

from __future__ import annotations

from typing import Any


REQUEST_SCHEMA_VERSION = "0.1.0"
REAL_EXECUTION_MODE = "REAL_SANDBOX_REQUIRED"

DEFAULT_LIMITS = {
    "timeoutSeconds": 30,
    "cpuCores": 1,
    "memoryMb": 512,
    "processLimit": 1,
    "network": "disabled_by_default",
    "filesystem": "isolated_submission_workspace_required",
}

CHECK_ACTIONS = {
    "file_exists": "verify_file_exists",
    "stdout_contains": "run_command_and_match_stdout",
    "pytest": "run_pytest_suite",
    "notebook_cell": "run_notebook_cell_and_match_output",
    "json_field": "inspect_json_field",
    "log_keyword": "inspect_log_keywords",
}


def build_sandbox_execution_request(check: dict[str, Any], *, grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
    check_type = str(check.get("type"))
    action = CHECK_ACTIONS.get(check_type)
    if not action:
        raise ValueError(f"unsupported check type for sandbox request: {check_type}")

    return {
        "schemaVersion": REQUEST_SCHEMA_VERSION,
        "mode": REAL_EXECUTION_MODE,
        "gradingId": grading.get("metadata", {}).get("id"),
        "checkId": check.get("id"),
        "checkType": check_type,
        "action": action,
        "traceId": trace_id,
        "workspace": {
            "kind": "isolated_submission_workspace",
            "hostPathAllowed": False,
            "writeOutsideWorkspaceAllowed": False,
            "submissionMountedReadOnly": True,
        },
        "limits": dict(DEFAULT_LIMITS),
        "network": {
            "enabled": False,
            "policy": "disabled_by_default",
        },
        "command": _command_payload(check),
        "evidenceRequired": [
            "stdout",
            "stderr",
            "exitCode",
            "durationMs",
            "matchedEvidence",
            "auditLogRef",
        ],
        "safety": {
            "hostExecutionAllowed": False,
            "unknownShellAllowed": False,
            "contestantCodeRequiresSandbox": True,
            "secretPassthroughAllowed": False,
            "realExecutionRequiresImplementation": True,
        },
    }


def build_sandbox_result_placeholder(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": REQUEST_SCHEMA_VERSION,
        "mode": "RESULT_PLACEHOLDER",
        "gradingId": request.get("gradingId"),
        "checkId": request.get("checkId"),
        "checkType": request.get("checkType"),
        "traceId": request.get("traceId"),
        "status": "NOT_EXECUTED",
        "passed": None,
        "earnedScore": None,
        "stdout": None,
        "stderr": None,
        "exitCode": None,
        "durationMs": None,
        "matchedEvidence": [],
        "auditLogRef": None,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "commandExecuted": False,
        "error": {
            "code": "REAL_SANDBOX_NOT_IMPLEMENTED",
            "message": "Execution request contract was built, but no real sandbox executor ran it.",
        },
    }


def _command_payload(check: dict[str, Any]) -> dict[str, Any]:
    check_type = str(check.get("type"))
    if check_type == "file_exists":
        return {"path": check.get("path")}
    if check_type == "stdout_contains":
        return {"command": check.get("command"), "expected": list(check.get("expected", []))}
    if check_type == "pytest":
        return {"path": check.get("path")}
    if check_type == "notebook_cell":
        return {
            "notebookPath": check.get("notebookPath"),
            "cellIndex": check.get("cellIndex"),
            "expected": list(check.get("expected", [])),
        }
    if check_type == "json_field":
        return {
            "path": check.get("path"),
            "jsonPath": check.get("jsonPath"),
            "expectedValue": check.get("expectedValue"),
        }
    if check_type == "log_keyword":
        return {"path": check.get("path"), "expected": list(check.get("expected", []))}
    return {}
