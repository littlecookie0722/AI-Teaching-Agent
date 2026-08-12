"""Disabled real SDK dependency execution task creation.

This module prepares a local task-creation model for a future reviewed real SDK
dependency-file change. It does not create or persist tasks, dispatch execution,
read or write dependency files, generate or apply patches, execute commands,
install SDKs, import SDKs, check secrets, use network access, call real LLMs,
or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_final_execution_confirmation import (
    RealSdkDependencyFinalExecutionConfirmationRequest,
    build_real_sdk_dependency_final_execution_confirmation,
    describe_real_sdk_dependency_final_execution_confirmation,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_EXECUTION_TASK_CREATION_ID = "real_sdk_dependency_execution_task_creation"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyExecutionTaskCreationRequest(RealSdkDependencyFinalExecutionConfirmationRequest):
    execution_task_scope_confirmed: bool = False
    task_owner_confirmed: bool = False
    task_queue_policy_confirmed: bool = False
    dependency_execution_runbook_confirmed: bool = False
    no_task_persistence_confirmed: bool = False
    no_execution_dispatch_confirmed: bool = False
    no_dependency_file_mutation_after_task_confirmed: bool = False
    no_command_execution_after_task_confirmed: bool = False
    no_dependency_install_after_task_confirmed: bool = False
    no_real_call_after_task_creation_confirmed: bool = False


def _base_context(request: RealSdkDependencyExecutionTaskCreationRequest, *, root: Path) -> dict[str, Any]:
    final_confirmation_descriptor = describe_real_sdk_dependency_final_execution_confirmation(root=root)
    return {
        **final_confirmation_descriptor,
        "executionTaskCreationId": REAL_SDK_DEPENDENCY_EXECUTION_TASK_CREATION_ID,
        "gateId": REAL_SDK_DEPENDENCY_EXECUTION_TASK_CREATION_ID,
        "upstreamGateId": "real_sdk_dependency_final_execution_confirmation",
        "gateMode": "DEPENDENCY_EXECUTION_TASK_CREATION_DISABLED_ONLY",
        "taskCreationMode": "LOCAL_TASK_CREATION_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "finalExecutionConfirmationRequired": True,
        "finalExecutionConfirmationReady": False,
        "executionTaskCreationOnly": True,
        "executionTaskCreationModelReady": False,
        "readyForDisabledDependencyExecutionTaskRecord": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "taskPersisted": False,
        "taskQueued": False,
        "executionDispatched": False,
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
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAfterTaskCreationAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_execution_task_creation(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyExecutionTaskCreationRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresFinalExecutionConfirmationReady": True,
        "requiresTaskOwner": True,
        "requiresTaskQueuePolicy": True,
        "requiresNoTaskPersistencePolicy": True,
        "pipeline": [
            "real_sdk_dependency_readonly_diff_review",
            "real_sdk_dependency_final_execution_confirmation",
            "dependency_execution_task_creation_disabled_shell",
            "future_real_dependency_file_change_executor",
            "future_real_llm_dry_run_after_dependency_review",
        ],
    }


def _final_confirmation_summary(final_confirmation: dict[str, Any]) -> dict[str, Any]:
    return {
        "finalExecutionConfirmationId": final_confirmation["finalExecutionConfirmationId"],
        "readonlyDiffReviewReady": final_confirmation["readonlyDiffReviewReady"],
        "finalExecutionConfirmationReady": final_confirmation["finalExecutionConfirmationReady"],
        "readyForReviewedDependencyExecutionTask": final_confirmation[
            "readyForReviewedDependencyExecutionTask"
        ],
        "executionApprovalGranted": final_confirmation["executionApprovalGranted"],
        "executionTaskCreated": final_confirmation["executionTaskCreated"],
        "dependencyFileMutationAuthorized": final_confirmation["dependencyFileMutationAuthorized"],
        "commandExecuted": final_confirmation["commandExecuted"],
        "dependencyInstallExecuted": final_confirmation["dependencyInstallExecuted"],
        "secretPresenceChecked": final_confirmation["secretPresenceChecked"],
        "networkAccess": final_confirmation["networkAccess"],
        "realLlmCalled": final_confirmation["realLlmCalled"],
    }


def _task_creation_checklist(
    request: RealSdkDependencyExecutionTaskCreationRequest,
    *,
    final_confirmation_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "final_execution_confirmation_ready", "passed": final_confirmation_ready, "required": True},
        {
            "id": "execution_task_scope_confirmed",
            "passed": request.execution_task_scope_confirmed,
            "required": True,
        },
        {"id": "task_owner_confirmed", "passed": request.task_owner_confirmed, "required": True},
        {
            "id": "task_queue_policy_confirmed",
            "passed": request.task_queue_policy_confirmed,
            "required": True,
        },
        {
            "id": "dependency_execution_runbook_confirmed",
            "passed": request.dependency_execution_runbook_confirmed,
            "required": True,
        },
        {
            "id": "no_task_persistence_confirmed",
            "passed": request.no_task_persistence_confirmed,
            "required": True,
        },
        {
            "id": "no_execution_dispatch_confirmed",
            "passed": request.no_execution_dispatch_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_mutation_after_task_confirmed",
            "passed": request.no_dependency_file_mutation_after_task_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_task_confirmed",
            "passed": request.no_command_execution_after_task_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_task_confirmed",
            "passed": request.no_dependency_install_after_task_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_task_creation_confirmed",
            "passed": request.no_real_call_after_task_creation_confirmed,
            "required": True,
        },
    ]


def _task_creation_model(request: RealSdkDependencyExecutionTaskCreationRequest) -> dict[str, Any]:
    return {
        "taskCreationId": REAL_SDK_DEPENDENCY_EXECUTION_TASK_CREATION_ID,
        "materializedNow": False,
        "writeNow": False,
        "persistNow": False,
        "queueNow": False,
        "dispatchNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "taskRecord": {
            "taskType": "REAL_SDK_DEPENDENCY_FILE_CHANGE",
            "status": "NOT_CREATED",
            "persistNow": False,
            "queueNow": False,
            "dispatchNow": False,
        },
        "blockedActions": [
            {"id": "persist_task_record", "allowedNow": False},
            {"id": "dispatch_execution", "allowedNow": False},
            {"id": "write_dependency_file", "allowedNow": False},
            {"id": "execute_install_command", "allowedNow": False},
            {"id": "check_secret_presence", "allowedNow": False},
            {"id": "network_call", "allowedNow": False},
            {"id": "real_llm_call", "allowedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "executionTaskCreationModelReady": False,
        "readyForDisabledDependencyExecutionTaskRecord": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "taskPersisted": False,
        "taskQueued": False,
        "executionDispatched": False,
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
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAfterTaskCreationAuthorized": False,
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
            {"field": "task_persistence", "reason": "not_allowed_by_task_creation_shell"},
            {"field": "execution_dispatch", "reason": "not_allowed_by_task_creation_shell"},
            {"field": "dependency_file_mutation", "reason": "not_authorized_by_task_creation_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_task_creation_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_task_creation_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_task_creation_shell"},
            {"field": "network_call", "reason": "not_allowed_by_task_creation_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_task_creation"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_execution_task_creation",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_execution_task_creation.py",
        },
        {
            "id": "test_real_sdk_dependency_final_execution_confirmation",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_final_execution_confirmation.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyExecutionTaskCreationRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖执行任务创建当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency task creation"}],
        )


def build_real_sdk_dependency_execution_task_creation_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyExecutionTaskCreationRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            final_confirmation = build_real_sdk_dependency_final_execution_confirmation(request, root=root)
        else:
            final_confirmation = None
    except ProviderError:
        final_confirmation = None
    if final_confirmation is not None:
        context["finalExecutionConfirmationReady"] = bool(
            final_confirmation.get("readyForReviewedDependencyExecutionTask", False)
        )
        context["finalExecutionConfirmationSummary"] = _final_confirmation_summary(final_confirmation)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_execution_task_creation(
    request: RealSdkDependencyExecutionTaskCreationRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    final_confirmation = build_real_sdk_dependency_final_execution_confirmation(request, root=root)
    final_confirmation_ready = final_confirmation.get("readyForReviewedDependencyExecutionTask") is True
    checklist = _task_creation_checklist(request, final_confirmation_ready=final_confirmation_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "finalExecutionConfirmationReady": final_confirmation_ready,
        "finalExecutionConfirmationSummary": _final_confirmation_summary(final_confirmation),
        "executionTaskCreationChecklist": checklist,
        "executionTaskCreationModelReady": checklist_passed,
        "readyForDisabledDependencyExecutionTaskRecord": checklist_passed,
        "taskCreationModel": _task_creation_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖执行任务创建模型已生成；当前不会创建或持久化任务、派发执行、读取或写入依赖文件、生成或应用 patch、执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
