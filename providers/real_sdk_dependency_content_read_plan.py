"""Disabled real SDK dependency content read plan model.

This module prepares a local review plan for a future dependency manifest and
lockfile content read. It does not read dependency files, return raw content,
persist content, write plan artifacts, generate patches, materialize or execute
commands, install SDKs, import SDKs, check secrets, use network access, call
real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_content_read_approval import (
    RealSdkDependencyContentReadApprovalRequest,
    build_real_sdk_dependency_content_read_approval,
    describe_real_sdk_dependency_content_read_approval,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_CONTENT_READ_PLAN_ID = "real_sdk_dependency_content_read_plan"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyContentReadPlanRequest(RealSdkDependencyContentReadApprovalRequest):
    content_read_plan_scope_confirmed: bool = False
    content_read_targets_reviewed: bool = False
    manifest_read_window_confirmed: bool = False
    lockfile_read_window_confirmed: bool = False
    redaction_test_plan_confirmed: bool = False
    reviewer_assignment_confirmed: bool = False
    no_dependency_content_read_during_plan_confirmed: bool = False
    no_raw_content_return_during_plan_confirmed: bool = False
    no_content_snapshot_write_confirmed: bool = False
    no_content_plan_artifact_write_confirmed: bool = False
    no_patch_generation_after_content_read_plan_confirmed: bool = False
    no_command_execution_after_content_read_plan_confirmed: bool = False
    no_dependency_install_after_content_read_plan_confirmed: bool = False
    no_real_call_after_content_read_plan_confirmed: bool = False


def _base_context(request: RealSdkDependencyContentReadPlanRequest, *, root: Path) -> dict[str, Any]:
    approval_descriptor = describe_real_sdk_dependency_content_read_approval(root=root)
    return {
        **approval_descriptor,
        "contentReadPlanId": REAL_SDK_DEPENDENCY_CONTENT_READ_PLAN_ID,
        "gateId": REAL_SDK_DEPENDENCY_CONTENT_READ_PLAN_ID,
        "upstreamGateId": "real_sdk_dependency_content_read_approval",
        "gateMode": "DEPENDENCY_CONTENT_READ_PLAN_DISABLED_ONLY",
        "planMode": "LOCAL_CONTENT_READ_PLAN_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "contentReadApprovalRequired": True,
        "contentReadApprovalModelReady": False,
        "contentReadPlanOnly": True,
        "contentReadPlanModelReady": False,
        "readyForFutureDependencyContentReadExecutionReview": False,
        "pipeline": [
            "real_sdk_dependency_readonly_snapshot",
            "real_sdk_dependency_content_read_approval",
            "dependency_content_read_plan_disabled_shell",
            "future_dependency_content_read_execution_after_explicit_review",
            "future_dependency_patch_generation_after_content_review",
        ],
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
        "realCallAfterContentReadPlanAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_content_read_plan(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyContentReadPlanRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresContentReadApprovalModelReady": True,
        "requiresContentReadPlanScope": True,
        "requiresReadTargetReview": True,
        "requiresRedactionTestPlan": True,
        "requiresNoContentReadDuringPlanPolicy": True,
    }


def _content_read_approval_summary(approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "contentReadApprovalId": approval["contentReadApprovalId"],
        "readonlySnapshotModelReady": approval["readonlySnapshotModelReady"],
        "contentReadApprovalModelReady": approval["contentReadApprovalModelReady"],
        "readyForFutureDependencyContentReadReview": approval["readyForFutureDependencyContentReadReview"],
        "dependencyContentReadAuthorized": approval["dependencyContentReadAuthorized"],
        "dependencyContentReadExecuted": approval["dependencyContentReadExecuted"],
        "dependencyContentReturned": approval["dependencyContentReturned"],
        "patchGenerated": approval["patchGenerated"],
        "commandExecuted": approval["commandExecuted"],
        "dependencyInstallExecuted": approval["dependencyInstallExecuted"],
        "secretPresenceChecked": approval["secretPresenceChecked"],
        "networkAccess": approval["networkAccess"],
        "realLlmCalled": approval["realLlmCalled"],
    }


def _content_read_plan_checklist(
    request: RealSdkDependencyContentReadPlanRequest,
    *,
    content_read_approval_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "content_read_approval_model_ready", "passed": content_read_approval_ready, "required": True},
        {
            "id": "content_read_plan_scope_confirmed",
            "passed": request.content_read_plan_scope_confirmed,
            "required": True,
        },
        {
            "id": "content_read_targets_reviewed",
            "passed": request.content_read_targets_reviewed,
            "required": True,
        },
        {
            "id": "manifest_read_window_confirmed",
            "passed": request.manifest_read_window_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_read_window_confirmed",
            "passed": request.lockfile_read_window_confirmed,
            "required": True,
        },
        {
            "id": "redaction_test_plan_confirmed",
            "passed": request.redaction_test_plan_confirmed,
            "required": True,
        },
        {
            "id": "reviewer_assignment_confirmed",
            "passed": request.reviewer_assignment_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_content_read_during_plan_confirmed",
            "passed": request.no_dependency_content_read_during_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_raw_content_return_during_plan_confirmed",
            "passed": request.no_raw_content_return_during_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_content_snapshot_write_confirmed",
            "passed": request.no_content_snapshot_write_confirmed,
            "required": True,
        },
        {
            "id": "no_content_plan_artifact_write_confirmed",
            "passed": request.no_content_plan_artifact_write_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_generation_after_content_read_plan_confirmed",
            "passed": request.no_patch_generation_after_content_read_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_content_read_plan_confirmed",
            "passed": request.no_command_execution_after_content_read_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_content_read_plan_confirmed",
            "passed": request.no_dependency_install_after_content_read_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_content_read_plan_confirmed",
            "passed": request.no_real_call_after_content_read_plan_confirmed,
            "required": True,
        },
    ]


def _content_read_plan_model(request: RealSdkDependencyContentReadPlanRequest) -> dict[str, Any]:
    return {
        "planId": REAL_SDK_DEPENDENCY_CONTENT_READ_PLAN_ID,
        "planOnly": True,
        "plannedReadOnly": True,
        "materializedNow": False,
        "readNow": False,
        "writeNow": False,
        "persistNow": False,
        "patchNow": False,
        "executeNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "plannedTargets": [
            {
                "id": "manifest_content_read_plan",
                "sourceCandidates": ["pyproject.toml", "requirements.txt"],
                "fileReadNow": False,
                "contentIncludedNow": False,
                "rawContentReturnedNow": False,
                "snapshotWrittenNow": False,
            },
            {
                "id": "lockfile_content_read_plan",
                "sourceCandidates": ["uv.lock", "poetry.lock", "requirements.lock"],
                "fileReadNow": False,
                "contentIncludedNow": False,
                "rawContentReturnedNow": False,
                "snapshotWrittenNow": False,
            },
        ],
        "reviewPlan": [
            {"id": "confirm_read_scope", "requiredBeforeFutureRead": True, "doneNow": False},
            {"id": "confirm_redaction_test", "requiredBeforeFutureRead": True, "doneNow": False},
            {"id": "confirm_no_raw_content_return", "requiredBeforeFutureRead": True, "doneNow": False},
            {"id": "confirm_no_content_persistence", "requiredBeforeFutureRead": True, "doneNow": False},
        ],
        "redactionPlan": {
            "secretPatternsRequired": True,
            "secretValueReadNow": False,
            "rawDependencyContentReturnedNow": False,
            "contentPersistedNow": False,
        },
        "blockedActions": [
            {"id": "read_dependency_manifest_content", "allowedNow": False},
            {"id": "read_dependency_lockfile_content", "allowedNow": False},
            {"id": "return_raw_dependency_content", "allowedNow": False},
            {"id": "persist_dependency_content", "allowedNow": False},
            {"id": "write_content_read_plan_artifact", "allowedNow": False},
            {"id": "write_content_snapshot", "allowedNow": False},
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
        "contentReadPlanModelReady": False,
        "readyForFutureDependencyContentReadExecutionReview": False,
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
        "snapshotFileWritten": False,
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
        "realCallAfterContentReadPlanAuthorized": False,
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
            {"field": "dependency_content_read", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "raw_dependency_content_return", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "dependency_content_persistence", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "content_read_plan_artifact_write", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "content_snapshot_write", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "patch_generation", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "network_call", "reason": "not_allowed_by_content_read_plan_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_content_read_plan_shell"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_content_read_plan",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_plan.py",
        },
        {
            "id": "test_real_sdk_dependency_content_read_approval",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_approval.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyContentReadPlanRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 content read plan 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency content read plan shell"}],
        )


def build_real_sdk_dependency_content_read_plan_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyContentReadPlanRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            approval = build_real_sdk_dependency_content_read_approval(request, root=root)
        else:
            approval = None
    except ProviderError:
        approval = None
    if approval is not None:
        context["contentReadApprovalModelReady"] = bool(
            approval.get("readyForFutureDependencyContentReadReview", False)
        )
        context["contentReadApprovalSummary"] = _content_read_approval_summary(approval)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_content_read_plan(
    request: RealSdkDependencyContentReadPlanRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    approval = build_real_sdk_dependency_content_read_approval(request, root=root)
    approval_ready = approval.get("readyForFutureDependencyContentReadReview") is True
    checklist = _content_read_plan_checklist(request, content_read_approval_ready=approval_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "contentReadApprovalModelReady": approval_ready,
        "contentReadApprovalSummary": _content_read_approval_summary(approval),
        "contentReadPlanChecklist": checklist,
        "contentReadPlanModelReady": checklist_passed,
        "readyForFutureDependencyContentReadExecutionReview": checklist_passed,
        "contentReadPlanModel": _content_read_plan_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 content read plan 模型已生成；当前不会读取依赖文件内容、返回原文、持久化内容或计划记录、写产物、生成 patch、物化或执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
