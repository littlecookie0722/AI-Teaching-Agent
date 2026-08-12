"""Disabled real SDK dependency content read approval model.

This module prepares a local approval model for future dependency manifest and
lockfile content review. It does not read dependency files, return dependency
content, persist approval records, write artifacts, generate patches,
materialize or execute commands, install SDKs, import SDKs, check secrets, use
network access, call real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_readonly_snapshot import (
    RealSdkDependencyReadonlySnapshotRequest,
    build_real_sdk_dependency_readonly_snapshot,
    describe_real_sdk_dependency_readonly_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_CONTENT_READ_APPROVAL_ID = "real_sdk_dependency_content_read_approval"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyContentReadApprovalRequest(RealSdkDependencyReadonlySnapshotRequest):
    content_read_approval_scope_confirmed: bool = False
    content_read_reviewer_confirmed: bool = False
    content_read_reason_confirmed: bool = False
    content_read_redaction_policy_confirmed: bool = False
    manifest_content_read_policy_confirmed: bool = False
    lockfile_content_read_policy_confirmed: bool = False
    no_dependency_content_read_now_confirmed: bool = False
    no_content_persistence_confirmed: bool = False
    no_patch_generation_after_content_read_approval_confirmed: bool = False
    no_command_execution_after_content_read_approval_confirmed: bool = False
    no_dependency_install_after_content_read_approval_confirmed: bool = False
    no_real_call_after_content_read_approval_confirmed: bool = False


def _base_context(request: RealSdkDependencyContentReadApprovalRequest, *, root: Path) -> dict[str, Any]:
    snapshot_descriptor = describe_real_sdk_dependency_readonly_snapshot(root=root)
    return {
        **snapshot_descriptor,
        "contentReadApprovalId": REAL_SDK_DEPENDENCY_CONTENT_READ_APPROVAL_ID,
        "gateId": REAL_SDK_DEPENDENCY_CONTENT_READ_APPROVAL_ID,
        "upstreamGateId": "real_sdk_dependency_readonly_snapshot",
        "gateMode": "DEPENDENCY_CONTENT_READ_APPROVAL_DISABLED_ONLY",
        "approvalMode": "LOCAL_CONTENT_READ_APPROVAL_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "readonlySnapshotRequired": True,
        "readonlySnapshotModelReady": False,
        "contentReadApprovalOnly": True,
        "contentReadApprovalModelReady": False,
        "readyForFutureDependencyContentReadReview": False,
        "pipeline": [
            "real_sdk_dependency_target_resolver",
            "real_sdk_dependency_readonly_snapshot",
            "dependency_content_read_approval_disabled_shell",
            "future_dependency_content_read_after_explicit_approval",
            "future_dependency_patch_generation_after_content_review",
        ],
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
        "realCallAfterContentReadApprovalAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_content_read_approval(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyContentReadApprovalRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresReadonlySnapshotModelReady": True,
        "requiresContentReadApprovalScope": True,
        "requiresContentReadRedactionPolicy": True,
        "requiresNoContentReadNowPolicy": True,
        "requiresNoContentPersistencePolicy": True,
    }


def _readonly_snapshot_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "readonlySnapshotId": snapshot["readonlySnapshotId"],
        "targetResolverModelReady": snapshot["targetResolverModelReady"],
        "readonlySnapshotModelReady": snapshot["readonlySnapshotModelReady"],
        "readyForReadonlyDependencySnapshotReview": snapshot["readyForReadonlyDependencySnapshotReview"],
        "dependencySnapshotReadFromFile": snapshot["dependencySnapshotReadFromFile"],
        "dependencySnapshotContentCaptured": snapshot["dependencySnapshotContentCaptured"],
        "snapshotFileWritten": snapshot["snapshotFileWritten"],
        "patchGenerated": snapshot["patchGenerated"],
        "commandExecuted": snapshot["commandExecuted"],
        "dependencyInstallExecuted": snapshot["dependencyInstallExecuted"],
        "secretPresenceChecked": snapshot["secretPresenceChecked"],
        "networkAccess": snapshot["networkAccess"],
        "realLlmCalled": snapshot["realLlmCalled"],
    }


def _content_read_checklist(
    request: RealSdkDependencyContentReadApprovalRequest,
    *,
    readonly_snapshot_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "readonly_snapshot_model_ready", "passed": readonly_snapshot_ready, "required": True},
        {
            "id": "content_read_approval_scope_confirmed",
            "passed": request.content_read_approval_scope_confirmed,
            "required": True,
        },
        {
            "id": "content_read_reviewer_confirmed",
            "passed": request.content_read_reviewer_confirmed,
            "required": True,
        },
        {
            "id": "content_read_reason_confirmed",
            "passed": request.content_read_reason_confirmed,
            "required": True,
        },
        {
            "id": "content_read_redaction_policy_confirmed",
            "passed": request.content_read_redaction_policy_confirmed,
            "required": True,
        },
        {
            "id": "manifest_content_read_policy_confirmed",
            "passed": request.manifest_content_read_policy_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_content_read_policy_confirmed",
            "passed": request.lockfile_content_read_policy_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_content_read_now_confirmed",
            "passed": request.no_dependency_content_read_now_confirmed,
            "required": True,
        },
        {
            "id": "no_content_persistence_confirmed",
            "passed": request.no_content_persistence_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_generation_after_content_read_approval_confirmed",
            "passed": request.no_patch_generation_after_content_read_approval_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_content_read_approval_confirmed",
            "passed": request.no_command_execution_after_content_read_approval_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_content_read_approval_confirmed",
            "passed": request.no_dependency_install_after_content_read_approval_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_content_read_approval_confirmed",
            "passed": request.no_real_call_after_content_read_approval_confirmed,
            "required": True,
        },
    ]


def _content_read_approval_model(request: RealSdkDependencyContentReadApprovalRequest) -> dict[str, Any]:
    return {
        "approvalId": REAL_SDK_DEPENDENCY_CONTENT_READ_APPROVAL_ID,
        "approvalOnly": True,
        "materializedNow": False,
        "readNow": False,
        "writeNow": False,
        "persistNow": False,
        "patchNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "contentReadScope": {
            "candidateManifestTargets": ["pyproject.toml", "requirements.txt"],
            "candidateLockfileTargets": ["uv.lock", "poetry.lock", "requirements.lock"],
            "contentIncludedNow": False,
            "fileReadNow": False,
            "rawContentReturnedNow": False,
        },
        "redactionPolicy": {
            "secretPatternsRequired": True,
            "secretValueReadNow": False,
            "rawDependencyContentReturnedNow": False,
            "dependencyContentPersistedNow": False,
        },
        "blockedActions": [
            {"id": "read_dependency_manifest_content", "allowedNow": False},
            {"id": "read_dependency_lockfile_content", "allowedNow": False},
            {"id": "return_raw_dependency_content", "allowedNow": False},
            {"id": "persist_dependency_content", "allowedNow": False},
            {"id": "write_content_read_approval_artifact", "allowedNow": False},
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
        "contentReadApprovalModelReady": False,
        "readyForFutureDependencyContentReadReview": False,
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
        "realCallAfterContentReadApprovalAuthorized": False,
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
            {"field": "dependency_content_read", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "raw_dependency_content_return", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "dependency_content_persistence", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "content_read_approval_artifact_write", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "patch_generation", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "network_call", "reason": "not_allowed_by_content_read_approval_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_content_read_approval_shell"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_content_read_approval",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_approval.py",
        },
        {
            "id": "test_real_sdk_dependency_readonly_snapshot",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_readonly_snapshot.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyContentReadApprovalRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 content read approval 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency content read approval shell"}],
        )


def build_real_sdk_dependency_content_read_approval_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyContentReadApprovalRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            snapshot = build_real_sdk_dependency_readonly_snapshot(request, root=root)
        else:
            snapshot = None
    except ProviderError:
        snapshot = None
    if snapshot is not None:
        context["readonlySnapshotModelReady"] = bool(snapshot.get("readyForReadonlyDependencySnapshotReview", False))
        context["readonlySnapshotSummary"] = _readonly_snapshot_summary(snapshot)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_content_read_approval(
    request: RealSdkDependencyContentReadApprovalRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    snapshot = build_real_sdk_dependency_readonly_snapshot(request, root=root)
    snapshot_ready = snapshot.get("readyForReadonlyDependencySnapshotReview") is True
    checklist = _content_read_checklist(request, readonly_snapshot_ready=snapshot_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "readonlySnapshotModelReady": snapshot_ready,
        "readonlySnapshotSummary": _readonly_snapshot_summary(snapshot),
        "contentReadApprovalChecklist": checklist,
        "contentReadApprovalModelReady": checklist_passed,
        "readyForFutureDependencyContentReadReview": checklist_passed,
        "contentReadApprovalModel": _content_read_approval_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 content read approval 模型已生成；当前不会读取依赖文件内容、返回原文、持久化内容或审批记录、写产物、生成 patch、物化或执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
