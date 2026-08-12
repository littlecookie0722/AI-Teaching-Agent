"""Disabled-by-default gate for future real LLM provider PoC.

This module performs local preflight checks only. It never imports provider SDKs,
never opens network connections, and never returns secret values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError, load_provider_contract


ROOT = Path(__file__).resolve().parents[1]
REAL_PROVIDER_IDS = {"openai", "anthropic", "local"}


@dataclass(frozen=True)
class RealProviderGateRequest:
    provider_id: str
    operation: str = "generateJson"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    explicit_opt_in: bool = False


def _find_provider(contract: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    for provider in contract["providers"]:
        if provider["id"] == provider_id:
            return provider
    return None


def _secret_present(secret_env: str | None, environ: dict[str, str]) -> bool:
    if not secret_env:
        return False
    return bool(environ.get(secret_env, "").strip())


def _base_context(request: RealProviderGateRequest, provider: dict[str, Any] | None) -> dict[str, Any]:
    secret_env = provider.get("secretEnv") if provider else None
    return {
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "phase": "Phase 1",
        "targetPhase": "Phase 2",
        "mode": "MOCK_ONLY",
        "defaultProvider": "mock",
        "explicitOptIn": request.explicit_opt_in,
        "secretEnv": secret_env,
        "secretValueReturned": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "autoPublishAllowed": False,
        "realPublish": False,
    }


def build_real_provider_gate_error_context(
    exc: ProviderError,
    *,
    request: RealProviderGateRequest,
    provider: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **_base_context(request, provider),
        "errorCode": exc.code,
        "readyForRealProvider": False,
    }


def preflight_real_provider(
    request: RealProviderGateRequest,
    *,
    root: Path = ROOT,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    contract = load_provider_contract(root)
    provider = _find_provider(contract, request.provider_id)
    env = environ if environ is not None else os.environ

    if provider is None:
        raise ProviderError("NOT_FOUND", "Provider 不存在", [{"field": "provider", "reason": "未找到 Provider"}])
    if request.provider_id not in REAL_PROVIDER_IDS:
        raise ProviderError(
            "VALIDATION_ERROR",
            "real-preflight 只检查真实 Provider 占位",
            [{"field": "provider", "reason": f"{request.provider_id} is not a real provider placeholder"}],
        )
    if request.operation != "generateJson":
        raise ProviderError(
            "UNSUPPORTED_OPERATION",
            "真实 Provider PoC 首批只允许 generateJson 预检",
            [{"field": "operation", "reason": "only generateJson preflight is allowed"}],
        )
    if request.prompt_id != "lab_generation_v0" or request.output_kind != "Lab":
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 Provider PoC 首批只允许 Lab DSL 生成预检",
            [{"field": "promptId", "reason": "expected lab_generation_v0 with outputKind Lab"}],
        )

    context = _base_context(request, provider)
    context["providerEnabled"] = bool(provider.get("enabled", False))
    context["requiresApiKey"] = bool(provider.get("requiresApiKey", False))
    context["secretPresenceChecked"] = False
    context["secretPresent"] = False
    context["schemaValidationRequired"] = True
    context["generatedStatus"] = "WAITING_REVIEW"

    if not request.explicit_opt_in:
        raise ProviderError(
            "REAL_PROVIDER_OPT_IN_REQUIRED",
            "真实 Provider 预检需要显式 opt-in",
            [{"field": "explicitOptIn", "reason": "pass --explicit-opt-in for local preflight only"}],
        )
    if not provider.get("enabled", False):
        raise ProviderError(
            "REAL_PROVIDER_DISABLED",
            "真实 Provider 默认禁用，当前只允许完成本地预检",
            [{"field": "provider", "reason": f"{request.provider_id} remains disabled by contract"}],
        )
    context["secretPresenceChecked"] = bool(provider.get("requiresApiKey", False))
    context["secretPresent"] = _secret_present(provider.get("secretEnv"), env)
    if provider.get("requiresApiKey") and not context["secretPresent"]:
        raise ProviderError(
            "MISSING_PROVIDER_SECRET",
            "真实 Provider 缺少环境变量密钥",
            [{"field": str(provider.get("secretEnv")), "reason": "environment variable is empty or unset"}],
        )

    return {
        **context,
        "readyForRealProvider": True,
        "llmPocScope": "lab_generate_from_source_only",
        "providerImplementationStatus": provider.get("implementationStatus"),
        "message": "真实 Provider 仅完成本地预检；当前模块不会发起真实调用。",
    }
