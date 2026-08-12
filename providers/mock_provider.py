"""Deterministic Phase 1 provider mock.

The module intentionally avoids real SDK imports, network calls, and secret
environment reads. It returns local DSL examples referenced by prompt metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "providers/provider.contract.json"
PROMPT_MANIFEST_PATH = ROOT / "prompts/manifest.json"


class ProviderError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        errors: list[dict[str, str]] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []
        self.details = details or {}


class LLMProvider(Protocol):
    def health(self) -> dict[str, Any]:
        ...

    def generate_text(self, prompt_id: str, *, trace_id: str | None = None) -> dict[str, Any]:
        ...

    def generate_json(
        self,
        prompt_id: str,
        *,
        output_kind: str | None = None,
        input_ref: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class ProviderCapabilities:
    generateText: bool = True
    generateJson: bool = True
    health: bool = True
    streamGenerate: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "generateText": self.generateText,
            "generateJson": self.generateJson,
            "health": self.health,
            "streamGenerate": self.streamGenerate,
        }


@dataclass(frozen=True)
class MockGenerationResult:
    providerId: str
    promptId: str
    outputKind: str
    generatedStatus: str
    reviewRequired: bool
    realLlmCalled: bool
    secretsRead: bool
    networkAccess: bool
    traceId: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "providerId": self.providerId,
            "promptId": self.promptId,
            "outputKind": self.outputKind,
            "generatedStatus": self.generatedStatus,
            "reviewRequired": self.reviewRequired,
            "realLlmCalled": self.realLlmCalled,
            "secretsRead": self.secretsRead,
            "networkAccess": self.networkAccess,
            "traceId": self.traceId,
            **self.payload,
        }


def make_trace_id() -> str:
    return f"trace_{uuid4().hex[:12]}"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ProviderError("PROVIDER_CONTRACT_ERROR", "JSON root must be object", [{"field": str(path), "reason": "root must be object"}])
    return payload


def load_provider_contract(root: Path = ROOT) -> dict[str, Any]:
    return _read_json(root / "providers/provider.contract.json")


def load_prompt_manifest(root: Path = ROOT) -> dict[str, Any]:
    return _read_json(root / "prompts/manifest.json")


def _enabled_provider_ids(contract: dict[str, Any]) -> list[str]:
    return [provider["id"] for provider in contract["providers"] if provider.get("enabled") is True]


def _assert_phase1_provider_rules(contract: dict[str, Any]) -> None:
    enabled_ids = _enabled_provider_ids(contract)
    if enabled_ids != ["mock"]:
        raise ProviderError(
            "PROVIDER_CONTRACT_ERROR",
            "Phase 1 only allows the mock provider",
            [{"field": "providers", "reason": f"enabled providers: {enabled_ids}"}],
        )
    for provider in contract["providers"]:
        if provider["id"] != "mock" and provider.get("enabled") is True:
            raise ProviderError(
                "PROVIDER_CONTRACT_ERROR",
                "Real providers must stay disabled in Phase 1",
                [{"field": provider["id"], "reason": "enabled real provider"}],
            )


def build_provider_registry(root: Path = ROOT) -> dict[str, Any]:
    contract = load_provider_contract(root)
    _assert_phase1_provider_rules(contract)
    return {
        "phase": contract["phase"],
        "mode": contract["mode"],
        "activeProvider": contract["activeProvider"],
        "providerInterface": contract["providerInterface"],
        "providers": contract["providers"],
        "rules": contract["rules"],
        "supportedMockOutputs": contract["supportedMockOutputs"],
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
    }


def _find_provider(contract: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    for provider in contract["providers"]:
        if provider["id"] == provider_id:
            return provider
    return None


def _find_prompt(manifest: dict[str, Any], prompt_id: str) -> dict[str, Any] | None:
    for prompt in manifest["prompts"]:
        if prompt["id"] == prompt_id:
            return prompt
    return None


def _find_supported_output(contract: dict[str, Any], prompt_id: str) -> dict[str, Any] | None:
    for output in contract["supportedMockOutputs"]:
        if output["promptId"] == prompt_id:
            return output
    return None


def _schema_kind(output_kind: str) -> str:
    mapping = {"Lab": "lab", "Exam": "exam", "Grading": "grading", "PPT": "ppt"}
    if output_kind not in mapping:
        raise ProviderError(
            "UNSUPPORTED_PROMPT",
            "该 Prompt 不支持 Mock JSON DSL 输出",
            [{"field": "outputKind", "reason": output_kind}],
        )
    return mapping[output_kind]


def _load_mock_dsl(output: dict[str, Any], root: Path) -> dict[str, Any]:
    output_kind = output["outputKind"]
    dsl_path = root / output["dslPath"]
    try:
        document = load_yaml(dsl_path)
        validate_dsl(document, load_schema(_schema_kind(output_kind), root))
    except DslValidationError as exc:
        raise ProviderError("SCHEMA_VALIDATION_ERROR", "Mock DSL Schema 校验失败", exc.errors) from exc
    if not isinstance(document, dict):
        raise ProviderError("SCHEMA_VALIDATION_ERROR", "Mock DSL Schema 校验失败", [{"field": "$", "reason": "root must be object"}])
    return document


class MockProvider:
    provider_id = "mock"

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.contract = load_provider_contract(root)
        _assert_phase1_provider_rules(self.contract)
        self.prompt_manifest = load_prompt_manifest(root)
        self.capabilities = ProviderCapabilities()

    def health(self) -> dict[str, Any]:
        return {
            "providerId": self.provider_id,
            "status": "UP",
            "phase": self.contract["phase"],
            "mode": self.contract["mode"],
            "capabilities": self.capabilities.to_dict(),
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
        }

    def _prompt_or_error(self, prompt_id: str) -> dict[str, Any]:
        prompt = _find_prompt(self.prompt_manifest, prompt_id)
        if prompt is None:
            raise ProviderError("NOT_FOUND", "Prompt 不存在", [{"field": "promptId", "reason": "未找到 Prompt"}])
        if not str(prompt.get("path", "")).startswith("prompts/"):
            raise ProviderError("PROVIDER_CONTRACT_ERROR", "Prompt 路径必须位于 prompts/", [{"field": "path", "reason": prompt.get("path", "")}])
        return prompt

    def generate_text(self, prompt_id: str, *, trace_id: str | None = None) -> dict[str, Any]:
        prompt = self._prompt_or_error(prompt_id)
        trace_id = trace_id or make_trace_id()
        return {
            "providerId": self.provider_id,
            "promptId": prompt_id,
            "promptPath": prompt["path"],
            "promptVersion": prompt["version"],
            "outputKind": prompt["outputKind"],
            "text": f"Mock text output for {prompt_id}.",
            "generatedStatus": prompt.get("defaultStatus", "DRAFT"),
            "reviewRequired": bool(prompt.get("reviewRequired", False)),
            "mode": "MOCK_ONLY",
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
            "traceId": trace_id,
        }

    def generate_json(
        self,
        prompt_id: str,
        *,
        output_kind: str | None = None,
        input_ref: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        prompt = self._prompt_or_error(prompt_id)
        supported_output = _find_supported_output(self.contract, prompt_id)
        if supported_output is None:
            raise ProviderError(
                "UNSUPPORTED_PROMPT",
                "该 Prompt 暂无 Phase 1 Mock DSL 输出",
                [{"field": "promptId", "reason": prompt_id}],
            )
        actual_output_kind = str(prompt["outputKind"])
        if output_kind and output_kind != actual_output_kind:
            raise ProviderError(
                "VALIDATION_ERROR",
                "outputKind 与 Prompt 输出类型不一致",
                [{"field": "outputKind", "reason": f"expected {actual_output_kind}"}],
            )
        document = _load_mock_dsl(supported_output, self.root)
        trace_id = trace_id or make_trace_id()
        result = MockGenerationResult(
            providerId=self.provider_id,
            promptId=prompt_id,
            outputKind=actual_output_kind,
            generatedStatus=prompt.get("defaultStatus", "WAITING_REVIEW"),
            reviewRequired=bool(prompt.get("reviewRequired", True)),
            realLlmCalled=False,
            secretsRead=False,
            networkAccess=False,
            traceId=trace_id,
            payload={
                "mode": "MOCK_ONLY",
                "promptPath": prompt["path"],
                "promptVersion": prompt["version"],
                "inputRef": input_ref,
                "outputSchema": prompt.get("outputSchema"),
                "dslPath": supported_output["dslPath"],
                "dslId": document.get("metadata", {}).get("id"),
                "dsl": document,
                "publishBlockedUntilApproved": True,
                "answerVisibleToCandidate": bool(prompt.get("answerVisibleToCandidate", False)),
                "artifactGenerated": bool(prompt.get("artifactGenerated", False)),
                "sandboxRequiredBeforeRealExecution": bool(prompt.get("sandboxRequiredBeforeRealExecution", False)),
            },
        )
        return result.to_dict()


def get_provider_health(provider_id: str, root: Path = ROOT) -> dict[str, Any]:
    contract = load_provider_contract(root)
    provider = _find_provider(contract, provider_id)
    if provider is None:
        raise ProviderError("NOT_FOUND", "Provider 不存在", [{"field": "provider", "reason": "未找到 Provider"}])
    if provider_id != "mock":
        raise ProviderError(
            "PROVIDER_DISABLED",
            "Phase 1 只启用 Mock Provider",
            [{"field": "provider", "reason": f"{provider_id} is disabled"}],
        )
    return MockProvider(root).health()
