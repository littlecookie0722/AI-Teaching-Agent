"""Mock-only provider adapter boundary.

The adapter gives workflows one stable provider-facing entry point while Phase 1
still routes exclusively to MockProvider.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .mock_provider import MockProvider, ProviderError, build_provider_registry


ROOT = Path(__file__).resolve().parents[1]
ProviderOperation = Literal["health", "generateText", "generateJson", "streamGenerate"]


@dataclass(frozen=True)
class ProviderRequest:
    operation: ProviderOperation
    prompt_id: str | None = None
    provider_id: str = "mock"
    output_kind: str | None = None
    input_ref: str | None = None
    trace_id: str | None = None


class ProviderAdapter:
    adapter_id = "mock_provider_adapter"
    interface_name = "LLMProvider"

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.registry = build_provider_registry(root)

    def _assert_mock_provider(self, provider_id: str) -> None:
        if provider_id != "mock":
            raise ProviderError(
                "PROVIDER_DISABLED",
                "Phase 1 Provider Adapter 只允许 Mock Provider",
                [{"field": "provider", "reason": f"{provider_id} is disabled"}],
            )

    def _with_adapter_fields(self, operation: ProviderOperation, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapterId": self.adapter_id,
            "interfaceName": self.interface_name,
            "operation": operation,
            **payload,
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
        }

    def invoke(self, request: ProviderRequest) -> dict[str, Any]:
        self._assert_mock_provider(request.provider_id)
        provider = MockProvider(self.root)

        if request.operation == "health":
            return self._with_adapter_fields("health", provider.health())

        if request.operation == "streamGenerate":
            raise ProviderError(
                "UNSUPPORTED_OPERATION",
                "Phase 1 不支持 streamGenerate",
                [{"field": "operation", "reason": "streamGenerate is deferred"}],
            )

        if not request.prompt_id:
            raise ProviderError("VALIDATION_ERROR", "参数错误", [{"field": "promptId", "reason": "缺少参数"}])

        if request.operation == "generateText":
            result = provider.generate_text(request.prompt_id, trace_id=request.trace_id)
            return self._with_adapter_fields("generateText", result)

        if request.operation == "generateJson":
            result = provider.generate_json(
                request.prompt_id,
                output_kind=request.output_kind,
                input_ref=request.input_ref,
                trace_id=request.trace_id,
            )
            return self._with_adapter_fields("generateJson", result)

        raise ProviderError(
            "UNSUPPORTED_OPERATION",
            "不支持的 Provider Adapter 操作",
            [{"field": "operation", "reason": str(request.operation)}],
        )


def invoke_provider(
    operation: ProviderOperation,
    *,
    prompt_id: str | None = None,
    provider_id: str = "mock",
    output_kind: str | None = None,
    input_ref: str | None = None,
    trace_id: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = ProviderRequest(
        operation=operation,
        prompt_id=prompt_id,
        provider_id=provider_id,
        output_kind=output_kind,
        input_ref=input_ref,
        trace_id=trace_id,
    )
    return ProviderAdapter(root).invoke(request)


def build_provider_error_context(
    exc: ProviderError,
    *,
    operation: str | None = None,
    provider_id: str | None = None,
) -> dict[str, Any]:
    return {
        "adapterId": ProviderAdapter.adapter_id,
        "interfaceName": ProviderAdapter.interface_name,
        "operation": operation,
        "providerId": provider_id or "mock",
        "mode": "MOCK_ONLY",
        "errorCode": exc.code,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "autoPublishAllowed": False,
        "realPublish": False,
    }
