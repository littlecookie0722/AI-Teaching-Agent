"""Default-disabled real SDK minimal implementation shell.

This module is the first implementation-shaped boundary for a future real
OpenAI SDK call. It requires the local enablement checklist before it reaches
the implementation gate, but it still does not install SDKs, import SDKs,
create clients, check or read secret values, open network connections, create
AI tasks, generate content, or publish artifacts.
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
REAL_SDK_MINIMAL_IMPL_ID = "real_sdk_minimal_impl"


@dataclass(frozen=True)
class RealSdkMinimalImplRequest:
    provider_id: str
    operation: str = "generateJson"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    explicit_implementation_opt_in: bool = False
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


def _enablement_request(request: RealSdkMinimalImplRequest) -> RealSdkEnablementRequest:
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


def _base_context(request: RealSdkMinimalImplRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    return {
        "implementationId": REAL_SDK_MINIMAL_IMPL_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "implementationMode": "DEFAULT_DISABLED_REAL_SDK_SHELL",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "supportedProvider": "openai",
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "explicitImplementationOptIn": request.explicit_implementation_opt_in,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "providerContractEnabled": bool(provider.get("enabled", False)) if provider else False,
        "secretEnv": provider.get("secretEnv") if provider else None,
        "secretNameOnly": True,
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
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "schemaValidationRequired": True,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "enablementRequired": True,
        "enablementReady": False,
        "switchDesignReady": False,
        "readyForRuntimeChangeReview": False,
        "readyForRealSdkImplementationTask": False,
        "implementationAllowed": False,
        "sdkImplementationEnabled": False,
        "sdkImplementationPassed": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "secretInjectionApplied": False,
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
        "plannedImplementationFiles": [
            "providers/real_sdk_minimal_impl.py",
            "providers/provider.contract.json",
            "config/runtime.contract.json",
            ".env.example",
        ],
        "traceId": request.trace_id,
    }


def describe_real_sdk_minimal_impl(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    return {
        "implementationId": REAL_SDK_MINIMAL_IMPL_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "implementationMode": "DEFAULT_DISABLED_REAL_SDK_SHELL",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "supportedProvider": "openai",
        "supportedOperation": "generateJson",
        "allowedScope": "lab_generate_from_source_only",
        "requiresEnablement": True,
        "requiresExplicitImplementationOptIn": True,
        "requiresProviderContractChange": True,
        "requiresRuntimeContractChange": True,
        "requiresHumanReview": True,
        "generatedStatus": "WAITING_REVIEW",
        "enablementReady": False,
        "switchDesignReady": False,
        "readyForRealSdkImplementationTask": False,
        "implementationAllowed": False,
        "sdkImplementationEnabled": False,
        "sdkImplementationPassed": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "secretInjectionApplied": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "networkAccessEnabledNow": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "pipeline": [
            "real_sdk_enablement_checklist",
            "explicit_real_sdk_implementation_opt_in",
            "provider_contract_review",
            "runtime_contract_review",
            "sdk_import_disabled",
            "network_call_disabled",
        ],
    }


def _enablement_summary(enablement: dict[str, Any]) -> dict[str, Any]:
    return {
        "enablementId": enablement["enablementId"],
        "blueprintReady": enablement["blueprintReady"],
        "switchDesignReady": enablement["switchDesignReady"],
        "readyForRuntimeChangeReview": enablement["readyForRuntimeChangeReview"],
        "readyForRealSdkImplementationTask": enablement["readyForRealSdkImplementationTask"],
        "implementationAllowed": enablement["implementationAllowed"],
        "realCallAuthorized": enablement["realCallAuthorized"],
        "sdkDependencyInstalled": enablement["sdkDependencyInstalled"],
        "secretPresenceChecked": enablement["secretPresenceChecked"],
        "secretValueRead": enablement["secretValueRead"],
        "realLlmCalled": enablement["realLlmCalled"],
        "networkAccess": enablement["networkAccess"],
    }


def _blocked_enablement_errors(enablement: dict[str, Any]) -> list[dict[str, str]]:
    errors = [
        {"field": item["id"], "reason": "required"}
        for item in enablement.get("enablementChecklist", [])
        if item.get("required") is True and item.get("passed") is False
    ]
    if not errors:
        errors.append({"field": "readyForRealSdkImplementationTask", "reason": "false"})
    return errors


def build_real_sdk_minimal_impl_error_context(
    exc: ProviderError,
    *,
    request: RealSdkMinimalImplRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        enablement = evaluate_real_sdk_enablement(_enablement_request(request), root=root)
    except ProviderError:
        enablement = None
    if enablement is not None:
        context["enablementReady"] = bool(enablement.get("readyForRealSdkImplementationTask", False))
        context["switchDesignReady"] = bool(enablement.get("switchDesignReady", False))
        context["readyForRuntimeChangeReview"] = bool(enablement.get("readyForRuntimeChangeReview", False))
        context["readyForRealSdkImplementationTask"] = bool(
            enablement.get("readyForRealSdkImplementationTask", False)
        )
        context["enablementSummary"] = _enablement_summary(enablement)
    return {
        **context,
        "sdkImplementationPassed": False,
        "errorCode": exc.code,
    }


def invoke_real_sdk_minimal_impl(
    request: RealSdkMinimalImplRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    if request.provider_id != "openai":
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 最小实现外壳当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in minimal implementation shell"}],
        )

    enablement = evaluate_real_sdk_enablement(_enablement_request(request), root=root)
    if enablement.get("readyForRealSdkImplementationTask") is not True:
        raise ProviderError(
            "REAL_SDK_ENABLEMENT_REQUIRED",
            "真实 SDK 最小实现外壳需要先通过 enablement 本地清单",
            _blocked_enablement_errors(enablement),
        )

    if request.explicit_implementation_opt_in is not True:
        raise ProviderError(
            "REAL_SDK_IMPLEMENTATION_OPT_IN_REQUIRED",
            "真实 SDK 最小实现外壳需要显式 implementation opt-in",
            [{"field": "explicitImplementationOptIn", "reason": "required"}],
        )

    raise ProviderError(
        "REAL_SDK_IMPLEMENTATION_DISABLED",
        "真实 SDK 最小实现外壳当前默认禁用，不会导入 SDK 或发起真实调用",
        [
            {"field": "sdkImplementationEnabled", "reason": "false"},
            {"field": "providerContractChangeApplied", "reason": "false"},
            {"field": "runtimeContractChangeApplied", "reason": "false"},
            {"field": "networkAccess", "reason": "false"},
        ],
    )

    return {  # pragma: no cover - documented future shape; blocked above.
        **context,
        "enablementReady": True,
        "switchDesignReady": True,
        "readyForRuntimeChangeReview": True,
        "readyForRealSdkImplementationTask": True,
        "enablementSummary": _enablement_summary(enablement),
    }
