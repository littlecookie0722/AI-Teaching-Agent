"""Local Lab DSL to platform import preview helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ai_task import TaskStatus
from .artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationResourceType, create_operation_audit_event
from .dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from .agent_entity import AgentEntityType, create_agent_entity_record
from .store import JsonTaskStore
from .workspace import resolve_cli_path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_TEMPLATE_IMPORT_PREVIEW_PATH = Path("examples/output/lab-template-import-preview.json")
DEFAULT_EXAM_QUESTION_IMPORT_PREVIEW_PATH = Path("examples/output/exam-question-import-preview.json")
DEFAULT_GRADING_RULE_IMPORT_PREVIEW_PATH = Path("examples/output/grading-rule-import-preview.json")
DEFAULT_PPT_DECK_IMPORT_PREVIEW_PATH = Path("examples/output/ppt-deck-import-preview.json")
DEFAULT_LAB_TEMPLATE_MOCK_IMPORT_PATH = Path("examples/output/lab-template-mock-import.json")
DEFAULT_EXAM_QUESTION_MOCK_IMPORT_PATH = Path("examples/output/exam-question-mock-import.json")
DEFAULT_GRADING_RULE_MOCK_IMPORT_PATH = Path("examples/output/grading-rule-mock-import.json")
DEFAULT_PPT_DECK_MOCK_IMPORT_PATH = Path("examples/output/ppt-deck-mock-import.json")
DEFAULT_GRADING_EVIDENCE_AUTO_PATH = Path("examples/output/grading-evidence-auto.json")
DEFAULT_CONTROLLED_COMMAND_SANDBOX_REPORT_PATH = Path("examples/output/controlled-command-sandbox-report.json")
DEFAULT_REVIEW_SUBMISSION_PATH = Path("examples/submissions/readonly-demo")


class LabTemplateImportPreviewError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


class AgentImportPreviewError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


class AgentEntityMockImportError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _resolve_local_path(path_value: str | None) -> Path | None:
    if not path_value or "://" in path_value:
        return None
    return resolve_cli_path(path_value, root=ROOT)


def _primary_lab_artifact(store: JsonTaskStore, task_id: str) -> Any | None:
    for artifact in store.list_artifacts(task_id=task_id, kind=ArtifactKind.LAB_DSL.value):
        return artifact
    return None


def _primary_artifact(store: JsonTaskStore, task_id: str, kind: ArtifactKind) -> Any | None:
    for artifact in store.list_artifacts(task_id=task_id, kind=kind.value):
        return artifact
    return None


def _latest_platform_import_preview_artifact(
    store: JsonTaskStore,
    *,
    task_id: str,
    component: str,
    agent_entity: str,
) -> Any | None:
    for artifact in store.list_artifacts(task_id=task_id, kind=ArtifactKind.WORKFLOW_REPORT.value):
        metadata = artifact.metadata if isinstance(artifact.metadata, dict) else {}
        if (
            artifact.mode == "LOCAL_PLATFORM_IMPORT_PREVIEW"
            and metadata.get("component") == component
            and metadata.get("agentEntity") == agent_entity
        ):
            return artifact
    return None


def _load_preview_payload(artifact: Any) -> dict[str, Any]:
    preview_path = _resolve_local_path(artifact.path)
    if preview_path is None or not preview_path.exists() or not preview_path.is_file():
        raise AgentEntityMockImportError(
            "VALIDATION_ERROR",
            "平台导入预览文件不存在",
            [{"field": "previewArtifact.path", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(preview_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEntityMockImportError(
            "VALIDATION_ERROR",
            "平台导入预览文件格式错误",
            [{"field": "previewArtifact.path", "reason": "expected JSON object"}],
        ) from exc
    if not isinstance(payload, dict):
        raise AgentEntityMockImportError(
            "VALIDATION_ERROR",
            "平台导入预览文件格式错误",
            [{"field": "previewArtifact", "reason": "expected object"}],
        )
    return payload


def _validated_artifact_dsl(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    artifact_kind: ArtifactKind,
    schema_kind: str,
    label: str,
) -> tuple[Any, Any, dict[str, Any]]:
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise AgentImportPreviewError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    task = store.get(task_id)
    if task is None:
        raise AgentImportPreviewError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )
    if task.status != TaskStatus.APPROVED:
        raise AgentImportPreviewError(
            "STATE_TRANSITION_ERROR",
            f"{label}导入预览要求任务已审核通过",
            [{"field": "status", "reason": "expected APPROVED"}],
        )
    artifact = _primary_artifact(store, task_id, artifact_kind)
    if artifact is None:
        raise AgentImportPreviewError(
            "VALIDATION_ERROR",
            f"任务未关联 {artifact_kind.value} Artifact",
            [{"field": "taskId", "reason": f"missing {artifact_kind.value} artifact"}],
        )
    dsl_path = _resolve_local_path(artifact.path)
    if dsl_path is None or not dsl_path.exists() or not dsl_path.is_file():
        raise AgentImportPreviewError(
            "VALIDATION_ERROR",
            f"{label} DSL 文件不存在",
            [{"field": "artifact.path", "reason": "文件不存在"}],
        )
    try:
        dsl = load_yaml(dsl_path)
        validate_dsl(dsl, load_schema(schema_kind, ROOT))
    except DslValidationError as exc:
        raise AgentImportPreviewError(
            "SCHEMA_VALIDATION_ERROR",
            f"{label} DSL Schema 校验失败",
            exc.errors,
        ) from exc
    return task, artifact, dsl


def _lab_template_draft_from_dsl(lab_dsl: dict[str, Any], *, source_task_id: str, source_path: str) -> dict[str, Any]:
    metadata = lab_dsl.get("metadata", {}) if isinstance(lab_dsl.get("metadata"), dict) else {}
    spec = lab_dsl.get("spec", {}) if isinstance(lab_dsl.get("spec"), dict) else {}
    objectives = spec.get("objectives") if isinstance(spec.get("objectives"), list) else []
    steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
    materials = spec.get("materials") if isinstance(spec.get("materials"), list) else []
    environment = spec.get("environment") if isinstance(spec.get("environment"), dict) else {}
    grading = spec.get("grading") if isinstance(spec.get("grading"), dict) else {}
    return {
        "id": str(metadata.get("id") or "lab_template_preview"),
        "title": str(metadata.get("title") or "Untitled Lab Template"),
        "category": metadata.get("category"),
        "difficulty": metadata.get("difficulty"),
        "durationMinutes": metadata.get("durationMinutes"),
        "tags": metadata.get("tags", []),
        "status": "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW",
        "sourceTaskId": source_task_id,
        "sourceDslPath": source_path,
        "objectiveTotal": len(objectives),
        "stepTotal": len(steps),
        "materialTotal": len(materials),
        "environment": {
            "type": environment.get("type"),
            "image": environment.get("image"),
            "resources": environment.get("resources", {}),
        },
        "gradingRef": grading.get("ref"),
        "reviewChecklist": [
            "confirm_objectives_are_measurable",
            "confirm_steps_are_teachable",
            "confirm_environment_matches_platform_capacity",
            "confirm_grading_ref_is_available_or_planned",
            "confirm_no_auto_publish",
        ],
    }


def _exam_question_draft_from_dsl(exam_dsl: dict[str, Any], *, source_task_id: str, source_path: str) -> dict[str, Any]:
    metadata = exam_dsl.get("metadata", {}) if isinstance(exam_dsl.get("metadata"), dict) else {}
    spec = exam_dsl.get("spec", {}) if isinstance(exam_dsl.get("spec"), dict) else {}
    questions = spec.get("questions") if isinstance(spec.get("questions"), list) else []
    return {
        "id": str(metadata.get("id") or "exam_question_preview"),
        "title": str(metadata.get("title") or "Untitled Exam Question Set"),
        "sourceLabId": metadata.get("sourceLabId"),
        "difficulty": metadata.get("difficulty"),
        "questionType": spec.get("questionType"),
        "status": "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW",
        "sourceTaskId": source_task_id,
        "sourceDslPath": source_path,
        "totalScore": spec.get("totalScore"),
        "questionTotal": len(questions),
        "questionIds": [str(item.get("id")) for item in questions if isinstance(item, dict) and item.get("id")],
        "gradingRefs": [
            str(item.get("gradingRef"))
            for item in questions
            if isinstance(item, dict) and item.get("gradingRef")
        ],
        "answerStoragePolicy": "teacher_only_do_not_show_to_candidate",
        "candidateAnswerVisible": False,
        "reviewChecklist": [
            "confirm_question_stems_are_clear",
            "confirm_score_total_matches_questions",
            "confirm_answers_are_teacher_only",
            "confirm_grading_refs_match_grading_rules",
            "confirm_no_auto_publish",
        ],
    }


def _grading_rule_draft_from_dsl(grading_dsl: dict[str, Any], *, source_task_id: str, source_path: str) -> dict[str, Any]:
    metadata = grading_dsl.get("metadata", {}) if isinstance(grading_dsl.get("metadata"), dict) else {}
    spec = grading_dsl.get("spec", {}) if isinstance(grading_dsl.get("spec"), dict) else {}
    checks = spec.get("checks") if isinstance(spec.get("checks"), list) else []
    assessment_plan = spec.get("assessmentPlan") if isinstance(spec.get("assessmentPlan"), list) else []
    return {
        "id": str(metadata.get("id") or "grading_rule_preview"),
        "title": str(metadata.get("title") or "Untitled Grading Rule Set"),
        "sourceExamId": metadata.get("sourceExamId"),
        "status": "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW",
        "sourceTaskId": source_task_id,
        "sourceDslPath": source_path,
        "totalScore": spec.get("totalScore"),
        "timeoutSeconds": spec.get("timeoutSeconds"),
        "checkTotal": len(checks),
        "checkIds": [str(item.get("id")) for item in checks if isinstance(item, dict) and item.get("id")],
        "runnerTypes": sorted({str(item.get("type")) for item in checks if isinstance(item, dict) and item.get("type")}),
        "assessmentPlanTotal": len(assessment_plan),
        "sandboxRequiredBeforeRealExecution": True,
        "reviewChecklist": [
            "confirm_checks_match_exam_grading_refs",
            "confirm_total_score_matches_exam",
            "confirm_execution_limits_are_complete",
            "confirm_real_sandbox_required_before_execution",
            "confirm_no_auto_publish",
        ],
    }


def _ppt_deck_draft_from_dsl(ppt_dsl: dict[str, Any], *, source_task_id: str, source_path: str) -> dict[str, Any]:
    metadata = ppt_dsl.get("metadata", {}) if isinstance(ppt_dsl.get("metadata"), dict) else {}
    spec = ppt_dsl.get("spec", {}) if isinstance(ppt_dsl.get("spec"), dict) else {}
    theme = spec.get("theme") if isinstance(spec.get("theme"), dict) else {}
    slides = spec.get("slides") if isinstance(spec.get("slides"), list) else []
    slide_dicts = [item for item in slides if isinstance(item, dict)]
    first_slide = slide_dicts[0] if slide_dicts else {}
    slide_types = sorted({str(item.get("type")) for item in slide_dicts if item.get("type")})
    return {
        "id": str(metadata.get("id") or "ppt_deck_preview"),
        "title": str(metadata.get("title") or "Untitled PPT Deck"),
        "audience": metadata.get("audience"),
        "durationMinutes": metadata.get("durationMinutes"),
        "status": "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW",
        "sourceTaskId": source_task_id,
        "sourceDslPath": source_path,
        "theme": {
            "style": theme.get("style"),
            "language": theme.get("language"),
        },
        "slideTotal": len(slide_dicts),
        "slideIds": [str(item.get("id")) for item in slide_dicts if item.get("id")],
        "slideTypes": slide_types,
        "firstSlideTitle": first_slide.get("title"),
        "pptxArtifactRequiredBeforePublish": True,
        "pptxArtifactImported": False,
        "reviewChecklist": [
            "confirm_slide_plan_matches_teaching_objectives",
            "confirm_pptx_artifact_generated_and_reviewed",
            "confirm_titles_and_bullets_are_classroom_ready",
            "confirm_no_auto_publish",
        ],
    }


def _controlled_grading_evidence_next_action(
    *,
    task_id: str,
    source_path: str,
) -> dict[str, Any]:
    evidence_output = DEFAULT_GRADING_EVIDENCE_AUTO_PATH.as_posix()
    controlled_report_output = DEFAULT_CONTROLLED_COMMAND_SANDBOX_REPORT_PATH.as_posix()
    submission_path = DEFAULT_REVIEW_SUBMISSION_PATH.as_posix()
    return {
        "component": "ControlledGradingEvidenceNextAction",
        "mode": "LOCAL_REVIEW_ACTION_PLAN",
        "taskId": task_id,
        "sourceGradingPath": source_path,
        "submissionSuggestion": submission_path,
        "outputSuggestion": evidence_output,
        "controlledReportOutputSuggestion": controlled_report_output,
        "apiEndpoint": "POST /api/grading/evidence-auto",
        "cliCommand": (
            "python lab_cli.py grade evidence-auto "
            f"--task-id {task_id} --grading {source_path} --submission {submission_path} "
            f"--output {evidence_output} --include-controlled-command"
        ),
        "readonlyCliCommand": (
            "python lab_cli.py grade evidence-auto "
            f"--task-id {task_id} --grading {source_path} --submission {submission_path} "
            f"--output {evidence_output}"
        ),
        "controlledSandboxCliCommand": (
            "python lab_cli.py grade sandbox-run --execution-mode controlled-command "
            f"--grading {source_path} --submission {submission_path} --output {controlled_report_output}"
        ),
        "nextRequiredAction": "run_grading_evidence_auto_before_final_grading_rule_import_review",
        "manualReviewRequired": True,
        "controlledCommandOptInRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "safety": {
            "previewRunsCommand": False,
            "sandboxExecutedByPreview": False,
            "contestantCodeExecutedByPreview": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        },
    }


def create_lab_template_import_preview(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise LabTemplateImportPreviewError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    task = store.get(task_id)
    if task is None:
        raise LabTemplateImportPreviewError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )
    if task.status != TaskStatus.APPROVED:
        raise LabTemplateImportPreviewError(
            "STATE_TRANSITION_ERROR",
            "Lab 模板导入预览要求任务已审核通过",
            [{"field": "status", "reason": "expected APPROVED"}],
        )
    artifact = _primary_lab_artifact(store, task_id)
    if artifact is None:
        raise LabTemplateImportPreviewError(
            "VALIDATION_ERROR",
            "任务未关联 Lab DSL Artifact",
            [{"field": "taskId", "reason": "missing LAB_DSL artifact"}],
        )
    lab_path = _resolve_local_path(artifact.path)
    if lab_path is None or not lab_path.exists() or not lab_path.is_file():
        raise LabTemplateImportPreviewError(
            "VALIDATION_ERROR",
            "Lab DSL 文件不存在",
            [{"field": "artifact.path", "reason": "文件不存在"}],
        )
    try:
        lab_dsl = load_yaml(lab_path)
        validate_dsl(lab_dsl, load_schema("lab", ROOT))
    except DslValidationError as exc:
        raise LabTemplateImportPreviewError(
            "SCHEMA_VALIDATION_ERROR",
            "Lab DSL Schema 校验失败",
            exc.errors,
        ) from exc

    draft = _lab_template_draft_from_dsl(lab_dsl, source_task_id=task.id, source_path=artifact.path)
    preview = {
        "component": "LabTemplateImportPreview",
        "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW",
        "sourceTaskId": task.id,
        "sourceTaskStatus": task.status.value,
        "sourceArtifactId": artifact.id,
        "sourceArtifactKind": artifact.kind.value,
        "sourceDslPath": artifact.path,
        "reviewer": reviewer,
        "schemaValidated": True,
        "agentEntity": "lab_template",
        "labTemplateDraft": draft,
        "importPlan": {
            "strategy": "manual_platform_import_after_review",
            "writeTarget": "local_preview_only",
            "databaseWritePlanned": False,
            "apiCallPlanned": False,
            "realAgentImport": False,
            "manualReviewRequired": True,
            "nextRequiredAction": "review_lab_template_draft_before_platform_import",
        },
        "safety": {
            "realLlmCalled": False,
            "newLlmRequestSent": False,
            "secretsRead": False,
            "networkAccess": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
        "traceId": trace_id,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path=str(output_path),
        title="Lab Template Import Preview",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=artifact.path,
        metadata={
            "component": "LabTemplateImportPreview",
            "agentEntity": "lab_template",
            "sourceArtifactId": artifact.id,
            "schemaValidated": True,
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublishAllowed": False,
        },
        mode="LOCAL_PLATFORM_IMPORT_PREVIEW",
    )
    store.save_artifact(preview_artifact)
    operation_event = create_operation_audit_event(
        action=OperationAction.LAB_TEMPLATE_IMPORT_PREVIEW,
        resource_type=OperationResourceType.LAB,
        resource_id=draft["id"],
        actor=reviewer,
        trace_id=trace_id,
        before_state=task.status.value,
        after_state="IMPORT_PREVIEW_CREATED",
        detail={
            "component": "LabTemplateImportPreview",
            "taskId": task.id,
            "sourceArtifactId": artifact.id,
            "previewArtifactId": preview_artifact.id,
            "outputPath": str(output_path),
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublishAllowed": False,
        },
    )
    store.save_operation_audit_event(operation_event)
    return {
        "labTemplateImportPreview": preview,
        "artifact": preview_artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }


def _create_platform_import_preview(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
    artifact_kind: ArtifactKind,
    schema_kind: str,
    label: str,
    component: str,
    agent_entity: str,
    draft_key: str,
    draft_builder: Any,
    action: OperationAction,
    resource_type: OperationResourceType,
    artifact_title: str,
    next_required_action: str,
) -> dict[str, Any]:
    task, artifact, dsl = _validated_artifact_dsl(
        store,
        task_id=task_id,
        reviewer=reviewer,
        artifact_kind=artifact_kind,
        schema_kind=schema_kind,
        label=label,
    )
    reviewer = str(reviewer).strip()
    draft = draft_builder(dsl, source_task_id=task.id, source_path=artifact.path)
    controlled_evidence_next_action = (
        _controlled_grading_evidence_next_action(task_id=task.id, source_path=artifact.path)
        if component == "GradingRuleImportPreview"
        else None
    )
    preview = {
        "component": component,
        "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW",
        "sourceTaskId": task.id,
        "sourceTaskStatus": task.status.value,
        "sourceArtifactId": artifact.id,
        "sourceArtifactKind": artifact.kind.value,
        "sourceDslPath": artifact.path,
        "reviewer": reviewer,
        "schemaValidated": True,
        "agentEntity": agent_entity,
        draft_key: draft,
        "importPlan": {
            "strategy": "manual_platform_import_after_review",
            "writeTarget": "local_preview_only",
            "databaseWritePlanned": False,
            "apiCallPlanned": False,
            "realAgentImport": False,
            "manualReviewRequired": True,
            "nextRequiredAction": next_required_action,
            "evidenceAutoRequiredBeforeFinalImportReview": controlled_evidence_next_action is not None,
        },
        "safety": {
            "realLlmCalled": False,
            "newLlmRequestSent": False,
            "secretsRead": False,
            "networkAccess": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "answerVisibleToCandidate": False,
        },
        "traceId": trace_id,
    }
    if controlled_evidence_next_action is not None:
        preview["controlledEvidenceNextAction"] = controlled_evidence_next_action
        preview["importPlan"]["controlledEvidenceNextAction"] = controlled_evidence_next_action
        draft["controlledEvidenceNextAction"] = controlled_evidence_next_action
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path=str(output_path),
        title=artifact_title,
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=artifact.path,
        metadata={
            "component": component,
            "agentEntity": agent_entity,
            "sourceArtifactId": artifact.id,
            "schemaValidated": True,
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublishAllowed": False,
        },
        mode="LOCAL_PLATFORM_IMPORT_PREVIEW",
    )
    store.save_artifact(preview_artifact)
    operation_event = create_operation_audit_event(
        action=action,
        resource_type=resource_type,
        resource_id=draft["id"],
        actor=reviewer,
        trace_id=trace_id,
        before_state=task.status.value,
        after_state="IMPORT_PREVIEW_CREATED",
        detail={
            "component": component,
            "taskId": task.id,
            "sourceArtifactId": artifact.id,
            "previewArtifactId": preview_artifact.id,
            "outputPath": str(output_path),
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublishAllowed": False,
        },
    )
    store.save_operation_audit_event(operation_event)
    return {
        draft_key.replace("Draft", "ImportPreview"): preview,
        "artifact": preview_artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }


def create_exam_question_import_preview(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    return _create_platform_import_preview(
        store,
        task_id=task_id,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        artifact_kind=ArtifactKind.EXAM_DSL,
        schema_kind="exam",
        label="Exam 试题",
        component="ExamQuestionImportPreview",
        agent_entity="exam_question",
        draft_key="examQuestionDraft",
        draft_builder=_exam_question_draft_from_dsl,
        action=OperationAction.EXAM_QUESTION_IMPORT_PREVIEW,
        resource_type=OperationResourceType.EXAM,
        artifact_title="Exam Question Import Preview",
        next_required_action="review_exam_question_draft_before_platform_import",
    )


def create_grading_rule_import_preview(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    return _create_platform_import_preview(
        store,
        task_id=task_id,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        artifact_kind=ArtifactKind.GRADING_DSL,
        schema_kind="grading",
        label="Grading 评分规则",
        component="GradingRuleImportPreview",
        agent_entity="grading_rule",
        draft_key="gradingRuleDraft",
        draft_builder=_grading_rule_draft_from_dsl,
        action=OperationAction.GRADING_RULE_IMPORT_PREVIEW,
        resource_type=OperationResourceType.GRADING_REPORT,
        artifact_title="Grading Rule Import Preview",
        next_required_action="review_grading_rule_draft_before_platform_import",
    )


def create_ppt_deck_import_preview(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    return _create_platform_import_preview(
        store,
        task_id=task_id,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        artifact_kind=ArtifactKind.PPT_DSL,
        schema_kind="ppt",
        label="PPT 课件",
        component="PptDeckImportPreview",
        agent_entity="ppt_deck",
        draft_key="pptDeckDraft",
        draft_builder=_ppt_deck_draft_from_dsl,
        action=OperationAction.PPT_DECK_IMPORT_PREVIEW,
        resource_type=OperationResourceType.PPT,
        artifact_title="PPT Deck Import Preview",
        next_required_action="review_ppt_deck_draft_and_pptx_artifact_before_platform_import",
    )


def _create_agent_entity_mock_import(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
    component: str,
    agent_entity: str,
    entity_type: AgentEntityType,
    draft_key: str,
    action: OperationAction,
    report_component: str,
    report_title: str,
) -> dict[str, Any]:
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise AgentEntityMockImportError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    task = store.get(task_id)
    if task is None:
        raise AgentEntityMockImportError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )
    if task.status != TaskStatus.APPROVED:
        raise AgentEntityMockImportError(
            "STATE_TRANSITION_ERROR",
            "平台实体 Mock 入库要求任务已审核通过",
            [{"field": "status", "reason": "expected APPROVED"}],
        )
    preview_artifact = _latest_platform_import_preview_artifact(
        store,
        task_id=task.id,
        component=component,
        agent_entity=agent_entity,
    )
    if preview_artifact is None:
        raise AgentEntityMockImportError(
            "VALIDATION_ERROR",
            "平台实体 Mock 入库要求先生成导入预览",
            [{"field": "platformImportPreview", "reason": f"missing {component}"}],
        )
    preview = _load_preview_payload(preview_artifact)
    draft = preview.get(draft_key) if isinstance(preview.get(draft_key), dict) else None
    if draft is None:
        raise AgentEntityMockImportError(
            "VALIDATION_ERROR",
            "平台导入预览缺少实体草稿",
            [{"field": draft_key, "reason": "expected object"}],
        )
    safety = preview.get("safety", {}) if isinstance(preview.get("safety"), dict) else {}
    if safety.get("databaseWritten") is not False or safety.get("realAgentImport") is not False:
        raise AgentEntityMockImportError(
            "VALIDATION_ERROR",
            "平台导入预览安全标记不允许 Mock 入库",
            [{"field": "safety", "reason": "expected databaseWritten=false and realAgentImport=false"}],
        )

    entity = create_agent_entity_record(
        entity_type=entity_type,
        title=str(draft.get("title") or report_title),
        payload=draft,
        source_task_id=task.id,
        source_preview_artifact_id=preview_artifact.id,
        source_preview_path=preview_artifact.path,
        reviewer=reviewer,
        trace_id=trace_id,
        source_dsl_path=preview.get("sourceDslPath"),
        source_artifact_id=preview.get("sourceArtifactId"),
        source_artifact_kind=preview.get("sourceArtifactKind"),
    )
    store.save_agent_entity(entity)

    operation_event = create_operation_audit_event(
        action=action,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state="IMPORT_PREVIEW_CREATED",
        after_state=entity.status.value,
        detail={
            "component": report_component,
            "taskId": task.id,
            "agentEntityId": entity.id,
            "agentEntity": agent_entity,
            "previewArtifactId": preview_artifact.id,
            "sourceArtifactId": entity.sourceArtifactId,
            "outputPath": str(output_path),
            "mockStoreWritten": True,
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublishAllowed": False,
        },
    )
    store.save_operation_audit_event(operation_event)

    report = {
        "component": report_component,
        "mode": "LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
        "taskId": task.id,
        "taskStatus": task.status.value,
        "reviewer": reviewer,
        "agentEntity": agent_entity,
        "agentEntityRecord": entity.to_dict(),
        "sourcePreview": {
            "component": component,
            "artifactId": preview_artifact.id,
            "artifactPath": preview_artifact.path,
            "sourceDslPath": preview.get("sourceDslPath"),
            "schemaValidated": bool(preview.get("schemaValidated")),
        },
        "safety": {
            "newLlmRequestSent": False,
            "secretsRead": False,
            "networkAccess": False,
            "mockStoreWritten": True,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
        "traceId": trace_id,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path=str(output_path),
        title=report_title,
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=preview_artifact.path,
        metadata={
            "component": report_component,
            "agentEntity": agent_entity,
            "agentEntityId": entity.id,
            "previewArtifactId": preview_artifact.id,
            "mockStoreWritten": True,
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublishAllowed": False,
        },
        mode="LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
    )
    store.save_artifact(artifact)
    report["artifactId"] = artifact.id
    return {
        "agentEntityMockImport": report,
        "agentEntityRecord": entity.to_dict(),
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }


def create_lab_template_mock_import(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    return _create_agent_entity_mock_import(
        store,
        task_id=task_id,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        component="LabTemplateImportPreview",
        agent_entity="lab_template",
        entity_type=AgentEntityType.LAB_TEMPLATE,
        draft_key="labTemplateDraft",
        action=OperationAction.LAB_TEMPLATE_MOCK_IMPORT,
        report_component="LabTemplateMockImport",
        report_title="Lab Template Mock Import",
    )


def create_exam_question_mock_import(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    return _create_agent_entity_mock_import(
        store,
        task_id=task_id,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        component="ExamQuestionImportPreview",
        agent_entity="exam_question",
        entity_type=AgentEntityType.EXAM_QUESTION,
        draft_key="examQuestionDraft",
        action=OperationAction.EXAM_QUESTION_MOCK_IMPORT,
        report_component="ExamQuestionMockImport",
        report_title="Exam Question Mock Import",
    )


def create_grading_rule_mock_import(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    return _create_agent_entity_mock_import(
        store,
        task_id=task_id,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        component="GradingRuleImportPreview",
        agent_entity="grading_rule",
        entity_type=AgentEntityType.GRADING_RULE,
        draft_key="gradingRuleDraft",
        action=OperationAction.GRADING_RULE_MOCK_IMPORT,
        report_component="GradingRuleMockImport",
        report_title="Grading Rule Mock Import",
    )


def create_ppt_deck_mock_import(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
) -> dict[str, Any]:
    return _create_agent_entity_mock_import(
        store,
        task_id=task_id,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        component="PptDeckImportPreview",
        agent_entity="ppt_deck",
        entity_type=AgentEntityType.PPT_DECK,
        draft_key="pptDeckDraft",
        action=OperationAction.PPT_DECK_MOCK_IMPORT,
        report_component="PptDeckMockImport",
        report_title="PPT Deck Mock Import",
    )
