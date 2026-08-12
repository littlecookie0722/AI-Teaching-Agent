"""Disabled real SDK dependency executor model.

This module prepares a local disabled-executor model for a future reviewed real
SDK dependency-file change. It does not persist tasks, dispatch execution,
materialize or execute commands, write dependency files, install SDKs, import
SDKs, check secrets, use network access, call real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_execution_task_creation import (
    RealSdkDependencyExecutionTaskCreationRequest,
    build_real_sdk_dependency_execution_task_creation,
    describe_real_sdk_dependency_execution_task_creation,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_EXECUTOR_DISABLED_ID = "real_sdk_dependency_executor_disabled"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyExecutorDisabledRequest(RealSdkDependencyExecutionTaskCreationRequest):
    executor_entry_scope_confirmed: bool = False
    executor_owner_confirmed: bool = False
    executor_runtime_guard_confirmed: bool = False
    executor_dry_run_mode_confirmed: bool = False
    no_execution_dispatch_after_executor_confirmed: bool = False
    no_command_materialization_confirmed: bool = False
    no_command_execution_after_executor_confirmed: bool = False
    no_dependency_file_mutation_after_executor_confirmed: bool = False
    no_dependency_install_after_executor_confirmed: bool = False
    no_real_call_after_executor_confirmed: bool = False


def _base_context(request: RealSdkDependencyExecutorDisabledRequest, *, root: Path) -> dict[str, Any]:
    task_creation_descriptor = describe_real_sdk_dependency_execution_task_creation(root=root)
    return {
        **task_creation_descriptor,
        "executorDisabledId": REAL_SDK_DEPENDENCY_EXECUTOR_DISABLED_ID,
        "gateId": REAL_SDK_DEPENDENCY_EXECUTOR_DISABLED_ID,
        "upstreamGateId": "real_sdk_dependency_execution_task_creation",
        "gateMode": "DEPENDENCY_EXECUTOR_DISABLED_ONLY",
        "executorMode": "LOCAL_DISABLED_EXECUTOR_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "executionTaskCreationRequired": True,
        "executionTaskCreationModelReady": False,
        "executorDisabledOnly": True,
        "executorModelReady": False,
        "readyForDisabledDependencyExecutor": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "taskPersisted": False,
        "taskQueued": False,
        "executionDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDryRunOnly": True,
        "commandMaterialized": False,
        "installCommandMaterialized": False,
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyFileMutationAuthorized": False,
        "dependencyFileChangeAuthorized": False,
        "dependencyManifestWriteAuthorized": False,
        "dependencyLockfileWriteAuthorized": False,
        "dependencyManifestMutated": False,
        "dependencyLockfileMutated": False,
        "dependencyFileChanged": False,
        "patchGenerated": False,
        "patchMaterialized": False,
        "patchFileWritten": False,
        "patchApplied": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAfterExecutorAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_executor_disabled(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyExecutorDisabledRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresExecutionTaskCreationModelReady": True,
        "requiresExecutorOwner": True,
        "requiresExecutorRuntimeGuard": True,
        "pipeline": [
            "real_sdk_dependency_final_execution_confirmation",
            "real_sdk_dependency_execution_task_creation",
            "dependency_executor_disabled_shell",
            "future_dependency_file_readonly_snapshot",
            "future_dependency_install_dry_run_after_executor_review",
        ],
    }


def _task_creation_summary(task_creation: dict[str, Any]) -> dict[str, Any]:
    return {
        "executionTaskCreationId": task_creation["executionTaskCreationId"],
        "finalExecutionConfirmationReady": task_creation["finalExecutionConfirmationReady"],
        "executionTaskCreationModelReady": task_creation["executionTaskCreationModelReady"],
        "readyForDisabledDependencyExecutionTaskRecord": task_creation[
            "readyForDisabledDependencyExecutionTaskRecord"
        ],
        "executionApprovalGranted": task_creation["executionApprovalGranted"],
        "executionTaskCreated": task_creation["executionTaskCreated"],
        "taskPersisted": task_creation["taskPersisted"],
        "taskQueued": task_creation["taskQueued"],
        "executionDispatched": task_creation["executionDispatched"],
        "commandExecuted": task_creation["commandExecuted"],
        "dependencyInstallExecuted": task_creation["dependencyInstallExecuted"],
        "secretPresenceChecked": task_creation["secretPresenceChecked"],
        "networkAccess": task_creation["networkAccess"],
        "realLlmCalled": task_creation["realLlmCalled"],
    }


def _executor_checklist(
    request: RealSdkDependencyExecutorDisabledRequest,
    *,
    task_creation_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "execution_task_creation_model_ready", "passed": task_creation_ready, "required": True},
        {
            "id": "executor_entry_scope_confirmed",
            "passed": request.executor_entry_scope_confirmed,
            "required": True,
        },
        {"id": "executor_owner_confirmed", "passed": request.executor_owner_confirmed, "required": True},
        {
            "id": "executor_runtime_guard_confirmed",
            "passed": request.executor_runtime_guard_confirmed,
            "required": True,
        },
        {
            "id": "executor_dry_run_mode_confirmed",
            "passed": request.executor_dry_run_mode_confirmed,
            "required": True,
        },
        {
            "id": "no_execution_dispatch_after_executor_confirmed",
            "passed": request.no_execution_dispatch_after_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_command_materialization_confirmed",
            "passed": request.no_command_materialization_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_executor_confirmed",
            "passed": request.no_command_execution_after_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_mutation_after_executor_confirmed",
            "passed": request.no_dependency_file_mutation_after_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_executor_confirmed",
            "passed": request.no_dependency_install_after_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_executor_confirmed",
            "passed": request.no_real_call_after_executor_confirmed,
            "required": True,
        },
    ]


def _executor_model(request: RealSdkDependencyExecutorDisabledRequest) -> dict[str, Any]:
    return {
        "executorId": REAL_SDK_DEPENDENCY_EXECUTOR_DISABLED_ID,
        "materializedNow": False,
        "writeNow": False,
        "persistNow": False,
        "startNow": False,
        "dispatchNow": False,
        "dryRunOnly": True,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "executorRun": {
            "status": "NOT_STARTED",
            "createdNow": False,
            "persistNow": False,
            "dispatchNow": False,
            "networkAllowed": False,
        },
        "commandPlan": {
            "materializedNow": False,
            "executableNow": False,
            "allowedCommands": [],
            "installCommandMaterialized": False,
        },
        "blockedActions": [
            {"id": "start_executor", "allowedNow": False},
            {"id": "create_executor_run", "allowedNow": False},
            {"id": "dispatch_execution", "allowedNow": False},
            {"id": "materialize_command", "allowedNow": False},
            {"id": "execute_command", "allowedNow": False},
            {"id": "write_dependency_file", "allowedNow": False},
            {"id": "execute_install_command", "allowedNow": False},
            {"id": "check_secret_presence", "allowedNow": False},
            {"id": "network_call", "allowedNow": False},
            {"id": "real_llm_call", "allowedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "executorModelReady": False,
        "readyForDisabledDependencyExecutor": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "taskPersisted": False,
        "taskQueued": False,
        "executionDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "commandMaterialized": False,
        "installCommandMaterialized": False,
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyFileMutationAuthorized": False,
        "dependencyFileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "lockfileChanged": False,
        "dependencyLockfileChanged": False,
        "dependencyManifestMutated": False,
        "dependencyLockfileMutated": False,
        "patchGenerated": False,
        "patchFileWritten": False,
        "patchMaterialized": False,
        "patchApplied": False,
        "applyAuthorized": False,
        "patchApplyAuthorized": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAfterExecutorAuthorized": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "autoPublishAllowed": False,
        "realPublish": False,
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "task_persistence", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "execution_dispatch", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "executor_start", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "executor_run_creation", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "command_materialization", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "dependency_file_mutation", "reason": "not_authorized_by_disabled_executor_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "network_call", "reason": "not_allowed_by_disabled_executor_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_executor_shell"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_executor_disabled",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_executor_disabled.py",
        },
        {
            "id": "test_real_sdk_dependency_execution_task_creation",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_execution_task_creation.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyExecutorDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖执行器禁用壳当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency executor disabled shell"}],
        )


def build_real_sdk_dependency_executor_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyExecutorDisabledRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            task_creation = build_real_sdk_dependency_execution_task_creation(request, root=root)
        else:
            task_creation = None
    except ProviderError:
        task_creation = None
    if task_creation is not None:
        context["executionTaskCreationModelReady"] = bool(
            task_creation.get("readyForDisabledDependencyExecutionTaskRecord", False)
        )
        context["executionTaskCreationSummary"] = _task_creation_summary(task_creation)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_executor_disabled(
    request: RealSdkDependencyExecutorDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    task_creation = build_real_sdk_dependency_execution_task_creation(request, root=root)
    task_creation_ready = task_creation.get("readyForDisabledDependencyExecutionTaskRecord") is True
    checklist = _executor_checklist(request, task_creation_ready=task_creation_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "executionTaskCreationModelReady": task_creation_ready,
        "executionTaskCreationSummary": _task_creation_summary(task_creation),
        "executorDisabledChecklist": checklist,
        "executorModelReady": checklist_passed,
        "readyForDisabledDependencyExecutor": checklist_passed,
        "executorModel": _executor_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖执行器禁用壳已生成；当前不会创建或持久化任务、派发执行、启动执行器、生成命令、执行命令、写依赖文件、安装依赖、读取密钥、联网或真实调用。",
    }
