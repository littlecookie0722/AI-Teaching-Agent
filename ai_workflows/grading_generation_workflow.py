"""Phase 2 mock grading generation workflow helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from providers import ProviderError

from .exam_conversion_workflow import _build_assessment_plan
from .provider_adapter_workflow import PHASE2_SAFETY, generate_mock_dsl_via_adapter


ROOT = Path(__file__).resolve().parents[1]
PHASE2_GRADING_WORKFLOW_ID = "phase2_grading_generation"
PHASE2_GRADING_STEP_BY_KIND = {"grading": "generate_grading_dsl"}


class GradingGenerationInputError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _load_exam_summary(exam_path: Path, root: Path) -> dict[str, Any]:
    try:
        exam_dsl = load_yaml(exam_path)
        validate_dsl(exam_dsl, load_schema("exam", root))
    except DslValidationError as exc:
        raise GradingGenerationInputError("SCHEMA_VALIDATION_ERROR", "Exam DSL Schema 校验失败", exc.errors) from exc
    if not isinstance(exam_dsl, dict):
        raise GradingGenerationInputError("SCHEMA_VALIDATION_ERROR", "Exam DSL Schema 校验失败", [{"field": "$", "reason": "root must be object"}])
    metadata = exam_dsl.get("metadata", {})
    spec = exam_dsl.get("spec", {})
    questions = spec.get("questions", []) if isinstance(spec.get("questions"), list) else []
    grading_refs = [
        str(question.get("gradingRef"))
        for question in questions
        if isinstance(question, dict) and question.get("gradingRef")
    ]
    return {
        "path": str(exam_path),
        "examId": metadata.get("id"),
        "title": metadata.get("title"),
        "sourceLabId": metadata.get("sourceLabId"),
        "difficulty": metadata.get("difficulty"),
        "status": exam_dsl.get("status"),
        "questionType": spec.get("questionType"),
        "questionCount": len(questions),
        "totalScore": int(spec.get("totalScore", 0) or 0),
        "gradingRefs": grading_refs,
        "answerVisibleToCandidate": False,
    }


def _summarize_generation(generation: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "grading",
        "outputKind": generation["outputKind"],
        "promptId": generation["promptId"],
        "dslId": generation["dslId"],
        "dslPath": generation["dslPath"],
        "status": generation["generatedStatus"],
        "reviewRequired": generation["reviewRequired"],
        "publishBlockedUntilApproved": generation["publishBlockedUntilApproved"],
        "provider": generation["provider"],
        "sandboxRequiredBeforeRealExecution": generation.get("sandboxRequiredBeforeRealExecution", True),
    }


def _list_from_spec(dsl: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = dsl.get("spec", {}).get(key)
    return value if isinstance(value, list) else []


def _build_grading_quality_signals(*, exam_summary: dict[str, Any], grading_dsl: dict[str, Any]) -> dict[str, Any]:
    spec = grading_dsl.get("spec", {})
    checks = _list_from_spec(grading_dsl, "checks")
    assessment_plan = spec.get("assessmentPlan")
    if not isinstance(assessment_plan, list) or not assessment_plan:
        assessment_plan = _build_assessment_plan(checks, int(spec.get("timeoutSeconds", 0) or 0))

    check_ids = [str(check.get("id")) for check in checks if isinstance(check, dict) and check.get("id")]
    check_types = [str(check.get("type")) for check in checks if isinstance(check, dict) and check.get("type")]
    check_score_total = sum(int(check.get("score", 0) or 0) for check in checks if isinstance(check, dict))
    grading_refs = [str(ref) for ref in exam_summary.get("gradingRefs", [])]
    missing_refs = [ref for ref in grading_refs if ref not in set(check_ids)]
    extra_checks = [check_id for check_id in check_ids if check_id not in set(grading_refs)]
    plan_check_ids = [str(plan.get("checkId")) for plan in assessment_plan if isinstance(plan, dict) and plan.get("checkId")]
    supported_types = {"file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword"}
    unsupported_types = [check_type for check_type in check_types if check_type not in supported_types]
    total_score = int(spec.get("totalScore", 0) or 0)
    score_matched = total_score > 0 and total_score == int(exam_summary.get("totalScore", 0) or 0) and total_score == check_score_total
    refs_matched = bool(grading_refs) and not missing_refs
    plan_aligned = check_ids == plan_check_ids
    plan_has_report_detail_fields = len(assessment_plan) == len(checks) and all(
        isinstance(plan, dict)
        and plan.get("inputSummary")
        and plan.get("executionPlan", {}).get("strategy") == "MOCK_PLAN_ONLY"
        and plan.get("executionPlan", {}).get("requiredLimits", {}).get("network") == "disabled_by_default"
        and plan.get("mockEvidence", {}).get("status") == "MOCK_EVIDENCE_NOT_COLLECTED"
        and plan.get("sandboxRequiredBeforeRealExecution") is True
        for plan in assessment_plan
    )
    explainable = bool(checks) and not unsupported_types and score_matched and plan_aligned and plan_has_report_detail_fields
    review_highlights = [
        "确认 Grading DSL 分值与 Exam DSL 总分一致",
        "确认 gradingRef 与 checks.id 一一覆盖",
        "确认 assessmentPlan 可解释且真实执行前需要沙箱证据",
    ]
    if missing_refs:
        review_highlights.append("确认缺失 gradingRef 对应的评分检查")
    if extra_checks:
        review_highlights.append("确认额外评分检查是否符合题目要求")
    if unsupported_types:
        review_highlights.append("确认暂不支持的评分类型是否需要人工改写")

    return {
        "overall": {
            "status": "READY_FOR_HUMAN_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "gradingPlanExplainable": explainable,
            "needsHumanReview": True,
            "reviewHighlightCount": len(review_highlights),
        },
        "grading": {
            "status": "READY_FOR_HUMAN_REVIEW",
            "sourceExamId": grading_dsl.get("metadata", {}).get("sourceExamId"),
            "sourceExamLinked": grading_dsl.get("metadata", {}).get("sourceExamId") == exam_summary.get("examId"),
            "checkCount": len(checks),
            "totalScore": total_score,
            "checkScoreTotal": check_score_total,
            "scoreMatchesExam": score_matched,
            "checkIds": check_ids,
            "checkTypes": check_types,
            "unsupportedCheckTypes": unsupported_types,
            "assessmentPlan": assessment_plan,
            "sandboxRequiredBeforeRealExecution": True,
        },
        "coverage": {
            "gradingRefCoverage": {
                "status": "MATCHED" if refs_matched else "NEEDS_REVIEW",
                "matched": refs_matched,
                "requestedRefs": grading_refs,
                "availableCheckIds": check_ids,
                "missingRefs": missing_refs,
                "extraChecks": extra_checks,
            },
            "scoreCoverage": {
                "status": "MATCHED" if score_matched else "NEEDS_REVIEW",
                "matched": score_matched,
                "examTotalScore": exam_summary.get("totalScore"),
                "gradingTotalScore": total_score,
                "checkScoreTotal": check_score_total,
            },
            "explainability": {
                "status": "EXPLAINABLE" if explainable else "NEEDS_REVIEW",
                "matched": explainable,
                "deterministicCheckTypesOnly": not unsupported_types,
                "assessmentPlanAlignedWithChecks": plan_aligned,
                "assessmentPlanHasReportDetailFields": plan_has_report_detail_fields,
                "mockEvidenceStatus": "MOCK_EVIDENCE_NOT_COLLECTED",
                "executionStrategy": "MOCK_PLAN_ONLY",
                "sandboxRequiredBeforeRealExecution": True,
            },
        },
        "reviewHighlights": review_highlights,
    }


def run_phase2_grading_generation(
    *,
    exam_path: Path,
    reviewer: str,
    trace_id: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    exam_summary = _load_exam_summary(exam_path, root)
    exam_id = str(exam_summary["examId"])
    try:
        grading = generate_mock_dsl_via_adapter("grading", input_ref=exam_id, trace_id=trace_id, root=root)
    except ProviderError:
        raise
    quality_signals = _build_grading_quality_signals(exam_summary=exam_summary, grading_dsl=grading["dsl"])
    generated_dsl = {"grading": _summarize_generation(grading)}
    generation_step = {
        "name": PHASE2_GRADING_STEP_BY_KIND["grading"],
        "kind": "grading",
        "status": grading["generatedStatus"],
        "generatedStatus": grading["generatedStatus"],
        "promptId": grading["promptId"],
        "dslId": grading["dslId"],
        "dslPath": grading["dslPath"],
        "provider": grading["provider"],
        "reviewRequired": grading["reviewRequired"],
        "publishBlockedUntilApproved": grading["publishBlockedUntilApproved"],
        "qualitySignals": quality_signals["grading"],
    }
    return {
        "id": f"phase2_grading_report_{uuid4().hex[:12]}",
        "workflowId": PHASE2_GRADING_WORKFLOW_ID,
        "phase": "Phase 2",
        "mode": "MOCK_ONLY",
        "title": "Phase 2 Mock Grading Generation Workflow",
        "examDslInput": exam_summary,
        "reviewer": reviewer,
        "providerAdapter": "mock_provider_adapter",
        "providerInterface": "LLMProvider",
        "workflowContract": "ai-workflows/phase2-grading-generation.contract.json",
        "providerAdapterContract": "providers/provider-adapter.contract.json",
        "promptManifest": "prompts/manifest.json",
        "steps": [
            {"name": "validate_exam_dsl", "status": "COMPLETED", "examId": exam_summary["examId"], "examPath": str(exam_path)},
            generation_step,
            {
                "name": "assemble_grading_review_bundle",
                "status": "COMPLETED",
                "generatedKinds": list(generated_dsl),
                "reviewRequired": True,
                "publishBlockedUntilApproved": True,
                "realPublish": False,
                "qualitySignals": quality_signals,
            },
        ],
        "generatedDsl": generated_dsl,
        "providerGenerations": {"grading": grading},
        "qualitySignals": quality_signals,
        "reviewSummary": {
            "generatedStatus": "WAITING_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "autoPublishAllowed": False,
            "qualitySignals": quality_signals["overall"],
            "reviewHighlights": quality_signals["reviewHighlights"],
        },
        "acceptanceSignals": {
            "examDslValidated": True,
            "providerAdapterUsed": True,
            "schemaValidated": True,
            "generatedDslWaitingReview": True,
            "gradingRefsCovered": quality_signals["coverage"]["gradingRefCoverage"]["matched"],
            "scoreCoverageMatched": quality_signals["coverage"]["scoreCoverage"]["matched"],
            "gradingPlanExplainable": quality_signals["coverage"]["explainability"]["matched"],
            "mockOnly": True,
        },
        "safety": dict(PHASE2_SAFETY),
        "traceId": trace_id,
    }
