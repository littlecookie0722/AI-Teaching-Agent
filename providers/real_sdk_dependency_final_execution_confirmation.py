"""Disabled real SDK dependency final execution confirmation.

This module prepares a local final-confirmation model for a future real SDK
dependency-file change. It does not grant execution approval, create tasks,
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
from .real_sdk_dependency_readonly_diff_review import (
    RealSdkDependencyReadonlyDiffReviewRequest,
    build_real_sdk_dependency_readonly_diff_review,
    describe_real_sdk_dependency_readonly_diff_review,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_FINAL_EXECUTION_CONFIRMATION_ID = "real_sdk_dependency_final_execution_confirmation"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyFinalExecutionConfirmationRequest(RealSdkDependencyReadonlyDiffReviewRequest):
    readonly_diff_review_confirmed: bool = False
    final_approver_identity_confirmed: bool = False
    change_ticket_confirmed: bool = False
    maintenance_window_reconfirmed: bool = False
    rollback_checkpoint_confirmed: bool = False
    post_change_validation_confirmed: bool = False
    dependency_file_target_reconfirmed: bool = False
    no_execution_authorization_confirmed: bool = False
    no_dependency_file_mutation_confirmed: bool = False
    no_real_call_after_final_confirmation_confirmed: bool = False


def _base_context(request: RealSdkDependencyFinalExecutionConfirmationRequest, *, root: Path) -> dict[str, Any]:
    readonly_diff_descriptor = describe_real_sdk_dependency_readonly_diff_review(root=root)
    return {
        **readonly_diff_descriptor,
        "finalExecutionConfirmationId": REAL_SDK_DEPENDENCY_FINAL_EXECUTION_CONFIRMATION_ID,
        "gateId": REAL_SDK_DEPENDENCY_FINAL_EXECUTION_CONFIRMATION_ID,
        "upstreamGateId": "real_sdk_dependency_readonly_diff_review",
        "gateMode": "DEPENDENCY_FINAL_EXECUTION_CONFIRMATION_DISABLED_ONLY",
        "finalConfirmationMode": "LOCAL_FINAL_CONFIRMATION_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "readonlyDiffReviewRequired": True,
        "readonlyDiffReviewReady": False,
        "finalExecutionConfirmationOnly": True,
        "finalExecutionConfirmationReady": False,
        "readyForReviewedDependencyExecutionTask": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
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
        "realCallAfterFinalConfirmationAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_final_execution_confirmation(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyFinalExecutionConfirmationRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresReadonlyDiffReviewReady": True,
        "requiresFinalApproverIdentity": True,
        "requiresChangeTicket": True,
        "requiresNoExecutionAuthorizationPolicy": True,
        "pipeline": [
            "real_sdk_dependency_change_approval_package",
            "real_sdk_dependency_readonly_diff_review",
            "dependency_final_execution_confirmation",
            "future_reviewed_dependency_file_change_task",
            "future_real_llm_dry_run_after_dependency_review",
        ],
    }


def _readonly_diff_summary(readonly_diff: dict[str, Any]) -> dict[str, Any]:
    return {
        "readonlyDiffReviewId": readonly_diff["readonlyDiffReviewId"],
        "approvalPackageReady": readonly_diff["approvalPackageReady"],
        "readonlyDiffReviewReady": readonly_diff["readonlyDiffReviewReady"],
        "readyForReadonlyDependencyDiffReview": readonly_diff["readyForReadonlyDependencyDiffReview"],
        "diffReviewArtifactWritten": readonly_diff["diffReviewArtifactWritten"],
        "dependencySnapshotReadFromFile": readonly_diff["dependencySnapshotReadFromFile"],
        "patchGenerated": readonly_diff["patchGenerated"],
        "dependencyFileChanged": readonly_diff["dependencyFileChanged"],
        "secretPresenceChecked": readonly_diff["secretPresenceChecked"],
        "networkAccess": readonly_diff["networkAccess"],
        "realLlmCalled": readonly_diff["realLlmCalled"],
    }


def _final_confirmation_checklist(
    request: RealSdkDependencyFinalExecutionConfirmationRequest,
    *,
    readonly_diff_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "readonly_diff_review_ready", "passed": readonly_diff_ready, "required": True},
        {
            "id": "readonly_diff_review_confirmed",
            "passed": request.readonly_diff_review_confirmed,
            "required": True,
        },
        {
            "id": "final_approver_identity_confirmed",
            "passed": request.final_approver_identity_confirmed,
            "required": True,
        },
        {"id": "change_ticket_confirmed", "passed": request.change_ticket_confirmed, "required": True},
        {
            "id": "maintenance_window_reconfirmed",
            "passed": request.maintenance_window_reconfirmed,
            "required": True,
        },
        {
            "id": "rollback_checkpoint_confirmed",
            "passed": request.rollback_checkpoint_confirmed,
            "required": True,
        },
        {
            "id": "post_change_validation_confirmed",
            "passed": request.post_change_validation_confirmed,
            "required": True,
        },
        {
            "id": "dependency_file_target_reconfirmed",
            "passed": request.dependency_file_target_reconfirmed,
            "required": True,
        },
        {
            "id": "no_execution_authorization_confirmed",
            "passed": request.no_execution_authorization_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_mutation_confirmed",
            "passed": request.no_dependency_file_mutation_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_final_confirmation_confirmed",
            "passed": request.no_real_call_after_final_confirmation_confirmed,
            "required": True,
        },
    ]


def _final_confirmation_model(request: RealSdkDependencyFinalExecutionConfirmationRequest) -> dict[str, Any]:
    return {
        "confirmationId": REAL_SDK_DEPENDENCY_FINAL_EXECUTION_CONFIRMATION_ID,
        "materializedNow": False,
        "writeNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "targetFiles": [
            {"path": "requirements*.txt", "mutateNow": False, "writeNow": False},
            {"path": "pyproject.toml", "mutateNow": False, "writeNow": False},
            {"path": "lockfile", "mutateNow": False, "writeNow": False},
        ],
        "requiredEvidence": [
            {"id": "readonly_diff_review", "materializedNow": False},
            {"id": "final_approver_identity", "materializedNow": False},
            {"id": "change_ticket", "materializedNow": False},
            {"id": "maintenance_window", "materializedNow": False},
            {"id": "rollback_checkpoint", "materializedNow": False},
            {"id": "post_change_validation", "materializedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "finalExecutionConfirmationReady": False,
        "readyForReviewedDependencyExecutionTask": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "dependencyFileMutationAuthorized": False,
        "dependencyFileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "lockfileChanged": False,
        "dependencyLockfileChanged": False,
        "dependencyManifestMutated": False,
        "dependencyLockfileMutated": False,
        "diffReviewArtifactWritten": False,
        "diffGenerated": False,
        "realDiffGenerated": False,
        "dependencyDiffGenerated": False,
        "candidateDiffMaterialized": False,
        "dependencySnapshotReadFromFile": False,
        "dependencySnapshotWritten": False,
        "dependencyVersionResolved": False,
        "dependencyHashResolved": False,
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
        "realCallAuthorized": False,
        "realCallAfterFinalConfirmationAuthorized": False,
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
            {"field": "execution_approval", "reason": "not_granted_by_final_confirmation"},
            {"field": "execution_task_creation", "reason": "not_created_by_final_confirmation"},
            {"field": "dependency_file_mutation", "reason": "not_authorized_by_final_confirmation"},
            {"field": "dependency_manifest_write", "reason": "not_written_by_final_confirmation"},
            {"field": "dependency_lockfile_write", "reason": "not_written_by_final_confirmation"},
            {"field": "patch_generation", "reason": "not_generated_by_final_confirmation"},
            {"field": "command_execution", "reason": "not_allowed_by_final_confirmation"},
            {"field": "dependency_install", "reason": "not_allowed_by_final_confirmation"},
            {"field": "real_llm_call", "reason": "not_allowed_after_final_confirmation"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_final_confirmation"},
            {"field": "network_call", "reason": "not_allowed_by_final_confirmation"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_final_execution_confirmation",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_final_execution_confirmation.py",
        },
        {
            "id": "test_real_sdk_dependency_readonly_diff_review",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_readonly_diff_review.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyFinalExecutionConfirmationRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖最终执行确认当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in final dependency execution confirmation"}],
        )


def build_real_sdk_dependency_final_execution_confirmation_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyFinalExecutionConfirmationRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            readonly_diff = build_real_sdk_dependency_readonly_diff_review(request, root=root)
        else:
            readonly_diff = None
    except ProviderError:
        readonly_diff = None
    if readonly_diff is not None:
        context["readonlyDiffReviewReady"] = bool(readonly_diff.get("readyForReadonlyDependencyDiffReview", False))
        context["readonlyDiffReviewSummary"] = _readonly_diff_summary(readonly_diff)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_final_execution_confirmation(
    request: RealSdkDependencyFinalExecutionConfirmationRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    readonly_diff = build_real_sdk_dependency_readonly_diff_review(request, root=root)
    readonly_diff_ready = readonly_diff.get("readyForReadonlyDependencyDiffReview") is True
    checklist = _final_confirmation_checklist(request, readonly_diff_ready=readonly_diff_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "readonlyDiffReviewReady": readonly_diff_ready,
        "readonlyDiffReviewSummary": _readonly_diff_summary(readonly_diff),
        "finalExecutionConfirmationChecklist": checklist,
        "finalExecutionConfirmationReady": checklist_passed,
        "readyForReviewedDependencyExecutionTask": checklist_passed,
        "finalConfirmationModel": _final_confirmation_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖最终执行确认包已生成；当前不会授予执行批准、创建任务、读取或写入依赖文件、生成或应用 patch、执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
