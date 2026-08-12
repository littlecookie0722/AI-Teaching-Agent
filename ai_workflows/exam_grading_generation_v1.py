"""Exam + Grading generation v1 stabilization helpers.

The second core feature starts from a Lab DSL and produces review-gated Exam
and Grading DSL artifacts. This module keeps the cross-artifact invariants out
of the CLI branch: task-specific output paths, schema validation, candidate-safe
preview redaction, gradingRef coverage, and local import-preview guidance.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl

from .exam_candidate_preview import ExamCandidatePreviewError, build_candidate_safe_exam_preview


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 30
GRADING_CHECK_TYPES = {"file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword"}
GRADING_RUNNERS = {
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


class ExamGradingGenerationV1Error(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def load_lab_dsl_for_exam_generation(lab_path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    if not lab_path.exists() or not lab_path.is_file():
        raise ExamGradingGenerationV1Error(
            "VALIDATION_ERROR",
            "Lab DSL 文件不存在",
            [{"field": "lab", "reason": "文件不存在"}],
        )
    try:
        document = load_yaml(lab_path)
        validate_dsl(document, load_schema("lab", root))
    except DslValidationError as exc:
        raise ExamGradingGenerationV1Error("SCHEMA_VALIDATION_ERROR", "Lab DSL Schema 校验失败", exc.errors) from exc
    if not isinstance(document, dict):
        raise ExamGradingGenerationV1Error(
            "SCHEMA_VALIDATION_ERROR",
            "Lab DSL Schema 校验失败",
            [{"field": "$", "reason": "root must be object"}],
        )
    return document


def lab_context_from_id(lab_id: str) -> dict[str, Any]:
    return {
        "version": "1.0",
        "kind": "Lab",
        "metadata": {
            "id": lab_id,
            "title": lab_id,
            "difficulty": "beginner",
        },
        "status": "WAITING_REVIEW",
        "spec": {"objectives": [], "steps": []},
    }


def generation_from_real_llm_result(kind: str, result: dict[str, Any]) -> dict[str, Any]:
    output_kind = "Exam" if kind == "exam" else "Grading"
    return {
        "kind": kind,
        "promptId": result.get("promptId", f"{kind}_generation_v0"),
        "promptVersion": result.get("promptVersion"),
        "provider": {
            "adapterId": "openai_responses_sdk_adapter",
            "interfaceName": "LLMProvider",
            "operation": "generateJson",
            "providerId": result.get("providerId", "openai"),
            "mode": "REAL_LLM",
            "model": result.get("model"),
            "baseUrlConfigured": result.get("baseUrlConfigured"),
            "baseUrlSource": result.get("baseUrlSource"),
            "realLlmCalled": bool(result.get("realLlmCalled", True)),
            "secretsRead": bool(result.get("secretValueRead")),
            "networkAccess": bool(result.get("networkAccess", True)),
            "traceId": result.get("traceId"),
            "requestCount": result.get("requestCount"),
            "singleRequestOnly": result.get("singleRequestForKind"),
            "schemaRepairAttempted": result.get("schemaRepairAttempted", False),
            "schemaRepairApplied": result.get("schemaRepairApplied", False),
            "secretValueReturned": result.get("secretValueReturned", False),
            "responseId": result.get("responseId"),
            "apiSurface": result.get("apiSurface"),
        },
        "dsl": result.get("dsl"),
        "dslPath": "",
        "dslId": result.get("dslId"),
        "inputRef": result.get("inputRef"),
        "outputKind": result.get("outputKind", output_kind),
        "generatedStatus": result.get("generatedStatus", "WAITING_REVIEW"),
        "reviewRequired": bool(result.get("reviewRequired", True)),
        "publishBlockedUntilApproved": True,
        "answerVisibleToCandidate": False,
        "artifactGenerated": True,
        "sandboxRequiredBeforeRealExecution": kind == "grading",
        "schemaValidated": bool(result.get("schemaValidated", True)),
        "usage": result.get("usage"),
        "responseId": result.get("responseId"),
        "apiSurface": result.get("apiSurface"),
        "normalization": result.get("normalization"),
        "schemaRepair": result.get("schemaRepair"),
        "schemaRepairAttempted": result.get("schemaRepairAttempted", False),
        "schemaRepairApplied": result.get("schemaRepairApplied", False),
    }


def finalize_exam_grading_generation_v1(
    exam_generation: dict[str, Any],
    grading_generation: dict[str, Any],
    *,
    lab_dsl: dict[str, Any],
    lab_ref: str,
    lab_dsl_validated: bool,
    task_id: str,
    trace_id: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    finalized_exam = deepcopy(exam_generation)
    finalized_grading = deepcopy(grading_generation)
    exam_dsl = _normalize_exam_dsl(finalized_exam.get("dsl"), lab_dsl=lab_dsl, task_id=task_id)
    grading_dsl = _normalize_grading_dsl(finalized_grading.get("dsl"), exam_dsl=exam_dsl, task_id=task_id)

    _validate_or_raise(exam_dsl, "exam", root=root)
    _validate_or_raise(grading_dsl, "grading", root=root)

    output_dir = root / "examples" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    exam_path = output_dir / f"{task_id}-exam.json"
    grading_path = output_dir / f"{task_id}-grading.json"
    candidate_preview_path = output_dir / f"{task_id}-exam-candidate-preview.json"

    _write_json(exam_path, exam_dsl)
    _write_json(grading_path, grading_dsl)
    try:
        candidate_preview = build_candidate_safe_exam_preview(
            exam_dsl,
            source_path=_display_path(exam_path, root=root),
            trace_id=trace_id,
        )
    except ExamCandidatePreviewError as exc:
        raise ExamGradingGenerationV1Error(exc.code, exc.message, exc.errors) from exc
    _write_json(candidate_preview_path, candidate_preview)

    exam_ref = _display_path(exam_path, root=root)
    grading_ref = _display_path(grading_path, root=root)
    preview_ref = _display_path(candidate_preview_path, root=root)
    finalized_exam.update(
        {
            "dsl": exam_dsl,
            "dslPath": exam_ref,
            "dslId": exam_dsl["metadata"]["id"],
            "inputRef": lab_ref,
            "outputKind": "Exam",
            "generatedStatus": "WAITING_REVIEW",
            "schemaValidated": True,
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "answerVisibleToCandidate": False,
        }
    )
    finalized_grading.update(
        {
            "dsl": grading_dsl,
            "dslPath": grading_ref,
            "dslId": grading_dsl["metadata"]["id"],
            "inputRef": exam_dsl["metadata"]["id"],
            "outputKind": "Grading",
            "generatedStatus": "WAITING_REVIEW",
            "schemaValidated": True,
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "answerVisibleToCandidate": False,
            "sandboxRequiredBeforeRealExecution": True,
        }
    )
    paths = {
        "examDslPath": exam_ref,
        "gradingDslPath": grading_ref,
        "candidatePreviewPath": preview_ref,
    }
    readiness = build_exam_grading_feature_readiness(
        finalized_exam,
        finalized_grading,
        lab_dsl=lab_dsl,
        lab_dsl_validated=lab_dsl_validated,
        task={"id": task_id, "status": "WAITING_REVIEW", "taskType": "EXAM_GENERATION", "finalResultPath": exam_ref},
        artifacts=[],
        candidate_preview=candidate_preview,
        paths=paths,
    )
    finalized_exam["examGradingFeatureReadiness"] = readiness
    finalized_grading["examGradingFeatureReadiness"] = readiness
    return {
        "examGeneration": finalized_exam,
        "gradingGeneration": finalized_grading,
        "candidatePreview": candidate_preview,
        "paths": paths,
        "examGradingFeatureReadiness": readiness,
    }


def build_exam_grading_feature_readiness(
    exam_generation: dict[str, Any],
    grading_generation: dict[str, Any],
    *,
    lab_dsl: dict[str, Any],
    lab_dsl_validated: bool,
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    candidate_preview: dict[str, Any],
    paths: dict[str, str],
) -> dict[str, Any]:
    exam_dsl = exam_generation.get("dsl") if isinstance(exam_generation.get("dsl"), dict) else {}
    grading_dsl = grading_generation.get("dsl") if isinstance(grading_generation.get("dsl"), dict) else {}
    exam_spec = exam_dsl.get("spec") if isinstance(exam_dsl.get("spec"), dict) else {}
    grading_spec = grading_dsl.get("spec") if isinstance(grading_dsl.get("spec"), dict) else {}
    questions = exam_spec.get("questions") if isinstance(exam_spec.get("questions"), list) else []
    checks = grading_spec.get("checks") if isinstance(grading_spec.get("checks"), list) else []
    assessment_plan = grading_spec.get("assessmentPlan") if isinstance(grading_spec.get("assessmentPlan"), list) else []
    question_refs = [str(question.get("gradingRef")) for question in questions if isinstance(question, dict) and question.get("gradingRef")]
    check_refs = {str(check.get("id")) for check in checks if isinstance(check, dict) and check.get("id")}
    plan_refs = {str(item.get("checkId")) for item in assessment_plan if isinstance(item, dict) and item.get("checkId")}
    score_aligned = _safe_int(exam_spec.get("totalScore"), 0) == _safe_int(grading_spec.get("totalScore"), -1)
    provider_exam = exam_generation.get("provider") if isinstance(exam_generation.get("provider"), dict) else {}
    provider_grading = grading_generation.get("provider") if isinstance(grading_generation.get("provider"), dict) else {}
    safety = {
        "realLlmCalled": bool(provider_exam.get("realLlmCalled") or provider_grading.get("realLlmCalled")),
        "networkAccess": bool(provider_exam.get("networkAccess") or provider_grading.get("networkAccess")),
        "secretsRead": bool(provider_exam.get("secretsRead") or provider_grading.get("secretsRead")),
        "answerVisibleToCandidate": bool(candidate_preview.get("answerVisibleToCandidate")),
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "realAgentImport": False,
    }
    requirements = {
        "labDslValidated": lab_dsl_validated,
        "examDslGenerated": exam_dsl.get("kind") == "Exam",
        "gradingDslGenerated": grading_dsl.get("kind") == "Grading",
        "examSchemaValidated": bool(exam_generation.get("schemaValidated")),
        "gradingSchemaValidated": bool(grading_generation.get("schemaValidated")),
        "waitingReviewTaskCreated": task.get("status") == "WAITING_REVIEW" and bool(task.get("id")),
        "taskSpecificExamOutputCreated": _is_task_specific_path(paths.get("examDslPath"), task.get("id"), "exam"),
        "taskSpecificGradingOutputCreated": _is_task_specific_path(paths.get("gradingDslPath"), task.get("id"), "grading"),
        "candidatePreviewCreated": bool(paths.get("candidatePreviewPath")) and bool(candidate_preview.get("questions")),
        "candidatePreviewAnswerSafe": candidate_preview.get("answerVisibleToCandidate") is False
        and candidate_preview.get("answersRemoved") is True
        and candidate_preview.get("redaction", {}).get("answerLeakDetected") is False,
        "questionGradingRefsUnique": bool(question_refs) and len(question_refs) == len(set(question_refs)),
        "questionGradingRefsCovered": bool(question_refs) and set(question_refs).issubset(check_refs) and set(question_refs).issubset(plan_refs),
        "scoreAligned": score_aligned,
        "manualReviewRequired": bool(exam_generation.get("reviewRequired")) and bool(grading_generation.get("reviewRequired")),
        "publishBlockedUntilApproved": bool(exam_generation.get("publishBlockedUntilApproved"))
        and bool(grading_generation.get("publishBlockedUntilApproved")),
        "importPreviewPathAvailable": bool(task.get("id")),
        "safetyBoundariesKept": not any(
            safety[key]
            for key in ("answerVisibleToCandidate", "sandboxExecuted", "contestantCodeExecuted", "autoPublishAllowed", "realPublish", "realAgentImport")
        ),
    }
    complete = all(requirements.values())
    task_id = str(task.get("id") or "")
    lab_metadata = lab_dsl.get("metadata") if isinstance(lab_dsl.get("metadata"), dict) else {}
    return {
        "component": "ExamGradingGenerationV1Readiness",
        "featureId": "exam_grading_generate_from_lab",
        "status": "STABLE_V1_READY_FOR_MANUAL_REVIEW" if complete else "NEEDS_FIX_BEFORE_STABLE_V1",
        "completeForStableV1": complete,
        "summary": {
            "sourceLabId": lab_metadata.get("id"),
            "examId": (exam_dsl.get("metadata") or {}).get("id") if isinstance(exam_dsl.get("metadata"), dict) else None,
            "gradingId": (grading_dsl.get("metadata") or {}).get("id") if isinstance(grading_dsl.get("metadata"), dict) else None,
            "questionTotal": len(questions),
            "checkTotal": len(checks),
            "assessmentPlanTotal": len(assessment_plan),
            "totalScore": exam_spec.get("totalScore"),
            "examDslPath": paths.get("examDslPath"),
            "gradingDslPath": paths.get("gradingDslPath"),
            "candidatePreviewPath": paths.get("candidatePreviewPath"),
            "artifactTotal": len(artifacts),
        },
        "requirements": requirements,
        "nextActions": {
            "reviewDetail": {
                "cli": f"python lab_cli.py review detail --task-id {task_id}",
                "api": f"GET /api/review-tasks/{task_id}",
                "frontend": f"review-center.html?taskId={task_id}",
            },
            "candidatePreview": {
                "cli": f"python lab_cli.py exam candidate-preview --exam {paths.get('examDslPath')} --output {paths.get('candidatePreviewPath')}",
                "answerVisibleToCandidate": False,
            },
            "approveThenExamImportPreview": {
                "enabledAfter": "task.status=APPROVED",
                "cli": f"python lab_cli.py exam import-preview --task-id {task_id} --reviewer <reviewer> --output examples/output/exam-question-import-preview.json",
                "api": "POST /api/exams/import-preview",
            },
            "approveThenGradingImportPreview": {
                "enabledAfter": "task.status=APPROVED",
                "cli": f"python lab_cli.py grade import-preview --task-id {task_id} --reviewer <reviewer> --output examples/output/grading-rule-import-preview.json",
                "api": "POST /api/grading/import-preview",
            },
        },
        "safety": safety,
        "stopLine": "Stable Exam+Grading v1 stops at Lab DSL input, task-specific WAITING_REVIEW Exam/Grading DSL, candidate-safe preview, and local import-preview path; no real platform publish.",
    }


def _normalize_exam_dsl(value: Any, *, lab_dsl: dict[str, Any], task_id: str) -> dict[str, Any]:
    source = deepcopy(value) if isinstance(value, dict) else {}
    source_metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    lab_metadata = lab_dsl.get("metadata") if isinstance(lab_dsl.get("metadata"), dict) else {}
    lab_id = str(lab_metadata.get("id") or "lab_demo")
    title = str(source_metadata.get("title") or f"{lab_metadata.get('title') or lab_id}考试题")
    difficulty = _normalize_difficulty(source_metadata.get("difficulty") or lab_metadata.get("difficulty"))
    spec = source.get("spec") if isinstance(source.get("spec"), dict) else {}
    questions = _normalize_exam_questions(spec.get("questions"), task_id=task_id)
    total_score = sum(_safe_int(question.get("score"), 1) for question in questions)
    question_type = spec.get("questionType") if spec.get("questionType") in {"notebook_fill_blank", "coding_task", "short_answer"} else "coding_task"
    return {
        "version": str(source.get("version") or "1.0"),
        "kind": "Exam",
        "metadata": {
            "id": str(source_metadata.get("id") or f"exam_{task_id.removeprefix('task_')}"),
            "title": title,
            "sourceLabId": lab_id,
            "difficulty": difficulty,
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "questionType": question_type,
            "totalScore": max(total_score, 1),
            "questions": questions,
        },
    }


def _normalize_exam_questions(value: Any, *, task_id: str) -> list[dict[str, Any]]:
    raw_questions = value if isinstance(value, list) else []
    questions: list[dict[str, Any]] = []
    used_grading_refs: set[str] = set()
    for index, raw_question in enumerate(raw_questions, start=1):
        if not isinstance(raw_question, dict):
            continue
        grading_ref = _unique_grading_ref(_string_or_default(raw_question.get("gradingRef"), f"check_q{index}"), index, used_grading_refs)
        question = {
            "id": _string_or_default(raw_question.get("id"), f"q{index}"),
            "title": _string_or_default(raw_question.get("title"), f"题目 {index}"),
            "stem": _string_or_default(raw_question.get("stem"), "请根据实验要求完成本题。"),
            "score": max(_safe_int(raw_question.get("score"), 20), 1),
            "gradingRef": grading_ref,
        }
        if raw_question.get("blankCode") is not None:
            question["blankCode"] = _string_or_default(raw_question.get("blankCode"), "")
        if raw_question.get("answer") is not None:
            question["answer"] = _string_or_default(raw_question.get("answer"), "")
        questions.append(question)
    if not questions:
        suffix = task_id.removeprefix("task_")[:6] or "demo"
        questions = [
            {
                "id": "q1",
                "title": "完成实验核心任务",
                "stem": "请根据 Lab DSL 的实验目标完成一个可审核的核心操作，并提交结果说明。",
                "blankCode": "submit_result = ____",
                "answer": "completed",
                "score": 100,
                "gradingRef": f"check_{suffix}_q1",
            }
        ]
    return questions


def _unique_grading_ref(value: str, index: int, used: set[str]) -> str:
    candidate = value.strip() or f"check_q{index}"
    if candidate in used:
        candidate = f"check_q{index}"
    suffix = 2
    base = candidate
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _normalize_grading_dsl(value: Any, *, exam_dsl: dict[str, Any], task_id: str) -> dict[str, Any]:
    source = deepcopy(value) if isinstance(value, dict) else {}
    source_metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    exam_metadata = exam_dsl.get("metadata") if isinstance(exam_dsl.get("metadata"), dict) else {}
    exam_spec = exam_dsl.get("spec") if isinstance(exam_dsl.get("spec"), dict) else {}
    questions = exam_spec.get("questions") if isinstance(exam_spec.get("questions"), list) else []
    checks = [_check_from_question(question, index) for index, question in enumerate(questions, start=1) if isinstance(question, dict)]
    if not checks:
        checks = [{"id": f"check_{task_id.removeprefix('task_')}_q1", "type": "stdout_contains", "command": "python main.py", "expected": ["PASS"], "score": 100}]
    total_score = sum(_safe_int(check.get("score"), 1) for check in checks)
    return {
        "version": str(source.get("version") or "1.0"),
        "kind": "Grading",
        "metadata": {
            "id": str(source_metadata.get("id") or f"grading_{task_id.removeprefix('task_')}"),
            "title": str(source_metadata.get("title") or f"{exam_metadata.get('title') or '考试'}评分规则"),
            "sourceExamId": str(exam_metadata.get("id") or ""),
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "totalScore": max(total_score, 1),
            "timeoutSeconds": DEFAULT_TIMEOUT_SECONDS,
            "assessmentPlan": [_assessment_plan_from_check(check) for check in checks],
            "checks": checks,
        },
    }


def _check_from_question(question: dict[str, Any], index: int) -> dict[str, Any]:
    check_id = _string_or_default(question.get("gradingRef"), f"check_q{index}")
    return {
        "id": check_id,
        "type": "stdout_contains",
        "command": "python main.py",
        "expected": ["PASS"],
        "score": max(_safe_int(question.get("score"), 20), 1),
    }


def _assessment_plan_from_check(check: dict[str, Any]) -> dict[str, Any]:
    check_type = str(check.get("type") or "stdout_contains")
    if check_type not in GRADING_CHECK_TYPES:
        check_type = "stdout_contains"
    return {
        "checkId": str(check.get("id")),
        "type": check_type,
        "runner": GRADING_RUNNERS[check_type],
        "score": max(_safe_int(check.get("score"), 1), 1),
        "inputSummary": f"根据 {check.get('id')} 的评分规则检查候选人提交结果。",
        "executionPlan": {
            "strategy": "MOCK_PLAN_ONLY",
            "requiredLimits": {
                "cpu": "1 core",
                "memory": "512MB",
                "timeout": "30s",
                "network": "disabled_by_default",
                "filesystem": "isolated_workspace_required",
                "process": "single_process_limit",
            },
            "wouldRunInsideRealSandbox": True,
        },
        "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
        "riskLevel": GRADING_RISK_LEVELS[check_type],
        "sandboxRequiredBeforeRealExecution": True,
    }


def _validate_or_raise(dsl: dict[str, Any], kind: str, *, root: Path) -> None:
    try:
        validate_dsl(dsl, load_schema(kind, root))
    except DslValidationError as exc:
        raise ExamGradingGenerationV1Error("SCHEMA_VALIDATION_ERROR", f"{kind} DSL Schema 校验失败", exc.errors) from exc


def _normalize_difficulty(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"beginner", "intermediate", "advanced"}:
        return text
    return "beginner"


def _safe_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _string_or_default(value: Any, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value).strip()
    return text or default


def _is_task_specific_path(value: Any, task_id: Any, suffix: str) -> bool:
    if not value or not task_id:
        return False
    text = str(value).replace("\\", "/")
    return text == f"examples/output/{task_id}-{suffix}.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _display_path(path: Path, *, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
