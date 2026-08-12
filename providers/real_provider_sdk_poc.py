"""Default-disabled real provider SDK PoC harness.

This module is the safety harness for a future minimal real SDK PoC. It
requires the local SDK task blueprint before it reaches the existing disabled
PoC adapter, and it still does not install SDKs, import SDKs, read secret
values, check secret presence, open network connections, create AI tasks, or
publish artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_poc_adapter import RealLlmPocAdapterRequest, invoke_real_llm_poc_adapter
from .real_llm_sdk_task_blueprint import (
    DEFAULT_MODEL_ALIAS,
    RealLlmSdkTaskBlueprintRequest,
    build_real_llm_sdk_task_blueprint,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_PROVIDER_SDK_POC_ID = "real_provider_sdk_poc"


@dataclass(frozen=True)
class RealProviderSdkPocRequest:
    provider_id: str
    operation: str = "generateJson"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    explicit_opt_in: bool = False
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


def _blueprint_request(request: RealProviderSdkPocRequest) -> RealLlmSdkTaskBlueprintRequest:
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


def _adapter_request(request: RealProviderSdkPocRequest) -> RealLlmPocAdapterRequest:
    return RealLlmPocAdapterRequest(
        provider_id=request.provider_id,
        operation=request.operation,
        prompt_id=request.prompt_id,
        output_kind=request.output_kind,
        input_ref=request.input_ref,
        explicit_opt_in=request.explicit_opt_in,
        timeout_seconds=request.timeout_seconds,
        retry_count=request.retry_count,
        concurrency_limit=request.concurrency_limit,
        payload=request.payload,
        trace_id=request.trace_id,
    )


def _base_context(request: RealProviderSdkPocRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    return {
        "pocId": REAL_PROVIDER_SDK_POC_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "explicitOptIn": request.explicit_opt_in,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "providerContractEnabled": bool(provider.get("enabled", False)) if provider else False,
        "secretEnv": provider.get("secretEnv") if provider else None,
        "targetModelAlias": request.target_model_alias or DEFAULT_MODEL_ALIAS,
        "runtimeFlags": _safe_runtime_flags(runtime_contract),
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "schemaValidationRequired": True,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "dryRunPlanConfirmed": request.dry_run_plan_confirmed,
        "runtimeGuardConfirmed": request.runtime_guard_confirmed,
        "schemaReviewConfirmed": request.schema_review_confirmed,
        "humanReviewPolicyConfirmed": request.human_review_policy_confirmed,
        "auditRedactionConfirmed": request.audit_redaction_confirmed,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "blueprintRequired": True,
        "blueprintReady": False,
        "sdkPocEnabled": False,
        "sdkPocPassed": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "networkAccessEnabledNow": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_provider_sdk_poc(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    return {
        "pocId": REAL_PROVIDER_SDK_POC_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "sdkPocEnabled": False,
        "supportedOperation": "generateJson",
        "llmPocScope": "lab_generate_from_source_only",
        "requiresBlueprint": True,
        "requiresApprovalGate": True,
        "requiresRuntimeGuard": True,
        "requiresHumanReview": True,
        "generatedStatus": "WAITING_REVIEW",
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
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
            "real_llm_sdk_task_blueprint",
            "provider_runtime_guard",
            "real_provider_preflight",
            "disabled_real_provider_shell",
            "sdk_call_disabled",
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


def build_real_provider_sdk_poc_error_context(
    exc: ProviderError,
    *,
    request: RealProviderSdkPocRequest,
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
        "sdkPocPassed": False,
        "errorCode": exc.code,
    }


def invoke_real_provider_sdk_poc(
    request: RealProviderSdkPocRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    blueprint = build_real_llm_sdk_task_blueprint(_blueprint_request(request), root=root)
    if blueprint.get("blueprintReady") is not True:
        raise ProviderError(
            "REAL_LLM_SDK_BLUEPRINT_REQUIRED",
            "真实 SDK PoC 需要先通过本地任务蓝图",
            [
                {"field": "approvalRef", "reason": "required"},
                {"field": "reviewer", "reason": "required"},
                {"field": "confirmations", "reason": "dry-run, runtime guard, schema, review, and audit confirmations required"},
            ],
        )

    try:
        adapter_result = invoke_real_llm_poc_adapter(_adapter_request(request), root=root)
    except ProviderError:
        raise

    raise ProviderError(
        "REAL_PROVIDER_SDK_POC_DISABLED",
        "真实 Provider SDK PoC 当前仍默认禁用",
        [
            {"field": "sdkPocEnabled", "reason": "false"},
            {"field": "provider", "reason": request.provider_id},
            {"field": "operation", "reason": request.operation},
        ],
    )

    return {  # pragma: no cover - documented future shape; blocked above.
        **context,
        "blueprintReady": True,
        "blueprintSummary": _blueprint_summary(blueprint),
        "adapterResult": adapter_result,
    }
