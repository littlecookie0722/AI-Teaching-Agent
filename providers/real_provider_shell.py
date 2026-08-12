"""Disabled real provider implementation shells.

These classes reserve the OpenAI, Anthropic, and local model provider shapes
without importing SDKs, opening network connections, or reading secret values.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .mock_provider import ProviderError, load_provider_contract
from .real_provider_gate import RealProviderGateRequest, preflight_real_provider


ROOT = Path(__file__).resolve().parents[1]
RealProviderShellOperation = Literal["health", "generateText", "generateJson", "streamGenerate"]


@dataclass(frozen=True)
class RealProviderShellRequest:
    provider_id: str
    operation: RealProviderShellOperation = "health"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    explicit_opt_in: bool = False
    trace_id: str | None = None


class DisabledRealProvider:
    provider_id = ""
    sdk_package = ""
    endpoint_env: str | None = None

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.contract = load_provider_contract(root)
        self.provider = _find_provider(self.contract, self.provider_id)
        if self.provider is None:
            raise ProviderError(
                "NOT_FOUND",
                "Provider 不存在",
                [{"field": "provider", "reason": f"{self.provider_id} is not declared"}],
            )

    def describe(self) -> dict[str, Any]:
        return {
            "providerId": self.provider_id,
            "className": self.__class__.__name__,
            "displayName": self.provider["displayName"],
            "phase": self.contract["phase"],
            "targetPhase": "Phase 2",
            "mode": self.contract["mode"],
            "enabled": bool(self.provider.get("enabled", False)),
            "defaultProvider": self.contract["activeProvider"],
            "contractImplementationStatus": self.provider.get("implementationStatus"),
            "shellImplementationStatus": "disabled_shell",
            "requiresApiKey": bool(self.provider.get("requiresApiKey", False)),
            "secretEnv": self.provider.get("secretEnv"),
            "endpointEnv": self.endpoint_env,
            "sdkPackage": self.sdk_package,
            "sdkImported": False,
            "clientCreated": False,
            "generationOperationsEnabled": False,
            "realProviderRoutingAllowed": False,
            "secretValueReturned": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
            "generatedContentCreated": False,
            "taskCreated": False,
            "reviewBypassed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "operations": {
                "health": {
                    "enabled": True,
                    "returns": "disabled_descriptor",
                    "readsSecretValue": False,
                    "performsNetworkCall": False,
                },
                "generateText": {
                    "enabled": False,
                    "errorCode": "REAL_PROVIDER_SHELL_DISABLED",
                    "readsSecretValue": False,
                    "performsNetworkCall": False,
                },
                "generateJson": {
                    "enabled": False,
                    "errorCode": "REAL_PROVIDER_SHELL_DISABLED",
                    "requiresPreflight": True,
                    "readsSecretValue": False,
                    "performsNetworkCall": False,
                },
                "streamGenerate": {
                    "enabled": False,
                    "errorCode": "UNSUPPORTED_OPERATION",
                    "readsSecretValue": False,
                    "performsNetworkCall": False,
                },
            },
        }

    def health(self, *, trace_id: str | None = None) -> dict[str, Any]:
        return {
            **self.describe(),
            "operation": "health",
            "status": "DISABLED",
            "readyForRealProvider": False,
            "traceId": trace_id,
        }

    def generate_text(self, prompt_id: str, *, trace_id: str | None = None) -> dict[str, Any]:
        raise self._disabled_error("generateText", prompt_id=prompt_id)

    def generate_json(
        self,
        prompt_id: str,
        *,
        output_kind: str = "Lab",
        input_ref: str = "examples/input/demo-source.md",
        explicit_opt_in: bool = False,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        preflight_real_provider(
            RealProviderGateRequest(
                provider_id=self.provider_id,
                operation="generateJson",
                prompt_id=prompt_id,
                output_kind=output_kind,
                input_ref=input_ref,
                explicit_opt_in=explicit_opt_in,
            ),
            root=self.root,
        )
        raise self._disabled_error("generateJson", prompt_id=prompt_id)

    def stream_generate(self, prompt_id: str, *, trace_id: str | None = None) -> dict[str, Any]:
        raise ProviderError(
            "UNSUPPORTED_OPERATION",
            "真实 Provider 空壳暂不支持 streamGenerate",
            [{"field": "operation", "reason": "streamGenerate remains disabled"}],
        )

    def _disabled_error(self, operation: str, *, prompt_id: str) -> ProviderError:
        return ProviderError(
            "REAL_PROVIDER_SHELL_DISABLED",
            "真实 Provider 适配器空壳默认禁用",
            [
                {"field": "provider", "reason": f"{self.provider_id} shell is disabled"},
                {"field": "operation", "reason": operation},
                {"field": "promptId", "reason": prompt_id},
            ],
        )


class OpenAIProvider(DisabledRealProvider):
    provider_id = "openai"
    sdk_package = "openai"


class AnthropicProvider(DisabledRealProvider):
    provider_id = "anthropic"
    sdk_package = "anthropic"


class LocalModelProvider(DisabledRealProvider):
    provider_id = "local"
    sdk_package = "local_http"
    endpoint_env = "LOCAL_MODEL_ENDPOINT"


REAL_PROVIDER_SHELLS: dict[str, type[DisabledRealProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "local": LocalModelProvider,
}


def _find_provider(contract: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    for provider in contract["providers"]:
        if provider["id"] == provider_id:
            return provider
    return None


def get_real_provider_shell(provider_id: str, *, root: Path = ROOT) -> DisabledRealProvider:
    provider_class = REAL_PROVIDER_SHELLS.get(provider_id)
    if provider_class is None:
        raise ProviderError(
            "VALIDATION_ERROR",
            "未知真实 Provider 空壳",
            [{"field": "provider", "reason": f"{provider_id} is not a real provider shell"}],
        )
    return provider_class(root)


def build_real_provider_shell_registry(*, root: Path = ROOT) -> dict[str, Any]:
    contract = load_provider_contract(root)
    return {
        "phase": contract["phase"],
        "targetPhase": "Phase 2",
        "mode": contract["mode"],
        "defaultProvider": contract["activeProvider"],
        "activeProvider": contract["activeProvider"],
        "shellImplementationStatus": "disabled_shell",
        "realProviderRoutingAllowed": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "sdkImported": False,
        "secretValueReturned": False,
        "providers": [
            get_real_provider_shell(provider_id, root=root).describe()
            for provider_id in ["openai", "anthropic", "local"]
        ],
    }


def invoke_real_provider_shell(request: RealProviderShellRequest, *, root: Path = ROOT) -> dict[str, Any]:
    provider = get_real_provider_shell(request.provider_id, root=root)

    if request.operation == "health":
        return provider.health(trace_id=request.trace_id)
    if request.operation == "generateText":
        return provider.generate_text(request.prompt_id, trace_id=request.trace_id)
    if request.operation == "generateJson":
        return provider.generate_json(
            request.prompt_id,
            output_kind=request.output_kind,
            input_ref=request.input_ref,
            explicit_opt_in=request.explicit_opt_in,
            trace_id=request.trace_id,
        )
    if request.operation == "streamGenerate":
        return provider.stream_generate(request.prompt_id, trace_id=request.trace_id)

    raise ProviderError(
        "UNSUPPORTED_OPERATION",
        "不支持的真实 Provider 空壳操作",
        [{"field": "operation", "reason": str(request.operation)}],
    )


def build_real_provider_shell_error_context(
    exc: ProviderError,
    *,
    request: RealProviderShellRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    try:
        base = get_real_provider_shell(request.provider_id, root=root).describe()
    except ProviderError:
        base = {
            "providerId": request.provider_id,
            "className": None,
            "phase": "Phase 1",
            "targetPhase": "Phase 2",
            "mode": "MOCK_ONLY",
            "defaultProvider": "mock",
            "enabled": False,
            "shellImplementationStatus": "unknown",
            "sdkImported": False,
            "secretValueReturned": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
            "generatedContentCreated": False,
            "taskCreated": False,
            "reviewBypassed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        }
    return {
        **base,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "explicitOptIn": request.explicit_opt_in,
        "readyForRealProvider": False,
        "errorCode": exc.code,
    }
