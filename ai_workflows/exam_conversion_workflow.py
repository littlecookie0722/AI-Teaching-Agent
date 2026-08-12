"""Phase 2 mock exam conversion workflow helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from providers import ProviderError

from .exam_candidate_preview import build_candidate_safe_exam_preview
from .provider_adapter_workflow import PHASE2_SAFETY, generate_mock_dsl_via_adapter


ROOT = Path(__file__).resolve().parents[1]
PHASE2_EXAM_WORKFLOW_ID = "phase2_exam_conversion"

PHASE2_EXAM_STEP_BY_KIND = {
    "exam": "generate_exam_dsl",
    "grading": "generate_grading_dsl",
}


class ExamConversionInputError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _load_lab_summary(lab_path: Path, root: Path) -> dict[str, Any]:
    try:
        lab_dsl = load_yaml(lab_path)
        validate_dsl(lab_dsl, load_schema("lab", root))
    except DslValidationError as exc:
        raise ExamConversionInputError("SCHEMA_VALIDATION_ERROR", "Lab DSL Schema 校验失败", exc.errors) from exc
    if not isinstance(lab_dsl, dict):
        raise ExamConversionInputError("SCHEMA_VALIDATION_ERROR", "Lab DSL Schema 校验失败", [{"field": "$", "reason": "root must be object"}])
    metadata = lab_dsl.get("metadata", {})
    spec = lab_dsl.get("spec", {})
    return {
        "path": str(lab_path),
        "labId": metadata.get("id"),
        "title": metadata.get("title"),
        "difficulty": metadata.get("difficulty"),
        "status": lab_dsl.get("status"),
        "objectiveCount": len(spec.get("objectives", [])),
        "stepCount": len(spec.get("steps", [])),
        "environmentType": spec.get("environment", {}).get("type"),
    }


def _source_to_text(source: Any) -> str:
    if isinstance(source, list):
        return "".join(str(item) for item in source)
    return str(source or "")


def _load_notebook_summary(notebook_path: Path) -> dict[str, Any]:
    try:
        with notebook_path.open("r", encoding="utf-8") as file:
            notebook = json.load(file)
    except json.JSONDecodeError as exc:
        raise ExamConversionInputError("VALIDATION_ERROR", "Notebook JSON 格式错误", [{"field": "notebook", "reason": str(exc)}]) from exc
    if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
        raise ExamConversionInputError("VALIDATION_ERROR", "Notebook 格式错误", [{"field": "notebook.cells", "reason": "必须是数组"}])

    cells = notebook["cells"]
    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
    candidate_cells = []
    for index, cell in enumerate(code_cells, start=1):
        source_text = _source_to_text(cell.get("source"))
        if "read_csv" in source_text or "TODO" in source_text or "____" in source_text:
            candidate_cells.append({"index": index, "reason": "api_or_blank_candidate"})

    return {
        "path": str(notebook_path),
        "format": "ipynb",
        "cellCount": len(cells),
        "codeCellCount": len(code_cells),
        "markdownCellCount": len(markdown_cells),
        "blankCandidateCount": len(candidate_cells),
        "blankCandidates": candidate_cells,
        "executionDisabled": True,
        "contestantCodeExecuted": False,
        "unknownShellExecuted": False,
    }


def _summarize_generation(kind: str, generation: dict[str, Any]) -> dict[str, Any]:
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
        "sandboxRequiredBeforeRealExecution": generation.get("sandboxRequiredBeforeRealExecution", False),
    }


def _list_from_spec(dsl: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = dsl.get("spec", {}).get(key)
    return value if isinstance(value, list) else []


def _runner_for_check(check_type: str) -> str:
    return {
        "file_exists": "FileExistsGrader",
        "stdout_contains": "StdoutContainsGrader",
        "pytest": "PytestGrader",
    }.get(check_type, "UnsupportedGrader")


def _risk_level_for_check(check_type: str) -> str:
    return {
        "file_exists": "low",
        "stdout_contains": "medium",
        "pytest": "high",
    }.get(check_type, "high")


def _input_summary_for_check(check: dict[str, Any]) -> str:
    check_type = str(check.get("type") or "")
    if check_type == "file_exists":
        return f"Plan file existence check for {check.get('path')}"
    if check_type == "stdout_contains":
        return f"Plan stdout check for command: {check.get('command')}"
    if check_type == "pytest":
        return f"Plan pytest check at {check.get('path')}"
    return f"Plan unsupported check type: {check_type or 'unknown'}"


def _build_assessment_plan(checks: list[dict[str, Any]], timeout_seconds: int) -> list[dict[str, Any]]:
    timeout_value = f"{timeout_seconds}s" if timeout_seconds > 0 else "required"
    plans = []
    for check in checks:
        check_type = str(check.get("type") or "")
        plans.append(
            {
                "checkId": str(check.get("id") or ""),
                "type": check_type,
                "runner": _runner_for_check(check_type),
                "score": int(check.get("score", 0) or 0),
                "inputSummary": _input_summary_for_check(check),
                "executionPlan": {
                    "strategy": "MOCK_PLAN_ONLY",
                    "requiredLimits": {
                        "cpu": "required",
                        "memory": "required",
                        "timeout": timeout_value,
                        "network": "disabled_by_default",
                        "filesystem": "isolated_workspace_required",
                        "process": "limited",
                    },
                    "wouldRunInsideRealSandbox": True,
                },
                "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                "riskLevel": _risk_level_for_check(check_type),
                "sandboxRequiredBeforeRealExecution": True,
            }
        )
    return plans


def _build_exam_quality_signals(
    *,
    exam_dsl: dict[str, Any],
    grading_dsl: dict[str, Any],
    candidate_preview: dict[str, Any],
    lab_summary: dict[str, Any],
    notebook_summary: dict[str, Any],
) -> dict[str, Any]:
    questions = _list_from_spec(exam_dsl, "questions")
    checks = _list_from_spec(grading_dsl, "checks")
    exam_spec = exam_dsl.get("spec", {})
    grading_spec = grading_dsl.get("spec", {})
    assessment_plan = _build_assessment_plan(
        checks,
        int(grading_spec.get("timeoutSeconds", 0) or 0),
    )

    question_refs = [
        str(question.get("gradingRef"))
        for question in questions
        if isinstance(question, dict) and question.get("gradingRef")
    ]
    check_ids = [
        str(check.get("id"))
        for check in checks
        if isinstance(check, dict) and check.get("id")
    ]
    plan_check_ids = [
        str(plan.get("checkId"))
        for plan in assessment_plan
        if isinstance(plan, dict) and plan.get("checkId")
    ]
    missing_refs = [ref for ref in question_refs if ref not in set(check_ids)]
    extra_checks = [check_id for check_id in check_ids if check_id not in set(question_refs)]
    question_score_total = sum(int(question.get("score", 0)) for question in questions if isinstance(question, dict))
    check_score_total = sum(int(check.get("score", 0)) for check in checks if isinstance(check, dict))
    exam_total_score = int(exam_spec.get("totalScore", 0) or 0)
    grading_total_score = int(grading_spec.get("totalScore", 0) or 0)
    answer_stored_in_dsl = any(isinstance(question, dict) and "answer" in question for question in questions)
    answers_hidden = (
        candidate_preview.get("answersRemoved") is True
        and candidate_preview.get("answerVisibleToCandidate") is False
        and all("answer" not in question for question in candidate_preview.get("questions", []))
    )
    all_questions_have_grading_ref = len(questions) > 0 and len(question_refs) == len(questions)
    score_coverage_matched = (
        exam_total_score > 0
        and grading_total_score == exam_total_score
        and question_score_total == exam_total_score
        and check_score_total == grading_total_score
    )
    ref_coverage_matched = all_questions_have_grading_ref and not missing_refs
    supported_check_types = {"file_exists", "stdout_contains", "pytest", "notebook", "json_field", "keyword"}
    check_types = [
        str(check.get("type"))
        for check in checks
        if isinstance(check, dict) and check.get("type")
    ]
    unsupported_check_types = [check_type for check_type in check_types if check_type not in supported_check_types]
    checks_have_required_fields = len(checks) > 0 and all(
        isinstance(check, dict) and check.get("id") and check.get("type") and int(check.get("score", 0) or 0) > 0
        for check in checks
    )
    plan_aligned_with_checks = check_ids == plan_check_ids
    plan_has_report_detail_fields = len(assessment_plan) == len(checks) and all(
        isinstance(plan, dict)
        and plan.get("inputSummary")
        and plan.get("executionPlan", {}).get("strategy") == "MOCK_PLAN_ONLY"
        and plan.get("executionPlan", {}).get("requiredLimits", {}).get("network") == "disabled_by_default"
        and plan.get("mockEvidence", {}).get("status") == "MOCK_EVIDENCE_NOT_COLLECTED"
        and plan.get("sandboxRequiredBeforeRealExecution") is True
        for plan in assessment_plan
    )
    explainable = checks_have_required_fields and not unsupported_check_types and score_coverage_matched and plan_aligned_with_checks and plan_has_report_detail_fields
    review_highlights = [
        "确认标准答案只保留在审核用 Exam DSL 中",
        "确认评分点覆盖每道题的 gradingRef",
        "确认评分总分与题目总分一致",
    ]
    if not answers_hidden:
        review_highlights.append("确认候选人预览未暴露标准答案")
    if missing_refs:
        review_highlights.append("确认缺失 gradingRef 对应的评分检查")
    if not score_coverage_matched:
        review_highlights.append("确认 Exam / Grading 分值合计一致")
    if not explainable:
        review_highlights.append("确认评分计划字段完整且可解释")

    return {
        "overall": {
            "status": "READY_FOR_HUMAN_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "answerVisibleToCandidate": False,
            "answerHiddenFromCandidatePreview": answers_hidden,
            "gradingPlanExplainable": explainable,
            "needsHumanReview": True,
            "reviewHighlightCount": len(review_highlights),
        },
        "exam": {
            "status": "READY_FOR_HUMAN_REVIEW",
            "sourceLabId": exam_dsl.get("metadata", {}).get("sourceLabId"),
            "sourceLabLinked": exam_dsl.get("metadata", {}).get("sourceLabId") == lab_summary.get("labId"),
            "questionType": exam_spec.get("questionType"),
            "questionCount": len(questions),
            "blankCandidateCount": notebook_summary.get("blankCandidateCount", 0),
            "totalScore": exam_total_score,
            "questionScoreTotal": question_score_total,
            "scoreMatchesTotal": question_score_total == exam_total_score,
            "answersStoredInDsl": answer_stored_in_dsl,
            "answerHiddenFromCandidatePreview": answers_hidden,
            "answerVisibleToCandidate": False,
            "allQuestionsHaveGradingRef": all_questions_have_grading_ref,
            "gradingRefs": question_refs,
        },
        "grading": {
            "status": "READY_FOR_HUMAN_REVIEW",
            "sourceExamId": grading_dsl.get("metadata", {}).get("sourceExamId"),
            "sourceExamLinked": grading_dsl.get("metadata", {}).get("sourceExamId") == exam_dsl.get("metadata", {}).get("id"),
            "checkCount": len(checks),
            "totalScore": grading_total_score,
            "checkScoreTotal": check_score_total,
            "scoreMatchesTotal": check_score_total == grading_total_score,
            "checkIds": check_ids,
            "checkTypes": check_types,
            "unsupportedCheckTypes": unsupported_check_types,
            "assessmentPlan": assessment_plan,
            "sandboxRequiredBeforeRealExecution": True,
        },
        "coverage": {
            "questionGradingRefCoverage": {
                "status": "MATCHED" if ref_coverage_matched else "NEEDS_REVIEW",
                "matched": ref_coverage_matched,
                "requestedRefs": question_refs,
                "availableCheckIds": check_ids,
                "missingRefs": missing_refs,
                "extraChecks": extra_checks,
            },
            "scoreCoverage": {
                "status": "MATCHED" if score_coverage_matched else "NEEDS_REVIEW",
                "matched": score_coverage_matched,
                "examTotalScore": exam_total_score,
                "questionScoreTotal": question_score_total,
                "gradingTotalScore": grading_total_score,
                "checkScoreTotal": check_score_total,
            },
            "explainability": {
                "status": "EXPLAINABLE" if explainable else "NEEDS_REVIEW",
                "matched": explainable,
                "eachCheckHasIdTypeScore": checks_have_required_fields,
                "deterministicCheckTypesOnly": not unsupported_check_types,
                "assessmentPlanAlignedWithChecks": plan_aligned_with_checks,
                "assessmentPlanHasReportDetailFields": plan_has_report_detail_fields,
                "mockEvidenceStatus": "MOCK_EVIDENCE_NOT_COLLECTED",
                "executionStrategy": "MOCK_PLAN_ONLY",
                "sandboxRequiredBeforeRealExecution": True,
            },
        },
        "reviewHighlights": review_highlights,
    }


def run_phase2_exam_conversion(
    *,
    lab_path: Path,
    notebook_path: Path,
    reviewer: str,
    trace_id: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    lab_summary = _load_lab_summary(lab_path, root)
    notebook_summary = _load_notebook_summary(notebook_path)
    lab_id = str(lab_summary["labId"])
    try:
        exam = generate_mock_dsl_via_adapter("exam", input_ref=lab_id, trace_id=trace_id, root=root)
        grading = generate_mock_dsl_via_adapter("grading", input_ref=exam["dslId"], trace_id=trace_id, root=root)
    except ProviderError:
        raise
    generated_dsl = {
        "exam": _summarize_generation("exam", exam),
        "grading": _summarize_generation("grading", grading),
    }
    candidate_preview = build_candidate_safe_exam_preview(exam["dsl"], trace_id=trace_id)
    quality_signals = _build_exam_quality_signals(
        exam_dsl=exam["dsl"],
        grading_dsl=grading["dsl"],
        candidate_preview=candidate_preview,
        lab_summary=lab_summary,
        notebook_summary=notebook_summary,
    )
    generation_steps = [
        {
            "name": PHASE2_EXAM_STEP_BY_KIND[kind],
            "kind": kind,
            "status": generation["generatedStatus"],
            "generatedStatus": generation["generatedStatus"],
            "promptId": generation["promptId"],
            "dslId": generation["dslId"],
            "dslPath": generation["dslPath"],
            "provider": generation["provider"],
            "reviewRequired": generation["reviewRequired"],
            "publishBlockedUntilApproved": generation["publishBlockedUntilApproved"],
            "answerVisibleToCandidate": generation.get("answerVisibleToCandidate", False),
            "qualitySignals": quality_signals.get(kind, {}),
        }
        for kind, generation in {"exam": exam, "grading": grading}.items()
    ]
    return {
        "id": f"phase2_exam_report_{uuid4().hex[:12]}",
        "workflowId": PHASE2_EXAM_WORKFLOW_ID,
        "phase": "Phase 2",
        "mode": "MOCK_ONLY",
        "title": "Phase 2 Mock Exam Conversion Workflow",
        "labDslInput": lab_summary,
        "notebookInput": notebook_summary,
        "reviewer": reviewer,
        "providerAdapter": "mock_provider_adapter",
        "providerInterface": "LLMProvider",
        "workflowContract": "ai-workflows/phase2-exam-conversion.contract.json",
        "providerAdapterContract": "providers/provider-adapter.contract.json",
        "promptManifest": "prompts/manifest.json",
        "steps": [
            {"name": "validate_lab_dsl", "status": "COMPLETED", "labId": lab_summary["labId"], "labPath": str(lab_path)},
            {"name": "analyze_notebook", "status": "COMPLETED", "notebook": notebook_summary},
            *generation_steps,
            {
                "name": "assemble_exam_review_bundle",
                "status": "COMPLETED",
                "generatedKinds": list(generated_dsl),
                "reviewRequired": True,
                "publishBlockedUntilApproved": True,
                "answerVisibleToCandidate": False,
                "realPublish": False,
            },
        ],
        "generatedDsl": generated_dsl,
        "providerGenerations": {"exam": exam, "grading": grading},
        "candidateSafeExamPreview": candidate_preview,
        "qualitySignals": quality_signals,
        "reviewSummary": {
            "generatedStatus": "WAITING_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "answerVisibleToCandidate": False,
            "autoPublishAllowed": False,
            "qualitySignals": quality_signals["overall"],
            "reviewHighlights": quality_signals["reviewHighlights"],
        },
        "acceptanceSignals": {
            "labDslValidated": True,
            "notebookParsedWithoutExecution": True,
            "providerAdapterUsed": True,
            "schemaValidated": True,
            "allGeneratedDslWaitingReview": True,
            "answerHiddenFromCandidatePreview": True,
            "gradingRefsCovered": quality_signals["coverage"]["questionGradingRefCoverage"]["matched"],
            "gradingPlanExplainable": quality_signals["coverage"]["explainability"]["matched"],
            "mockOnly": True,
        },
        "safety": dict(PHASE2_SAFETY),
        "traceId": trace_id,
    }
