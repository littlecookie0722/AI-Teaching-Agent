"""Real SDK enablement switch design gate.

This module evaluates the final local checklist before a future task may
change runtime/provider contracts for a minimal real SDK implementation. It
does not install SDKs, import SDKs, read or check secret values, open network
connections, create AI tasks, generate content, or publish artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_sdk_task_blueprint import (
    DEFAULT_MODEL_ALIAS,
    RealLlmSdkTaskBlueprintRequest,
    build_real_llm_sdk_task_blueprint,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_ENABLEMENT_ID = "real_sdk_enablement"


@dataclass(frozen=True)
class RealSdkEnablementRequest:
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


def _blueprint_request(request: RealSdkEnablementRequest) -> RealLlmSdkTaskBlueprintRequest:
    return RealLlmSdkTaskBlueprintRequest(
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
        trace_id=request.trace_id,
    )


def _base_context(request: RealSdkEnablementRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    return {
        "enablementId": REAL_SDK_ENABLEMENT_ID,
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "enablementMode": "PRE_RUNTIME_SWITCH_DESIGN",
        "targetTaskType": "REAL_LLM_SDK_MINIMAL_POC_ENABLEMENT",
        "taskRef": _clean_text(request.task_ref),
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "providerContractEnabled": bool(provider.get("enabled", False)) if provider else False,
        "secretEnv": provider.get("secretEnv") if provider else None,
        "secretNameOnly": True,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "timeoutSeconds": request.timeout_seconds,
        "retryCount": request.retry_count,
        "concurrencyLimit": request.concurrency_limit,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
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
        "runtimeFlags": _safe_runtime_flags(runtime_contract),
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "schemaValidationRequired": True,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "blueprintRequired": True,
        "blueprintReady": False,
        "enablementChecklistPassed": False,
        "switchDesignReady": False,
        "readyForRuntimeChangeReview": False,
        "readyForRealSdkImplementationTask": False,
        "implementationAllowed": False,
        "realCallAuthorized": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "secretInjectionApplied": False,
        "networkAccessEnabledNow": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_enablement(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    return {
        "enablementId": REAL_SDK_ENABLEMENT_ID,
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "enablementMode": "PRE_RUNTIME_SWITCH_DESIGN",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "targetTaskType": "REAL_LLM_SDK_MINIMAL_POC_ENABLEMENT",
        "supportedOperation": "generateJson",
        "allowedScope": "lab_generate_from_source_only",
        "requiresBlueprint": True,
        "requiresSdkDependencyReview": True,
        "requiresProviderContractReview": True,
        "requiresRuntimeContractReview": True,
        "requiresSecretInjectionReview": True,
        "requiresNetworkAccessReview": True,
        "requiresRollbackPlan": True,
        "requiresHumanReview": True,
        "generatedStatus": "WAITING_REVIEW",
        "switchDesignReady": False,
        "implementationAllowed": False,
        "realCallAuthorized": False,
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
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "pipeline": [
            "real_llm_sdk_task_blueprint",
            "real_sdk_enablement_checklist",
            "future_provider_contract_review",
            "future_runtime_contract_review",
            "future_real_sdk_implementation_task",
        ],
    }


def _blueprint_summary(blueprint: dict[str, Any]) -> dict[str, Any]:
    return {
        "blueprintId": blueprint["blueprintId"],
        "blueprintReady": blueprint["blueprintReady"],
        "readyForImplementationTask": blueprint["readyForImplementationTask"],
        "implementationAllowed": blueprint["implementationAllowed"],
        "realCallAuthorized": blueprint["realCallAuthorized"],
        "sdkDependencyInstalled": blueprint["sdkDependencyInstalled"],
        "secretPresenceChecked": blueprint["secretPresenceChecked"],
        "secretValueRead": blueprint["secretValueRead"],
        "realLlmCalled": blueprint["realLlmCalled"],
        "networkAccess": blueprint["networkAccess"],
    }


def _enablement_checklist(
    request: RealSdkEnablementRequest,
    *,
    blueprint_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "blueprint_ready", "passed": blueprint_ready, "required": True},
        {
            "id": "sdk_dependency_review_confirmed",
            "passed": request.sdk_dependency_review_confirmed,
            "required": True,
        },
        {
            "id": "provider_contract_review_confirmed",
            "passed": request.provider_contract_review_confirmed,
            "required": True,
        },
        {
            "id": "runtime_contract_review_confirmed",
            "passed": request.runtime_contract_review_confirmed,
            "required": True,
        },
        {
            "id": "secret_injection_review_confirmed",
            "passed": request.secret_injection_review_confirmed,
            "required": True,
        },
        {
            "id": "network_access_review_confirmed",
            "passed": request.network_access_review_confirmed,
            "required": True,
        },
        {
            "id": "schema_review_confirmed",
            "passed": request.schema_review_confirmed,
            "required": True,
        },
        {
            "id": "human_review_policy_confirmed",
            "passed": request.human_review_policy_confirmed,
            "required": True,
        },
        {
            "id": "audit_redaction_confirmed",
            "passed": request.audit_redaction_confirmed,
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
            {"field": "explicit_future_task", "reason": "real_sdk_implementation_must_be_separate"},
            {"field": "provider_contract_change", "reason": "not_applied_in_enablement_design"},
            {"field": "runtime_contract_change", "reason": "not_applied_in_enablement_design"},
            {"field": "realCallAuthorized", "reason": "false_in_enablement_design"},
        ]
    )
    return reasons


def _planned_switches(secret_env: str | None) -> list[dict[str, Any]]:
    return [
        {
            "id": "runtime_enable_real_llm",
            "path": "config/runtime.contract.json",
            "plannedValue": "reviewed_true_in_future_task",
            "appliedNow": False,
            "requiresReview": True,
        },
        {
            "id": "provider_enablement",
            "path": "providers/provider.contract.json",
            "plannedValue": "enable_single_reviewed_provider",
            "appliedNow": False,
            "requiresReview": True,
        },
        {
            "id": "secret_injection",
            "path": ".env.example",
            "secretEnv": secret_env,
            "secretNameOnly": True,
            "appliedNow": False,
            "requiresReview": True,
        },
        {
            "id": "network_access",
            "path": "providers/provider-runtime-guard.contract.json",
            "plannedValue": "allow_single_provider_endpoint_in_future_task",
            "appliedNow": False,
            "requiresReview": True,
        },
    ]


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_enablement",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_enablement.py",
        },
        {
            "id": "test_real_provider_sdk_poc",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_provider_sdk_poc.py",
        },
        {
            "id": "test_real_llm_sdk_task_blueprint",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_llm_sdk_task_blueprint.py",
        },
        {
            "id": "test_all",
            "status": "REQUIRED_BEFORE_REAL_CALL",
            "command": "python -m pytest",
        },
    ]


def build_real_sdk_enablement_error_context(
    exc: ProviderError,
    *,
    request: RealSdkEnablementRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        blueprint = build_real_llm_sdk_task_blueprint(_blueprint_request(request), root=root)
    except ProviderError:
        blueprint = None
    if blueprint is not None:
        context["blueprintReady"] = bool(blueprint.get("blueprintReady", False))
        context["blueprintSummary"] = _blueprint_summary(blueprint)
    return {
        **context,
        "errorCode": exc.code,
    }


def evaluate_real_sdk_enablement(
    request: RealSdkEnablementRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    blueprint = build_real_llm_sdk_task_blueprint(_blueprint_request(request), root=root)
    blueprint_ready = blueprint.get("blueprintReady") is True
    checklist = _enablement_checklist(request, blueprint_ready=blueprint_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "blueprintReady": blueprint_ready,
        "blueprintSummary": _blueprint_summary(blueprint),
        "enablementChecklist": checklist,
        "enablementChecklistPassed": checklist_passed,
        "switchDesignReady": checklist_passed,
        "readyForRuntimeChangeReview": checklist_passed,
        "readyForRealSdkImplementationTask": checklist_passed,
        "implementationAllowed": False,
        "realCallAuthorized": False,
        "plannedSwitches": _planned_switches(context["secretEnv"]),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 最终开关设计已评估；当前不会修改契约或授权真实调用。",
    }
