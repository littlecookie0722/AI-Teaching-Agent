"""Container sandbox dry-run planning adapter.

This module turns a sandbox execution request into a deterministic container
plan. It does not start a runtime, invoke shell commands, execute notebooks, or
inspect contestant submissions.
"""

from __future__ import annotations

from typing import Any

from sandbox.execution_contract import (
    REAL_EXECUTION_MODE,
    REQUEST_SCHEMA_VERSION,
    build_sandbox_result_placeholder,
)


PLAN_MODE = "CONTAINER_PLAN_ONLY"
EXECUTOR_ID = "container_sandbox_executor_dry_run"
DEFAULT_IMAGE = "python:3.11-slim"

REQUIRED_TOP_LEVEL_FIELDS = (
    "schemaVersion",
    "mode",
    "gradingId",
    "checkId",
    "checkType",
    "action",
    "traceId",
    "workspace",
    "limits",
    "network",
    "command",
    "evidenceRequired",
    "safety",
)


class ContainerSandboxExecutorError(ValueError):
    """Raised when a sandbox execution request cannot be planned."""

    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class ContainerSandboxExecutor:
    """Build container execution plans from sandbox execution requests."""

    def __init__(self, *, image: str = DEFAULT_IMAGE):
        self.image = image

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        _validate_request(request)

        return {
            "schemaVersion": REQUEST_SCHEMA_VERSION,
            "mode": PLAN_MODE,
            "status": "PLANNED",
            "executor": {
                "id": EXECUTOR_ID,
                "implementation": "sandbox.container_executor.ContainerSandboxExecutor",
                "runtime": "container",
                "dryRun": True,
            },
            "request": {
                "gradingId": request["gradingId"],
                "checkId": request["checkId"],
                "checkType": request["checkType"],
                "action": request["action"],
                "traceId": request["traceId"],
            },
            "containerPlan": {
                "image": self.image,
                "workingDirectory": "/workspace/submission",
                "mounts": [
                    {
                        "kind": "submission",
                        "target": "/workspace/submission",
                        "mode": "read_only",
                    }
                ],
                "limits": dict(request["limits"]),
                "network": {
                    "enabled": False,
                    "policy": request["network"].get("policy", "disabled_by_default"),
                },
                "commandPreview": dict(request["command"]),
                "evidenceRequired": list(request["evidenceRequired"]),
            },
            "safety": {
                "containerStarted": False,
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "hostExecutionAllowed": False,
                "unknownShellAllowed": False,
                "networkEnabled": False,
                "secretPassthroughAllowed": False,
            },
            "resultPlaceholder": build_sandbox_result_placeholder(request),
        }


def build_container_sandbox_plan(request: dict[str, Any], *, image: str = DEFAULT_IMAGE) -> dict[str, Any]:
    return ContainerSandboxExecutor(image=image).plan(request)


def _validate_request(request: dict[str, Any]) -> None:
    errors: list[dict[str, str]] = []

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in request:
            errors.append({"field": field, "reason": "required field is missing"})

    if errors:
        raise ContainerSandboxExecutorError("VALIDATION_ERROR", "Sandbox execution request is incomplete.", errors)

    if request.get("schemaVersion") != REQUEST_SCHEMA_VERSION:
        errors.append({"field": "schemaVersion", "reason": f"must be {REQUEST_SCHEMA_VERSION}"})
    if request.get("mode") != REAL_EXECUTION_MODE:
        errors.append({"field": "mode", "reason": f"must be {REAL_EXECUTION_MODE}"})

    workspace = request.get("workspace", {})
    if workspace.get("hostPathAllowed") is not False:
        errors.append({"field": "workspace.hostPathAllowed", "reason": "host paths must not be allowed"})
    if workspace.get("writeOutsideWorkspaceAllowed") is not False:
        errors.append({"field": "workspace.writeOutsideWorkspaceAllowed", "reason": "writes must stay inside workspace"})
    if workspace.get("submissionMountedReadOnly") is not True:
        errors.append({"field": "workspace.submissionMountedReadOnly", "reason": "submission mount must be read-only"})

    network = request.get("network", {})
    if network.get("enabled") is not False:
        errors.append({"field": "network.enabled", "reason": "network must be off by default"})

    safety = request.get("safety", {})
    if safety.get("hostExecutionAllowed") is not False:
        errors.append({"field": "safety.hostExecutionAllowed", "reason": "host execution must not be allowed"})
    if safety.get("unknownShellAllowed") is not False:
        errors.append({"field": "safety.unknownShellAllowed", "reason": "unknown shells must not be allowed"})
    if safety.get("contestantCodeRequiresSandbox") is not True:
        errors.append({"field": "safety.contestantCodeRequiresSandbox", "reason": "contestant code must require sandbox"})
    if safety.get("secretPassthroughAllowed") is not False:
        errors.append({"field": "safety.secretPassthroughAllowed", "reason": "secrets must not pass through"})

    if not isinstance(request.get("evidenceRequired"), list) or not request["evidenceRequired"]:
        errors.append({"field": "evidenceRequired", "reason": "at least one evidence field is required"})

    if errors:
        raise ContainerSandboxExecutorError("VALIDATION_ERROR", "Sandbox execution request is not safe to plan.", errors)
