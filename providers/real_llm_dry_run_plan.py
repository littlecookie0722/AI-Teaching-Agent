"""Real LLM PoC dry-run plan.

This module builds a local, non-executing plan for a future real LLM Lab DSL
PoC. It never imports provider SDKs, reads secret values, opens network
connections, generates content, creates AI tasks, or publishes artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import (
    ProviderRuntimeGuardRequest,
    evaluate_provider_runtime_guard,
    redact_provider_payload,
)
from .real_llm_poc_adapter import describe_real_llm_poc_adapter


ROOT = Path(__file__).resolve().parents[1]
REAL_LLM_DRY_RUN_PLAN_ID = "real_llm_dry_run_plan"


@dataclass(frozen=True)
class RealLlmDryRunPlanRequest:
    provider_id: str
    operation: str = "generateJson"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    timeout_seconds: int = 30
    retry_count: int = 1
    concurrency_limit: int = 1
    payload: Mapping[str, Any] | None = None
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


def _base_context(request: RealLlmDryRunPlanRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    return {
        "planId": REAL_LLM_DRY_RUN_PLAN_ID,
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "dryRunOnly": True,
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "providerContractEnabled": bool(provider.get("enabled", False)) if provider else False,
        "secretEnv": provider.get("secretEnv") if provider else None,
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
        "llmPocScope": "lab_generate_from_source_only",
        "runtimeFlags": _safe_runtime_flags(runtime_contract),
        "preflightRequired": True,
        "explicitOptInRequired": True,
        "schemaValidationRequired": True,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "auditRequired": True,
        "readyForRealProvider": False,
        "adapterEnabled": False,
        "sdkImported": False,
        "clientCreated": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "traceId": request.trace_id,
    }


def _planned_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "validate_prompt_scope",
            "status": "READY",
            "localOnly": True,
            "description": "Only generateJson + lab_generation_v0 + Lab is in scope for the first PoC.",
        },
        {
            "id": "provider_runtime_guard",
            "status": "PASSED",
            "localOnly": True,
            "description": "Timeout, retry, concurrency, redaction, schema, audit, and review gates are checked locally.",
        },
        {
            "id": "real_provider_preflight",
            "status": "BLOCKED_UNTIL_EXPLICIT_OPT_IN",
            "localOnly": True,
            "description": "A future real call must pass explicit opt-in and provider contract checks first.",
        },
        {
            "id": "disabled_real_llm_poc_adapter",
            "status": "BLOCKED_BY_DEFAULT",
            "localOnly": True,
            "description": "The current adapter shell remains disabled and cannot import SDKs or create clients.",
        },
        {
            "id": "schema_validate_lab_dsl",
            "status": "REQUIRED_BEFORE_TASK",
            "localOnly": True,
            "description": "Future real JSON output must validate against Lab DSL before any task is created.",
        },
        {
            "id": "create_waiting_review_task",
            "status": "BLOCKED_IN_DRY_RUN",
            "localOnly": True,
            "description": "Dry-run never creates AI tasks; a future task must default to WAITING_REVIEW.",
        },
        {
            "id": "human_review",
            "status": "REQUIRED",
            "localOnly": True,
            "description": "Generated content cannot publish before human approval.",
        },
    ]


def _blocked_reasons(request: RealLlmDryRunPlanRequest, provider_enabled: bool) -> list[dict[str, str]]:
    reasons = [
        {"field": "ENABLE_REAL_LLM", "reason": "false"},
        {"field": "adapterEnabled", "reason": "false"},
        {"field": "dryRunOnly", "reason": "true"},
        {"field": "realCall", "reason": "disabled_in_dry_run_plan"},
    ]
    if not provider_enabled:
        reasons.append({"field": "providerContractEnabled", "reason": f"{request.provider_id}=false"})
    return reasons


def build_real_llm_dry_run_plan_error_context(
    exc: ProviderError,
    *,
    request: RealLlmDryRunPlanRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    return {
        **_base_context(request, root=root),
        "planPassed": False,
        "runtimeGuardPassed": False,
        "errorCode": exc.code,
    }


def build_real_llm_dry_run_plan(request: RealLlmDryRunPlanRequest, *, root: Path = ROOT) -> dict[str, Any]:
    context = _base_context(request, root=root)
    runtime_guard = evaluate_provider_runtime_guard(
        ProviderRuntimeGuardRequest(
            provider_id=request.provider_id,
            operation=request.operation,
            prompt_id=request.prompt_id,
            output_kind=request.output_kind,
            input_ref=request.input_ref,
            timeout_seconds=request.timeout_seconds,
            retry_count=request.retry_count,
            concurrency_limit=request.concurrency_limit,
            payload=request.payload,
            trace_id=request.trace_id,
        ),
        root=root,
    )
    adapter_descriptor = describe_real_llm_poc_adapter(root=root)

    return {
        **context,
        "planPassed": True,
        "runtimeGuardPassed": True,
        "runtimeGuard": runtime_guard,
        "adapterDescriptor": adapter_descriptor,
        "plannedSteps": _planned_steps(),
        "blockedReasons": _blocked_reasons(request, bool(context["providerContractEnabled"])),
        "message": "真实 LLM dry-run 计划已生成；当前不会发起真实调用。",
    }
