"""Local runtime guard for future real provider calls.

The guard checks timeout, retry, concurrency, redaction, schema, and review
requirements before a future real LLM PoC. It never imports SDKs, opens network
connections, or reads secret values.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract


ROOT = Path(__file__).resolve().parents[1]
REAL_PROVIDER_IDS = {"openai", "anthropic", "local"}
SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]+"),
    re.compile(r"xoxb-[A-Za-z0-9_\-]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[^\s,;]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key|token|secret|password)=([^\s&;,]+)", re.IGNORECASE),
    re.compile(r"BEGIN PRIVATE KEY.*?END PRIVATE KEY", re.IGNORECASE | re.DOTALL),
]


@dataclass(frozen=True)
class ProviderRuntimeGuardRequest:
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
        return json.load(file)


def _find_provider(contract: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    for provider in contract["providers"]:
        if provider["id"] == provider_id:
            return provider
    return None


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _redact_string(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(api"):
            redacted = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
        elif pattern.pattern.startswith("Bearer"):
            redacted = pattern.sub("Bearer [REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_provider_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key)
            redacted[key_text] = "[REDACTED]" if _is_sensitive_key(key_text) else redact_provider_payload(value)
        return redacted
    if isinstance(payload, list):
        return [redact_provider_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return [redact_provider_payload(item) for item in payload]
    if isinstance(payload, str):
        return _redact_string(payload)
    return payload


def _safe_runtime_defaults(runtime_contract: dict[str, Any]) -> dict[str, str]:
    return {
        key: value
        for key, value in runtime_contract.get("defaults", {}).items()
        if key.startswith("ENABLE_") or key in {"APP_PHASE", "APP_MODE"}
    }


def _base_context(
    request: ProviderRuntimeGuardRequest,
    *,
    root: Path,
    provider: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider_data = provider or _find_provider(provider_contract, request.provider_id)
    redacted_payload = redact_provider_payload(dict(request.payload or {}))
    return {
        "guardId": "provider_runtime_guard",
        "interfaceName": "LLMProvider",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerEnabled": bool(provider_data.get("enabled", False)) if provider_data else False,
        "secretEnv": provider_data.get("secretEnv") if provider_data else None,
        "runtimeDefaults": _safe_runtime_defaults(runtime_contract),
        "timeoutSeconds": request.timeout_seconds,
        "retryCount": request.retry_count,
        "concurrencyLimit": request.concurrency_limit,
        "timeoutConfigured": True,
        "retryConfigured": True,
        "concurrencyLimitConfigured": True,
        "logRedactionRequired": True,
        "redactionApplied": True,
        "redactedPayloadPreview": redacted_payload,
        "schemaValidationRequired": True,
        "generatedStatus": "WAITING_REVIEW",
        "auditRequired": True,
        "readyForRealProvider": False,
        "secretValueReturned": False,
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
        "traceId": request.trace_id,
    }


def build_provider_runtime_guard_error_context(
    exc: ProviderError,
    *,
    request: ProviderRuntimeGuardRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    return {
        **_base_context(request, root=root),
        "guardPassed": False,
        "errorCode": exc.code,
    }


def evaluate_provider_runtime_guard(
    request: ProviderRuntimeGuardRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    if provider is None:
        raise ProviderError("NOT_FOUND", "Provider 不存在", [{"field": "provider", "reason": "未找到 Provider"}])
    if request.provider_id not in REAL_PROVIDER_IDS:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Provider Runtime Guard 只检查真实 Provider 占位",
            [{"field": "provider", "reason": f"{request.provider_id} is not a real provider placeholder"}],
        )
    if request.operation != "generateJson":
        raise ProviderError(
            "UNSUPPORTED_OPERATION",
            "真实 Provider PoC 首批只允许 generateJson 运行时护栏",
            [{"field": "operation", "reason": "only generateJson runtime guard is allowed"}],
        )
    if request.prompt_id != "lab_generation_v0" or request.output_kind != "Lab":
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 Provider PoC 首批只允许 Lab DSL 生成运行时护栏",
            [{"field": "promptId", "reason": "expected lab_generation_v0 with outputKind Lab"}],
        )
    if not 1 <= request.timeout_seconds <= 120:
        raise ProviderError(
            "VALIDATION_ERROR",
            "timeoutSeconds 超出允许范围",
            [{"field": "timeoutSeconds", "reason": "must be between 1 and 120"}],
        )
    if not 0 <= request.retry_count <= 3:
        raise ProviderError(
            "VALIDATION_ERROR",
            "retryCount 超出允许范围",
            [{"field": "retryCount", "reason": "must be between 0 and 3"}],
        )
    if not 1 <= request.concurrency_limit <= 4:
        raise ProviderError(
            "VALIDATION_ERROR",
            "concurrencyLimit 超出允许范围",
            [{"field": "concurrencyLimit", "reason": "must be between 1 and 4"}],
        )

    return {
        **_base_context(request, root=root, provider=provider),
        "guardPassed": True,
        "llmPocScope": "lab_generate_from_source_only",
        "message": "Provider 运行时护栏本地检查通过；当前不会发起真实调用。",
    }
