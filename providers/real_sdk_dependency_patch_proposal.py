"""Disabled real SDK dependency patch proposal.

This module turns the dependency change preview into a reviewable patch plan for
a future implementation task. It does not write patch files, generate real diff
artifacts, apply patches, write dependency manifests, install SDKs, import SDKs,
check secrets, call networks, create tasks, or publish content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS
from .real_sdk_dependency_change_preview import (
    RealSdkDependencyChangePreviewRequest,
    build_real_sdk_dependency_change_preview,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_PATCH_PROPOSAL_ID = "real_sdk_dependency_patch_proposal"
SUPPORTED_PROVIDER = "openai"
TARGET_PACKAGE = "openai"


@dataclass(frozen=True)
class RealSdkDependencyPatchProposalRequest:
    provider_id: str
    operation: str = "generateJson"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    timeout_seconds: int = 30
    retry_count: int = 1
    concurrency_limit: int = 1
    payload: Mapping[str, Any] | None = None
    approval_ref: str | None = None
    reviewer: str | None = None
    dry_run_plan_confirmed: bool = False
    runtime_guard_confirmed: bool = False
    schema_review_confirmed: bool = False
    human_review_policy_confirmed: bool = False
    audit_redaction_confirmed: bool = False
    target_model_alias: str = DEFAULT_MODEL_ALIAS
    task_ref: str | None = None
    sdk_dependency_review_confirmed: bool = False
    provider_contract_review_confirmed: bool = False
    runtime_contract_review_confirmed: bool = False
    secret_injection_review_confirmed: bool = False
    network_access_review_confirmed: bool = False
    rollback_plan_confirmed: bool = False
    minimal_impl_review_confirmed: bool = False
    sdk_package_review_confirmed: bool = False
    sdk_version_pin_review_confirmed: bool = False
    dependency_license_review_confirmed: bool = False
    dependency_hash_review_confirmed: bool = False
    env_var_name_review_confirmed: bool = False
    env_example_review_confirmed: bool = False
    secret_non_read_policy_confirmed: bool = False
    ci_install_policy_confirmed: bool = False
    package_manager_review_confirmed: bool = False
    lockfile_strategy_review_confirmed: bool = False
    version_pin_strategy_confirmed: bool = False
    hash_verification_strategy_confirmed: bool = False
    rollback_files_review_confirmed: bool = False
    ci_cache_policy_confirmed: bool = False
    no_install_execution_confirmed: bool = False
    no_network_policy_confirmed: bool = False
    no_secret_policy_confirmed: bool = False
    command_review_confirmed: bool = False
    dependency_file_review_confirmed: bool = False
    lockfile_diff_review_confirmed: bool = False
    offline_ci_review_confirmed: bool = False
    rollback_command_review_confirmed: bool = False
    execution_disabled_confirmed: bool = False
    preview_scope_confirmed: bool = False
    manifest_preview_confirmed: bool = False
    lockfile_preview_confirmed: bool = False
    rollback_preview_confirmed: bool = False
    no_diff_generation_confirmed: bool = False
    no_file_write_confirmed: bool = False
    patch_scope_confirmed: bool = False
    patch_plan_review_confirmed: bool = False
    no_patch_file_write_confirmed: bool = False
    no_patch_apply_confirmed: bool = False
    no_diff_artifact_confirmed: bool = False
    trace_id: str | None = None


def _load_runtime_contract(root: Path) -> dict[str, Any]:
    with (root / "config/runtime.contract.json").open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ProviderError(
            "PROVIDER_CONTRACT_ERROR",
            "Runtime contract root must be object",
            [{"field": "config/runtime.contract.json", "reason": "root must be object"}],
        )
    return payload


def _find_provider(contract: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    for provider in contract.get("providers", []):
        if provider.get("id") == provider_id:
            return provider
    return None


def _safe_runtime_flags(runtime_contract: dict[str, Any]) -> dict[str, str]:
    return {
        key: value
        for key, value in runtime_contract.get("defaults", {}).items()
        if key.startswith("ENABLE_") or key in {"APP_PHASE", "APP_MODE"}
    }


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _change_preview_request(request: RealSdkDependencyPatchProposalRequest) -> RealSdkDependencyChangePreviewRequest:
    return RealSdkDependencyChangePreviewRequest(
        provider_id=request.provider_id,
        operation=request.operation,
        prompt_id=request.prompt_id,
        output_kind=request.output_kind,
        input_ref=request.input_ref,
        timeout_seconds=request.timeout_seconds,
        retry_count=request.retry_count,
        concurrency_limit=request.concurrency_limit,
        payload=request.payload,
        approval_ref=request.approval_ref,
        reviewer=request.reviewer,
        dry_run_plan_confirmed=request.dry_run_plan_confirmed,
        runtime_guard_confirmed=request.runtime_guard_confirmed,
        schema_review_confirmed=request.schema_review_confirmed,
        human_review_policy_confirmed=request.human_review_policy_confirmed,
        audit_redaction_confirmed=request.audit_redaction_confirmed,
        target_model_alias=request.target_model_alias,
        task_ref=request.task_ref,
        sdk_dependency_review_confirmed=request.sdk_dependency_review_confirmed,
        provider_contract_review_confirmed=request.provider_contract_review_confirmed,
        runtime_contract_review_confirmed=request.runtime_contract_review_confirmed,
        secret_injection_review_confirmed=request.secret_injection_review_confirmed,
        network_access_review_confirmed=request.network_access_review_confirmed,
        rollback_plan_confirmed=request.rollback_plan_confirmed,
        minimal_impl_review_confirmed=request.minimal_impl_review_confirmed,
        sdk_package_review_confirmed=request.sdk_package_review_confirmed,
        sdk_version_pin_review_confirmed=request.sdk_version_pin_review_confirmed,
        dependency_license_review_confirmed=request.dependency_license_review_confirmed,
        dependency_hash_review_confirmed=request.dependency_hash_review_confirmed,
        env_var_name_review_confirmed=request.env_var_name_review_confirmed,
        env_example_review_confirmed=request.env_example_review_confirmed,
        secret_non_read_policy_confirmed=request.secret_non_read_policy_confirmed,
        ci_install_policy_confirmed=request.ci_install_policy_confirmed,
        package_manager_review_confirmed=request.package_manager_review_confirmed,
        lockfile_strategy_review_confirmed=request.lockfile_strategy_review_confirmed,
        version_pin_strategy_confirmed=request.version_pin_strategy_confirmed,
        hash_verification_strategy_confirmed=request.hash_verification_strategy_confirmed,
        rollback_files_review_confirmed=request.rollback_files_review_confirmed,
        ci_cache_policy_confirmed=request.ci_cache_policy_confirmed,
        no_install_execution_confirmed=request.no_install_execution_confirmed,
        no_network_policy_confirmed=request.no_network_policy_confirmed,
        no_secret_policy_confirmed=request.no_secret_policy_confirmed,
        command_review_confirmed=request.command_review_confirmed,
        dependency_file_review_confirmed=request.dependency_file_review_confirmed,
        lockfile_diff_review_confirmed=request.lockfile_diff_review_confirmed,
        offline_ci_review_confirmed=request.offline_ci_review_confirmed,
        rollback_command_review_confirmed=request.rollback_command_review_confirmed,
        execution_disabled_confirmed=request.execution_disabled_confirmed,
        preview_scope_confirmed=request.preview_scope_confirmed,
        manifest_preview_confirmed=request.manifest_preview_confirmed,
        lockfile_preview_confirmed=request.lockfile_preview_confirmed,
        rollback_preview_confirmed=request.rollback_preview_confirmed,
        no_diff_generation_confirmed=request.no_diff_generation_confirmed,
        no_file_write_confirmed=request.no_file_write_confirmed,
        trace_id=request.trace_id,
    )


def _base_context(request: RealSdkDependencyPatchProposalRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    secret_env = provider.get("secretEnv") if provider else None
    return {
        "proposalId": REAL_SDK_DEPENDENCY_PATCH_PROPOSAL_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "proposalMode": "DEPENDENCY_PATCH_PROPOSAL_DISABLED_ONLY",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "supportedProvider": SUPPORTED_PROVIDER,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "targetPackage": TARGET_PACKAGE,
        "targetSecretEnv": secret_env,
        "secretNameOnly": True,
        "packageNameOnly": True,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "runtimeFlags": _safe_runtime_flags(runtime_contract),
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "changePreviewRequired": True,
        "changePreviewReady": False,
        "patchProposalChecklistPassed": False,
        "readyForDependencyPatchImplementationTask": False,
        "dependencyPatchProposalOnly": True,
        "dependencyPatchProposalReady": False,
        "patchProposalMaterialized": False,
        "patchFileWritten": False,
        "patchApplied": False,
        "dependencyPatchGenerated": False,
        "dependencyFileWritePlannedNow": False,
        "dependencyFileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "lockfileChanged": False,
        "dependencyLockfileChanged": False,
        "lockfileDiffGenerated": False,
        "dependencyDiffGenerated": False,
        "diffArtifactWritten": False,
        "rollbackDiffGenerated": False,
        "rollbackCommandGenerated": False,
        "offlineCiExecuted": False,
        "installerExecutionEnabled": False,
        "installCommandMaterialized": False,
        "dependencyInstallAllowed": False,
        "dependencyInstallCommandGenerated": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstalled": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "networkAccess": False,
        "networkAccessEnabledNow": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_patch_proposal(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, SUPPORTED_PROVIDER)
    request = RealSdkDependencyPatchProposalRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "phase": runtime_contract.get("phase", "Phase 1"),
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "targetSecretEnv": provider.get("secretEnv") if provider else None,
        "requiresChangePreview": True,
        "requiresPatchScopeReview": True,
        "requiresPatchPlanReview": True,
        "requiresNoPatchFileWritePolicy": True,
        "requiresNoPatchApplyPolicy": True,
        "pipeline": [
            "real_sdk_dependency_change_preview",
            "dependency_patch_plan",
            "patch_apply_policy_review",
            "future_dependency_patch_implementation_task",
        ],
    }


def _change_preview_summary(preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "previewId": preview["previewId"],
        "changePreviewChecklistPassed": preview["changePreviewChecklistPassed"],
        "readyForDependencyChangeImplementationTask": preview["readyForDependencyChangeImplementationTask"],
        "dependencyFileChanged": preview["dependencyFileChanged"],
        "dependencyDiffGenerated": preview["dependencyDiffGenerated"],
        "diffArtifactWritten": preview["diffArtifactWritten"],
        "secretPresenceChecked": preview["secretPresenceChecked"],
        "networkAccess": preview["networkAccess"],
    }


def _patch_proposal_checklist(
    request: RealSdkDependencyPatchProposalRequest,
    *,
    change_preview_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "change_preview_ready", "passed": change_preview_ready, "required": True},
        {"id": "patch_scope_confirmed", "passed": request.patch_scope_confirmed, "required": True},
        {"id": "patch_plan_review_confirmed", "passed": request.patch_plan_review_confirmed, "required": True},
        {"id": "no_patch_file_write_confirmed", "passed": request.no_patch_file_write_confirmed, "required": True},
        {"id": "no_patch_apply_confirmed", "passed": request.no_patch_apply_confirmed, "required": True},
        {"id": "no_diff_artifact_confirmed", "passed": request.no_diff_artifact_confirmed, "required": True},
    ]


def _patch_plan() -> list[dict[str, Any]]:
    return [
        {
            "id": "pyproject_toml_patch_plan",
            "targetPath": "pyproject.toml",
            "proposalOnly": True,
            "writeNow": False,
            "applyNow": False,
            "plannedChange": "future add reviewed openai dependency entry",
            "versionPlaceholder": "<reviewed-version>",
            "hashReviewRequired": True,
        },
        {
            "id": "requirements_txt_patch_plan",
            "targetPath": "requirements.txt",
            "proposalOnly": True,
            "writeNow": False,
            "applyNow": False,
            "plannedChange": "future add pinned openai dependency entry",
            "versionPlaceholder": "<reviewed-version>",
            "hashReviewRequired": True,
        },
        {
            "id": "lockfile_patch_plan",
            "targetPath": "future_lockfile",
            "proposalOnly": True,
            "writeNow": False,
            "applyNow": False,
            "plannedChange": "future lockfile regeneration in separate network-disabled CI task",
            "packageMetadataResolvedNow": False,
        },
    ]


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "future_dependency_patch_implementation_task", "reason": "must_be_separate_reviewed_task"},
            {"field": "patch_file_write", "reason": "not_written_by_proposal"},
            {"field": "patch_apply", "reason": "not_applied_by_proposal"},
            {"field": "dependency_diff_artifact", "reason": "not_generated_by_proposal"},
            {"field": "dependency_manifest_write", "reason": "not_written_by_proposal"},
            {"field": "package_resolution", "reason": "not_performed_by_proposal"},
            {"field": "network_call", "reason": "not_allowed_by_proposal"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_patch_proposal",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_patch_proposal.py",
        },
        {
            "id": "test_real_sdk_dependency_change_preview",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_change_preview.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyPatchProposalRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 patch proposal 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency patch proposal"}],
        )


def build_real_sdk_dependency_patch_proposal_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyPatchProposalRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            preview = build_real_sdk_dependency_change_preview(_change_preview_request(request), root=root)
        else:
            preview = None
    except ProviderError:
        preview = None
    if preview is not None:
        context["changePreviewReady"] = bool(preview.get("readyForDependencyChangeImplementationTask", False))
        context["changePreviewSummary"] = _change_preview_summary(preview)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_patch_proposal(
    request: RealSdkDependencyPatchProposalRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    preview = build_real_sdk_dependency_change_preview(_change_preview_request(request), root=root)
    change_preview_ready = preview.get("readyForDependencyChangeImplementationTask") is True
    checklist = _patch_proposal_checklist(request, change_preview_ready=change_preview_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "changePreviewReady": change_preview_ready,
        "changePreviewSummary": _change_preview_summary(preview),
        "patchProposalChecklist": checklist,
        "patchProposalChecklistPassed": checklist_passed,
        "readyForDependencyPatchImplementationTask": checklist_passed,
        "dependencyPatchProposalReady": checklist_passed,
        "patchPlan": _patch_plan(),
        "patchApplyPolicy": {
            "proposalOnly": True,
            "patchFileWritten": False,
            "patchApplied": False,
            "diffArtifactWritten": False,
            "requiresSeparateReviewedTask": True,
        },
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 patch proposal 已生成；当前不会写 patch、应用补丁、写依赖文件、生成 diff artifact、安装依赖、解析包元数据或联网。",
    }
