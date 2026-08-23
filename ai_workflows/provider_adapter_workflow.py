"""Provider-adapter backed Phase 2 workflow helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from providers import (
    ProviderError,
    RealLlmDemoDslRequest,
    RealLlmMinimalPocRequest,
    invoke_provider,
    run_real_llm_demo_dsl_generation,
    run_real_llm_minimal_poc,
)


ROOT = Path(__file__).resolve().parents[1]

PROMPTS_BY_KIND = {
    "lab": "lab_generation_v0",
    "exam": "exam_generation_v0",
    "grading": "grading_generation_v0",
    "ppt": "ppt_generation_v0",
}

OUTPUT_KIND_BY_KIND = {
    "lab": "Lab",
    "exam": "Exam",
    "grading": "Grading",
    "ppt": "PPT",
}

PHASE2_WORKFLOW_ID = "phase2_content_generation"

PHASE2_GENERATION_STEP_BY_KIND = {
    "lab": "generate_lab_dsl",
    "exam": "generate_exam_dsl",
    "grading": "generate_grading_dsl",
    "ppt": "generate_ppt_dsl",
}
ARTIFACT_PROFILE_LEGACY_ALL = "legacy-all"
ARTIFACT_PROFILE_TEACHING_CORE = "teaching-core"
ARTIFACT_KINDS_BY_PROFILE = {
    ARTIFACT_PROFILE_LEGACY_ALL: ("lab", "exam", "grading", "ppt"),
    ARTIFACT_PROFILE_TEACHING_CORE: ("lab", "exam", "grading"),
}

PHASE2_SAFETY = {
    "realLlmCalled": False,
    "secretsRead": False,
    "networkAccess": False,
    "realAgentStarted": False,
    "realCloudResourceCreated": False,
    "realCloudResourceChanged": False,
    "sandboxExecuted": False,
    "contestantCodeExecuted": False,
    "unknownShellExecuted": False,
    "autoPublishAllowed": False,
    "realPublish": False,
    "reviewBypassed": False,
}

PROVIDER_MODE_MOCK = "mock"
PROVIDER_MODE_REAL_LLM_MINIMAL = "real-llm-minimal"
PROVIDER_MODE_REAL_LLM = "real-llm"
PROVIDER_MODE_REAL_LLM_DEMO = "real-llm-demo"
PHASE2_MOCK_ONLY_MODE = "MOCK_ONLY"
PHASE2_REAL_LLM_MINIMAL_MODE = "REAL_LLM_MINIMAL_LAB_WORKFLOW"
PHASE2_REAL_LLM_MODE = "REAL_LLM_WORKFLOW"
PHASE2_REAL_LLM_DEMO_MODE = "REAL_LLM_DEMO_WORKFLOW"
REAL_LLM_DSL_GENERATION_MODE = "REAL_LLM_DSL_GENERATION"
REAL_LLM_MINIMAL_LAB_OUTPUT_REF = "examples/output/phase2-real-llm-lab.json"
REAL_LLM_OUTPUT_REFS = {
    "lab": "examples/output/real-llm-lab.json",
    "exam": "examples/output/real-llm-exam.json",
    "grading": "examples/output/real-llm-grading.json",
    "ppt": "examples/output/real-llm-ppt.json",
}
REAL_LLM_DEMO_OUTPUT_REFS = {
    "lab": "examples/output/demo-real-lab.json",
    "exam": "examples/output/demo-real-exam.json",
    "grading": "examples/output/demo-real-grading.json",
    "ppt": "examples/output/demo-real-ppt.json",
}
REAL_LLM_MINIMAL_PROVIDER_ADAPTER = "openai_responses_sdk_adapter"
MIXED_REAL_LLM_MINIMAL_PROVIDER_ADAPTER = "mixed_real_llm_minimal_and_mock_provider_adapter"
REAL_LLM_PROVIDER_ADAPTER = "openai_responses_sdk_adapter"
REAL_LLM_DEMO_PROVIDER_ADAPTER = "openai_responses_sdk_demo_adapter"
REAL_LLM_SOURCE_MODE_MINIMAL = "minimal"
REAL_LLM_SOURCE_MODE_OFFICIAL = "official"
REAL_LLM_SOURCE_MODE_DEMO = "demo"
ALLOWED_LAB_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
ALLOWED_LAB_TEACHING_STYLES = {"guided_practice", "project_based", "challenge_based", "lecture_demo"}
DEFAULT_LAB_GENERATION_CONTEXT = {
    "targetUsers": ["高职学生"],
    "durationMinutes": 60,
    "difficulty": "beginner",
    "techTags": [],
    "teachingStyle": "guided_practice",
}


def _split_generation_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(_split_generation_list(item))
        return items
    text = str(value).replace("，", ",").replace("；", ",").replace(";", ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _context_value(context: dict[str, Any], camel_key: str, snake_key: str) -> Any:
    if camel_key in context:
        return context[camel_key]
    if snake_key in context:
        return context[snake_key]
    return DEFAULT_LAB_GENERATION_CONTEXT[camel_key]


def normalize_lab_generation_context(context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = context or {}
    target_users = _split_generation_list(_context_value(payload, "targetUsers", "target_users"))
    tech_tags = _split_generation_list(_context_value(payload, "techTags", "tech_tags"))
    duration_value = _context_value(payload, "durationMinutes", "duration_minutes")
    difficulty = str(_context_value(payload, "difficulty", "difficulty")).strip() or "beginner"
    teaching_style = str(_context_value(payload, "teachingStyle", "teaching_style")).strip() or "guided_practice"

    errors: list[dict[str, str]] = []
    try:
        duration_minutes = int(duration_value)
    except (TypeError, ValueError):
        duration_minutes = 0
        errors.append({"field": "durationMinutes", "reason": "必须是正整数"})
    if duration_minutes <= 0:
        errors.append({"field": "durationMinutes", "reason": "必须大于 0"})
    if not target_users:
        errors.append({"field": "targetUsers", "reason": "至少提供一个目标用户"})
    if difficulty not in ALLOWED_LAB_DIFFICULTIES:
        errors.append({"field": "difficulty", "reason": "必须是 beginner/intermediate/advanced"})
    if teaching_style not in ALLOWED_LAB_TEACHING_STYLES:
        errors.append({"field": "teachingStyle", "reason": "必须是 guided_practice/project_based/challenge_based/lecture_demo"})
    if errors:
        raise ProviderError("VALIDATION_ERROR", "Lab 生成业务参数错误", errors)

    return {
        "targetUsers": target_users,
        "durationMinutes": duration_minutes,
        "difficulty": difficulty,
        "techTags": tech_tags,
        "teachingStyle": teaching_style,
        "constraintsApplied": True,
    }


def generate_mock_dsl_via_adapter(
    kind: str,
    *,
    input_ref: str | None = None,
    trace_id: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    if kind not in PROMPTS_BY_KIND:
        raise ProviderError("VALIDATION_ERROR", "不支持的 Workflow DSL 类型", [{"field": "kind", "reason": kind}])

    result = invoke_provider(
        "generateJson",
        prompt_id=PROMPTS_BY_KIND[kind],
        output_kind=OUTPUT_KIND_BY_KIND[kind],
        input_ref=input_ref,
        trace_id=trace_id,
        root=root,
    )
    return {
        "kind": kind,
        "promptId": result["promptId"],
        "provider": {
            "adapterId": result["adapterId"],
            "interfaceName": result["interfaceName"],
            "operation": result["operation"],
            "providerId": result["providerId"],
            "mode": result["mode"],
            "realLlmCalled": result["realLlmCalled"],
            "secretsRead": result["secretsRead"],
            "networkAccess": result["networkAccess"],
            "traceId": result["traceId"],
        },
        "dsl": result["dsl"],
        "dslPath": result["dslPath"],
        "dslId": result["dslId"],
        "inputRef": result.get("inputRef"),
        "outputKind": result["outputKind"],
        "generatedStatus": result["generatedStatus"],
        "reviewRequired": result["reviewRequired"],
        "publishBlockedUntilApproved": result["publishBlockedUntilApproved"],
        "answerVisibleToCandidate": result.get("answerVisibleToCandidate", False),
        "artifactGenerated": result.get("artifactGenerated", False),
        "sandboxRequiredBeforeRealExecution": result.get("sandboxRequiredBeforeRealExecution", False),
    }


def generate_real_llm_minimal_lab_via_poc(
    *,
    input_ref: str,
    output_ref: str = REAL_LLM_MINIMAL_LAB_OUTPUT_REF,
    lab_generation_context: dict[str, Any] | None = None,
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: int = 60,
    max_output_tokens: int = 1800,
    explicit_real_call_opt_in: bool = False,
    confirm_single_request: bool = False,
    confirm_lab_only: bool = False,
    confirm_waiting_review: bool = False,
    confirm_no_auto_publish: bool = False,
    trace_id: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    result = run_real_llm_minimal_poc(
        RealLlmMinimalPocRequest(
            input_ref=input_ref,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_single_request=confirm_single_request,
            confirm_lab_only=confirm_lab_only,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            generation_context=lab_generation_context,
            trace_id=trace_id,
        ),
        root=root,
    )
    output_path = _resolve_output_path(root, output_ref)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result["labDsl"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "kind": "lab",
        "promptId": result["promptId"],
        "promptVersion": result["promptVersion"],
        "provider": {
            "adapterId": REAL_LLM_MINIMAL_PROVIDER_ADAPTER,
            "interfaceName": "LLMProvider",
            "operation": "generateJson",
            "providerId": result["providerId"],
            "mode": result["mode"],
            "model": result.get("model"),
            "baseUrlConfigured": result.get("baseUrlConfigured"),
            "baseUrlSource": result.get("baseUrlSource"),
            "realLlmCalled": True,
            "secretsRead": True,
            "networkAccess": True,
            "traceId": result["traceId"],
            "requestCount": result["requestCount"],
            "singleRequestOnly": result["singleRequestOnly"],
            "secretValueReturned": result["secretValueReturned"],
            "responseId": result.get("responseId"),
            "apiSurface": result.get("apiSurface"),
        },
        "dsl": result["labDsl"],
        "dslPath": str(output_path),
        "dslId": result["dslId"],
        "inputRef": result.get("inputRef"),
        "outputKind": result["outputKind"],
        "generatedStatus": result["generatedStatus"],
        "reviewRequired": result["reviewRequired"],
        "publishBlockedUntilApproved": True,
        "answerVisibleToCandidate": False,
        "artifactGenerated": True,
        "sandboxRequiredBeforeRealExecution": False,
        "schemaValidated": result["schemaValidated"],
        "usage": result.get("usage"),
        "responseId": result.get("responseId"),
        "apiSurface": result.get("apiSurface"),
        "normalization": result.get("normalization"),
    }


def _real_demo_input_payload(
    *,
    kind: str,
    input_ref: str,
    lab_generation_context: dict[str, Any] | None,
    lab: dict[str, Any] | None = None,
    exam: dict[str, Any] | None = None,
    grading: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "demoGoal": "Generate real LLM DSL artifacts for a first demo. Keep every artifact WAITING_REVIEW.",
        "sourceRef": input_ref,
        "labGenerationContext": lab_generation_context or {},
        "safety": {
            "autoPublishAllowed": False,
            "realPublish": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "answerVisibleToCandidate": False,
        },
    }
    if lab is not None:
        payload["labDsl"] = lab
    if exam is not None:
        payload["examDsl"] = exam
    if grading is not None:
        payload["gradingDsl"] = grading
    if kind == "exam":
        payload["instruction"] = "Convert the Lab DSL into a candidate-facing Exam DSL. Store answers only inside DSL for reviewer use; never expose them to candidate preview."
    elif kind == "grading":
        payload["instruction"] = "Generate deterministic Grading DSL checks and assessmentPlan aligned with Exam gradingRef values. Do not execute code."
    elif kind == "ppt":
        payload["instruction"] = "Generate PPT DSL from source and Lab DSL. Do not create a real PPTX file."
    else:
        payload["instruction"] = "Generate Lab DSL from source material."
    return payload


def generate_real_llm_demo_dsl_via_provider(
    kind: str,
    *,
    input_ref: str | None,
    output_ref: str,
    input_payload: dict[str, Any],
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: int = 60,
    max_output_tokens: int = 2200,
    explicit_real_call_opt_in: bool = False,
    confirm_waiting_review: bool = False,
    confirm_no_auto_publish: bool = False,
    repair_on_schema_failure: bool = False,
    api_surface: str = "auto",
    trace_id: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind=kind,
            input_ref=input_ref,
            input_payload=input_payload,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            repair_on_schema_failure=repair_on_schema_failure,
            api_surface=api_surface,
            trace_id=trace_id,
        ),
        root=root,
    )
    output_path = _resolve_output_path(root, output_ref)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result["dsl"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "kind": kind,
        "promptId": result["promptId"],
        "promptVersion": result["promptVersion"],
        "provider": {
            "adapterId": REAL_LLM_DEMO_PROVIDER_ADAPTER,
            "interfaceName": "LLMProvider",
            "operation": "generateJson",
            "providerId": result["providerId"],
            "mode": result["mode"],
            "model": result.get("model"),
            "baseUrlConfigured": result.get("baseUrlConfigured"),
            "baseUrlSource": result.get("baseUrlSource"),
            "realLlmCalled": True,
            "secretsRead": True,
            "networkAccess": True,
            "traceId": result["traceId"],
            "requestCount": result["requestCount"],
            "singleRequestOnly": result["singleRequestForKind"],
            "schemaRepairAttempted": result.get("schemaRepairAttempted", False),
            "schemaRepairApplied": result.get("schemaRepairApplied", False),
            "secretValueReturned": result["secretValueReturned"],
            "responseId": result.get("responseId"),
            "apiSurface": result.get("apiSurface"),
        },
        "dsl": result["dsl"],
        "dslPath": str(output_path),
        "dslId": result["dslId"],
        "inputRef": input_ref,
        "outputKind": result["outputKind"],
        "generatedStatus": result["generatedStatus"],
        "reviewRequired": result["reviewRequired"],
        "publishBlockedUntilApproved": True,
        "answerVisibleToCandidate": False,
        "artifactGenerated": kind != "ppt",
        "sandboxRequiredBeforeRealExecution": kind == "grading",
        "schemaValidated": result["schemaValidated"],
        "usage": result.get("usage"),
        "responseId": result.get("responseId"),
        "apiSurface": result.get("apiSurface"),
        "normalization": result.get("normalization"),
        "schemaRepair": result.get("schemaRepair"),
    }


def generate_real_llm_demo_dsl_bundle(
    *,
    input_ref: str,
    trace_id: str,
    root: Path = ROOT,
    lab_generation_context: dict[str, Any] | None = None,
    output_refs: dict[str, str] | None = None,
    real_llm_model: str | None = None,
    real_llm_base_url: str | None = None,
    timeout_seconds: int = 60,
    max_output_tokens: int = 2200,
    explicit_real_call_opt_in: bool = False,
    confirm_waiting_review: bool = False,
    confirm_no_auto_publish: bool = False,
    repair_on_schema_failure: bool = False,
    api_surface: str = "auto",
    include_ppt: bool = True,
) -> dict[str, dict[str, Any]]:
    refs = {**REAL_LLM_DEMO_OUTPUT_REFS, **(output_refs or {})}
    lab = generate_real_llm_demo_dsl_via_provider(
        "lab",
        input_ref=input_ref,
        output_ref=refs["lab"],
        input_payload=_real_demo_input_payload(
            kind="lab",
            input_ref=input_ref,
            lab_generation_context=lab_generation_context,
        ),
        model=real_llm_model,
        base_url=real_llm_base_url,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        explicit_real_call_opt_in=explicit_real_call_opt_in,
        confirm_waiting_review=confirm_waiting_review,
        confirm_no_auto_publish=confirm_no_auto_publish,
        repair_on_schema_failure=repair_on_schema_failure,
        api_surface=api_surface,
        trace_id=trace_id,
        root=root,
    )
    exam = generate_real_llm_demo_dsl_via_provider(
        "exam",
        input_ref=input_ref,
        output_ref=refs["exam"],
        input_payload=_real_demo_input_payload(
            kind="exam",
            input_ref=input_ref,
            lab_generation_context=lab_generation_context,
            lab=lab["dsl"],
        ),
        model=real_llm_model,
        base_url=real_llm_base_url,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        explicit_real_call_opt_in=explicit_real_call_opt_in,
        confirm_waiting_review=confirm_waiting_review,
        confirm_no_auto_publish=confirm_no_auto_publish,
        repair_on_schema_failure=repair_on_schema_failure,
        api_surface=api_surface,
        trace_id=trace_id,
        root=root,
    )
    grading = generate_real_llm_demo_dsl_via_provider(
        "grading",
        input_ref=input_ref,
        output_ref=refs["grading"],
        input_payload=_real_demo_input_payload(
            kind="grading",
            input_ref=input_ref,
            lab_generation_context=lab_generation_context,
            lab=lab["dsl"],
            exam=exam["dsl"],
        ),
        model=real_llm_model,
        base_url=real_llm_base_url,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        explicit_real_call_opt_in=explicit_real_call_opt_in,
        confirm_waiting_review=confirm_waiting_review,
        confirm_no_auto_publish=confirm_no_auto_publish,
        repair_on_schema_failure=repair_on_schema_failure,
        api_surface=api_surface,
        trace_id=trace_id,
        root=root,
    )
    bundle = {"lab": lab, "exam": exam, "grading": grading}
    if include_ppt:
        bundle["ppt"] = generate_real_llm_demo_dsl_via_provider(
            "ppt",
            input_ref=input_ref,
            output_ref=refs["ppt"],
            input_payload=_real_demo_input_payload(
                kind="ppt",
                input_ref=input_ref,
                lab_generation_context=lab_generation_context,
                lab=lab["dsl"],
                exam=exam["dsl"],
                grading=grading["dsl"],
            ),
            model=real_llm_model,
            base_url=real_llm_base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            repair_on_schema_failure=repair_on_schema_failure,
            api_surface=api_surface,
            trace_id=trace_id,
            root=root,
        )
    return bundle


def generate_real_llm_dsl_bundle(
    *,
    input_ref: str,
    trace_id: str,
    root: Path = ROOT,
    lab_generation_context: dict[str, Any] | None = None,
    output_refs: dict[str, str] | None = None,
    real_llm_model: str | None = None,
    real_llm_base_url: str | None = None,
    timeout_seconds: int = 60,
    max_output_tokens: int = 2200,
    explicit_real_call_opt_in: bool = False,
    confirm_waiting_review: bool = False,
    confirm_no_auto_publish: bool = False,
    repair_on_schema_failure: bool = False,
    api_surface: str = "auto",
    include_ppt: bool = True,
) -> dict[str, dict[str, Any]]:
    bundle = generate_real_llm_demo_dsl_bundle(
        input_ref=input_ref,
        trace_id=trace_id,
        root=root,
        lab_generation_context=lab_generation_context,
        output_refs={**REAL_LLM_OUTPUT_REFS, **(output_refs or {})},
        real_llm_model=real_llm_model,
        real_llm_base_url=real_llm_base_url,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        explicit_real_call_opt_in=explicit_real_call_opt_in,
        confirm_waiting_review=confirm_waiting_review,
        confirm_no_auto_publish=confirm_no_auto_publish,
        repair_on_schema_failure=repair_on_schema_failure,
        api_surface=api_surface,
        include_ppt=include_ppt,
    )
    for generation in bundle.values():
        generation["provider"]["adapterId"] = REAL_LLM_PROVIDER_ADAPTER
        generation["provider"]["mode"] = REAL_LLM_DSL_GENERATION_MODE
    return bundle


def generate_workflow_dsl_bundle(
    *,
    input_ref: str,
    trace_id: str,
    root: Path = ROOT,
    provider_mode: str = PROVIDER_MODE_MOCK,
    lab_generation_context: dict[str, Any] | None = None,
    real_lab_output_ref: str = REAL_LLM_MINIMAL_LAB_OUTPUT_REF,
    real_output_refs: dict[str, str] | None = None,
    real_demo_output_refs: dict[str, str] | None = None,
    real_llm_model: str | None = None,
    real_llm_base_url: str | None = None,
    timeout_seconds: int = 60,
    max_output_tokens: int = 1800,
    explicit_real_call_opt_in: bool = False,
    confirm_single_request: bool = False,
    confirm_lab_only: bool = False,
    confirm_waiting_review: bool = False,
    confirm_no_auto_publish: bool = False,
    repair_on_schema_failure: bool = False,
    api_surface: str = "auto",
    artifact_kinds: tuple[str, ...] = ARTIFACT_KINDS_BY_PROFILE[ARTIFACT_PROFILE_LEGACY_ALL],
) -> dict[str, dict[str, Any]]:
    include_ppt = "ppt" in artifact_kinds
    if provider_mode == PROVIDER_MODE_MOCK:
        lab = generate_mock_dsl_via_adapter("lab", input_ref=input_ref, trace_id=trace_id, root=root)
    elif provider_mode == PROVIDER_MODE_REAL_LLM_MINIMAL:
        lab = generate_real_llm_minimal_lab_via_poc(
            input_ref=input_ref,
            output_ref=real_lab_output_ref,
            lab_generation_context=lab_generation_context,
            model=real_llm_model,
            base_url=real_llm_base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_single_request=confirm_single_request,
            confirm_lab_only=confirm_lab_only,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            trace_id=trace_id,
            root=root,
        )
    elif provider_mode == PROVIDER_MODE_REAL_LLM:
        return generate_real_llm_dsl_bundle(
            input_ref=input_ref,
            trace_id=trace_id,
            root=root,
            lab_generation_context=lab_generation_context,
            output_refs=real_output_refs,
            real_llm_model=real_llm_model,
            real_llm_base_url=real_llm_base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            repair_on_schema_failure=repair_on_schema_failure,
            api_surface=api_surface,
            include_ppt=include_ppt,
        )
    elif provider_mode == PROVIDER_MODE_REAL_LLM_DEMO:
        return generate_real_llm_demo_dsl_bundle(
            input_ref=input_ref,
            trace_id=trace_id,
            root=root,
            lab_generation_context=lab_generation_context,
            output_refs=real_demo_output_refs,
            real_llm_model=real_llm_model,
            real_llm_base_url=real_llm_base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            repair_on_schema_failure=repair_on_schema_failure,
            api_surface=api_surface,
            include_ppt=include_ppt,
        )
    else:
        raise ProviderError(
            "PHASE2_PROVIDER_MODE_INVALID",
            "Phase 2 Workflow 不支持的 provider mode",
            [{"field": "providerMode", "reason": provider_mode}],
        )
    exam = generate_mock_dsl_via_adapter("exam", input_ref=lab["dslId"], trace_id=trace_id, root=root)
    grading = generate_mock_dsl_via_adapter("grading", input_ref=exam["dslId"], trace_id=trace_id, root=root)
    bundle = {"lab": lab, "exam": exam, "grading": grading}
    if include_ppt:
        bundle["ppt"] = generate_mock_dsl_via_adapter("ppt", input_ref=input_ref, trace_id=trace_id, root=root)
    return bundle


def _summarize_generation(
    kind: str,
    generation: dict[str, Any],
    *,
    content_quality_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_summary = _build_generation_quality_summary(kind, generation)
    return {
        "kind": kind,
        "outputKind": generation["outputKind"],
        "promptId": generation["promptId"],
        "dslId": generation["dslId"],
        "dslPath": generation["dslPath"],
        "status": generation["generatedStatus"],
        "reviewRequired": generation["reviewRequired"],
        "publishBlockedUntilApproved": generation["publishBlockedUntilApproved"],
        "provider": generation["provider"],
        "answerVisibleToCandidate": generation.get("answerVisibleToCandidate", False),
        "artifactGenerated": generation.get("artifactGenerated", False),
        "schemaValidated": generation.get("schemaValidated", True),
        "schemaRepair": generation.get("schemaRepair"),
        "qualitySummary": quality_summary,
        "contentQualitySummary": content_quality_summary,
    }


def _build_generation_quality_summary(kind: str, generation: dict[str, Any]) -> dict[str, Any]:
    provider = generation.get("provider", {})
    normalization = generation.get("normalization") or {}
    patches = normalization.get("patches") if isinstance(normalization, dict) else []
    if not isinstance(patches, list):
        patches = []
    schema_repair = generation.get("schemaRepair") or {}
    schema_repair_attempted = bool(
        provider.get("schemaRepairAttempted")
        or generation.get("schemaRepairAttempted")
        or (isinstance(schema_repair, dict) and schema_repair.get("attempted"))
    )
    schema_repair_applied = bool(
        provider.get("schemaRepairApplied")
        or generation.get("schemaRepairApplied")
        or (isinstance(schema_repair, dict) and schema_repair.get("applied"))
    )
    schema_validated = bool(generation.get("schemaValidated", True))
    review_required = bool(generation.get("reviewRequired", True))
    status = generation.get("generatedStatus")
    issue_count = 0
    if not schema_validated:
        issue_count += 1
    if status != "WAITING_REVIEW":
        issue_count += 1
    if not review_required:
        issue_count += 1
    return {
        "kind": kind,
        "schemaValidated": schema_validated,
        "status": status,
        "reviewRequired": review_required,
        "normalizationApplied": bool(normalization.get("applied")) if isinstance(normalization, dict) else False,
        "normalizationPatchCount": len(patches),
        "normalizationPatches": patches,
        "schemaRepairAttempted": schema_repair_attempted,
        "schemaRepairApplied": schema_repair_applied,
        "schemaRepairErrorCount": schema_repair.get("errorCount", 0) if isinstance(schema_repair, dict) else 0,
        "requestCount": provider.get("requestCount"),
        "apiSurface": provider.get("apiSurface") or generation.get("apiSurface"),
        "responseId": provider.get("responseId") or generation.get("responseId"),
        "realLlmCalled": bool(provider.get("realLlmCalled", False)),
        "needsManualReview": review_required or bool(patches) or schema_repair_applied,
        "issueCount": issue_count,
        "readyForReview": schema_validated and status == "WAITING_REVIEW" and review_required,
    }


def _build_content_quality_item(kind: str, dsl: dict[str, Any], *, bundle: dict[str, dict[str, Any]]) -> dict[str, Any]:
    spec = dsl.get("spec") if isinstance(dsl.get("spec"), dict) else {}
    issues: list[dict[str, Any]] = []

    def issue(issue_id: str, severity: str, field: str, message: str, next_action: str) -> None:
        issues.append(
            {
                "id": issue_id,
                "severity": severity,
                "field": field,
                "message": message,
                "nextAction": next_action,
            }
        )

    if kind == "lab":
        objectives = spec.get("objectives") if isinstance(spec.get("objectives"), list) else []
        steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
        if len(objectives) < 2:
            issue("lab_objective_depth", "MEDIUM", "$.spec.objectives", "学习目标少于 2 个。", "review_or_expand_lab_objectives")
        if len(steps) < 3:
            issue("lab_step_depth", "MEDIUM", "$.spec.steps", "实验步骤少于 3 个。", "review_or_expand_lab_steps")
        if any(isinstance(step, dict) and not step.get("expectedResult") for step in steps):
            issue("lab_expected_result_missing", "LOW", "$.spec.steps[].expectedResult", "部分步骤缺少预期结果。", "add_expected_results_before_import")
        coverage = {
            "objectiveTotal": len(objectives),
            "stepTotal": len(steps),
            "materialTotal": len(spec.get("materials", [])) if isinstance(spec.get("materials"), list) else 0,
        }
    elif kind == "exam":
        questions = spec.get("questions") if isinstance(spec.get("questions"), list) else []
        total_score = _positive_number(spec.get("totalScore"))
        score_sum = sum(_positive_number(item.get("score")) for item in questions if isinstance(item, dict))
        if not questions:
            issue("exam_question_missing", "HIGH", "$.spec.questions", "试题为空。", "regenerate_or_add_exam_questions")
        if total_score and score_sum and total_score != score_sum:
            issue("exam_score_mismatch", "HIGH", "$.spec.totalScore", "试题分值合计与总分不一致。", "align_question_scores")
        if any(isinstance(item, dict) and not item.get("gradingRef") for item in questions):
            issue("exam_grading_ref_missing", "HIGH", "$.spec.questions[].gradingRef", "存在题目缺少 gradingRef。", "add_teacher_only_grading_refs")
        coverage = {
            "questionTotal": len(questions),
            "totalScore": total_score,
            "questionScoreTotal": score_sum,
            "scoreMatched": not total_score or not score_sum or total_score == score_sum,
        }
    elif kind == "grading":
        checks = spec.get("checks") if isinstance(spec.get("checks"), list) else []
        plans = spec.get("assessmentPlan") if isinstance(spec.get("assessmentPlan"), list) else []
        total_score = _positive_number(spec.get("totalScore"))
        score_sum = sum(_positive_number(item.get("score")) for item in checks if isinstance(item, dict))
        exam = bundle.get("exam", {}).get("dsl", {})
        question_refs = {
            str(question.get("gradingRef") or "").strip()
            for question in (exam.get("spec", {}).get("questions", []) if isinstance(exam, dict) else [])
            if isinstance(question, dict) and question.get("gradingRef")
        }
        check_ids = {str(check.get("id") or "").strip() for check in checks if isinstance(check, dict) and check.get("id")}
        missing_refs = sorted(ref for ref in question_refs if ref and ref not in check_ids)
        if not checks:
            issue("grading_check_missing", "HIGH", "$.spec.checks", "评分 check 为空。", "generate_grading_checks")
        if missing_refs:
            issue("grading_ref_uncovered", "HIGH", "$.spec.checks[].id", "存在题目 gradingRef 未被评分 check 覆盖。", "align_grading_refs_to_checks")
        if len(plans) != len(checks):
            issue("grading_plan_check_mismatch", "MEDIUM", "$.spec.assessmentPlan", "assessmentPlan 数量与 checks 不一致。", "align_assessment_plan")
        if total_score and score_sum and total_score != score_sum:
            issue("grading_score_mismatch", "HIGH", "$.spec.totalScore", "评分 check 分值合计与总分不一致。", "align_grading_scores")
        coverage = {
            "checkTotal": len(checks),
            "assessmentPlanTotal": len(plans),
            "gradingRefsCovered": not missing_refs,
            "missingGradingRefs": missing_refs,
            "totalScore": total_score,
            "checkScoreTotal": score_sum,
            "scoreMatched": not total_score or not score_sum or total_score == score_sum,
        }
    elif kind == "ppt":
        slides = spec.get("slides") if isinstance(spec.get("slides"), list) else []
        if len(slides) < 4:
            issue("ppt_slide_depth", "LOW", "$.spec.slides", "PPT 页数少于 4 页。", "review_or_expand_slide_plan")
        if any(isinstance(slide, dict) and slide.get("type") == "content" and not slide.get("bullets") for slide in slides):
            issue("ppt_content_bullets_missing", "LOW", "$.spec.slides[].bullets", "部分内容页缺少 bullet。", "add_slide_bullets")
        coverage = {
            "slideTotal": len(slides),
            "contentSlideTotal": sum(1 for slide in slides if isinstance(slide, dict) and slide.get("type") == "content"),
        }
    else:
        coverage = {}

    blocking = sum(1 for item in issues if item["severity"] == "HIGH")
    status = "READY_FOR_MANUAL_REVIEW"
    if blocking:
        status = "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
    elif issues:
        status = "REVIEW_WITH_WARNINGS"
    decision = _build_content_quality_decision(kind, status=status, issues=issues)
    return {
        "kind": kind,
        "status": status,
        "decision": decision,
        "decisionStatus": decision["status"],
        "recommendedAction": decision["recommendedAction"],
        "requiresRevisionBeforeImportPreview": decision["requiresRevisionBeforeImportPreview"],
        "requiresEvidenceBeforeFinalApproval": decision["requiresEvidenceBeforeFinalApproval"],
        "evidenceStatus": decision["evidenceStatus"],
        "readyForManualReview": True,
        "readyForImportPreview": blocking == 0,
        "issueTotal": len(issues),
        "blockingIssueTotal": blocking,
        "warningIssueTotal": len(issues) - blocking,
        "issues": issues,
        "coverage": coverage,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _build_content_quality_decision(
    kind: str,
    *,
    status: str,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers = [
        _content_quality_decision_issue(item)
        for item in issues
        if item.get("severity") == "HIGH"
    ]
    warnings = [
        _content_quality_decision_issue(item)
        for item in issues
        if item.get("severity") != "HIGH"
    ]
    requires_revision = bool(blockers)
    requires_evidence = kind == "grading" and not requires_revision
    if requires_revision:
        decision_status = "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
        recommended_action = _first_next_action(blockers, "revise_dsl_before_import_preview")
    elif requires_evidence:
        decision_status = "READY_FOR_IMPORT_PREVIEW_EVIDENCE_REQUIRED_BEFORE_FINAL_APPROVAL"
        recommended_action = "create_import_preview_then_collect_grading_evidence"
    elif warnings:
        decision_status = "READY_FOR_IMPORT_PREVIEW_WITH_WARNINGS"
        recommended_action = _ready_recommended_action(kind, with_warnings=True)
    else:
        decision_status = "READY_FOR_IMPORT_PREVIEW"
        recommended_action = _ready_recommended_action(kind, with_warnings=False)
    return {
        "component": "RealDslContentQualityDecision",
        "kind": kind,
        "status": decision_status,
        "sourceStatus": status,
        "readyForManualReview": True,
        "readyForImportPreview": not requires_revision and kind in {"lab", "exam", "grading"},
        "requiresRevisionBeforeImportPreview": requires_revision,
        "requiresEvidenceBeforeFinalApproval": requires_evidence,
        "evidenceStatus": (
            "GRADING_EVIDENCE_REQUIRED_BEFORE_FINAL_APPROVAL"
            if requires_evidence
            else ("NOT_APPLICABLE" if kind != "grading" else "BLOCKED_BY_REVISION")
        ),
        "recommendedAction": recommended_action,
        "blockers": blockers,
        "warnings": warnings,
        "blockerTotal": len(blockers),
        "warningTotal": len(warnings),
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _content_quality_decision_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": issue.get("id"),
        "severity": issue.get("severity"),
        "field": issue.get("field"),
        "message": issue.get("message"),
        "nextAction": issue.get("nextAction"),
    }


def _first_next_action(items: list[dict[str, Any]], default: str) -> str:
    for item in items:
        action = item.get("nextAction")
        if isinstance(action, str) and action:
            return action
    return default


def _ready_recommended_action(kind: str, *, with_warnings: bool) -> str:
    if kind == "lab":
        return "review_warnings_then_create_lab_import_preview" if with_warnings else "create_lab_import_preview_after_review"
    if kind == "exam":
        return "review_warnings_then_create_exam_import_preview" if with_warnings else "create_exam_import_preview_after_review"
    if kind == "grading":
        return "create_import_preview_then_collect_grading_evidence"
    if kind == "ppt":
        return "review_warnings_then_review_ppt_pages" if with_warnings else "review_ppt_pages"
    return "manual_review_required"


def _positive_number(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0:
        return int(value)
    return 0


def _build_content_quality_summary(bundle: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items = {
        kind: _build_content_quality_item(kind, generation.get("dsl", {}), bundle=bundle)
        for kind, generation in bundle.items()
    }
    blocking_total = sum(item["blockingIssueTotal"] for item in items.values())
    issue_total = sum(item["issueTotal"] for item in items.values())
    ready_for_import_kinds = [
        kind
        for kind, item in items.items()
        if item.get("readyForImportPreview") is True and kind in {"lab", "exam", "grading"}
    ]
    decision = _build_content_quality_summary_decision(items)
    return {
        "component": "RealDslContentQualitySummary",
        "source": "provider_adapter_workflow.generatedDsl.dsl",
        "status": (
            "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
            if blocking_total
            else ("REVIEW_WITH_WARNINGS" if issue_total else "READY_FOR_MANUAL_REVIEW")
        ),
        "decision": decision,
        "decisionStatus": decision["status"],
        "recommendedAction": decision["recommendedAction"],
        "requiresRevisionBeforeImportPreview": decision["requiresRevisionBeforeImportPreview"],
        "requiresEvidenceBeforeFinalApproval": decision["requiresEvidenceBeforeFinalApproval"],
        "itemTotal": len(items),
        "issueTotal": issue_total,
        "blockingIssueTotal": blocking_total,
        "readyForReviewTotal": sum(1 for item in items.values() if item.get("readyForManualReview")),
        "readyForImportPreviewKinds": ready_for_import_kinds,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "items": items,
    }


def _build_content_quality_summary_decision(items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    item_decisions = {
        kind: item.get("decision", {})
        for kind, item in items.items()
        if isinstance(item.get("decision"), dict)
    }
    blockers = [
        blocker
        for decision in item_decisions.values()
        for blocker in decision.get("blockers", [])
        if isinstance(blocker, dict)
    ]
    warnings = [
        warning
        for decision in item_decisions.values()
        for warning in decision.get("warnings", [])
        if isinstance(warning, dict)
    ]
    evidence_kinds = sorted(
        kind
        for kind, decision in item_decisions.items()
        if decision.get("requiresEvidenceBeforeFinalApproval") is True
    )
    if blockers:
        status = "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
        recommended_action = "revise_blocked_dsl_before_import_preview"
    elif evidence_kinds:
        status = "READY_FOR_IMPORT_PREVIEW_EVIDENCE_REQUIRED_BEFORE_FINAL_APPROVAL"
        recommended_action = "create_import_previews_then_collect_required_evidence"
    elif warnings:
        status = "READY_FOR_IMPORT_PREVIEW_WITH_WARNINGS"
        recommended_action = "review_warnings_then_create_import_previews"
    else:
        status = "READY_FOR_IMPORT_PREVIEW"
        recommended_action = "create_import_previews_after_manual_review"
    return {
        "component": "RealDslContentQualityDecision",
        "status": status,
        "readyForManualReview": True,
        "readyForImportPreview": not blockers,
        "requiresRevisionBeforeImportPreview": bool(blockers),
        "requiresEvidenceBeforeFinalApproval": bool(evidence_kinds),
        "evidenceRequiredKinds": evidence_kinds,
        "recommendedAction": recommended_action,
        "blockers": blockers,
        "warnings": warnings,
        "blockerTotal": len(blockers),
        "warningTotal": len(warnings),
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _material_step_detail(material_analysis: dict[str, Any] | None) -> dict[str, Any]:
    if material_analysis is None:
        return {
            "mode": "MOCK_ONLY",
            "materialAnalysisAvailable": False,
            "unknownShellExecuted": False,
            "requiresHumanReview": True,
        }
    return {
        "mode": material_analysis.get("mode", "MOCK_ONLY"),
        "materialAnalysisAvailable": True,
        "title": material_analysis.get("title"),
        "fileType": material_analysis.get("fileType"),
        "riskCount": material_analysis.get("riskCount", 0),
        "unknownShellExecuted": material_analysis.get("unknownShellExecuted", False),
        "requiresHumanReview": material_analysis.get("requiresHumanReview", True),
    }


def _list_from_lab_dsl(lab_dsl: dict[str, Any], key: str) -> list[str]:
    value = lab_dsl.get("spec", {}).get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _metadata_list(metadata: dict[str, Any], key: str) -> list[str]:
    value = metadata.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _normalized_set(values: list[str]) -> set[str]:
    return {value.strip().casefold() for value in values if value.strip()}


def _match_signal(*, requested: Any, actual: Any, matched: bool, severity: str = "review") -> dict[str, Any]:
    return {
        "matched": matched,
        "severity": "info" if matched else severity,
        "requested": requested,
        "actual": actual,
    }


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").casefold()


def _path_matches(reference: Any, candidate: Any) -> bool:
    normalized_reference = _normalized_text(reference)
    normalized_candidate = _normalized_text(candidate)
    if not normalized_reference or not normalized_candidate:
        return False
    return (
        normalized_reference == normalized_candidate
        or normalized_reference.endswith("/" + normalized_candidate)
        or normalized_candidate.endswith("/" + normalized_reference)
    )


def _material_paths_from_lab_dsl(lab_dsl: dict[str, Any]) -> list[str]:
    materials = lab_dsl.get("spec", {}).get("materials")
    if not isinstance(materials, list):
        return []
    return [
        str(item.get("path"))
        for item in materials
        if isinstance(item, dict) and item.get("path")
    ]


def _teaching_style_signal(requested_style: str, steps: Any) -> dict[str, Any]:
    style_keywords = {
        "guided_practice": ["检查", "确认", "步骤", "完成", "guided", "practice"],
        "project_based": ["项目", "作品", "交付", "构建", "project", "deliverable", "build"],
        "challenge_based": ["挑战", "排错", "独立", "challenge", "troubleshoot"],
        "lecture_demo": ["演示", "讲解", "教师", "demo", "lecture"],
    }
    step_items = steps if isinstance(steps, list) else []
    text_parts: list[str] = []
    complete_step_count = 0
    for step in step_items:
        if not isinstance(step, dict):
            continue
        if step.get("id") and step.get("title") and step.get("instruction"):
            complete_step_count += 1
        text_parts.extend(
            str(value)
            for key, value in step.items()
            if key in {"title", "instruction", "expectedResult"} and value
        )
    normalized_text = _normalized_text(" ".join(text_parts))
    keywords = style_keywords.get(requested_style, [])
    evidence_keywords = [keyword for keyword in keywords if _normalized_text(keyword) in normalized_text]
    inferred_match = bool(evidence_keywords)
    if requested_style == "guided_practice" and complete_step_count > 0:
        inferred_match = True
    return {
        "status": "MATCHED" if inferred_match else "NEEDS_REVIEW",
        "requestedStyle": requested_style,
        "matched": inferred_match,
        "evidenceKeywords": evidence_keywords,
        "completeStepCount": complete_step_count,
    }


def _lab_quality_signals(
    *,
    bundle: dict[str, dict[str, Any]],
    material_analysis: dict[str, Any] | None,
    lab_generation_context: dict[str, Any],
    real_llm_source_mode: str | None,
) -> dict[str, Any]:
    lab_generation = bundle["lab"]
    lab_dsl = lab_generation.get("dsl", {})
    metadata = lab_dsl.get("metadata", {}) if isinstance(lab_dsl, dict) else {}
    provider = lab_generation.get("provider", {})
    input_ref = lab_generation.get("inputRef")
    objectives = _list_from_lab_dsl(lab_dsl, "objectives") if isinstance(lab_dsl, dict) else []
    steps = lab_dsl.get("spec", {}).get("steps", []) if isinstance(lab_dsl, dict) else []
    material_paths = _material_paths_from_lab_dsl(lab_dsl) if isinstance(lab_dsl, dict) else []
    target_users = _list_from_lab_dsl(lab_dsl, "targetUsers") if isinstance(lab_dsl, dict) else []
    tags = _metadata_list(metadata, "tags")
    dsl_duration = metadata.get("durationMinutes")
    requested_duration = lab_generation_context["durationMinutes"]
    requested_users = lab_generation_context["targetUsers"]
    requested_tags = lab_generation_context["techTags"]
    difficulty = metadata.get("difficulty")
    requested_difficulty = lab_generation_context["difficulty"]
    requested_user_set = _normalized_set(requested_users)
    dsl_user_set = _normalized_set(target_users)
    requested_tag_set = _normalized_set(requested_tags)
    dsl_tag_set = _normalized_set(tags)
    valid_steps = [
        step
        for step in steps
        if isinstance(step, dict) and step.get("id") and step.get("title") and step.get("instruction")
    ] if isinstance(steps, list) else []
    steps_count = len(steps) if isinstance(steps, list) else 0
    missing_expected_result_count = (
        sum(1 for step in steps if isinstance(step, dict) and not step.get("expectedResult"))
        if isinstance(steps, list)
        else 0
    )
    target_users_match = dsl_user_set.issuperset(requested_user_set)
    duration_match = dsl_duration == requested_duration
    difficulty_match = difficulty == requested_difficulty
    tags_match = dsl_tag_set.issuperset(requested_tag_set)
    step_granularity_match = steps_count >= 1 and len(valid_steps) == steps_count
    teaching_style_signal = _teaching_style_signal(lab_generation_context["teachingStyle"], steps)
    teaching_style_match = bool(teaching_style_signal["matched"])
    source_referenced_in_dsl = any(_path_matches(input_ref, path) for path in material_paths)
    material_risk_count = material_analysis.get("riskCount", 0) if material_analysis else 0
    unknown_shell_executed = (
        material_analysis.get("unknownShellExecuted", False) if material_analysis else False
    )
    review_highlights = [
        "确认 Lab DSL 内容与输入素材一致",
        "确认生成内容保持 WAITING_REVIEW 且未自动发布",
    ]
    if input_ref and not source_referenced_in_dsl:
        review_highlights.append("确认 Lab materials 是否引用输入素材")
    if material_risk_count > 0 or unknown_shell_executed:
        review_highlights.append("确认输入素材风险项是否已人工复核")
    if not target_users_match:
        review_highlights.append("确认目标用户是否覆盖本次生成参数")
    if not duration_match:
        review_highlights.append("确认课时是否符合本次生成参数")
    if not difficulty_match:
        review_highlights.append("确认难度是否符合本次生成参数")
    if requested_tags and not tags_match:
        review_highlights.append("确认技术标签是否覆盖本次生成参数")
    if not step_granularity_match:
        review_highlights.append("确认实验步骤粒度和必填字段是否完整")
    if not teaching_style_match:
        review_highlights.append("确认教学风格是否符合本次生成参数")
    if real_llm_source_mode == REAL_LLM_SOURCE_MODE_MINIMAL:
        review_highlights.append(
            "真实 LLM 仅用于 Lab DSL，Exam/Grading/PPT 仍为 Mock"
            if "ppt" in bundle
            else "真实 LLM 仅用于 Lab DSL，Exam/Grading 仍为 Mock"
        )
    elif real_llm_source_mode == REAL_LLM_SOURCE_MODE_OFFICIAL:
        review_highlights.append(
            "真实 LLM 已生成 Lab/Exam/Grading/PPT 四类 DSL，全部仍需人工审核"
            if "ppt" in bundle
            else "真实 LLM 已生成 Lab/Exam/Grading 三类核心 DSL，全部仍需人工审核"
        )
    elif real_llm_source_mode == REAL_LLM_SOURCE_MODE_DEMO:
        review_highlights.append(
            "真实 LLM Demo 已生成 Lab/Exam/Grading/PPT 四类 DSL，全部仍需人工审核"
            if "ppt" in bundle
            else "真实 LLM Demo 已生成 Lab/Exam/Grading 三类核心 DSL，全部仍需人工审核"
        )

    schema_checks = {
        kind: {
            "schemaValidated": bool(generation.get("schemaValidated", True)),
            "status": generation.get("generatedStatus"),
            "reviewRequired": bool(generation.get("reviewRequired")),
        }
        for kind, generation in bundle.items()
    }
    return {
        "overall": {
            "status": "READY_FOR_HUMAN_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "schemaValidated": all(item["schemaValidated"] for item in schema_checks.values()),
            "needsHumanReview": True,
            "reviewHighlightCount": len(review_highlights),
        },
        "lab": {
            "status": "READY_FOR_HUMAN_REVIEW",
            "objectivesCount": len(objectives),
            "stepsCount": steps_count,
            "durationMinutes": dsl_duration,
            "requestedDurationMinutes": requested_duration,
            "durationMatchesRequest": duration_match,
            "targetUsers": target_users,
            "requestedTargetUsers": requested_users,
            "targetUsersCoverRequest": target_users_match,
            "difficulty": difficulty,
            "requestedDifficulty": requested_difficulty,
            "difficultyMatchesRequest": difficulty_match,
            "tags": tags,
            "requestedTechTags": requested_tags,
            "techTagsCoverRequest": tags_match,
            "teachingStyle": lab_generation_context["teachingStyle"],
            "teachingStyleSignal": teaching_style_signal,
            "teachingStyleMatchesRequest": teaching_style_match,
            "stepGranularity": {
                "status": "READY_FOR_REVIEW" if step_granularity_match else "NEEDS_REVIEW",
                "matched": step_granularity_match,
                "stepsCount": steps_count,
                "validStepCount": len(valid_steps),
                "missingExpectedResultCount": missing_expected_result_count,
            },
            "matching": {
                "status": "MATCHED" if all(
                    [
                        target_users_match,
                        duration_match,
                        difficulty_match,
                        tags_match,
                        step_granularity_match,
                        teaching_style_match,
                    ]
                ) else "NEEDS_REVIEW",
                "targetUsers": _match_signal(requested=requested_users, actual=target_users, matched=target_users_match),
                "durationMinutes": _match_signal(
                    requested=requested_duration,
                    actual=dsl_duration,
                    matched=duration_match,
                ),
                "difficulty": _match_signal(
                    requested=requested_difficulty,
                    actual=difficulty,
                    matched=difficulty_match,
                ),
                "techTags": _match_signal(requested=requested_tags, actual=tags, matched=tags_match),
                "stepGranularity": _match_signal(
                    requested="at least one complete step with id/title/instruction",
                    actual={"stepsCount": steps_count, "validStepCount": len(valid_steps)},
                    matched=step_granularity_match,
                ),
                "teachingStyle": _match_signal(
                    requested=lab_generation_context["teachingStyle"],
                    actual=teaching_style_signal,
                    matched=teaching_style_match,
                ),
            },
            "provider": {
                "adapterId": provider.get("adapterId"),
                "providerId": provider.get("providerId"),
                "mode": provider.get("mode"),
                "realLlmCalled": bool(provider.get("realLlmCalled", False)),
                "responseId": provider.get("responseId"),
            },
        },
        "materialCoverage": {
            "available": material_analysis is not None,
            "fileType": material_analysis.get("fileType") if material_analysis else None,
            "riskCount": material_risk_count,
            "unknownShellExecuted": unknown_shell_executed,
            "sourceLinked": source_referenced_in_dsl,
            "inputRef": input_ref,
            "referencedPaths": material_paths,
            "sourceReferencedInDsl": source_referenced_in_dsl,
            "status": "LINKED" if source_referenced_in_dsl else "NEEDS_REVIEW",
            "riskReview": {
                "status": "NEEDS_REVIEW" if material_risk_count > 0 or unknown_shell_executed else "CLEAR",
                "riskCount": material_risk_count,
                "unknownShellExecuted": unknown_shell_executed,
            },
        },
        "schemaChecks": schema_checks,
        "reviewHighlights": review_highlights,
    }


def run_phase2_content_generation(
    *,
    input_ref: str,
    reviewer: str,
    trace_id: str,
    root: Path = ROOT,
    material_analysis: dict[str, Any] | None = None,
    provider_mode: str = PROVIDER_MODE_MOCK,
    lab_generation_context: dict[str, Any] | None = None,
    real_lab_output_ref: str = REAL_LLM_MINIMAL_LAB_OUTPUT_REF,
    real_output_refs: dict[str, str] | None = None,
    real_demo_output_refs: dict[str, str] | None = None,
    real_llm_model: str | None = None,
    real_llm_base_url: str | None = None,
    timeout_seconds: int = 60,
    max_output_tokens: int = 1800,
    explicit_real_call_opt_in: bool = False,
    confirm_single_request: bool = False,
    confirm_lab_only: bool = False,
    confirm_waiting_review: bool = False,
    confirm_no_auto_publish: bool = False,
    repair_on_schema_failure: bool = False,
    api_surface: str = "auto",
    artifact_profile: str = ARTIFACT_PROFILE_LEGACY_ALL,
) -> dict[str, Any]:
    artifact_kinds = ARTIFACT_KINDS_BY_PROFILE.get(artifact_profile)
    if artifact_kinds is None:
        raise ProviderError(
            "PHASE2_ARTIFACT_PROFILE_INVALID",
            "Phase 2 Workflow 不支持的 artifact profile",
            [{"field": "artifactProfile", "reason": artifact_profile}],
        )
    normalized_lab_context = normalize_lab_generation_context(lab_generation_context)
    bundle = generate_workflow_dsl_bundle(
        input_ref=input_ref,
        trace_id=trace_id,
        root=root,
        provider_mode=provider_mode,
        lab_generation_context=normalized_lab_context,
        real_lab_output_ref=real_lab_output_ref,
        real_output_refs=real_output_refs,
        real_demo_output_refs=real_demo_output_refs,
        real_llm_model=real_llm_model,
        real_llm_base_url=real_llm_base_url,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        explicit_real_call_opt_in=explicit_real_call_opt_in,
        confirm_single_request=confirm_single_request,
        confirm_lab_only=confirm_lab_only,
        confirm_waiting_review=confirm_waiting_review,
        confirm_no_auto_publish=confirm_no_auto_publish,
        repair_on_schema_failure=repair_on_schema_failure,
        api_surface=api_surface,
        artifact_kinds=artifact_kinds,
    )
    real_lab_mode = provider_mode == PROVIDER_MODE_REAL_LLM_MINIMAL
    real_llm_mode = provider_mode == PROVIDER_MODE_REAL_LLM
    real_demo_mode = provider_mode == PROVIDER_MODE_REAL_LLM_DEMO
    if real_llm_mode:
        workflow_mode = PHASE2_REAL_LLM_MODE
        provider_adapter = REAL_LLM_PROVIDER_ADAPTER
    elif real_demo_mode:
        workflow_mode = PHASE2_REAL_LLM_DEMO_MODE
        provider_adapter = REAL_LLM_DEMO_PROVIDER_ADAPTER
    elif real_lab_mode:
        workflow_mode = PHASE2_REAL_LLM_MINIMAL_MODE
        provider_adapter = MIXED_REAL_LLM_MINIMAL_PROVIDER_ADAPTER
    else:
        workflow_mode = PHASE2_MOCK_ONLY_MODE
        provider_adapter = "mock_provider_adapter"
    safety = dict(PHASE2_SAFETY)
    if real_lab_mode or real_llm_mode or real_demo_mode:
        safety.update(
            {
                "realLlmCalled": True,
                "secretsRead": True,
                "networkAccess": True,
                "realLlmGeneratedKinds": [
                    kind
                    for kind, generation in bundle.items()
                    if generation.get("provider", {}).get("realLlmCalled") is True
                ],
                "realLlmRequestCount": sum(
                    int(generation.get("provider", {}).get("requestCount", 0) or 0)
                    for generation in bundle.values()
                    if generation.get("provider", {}).get("realLlmCalled") is True
                ),
            }
        )
    real_llm_source_mode = None
    if real_lab_mode:
        real_llm_source_mode = REAL_LLM_SOURCE_MODE_MINIMAL
    elif real_llm_mode:
        real_llm_source_mode = REAL_LLM_SOURCE_MODE_OFFICIAL
    elif real_demo_mode:
        real_llm_source_mode = REAL_LLM_SOURCE_MODE_DEMO
    quality_signals = _lab_quality_signals(
        bundle=bundle,
        material_analysis=material_analysis,
        lab_generation_context=normalized_lab_context,
        real_llm_source_mode=real_llm_source_mode,
    )
    content_quality_summary = _build_content_quality_summary(bundle)
    generated_dsl = {
        kind: _summarize_generation(
            kind,
            generation,
            content_quality_summary=content_quality_summary["items"].get(kind),
        )
        for kind, generation in bundle.items()
    }
    generation_steps = [
        {
            "name": PHASE2_GENERATION_STEP_BY_KIND[kind],
            "kind": kind,
            "status": generation["generatedStatus"],
            "generatedStatus": generation["generatedStatus"],
            "promptId": generation["promptId"],
            "dslId": generation["dslId"],
            "dslPath": generation["dslPath"],
            "provider": generation["provider"],
            "providerMode": generation["provider"].get("mode"),
            "reviewRequired": generation["reviewRequired"],
            "publishBlockedUntilApproved": generation["publishBlockedUntilApproved"],
            "labGenerationContext": normalized_lab_context if kind == "lab" else None,
            "qualitySignals": quality_signals.get("lab") if kind == "lab" else None,
        }
        for kind, generation in bundle.items()
    ]
    return {
        "id": f"phase2_report_{uuid4().hex[:12]}",
        "workflowId": PHASE2_WORKFLOW_ID,
        "phase": "Phase 2",
        "mode": workflow_mode,
        "providerMode": provider_mode,
        "artifactProfile": artifact_profile,
        "generatedKinds": list(artifact_kinds),
        "title": (
            "Phase 2 Real LLM Workflow"
            if real_llm_mode
            else (
                "Phase 2 Real LLM Demo Workflow"
                if real_demo_mode
                else ("Phase 2 Real LLM Minimal Lab Workflow" if real_lab_mode else "Phase 2 Mock Content Generation Workflow")
            )
        ),
        "input": input_ref,
        "reviewer": reviewer,
        "labGenerationContext": normalized_lab_context,
        "qualitySignals": quality_signals,
        "contentQualitySummary": content_quality_summary,
        "providerAdapter": provider_adapter,
        "providerInterface": "LLMProvider",
        "workflowContract": "ai-workflows/phase2-content-generation.contract.json",
        "providerAdapterContract": "providers/provider-adapter.contract.json",
        "realLlmMinimalPocDoc": "docs/15_REAL_LLM_MINIMAL_POC.md" if real_lab_mode else None,
        "realLlmWorkflowDoc": "docs/AI_PLATFORM_CODEX_FULL_GUIDE.md" if real_llm_mode else None,
        "realLlmDemoDoc": "docs/18_REAL_LLM_DEMO_WORKFLOW.md" if real_demo_mode else None,
        "promptManifest": "prompts/manifest.json",
        "steps": [
            {
                "name": "validate_input",
                "status": "COMPLETED",
                "inputRef": input_ref,
                "localOnly": True,
                "labGenerationContext": normalized_lab_context,
            },
            {
                "name": "analyze_material",
                "status": "COMPLETED",
                "materialAnalysis": _material_step_detail(material_analysis),
            },
            *generation_steps,
            {
                "name": "assemble_review_bundle",
                "status": "COMPLETED",
                "generatedKinds": list(generated_dsl),
                "reviewRequired": True,
                "publishBlockedUntilApproved": True,
                "answerVisibleToCandidate": False,
                "realPublish": False,
                "qualitySignals": quality_signals,
                "contentQualitySummary": content_quality_summary,
            },
        ],
        "generatedDsl": generated_dsl,
        "providerGenerations": bundle,
        "reviewSummary": {
            "generatedStatus": "WAITING_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "answerVisibleToCandidate": False,
            "autoPublishAllowed": False,
            "qualitySignals": quality_signals["overall"],
            "reviewHighlights": quality_signals["reviewHighlights"],
            "contentQualitySummary": {
                "status": content_quality_summary["status"],
                "issueTotal": content_quality_summary["issueTotal"],
                "blockingIssueTotal": content_quality_summary["blockingIssueTotal"],
                "readyForImportPreviewKinds": content_quality_summary["readyForImportPreviewKinds"],
            },
        },
        "acceptanceSignals": {
            "providerAdapterUsed": True,
            "schemaValidated": True,
            "promptManifestReferenced": True,
            "allGeneratedDslWaitingReview": True,
            "reviewGateRequired": True,
            "mockOnly": not (real_lab_mode or real_llm_mode or real_demo_mode),
            "realLlmConnected": real_llm_mode,
            "realLlmGeneratedAllDsl": real_llm_mode and set(safety.get("realLlmGeneratedKinds", [])) == set(artifact_kinds),
            "realLlmRequestCount": safety.get("realLlmRequestCount", 0) if real_llm_mode else 0,
            "realLlmDemoConnected": real_demo_mode,
            "realLlmDemoGeneratedAllDsl": real_demo_mode and set(safety.get("realLlmGeneratedKinds", [])) == set(artifact_kinds),
            "realLlmDemoRequestCount": safety.get("realLlmRequestCount", 0) if real_demo_mode else 0,
            "realLlmMinimalLabConnected": real_lab_mode,
            "realLabOnly": real_lab_mode,
            "singleRequestOnly": real_lab_mode,
            "labGenerationContextCaptured": True,
            "qualitySignalsGenerated": True,
        },
        "safety": safety,
        "traceId": trace_id,
    }


def _resolve_output_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path
