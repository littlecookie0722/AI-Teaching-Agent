"""Real SDK dependency and environment review gate.

This module evaluates the local design checklist for a future task that may
add a real SDK dependency and environment-variable presence checks. It does
not install packages, import SDKs, read or check secret values, open network
connections, create AI tasks, generate content, or publish artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS
from .real_sdk_enablement import RealSdkEnablementRequest, evaluate_real_sdk_enablement


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_ENV_GATE_ID = "real_sdk_dependency_env_gate"
SUPPORTED_PROVIDER = "openai"
TARGET_PACKAGE = "openai"


@dataclass(frozen=True)
class RealSdkDependencyEnvGateRequest:
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


def _enablement_request(request: RealSdkDependencyEnvGateRequest) -> RealSdkEnablementRequest:
    return RealSdkEnablementRequest(
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
        trace_id=request.trace_id,
    )


def _base_context(request: RealSdkDependencyEnvGateRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    secret_env = provider.get("secretEnv") if provider else None
    return {
        "gateId": REAL_SDK_DEPENDENCY_ENV_GATE_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "gateMode": "DEPENDENCY_ENV_DESIGN_ONLY",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "supportedProvider": SUPPORTED_PROVIDER,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "providerContractEnabled": bool(provider.get("enabled", False)) if provider else False,
        "targetPackage": TARGET_PACKAGE,
        "packageNameOnly": True,
        "targetSecretEnv": secret_env,
        "secretEnv": secret_env,
        "secretNameOnly": True,
        "envVarNameOnly": True,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "runtimeFlags": _safe_runtime_flags(runtime_contract),
        "timeoutSeconds": request.timeout_seconds,
        "retryCount": request.retry_count,
        "concurrencyLimit": request.concurrency_limit,
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "dryRunPlanConfirmed": request.dry_run_plan_confirmed,
        "runtimeGuardConfirmed": request.runtime_guard_confirmed,
        "schemaReviewConfirmed": request.schema_review_confirmed,
        "humanReviewPolicyConfirmed": request.human_review_policy_confirmed,
        "auditRedactionConfirmed": request.audit_redaction_confirmed,
        "sdkDependencyReviewConfirmed": request.sdk_dependency_review_confirmed,
        "providerContractReviewConfirmed": request.provider_contract_review_confirmed,
        "runtimeContractReviewConfirmed": request.runtime_contract_review_confirmed,
        "secretInjectionReviewConfirmed": request.secret_injection_review_confirmed,
        "networkAccessReviewConfirmed": request.network_access_review_confirmed,
        "rollbackPlanConfirmed": request.rollback_plan_confirmed,
        "minimalImplReviewConfirmed": request.minimal_impl_review_confirmed,
        "sdkPackageReviewConfirmed": request.sdk_package_review_confirmed,
        "sdkVersionPinReviewConfirmed": request.sdk_version_pin_review_confirmed,
        "dependencyLicenseReviewConfirmed": request.dependency_license_review_confirmed,
        "dependencyHashReviewConfirmed": request.dependency_hash_review_confirmed,
        "envVarNameReviewConfirmed": request.env_var_name_review_confirmed,
        "envExampleReviewConfirmed": request.env_example_review_confirmed,
        "secretNonReadPolicyConfirmed": request.secret_non_read_policy_confirmed,
        "ciInstallPolicyConfirmed": request.ci_install_policy_confirmed,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "schemaValidationRequired": True,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "enablementRequired": True,
        "enablementReady": False,
        "minimalImplementationShellRequired": True,
        "dependencyEnvChecklistPassed": False,
        "readyForDependencyImplementationTask": False,
        "readyForEnvPresenceCheckDesign": False,
        "dependencyInstallAllowed": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstallPlannedNow": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "dependencyLockfileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "envExampleChangeApplied": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "secretInjectionApplied": False,
        "secretPresenceCheckDesigned": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "networkAccessEnabledNow": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_env_gate(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    openai_provider = _find_provider(provider_contract, SUPPORTED_PROVIDER)
    secret_env = openai_provider.get("secretEnv") if openai_provider else None
    return {
        "gateId": REAL_SDK_DEPENDENCY_ENV_GATE_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "gateMode": "DEPENDENCY_ENV_DESIGN_ONLY",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "supportedProvider": SUPPORTED_PROVIDER,
        "supportedOperation": "generateJson",
        "allowedScope": "lab_generate_from_source_only",
        "targetPackage": TARGET_PACKAGE,
        "packageNameOnly": True,
        "targetSecretEnv": secret_env,
        "secretNameOnly": True,
        "envVarNameOnly": True,
        "requiresEnablement": True,
        "requiresMinimalImplementationShellReview": True,
        "requiresSdkPackageReview": True,
        "requiresSdkVersionPinReview": True,
        "requiresDependencyLicenseReview": True,
        "requiresDependencyHashReview": True,
        "requiresEnvVarNameReview": True,
        "requiresEnvExampleReview": True,
        "requiresSecretNonReadPolicy": True,
        "requiresCiInstallPolicy": True,
        "requiresHumanReview": True,
        "generatedStatus": "WAITING_REVIEW",
        "enablementReady": False,
        "dependencyEnvChecklistPassed": False,
        "readyForDependencyImplementationTask": False,
        "readyForEnvPresenceCheckDesign": False,
        "dependencyInstallAllowed": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstallPlannedNow": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "dependencyLockfileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "envExampleChangeApplied": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "secretInjectionApplied": False,
        "secretPresenceCheckDesigned": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "networkAccessEnabledNow": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "pipeline": [
            "real_sdk_enablement_checklist",
            "real_sdk_minimal_impl_review",
            "dependency_package_name_review",
            "version_pin_and_hash_review",
            "env_var_name_only_review",
            "secret_non_read_policy_review",
            "future_dependency_implementation_task",
        ],
    }


def _enablement_summary(enablement: dict[str, Any]) -> dict[str, Any]:
    return {
        "enablementId": enablement["enablementId"],
        "blueprintReady": enablement["blueprintReady"],
        "enablementChecklistPassed": enablement["enablementChecklistPassed"],
        "switchDesignReady": enablement["switchDesignReady"],
        "readyForRealSdkImplementationTask": enablement["readyForRealSdkImplementationTask"],
        "implementationAllowed": enablement["implementationAllowed"],
        "realCallAuthorized": enablement["realCallAuthorized"],
        "sdkDependencyInstalled": enablement["sdkDependencyInstalled"],
        "secretPresenceChecked": enablement["secretPresenceChecked"],
        "secretValueRead": enablement["secretValueRead"],
        "realLlmCalled": enablement["realLlmCalled"],
        "networkAccess": enablement["networkAccess"],
    }


def _dependency_env_checklist(
    request: RealSdkDependencyEnvGateRequest,
    *,
    enablement_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "enablement_ready", "passed": enablement_ready, "required": True},
        {
            "id": "minimal_impl_review_confirmed",
            "passed": request.minimal_impl_review_confirmed,
            "required": True,
        },
        {
            "id": "sdk_package_review_confirmed",
            "passed": request.sdk_package_review_confirmed,
            "required": True,
        },
        {
            "id": "sdk_version_pin_review_confirmed",
            "passed": request.sdk_version_pin_review_confirmed,
            "required": True,
        },
        {
            "id": "dependency_license_review_confirmed",
            "passed": request.dependency_license_review_confirmed,
            "required": True,
        },
        {
            "id": "dependency_hash_review_confirmed",
            "passed": request.dependency_hash_review_confirmed,
            "required": True,
        },
        {
            "id": "env_var_name_review_confirmed",
            "passed": request.env_var_name_review_confirmed,
            "required": True,
        },
        {
            "id": "env_example_review_confirmed",
            "passed": request.env_example_review_confirmed,
            "required": True,
        },
        {
            "id": "secret_non_read_policy_confirmed",
            "passed": request.secret_non_read_policy_confirmed,
            "required": True,
        },
        {
            "id": "ci_install_policy_confirmed",
            "passed": request.ci_install_policy_confirmed,
            "required": True,
        },
        {"id": "rollback_plan_confirmed", "passed": request.rollback_plan_confirmed, "required": True},
    ]


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "future_dependency_implementation_task", "reason": "must_be_separate_reviewed_task"},
            {"field": "sdk_dependency_install", "reason": "not_allowed_in_dependency_env_gate"},
            {"field": "sdk_import", "reason": "not_allowed_in_dependency_env_gate"},
            {"field": "secret_presence_check", "reason": "design_only_no_environment_lookup"},
            {"field": "network_call", "reason": "not_allowed_in_dependency_env_gate"},
            {"field": "realCallAuthorized", "reason": "false_in_dependency_env_gate"},
        ]
    )
    return reasons


def _planned_dependency_changes() -> list[dict[str, Any]]:
    return [
        {
            "id": "python_sdk_dependency",
            "path": "pyproject.toml_or_requirements.txt",
            "packageName": TARGET_PACKAGE,
            "packageNameOnly": True,
            "versionPinRequired": True,
            "hashReviewRequired": True,
            "licenseReviewRequired": True,
            "appliedNow": False,
            "requiresReview": True,
        },
        {
            "id": "dependency_lockfile",
            "path": "future_lockfile",
            "versionResolvedNow": False,
            "hashResolvedNow": False,
            "downloadedNow": False,
            "appliedNow": False,
            "requiresReview": True,
        },
    ]


def _planned_env_changes(secret_env: str | None) -> list[dict[str, Any]]:
    return [
        {
            "id": "env_example_secret_name",
            "path": ".env.example",
            "secretEnv": secret_env,
            "secretNameOnly": True,
            "presenceCheckDesignedNow": False,
            "valueReadNow": False,
            "appliedNow": False,
            "requiresReview": True,
        },
        {
            "id": "runtime_secret_presence_policy",
            "path": "providers/provider-runtime-guard.contract.json",
            "secretPresenceCheckAllowedNow": False,
            "secretValueReadAllowedNow": False,
            "appliedNow": False,
            "requiresReview": True,
        },
    ]


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_env_gate",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_env_gate.py",
        },
        {
            "id": "test_real_sdk_minimal_impl",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_minimal_impl.py",
        },
        {
            "id": "test_real_sdk_enablement",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_enablement.py",
        },
        {
            "id": "test_all",
            "status": "REQUIRED_BEFORE_REAL_CALL",
            "command": "python -m pytest",
        },
    ]


def _validate_provider_scope(request: RealSdkDependencyEnvGateRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖与环境变量门禁当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency env gate"}],
        )


def build_real_sdk_dependency_env_gate_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyEnvGateRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            enablement = evaluate_real_sdk_enablement(_enablement_request(request), root=root)
        else:
            enablement = None
    except ProviderError:
        enablement = None
    if enablement is not None:
        context["enablementReady"] = bool(enablement.get("readyForRealSdkImplementationTask", False))
        context["enablementSummary"] = _enablement_summary(enablement)
    return {
        **context,
        "errorCode": exc.code,
    }


def evaluate_real_sdk_dependency_env_gate(
    request: RealSdkDependencyEnvGateRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    enablement = evaluate_real_sdk_enablement(_enablement_request(request), root=root)
    enablement_ready = enablement.get("readyForRealSdkImplementationTask") is True
    checklist = _dependency_env_checklist(request, enablement_ready=enablement_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "enablementReady": enablement_ready,
        "enablementSummary": _enablement_summary(enablement),
        "dependencyEnvChecklist": checklist,
        "dependencyEnvChecklistPassed": checklist_passed,
        "readyForDependencyImplementationTask": checklist_passed,
        "readyForEnvPresenceCheckDesign": checklist_passed,
        "dependencyInstallAllowed": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstallPlannedNow": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceCheckDesigned": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAuthorized": False,
        "plannedDependencyChanges": _planned_dependency_changes(),
        "plannedEnvChanges": _planned_env_changes(context["targetSecretEnv"]),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖与环境变量门禁已评估；当前不会安装 SDK、检查密钥或授权真实调用。",
    }
