"""Controlled Docker-backed sandbox PoC for command-based grading checks.

This executor is intentionally narrow. It only runs allowlisted Python
commands inside a local Docker container with network disabled and the
submission mounted read-only.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from sandbox.grade_runner import (
    SANDBOX_POLICY,
    SUPPORTED_CHECK_TYPES,
    build_assessment_plan_summary,
    build_grading_check_plan_fields,
)


MODE = "CONTROLLED_DOCKER_SANDBOX_POC"
EXECUTOR_ID = "controlled_docker_sandbox_executor"
DEFAULT_IMAGE = "ai-grading-python:0.1"
SUPPORTED_CONTROLLED_CHECK_TYPES = ("stdout_contains", "pytest")
DEFERRED_CHECK_TYPES = tuple(check_type for check_type in SUPPORTED_CHECK_TYPES if check_type not in SUPPORTED_CONTROLLED_CHECK_TYPES)
IMAGE_ALLOWLIST = (
    "ai-grading-python:",
    "local-python:",
    "python:",
)
IMAGE_SUPPLY_CHAIN_POLICY_ID = "controlled-docker-local-image-allowlist-v1"
EXECUTION_PROFILE_ID = "local-python-pytest-controlled-v1"
REQUIRED_IMAGE_LABELS = {
    "org.opencontainers.image.title": "AI Training Platform Python Pytest Grading Image",
    "org.opencontainers.image.version": "0.1",
    "ai-training-platform.sandbox": "controlled-command",
    "ai-training-platform.sandbox.profile": EXECUTION_PROFILE_ID,
}
MAX_OUTPUT_CHARS = 12000
CONTAINER_SUBMISSION_PATH = "/workspace/submission"
DOCKER_CPU_LIMIT = "1"
DOCKER_MEMORY_LIMIT = "512m"
DOCKER_PIDS_LIMIT = 64
DOCKER_TMPFS = "/tmp:rw,noexec,nosuid,size=64m"
MAX_TIMEOUT_SECONDS = 60


class ControlledCommandSandboxError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class ControlledCommandSandboxExecutor:
    mode = MODE
    executor_id = EXECUTOR_ID

    def __init__(self, *, image: str = DEFAULT_IMAGE):
        self.image = image

    def run(self, grading: dict[str, Any], submission_root: Path | str, trace_id: str) -> dict[str, Any]:
        root = _validate_submission_root(Path(submission_root))
        image_supply_chain = _ensure_docker_runtime(self.image)

        checks = grading.get("spec", {}).get("checks", [])
        check_results = [self._execute_check(check, grading=grading, submission_root=root, trace_id=trace_id) for check in checks]
        completed = [check for check in check_results if check["status"] in {"PASSED", "FAILED", "ERROR"}]
        executed = [check for check in completed if check.get("sandboxExecuted") is True]
        deferred = [check for check in check_results if check["status"] == "DEFERRED"]
        passed = [check for check in completed if check["passed"] is True]
        failed = [check for check in completed if check["passed"] is False]
        total_score = int(grading.get("spec", {}).get("totalScore", 0))
        executable_score = sum(int(check.get("score", 0)) for check in executed)
        earned_score = sum(int(check.get("earnedScore", 0)) for check in completed)
        type_counts = _counts_by_type(check_results)
        assessment_plan_summary = build_assessment_plan_summary(grading, check_results)
        isolation = _build_isolation_summary(root, image=self.image, image_supply_chain=image_supply_chain)
        isolation_quality = _build_isolation_quality_summary(isolation, image_supply_chain)
        execution_profile = _build_execution_profile(isolation, image_supply_chain)

        return {
            "id": f"controlled_sandbox_report_{uuid4().hex[:12]}",
            "mode": MODE,
            "phase": "Phase 3",
            "gradingId": grading.get("metadata", {}).get("id"),
            "totalScore": total_score,
            "earnedScore": earned_score,
            "submissionRoot": str(root),
            "runner": {
                "id": EXECUTOR_ID,
                "mode": MODE,
                "runtime": "docker",
                "image": self.image,
                "imageSupplyChain": image_supply_chain,
                "executionProfile": execution_profile,
                "supportedCheckTypes": list(SUPPORTED_CONTROLLED_CHECK_TYPES),
                "deferredCheckTypes": list(DEFERRED_CHECK_TYPES),
                "strategy": "CONTROLLED_DOCKER_COMMAND_EXECUTION",
                "realSandboxExecuted": bool(executed),
                "hostExecutionAllowed": False,
            },
            "sandboxPolicy": {
                **SANDBOX_POLICY,
                "mode": MODE,
                "realSandboxRunEnabled": True,
                "readonlyOnly": False,
                "runtime": "docker",
                "image": self.image,
                "imageSupplyChain": image_supply_chain,
                "networkEnabled": False,
                "containerReadOnlyRootFilesystem": True,
                "submissionMountMode": "ro",
                "outputIsolation": isolation["outputPolicy"],
                "resourceLimits": isolation["resourceLimits"],
                "isolationQuality": isolation_quality,
                "executionProfile": execution_profile,
                "supportedRealExecutionCheckTypes": list(SUPPORTED_CONTROLLED_CHECK_TYPES),
                "deferredCheckTypes": list(DEFERRED_CHECK_TYPES),
            },
            "isolation": isolation,
            "isolationQuality": isolation_quality,
            "imageSupplyChain": image_supply_chain,
            "executionProfile": execution_profile,
            "checkSummary": {
                "total": len(check_results),
                "passed": len(passed),
                "failed": len(failed),
                "executed": len(executed),
                "completed": len(completed),
                "deferred": len(deferred),
                "plannedOnly": len(deferred),
                "byType": type_counts,
                "scoreTotalMatchesSpec": sum(int(check.get("score", 0)) for check in check_results) == total_score,
            },
            "executionSummary": {
                "total": len(check_results),
                "executed": len(executed),
                "completed": len(completed),
                "passed": len(passed),
                "failed": len(failed),
                "deferred": len(deferred),
                "byType": type_counts,
                "runtime": "docker",
                "image": self.image,
                "imageId": image_supply_chain["inspection"]["imageId"],
                "digest": image_supply_chain["inspection"]["digest"],
                "allowlistStatus": image_supply_chain["allowlist"]["status"],
                "isolationQualityState": isolation_quality["qualityState"],
                "readyForLocalControlledEvidence": isolation_quality["readyForLocalControlledEvidence"],
                "executionProfileId": EXECUTION_PROFILE_ID,
                "submissionMountMode": "ro",
                "networkEnabled": False,
            },
            "score": {
                "totalScore": total_score,
                "executableScore": executable_score,
                "earnedScore": earned_score,
                "deferredScore": sum(int(check.get("score", 0)) for check in deferred),
            },
            "assessmentPlanSummary": assessment_plan_summary,
            "explainability": {
                "status": "CONTROLLED_DOCKER_EVIDENCE_PARTIAL",
                "eachCheckHasPlan": all(bool(check.get("executionPlan")) for check in check_results),
                "eachCheckHasInputSummary": all(bool(check.get("inputSummary")) for check in check_results),
                "eachCheckHasMockEvidencePlaceholder": all(bool(check.get("mockEvidence")) for check in check_results),
                "assessmentPlanSource": assessment_plan_summary["source"],
                "assessmentPlanAlignedWithChecks": assessment_plan_summary["alignedWithChecks"],
                "controlledEvidenceCollected": bool(executed),
                "controlledEvidenceCheckTypes": list(SUPPORTED_CONTROLLED_CHECK_TYPES),
                "deferredCheckTypes": list(DEFERRED_CHECK_TYPES),
                "realSandboxEvidenceRequired": bool(deferred),
            },
            "passed": len(deferred) == 0 and len(failed) == 0 and earned_score >= total_score,
            "checks": check_results,
            "sandboxExecuted": bool(executed),
            "contestantCodeExecuted": bool(executed),
            "unknownShellExecuted": False,
            "commandExecuted": bool(executed),
            "networkEnabled": False,
            "filesystemIsolated": True,
            "realSandboxRequiredBeforeExecution": bool(deferred),
            "safety": {
                "sandboxExecuted": bool(executed),
                "readonlyOnly": False,
                "contestantCodeExecuted": bool(executed),
                "commandExecuted": bool(executed),
                "unknownShellExecuted": False,
                "pytestExecuted": any(check.get("type") == "pytest" and check.get("status") in {"PASSED", "FAILED", "ERROR"} for check in check_results),
                "notebookExecuted": False,
                "networkEnabled": False,
                "hostExecutionAllowed": False,
                "submissionMountedReadOnly": True,
                "containerReadOnlyRootFilesystem": True,
                "outputCapturedByRunner": True,
                "imageSupplyChainAudited": True,
                "imageAllowlistMatched": image_supply_chain["allowlist"]["matched"],
                "imageMetadataValidated": image_supply_chain["metadata"]["requiredLabelsPresent"],
                "imagePulledAutomatically": False,
                "registryAuthUsed": False,
                "realPublish": False,
            },
            "traceId": trace_id,
            "note": "Controlled Docker sandbox executes the local Python/pytest execution profile with network disabled and a read-only submission mount.",
        }

    def _execute_check(
        self,
        check: dict[str, Any],
        *,
        grading: dict[str, Any],
        submission_root: Path,
        trace_id: str,
    ) -> dict[str, Any]:
        check_type = str(check.get("type"))
        plan_fields = build_grading_check_plan_fields(check, grading=grading, trace_id=trace_id)
        base = {
            **plan_fields,
            "id": check.get("id"),
            "type": check_type,
            "score": int(check.get("score", 0)),
            "mode": MODE,
            "executor": EXECUTOR_ID,
            "sandboxExecuted": False,
            "readonlyOnly": False,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
            "unknownShellExecuted": False,
            "networkEnabled": False,
            "traceId": trace_id,
        }
        if check_type not in SUPPORTED_CONTROLLED_CHECK_TYPES:
            return {
                **base,
                "status": "DEFERRED",
                "passed": None,
                "earnedScore": 0,
                "reason": "Check type is not supported by the controlled Docker sandbox PoC.",
                "realSandboxRequiredBeforeExecution": True,
                "evidence": {
                    "status": "NOT_COLLECTED",
                    "matchedEvidence": [],
                    "filesInspected": [],
                    "auditLogRef": None,
                },
            }
        if check_type == "stdout_contains":
            return self._run_stdout_contains(check, base=base, submission_root=submission_root)
        return self._run_pytest(check, base=base, submission_root=submission_root)

    def _run_stdout_contains(self, check: dict[str, Any], *, base: dict[str, Any], submission_root: Path) -> dict[str, Any]:
        command = _parse_stdout_command(check.get("command"))
        expected = _expected_tokens(check)
        return self._run_container_command(command, expected, base=base, submission_root=submission_root)

    def _run_pytest(self, check: dict[str, Any], *, base: dict[str, Any], submission_root: Path) -> dict[str, Any]:
        resolved = _resolve_submission_file(submission_root, check.get("path"), field=f"checks.{check.get('id')}.path")
        if isinstance(resolved, dict):
            return _failed_check(base, resolved, duration_ms=0)
        if not resolved.exists():
            return _failed_check(
                base,
                {"code": "FILE_NOT_FOUND", "field": f"checks.{check.get('id')}.path", "reason": "pytest path does not exist"},
                duration_ms=0,
                files_inspected=[_relative_posix(submission_root, resolved)],
            )
        command = ["python", "-m", "pytest", _relative_posix(submission_root, resolved)]
        return self._run_container_command(command, [], base=base, submission_root=submission_root)

    def _run_container_command(
        self,
        command: list[str],
        expected: list[str],
        *,
        base: dict[str, Any],
        submission_root: Path,
    ) -> dict[str, Any]:
        timeout_seconds = _timeout_seconds(base)
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cpus",
            DOCKER_CPU_LIMIT,
            "--memory",
            DOCKER_MEMORY_LIMIT,
            "--pids-limit",
            str(DOCKER_PIDS_LIMIT),
            "--read-only",
            "--tmpfs",
            DOCKER_TMPFS,
            "-v",
            f"{submission_root.as_posix()}:{CONTAINER_SUBMISSION_PATH}:ro",
            "-w",
            CONTAINER_SUBMISSION_PATH,
            "--entrypoint",
            command[0],
            self.image,
            *command[1:],
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
            duration_ms = _duration_ms(started)
            stdout = _truncate_output(completed.stdout)
            stderr = _truncate_output(completed.stderr)
            matched = [token for token in expected if token in stdout]
            passed = completed.returncode == 0 and len(matched) == len(expected)
            return {
                **base,
                "status": "PASSED" if passed else "FAILED",
                "passed": passed,
                "earnedScore": base["score"] if passed else 0,
                "sandboxExecuted": True,
                "contestantCodeExecuted": True,
                "commandExecuted": True,
                "durationMs": duration_ms,
                "isolation": _build_check_isolation_summary(timeout_seconds),
                "evidence": {
                    "status": "COLLECTED",
                    "runtime": "docker",
                    "image": self.image,
                    "command": command,
                    "exitCode": completed.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "matchedEvidence": matched,
                    "expected": expected,
                    "filesInspected": [],
                    "auditLogRef": f"controlled-docker://{base['id']}",
                    "outputTruncatedToChars": MAX_OUTPUT_CHARS,
                },
                "logs": [
                    {
                        "event": "docker_command_completed",
                        "exitCode": completed.returncode,
                        "durationMs": duration_ms,
                    }
                ],
            }
        except subprocess.TimeoutExpired as exc:
            return _failed_check(
                base,
                {"code": "COMMAND_TIMEOUT", "field": f"checks.{base['id']}.command", "reason": f"timed out after {timeout_seconds}s"},
                duration_ms=_duration_ms(started),
                stdout=_truncate_output(exc.stdout or ""),
                stderr=_truncate_output(exc.stderr or ""),
                executed=True,
            )


def build_controlled_command_sandbox_report(
    grading: dict[str, Any],
    submission_root: Path | str,
    trace_id: str,
    *,
    image: str = DEFAULT_IMAGE,
) -> dict[str, Any]:
    return ControlledCommandSandboxExecutor(image=image).run(grading, submission_root, trace_id)


def _ensure_docker_runtime(image: str) -> dict[str, Any]:
    try:
        subprocess.run(
            ["docker", "info", "--format", "{{json .ServerVersion}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ControlledCommandSandboxError(
            "DOCKER_RUNTIME_UNAVAILABLE",
            "Docker runtime is not available.",
            [
                {"field": "docker", "reason": exc.__class__.__name__},
                {"field": "nextAction", "reason": "start_or_repair_local_docker_runtime"},
            ],
        ) from exc

    try:
        image_inspect = subprocess.run(
            ["docker", "image", "inspect", image, "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ControlledCommandSandboxError(
            "SANDBOX_IMAGE_MISSING",
            "Docker image is not available locally; this command will not pull images automatically.",
            [
                {"field": "image", "reason": image},
                {"field": "nextAction", "reason": "build_or_select_a_local_allowlisted_image"},
            ],
        ) from exc
    return _build_image_supply_chain_summary(image, image_inspect.stdout)


def _validate_submission_root(path: Path) -> Path:
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "Submission root must be an existing directory.",
            [{"field": "submission", "reason": "directory does not exist"}],
        )
    return root


def _parse_stdout_command(value: Any) -> list[str]:
    if not isinstance(value, str) or not value:
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "stdout_contains command must be a non-empty string.",
            [{"field": "command", "reason": "required"}],
        )
    parts = shlex.split(value, posix=False)
    if parts and parts[0] == "cat":
        return _translate_cat_command(parts, original=value)
    if not parts or parts[0] not in {"python", "python3"}:
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "Only python/python3 commands are allowed in controlled Docker sandbox PoC.",
            [{"field": "command", "reason": value}],
        )
    if any(_looks_like_shell_operator(part) for part in parts):
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "Shell operators are not allowed in controlled Docker sandbox PoC commands.",
            [{"field": "command", "reason": value}],
        )
    for part in parts[1:]:
        if part.startswith("-"):
            continue
        candidate = _strip_quotes(part)
        if candidate and ("/" in candidate or "\\" in candidate or candidate.endswith(".py")):
            path_error = _validate_relative_path_text(candidate, field="command")
            if path_error:
                raise ControlledCommandSandboxError(
                    "VALIDATION_ERROR",
                    "Command paths must stay inside the submission root.",
                    [{"field": path_error["field"], "reason": path_error["reason"]}],
                )
    return ["python", *parts[1:]]


def _translate_cat_command(parts: list[str], *, original: str) -> list[str]:
    if len(parts) != 2:
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "Only single-file cat commands can be translated in controlled Docker sandbox PoC.",
            [{"field": "command", "reason": original}],
        )
    target = _strip_quotes(parts[1])
    path_error = _validate_relative_path_text(target, field="command")
    if path_error:
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "Command paths must stay inside the submission root.",
            [{"field": path_error["field"], "reason": path_error["reason"]}],
        )
    if _looks_like_shell_operator(target):
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "Shell operators are not allowed in controlled Docker sandbox PoC commands.",
            [{"field": "command", "reason": original}],
        )
    return [
        "python",
        "-c",
        f"from pathlib import Path; print(Path({target!r}).read_text(encoding='utf-8'), end='')",
    ]


def _expected_tokens(check: dict[str, Any]) -> list[str]:
    expected = check.get("expected")
    if not isinstance(expected, list) or not all(isinstance(item, str) and item for item in expected):
        raise ControlledCommandSandboxError(
            "VALIDATION_ERROR",
            "stdout_contains expected must be a non-empty string array.",
            [{"field": f"checks.{check.get('id')}.expected", "reason": "must be non-empty string array"}],
        )
    return expected


def _resolve_submission_file(submission_root: Path, value: Any, *, field: str) -> Path | dict[str, str]:
    if not isinstance(value, str) or not value:
        return {"code": "PATH_REQUIRED", "field": field, "reason": "must be a non-empty relative path"}
    path_error = _validate_relative_path_text(value, field=field)
    if path_error:
        return path_error
    candidate = (submission_root / value).resolve()
    try:
        candidate.relative_to(submission_root)
    except ValueError:
        return {"code": "PATH_OUTSIDE_SUBMISSION", "field": field, "reason": "path escapes submission root"}
    return candidate


def _validate_relative_path_text(value: str, *, field: str) -> dict[str, str] | None:
    raw_path = Path(_strip_quotes(value))
    if raw_path.is_absolute():
        return {"code": "ABSOLUTE_PATH_NOT_ALLOWED", "field": field, "reason": "path must be relative to submission root"}
    if any(part == ".." for part in raw_path.parts):
        return {"code": "PATH_OUTSIDE_SUBMISSION", "field": field, "reason": "path escapes submission root"}
    return None


def _failed_check(
    base: dict[str, Any],
    error: dict[str, str],
    *,
    duration_ms: int,
    files_inspected: list[str] | None = None,
    stdout: str = "",
    stderr: str = "",
    executed: bool = False,
) -> dict[str, Any]:
    status = "FAILED" if error.get("code") != "COMMAND_TIMEOUT" else "ERROR"
    return {
        **base,
        "status": status,
        "passed": False,
        "earnedScore": 0,
        "sandboxExecuted": executed,
        "contestantCodeExecuted": executed,
        "commandExecuted": executed,
        "durationMs": duration_ms,
        "error": error,
        "isolation": _build_check_isolation_summary(_timeout_seconds(base)) if executed else _not_started_isolation_summary(),
        "evidence": {
            "status": "ERROR",
            "stdout": stdout,
            "stderr": stderr,
            "matchedEvidence": [],
            "filesInspected": files_inspected or [],
            "auditLogRef": f"controlled-docker://{base['id']}" if executed else None,
            "outputTruncatedToChars": MAX_OUTPUT_CHARS,
        },
        "logs": [
            {
                "event": "docker_command_timeout" if executed and status == "ERROR" else "docker_command_not_started",
                "reason": error.get("code"),
                "durationMs": duration_ms,
            }
        ],
    }


def _timeout_seconds(base: dict[str, Any]) -> int:
    limits = base.get("sandboxExecutionRequest", {}).get("limits", {})
    value = limits.get("timeoutSeconds", 30)
    return max(1, min(int(value), MAX_TIMEOUT_SECONDS))


def _build_image_supply_chain_summary(image: str, inspect_stdout: str) -> dict[str, Any]:
    inspection_payload = _parse_image_inspection(inspect_stdout)
    image_id = str(inspection_payload.get("Id") or inspection_payload.get("id") or _normalize_inspect_value(inspect_stdout))
    config = inspection_payload.get("Config") if isinstance(inspection_payload.get("Config"), dict) else {}
    labels = config.get("Labels") if isinstance(config.get("Labels"), dict) else {}
    required_label_results = [
        {"key": key, "expected": expected, "actual": labels.get(key), "present": labels.get(key) == expected}
        for key, expected in REQUIRED_IMAGE_LABELS.items()
    ]
    missing_required_labels = [item["key"] for item in required_label_results if not item["present"]]
    allowlist_match = _match_image_allowlist(image)
    return {
        "component": "ControlledDockerImageSupplyChain",
        "policyId": IMAGE_SUPPLY_CHAIN_POLICY_ID,
        "image": image,
        "resolvedImage": image,
        "inspection": {
            "dockerImageInspectExecuted": True,
            "command": ["docker", "image", "inspect", image, "--format", "{{json .}}"],
            "imageId": image_id,
            "digest": image_id if image_id.startswith("sha256:") else None,
            "digestSource": "docker_image_inspect_id",
            "localImagePresent": True,
            "created": inspection_payload.get("Created"),
            "repoTags": inspection_payload.get("RepoTags") if isinstance(inspection_payload.get("RepoTags"), list) else [],
        },
        "metadata": {
            "source": "docker image inspect Config.Labels",
            "labels": labels,
            "requiredLabels": required_label_results,
            "requiredLabelsPresent": not missing_required_labels,
            "missingRequiredLabels": missing_required_labels,
            "profileId": EXECUTION_PROFILE_ID,
        },
        "allowlist": {
            "source": "sandbox.controlled_command_executor.IMAGE_ALLOWLIST",
            "entries": list(IMAGE_ALLOWLIST),
            "matched": allowlist_match is not None,
            "matchedEntry": allowlist_match,
            "status": "MATCHED" if allowlist_match is not None else "UNMATCHED_AUDIT_ONLY",
            "enforcementMode": "AUDIT_ONLY_LOCAL_POC",
        },
        "registry": {
            "pullAttempted": False,
            "automaticPullDisabled": True,
            "registryAuthUsed": False,
            "productionRegistryUsed": False,
            "networkAccessForPull": False,
        },
        "safety": {
            "hostExecutionAllowed": False,
            "realCloudResourceChanged": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }


def _normalize_inspect_value(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith('"') and normalized.endswith('"'):
        return normalized[1:-1]
    return normalized


def _parse_image_inspection(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _match_image_allowlist(image: str) -> str | None:
    return next((entry for entry in IMAGE_ALLOWLIST if image.startswith(entry)), None)


def _build_isolation_summary(submission_root: Path, *, image: str, image_supply_chain: dict[str, Any]) -> dict[str, Any]:
    return {
        "component": "ControlledDockerIsolationSummary",
        "runtime": "docker",
        "image": image,
        "imageSupplyChain": image_supply_chain,
        "submissionMount": {
            "hostPath": str(submission_root),
            "containerPath": CONTAINER_SUBMISSION_PATH,
            "mode": "ro",
            "readOnly": True,
        },
        "workingDirectory": CONTAINER_SUBMISSION_PATH,
        "networkEnabled": False,
        "hostExecutionAllowed": False,
        "containerReadOnlyRootFilesystem": True,
        "tmpfsMounts": [
            {
                "path": "/tmp",
                "mode": "rw",
                "options": ["noexec", "nosuid"],
                "size": "64m",
            }
        ],
        "resourceLimits": {
            "cpus": DOCKER_CPU_LIMIT,
            "memory": DOCKER_MEMORY_LIMIT,
            "pidsLimit": DOCKER_PIDS_LIMIT,
            "timeoutSecondsMax": MAX_TIMEOUT_SECONDS,
        },
        "executionProfileId": EXECUTION_PROFILE_ID,
        "outputPolicy": {
            "stdoutCaptured": True,
            "stderrCaptured": True,
            "maxOutputChars": MAX_OUTPUT_CHARS,
            "hostOutputWriteAllowed": False,
            "artifactWriteOnlyByRunner": True,
        },
    }


def _build_isolation_quality_summary(isolation: dict[str, Any], image_supply_chain: dict[str, Any]) -> dict[str, Any]:
    submission_mount = isolation.get("submissionMount", {})
    output_policy = isolation.get("outputPolicy", {})
    resource_limits = isolation.get("resourceLimits", {})
    registry = image_supply_chain.get("registry", {})
    inspection = image_supply_chain.get("inspection", {})
    allowlist = image_supply_chain.get("allowlist", {})
    tmpfs_mounts = isolation.get("tmpfsMounts", [])
    tmpfs_locked_down = any(
        mount.get("path") == "/tmp"
        and mount.get("mode") == "rw"
        and {"noexec", "nosuid"}.issubset(set(mount.get("options", [])))
        for mount in tmpfs_mounts
        if isinstance(mount, dict)
    )
    checks = [
        {
            "id": "network_disabled",
            "passed": isolation.get("networkEnabled") is False,
            "evidence": "docker run --network none",
        },
        {
            "id": "submission_mount_readonly",
            "passed": submission_mount.get("readOnly") is True and submission_mount.get("mode") == "ro",
            "evidence": f"{submission_mount.get('containerPath')}:{submission_mount.get('mode')}",
        },
        {
            "id": "rootfs_readonly",
            "passed": isolation.get("containerReadOnlyRootFilesystem") is True,
            "evidence": "docker run --read-only",
        },
        {
            "id": "host_execution_blocked",
            "passed": isolation.get("hostExecutionAllowed") is False,
            "evidence": "container runtime only",
        },
        {
            "id": "resource_limits_present",
            "passed": all(resource_limits.get(key) for key in ("cpus", "memory", "pidsLimit", "timeoutSecondsMax")),
            "evidence": "cpus/memory/pids/timeout",
        },
        {
            "id": "tmpfs_restricted",
            "passed": tmpfs_locked_down,
            "evidence": DOCKER_TMPFS,
        },
        {
            "id": "output_captured_by_runner",
            "passed": output_policy.get("stdoutCaptured") is True
            and output_policy.get("stderrCaptured") is True
            and output_policy.get("hostOutputWriteAllowed") is False
            and output_policy.get("artifactWriteOnlyByRunner") is True,
            "evidence": "stdout/stderr captured, host output writes disabled",
        },
        {
            "id": "local_image_inspected",
            "passed": inspection.get("dockerImageInspectExecuted") is True
            and inspection.get("localImagePresent") is True
            and bool(inspection.get("imageId")),
            "evidence": "docker image inspect",
        },
        {
            "id": "registry_network_not_used",
            "passed": registry.get("pullAttempted") is False
            and registry.get("automaticPullDisabled") is True
            and registry.get("registryAuthUsed") is False
            and registry.get("productionRegistryUsed") is False
            and registry.get("networkAccessForPull") is False,
            "evidence": "no pull, no registry auth, no production registry",
        },
    ]
    failed = [check["id"] for check in checks if not check["passed"]]
    allowlist_matched = allowlist.get("matched") is True
    critical_ready = len(failed) == 0
    if not critical_ready:
        quality_state = "CONTROLLED_DOCKER_ISOLATION_NEEDS_FIX"
    elif not allowlist_matched:
        quality_state = "CONTROLLED_DOCKER_ISOLATION_NEEDS_IMAGE_REVIEW"
    else:
        quality_state = "CONTROLLED_DOCKER_ISOLATION_READY"
    return {
        "component": "ControlledDockerIsolationQuality",
        "qualityState": quality_state,
        "readyForLocalControlledEvidence": critical_ready and allowlist_matched,
        "criticalIsolationReady": critical_ready,
        "manualImageReviewRequired": not allowlist_matched,
        "allowlistStatus": allowlist.get("status"),
        "passedCheckTotal": len(checks) - len(failed),
        "checkTotal": len(checks),
        "failedCheckIds": failed,
        "checks": checks,
        "reviewBoundary": {
            "localEvidenceOnly": True,
            "productionSandboxCertified": False,
            "imageSignatureVerified": False,
            "tenantIsolationCertified": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    }


def _build_execution_profile(isolation: dict[str, Any], image_supply_chain: dict[str, Any]) -> dict[str, Any]:
    """Return the local, reviewable execution shape used for this report."""
    return {
        "id": EXECUTION_PROFILE_ID,
        "scope": "local controlled Docker grading only",
        "supportedCheckTypes": list(SUPPORTED_CONTROLLED_CHECK_TYPES),
        "allowedEntrypoints": ["python", "python3", "python -m pytest", "translated single-file cat"],
        "network": {"enabled": False, "dockerArgument": "--network none"},
        "filesystem": {
            "submissionMount": isolation.get("submissionMount", {}),
            "rootFilesystemReadOnly": isolation.get("containerReadOnlyRootFilesystem") is True,
            "tmpfsMounts": isolation.get("tmpfsMounts", []),
            "hostOutputWriteAllowed": isolation.get("outputPolicy", {}).get("hostOutputWriteAllowed") is True,
        },
        "resourceLimits": isolation.get("resourceLimits", {}),
        "output": isolation.get("outputPolicy", {}),
        "image": {
            "image": image_supply_chain.get("image"),
            "imageId": image_supply_chain.get("inspection", {}).get("imageId"),
            "allowlistStatus": image_supply_chain.get("allowlist", {}).get("status"),
            "metadataValidated": image_supply_chain.get("metadata", {}).get("requiredLabelsPresent") is True,
        },
        "boundaries": {
            "unknownShellExecuted": False,
            "hostExecutionAllowed": False,
            "automaticImagePull": False,
            "registryAuthUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    }


def _build_check_isolation_summary(timeout_seconds: int) -> dict[str, Any]:
    return {
        "runtime": "docker",
        "workingDirectory": CONTAINER_SUBMISSION_PATH,
        "submissionMountMode": "ro",
        "networkEnabled": False,
        "hostExecutionAllowed": False,
        "containerReadOnlyRootFilesystem": True,
        "executionProfileId": EXECUTION_PROFILE_ID,
        "timeoutSeconds": timeout_seconds,
        "cpus": DOCKER_CPU_LIMIT,
        "memory": DOCKER_MEMORY_LIMIT,
        "pidsLimit": DOCKER_PIDS_LIMIT,
        "tmpfs": DOCKER_TMPFS,
        "stdoutCaptured": True,
        "stderrCaptured": True,
        "maxOutputChars": MAX_OUTPUT_CHARS,
    }


def _not_started_isolation_summary() -> dict[str, Any]:
    return {
        "runtime": "docker",
        "containerStarted": False,
        "submissionMountMode": "not_mounted",
        "networkEnabled": False,
        "hostExecutionAllowed": False,
        "reason": "validation_failed_before_container_start",
    }


def _counts_by_type(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {check_type: sum(1 for check in checks if check.get("type") == check_type) for check_type in SUPPORTED_CHECK_TYPES}


def _relative_posix(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _truncate_output(value: str) -> str:
    return value[:MAX_OUTPUT_CHARS]


def _strip_quotes(value: str) -> str:
    return value.strip("\"'")


def _looks_like_shell_operator(value: str) -> bool:
    return any(operator in value for operator in (";", "&&", "||", "|", "`", "$(", ">", "<"))
