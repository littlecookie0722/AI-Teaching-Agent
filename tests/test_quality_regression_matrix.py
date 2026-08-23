import json
import subprocess
from pathlib import Path

import pytest
import yaml

from quality.regression_matrix import (
    REGRESSION_COMMANDS,
    RegressionMatrixError,
    list_regression_profiles,
    run_regression_matrix,
)


ROOT = Path(__file__).resolve().parents[1]


def test_regression_profiles_are_predefined_and_safe():
    profiles = list_regression_profiles()
    quick_profile = next(profile for profile in profiles["profiles"] if profile["id"] == "quick")
    core_profile = next(profile for profile in profiles["profiles"] if profile["id"] == "core")
    grading_command = next(command for command in core_profile["commands"] if command["id"] == "grading_core")
    ppt_command = next(command for command in core_profile["commands"] if command["id"] == "ppt_quality_preflight")

    assert profiles["mode"] == "LOCAL_REGRESSION_TEST_MATRIX_PROFILES"
    assert profiles["defaultProfile"] == "quick"
    assert {profile["id"] for profile in profiles["profiles"]} >= {"quick", "core", "backend-core"}
    assert "frontend_core_manifest" in quick_profile["commandIds"]
    assert "tests/test_controlled_command_sandbox_executor.py" in grading_command["paths"]
    assert set(ppt_command["paths"]) >= {
        "tests/test_ppt_preflight.py",
        "tests/test_pptx_artifact.py",
        "tests/test_teaching_presentation.py",
    }
    assert profiles["safety"]["predefinedProfilesOnly"] is True
    assert profiles["safety"]["arbitraryCommandAllowed"] is False
    assert profiles["safety"]["shellExecutionAllowed"] is False


def test_regression_matrix_references_existing_test_files():
    missing_paths = sorted(
        path
        for command in REGRESSION_COMMANDS.values()
        for path in command.paths
        if not (ROOT / path.split("::", 1)[0]).is_file()
    )

    assert missing_paths == []


def test_regression_matrix_dry_run_writes_report(tmp_path):
    output = tmp_path / "regression-matrix.json"

    report = run_regression_matrix(profile="mcp", root=ROOT, output_path=output, dry_run=True)

    assert report["success"] is True
    assert report["dryRun"] is True
    assert report["commandTotal"] == 1
    assert report["commands"][0]["id"] == "mcp_stdio_client"
    assert report["commands"][0]["status"] == "DRY_RUN"
    assert report["commands"][0]["command"][1:3] == ["-m", "pytest"]
    assert "not integration and not real_llm_online" in report["commands"][0]["command"]
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_regression_matrix_runs_predefined_pytest_commands(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")

    monkeypatch.setattr("quality.regression_matrix.subprocess.run", fake_run)

    report = run_regression_matrix(profile="mcp", root=ROOT, output_path=tmp_path / "report.json")

    assert report["success"] is True
    assert report["passedTotal"] == 1
    assert report["commands"][0]["status"] == "PASSED"
    assert calls[0]["kwargs"].get("shell") is not True
    assert calls[0]["args"][1:3] == ["-m", "pytest"]
    assert "tests/test_mcp_stdio_client_smoke.py" in calls[0]["args"]


def test_regression_matrix_reports_failure_and_stop_on_failure(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="failed")

    monkeypatch.setattr("quality.regression_matrix.subprocess.run", fake_run)

    report = run_regression_matrix(profile="quick", root=ROOT, stop_on_failure=True)

    assert report["success"] is False
    assert report["stoppedEarly"] is True
    assert report["executedTotal"] == 1
    assert report["failedTotal"] == 1
    assert len(calls) == 1


def test_regression_matrix_rejects_unknown_profile():
    with pytest.raises(RegressionMatrixError) as exc_info:
        run_regression_matrix(profile="unknown", root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.errors[0]["field"] == "profile"


def test_core_regression_matrix_github_workflow_uses_existing_cli_runner():
    workflow_path = ROOT / ".github/workflows/core-regression-matrix.yml"
    raw = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(raw)

    assert workflow["name"] == "Core Regression Matrix"
    assert workflow["permissions"]["contents"] == "read"
    assert "core-regression-matrix" in workflow["jobs"]
    assert workflow["jobs"]["core-regression-matrix"]["timeout-minutes"] == 15
    assert "mkdir -p examples/output" in raw
    assert "python lab_cli.py quality regression-matrix --profile core --stop-on-failure" in raw
    assert "examples/output/regression-matrix-core.json" in raw
    assert "actions/upload-artifact@v4" in raw
    assert "payload.get(\"success\") is not True" in raw
    assert "raise SystemExit(1)" in raw
    assert "OPENAI_API_KEY" not in raw
    assert "AGENT_API_TOKEN" not in raw
    assert "real_llm_online" not in raw
    assert "integration" not in raw
