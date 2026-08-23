"""Predefined local regression-test matrix runner.

The matrix intentionally accepts only named profiles. It does not execute
arbitrary command strings and it keeps optional online/integration tests out of
the default path.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTEST_MARKER_FILTER = "not integration and not real_llm_online"
DEFAULT_TIMEOUT_SECONDS = 180


class RegressionMatrixError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        errors: list[dict[str, str]] | None = None,
        report: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []
        self.report = report or {}


@dataclass(frozen=True)
class RegressionCommand:
    id: str
    label: str
    paths: tuple[str, ...]
    owner: str
    reason: str

    def command(self) -> list[str]:
        return [sys.executable, "-m", "pytest", *self.paths, "-q", "-m", PYTEST_MARKER_FILTER]


REGRESSION_COMMANDS: dict[str, RegressionCommand] = {
    "dsl_contract": RegressionCommand(
        id="dsl_contract",
        label="DSL schema and examples",
        paths=("tests/test_dsl_examples.py",),
        owner="DSL",
        reason="Lab / Exam / Grading / PPT examples remain schema-valid.",
    ),
    "provider_mock_and_workflow": RegressionCommand(
        id="provider_mock_and_workflow",
        label="Provider mock and workflow adapter",
        paths=("tests/test_provider_mock.py", "tests/test_provider_adapter_workflow.py"),
        owner="Provider",
        reason="MockProvider and workflow adapter remain deterministic and review-gated.",
    ),
    "lab_generation_v1": RegressionCommand(
        id="lab_generation_v1",
        label="Lab generation stable v1",
        paths=(
            "tests/test_cli.py::test_lab_generate_from_source_returns_json",
            "tests/test_cli.py::test_lab_generate_from_source_real_llm_mode_uses_explicit_opt_in_and_stays_review_gated",
            "tests/test_backend_mock_api.py::test_lab_generate_creates_waiting_review_task",
            "tests/test_provider_adapter_workflow.py::test_generate_mock_dsl_via_adapter_returns_review_gated_lab",
        ),
        owner="Lab",
        reason="The first core feature stays task-specific, schema-valid, review-gated, and ready for local import preview.",
    ),
    "exam_grading_generation_v1": RegressionCommand(
        id="exam_grading_generation_v1",
        label="Exam and grading generation stable v1",
        paths=(
            "tests/test_cli.py::test_exam_generate_from_lab_real_llm_mode_outputs_task_specific_exam_grading_and_candidate_preview",
            "tests/test_cli.py::test_exam_generate_from_lab_real_llm_mode_requires_lab_dsl",
            "tests/test_cli.py::test_exam_and_grading_import_preview_from_approved_task",
            "tests/test_backend_mock_api.py::test_exam_generate_from_lab_creates_waiting_review_task",
        ),
        owner="Exam/Grading",
        reason="The second core feature stays Lab-DSL based, task-specific, schema-valid, candidate-safe, review-gated, and ready for local import preview.",
    ),
    "offline_demo": RegressionCommand(
        id="offline_demo",
        label="Reproducible offline demo",
        paths=("tests/test_offline_demo.py",),
        owner="Demo",
        reason="The no-key Demo remains deterministic, schema-valid, candidate-safe, and review-gated.",
    ),
    "ppt_quality_preflight": RegressionCommand(
        id="ppt_quality_preflight",
        label="PPT layout preflight and artifact integrity",
        paths=(
            "tests/test_ppt_preflight.py",
            "tests/test_pptx_artifact.py",
            "tests/test_teaching_presentation.py",
        ),
        owner="PPT",
        reason="PPT layout capacity, visible text, and generated artifact integrity stay aligned before manual review.",
    ),
    "real_llm_offline_schema": RegressionCommand(
        id="real_llm_offline_schema",
        label="Real LLM offline schema normalization",
        paths=("tests/test_real_llm_demo_dsl.py",),
        owner="Real LLM",
        reason="Offline real-LLM DSL samples and normalization regressions stay covered.",
    ),
    "backend_asgi_core": RegressionCommand(
        id="backend_asgi_core",
        label="Backend ASGI core smoke",
        paths=("tests/test_backend_asgi_mount_smoke.py", "tests/test_backend_deployment_manifest.py"),
        owner="Backend",
        reason="ASGI mount, core readiness, MCP call, and deployment manifest stay aligned.",
    ),
    "backend_core_services": RegressionCommand(
        id="backend_core_services",
        label="Backend core service boundaries",
        paths=(
            "tests/test_backend_core_contract.py",
            "tests/test_backend_core_service.py",
            "tests/test_backend_core_task_service.py",
            "tests/test_backend_audit_query_service.py",
            "tests/test_backend_agent_entity_service.py",
        ),
        owner="Backend",
        reason="Repository-backed task, audit, and platform entity service boundaries stay stable.",
    ),
    "grading_core": RegressionCommand(
        id="grading_core",
        label="Grading evidence and records",
        paths=(
            "tests/test_controlled_command_sandbox_executor.py",
            "tests/test_grading_evidence_merge.py",
            "tests/test_backend_grading_job_service.py",
            "tests/test_backend_grading_record_service.py",
            "tests/test_grading_repository.py",
        ),
        owner="Grading",
        reason="Controlled Docker evidence, merge, job, record, and SQLite staging behavior stay covered.",
    ),
    "grading_stable_v1": RegressionCommand(
        id="grading_stable_v1",
        label="Grading stable v1 closure",
        paths=(
            "tests/test_cli.py::test_grade_stable_v1_creates_controlled_evidence_record_review_detail_and_report",
            "tests/test_cli.py::test_grade_stable_v1_mixed_checks_pass_fixture_scores_full_marks",
            "tests/test_cli.py::test_grade_stable_v1_requires_submission_directory",
            "tests/test_cli.py::test_grade_record_review_updates_local_record_without_task_transition",
        ),
        owner="Grading",
        reason="The third core feature stays Grading-DSL based, controlled-evidence backed, record-producing, review-detail visible, and report-readable.",
    ),
    "platform_api_contract": RegressionCommand(
        id="platform_api_contract",
        label="Platform API contract and adapter",
        paths=("tests/test_agent_api_contract.py", "tests/test_agent_api_adapter.py"),
        owner="Platform",
        reason="Draft-import contract mapping and HTTP adapter behavior stay covered.",
    ),
    "mcp_stdio_client": RegressionCommand(
        id="mcp_stdio_client",
        label="MCP stdio client and local Agent smoke",
        paths=(
            "tests/test_mcp_stdio_server.py",
            "tests/test_mcp_stdio_client_smoke.py",
            "tests/test_mcp_manifest.py",
            "tests/test_local_core_agent.py",
        ),
        owner="MCP",
        reason="Local MCP stdio, manifest, client hookup, and local-core Agent stop line stay covered.",
    ),
    "frontend_core_manifest": RegressionCommand(
        id="frontend_core_manifest",
        label="Frontend core manifest",
        paths=("tests/test_frontend_manifest.py",),
        owner="Frontend",
        reason="Core static pages and data loaders keep declared contracts.",
    ),
}


REGRESSION_PROFILES: dict[str, tuple[str, ...]] = {
    "quick": (
        "dsl_contract",
        "provider_mock_and_workflow",
        "lab_generation_v1",
        "exam_grading_generation_v1",
        "offline_demo",
        "ppt_quality_preflight",
        "grading_stable_v1",
        "backend_asgi_core",
        "platform_api_contract",
        "mcp_stdio_client",
        "frontend_core_manifest",
    ),
    "core": (
        "dsl_contract",
        "provider_mock_and_workflow",
        "lab_generation_v1",
        "exam_grading_generation_v1",
        "offline_demo",
        "ppt_quality_preflight",
        "real_llm_offline_schema",
        "backend_asgi_core",
        "backend_core_services",
        "grading_core",
        "grading_stable_v1",
        "platform_api_contract",
        "mcp_stdio_client",
        "frontend_core_manifest",
    ),
    "backend-core": ("backend_asgi_core", "backend_core_services", "grading_core", "platform_api_contract"),
    "real-llm-offline": ("real_llm_offline_schema", "provider_mock_and_workflow", "dsl_contract"),
    "mcp": ("mcp_stdio_client",),
}


def list_regression_profiles() -> dict[str, Any]:
    return {
        "mode": "LOCAL_REGRESSION_TEST_MATRIX_PROFILES",
        "profiles": [
            {
                "id": profile_id,
                "commandIds": list(command_ids),
                "commandTotal": len(command_ids),
                "commands": [_command_summary(REGRESSION_COMMANDS[command_id]) for command_id in command_ids],
            }
            for profile_id, command_ids in REGRESSION_PROFILES.items()
        ],
        "defaultProfile": "quick",
        "pytestMarkerFilter": PYTEST_MARKER_FILTER,
        "safety": _safety(),
    }


def run_regression_matrix(
    *,
    profile: str = "quick",
    root: Path = ROOT,
    output_path: Path | None = None,
    dry_run: bool = False,
    stop_on_failure: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise RegressionMatrixError(
            "VALIDATION_ERROR",
            "回归测试矩阵 timeout 必须为正数",
            [{"field": "timeoutSeconds", "reason": "must be positive"}],
        )
    if profile not in REGRESSION_PROFILES:
        raise RegressionMatrixError(
            "VALIDATION_ERROR",
            "未知回归测试矩阵 profile",
            [{"field": "profile", "reason": f"supported: {', '.join(sorted(REGRESSION_PROFILES))}"}],
        )

    commands = [REGRESSION_COMMANDS[command_id] for command_id in REGRESSION_PROFILES[profile]]
    started_at = time.perf_counter()
    results: list[dict[str, Any]] = []
    stopped_early = False
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    for command in commands:
        result = _dry_run_result(command) if dry_run else _run_command(command, root=root, env=env, timeout_seconds=timeout_seconds)
        results.append(result)
        if stop_on_failure and result["status"] != "PASSED":
            stopped_early = True
            break

    report = {
        "mode": "LOCAL_REGRESSION_TEST_MATRIX",
        "profile": profile,
        "dryRun": dry_run,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": stopped_early,
        "pytestMarkerFilter": PYTEST_MARKER_FILTER,
        "commandTotal": len(commands),
        "executedTotal": len(results),
        "passedTotal": sum(1 for result in results if result["status"] == "PASSED"),
        "failedTotal": sum(1 for result in results if result["status"] == "FAILED"),
        "timeoutTotal": sum(1 for result in results if result["status"] == "TIMEOUT"),
        "skippedByDryRunTotal": sum(1 for result in results if result["status"] == "DRY_RUN"),
        "durationMs": int((time.perf_counter() - started_at) * 1000),
        "commands": results,
        "safety": _safety(),
    }
    report["success"] = report["failedTotal"] == 0 and report["timeoutTotal"] == 0
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _run_command(
    command: RegressionCommand,
    *,
    root: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    command_args = command.command()
    try:
        completed = subprocess.run(
            command_args,
            cwd=root,
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            **_command_summary(command),
            "command": command_args,
            "status": "TIMEOUT",
            "exitCode": None,
            "durationMs": int((time.perf_counter() - started_at) * 1000),
            "stdoutTail": _tail(exc.stdout),
            "stderrTail": _tail(exc.stderr),
        }
    return {
        **_command_summary(command),
        "command": command_args,
        "status": "PASSED" if completed.returncode == 0 else "FAILED",
        "exitCode": completed.returncode,
        "durationMs": int((time.perf_counter() - started_at) * 1000),
        "stdoutTail": _tail(completed.stdout),
        "stderrTail": _tail(completed.stderr),
    }


def _dry_run_result(command: RegressionCommand) -> dict[str, Any]:
    return {
        **_command_summary(command),
        "command": command.command(),
        "status": "DRY_RUN",
        "exitCode": None,
        "durationMs": 0,
        "stdoutTail": "",
        "stderrTail": "",
    }


def _command_summary(command: RegressionCommand) -> dict[str, Any]:
    return {
        "id": command.id,
        "label": command.label,
        "owner": command.owner,
        "reason": command.reason,
        "paths": list(command.paths),
    }


def _safety() -> dict[str, bool]:
    return {
        "predefinedProfilesOnly": True,
        "arbitraryCommandAllowed": False,
        "shellExecutionAllowed": False,
        "unknownShellExecuted": False,
        "realLlmOnlineTestsExcludedByDefault": True,
        "integrationTestsExcludedByDefault": True,
        "productionDatabaseUsed": False,
        "realCloudResourceChanged": False,
        "contestantCodeExecutedByRunner": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "secretsReadByRunner": False,
    }


def _tail(value: str | bytes | None, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-limit:]
