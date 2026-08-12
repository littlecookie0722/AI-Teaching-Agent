"""Minimal real LLM single-request PoC for Lab DSL generation."""

from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from cli.dsl import DslValidationError, load_schema, validate_dsl

from .mock_provider import ProviderError


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PROVIDER = "openai"
SDK_IMPORT_NAME = "openai"
SECRET_ENV = "OPENAI_API_KEY"
MODEL_ENV = "OPENAI_MODEL"
BASE_URL_ENV = "OPENAI_BASE_URL"
PROMPT_ID = "lab_generation_v0"
PROMPT_VERSION = "real-llm-minimal-poc-v2"
PROMPT_PATH = "prompts/workflows/lab_generation.md"
MODE = "REAL_LLM_MINIMAL_SINGLE_REQUEST"
DEFAULT_INPUT_REF = "examples/input/demo-source.md"
DEFAULT_OUTPUT_REF = "examples/output/real-llm-minimal-poc-lab.json"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_OUTPUT_TOKENS = 1800
MAX_SOURCE_BYTES = 128 * 1024


@dataclass(frozen=True)
class RealLlmMinimalPocRequest:
    provider_id: str = SUPPORTED_PROVIDER
    input_ref: str = DEFAULT_INPUT_REF
    model: str | None = None
    base_url: str | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    explicit_real_call_opt_in: bool = False
    confirm_single_request: bool = False
    confirm_lab_only: bool = False
    confirm_waiting_review: bool = False
    confirm_no_auto_publish: bool = False
    generation_context: dict[str, Any] | None = None
    trace_id: str | None = None


ClientFactory = Callable[..., Any]


def describe_real_llm_minimal_poc(root: Path = ROOT) -> dict[str, Any]:
    schema_path = root / "templates/lab/lab.schema.json"
    input_path = root / DEFAULT_INPUT_REF
    return {
        "pocId": "real_llm_minimal_poc",
        "phase": "Phase 2",
        "mode": MODE,
        "providerId": SUPPORTED_PROVIDER,
        "sdkImportName": SDK_IMPORT_NAME,
        "secretEnv": SECRET_ENV,
        "modelEnv": MODEL_ENV,
        "baseUrlEnv": BASE_URL_ENV,
        "defaultInputRef": DEFAULT_INPUT_REF,
        "defaultOutputRef": DEFAULT_OUTPUT_REF,
        "promptPath": PROMPT_PATH,
        "promptVersion": PROMPT_VERSION,
        "promptExists": (root / PROMPT_PATH).exists(),
        "inputExists": input_path.exists(),
        "schemaPath": str(schema_path),
        "schemaExists": schema_path.exists(),
        "scope": {
            "outputKind": "Lab DSL",
            "requestCount": 1,
            "batchRequest": False,
            "streaming": False,
            "realCloudResourceChanged": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
        "requiredRuntime": {
            "openaiPackage": "installed and importable",
            "apiKey": f"{SECRET_ENV} must be present",
            "model": f"--model or {MODEL_ENV} must be present",
        },
        "reviewPolicy": {
            "generatedStatus": "WAITING_REVIEW",
            "taskStatus": "WAITING_REVIEW",
            "autoPublishAllowed": False,
            "reviewBypassed": False,
        },
        "requiredConfirmations": [
            "explicit_real_call_opt_in",
            "confirm_single_request",
            "confirm_lab_only",
            "confirm_waiting_review",
            "confirm_no_auto_publish",
        ],
    }


def run_real_llm_minimal_poc(
    request: RealLlmMinimalPocRequest,
    *,
    root: Path = ROOT,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    trace_id = request.trace_id or f"trace_{uuid4().hex[:12]}"
    _validate_request(request, root)
    input_path = _resolve_path(root, request.input_ref)
    source_text = _read_source(input_path)
    lab_schema = load_schema("lab", root)
    api_key = _read_required_secret()
    model = _resolve_model(request)
    base_url, base_url_source = _resolve_base_url(request.base_url)
    sdk_module = _import_sdk()
    client = _create_client(sdk_module, api_key=api_key, base_url=base_url, client_factory=client_factory)

    try:
        response = client.responses.create(
            model=model,
            instructions=_build_instructions(root),
            input=_build_input(source_text, request.generation_context),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "lab_dsl",
                    "schema": _response_format_schema(lab_schema),
                    "strict": False,
                }
            },
            temperature=0,
            max_output_tokens=request.max_output_tokens,
            stream=False,
            timeout=request.timeout_seconds,
        )
    except Exception as exc:  # pragma: no cover - exercised by integration/runtime only
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_FAILED",
            "真实 LLM 最小单请求调用失败",
            [{"field": "provider.openai.responses.create", "reason": exc.__class__.__name__}],
        ) from exc

    lab_dsl = _parse_response_json(response)
    _validate_lab_dsl(lab_dsl, lab_schema)
    return {
        "pocId": "real_llm_minimal_poc",
        "phase": "Phase 2",
        "mode": MODE,
        "providerId": request.provider_id,
        "sdkImportName": SDK_IMPORT_NAME,
        "sdkImported": True,
        "clientCreated": True,
        "secretEnv": SECRET_ENV,
        "secretPresent": True,
        "secretValueRead": True,
        "secretValueReturned": False,
        "secretValueLogged": False,
        "model": model,
        "baseUrlEnv": BASE_URL_ENV,
        "baseUrlConfigured": bool(base_url),
        "baseUrlSource": base_url_source,
        "inputRef": request.input_ref,
        "generationContext": request.generation_context,
        "promptId": PROMPT_ID,
        "promptVersion": PROMPT_VERSION,
        "promptPath": PROMPT_PATH,
        "requestSent": True,
        "requestCount": 1,
        "singleRequestOnly": True,
        "batchRequest": False,
        "streaming": False,
        "networkAccess": True,
        "realLlmCalled": True,
        "realCloudResourceChanged": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "generatedContentCreated": True,
        "schemaValidated": True,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "taskCreated": False,
        "outputKind": "Lab",
        "dslId": lab_dsl.get("metadata", {}).get("id"),
        "responseId": _response_id(response),
        "usage": _response_usage(response),
        "labDsl": lab_dsl,
        "traceId": trace_id,
    }


def build_real_llm_minimal_poc_error_context(
    exc: ProviderError,
    *,
    request: RealLlmMinimalPocRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    return {
        "pocId": "real_llm_minimal_poc",
        "phase": "Phase 2",
        "mode": MODE,
        "providerId": request.provider_id,
        "sdkImportName": SDK_IMPORT_NAME,
        "secretEnv": SECRET_ENV,
        "secretPresent": SECRET_ENV in os.environ,
        "secretValueReturned": False,
        "modelPresent": bool(request.model or os.environ.get(MODEL_ENV)),
        "baseUrlEnv": BASE_URL_ENV,
        "baseUrlConfigured": bool(request.base_url or os.environ.get(BASE_URL_ENV)),
        "baseUrlSource": "argument" if request.base_url else ("env" if os.environ.get(BASE_URL_ENV) else None),
        "inputRef": request.input_ref,
        "inputExists": _resolve_path(root, request.input_ref).exists(),
        "requestSent": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "taskCreated": False,
        "errorCode": exc.code,
        "errors": exc.errors,
    }


def _validate_request(request: RealLlmMinimalPocRequest, root: Path) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_UNSUPPORTED_PROVIDER",
            "真实 LLM 最小 PoC 仅支持 openai provider",
            [{"field": "provider", "reason": f"unsupported provider: {request.provider_id}"}],
        )
    missing = [
        field
        for field, enabled in {
            "explicit_real_call_opt_in": request.explicit_real_call_opt_in,
            "confirm_single_request": request.confirm_single_request,
            "confirm_lab_only": request.confirm_lab_only,
            "confirm_waiting_review": request.confirm_waiting_review,
            "confirm_no_auto_publish": request.confirm_no_auto_publish,
        }.items()
        if not enabled
    ]
    if missing:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_CONFIRMATION_REQUIRED",
            "真实 LLM 最小 PoC 需要显式确认调用边界",
            [{"field": field, "reason": "required"} for field in missing],
        )
    if request.timeout_seconds <= 0:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_INVALID_TIMEOUT",
            "timeout-seconds 必须大于 0",
            [{"field": "timeoutSeconds", "reason": "must be > 0"}],
        )
    if request.max_output_tokens <= 0:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_INVALID_MAX_OUTPUT_TOKENS",
            "max-output-tokens 必须大于 0",
            [{"field": "maxOutputTokens", "reason": "must be > 0"}],
        )
    input_path = _resolve_path(root, request.input_ref)
    if not input_path.exists():
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_INPUT_NOT_FOUND",
            "真实 LLM 最小 PoC 输入文件不存在",
            [{"field": "inputRef", "reason": str(input_path)}],
        )


def _resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def _read_source(path: Path) -> str:
    size = path.stat().st_size
    if size > MAX_SOURCE_BYTES:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_INPUT_TOO_LARGE",
            "真实 LLM 最小 PoC 输入文件过大",
            [{"field": "inputRef", "reason": f"{size} bytes > {MAX_SOURCE_BYTES} bytes"}],
        )
    return path.read_text(encoding="utf-8")


def _read_required_secret() -> str:
    value = os.environ.get(SECRET_ENV)
    if not value:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED",
            "真实 LLM 最小 PoC 需要通过环境变量提供 OPENAI_API_KEY",
            [{"field": SECRET_ENV, "reason": "missing or empty"}],
        )
    return value


def _resolve_model(request: RealLlmMinimalPocRequest) -> str:
    model = request.model or os.environ.get(MODEL_ENV)
    if not model:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_MODEL_REQUIRED",
            "真实 LLM 最小 PoC 需要通过 --model 或 OPENAI_MODEL 指定模型",
            [{"field": "model", "reason": f"provide --model or {MODEL_ENV}"}],
        )
    return model


def _resolve_base_url(base_url: str | None = None) -> tuple[str | None, str | None]:
    if base_url:
        return base_url, "argument"
    env_value = os.environ.get(BASE_URL_ENV)
    if env_value:
        return env_value, "env"
    return None, None


def _import_sdk() -> Any:
    try:
        return importlib.import_module(SDK_IMPORT_NAME)
    except ImportError as exc:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_SDK_IMPORT_FAILED",
            "openai SDK 未安装或不可导入",
            [{"field": SDK_IMPORT_NAME, "reason": exc.__class__.__name__}],
        ) from exc


def _create_client(
    sdk_module: Any,
    *,
    api_key: str,
    base_url: str | None,
    client_factory: ClientFactory | None,
) -> Any:
    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    factory = client_factory or sdk_module.OpenAI
    try:
        return factory(**kwargs)
    except Exception as exc:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_CLIENT_CREATE_FAILED",
            "真实 LLM 最小 PoC 客户端创建失败",
            [{"field": "client", "reason": exc.__class__.__name__}],
        ) from exc


def _build_instructions(root: Path) -> str:
    return (root / PROMPT_PATH).read_text(encoding="utf-8")


def _build_input(source_text: str, generation_context: dict[str, Any] | None = None) -> str:
    context_block = ""
    if generation_context:
        context_block = (
            "\n\nLab generation context JSON:\n"
            f"{json.dumps(generation_context, ensure_ascii=False, sort_keys=True)}"
        )
    return (
        "Teaching source material:\n"
        f"{source_text}"
        f"{context_block}"
    )


def _response_format_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return _strip_schema_metadata(_replace_const(dict(schema)))


def _replace_const(value: Any) -> Any:
    if isinstance(value, dict):
        converted = {key: _replace_const(item) for key, item in value.items() if key != "const"}
        if "const" in value:
            converted["enum"] = [value["const"]]
        return converted
    if isinstance(value, list):
        return [_replace_const(item) for item in value]
    return value


def _strip_schema_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_schema_metadata(item)
            for key, item in value.items()
            if key not in {"$schema", "title"}
        }
    if isinstance(value, list):
        return [_strip_schema_metadata(item) for item in value]
    return value


def _parse_response_json(response: Any) -> dict[str, Any]:
    text = _response_output_text(response)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_INVALID_JSON",
            "真实 LLM 返回内容不是合法 JSON",
            [{"field": "response.output_text", "reason": exc.__class__.__name__}],
        ) from exc
    if not isinstance(payload, dict):
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_INVALID_JSON_ROOT",
            "真实 LLM 返回 JSON 根节点必须是对象",
            [{"field": "response.output_text", "reason": "root must be object"}],
        )
    return payload


def _response_output_text(response: Any) -> str:
    if isinstance(response, dict):
        if isinstance(response.get("output_text"), str):
            return response["output_text"]
        output = response.get("output")
    else:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text
        output = getattr(response, "output", None)
    text = _extract_text_from_output(output)
    if text:
        return text
    raise ProviderError(
        "REAL_LLM_MINIMAL_CALL_EMPTY_RESPONSE",
        "真实 LLM 返回内容为空或无法提取文本",
        [{"field": "response.output", "reason": "missing output_text"}],
    )


def _extract_text_from_output(output: Any) -> str | None:
    if not output:
        return None
    chunks: list[str] = []
    for item in output:
        content = item.get("content") if isinstance(item, dict) else getattr(item, "content", None)
        if not content:
            continue
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
            else:
                text = getattr(part, "text", None)
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks) if chunks else None


def _validate_lab_dsl(document: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        validate_dsl(document, schema)
    except DslValidationError as exc:
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_SCHEMA_VALIDATION_FAILED",
            "真实 LLM 生成内容未通过 Lab DSL Schema 校验",
            [
                {"field": err.get("field", "$"), "reason": err.get("reason", "schema validation failed")}
                for err in exc.errors
            ],
        ) from exc
    if document.get("kind") != "Lab":
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_KIND_INVALID",
            "真实 LLM 最小 PoC 只允许生成 Lab DSL",
            [{"field": "kind", "reason": "must be Lab"}],
        )
    if document.get("status") != "WAITING_REVIEW":
        raise ProviderError(
            "REAL_LLM_MINIMAL_CALL_REVIEW_STATUS_REQUIRED",
            "真实 LLM 生成内容必须进入 WAITING_REVIEW",
            [{"field": "status", "reason": "must be WAITING_REVIEW"}],
        )


def _response_id(response: Any) -> str | None:
    if isinstance(response, dict):
        value = response.get("id")
    else:
        value = getattr(response, "id", None)
    return value if isinstance(value, str) else None


def _response_usage(response: Any) -> dict[str, Any] | None:
    if isinstance(response, dict):
        usage = response.get("usage")
    else:
        usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    to_dict = getattr(usage, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return {
        key: getattr(usage, key)
        for key in ("input_tokens", "output_tokens", "total_tokens")
        if hasattr(usage, key)
    }
