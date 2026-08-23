"""Build a review-gated teaching presentation from an approved teaching package."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable
from uuid import uuid4

from quality.ppt_preflight import (
    build_ppt_preflight_report,
    bullet_character_limit_for_layout,
    rendered_bullet_limit_for_layout,
    subtitle_character_limit_for_layout,
    title_character_limit_for_layout,
)

from .ai_task import TaskStatus, create_waiting_review_task
from .artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from .dsl import DslValidationError, load_schema, validate_dsl
from .review_batch import build_teaching_package_review_summary
from .store import JsonTaskStore
from .teaching_package_export import (
    TeachingPackageExportError,
    _build_candidate_preview,
    _load_and_validate_documents,
    _validate_cross_artifact_contract,
    _validate_export_gate,
)
from .workflow import create_workflow_run, create_workflow_step
from .workspace import workspace_root


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_PROFILE = "presentation-deck"
PRESENTATION_WORKFLOW_ID = "teaching_presentation_generation"
PRESENTATION_MODE = "LOCAL_TEACHING_PRESENTATION"
MIN_SLIDE_COUNT = 5
MAX_SLIDE_COUNT = 8
DEFAULT_SLIDE_COUNT = 6
ANSWER_FIELDS = frozenset({"answer", "standardAnswer", "solution", "referenceAnswer"})
REQUIRED_SEMANTIC_ROLES = ("hero", "objectives", "concept", "process", "exercise", "summary")

Builder = Callable[..., dict[str, Any]]


class TeachingPresentationError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def generate_teaching_presentation(
    store: JsonTaskStore,
    *,
    workflow_run_id: str,
    reviewer: str,
    slide_count: int = DEFAULT_SLIDE_COUNT,
    output_root: Path | str | None = None,
    trace_id: str | None = None,
    builder: Builder | None = None,
) -> dict[str, Any]:
    """Generate a local PPT DSL/PPTX pair without changing the parent review state."""

    workflow_run_id = str(workflow_run_id or "").strip()
    reviewer = str(reviewer or "").strip()
    _validate_inputs(workflow_run_id, reviewer, slide_count)
    effective_trace_id = str(trace_id or f"trace_{uuid4().hex[:12]}")

    try:
        review_summary = build_teaching_package_review_summary(store, workflow_run_id)
        source_artifacts, _ = _validate_export_gate(store, workflow_run_id, review_summary)
        documents = _load_and_validate_documents(source_artifacts)
        contract_summary = _validate_cross_artifact_contract(documents)
        candidate_preview = _build_candidate_preview(documents["exam"])
    except TeachingPackageExportError as exc:
        raise TeachingPresentationError(exc.code, exc.message, exc.errors) from exc

    if not isinstance(review_summary, dict) or review_summary.get("exportReady") is not True:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_SOURCE_NOT_READY",
            "教学包尚未满足演示课件生成条件",
            [{"field": "workflowRunId", "reason": "approved teaching-core package is required"}],
        )

    presentation = _build_presentation_dsl(
        workflow_run_id=workflow_run_id,
        lab=documents["lab"],
        candidate_preview=candidate_preview,
        slide_count=slide_count,
    )
    quality_report = _validate_presentation(
        presentation,
        expected_slide_count=slide_count,
        exam=documents["exam"],
        lab=documents["lab"],
        candidate_preview=candidate_preview,
    )

    task = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title=f"Teaching presentation for {workflow_run_id}",
        input_type="teaching_package_workflow",
        input_ref=workflow_run_id,
        trace_id=effective_trace_id,
    )
    workflow_steps = [
        create_workflow_step(
            "validate_source_teaching_package",
            1,
            {
                "sourceWorkflowRunId": workflow_run_id,
                "artifactProfile": "teaching-core",
                "approved": True,
                "schemaValidated": True,
                "crossArtifactValidated": True,
                "candidateSafe": True,
            },
        ),
        create_workflow_step(
            "build_presentation_dsl",
            2,
            {
                "taskId": task.id,
                "artifactProfile": PRESENTATION_PROFILE,
                "slideCount": slide_count,
                "schemaValidated": True,
                "candidateSafe": True,
            },
        ),
        create_workflow_step(
            "build_pptx_artifact",
            3,
            {
                "taskId": task.id,
                "slideCount": slide_count,
                "localOnly": True,
                "reviewRequired": True,
            },
        ),
        create_workflow_step(
            "enqueue_presentation_review",
            4,
            {
                "taskId": task.id,
                "status": TaskStatus.WAITING_REVIEW.value,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
            },
        ),
    ]
    child_run = create_workflow_run(
        workflow_id=PRESENTATION_WORKFLOW_ID,
        input_ref=workflow_run_id,
        reviewer=reviewer,
        trace_id=effective_trace_id,
        report_path=None,
        steps=workflow_steps,
    )
    child_run.mode = PRESENTATION_MODE

    base_output = _resolve_output_root(output_root)
    final_dir = base_output / child_run.id
    if final_dir.exists():
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_OUTPUT_CONFLICT",
            "演示课件输出目录已存在",
            [{"field": "outputRoot", "reason": "child workflow output already exists"}],
        )

    base_output.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{child_run.id}-", dir=str(base_output)))
    promoted = False
    try:
        staged_dsl_path = temporary_dir / "presentation.json"
        staged_pptx_path = temporary_dir / "presentation.pptx"
        staged_manifest_path = temporary_dir / "manifest.json"
        staged_preview_dir = temporary_dir / "slides"
        staged_contact_sheet_path = temporary_dir / "contact-sheet.png"
        _write_json(staged_dsl_path, presentation)

        build = _invoke_builder(
            builder,
            presentation,
            pptx_path=staged_pptx_path,
            preview_dir=staged_preview_dir,
            contact_sheet_path=staged_contact_sheet_path,
            manifest_path=staged_manifest_path,
        )
        staged_build = _validate_builder_output(
            build,
            temporary_dir=temporary_dir,
            pptx_path=staged_pptx_path,
            contact_sheet_path=staged_contact_sheet_path,
            expected_slide_count=slide_count,
        )

        final_dsl_path = final_dir / staged_dsl_path.relative_to(temporary_dir)
        final_pptx_path = final_dir / staged_pptx_path.relative_to(temporary_dir)
        final_manifest_path = final_dir / staged_manifest_path.relative_to(temporary_dir)
        final_slide_previews = _rebase_slide_previews(
            staged_build["slidePreviews"],
            temporary_dir=temporary_dir,
            final_dir=final_dir,
            presentation=presentation,
            quality_report=quality_report,
            reviewer=reviewer,
        )
        final_contact_sheet = _rebase_contact_sheet(
            staged_build["contactSheet"],
            temporary_dir=temporary_dir,
            final_dir=final_dir,
        )
        page_review_summary = _build_page_review_summary(final_slide_previews, quality_report)

        task.finalResultPath = str(final_dsl_path)
        dsl_artifact = create_artifact_record(
            kind=ArtifactKind.PPT_DSL,
            path=str(final_dsl_path),
            title=f"{presentation['metadata']['title']} PPT DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=effective_trace_id,
            task_id=task.id,
            workflow_run_id=child_run.id,
            source_ref=workflow_run_id,
            metadata={
                "dslKind": "PPT",
                "sourceWorkflowRunId": workflow_run_id,
                "artifactProfile": PRESENTATION_PROFILE,
                "slideCount": slide_count,
                "schemaValidated": True,
                "qualityReport": quality_report,
                "candidateSafety": _candidate_safety(),
                "reviewRequired": True,
                "autoPublishAllowed": False,
                "realPublish": False,
            },
            mode=PRESENTATION_MODE,
        )
        pptx_artifact = create_artifact_record(
            kind=ArtifactKind.PPTX_FILE,
            path=str(final_pptx_path),
            title=f"{presentation['metadata']['title']} PPTX",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=effective_trace_id,
            task_id=task.id,
            workflow_run_id=child_run.id,
            source_ref=dsl_artifact.id,
            metadata={
                "sourceWorkflowRunId": workflow_run_id,
                "artifactProfile": PRESENTATION_PROFILE,
                "sourceDslId": presentation["metadata"]["id"],
                "slideCount": slide_count,
                "sha256": staged_build["sha256"],
                "sizeBytes": staged_build["sizeBytes"],
                "generator": staged_build.get("generator"),
                "qualityReport": quality_report,
                "slidePreviews": final_slide_previews,
                "preview": {
                    "previewAvailable": True,
                    "slidePreviews": final_slide_previews,
                    "contactSheet": final_contact_sheet,
                    "firstSlide": final_slide_previews[0],
                },
                "pageReviewSummary": page_review_summary,
                "manifestPath": str(final_manifest_path),
                "contactSheet": final_contact_sheet,
                "candidateSafety": _candidate_safety(),
                "reviewRequired": True,
                "autoPublishAllowed": False,
                "realPublish": False,
            },
            mode=PRESENTATION_MODE,
        )
        child_run.reportPath = str(final_manifest_path)

        manifest = _build_manifest(
            source_workflow_run_id=workflow_run_id,
            child_run_id=child_run.id,
            task_id=task.id,
            dsl_artifact_id=dsl_artifact.id,
            pptx_artifact_id=pptx_artifact.id,
            dsl_path=final_dsl_path,
            pptx_path=final_pptx_path,
            manifest_path=final_manifest_path,
            slide_count=slide_count,
            sha256_value=staged_build["sha256"],
            size_bytes=staged_build["sizeBytes"],
            quality_report=quality_report,
            slide_previews=final_slide_previews,
            contact_sheet=final_contact_sheet,
            page_review_summary=page_review_summary,
            contract_summary=contract_summary,
        )
        _write_json(staged_manifest_path, manifest)

        os.replace(temporary_dir, final_dir)
        promoted = True
    except TeachingPresentationError:
        raise
    except Exception as exc:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_BUILD_ERROR",
            "演示课件构建失败",
            [{"field": "builder", "reason": str(exc)[:500] or "builder failed"}],
        ) from exc
    finally:
        if not promoted:
            shutil.rmtree(temporary_dir, ignore_errors=True)

    store.save(task)
    store.save_workflow_run(child_run)
    store.save_artifact(dsl_artifact)
    store.save_artifact(pptx_artifact)

    artifacts = [dsl_artifact.to_dict(), pptx_artifact.to_dict()]
    return {
        "component": "TeachingPresentationGenerationResult",
        "mode": PRESENTATION_MODE,
        "artifactProfile": PRESENTATION_PROFILE,
        "sourceWorkflowRunId": workflow_run_id,
        "slideCount": slide_count,
        "outputDirectory": str(final_dir),
        "presentationDsl": presentation,
        "presentationDslPath": str(final_dsl_path),
        "childWorkflowRun": child_run.to_dict(),
        "task": task.to_dict(),
        "artifacts": artifacts,
        "pptxArtifact": pptx_artifact.to_dict(),
        "qualityReport": quality_report,
        "pageReviewSummary": page_review_summary,
        "candidateSafety": _candidate_safety(),
        "safety": {
            "localOnly": True,
            "sourceTeachingPackageApproved": True,
            "sourceTaskStatusChanged": False,
            "schemaValidated": True,
            "crossArtifactValidated": True,
            "candidateSafe": True,
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "newLlmRequestSent": False,
            "secretsRead": False,
            "networkAccess": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "manualReviewRequired": True,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def _validate_inputs(workflow_run_id: str, reviewer: str, slide_count: int) -> None:
    errors: list[dict[str, str]] = []
    if not workflow_run_id:
        errors.append({"field": "workflowRunId", "reason": "required"})
    if not reviewer:
        errors.append({"field": "reviewer", "reason": "required"})
    if isinstance(slide_count, bool) or not isinstance(slide_count, int):
        errors.append({"field": "slideCount", "reason": "must be an integer from 5 to 8"})
    elif not MIN_SLIDE_COUNT <= slide_count <= MAX_SLIDE_COUNT:
        errors.append({"field": "slideCount", "reason": "must be between 5 and 8"})
    if errors:
        raise TeachingPresentationError("VALIDATION_ERROR", "演示课件生成参数错误", errors)


def _build_presentation_dsl(
    *,
    workflow_run_id: str,
    lab: dict[str, Any],
    candidate_preview: dict[str, Any],
    slide_count: int,
) -> dict[str, Any]:
    metadata = _mapping(lab.get("metadata"))
    spec = _mapping(lab.get("spec"))
    title = _short_text(metadata.get("title") or "教学演示课件", 30)
    objectives = _string_list(spec.get("objectives"))
    steps = _object_list(spec.get("steps"))
    questions = _object_list(candidate_preview.get("questions"))
    audience_items = _string_list(spec.get("targetUsers"))
    audience = "、".join(audience_items[:3]) or "学习者"
    duration = _positive_int(metadata.get("durationMinutes"), default=45)

    objective_bullets = _ensure_bullets(
        objectives,
        ["理解课程中的关键概念", "按步骤完成课堂实践", "能够复盘并说明实践结果"],
    )
    concept_bullets = _concept_bullets(metadata, spec, objectives)
    process_slide_capacity = rendered_bullet_limit_for_layout("process")
    if slide_count == 5:
        process_slot_total = max(1, process_slide_capacity - 1)
    elif slide_count == 6:
        process_slot_total = process_slide_capacity
    else:
        process_slot_total = process_slide_capacity * 2
    process_bullets = _process_bullets(steps, slot_limit=process_slot_total)
    exercise_bullets = _exercise_bullets(questions)
    summary_bullets = _ensure_bullets(
        [
            f"回顾：{objectives[0]}" if objectives else "回顾本课关键概念",
            f"流程：课件覆盖全部 {len(steps)} 个实验步骤" if steps else "流程：按步骤完成课堂任务",
            f"检查：完成 {len(questions)} 个课堂练习" if questions else "检查：完成课堂练习与自检",
            "整理成果并完成课堂复盘",
        ],
        ["回顾学习目标", "复盘实践过程", "整理可展示的学习成果"],
    )

    hero = _slide(
        "hero",
        "title",
        title,
        layout="hero",
        subtitle=_short_text(f"{audience} · {duration} 分钟 · 教学演示", 72),
    )
    objectives_slide = _slide(
        "objectives",
        "content",
        "学习目标",
        layout="objectives",
        bullets=objective_bullets,
    )
    concept_slide = _slide("concept", "content", "核心概念", layout="concept", bullets=concept_bullets)
    exercise_slide = _slide("exercise", "content", "课堂练习", layout="exercise", bullets=exercise_bullets)
    summary_slide = _slide("summary", "summary", "总结与下一步", layout="summary", bullets=summary_bullets)

    if slide_count == 5:
        middle = _slide(
            "concept_process",
            "content",
            "核心概念与实验流程",
            layout="process",
            bullets=_ensure_bullets(concept_bullets[:1] + process_bullets[:3], process_bullets),
        )
        slides = [hero, objectives_slide, middle, exercise_slide, summary_slide]
    elif slide_count == 6:
        slides = [
            hero,
            objectives_slide,
            concept_slide,
            _slide("process", "content", "实验步骤", layout="process", bullets=process_bullets),
            exercise_slide,
            summary_slide,
        ]
    elif slide_count == 7:
        first_process, second_process = _split_bullets(process_bullets)
        slides = [
            hero,
            objectives_slide,
            concept_slide,
            _slide("process_1", "content", "实验步骤 · 准备", layout="process", bullets=first_process),
            _slide("process_2", "content", "实验步骤 · 完成", layout="process", bullets=second_process),
            exercise_slide,
            summary_slide,
        ]
    else:
        first_process, second_process = _split_bullets(process_bullets)
        application_bullets = _ensure_bullets(
            objectives[1:4] + concept_bullets[-2:],
            ["把关键概念应用到实验任务", "记录选择与判断依据", "对照目标检查实践结果"],
        )
        slides = [
            hero,
            objectives_slide,
            concept_slide,
            _slide(
                "concept_application",
                "content",
                "概念应用",
                layout="concept",
                bullets=application_bullets,
            ),
            _slide("process_1", "content", "实验步骤 · 准备", layout="process", bullets=first_process),
            _slide("process_2", "content", "实验步骤 · 完成", layout="process", bullets=second_process),
            exercise_slide,
            summary_slide,
        ]

    for index, slide in enumerate(slides, start=1):
        slide["id"] = f"slide_{index}_{slide['id']}"

    return {
        "version": "1.0",
        "kind": "PPT",
        "metadata": {
            "id": f"ppt_{workflow_run_id}",
            "title": title,
            "audience": audience,
            "durationMinutes": duration,
        },
        "status": TaskStatus.WAITING_REVIEW.value,
        "spec": {
            "theme": {"style": "teaching-presentation-v1", "language": "zh-CN"},
            "slides": slides,
        },
    }


def _validate_presentation(
    presentation: dict[str, Any],
    *,
    expected_slide_count: int,
    exam: dict[str, Any],
    lab: dict[str, Any],
    candidate_preview: dict[str, Any],
) -> dict[str, Any]:
    try:
        validate_dsl(presentation, load_schema("ppt", ROOT))
    except DslValidationError as exc:
        raise TeachingPresentationError(
            "SCHEMA_VALIDATION_ERROR",
            "演示课件 PPT DSL Schema 校验失败",
            [{"field": str(item.get("field") or "ppt"), "reason": "schema validation failed"} for item in exc.errors[:20]],
        ) from exc

    slides = _object_list(_mapping(presentation.get("spec")).get("slides"))
    errors: list[dict[str, str]] = []
    if len(slides) != expected_slide_count or not MIN_SLIDE_COUNT <= len(slides) <= MAX_SLIDE_COUNT:
        errors.append({"field": "$.spec.slides", "reason": "presentation deck must contain 5 to 8 slides"})
    slide_ids = [str(slide.get("id") or "") for slide in slides]
    if not all(slide_ids) or len(set(slide_ids)) != len(slide_ids):
        errors.append({"field": "$.spec.slides[].id", "reason": "slide IDs must be non-empty and unique"})
    if not slides or slides[0].get("type") != "title" or "hero" not in slide_ids[0]:
        errors.append({"field": "$.spec.slides[0]", "reason": "first slide must be the hero title slide"})
    if not slides or slides[-1].get("type") != "summary" or "summary" not in slide_ids[-1]:
        errors.append({"field": "$.spec.slides[-1]", "reason": "last slide must be the summary slide"})
    for role in REQUIRED_SEMANTIC_ROLES:
        if not any(role in slide_id for slide_id in slide_ids):
            errors.append({"field": "$.spec.slides", "reason": f"missing required {role} section"})
    if errors:
        raise TeachingPresentationError("TEACHING_PRESENTATION_VALIDATION_ERROR", "演示课件结构校验失败", errors)

    leaks = _find_presentation_leaks(
        presentation,
        exam,
        lab=lab,
        candidate_preview=candidate_preview,
    )
    if leaks:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_CANDIDATE_LEAK_DETECTED",
            "演示课件检测到标准答案或内部评分引用泄露",
            leaks,
        )

    report = build_ppt_preflight_report(presentation)
    if report.get("status") == "BLOCKED" or int(report.get("blockingIssueTotal") or 0) > 0:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_PREFLIGHT_BLOCKED",
            "演示课件质量预检未通过",
            [
                {"field": str(issue.get("path") or "$.spec.slides"), "reason": str(issue.get("code") or "blocking issue")}
                for issue in report.get("issues", [])
                if isinstance(issue, dict) and issue.get("severity") == "BLOCKING"
            ] or [{"field": "$.spec.slides", "reason": "quality preflight blocked"}],
        )
    return {
        **report,
        "profile": PRESENTATION_PROFILE,
        "minimumSlideCount": MIN_SLIDE_COUNT,
        "maximumSlideCount": MAX_SLIDE_COUNT,
        "slideCountInRange": True,
        "requiredSemanticRoles": list(REQUIRED_SEMANTIC_ROLES),
        "requiredSemanticRolesPresent": True,
        "uniqueSlideIds": True,
        "candidateSafe": True,
    }


def _find_presentation_leaks(
    presentation: dict[str, Any],
    exam: dict[str, Any],
    *,
    lab: dict[str, Any] | None = None,
    candidate_preview: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    visible_fields = list(_iter_visible_text(presentation))
    if lab is not None or candidate_preview is not None:
        visible_fields.extend(_iter_presentation_source_text(lab or {}, candidate_preview or {}))
    questions = _object_list(_mapping(exam.get("spec")).get("questions"))
    answer_values = [
        _normalize_sensitive_value(question.get(field))
        for question in questions
        for field in ANSWER_FIELDS
        if question.get(field) is not None
    ]
    grading_refs = [
        _normalize_sensitive_value(question.get("gradingRef"))
        for question in questions
        if question.get("gradingRef") is not None
    ]
    errors: list[dict[str, str]] = []
    for path, text in visible_fields:
        normalized = text.casefold()
        if "gradingref" in normalized:
            errors.append({"field": path, "reason": "presentation contains internal grading reference"})
            continue
        if any(_sensitive_value_matches(value, normalized) for value in grading_refs if value):
            errors.append({"field": path, "reason": "presentation contains internal grading reference value"})
            continue
        if any(_sensitive_value_matches(value, normalized) for value in answer_values if value):
            errors.append({"field": path, "reason": "presentation contains answer text"})
    return _deduplicate_errors(errors)


def _iter_presentation_source_text(
    lab: dict[str, Any],
    candidate_preview: dict[str, Any],
) -> Iterable[tuple[str, str]]:
    metadata = _mapping(lab.get("metadata"))
    for key in ("title", "category", "difficulty"):
        value = _clean_text(metadata.get(key))
        if value:
            yield f"$.source.lab.metadata.{key}", value
    for index, value in enumerate(_string_list(metadata.get("tags"))):
        yield f"$.source.lab.metadata.tags[{index}]", value

    spec = _mapping(lab.get("spec"))
    for key in ("objectives", "targetUsers"):
        for index, value in enumerate(_string_list(spec.get(key))):
            yield f"$.source.lab.spec.{key}[{index}]", value
    environment_type = _clean_text(_mapping(spec.get("environment")).get("type"))
    if environment_type:
        yield "$.source.lab.spec.environment.type", environment_type
    for index, step in enumerate(_object_list(spec.get("steps"))):
        for key in ("title", "instruction"):
            value = _clean_text(step.get(key))
            if value:
                yield f"$.source.lab.spec.steps[{index}].{key}", value

    for index, question in enumerate(_object_list(candidate_preview.get("questions"))):
        for key in ("title", "stem"):
            value = _clean_text(question.get(key))
            if value:
                yield f"$.source.candidatePreview.questions[{index}].{key}", value


def _iter_visible_text(presentation: dict[str, Any]) -> Iterable[tuple[str, str]]:
    metadata = _mapping(presentation.get("metadata"))
    for key in ("title", "audience"):
        value = _clean_text(metadata.get(key))
        if value:
            yield f"$.metadata.{key}", value
    slides = _object_list(_mapping(presentation.get("spec")).get("slides"))
    for index, slide in enumerate(slides):
        for key in ("title", "subtitle"):
            value = _clean_text(slide.get(key))
            if value:
                yield f"$.spec.slides[{index}].{key}", value
        for bullet_index, bullet in enumerate(_string_list(slide.get("bullets"))):
            yield f"$.spec.slides[{index}].bullets[{bullet_index}]", bullet


def _invoke_builder(
    builder: Builder | None,
    presentation: dict[str, Any],
    **paths: Path,
) -> dict[str, Any]:
    if builder is None:
        from .pptx_artifact import build_pptx_artifact

        builder = build_pptx_artifact
    result = builder(presentation, **paths)
    if not isinstance(result, dict):
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_BUILD_ERROR",
            "演示课件构建失败",
            [{"field": "builder", "reason": "builder result must be an object"}],
        )
    return result


def _validate_builder_output(
    build: dict[str, Any],
    *,
    temporary_dir: Path,
    pptx_path: Path,
    contact_sheet_path: Path,
    expected_slide_count: int,
) -> dict[str, Any]:
    try:
        builder_slide_count = int(build.get("slideCount"))
    except (TypeError, ValueError) as exc:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_BUILD_ERROR",
            "演示课件构建结果无效",
            [{"field": "builder.slideCount", "reason": "missing or invalid"}],
        ) from exc
    if builder_slide_count != expected_slide_count:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_BUILD_ERROR",
            "演示课件构建页数不一致",
            [{"field": "builder.slideCount", "reason": "must match presentation DSL"}],
        )
    _require_staged_file(pptx_path, temporary_dir, "builder.pptx")
    _require_staged_file(contact_sheet_path, temporary_dir, "builder.contactSheet")
    previews = build.get("slidePreviews")
    if not isinstance(previews, list) or len(previews) != expected_slide_count:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_BUILD_ERROR",
            "演示课件预览不完整",
            [{"field": "builder.slidePreviews", "reason": "one preview per slide is required"}],
        )
    normalized_previews: list[dict[str, Any]] = []
    for index, preview in enumerate(previews, start=1):
        if not isinstance(preview, dict):
            raise TeachingPresentationError(
                "TEACHING_PRESENTATION_BUILD_ERROR",
                "演示课件预览不完整",
                [{"field": f"builder.slidePreviews[{index - 1}]", "reason": "must be an object"}],
            )
        preview_path_value = preview.get("imagePath") or preview.get("path") or preview.get("thumbnailPath")
        preview_path = Path(str(preview_path_value or ""))
        if not preview_path.is_absolute():
            preview_path = temporary_dir / preview_path
        _require_staged_file(preview_path, temporary_dir, f"builder.slidePreviews[{index - 1}]")
        normalized_previews.append({**preview, "index": index, "imagePath": str(preview_path.resolve())})
    pptx_bytes = pptx_path.read_bytes()
    return {
        "slideCount": expected_slide_count,
        "sha256": sha256(pptx_bytes).hexdigest(),
        "sizeBytes": len(pptx_bytes),
        "generator": build.get("generator"),
        "slidePreviews": normalized_previews,
        "contactSheet": {
            **(build.get("contactSheet") if isinstance(build.get("contactSheet"), dict) else {}),
            "path": str(contact_sheet_path.resolve()),
            "slideCount": expected_slide_count,
            "sizeBytes": contact_sheet_path.stat().st_size,
        },
    }


def _require_staged_file(path: Path, temporary_dir: Path, field: str) -> None:
    try:
        resolved = path.resolve()
        resolved.relative_to(temporary_dir.resolve())
    except (OSError, ValueError) as exc:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_BUILD_ERROR",
            "演示课件构建路径无效",
            [{"field": field, "reason": "builder output must stay inside the staging directory"}],
        ) from exc
    if not resolved.is_file() or resolved.stat().st_size <= 0:
        raise TeachingPresentationError(
            "TEACHING_PRESENTATION_BUILD_ERROR",
            "演示课件构建结果缺失",
            [{"field": field, "reason": "required non-empty file is missing"}],
        )


def _rebase_slide_previews(
    previews: list[dict[str, Any]],
    *,
    temporary_dir: Path,
    final_dir: Path,
    presentation: dict[str, Any],
    quality_report: dict[str, Any],
    reviewer: str,
) -> list[dict[str, Any]]:
    slides = _object_list(_mapping(presentation.get("spec")).get("slides"))
    quality_by_index = {
        item.get("index"): item
        for item in quality_report.get("slides", [])
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }
    result: list[dict[str, Any]] = []
    for index, preview in enumerate(previews, start=1):
        staged_path = Path(str(preview["imagePath"])).resolve()
        final_path = final_dir / staged_path.relative_to(temporary_dir.resolve())
        slide = slides[index - 1]
        quality = quality_by_index.get(index, {})
        result.append(
            {
                **preview,
                "index": index,
                "id": slide.get("id"),
                "title": slide.get("title"),
                "type": slide.get("type"),
                "imagePath": str(final_path),
                "thumbnailPath": str(final_path),
                "reviewStatus": "NEEDS_REVIEW",
                "manualComment": {
                    "required": True,
                    "text": "请人工确认本页内容、版式和课程目标是否匹配。",
                    "reviewer": reviewer,
                    "updatedAt": None,
                },
                "qaSignals": {
                    "layout": "NEEDS_REVIEW",
                    "textOverflow": quality.get("estimatedTextOverflow", False),
                    "visualDensity": quality.get("visualDensity", "UNKNOWN"),
                    "contentQuality": quality.get("status", "UNKNOWN"),
                    "qualityIssueCodes": [
                        issue.get("code")
                        for issue in quality.get("issues", [])
                        if isinstance(issue, dict) and issue.get("code")
                    ],
                    "contrast": "NEEDS_REVIEW",
                    "reviewFocus": "manual_page_review_required",
                },
            }
        )
    return result


def _rebase_contact_sheet(contact_sheet: dict[str, Any], *, temporary_dir: Path, final_dir: Path) -> dict[str, Any]:
    staged_path = Path(str(contact_sheet["path"])).resolve()
    return {
        **contact_sheet,
        "path": str(final_dir / staged_path.relative_to(temporary_dir.resolve())),
    }


def _build_page_review_summary(
    slide_previews: list[dict[str, Any]],
    quality_report: dict[str, Any],
) -> dict[str, Any]:
    total = len(slide_previews)
    return {
        "status": "NEEDS_REVIEW",
        "total": total,
        "approved": 0,
        "needsReview": total,
        "reviseRequired": 0,
        "manualCommentTotal": total,
        "qaSignalStatus": "NEEDS_REVIEW",
        "preflightStatus": quality_report.get("status", "UNKNOWN"),
        "preflightIssueTotal": quality_report.get("issueTotal", 0),
        "preflightBlockingIssueTotal": quality_report.get("blockingIssueTotal", 0),
        "preflightWarningIssueTotal": quality_report.get("warningIssueTotal", 0),
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _build_manifest(**values: Any) -> dict[str, Any]:
    return {
        "component": "TeachingPresentationManifest",
        "mode": PRESENTATION_MODE,
        "artifactProfile": PRESENTATION_PROFILE,
        "sourceWorkflowRunId": values["source_workflow_run_id"],
        "workflowRunId": values["child_run_id"],
        "taskId": values["task_id"],
        "status": TaskStatus.WAITING_REVIEW.value,
        "slideCount": values["slide_count"],
        "files": {
            "presentationDsl": str(values["dsl_path"]),
            "pptx": str(values["pptx_path"]),
            "manifest": str(values["manifest_path"]),
            "slidePreviews": [item["imagePath"] for item in values["slide_previews"]],
            "contactSheet": values["contact_sheet"]["path"],
        },
        "artifacts": {
            "pptDslArtifactId": values["dsl_artifact_id"],
            "pptxArtifactId": values["pptx_artifact_id"],
        },
        "integrity": {
            "algorithm": "SHA-256",
            "sha256": values["sha256_value"],
            "sizeBytes": values["size_bytes"],
        },
        "qualityReport": values["quality_report"],
        "slidePreviews": values["slide_previews"],
        "contactSheet": values["contact_sheet"],
        "pageReviewSummary": values["page_review_summary"],
        "sourceValidation": {
            "schemaValidated": True,
            "crossArtifactValidated": True,
            **values["contract_summary"],
        },
        "candidateSafety": _candidate_safety(),
        "safety": {
            "localOnly": True,
            "manualReviewRequired": True,
            "networkAccess": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def _resolve_output_root(output_root: Path | str | None) -> Path:
    if output_root is None:
        return workspace_root(root=ROOT) / "examples" / "output" / "teaching-presentations"
    return Path(output_root).expanduser().resolve()


def _slide(
    semantic_id: str,
    slide_type: str,
    title: str,
    *,
    layout: str,
    subtitle: str | None = None,
    bullets: list[str] | None = None,
) -> dict[str, Any]:
    slide: dict[str, Any] = {
        "id": semantic_id,
        "type": slide_type,
        "layout": layout,
        "title": _short_text(title, title_character_limit_for_layout(layout)),
    }
    if subtitle:
        slide["subtitle"] = _short_text(subtitle, subtitle_character_limit_for_layout(layout))
    if bullets:
        rendered_bullet_limit = rendered_bullet_limit_for_layout(layout)
        slide["bullets"] = [
            _short_text(item, bullet_character_limit_for_layout(layout, index))
            for index, item in enumerate(bullets[:rendered_bullet_limit])
        ]
    return slide


def _concept_bullets(metadata: dict[str, Any], spec: dict[str, Any], objectives: list[str]) -> list[str]:
    environment = _mapping(spec.get("environment"))
    candidates = [
        f"课程主题：{_clean_text(metadata.get('category') or metadata.get('title'))}",
        f"学习难度：{_clean_text(metadata.get('difficulty') or '按课堂要求完成')}",
        f"关键技术：{'、'.join(_string_list(metadata.get('tags'))[:4])}" if _string_list(metadata.get("tags")) else "围绕课程目标理解关键方法",
        f"实践环境：{_clean_text(environment.get('type'))}" if environment.get("type") else "在指定实践环境中完成任务",
        objectives[0] if objectives else "理解概念与实践任务之间的关系",
    ]
    return _ensure_bullets(candidates, ["理解关键概念", "识别实践重点", "说明方法的适用场景"])


def _process_bullets(steps: list[dict[str, Any]], *, slot_limit: int) -> list[str]:
    fallbacks = ["检查实践环境", "按步骤完成任务", "记录并复核实践结果"]
    if not steps:
        return _ensure_bullets([], fallbacks)

    direct_step_total = len(steps)
    if len(steps) > slot_limit:
        direct_step_total = max(0, slot_limit - 1)

    items = []
    for step in steps[:direct_step_total]:
        title = _clean_text(step.get("title")) or "完成实验步骤"
        instruction = _clean_text(step.get("instruction"))
        items.append(f"{title}：{instruction}" if instruction else title)
    if direct_step_total < len(steps):
        remaining_total = len(steps) - direct_step_total
        items.append(
            f"步骤 {direct_step_total + 1}-{len(steps)}：完成其余 {remaining_total} 步并整理结果"
        )

    result = [_short_text(item, 88) for item in items if _clean_text(item)]
    for fallback in fallbacks:
        if len(result) >= min(3, slot_limit):
            break
        if fallback not in result:
            result.append(fallback)
    return result[:slot_limit]


def _exercise_bullets(questions: list[dict[str, Any]]) -> list[str]:
    items = []
    for question in questions[:3]:
        title = _clean_text(question.get("title")) or "课堂练习"
        stem = _clean_text(question.get("stem"))
        items.append(f"{title}：{stem}" if stem else title)
    return _ensure_bullets(
        items,
        ["独立完成题目要求", "记录关键思路与操作过程", "完成后对照课程目标进行自检"],
    )


def _ensure_bullets(items: list[str], fallbacks: list[str]) -> list[str]:
    result: list[str] = []
    for value in [*items, *fallbacks]:
        text = _short_text(value, 88)
        if text and text not in result:
            result.append(text)
        if len(result) >= 5:
            break
    while len(result) < 3:
        result.append(f"课堂要点 {len(result) + 1}")
    return result


def _split_bullets(items: list[str]) -> tuple[list[str], list[str]]:
    midpoint = max(1, (len(items) + 1) // 2)
    first = _ensure_bullets(items[:midpoint], ["确认环境与任务要求", "明确本轮实践目标", "准备所需材料"])
    second = _ensure_bullets(items[midpoint:], ["完成核心操作", "检查实践结果", "整理过程记录"])
    return first, second


def _candidate_safety() -> dict[str, bool]:
    return {
        "candidateSafe": True,
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _object_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _short_text(value: Any, maximum: int) -> str:
    text = _clean_text(value)
    if len(text) <= maximum:
        return text
    return text[: maximum - 1].rstrip() + "…"


def _positive_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _normalize_sensitive_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).strip().casefold()
    return _clean_text(value).casefold()


def _sensitive_value_matches(value: str, visible_text: str) -> bool:
    if not value:
        return False
    if len(value) <= 4:
        if re.fullmatch(r"[a-z0-9][a-z0-9._+-]{0,3}", value):
            return re.search(rf"(?<![a-z0-9_]){re.escape(value)}(?![a-z0-9_])", visible_text) is not None
        return value in visible_text
    return value in visible_text


def _deduplicate_errors(errors: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for error in errors:
        key = (error["field"], error["reason"])
        if key not in seen:
            seen.add(key)
            result.append(error)
    return result
