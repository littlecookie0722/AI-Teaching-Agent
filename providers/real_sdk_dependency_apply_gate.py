"""Disabled real SDK dependency apply gate.

This module reviews whether a future dependency patch apply task has enough
evidence to be created. It does not write dependency files, write patch files,
apply patches, generate diff artifacts, execute commands, install SDKs, import
SDKs, check secrets, call networks, create tasks, or publish content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS
from .real_sdk_dependency_patch_proposal import (
    RealSdkDependencyPatchProposalRequest,
    build_real_sdk_dependency_patch_proposal,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_APPLY_GATE_ID = "real_sdk_dependency_apply_gate"
SUPPORTED_PROVIDER = "openai"
TARGET_PACKAGE = "openai"


@dataclass(frozen=True)
class RealSdkDependencyApplyGateRequest(RealSdkDependencyPatchProposalRequest):
    apply_scope_confirmed: bool = False
    final_manual_approval_confirmed: bool = False
    dependency_patch_proposal_review_confirmed: bool = False
    dependency_file_backup_review_confirmed: bool = False
    rollback_rehearsal_review_confirmed: bool = False
    no_apply_execution_confirmed: bool = False
    no_dependency_file_write_confirmed: bool = False
    no_command_execution_confirmed: bool = False


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


def _base_context(request: RealSdkDependencyApplyGateRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    secret_env = provider.get("secretEnv") if provider else None
    return {
        "gateId": REAL_SDK_DEPENDENCY_APPLY_GATE_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "gateMode": "DEPENDENCY_APPLY_GATE_DISABLED_ONLY",
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
        "patchProposalRequired": True,
        "patchProposalReady": False,
        "applyGateChecklistPassed": False,
        "readyForFutureDependencyPatchApplyTask": False,
        "dependencyApplyGateOnly": True,
        "dependencyApplyGateReady": False,
        "applyAuthorized": False,
        "applyApprovalMaterialized": False,
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


def describe_real_sdk_dependency_apply_gate(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, SUPPORTED_PROVIDER)
    request = RealSdkDependencyApplyGateRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "phase": runtime_contract.get("phase", "Phase 1"),
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "targetSecretEnv": provider.get("secretEnv") if provider else None,
        "requiresPatchProposal": True,
        "requiresFinalManualApproval": True,
        "requiresRollbackReview": True,
        "requiresNoApplyExecutionPolicy": True,
        "pipeline": [
            "real_sdk_dependency_patch_proposal",
            "dependency_apply_gate",
            "future_dependency_patch_apply_task",
            "future_real_llm_dry_run_after_dependency_review",
        ],
    }


def _patch_proposal_summary(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposalId": proposal["proposalId"],
        "changePreviewReady": proposal["changePreviewReady"],
        "patchProposalChecklistPassed": proposal["patchProposalChecklistPassed"],
        "readyForDependencyPatchImplementationTask": proposal["readyForDependencyPatchImplementationTask"],
        "patchFileWritten": proposal["patchFileWritten"],
        "patchApplied": proposal["patchApplied"],
        "diffArtifactWritten": proposal["diffArtifactWritten"],
        "dependencyFileChanged": proposal["dependencyFileChanged"],
        "secretPresenceChecked": proposal["secretPresenceChecked"],
        "networkAccess": proposal["networkAccess"],
    }


def _apply_gate_checklist(
    request: RealSdkDependencyApplyGateRequest,
    *,
    patch_proposal_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "patch_proposal_ready", "passed": patch_proposal_ready, "required": True},
        {"id": "apply_scope_confirmed", "passed": request.apply_scope_confirmed, "required": True},
        {
            "id": "dependency_patch_proposal_review_confirmed",
            "passed": request.dependency_patch_proposal_review_confirmed,
            "required": True,
        },
        {"id": "final_manual_approval_confirmed", "passed": request.final_manual_approval_confirmed, "required": True},
        {
            "id": "dependency_file_backup_review_confirmed",
            "passed": request.dependency_file_backup_review_confirmed,
            "required": True,
        },
        {
            "id": "rollback_rehearsal_review_confirmed",
            "passed": request.rollback_rehearsal_review_confirmed,
            "required": True,
        },
        {"id": "no_apply_execution_confirmed", "passed": request.no_apply_execution_confirmed, "required": True},
        {
            "id": "no_dependency_file_write_confirmed",
            "passed": request.no_dependency_file_write_confirmed,
            "required": True,
        },
        {"id": "no_command_execution_confirmed", "passed": request.no_command_execution_confirmed, "required": True},
    ]


def _apply_evidence_plan() -> list[dict[str, Any]]:
    return [
        {
            "id": "manual_approval_record",
            "requiredForFutureApply": True,
            "materializedNow": False,
            "description": "future approved ticket or review record for dependency file changes",
        },
        {
            "id": "dependency_file_backup_plan",
            "requiredForFutureApply": True,
            "materializedNow": False,
            "description": "future backup or restore point for dependency manifests and lockfiles",
        },
        {
            "id": "rollback_rehearsal_plan",
            "requiredForFutureApply": True,
            "materializedNow": False,
            "description": "future reviewed rollback command sequence without secret output",
        },
        {
            "id": "post_apply_test_plan",
            "requiredForFutureApply": True,
            "materializedNow": False,
            "description": "future test suite run after dependency patch is applied in a reviewed task",
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
            {"field": "future_dependency_patch_apply_task", "reason": "must_be_separate_reviewed_task"},
            {"field": "apply_authorization", "reason": "not_granted_by_disabled_gate"},
            {"field": "patch_apply", "reason": "not_executed_by_gate"},
            {"field": "dependency_manifest_write", "reason": "not_written_by_gate"},
            {"field": "dependency_lockfile_write", "reason": "not_written_by_gate"},
            {"field": "command_execution", "reason": "not_allowed_by_gate"},
            {"field": "network_call", "reason": "not_allowed_by_gate"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_gate"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_apply_gate",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_apply_gate.py",
        },
        {
            "id": "test_real_sdk_dependency_patch_proposal",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_patch_proposal.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyApplyGateRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 apply gate 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency apply gate"}],
        )


def build_real_sdk_dependency_apply_gate_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyApplyGateRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            proposal = build_real_sdk_dependency_patch_proposal(request, root=root)
        else:
            proposal = None
    except ProviderError:
        proposal = None
    if proposal is not None:
        context["patchProposalReady"] = bool(proposal.get("readyForDependencyPatchImplementationTask", False))
        context["patchProposalSummary"] = _patch_proposal_summary(proposal)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_apply_gate(
    request: RealSdkDependencyApplyGateRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    proposal = build_real_sdk_dependency_patch_proposal(request, root=root)
    patch_proposal_ready = proposal.get("readyForDependencyPatchImplementationTask") is True
    checklist = _apply_gate_checklist(request, patch_proposal_ready=patch_proposal_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "patchProposalReady": patch_proposal_ready,
        "patchProposalSummary": _patch_proposal_summary(proposal),
        "applyGateChecklist": checklist,
        "applyGateChecklistPassed": checklist_passed,
        "readyForFutureDependencyPatchApplyTask": checklist_passed,
        "dependencyApplyGateReady": checklist_passed,
        "applyPolicy": {
            "gateOnly": True,
            "applyAuthorized": False,
            "applyApprovalMaterialized": False,
            "patchFileWritten": False,
            "patchApplied": False,
            "dependencyFileChanged": False,
            "commandExecuted": False,
            "requiresSeparateReviewedTask": True,
        },
        "applyEvidencePlan": _apply_evidence_plan(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 apply gate 已评估；当前不会写依赖文件、写 patch、应用补丁、执行命令、安装依赖、读取密钥或联网。",
    }
