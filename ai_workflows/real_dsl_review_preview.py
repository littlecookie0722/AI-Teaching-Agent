"""Deterministic review preview for real LLM generated DSL artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl

from .exam_candidate_preview import build_candidate_safe_exam_preview


ROOT = Path(__file__).resolve().parents[1]


class RealDslReviewPreviewError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def build_real_dsl_review_preview_from_files(
    *,
    lab_path: Path,
    exam_path: Path,
    grading_path: Path,
    ppt_path: Path,
    candidate_preview_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    lab = _load_and_validate_dsl(lab_path, "lab", root=root, field="lab")
    exam = _load_and_validate_dsl(exam_path, "exam", root=root, field="exam")
    grading = _load_and_validate_dsl(grading_path, "grading", root=root, field="grading")
    ppt = _load_and_validate_dsl(ppt_path, "ppt", root=root, field="ppt")

    candidate_preview = _load_candidate_preview(
        exam,
        exam_path=exam_path,
        candidate_preview_path=candidate_preview_path,
        trace_id=trace_id,
    )
    return build_real_dsl_review_preview(
        lab=lab,
        exam=exam,
        grading=grading,
        ppt=ppt,
        candidate_preview=candidate_preview,
        paths={
            "lab": lab_path,
            "exam": exam_path,
            "grading": grading_path,
            "ppt": ppt_path,
            "candidatePreview": candidate_preview_path,
        },
        trace_id=trace_id,
    )


def build_real_dsl_review_preview(
    *,
    lab: dict[str, Any],
    exam: dict[str, Any],
    grading: dict[str, Any],
    ppt: dict[str, Any],
    candidate_preview: dict[str, Any],
    paths: dict[str, Path | None],
    trace_id: str | None = None,
) -> dict[str, Any]:
    lab_metadata = _object(lab.get("metadata"))
    lab_spec = _object(lab.get("spec"))
    exam_metadata = _object(exam.get("metadata"))
    exam_spec = _object(exam.get("spec"))
    grading_metadata = _object(grading.get("metadata"))
    grading_spec = _object(grading.get("spec"))
    ppt_metadata = _object(ppt.get("metadata"))
    ppt_spec = _object(ppt.get("spec"))

    lab_steps = [
        {
            "id": step.get("id"),
            "title": step.get("title"),
            "instructionPreview": _take_text(step.get("instruction"), 220),
            "expectedResult": step.get("expectedResult"),
        }
        for step in _list_of_objects(lab_spec.get("steps"))
    ]
    candidate_questions = [
        {
            "id": question.get("id"),
            "title": question.get("title"),
            "stemPreview": _take_text(question.get("stem"), 220),
            "blankCodePresent": bool(question.get("blankCode")),
            "score": question.get("score"),
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
        }
        for question in _list_of_objects(candidate_preview.get("questions"))
    ]
    teacher_question_refs = [
        {
            "id": question.get("id"),
            "title": question.get("title"),
            "score": question.get("score"),
            "gradingRefPreview": _take_text(question.get("gradingRef"), 220),
            "teacherOnly": True,
            "candidateVisible": False,
        }
        for question in _list_of_objects(exam_spec.get("questions"))
    ]
    assessment_plan = [
        {
            "checkId": plan.get("checkId"),
            "type": plan.get("type"),
            "runner": plan.get("runner"),
            "score": plan.get("score"),
            "inputSummary": _take_text(plan.get("inputSummary"), 180),
            "strategy": _object(plan.get("executionPlan")).get("strategy"),
            "requiredLimits": _object(_object(plan.get("executionPlan")).get("requiredLimits")),
            "mockEvidenceStatus": _object(plan.get("mockEvidence")).get("status"),
            "sandboxRequiredBeforeRealExecution": plan.get("sandboxRequiredBeforeRealExecution") is True,
            "riskLevel": plan.get("riskLevel"),
        }
        for plan in _list_of_objects(grading_spec.get("assessmentPlan"))
    ]
    checks = [
        {
            "id": check.get("id"),
            "type": check.get("type"),
            "score": check.get("score"),
            "commandPreview": _take_text(check.get("command"), 160),
            "expected": check.get("expected", []),
            "commandExecutionAllowedFromPage": False,
        }
        for check in _list_of_objects(grading_spec.get("checks"))
    ]
    slides = [
        {
            "index": index + 1,
            "id": slide.get("id"),
            "type": slide.get("type"),
            "title": slide.get("title"),
            "bulletCount": len(slide.get("bullets", [])) if isinstance(slide.get("bullets"), list) else 0,
            "bullets": slide.get("bullets", []) if isinstance(slide.get("bullets"), list) else [],
            "reviewStatus": "NEEDS_REVIEW",
        }
        for index, slide in enumerate(_list_of_objects(ppt_spec.get("slides")))
    ]
    quality_signals = _build_quality_signals(
        lab=lab,
        exam=exam,
        grading=grading,
        ppt=ppt,
        candidate_preview=candidate_preview,
        lab_steps=lab_steps,
        candidate_questions=candidate_questions,
        teacher_question_refs=teacher_question_refs,
        assessment_plan=assessment_plan,
        checks=checks,
        slides=slides,
    )

    preview = {
        "component": "RealDslReviewPreview",
        "mode": "STATIC_REAL_LLM_DSL_REVIEW_PREVIEW",
        "source": "real_llm_dsl_files",
        "route": "/real-demo -> /review-center -> /labs/:id/review -> /exams/:id/review -> /grading/:id/review -> /ppt/:id/review",
        "summary": {
            "labTitle": lab_metadata.get("title"),
            "labStepTotal": len(lab_steps),
            "labObjectiveTotal": len(lab_spec.get("objectives", [])) if isinstance(lab_spec.get("objectives"), list) else 0,
            "examTitle": exam_metadata.get("title"),
            "examQuestionTotal": len(candidate_questions),
            "examTotalScore": candidate_preview.get("totalScore"),
            "gradingPlanTotal": len(assessment_plan),
            "gradingCheckTotal": len(checks),
            "gradingTotalScore": grading_spec.get("totalScore"),
            "pptTitle": ppt_metadata.get("title"),
            "pptSlideTotal": len(slides),
            "manualReviewRequired": True,
            "allDslWaitingReview": all(
                dsl.get("status") == "WAITING_REVIEW"
                for dsl in (lab, exam, grading, ppt)
            ),
            "qualityStatus": quality_signals["summary"]["status"],
            "qualityIssueTotal": quality_signals["summary"]["issueTotal"],
            "blockingIssueTotal": quality_signals["summary"]["blockingIssueTotal"],
            "revisionSuggestionTotal": quality_signals["summary"]["revisionSuggestionTotal"],
        },
        "qualitySignals": quality_signals,
        "reviewIssues": quality_signals["issues"],
        "revisionSuggestions": quality_signals["revisionSuggestions"],
        "labReview": {
            "path": _path_str(paths.get("lab")),
            "id": lab_metadata.get("id"),
            "title": lab_metadata.get("title"),
            "durationMinutes": lab_metadata.get("durationMinutes"),
            "difficulty": lab_metadata.get("difficulty"),
            "targetUsers": lab_spec.get("targetUsers", []),
            "objectives": lab_spec.get("objectives", []),
            "environment": lab_spec.get("environment", {}),
            "materials": lab_spec.get("materials", []),
            "steps": lab_steps,
        },
        "examReview": {
            "sourceDslPath": _path_str(paths.get("exam")),
            "candidatePreviewPath": _path_str(paths.get("candidatePreview")),
            "id": exam_metadata.get("id"),
            "title": exam_metadata.get("title"),
            "questionType": exam_spec.get("questionType"),
            "totalScore": candidate_preview.get("totalScore"),
            "candidateQuestions": candidate_questions,
            "teacherQuestionRefs": teacher_question_refs,
            "candidateSafety": {
                "answersRemoved": candidate_preview.get("answersRemoved") is True,
                "answerVisibleToCandidate": False,
                "gradingRefVisibleToCandidate": False,
                "removedFields": _object(candidate_preview.get("redaction")).get("removedFields", []),
                "answerLeakDetected": _object(candidate_preview.get("redaction")).get("answerLeakDetected") is True,
            },
        },
        "gradingReview": {
            "path": _path_str(paths.get("grading")),
            "normalizedPath": "examples/output/real-llm-demo-grading-normalized.json",
            "precheckPath": "examples/output/real-llm-demo-grading-precheck.json",
            "id": grading_metadata.get("id"),
            "title": grading_metadata.get("title"),
            "sourceExamId": grading_metadata.get("sourceExamId"),
            "totalScore": grading_spec.get("totalScore"),
            "assessmentPlan": assessment_plan,
            "checks": checks,
            "precheckStatus": "READY_FOR_MANUAL_SANDBOX_REVIEW",
            "realSandboxExecutionAllowedFromPage": False,
            "commandExecutionAllowedFromPage": False,
        },
        "pptReview": {
            "sourceDslPath": _path_str(paths.get("ppt")),
            "artifactPath": "examples/output/real-llm-demo-ppt-artifact.pptx",
            "manifestPath": "examples/output/real-llm-demo-ppt-artifact-manifest.json",
            "firstSlidePreviewPath": "examples/output/real-llm-demo-ppt-artifact-slide-01.png",
            "title": ppt_metadata.get("title"),
            "audience": ppt_metadata.get("audience"),
            "durationMinutes": ppt_metadata.get("durationMinutes"),
            "theme": ppt_spec.get("theme", {}),
            "slideTotal": len(slides),
            "slides": slides,
            "pageReviewActionVisible": True,
        },
        "safety": {
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "teacherOnlyGradingRefVisibleInReview": True,
            "commandExecutedFromPage": False,
            "realSandboxRunEnabled": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "secretVisibleInFrontend": False,
        },
    }
    if trace_id:
        preview["traceId"] = trace_id
    return preview


def _build_quality_signals(
    *,
    lab: dict[str, Any],
    exam: dict[str, Any],
    grading: dict[str, Any],
    ppt: dict[str, Any],
    candidate_preview: dict[str, Any],
    lab_steps: list[dict[str, Any]],
    candidate_questions: list[dict[str, Any]],
    teacher_question_refs: list[dict[str, Any]],
    assessment_plan: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    slides: list[dict[str, Any]],
) -> dict[str, Any]:
    lab_spec = _object(lab.get("spec"))
    exam_spec = _object(exam.get("spec"))
    grading_spec = _object(grading.get("spec"))
    issues: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []

    def add_issue(
        issue_id: str,
        severity: str,
        kind: str,
        field: str,
        message: str,
        suggestion: str,
        target_section: str,
    ) -> None:
        issues.append(
            {
                "id": issue_id,
                "severity": severity,
                "kind": kind,
                "field": field,
                "message": message,
                "suggestedAction": suggestion,
                "targetSection": target_section,
            }
        )
        suggestions.append(
            {
                "id": f"revise_{issue_id}",
                "kind": kind,
                "targetSection": target_section,
                "comment": suggestion,
                "defaultReviewer": "teacher_1",
                "safeCommandExample": (
                    "python lab_cli.py review real-dsl-revision "
                    f"--kind {kind} --reviewer teacher_1 "
                    f"--comment \"{suggestion}\" --target-section {target_section}"
                ),
                "requiresNewLlmRequest": False,
                "keepsWaitingReview": True,
                "autoPublishAllowed": False,
            }
        )

    lab_objectives = lab_spec.get("objectives") if isinstance(lab_spec.get("objectives"), list) else []
    if len(lab_objectives) < 2:
        add_issue(
            "lab_objective_depth",
            "MEDIUM",
            "lab",
            "$.spec.objectives",
            "实验学习目标偏少，审核时较难判断知识点覆盖面。",
            "补充至少 2 个可观察、可验收的学习目标。",
            "objectives",
        )
    if len(lab_steps) < 4:
        add_issue(
            "lab_step_granularity",
            "LOW",
            "lab",
            "$.spec.steps",
            "实验步骤数量较少，可能不利于课堂分段讲解。",
            "将实验拆分为准备、实践、验证和总结四类步骤。",
            "steps",
        )
    if any(not step.get("expectedResult") for step in lab_steps):
        add_issue(
            "lab_expected_result_missing",
            "MEDIUM",
            "lab",
            "$.spec.steps[].expectedResult",
            "部分实验步骤缺少 expectedResult。",
            "为每个步骤补充可观察的验收结果。",
            "steps",
        )

    exam_total = _number(exam_spec.get("totalScore"))
    question_score_total = sum(_number(question.get("score")) for question in _list_of_objects(exam_spec.get("questions")))
    if candidate_preview.get("answersRemoved") is not True:
        add_issue(
            "exam_candidate_redaction",
            "HIGH",
            "exam",
            "$.candidatePreview.answersRemoved",
            "候选人预览未确认移除标准答案。",
            "重新生成候选人安全预览并确认 answer/gradingRef 不进入选手端。",
            "candidatePreview",
        )
    if not candidate_questions:
        add_issue(
            "exam_question_missing",
            "HIGH",
            "exam",
            "$.spec.questions",
            "考试 DSL 没有可展示给候选人的题目。",
            "补充至少 1 道候选人可作答题目。",
            "questions",
        )
    if exam_total and question_score_total and abs(exam_total - question_score_total) > 0.001:
        add_issue(
            "exam_score_mismatch",
            "HIGH",
            "exam",
            "$.spec.totalScore",
            "题目分值之和与试卷总分不一致。",
            "调整 questions[].score 或 spec.totalScore，使二者一致。",
            "questions",
        )

    grading_total = _number(grading_spec.get("totalScore"))
    check_score_total = sum(_number(check.get("score")) for check in _list_of_objects(grading_spec.get("checks")))
    question_refs = {str(ref.get("gradingRefPreview") or "").strip() for ref in teacher_question_refs if ref.get("gradingRefPreview")}
    check_ids = {str(check.get("id") or "").strip() for check in checks if check.get("id")}
    missing_refs = sorted(ref for ref in question_refs if ref and ref not in check_ids)
    if missing_refs:
        add_issue(
            "grading_ref_uncovered",
            "HIGH",
            "grading",
            "$.spec.checks[].id",
            f"存在未被评分 check 覆盖的 gradingRef：{', '.join(missing_refs)}。",
            "补充与每个题目 gradingRef 同名或明确映射的评分 check。",
            "checks",
        )
    if grading_total and check_score_total and abs(grading_total - check_score_total) > 0.001:
        add_issue(
            "grading_score_mismatch",
            "HIGH",
            "grading",
            "$.spec.totalScore",
            "评分 check 分值之和与评分总分不一致。",
            "调整 checks[].score 或 spec.totalScore，使评分总分可解释。",
            "checks",
        )
    deferred_check_types = sorted(
        {
            str(check.get("type") or "")
            for check in checks
            if str(check.get("type") or "") in {"stdout_contains", "pytest", "notebook_cell"}
        }
    )
    if deferred_check_types:
        add_issue(
            "grading_sandbox_execution_required",
            "MEDIUM",
            "grading",
            "$.spec.checks",
            f"评分包含需要受控沙箱执行的检查类型：{', '.join(deferred_check_types)}。",
            "进入真实执行前先绑定受控沙箱、超时和网络/文件系统限制。",
            "assessmentPlan",
        )
    if len(assessment_plan) != len(checks):
        add_issue(
            "grading_plan_check_count_mismatch",
            "MEDIUM",
            "grading",
            "$.spec.assessmentPlan",
            "assessmentPlan 数量与 checks 数量不一致。",
            "为每个评分 check 补充一条可审计 assessmentPlan。",
            "assessmentPlan",
        )

    if len(slides) < 5:
        add_issue(
            "ppt_slide_depth",
            "LOW",
            "ppt",
            "$.spec.slides",
            "PPT 页数偏少，可能不足以覆盖导入、讲解、示例、练习和总结。",
            "补充课堂练习或总结页，让演示结构更完整。",
            "slides",
        )
    if any(slide.get("type") == "content" and int(slide.get("bulletCount") or 0) == 0 for slide in slides):
        add_issue(
            "ppt_content_bullets_missing",
            "LOW",
            "ppt",
            "$.spec.slides[].bullets",
            "部分内容页缺少要点 bullet。",
            "为内容页补充 2 到 4 条可讲解要点。",
            "slides",
        )

    status = "READY_FOR_REVIEW"
    if any(issue["severity"] == "HIGH" for issue in issues):
        status = "NEEDS_REVISION"
    elif issues:
        status = "NEEDS_REVIEW"
    blocking_issue_total = sum(1 for issue in issues if issue["severity"] == "HIGH")
    return {
        "summary": {
            "status": status,
            "issueTotal": len(issues),
            "blockingIssueTotal": blocking_issue_total,
            "revisionSuggestionTotal": len(suggestions),
            "manualReviewRequired": True,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "coverage": {
            "labObjectiveTotal": len(lab_objectives),
            "labStepTotal": len(lab_steps),
            "examQuestionTotal": len(candidate_questions),
            "examScoreMatched": not exam_total or not question_score_total or abs(exam_total - question_score_total) <= 0.001,
            "gradingCheckTotal": len(checks),
            "gradingPlanTotal": len(assessment_plan),
            "gradingRefsCovered": not missing_refs,
            "gradingScoreMatched": not grading_total or not check_score_total or abs(grading_total - check_score_total) <= 0.001,
            "pptSlideTotal": len(slides),
            "candidatePreviewAnswerSafe": candidate_preview.get("answersRemoved") is True,
        },
        "issues": issues,
        "revisionSuggestions": suggestions,
    }


def _load_and_validate_dsl(path: Path, schema_name: str, *, root: Path, field: str) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise RealDslReviewPreviewError(
            "VALIDATION_ERROR",
            "真实 DSL 审核预览输入不存在",
            [{"field": field, "reason": "文件不存在"}],
        )
    try:
        dsl = load_yaml(path)
        validate_dsl(dsl, load_schema(schema_name, root))
    except DslValidationError as exc:
        raise RealDslReviewPreviewError(
            "SCHEMA_VALIDATION_ERROR",
            "真实 DSL 审核预览 Schema 校验失败",
            exc.errors,
        ) from exc
    if not isinstance(dsl, dict):
        raise RealDslReviewPreviewError(
            "SCHEMA_VALIDATION_ERROR",
            "真实 DSL 审核预览 Schema 校验失败",
            [{"field": "$", "reason": "root must be object"}],
        )
    return dsl


def _load_candidate_preview(
    exam: dict[str, Any],
    *,
    exam_path: Path,
    candidate_preview_path: Path | None,
    trace_id: str | None,
) -> dict[str, Any]:
    if candidate_preview_path is None:
        return build_candidate_safe_exam_preview(exam, source_path=exam_path, trace_id=trace_id)
    if not candidate_preview_path.exists() or not candidate_preview_path.is_file():
        raise RealDslReviewPreviewError(
            "VALIDATION_ERROR",
            "候选人预览文件不存在",
            [{"field": "candidatePreview", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(candidate_preview_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RealDslReviewPreviewError(
            "VALIDATION_ERROR",
            "候选人预览 JSON 解析失败",
            [{"field": "candidatePreview", "reason": str(exc)}],
        ) from exc
    if not isinstance(payload, dict):
        raise RealDslReviewPreviewError(
            "VALIDATION_ERROR",
            "候选人预览 JSON 格式错误",
            [{"field": "candidatePreview", "reason": "root must be object"}],
        )
    return payload


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _take_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _path_str(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)
