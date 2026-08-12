"""Disabled real SDK dependency content read final confirmation model.

This module records a local final confirmation model for a future readonly
dependency manifest and lockfile content read. It does not read dependency
files, return raw content, persist content, write artifacts, generate patches,
materialize or execute commands, install SDKs, import SDKs, check secrets, use
network access, call real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_content_read_plan import (
    RealSdkDependencyContentReadPlanRequest,
    build_real_sdk_dependency_content_read_plan,
    describe_real_sdk_dependency_content_read_plan,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_CONTENT_READ_FINAL_CONFIRMATION_ID = (
    "real_sdk_dependency_content_read_final_confirmation"
)
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyContentReadFinalConfirmationRequest(RealSdkDependencyContentReadPlanRequest):
    content_read_final_scope_confirmed: bool = False
    content_read_final_approver_confirmed: bool = False
    content_read_ticket_confirmed: bool = False
    content_read_targets_final_confirmed: bool = False
    manifest_read_final_confirmed: bool = False
    lockfile_read_final_confirmed: bool = False
    redaction_policy_final_confirmed: bool = False
    no_raw_content_return_final_confirmed: bool = False
    no_content_persistence_final_confirmed: bool = False
    no_content_artifact_write_final_confirmed: bool = False
    no_patch_generation_after_content_read_final_confirmed: bool = False
    no_command_execution_after_content_read_final_confirmed: bool = False
    no_dependency_install_after_content_read_final_confirmed: bool = False
    no_real_call_after_content_read_final_confirmed: bool = False


def _base_context(
    request: RealSdkDependencyContentReadFinalConfirmationRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    plan_descriptor = describe_real_sdk_dependency_content_read_plan(root=root)
    return {
        **plan_descriptor,
        "contentReadFinalConfirmationId": REAL_SDK_DEPENDENCY_CONTENT_READ_FINAL_CONFIRMATION_ID,
        "gateId": REAL_SDK_DEPENDENCY_CONTENT_READ_FINAL_CONFIRMATION_ID,
        "upstreamGateId": "real_sdk_dependency_content_read_plan",
        "gateMode": "DEPENDENCY_CONTENT_READ_FINAL_CONFIRMATION_DISABLED_ONLY",
        "confirmationMode": "LOCAL_CONTENT_READ_FINAL_CONFIRMATION_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "contentReadPlanRequired": True,
        "contentReadPlanModelReady": False,
        "contentReadFinalConfirmationOnly": True,
        "contentReadFinalConfirmationModelReady": False,
        "readyForRealDependencyContentReadonlyReadTask": False,
        "pipeline": [
            "real_sdk_dependency_content_read_approval",
            "real_sdk_dependency_content_read_plan",
            "dependency_content_read_final_confirmation_disabled_shell",
            "future_dependency_content_read_readonly_execution",
            "future_dependency_patch_generation_after_content_review",
        ],
        "contentReadFinalConfirmationRecordPersisted": False,
        "contentReadFinalConfirmationArtifactWritten": False,
        "contentReadFinalConfirmationExecuted": False,
        "contentReadExecutionApprovalGranted": False,
        "contentReadExecutionTaskCreated": False,
        "contentReadPlanRecordPersisted": False,
        "contentReadPlanArtifactWritten": False,
        "contentReadPlanExecuted": False,
        "contentReadApprovalRecordPersisted": False,
        "contentReadApprovalArtifactWritten": False,
        "dependencyContentReadAuthorized": False,
        "dependencyContentReadExecuted": False,
        "dependencyManifestContentRead": False,
        "dependencyLockfileContentRead": False,
        "dependencyContentPersisted": False,
        "dependencyContentReturned": False,
        "rawDependencyContentReturned": False,
        "dependencyFileRead": False,
        "liveDependencyFileRead": False,
        "dependencySnapshotReadFromFile": False,
        "dependencySnapshotContentCaptured": False,
        "snapshotModelMaterialized": False,
        "snapshotReviewRecordPersisted": False,
        "snapshotFileWritten": False,
        "snapshotArtifactWritten": False,
        "targetPathResolutionExecuted": False,
        "dependencyManifestTargetResolved": False,
        "dependencyLockfileTargetResolved": False,
        "targetFileWritten": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "taskPersisted": False,
        "taskQueued": False,
        "executionDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "dryRunExecuted": False,
        "installDryRunExecuted": False,
        "evidenceFileWritten": False,
        "commandReviewRecordPersisted": False,
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
        "realCallAfterContentReadFinalConfirmationAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_content_read_final_confirmation(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyContentReadFinalConfirmationRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresContentReadPlanModelReady": True,
        "requiresContentReadFinalScope": True,
        "requiresFinalApprover": True,
        "requiresContentReadTicket": True,
        "requiresFinalRedactionPolicy": True,
        "requiresNoDependencyContentReadNowPolicy": True,
    }


def _content_read_plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "contentReadPlanId": plan["contentReadPlanId"],
        "contentReadApprovalModelReady": plan["contentReadApprovalModelReady"],
        "contentReadPlanModelReady": plan["contentReadPlanModelReady"],
        "readyForFutureDependencyContentReadExecutionReview": (
            plan["readyForFutureDependencyContentReadExecutionReview"]
        ),
        "dependencyContentReadAuthorized": plan["dependencyContentReadAuthorized"],
        "dependencyContentReadExecuted": plan["dependencyContentReadExecuted"],
        "dependencyContentReturned": plan["dependencyContentReturned"],
        "contentReadPlanArtifactWritten": plan["contentReadPlanArtifactWritten"],
        "patchGenerated": plan["patchGenerated"],
        "commandExecuted": plan["commandExecuted"],
        "dependencyInstallExecuted": plan["dependencyInstallExecuted"],
        "secretPresenceChecked": plan["secretPresenceChecked"],
        "networkAccess": plan["networkAccess"],
        "realLlmCalled": plan["realLlmCalled"],
    }


def _content_read_final_checklist(
    request: RealSdkDependencyContentReadFinalConfirmationRequest,
    *,
    content_read_plan_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "content_read_plan_model_ready", "passed": content_read_plan_ready, "required": True},
        {
            "id": "content_read_final_scope_confirmed",
            "passed": request.content_read_final_scope_confirmed,
            "required": True,
        },
        {
            "id": "content_read_final_approver_confirmed",
            "passed": request.content_read_final_approver_confirmed,
            "required": True,
        },
        {
            "id": "content_read_ticket_confirmed",
            "passed": request.content_read_ticket_confirmed,
            "required": True,
        },
        {
            "id": "content_read_targets_final_confirmed",
            "passed": request.content_read_targets_final_confirmed,
            "required": True,
        },
        {
            "id": "manifest_read_final_confirmed",
            "passed": request.manifest_read_final_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_read_final_confirmed",
            "passed": request.lockfile_read_final_confirmed,
            "required": True,
        },
        {
            "id": "redaction_policy_final_confirmed",
            "passed": request.redaction_policy_final_confirmed,
            "required": True,
        },
        {
            "id": "no_raw_content_return_final_confirmed",
            "passed": request.no_raw_content_return_final_confirmed,
            "required": True,
        },
        {
            "id": "no_content_persistence_final_confirmed",
            "passed": request.no_content_persistence_final_confirmed,
            "required": True,
        },
        {
            "id": "no_content_artifact_write_final_confirmed",
            "passed": request.no_content_artifact_write_final_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_generation_after_content_read_final_confirmed",
            "passed": request.no_patch_generation_after_content_read_final_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_content_read_final_confirmed",
            "passed": request.no_command_execution_after_content_read_final_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_content_read_final_confirmed",
            "passed": request.no_dependency_install_after_content_read_final_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_content_read_final_confirmed",
            "passed": request.no_real_call_after_content_read_final_confirmed,
            "required": True,
        },
    ]


def _content_read_final_confirmation_model(
    request: RealSdkDependencyContentReadFinalConfirmationRequest,
) -> dict[str, Any]:
    return {
        "confirmationId": REAL_SDK_DEPENDENCY_CONTENT_READ_FINAL_CONFIRMATION_ID,
        "confirmationOnly": True,
        "materializedNow": False,
        "readNow": False,
        "writeNow": False,
        "persistNow": False,
        "executeNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "finalReadScope": {
            "candidateManifestTargets": ["pyproject.toml", "requirements.txt"],
            "candidateLockfileTargets": ["uv.lock", "poetry.lock", "requirements.lock"],
            "readAllowedNow": False,
            "contentIncludedNow": False,
            "rawContentReturnedNow": False,
        },
        "finalSafetyAssertions": {
            "redactionRequiredBeforeFutureRead": True,
            "noRawContentReturn": True,
            "noContentPersistence": True,
            "noPatchGenerationNow": True,
            "noCommandExecutionNow": True,
            "noDependencyInstallNow": True,
            "noRealCallNow": True,
        },
        "blockedActions": [
            {"id": "read_dependency_manifest_content", "allowedNow": False},
            {"id": "read_dependency_lockfile_content", "allowedNow": False},
            {"id": "return_raw_dependency_content", "allowedNow": False},
            {"id": "persist_dependency_content", "allowedNow": False},
            {"id": "write_content_read_final_confirmation_artifact", "allowedNow": False},
            {"id": "create_content_read_execution_task", "allowedNow": False},
            {"id": "authorize_content_read_execution", "allowedNow": False},
            {"id": "generate_dependency_patch", "allowedNow": False},
            {"id": "materialize_command", "allowedNow": False},
            {"id": "execute_command", "allowedNow": False},
            {"id": "install_sdk_dependency", "allowedNow": False},
            {"id": "check_secret_presence", "allowedNow": False},
            {"id": "network_call", "allowedNow": False},
            {"id": "real_llm_call", "allowedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "contentReadFinalConfirmationModelReady": False,
        "readyForRealDependencyContentReadonlyReadTask": False,
        "contentReadFinalConfirmationRecordPersisted": False,
        "contentReadFinalConfirmationArtifactWritten": False,
        "contentReadFinalConfirmationExecuted": False,
        "contentReadExecutionApprovalGranted": False,
        "contentReadExecutionTaskCreated": False,
        "contentReadPlanRecordPersisted": False,
        "contentReadPlanArtifactWritten": False,
        "contentReadPlanExecuted": False,
        "dependencyContentReadAuthorized": False,
        "dependencyContentReadExecuted": False,
        "dependencyManifestContentRead": False,
        "dependencyLockfileContentRead": False,
        "dependencyContentPersisted": False,
        "dependencyContentReturned": False,
        "rawDependencyContentReturned": False,
        "dependencyFileRead": False,
        "liveDependencyFileRead": False,
        "targetPathResolutionExecuted": False,
        "targetFileWritten": False,
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyFileMutationAuthorized": False,
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
        "realCallAfterContentReadFinalConfirmationAuthorized": False,
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
            {"field": "dependency_content_read", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "raw_dependency_content_return", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "dependency_content_persistence", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {
                "field": "content_read_final_confirmation_artifact_write",
                "reason": "not_allowed_by_content_read_final_confirmation_shell",
            },
            {"field": "content_read_execution_task_creation", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "content_read_execution_authorization", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "patch_generation", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "network_call", "reason": "not_allowed_by_content_read_final_confirmation_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_content_read_final_confirmation_shell"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_content_read_final_confirmation",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_final_confirmation.py",
        },
        {
            "id": "test_real_sdk_dependency_content_read_plan",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_plan.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_READ", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyContentReadFinalConfirmationRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 content read final confirmation 当前只允许 OpenAI 单 Provider 范围",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed in dependency content read final confirmation shell",
                }
            ],
        )


def build_real_sdk_dependency_content_read_final_confirmation_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyContentReadFinalConfirmationRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            plan = build_real_sdk_dependency_content_read_plan(request, root=root)
        else:
            plan = None
    except ProviderError:
        plan = None
    if plan is not None:
        context["contentReadPlanModelReady"] = bool(
            plan.get("readyForFutureDependencyContentReadExecutionReview", False)
        )
        context["contentReadPlanSummary"] = _content_read_plan_summary(plan)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_content_read_final_confirmation(
    request: RealSdkDependencyContentReadFinalConfirmationRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    plan = build_real_sdk_dependency_content_read_plan(request, root=root)
    plan_ready = plan.get("readyForFutureDependencyContentReadExecutionReview") is True
    checklist = _content_read_final_checklist(request, content_read_plan_ready=plan_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "contentReadPlanModelReady": plan_ready,
        "contentReadPlanSummary": _content_read_plan_summary(plan),
        "contentReadFinalChecklist": checklist,
        "contentReadFinalConfirmationModelReady": checklist_passed,
        "readyForRealDependencyContentReadonlyReadTask": checklist_passed,
        "contentReadFinalConfirmationModel": _content_read_final_confirmation_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 content read final confirmation 模型已生成；当前不会读取依赖文件内容、返回原文、持久化内容或确认记录、写产物、创建执行任务、授权读取执行、生成 patch、物化或执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
