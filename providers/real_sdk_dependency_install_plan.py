"""Real SDK dependency install plan draft.

This module drafts a future dependency-install implementation plan after the
dependency/env gate is reviewed. It does not install packages, resolve package
versions, download artifacts, modify dependency files or lockfiles, import
SDKs, check or read secrets, open network connections, create AI tasks, or
publish artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS
from .real_sdk_dependency_env_gate import (
    RealSdkDependencyEnvGateRequest,
    evaluate_real_sdk_dependency_env_gate,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_INSTALL_PLAN_ID = "real_sdk_dependency_install_plan"
SUPPORTED_PROVIDER = "openai"
TARGET_PACKAGE = "openai"


@dataclass(frozen=True)
class RealSdkDependencyInstallPlanRequest:
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


def _dependency_env_request(request: RealSdkDependencyInstallPlanRequest) -> RealSdkDependencyEnvGateRequest:
    return RealSdkDependencyEnvGateRequest(
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
        trace_id=request.trace_id,
    )


def _base_context(request: RealSdkDependencyInstallPlanRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    secret_env = provider.get("secretEnv") if provider else None
    return {
        "planId": REAL_SDK_DEPENDENCY_INSTALL_PLAN_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "planMode": "DEPENDENCY_INSTALL_DRAFT_ONLY",
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
        "dependencyEnvGateRequired": True,
        "dependencyEnvGateReady": False,
        "installPlanChecklistPassed": False,
        "readyForDependencyInstallImplementationReview": False,
        "dependencyInstallAllowed": False,
        "dependencyInstallCommandGenerated": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstalled": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "dependencyLockfileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
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


def describe_real_sdk_dependency_install_plan(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, SUPPORTED_PROVIDER)
    return {
        "planId": REAL_SDK_DEPENDENCY_INSTALL_PLAN_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "planMode": "DEPENDENCY_INSTALL_DRAFT_ONLY",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "supportedProvider": SUPPORTED_PROVIDER,
        "targetPackage": TARGET_PACKAGE,
        "targetSecretEnv": provider.get("secretEnv") if provider else None,
        "requiresDependencyEnvGate": True,
        "requiresPackageManagerReview": True,
        "requiresLockfileStrategyReview": True,
        "requiresVersionPinStrategy": True,
        "requiresHashVerificationStrategy": True,
        "requiresRollbackFilesReview": True,
        "requiresCiCachePolicy": True,
        "generatedStatus": "WAITING_REVIEW",
        "dependencyEnvGateReady": False,
        "readyForDependencyInstallImplementationReview": False,
        "dependencyInstallAllowed": False,
        "dependencyInstallCommandGenerated": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstalled": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "dependencyLockfileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
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
        "pipeline": [
            "real_sdk_dependency_env_gate",
            "package_manager_strategy_review",
            "version_pin_strategy_review",
            "hash_and_lockfile_strategy_review",
            "rollback_files_review",
            "future_dependency_install_implementation_task",
        ],
    }


def _gate_summary(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "gateId": gate["gateId"],
        "dependencyEnvChecklistPassed": gate["dependencyEnvChecklistPassed"],
        "readyForDependencyImplementationTask": gate["readyForDependencyImplementationTask"],
        "dependencyInstallAllowed": gate["dependencyInstallAllowed"],
        "sdkDependencyInstalled": gate["sdkDependencyInstalled"],
        "secretPresenceChecked": gate["secretPresenceChecked"],
        "networkAccess": gate["networkAccess"],
        "realLlmCalled": gate["realLlmCalled"],
    }


def _install_plan_checklist(
    request: RealSdkDependencyInstallPlanRequest,
    *,
    gate_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "dependency_env_gate_ready", "passed": gate_ready, "required": True},
        {"id": "package_manager_review_confirmed", "passed": request.package_manager_review_confirmed, "required": True},
        {"id": "lockfile_strategy_review_confirmed", "passed": request.lockfile_strategy_review_confirmed, "required": True},
        {"id": "version_pin_strategy_confirmed", "passed": request.version_pin_strategy_confirmed, "required": True},
        {"id": "hash_verification_strategy_confirmed", "passed": request.hash_verification_strategy_confirmed, "required": True},
        {"id": "rollback_files_review_confirmed", "passed": request.rollback_files_review_confirmed, "required": True},
        {"id": "ci_cache_policy_confirmed", "passed": request.ci_cache_policy_confirmed, "required": True},
        {"id": "no_install_execution_confirmed", "passed": request.no_install_execution_confirmed, "required": True},
        {"id": "no_network_policy_confirmed", "passed": request.no_network_policy_confirmed, "required": True},
        {"id": "no_secret_policy_confirmed", "passed": request.no_secret_policy_confirmed, "required": True},
    ]


def _planned_files() -> list[dict[str, Any]]:
    return [
        {
            "id": "dependency_manifest",
            "path": "pyproject.toml_or_requirements.txt",
            "plannedChange": "add_reviewed_openai_dependency_pin",
            "appliedNow": False,
            "requiresSeparateTask": True,
        },
        {
            "id": "dependency_lockfile",
            "path": "future_lockfile",
            "plannedChange": "record_reviewed_version_and_hashes",
            "appliedNow": False,
            "requiresSeparateTask": True,
        },
        {
            "id": "rollback_note",
            "path": "docs/decisions/future-real-sdk-dependency-rollback.md",
            "plannedChange": "document_dependency_rollback",
            "appliedNow": False,
            "requiresSeparateTask": True,
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
            {"field": "future_dependency_install_implementation_task", "reason": "must_be_separate_reviewed_task"},
            {"field": "dependency_install_command", "reason": "not_generated_in_plan_draft"},
            {"field": "dependency_file_changes", "reason": "not_applied_in_plan_draft"},
            {"field": "package_resolution", "reason": "not_performed_without_install_task"},
            {"field": "network_call", "reason": "not_allowed_in_plan_draft"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_install_plan",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_plan.py",
        },
        {
            "id": "test_real_sdk_dependency_env_gate",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_env_gate.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyInstallPlanRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖安装计划草案当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency install plan"}],
        )


def build_real_sdk_dependency_install_plan_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyInstallPlanRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            gate = evaluate_real_sdk_dependency_env_gate(_dependency_env_request(request), root=root)
        else:
            gate = None
    except ProviderError:
        gate = None
    if gate is not None:
        context["dependencyEnvGateReady"] = bool(gate.get("readyForDependencyImplementationTask", False))
        context["dependencyEnvGateSummary"] = _gate_summary(gate)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_install_plan(
    request: RealSdkDependencyInstallPlanRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    gate = evaluate_real_sdk_dependency_env_gate(_dependency_env_request(request), root=root)
    gate_ready = gate.get("readyForDependencyImplementationTask") is True
    checklist = _install_plan_checklist(request, gate_ready=gate_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "dependencyEnvGateReady": gate_ready,
        "dependencyEnvGateSummary": _gate_summary(gate),
        "installPlanChecklist": checklist,
        "installPlanChecklistPassed": checklist_passed,
        "readyForDependencyInstallImplementationReview": checklist_passed,
        "proposedDependencySpec": {
            "packageName": TARGET_PACKAGE,
            "packageNameOnly": True,
            "exactVersionKnown": False,
            "versionPinRequired": True,
            "hashVerificationRequired": True,
            "licenseReviewRequired": True,
            "resolvedNow": False,
        },
        "plannedFiles": _planned_files(),
        "rollbackPlan": {
            "requiresSeparateReview": True,
            "removeDependencyManifestChange": True,
            "restoreLockfile": True,
            "disableProviderContracts": True,
            "appliedNow": False,
        },
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖安装计划草案已生成；当前不会安装、下载、解析版本、修改锁文件或联网。",
    }
