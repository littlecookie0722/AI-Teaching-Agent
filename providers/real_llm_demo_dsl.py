"""Real LLM demo DSL generation for Lab / Exam / Grading / PPT."""

from __future__ import annotations

import importlib
import json
import os
import re
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
MODE = "REAL_LLM_DEMO_DSL_GENERATION"
PROMPT_VERSION = "real-llm-demo-v1"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_OUTPUT_TOKENS = 2200
MAX_SOURCE_BYTES = 128 * 1024
API_SURFACE_AUTO = "auto"
API_SURFACE_RESPONSES = "responses"
API_SURFACE_CHAT_COMPLETIONS = "chat.completions"
API_SURFACE_CHAT_JSON_OBJECT = "chat.completions.json_object"
ALLOWED_API_SURFACES = {
    API_SURFACE_AUTO,
    API_SURFACE_RESPONSES,
    API_SURFACE_CHAT_COMPLETIONS,
    API_SURFACE_CHAT_JSON_OBJECT,
}
EXAM_QUESTION_TYPES = {"notebook_fill_blank", "coding_task", "short_answer"}
EXAM_QUESTION_TYPE_ALIASES = {
    "coding": "coding_task",
    "code": "coding_task",
    "programming": "coding_task",
    "programming_task": "coding_task",
    "code_task": "coding_task",
    "notebook": "notebook_fill_blank",
    "notebook_task": "notebook_fill_blank",
    "ipynb": "notebook_fill_blank",
    "fill_blank": "notebook_fill_blank",
    "fill_in_blank": "notebook_fill_blank",
    "blank": "notebook_fill_blank",
    "short": "short_answer",
    "short-answer": "short_answer",
    "qa": "short_answer",
    "question_answer": "short_answer",
    "text": "short_answer",
}
DIFFICULTY_LEVELS = {"beginner", "intermediate", "advanced"}
DIFFICULTY_ALIASES = {
    "easy": "beginner",
    "basic": "beginner",
    "intro": "beginner",
    "introductory": "beginner",
    "入门": "beginner",
    "初级": "beginner",
    "medium": "intermediate",
    "normal": "intermediate",
    "middle": "intermediate",
    "中级": "intermediate",
    "hard": "advanced",
    "expert": "advanced",
    "difficult": "advanced",
    "高级": "advanced",
}
SCHEMA_FAILURE_DIAGNOSTIC_VERSION = "real-llm-schema-failure-diagnostic-v1"
SCHEMA_FAILURE_ERROR_LIMIT = 20
SCHEMA_FAILURE_SENSITIVE_FIELD_MARKERS = {
    "answer",
    "gradingref",
    "apikey",
    "api_key",
    "token",
    "secret",
    "password",
    "authorization",
}
SCHEMA_FAILURE_RECOMMENDATIONS = {
    "missing_required_field": "补齐 Prompt 必填字段约束；若字段可从上下文推断，则补确定性默认值。",
    "expected_object": "优先在归一化层处理 string/list 到 object 的可逆结构漂移。",
    "expected_string": "优先在归一化层处理 object/list/number 到 string 的可审核摘要转换。",
    "expected_array": "补充数组字段约束；仅在业务语义明确时把单值转为数组。",
    "expected_integer": "补充整数格式约束；仅转换可安全解析的数字。",
    "enum_mismatch": "收敛 Prompt 枚举输出，必要时补充同义词映射。",
    "additional_field": "确认是否为平台不接收字段；若无业务价值则在归一化层移除。",
    "cardinality": "补充最小项数约束或默认可审核条目。",
    "string_length": "补充非空或长度约束；只有业务语义明确时才生成可审核的默认文本。",
    "pattern_mismatch": "收敛 Prompt 的字符串格式约束；保留失败样本验证格式归一化。",
    "numeric_range": "收敛数值范围约束；仅修复可由业务规则确定的越界值。",
    "composition_mismatch": "检查 oneOf/anyOf/allOf 分支歧义，优先修正输出结构而不是放宽 Schema。",
    "unknown_schema_failure": "保留失败样本，先加入漂移矩阵再决定是否归一化。",
}

KIND_CONFIG = {
    "lab": {
        "outputKind": "Lab",
        "schemaKind": "lab",
        "promptId": "lab_generation_v0",
        "promptPath": "prompts/workflows/lab_generation.md",
    },
    "exam": {
        "outputKind": "Exam",
        "schemaKind": "exam",
        "promptId": "exam_generation_v0",
        "promptPath": "prompts/workflows/exam_generation.md",
    },
    "grading": {
        "outputKind": "Grading",
        "schemaKind": "grading",
        "promptId": "grading_generation_v0",
        "promptPath": "prompts/workflows/grading_generation.md",
    },
    "ppt": {
        "outputKind": "PPT",
        "schemaKind": "ppt",
        "promptId": "ppt_generation_v0",
        "promptPath": "prompts/workflows/ppt_generation.md",
    },
}

GRADING_CHECK_TYPES = {"file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword"}
GRADING_CHECK_TYPE_ALIASES = {
    "file": "file_exists",
    "file_exists_check": "file_exists",
    "fileexistsgrader": "file_exists",
    "exists": "file_exists",
    "stdout": "stdout_contains",
    "stdout_check": "stdout_contains",
    "output_contains": "stdout_contains",
    "command_output": "stdout_contains",
    "stdoutcontainsgrader": "stdout_contains",
    "unit_test": "pytest",
    "unit_tests": "pytest",
    "test": "pytest",
    "tests": "pytest",
    "pytestgrader": "pytest",
    "notebook": "notebook_cell",
    "notebook_output": "notebook_cell",
    "ipynb": "notebook_cell",
    "notebookgrader": "notebook_cell",
    "json": "json_field",
    "json_path": "json_field",
    "json_value": "json_field",
    "jsonfieldgrader": "json_field",
    "log": "log_keyword",
    "keyword": "log_keyword",
    "log_contains": "log_keyword",
    "logkeywordgrader": "log_keyword",
}
GRADING_CHECK_RUNNERS = {
    "file_exists": "FileExistsGrader",
    "stdout_contains": "StdoutContainsGrader",
    "pytest": "PytestGrader",
    "notebook_cell": "NotebookGrader",
    "json_field": "JsonFieldGrader",
    "log_keyword": "LogKeywordGrader",
}
GRADING_RISK_LEVELS = {
    "file_exists": "low",
    "stdout_contains": "medium",
    "pytest": "medium",
    "notebook_cell": "high",
    "json_field": "low",
    "log_keyword": "medium",
}
GRADING_CHECK_FIELD_ALIASES = {
    "id": ("checkId", "check_id", "ruleId", "rule_id", "key", "ref", "name"),
    "type": ("kind", "checkType", "check_type", "runner", "validator", "method"),
    "score": ("points", "weight", "maxScore", "max_score"),
    "path": ("file", "filePath", "file_path", "filename", "targetFile", "target_file", "logPath", "log_path"),
    "command": ("cmd", "run", "shell", "shellCommand", "shell_command"),
    "notebookPath": ("notebook", "notebookFile", "notebook_file", "ipynb", "ipynbPath", "ipynb_path"),
    "cellIndex": ("cell", "cellNumber", "cell_number", "cell_index"),
    "jsonPath": ("json_path", "fieldPath", "field_path", "pathExpression", "jsonPointer", "json_pointer"),
    "expectedValue": ("expected_value", "expectedJsonValue", "expected_json_value", "targetValue", "target_value", "value"),
    "expected": (
        "expectedOutput",
        "expected_output",
        "expectedTokens",
        "expected_tokens",
        "contains",
        "keywords",
        "keyword",
        "output",
        "stdout",
        "expectedStdout",
        "expected_stdout",
    ),
}
ASSESSMENT_PLAN_FIELD_ALIASES = {
    "checkId": ("check_id", "id", "check", "ruleId", "rule_id", "ref"),
    "type": ("kind", "checkType", "check_type", "runnerType", "runner_type"),
    "runner": ("runnerName", "runner_name", "grader", "graderName", "grader_name"),
    "score": ("points", "weight", "maxScore", "max_score"),
    "inputSummary": (
        "summary",
        "input",
        "description",
        "reviewSummary",
        "review_summary",
        "planSummary",
        "plan_summary",
    ),
    "executionPlan": ("execution", "execution_plan", "runPlan", "run_plan", "sandboxPlan", "sandbox_plan"),
    "mockEvidence": ("evidence", "mock_evidence", "sampleEvidence", "sample_evidence"),
    "riskLevel": ("risk", "risk_level", "severity"),
    "sandboxRequiredBeforeRealExecution": (
        "sandboxRequired",
        "sandbox_required",
        "requiresSandbox",
        "requires_sandbox",
    ),
}
ASSESSMENT_EXECUTION_PLAN_FIELD_ALIASES = {
    "strategy": ("mode", "executionMode", "execution_mode"),
    "requiredLimits": ("limits", "resources", "required_limits", "resourceLimits", "resource_limits"),
    "wouldRunInsideRealSandbox": ("wouldRunInSandbox", "would_run_in_sandbox", "sandbox", "sandboxed"),
}
LAB_STEP_FIELD_ALIASES = {
    "id": ("stepId", "step_id", "key", "ref"),
    "title": ("name", "heading", "stepTitle", "step_title"),
    "instruction": ("description", "task", "content", "text", "body", "prompt", "detail", "details"),
    "commands": (
        "command",
        "shell",
        "shellCommands",
        "shell_commands",
        "cmd",
        "cmds",
        "commandList",
        "command_list",
    ),
    "expectedResult": (
        "expected",
        "output",
        "result",
        "expectedOutput",
        "expected_output",
        "successCriteria",
        "success_criteria",
    ),
}
EXAM_QUESTION_FIELD_ALIASES = {
    "title": ("name", "heading", "questionTitle", "question_title"),
    "stem": ("question", "description", "prompt", "task", "instruction", "instructions"),
    "blankCode": ("blank", "codeBlank", "code_blank", "starterCode", "starter_code", "templateCode", "template_code"),
    "answer": ("correctAnswer", "correct_answer", "referenceAnswer", "reference_answer", "solution"),
    "gradingRef": ("checkId", "check_id", "gradingId", "grading_id", "rubricRef", "rubric_ref", "assessmentRef", "assessment_ref"),
}
GRADING_REF_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
UNSTABLE_GENERIC_GRADING_REFS = {
    "manual",
    "manual_review",
    "manual-check",
    "review",
    "teacher_review",
    "human_review",
}
PPT_SLIDE_FIELD_ALIASES = {
    "id": ("slideId", "slide_id", "key", "ref"),
    "type": ("slideType", "slide_type", "layout", "kind"),
    "title": ("name", "heading", "slideTitle", "slide_title"),
    "subtitle": ("subTitle", "sub_title", "subtitleText", "subtitle_text", "tagline"),
    "bullets": (
        "points",
        "items",
        "keyPoints",
        "key_points",
        "takeaways",
        "talkingPoints",
        "talking_points",
        "content",
        "body",
    ),
}
PPT_SLIDE_LAYOUTS = frozenset({"hero", "objectives", "concept", "process", "exercise", "summary"})


@dataclass(frozen=True)
class RealLlmDemoDslRequest:
    kind: str
    provider_id: str = SUPPORTED_PROVIDER
    input_ref: str | None = None
    input_payload: dict[str, Any] | None = None
    model: str | None = None
    base_url: str | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    explicit_real_call_opt_in: bool = False
    confirm_waiting_review: bool = False
    confirm_no_auto_publish: bool = False
    repair_on_schema_failure: bool = False
    api_surface: str = API_SURFACE_AUTO
    trace_id: str | None = None


ClientFactory = Callable[..., Any]


def run_real_llm_demo_dsl_generation(
    request: RealLlmDemoDslRequest,
    *,
    root: Path = ROOT,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    trace_id = request.trace_id or f"trace_{uuid4().hex[:12]}"
    config = _validate_request(request, root)
    schema = load_schema(config["schemaKind"], root)
    source_text = _read_optional_source(root, request.input_ref)
    api_key = _read_required_secret()
    model = _resolve_model(request)
    base_url, base_url_source = _resolve_base_url(request.base_url)
    sdk_module = _import_sdk()
    client = _create_client(sdk_module, api_key=api_key, base_url=base_url, client_factory=client_factory)
    instructions = _build_instructions(root, config)
    request_input = _build_input(
        kind=request.kind,
        output_kind=config["outputKind"],
        input_ref=request.input_ref,
        source_text=source_text,
        input_payload=request.input_payload,
    )
    text_format = {
        "type": "json_schema",
        "name": f"{request.kind}_dsl",
        "schema": _response_format_schema(schema),
        "strict": False,
    }

    response, api_surface = _send_real_llm_demo_request(
        client,
        model=model,
        instructions=instructions,
        request_input=request_input,
        text_format=text_format,
        timeout_seconds=request.timeout_seconds,
        max_output_tokens=request.max_output_tokens,
        api_surface=request.api_surface,
        kind=request.kind,
    )
    request_count = 1
    try:
        dsl, normalization = _parse_normalize_validate_response(
            response,
            schema=schema,
            kind=request.kind,
            output_kind=config["outputKind"],
            input_ref=request.input_ref,
            input_payload=request.input_payload or {},
        )
        schema_repair = {"attempted": False, "applied": False, "errorCount": 0}
    except ProviderError as exc:
        if exc.code != "REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED" or not request.repair_on_schema_failure:
            raise
        repair_input = _build_schema_repair_input(
            original_input=request_input,
            failed_response=_response_output_text(response),
            errors=exc.errors,
            kind=request.kind,
            output_kind=config["outputKind"],
        )
        repair_response, repair_api_surface = _send_real_llm_demo_request(
            client,
            model=model,
            instructions=instructions,
            request_input=repair_input,
            text_format=text_format,
            timeout_seconds=request.timeout_seconds,
            max_output_tokens=request.max_output_tokens,
            api_surface=request.api_surface,
            kind=request.kind,
        )
        request_count = 2
        api_surface = f"{api_surface}+repair:{repair_api_surface}"
        dsl, normalization = _parse_normalize_validate_response(
            repair_response,
            schema=schema,
            kind=request.kind,
            output_kind=config["outputKind"],
            input_ref=request.input_ref,
            input_payload=request.input_payload or {},
        )
        normalization["schemaRepair"] = {
            "attempted": True,
            "applied": True,
            "errorCount": len(exc.errors),
            "errors": exc.errors,
            "firstResponseId": _response_id(response),
            "repairResponseId": _response_id(repair_response),
        }
        schema_repair = normalization["schemaRepair"]
        response = repair_response
    return {
        "demoId": "real_llm_demo_dsl_generation",
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
        "kind": request.kind,
        "outputKind": config["outputKind"],
        "inputRef": request.input_ref,
        "inputPayloadKeys": sorted(request.input_payload or {}),
        "promptId": config["promptId"],
        "promptVersion": PROMPT_VERSION,
        "promptPath": config["promptPath"],
        "requestSent": True,
        "requestCount": request_count,
        "singleRequestForKind": request_count == 1,
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
        "apiSurface": api_surface,
        "normalization": normalization,
        "schemaRepair": schema_repair,
        "schemaRepairAttempted": schema_repair["attempted"],
        "schemaRepairApplied": schema_repair["applied"],
        "dslId": dsl.get("metadata", {}).get("id"),
        "responseId": _response_id(response),
        "usage": _response_usage(response),
        "dsl": dsl,
        "traceId": trace_id,
    }


def normalize_real_llm_demo_grading_dsl(
    grading: dict[str, Any],
    *,
    exam: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Normalize an existing Grading DSL with the same deterministic real-demo rules."""

    schema = load_schema("grading", root)
    dsl, normalization = _normalize_generated_dsl(
        grading,
        schema,
        kind="grading",
        output_kind="Grading",
        input_ref=None,
        input_payload={"examDsl": exam} if exam is not None else {},
    )
    _validate_generated_dsl(dsl, schema, output_kind="Grading", kind="grading")
    return {
        "mode": "REAL_LLM_DEMO_DSL_NORMALIZATION",
        "kind": "grading",
        "outputKind": "Grading",
        "schemaValidated": True,
        "generatedStatus": dsl.get("status"),
        "reviewRequired": True,
        "autoPublishAllowed": False,
        "realPublish": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "normalization": normalization,
        "dslId": dsl.get("metadata", {}).get("id"),
        "dsl": dsl,
    }


def _create_real_llm_demo_response(
    client: Any,
    *,
    model: str,
    instructions: str,
    request_input: str,
    text_format: dict[str, Any],
    timeout_seconds: int,
    max_output_tokens: int,
    api_surface: str = API_SURFACE_AUTO,
) -> tuple[Any, str]:
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": request_input},
    ]
    attempts: list[dict[str, str]] = []
    if api_surface in {API_SURFACE_AUTO, API_SURFACE_RESPONSES}:
        try:
            return (
                client.responses.create(
                    model=model,
                    instructions=instructions,
                    input=request_input,
                    text={"format": text_format},
                    temperature=0,
                    max_output_tokens=max_output_tokens,
                    stream=False,
                    timeout=timeout_seconds,
                ),
                API_SURFACE_RESPONSES,
            )
        except Exception as exc:
            attempts.append(_api_surface_error(API_SURFACE_RESPONSES, exc))
            if api_surface == API_SURFACE_RESPONSES or not _should_fallback_to_chat_completions(exc):
                raise RealLlmApiSurfaceCallError(attempts) from exc
    if api_surface in {API_SURFACE_AUTO, API_SURFACE_CHAT_COMPLETIONS, API_SURFACE_RESPONSES}:
        try:
            return _create_chat_completions_response(
                client,
                model=model,
                messages=messages,
                text_format=text_format,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
            )
        except RealLlmApiSurfaceCallError as exc:
            attempts.extend(exc.attempts)
            raise RealLlmApiSurfaceCallError(attempts) from exc
        except Exception as exc:
            attempts.append(_api_surface_error(API_SURFACE_CHAT_COMPLETIONS, exc))
            raise RealLlmApiSurfaceCallError(attempts) from exc
    if api_surface == API_SURFACE_CHAT_JSON_OBJECT:
        return _create_chat_json_object_response(
            client,
            model=model,
            messages=messages,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            attempts=attempts,
        )
    raise ProviderError(
        "REAL_LLM_DEMO_DSL_INVALID_API_SURFACE",
        "真实 LLM Demo DSL 不支持该 API surface",
        [{"field": "apiSurface", "reason": api_surface}],
    )


class RealLlmApiSurfaceCallError(Exception):
    def __init__(self, attempts: list[dict[str, str]]) -> None:
        super().__init__("real llm api surface calls failed")
        self.attempts = attempts


def _api_surface_error(api_surface: str, exc: Exception) -> dict[str, str]:
    return {"apiSurface": api_surface, "errorType": exc.__class__.__name__}


def _create_chat_completions_response(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, str]],
    text_format: dict[str, Any],
    timeout_seconds: int,
    max_output_tokens: int,
) -> tuple[Any, str]:
    try:
        return (
            client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=_chat_completion_response_format(text_format),
                temperature=0,
                max_tokens=max_output_tokens,
                timeout=timeout_seconds,
            ),
            API_SURFACE_CHAT_COMPLETIONS,
        )
    except Exception as exc:
        if not _should_fallback_to_chat_json_object(exc):
            raise
        return _create_chat_json_object_response(
            client,
            model=model,
            messages=messages,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            attempts=[_api_surface_error(API_SURFACE_CHAT_COMPLETIONS, exc)],
        )


def _create_chat_json_object_response(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: int,
    max_output_tokens: int,
    attempts: list[dict[str, str]],
) -> tuple[Any, str]:
    try:
        return (
            client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=max_output_tokens,
                timeout=timeout_seconds,
            ),
            API_SURFACE_CHAT_JSON_OBJECT,
        )
    except Exception as exc:
        attempts.append(_api_surface_error(API_SURFACE_CHAT_JSON_OBJECT, exc))
        raise RealLlmApiSurfaceCallError(attempts) from exc


def _send_real_llm_demo_request(
    client: Any,
    *,
    model: str,
    instructions: str,
    request_input: str,
    text_format: dict[str, Any],
    timeout_seconds: int,
    max_output_tokens: int,
    api_surface: str,
    kind: str,
) -> tuple[Any, str]:
    try:
        return _create_real_llm_demo_response(
            client,
            model=model,
            instructions=instructions,
            request_input=request_input,
            text_format=text_format,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            api_surface=api_surface,
        )
    except RealLlmApiSurfaceCallError as exc:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_CALL_FAILED",
            "真实 LLM Demo DSL 调用失败",
            [
                {
                    "field": f"provider.openai.{kind}",
                    "reason": "API surface calls failed",
                    "apiSurface": ",".join(attempt["apiSurface"] for attempt in exc.attempts),
                    "attempts": json.dumps(exc.attempts, ensure_ascii=False),
                }
            ],
        ) from exc
    except Exception as exc:  # pragma: no cover - runtime integration only
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_CALL_FAILED",
            "真实 LLM Demo DSL 调用失败",
            [
                {
                    "field": f"provider.openai.{kind}",
                    "reason": exc.__class__.__name__,
                    "apiSurface": api_surface,
                }
            ],
        ) from exc


def _parse_normalize_validate_response(
    response: Any,
    *,
    schema: dict[str, Any],
    kind: str,
    output_kind: str,
    input_ref: str | None,
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_dsl = _parse_response_json(response)
    dsl, normalization = _normalize_generated_dsl(
        raw_dsl,
        schema,
        kind=kind,
        output_kind=output_kind,
        input_ref=input_ref,
        input_payload=input_payload,
    )
    _validate_generated_dsl(dsl, schema, output_kind=output_kind, kind=kind)
    return dsl, normalization


def _build_schema_repair_input(
    *,
    original_input: str,
    failed_response: str,
    errors: list[dict[str, str]],
    kind: str,
    output_kind: str,
) -> str:
    repair_payload = {
        "repairMode": "SCHEMA_VALIDATION_REPAIR_ONCE",
        "kind": kind,
        "outputKind": output_kind,
        "errors": errors,
        "requirements": [
            "Return exactly one complete DSL JSON object.",
            "Keep status WAITING_REVIEW.",
            "Do not include markdown fences or commentary.",
            "Fix every listed schema validation error.",
        ],
    }
    return (
        "The previous DSL JSON failed schema validation. Repair it once.\n"
        f"Repair JSON:\n{json.dumps(repair_payload, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Original request:\n{original_input}\n\n"
        f"Failed JSON response:\n{failed_response}"
    )


def _should_fallback_to_chat_completions(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    status_code = getattr(exc, "status_code", None)
    return (
        status_code in {400, 404, 405, 422}
        or "notfound" in name
        or "badrequest" in name
        or "apiconnection" in name
        or "api_connection" in name
    )


def _should_fallback_to_chat_json_object(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    status_code = getattr(exc, "status_code", None)
    return status_code in {400, 404, 422} or "badrequest" in name or "notfound" in name


def _chat_completion_response_format(text_format: dict[str, Any]) -> dict[str, Any]:
    json_schema = {key: value for key, value in text_format.items() if key != "type"}
    return {
        "type": "json_schema",
        "json_schema": json_schema,
    }


def build_real_llm_demo_dsl_error_context(
    exc: ProviderError,
    *,
    request: RealLlmDemoDslRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    input_path = _resolve_path(root, request.input_ref) if request.input_ref else None
    context = {
        "demoId": "real_llm_demo_dsl_generation",
        "phase": "Phase 2",
        "mode": MODE,
        "providerId": request.provider_id,
        "kind": request.kind,
        "sdkImportName": SDK_IMPORT_NAME,
        "secretEnv": SECRET_ENV,
        "secretPresent": SECRET_ENV in os.environ,
        "secretValueReturned": False,
        "modelPresent": bool(request.model or os.environ.get(MODEL_ENV)),
        "baseUrlEnv": BASE_URL_ENV,
        "baseUrlConfigured": bool(request.base_url or os.environ.get(BASE_URL_ENV)),
        "baseUrlSource": "argument" if request.base_url else ("env" if os.environ.get(BASE_URL_ENV) else None),
        "inputRef": request.input_ref,
        "inputExists": bool(input_path and input_path.exists()),
        "inputPayloadKeys": sorted(request.input_payload or {}),
        "requestSent": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "taskCreated": False,
        "errorCode": exc.code,
        "errors": exc.errors,
    }
    schema_failure_diagnostic = exc.details.get("schemaFailureDiagnostic")
    if isinstance(schema_failure_diagnostic, dict):
        context["schemaFailureDiagnostic"] = schema_failure_diagnostic
    return context


def build_real_llm_schema_failure_diagnostic(
    errors: list[dict[str, str]],
    *,
    document: dict[str, Any],
    kind: str,
    output_kind: str,
) -> dict[str, Any]:
    sanitized_errors = [
        {
            "field": str(error.get("field", "$")),
            "reason": str(error.get("reason", "schema validation failed")),
            "category": _classify_schema_failure(error),
            "sensitiveValueRedacted": _schema_path_has_sensitive_marker(str(error.get("field", "$"))),
        }
        for error in errors[:SCHEMA_FAILURE_ERROR_LIMIT]
    ]
    categories = _count_values(error["category"] for error in sanitized_errors)
    suspected_drift_types = sorted(categories)
    return {
        "version": SCHEMA_FAILURE_DIAGNOSTIC_VERSION,
        "kind": kind,
        "outputKind": output_kind,
        "errorTotal": len(errors),
        "reportedErrorLimit": SCHEMA_FAILURE_ERROR_LIMIT,
        "errors": sanitized_errors,
        "reasonSummary": _count_values(str(error.get("reason", "schema validation failed")) for error in errors),
        "topLevelFieldSummary": _schema_failure_top_level_summary(errors),
        "suspectedDriftTypes": suspected_drift_types,
        "recommendedActions": [
            SCHEMA_FAILURE_RECOMMENDATIONS.get(category, SCHEMA_FAILURE_RECOMMENDATIONS["unknown_schema_failure"])
            for category in suspected_drift_types
        ],
        "documentShape": _dsl_document_shape(document),
        "redaction": {
            "rawValuesIncluded": False,
            "sensitiveFieldValuesIncluded": False,
        },
    }


def _classify_schema_failure(error: dict[str, str]) -> str:
    reason = str(error.get("reason", "")).lower()
    if "required field missing" in reason:
        return "missing_required_field"
    if "expected string matching pattern" in reason:
        return "pattern_mismatch"
    if "expected length" in reason:
        return "string_length"
    if "expected object" in reason:
        return "expected_object"
    if "expected string" in reason:
        return "expected_string"
    if "expected array" in reason:
        return "expected_array"
    if "expected integer" in reason:
        return "expected_integer"
    if "expected one of" in reason:
        return "enum_mismatch"
    if "additional field" in reason:
        return "additional_field"
    if "expected at least" in reason:
        return "cardinality"
    if any(token in reason for token in ("expected >=", "expected <=", "expected >", "expected <")):
        return "numeric_range"
    if "schema in oneof" in reason or "schema in anyof" in reason or "allof" in reason:
        return "composition_mismatch"
    return "unknown_schema_failure"


def _schema_path_has_sensitive_marker(path: str) -> bool:
    normalized = path.lower()
    return any(marker in normalized for marker in SCHEMA_FAILURE_SENSITIVE_FIELD_MARKERS)


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _schema_failure_top_level_summary(errors: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for error in errors:
        top_level = _top_level_schema_path(str(error.get("field", "$")))
        counts[top_level] = counts.get(top_level, 0) + 1
    return dict(sorted(counts.items()))


def _top_level_schema_path(path: str) -> str:
    if not path.startswith("$."):
        return "$"
    first = path[2:].split(".", 1)[0].split("[", 1)[0]
    return f"$.{first}" if first else "$"


def _dsl_document_shape(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata")
    spec = document.get("spec")
    return {
        "topLevelKeys": sorted(str(key) for key in document),
        "metadataKeys": sorted(str(key) for key in metadata) if isinstance(metadata, dict) else [],
        "specKeys": sorted(str(key) for key in spec) if isinstance(spec, dict) else [],
        "counts": {
            "objectives": _list_count(spec, "objectives"),
            "materials": _list_count(spec, "materials"),
            "steps": _list_count(spec, "steps"),
            "questions": _list_count(spec, "questions"),
            "checks": _list_count(spec, "checks"),
            "assessmentPlan": _list_count(spec, "assessmentPlan"),
            "slides": _list_count(spec, "slides"),
        },
    }


def _list_count(parent: Any, key: str) -> int:
    if not isinstance(parent, dict):
        return 0
    value = parent.get(key)
    return len(value) if isinstance(value, list) else 0


def _validate_request(request: RealLlmDemoDslRequest, root: Path) -> dict[str, str]:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_UNSUPPORTED_PROVIDER",
            "真实 LLM Demo DSL 仅支持 openai provider",
            [{"field": "provider", "reason": f"unsupported provider: {request.provider_id}"}],
        )
    config = KIND_CONFIG.get(request.kind)
    if config is None:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_UNSUPPORTED_KIND",
            "真实 LLM Demo DSL 不支持该 kind",
            [{"field": "kind", "reason": request.kind}],
        )
    missing = [
        field
        for field, enabled in {
            "explicit_real_call_opt_in": request.explicit_real_call_opt_in,
            "confirm_waiting_review": request.confirm_waiting_review,
            "confirm_no_auto_publish": request.confirm_no_auto_publish,
        }.items()
        if not enabled
    ]
    if missing:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_CONFIRMATION_REQUIRED",
            "真实 LLM Demo DSL 需要显式确认调用边界",
            [{"field": field, "reason": "required"} for field in missing],
        )
    if request.timeout_seconds <= 0:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_INVALID_TIMEOUT",
            "timeout-seconds 必须大于 0",
            [{"field": "timeoutSeconds", "reason": "must be > 0"}],
        )
    if request.max_output_tokens <= 0:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_INVALID_MAX_OUTPUT_TOKENS",
            "max-output-tokens 必须大于 0",
            [{"field": "maxOutputTokens", "reason": "must be > 0"}],
        )
    if request.api_surface not in ALLOWED_API_SURFACES:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_INVALID_API_SURFACE",
            "真实 LLM Demo DSL 不支持该 API surface",
            [{"field": "apiSurface", "reason": f"must be one of {sorted(ALLOWED_API_SURFACES)}"}],
        )
    if request.input_ref:
        input_path = _resolve_path(root, request.input_ref)
        if not input_path.exists() and not request.input_payload:
            raise ProviderError(
                "REAL_LLM_DEMO_DSL_INPUT_NOT_FOUND",
                "真实 LLM Demo DSL 输入文件不存在",
                [{"field": "inputRef", "reason": str(input_path)}],
            )
    if not request.input_ref and not request.input_payload:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_INPUT_REQUIRED",
            "真实 LLM Demo DSL 需要 input_ref 或 input_payload",
            [{"field": "input", "reason": "missing"}],
        )
    return config


def _resolve_path(root: Path, value: str | None) -> Path:
    path = Path(value or "")
    if path.is_absolute():
        return path
    return root / path


def _read_optional_source(root: Path, value: str | None) -> str | None:
    if not value:
        return None
    path = _resolve_path(root, value)
    if not path.exists():
        return None
    size = path.stat().st_size
    if size > MAX_SOURCE_BYTES:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_INPUT_TOO_LARGE",
            "真实 LLM Demo DSL 输入文件过大",
            [{"field": "inputRef", "reason": f"{size} bytes > {MAX_SOURCE_BYTES} bytes"}],
        )
    return path.read_text(encoding="utf-8")


def _read_required_secret() -> str:
    value = os.environ.get(SECRET_ENV)
    if not value:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_SECRET_REQUIRED",
            "真实 LLM Demo DSL 需要通过环境变量提供 OPENAI_API_KEY",
            [{"field": SECRET_ENV, "reason": "missing or empty"}],
        )
    return value


def _resolve_model(request: RealLlmDemoDslRequest) -> str:
    model = request.model or os.environ.get(MODEL_ENV)
    if not model:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_MODEL_REQUIRED",
            "真实 LLM Demo DSL 需要通过 --model 或 OPENAI_MODEL 指定模型",
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
            "REAL_LLM_DEMO_DSL_SDK_IMPORT_FAILED",
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
            "REAL_LLM_DEMO_DSL_CLIENT_CREATE_FAILED",
            "真实 LLM Demo DSL 客户端创建失败",
            [{"field": "client", "reason": exc.__class__.__name__}],
        ) from exc


def _build_instructions(root: Path, config: dict[str, str]) -> str:
    return (root / config["promptPath"]).read_text(encoding="utf-8")


def _build_input(
    *,
    kind: str,
    output_kind: str,
    input_ref: str | None,
    source_text: str | None,
    input_payload: dict[str, Any] | None,
) -> str:
    payload = {
        "kind": kind,
        "outputKind": output_kind,
        "inputRef": input_ref,
        "context": input_payload or {},
    }
    source_block = f"\n\nSource material:\n{source_text}" if source_text else ""
    return (
        "Generate exactly one DSL JSON object for this AI training platform demo.\n"
        f"Request JSON:\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
        f"{source_block}"
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
    last_error: json.JSONDecodeError | None = None
    for candidate in _json_payload_text_candidates(text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(payload, list):
            selected = _select_response_list_candidate(payload)
            if selected is not None:
                return selected
            raise ProviderError(
                "REAL_LLM_DEMO_DSL_INVALID_JSON_ROOT",
                "真实 LLM Demo DSL 返回 JSON 根节点必须是对象",
                [{"field": "response.output_text", "reason": "root array did not contain a DSL object"}],
            )
        if not isinstance(payload, dict):
            raise ProviderError(
                "REAL_LLM_DEMO_DSL_INVALID_JSON_ROOT",
                "真实 LLM Demo DSL 返回 JSON 根节点必须是对象",
                [{"field": "response.output_text", "reason": "root must be object"}],
            )
        return payload
    exc = last_error or json.JSONDecodeError("no JSON object found", text, 0)
    raise ProviderError(
        "REAL_LLM_DEMO_DSL_INVALID_JSON",
        "真实 LLM Demo DSL 返回内容不是合法 JSON",
        [{"field": "response.output_text", "reason": exc.__class__.__name__}],
    ) from exc


def _json_payload_text_candidates(text: str) -> list[str]:
    stripped = text.strip()
    candidates = [stripped] if stripped else []
    for match in re.finditer(r"```(?:json|JSON)?\s*(.*?)```", stripped, flags=re.DOTALL):
        fenced = match.group(1).strip()
        if fenced:
            candidates.append(fenced)
    candidates.extend(_balanced_json_text_candidates(stripped))
    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _balanced_json_text_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for start, char in enumerate(text):
        if char not in "{[":
            continue
        end = _find_balanced_json_end(text, start)
        if end is not None:
            candidates.append(text[start : end + 1])
    return candidates


def _find_balanced_json_end(text: str, start: int) -> int | None:
    stack: list[str] = []
    in_string = False
    escaped = False
    pairs = {"{": "}", "[": "]"}
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char in pairs:
            stack.append(pairs[char])
            continue
        if char in {"}", "]"}:
            if not stack or char != stack[-1]:
                return None
            stack.pop()
            if not stack:
                return index
    return None


def _select_response_list_candidate(payload: list[Any]) -> dict[str, Any] | None:
    dict_items = [item for item in payload if isinstance(item, dict)]
    if len(dict_items) == 1:
        return dict_items[0]
    for item in dict_items:
        if _looks_like_dsl_payload(item):
            return item
    return None


def _looks_like_dsl_payload(value: Any) -> bool:
    return isinstance(value, dict) and (
        value.get("kind") in {"Lab", "Exam", "Grading", "PPT"}
        or "spec" in value
        or "metadata" in value
    )


def _normalize_generated_dsl(
    document: dict[str, Any],
    schema: dict[str, Any],
    *,
    kind: str,
    output_kind: str,
    input_ref: str | None,
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = json.loads(json.dumps(document, ensure_ascii=False))
    patches: list[str] = []
    unwrapped = _unwrap_dsl_response_envelope(normalized, kind=kind, output_kind=output_kind)
    if unwrapped is not None:
        normalized, unwrap_path = unwrapped
        patches.append(f"unwrap.response.{unwrap_path}")

    if normalized.get("version") != "1.0":
        normalized["version"] = "1.0"
        patches.append("set.version")
    if normalized.get("kind") != output_kind:
        normalized["kind"] = output_kind
        patches.append("set.kind")
    if normalized.get("status") != "WAITING_REVIEW":
        normalized["status"] = "WAITING_REVIEW"
        patches.append("set.status")

    _coerce_spec_container(normalized, kind=kind, patches=patches)
    metadata = _ensure_dict(normalized, "metadata", patches)
    spec = _ensure_dict(normalized, "spec", patches)
    _promote_kind_alias_fields(normalized, metadata=metadata, spec=spec, kind=kind, patches=patches)

    if kind == "lab":
        _normalize_lab_dsl(metadata, spec, input_ref=input_ref, input_payload=input_payload, patches=patches)
    elif kind == "exam":
        _normalize_exam_dsl(metadata, spec, input_payload=input_payload, patches=patches)
    elif kind == "grading":
        _normalize_grading_dsl(metadata, spec, input_payload=input_payload, patches=patches)
    elif kind == "ppt":
        _normalize_ppt_dsl(metadata, spec, input_payload=input_payload, patches=patches)

    _prune_additional_properties(normalized, schema, "$", patches)
    return normalized, {
        "applied": bool(patches),
        "patches": patches,
        "mode": "DETERMINISTIC_DSL_SHAPE_NORMALIZATION",
    }


def _unwrap_dsl_response_envelope(
    value: Any,
    *,
    kind: str,
    output_kind: str,
    path: str = "$",
    depth: int = 0,
) -> tuple[dict[str, Any], str] | None:
    if depth > 4 or not isinstance(value, dict):
        return None
    if _is_direct_dsl_document(value, output_kind):
        return None

    preferred_keys = _dsl_envelope_keys(kind, output_kind)
    for key in preferred_keys:
        if key not in value:
            continue
        candidate = _select_dsl_envelope_candidate(
            value[key],
            kind=kind,
            output_kind=output_kind,
            path=f"{path}.{key}",
            depth=depth + 1,
        )
        if candidate is not None:
            return candidate

    for key, child in value.items():
        if key in {"metadata", "spec"}:
            continue
        candidate = _select_dsl_envelope_candidate(
            child,
            kind=kind,
            output_kind=output_kind,
            path=f"{path}.{key}",
            depth=depth + 1,
        )
        if candidate is not None:
            return candidate
    return None


def _select_dsl_envelope_candidate(
    candidate: Any,
    *,
    kind: str,
    output_kind: str,
    path: str,
    depth: int,
) -> tuple[dict[str, Any], str] | None:
    if isinstance(candidate, dict):
        if _is_direct_dsl_document(candidate, output_kind):
            return json.loads(json.dumps(candidate, ensure_ascii=False)), path.lstrip("$.")
        return _unwrap_dsl_response_envelope(
            candidate,
            kind=kind,
            output_kind=output_kind,
            path=path,
            depth=depth,
        )
    if isinstance(candidate, list):
        for index, item in enumerate(candidate):
            selected = _select_dsl_envelope_candidate(
                item,
                kind=kind,
                output_kind=output_kind,
                path=f"{path}[{index}]",
                depth=depth + 1,
            )
            if selected is not None:
                return selected
    return None


def _is_direct_dsl_document(value: dict[str, Any], output_kind: str) -> bool:
    return (
        value.get("kind") == output_kind and ("metadata" in value or "spec" in value)
    ) or ("metadata" in value and "spec" in value)


def _dsl_envelope_keys(kind: str, output_kind: str) -> tuple[str, ...]:
    return (
        "dsl",
        "document",
        "data",
        "result",
        "output",
        "content",
        "payload",
        "json",
        kind,
        output_kind,
        f"{kind}Dsl",
        f"{output_kind}Dsl",
        f"{kind}_dsl",
        f"{output_kind.lower()}_dsl",
    )


def _ensure_dict(parent: dict[str, Any], key: str, patches: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        value = {}
        parent[key] = value
        patches.append(f"set.{key}")
    return value


def _coerce_spec_container(document: dict[str, Any], *, kind: str, patches: list[str]) -> None:
    spec = document.get("spec")
    list_field_by_kind = {
        "lab": "steps",
        "exam": "questions",
        "grading": "checks",
        "ppt": "slides",
    }
    if isinstance(spec, list):
        field = list_field_by_kind.get(kind)
        if field:
            document["spec"] = {field: spec}
            patches.append(f"set.spec.from_list.{field}")
        return
    if isinstance(spec, dict):
        return

    promoted: dict[str, Any] = {}
    for canonical, aliases in _kind_spec_alias_map(kind).items():
        value, _ = _first_alias_value(document, (canonical, *aliases))
        if _has_meaningful_value(value):
            promoted[canonical] = value
    if promoted:
        document["spec"] = promoted
        patches.append("set.spec.from_top_level_aliases")


def _promote_kind_alias_fields(
    document: dict[str, Any],
    *,
    metadata: dict[str, Any],
    spec: dict[str, Any],
    kind: str,
    patches: list[str],
) -> None:
    for canonical, aliases in _kind_metadata_alias_map(kind).items():
        _promote_alias_field(metadata, canonical, aliases, f"metadata.{canonical}", patches, sources=[metadata, document])
    for canonical, aliases in _kind_spec_alias_map(kind).items():
        _promote_alias_field(spec, canonical, aliases, f"spec.{canonical}", patches, sources=[spec, document])


def _kind_metadata_alias_map(kind: str) -> dict[str, tuple[str, ...]]:
    common = {
        "id": ("dslId", "uid", "key"),
        "title": ("name", "heading"),
    }
    if kind == "lab":
        return {
            **common,
            "category": ("subject", "domain", "topic"),
            "difficulty": ("level", "difficultyLevel"),
            "durationMinutes": ("duration", "duration_minutes", "estimatedMinutes", "estimated_minutes"),
            "tags": ("techTags", "keywords", "labels"),
        }
    if kind == "exam":
        return {
            **common,
            "sourceLabId": ("labId", "source_lab_id", "sourceLab", "labRef"),
            "difficulty": ("level", "difficultyLevel"),
        }
    if kind == "grading":
        return {
            **common,
            "sourceExamId": ("examId", "source_exam_id", "sourceExam", "examRef"),
        }
    if kind == "ppt":
        return {
            **common,
            "audience": ("targetAudience", "targetUsers", "learners"),
            "durationMinutes": ("duration", "duration_minutes", "estimatedMinutes", "estimated_minutes"),
        }
    return common


def _kind_spec_alias_map(kind: str) -> dict[str, tuple[str, ...]]:
    if kind == "lab":
        return {
            "objectives": ("learningObjectives", "learning_objectives", "goals", "outcomes"),
            "targetUsers": ("audience", "targetAudience", "learners", "users"),
            "environment": ("runtime", "runtimeEnvironment", "environmentConfig", "labEnvironment"),
            "materials": ("references", "sourceMaterials", "resourcesList", "documents"),
            "steps": ("tasks", "activities", "procedure", "instructions"),
            "grading": ("gradingRef", "gradingReference", "assessment"),
        }
    if kind == "exam":
        return {
            "questionType": ("type", "question_type", "format", "mode"),
            "totalScore": ("score", "total", "points", "total_score", "totalPoints", "total_points"),
            "questions": ("questions", "items", "problems", "tasks", "questionList", "question_list"),
        }
    if kind == "grading":
        return {
            "totalScore": ("score", "total", "points", "total_score", "totalPoints", "total_points"),
            "timeoutSeconds": ("timeout", "timeout_seconds", "timeLimitSeconds", "time_limit_seconds"),
            "checks": ("rules", "gradingRules", "grading_rules", "testCases", "test_cases", "tests"),
            "assessmentPlan": ("assessment", "plan", "reviewPlan", "review_plan"),
        }
    if kind == "ppt":
        return {
            "theme": ("style", "themeConfig", "theme_config"),
            "slides": ("pages", "slidePlan", "slide_plan", "outline", "sections"),
        }
    return {}


def _promote_alias_field(
    target: dict[str, Any],
    canonical: str,
    aliases: tuple[str, ...],
    path: str,
    patches: list[str],
    *,
    sources: list[dict[str, Any]],
) -> None:
    existing = target.get(canonical)
    if _has_meaningful_value(existing):
        return
    value, alias = _first_alias_value_from_sources(sources, aliases)
    if not _has_meaningful_value(value):
        return
    target[canonical] = value
    patches.append(f"set.{path}.from.{alias}")


def _first_alias_value_from_sources(sources: list[dict[str, Any]], aliases: tuple[str, ...]) -> tuple[Any, str | None]:
    for source in sources:
        value, alias = _first_alias_value(source, aliases)
        if _has_meaningful_value(value):
            return value, alias
    return None, None


def _first_alias_value(source: dict[str, Any], aliases: tuple[str, ...]) -> tuple[Any, str | None]:
    for alias in aliases:
        if alias in source and _has_meaningful_value(source.get(alias)):
            return source.get(alias), alias
    return None, None


def _has_meaningful_value(value: Any) -> bool:
    return value not in (None, "", [], {})


def _normalize_lab_dsl(
    metadata: dict[str, Any],
    spec: dict[str, Any],
    *,
    input_ref: str | None,
    input_payload: dict[str, Any],
    patches: list[str],
) -> None:
    context = input_payload.get("labGenerationContext", {})
    if not isinstance(context, dict):
        context = {}
    defaults = {
        "id": "lab_real_llm_demo",
        "title": "真实 LLM Demo 实验",
        "category": "ai-platform",
        "difficulty": str(context.get("difficulty") or "beginner"),
        "durationMinutes": int(context.get("durationMinutes") or 45),
        "tags": context.get("techTags") if isinstance(context.get("techTags"), list) else ["LLM"],
    }
    _fill_defaults(metadata, defaults, "metadata", patches)
    _normalize_lab_metadata(metadata, patches)

    objectives = _normalize_string_list(spec.get("objectives"))
    if not objectives:
        spec["objectives"] = ["完成真实 LLM 生成内容的人工审核演示"]
        patches.append("set.spec.objectives")
    elif objectives != spec.get("objectives"):
        spec["objectives"] = objectives
        patches.append("set.spec.objectives")
    target_users = context.get("targetUsers")
    target_user_defaults = _normalize_string_list(target_users) or ["平台开发者"]
    target_users_value = _normalize_string_list(spec.get("targetUsers"))
    if not target_users_value:
        spec["targetUsers"] = target_user_defaults
        patches.append("set.spec.targetUsers")
    elif target_users_value != spec.get("targetUsers"):
        spec["targetUsers"] = target_users_value
        patches.append("set.spec.targetUsers")
    environment = spec.get("environment")
    if not isinstance(environment, dict):
        environment = {}
        spec["environment"] = environment
        patches.append("set.spec.environment")
    _fill_defaults(
        environment,
        {"type": "notebook", "image": "python:3.11"},
        "spec.environment",
        patches,
    )
    _normalize_lab_environment_resources(environment, patches)
    _normalize_lab_materials(spec, input_ref=input_ref, patches=patches)
    _normalize_lab_steps(spec, patches)
    _normalize_lab_grading_ref(spec, patches)


def _normalize_lab_metadata(metadata: dict[str, Any], patches: list[str]) -> None:
    for key in ("id", "title", "category"):
        if key in metadata and metadata.get(key) is not None and not isinstance(metadata.get(key), str):
            metadata[key] = _stringify_llm_scalar(metadata[key])
            patches.append(f"set.metadata.{key}")
    difficulty = _normalize_difficulty(metadata.get("difficulty"))
    if metadata.get("difficulty") != difficulty:
        metadata["difficulty"] = difficulty
        patches.append("set.metadata.difficulty")
    duration = _coerce_positive_int(metadata.get("durationMinutes"))
    if duration is None:
        metadata["durationMinutes"] = 45
        patches.append("set.metadata.durationMinutes")
    elif metadata.get("durationMinutes") != duration:
        metadata["durationMinutes"] = duration
        patches.append("set.metadata.durationMinutes")
    tags = _normalize_string_list(metadata.get("tags"))
    if not tags:
        metadata["tags"] = ["LLM"]
        patches.append("set.metadata.tags")
    elif tags != metadata.get("tags"):
        metadata["tags"] = tags
        patches.append("set.metadata.tags")


def _normalize_difficulty(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in DIFFICULTY_LEVELS:
        return text
    return DIFFICULTY_ALIASES.get(text, "beginner")


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        chunks = [value]
        for delimiter in ("，", ",", "；", ";", "\n"):
            chunks = [part for chunk in chunks for part in chunk.split(delimiter)]
        return [part.strip() for part in chunks if part.strip()]
    if isinstance(value, list):
        normalized = [_stringify_llm_scalar(item).strip() for item in value if item is not None]
        return [item for item in normalized if item]
    text = _stringify_llm_scalar(value).strip()
    return [text] if text else []


def _normalize_lab_environment_resources(environment: dict[str, Any], patches: list[str]) -> None:
    resources = environment.get("resources")
    default_resources = {"cpu": 2, "memoryGb": 4}
    if resources in (None, "", []):
        return
    if not isinstance(resources, dict):
        environment["resources"] = _parse_lab_resource_text(resources) or default_resources
        patches.append("set.spec.environment.resources")
        return
    normalized: dict[str, int] = {}
    cpu_value = _first_resource_alias_value(resources, ("cpu", "cpus", "cpuCores", "cores", "vcpu", "vcpus"))
    memory_value = _first_resource_alias_value(
        resources,
        ("memoryGb", "memoryGB", "memory_gb", "memory", "memoryGib", "ramGb", "ram", "memGb", "mem"),
    )
    value_by_key = {"cpu": cpu_value, "memoryGb": memory_value}
    for key, default_value in default_resources.items():
        value = value_by_key[key]
        number = _coerce_positive_int(value)
        if number is None:
            normalized[key] = default_value
            patches.append(f"set.spec.environment.resources.{key}")
        else:
            normalized[key] = number
            if resources.get(key) != number:
                patches.append(f"set.spec.environment.resources.{key}")
    if normalized != resources:
        environment["resources"] = normalized


def _first_resource_alias_value(resources: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in resources and resources.get(alias) not in (None, "", []):
            return resources.get(alias)
    return None


def _parse_lab_resource_text(value: Any) -> dict[str, int] | None:
    text = _stringify_llm_scalar(value).lower()
    if not text.strip():
        return None

    cpu = _first_int_before_or_after_keywords(text, ("cpu", "core", "cores", "vcpu", "vcpus", "核"))
    memory = _first_int_before_or_after_keywords(text, ("memory", "mem", "ram", "gb", "gib", "内存"))
    if cpu is None and memory is None:
        return None
    return {
        "cpu": cpu if cpu is not None else 2,
        "memoryGb": memory if memory is not None else 4,
    }


def _first_int_before_or_after_keywords(text: str, keywords: tuple[str, ...]) -> int | None:
    keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
    before = re.search(rf"(\d+)\s*(?:{keyword_pattern})\b", text)
    if before:
        return int(before.group(1))
    after = re.search(rf"(?:{keyword_pattern})\s*(\d+)", text)
    if after:
        return int(after.group(1))
    return None


def _normalize_lab_materials(spec: dict[str, Any], *, input_ref: str | None, patches: list[str]) -> None:
    materials = spec.get("materials")
    default_material = {"type": "markdown", "path": input_ref or "examples/input/demo-source.md"}
    if isinstance(materials, dict):
        spec["materials"] = _lab_material_object_to_list(materials, default_material=default_material)
        materials = spec["materials"]
        patches.append("set.spec.materials.from_object")
    if not isinstance(materials, list):
        if input_ref:
            spec["materials"] = [default_material]
            patches.append("set.spec.materials")
        return
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(materials):
        path = f"spec.materials[{index}]"
        if isinstance(item, dict):
            material_type = _first_non_empty_string(item, ("type", "kind", "format", "mediaType")) or default_material["type"]
            material_path = _first_non_empty_string(
                item,
                ("path", "file", "filename", "source", "sourcePath", "url", "title", "name", "description"),
            ) or input_ref
            if material_path is None:
                material_path = f"generated-material-{index + 1}.md"
            normalized_item = {"type": material_type.strip(), "path": material_path.strip()}
            if normalized_item != item:
                patches.append(f"set.{path}")
            normalized.append(normalized_item)
            continue
        text = str(item).strip()
        normalized.append({"type": "markdown", "path": text or default_material["path"]})
        patches.append(f"set.{path}")
    if not normalized and input_ref:
        normalized = [default_material]
        patches.append("set.spec.materials.default")
    if normalized != materials:
        spec["materials"] = normalized


def _lab_material_object_to_list(materials: dict[str, Any], *, default_material: dict[str, str]) -> list[dict[str, str]]:
    if _looks_like_single_lab_material(materials):
        return [_lab_material_to_schema_item(materials, default_material=default_material, index=1)]

    normalized: list[dict[str, str]] = []
    for index, (key, value) in enumerate(materials.items(), start=1):
        fallback = {
            "type": default_material["type"],
            "path": str(key).strip() or default_material["path"],
        }
        if isinstance(value, dict):
            normalized.append(_lab_material_to_schema_item(value, default_material=fallback, index=index))
            continue
        text = _stringify_llm_scalar(value).strip()
        normalized.append({"type": "markdown", "path": text or fallback["path"]})
    return normalized


def _looks_like_single_lab_material(value: dict[str, Any]) -> bool:
    material_keys = {
        "type",
        "kind",
        "format",
        "mediaType",
        "path",
        "file",
        "filename",
        "source",
        "sourcePath",
        "url",
        "title",
        "name",
        "description",
    }
    anchor_keys = {
        "type",
        "kind",
        "format",
        "mediaType",
        "path",
        "file",
        "filename",
        "source",
        "sourcePath",
        "url",
    }
    return any(key in value for key in anchor_keys) and all(key in material_keys for key in value)


def _lab_material_to_schema_item(
    item: dict[str, Any],
    *,
    default_material: dict[str, str],
    index: int,
) -> dict[str, str]:
    material_type = _first_non_empty_string(item, ("type", "kind", "format", "mediaType")) or default_material["type"]
    material_path = _first_non_empty_string(
        item,
        ("path", "file", "filename", "source", "sourcePath", "url", "title", "name", "description"),
    ) or default_material.get("path") or f"generated-material-{index}.md"
    return {"type": material_type.strip(), "path": material_path.strip()}


def _first_non_empty_string(source: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        text = _stringify_llm_scalar(value).strip()
        if text:
            return text
    return None


def _normalize_lab_steps(spec: dict[str, Any], patches: list[str]) -> None:
    steps = spec.get("steps")
    if isinstance(steps, dict):
        spec["steps"] = _lab_step_map_to_list(steps)
        steps = spec["steps"]
        patches.append("set.spec.steps.from_object")
    if not isinstance(steps, list) or not steps:
        spec["steps"] = [
            {
                "id": "step_1",
                "title": "审核生成内容",
                "instruction": "检查 AI 生成 DSL 是否符合课程目标并保持 WAITING_REVIEW。",
            }
        ]
        patches.append("set.spec.steps")
        return
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            steps[index - 1] = {
                "id": f"step_{index}",
                "title": f"步骤 {index}",
                "instruction": str(step),
            }
            patches.append(f"set.spec.steps[{index - 1}]")
            continue
        _promote_lab_step_alias_fields(step, index=index, patches=patches)
        _fill_defaults(
            step,
            {
                "id": f"step_{index}",
                "title": f"步骤 {index}",
                "instruction": "完成本步骤并记录结果。",
            },
            f"spec.steps[{index - 1}]",
            patches,
        )
        _normalize_lab_step_fields(step, index=index, patches=patches)


def _lab_step_map_to_list(steps: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, (key, value) in enumerate(steps.items(), start=1):
        step_id = str(key).strip() or f"step_{index}"
        if isinstance(value, dict):
            normalized.append(_lab_step_to_schema_item(value, step_id=step_id, index=index))
            continue
        normalized.append(
            {
                "id": step_id,
                "title": f"步骤 {index}",
                "instruction": _stringify_llm_scalar(value),
            }
        )
    return normalized


def _lab_step_to_schema_item(step: dict[str, Any], *, step_id: str, index: int) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "id": _first_non_empty_string(step, ("id", "stepId", "key", "ref")) or step_id,
        "title": _first_non_empty_string(step, ("title", "name", "heading")) or f"步骤 {index}",
        "instruction": _first_non_empty_string(
            step,
            ("instruction", "description", "task", "content", "text", "body"),
        )
        or "完成本步骤并记录结果。",
    }
    commands = _first_present_value(step, ("commands", "command", "shell", "shellCommands"))
    if commands is not None:
        normalized["commands"] = commands
    expected_result = _first_non_empty_string(step, ("expectedResult", "expected", "output", "result"))
    if expected_result:
        normalized["expectedResult"] = expected_result
    return normalized


def _first_present_value(source: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in source and source.get(key) not in (None, "", []):
            return source.get(key)
    return None


def _normalize_lab_step_fields(step: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.steps[{index - 1}]"
    for key in ("id", "title", "instruction", "expectedResult"):
        if key in step and step.get(key) is not None and not isinstance(step.get(key), str):
            step[key] = _stringify_llm_scalar(step[key])
            patches.append(f"set.{path}.{key}")
    commands = step.get("commands")
    if commands is None:
        return
    normalized = _normalize_string_list(commands)
    if normalized:
        if normalized != commands:
            step["commands"] = normalized
            patches.append(f"set.{path}.commands")
        return
    del step["commands"]
    patches.append(f"remove.{path}.commands")


def _promote_lab_step_alias_fields(step: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.steps[{index - 1}]"
    for canonical, aliases in LAB_STEP_FIELD_ALIASES.items():
        if _llm_value_has_content(step.get(canonical)):
            continue
        for alias in aliases:
            if _llm_value_has_content(step.get(alias)):
                step[canonical] = step[alias]
                patches.append(f"set.{path}.{canonical}.from.{alias}")
                break


def _normalize_lab_grading_ref(spec: dict[str, Any], patches: list[str]) -> None:
    grading = spec.get("grading")
    if grading in (None, "", []):
        return
    if isinstance(grading, dict):
        ref = _first_non_empty_string(grading, ("ref", "id", "gradingRef", "gradingReference", "name", "value", "text"))
        if ref:
            normalized = {"ref": ref}
            if normalized != grading:
                spec["grading"] = normalized
                patches.append("set.spec.grading")
            return
        del spec["grading"]
        patches.append("remove.spec.grading")
        return
    ref = _stringify_llm_scalar(grading).strip()
    if ref:
        spec["grading"] = {"ref": ref}
        patches.append("set.spec.grading")
        return
    del spec["grading"]
    patches.append("remove.spec.grading")


def _normalize_exam_dsl(
    metadata: dict[str, Any],
    spec: dict[str, Any],
    *,
    input_payload: dict[str, Any],
    patches: list[str],
) -> None:
    lab_dsl = input_payload.get("labDsl", {})
    lab_metadata = lab_dsl.get("metadata", {}) if isinstance(lab_dsl, dict) else {}
    _fill_defaults(
        metadata,
        {
            "id": "exam_real_llm_demo",
            "title": "真实 LLM Demo 试题",
            "sourceLabId": lab_metadata.get("id") if isinstance(lab_metadata, dict) else "lab_real_llm_demo",
            "difficulty": metadata.get("difficulty") or "beginner",
        },
        "metadata",
        patches,
    )
    _normalize_exam_metadata(metadata, patches)
    normalized_question_type = _normalize_exam_question_type(spec.get("questionType"))
    if spec.get("questionType") != normalized_question_type:
        spec["questionType"] = normalized_question_type
        patches.append("set.spec.questionType")
    total_score = _coerce_positive_int(spec.get("totalScore"))
    if total_score is None:
        spec["totalScore"] = 100
        patches.append("set.spec.totalScore")
    elif spec.get("totalScore") != total_score:
        spec["totalScore"] = total_score
        patches.append("set.spec.totalScore")
    questions = spec.get("questions")
    if isinstance(questions, dict):
        spec["questions"] = _exam_question_map_to_list(questions)
        questions = spec["questions"]
        patches.append("set.spec.questions.from_object")
    if not isinstance(questions, list) or not questions:
        default_score = spec.get("totalScore")
        if not isinstance(default_score, int) or default_score <= 0:
            default_score = 100
        spec["questions"] = [
            {
                "id": "q1",
                "title": "审核状态确认",
                "stem": "请说明生成内容为什么必须进入 WAITING_REVIEW。",
                "score": default_score,
                "gradingRef": "check_waiting_review",
            }
        ]
        patches.append("set.spec.questions")
        return
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            questions[index - 1] = {
                "id": f"q{index}",
                "title": f"题目 {index}",
                "stem": str(question),
                "score": 1,
                "gradingRef": f"check_q{index}",
            }
            patches.append(f"set.spec.questions[{index - 1}]")
            continue
        _promote_exam_question_alias_fields(question, index=index, patches=patches)
        _fill_defaults(
            question,
            {
                "id": f"q{index}",
                "title": f"题目 {index}",
                "stem": "请完成题目要求。",
                "score": max(1, int(spec.get("totalScore", 100) / max(1, len(questions)))),
                "gradingRef": f"check_q{index}",
            },
            f"spec.questions[{index - 1}]",
            patches,
        )
        _normalize_exam_question_string_fields(question, index=index, patches=patches)
        _normalize_exam_question_score(question, index=index, patches=patches)
        _normalize_exam_question_grading_ref(question, index=index, patches=patches)
    _normalize_exam_question_scores(spec, patches)


def _exam_question_map_to_list(questions: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, (key, value) in enumerate(questions.items(), start=1):
        if isinstance(value, dict):
            question = json.loads(json.dumps(value, ensure_ascii=False))
            question.setdefault("id", str(key))
        else:
            question = {
                "id": str(key) if key else f"q{index}",
                "title": f"题目 {index}",
                "stem": _stringify_llm_scalar(value),
            }
        normalized.append(question)
    return normalized


def _normalize_exam_metadata(metadata: dict[str, Any], patches: list[str]) -> None:
    for key in ("id", "title", "sourceLabId"):
        if key in metadata and metadata.get(key) is not None and not isinstance(metadata.get(key), str):
            metadata[key] = _stringify_llm_scalar(metadata[key])
            patches.append(f"set.metadata.{key}")
    difficulty = _normalize_difficulty(metadata.get("difficulty"))
    if metadata.get("difficulty") != difficulty:
        metadata["difficulty"] = difficulty
        patches.append("set.metadata.difficulty")


def _normalize_exam_question_type(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "_")
    if text in EXAM_QUESTION_TYPES:
        return text
    return EXAM_QUESTION_TYPE_ALIASES.get(text, "coding_task")


def _promote_exam_question_alias_fields(question: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.questions[{index - 1}]"
    for canonical, aliases in EXAM_QUESTION_FIELD_ALIASES.items():
        if _llm_value_has_content(question.get(canonical)):
            continue
        for alias in aliases:
            if _llm_value_has_content(question.get(alias)):
                question[canonical] = question[alias]
                patches.append(f"set.{path}.{canonical}.from.{alias}")
                break


def _llm_value_has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _normalize_exam_question_string_fields(question: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.questions[{index - 1}]"
    for key in ("id", "title", "stem", "blankCode", "answer", "gradingRef"):
        if key not in question or question.get(key) is None:
            continue
        if isinstance(question.get(key), str):
            if not question[key].strip() and key in {"id", "title", "stem", "gradingRef"}:
                question[key] = f"q{index}" if key in {"id", "gradingRef"} else f"题目 {index}"
                patches.append(f"set.{path}.{key}")
            continue
        question[key] = _stringify_llm_scalar(question[key])
        patches.append(f"set.{path}.{key}")


def _normalize_exam_question_score(question: dict[str, Any], *, index: int, patches: list[str]) -> None:
    score = _coerce_positive_int(question.get("score"))
    if score is None:
        question["score"] = 1
        patches.append(f"set.spec.questions[{index - 1}].score")
    elif question.get("score") != score:
        question["score"] = score
        patches.append(f"set.spec.questions[{index - 1}].score")


def _normalize_exam_question_grading_ref(question: dict[str, Any], *, index: int, patches: list[str]) -> None:
    grading_ref = question.get("gradingRef")
    question_id = question.get("id")
    fallback_ref = str(question_id).strip() if _is_grading_ref_id_like(question_id) else f"check_q{index}"
    if _is_grading_ref_id_like(grading_ref) and not _is_unstable_generic_grading_ref(grading_ref):
        return
    answer = question.get("answer")
    if (
        isinstance(grading_ref, str)
        and grading_ref.strip()
        and not _is_unstable_generic_grading_ref(grading_ref)
        and not (isinstance(answer, str) and answer.strip())
    ):
        question["answer"] = grading_ref.strip()
        patches.append(f"set.spec.questions[{index - 1}].answer.fromUnstableGradingRef")
    if question.get("gradingRef") != fallback_ref:
        question["gradingRef"] = fallback_ref
        patches.append(f"set.spec.questions[{index - 1}].gradingRef.fromUnstableValue")


def _normalize_exam_question_scores(spec: dict[str, Any], patches: list[str]) -> None:
    questions = [question for question in spec.get("questions", []) if isinstance(question, dict)]
    if not questions:
        return
    total_score = spec.get("totalScore")
    if not isinstance(total_score, int) or total_score <= 0:
        return
    if total_score < len(questions):
        spec["totalScore"] = len(questions)
        total_score = spec["totalScore"]
        patches.append("set.spec.totalScore.minimumForQuestions")
    current_sum = sum(question.get("score", 0) for question in questions if isinstance(question.get("score"), int))
    if current_sum == total_score and all(isinstance(question.get("score"), int) and question.get("score", 0) > 0 for question in questions):
        return
    desired_scores = _distribute_total_score(total_score, len(questions))
    for index, (question, desired_score) in enumerate(zip(questions, desired_scores), start=1):
        if question.get("score") != desired_score:
            question["score"] = desired_score
            patches.append(f"set.spec.questions[{index - 1}].score")


def _stringify_llm_scalar(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(_stringify_llm_scalar(item) for item in value if item is not None)
    if isinstance(value, dict):
        for key in ("id", "ref", "text", "value", "name", "answer", "gradingRef", "description"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _normalize_grading_dsl(
    metadata: dict[str, Any],
    spec: dict[str, Any],
    *,
    input_payload: dict[str, Any],
    patches: list[str],
) -> None:
    exam_dsl = input_payload.get("examDsl", {})
    exam_metadata = exam_dsl.get("metadata", {}) if isinstance(exam_dsl, dict) else {}
    _fill_defaults(
        metadata,
        {
            "id": "grading_real_llm_demo",
            "title": "真实 LLM Demo 评分",
            "sourceExamId": exam_metadata.get("id") if isinstance(exam_metadata, dict) else "exam_real_llm_demo",
        },
        "metadata",
        patches,
    )
    _normalize_grading_metadata(metadata, patches)
    total_score = _coerce_positive_int(spec.get("totalScore"))
    if total_score is None:
        spec["totalScore"] = 100
        patches.append("set.spec.totalScore")
    elif spec.get("totalScore") != total_score:
        spec["totalScore"] = total_score
        patches.append("set.spec.totalScore")
    timeout_seconds = _coerce_positive_int(spec.get("timeoutSeconds"))
    if timeout_seconds is None:
        spec["timeoutSeconds"] = 30
        patches.append("set.spec.timeoutSeconds")
    elif spec.get("timeoutSeconds") != timeout_seconds:
        spec["timeoutSeconds"] = timeout_seconds
        patches.append("set.spec.timeoutSeconds")
    checks = spec.get("checks")
    if isinstance(checks, dict):
        spec["checks"] = _grading_check_map_to_list(checks)
        checks = spec["checks"]
        patches.append("set.spec.checks.from_object")
    if not isinstance(checks, list) or not checks:
        spec["checks"] = [
            {
                "id": "check_waiting_review",
                "type": "stdout_contains",
                "command": "python main.py",
                "expected": ["WAITING_REVIEW"],
                "score": spec["totalScore"],
            }
        ]
        patches.append("set.spec.checks")
    _normalize_grading_checks(spec, input_payload=input_payload, patches=patches)
    _normalize_grading_scores(spec, input_payload=input_payload, patches=patches)
    _normalize_assessment_plan(spec, patches)


def _grading_check_map_to_list(checks: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, (key, value) in enumerate(checks.items(), start=1):
        check_id = str(key).strip() or f"check_{index}"
        if isinstance(value, dict):
            normalized.append(_grading_check_to_schema_item(value, check_id=check_id))
            continue
        text = _stringify_llm_scalar(value).strip()
        check: dict[str, Any] = {"id": check_id, "type": "stdout_contains", "score": 1}
        if _normalize_grading_check_type(text) != "stdout_contains":
            check["type"] = text
        elif text:
            check["expected"] = [text]
        normalized.append(check)
    return normalized


def _grading_check_to_schema_item(check: dict[str, Any], *, check_id: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "id": _first_non_empty_string(check, ("id", "checkId", "key", "ref", "name")) or check_id,
        "type": _first_non_empty_string(check, ("type", "kind", "checkType", "runner")) or "stdout_contains",
        "score": _first_present_value(check, ("score", "points", "weight")) or 1,
    }
    for target_key, aliases in (
        ("path", ("path", "file", "filePath", "filename")),
        ("command", ("command", "cmd", "run", "shell")),
        ("notebookPath", ("notebookPath", "notebook", "notebookFile")),
        ("cellIndex", ("cellIndex", "cell", "cellNumber")),
        ("jsonPath", ("jsonPath", "json_path", "fieldPath")),
        ("expectedValue", ("expectedValue", "expected_value", "value")),
        ("expected", ("expected", "expectedOutput", "expectedTokens", "contains")),
    ):
        value = _first_present_value(check, aliases)
        if value is not None:
            normalized[target_key] = [value] if target_key == "expected" and not isinstance(value, list) else value
    return normalized


def _normalize_grading_metadata(metadata: dict[str, Any], patches: list[str]) -> None:
    for key in ("id", "title", "sourceExamId"):
        if key in metadata and metadata.get(key) is not None and not isinstance(metadata.get(key), str):
            metadata[key] = _stringify_llm_scalar(metadata[key])
            patches.append(f"set.metadata.{key}")


def _normalize_grading_checks(spec: dict[str, Any], *, input_payload: dict[str, Any], patches: list[str]) -> None:
    checks = spec.get("checks", [])
    questions = _exam_questions(input_payload)
    for index, check in enumerate(checks, start=1):
        path = f"spec.checks[{index - 1}]"
        if not isinstance(check, dict):
            checks[index - 1] = {
                "id": f"check_{index}",
                "type": "stdout_contains",
                "command": "python main.py",
                "expected": ["WAITING_REVIEW"],
                "score": 1,
            }
            patches.append(f"set.{path}")
            continue
        _promote_grading_check_alias_fields(check, index=index, patches=patches)
        _fill_defaults(
            check,
            {
                "id": f"check_{index}",
                "type": "stdout_contains",
                "score": 1,
            },
            path,
            patches,
        )
        normalized_type = _normalize_grading_check_type(check.get("type"))
        if check.get("type") != normalized_type:
            check["type"] = normalized_type
            patches.append(f"set.{path}.type")
        _normalize_grading_check_string_fields(check, path=path, patches=patches)
        _normalize_grading_check_required_fields(check, index=index, questions=questions, path=path, patches=patches)
    _normalize_grading_check_ids_for_exam_refs(checks, questions=questions, patches=patches)
    _ensure_grading_checks_cover_exam_refs(spec, questions=questions, patches=patches)


def _normalize_grading_check_ids_for_exam_refs(
    checks: list[Any],
    *,
    questions: list[dict[str, Any]],
    patches: list[str],
) -> None:
    if not questions or not checks:
        return
    desired_ids: list[str | None] = []
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            desired_ids.append(None)
            continue
        question = _question_for_check_id_match(check, questions)
        if not question and len(checks) == len(questions) and 0 <= index - 1 < len(questions):
            question = questions[index - 1]
        grading_ref = question.get("gradingRef") if isinstance(question, dict) else None
        if not _is_grading_ref_id_like(grading_ref):
            desired_ids.append(None)
            continue
        desired_ids.append(str(grading_ref).strip())

    non_empty_desired_ids = [item for item in desired_ids if item]
    if len(non_empty_desired_ids) != len(set(non_empty_desired_ids)):
        return

    for index, (check, desired_id) in enumerate(zip(checks, desired_ids), start=1):
        if not isinstance(check, dict) or not desired_id:
            continue
        if check.get("id") != desired_id:
            check["id"] = desired_id
            patches.append(f"set.spec.checks[{index - 1}].id.fromExamGradingRef")


def _is_grading_ref_id_like(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return bool(GRADING_REF_ID_PATTERN.fullmatch(text))


def _is_unstable_generic_grading_ref(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower() in UNSTABLE_GENERIC_GRADING_REFS


def _ensure_grading_checks_cover_exam_refs(
    spec: dict[str, Any],
    *,
    questions: list[dict[str, Any]],
    patches: list[str],
) -> None:
    checks = spec.get("checks")
    if not isinstance(checks, list) or not questions or len(checks) >= len(questions):
        return
    refs = [
        str(question.get("gradingRef") or "").strip()
        for question in questions
        if isinstance(question.get("gradingRef"), str) and question.get("gradingRef").strip()
    ]
    if not refs:
        return
    check_ids = {str(check.get("id") or "").strip() for check in checks if isinstance(check, dict) and check.get("id")}
    missing_refs = [ref for ref in refs if ref not in check_ids]
    if not missing_refs:
        return
    spec["checks"] = [_grading_check_from_exam_question(question, index=index) for index, question in enumerate(questions, start=1)]
    patches.append("set.spec.checks.fromExamGradingRefs")


def _grading_check_from_exam_question(question: dict[str, Any], *, index: int) -> dict[str, Any]:
    grading_ref = str(question.get("gradingRef") or f"check_q{index}").strip() or f"check_q{index}"
    score = question.get("score") if isinstance(question.get("score"), int) and question.get("score") > 0 else 1
    expected = _grading_expected_from_exam_question(question, grading_ref)
    return {
        "id": grading_ref,
        "type": "stdout_contains",
        "command": "python main.py",
        "expected": expected,
        "score": score,
    }


def _grading_expected_from_exam_question(question: dict[str, Any], grading_ref: str) -> list[str]:
    answer = question.get("answer")
    if isinstance(answer, str) and answer.strip():
        return [answer.strip()]
    return [grading_ref]


def _normalize_grading_check_string_fields(check: dict[str, Any], *, path: str, patches: list[str]) -> None:
    for key in ("id", "path", "command", "notebookPath", "jsonPath"):
        if key not in check or check.get(key) is None or isinstance(check.get(key), str):
            continue
        check[key] = _stringify_llm_field(check[key], preferred_key=key)
        patches.append(f"set.{path}.{key}")


def _promote_grading_check_alias_fields(check: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.checks[{index - 1}]"
    for canonical, aliases in GRADING_CHECK_FIELD_ALIASES.items():
        if _llm_value_has_content(check.get(canonical)):
            continue
        for alias in aliases:
            value = _grading_check_alias_value(check.get(alias), canonical=canonical)
            if _llm_value_has_content(value):
                check[canonical] = value
                patches.append(f"set.{path}.{canonical}.from.{alias}")
                break


def _grading_check_alias_value(value: Any, *, canonical: str) -> Any:
    if canonical in {"id", "type", "path", "command", "notebookPath", "jsonPath"} and isinstance(value, dict):
        return _stringify_llm_field(value, preferred_key=canonical)
    if canonical == "expected" and isinstance(value, dict):
        for key in ("expected", "expectedOutput", "expected_output", "tokens", "items", "contains", "value", "text", "description"):
            nested = value.get(key)
            if _llm_value_has_content(nested):
                return nested
    if canonical == "expectedValue" and isinstance(value, dict):
        for key in ("expectedValue", "expected_value", "expectedJsonValue", "expected_json_value", "value", "text", "answer"):
            nested = value.get(key)
            if _llm_value_has_content(nested):
                return nested
    return value


def _promote_assessment_plan_alias_fields(plan: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.assessmentPlan[{index - 1}]"
    for canonical, aliases in ASSESSMENT_PLAN_FIELD_ALIASES.items():
        if _llm_value_has_content(plan.get(canonical)):
            continue
        for alias in aliases:
            value = _assessment_plan_alias_value(plan.get(alias), canonical=canonical)
            if _llm_value_has_content(value):
                plan[canonical] = value
                patches.append(f"set.{path}.{canonical}.from.{alias}")
                break

    execution_plan = plan.get("executionPlan")
    if isinstance(execution_plan, dict):
        _promote_assessment_execution_plan_alias_fields(execution_plan, path=f"{path}.executionPlan", patches=patches)


def _assessment_plan_alias_value(value: Any, *, canonical: str) -> Any:
    if canonical in {"checkId", "type", "runner", "inputSummary", "riskLevel"} and isinstance(value, dict):
        return _stringify_llm_field(value, preferred_key=canonical)
    return value


def _promote_assessment_execution_plan_alias_fields(
    execution_plan: dict[str, Any],
    *,
    path: str,
    patches: list[str],
) -> None:
    for canonical, aliases in ASSESSMENT_EXECUTION_PLAN_FIELD_ALIASES.items():
        if _llm_value_has_content(execution_plan.get(canonical)):
            continue
        for alias in aliases:
            value = execution_plan.get(alias)
            if _llm_value_has_content(value):
                execution_plan[canonical] = value
                patches.append(f"set.{path}.{canonical}.from.{alias}")
                break


def _stringify_llm_field(value: Any, *, preferred_key: str) -> str:
    if isinstance(value, dict):
        text = _first_non_empty_string(
            value,
            (preferred_key, "id", "ref", "text", "value", "name", "answer", "gradingRef", "description"),
        )
        if text:
            return text
    return _stringify_llm_scalar(value)


def _normalize_grading_check_type(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in GRADING_CHECK_TYPES:
        return text
    return GRADING_CHECK_TYPE_ALIASES.get(text, "stdout_contains")


def _normalize_grading_check_required_fields(
    check: dict[str, Any],
    *,
    index: int,
    questions: list[dict[str, Any]],
    path: str,
    patches: list[str],
) -> None:
    check_type = str(check.get("type"))
    expected_tokens = _default_expected_tokens(check, index=index, questions=questions)
    if check_type == "file_exists":
        _set_if_empty(check, "path", "result.csv", path, patches)
    elif check_type == "stdout_contains":
        _set_if_empty(check, "command", "python main.py", path, patches)
        _normalize_expected_tokens(check, "expected", expected_tokens, path, patches)
    elif check_type == "pytest":
        _set_if_empty(check, "path", "tests/test_main.py", path, patches)
    elif check_type == "notebook_cell":
        _set_if_empty(check, "notebookPath", "notebooks/analysis.ipynb", path, patches)
        if not isinstance(check.get("cellIndex"), int) or check.get("cellIndex", -1) < 0:
            check["cellIndex"] = 0
            patches.append(f"set.{path}.cellIndex")
        _normalize_expected_tokens(check, "expected", expected_tokens, path, patches)
    elif check_type == "json_field":
        _set_if_empty(check, "path", "metrics.json", path, patches)
        _set_if_empty(check, "jsonPath", "$.score", path, patches)
        if check.get("expectedValue") is None:
            check["expectedValue"] = expected_tokens[0]
            patches.append(f"set.{path}.expectedValue")
    elif check_type == "log_keyword":
        _set_if_empty(check, "path", "logs/output.log", path, patches)
        _normalize_expected_tokens(check, "expected", expected_tokens, path, patches)


def _normalize_grading_scores(spec: dict[str, Any], *, input_payload: dict[str, Any], patches: list[str]) -> None:
    checks = [check for check in spec.get("checks", []) if isinstance(check, dict)]
    if not checks:
        return
    total_score = spec.get("totalScore")
    if not isinstance(total_score, int) or total_score <= 0:
        return
    if total_score < len(checks):
        spec["totalScore"] = len(checks)
        total_score = spec["totalScore"]
        patches.append("set.spec.totalScore.minimumForChecks")
    current_sum = sum(int(check.get("score", 0)) for check in checks if isinstance(check.get("score"), int))
    if current_sum == total_score and all(isinstance(check.get("score"), int) and check.get("score", 0) > 0 for check in checks):
        return

    questions = _exam_questions(input_payload)
    question_scores = [question.get("score") for question in questions]
    if len(question_scores) == len(checks) and all(isinstance(score, int) and score > 0 for score in question_scores) and sum(question_scores) == total_score:
        desired_scores = list(question_scores)
    else:
        desired_scores = _distribute_total_score(total_score, len(checks))

    for index, (check, desired_score) in enumerate(zip(checks, desired_scores), start=1):
        if check.get("score") != desired_score:
            check["score"] = desired_score
            patches.append(f"set.spec.checks[{index - 1}].score")


def _distribute_total_score(total_score: int, count: int) -> list[int]:
    base = max(1, total_score // count)
    remainder = total_score - base * count
    scores = [base for _ in range(count)]
    index = 0
    while remainder > 0:
        scores[index % count] += 1
        remainder -= 1
        index += 1
    while sum(scores) > total_score:
        for score_index in range(len(scores) - 1, -1, -1):
            if scores[score_index] > 1 and sum(scores) > total_score:
                scores[score_index] -= 1
    return scores


def _normalize_assessment_plan(spec: dict[str, Any], patches: list[str]) -> None:
    plans = spec.get("assessmentPlan")
    checks = [check for check in spec.get("checks", []) if isinstance(check, dict)]
    if isinstance(plans, dict):
        spec["assessmentPlan"] = _assessment_plan_map_to_list(plans)
        plans = spec["assessmentPlan"]
        patches.append("set.spec.assessmentPlan.from_object")
    if not isinstance(plans, list) or not plans:
        plans = []
        for check in checks:
            plans.append(_assessment_plan_item_from_check(check))
        spec["assessmentPlan"] = plans or [_assessment_plan_item_from_check({"id": "check_1", "type": "stdout_contains", "score": 1})]
        patches.append("set.spec.assessmentPlan")
        return

    for index, plan in enumerate(plans, start=1):
        if isinstance(plan, dict):
            _promote_assessment_plan_alias_fields(plan, index=index, patches=patches)

    plan_by_check_id = {str(plan.get("checkId")): plan for plan in plans if isinstance(plan, dict) and plan.get("checkId")}
    normalized_plans = []
    for index, check in enumerate(checks):
        plan = plan_by_check_id.get(str(check.get("id")))
        if plan is None and index < len(plans) and isinstance(plans[index], dict):
            plan = plans[index]
        if not isinstance(plan, dict):
            plan = {}
            patches.append(f"set.spec.assessmentPlan[{index}]")
        normalized_plan = json.loads(json.dumps(plan, ensure_ascii=False))
        _normalize_assessment_plan_item(normalized_plan, check, path=f"spec.assessmentPlan[{index}]", patches=patches)
        normalized_plans.append(normalized_plan)
    if plans != normalized_plans:
        spec["assessmentPlan"] = normalized_plans
        patches.append("set.spec.assessmentPlan.alignedWithChecks")


def _assessment_plan_map_to_list(plans: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    allowed_keys = {
        "checkId",
        "type",
        "runner",
        "score",
        "inputSummary",
        "executionPlan",
        "mockEvidence",
        "riskLevel",
        "sandboxRequiredBeforeRealExecution",
    }
    for aliases in ASSESSMENT_PLAN_FIELD_ALIASES.values():
        allowed_keys.update(aliases)
    for index, (key, value) in enumerate(plans.items(), start=1):
        check_id = str(key).strip() or f"check_{index}"
        if isinstance(value, dict):
            plan = {item_key: item_value for item_key, item_value in value.items() if item_key in allowed_keys}
            plan.setdefault("checkId", check_id)
        else:
            plan = {"checkId": check_id, "inputSummary": _stringify_llm_scalar(value)}
        normalized.append(plan)
    return normalized


def _normalize_assessment_plan_item(plan: dict[str, Any], check: dict[str, Any], *, path: str, patches: list[str]) -> None:
    defaults = _assessment_plan_item_from_check(check)
    for key in ("checkId", "type", "runner", "score"):
        if plan.get(key) != defaults[key]:
            plan[key] = defaults[key]
            patches.append(f"set.{path}.{key}")
    _set_if_empty(plan, "inputSummary", defaults["inputSummary"], path, patches)
    if plan.get("inputSummary") is not None and not isinstance(plan.get("inputSummary"), str):
        plan["inputSummary"] = _stringify_llm_field(plan["inputSummary"], preferred_key="inputSummary")
        patches.append(f"set.{path}.inputSummary")
    if isinstance(plan.get("inputSummary"), str) and not plan["inputSummary"].strip():
        plan["inputSummary"] = defaults["inputSummary"]
        patches.append(f"set.{path}.inputSummary")

    execution_plan = plan.get("executionPlan")
    if not isinstance(execution_plan, dict):
        execution_plan = {}
        plan["executionPlan"] = execution_plan
        patches.append(f"set.{path}.executionPlan")
    if execution_plan.get("strategy") != "MOCK_PLAN_ONLY":
        execution_plan["strategy"] = "MOCK_PLAN_ONLY"
        patches.append(f"set.{path}.executionPlan.strategy")
    if execution_plan.get("wouldRunInsideRealSandbox") is not True:
        execution_plan["wouldRunInsideRealSandbox"] = True
        patches.append(f"set.{path}.executionPlan.wouldRunInsideRealSandbox")
    required_limits = execution_plan.get("requiredLimits")
    if not isinstance(required_limits, dict):
        required_limits = {}
        execution_plan["requiredLimits"] = required_limits
        patches.append(f"set.{path}.executionPlan.requiredLimits")
    for key, value in defaults["executionPlan"]["requiredLimits"].items():
        if not isinstance(required_limits.get(key), str) or not required_limits.get(key).strip():
            required_limits[key] = value
            patches.append(f"set.{path}.executionPlan.requiredLimits.{key}")
    if required_limits.get("network") != "disabled_by_default":
        required_limits["network"] = "disabled_by_default"
        patches.append(f"set.{path}.executionPlan.requiredLimits.network")

    mock_evidence = plan.get("mockEvidence")
    if mock_evidence != {"status": "MOCK_EVIDENCE_NOT_COLLECTED"}:
        plan["mockEvidence"] = {"status": "MOCK_EVIDENCE_NOT_COLLECTED"}
        patches.append(f"set.{path}.mockEvidence.status")
    if plan.get("riskLevel") not in {"low", "medium", "high"}:
        plan["riskLevel"] = defaults["riskLevel"]
        patches.append(f"set.{path}.riskLevel")
    if plan.get("sandboxRequiredBeforeRealExecution") is not True:
        plan["sandboxRequiredBeforeRealExecution"] = True
        patches.append(f"set.{path}.sandboxRequiredBeforeRealExecution")


def _assessment_plan_item_from_check(check: dict[str, Any]) -> dict[str, Any]:
    check_type = check.get("type") if check.get("type") in GRADING_CHECK_TYPES else "stdout_contains"
    return {
        "checkId": str(check.get("id") or "check_1"),
        "type": check_type,
        "runner": GRADING_CHECK_RUNNERS[check_type],
        "score": check.get("score") if isinstance(check.get("score"), int) and check.get("score") > 0 else 1,
        "inputSummary": _assessment_plan_input_summary(check),
        "executionPlan": {
            "strategy": "MOCK_PLAN_ONLY",
            "requiredLimits": {
                "cpu": "required",
                "memory": "required",
                "timeout": "30s",
                "network": "disabled_by_default",
                "filesystem": "isolated_workspace_required",
                "process": "limited",
            },
            "wouldRunInsideRealSandbox": True,
        },
        "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
        "riskLevel": GRADING_RISK_LEVELS[check_type],
        "sandboxRequiredBeforeRealExecution": True,
    }


def _assessment_plan_input_summary(check: dict[str, Any]) -> str:
    check_type = check.get("type")
    if check_type == "file_exists":
        return f"Plan file existence check for {check.get('path', 'result.csv')}"
    if check_type == "stdout_contains":
        return f"Plan stdout check for command: {check.get('command', 'python main.py')}"
    if check_type == "pytest":
        return f"Plan pytest check at {check.get('path', 'tests/test_main.py')}"
    if check_type == "notebook_cell":
        return f"Plan notebook cell output check for {check.get('notebookPath', 'notebooks/analysis.ipynb')} cell {check.get('cellIndex', 0)}"
    if check_type == "json_field":
        return f"Plan JSON field check for {check.get('path', 'metrics.json')} {check.get('jsonPath', '$.score')}"
    if check_type == "log_keyword":
        return f"Plan log keyword check for {check.get('path', 'logs/output.log')}"
    return "真实执行前仅生成可审核评分计划。"


def _set_if_empty(target: dict[str, Any], key: str, value: Any, path: str, patches: list[str]) -> None:
    if target.get(key) in (None, "", []):
        target[key] = value
        patches.append(f"set.{path}.{key}")


def _normalize_expected_tokens(target: dict[str, Any], key: str, default: list[str], path: str, patches: list[str]) -> None:
    value = target.get(key)
    if isinstance(value, str) and value.strip():
        target[key] = [value.strip()]
        patches.append(f"set.{path}.{key}")
        return
    if not isinstance(value, list):
        target[key] = default
        patches.append(f"set.{path}.{key}")
        return
    cleaned = [_stringify_llm_scalar(item).strip() for item in value if item is not None]
    cleaned = [item for item in cleaned if item]
    if not cleaned:
        target[key] = default
        patches.append(f"set.{path}.{key}")
    elif cleaned != value:
        target[key] = cleaned
        patches.append(f"set.{path}.{key}")


def _exam_questions(input_payload: dict[str, Any]) -> list[dict[str, Any]]:
    exam_dsl = input_payload.get("examDsl", {})
    if not isinstance(exam_dsl, dict):
        return []
    questions = exam_dsl.get("spec", {}).get("questions", [])
    if not isinstance(questions, list):
        return []
    return [question for question in questions if isinstance(question, dict)]


def _default_expected_tokens(check: dict[str, Any], *, index: int, questions: list[dict[str, Any]]) -> list[str]:
    question = _question_for_check(check, index=index, questions=questions)
    answer = question.get("answer") if isinstance(question, dict) else None
    if isinstance(answer, str) and answer.strip():
        return [answer.strip()]
    grading_ref = question.get("gradingRef") if isinstance(question, dict) else None
    if isinstance(grading_ref, str) and grading_ref.strip():
        return [grading_ref.strip()]
    return ["PASS"]


def _question_for_check(check: dict[str, Any], *, index: int, questions: list[dict[str, Any]]) -> dict[str, Any]:
    matched_question = _question_for_check_id_match(check, questions)
    if matched_question:
        return matched_question
    if 0 <= index - 1 < len(questions):
        return questions[index - 1]
    return {}


def _question_for_check_id_match(check: dict[str, Any], questions: list[dict[str, Any]]) -> dict[str, Any]:
    check_id = str(check.get("id") or "")
    for question in questions:
        question_id = str(question.get("id") or "")
        grading_ref = str(question.get("gradingRef") or "")
        if check_id and check_id in {grading_ref, question_id, f"check_{question_id}"}:
            return question
    return {}


def _normalize_ppt_dsl(
    metadata: dict[str, Any],
    spec: dict[str, Any],
    *,
    input_payload: dict[str, Any],
    patches: list[str],
) -> None:
    lab_dsl = input_payload.get("labDsl", {})
    lab_metadata = lab_dsl.get("metadata", {}) if isinstance(lab_dsl, dict) else {}
    _fill_defaults(
        metadata,
        {
            "id": "ppt_real_llm_demo",
            "title": lab_metadata.get("title") if isinstance(lab_metadata, dict) else "真实 LLM Demo 课件",
            "audience": "平台开发者",
            "durationMinutes": 30,
        },
        "metadata",
        patches,
    )
    _normalize_ppt_metadata(metadata, patches)
    theme = spec.get("theme")
    if not isinstance(theme, dict):
        theme = {}
        spec["theme"] = theme
        patches.append("set.spec.theme")
    _fill_defaults(theme, {"style": "clean", "language": "zh-CN"}, "spec.theme", patches)
    _normalize_ppt_theme(theme, patches)
    slides = spec.get("slides")
    if isinstance(slides, dict):
        spec["slides"] = _ppt_slide_map_to_list(slides)
        slides = spec["slides"]
        patches.append("set.spec.slides.from_object")
    if not isinstance(slides, list) or not slides:
        spec["slides"] = [{"id": "slide_1", "type": "title", "title": metadata.get("title", "真实 LLM Demo")}]
        patches.append("set.spec.slides")
        return
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            slides[index - 1] = {"id": f"slide_{index}", "type": "content", "title": str(slide)}
            patches.append(f"set.spec.slides[{index - 1}]")
            continue
        _promote_ppt_slide_alias_fields(slide, index=index, patches=patches)
        if slide.get("type") not in {"title", "content", "summary"}:
            slide["type"] = _normalize_ppt_slide_type(slide.get("type"))
            patches.append(f"set.spec.slides[{index - 1}].type")
        if "layout" in slide and slide.get("layout") not in PPT_SLIDE_LAYOUTS:
            del slide["layout"]
            patches.append(f"remove.spec.slides[{index - 1}].layout")
        _fill_defaults(
            slide,
            {"id": f"slide_{index}", "title": f"页面 {index}"},
            f"spec.slides[{index - 1}]",
            patches,
        )
        _normalize_ppt_slide_fields(slide, index=index, patches=patches)


def _ppt_slide_map_to_list(slides: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, (key, value) in enumerate(slides.items(), start=1):
        if isinstance(value, dict):
            slide = json.loads(json.dumps(value, ensure_ascii=False))
            slide.setdefault("id", str(key))
        else:
            slide = {
                "id": str(key) if key else f"slide_{index}",
                "type": "content",
                "title": _stringify_llm_scalar(value),
            }
        normalized.append(slide)
    return normalized


def _normalize_ppt_metadata(metadata: dict[str, Any], patches: list[str]) -> None:
    for key in ("id", "title", "audience"):
        if key in metadata and not isinstance(metadata.get(key), str):
            metadata[key] = _stringify_llm_field(metadata[key], preferred_key=key)
            patches.append(f"set.metadata.{key}")
    duration = _coerce_positive_int(metadata.get("durationMinutes"))
    if duration is None:
        metadata["durationMinutes"] = 30
        patches.append("set.metadata.durationMinutes")
    elif duration != metadata.get("durationMinutes"):
        metadata["durationMinutes"] = duration
        patches.append("set.metadata.durationMinutes")


def _normalize_ppt_theme(theme: dict[str, Any], patches: list[str]) -> None:
    for key in ("style", "language"):
        if key in theme and not isinstance(theme.get(key), str):
            theme[key] = _stringify_llm_scalar(theme[key])
            patches.append(f"set.spec.theme.{key}")


def _normalize_ppt_slide_type(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in {"title", "cover", "opening", "intro", "front_page", "封面", "首页", "标题页"}:
        return "title"
    if text in {"summary", "conclusion", "closing", "recap", "wrap_up", "ending", "总结", "结尾", "回顾"}:
        return "summary"
    return "content"


def _normalize_ppt_slide_fields(slide: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.slides[{index - 1}]"
    for key in ("id", "title", "subtitle"):
        if key in slide and slide.get(key) is not None and not isinstance(slide.get(key), str):
            slide[key] = _stringify_llm_field(slide[key], preferred_key=key)
            patches.append(f"set.{path}.{key}")
    supplemental_bullets = _ppt_slide_supplemental_bullets(slide)
    bullets = slide.get("bullets")
    if isinstance(bullets, str):
        normalized = [bullets.strip()] if bullets.strip() else []
        normalized.extend(supplemental_bullets)
        slide["bullets"] = normalized
        patches.append(f"set.{path}.bullets")
        return
    if isinstance(bullets, list):
        normalized = [_stringify_llm_scalar(item).strip() for item in bullets if item is not None]
        normalized = [item for item in normalized if item]
        normalized.extend(item for item in supplemental_bullets if item not in normalized)
        if normalized != bullets:
            slide["bullets"] = normalized
            patches.append(f"set.{path}.bullets")
        return
    if bullets is None and not supplemental_bullets:
        return
    normalized = []
    if bullets is not None:
        text = _stringify_llm_scalar(bullets).strip()
        if text:
            normalized.append(text)
    normalized.extend(supplemental_bullets)
    slide["bullets"] = normalized
    patches.append(f"set.{path}.bullets")


def _promote_ppt_slide_alias_fields(slide: dict[str, Any], *, index: int, patches: list[str]) -> None:
    path = f"spec.slides[{index - 1}]"
    for canonical, aliases in PPT_SLIDE_FIELD_ALIASES.items():
        if _llm_value_has_content(slide.get(canonical)):
            continue
        for alias in aliases:
            value = _ppt_slide_alias_value(slide.get(alias), canonical=canonical)
            if _llm_value_has_content(value):
                slide[canonical] = value
                patches.append(f"set.{path}.{canonical}.from.{alias}")
                break


def _ppt_slide_alias_value(value: Any, *, canonical: str) -> Any:
    if canonical != "bullets" or not isinstance(value, dict):
        return value
    for key in ("bullets", "points", "items", "keyPoints", "key_points", "content", "body", "text", "description"):
        nested = value.get(key)
        if _llm_value_has_content(nested):
            return nested
    return value


def _ppt_slide_supplemental_bullets(slide: dict[str, Any]) -> list[str]:
    supplemental: list[str] = []
    for key in ("speakerNotes", "speaker_notes", "notes"):
        text = _stringify_llm_scalar(slide.get(key)).strip() if slide.get(key) is not None else ""
        if text:
            supplemental.append(f"讲稿提示：{text}")
            break
    duration = _coerce_positive_int(slide.get("durationSeconds") or slide.get("duration") or slide.get("durationMinutes"))
    if duration is not None:
        supplemental.append(f"建议时长：{duration}")
    return supplemental


def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    text = str(value or "").strip()
    digits = ""
    for char in text:
        if char.isdigit():
            digits += char
        elif digits:
            break
    if not digits:
        return None
    number = int(digits)
    return number if number > 0 else None


def _fill_defaults(target: dict[str, Any], defaults: dict[str, Any], path: str, patches: list[str]) -> None:
    for key, value in defaults.items():
        if target.get(key) in (None, "", []):
            target[key] = value
            patches.append(f"set.{path}.{key}")


def _prune_additional_properties(
    value: Any,
    schema: dict[str, Any],
    path: str,
    patches: list[str],
) -> None:
    if not isinstance(value, dict) or not isinstance(schema, dict):
        return
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for key in list(value):
            if key not in properties and schema.get("additionalProperties") is False:
                del value[key]
                patches.append(f"remove.{path}.{key}")
                continue
            _prune_by_schema_node(value.get(key), properties.get(key, {}), f"{path}.{key}", patches)


def _prune_by_schema_node(value: Any, schema: dict[str, Any], path: str, patches: list[str]) -> None:
    if isinstance(value, dict):
        _prune_additional_properties(value, schema, path, patches)
    elif isinstance(value, list):
        item_schema = schema.get("items", {}) if isinstance(schema, dict) else {}
        for index, item in enumerate(value):
            _prune_by_schema_node(item, item_schema, f"{path}[{index}]", patches)


def _response_output_text(response: Any) -> str:
    if isinstance(response, dict):
        if isinstance(response.get("output_text"), str):
            return response["output_text"]
        choice_text = _extract_chat_completion_text(response.get("choices"))
        if choice_text:
            return choice_text
        output = response.get("output")
    else:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text
        choice_text = _extract_chat_completion_text(getattr(response, "choices", None))
        if choice_text:
            return choice_text
        output = getattr(response, "output", None)
    text = _extract_text_from_output(output)
    if text:
        return text
    raise ProviderError(
        "REAL_LLM_DEMO_DSL_EMPTY_RESPONSE",
        "真实 LLM Demo DSL 返回内容为空或无法提取文本",
        [{"field": "response.output", "reason": "missing output_text"}],
    )


def _extract_chat_completion_text(choices: Any) -> str | None:
    if not choices:
        return None
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else getattr(first, "message", None)
    if message is None:
        return None
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    return content if isinstance(content, str) and content else None


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


def _validate_generated_dsl(document: dict[str, Any], schema: dict[str, Any], *, output_kind: str, kind: str) -> None:
    try:
        validate_dsl(document, schema)
    except DslValidationError as exc:
        errors = [
            {"field": err.get("field", "$"), "reason": err.get("reason", "schema validation failed")}
            for err in exc.errors
        ]
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED",
            "真实 LLM Demo DSL 生成内容未通过 Schema 校验",
            errors,
            {
                "schemaFailureDiagnostic": build_real_llm_schema_failure_diagnostic(
                    errors,
                    document=document,
                    kind=kind,
                    output_kind=output_kind,
                )
            },
        ) from exc
    if document.get("kind") != output_kind:
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_KIND_INVALID",
            "真实 LLM Demo DSL kind 不匹配",
            [{"field": "kind", "reason": f"must be {output_kind}"}],
        )
    if document.get("status") != "WAITING_REVIEW":
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_REVIEW_STATUS_REQUIRED",
            "真实 LLM Demo DSL 生成内容必须进入 WAITING_REVIEW",
            [{"field": "status", "reason": "must be WAITING_REVIEW"}],
        )
    if kind == "grading":
        plans = document.get("spec", {}).get("assessmentPlan")
        if not isinstance(plans, list) or not plans:
            raise ProviderError(
                "REAL_LLM_DEMO_DSL_ASSESSMENT_PLAN_REQUIRED",
                "真实 LLM Demo Grading DSL 必须包含 assessmentPlan",
                [{"field": "spec.assessmentPlan", "reason": "required for demo review"}],
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
