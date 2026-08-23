"""Deterministic local export for an approved Lab + Exam/Grading package."""

from __future__ import annotations

import io
import json
import os
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from ai_workflows.exam_candidate_preview import (
    ANSWER_FIELD_NAMES,
    ExamCandidatePreviewError,
    build_candidate_safe_exam_preview,
)

from .ai_task import TaskStatus
from .artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationResourceType, create_operation_audit_event
from .dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from .review_batch import build_teaching_package_review_summary
from .store import JsonTaskStore
from .workspace import resolve_cli_path, workspace_root


ROOT = Path(__file__).resolve().parents[1]
EXPORT_MODE = "LOCAL_TEACHING_PACKAGE_EXPORT"
ENTRY_NAMES = (
    "manifest.json",
    "lab.json",
    "exam.json",
    "grading.json",
    "exam-candidate-preview.json",
    "review-summary.json",
)
SOURCE_SPECS = {
    "lab": (ArtifactKind.LAB_DSL, "lab"),
    "exam": (ArtifactKind.EXAM_DSL, "exam"),
    "grading": (ArtifactKind.GRADING_DSL, "grading"),
}
SOURCE_TASK_TYPES = {
    "lab": "LAB_GENERATION",
    "exam": "EXAM_GENERATION",
    "grading": "GRADING_GENERATION",
}
PAYLOAD_FILE_SPECS = (
    ("lab.json", "lab_dsl", "teacher"),
    ("exam.json", "teacher_exam_dsl", "teacher"),
    ("grading.json", "grading_rules", "teacher_internal"),
    ("exam-candidate-preview.json", "candidate_exam_preview", "candidate"),
    ("review-summary.json", "review_evidence", "teacher"),
)
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FORBIDDEN_CANDIDATE_KEYS = frozenset(ANSWER_FIELD_NAMES) | {"gradingRef"}


class TeachingPackageExportError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


@dataclass(frozen=True)
class TeachingPackageExportResult:
    workflow_run_id: str
    output_path: Path
    sha256: str
    size_bytes: int
    artifact_id: str
    audit_event_id: str
    idempotent: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": "TeachingPackageExportResult",
            "workflowRunId": self.workflow_run_id,
            "artifactProfile": "teaching-core",
            "status": ArtifactStatus.COMPLETED.value,
            "outputPath": str(self.output_path),
            "fileName": self.output_path.name,
            "sha256": self.sha256,
            "sizeBytes": self.size_bytes,
            "fileTotal": len(ENTRY_NAMES),
            "includedFileTotal": len(ENTRY_NAMES),
            "entryNames": list(ENTRY_NAMES),
            "artifactId": self.artifact_id,
            "operationAuditEventId": self.audit_event_id,
            "idempotent": self.idempotent,
            "integrity": {
                "algorithm": "SHA-256",
                "sha256": self.sha256,
                "sizeBytes": self.size_bytes,
            },
            "candidateSafety": {
                "candidateSafe": True,
                "answerVisibleToCandidate": False,
                "gradingRefVisibleToCandidate": False,
            },
            "safety": {
                "localOnly": True,
                "candidatePreviewSafe": True,
                "networkAccess": False,
                "sandboxExecuted": False,
                "taskStatusChanged": False,
                "autoPublishAllowed": False,
                "realPublishAllowed": False,
                "realPublish": False,
                "contestantCodeExecuted": False,
            },
        }


def export_teaching_package(
    store: JsonTaskStore,
    *,
    workflow_run_id: str,
    reviewer: str,
    output_path: Path | str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    workflow_run_id = str(workflow_run_id or "").strip()
    reviewer = str(reviewer or "").strip()
    input_errors: list[dict[str, str]] = []
    if not workflow_run_id:
        input_errors.append({"field": "workflowRunId", "reason": "required"})
    if not reviewer:
        input_errors.append({"field": "reviewer", "reason": "required"})
    if output_path is not None and not str(output_path).strip():
        input_errors.append({"field": "output", "reason": "must not be empty"})
    if input_errors:
        raise TeachingPackageExportError("VALIDATION_ERROR", "教学包导出参数错误", input_errors)

    summary = build_teaching_package_review_summary(store, workflow_run_id)
    source_artifacts, source_tasks = _validate_export_gate(store, workflow_run_id, summary)
    documents = _load_and_validate_documents(source_artifacts)
    contract_summary = _validate_cross_artifact_contract(documents)
    candidate_preview = _build_candidate_preview(documents["exam"])
    if summary.get("exportReady") is not True:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_NOT_READY",
            "教学包聚合审核摘要尚未满足导出条件",
            [{"field": "exportReady", "reason": "must be true"}],
        )
    review_summary = _build_export_review_summary(
        workflow_run_id=workflow_run_id,
        summary=summary,
        source_artifacts=source_artifacts,
        source_tasks=source_tasks,
        contract_summary=contract_summary,
        candidate_preview=candidate_preview,
    )
    package_bytes = _build_package_bytes(
        workflow_run_id=workflow_run_id,
        documents=documents,
        candidate_preview=candidate_preview,
        review_summary=review_summary,
    )
    package_sha256 = sha256(package_bytes).hexdigest()
    destination = _resolve_output_path(workflow_run_id, output_path)

    matching_artifact = _find_matching_artifact(
        store,
        workflow_run_id=workflow_run_id,
        output_path=destination,
        package_sha256=package_sha256,
    )
    idempotent = _ensure_output(destination, package_bytes, package_sha256)
    effective_trace_id = str(trace_id or f"trace_{uuid4().hex[:12]}")
    artifact = matching_artifact or _save_package_artifact(
        store,
        workflow_run_id=workflow_run_id,
        output_path=destination,
        package_sha256=package_sha256,
        size_bytes=len(package_bytes),
        trace_id=effective_trace_id,
        contract_summary=contract_summary,
    )
    audit_event = _save_export_audit(
        store,
        artifact=artifact,
        workflow_run_id=workflow_run_id,
        reviewer=reviewer,
        output_path=destination,
        package_sha256=package_sha256,
        size_bytes=len(package_bytes),
        trace_id=effective_trace_id,
    )

    return TeachingPackageExportResult(
        workflow_run_id=workflow_run_id,
        output_path=destination,
        sha256=package_sha256,
        size_bytes=len(package_bytes),
        artifact_id=artifact.id,
        audit_event_id=audit_event.id,
        idempotent=idempotent,
    ).to_dict()


def _validate_export_gate(
    store: JsonTaskStore,
    workflow_run_id: str,
    summary: dict[str, Any] | None,
) -> tuple[dict[str, ArtifactRecord], dict[str, Any]]:
    if summary is None:
        raise TeachingPackageExportError(
            "NOT_FOUND",
            "教学包工作流不存在",
            [{"field": "workflowRunId", "reason": "workflow run not found"}],
        )
    if summary.get("available") is not True or summary.get("artifactProfile") != "teaching-core":
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_NOT_EXPORTABLE",
            "该工作流不是可导出的教学包批次",
            [{"field": "workflowRunId", "reason": "expected teaching-core workflow run"}],
        )

    artifact_summaries = summary.get("artifacts")
    if not isinstance(artifact_summaries, dict) or set(artifact_summaries) != set(SOURCE_SPECS):
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_NOT_READY",
            "教学包尚未满足导出条件",
            [{"field": "artifacts", "reason": "exactly Lab, Exam, and Grading artifacts are required"}],
        )

    source_artifacts: dict[str, ArtifactRecord] = {}
    source_tasks: dict[str, Any] = {}
    task_ids: set[str] = set()
    readiness_errors: list[dict[str, str]] = []
    workflow_artifacts = store.list_artifacts(workflow_run_id=workflow_run_id)
    for kind, (expected_artifact_kind, _) in SOURCE_SPECS.items():
        matches = [artifact for artifact in workflow_artifacts if artifact.kind == expected_artifact_kind]
        if len(matches) != 1:
            readiness_errors.append(
                {
                    "field": f"artifacts.{kind}",
                    "reason": "exactly one source artifact is required",
                }
            )
    for kind, (expected_artifact_kind, _) in SOURCE_SPECS.items():
        item = artifact_summaries[kind]
        artifact_id = item.get("artifactId") if isinstance(item, dict) else None
        artifact = store.get_artifact(str(artifact_id)) if artifact_id else None
        if (
            artifact is None
            or artifact.kind != expected_artifact_kind
            or artifact.workflowRunId != workflow_run_id
        ):
            readiness_errors.append({"field": f"artifacts.{kind}", "reason": "source artifact record is missing"})
            continue
        task = store.get(str(artifact.taskId or "")) if artifact.taskId else None
        if task is None:
            readiness_errors.append({"field": f"artifacts.{kind}.taskId", "reason": "review task is missing"})
            continue
        source_artifacts[kind] = artifact
        source_tasks[kind] = task
        task_ids.add(task.id)
        if task.taskType != SOURCE_TASK_TYPES[kind]:
            readiness_errors.append(
                {
                    "field": f"artifacts.{kind}.taskType",
                    "reason": f"must be {SOURCE_TASK_TYPES[kind]}",
                }
            )
        if task.status != TaskStatus.APPROVED:
            readiness_errors.append({"field": f"artifacts.{kind}.status", "reason": "must be APPROVED"})
        if not task.reviewer:
            readiness_errors.append({"field": f"artifacts.{kind}.reviewer", "reason": "approved task must retain reviewer"})
        if not task.reviewedAt:
            readiness_errors.append({"field": f"artifacts.{kind}.reviewedAt", "reason": "approved task must retain reviewedAt"})

    if len(task_ids) != len(SOURCE_SPECS):
        readiness_errors.append({"field": "reviewTasks", "reason": "exactly three distinct review tasks are required"})
    if readiness_errors:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_NOT_READY",
            "教学包尚未满足导出条件",
            readiness_errors,
        )
    return source_artifacts, source_tasks


def _load_and_validate_documents(source_artifacts: dict[str, ArtifactRecord]) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for kind, (_, schema_kind) in SOURCE_SPECS.items():
        artifact = source_artifacts[kind]
        path = resolve_cli_path(artifact.path, root=ROOT)
        if not path.exists() or not path.is_file():
            raise TeachingPackageExportError(
                "TEACHING_PACKAGE_ARTIFACT_NOT_FOUND",
                "教学包源产物文件不存在",
                [{"field": f"artifacts.{kind}", "reason": "local artifact file not found"}],
            )
        try:
            document = load_yaml(path)
            validate_dsl(document, load_schema(schema_kind, ROOT))
        except DslValidationError as exc:
            raise TeachingPackageExportError(
                "SCHEMA_VALIDATION_ERROR",
                f"{kind.title()} DSL Schema 校验失败",
                _safe_schema_errors(kind, exc.errors),
            ) from exc
        except Exception as exc:
            raise TeachingPackageExportError(
                "SCHEMA_VALIDATION_ERROR",
                f"{kind.title()} DSL 无法解析",
                [{"field": kind, "reason": "document parse failed"}],
            ) from exc
        if not isinstance(document, dict):
            raise TeachingPackageExportError(
                "SCHEMA_VALIDATION_ERROR",
                f"{kind.title()} DSL Schema 校验失败",
                [{"field": kind, "reason": "document root must be an object"}],
            )
        documents[kind] = document
    return documents


def _safe_schema_errors(kind: str, errors: list[dict[str, str]]) -> list[dict[str, str]]:
    safe: list[dict[str, str]] = []
    for error in errors[:20]:
        source_field = str(error.get("field") or "$")
        field = f"{kind}{source_field[1:]}" if source_field.startswith("$") else f"{kind}.{source_field}"
        safe.append({"field": field, "reason": "schema validation failed"})
    return safe or [{"field": kind, "reason": "schema validation failed"}]


def _validate_cross_artifact_contract(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lab = documents["lab"]
    exam = documents["exam"]
    grading = documents["grading"]
    lab_metadata = _mapping(lab.get("metadata"))
    exam_metadata = _mapping(exam.get("metadata"))
    grading_metadata = _mapping(grading.get("metadata"))
    lab_spec = _mapping(lab.get("spec"))
    exam_spec = _mapping(exam.get("spec"))
    grading_spec = _mapping(grading.get("spec"))
    questions = _object_list(exam_spec.get("questions"))
    checks = _object_list(grading_spec.get("checks"))
    plans = _object_list(grading_spec.get("assessmentPlan"))
    errors: list[dict[str, str]] = []

    if _mapping(lab_spec.get("grading")).get("ref") != grading_metadata.get("id"):
        errors.append({"field": "lab.spec.grading.ref", "reason": "must reference grading.metadata.id"})
    if exam_metadata.get("sourceLabId") != lab_metadata.get("id"):
        errors.append({"field": "exam.metadata.sourceLabId", "reason": "must reference lab.metadata.id"})
    if grading_metadata.get("sourceExamId") != exam_metadata.get("id"):
        errors.append({"field": "grading.metadata.sourceExamId", "reason": "must reference exam.metadata.id"})

    checks_by_id = _unique_items_by_key(checks, "id", "grading.spec.checks", errors)
    plans_by_id = _unique_items_by_key(plans, "checkId", "grading.spec.assessmentPlan", errors)
    question_refs: set[str] = set()
    for index, question in enumerate(questions):
        reference = question.get("gradingRef")
        if not isinstance(reference, str) or not reference:
            errors.append({"field": f"exam.spec.questions[{index}].gradingRef", "reason": "must reference a grading check"})
            continue
        if reference in question_refs:
            errors.append({"field": f"exam.spec.questions[{index}].gradingRef", "reason": "must be unique across questions"})
        question_refs.add(reference)
        check = checks_by_id.get(reference)
        plan = plans_by_id.get(reference)
        if check is None:
            errors.append({"field": f"exam.spec.questions[{index}].gradingRef", "reason": "referenced grading check is missing"})
            continue
        if plan is None:
            errors.append({"field": f"grading.spec.assessmentPlan[{reference}]", "reason": "assessment plan entry is missing"})
            continue
        question_score = _score(question.get("score"))
        check_score = _score(check.get("score"))
        plan_score = _score(plan.get("score"))
        if question_score is None or check_score is None or plan_score is None or not (
            question_score == check_score == plan_score
        ):
            errors.append({"field": f"exam.spec.questions[{index}].score", "reason": "must align with grading check and assessment plan scores"})

    check_ids = set(checks_by_id)
    plan_ids = set(plans_by_id)
    if check_ids != plan_ids:
        errors.append({"field": "grading.spec.assessmentPlan", "reason": "check IDs must align exactly with grading checks"})
    if not question_refs.issubset(check_ids):
        errors.append({"field": "exam.spec.questions", "reason": "every gradingRef must be covered by grading checks"})

    exam_total = _score(exam_spec.get("totalScore"))
    grading_total = _score(grading_spec.get("totalScore"))
    question_total = _score_sum(questions)
    check_total = _score_sum(checks)
    plan_total = _score_sum(plans)
    if exam_total is None or question_total is None or exam_total != question_total:
        errors.append({"field": "exam.spec.totalScore", "reason": "must equal the sum of question scores"})
    if grading_total is None or check_total is None or grading_total != check_total:
        errors.append({"field": "grading.spec.totalScore", "reason": "must equal the sum of grading check scores"})
    if grading_total is None or plan_total is None or grading_total != plan_total:
        errors.append({"field": "grading.spec.assessmentPlan", "reason": "assessment plan scores must equal grading totalScore"})
    if exam_total is None or grading_total is None or exam_total != grading_total:
        errors.append({"field": "grading.spec.totalScore", "reason": "must equal exam totalScore"})

    if errors:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_CONTRACT_VALIDATION_ERROR",
            "教学包跨产物契约校验失败",
            _deduplicate_errors(errors),
        )
    return {
        "crossReferencesValid": True,
        "gradingRefCoverageComplete": True,
        "assessmentPlanAlignedWithChecks": True,
        "scoreAlignmentValid": True,
        "questionTotal": len(questions),
        "gradingCheckTotal": len(checks),
        "assessmentPlanTotal": len(plans),
    }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _object_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _unique_items_by_key(
    items: list[dict[str, Any]],
    key: str,
    field: str,
    errors: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        identifier = item.get(key)
        if not isinstance(identifier, str) or not identifier:
            errors.append({"field": f"{field}[{index}].{key}", "reason": "identifier is required"})
            continue
        if identifier in result:
            errors.append({"field": f"{field}[{index}].{key}", "reason": "identifier must be unique"})
            continue
        result[identifier] = item
    return result


def _score(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _score_sum(items: list[dict[str, Any]]) -> Decimal | None:
    values = [_score(item.get("score")) for item in items]
    if any(value is None for value in values):
        return None
    return sum((value for value in values if value is not None), Decimal(0))


def _deduplicate_errors(errors: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for error in errors:
        key = (error["field"], error["reason"])
        if key not in seen:
            seen.add(key)
            result.append(error)
    return result


def _build_candidate_preview(exam_dsl: dict[str, Any]) -> dict[str, Any]:
    try:
        preview = build_candidate_safe_exam_preview(exam_dsl)
    except ExamCandidatePreviewError as exc:
        raise TeachingPackageExportError(exc.code, exc.message, exc.errors) from exc
    forbidden_fields = _find_forbidden_candidate_fields(preview)
    grading_ref_leaks = _find_grading_ref_value_leaks(preview, exam_dsl)
    redaction = _mapping(preview.get("redaction"))
    if (
        forbidden_fields
        or grading_ref_leaks
        or preview.get("answerVisibleToCandidate") is not False
        or redaction.get("answerLeakDetected") is not False
        or redaction.get("candidateSafe") is not True
    ):
        errors = forbidden_fields or grading_ref_leaks or [
            {"field": "examCandidatePreview", "reason": "candidate preview is not safe"}
        ]
        raise TeachingPackageExportError(
            "CANDIDATE_PREVIEW_ANSWER_LEAK_DETECTED",
            "候选人预览检测到标准答案或内部评分引用泄露",
            errors,
        )
    return preview


def _find_forbidden_candidate_fields(value: Any, path: str = "$") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_CANDIDATE_KEYS:
                errors.append({"field": child_path, "reason": "candidate preview contains an internal field"})
            errors.extend(_find_forbidden_candidate_fields(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_find_forbidden_candidate_fields(item, f"{path}[{index}]"))
    return errors


def _find_grading_ref_value_leaks(
    preview: dict[str, Any],
    exam_dsl: dict[str, Any],
) -> list[dict[str, str]]:
    questions = _object_list(_mapping(exam_dsl.get("spec")).get("questions"))
    references = {
        str(question.get("gradingRef") or "").strip().casefold()
        for question in questions
        if str(question.get("gradingRef") or "").strip()
    }
    if not references:
        return []
    errors: list[dict[str, str]] = []
    for field, value in _iter_string_values(preview):
        normalized = value.casefold()
        for reference in references:
            leaked = normalized.strip() == reference if len(reference) <= 4 else reference in normalized
            if leaked:
                errors.append(
                    {
                        "field": field,
                        "reason": "candidate preview contains an internal grading reference value",
                    }
                )
                break
    return errors


def _iter_string_values(value: Any, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_string_values(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_string_values(item, f"{path}[{index}]")


def _build_export_review_summary(
    *,
    workflow_run_id: str,
    summary: dict[str, Any],
    source_artifacts: dict[str, ArtifactRecord],
    source_tasks: dict[str, Any],
    contract_summary: dict[str, Any],
    candidate_preview: dict[str, Any],
) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    for kind in SOURCE_SPECS:
        artifact = source_artifacts[kind]
        task = source_tasks[kind]
        artifacts[kind] = {
            "kind": kind,
            "artifactKind": artifact.kind.value,
            "artifactId": artifact.id,
            "taskId": task.id,
            "taskType": task.taskType,
            "status": task.status.value,
            "reviewer": task.reviewer,
            "reviewedAt": task.reviewedAt,
            "schemaValidated": True,
        }
    return {
        "component": "TeachingPackageExportReviewSummary",
        "workflowRunId": workflow_run_id,
        "workflowId": summary.get("workflowId"),
        "artifactProfile": "teaching-core",
        "status": "APPROVED",
        "artifacts": artifacts,
        "validation": {
            "schemaValidatedTotal": len(SOURCE_SPECS),
            "allSchemaValidated": True,
            **contract_summary,
        },
        "reviewProgress": {
            "total": len(SOURCE_SPECS),
            "approved": len(SOURCE_SPECS),
            "waitingReview": 0,
            "rejected": 0,
            "missing": 0,
        },
        "candidateSafeExamPreview": {
            "candidateSafe": True,
            "answersRemovedFromSafePreview": candidate_preview.get("answersRemoved") is True,
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "answerLeakDetected": False,
        },
        "exportReady": True,
        "safety": {
            "humanReviewRequired": True,
            "allArtifactsHumanApproved": True,
            "taskStatusChanged": False,
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_ERROR",
            "教学包内容无法序列化",
            [{"field": "package", "reason": "canonical JSON serialization failed"}],
        ) from exc
    return (payload + "\n").encode("utf-8")


def _build_package_bytes(
    *,
    workflow_run_id: str,
    documents: dict[str, dict[str, Any]],
    candidate_preview: dict[str, Any],
    review_summary: dict[str, Any],
) -> bytes:
    payloads = {
        "lab.json": _canonical_json_bytes(documents["lab"]),
        "exam.json": _canonical_json_bytes(documents["exam"]),
        "grading.json": _canonical_json_bytes(documents["grading"]),
        "exam-candidate-preview.json": _canonical_json_bytes(candidate_preview),
        "review-summary.json": _canonical_json_bytes(review_summary),
    }
    manifest_files = [
        {
            "name": name,
            "role": role,
            "audience": audience,
            "sha256": sha256(payloads[name]).hexdigest(),
            "sizeBytes": len(payloads[name]),
        }
        for name, role, audience in PAYLOAD_FILE_SPECS
    ]
    manifest = {
        "version": "1.0",
        "kind": "TeachingPackageManifest",
        "workflowRunId": workflow_run_id,
        "artifactProfile": "teaching-core",
        "status": "APPROVED",
        "entryNames": list(ENTRY_NAMES),
        "entryCount": len(ENTRY_NAMES),
        "payloadFileCount": len(manifest_files),
        "files": manifest_files,
        "deterministic": {
            "canonicalJson": True,
            "fixedEntryOrder": True,
            "fixedZipMetadata": True,
        },
        "safety": {
            "candidatePreviewIncluded": True,
            "candidatePreviewSafe": True,
            "teacherExamIncludesAnswers": True,
            "gradingRulesTeacherInternal": True,
            "networkAccess": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }
    entries = {"manifest.json": _canonical_json_bytes(manifest), **payloads}
    buffer = io.BytesIO()
    try:
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for name in ENTRY_NAMES:
                info = ZipInfo(name, date_time=ZIP_TIMESTAMP)
                info.compress_type = ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.extra = b""
                info.comment = b""
                archive.writestr(info, entries[name], compress_type=ZIP_DEFLATED, compresslevel=9)
    except Exception as exc:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_ERROR",
            "教学包 ZIP 构建失败",
            [{"field": "package", "reason": "ZIP construction failed"}],
        ) from exc
    return buffer.getvalue()


def _resolve_output_path(workflow_run_id: str, output_path: Path | str | None) -> Path:
    if output_path is None:
        candidate = workspace_root(root=ROOT) / "examples" / "output" / "teaching-packages" / f"{workflow_run_id}.zip"
    else:
        candidate = Path(output_path).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
    if candidate.suffix.lower() != ".zip":
        raise TeachingPackageExportError(
            "VALIDATION_ERROR",
            "教学包输出路径必须使用 .zip 扩展名",
            [{"field": "output", "reason": "must use .zip extension"}],
        )
    return Path(os.path.abspath(candidate))


def _path_key(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(Path(path).expanduser()))


def _find_matching_artifact(
    store: JsonTaskStore,
    *,
    workflow_run_id: str,
    output_path: Path,
    package_sha256: str,
) -> ArtifactRecord | None:
    path_matches = [
        artifact
        for artifact in store.list_artifacts(
            kind=ArtifactKind.TEACHING_PACKAGE_ZIP.value,
            workflow_run_id=workflow_run_id,
        )
        if _path_key(artifact.path) == _path_key(output_path)
    ]
    for artifact in path_matches:
        if artifact.metadata.get("packageSha256") == package_sha256:
            return artifact
    if path_matches:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_CONFLICT",
            "目标路径已有不匹配的教学包记录",
            [{"field": "output", "reason": "stored artifact integrity does not match expected package"}],
        )
    return None


def _ensure_output(output_path: Path, package_bytes: bytes, package_sha256: str) -> bool:
    existing = _existing_output_state(output_path, package_sha256)
    if existing is not None:
        return existing
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_ERROR",
            "无法创建教学包输出目录",
            [{"field": "output", "reason": "output directory creation failed"}],
        ) from exc

    temp_path: Path | None = None
    file_descriptor: int | None = None
    try:
        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
        )
        temp_path = Path(temp_name)
        with os.fdopen(file_descriptor, "wb") as file:
            file_descriptor = None
            file.write(package_bytes)
            file.flush()
            os.fsync(file.fileno())
        raced = _existing_output_state(output_path, package_sha256)
        if raced is not None:
            return raced
        os.replace(temp_path, output_path)
        temp_path = None
        return False
    except TeachingPackageExportError:
        raise
    except OSError as exc:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_ERROR",
            "教学包写入失败",
            [{"field": "output", "reason": "atomic ZIP write failed"}],
        ) from exc
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _existing_output_state(output_path: Path, package_sha256: str) -> bool | None:
    if output_path.is_symlink():
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_CONFLICT",
            "目标路径不是可复用的普通文件",
            [{"field": "output", "reason": "symbolic links are not allowed"}],
        )
    if not output_path.exists():
        return None
    if not output_path.is_file():
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_CONFLICT",
            "目标路径不是可复用的普通文件",
            [{"field": "output", "reason": "existing output is not a regular file"}],
        )
    try:
        digest = _file_sha256(output_path)
    except OSError as exc:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_ERROR",
            "无法校验已有教学包",
            [{"field": "output", "reason": "existing output could not be read"}],
        ) from exc
    if digest != package_sha256:
        raise TeachingPackageExportError(
            "TEACHING_PACKAGE_EXPORT_CONFLICT",
            "目标路径已存在不同内容",
            [{"field": "output", "reason": "existing file does not match expected package"}],
        )
    return True


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_package_artifact(
    store: JsonTaskStore,
    *,
    workflow_run_id: str,
    output_path: Path,
    package_sha256: str,
    size_bytes: int,
    trace_id: str,
    contract_summary: dict[str, Any],
) -> ArtifactRecord:
    artifact = create_artifact_record(
        kind=ArtifactKind.TEACHING_PACKAGE_ZIP,
        path=str(output_path),
        title=f"Teaching package {workflow_run_id}",
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        workflow_run_id=workflow_run_id,
        source_ref=workflow_run_id,
        metadata={
            "packageSha256": package_sha256,
            "sizeBytes": size_bytes,
            "entryNames": list(ENTRY_NAMES),
            "entryCount": len(ENTRY_NAMES),
            "workflowRunId": workflow_run_id,
            "artifactProfile": "teaching-core",
            "validation": {
                "schemaValidatedTotal": len(SOURCE_SPECS),
                "allSchemaValidated": True,
                **contract_summary,
            },
            "deterministic": {
                "canonicalJson": True,
                "fixedEntryOrder": True,
                "fixedZipMetadata": True,
            },
            "conflictPolicy": "REUSE_MATCHING_SHA256_OR_FAIL_WITHOUT_OVERWRITE",
            "safety": {
                "candidatePreviewSafe": True,
                "taskStatusChanged": False,
                "localOnly": True,
                "realPublish": False,
            },
        },
        mode=EXPORT_MODE,
    )
    return store.save_artifact(artifact)


def _save_export_audit(
    store: JsonTaskStore,
    *,
    artifact: ArtifactRecord,
    workflow_run_id: str,
    reviewer: str,
    output_path: Path,
    package_sha256: str,
    size_bytes: int,
    trace_id: str,
) -> Any:
    event = create_operation_audit_event(
        action=OperationAction.TEACHING_PACKAGE_EXPORT,
        resource_type=OperationResourceType.ARTIFACT,
        resource_id=artifact.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=None,
        after_state=ArtifactStatus.COMPLETED.value,
        detail={
            "workflowRunId": workflow_run_id,
            "artifactProfile": "teaching-core",
            "outputPath": str(output_path),
            "packageSha256": package_sha256,
            "sizeBytes": size_bytes,
            "entryNames": list(ENTRY_NAMES),
            "entryCount": len(ENTRY_NAMES),
            "localOnly": True,
            "candidatePreviewSafe": True,
            "networkAccess": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "taskStatusChanged": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        },
    )
    event.mode = EXPORT_MODE
    return store.save_operation_audit_event(event)
