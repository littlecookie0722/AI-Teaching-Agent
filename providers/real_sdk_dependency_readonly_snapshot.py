"""Disabled real SDK dependency readonly snapshot model.

This module prepares a local readonly snapshot review model for future
dependency manifest review. It does not read live dependency files, write
snapshot files, resolve target paths from disk, generate patches, materialize or
execute commands, install SDKs, import SDKs, check secrets, use network access,
call real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_target_resolver import (
    RealSdkDependencyTargetResolverRequest,
    build_real_sdk_dependency_target_resolver,
    describe_real_sdk_dependency_target_resolver,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_READONLY_SNAPSHOT_ID = "real_sdk_dependency_readonly_snapshot"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyReadonlySnapshotRequest(RealSdkDependencyTargetResolverRequest):
    readonly_snapshot_scope_confirmed: bool = False
    snapshot_review_policy_confirmed: bool = False
    manifest_snapshot_policy_confirmed: bool = False
    lockfile_snapshot_policy_confirmed: bool = False
    snapshot_redaction_policy_confirmed: bool = False
    no_live_dependency_file_read_after_snapshot_confirmed: bool = False
    no_snapshot_file_write_confirmed: bool = False
    no_patch_generation_after_snapshot_confirmed: bool = False
    no_command_execution_after_snapshot_confirmed: bool = False
    no_dependency_install_after_snapshot_confirmed: bool = False
    no_real_call_after_snapshot_confirmed: bool = False


def _base_context(request: RealSdkDependencyReadonlySnapshotRequest, *, root: Path) -> dict[str, Any]:
    target_descriptor = describe_real_sdk_dependency_target_resolver(root=root)
    return {
        **target_descriptor,
        "readonlySnapshotId": REAL_SDK_DEPENDENCY_READONLY_SNAPSHOT_ID,
        "gateId": REAL_SDK_DEPENDENCY_READONLY_SNAPSHOT_ID,
        "upstreamGateId": "real_sdk_dependency_target_resolver",
        "gateMode": "DEPENDENCY_READONLY_SNAPSHOT_DISABLED_ONLY",
        "snapshotMode": "LOCAL_SNAPSHOT_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "targetResolverRequired": True,
        "targetResolverModelReady": False,
        "readonlySnapshotOnly": True,
        "readonlySnapshotModelReady": False,
        "readyForReadonlyDependencySnapshotReview": False,
        "pipeline": [
            "real_sdk_dependency_dry_run_evidence",
            "real_sdk_dependency_target_resolver",
            "dependency_readonly_snapshot_disabled_shell",
            "future_dependency_manifest_content_review",
            "future_dependency_patch_generation_after_snapshot_review",
        ],
        "snapshotModelMaterialized": False,
        "snapshotReviewRecordPersisted": False,
        "snapshotFileWritten": False,
        "snapshotArtifactWritten": False,
        "targetPathResolutionExecuted": False,
        "dependencyManifestTargetResolved": False,
        "dependencyLockfileTargetResolved": False,
        "dependencySnapshotReadFromFile": False,
        "dependencySnapshotContentCaptured": False,
        "dependencyFileRead": False,
        "liveDependencyFileRead": False,
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
        "realCallAfterSnapshotAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_readonly_snapshot(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyReadonlySnapshotRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresTargetResolverModelReady": True,
        "requiresSnapshotReviewPolicy": True,
        "requiresNoSnapshotFileWritePolicy": True,
        "requiresNoLiveDependencyFileReadPolicy": True,
    }


def _target_resolver_summary(resolver: dict[str, Any]) -> dict[str, Any]:
    return {
        "targetResolverId": resolver["targetResolverId"],
        "dryRunEvidenceModelReady": resolver["dryRunEvidenceModelReady"],
        "targetResolverModelReady": resolver["targetResolverModelReady"],
        "readyForDependencyTargetReview": resolver["readyForDependencyTargetReview"],
        "targetPathResolutionExecuted": resolver["targetPathResolutionExecuted"],
        "liveDependencyFileRead": resolver["liveDependencyFileRead"],
        "targetFileWritten": resolver["targetFileWritten"],
        "patchGenerated": resolver["patchGenerated"],
        "commandExecuted": resolver["commandExecuted"],
        "dependencyInstallExecuted": resolver["dependencyInstallExecuted"],
        "secretPresenceChecked": resolver["secretPresenceChecked"],
        "networkAccess": resolver["networkAccess"],
        "realLlmCalled": resolver["realLlmCalled"],
    }


def _snapshot_checklist(
    request: RealSdkDependencyReadonlySnapshotRequest,
    *,
    target_resolver_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "target_resolver_model_ready", "passed": target_resolver_ready, "required": True},
        {
            "id": "readonly_snapshot_scope_confirmed",
            "passed": request.readonly_snapshot_scope_confirmed,
            "required": True,
        },
        {
            "id": "snapshot_review_policy_confirmed",
            "passed": request.snapshot_review_policy_confirmed,
            "required": True,
        },
        {
            "id": "manifest_snapshot_policy_confirmed",
            "passed": request.manifest_snapshot_policy_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_snapshot_policy_confirmed",
            "passed": request.lockfile_snapshot_policy_confirmed,
            "required": True,
        },
        {
            "id": "snapshot_redaction_policy_confirmed",
            "passed": request.snapshot_redaction_policy_confirmed,
            "required": True,
        },
        {
            "id": "no_live_dependency_file_read_after_snapshot_confirmed",
            "passed": request.no_live_dependency_file_read_after_snapshot_confirmed,
            "required": True,
        },
        {
            "id": "no_snapshot_file_write_confirmed",
            "passed": request.no_snapshot_file_write_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_generation_after_snapshot_confirmed",
            "passed": request.no_patch_generation_after_snapshot_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_snapshot_confirmed",
            "passed": request.no_command_execution_after_snapshot_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_snapshot_confirmed",
            "passed": request.no_dependency_install_after_snapshot_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_snapshot_confirmed",
            "passed": request.no_real_call_after_snapshot_confirmed,
            "required": True,
        },
    ]


def _readonly_snapshot_model(request: RealSdkDependencyReadonlySnapshotRequest) -> dict[str, Any]:
    return {
        "snapshotId": REAL_SDK_DEPENDENCY_READONLY_SNAPSHOT_ID,
        "materializedNow": False,
        "readNow": False,
        "writeNow": False,
        "persistNow": False,
        "patchNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "snapshotTargets": [
            {
                "id": "manifest_snapshot_model",
                "sourceCandidates": ["pyproject.toml", "requirements.txt"],
                "contentCapturedNow": False,
                "fileReadNow": False,
                "fileWrittenNow": False,
            },
            {
                "id": "lockfile_snapshot_model",
                "sourceCandidates": ["uv.lock", "poetry.lock", "requirements.lock"],
                "contentCapturedNow": False,
                "fileReadNow": False,
                "fileWrittenNow": False,
            },
        ],
        "redactionPolicy": {
            "secretPatternsRedacted": True,
            "dependencyContentIncludedNow": False,
            "secretValueReadNow": False,
        },
        "blockedActions": [
            {"id": "read_live_dependency_manifest", "allowedNow": False},
            {"id": "read_live_dependency_lockfile", "allowedNow": False},
            {"id": "write_snapshot_file", "allowedNow": False},
            {"id": "persist_snapshot_review_record", "allowedNow": False},
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
        "readonlySnapshotModelReady": False,
        "readyForReadonlyDependencySnapshotReview": False,
        "snapshotModelMaterialized": False,
        "snapshotReviewRecordPersisted": False,
        "snapshotFileWritten": False,
        "snapshotArtifactWritten": False,
        "targetPathResolutionExecuted": False,
        "dependencyManifestTargetResolved": False,
        "dependencyLockfileTargetResolved": False,
        "dependencySnapshotReadFromFile": False,
        "dependencySnapshotContentCaptured": False,
        "dependencyFileRead": False,
        "liveDependencyFileRead": False,
        "targetFileWritten": False,
        "dryRunExecuted": False,
        "installDryRunExecuted": False,
        "evidenceFileWritten": False,
        "commandReviewRecordPersisted": False,
        "commandMaterialized": False,
        "installCommandMaterialized": False,
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
        "realCallAfterSnapshotAuthorized": False,
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
            {"field": "live_dependency_file_read", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "snapshot_file_write", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "snapshot_review_persistence", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "patch_generation", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "network_call", "reason": "not_allowed_by_readonly_snapshot_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_readonly_snapshot_shell"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_readonly_snapshot",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_readonly_snapshot.py",
        },
        {
            "id": "test_real_sdk_dependency_target_resolver",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_target_resolver.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyReadonlySnapshotRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 readonly snapshot 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency readonly snapshot shell"}],
        )


def build_real_sdk_dependency_readonly_snapshot_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyReadonlySnapshotRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            resolver = build_real_sdk_dependency_target_resolver(request, root=root)
        else:
            resolver = None
    except ProviderError:
        resolver = None
    if resolver is not None:
        context["targetResolverModelReady"] = bool(resolver.get("readyForDependencyTargetReview", False))
        context["targetResolverSummary"] = _target_resolver_summary(resolver)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_readonly_snapshot(
    request: RealSdkDependencyReadonlySnapshotRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    resolver = build_real_sdk_dependency_target_resolver(request, root=root)
    resolver_ready = resolver.get("readyForDependencyTargetReview") is True
    checklist = _snapshot_checklist(request, target_resolver_ready=resolver_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "targetResolverModelReady": resolver_ready,
        "targetResolverSummary": _target_resolver_summary(resolver),
        "readonlySnapshotChecklist": checklist,
        "readonlySnapshotModelReady": checklist_passed,
        "readyForReadonlyDependencySnapshotReview": checklist_passed,
        "readonlySnapshotModel": _readonly_snapshot_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 readonly snapshot 模型已生成；当前不会读取依赖文件、写 snapshot 文件、持久化审查记录、生成 patch、物化或执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
