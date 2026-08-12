"""Disabled real LLM PoC adapter shell.

The adapter wires the future real-provider path through local runtime guard and
preflight checks while keeping the actual SDK call disabled. It never imports
provider SDKs, reads secret values, opens network connections, or creates AI
tasks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import ProviderRuntimeGuardRequest, evaluate_provider_runtime_guard
from .real_provider_gate import RealProviderGateRequest, preflight_real_provider
from .real_provider_shell import get_real_provider_shell


ROOT = Path(__file__).resolve().parents[1]
REAL_LLM_POC_ADAPTER_ID = "real_llm_poc_adapter"


@dataclass(frozen=True)
class RealLlmPocAdapterRequest:
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
    trace_id: str | None = None


def _find_provider(contract: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    for provider in contract["providers"]:
        if provider["id"] == provider_id:
            return provider
    return None


def _base_context(request: RealLlmPocAdapterRequest, *, root: Path) -> dict[str, Any]:
    contract = load_provider_contract(root)
    provider = _find_provider(contract, request.provider_id)
    shell = None
    try:
        shell = get_real_provider_shell(request.provider_id, root=root).describe()
    except ProviderError:
        shell = None
    return {
        "adapterId": REAL_LLM_POC_ADAPTER_ID,
        "interfaceName": "LLMProvider",
        "phase": contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": contract.get("mode", "MOCK_ONLY"),
        "defaultProvider": contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "explicitOptIn": request.explicit_opt_in,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "secretEnv": provider.get("secretEnv") if provider else None,
        "shellImplementationStatus": shell.get("shellImplementationStatus") if shell else None,
        "pipeline": [
            "provider_runtime_guard",
            "real_provider_preflight",
            "disabled_real_provider_shell",
            "sdk_call_disabled",
        ],
        "readyForRealProvider": False,
        "adapterEnabled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretValueReturned": False,
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


def describe_real_llm_poc_adapter(*, root: Path = ROOT) -> dict[str, Any]:
    contract = load_provider_contract(root)
    return {
        "adapterId": REAL_LLM_POC_ADAPTER_ID,
        "interfaceName": "LLMProvider",
        "phase": contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": contract.get("mode", "MOCK_ONLY"),
        "defaultProvider": contract.get("activeProvider", "mock"),
        "adapterEnabled": False,
        "supportedOperation": "generateJson",
        "llmPocScope": "lab_generate_from_source_only",
        "pipeline": [
            "provider_runtime_guard",
            "real_provider_preflight",
            "disabled_real_provider_shell",
            "sdk_call_disabled",
        ],
        "sdkImported": False,
        "clientCreated": False,
        "secretValueReturned": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "providers": [
            {
                "providerId": provider["id"],
                "enabled": bool(provider.get("enabled", False)),
                "implementationStatus": provider.get("implementationStatus"),
                "secretEnv": provider.get("secretEnv"),
            }
            for provider in contract.get("providers", [])
            if provider.get("type") == "llm"
        ],
    }


def build_real_llm_poc_adapter_error_context(
    exc: ProviderError,
    *,
    request: RealLlmPocAdapterRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    return {
        **_base_context(request, root=root),
        "adapterPassed": False,
        "errorCode": exc.code,
    }


def invoke_real_llm_poc_adapter(request: RealLlmPocAdapterRequest, *, root: Path = ROOT) -> dict[str, Any]:
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
    preflight = preflight_real_provider(
        RealProviderGateRequest(
            provider_id=request.provider_id,
            operation=request.operation,
            prompt_id=request.prompt_id,
            output_kind=request.output_kind,
            input_ref=request.input_ref,
            explicit_opt_in=request.explicit_opt_in,
        ),
        root=root,
    )

    raise ProviderError(
        "REAL_LLM_POC_ADAPTER_DISABLED",
        "真实 LLM PoC Adapter 当前默认禁用",
        [
            {"field": "adapter", "reason": REAL_LLM_POC_ADAPTER_ID},
            {"field": "provider", "reason": request.provider_id},
            {"field": "operation", "reason": request.operation},
        ],
    )

    return {  # pragma: no cover - documented future shape; blocked above.
        **context,
        "adapterPassed": True,
        "runtimeGuard": runtime_guard,
        "preflight": preflight,
    }
