"""Disabled real SDK dependency target resolver model.

This module prepares a local candidate dependency target model for future
review. It does not read live dependency files, write target files, generate
patches, materialize or execute commands, install SDKs, import SDKs, check
secrets, use network access, call real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_dry_run_evidence import (
    RealSdkDependencyDryRunEvidenceRequest,
    build_real_sdk_dependency_dry_run_evidence,
    describe_real_sdk_dependency_dry_run_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_TARGET_RESOLVER_ID = "real_sdk_dependency_target_resolver"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyTargetResolverRequest(RealSdkDependencyDryRunEvidenceRequest):
    target_resolver_scope_confirmed: bool = False
    manifest_target_policy_confirmed: bool = False
    lockfile_target_policy_confirmed: bool = False
    path_safety_policy_confirmed: bool = False
    no_live_dependency_file_read_confirmed: bool = False
    no_target_file_write_confirmed: bool = False
    no_patch_generation_after_resolver_confirmed: bool = False
    no_command_execution_after_resolver_confirmed: bool = False
    no_dependency_install_after_resolver_confirmed: bool = False
    no_real_call_after_resolver_confirmed: bool = False


def _base_context(request: RealSdkDependencyTargetResolverRequest, *, root: Path) -> dict[str, Any]:
    evidence_descriptor = describe_real_sdk_dependency_dry_run_evidence(root=root)
    return {
        **evidence_descriptor,
        "targetResolverId": REAL_SDK_DEPENDENCY_TARGET_RESOLVER_ID,
        "gateId": REAL_SDK_DEPENDENCY_TARGET_RESOLVER_ID,
        "upstreamGateId": "real_sdk_dependency_dry_run_evidence",
        "gateMode": "DEPENDENCY_TARGET_RESOLVER_DISABLED_ONLY",
        "resolverMode": "LOCAL_TARGET_PATH_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "dryRunEvidenceRequired": True,
        "dryRunEvidenceModelReady": False,
        "targetResolverOnly": True,
        "targetResolverModelReady": False,
        "readyForDependencyTargetReview": False,
        "pipeline": [
            "real_sdk_dependency_executor_disabled",
            "real_sdk_dependency_dry_run_evidence",
            "dependency_target_resolver_disabled_shell",
            "future_dependency_manifest_readonly_review",
            "future_dependency_patch_generation_after_target_review",
        ],
        "targetPathResolutionExecuted": False,
        "dependencyManifestTargetResolved": False,
        "dependencyLockfileTargetResolved": False,
        "dependencySnapshotReadFromFile": False,
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
        "realCallAfterResolverAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_target_resolver(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyTargetResolverRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresDryRunEvidenceModelReady": True,
        "requiresManifestTargetPolicy": True,
        "requiresLockfileTargetPolicy": True,
        "requiresNoLiveDependencyFileReadPolicy": True,
        "pipeline": [
            "real_sdk_dependency_executor_disabled",
            "real_sdk_dependency_dry_run_evidence",
            "dependency_target_resolver_disabled_shell",
            "future_dependency_manifest_readonly_review",
            "future_dependency_patch_generation_after_target_review",
        ],
    }


def _dry_run_evidence_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "dryRunEvidenceId": evidence["dryRunEvidenceId"],
        "executorModelReady": evidence["executorModelReady"],
        "dryRunEvidenceModelReady": evidence["dryRunEvidenceModelReady"],
        "readyForCommandReviewEvidence": evidence["readyForCommandReviewEvidence"],
        "dryRunExecuted": evidence["dryRunExecuted"],
        "evidenceFileWritten": evidence["evidenceFileWritten"],
        "commandReviewRecordPersisted": evidence["commandReviewRecordPersisted"],
        "commandMaterialized": evidence["commandMaterialized"],
        "commandExecuted": evidence["commandExecuted"],
        "dependencyInstallExecuted": evidence["dependencyInstallExecuted"],
        "secretPresenceChecked": evidence["secretPresenceChecked"],
        "networkAccess": evidence["networkAccess"],
        "realLlmCalled": evidence["realLlmCalled"],
    }


def _resolver_checklist(
    request: RealSdkDependencyTargetResolverRequest,
    *,
    dry_run_evidence_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "dry_run_evidence_model_ready", "passed": dry_run_evidence_ready, "required": True},
        {
            "id": "target_resolver_scope_confirmed",
            "passed": request.target_resolver_scope_confirmed,
            "required": True,
        },
        {
            "id": "manifest_target_policy_confirmed",
            "passed": request.manifest_target_policy_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_target_policy_confirmed",
            "passed": request.lockfile_target_policy_confirmed,
            "required": True,
        },
        {
            "id": "path_safety_policy_confirmed",
            "passed": request.path_safety_policy_confirmed,
            "required": True,
        },
        {
            "id": "no_live_dependency_file_read_confirmed",
            "passed": request.no_live_dependency_file_read_confirmed,
            "required": True,
        },
        {
            "id": "no_target_file_write_confirmed",
            "passed": request.no_target_file_write_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_generation_after_resolver_confirmed",
            "passed": request.no_patch_generation_after_resolver_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_resolver_confirmed",
            "passed": request.no_command_execution_after_resolver_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_resolver_confirmed",
            "passed": request.no_dependency_install_after_resolver_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_resolver_confirmed",
            "passed": request.no_real_call_after_resolver_confirmed,
            "required": True,
        },
    ]


def _target_resolver_model(request: RealSdkDependencyTargetResolverRequest) -> dict[str, Any]:
    return {
        "resolverId": REAL_SDK_DEPENDENCY_TARGET_RESOLVER_ID,
        "materializedNow": False,
        "readNow": False,
        "writeNow": False,
        "persistNow": False,
        "patchNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "candidateTargets": [
            {
                "id": "pyproject_toml",
                "path": "pyproject.toml",
                "selectedNow": False,
                "readNow": False,
                "writeNow": False,
            },
            {
                "id": "requirements_txt",
                "path": "requirements.txt",
                "selectedNow": False,
                "readNow": False,
                "writeNow": False,
            },
        ],
        "lockfileTargets": [
            {"id": "uv_lock", "path": "uv.lock", "selectedNow": False, "readNow": False, "writeNow": False},
            {
                "id": "poetry_lock",
                "path": "poetry.lock",
                "selectedNow": False,
                "readNow": False,
                "writeNow": False,
            },
            {
                "id": "requirements_lock",
                "path": "requirements.lock",
                "selectedNow": False,
                "readNow": False,
                "writeNow": False,
            },
        ],
        "pathSafety": {
            "workspaceOnly": True,
            "absolutePathAllowed": False,
            "parentTraversalAllowed": False,
            "pathReadNow": False,
        },
        "blockedActions": [
            {"id": "read_live_dependency_manifest", "allowedNow": False},
            {"id": "read_live_dependency_lockfile", "allowedNow": False},
            {"id": "write_dependency_target", "allowedNow": False},
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
        "targetResolverModelReady": False,
        "readyForDependencyTargetReview": False,
        "targetPathResolutionExecuted": False,
        "dependencyManifestTargetResolved": False,
        "dependencyLockfileTargetResolved": False,
        "dependencySnapshotReadFromFile": False,
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
        "realCallAfterResolverAuthorized": False,
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
            {"field": "live_dependency_file_read", "reason": "not_allowed_by_target_resolver_shell"},
            {"field": "target_file_write", "reason": "not_allowed_by_target_resolver_shell"},
            {"field": "patch_generation", "reason": "not_allowed_by_target_resolver_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_target_resolver_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_target_resolver_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_target_resolver_shell"},
            {"field": "network_call", "reason": "not_allowed_by_target_resolver_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_target_resolver_shell"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_target_resolver",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_target_resolver.py",
        },
        {
            "id": "test_real_sdk_dependency_dry_run_evidence",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_dry_run_evidence.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyTargetResolverRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 target resolver 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency target resolver shell"}],
        )


def build_real_sdk_dependency_target_resolver_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyTargetResolverRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            evidence = build_real_sdk_dependency_dry_run_evidence(request, root=root)
        else:
            evidence = None
    except ProviderError:
        evidence = None
    if evidence is not None:
        context["dryRunEvidenceModelReady"] = bool(evidence.get("readyForCommandReviewEvidence", False))
        context["dryRunEvidenceSummary"] = _dry_run_evidence_summary(evidence)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_target_resolver(
    request: RealSdkDependencyTargetResolverRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    evidence = build_real_sdk_dependency_dry_run_evidence(request, root=root)
    evidence_ready = evidence.get("readyForCommandReviewEvidence") is True
    checklist = _resolver_checklist(request, dry_run_evidence_ready=evidence_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "dryRunEvidenceModelReady": evidence_ready,
        "dryRunEvidenceSummary": _dry_run_evidence_summary(evidence),
        "targetResolverChecklist": checklist,
        "targetResolverModelReady": checklist_passed,
        "readyForDependencyTargetReview": checklist_passed,
        "targetResolverModel": _target_resolver_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 target resolver 模型已生成；当前不会读取依赖文件、写目标文件、生成 patch、物化或执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
