"""Phase 1 Backend API mock adapter.

This module does not start an HTTP server. It exposes a small request handler
that mirrors selected API routes and reads only local mock files.
"""

from __future__ import annotations

import hmac
import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from cli.artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from cli.ai_task import (
    AiTask,
    ReviewAction,
    ReviewAuditEvent,
    TaskStatus,
    create_review_audit_event,
    create_waiting_review_task,
)
from cli.audit import OperationAction, OperationAuditEvent, OperationResourceType, create_operation_audit_event
from cli.core_readiness import build_core_readiness_report
from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from cli.environment import EnvironmentInstance, EnvironmentStatus, EnvironmentType
from cli.grading_result_preview import GradingResultPreviewError, build_grading_result_preview
from cli.grading_job import GradingJob, GradingJobError, GradingJobStatus, create_grading_job, run_grading_job
from cli.grading_record import GradingRecord
from cli.lab_import import (
    DEFAULT_EXAM_QUESTION_IMPORT_PREVIEW_PATH,
    DEFAULT_EXAM_QUESTION_MOCK_IMPORT_PATH,
    DEFAULT_GRADING_RULE_IMPORT_PREVIEW_PATH,
    DEFAULT_GRADING_RULE_MOCK_IMPORT_PATH,
    DEFAULT_LAB_TEMPLATE_IMPORT_PREVIEW_PATH,
    DEFAULT_LAB_TEMPLATE_MOCK_IMPORT_PATH,
    DEFAULT_PPT_DECK_IMPORT_PREVIEW_PATH,
    DEFAULT_PPT_DECK_MOCK_IMPORT_PATH,
    LabTemplateImportPreviewError,
    AgentEntityMockImportError,
    AgentImportPreviewError,
    create_exam_question_import_preview,
    create_exam_question_mock_import,
    create_grading_rule_import_preview,
    create_grading_rule_mock_import,
    create_lab_template_import_preview,
    create_lab_template_mock_import,
    create_ppt_deck_import_preview,
    create_ppt_deck_mock_import,
)
from cli.mcp_audit import McpToolCallStatus
from cli.agent_entity import AgentEntityRecord
from cli.provider_audit import ProviderCallStatus, create_provider_call_audit_event
from cli.review_batch import build_review_batch_summary
from cli.review_decision_note import ReviewDecisionNoteError, create_review_decision_note
from cli.review_detail import (
    PromotionReviewEnqueueError,
    PptPageReviewUpdateError,
    ReviewMockRegenerationError,
    ReviewRevisionRequestError,
    build_review_detail,
    build_second_confirmation_status,
    enqueue_promoted_revision_for_review,
    create_review_mock_regeneration,
    create_review_revision_request,
    list_review_revision_requests,
    update_ppt_page_review_status,
)
from cli.review_pre_approve import build_pre_approve_review_check
from cli.store import JsonTaskStore
from cli.teaching_package_export import TeachingPackageExportError, export_teaching_package
from cli.workflow import WorkflowStatus, create_workflow_run, create_workflow_step
from backend.core_contract import BackendCoreRepositoryContract
from backend.core_repository import CoreRepositoryError, sync_core_repository_from_store
from backend.core_service import BackendCoreService
from backend.core_task_service import (
    BackendCoreTaskService,
    BackendCoreTaskServiceError,
    CoreArtifactInput,
)
from backend.audit_query_service import BackendAuditQueryService, BackendAuditQueryServiceError
from backend.agent_entity_service import BackendAgentEntityService, BackendAgentEntityServiceError
from backend.grading_repository import (
    DEFAULT_CLAIM_LEASE_SECONDS,
    DEFAULT_GRADING_DB_PATH,
    DEFAULT_MAX_ATTEMPTS,
    GradingRepositoryError,
    GradingSQLiteRepository,
    sync_grading_repository_from_store,
)
from backend.grading_job_service import (
    BackendGradingJobService,
    BackendGradingJobServiceError,
    GradingRepositoryPolicy,
)
from backend.grading_record_service import BackendGradingRecordService, BackendGradingRecordServiceError
from backend.grading_worker import (
    DEFAULT_WORKER_DRAIN_LIMIT,
    MAX_WORKER_DRAIN_LIMIT,
    GradingWorkerError,
    drain_grading_jobs_once,
    run_next_grading_job_once,
)
from ai_workflows.exam_conversion_workflow import (
    PHASE2_EXAM_STEP_BY_KIND,
    PHASE2_EXAM_WORKFLOW_ID,
    ExamConversionInputError,
    run_phase2_exam_conversion,
)
from ai_workflows.exam_candidate_preview import ExamCandidatePreviewError, build_candidate_safe_exam_preview
from ai_workflows.grading_generation_workflow import (
    PHASE2_GRADING_STEP_BY_KIND,
    PHASE2_GRADING_WORKFLOW_ID,
    GradingGenerationInputError,
    run_phase2_grading_generation,
)
from ai_workflows.lab_generation_v1 import build_lab_feature_readiness, finalize_lab_generation_v1
from ai_workflows.ppt_generation_workflow import (
    PHASE2_PPT_STEP_BY_KIND,
    PHASE2_PPT_WORKFLOW_ID,
    PptWorkflowInputError,
    run_phase2_ppt_generation,
)
from ai_workflows.provider_adapter_workflow import (
    ARTIFACT_PROFILE_LEGACY_ALL,
    ARTIFACT_PROFILE_TEACHING_CORE,
    PHASE2_GENERATION_STEP_BY_KIND,
    PHASE2_WORKFLOW_ID,
    PROVIDER_MODE_MOCK,
    PROVIDER_MODE_REAL_LLM,
    PROVIDER_MODE_REAL_LLM_DEMO,
    PROVIDER_MODE_REAL_LLM_MINIMAL,
    REAL_LLM_DEMO_OUTPUT_REFS,
    REAL_LLM_MINIMAL_LAB_OUTPUT_REF,
    REAL_LLM_OUTPUT_REFS,
    _build_generation_quality_summary,
    generate_real_llm_demo_dsl_via_provider,
    generate_mock_dsl_via_adapter,
    generate_workflow_dsl_bundle,
    run_phase2_content_generation,
)
from ai_workflows.real_dsl_review_preview import (
    RealDslReviewPreviewError,
    build_real_dsl_review_preview_from_files,
)
from ai_workflows.real_dsl_revision import (
    DEFAULT_BATCH_REPORT_PATH as REAL_DSL_REVISION_DEFAULT_BATCH_REPORT_PATH,
    DEFAULT_DECISION_REPORT_PATH as REAL_DSL_REVISION_DEFAULT_DECISION_REPORT_PATH,
    DEFAULT_DIFF_PREVIEW_PATH as REAL_DSL_REVISION_DEFAULT_DIFF_PREVIEW_PATH,
    DEFAULT_OUTPUT_BY_KIND as REAL_DSL_REVISION_DEFAULT_OUTPUT_BY_KIND,
    DEFAULT_PROMOTION_OUTPUT_PATH as REAL_DSL_REVISION_DEFAULT_PROMOTION_OUTPUT_PATH,
    DEFAULT_PROMOTION_REPORT_PATH as REAL_DSL_REVISION_DEFAULT_PROMOTION_REPORT_PATH,
    DEFAULT_REPORT_BY_KIND as REAL_DSL_REVISION_DEFAULT_REPORT_BY_KIND,
    DEFAULT_SOURCE_BY_KIND as REAL_DSL_REVISION_DEFAULT_SOURCE_BY_KIND,
    PROVIDER_MODE_LOCAL as REAL_DSL_REVISION_PROVIDER_MODE_LOCAL,
    RealDslRevisionError,
    build_real_dsl_revision_diff_preview,
    create_real_dsl_revision_decision,
    create_real_dsl_revision_batch_from_preview,
    create_real_dsl_revision_draft,
    promote_real_dsl_revision_candidate,
)
from ai_workflows.workflow_registry import (
    WorkflowRegistryError,
    get_phase2_workflow,
    list_phase2_workflows,
)
from materials import MaterialAnalysisError, analyze_material
from providers import (
    ProviderError,
    build_provider_error_context,
    build_provider_registry,
    build_real_llm_runtime_config_summary,
    get_provider_health,
    invoke_provider,
)
from sandbox.mock_executor import (
    GradingRunnerError,
    build_grading_audit_detail,
    build_grading_report_detail,
    build_mock_grading_report,
)
from sandbox.controlled_command_executor import (
    DEFAULT_IMAGE as DEFAULT_CONTROLLED_DOCKER_IMAGE,
    ControlledCommandSandboxError,
    build_controlled_command_sandbox_report,
)
from sandbox.evidence_auto import GradingEvidenceAutoError, build_grading_evidence_auto_report
from sandbox.evidence_merge import EvidenceMergeError, build_grading_evidence_merge_report
from sandbox.evidence_readiness import EvidenceReadinessError, build_grading_evidence_readiness, load_evidence_report
from sandbox.readonly_sandbox_executor import ReadonlySandboxExecutorError, build_readonly_sandbox_report


ROOT = Path(__file__).resolve().parents[1]
CORE_SERVICE = BackendCoreService(ROOT)
BACKEND_DEFAULT_GRADING_DB_ENV = "LAB_BACKEND_GRADING_DB_PATH"
BACKEND_API_TOKEN_ENV = "LAB_BACKEND_API_TOKEN"
GRADING_DB_PATH_SOURCE_REQUEST = "REQUEST_DB_PATH"
GRADING_DB_PATH_SOURCE_BACKEND_DEFAULT = "BACKEND_DEFAULT_ENV"
GRADING_DB_PATH_SOURCE_BUILTIN = "BUILTIN_DEFAULT"
GRADING_DB_PATH_SOURCE_JSON_STORE = "JSON_STORE"
AUTH_EXEMPT_PATHS = {"/api/health"}


def make_trace_id() -> str:
    return f"trace_{uuid4().hex[:12]}"


def ok(message: str, data: dict[str, Any], trace_id: str | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "code": "OK",
        "message": message,
        "data": data,
        "traceId": trace_id or make_trace_id(),
    }


def fail(
    code: str,
    message: str,
    errors: list[dict[str, str]] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "code": code,
        "message": message,
        "errors": errors or [],
        "traceId": trace_id or make_trace_id(),
    }


def validate_backend_api_auth(
    *,
    headers: dict[str, str] | None,
    path: str,
    trace_id: str,
) -> dict[str, Any] | None:
    configured_token = str(os.environ.get(BACKEND_API_TOKEN_ENV) or "").strip()
    if not configured_token or path in AUTH_EXEMPT_PATHS:
        return None
    auth_header = _get_header(headers, "Authorization")
    if not auth_header:
        return fail(
            "AUTH_REQUIRED",
            "Backend API 需要 Authorization Bearer token",
            [{"field": "Authorization", "reason": "missing bearer token"}],
            trace_id,
        )
    if not auth_header.startswith("Bearer "):
        return fail(
            "AUTH_INVALID",
            "Backend API Authorization 格式错误",
            [{"field": "Authorization", "reason": "expected Bearer token"}],
            trace_id,
        )
    provided_token = auth_header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(provided_token, configured_token):
        return fail(
            "AUTH_INVALID",
            "Backend API token 校验失败",
            [{"field": "Authorization", "reason": "invalid bearer token"}],
            trace_id,
        )
    return None


def _get_header(headers: dict[str, str] | None, name: str) -> str | None:
    if not headers:
        return None
    expected = name.lower()
    for key, value in headers.items():
        if key.lower() == expected:
            return str(value)
    return None


def read_local_report(query: dict[str, str], trace_id: str) -> dict[str, Any]:
    file_value = query.get("file")
    if not file_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "file", "reason": "缺少参数"}], trace_id)
    report_path = Path(file_value)
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    if not report_path.exists() or not report_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "file", "reason": "文件不存在"}], trace_id)
    with report_path.open("r", encoding="utf-8") as file:
        report = json.load(file)
    if not isinstance(report, dict):
        return fail("VALIDATION_ERROR", "报告格式错误", [{"field": "file", "reason": "root must be object"}], trace_id)
    return ok("查询成功", {"report": report, "reportPath": str(report_path)}, trace_id)


def attach_grading_review_evidence(
    response: dict[str, Any],
    query: dict[str, str],
    store: JsonTaskStore,
) -> dict[str, Any]:
    task_id = str(query.get("taskId") or "").strip()
    if not task_id:
        return response
    detail = build_review_detail(store, task_id)
    if detail is None:
        response["data"]["mergedGradingEvidence"] = {
            "visible": False,
            "source": "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence",
            "taskId": task_id,
            "summary": {
                "available": False,
                "checkEvidenceReviewItemTotal": 0,
                "manualCheckReviewTotal": 0,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
            },
            "checkEvidenceReviewItems": [],
            "reviewDecisionHints": {
                "available": False,
                "source": "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence.reviewDecisionHints",
                "overallHint": "NEEDS_EVIDENCE",
                "hintTotal": 0,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
            },
            "safety": {
                "mergeExecutedOnlyExistingReports": True,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
                "realPublish": False,
            },
            "message": "AI Task 不存在或暂无审核详情",
        }
        response["data"]["reviewDecisionNotes"] = {
            "component": "ReviewDecisionNoteSummary",
            "visible": False,
            "total": 0,
            "latest": None,
            "items": [],
            "source": "GET /api/review-tasks/{id}.reviewDetail.reviewDecisionNotes",
            "safety": {
                "statusChanged": False,
                "taskStatusUnchanged": True,
                "autoApproveAllowed": False,
                "batchStateChangeAllowed": False,
                "realPublishAllowed": False,
                "realPublish": False,
            },
        }
        response["data"]["reviewTaskId"] = task_id
        response["data"]["mergedGradingEvidenceSummary"] = response["data"]["mergedGradingEvidence"]["summary"]
        response["data"]["mergedGradingEvidenceCheckItems"] = []
        response["data"]["reviewDecisionHints"] = response["data"]["mergedGradingEvidence"]["reviewDecisionHints"]
        return response
    merged_evidence = detail.get("mergedGradingEvidence", {})
    response["data"]["reviewTaskId"] = task_id
    response["data"]["mergedGradingEvidence"] = merged_evidence
    response["data"]["mergedGradingEvidenceSummary"] = (
        merged_evidence.get("summary", {}) if isinstance(merged_evidence, dict) else {}
    )
    response["data"]["mergedGradingEvidenceCheckItems"] = (
        merged_evidence.get("checkEvidenceReviewItems", []) if isinstance(merged_evidence, dict) else []
    )
    response["data"]["reviewDecisionHints"] = (
        merged_evidence.get("reviewDecisionHints", {}) if isinstance(merged_evidence, dict) else {}
    )
    response["data"]["reviewDecisionNotes"] = (
        detail.get("reviewDecisionNotes", {}) if isinstance(detail.get("reviewDecisionNotes"), dict) else {}
    )
    response["data"]["autoGradingEvidenceSummary"] = (
        response["data"]["mergedGradingEvidenceSummary"]
        if isinstance(response["data"]["mergedGradingEvidenceSummary"], dict)
        and response["data"]["mergedGradingEvidenceSummary"].get("autoEvidenceReport") is True
        else {
            "available": False,
            "autoEvidenceReport": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        }
    )
    return response


def read_grading_report(query: dict[str, str], trace_id: str, store: JsonTaskStore) -> dict[str, Any]:
    response = read_local_report(query, trace_id)
    if response.get("success") is not True:
        return response
    report = response["data"]["report"]
    response["data"]["reportDetail"] = build_grading_report_detail(report)
    return attach_grading_review_evidence(response, query, store)


def build_backend_core_readiness_report(
    store: JsonTaskStore,
    *,
    query: dict[str, str] | None = None,
    trace_id: str,
) -> dict[str, Any]:
    query = query or {}
    task_filter = str(query.get("taskId") or "").strip() or None
    repository, repository_policy = resolve_grading_repository(query, use_backend_default=True)
    core_repository, core_repository_policy = resolve_backend_core_repository(query)
    tasks = store.list()
    artifacts = store.list_artifacts()
    agent_entities = store.list_agent_entities(source_task_id=task_filter) if task_filter else store.list_agent_entities()
    operation_audits = store.list_operation_audit_events()
    review_audits = store.list_review_audit_events()
    provider_audits = store.list_provider_call_audit_events()
    grading_jobs = _read_grading_jobs_for_backend_readiness(store, repository, task_filter)
    grading_records = _read_grading_records_for_backend_readiness(store, repository, task_filter)
    sqlite_summary = _backend_readiness_sqlite_summary(repository)
    core_repository_summary = _backend_core_repository_summary(core_repository)

    capability_groups = [
        _backend_readiness_capability(
            "aiTaskApi",
            "AI Task API",
            ["GET /api/ai-tasks", "GET /api/ai-tasks/{id}", "POST /api/ai-tasks/{id}/approve", "POST /api/ai-tasks/{id}/reject"],
            implemented=True,
            production_ready=False,
            stored_total=len(tasks),
            remaining=["replace_json_store_with_database", "add_authn_authz", "add_pagination"],
        ),
        _backend_readiness_capability(
            "artifactApi",
            "Artifact API",
            ["GET /api/artifacts", "GET /api/artifacts/{id}"],
            implemented=True,
            production_ready=False,
            stored_total=len(artifacts),
            remaining=["replace_local_paths_with_object_storage_refs", "add_artifact_access_control"],
        ),
        _backend_readiness_capability(
            "reviewApi",
            "Review API",
            ["GET /api/review-tasks", "GET /api/review-tasks/{id}", "GET /api/review-tasks/{id}/core-readiness"],
            implemented=True,
            production_ready=False,
            stored_total=len(review_audits),
            remaining=["persist_review_decisions_in_database", "add_reviewer_permissions", "add_audit_retention_policy"],
        ),
        _backend_readiness_capability(
            "agentEntityImportApi",
            "Platform Entity Import API",
            [
                "POST /api/labs/import-preview",
                "POST /api/exams/import-preview",
                "POST /api/grading/import-preview",
                "POST /api/ppt/import-preview",
                "POST /api/platform-entities/contract-validate",
                "POST /api/platform-entities/{id}/import-dry-run",
            ],
            implemented=True,
            production_ready=False,
            stored_total=len(agent_entities),
            remaining=["connect_real_platform_adapter_after_contract_confirmed", "persist_import_activity", "add_platform_api_auth"],
        ),
        _backend_readiness_capability(
            "gradingJobApi",
            "Grading Job API",
            ["POST /api/grading/jobs", "GET /api/grading/jobs", "GET /api/grading/jobs/{id}", "POST /api/grading/jobs/{id}/run"],
            implemented=True,
            production_ready=False,
            stored_total=len(grading_jobs),
            remaining=["replace_sync_worker_with_queue_consumer", "add_transactional_job_claims", "add_multi_tenant_limits"],
        ),
        _backend_readiness_capability(
            "gradingRecordApi",
            "Grading Record API",
            ["POST /api/grading/records", "GET /api/grading/records", "GET /api/grading/records/{id}", "POST /api/grading/records/{id}/review"],
            implemented=True,
            production_ready=False,
            stored_total=len(grading_records),
            remaining=["persist_records_in_production_database", "connect_platform_review_api", "hide_teacher_only_evidence_from_candidate"],
        ),
        _backend_readiness_capability(
            "gradingWorkerApi",
            "Grading Worker API",
            ["POST /api/grading/workers/run-once", "POST /api/grading/workers/drain-once"],
            implemented=True,
            production_ready=False,
            stored_total=int(sqlite_summary.get("jobTotal", 0)) if sqlite_summary.get("available") else len(grading_jobs),
            remaining=["replace_local_sqlite_with_real_queue", "run_managed_worker_service", "add_observability_and_retry_policy"],
        ),
        _backend_readiness_capability(
            "auditApi",
            "Audit API",
            ["GET /api/audit-events", "GET /api/review-audit-events", "GET /api/provider-audit-events"],
            implemented=True,
            production_ready=False,
            stored_total=len(operation_audits) + len(review_audits) + len(provider_audits),
            remaining=["centralize_audit_storage", "add_actor_identity", "add_retention_and_export_policy"],
        ),
    ]
    ready_for_real_backend_mvp = all(item["implemented"] for item in capability_groups)
    production_ready_total = sum(1 for item in capability_groups if item["productionReady"])
    return {
        "component": "BackendCoreReadinessReport",
        "mode": "BACKEND_CORE_READINESS_LOCAL_STAGING",
        "traceId": trace_id,
        "storePath": str(store.path),
        "filters": {"taskId": task_filter},
        "summary": {
            "capabilityTotal": len(capability_groups),
            "implementedTotal": sum(1 for item in capability_groups if item["implemented"]),
            "productionReadyTotal": production_ready_total,
            "readyForRealBackendMvp": ready_for_real_backend_mvp,
            "readyForProduction": production_ready_total == len(capability_groups),
            "nextStage": "REAL_BACKEND_API_MVP",
            "nextRecommendedCapability": "real_backend_persistence_and_auth_boundary",
        },
        "capabilities": capability_groups,
        "dataSnapshot": {
            "taskTotal": len(tasks),
            "waitingReviewTaskTotal": sum(1 for task in tasks if task.status.value == "WAITING_REVIEW"),
            "artifactTotal": len(artifacts),
            "agentEntityTotal": len(agent_entities),
            "gradingJobTotal": len(grading_jobs),
            "gradingRecordTotal": len(grading_records),
            "operationAuditTotal": len(operation_audits),
            "reviewAuditTotal": len(review_audits),
            "providerAuditTotal": len(provider_audits),
            "gradingJobsByStatus": _count_values(job.status.value for job in grading_jobs),
            "gradingRecordsByStatus": _count_values(record.status.value for record in grading_records),
        },
        "sqliteStaging": {
            "enabled": repository is not None,
            "policy": repository_policy,
            "summary": sqlite_summary,
        },
        "coreSqliteStaging": {
            "enabled": core_repository is not None,
            "policy": core_repository_policy,
            "summary": core_repository_summary,
        },
        "migrationBoundary": {
            "source": "JsonTaskStore + optional local SQLite staging",
            "target": "real backend database + authenticated API + managed queue",
            "keepContracts": [
                "unified_json_envelope",
                "WAITING_REVIEW_before_publish",
                "grading_job_to_grading_record_flow",
                "operation_audit_event",
                "manual_review_required",
            ],
            "replaceImplementations": [
                "JsonTaskStore",
                "local SQLite staging path",
                "mock HTTP request handler",
                "single-process worker",
            ],
        },
        "safety": {
            "readOnly": True,
            "storeMutated": False,
            "workerStarted": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "networkAccess": False,
            "secretsRead": False,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }


def get_backend_core_readiness_request(query: dict[str, str], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    return ok(
        "Backend 核心 API readiness 已生成",
        {"backendCoreReadiness": build_backend_core_readiness_report(store, query=query, trace_id=trace_id)},
        trace_id,
    )


def create_backend_core_repository(payload: dict[str, Any]) -> BackendCoreRepositoryContract:
    return CORE_SERVICE.create_repository(payload)


def resolve_backend_core_repository(
    payload: dict[str, Any],
    *,
    fallback_to_builtin: bool = False,
) -> tuple[BackendCoreRepositoryContract | None, dict[str, Any]]:
    return CORE_SERVICE.resolve_repository(payload, fallback_to_builtin=fallback_to_builtin)


def backend_core_repository_error_response(exc: CoreRepositoryError, trace_id: str) -> dict[str, Any]:
    return fail(exc.code, exc.message, exc.errors, trace_id)


def backend_core_task_service_error_response(exc: BackendCoreTaskServiceError, trace_id: str) -> dict[str, Any]:
    return fail(exc.code, exc.message, exc.errors, trace_id)


def create_backend_core_task_request(payload: dict[str, Any], trace_id: str) -> dict[str, Any]:
    try:
        repository = create_backend_core_repository(payload)
        service = BackendCoreTaskService(repository)
        result = service.create_waiting_review_task(
            task_type=str(payload.get("taskType") or payload.get("task_type") or ""),
            title=str(payload.get("title") or ""),
            input_type=str(payload.get("inputType") or payload.get("input_type") or ""),
            input_ref=str(payload.get("inputRef") or payload.get("input_ref") or ""),
            final_result_path=_optional_text(payload.get("finalResultPath") or payload.get("final_result_path")),
            actor=str(payload.get("actor") or payload.get("createdBy") or ""),
            trace_id=trace_id,
            artifacts=parse_backend_core_artifact_inputs(payload.get("artifacts")),
        )
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    except BackendCoreTaskServiceError as exc:
        return backend_core_task_service_error_response(exc, trace_id)
    except ValueError as exc:
        return fail(
            "BACKEND_CORE_TASK_VALIDATION_ERROR",
            "Backend Core task 参数错误",
            [{"field": "artifacts", "reason": str(exc)}],
            trace_id,
        )
    data = {
        "task": result["task"].to_dict(),
        "artifacts": [artifact.to_dict() for artifact in result["artifacts"]],
        "operationAuditEvent": result["operationAuditEvent"].to_dict(),
        "backendCoreTaskService": {
            "mode": "LOCAL_SQLITE_BACKEND_CORE_SERVICE",
            "coreDbPath": str(repository.db_path),
            "taskWritten": True,
            "artifactsWritten": len(result["artifacts"]),
            "operationAuditEventWritten": True,
            "reviewAuditEventWritten": False,
            "localSqliteWritten": True,
            **result["safety"],
        },
    }
    return ok("Backend Core AI Task 已创建，等待人工审核", data, trace_id)


def list_backend_core_task_request(query: dict[str, str], trace_id: str) -> dict[str, Any]:
    try:
        repository = create_backend_core_repository(query)
        items = CORE_SERVICE.list_ai_task_payloads(
            repository,
            status=_optional_text(query.get("status")),
            task_type=_optional_text(query.get("taskType") or query.get("task_type")),
        )
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    except sqlite3.Error as exc:
        return fail(
            "BACKEND_CORE_SQLITE_READONLY_ERROR",
            "Backend Core 本地 SQLite 只读查询失败",
            [{"field": "coreDbPath", "reason": str(exc)}],
            trace_id,
        )
    return ok(
        "查询成功",
        {
            "items": items,
            "total": len(items),
            "backendCoreTaskService": {
                "mode": "LOCAL_SQLITE_BACKEND_CORE_SERVICE_READONLY",
                "coreDbPath": str(repository.db_path),
                "repositoryContractUsed": True,
                "localSqliteRead": True,
                "jsonStoreRead": False,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        },
        trace_id,
    )


def get_backend_core_task_request(task_id: str, query: dict[str, str], trace_id: str) -> dict[str, Any]:
    try:
        repository = create_backend_core_repository(query)
        task_payload = CORE_SERVICE.get_ai_task_payload(repository, task_id)
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    except sqlite3.Error as exc:
        return fail(
            "BACKEND_CORE_SQLITE_READONLY_ERROR",
            "Backend Core 本地 SQLite 只读查询失败",
            [{"field": "coreDbPath", "reason": str(exc)}],
            trace_id,
        )
    if task_payload is None:
        return fail("NOT_FOUND", "Backend Core AI Task 不存在", [{"field": "id", "reason": "未找到任务"}], trace_id)
    return ok(
        "查询成功",
        {
            "task": task_payload,
            "backendCoreTaskService": {
                "mode": "LOCAL_SQLITE_BACKEND_CORE_SERVICE_READONLY",
                "coreDbPath": str(repository.db_path),
                "repositoryContractUsed": True,
                "localSqliteRead": True,
                "jsonStoreRead": False,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        },
        trace_id,
    )


def review_backend_core_task_request(
    task_id: str,
    payload: dict[str, Any],
    *,
    decision: str,
    trace_id: str,
) -> dict[str, Any]:
    try:
        repository = create_backend_core_repository(payload)
        service = BackendCoreTaskService(repository)
        result = service.review_task(
            task_id=task_id,
            reviewer=str(payload.get("reviewer") or payload.get("actor") or ""),
            decision=decision,
            reason=_optional_text(payload.get("reason")),
            trace_id=trace_id,
        )
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    except BackendCoreTaskServiceError as exc:
        return backend_core_task_service_error_response(exc, trace_id)
    data = {
        "task": result["task"].to_dict(),
        "reviewAuditEvent": result["reviewAuditEvent"].to_dict(),
        "operationAuditEvent": result["operationAuditEvent"].to_dict(),
        "backendCoreTaskService": {
            "mode": "LOCAL_SQLITE_BACKEND_CORE_SERVICE",
            "coreDbPath": str(repository.db_path),
            "taskWritten": True,
            "artifactsWritten": 0,
            "operationAuditEventWritten": True,
            "reviewAuditEventWritten": True,
            "localSqliteWritten": True,
            **result["safety"],
        },
    }
    message = "Backend Core AI Task 审核通过" if decision == "approve" else "Backend Core AI Task 审核拒绝"
    return ok(message, data, trace_id)


def parse_backend_core_review_action(path: str) -> tuple[str, str] | None:
    if not path.startswith("/api/backend/core-tasks/"):
        return None
    parts = path.removeprefix("/api/backend/core-tasks/").split("/")
    if len(parts) != 2 or parts[1] not in {"approve", "reject", "review"}:
        return None
    return parts[0], parts[1]


def parse_backend_core_artifact_inputs(value: Any) -> list[CoreArtifactInput]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("must be array")
    artifact_inputs: list[CoreArtifactInput] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"artifacts[{index}] must be object")
        try:
            kind = ArtifactKind(str(item.get("kind") or ""))
        except ValueError as exc:
            raise ValueError(f"artifacts[{index}].kind unsupported") from exc
        try:
            status = ArtifactStatus(str(item.get("status") or ArtifactStatus.WAITING_REVIEW.value))
        except ValueError as exc:
            raise ValueError(f"artifacts[{index}].status unsupported") from exc
        artifact_inputs.append(
            CoreArtifactInput(
                kind=kind,
                path=str(item.get("path") or ""),
                title=str(item.get("title") or ""),
                status=status,
                source_ref=_optional_text(item.get("sourceRef") or item.get("source_ref")),
                metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                mode=str(item.get("mode") or "BACKEND_CORE_API"),
                real_llm_called=item.get("realLlmCalled") is True,
                real_cloud_resource_changed=item.get("realCloudResourceChanged") is True,
                sandbox_executed=item.get("sandboxExecuted") is True,
                contestant_code_executed=item.get("contestantCodeExecuted") is True,
                real_publish=item.get("realPublish") is True,
            )
        )
    return artifact_inputs


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def initialize_backend_core_repository_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    try:
        repository = create_backend_core_repository(payload)
        summary = repository.initialize_schema()
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    event = create_operation_audit_event(
        action=OperationAction.BACKEND_CORE_REPOSITORY_INIT,
        resource_type=OperationResourceType.BACKEND_CORE_REPOSITORY,
        resource_id=str(repository.db_path),
        actor=str(payload.get("actor") or "backend-mock"),
        trace_id=trace_id,
        after_state="INITIALIZED",
        detail={
            "component": "BackendCoreSQLiteRepositoryInit",
            "dbPath": str(repository.db_path),
            "schemaVersion": summary["schemaVersion"],
            "tables": summary["tables"],
            "localSqliteOnly": True,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    )
    store.save_operation_audit_event(event)
    return ok(
        "Backend Core 本地 SQLite 仓储已初始化",
        {
            "backendCoreRepository": summary,
            "operationAuditEvent": event.to_dict(),
            "mode": "LOCAL_SQLITE_BACKEND_CORE_REPOSITORY",
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def sync_backend_core_repository_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    try:
        repository = create_backend_core_repository(payload)
        result = sync_core_repository_from_store(repository=repository, store=store)
        summary = repository.summary()
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    event = create_operation_audit_event(
        action=OperationAction.BACKEND_CORE_REPOSITORY_SYNC_LOCAL,
        resource_type=OperationResourceType.BACKEND_CORE_REPOSITORY,
        resource_id=str(repository.db_path),
        actor=str(payload.get("actor") or "backend-mock"),
        trace_id=trace_id,
        after_state="SYNCED",
        detail={
            "component": "BackendCoreSQLiteRepositorySyncLocal",
            "dbPath": str(repository.db_path),
            "tasksSynced": result["tasksSynced"],
            "artifactsSynced": result["artifactsSynced"],
            "reviewAuditEventsSynced": result["reviewAuditEventsSynced"],
            "operationAuditEventsSynced": result["operationAuditEventsSynced"],
            "agentEntitiesSynced": result["agentEntitiesSynced"],
            "localSqliteOnly": True,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    )
    store.save_operation_audit_event(event)
    return ok(
        "Backend Core 本地 JSON store 已同步到 SQLite 仓储",
        {
            "backendCoreRepositorySync": result,
            "backendCoreRepository": summary,
            "operationAuditEvent": event.to_dict(),
            "mode": "LOCAL_JSON_STORE_TO_BACKEND_CORE_SQLITE_SYNC",
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def prepare_backend_core_write_through(
    payload: dict[str, Any],
) -> tuple[BackendCoreRepositoryContract | None, dict[str, Any] | None]:
    return CORE_SERVICE.prepare_write_through(payload)


def backend_core_write_through(
    repository: BackendCoreRepositoryContract | None,
    summary: dict[str, Any] | None,
    *,
    task: AiTask | None = None,
    agent_entity: AgentEntityRecord | None = None,
    artifacts: list[ArtifactRecord | dict[str, Any]] | None = None,
    review_audit_event: ReviewAuditEvent | None = None,
    operation_audit_event: OperationAuditEvent | None = None,
) -> None:
    CORE_SERVICE.write_through(
        repository,
        summary,
        task=task,
        agent_entity=agent_entity,
        artifacts=artifacts,
        review_audit_event=review_audit_event,
        operation_audit_event=operation_audit_event,
    )


def attach_agent_entity_mock_import_core_write(
    payload: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Mirror an existing local mock-import record into the requested Core repository."""
    repository, summary = prepare_backend_core_write_through(payload)
    if repository is None:
        return
    entity_payload = result.get("agentEntityRecord")
    artifact_payload = result.get("artifact")
    operation_payload = result.get("operationAuditEvent")
    if not isinstance(entity_payload, dict) or not isinstance(artifact_payload, dict) or not isinstance(operation_payload, dict):
        raise CoreRepositoryError(
            "BACKEND_CORE_WRITE_THROUGH_INVALID_RESULT",
            "平台实体 Mock 入库结果缺少 Core 镜像所需数据",
            [{"field": "result", "reason": "agentEntityRecord, artifact, operationAuditEvent are required"}],
        )
    backend_core_write_through(
        repository,
        summary,
        agent_entity=AgentEntityRecord.from_dict(entity_payload),
        artifacts=[ArtifactRecord.from_dict(artifact_payload)],
        operation_audit_event=OperationAuditEvent.from_dict(operation_payload),
    )
    result["backendCoreWriteThrough"] = summary


def attach_platform_import_preview_core_write(
    payload: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Mirror an existing local import-preview artifact into the requested Core repository."""
    repository, summary = prepare_backend_core_write_through(payload)
    if repository is None:
        return
    artifact_payload = result.get("artifact")
    operation_payload = result.get("operationAuditEvent")
    if not isinstance(artifact_payload, dict) or not isinstance(operation_payload, dict):
        raise CoreRepositoryError(
            "BACKEND_CORE_WRITE_THROUGH_INVALID_RESULT",
            "平台实体导入预览结果缺少 Core 镜像所需数据",
            [{"field": "result", "reason": "artifact and operationAuditEvent are required"}],
        )
    backend_core_write_through(
        repository,
        summary,
        artifacts=[ArtifactRecord.from_dict(artifact_payload)],
        operation_audit_event=OperationAuditEvent.from_dict(operation_payload),
    )
    result["backendCoreWriteThrough"] = summary


def get_backend_core_repository_summary_request(
    query: dict[str, str],
    trace_id: str,
) -> dict[str, Any]:
    try:
        repository, policy = resolve_backend_core_repository(query)
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    return ok(
        "Backend Core 本地 SQLite 仓储摘要已生成",
        {
            "backendCoreRepository": _backend_core_repository_summary(repository),
            "policy": policy,
            "mode": "LOCAL_SQLITE_BACKEND_CORE_REPOSITORY_SUMMARY",
            "readOnly": True,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def _backend_readiness_capability(
    capability_id: str,
    title: str,
    endpoints: list[str],
    *,
    implemented: bool,
    production_ready: bool,
    stored_total: int,
    remaining: list[str],
) -> dict[str, Any]:
    return {
        "id": capability_id,
        "title": title,
        "implemented": implemented,
        "productionReady": production_ready,
        "storedTotal": stored_total,
        "endpoints": endpoints,
        "storageMode": "LOCAL_JSON_OR_SQLITE_STAGING",
        "remainingForProduction": remaining,
        "stopLine": "do_not_add_more_mock_shells_for_this_capability",
    }


def _read_grading_jobs_for_backend_readiness(
    store: JsonTaskStore,
    repository: GradingSQLiteRepository | None,
    task_id: str | None,
) -> list[Any]:
    if repository is not None and repository.db_path.exists():
        try:
            return _readonly_sqlite_grading_jobs(repository.db_path, task_id)
        except (sqlite3.Error, KeyError, TypeError, ValueError):
            return store.list_grading_jobs(task_id=task_id)
    return store.list_grading_jobs(task_id=task_id)


def _read_grading_records_for_backend_readiness(
    store: JsonTaskStore,
    repository: GradingSQLiteRepository | None,
    task_id: str | None,
) -> list[Any]:
    if repository is not None and repository.db_path.exists():
        try:
            return _readonly_sqlite_grading_records(repository.db_path, task_id)
        except (sqlite3.Error, KeyError, TypeError, ValueError):
            return store.list_grading_records(task_id=task_id)
    return store.list_grading_records(task_id=task_id)


def _backend_readiness_sqlite_summary(repository: GradingSQLiteRepository | None) -> dict[str, Any]:
    if repository is None:
        return {
            "available": False,
            "reason": "dbPath not configured",
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }
    if not repository.db_path.exists():
        return {
            "available": False,
            "dbPath": str(repository.db_path),
            "reason": "sqlite staging file does not exist",
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }
    try:
        connection = _connect_readonly_grading_sqlite(repository.db_path)
        try:
            connection.row_factory = sqlite3.Row
            tables = _readonly_sqlite_tables(connection)
            job_total = _readonly_sqlite_count(connection, "grading_jobs") if "grading_jobs" in tables else 0
            record_total = _readonly_sqlite_count(connection, "grading_records") if "grading_records" in tables else 0
            jobs_by_status = (
                _readonly_sqlite_count_by_status(connection, "grading_jobs") if "grading_jobs" in tables else {}
            )
            records_by_status = (
                _readonly_sqlite_count_by_status(connection, "grading_records") if "grading_records" in tables else {}
            )
            schema_version = (
                _readonly_sqlite_schema_version(connection) if "grading_repository_meta" in tables else None
            )
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return {
            "available": False,
            "dbPath": str(repository.db_path),
            "errorCode": "LOCAL_SQLITE_READONLY_ERROR",
            "errors": [{"field": "dbPath", "reason": str(exc)}],
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }
    return {
        "available": True,
        "dbPath": str(repository.db_path),
        "schemaVersion": schema_version,
        "tables": tables,
        "jobTotal": job_total,
        "recordTotal": record_total,
        "jobsByStatus": jobs_by_status,
        "recordsByStatus": records_by_status,
        "mode": "LOCAL_SQLITE_GRADING_REPOSITORY_READONLY",
        "safety": {
            "localSqliteOnly": True,
            "readOnly": True,
            "workerStarted": False,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        "productionDatabaseWritten": False,
        "productionQueueUsed": False,
    }


def _backend_core_repository_summary(repository: BackendCoreRepositoryContract | None) -> dict[str, Any]:
    return CORE_SERVICE.repository_summary(repository)


def _connect_readonly_grading_sqlite(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _readonly_sqlite_grading_jobs(path: Path, task_id: str | None) -> list[GradingJob]:
    connection = _connect_readonly_grading_sqlite(path)
    try:
        query = "SELECT raw_json FROM grading_jobs"
        values: list[Any] = []
        if task_id:
            query += " WHERE task_id = ?"
            values.append(task_id)
        query += " ORDER BY created_at DESC"
        rows = connection.execute(query, values).fetchall()
    finally:
        connection.close()
    return [GradingJob.from_dict(json.loads(row["raw_json"])) for row in rows]


def _readonly_sqlite_grading_records(path: Path, task_id: str | None) -> list[GradingRecord]:
    connection = _connect_readonly_grading_sqlite(path)
    try:
        query = "SELECT raw_json FROM grading_records"
        values: list[Any] = []
        if task_id:
            query += " WHERE task_id = ?"
            values.append(task_id)
        query += " ORDER BY created_at DESC"
        rows = connection.execute(query, values).fetchall()
    finally:
        connection.close()
    return [GradingRecord.from_dict(json.loads(row["raw_json"])) for row in rows]


def _readonly_sqlite_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return [str(row["name"]) for row in rows]


def _readonly_sqlite_count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    return int(row["total"]) if row is not None else 0


def _readonly_sqlite_count_by_status(connection: sqlite3.Connection, table: str) -> dict[str, int]:
    rows = connection.execute(f"SELECT status, COUNT(*) AS total FROM {table} GROUP BY status").fetchall()
    return {str(row["status"]): int(row["total"]) for row in rows}


def _readonly_sqlite_count_by_column(connection: sqlite3.Connection, table: str, column: str) -> dict[str, int]:
    rows = connection.execute(f"SELECT {column} AS value, COUNT(*) AS total FROM {table} GROUP BY {column}").fetchall()
    return {str(row["value"]): int(row["total"]) for row in rows}


def _readonly_sqlite_schema_version(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT value FROM grading_repository_meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        return None
    return str(row["value"])


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def create_grading_record_request(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    repository, repository_policy = resolve_grading_repository(payload, use_backend_default=True)
    service = BackendGradingRecordService(
        root=ROOT,
        store=store,
        repository=repository,
        repository_policy=GradingRepositoryPolicy.from_dict(repository_policy),
    )
    try:
        result = service.create_record(payload, trace_id=trace_id)
    except BackendGradingRecordServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok(
        "Grading 评分记录已创建，等待人工复核",
        {
            **{key: value for key, value in result.items() if key not in {"gradingRecord", "operationAuditEvent"}},
            "gradingRecord": result["gradingRecord"].to_dict(),
            "operationAuditEvent": result["operationAuditEvent"].to_dict(),
        },
        trace_id,
    )


def list_grading_record_request(query: dict[str, str], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    repository, repository_policy = resolve_grading_repository(query, use_backend_default=True)
    if repository:
        try:
            records = repository.list_grading_records(
                task_id=query.get("taskId"),
                submission_id=query.get("submissionId"),
                status=query.get("status"),
                candidate_id=query.get("candidateId"),
            )
        except GradingRepositoryError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok(
            "查询成功",
            {
                "items": [record.to_dict() for record in records],
                "total": len(records),
                "filters": {
                    "taskId": query.get("taskId"),
                    "submissionId": query.get("submissionId"),
                    "candidateId": query.get("candidateId"),
                    "status": query.get("status"),
                },
                "mode": "LOCAL_SQLITE_GRADING_RECORD",
                "dbPath": str(repository.db_path),
                "dbPathSource": repository_policy["dbPathSource"],
                "backendDefaultSqliteEnabled": repository_policy["backendDefaultSqliteEnabled"],
                "localSqliteRead": True,
                "databaseWritten": False,
                "productionDatabaseWritten": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
            trace_id,
        )
    records = store.list_grading_records(
        task_id=query.get("taskId"),
        submission_id=query.get("submissionId"),
        status=query.get("status"),
        candidate_id=query.get("candidateId"),
    )
    return ok(
        "查询成功",
        {
            "items": [record.to_dict() for record in records],
            "total": len(records),
            "filters": {
                "taskId": query.get("taskId"),
                "submissionId": query.get("submissionId"),
                "candidateId": query.get("candidateId"),
                "status": query.get("status"),
            },
            "mode": "LOCAL_GRADING_RECORD",
            "databaseWritten": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def get_grading_record_request(
    record_id: str,
    store: JsonTaskStore,
    trace_id: str,
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    query = query or {}
    repository, repository_policy = resolve_grading_repository(query, use_backend_default=True)
    if repository:
        try:
            record = repository.get_grading_record(record_id)
        except GradingRepositoryError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        if record is None:
            return fail("NOT_FOUND", "Grading 评分记录不存在", [{"field": "id", "reason": "未找到记录"}], trace_id)
        return ok(
            "查询成功",
            {
                "gradingRecord": record.to_dict(),
                "mode": "LOCAL_SQLITE_GRADING_RECORD",
                "dbPath": str(repository.db_path),
                "dbPathSource": repository_policy["dbPathSource"],
                "backendDefaultSqliteEnabled": repository_policy["backendDefaultSqliteEnabled"],
                "localSqliteRead": True,
                "databaseWritten": False,
                "productionDatabaseWritten": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
            trace_id,
        )
    record = store.get_grading_record(record_id)
    if record is None:
        return fail("NOT_FOUND", "Grading 评分记录不存在", [{"field": "id", "reason": "未找到记录"}], trace_id)
    return ok(
        "查询成功",
        {
            "gradingRecord": record.to_dict(),
            "mode": "LOCAL_GRADING_RECORD",
            "databaseWritten": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def _create_grading_job_from_payload(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> tuple[Any, dict[str, Any] | None]:
    required_fields = {
        "grading": payload.get("grading"),
        "submission": payload.get("submission"),
        "output": payload.get("output"),
        "submissionId": payload.get("submissionId"),
    }
    missing = [
        {"field": field, "reason": "缺少参数"}
        for field, value in required_fields.items()
        if not value
    ]
    if missing:
        return None, fail("VALIDATION_ERROR", "参数错误", missing, trace_id)
    task_id = str(payload.get("taskId") or "").strip() or None
    if task_id and store.get(task_id) is None:
        return None, fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
    grading_path = resolve_local_path(str(payload["grading"]))
    submission_path = resolve_local_path(str(payload["submission"]))
    if not grading_path.exists() or not grading_path.is_file():
        return None, fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "文件不存在"}], trace_id)
    if not submission_path.exists() or not submission_path.is_dir():
        return None, fail("VALIDATION_ERROR", "参数错误", [{"field": "submission", "reason": "目录不存在"}], trace_id)
    try:
        job = create_grading_job(
            grading_path=grading_path,
            submission_path=submission_path,
            output_path=resolve_local_path(str(payload["output"])),
            submission_id=str(payload.get("submissionId") or ""),
            trace_id=trace_id,
            task_id=task_id,
            candidate_id=str(payload.get("candidateId") or "").strip() or None,
            reviewer=str(payload.get("reviewer") or "").strip() or None,
            include_controlled_command=payload.get("includeControlledCommand") is True,
            fail_on_controlled_unavailable=payload.get("failOnControlledUnavailable") is True,
            image=str(payload.get("image") or DEFAULT_CONTROLLED_DOCKER_IMAGE),
        )
    except GradingJobError as exc:
        return None, fail(exc.code, exc.message, exc.errors, trace_id)
    return job, None


def create_grading_job_request(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    repository, repository_policy = resolve_grading_repository(payload, use_backend_default=True)
    service = BackendGradingJobService(
        root=ROOT,
        store=store,
        repository=repository,
        repository_policy=GradingRepositoryPolicy.from_dict(repository_policy),
    )
    try:
        result = service.create_job(payload, trace_id=trace_id)
    except BackendGradingJobServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok(
        "Grading 评分任务已创建，等待执行",
        {
            **{key: value for key, value in result.items() if key not in {"gradingJob", "operationAuditEvent"}},
            "gradingJob": result["gradingJob"].to_dict(),
            "operationAuditEvent": result["operationAuditEvent"].to_dict(),
        },
        trace_id,
    )


def run_grading_job_request(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    repository, repository_policy = resolve_grading_repository(payload, use_backend_default=True)
    service = BackendGradingJobService(
        root=ROOT,
        store=store,
        repository=repository,
        repository_policy=GradingRepositoryPolicy.from_dict(repository_policy),
    )
    try:
        result = service.run_job(payload, trace_id=trace_id)
    except BackendGradingJobServiceError as exc:
        response = fail(exc.code, exc.message, exc.errors, trace_id)
        if hasattr(exc, "provider_error_context"):
            response["providerErrorContext"] = exc.provider_error_context
        if hasattr(exc, "data"):
            response["data"] = exc.data
        return response
    message = (
        "Grading 本地 SQLite worker 单次运行完成"
        if repository
        else "Grading 评分任务已执行，评分记录等待人工复核"
    )
    return ok(message, result, trace_id)

def create_grading_repository(payload: dict[str, Any]) -> GradingSQLiteRepository:
    repository, _policy = resolve_grading_repository(payload, use_backend_default=True, fallback_to_builtin=True)
    if repository is None:
        return GradingSQLiteRepository(resolve_local_path(DEFAULT_GRADING_DB_PATH))
    return repository


def resolve_grading_repository(
    payload: dict[str, Any],
    *,
    use_backend_default: bool = False,
    fallback_to_builtin: bool = False,
) -> tuple[GradingSQLiteRepository | None, dict[str, Any]]:
    db_path = str(payload.get("dbPath") or "").strip()
    db_path_source = GRADING_DB_PATH_SOURCE_REQUEST if db_path else GRADING_DB_PATH_SOURCE_JSON_STORE
    backend_default = str(os.environ.get(BACKEND_DEFAULT_GRADING_DB_ENV) or "").strip()
    backend_default_enabled = bool(backend_default) and use_backend_default
    if not db_path and backend_default_enabled:
        db_path = backend_default
        db_path_source = GRADING_DB_PATH_SOURCE_BACKEND_DEFAULT
    if not db_path and fallback_to_builtin:
        db_path = DEFAULT_GRADING_DB_PATH
        db_path_source = GRADING_DB_PATH_SOURCE_BUILTIN
    policy = {
        "dbPath": db_path or None,
        "dbPathSource": db_path_source,
        "backendDefaultSqliteEnabled": backend_default_enabled,
        "backendDefaultEnv": BACKEND_DEFAULT_GRADING_DB_ENV,
        "builtinDefaultDbPath": DEFAULT_GRADING_DB_PATH,
    }
    if not db_path:
        return None, policy
    return GradingSQLiteRepository(resolve_local_path(db_path)), policy


def read_grading_records_for_platform_readiness(
    query: dict[str, str],
    *,
    source_task_id: str | None,
) -> tuple[list[GradingRecord] | None, dict[str, Any] | None]:
    grading_db_path = str(query.get("gradingDbPath") or "").strip()
    if not grading_db_path:
        return None, None
    repository, policy = resolve_grading_repository({"dbPath": grading_db_path}, use_backend_default=False)
    if repository is None:
        return [], {
            "mode": "LOCAL_SQLITE_GRADING_RECORD_READINESS_BRIDGE",
            "configured": False,
            "dbPath": None,
            "dbPathSource": policy["dbPathSource"],
            "recordTotal": 0,
        }
    if not repository.db_path.exists():
        return [], {
            "mode": "LOCAL_SQLITE_GRADING_RECORD_READINESS_BRIDGE",
            "configured": True,
            "available": False,
            "reason": "grading sqlite file does not exist",
            "dbPath": str(repository.db_path),
            "dbPathSource": policy["dbPathSource"],
            "sourceTaskId": source_task_id,
            "recordTotal": 0,
            "localSqliteRead": False,
            "databaseWritten": False,
            "productionDatabaseWritten": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        }
    records = repository.list_grading_records(task_id=source_task_id)
    return records, {
        "mode": "LOCAL_SQLITE_GRADING_RECORD_READINESS_BRIDGE",
        "configured": True,
        "available": True,
        "dbPath": str(repository.db_path),
        "dbPathSource": policy["dbPathSource"],
        "sourceTaskId": source_task_id,
        "recordTotal": len(records),
        "localSqliteRead": True,
        "databaseWritten": False,
        "productionDatabaseWritten": False,
        "autoPublishAllowed": False,
        "realPublish": False,
    }


def review_detail_grading_records_override(
    query: dict[str, str],
    *,
    task_id: str,
) -> tuple[list[GradingRecord] | None, str]:
    """Use the requested local grading SQLite file when it is available.

    Review detail remains readable from JsonTaskStore if a caller provides an
    unavailable local file. This avoids a stale URL context hiding otherwise
    valid local review evidence.
    """
    records, source = read_grading_records_for_platform_readiness(query, source_task_id=task_id)
    if source and source.get("available") is True:
        return records or [], "LOCAL_SQLITE_GRADING_RECORDS"
    return None, "JsonTaskStore.gradingRecords"


def _uses_grading_sqlite_payload(payload: dict[str, Any]) -> bool:
    repository, _policy = resolve_grading_repository(payload, use_backend_default=True)
    return repository is not None


def _save_grading_job_to_sqlite_mode(
    *,
    repository: GradingSQLiteRepository,
    store: JsonTaskStore,
    job: Any,
) -> Any:
    job.safety = {
        **job.safety,
        "localSqliteWritten": True,
        "localSqliteOnly": True,
        "databaseWritten": False,
        "productionDatabaseWritten": False,
        "queuePersistedToProduction": False,
        "autoApproveAllowed": False,
        "realPublish": False,
    }
    repository.save_grading_job(job)
    store.save_grading_job(job)
    return job


def initialize_grading_repository_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    repository = create_grading_repository(payload)
    try:
        summary = repository.initialize_schema()
    except GradingRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    event = create_operation_audit_event(
        action=OperationAction.GRADING_REPOSITORY_INIT,
        resource_type=OperationResourceType.GRADING_REPOSITORY,
        resource_id=str(repository.db_path),
        actor=str(payload.get("actor") or "backend-mock"),
        trace_id=trace_id,
        after_state="INITIALIZED",
        detail={
            "component": "GradingSQLiteRepositoryInit",
            "dbPath": str(repository.db_path),
            "schemaVersion": summary["schemaVersion"],
            "tables": summary["tables"],
            "localSqliteOnly": True,
            "productionDatabaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    )
    store.save_operation_audit_event(event)
    return ok(
        "Grading 本地 SQLite 仓储已初始化",
        {
            "gradingRepository": summary,
            "operationAuditEvent": event.to_dict(),
            "mode": "LOCAL_SQLITE_GRADING_REPOSITORY",
            "productionDatabaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def sync_grading_repository_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    repository = create_grading_repository(payload)
    try:
        result = sync_grading_repository_from_store(repository=repository, store=store)
    except GradingRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    event = create_operation_audit_event(
        action=OperationAction.GRADING_REPOSITORY_SYNC_LOCAL,
        resource_type=OperationResourceType.GRADING_REPOSITORY,
        resource_id=str(repository.db_path),
        actor=str(payload.get("actor") or "backend-mock"),
        trace_id=trace_id,
        after_state="SYNCED",
        detail={
            "component": "GradingSQLiteRepositorySyncLocal",
            "dbPath": str(repository.db_path),
            "jobsSynced": result["jobsSynced"],
            "recordsSynced": result["recordsSynced"],
            "localSqliteOnly": True,
            "productionDatabaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    )
    store.save_operation_audit_event(event)
    return ok(
        "Grading 本地 JSON store 已同步到 SQLite 仓储",
        {
            "gradingRepositorySync": result,
            "operationAuditEvent": event.to_dict(),
            "mode": "LOCAL_JSON_STORE_TO_SQLITE_SYNC",
            "productionDatabaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def run_grading_worker_once_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    repository = create_grading_repository(payload)
    lease_seconds, lease_error = _optional_positive_int(payload, "leaseSeconds", DEFAULT_CLAIM_LEASE_SECONDS)
    if lease_error:
        return fail("VALIDATION_ERROR", "参数错误", [lease_error], trace_id)
    max_attempts, max_attempts_error = _optional_positive_int(payload, "maxAttempts", DEFAULT_MAX_ATTEMPTS)
    if max_attempts_error:
        return fail("VALIDATION_ERROR", "参数错误", [max_attempts_error], trace_id)
    try:
        result = run_next_grading_job_once(
            repository=repository,
            store=store,
            root=ROOT,
            trace_id=trace_id,
            actor=str(payload.get("actor") or "backend-grading-worker"),
            job_id=str(payload.get("jobId") or "").strip() or None,
            lease_seconds=lease_seconds,
            max_attempts=max_attempts,
        )
    except GradingWorkerError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("Grading 本地 SQLite worker 单次运行完成", result, trace_id)


def drain_grading_worker_once_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    repository = create_grading_repository(payload)
    limit, limit_error = _optional_positive_int(payload, "limit", DEFAULT_WORKER_DRAIN_LIMIT)
    if limit_error:
        return fail("VALIDATION_ERROR", "参数错误", [limit_error], trace_id)
    if limit > MAX_WORKER_DRAIN_LIMIT:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "limit", "reason": f"必须小于等于 {MAX_WORKER_DRAIN_LIMIT}"}],
            trace_id,
        )
    lease_seconds, lease_error = _optional_positive_int(payload, "leaseSeconds", DEFAULT_CLAIM_LEASE_SECONDS)
    if lease_error:
        return fail("VALIDATION_ERROR", "参数错误", [lease_error], trace_id)
    max_attempts, max_attempts_error = _optional_positive_int(payload, "maxAttempts", DEFAULT_MAX_ATTEMPTS)
    if max_attempts_error:
        return fail("VALIDATION_ERROR", "参数错误", [max_attempts_error], trace_id)
    result = drain_grading_jobs_once(
        repository=repository,
        store=store,
        root=ROOT,
        trace_id=trace_id,
        actor=str(payload.get("actor") or "backend-grading-worker"),
        limit=limit,
        lease_seconds=lease_seconds,
        max_attempts=max_attempts,
    )
    return ok("Grading 本地 SQLite worker 有限批次运行完成", result, trace_id)


def list_grading_job_request(query: dict[str, str], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    repository, repository_policy = resolve_grading_repository(query, use_backend_default=True)
    if repository:
        try:
            jobs = repository.list_grading_jobs(
                task_id=query.get("taskId"),
                submission_id=query.get("submissionId"),
                status=query.get("status"),
                candidate_id=query.get("candidateId"),
            )
        except GradingRepositoryError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok(
            "查询成功",
            {
                "items": [job.to_dict() for job in jobs],
                "total": len(jobs),
                "filters": {
                    "taskId": query.get("taskId"),
                    "submissionId": query.get("submissionId"),
                    "candidateId": query.get("candidateId"),
                    "status": query.get("status"),
                },
                "mode": "LOCAL_SQLITE_GRADING_JOB",
                "dbPath": str(repository.db_path),
                "dbPathSource": repository_policy["dbPathSource"],
                "backendDefaultSqliteEnabled": repository_policy["backendDefaultSqliteEnabled"],
                "localSqliteRead": True,
                "databaseWritten": False,
                "productionDatabaseWritten": False,
                "realPublish": False,
            },
            trace_id,
        )
    jobs = store.list_grading_jobs(
        task_id=query.get("taskId"),
        submission_id=query.get("submissionId"),
        status=query.get("status"),
        candidate_id=query.get("candidateId"),
    )
    return ok(
        "查询成功",
        {
            "items": [job.to_dict() for job in jobs],
            "total": len(jobs),
            "filters": {
                "taskId": query.get("taskId"),
                "submissionId": query.get("submissionId"),
                "candidateId": query.get("candidateId"),
                "status": query.get("status"),
            },
            "mode": "LOCAL_GRADING_JOB",
            "databaseWritten": False,
            "realPublish": False,
        },
        trace_id,
    )


def get_grading_job_request(
    job_id: str,
    store: JsonTaskStore,
    trace_id: str,
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    query = query or {}
    repository, repository_policy = resolve_grading_repository(query, use_backend_default=True)
    if repository:
        try:
            job = repository.get_grading_job(job_id)
        except GradingRepositoryError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        if job is None:
            return fail("NOT_FOUND", "Grading 评分任务不存在", [{"field": "id", "reason": "未找到任务"}], trace_id)
        return ok(
            "查询成功",
            {
                "gradingJob": job.to_dict(),
                "mode": "LOCAL_SQLITE_GRADING_JOB",
                "dbPath": str(repository.db_path),
                "dbPathSource": repository_policy["dbPathSource"],
                "backendDefaultSqliteEnabled": repository_policy["backendDefaultSqliteEnabled"],
                "localSqliteRead": True,
                "databaseWritten": False,
                "productionDatabaseWritten": False,
                "realPublish": False,
            },
            trace_id,
        )
    job = store.get_grading_job(job_id)
    if job is None:
        return fail("NOT_FOUND", "Grading 评分任务不存在", [{"field": "id", "reason": "未找到任务"}], trace_id)
    return ok(
        "查询成功",
        {
            "gradingJob": job.to_dict(),
            "mode": "LOCAL_GRADING_JOB",
            "databaseWritten": False,
            "realPublish": False,
        },
        trace_id,
    )


def review_grading_record_request(
    record_id: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    repository, repository_policy = resolve_grading_repository(payload, use_backend_default=True)
    service = BackendGradingRecordService(
        root=ROOT,
        store=store,
        repository=repository,
        repository_policy=GradingRepositoryPolicy.from_dict(repository_policy),
    )
    try:
        result = service.review_record(record_id, payload, trace_id=trace_id)
    except BackendGradingRecordServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok(
        "Grading 评分记录复核意见已记录",
        {
            **{key: value for key, value in result.items() if key not in {"gradingRecord", "operationAuditEvent"}},
            "gradingRecord": result["gradingRecord"].to_dict(),
            "operationAuditEvent": result["operationAuditEvent"].to_dict(),
        },
        trace_id,
    )


def read_real_dsl_review_preview(query: dict[str, str], trace_id: str) -> dict[str, Any]:
    try:
        preview = build_real_dsl_review_preview_from_files(
            lab_path=resolve_local_path(query.get("lab", "examples/output/real-llm-lab.json")),
            exam_path=resolve_local_path(query.get("exam", "examples/output/real-llm-exam.json")),
            grading_path=resolve_local_path(query.get("grading", "examples/output/real-llm-grading.json")),
            ppt_path=resolve_local_path(query.get("ppt", "examples/output/real-llm-ppt.json")),
            candidate_preview_path=resolve_local_path(
                query.get("candidatePreview", "examples/output/real-llm-demo-candidate-preview.json")
            ),
            root=ROOT,
            trace_id=trace_id,
        )
    except RealDslReviewPreviewError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok(
        "查询成功",
        {
            "realDslReviewPreview": preview,
            "mode": "STATIC_REAL_LLM_DSL_REVIEW_PREVIEW",
            "safety": {
                "newLlmRequestSent": False,
                "secretsRead": False,
                "networkAccess": False,
                "taskCreated": False,
                "artifactCreated": False,
                "answerVisibleToCandidate": False,
                "gradingRefVisibleToCandidate": False,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
            },
        },
        trace_id,
    )


def create_real_dsl_revision_request(payload: dict[str, Any], trace_id: str) -> dict[str, Any]:
    kind = str(payload.get("kind", "")).strip().lower()
    if not kind:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "kind", "reason": "缺少参数"}], trace_id)
    source = str(payload.get("source") or REAL_DSL_REVISION_DEFAULT_SOURCE_BY_KIND.get(kind, ""))
    output = str(payload.get("output") or REAL_DSL_REVISION_DEFAULT_OUTPUT_BY_KIND.get(kind, ""))
    report_output = str(payload.get("reportOutput") or REAL_DSL_REVISION_DEFAULT_REPORT_BY_KIND.get(kind, ""))
    try:
        timeout_seconds = int(payload["timeoutSeconds"]) if payload.get("timeoutSeconds") is not None else 60
        max_output_tokens = int(payload["maxOutputTokens"]) if payload.get("maxOutputTokens") is not None else 2200
    except (TypeError, ValueError):
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "timeoutSeconds/maxOutputTokens", "reason": "必须是整数"}], trace_id)
    try:
        result = create_real_dsl_revision_draft(
            kind=kind,
            source_path=resolve_local_path(source),
            reviewer=str(payload.get("reviewer", "")),
            comment=str(payload.get("comment", "")),
            target_sections=payload.get("targetSections") if isinstance(payload.get("targetSections"), list) else [],
            requested_changes=payload.get("requestedChanges") if isinstance(payload.get("requestedChanges"), list) else [],
            output_path=resolve_local_path(output),
            report_output_path=resolve_local_path(report_output),
            provider_mode=str(payload.get("providerMode") or REAL_DSL_REVISION_PROVIDER_MODE_LOCAL),
            model=payload.get("model") if isinstance(payload.get("model"), str) else None,
            base_url=payload.get("baseUrl") if isinstance(payload.get("baseUrl"), str) else None,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=payload.get("explicitRealCallOptIn") is True,
            confirm_waiting_review=payload.get("confirmWaitingReview") is True,
            confirm_no_auto_publish=payload.get("confirmNoAutoPublish") is True,
            root=ROOT,
            trace_id=trace_id,
        )
    except ProviderError as exc:
        return provider_fail(exc, trace_id, operation="reviseDsl", provider_id="openai")
    except RealDslRevisionError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("真实 DSL 修订草稿已生成，等待人工审核", result, trace_id)


def create_real_dsl_revision_batch_request(payload: dict[str, Any], trace_id: str) -> dict[str, Any]:
    preview = str(payload.get("preview") or "examples/output/real-llm-demo-real-dsl-review-preview.json")
    output_dir = str(payload.get("outputDir") or "examples/output")
    report_output = str(payload.get("reportOutput") or REAL_DSL_REVISION_DEFAULT_BATCH_REPORT_PATH)
    try:
        result = create_real_dsl_revision_batch_from_preview(
            preview_path=resolve_local_path(preview),
            reviewer=str(payload.get("reviewer", "")),
            output_dir=resolve_local_path(output_dir),
            report_output_path=resolve_local_path(report_output),
            root=ROOT,
            trace_id=trace_id,
        )
    except RealDslRevisionError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("真实 DSL 批量修订草稿已生成，等待人工审核", result, trace_id)


def get_real_dsl_revision_diff_preview_request(query: dict[str, str], trace_id: str) -> dict[str, Any]:
    batch_report = str(query.get("batchReport") or REAL_DSL_REVISION_DEFAULT_BATCH_REPORT_PATH)
    output = query.get("output")
    try:
        result = build_real_dsl_revision_diff_preview(
            batch_report_path=resolve_local_path(batch_report),
            output_path=resolve_local_path(output) if output else None,
            root=ROOT,
            trace_id=trace_id,
        )
    except RealDslRevisionError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("真实 DSL 修订差异预览查询成功", result, trace_id)


def create_real_dsl_revision_decision_request(payload: dict[str, Any], trace_id: str) -> dict[str, Any]:
    diff_preview = str(payload.get("diffPreview") or REAL_DSL_REVISION_DEFAULT_DIFF_PREVIEW_PATH)
    output = str(payload.get("output") or REAL_DSL_REVISION_DEFAULT_DECISION_REPORT_PATH)
    try:
        result = create_real_dsl_revision_decision(
            diff_preview_path=resolve_local_path(diff_preview),
            suggestion_id=str(payload.get("suggestionId", "")),
            reviewer=str(payload.get("reviewer", "")),
            decision=str(payload.get("decision", "")),
            reason=payload.get("reason") if isinstance(payload.get("reason"), str) else None,
            output_path=resolve_local_path(output) if output else None,
            root=ROOT,
            trace_id=trace_id,
        )
    except RealDslRevisionError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("真实 DSL 修订审核决策已记录", result, trace_id)


def promote_real_dsl_revision_request(payload: dict[str, Any], trace_id: str) -> dict[str, Any]:
    decision_report = str(payload.get("decisionReport") or REAL_DSL_REVISION_DEFAULT_DECISION_REPORT_PATH)
    output = str(payload.get("output") or REAL_DSL_REVISION_DEFAULT_PROMOTION_OUTPUT_PATH)
    report_output = str(payload.get("reportOutput") or REAL_DSL_REVISION_DEFAULT_PROMOTION_REPORT_PATH)
    try:
        result = promote_real_dsl_revision_candidate(
            decision_report_path=resolve_local_path(decision_report),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output) if output else None,
            report_output_path=resolve_local_path(report_output) if report_output else None,
            root=ROOT,
            trace_id=trace_id,
        )
    except RealDslRevisionError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("真实 DSL 修订候选版已生成，等待人工审核", result, trace_id)


def enqueue_real_dsl_revision_request(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    promotion_report = str(payload.get("promotionReport") or REAL_DSL_REVISION_DEFAULT_PROMOTION_REPORT_PATH)
    try:
        result = enqueue_promoted_revision_for_review(
            store,
            promotion_report_path=resolve_local_path(promotion_report),
            reviewer=str(payload.get("reviewer", "")),
            trace_id=trace_id,
        )
    except PromotionReviewEnqueueError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("真实 DSL 修订候选版已进入审核队列", result, trace_id)


def create_lab_template_import_preview_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_LAB_TEMPLATE_IMPORT_PREVIEW_PATH)
    try:
        result = create_lab_template_import_preview(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_platform_import_preview_core_write(payload, result)
    except (LabTemplateImportPreviewError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("Lab 模板导入预览已生成", result, trace_id)


def create_lab_template_mock_import_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_LAB_TEMPLATE_MOCK_IMPORT_PATH)
    try:
        result = create_lab_template_mock_import(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_agent_entity_mock_import_core_write(payload, result)
    except (AgentEntityMockImportError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("Lab 模板已写入本地 Mock 平台实体", result, trace_id)


def create_exam_question_import_preview_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_EXAM_QUESTION_IMPORT_PREVIEW_PATH)
    try:
        result = create_exam_question_import_preview(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_platform_import_preview_core_write(payload, result)
    except (AgentImportPreviewError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("Exam 试题导入预览已生成", result, trace_id)


def create_exam_question_mock_import_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_EXAM_QUESTION_MOCK_IMPORT_PATH)
    try:
        result = create_exam_question_mock_import(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_agent_entity_mock_import_core_write(payload, result)
    except (AgentEntityMockImportError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("Exam 试题已写入本地 Mock 平台实体", result, trace_id)


def create_grading_rule_import_preview_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_GRADING_RULE_IMPORT_PREVIEW_PATH)
    try:
        result = create_grading_rule_import_preview(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_platform_import_preview_core_write(payload, result)
    except (AgentImportPreviewError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("Grading 评分规则导入预览已生成", result, trace_id)


def create_grading_rule_mock_import_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_GRADING_RULE_MOCK_IMPORT_PATH)
    try:
        result = create_grading_rule_mock_import(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_agent_entity_mock_import_core_write(payload, result)
    except (AgentEntityMockImportError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("Grading 评分规则已写入本地 Mock 平台实体", result, trace_id)


def create_ppt_deck_import_preview_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_PPT_DECK_IMPORT_PREVIEW_PATH)
    try:
        result = create_ppt_deck_import_preview(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_platform_import_preview_core_write(payload, result)
    except (AgentImportPreviewError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("PPT 课件导入预览已生成", result, trace_id)


def create_ppt_deck_mock_import_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    output = str(payload.get("output") or DEFAULT_PPT_DECK_MOCK_IMPORT_PATH)
    try:
        result = create_ppt_deck_mock_import(
            store,
            task_id=str(payload.get("taskId", "")),
            reviewer=str(payload.get("reviewer", "")),
            output_path=resolve_local_path(output),
            trace_id=trace_id,
        )
        attach_agent_entity_mock_import_core_write(payload, result)
    except (AgentEntityMockImportError, CoreRepositoryError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("PPT 课件已写入本地 Mock 平台实体", result, trace_id)


def build_agent_entity_publish_preview_request(
    entity_id: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    service = BackendAgentEntityService(store=store, root=ROOT, core_service=CORE_SERVICE)
    try:
        core_repository, core_write = prepare_backend_core_write_through(payload)
        if core_repository is not None:
            result = service.build_publish_preview_from_repository(
                entity_id,
                payload,
                trace_id=trace_id,
                repository=core_repository,
                write_summary=core_write,
            )
        else:
            result = service.build_publish_preview(entity_id, payload, trace_id=trace_id)
    except BackendAgentEntityServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    except CoreRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("平台实体真实导入 Dry-run Payload 已生成，未发送请求", result, trace_id)


def validate_agent_entity_contract_config_request(
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    service = BackendAgentEntityService(store=store, root=ROOT)
    try:
        result = service.validate_agent_entity_schema(payload)
    except BackendAgentEntityServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("平台 API 契约配置已通过本地校验", result, trace_id)


def agent_internal_publish_request(
    entity_id: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    service = BackendAgentEntityService(store=store, root=ROOT)
    try:
        result = service.publish_entity(entity_id, payload, trace_id=trace_id)
    except BackendAgentEntityServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("平台实体真实导入请求已发送，结果等待人工确认", result, trace_id)


def record_agent_entity_publish_result_request(
    entity_id: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    service = BackendAgentEntityService(store=store, root=ROOT, core_service=CORE_SERVICE)
    try:
        core_repository, core_write = prepare_backend_core_write_through(payload)
        if core_repository is not None:
            result = service.record_publish_result_from_repository(
                entity_id,
                payload,
                trace_id=trace_id,
                repository=core_repository,
                write_summary=core_write,
            )
        else:
            result = service.record_publish_result(entity_id, payload, trace_id=trace_id)
    except BackendAgentEntityServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    except CoreRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("平台实体导入平台侧结果已登记，等待后续人工发布流程", result, trace_id)


def record_agent_entity_signoff_request(
    entity_id: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    service = BackendAgentEntityService(store=store, root=ROOT, core_service=CORE_SERVICE)
    try:
        core_repository, core_write = prepare_backend_core_write_through(payload)
        if core_repository is not None:
            result = service.record_signoff_from_repository(
                entity_id,
                payload,
                trace_id=trace_id,
                repository=core_repository,
                write_summary=core_write,
            )
        else:
            result = service.record_signoff(entity_id, payload, trace_id=trace_id)
    except BackendAgentEntityServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    except CoreRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("平台实体人工签收记录已生成，仍未发布", result, trace_id)


def record_agent_entity_final_publish_review_decision_request(
    entity_id: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    service = BackendAgentEntityService(store=store, root=ROOT, core_service=CORE_SERVICE)
    try:
        core_repository, core_write = prepare_backend_core_write_through(payload)
        if core_repository is not None:
            result = service.record_final_publish_review_decision_from_repository(
                entity_id,
                payload,
                trace_id=trace_id,
                repository=core_repository,
                write_summary=core_write,
            )
        else:
            result = service.record_final_publish_review_decision(entity_id, payload, trace_id=trace_id)
    except BackendAgentEntityServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    except CoreRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("平台实体最终人工复核结论已记录，仍未发布", result, trace_id)


def query_agent_publish_status_request(
    entity_id: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    service = BackendAgentEntityService(store=store, root=ROOT)
    try:
        result = service.query_publish_status(entity_id, payload, trace_id=trace_id)
    except BackendAgentEntityServiceError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    return ok("平台实体真实导入状态已查询，结果需人工登记确认", result, trace_id)


def resolve_local_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def validate_yaml_dsl(kind: str, path: Path, trace_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        document = load_yaml(path)
        validate_dsl(document, load_schema(kind, ROOT))
    except DslValidationError as exc:
        return None, fail("SCHEMA_VALIDATION_ERROR", "DSL Schema 校验失败", exc.errors, trace_id)
    if not isinstance(document, dict):
        return None, fail("SCHEMA_VALIDATION_ERROR", "DSL Schema 校验失败", [{"field": "$", "reason": "root must be object"}], trace_id)
    return document, None


def parse_review_action(path: str) -> tuple[str, str] | None:
    if not path.startswith("/api/ai-tasks/"):
        return None
    parts = path.removeprefix("/api/ai-tasks/").split("/")
    if len(parts) != 2 or parts[1] not in {"approve", "reject"}:
        return None
    return parts[0], parts[1]


def parse_environment_action(path: str) -> tuple[str, str] | None:
    if not path.startswith("/api/environments/"):
        return None
    parts = path.removeprefix("/api/environments/").split("/")
    if len(parts) != 2 or parts[1] not in {"start", "stop", "reset"}:
        return None
    return parts[0], parts[1]


def parse_environment_create(path: str) -> EnvironmentType | None:
    if path == "/api/environments/vm":
        return EnvironmentType.VM
    if path == "/api/environments/notebook":
        return EnvironmentType.NOTEBOOK
    return None


def parse_provider_health(path: str) -> str | None:
    if not path.startswith("/api/providers/") or not path.endswith("/health"):
        return None
    parts = path.removeprefix("/api/providers/").split("/")
    if len(parts) != 2 or parts[1] != "health":
        return None
    return parts[0]


def parse_provider_generate(path: str) -> str | None:
    if not path.startswith("/api/providers/") or not path.endswith("/generate"):
        return None
    parts = path.removeprefix("/api/providers/").split("/")
    if len(parts) != 2 or parts[1] != "generate":
        return None
    return parts[0]


def provider_fail(
    exc: ProviderError,
    trace_id: str,
    *,
    operation: str | None = None,
    provider_id: str | None = None,
) -> dict[str, Any]:
    payload = fail(exc.code, exc.message, exc.errors, trace_id)
    payload["providerErrorContext"] = build_provider_error_context(
        exc,
        operation=operation,
        provider_id=provider_id,
    )
    return payload


def provider_error_response(exc: ProviderError, trace_id: str, provider_id: str = "mock") -> dict[str, Any]:
    payload = fail(exc.code, exc.message, exc.errors, trace_id)
    if provider_id == "openai" and exc.code.startswith("REAL_LLM_"):
        payload["providerErrorContext"] = {
            "adapterId": "openai_responses_sdk_adapter",
            "interfaceName": "LLMProvider",
            "operation": "generateJson",
            "providerId": provider_id,
            "mode": "REAL_LLM",
            "errorCode": exc.code,
            "generatedContentCreated": False,
            "taskCreated": False,
            "reviewBypassed": False,
            "realLlmCalled": exc.code not in {
                "REAL_LLM_DEMO_DSL_CONFIRMATION_REQUIRED",
                "REAL_LLM_DEMO_DSL_SECRET_REQUIRED",
                "REAL_LLM_DEMO_DSL_MODEL_REQUIRED",
                "REAL_LLM_DEMO_DSL_SDK_IMPORT_FAILED",
                "REAL_LLM_DEMO_DSL_CLIENT_CREATE_FAILED",
                "REAL_LLM_MINIMAL_CALL_CONFIRMATION_REQUIRED",
                "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED",
                "REAL_LLM_MINIMAL_CALL_MODEL_REQUIRED",
                "REAL_LLM_MINIMAL_CALL_SDK_IMPORT_FAILED",
                "REAL_LLM_MINIMAL_CALL_CLIENT_CREATE_FAILED",
            },
            "secretsRead": True,
            "networkAccess": True,
            "autoPublishAllowed": False,
            "realPublish": False,
        }
        return payload
    payload["providerErrorContext"] = build_provider_error_context(
        exc,
        operation="generateJson",
        provider_id=provider_id,
    )
    return payload


def provider_error_field(exc: ProviderError) -> str | None:
    if not exc.errors:
        return None
    return exc.errors[0].get("field")


def save_provider_call_audit(
    store: JsonTaskStore,
    *,
    operation: str,
    provider_id: str,
    status: ProviderCallStatus,
    actor: str,
    trace_id: str,
    prompt_id: str | None = None,
    output_kind: str | None = None,
    input_ref: str | None = None,
    error_code: str | None = None,
    error_field: str | None = None,
    error_message: str | None = None,
    result: dict[str, Any] | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = create_provider_call_audit_event(
        operation=operation,
        provider_id=provider_id,
        status=status,
        actor=actor,
        trace_id=trace_id,
        prompt_id=prompt_id,
        output_kind=output_kind,
        input_ref=input_ref,
        error_code=error_code,
        error_field=error_field,
        error_message=error_message,
        result=result,
        detail=detail,
    )
    store.save_provider_call_audit_event(event)
    return event.to_dict()


def save_provider_generation_audit(
    store: JsonTaskStore,
    *,
    generation: dict[str, Any],
    actor: str,
    trace_id: str,
    workflow_id: str | None = None,
    workflow_step: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    provider = generation["provider"]
    quality_summary = generation.get("qualitySummary")
    if not isinstance(quality_summary, dict) and provider.get("realLlmCalled") is True:
        quality_summary = _build_generation_quality_summary(str(generation.get("kind") or ""), generation)
    audit_event = save_provider_call_audit(
        store,
        operation=provider.get("operation", "generateJson"),
        provider_id=provider.get("providerId", "mock"),
        status=ProviderCallStatus.SUCCESS,
        actor=actor,
        trace_id=trace_id,
        prompt_id=generation.get("promptId"),
        output_kind=generation.get("outputKind"),
        input_ref=generation.get("inputRef"),
        result=generation,
        detail={
            "source": "workflow_adapter",
            "kind": generation.get("kind"),
            "workflowId": workflow_id,
            "workflowStep": workflow_step,
            "taskId": task_id,
            "providerId": provider.get("providerId"),
            "providerAdapter": provider.get("adapterId"),
            "model": provider.get("model"),
            "promptId": generation.get("promptId"),
            "outputKind": generation.get("outputKind"),
            "dslId": generation.get("dslId"),
            "dslPath": generation.get("dslPath"),
            "responseId": generation.get("responseId") or provider.get("responseId"),
            "usage": generation.get("usage"),
            "apiSurface": generation.get("apiSurface") or provider.get("apiSurface"),
            "normalization": generation.get("normalization"),
            "qualitySummary": quality_summary if isinstance(quality_summary, dict) else None,
            "contentQualitySummary": generation.get("contentQualitySummary"),
            "reviewRequired": generation.get("reviewRequired"),
            "publishBlockedUntilApproved": generation.get("publishBlockedUntilApproved"),
            "providerMode": provider.get("mode"),
            "requestCount": provider.get("requestCount"),
            "singleRequestOnly": provider.get("singleRequestOnly"),
        },
    )
    if isinstance(quality_summary, dict):
        generation["qualitySummary"] = quality_summary
    generation["providerCallAuditEvent"] = audit_event
    generation["provider"]["providerCallAuditEventId"] = audit_event["id"]
    return audit_event


def save_provider_bundle_audits(
    store: JsonTaskStore,
    *,
    bundle: dict[str, dict[str, Any]],
    actor: str,
    trace_id: str,
    workflow_id: str | None = None,
    step_names: dict[str, str] | None = None,
    task_ids: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    audit_events: dict[str, dict[str, Any]] = {}
    for kind, generation in bundle.items():
        audit_events[kind] = save_provider_generation_audit(
            store,
            generation=generation,
            actor=actor,
            trace_id=trace_id,
            workflow_id=workflow_id,
            workflow_step=(step_names or {}).get(kind),
            task_id=(task_ids or {}).get(kind),
        )
    return audit_events


def material_fail(exc: MaterialAnalysisError, trace_id: str) -> dict[str, Any]:
    return fail(exc.code, exc.message, exc.errors, trace_id)


def workflow_registry_fail(exc: WorkflowRegistryError, trace_id: str) -> dict[str, Any]:
    return fail(exc.code, exc.message, exc.errors, trace_id)


def workflow_registry_list_request(query: dict[str, str], trace_id: str) -> dict[str, Any]:
    try:
        registry = list_phase2_workflows(root=ROOT, category=query.get("category"))
    except WorkflowRegistryError as exc:
        return workflow_registry_fail(exc, trace_id)
    return ok("Phase 2 Workflow Registry 查询成功", registry, trace_id)


def workflow_registry_get_request(workflow_id: str, trace_id: str) -> dict[str, Any]:
    try:
        workflow = get_phase2_workflow(workflow_id, root=ROOT)
    except WorkflowRegistryError as exc:
        return workflow_registry_fail(exc, trace_id)
    return ok("Phase 2 Workflow Registry 详情读取成功", workflow, trace_id)


def material_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": analysis["title"],
        "fileType": analysis["fileType"],
        "riskCount": analysis["riskCount"],
        "unknownShellExecuted": analysis["unknownShellExecuted"],
        "requiresHumanReview": analysis["requiresHumanReview"],
    }


def save_artifact(
    store: JsonTaskStore,
    *,
    kind: ArtifactKind,
    path: str,
    title: str,
    status: ArtifactStatus,
    trace_id: str,
    task_id: str | None = None,
    workflow_run_id: str | None = None,
    source_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    sandbox_executed: bool = False,
    contestant_code_executed: bool = False,
) -> dict[str, Any]:
    artifact = create_artifact_record(
        kind=kind,
        path=path,
        title=title,
        status=status,
        trace_id=trace_id,
        task_id=task_id,
        workflow_run_id=workflow_run_id,
        source_ref=source_ref,
        metadata=metadata,
        sandbox_executed=sandbox_executed,
        contestant_code_executed=contestant_code_executed,
    )
    store.save_artifact(artifact)
    return artifact.to_dict()


def create_phase2_review_tasks(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    input_ref: str,
    trace_id: str,
) -> dict[str, Any]:
    generated = report["generatedDsl"]
    task_specs = {
        "lab": ("LAB_GENERATION", "Phase 2 Mock Lab DSL generation", "markdown", input_ref, generated["lab"]["dslPath"]),
        "exam": ("EXAM_GENERATION", "Phase 2 Mock Exam DSL generation", "lab_dsl", generated["lab"]["dslId"], generated["exam"]["dslPath"]),
        "grading": (
            "GRADING_GENERATION",
            "Phase 2 Mock Grading DSL generation",
            "exam_dsl",
            generated["exam"]["dslId"],
            generated["grading"]["dslPath"],
        ),
    }
    if "ppt" in generated:
        task_specs["ppt"] = (
            "PPT_GENERATION",
            "Phase 2 Mock PPT DSL generation",
            "markdown",
            input_ref,
            generated["ppt"]["dslPath"],
        )
    tasks = {}
    for kind, (task_type, title, input_type, source_ref, final_result_path) in task_specs.items():
        task = store.save(
            create_waiting_review_task(
                task_type=task_type,
                title=title,
                input_type=input_type,
                input_ref=source_ref,
                final_result_path=final_result_path,
                trace_id=trace_id,
            )
        )
        tasks[kind] = task
    return tasks


def link_phase2_tasks(report: dict[str, Any], tasks: dict[str, Any]) -> None:
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in tasks:
            step["taskId"] = tasks[kind].id
            report["generatedDsl"][kind]["taskId"] = tasks[kind].id


def save_phase2_artifacts(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    input_path: Path,
    tasks: dict[str, Any],
    trace_id: str,
) -> list[dict[str, Any]]:
    generated = report["generatedDsl"]
    content_quality_summary = report.get("contentQualitySummary", {})
    content_quality_items = (
        content_quality_summary.get("items", {})
        if isinstance(content_quality_summary, dict) and isinstance(content_quality_summary.get("items"), dict)
        else {}
    )
    material_step = next((step for step in report["steps"] if step["name"] == "analyze_material"), {})
    material_analysis = material_step.get("materialAnalysis", {})
    return [
        save_artifact(
            store,
            kind=ArtifactKind.MATERIAL_ANALYSIS,
            path=str(input_path),
            title=str(material_analysis.get("title") or "Phase 2 Mock Source Material"),
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(input_path),
            metadata={
                "fileType": material_analysis.get("fileType"),
                "riskCount": material_analysis.get("riskCount", 0),
                "unknownShellExecuted": material_analysis.get("unknownShellExecuted", False),
                "workflowId": PHASE2_WORKFLOW_ID,
                "artifactProfile": report.get("artifactProfile", ARTIFACT_PROFILE_LEGACY_ALL),
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.LAB_DSL,
            path=generated["lab"]["dslPath"],
            title="Phase 2 Mock Lab DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=tasks["lab"].id,
            source_ref=str(input_path),
            metadata={
                "dslKind": "Lab",
                "reviewRequired": True,
                "providerAdapter": generated["lab"].get("provider", {}).get("adapterId", "mock_provider_adapter"),
                "workflowId": PHASE2_WORKFLOW_ID,
                "artifactProfile": report.get("artifactProfile", ARTIFACT_PROFILE_LEGACY_ALL),
                "schemaValidated": generated["lab"].get("schemaValidated") is True,
                "contentQualitySummary": content_quality_items.get("lab", {}),
                "workflowContentQualitySummary": content_quality_summary,
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.EXAM_DSL,
            path=generated["exam"]["dslPath"],
            title="Phase 2 Mock Exam DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=tasks["exam"].id,
            source_ref=generated["lab"]["dslId"],
            metadata={
                "dslKind": "Exam",
                "answerVisibleToCandidate": False,
                "providerAdapter": generated["exam"].get("provider", {}).get("adapterId", "mock_provider_adapter"),
                "workflowId": PHASE2_WORKFLOW_ID,
                "artifactProfile": report.get("artifactProfile", ARTIFACT_PROFILE_LEGACY_ALL),
                "schemaValidated": generated["exam"].get("schemaValidated") is True,
                "contentQualitySummary": content_quality_items.get("exam", {}),
                "workflowContentQualitySummary": content_quality_summary,
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.GRADING_DSL,
            path=generated["grading"]["dslPath"],
            title="Phase 2 Mock Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=tasks["grading"].id,
            source_ref=generated["exam"]["dslId"],
            metadata={
                "dslKind": "Grading",
                "reviewRequired": True,
                "providerAdapter": generated["grading"].get("provider", {}).get("adapterId", "mock_provider_adapter"),
                "workflowId": PHASE2_WORKFLOW_ID,
                "artifactProfile": report.get("artifactProfile", ARTIFACT_PROFILE_LEGACY_ALL),
                "schemaValidated": generated["grading"].get("schemaValidated") is True,
                "contentQualitySummary": content_quality_items.get("grading", {}),
                "workflowContentQualitySummary": content_quality_summary,
            },
        ),
        *(
            [
                save_artifact(
                    store,
                    kind=ArtifactKind.PPT_DSL,
                    path=generated["ppt"]["dslPath"],
                    title="Phase 2 Mock PPT DSL",
                    status=ArtifactStatus.WAITING_REVIEW,
                    trace_id=trace_id,
                    task_id=tasks["ppt"].id,
                    source_ref=str(input_path),
                    metadata={
                        "dslKind": "PPT",
                        "artifactGenerated": False,
                        "providerAdapter": generated["ppt"].get("provider", {}).get("adapterId", "mock_provider_adapter"),
                        "workflowId": PHASE2_WORKFLOW_ID,
                        "artifactProfile": report.get("artifactProfile", ARTIFACT_PROFILE_LEGACY_ALL),
                        "schemaValidated": generated["ppt"].get("schemaValidated") is True,
                        "contentQualitySummary": content_quality_items.get("ppt", {}),
                        "workflowContentQualitySummary": content_quality_summary,
                    },
                )
            ]
            if "ppt" in generated
            else []
        ),
        save_artifact(
            store,
            kind=ArtifactKind.WORKFLOW_REPORT,
            path=f"memory://{report['id']}",
            title="Phase 2 Mock Content Generation Report",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(input_path),
            metadata={
                "workflowId": PHASE2_WORKFLOW_ID,
                "reviewRequired": True,
                "artifactProfile": report.get("artifactProfile", ARTIFACT_PROFILE_LEGACY_ALL),
                "contentQualitySummary": content_quality_summary,
            },
        ),
    ]


def create_phase2_exam_tasks(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    trace_id: str,
) -> dict[str, Any]:
    generated = report["generatedDsl"]
    lab_id = str(report["labDslInput"]["labId"])
    task_specs = {
        "exam": ("EXAM_GENERATION", "Phase 2 Mock Exam conversion", "lab_dsl", lab_id, generated["exam"]["dslPath"]),
        "grading": (
            "GRADING_GENERATION",
            "Phase 2 Mock Grading conversion",
            "exam_dsl",
            generated["exam"]["dslId"],
            generated["grading"]["dslPath"],
        ),
    }
    tasks = {}
    for kind, (task_type, title, input_type, source_ref, final_result_path) in task_specs.items():
        task = store.save(
            create_waiting_review_task(
                task_type=task_type,
                title=title,
                input_type=input_type,
                input_ref=source_ref,
                final_result_path=final_result_path,
                trace_id=trace_id,
            )
        )
        tasks[kind] = task
    return tasks


def link_phase2_exam_tasks(report: dict[str, Any], tasks: dict[str, Any]) -> None:
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in tasks:
            step["taskId"] = tasks[kind].id
            report["generatedDsl"][kind]["taskId"] = tasks[kind].id


def save_phase2_exam_artifacts(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    lab_path: Path,
    notebook_path: Path,
    tasks: dict[str, Any],
    trace_id: str,
) -> list[dict[str, Any]]:
    generated = report["generatedDsl"]
    quality_signals = report.get("qualitySignals", {})
    return [
        save_artifact(
            store,
            kind=ArtifactKind.LAB_DSL,
            path=str(lab_path),
            title="Phase 2 Exam Conversion Source Lab DSL",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(lab_path),
            metadata={"workflowId": PHASE2_EXAM_WORKFLOW_ID, "sourceOnly": True},
        ),
        save_artifact(
            store,
            kind=ArtifactKind.MATERIAL_ANALYSIS,
            path=str(notebook_path),
            title="Phase 2 Exam Conversion Notebook Analysis",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(notebook_path),
            metadata={
                "workflowId": PHASE2_EXAM_WORKFLOW_ID,
                "fileType": "ipynb",
                "cellCount": report["notebookInput"]["cellCount"],
                "contestantCodeExecuted": False,
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.EXAM_DSL,
            path=generated["exam"]["dslPath"],
            title="Phase 2 Mock Converted Exam DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=tasks["exam"].id,
            source_ref=str(lab_path),
            metadata={
                "dslKind": "Exam",
                "answerVisibleToCandidate": False,
                "providerAdapter": "mock_provider_adapter",
                "workflowId": PHASE2_EXAM_WORKFLOW_ID,
                "qualitySignals": quality_signals.get("exam", {}),
                "workflowQualitySignals": quality_signals,
                "qualitySignalSummary": quality_signals.get("overall", {}),
                "reviewHighlights": quality_signals.get("reviewHighlights", []),
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.GRADING_DSL,
            path=generated["grading"]["dslPath"],
            title="Phase 2 Mock Converted Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=tasks["grading"].id,
            source_ref=generated["exam"]["dslId"],
            metadata={
                "dslKind": "Grading",
                "sandboxRequiredBeforeRealExecution": True,
                "providerAdapter": "mock_provider_adapter",
                "workflowId": PHASE2_EXAM_WORKFLOW_ID,
                "qualitySignals": quality_signals.get("grading", {}),
                "workflowQualitySignals": quality_signals,
                "qualitySignalSummary": quality_signals.get("overall", {}),
                "reviewHighlights": quality_signals.get("reviewHighlights", []),
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.WORKFLOW_REPORT,
            path=f"memory://{report['id']}",
            title="Phase 2 Mock Exam Conversion Report",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(lab_path),
            metadata={
                "workflowId": PHASE2_EXAM_WORKFLOW_ID,
                "reviewRequired": True,
                "qualitySignalSummary": quality_signals.get("overall", {}),
                "reviewHighlights": quality_signals.get("reviewHighlights", []),
            },
        ),
    ]


def create_phase2_grading_tasks(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    trace_id: str,
) -> dict[str, Any]:
    generated = report["generatedDsl"]
    task = store.save(
        create_waiting_review_task(
            task_type="GRADING_GENERATION",
            title="Phase 2 Mock Grading generation",
            input_type="exam_dsl",
            input_ref=str(report["examDslInput"]["examId"]),
            final_result_path=generated["grading"]["dslPath"],
            trace_id=trace_id,
        )
    )
    return {"grading": task}


def link_phase2_grading_tasks(report: dict[str, Any], tasks: dict[str, Any]) -> None:
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in tasks:
            step["taskId"] = tasks[kind].id
            report["generatedDsl"][kind]["taskId"] = tasks[kind].id


def save_phase2_grading_artifacts(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    exam_path: Path,
    tasks: dict[str, Any],
    trace_id: str,
) -> list[dict[str, Any]]:
    generated = report["generatedDsl"]
    quality_signals = report.get("qualitySignals", {})
    return [
        save_artifact(
            store,
            kind=ArtifactKind.EXAM_DSL,
            path=str(exam_path),
            title="Phase 2 Grading Generation Source Exam DSL",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(exam_path),
            metadata={"workflowId": PHASE2_GRADING_WORKFLOW_ID, "sourceOnly": True},
        ),
        save_artifact(
            store,
            kind=ArtifactKind.GRADING_DSL,
            path=generated["grading"]["dslPath"],
            title="Phase 2 Mock Generated Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=tasks["grading"].id,
            source_ref=str(report["examDslInput"]["examId"]),
            metadata={
                "dslKind": "Grading",
                "sandboxRequiredBeforeRealExecution": True,
                "providerAdapter": "mock_provider_adapter",
                "workflowId": PHASE2_GRADING_WORKFLOW_ID,
                "qualitySignals": quality_signals.get("grading", {}),
                "workflowQualitySignals": quality_signals,
                "qualitySignalSummary": quality_signals.get("overall", {}),
                "reviewHighlights": quality_signals.get("reviewHighlights", []),
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.WORKFLOW_REPORT,
            path=f"memory://{report['id']}",
            title="Phase 2 Mock Grading Generation Report",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(exam_path),
            metadata={
                "workflowId": PHASE2_GRADING_WORKFLOW_ID,
                "reviewRequired": True,
                "qualitySignalSummary": quality_signals.get("overall", {}),
                "reviewHighlights": quality_signals.get("reviewHighlights", []),
            },
        ),
    ]


def create_phase2_ppt_tasks(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    trace_id: str,
) -> dict[str, Any]:
    generated = report["generatedDsl"]
    task = store.save(
        create_waiting_review_task(
            task_type="PPT_GENERATION",
            title="Phase 2 Mock PPT generation",
            input_type="markdown",
            input_ref=str(report["input"]),
            final_result_path=generated["ppt"]["dslPath"],
            trace_id=trace_id,
        )
    )
    return {"ppt": task}


def link_phase2_ppt_tasks(report: dict[str, Any], tasks: dict[str, Any]) -> None:
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in tasks:
            step["taskId"] = tasks[kind].id
            report["generatedDsl"][kind]["taskId"] = tasks[kind].id


def save_phase2_ppt_artifacts(
    store: JsonTaskStore,
    *,
    report: dict[str, Any],
    input_path: Path,
    tasks: dict[str, Any],
    trace_id: str,
) -> list[dict[str, Any]]:
    generated = report["generatedDsl"]
    material_analysis = report.get("materialAnalysis", {})
    return [
        save_artifact(
            store,
            kind=ArtifactKind.MATERIAL_ANALYSIS,
            path=str(input_path),
            title=str(material_analysis.get("title") or "Phase 2 PPT Source Material"),
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(input_path),
            metadata={
                "fileType": material_analysis.get("fileType"),
                "riskCount": material_analysis.get("riskCount", 0),
                "unknownShellExecuted": material_analysis.get("unknownShellExecuted", False),
                "workflowId": PHASE2_PPT_WORKFLOW_ID,
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.WORKFLOW_REPORT,
            path=f"memory://{report['slidePlan']['id']}",
            title="Phase 2 Mock PPT Slide Plan",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(input_path),
            metadata={
                "workflowId": PHASE2_PPT_WORKFLOW_ID,
                "artifactType": "slide_plan",
                "slideCount": len(report.get("slidePlan", {}).get("slides", [])),
                "pptFileGenerated": False,
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.PPT_DSL,
            path=generated["ppt"]["dslPath"],
            title="Phase 2 Mock PPT DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=tasks["ppt"].id,
            source_ref=str(input_path),
            metadata={
                "dslKind": "PPT",
                "artifactGenerated": False,
                "pptFileGenerated": False,
                "reviewRequired": True,
                "providerAdapter": "mock_provider_adapter",
                "workflowId": PHASE2_PPT_WORKFLOW_ID,
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.WORKFLOW_REPORT,
            path=f"memory://{report['id']}",
            title="Phase 2 Mock PPT Generation Report",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(input_path),
            metadata={"workflowId": PHASE2_PPT_WORKFLOW_ID, "reviewRequired": True},
        ),
    ]


def create_environment(
    env_type: EnvironmentType,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    title = payload.get("title")
    if not title:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "title", "reason": "缺少参数"}], trace_id)
    image = payload.get("image")
    if not image:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "image", "reason": "缺少参数"}], trace_id)
    resources = payload.get("resources") or {}
    cpu = resources.get("cpu", 2)
    memory_gb = resources.get("memoryGb", 4)
    if not isinstance(cpu, int) or cpu < 1:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "cpu", "reason": "必须大于等于 1"}], trace_id)
    if not isinstance(memory_gb, int) or memory_gb < 1:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "memoryGb", "reason": "必须大于等于 1"}], trace_id)
    environment = EnvironmentInstance(
        envType=env_type,
        title=title,
        image=image,
        resources={"cpu": cpu, "memoryGb": memory_gb},
    )
    store.save_environment(environment)
    audit_event = create_operation_audit_event(
        action=OperationAction.ENV_CREATE,
        resource_type=OperationResourceType.ENVIRONMENT,
        resource_id=environment.id,
        actor="backend-mock",
        trace_id=trace_id,
        after_state=environment.status.value,
        detail={"envType": environment.envType.value, "realCloudResourceChanged": False},
    )
    store.save_operation_audit_event(audit_event)
    return ok(
        "Mock 环境已创建",
        {
            "environment": environment.to_dict(),
            "operationAuditEvent": audit_event.to_dict(),
            "mode": "MOCK_ONLY",
            "note": "Phase 1 不创建真实 VM 或 Notebook",
        },
        trace_id,
    )


def generate_lab(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    input_value = payload.get("input")
    if not input_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "缺少参数"}], trace_id)
    try:
        core_repository, core_write = prepare_backend_core_write_through(payload)
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    input_path = resolve_local_path(str(input_value))
    if not input_path.exists() or not input_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "文件不存在"}], trace_id)
    try:
        material_analysis = analyze_material(input_path, trace_id=trace_id)
    except MaterialAnalysisError as exc:
        return material_fail(exc, trace_id)
    provider_mode = str(payload.get("providerMode") or PROVIDER_MODE_MOCK).strip().lower()
    if provider_mode not in {PROVIDER_MODE_MOCK, PROVIDER_MODE_REAL_LLM}:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "providerMode", "reason": "expected mock or real-llm"}],
            trace_id,
        )
    try:
        if provider_mode == PROVIDER_MODE_REAL_LLM:
            lab_generation = generate_real_llm_demo_dsl_via_provider(
                "lab",
                input_ref=str(input_path),
                output_ref=f"examples/output/ui-real-llm-lab-{uuid4().hex[:12]}.json",
                input_payload={
                    "sourceRef": str(input_path),
                    "materialAnalysis": material_analysis,
                    "instruction": "Generate one complete Lab DSL from the local source. Keep status WAITING_REVIEW.",
                },
                model=payload.get("model") if isinstance(payload.get("model"), str) else None,
                base_url=payload.get("baseUrl") if isinstance(payload.get("baseUrl"), str) else None,
                timeout_seconds=int(payload.get("timeoutSeconds") or 60),
                max_output_tokens=int(payload.get("maxOutputTokens") or 2200),
                explicit_real_call_opt_in=payload.get("explicitRealCallOptIn") is True,
                confirm_waiting_review=payload.get("confirmWaitingReview") is True,
                confirm_no_auto_publish=payload.get("confirmNoAutoPublish") is True,
                repair_on_schema_failure=payload.get("repairOnSchemaFailure") is True,
                api_surface=str(payload.get("apiSurface") or "auto"),
                trace_id=trace_id,
                root=ROOT,
            )
        else:
            lab_generation = generate_mock_dsl_via_adapter("lab", input_ref=str(input_path), trace_id=trace_id, root=ROOT)
    except ValueError:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "timeoutSeconds/maxOutputTokens", "reason": "必须是整数"}],
            trace_id,
        )
    except ProviderError as exc:
        return provider_error_response(exc, trace_id, provider_id="openai" if provider_mode == PROVIDER_MODE_REAL_LLM else "mock")
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock Lab DSL generation",
        input_type="markdown",
        input_ref=str(input_path),
        trace_id=trace_id,
    )
    lab_generation = finalize_lab_generation_v1(
        lab_generation,
        input_path=input_path,
        material_analysis=material_analysis,
        task_id=task.id,
        root=ROOT,
    )
    task.finalResultPath = lab_generation["dslPath"]
    store.save(task)
    save_provider_generation_audit(
        store,
        generation=lab_generation,
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id="lab_generate",
        workflow_step="generate_lab_dsl",
        task_id=task.id,
    )
    material_artifact = save_artifact(
        store,
        kind=ArtifactKind.MATERIAL_ANALYSIS,
        path=str(input_path),
        title=material_analysis["title"],
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=str(input_path),
        metadata={
            "fileType": material_analysis["fileType"],
            "riskCount": material_analysis["riskCount"],
            "unknownShellExecuted": material_analysis["unknownShellExecuted"],
        },
    )
    lab_artifact = save_artifact(
        store,
        kind=ArtifactKind.LAB_DSL,
        path=lab_generation["dslPath"],
        title="Mock Lab DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=str(input_path),
        metadata={
            "dslKind": "Lab",
            "reviewRequired": True,
            "providerAdapter": lab_generation["provider"]["adapterId"],
            "schemaValidated": True,
            "labFeatureReadiness": lab_generation["labFeatureReadiness"],
        },
    )
    lab_feature_readiness = build_lab_feature_readiness(
        lab_generation,
        material_analysis=material_analysis,
        task=task.to_dict(),
        artifacts=[material_artifact, lab_artifact],
    )
    lab_generation["labFeatureReadiness"] = lab_feature_readiness
    lab_artifact["metadata"]["labFeatureReadiness"] = lab_feature_readiness
    store.save_artifact(ArtifactRecord.from_dict(lab_artifact))
    try:
        backend_core_write_through(
            core_repository,
            core_write,
            task=task,
            artifacts=[material_artifact, lab_artifact],
        )
    except CoreRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    data = {
        "task": task.to_dict(),
        "providerGeneration": lab_generation,
        "dsl": lab_generation["dsl"],
        "dslPath": lab_generation["dslPath"],
        "status": TaskStatus.WAITING_REVIEW.value,
        "reviewRequired": True,
        "mode": "REAL_LLM" if provider_mode == PROVIDER_MODE_REAL_LLM else "MOCK_ONLY",
        "materialAnalysis": material_analysis,
        "artifacts": [material_artifact, lab_artifact],
        "labFeatureReadiness": lab_feature_readiness,
    }
    if core_write is not None:
        data["backendCoreWriteThrough"] = core_write
    return ok(
        "真实 LLM Lab DSL 已生成，等待人工审核" if provider_mode == PROVIDER_MODE_REAL_LLM else "Mock Lab DSL 已生成，等待人工审核",
        data,
        trace_id,
    )


def generate_exam_from_lab(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    lab_id = payload.get("labId")
    if not lab_id:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "labId", "reason": "缺少参数"}], trace_id)
    try:
        core_repository, core_write = prepare_backend_core_write_through(payload)
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    provider_mode = str(payload.get("providerMode") or PROVIDER_MODE_MOCK).strip().lower()
    if provider_mode not in {PROVIDER_MODE_MOCK, PROVIDER_MODE_REAL_LLM}:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "providerMode", "reason": "expected mock or real-llm"}],
            trace_id,
        )
    try:
        if provider_mode == PROVIDER_MODE_REAL_LLM:
            lab_dsl_value = payload.get("labDslPath")
            if not isinstance(lab_dsl_value, str) or not lab_dsl_value.strip():
                return fail(
                    "VALIDATION_ERROR",
                    "参数错误",
                    [{"field": "labDslPath", "reason": "真实 LLM 生成需要本地 Lab DSL 路径"}],
                    trace_id,
                )
            lab_path = resolve_local_path(lab_dsl_value)
            if not lab_path.exists() or not lab_path.is_file():
                return fail("VALIDATION_ERROR", "参数错误", [{"field": "labDslPath", "reason": "文件不存在"}], trace_id)
            lab_dsl, lab_error = validate_yaml_dsl("lab", lab_path, trace_id)
            if lab_error:
                return lab_error
            options = {
                "model": payload.get("model") if isinstance(payload.get("model"), str) else None,
                "base_url": payload.get("baseUrl") if isinstance(payload.get("baseUrl"), str) else None,
                "timeout_seconds": int(payload.get("timeoutSeconds") or 60),
                "max_output_tokens": int(payload.get("maxOutputTokens") or 2200),
                "explicit_real_call_opt_in": payload.get("explicitRealCallOptIn") is True,
                "confirm_waiting_review": payload.get("confirmWaitingReview") is True,
                "confirm_no_auto_publish": payload.get("confirmNoAutoPublish") is True,
                "repair_on_schema_failure": payload.get("repairOnSchemaFailure") is True,
                "api_surface": str(payload.get("apiSurface") or "auto"),
                "trace_id": trace_id,
                "root": ROOT,
            }
            exam_generation = generate_real_llm_demo_dsl_via_provider(
                "exam",
                input_ref=str(lab_path),
                output_ref=f"examples/output/ui-real-llm-exam-{uuid4().hex[:12]}.json",
                input_payload={
                    "sourceRef": str(lab_path),
                    "labDsl": lab_dsl,
                    "instruction": "Generate one complete Exam DSL from this Lab DSL. Keep answers for reviewers only and status WAITING_REVIEW.",
                },
                **options,
            )
            grading_generation = generate_real_llm_demo_dsl_via_provider(
                "grading",
                input_ref=exam_generation["dslId"],
                output_ref=f"examples/output/ui-real-llm-grading-{uuid4().hex[:12]}.json",
                input_payload={
                    "examDsl": exam_generation["dsl"],
                    "instruction": "Generate one complete Grading DSL aligned with the Exam grading references. Do not execute code.",
                },
                **options,
            )
        else:
            exam_generation = generate_mock_dsl_via_adapter("exam", input_ref=str(lab_id), trace_id=trace_id, root=ROOT)
            grading_generation = generate_mock_dsl_via_adapter(
                "grading",
                input_ref=exam_generation["dslId"],
                trace_id=trace_id,
                root=ROOT,
            )
    except ValueError:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "timeoutSeconds/maxOutputTokens", "reason": "必须是整数"}],
            trace_id,
        )
    except ProviderError as exc:
        return provider_error_response(exc, trace_id, provider_id="openai" if provider_mode == PROVIDER_MODE_REAL_LLM else "mock")
    task = create_waiting_review_task(
        task_type="EXAM_GENERATION",
        title="Mock Exam and Grading DSL generation",
        input_type="lab_id",
        input_ref=str(lab_id),
        final_result_path=exam_generation["dslPath"],
        trace_id=trace_id,
    )
    store.save(task)
    save_provider_bundle_audits(
        store,
        bundle={"exam": exam_generation, "grading": grading_generation},
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id="exam_generate_from_lab",
        step_names={"exam": "generate_exam_dsl", "grading": "generate_grading_dsl"},
        task_ids={"exam": task.id, "grading": task.id},
    )
    exam_artifact = save_artifact(
        store,
        kind=ArtifactKind.EXAM_DSL,
        path=exam_generation["dslPath"],
        title="Mock Exam DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=str(lab_id),
        metadata={"dslKind": "Exam", "answerVisibleToCandidate": False, "providerAdapter": exam_generation["provider"]["adapterId"]},
    )
    grading_artifact = save_artifact(
        store,
        kind=ArtifactKind.GRADING_DSL,
        path=grading_generation["dslPath"],
        title="Mock Grading DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=str(lab_id),
        metadata={"dslKind": "Grading", "reviewRequired": True, "providerAdapter": grading_generation["provider"]["adapterId"]},
    )
    try:
        backend_core_write_through(
            core_repository,
            core_write,
            task=task,
            artifacts=[exam_artifact, grading_artifact],
        )
    except CoreRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    data = {
        "task": task.to_dict(),
        "providerGenerations": {"exam": exam_generation, "grading": grading_generation},
        "examDsl": exam_generation["dsl"],
        "gradingDsl": grading_generation["dsl"],
        "examDslPath": exam_generation["dslPath"],
        "gradingDslPath": grading_generation["dslPath"],
        "status": TaskStatus.WAITING_REVIEW.value,
        "reviewRequired": True,
        "answerVisibleToCandidate": False,
        "mode": "REAL_LLM" if provider_mode == PROVIDER_MODE_REAL_LLM else "MOCK_ONLY",
        "artifacts": [exam_artifact, grading_artifact],
    }
    if core_write is not None:
        data["backendCoreWriteThrough"] = core_write
    return ok(
        "真实 LLM Exam / Grading DSL 已生成，等待人工审核" if provider_mode == PROVIDER_MODE_REAL_LLM else "Mock Exam DSL 已生成，等待人工审核",
        data,
        trace_id,
    )


def build_grading_report(grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
    return build_mock_grading_report(grading, trace_id)


def run_grading(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    grading_value = payload.get("grading")
    if not grading_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "缺少参数"}], trace_id)
    grading_path = resolve_local_path(str(grading_value))
    if not grading_path.exists() or not grading_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "文件不存在"}], trace_id)
    grading_dsl, error = validate_yaml_dsl("grading", grading_path, trace_id)
    if error:
        return error
    try:
        report = build_grading_report(grading_dsl, trace_id)
    except GradingRunnerError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    audit_event = create_operation_audit_event(
        action=OperationAction.MOCK_GRADING_RUN,
        resource_type=OperationResourceType.GRADING_REPORT,
        resource_id=report["id"],
        actor="backend-mock",
        trace_id=trace_id,
        after_state="COMPLETED",
        detail=build_grading_audit_detail(report),
    )
    store.save_operation_audit_event(audit_event)
    artifact = save_artifact(
        store,
        kind=ArtifactKind.GRADING_REPORT,
        path=f"memory://{report['id']}",
        title="Mock Grading Report",
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        source_ref=str(grading_path),
        metadata={
            "gradingId": report["gradingId"],
            "earnedScore": report["earnedScore"],
            "sandboxExecuted": False,
            "checkSummary": report.get("checkSummary", {}),
            "sandboxPolicy": report.get("sandboxPolicy", {}),
            "explainability": report.get("explainability", {}),
        },
    )
    operation_audit_event = audit_event.to_dict()
    return ok(
        "Mock 评分完成",
        {
            "report": report,
            "reportDetail": build_grading_report_detail(report, operation_audit_event),
            "gradingDslPath": str(grading_path),
            "operationAuditEvent": operation_audit_event,
            "artifact": artifact,
            "mode": "MOCK_ONLY",
            "sandboxExecuted": False,
        },
        trace_id,
    )


def run_readonly_grading_evidence(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    grading_value = payload.get("grading")
    if not grading_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "缺少参数"}], trace_id)
    submission_value = payload.get("submission")
    if not submission_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "submission", "reason": "缺少参数"}], trace_id)
    grading_path = resolve_local_path(str(grading_value))
    if not grading_path.exists() or not grading_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "文件不存在"}], trace_id)
    submission_path = resolve_local_path(str(submission_value))
    grading_dsl, error = validate_yaml_dsl("grading", grading_path, trace_id)
    if error:
        return error
    try:
        report = build_readonly_sandbox_report(grading_dsl, submission_path, trace_id)
    except ReadonlySandboxExecutorError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    output = payload.get("output")
    if output:
        output_path = resolve_local_path(str(output))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report["reportPath"] = str(output_path)
    operation_audit_event = create_operation_audit_event(
        action=OperationAction.READONLY_SANDBOX_RUN,
        resource_type=OperationResourceType.GRADING_REPORT,
        resource_id=report["id"],
        actor="backend-mock",
        trace_id=trace_id,
        after_state="COMPLETED",
        detail={
            "reportType": "READONLY_SANDBOX_RUN",
            "mode": report["mode"],
            "gradingId": report["gradingId"],
            "submissionRoot": report["submissionRoot"],
            "runner": report["runner"],
            "executionSummary": report["executionSummary"],
            "score": report["score"],
            "safety": report["safety"],
            "blockedActions": [
                "executeGradingCommand",
                "runRealPytest",
                "executeNotebook",
                "executeContestantCode",
                "unknownShellExecution",
                "networkAccess",
                "realPublish",
            ],
        },
    )
    store.save_operation_audit_event(operation_audit_event)
    report["operationAuditEvent"] = operation_audit_event.to_dict()
    report["reportDetail"] = build_grading_report_detail(report, report["operationAuditEvent"])
    artifact = save_artifact(
        store,
        kind=ArtifactKind.GRADING_REPORT,
        path=report.get("reportPath", f"memory://{report['id']}"),
        title="Readonly Sandbox Report",
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        source_ref=str(grading_path),
        metadata={
            "reportType": "READONLY_SANDBOX_RUN",
            "gradingId": report["gradingId"],
            "submissionRoot": report["submissionRoot"],
            "executionSummary": report["executionSummary"],
            "score": report["score"],
            "checkSummary": report.get("checkSummary", {}),
            "assessmentPlanSummary": report.get("assessmentPlanSummary", {}),
            "reportDetailSummary": {
                "source": report.get("reportDetail", {}).get("source"),
                "mode": report.get("reportDetail", {}).get("mode"),
                "checkSummary": report.get("reportDetail", {}).get("checkSummary", {}),
                "safety": report.get("reportDetail", {}).get("safety", {}),
            },
            "safety": report["safety"],
        },
    )
    report["artifact"] = artifact
    if output:
        Path(report["reportPath"]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ok(
        "只读评分证据已生成",
        {
            "report": report,
            "reportDetail": report["reportDetail"],
            "gradingDslPath": str(grading_path),
            "submissionPath": str(submission_path),
            "operationAuditEvent": report["operationAuditEvent"],
            "artifact": artifact,
            "mode": "READONLY_REAL_SANDBOX_POC",
            "sandboxExecuted": report["safety"]["sandboxExecuted"],
            "readonlyOnly": True,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
        },
        trace_id,
    )


def run_controlled_grading_evidence(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    grading_value = payload.get("grading")
    if not grading_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "缺少参数"}], trace_id)
    submission_value = payload.get("submission")
    if not submission_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "submission", "reason": "缺少参数"}], trace_id)
    grading_path = resolve_local_path(str(grading_value))
    if not grading_path.exists() or not grading_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "文件不存在"}], trace_id)
    submission_path = resolve_local_path(str(submission_value))
    grading_dsl, error = validate_yaml_dsl("grading", grading_path, trace_id)
    if error:
        return error
    image = str(payload.get("image") or DEFAULT_CONTROLLED_DOCKER_IMAGE)
    try:
        report = build_controlled_command_sandbox_report(grading_dsl, submission_path, trace_id, image=image)
    except ControlledCommandSandboxError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    output = payload.get("output")
    if output:
        output_path = resolve_local_path(str(output))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report["reportPath"] = str(output_path)
    operation_audit_event = create_operation_audit_event(
        action=OperationAction.CONTROLLED_SANDBOX_RUN,
        resource_type=OperationResourceType.GRADING_REPORT,
        resource_id=report["id"],
        actor="backend-mock",
        trace_id=trace_id,
        after_state="COMPLETED",
        detail={
            "reportType": "CONTROLLED_DOCKER_SANDBOX_RUN",
            "mode": report["mode"],
            "gradingId": report["gradingId"],
            "submissionRoot": report["submissionRoot"],
            "runner": report["runner"],
            "executionSummary": report["executionSummary"],
            "score": report["score"],
            "safety": report["safety"],
            "isolation": report.get("isolation", {}),
            "isolationQuality": report.get("isolationQuality", {}),
            "imageSupplyChain": report.get("imageSupplyChain", {}),
            "blockedActions": [
                "executeNotebook",
                "unknownShellExecution",
                "networkAccess",
                "hostExecution",
                "realPublish",
            ],
        },
    )
    store.save_operation_audit_event(operation_audit_event)
    report["operationAuditEvent"] = operation_audit_event.to_dict()
    report["reportDetail"] = build_grading_report_detail(report, report["operationAuditEvent"])
    artifact = save_artifact(
        store,
        kind=ArtifactKind.GRADING_REPORT,
        path=report.get("reportPath", f"memory://{report['id']}"),
        title="Controlled Docker Sandbox Report",
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        source_ref=str(grading_path),
        metadata={
            "reportType": "CONTROLLED_DOCKER_SANDBOX_RUN",
            "gradingId": report["gradingId"],
            "submissionRoot": report["submissionRoot"],
            "executionSummary": report["executionSummary"],
            "score": report["score"],
            "checkSummary": report.get("checkSummary", {}),
            "assessmentPlanSummary": report.get("assessmentPlanSummary", {}),
            "isolation": report.get("isolation", {}),
            "isolationQuality": report.get("isolationQuality", {}),
            "imageSupplyChain": report.get("imageSupplyChain", {}),
            "reportDetailSummary": {
                "source": report.get("reportDetail", {}).get("source"),
                "mode": report.get("reportDetail", {}).get("mode"),
                "checkSummary": report.get("reportDetail", {}).get("checkSummary", {}),
                "safety": report.get("reportDetail", {}).get("safety", {}),
            },
            "safety": report["safety"],
        },
    )
    report["artifact"] = artifact
    if output:
        Path(report["reportPath"]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ok(
        "受控 Docker 评分证据已生成",
        {
            "report": report,
            "reportDetail": report["reportDetail"],
            "gradingDslPath": str(grading_path),
            "submissionPath": str(submission_path),
            "operationAuditEvent": report["operationAuditEvent"],
            "artifact": artifact,
            "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
            "sandboxExecuted": report["safety"]["sandboxExecuted"],
            "readonlyOnly": False,
            "contestantCodeExecuted": report["safety"]["contestantCodeExecuted"],
            "commandExecuted": report["safety"]["commandExecuted"],
        },
        trace_id,
    )


def merge_grading_evidence_reports(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    report_values = payload.get("reports")
    if not report_values:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "reports", "reason": "缺少参数"}], trace_id)
    if not isinstance(report_values, list):
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "reports", "reason": "必须是数组"}], trace_id)
    output_value = payload.get("output")
    if not output_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "output", "reason": "缺少参数"}], trace_id)
    task_id = payload.get("taskId")
    if task_id and store.get(str(task_id)) is None:
        return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)

    report_paths: list[Path] = []
    reports: list[dict[str, Any]] = []
    for index, value in enumerate(report_values):
        if not isinstance(value, str):
            return fail("VALIDATION_ERROR", "参数错误", [{"field": f"reports[{index}]", "reason": "必须是字符串"}], trace_id)
        report_path = resolve_local_path(value)
        if not report_path.exists() or not report_path.is_file():
            return fail("VALIDATION_ERROR", "参数错误", [{"field": f"reports[{index}]", "reason": "文件不存在"}], trace_id)
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": f"reports[{index}]", "reason": f"JSON 格式错误: {exc.msg}"}], trace_id)
        if not isinstance(report, dict):
            return fail("VALIDATION_ERROR", "参数错误", [{"field": f"reports[{index}]", "reason": "必须是 JSON 对象"}], trace_id)
        report_paths.append(report_path)
        reports.append(report)

    output_path = resolve_local_path(str(output_value))
    try:
        merge_payload = build_grading_evidence_merge_report(reports, report_paths=report_paths, trace_id=trace_id)
    except EvidenceMergeError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)

    merge_payload["reportPath"] = str(output_path)
    operation_audit_event = create_operation_audit_event(
        action=OperationAction.GRADING_EVIDENCE_MERGE,
        resource_type=OperationResourceType.GRADING_REPORT,
        resource_id=merge_payload["id"],
        actor="backend-mock",
        trace_id=trace_id,
        after_state="COMPLETED",
        detail={
            "reportType": "GRADING_EVIDENCE_MERGE",
            "mode": merge_payload["mode"],
            "sourceReportPaths": [str(path) for path in report_paths],
            "taskId": str(task_id) if task_id else None,
            "summary": merge_payload["summary"],
            "evidenceCoverage": merge_payload["evidenceCoverage"],
            "safety": merge_payload["safety"],
        },
    )
    store.save_operation_audit_event(operation_audit_event)
    merge_payload["operationAuditEvent"] = operation_audit_event.to_dict()
    artifact = save_artifact(
        store,
        kind=ArtifactKind.GRADING_REPORT,
        path=str(output_path),
        title="Merged Grading Evidence Report",
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        task_id=str(task_id) if task_id else None,
        source_ref=";".join(str(path) for path in report_paths),
        metadata={
            "reportType": "GRADING_EVIDENCE_MERGE",
            "sourceReportTotal": merge_payload["sourceReportTotal"],
            "taskId": str(task_id) if task_id else None,
            "summary": merge_payload["summary"],
            "evidenceCoverage": merge_payload["evidenceCoverage"],
            "safety": merge_payload["safety"],
        },
    )
    merge_payload["artifact"] = artifact
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merge_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ok(
        "评分 evidence 合并报告已生成",
        {
            "report": merge_payload,
            "operationAuditEvent": merge_payload["operationAuditEvent"],
            "artifact": artifact,
            "mode": "GRADING_EVIDENCE_MERGE_REPORT",
            "sourceReportPaths": [str(path) for path in report_paths],
            "readExistingReportsOnly": True,
            "mergeExecutedOnlyExistingReports": True,
            "sandboxExecutedByTool": False,
            "contestantCodeExecutedByTool": False,
            "commandExecutedByTool": False,
            "notebookExecutedByTool": False,
            "networkAccess": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def run_grading_evidence_auto(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    grading_value = payload.get("grading")
    if not grading_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "缺少参数"}], trace_id)
    submission_value = payload.get("submission")
    if not submission_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "submission", "reason": "缺少参数"}], trace_id)
    output_value = payload.get("output")
    if not output_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "output", "reason": "缺少参数"}], trace_id)
    task_id = payload.get("taskId")
    if task_id and store.get(str(task_id)) is None:
        return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)

    grading_path = resolve_local_path(str(grading_value))
    if not grading_path.exists() or not grading_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "文件不存在"}], trace_id)
    submission_path = resolve_local_path(str(submission_value))
    if not submission_path.exists() or not submission_path.is_dir():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "submission", "reason": "目录不存在"}], trace_id)
    grading_dsl, error = validate_yaml_dsl("grading", grading_path, trace_id)
    if error:
        return error

    include_controlled_command = payload.get("includeControlledCommand") is True
    fail_on_controlled_unavailable = payload.get("failOnControlledUnavailable") is True
    image = str(payload.get("image") or DEFAULT_CONTROLLED_DOCKER_IMAGE)
    output_path = resolve_local_path(str(output_value))
    try:
        auto_payload = build_grading_evidence_auto_report(
            grading_dsl,
            submission_path,
            trace_id=trace_id,
            include_controlled_command=include_controlled_command,
            image=image,
            fail_on_controlled_unavailable=fail_on_controlled_unavailable,
        )
    except (GradingEvidenceAutoError, ReadonlySandboxExecutorError, EvidenceMergeError) as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)

    auto_payload["reportPath"] = str(output_path)
    operation_audit_event = create_operation_audit_event(
        action=OperationAction.GRADING_EVIDENCE_MERGE,
        resource_type=OperationResourceType.GRADING_REPORT,
        resource_id=auto_payload["id"],
        actor="backend-mock",
        trace_id=trace_id,
        after_state="COMPLETED",
        detail={
            "reportType": "GRADING_EVIDENCE_AUTO",
            "mode": auto_payload["mode"],
            "sourceMode": auto_payload["sourceMode"],
            "gradingPath": str(grading_path),
            "submissionPath": str(submission_path),
            "taskId": str(task_id) if task_id else None,
            "includeControlledCommand": include_controlled_command,
            "failOnControlledUnavailable": fail_on_controlled_unavailable,
            "summary": auto_payload["summary"],
            "evidenceCoverage": auto_payload["evidenceCoverage"],
            "scorePreview": auto_payload["scorePreview"],
            "gradingDslCoverageSummary": auto_payload["gradingDslCoverageSummary"],
            "reviewerSafetySummary": auto_payload["reviewerSafetySummary"],
            "safety": auto_payload["safety"],
        },
    )
    store.save_operation_audit_event(operation_audit_event)
    auto_payload["operationAuditEvent"] = operation_audit_event.to_dict()
    artifact = save_artifact(
        store,
        kind=ArtifactKind.GRADING_REPORT,
        path=str(output_path),
        title="Auto Grading Evidence Report",
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        task_id=str(task_id) if task_id else None,
        source_ref=str(grading_path),
        metadata={
            "reportType": "GRADING_EVIDENCE_AUTO",
            "sourceMode": auto_payload["sourceMode"],
            "taskId": str(task_id) if task_id else None,
            "gradingPath": str(grading_path),
            "submissionPath": str(submission_path),
            "summary": auto_payload["summary"],
            "evidenceCoverage": auto_payload["evidenceCoverage"],
            "scorePreview": auto_payload["scorePreview"],
            "gradingDslCoverageSummary": auto_payload["gradingDslCoverageSummary"],
            "reviewerSafetySummary": auto_payload["reviewerSafetySummary"],
            "safety": auto_payload["safety"],
            "warnings": auto_payload.get("warnings", []),
        },
    )
    auto_payload["artifact"] = artifact
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(auto_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ok(
        "自动评分 evidence 报告已生成",
        {
            "report": auto_payload,
            "gradingEvidenceAutoReport": auto_payload,
            "reportPath": str(output_path),
            "gradingDslPath": str(grading_path),
            "submissionPath": str(submission_path),
            "operationAuditEvent": auto_payload["operationAuditEvent"],
            "artifact": artifact,
            "mode": "GRADING_EVIDENCE_AUTO_REPORT",
            "sourceMode": "EVIDENCE_AUTO",
            "includeControlledCommand": include_controlled_command,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
        trace_id,
    )


def generate_ppt(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    input_value = payload.get("input")
    if not input_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "缺少参数"}], trace_id)
    try:
        core_repository, core_write = prepare_backend_core_write_through(payload)
    except CoreRepositoryError as exc:
        return backend_core_repository_error_response(exc, trace_id)
    input_path = resolve_local_path(str(input_value))
    if not input_path.exists() or not input_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "文件不存在"}], trace_id)
    provider_mode = str(payload.get("providerMode") or PROVIDER_MODE_MOCK).strip().lower()
    if provider_mode not in {PROVIDER_MODE_MOCK, PROVIDER_MODE_REAL_LLM}:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "providerMode", "reason": "expected mock or real-llm"}],
            trace_id,
        )
    try:
        if provider_mode == PROVIDER_MODE_REAL_LLM:
            ppt_generation = generate_real_llm_demo_dsl_via_provider(
                "ppt",
                input_ref=str(input_path),
                output_ref=f"examples/output/ui-real-llm-ppt-{uuid4().hex[:12]}.json",
                input_payload={
                    "sourceRef": str(input_path),
                    "instruction": "Generate one complete PPT DSL from the local source. Do not create a PPTX file. Keep status WAITING_REVIEW.",
                },
                model=payload.get("model") if isinstance(payload.get("model"), str) else None,
                base_url=payload.get("baseUrl") if isinstance(payload.get("baseUrl"), str) else None,
                timeout_seconds=int(payload.get("timeoutSeconds") or 60),
                max_output_tokens=int(payload.get("maxOutputTokens") or 2200),
                explicit_real_call_opt_in=payload.get("explicitRealCallOptIn") is True,
                confirm_waiting_review=payload.get("confirmWaitingReview") is True,
                confirm_no_auto_publish=payload.get("confirmNoAutoPublish") is True,
                repair_on_schema_failure=payload.get("repairOnSchemaFailure") is True,
                api_surface=str(payload.get("apiSurface") or "auto"),
                trace_id=trace_id,
                root=ROOT,
            )
        else:
            ppt_generation = generate_mock_dsl_via_adapter("ppt", input_ref=str(input_path), trace_id=trace_id, root=ROOT)
    except ValueError:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "timeoutSeconds/maxOutputTokens", "reason": "必须是整数"}],
            trace_id,
        )
    except ProviderError as exc:
        return provider_error_response(exc, trace_id, provider_id="openai" if provider_mode == PROVIDER_MODE_REAL_LLM else "mock")
    task = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Mock PPT DSL generation",
        input_type="markdown",
        input_ref=str(input_path),
        final_result_path=ppt_generation["dslPath"],
        trace_id=trace_id,
    )
    store.save(task)
    save_provider_generation_audit(
        store,
        generation=ppt_generation,
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id="ppt_generate",
        workflow_step="generate_ppt_dsl",
        task_id=task.id,
    )
    artifact = save_artifact(
        store,
        kind=ArtifactKind.PPT_DSL,
        path=ppt_generation["dslPath"],
        title="Mock PPT DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=trace_id,
        task_id=task.id,
        source_ref=str(input_path),
        metadata={"dslKind": "PPT", "artifactGenerated": False, "providerAdapter": ppt_generation["provider"]["adapterId"]},
    )
    try:
        backend_core_write_through(core_repository, core_write, task=task, artifacts=[artifact])
    except CoreRepositoryError as exc:
        return fail(exc.code, exc.message, exc.errors, trace_id)
    data = {
        "task": task.to_dict(),
        "providerGeneration": ppt_generation,
        "pptDsl": ppt_generation["dsl"],
        "pptDslPath": ppt_generation["dslPath"],
        "status": TaskStatus.WAITING_REVIEW.value,
        "reviewRequired": True,
        "artifactGenerated": False,
        "mode": "REAL_LLM" if provider_mode == PROVIDER_MODE_REAL_LLM else "MOCK_ONLY",
        "artifact": artifact,
    }
    if core_write is not None:
        data["backendCoreWriteThrough"] = core_write
    return ok(
        "真实 LLM PPT DSL 已生成，等待人工审核" if provider_mode == PROVIDER_MODE_REAL_LLM else "Mock PPT DSL 已生成，等待人工审核",
        data,
        trace_id,
    )


def run_workflow_demo(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    input_value = payload.get("input")
    if not input_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "缺少参数"}], trace_id)
    reviewer = payload.get("reviewer")
    if not reviewer:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}], trace_id)
    input_path = resolve_local_path(str(input_value))
    if not input_path.exists() or not input_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "文件不存在"}], trace_id)
    try:
        material_analysis = analyze_material(input_path, trace_id=trace_id)
    except MaterialAnalysisError as exc:
        return material_fail(exc, trace_id)

    try:
        dsl_bundle = generate_workflow_dsl_bundle(input_ref=str(input_path), trace_id=trace_id, root=ROOT)
    except ProviderError as exc:
        return provider_error_response(exc, trace_id)
    dsl_paths = {kind: generation["dslPath"] for kind, generation in dsl_bundle.items()}
    documents = {kind: generation["dsl"] for kind, generation in dsl_bundle.items()}

    task_specs = [
        ("LAB_GENERATION", "Mock Lab DSL generation", "markdown", str(input_path), dsl_paths["lab"]),
        ("EXAM_GENERATION", "Mock Exam DSL generation", "lab_dsl", dsl_bundle["lab"]["dslId"], dsl_paths["exam"]),
        (
            "GRADING_GENERATION",
            "Mock Grading DSL generation",
            "exam_dsl",
            dsl_bundle["exam"]["dslId"],
            dsl_paths["grading"],
        ),
        ("PPT_GENERATION", "Mock PPT DSL generation", "markdown", str(input_path), dsl_paths["ppt"]),
    ]
    created_tasks = [
        store.save(
            create_waiting_review_task(
                task_type=task_type,
                title=title,
                input_type=input_type,
                input_ref=input_ref,
                final_result_path=final_result_path,
                trace_id=trace_id,
            )
        )
        for task_type, title, input_type, input_ref, final_result_path in task_specs
    ]

    lab_task, exam_task, grading_task, ppt_task = created_tasks
    provider_audit_events = save_provider_bundle_audits(
        store,
        bundle=dsl_bundle,
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id="phase1_main_demo",
        step_names={
            "lab": "generate_lab_dsl",
            "exam": "generate_exam_dsl",
            "grading": "generate_grading_dsl",
            "ppt": "generate_ppt_dsl",
        },
        task_ids={
            "lab": lab_task.id,
            "exam": exam_task.id,
            "grading": grading_task.id,
            "ppt": ppt_task.id,
        },
    )
    grading_report = build_grading_report(documents["grading"], trace_id)
    report = {
        "id": f"workflow_report_{uuid4().hex[:12]}",
        "mode": "MOCK_ONLY",
        "providerAdapter": "mock_provider_adapter",
        "input": str(input_path),
        "reviewer": str(reviewer),
        "steps": [
            {
                "name": "generate_lab_dsl",
                "status": lab_task.status.value,
                "taskId": lab_task.id,
                "dslPath": dsl_paths["lab"],
                "dslId": dsl_bundle["lab"]["dslId"],
                "provider": dsl_bundle["lab"]["provider"],
                "providerCallAuditEvent": provider_audit_events["lab"],
            },
            {
                "name": "generate_exam_dsl",
                "status": exam_task.status.value,
                "taskId": exam_task.id,
                "dslPath": dsl_paths["exam"],
                "dslId": dsl_bundle["exam"]["dslId"],
                "provider": dsl_bundle["exam"]["provider"],
                "providerCallAuditEvent": provider_audit_events["exam"],
            },
            {
                "name": "generate_grading_dsl",
                "status": grading_task.status.value,
                "taskId": grading_task.id,
                "dslPath": dsl_paths["grading"],
                "dslId": dsl_bundle["grading"]["dslId"],
                "provider": dsl_bundle["grading"]["provider"],
                "providerCallAuditEvent": provider_audit_events["grading"],
            },
            {
                "name": "generate_ppt_dsl",
                "status": ppt_task.status.value,
                "taskId": ppt_task.id,
                "dslPath": dsl_paths["ppt"],
                "dslId": dsl_bundle["ppt"]["dslId"],
                "provider": dsl_bundle["ppt"]["provider"],
                "providerCallAuditEvent": provider_audit_events["ppt"],
            },
            {
                "name": "mock_grade_run",
                "status": TaskStatus.COMPLETED.value,
                "report": grading_report,
                "sandboxExecuted": False,
            },
        ],
        "reviewRequired": True,
        "publishBlockedUntilApproved": True,
        "answerVisibleToCandidate": False,
        "sandboxExecuted": False,
        "materialAnalysis": material_analysis,
        "providerCallAuditEvents": provider_audit_events,
        "traceId": trace_id,
    }
    report["steps"][0]["materialAnalysis"] = material_summary(material_analysis)
    pre_run_artifacts = [
        save_artifact(
            store,
            kind=ArtifactKind.MATERIAL_ANALYSIS,
            path=str(input_path),
            title=material_analysis["title"],
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(input_path),
            metadata={
                "fileType": material_analysis["fileType"],
                "riskCount": material_analysis["riskCount"],
                "unknownShellExecuted": material_analysis["unknownShellExecuted"],
            },
        ),
        save_artifact(
            store,
            kind=ArtifactKind.LAB_DSL,
            path=dsl_paths["lab"],
            title="Mock Workflow Lab DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=lab_task.id,
            source_ref=str(input_path),
            metadata={"dslKind": "Lab", "reviewRequired": True, "providerAdapter": dsl_bundle["lab"]["provider"]["adapterId"]},
        ),
        save_artifact(
            store,
            kind=ArtifactKind.EXAM_DSL,
            path=dsl_paths["exam"],
            title="Mock Workflow Exam DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=exam_task.id,
            source_ref=dsl_bundle["lab"]["dslId"],
            metadata={"dslKind": "Exam", "answerVisibleToCandidate": False, "providerAdapter": dsl_bundle["exam"]["provider"]["adapterId"]},
        ),
        save_artifact(
            store,
            kind=ArtifactKind.GRADING_DSL,
            path=dsl_paths["grading"],
            title="Mock Workflow Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=grading_task.id,
            source_ref=dsl_bundle["exam"]["dslId"],
            metadata={"dslKind": "Grading", "reviewRequired": True, "providerAdapter": dsl_bundle["grading"]["provider"]["adapterId"]},
        ),
        save_artifact(
            store,
            kind=ArtifactKind.PPT_DSL,
            path=dsl_paths["ppt"],
            title="Mock Workflow PPT DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=trace_id,
            task_id=ppt_task.id,
            source_ref=str(input_path),
            metadata={"dslKind": "PPT", "artifactGenerated": False, "providerAdapter": dsl_bundle["ppt"]["provider"]["adapterId"]},
        ),
        save_artifact(
            store,
            kind=ArtifactKind.GRADING_REPORT,
            path=f"memory://{grading_report['id']}",
            title="Mock Workflow Grading Report",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=dsl_paths["grading"],
            metadata={"gradingId": grading_report["gradingId"], "sandboxExecuted": False},
        ),
        save_artifact(
            store,
            kind=ArtifactKind.WORKFLOW_REPORT,
            path=f"memory://{report['id']}",
            title="Mock Workflow Report",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            source_ref=str(input_path),
            metadata={"workflowId": "phase1_main_demo", "reviewRequired": True},
        ),
    ]
    workflow_steps = [
        create_workflow_step(
            step["name"],
            index,
            {key: value for key, value in step.items() if key not in {"name", "status"}},
        )
        for index, step in enumerate(report["steps"], start=1)
    ]
    workflow_run = store.save_workflow_run(
        create_workflow_run(
            workflow_id="phase1_main_demo",
            input_ref=str(input_path),
            reviewer=str(reviewer),
            trace_id=trace_id,
            report_path=None,
            steps=workflow_steps,
        )
    )
    linked_artifacts = []
    for artifact in pre_run_artifacts:
        artifact_record = store.get_artifact(artifact["id"])
        if artifact_record is not None:
            artifact_record.workflowRunId = workflow_run.id
            store.save_artifact(artifact_record)
            linked_artifacts.append(artifact_record.to_dict())
    return ok(
        "Mock 主链路执行完成，生成内容等待人工审核",
        {
            "mode": "MOCK_ONLY",
            "report": report,
            "workflowRun": workflow_run.to_dict(),
            "materialAnalysis": material_analysis,
            "createdTasks": [task.to_dict() for task in created_tasks],
            "artifacts": linked_artifacts,
            "dslPaths": dsl_paths,
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "answerVisibleToCandidate": False,
            "sandboxExecuted": False,
        },
        trace_id,
    )


def run_phase2_workflow(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    input_value = payload.get("input")
    if not input_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "缺少参数"}], trace_id)
    reviewer = payload.get("reviewer")
    if not reviewer:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}], trace_id)
    artifact_profile = str(payload.get("artifactProfile") or ARTIFACT_PROFILE_LEGACY_ALL)
    if artifact_profile not in {ARTIFACT_PROFILE_LEGACY_ALL, ARTIFACT_PROFILE_TEACHING_CORE}:
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "artifactProfile", "reason": "必须是 legacy-all 或 teaching-core"}],
            trace_id,
        )
    input_path = resolve_local_path(str(input_value))
    if not input_path.exists() or not input_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "文件不存在"}], trace_id)
    try:
        material_analysis = analyze_material(input_path, trace_id=trace_id)
    except MaterialAnalysisError as exc:
        return material_fail(exc, trace_id)
    provider_mode = str(payload.get("providerMode") or PROVIDER_MODE_MOCK)
    real_provider_modes = {PROVIDER_MODE_REAL_LLM_MINIMAL, PROVIDER_MODE_REAL_LLM, PROVIDER_MODE_REAL_LLM_DEMO}
    try:
        timeout_seconds = int(payload.get("timeoutSeconds") or 60)
        max_output_tokens = int(payload.get("maxOutputTokens") or 1800)
    except (TypeError, ValueError):
        return fail(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "timeoutSeconds/maxOutputTokens", "reason": "必须是整数"}],
            trace_id,
        )
    lab_generation_context = {
        "targetUsers": payload.get("targetUsers", "高职学生"),
        "durationMinutes": payload.get("durationMinutes", 60),
        "difficulty": payload.get("difficulty", "beginner"),
        "techTags": payload.get("techTags", ""),
        "teachingStyle": payload.get("teachingStyle", "guided_practice"),
    }
    try:
        report = run_phase2_content_generation(
            input_ref=str(input_path),
            reviewer=str(reviewer),
            trace_id=trace_id,
            root=ROOT,
            material_analysis=material_analysis,
            provider_mode=provider_mode,
            lab_generation_context=lab_generation_context,
            real_lab_output_ref=str(payload.get("realLabOutput") or REAL_LLM_MINIMAL_LAB_OUTPUT_REF),
            real_output_refs={
                "lab": str(payload.get("realLlmLabOutput") or REAL_LLM_OUTPUT_REFS["lab"]),
                "exam": str(payload.get("realLlmExamOutput") or REAL_LLM_OUTPUT_REFS["exam"]),
                "grading": str(payload.get("realLlmGradingOutput") or REAL_LLM_OUTPUT_REFS["grading"]),
                "ppt": str(payload.get("realLlmPptOutput") or REAL_LLM_OUTPUT_REFS["ppt"]),
            },
            real_demo_output_refs={
                "lab": str(payload.get("realDemoLabOutput") or REAL_LLM_DEMO_OUTPUT_REFS["lab"]),
                "exam": str(payload.get("realDemoExamOutput") or REAL_LLM_DEMO_OUTPUT_REFS["exam"]),
                "grading": str(payload.get("realDemoGradingOutput") or REAL_LLM_DEMO_OUTPUT_REFS["grading"]),
                "ppt": str(payload.get("realDemoPptOutput") or REAL_LLM_DEMO_OUTPUT_REFS["ppt"]),
            },
            real_llm_model=payload.get("model") if isinstance(payload.get("model"), str) else None,
            real_llm_base_url=payload.get("baseUrl") if isinstance(payload.get("baseUrl"), str) else None,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            api_surface=str(payload.get("apiSurface") or "auto"),
            explicit_real_call_opt_in=payload.get("explicitRealCallOptIn") is True,
            confirm_single_request=payload.get("confirmSingleRequest") is True,
            confirm_lab_only=(
                payload.get("confirmLabOnly") is True
                or payload.get("confirmRealDsl") is True
                or payload.get("confirmDemoRealDsl") is True
            ),
            confirm_waiting_review=payload.get("confirmWaitingReview") is True,
            confirm_no_auto_publish=payload.get("confirmNoAutoPublish") is True,
            repair_on_schema_failure=payload.get("repairOnSchemaFailure") is True,
            artifact_profile=artifact_profile,
        )
    except ProviderError as exc:
        provider_id = "openai" if provider_mode in real_provider_modes else "mock"
        return provider_error_response(exc, trace_id, provider_id=provider_id)
    candidate_safe_exam_preview = None
    if artifact_profile == ARTIFACT_PROFILE_TEACHING_CORE:
        try:
            candidate_safe_exam_preview = build_candidate_safe_exam_preview(
                report["providerGenerations"]["exam"]["dsl"],
                source_path=report["generatedDsl"]["exam"]["dslPath"],
                trace_id=trace_id,
            )
        except ExamCandidatePreviewError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
    tasks = create_phase2_review_tasks(store, report=report, input_ref=str(input_path), trace_id=trace_id)
    link_phase2_tasks(report, tasks)
    provider_audit_events = save_provider_bundle_audits(
        store,
        bundle=report["providerGenerations"],
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id=PHASE2_WORKFLOW_ID,
        step_names=PHASE2_GENERATION_STEP_BY_KIND,
        task_ids={kind: task.id for kind, task in tasks.items()},
    )
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in provider_audit_events:
            step["providerCallAuditEvent"] = provider_audit_events[kind]
            report["generatedDsl"][kind]["providerCallAuditEvent"] = provider_audit_events[kind]
    report["providerCallAuditEvents"] = provider_audit_events

    pre_run_artifacts = save_phase2_artifacts(
        store,
        report=report,
        input_path=input_path,
        tasks=tasks,
        trace_id=trace_id,
    )
    workflow_steps = [
        create_workflow_step(
            step["name"],
            index,
            {key: value for key, value in step.items() if key not in {"name", "status"}},
        )
        for index, step in enumerate(report["steps"], start=1)
    ]
    workflow_run = store.save_workflow_run(
        create_workflow_run(
            workflow_id=PHASE2_WORKFLOW_ID,
            input_ref=str(input_path),
            reviewer=str(reviewer),
            trace_id=trace_id,
            report_path=None,
            steps=workflow_steps,
        )
    )
    linked_artifacts = []
    for artifact in pre_run_artifacts:
        artifact_record = store.get_artifact(artifact["id"])
        if artifact_record is not None:
            artifact_record.workflowRunId = workflow_run.id
            store.save_artifact(artifact_record)
            linked_artifacts.append(artifact_record.to_dict())
    teaching_package_summary = None
    if artifact_profile == ARTIFACT_PROFILE_TEACHING_CORE:
        teaching_package_summary = {
            "component": "TeachingPackageGenerationSummary",
            "workflowRunId": workflow_run.id,
            "artifactProfile": ARTIFACT_PROFILE_TEACHING_CORE,
            "sourceRef": str(input_path),
            "status": "WAITING_REVIEW",
            "artifacts": {
                kind: {
                    "taskId": tasks[kind].id,
                    "status": tasks[kind].status.value,
                    "dslPath": report["generatedDsl"][kind]["dslPath"],
                    "schemaValidated": report["generatedDsl"][kind].get("schemaValidated") is True,
                }
                for kind in ("lab", "exam", "grading")
            },
            "candidateSafeExamPreview": candidate_safe_exam_preview,
            "reviewProgress": {"total": 3, "waitingReview": 3, "approved": 0, "rejected": 0},
            "exportReady": False,
            "reviewEntry": {
                "path": "/review-center.html",
                "workflowRunId": workflow_run.id,
                "href": f"/review-center.html?workflowRunId={workflow_run.id}",
            },
        }
    return ok(
        "Phase 2 Workflow 已执行，生成内容等待人工审核",
        {
            "mode": report["mode"],
            "providerMode": report["providerMode"],
            "artifactProfile": artifact_profile,
            "report": report,
            "workflowRun": workflow_run.to_dict(),
            "materialAnalysis": material_analysis,
            "createdTasks": [task.to_dict() for task in tasks.values()],
            "artifacts": linked_artifacts,
            "generatedDsl": report["generatedDsl"],
            "reviewSummary": report["reviewSummary"],
            "candidateSafeExamPreview": candidate_safe_exam_preview,
            "teachingPackageSummary": teaching_package_summary,
            "safety": report["safety"],
        },
        trace_id,
    )


def exam_conversion_input_fail(exc: ExamConversionInputError, trace_id: str) -> dict[str, Any]:
    return fail(exc.code, exc.message, exc.errors, trace_id)


def ppt_workflow_input_fail(exc: PptWorkflowInputError, trace_id: str) -> dict[str, Any]:
    return fail(exc.code, exc.message, exc.errors, trace_id)


def grading_generation_input_fail(exc: GradingGenerationInputError, trace_id: str) -> dict[str, Any]:
    return fail(exc.code, exc.message, exc.errors, trace_id)


def run_phase2_exam_workflow(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    lab_value = payload.get("lab")
    if not lab_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "lab", "reason": "缺少参数"}], trace_id)
    notebook_value = payload.get("notebook")
    if not notebook_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "notebook", "reason": "缺少参数"}], trace_id)
    reviewer = payload.get("reviewer")
    if not reviewer:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}], trace_id)
    lab_path = resolve_local_path(str(lab_value))
    notebook_path = resolve_local_path(str(notebook_value))
    if not lab_path.exists() or not lab_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "lab", "reason": "文件不存在"}], trace_id)
    if not notebook_path.exists() or not notebook_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "notebook", "reason": "文件不存在"}], trace_id)
    try:
        report = run_phase2_exam_conversion(
            lab_path=lab_path,
            notebook_path=notebook_path,
            reviewer=str(reviewer),
            trace_id=trace_id,
            root=ROOT,
        )
    except ExamConversionInputError as exc:
        return exam_conversion_input_fail(exc, trace_id)
    except ProviderError as exc:
        return provider_error_response(exc, trace_id)
    tasks = create_phase2_exam_tasks(store, report=report, trace_id=trace_id)
    link_phase2_exam_tasks(report, tasks)
    provider_audit_events = save_provider_bundle_audits(
        store,
        bundle=report["providerGenerations"],
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id=PHASE2_EXAM_WORKFLOW_ID,
        step_names=PHASE2_EXAM_STEP_BY_KIND,
        task_ids={kind: task.id for kind, task in tasks.items()},
    )
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in provider_audit_events:
            step["providerCallAuditEvent"] = provider_audit_events[kind]
            report["generatedDsl"][kind]["providerCallAuditEvent"] = provider_audit_events[kind]
    report["providerCallAuditEvents"] = provider_audit_events

    pre_run_artifacts = save_phase2_exam_artifacts(
        store,
        report=report,
        lab_path=lab_path,
        notebook_path=notebook_path,
        tasks=tasks,
        trace_id=trace_id,
    )
    workflow_steps = [
        create_workflow_step(
            step["name"],
            index,
            {key: value for key, value in step.items() if key not in {"name", "status"}},
        )
        for index, step in enumerate(report["steps"], start=1)
    ]
    workflow_run = store.save_workflow_run(
        create_workflow_run(
            workflow_id=PHASE2_EXAM_WORKFLOW_ID,
            input_ref=str(lab_path),
            reviewer=str(reviewer),
            trace_id=trace_id,
            report_path=None,
            steps=workflow_steps,
        )
    )
    linked_artifacts = []
    for artifact in pre_run_artifacts:
        artifact_record = store.get_artifact(artifact["id"])
        if artifact_record is not None:
            artifact_record.workflowRunId = workflow_run.id
            store.save_artifact(artifact_record)
            linked_artifacts.append(artifact_record.to_dict())
    return ok(
        "Phase 2 Exam Mock Workflow 已执行，试题和评分 DSL 等待人工审核",
        {
            "mode": "MOCK_ONLY",
            "report": report,
            "workflowRun": workflow_run.to_dict(),
            "createdTasks": [task.to_dict() for task in tasks.values()],
            "artifacts": linked_artifacts,
            "generatedDsl": report["generatedDsl"],
            "candidateSafeExamPreview": report["candidateSafeExamPreview"],
            "reviewSummary": report["reviewSummary"],
            "safety": report["safety"],
        },
        trace_id,
    )


def run_phase2_grading_workflow(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    exam_value = payload.get("exam")
    if not exam_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "exam", "reason": "缺少参数"}], trace_id)
    reviewer = payload.get("reviewer")
    if not reviewer:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}], trace_id)
    exam_path = resolve_local_path(str(exam_value))
    if not exam_path.exists() or not exam_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "exam", "reason": "文件不存在"}], trace_id)
    try:
        report = run_phase2_grading_generation(
            exam_path=exam_path,
            reviewer=str(reviewer),
            trace_id=trace_id,
            root=ROOT,
        )
    except GradingGenerationInputError as exc:
        return grading_generation_input_fail(exc, trace_id)
    except ProviderError as exc:
        return provider_error_response(exc, trace_id)
    tasks = create_phase2_grading_tasks(store, report=report, trace_id=trace_id)
    link_phase2_grading_tasks(report, tasks)
    provider_audit_events = save_provider_bundle_audits(
        store,
        bundle=report["providerGenerations"],
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id=PHASE2_GRADING_WORKFLOW_ID,
        step_names=PHASE2_GRADING_STEP_BY_KIND,
        task_ids={kind: task.id for kind, task in tasks.items()},
    )
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in provider_audit_events:
            step["providerCallAuditEvent"] = provider_audit_events[kind]
            report["generatedDsl"][kind]["providerCallAuditEvent"] = provider_audit_events[kind]
    report["providerCallAuditEvents"] = provider_audit_events

    pre_run_artifacts = save_phase2_grading_artifacts(
        store,
        report=report,
        exam_path=exam_path,
        tasks=tasks,
        trace_id=trace_id,
    )
    workflow_steps = [
        create_workflow_step(
            step["name"],
            index,
            {key: value for key, value in step.items() if key not in {"name", "status"}},
        )
        for index, step in enumerate(report["steps"], start=1)
    ]
    workflow_run = store.save_workflow_run(
        create_workflow_run(
            workflow_id=PHASE2_GRADING_WORKFLOW_ID,
            input_ref=str(exam_path),
            reviewer=str(reviewer),
            trace_id=trace_id,
            report_path=None,
            steps=workflow_steps,
        )
    )
    linked_artifacts = []
    for artifact in pre_run_artifacts:
        artifact_record = store.get_artifact(artifact["id"])
        if artifact_record is not None:
            artifact_record.workflowRunId = workflow_run.id
            store.save_artifact(artifact_record)
            linked_artifacts.append(artifact_record.to_dict())
    return ok(
        "Phase 2 Grading Mock Workflow 已执行，评分 DSL 等待人工审核",
        {
            "mode": "MOCK_ONLY",
            "report": report,
            "workflowRun": workflow_run.to_dict(),
            "createdTasks": [task.to_dict() for task in tasks.values()],
            "artifacts": linked_artifacts,
            "generatedDsl": report["generatedDsl"],
            "reviewSummary": report["reviewSummary"],
            "safety": report["safety"],
        },
        trace_id,
    )


def run_phase2_ppt_workflow(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    input_value = payload.get("input")
    if not input_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "缺少参数"}], trace_id)
    reviewer = payload.get("reviewer")
    if not reviewer:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}], trace_id)
    input_path = resolve_local_path(str(input_value))
    if not input_path.exists() or not input_path.is_file():
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "文件不存在"}], trace_id)
    try:
        report = run_phase2_ppt_generation(
            input_path=input_path,
            reviewer=str(reviewer),
            trace_id=trace_id,
            root=ROOT,
        )
    except PptWorkflowInputError as exc:
        return ppt_workflow_input_fail(exc, trace_id)
    except ProviderError as exc:
        return provider_error_response(exc, trace_id)
    tasks = create_phase2_ppt_tasks(store, report=report, trace_id=trace_id)
    link_phase2_ppt_tasks(report, tasks)
    provider_audit_events = save_provider_bundle_audits(
        store,
        bundle=report["providerGenerations"],
        actor="backend-mock",
        trace_id=trace_id,
        workflow_id=PHASE2_PPT_WORKFLOW_ID,
        step_names=PHASE2_PPT_STEP_BY_KIND,
        task_ids={kind: task.id for kind, task in tasks.items()},
    )
    for step in report["steps"]:
        kind = step.get("kind")
        if kind in provider_audit_events:
            step["providerCallAuditEvent"] = provider_audit_events[kind]
            report["generatedDsl"][kind]["providerCallAuditEvent"] = provider_audit_events[kind]
    report["providerCallAuditEvents"] = provider_audit_events

    pre_run_artifacts = save_phase2_ppt_artifacts(
        store,
        report=report,
        input_path=input_path,
        tasks=tasks,
        trace_id=trace_id,
    )
    workflow_steps = [
        create_workflow_step(
            step["name"],
            index,
            {key: value for key, value in step.items() if key not in {"name", "status"}},
        )
        for index, step in enumerate(report["steps"], start=1)
    ]
    workflow_run = store.save_workflow_run(
        create_workflow_run(
            workflow_id=PHASE2_PPT_WORKFLOW_ID,
            input_ref=str(input_path),
            reviewer=str(reviewer),
            trace_id=trace_id,
            report_path=None,
            steps=workflow_steps,
        )
    )
    linked_artifacts = []
    for artifact in pre_run_artifacts:
        artifact_record = store.get_artifact(artifact["id"])
        if artifact_record is not None:
            artifact_record.workflowRunId = workflow_run.id
            store.save_artifact(artifact_record)
            linked_artifacts.append(artifact_record.to_dict())
    return ok(
        "Phase 2 PPT Mock Workflow 已执行，PPT DSL 等待人工审核",
        {
            "mode": "MOCK_ONLY",
            "report": report,
            "workflowRun": workflow_run.to_dict(),
            "materialAnalysis": report["materialAnalysis"],
            "slidePlan": report["slidePlan"],
            "createdTasks": [task.to_dict() for task in tasks.values()],
            "artifacts": linked_artifacts,
            "generatedDsl": report["generatedDsl"],
            "reviewSummary": report["reviewSummary"],
            "safety": report["safety"],
        },
        trace_id,
    )


def generate_with_provider(provider_id: str, payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    prompt_id = str(payload["promptId"]) if payload.get("promptId") else None
    output_kind = str(payload["outputKind"]) if payload.get("outputKind") else None
    input_ref = str(payload["inputRef"]) if payload.get("inputRef") else None
    if provider_id != "mock":
        exc = ProviderError(
            "PROVIDER_DISABLED",
            "Phase 1 只启用 Mock Provider",
            [{"field": "provider", "reason": f"{provider_id} is disabled"}],
        )
        save_provider_call_audit(
            store,
            operation="generateJson",
            provider_id=provider_id,
            status=ProviderCallStatus.FAILED,
            actor="backend-mock",
            trace_id=trace_id,
            prompt_id=prompt_id,
            output_kind=output_kind,
            input_ref=input_ref,
            error_code=exc.code,
            error_field=provider_error_field(exc),
            error_message=exc.message,
        )
        return provider_fail(exc, trace_id, operation="generateJson", provider_id=provider_id)
    if not prompt_id:
        save_provider_call_audit(
            store,
            operation="generateJson",
            provider_id=provider_id,
            status=ProviderCallStatus.FAILED,
            actor="backend-mock",
            trace_id=trace_id,
            error_code="VALIDATION_ERROR",
            error_field="promptId",
            error_message="参数错误",
        )
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "promptId", "reason": "缺少参数"}], trace_id)
    try:
        result = invoke_provider(
            "generateJson",
            prompt_id=prompt_id,
            output_kind=output_kind,
            input_ref=input_ref,
            trace_id=trace_id,
            root=ROOT,
        )
    except ProviderError as exc:
        save_provider_call_audit(
            store,
            operation="generateJson",
            provider_id=provider_id,
            status=ProviderCallStatus.FAILED,
            actor="backend-mock",
            trace_id=trace_id,
            prompt_id=prompt_id,
            output_kind=output_kind,
            input_ref=input_ref,
            error_code=exc.code,
            error_field=provider_error_field(exc),
            error_message=exc.message,
        )
        return provider_fail(exc, trace_id, operation="generateJson", provider_id=provider_id)
    audit_event = save_provider_call_audit(
        store,
        operation="generateJson",
        provider_id=provider_id,
        status=ProviderCallStatus.SUCCESS,
        actor="backend-mock",
        trace_id=trace_id,
        prompt_id=prompt_id,
        output_kind=output_kind,
        input_ref=input_ref,
        result=result,
    )
    return ok("Mock Provider 已生成 DSL 引用，等待人工审核", {**result, "providerCallAuditEvent": audit_event}, trace_id)


def analyze_material_request(payload: dict[str, Any], store: JsonTaskStore, trace_id: str) -> dict[str, Any]:
    input_value = payload.get("input")
    if not input_value:
        return fail("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "缺少参数"}], trace_id)
    input_path = resolve_local_path(str(input_value))
    try:
        analysis = analyze_material(input_path, trace_id=trace_id)
    except MaterialAnalysisError as exc:
        return material_fail(exc, trace_id)
    artifact = save_artifact(
        store,
        kind=ArtifactKind.MATERIAL_ANALYSIS,
        path=str(input_path),
        title=analysis["title"],
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        source_ref=str(input_path),
        metadata={
            "fileType": analysis["fileType"],
            "riskCount": analysis["riskCount"],
            "unknownShellExecuted": analysis["unknownShellExecuted"],
        },
    )
    return ok("素材分析完成", {"analysis": analysis, "artifact": artifact}, trace_id)


def _require_string(payload: dict[str, Any], field: str) -> tuple[str | None, dict[str, Any] | None]:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        return None, {"field": field, "reason": "缺少参数"}
    return value, None


def _optional_positive_int(
    payload: dict[str, Any],
    field: str,
    default: int,
) -> tuple[int, dict[str, str] | None]:
    raw_value = payload.get(field)
    if raw_value is None:
        return default, None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default, {"field": field, "reason": "必须是正整数"}
    if value <= 0:
        return default, {"field": field, "reason": "必须是正整数"}
    return value, None


def create_high_risk_mcp_intent(
    intent_type: str,
    payload: dict[str, Any],
    store: JsonTaskStore,
    trace_id: str,
) -> dict[str, Any]:
    actor = str(payload.get("actor") or "mcp-server-mock")
    reason = str(payload.get("reason") or "MCP high-risk action requires human review")
    request_id = f"intent_{uuid4().hex[:12]}"

    if intent_type == "publish_lab":
        resource_id, error = _require_string(payload, "labId")
        task_type = "MCP_PUBLISH_LAB_INTENT"
        title = f"发布实验待审核：{resource_id}" if resource_id else "发布实验待审核"
        input_type = "Lab"
        resource_type = OperationResourceType.LAB
        action = OperationAction.PUBLISH_LAB_INTENT
        risk_level = "high"
        requires_second_confirmation = False
    elif intent_type == "publish_exam":
        resource_id, error = _require_string(payload, "examId")
        task_type = "MCP_PUBLISH_EXAM_INTENT"
        title = f"发布考试待审核：{resource_id}" if resource_id else "发布考试待审核"
        input_type = "Exam"
        resource_type = OperationResourceType.EXAM
        action = OperationAction.PUBLISH_EXAM_INTENT
        risk_level = "high"
        requires_second_confirmation = False
    elif intent_type == "destroy_environment":
        resource_id, error = _require_string(payload, "environmentId")
        task_type = "MCP_DESTROY_ENVIRONMENT_INTENT"
        title = f"销毁环境待审核：{resource_id}" if resource_id else "销毁环境待审核"
        input_type = "Environment"
        resource_type = OperationResourceType.ENVIRONMENT
        action = OperationAction.DESTROY_ENVIRONMENT_INTENT
        risk_level = "critical"
        requires_second_confirmation = True
    else:
        return fail("NOT_FOUND", "高风险 MCP 意图不存在", [{"field": "intentType", "reason": intent_type}], trace_id)

    if error:
        return fail("VALIDATION_ERROR", "参数错误", [error], trace_id)

    task = create_waiting_review_task(
        task_type=task_type,
        title=title,
        input_type=input_type,
        input_ref=resource_id,
        trace_id=trace_id,
    )
    task.createdBy = actor
    task.intermediateResultPath = f"memory://{request_id}"
    store.save(task)

    detail = {
        "intentType": intent_type,
        "requestId": request_id,
        "reason": reason,
        "riskLevel": risk_level,
        "reviewRequired": True,
        "requiresSecondConfirmation": requires_second_confirmation,
        "createdTaskId": task.id,
        "realActionExecuted": False,
        "realPublish": False,
        "realCloudResourceChanged": False,
        "environmentDestroyed": False,
        "autoPublishAllowed": False,
        "blockedUntilApproved": True,
        "blockedActions": [
            "realPublish",
            "autoPublish",
            "destroyRealCloudResource",
            "bypassHumanReview",
        ],
    }
    audit_event = create_operation_audit_event(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor=actor,
        trace_id=trace_id,
        before_state=None,
        after_state=TaskStatus.WAITING_REVIEW.value,
        detail=detail,
    )
    store.save_operation_audit_event(audit_event)

    return ok(
        "高风险 MCP 操作已创建待审核意图",
        {
            "intent": {
                "id": request_id,
                "type": intent_type,
                "resourceId": resource_id,
                "status": TaskStatus.WAITING_REVIEW.value,
                "riskLevel": risk_level,
                "reviewRequired": True,
                "requiresSecondConfirmation": requires_second_confirmation,
                "blockedUntilApproved": True,
                "realActionExecuted": False,
                "realPublish": False,
                "realCloudResourceChanged": False,
                "environmentDestroyed": False,
                "autoPublishAllowed": False,
            },
            "task": task.to_dict(),
            "operationAuditEvent": audit_event.to_dict(),
            "mode": "MOCK_ONLY",
            "safety": {
                "realActionExecuted": False,
                "realPublish": False,
                "realCloudResourceChanged": False,
                "environmentDestroyed": False,
                "autoPublishAllowed": False,
            },
        },
        trace_id,
    )


def handle_request(
    method: str,
    raw_path: str,
    *,
    store_path: Path | None = None,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    trace_id = make_trace_id()
    method = method.upper()
    parsed = urlparse(raw_path)
    path = parsed.path.rstrip("/") or "/"
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
    auth_error = validate_backend_api_auth(headers=headers, path=path, trace_id=trace_id)
    if auth_error:
        return auth_error
    store = JsonTaskStore(store_path)
    review_action = parse_review_action(path)
    backend_core_review_action = parse_backend_core_review_action(path)
    environment_action = parse_environment_action(path)
    environment_create = parse_environment_create(path)
    provider_health = parse_provider_health(path)
    provider_generate = parse_provider_generate(path)

    high_risk_mcp_intents = {
        "/api/mcp/intents/publish-lab": "publish_lab",
        "/api/mcp/intents/publish-exam": "publish_exam",
        "/api/mcp/intents/destroy-environment": "destroy_environment",
    }
    high_risk_mcp_intent = high_risk_mcp_intents.get(path)

    if method == "GET" and path == "/api/mcp/server/info":
        from mcp_server import McpToolError, initialize_mcp_server

        try:
            return ok("MCP Server Mock 初始化完成", initialize_mcp_server(ROOT, profile=query.get("profile")), trace_id)
        except McpToolError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)

    if method == "GET" and path == "/api/mcp/server/tools":
        from mcp_server import McpToolError, list_server_tools

        try:
            return ok("查询成功", list_server_tools(ROOT, profile=query.get("profile")), trace_id)
        except McpToolError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)

    if method == "POST" and path == "/api/mcp/server/call":
        from mcp_server import McpToolError, call_server_tool

        payload = body or {}
        tool_name = payload.get("tool")
        if not tool_name:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "tool", "reason": "缺少参数"}], trace_id)
        arguments = payload.get("arguments", {})
        if not isinstance(arguments, dict):
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "arguments", "reason": "必须是对象"}], trace_id)
        try:
            response = call_server_tool(
                str(tool_name),
                arguments,
                store_path=store_path,
                root=ROOT,
                actor="backend-mcp-server",
                trace_id=trace_id,
                profile=str(payload.get("profile") or "local-core-mvp"),
            )
        except McpToolError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok(
            "MCP Server Mock Tool 调用完成",
            {
                "tool": str(tool_name),
                "arguments": arguments,
                "response": response,
                "mode": "MOCK_ONLY",
                "realMcpServerStarted": False,
                "realAgentStarted": False,
                "networkListenerStarted": False,
            },
            trace_id,
        )

    if method == "POST" and high_risk_mcp_intent:
        return create_high_risk_mcp_intent(high_risk_mcp_intent, body or {}, store, trace_id)

    if method == "GET" and path == "/api/backend/core-readiness":
        return get_backend_core_readiness_request(query, store, trace_id)

    if method == "GET" and path == "/api/backend/core-db/summary":
        return get_backend_core_repository_summary_request(query, trace_id)

    if method == "GET" and path == "/api/providers/real-llm-runtime-config":
        return ok(
            "真实 LLM 运行时配置摘要已生成，未读取密钥值、未发起请求",
            {"realLlmRuntimeConfig": build_real_llm_runtime_config_summary(root=ROOT)},
            trace_id,
        )

    if method == "POST" and provider_generate:
        return generate_with_provider(provider_generate, body or {}, store, trace_id)

    if method == "POST" and path == "/api/materials/analyze":
        return analyze_material_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/labs/generate":
        return generate_lab(body or {}, store, trace_id)

    if method == "POST" and path == "/api/labs/import-preview":
        return create_lab_template_import_preview_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/labs/mock-import":
        return create_lab_template_mock_import_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/exams/generate-from-lab":
        return generate_exam_from_lab(body or {}, store, trace_id)

    if method == "POST" and path == "/api/exams/import-preview":
        return create_exam_question_import_preview_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/exams/mock-import":
        return create_exam_question_mock_import_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/run":
        return run_grading(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/readonly-evidence":
        return run_readonly_grading_evidence(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/controlled-evidence":
        return run_controlled_grading_evidence(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/evidence-merge":
        return merge_grading_evidence_reports(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/evidence-auto":
        return run_grading_evidence_auto(body or {}, store, trace_id)

    if method == "POST" and path == "/api/teaching-packages/export":
        payload = body or {}
        if "output" in payload:
            return fail(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "output", "reason": "API 不接受输出路径"}],
                trace_id,
            )
        try:
            result = export_teaching_package(
                store,
                workflow_run_id=str(payload.get("workflowRunId") or ""),
                reviewer=str(payload.get("reviewer") or ""),
                trace_id=trace_id,
            )
        except TeachingPackageExportError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("教学包已导出到本地工作区", {"teachingPackageExport": result}, trace_id)

    if method == "POST" and path == "/api/backend/core-db/init":
        return initialize_backend_core_repository_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/backend/core-db/sync-local":
        return sync_backend_core_repository_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/backend/core-tasks":
        return create_backend_core_task_request(body or {}, trace_id)

    if method == "GET" and path == "/api/backend/core-tasks":
        return list_backend_core_task_request(query, trace_id)

    if method == "GET" and path.startswith("/api/backend/core-tasks/") and parse_backend_core_review_action(path) is None:
        task_id = path.removeprefix("/api/backend/core-tasks/")
        return get_backend_core_task_request(task_id, query, trace_id)

    if method == "POST" and backend_core_review_action:
        task_id, action = backend_core_review_action
        payload = body or {}
        decision = str(payload.get("decision") or "").strip().lower() if action == "review" else action
        return review_backend_core_task_request(task_id, payload, decision=decision, trace_id=trace_id)

    if method == "POST" and path == "/api/grading/db/init":
        return initialize_grading_repository_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/db/sync-local":
        return sync_grading_repository_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/workers/run-once":
        return run_grading_worker_once_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/workers/drain-once":
        return drain_grading_worker_once_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/jobs":
        return create_grading_job_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/jobs/run":
        return run_grading_job_request(body or {}, store, trace_id)

    if method == "POST" and path.startswith("/api/grading/jobs/") and path.endswith("/run"):
        job_id = path.removeprefix("/api/grading/jobs/").removesuffix("/run")
        payload = dict(body or {})
        payload["id"] = job_id
        if query.get("dbPath"):
            payload["dbPath"] = query["dbPath"]
        return run_grading_job_request(payload, store, trace_id)

    if method == "GET" and path == "/api/grading/jobs":
        return list_grading_job_request(query, store, trace_id)

    if method == "GET" and path.startswith("/api/grading/jobs/"):
        job_id = path.removeprefix("/api/grading/jobs/")
        return get_grading_job_request(job_id, store, trace_id, query)

    if method == "POST" and path == "/api/grading/records":
        return create_grading_record_request(body or {}, store, trace_id)

    if method == "GET" and path == "/api/grading/records":
        return list_grading_record_request(query, store, trace_id)

    if method == "POST" and path.startswith("/api/grading/records/") and path.endswith("/review"):
        record_id = path.removeprefix("/api/grading/records/").removesuffix("/review")
        payload = dict(body or {})
        if not payload.get("dbPath") and query.get("dbPath"):
            payload["dbPath"] = query["dbPath"]
        return review_grading_record_request(record_id, payload, store, trace_id)

    if method == "GET" and path.startswith("/api/grading/records/"):
        record_id = path.removeprefix("/api/grading/records/")
        return get_grading_record_request(record_id, store, trace_id, query)

    if method == "POST" and path == "/api/grading/import-preview":
        return create_grading_rule_import_preview_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/grading/mock-import":
        return create_grading_rule_mock_import_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/platform-entities/contract-validate":
        return validate_agent_entity_contract_config_request(body or {}, store, trace_id)

    if method == "POST" and path.startswith("/api/platform-entities/") and path.endswith("/import-dry-run"):
        entity_id = path.removeprefix("/api/platform-entities/").removesuffix("/import-dry-run")
        return build_agent_entity_publish_preview_request(entity_id, body or {}, store, trace_id)

    if method == "POST" and path.startswith("/api/platform-entities/") and path.endswith("/import-send"):
        entity_id = path.removeprefix("/api/platform-entities/").removesuffix("/import-send")
        return agent_internal_publish_request(entity_id, body or {}, store, trace_id)

    if method == "POST" and path.startswith("/api/platform-entities/") and path.endswith("/import-status"):
        entity_id = path.removeprefix("/api/platform-entities/").removesuffix("/import-status")
        return query_agent_publish_status_request(entity_id, body or {}, store, trace_id)

    if method == "POST" and path.startswith("/api/platform-entities/") and path.endswith("/import-result"):
        entity_id = path.removeprefix("/api/platform-entities/").removesuffix("/import-result")
        return record_agent_entity_publish_result_request(entity_id, body or {}, store, trace_id)

    if method == "POST" and path.startswith("/api/platform-entities/") and path.endswith("/signoff"):
        entity_id = path.removeprefix("/api/platform-entities/").removesuffix("/signoff")
        return record_agent_entity_signoff_request(entity_id, body or {}, store, trace_id)

    if (
        method == "POST"
        and path.startswith("/api/platform-entities/")
        and path.endswith("/final-publish-review-decision")
    ):
        entity_id = path.removeprefix("/api/platform-entities/").removesuffix("/final-publish-review-decision")
        return record_agent_entity_final_publish_review_decision_request(entity_id, body or {}, store, trace_id)

    if method == "POST" and path == "/api/ppt/generate":
        return generate_ppt(body or {}, store, trace_id)

    if method == "POST" and path == "/api/ppt/import-preview":
        return create_ppt_deck_import_preview_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/ppt/mock-import":
        return create_ppt_deck_mock_import_request(body or {}, store, trace_id)

    if method == "POST" and path == "/api/workflow/demo":
        return run_workflow_demo(body or {}, store, trace_id)

    if method == "POST" and path == "/api/phase2/workflows/content-generation/run":
        return run_phase2_workflow(body or {}, store, trace_id)

    if method == "POST" and path == "/api/phase2/workflows/exam-conversion/run":
        return run_phase2_exam_workflow(body or {}, store, trace_id)

    if method == "POST" and path == "/api/phase2/workflows/grading-generation/run":
        return run_phase2_grading_workflow(body or {}, store, trace_id)

    if method == "POST" and path == "/api/phase2/workflows/ppt-generation/run":
        return run_phase2_ppt_workflow(body or {}, store, trace_id)

    if method == "POST" and path == "/api/review/real-dsl-revision":
        return create_real_dsl_revision_request(body or {}, trace_id)

    if method == "POST" and path == "/api/review/real-dsl-revision-batch":
        return create_real_dsl_revision_batch_request(body or {}, trace_id)

    if method == "GET" and path == "/api/review/real-dsl-revision-diff-preview":
        return get_real_dsl_revision_diff_preview_request(query, trace_id)

    if method == "POST" and path == "/api/review/real-dsl-revision-decision":
        return create_real_dsl_revision_decision_request(body or {}, trace_id)

    if method == "POST" and path == "/api/review/real-dsl-revision-promote":
        return promote_real_dsl_revision_request(body or {}, trace_id)

    if method == "POST" and path == "/api/review/real-dsl-revision-enqueue":
        return enqueue_real_dsl_revision_request(body or {}, store, trace_id)

    if method == "GET" and path == "/api/workflow-registry":
        return workflow_registry_list_request(query, trace_id)

    if method == "GET" and path.startswith("/api/workflow-registry/"):
        workflow_id = path.removeprefix("/api/workflow-registry/")
        return workflow_registry_get_request(workflow_id, trace_id)

    if method == "POST" and path.startswith("/api/review-tasks/") and path.endswith("/ppt-page-review-status"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/ppt-page-review-status")
        payload = body or {}
        try:
            result = update_ppt_page_review_status(
                store,
                task_id=task_id,
                slide_index=int(payload.get("slideIndex", 0)),
                review_status=str(payload.get("reviewStatus", "")),
                reviewer=str(payload.get("reviewer", "")),
                comment=payload.get("comment"),
                trace_id=trace_id,
            )
        except ValueError:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "slideIndex", "reason": "必须是整数"}], trace_id)
        except PptPageReviewUpdateError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("PPT 页级审核状态已更新", {"pptPageReviewUpdate": result}, trace_id)

    if method == "POST" and path.startswith("/api/review-tasks/") and path.endswith("/revision-request"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/revision-request")
        payload = body or {}
        try:
            result = create_review_revision_request(
                store,
                task_id=task_id,
                reviewer=str(payload.get("reviewer", "")),
                comment=str(payload.get("comment", "")),
                priority=str(payload.get("priority", "NORMAL")),
                target_sections=payload.get("targetSections"),
                requested_changes=payload.get("requestedChanges"),
                trace_id=trace_id,
            )
        except ReviewRevisionRequestError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("修改意见已记录，任务仍等待人工审核", result, trace_id)

    if method == "POST" and path.startswith("/api/review-tasks/") and path.endswith("/regenerate-mock"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/regenerate-mock")
        payload = body or {}
        output = payload.get("output")
        try:
            result = create_review_mock_regeneration(
                store,
                task_id=task_id,
                reviewer=str(payload.get("reviewer", "")),
                revision_request_id=payload.get("revisionRequestId"),
                output_path=Path(str(output)) if output else None,
                trace_id=trace_id,
            )
        except ReviewMockRegenerationError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("Mock 修订草稿已生成，等待人工审核", {"mockRegeneration": result}, trace_id)

    if method == "POST" and path.startswith("/api/review-tasks/") and path.endswith("/decision-note"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/decision-note")
        payload = body or {}
        output = payload.get("output")
        try:
            result = create_review_decision_note(
                store,
                task_id=task_id,
                reviewer=str(payload.get("reviewer", "")),
                decision=str(payload.get("decision", "")),
                reason=payload.get("reason"),
                output_path=Path(str(output)) if output else None,
                trace_id=trace_id,
            )
        except ReviewDecisionNoteError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("审核决策备注已记录，任务状态保持不变", result, trace_id)

    if method == "POST" and review_action:
        task_id, action = review_action
        payload = body or {}
        reviewer = payload.get("reviewer")
        if not reviewer:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}], trace_id)
        reason = payload.get("reason")
        if action == "reject" and not reason:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "reason", "reason": "缺少参数"}], trace_id)
        try:
            core_repository, core_write = prepare_backend_core_write_through(payload)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        task = store.get(task_id)
        if task is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
        pre_approve_review_check = (
            build_pre_approve_review_check(store, task.id) if action == "approve" else None
        )
        try:
            from_status = task.status
            if action == "approve":
                task.transition_to(TaskStatus.APPROVED, reviewer=reviewer)
                message = "审核通过"
                audit_action = ReviewAction.APPROVE
            else:
                task.transition_to(TaskStatus.REJECTED, reviewer=reviewer, reason=reason)
                message = "审核拒绝"
                audit_action = ReviewAction.REJECT
        except ValueError as exc:
            return fail("STATE_TRANSITION_ERROR", "AI Task 状态非法流转", [{"field": "status", "reason": str(exc)}], trace_id)
        store.save(task)
        audit_event = create_review_audit_event(
            task=task,
            action=audit_action,
            actor=str(reviewer),
            from_status=from_status,
            to_status=task.status,
            trace_id=trace_id,
            reason=str(reason) if reason else None,
        )
        store.save_review_audit_event(audit_event)
        operation_action = {
            ReviewAction.APPROVE: OperationAction.REVIEW_APPROVE,
            ReviewAction.REJECT: OperationAction.REVIEW_REJECT,
        }[audit_action]
        operation_event = create_operation_audit_event(
            action=operation_action,
            resource_type=OperationResourceType.AI_TASK,
            resource_id=task.id,
            actor=str(reviewer),
            trace_id=trace_id,
            before_state=from_status.value,
            after_state=task.status.value,
            detail={
                "reviewAuditEventId": audit_event.id,
                "reason": str(reason) if reason else None,
                "preApproveReviewCheck": pre_approve_review_check,
            },
        )
        store.save_operation_audit_event(operation_event)
        try:
            backend_core_write_through(
                core_repository,
                core_write,
                task=task,
                review_audit_event=audit_event,
                operation_audit_event=operation_event,
            )
        except CoreRepositoryError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        data = {
            "task": task.to_dict(),
            "auditEvent": audit_event.to_dict(),
            "operationAuditEvent": operation_event.to_dict(),
            "mode": "MOCK_ONLY",
        }
        if core_write is not None:
            data["backendCoreWriteThrough"] = core_write
        if pre_approve_review_check is not None:
            data["preApproveReviewCheck"] = pre_approve_review_check
        return ok(message, data, trace_id)

    if method == "POST" and environment_action:
        env_id, action = environment_action
        environment = store.get_environment(env_id)
        if environment is None:
            return fail("NOT_FOUND", "环境不存在", [{"field": "id", "reason": "未找到环境"}], trace_id)
        next_status = {
            "start": EnvironmentStatus.RUNNING,
            "stop": EnvironmentStatus.STOPPED,
            "reset": EnvironmentStatus.RESETTING,
        }[action]
        try:
            from_status = environment.status
            environment.transition_to(next_status)
            if action == "reset":
                environment.transition_to(EnvironmentStatus.STOPPED)
        except ValueError as exc:
            return fail("STATE_TRANSITION_ERROR", "环境状态非法流转", [{"field": "status", "reason": str(exc)}], trace_id)
        store.save_environment(environment)
        audit_action = {
            "start": OperationAction.ENV_START,
            "stop": OperationAction.ENV_STOP,
            "reset": OperationAction.ENV_RESET,
        }[action]
        audit_event = create_operation_audit_event(
            action=audit_action,
            resource_type=OperationResourceType.ENVIRONMENT,
            resource_id=environment.id,
            actor="backend-mock",
            trace_id=trace_id,
            before_state=from_status.value,
            after_state=environment.status.value,
            detail={"realCloudResourceChanged": False},
        )
        store.save_operation_audit_event(audit_event)
        return ok(
            "Mock 环境状态已更新",
            {
                "environment": environment.to_dict(),
                "operationAuditEvent": audit_event.to_dict(),
                "mode": "MOCK_ONLY",
                "note": "Phase 1 仅更新本地状态，不操作真实资源",
            },
            trace_id,
        )

    if method == "POST" and environment_create:
        return create_environment(environment_create, body or {}, store, trace_id)

    if review_action:
        return fail("METHOD_NOT_ALLOWED", "审核动作仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if environment_action:
        return fail("METHOD_NOT_ALLOWED", "环境动作仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if environment_create:
        return fail("METHOD_NOT_ALLOWED", "环境创建仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if high_risk_mcp_intent:
        return fail("METHOD_NOT_ALLOWED", "高风险 MCP 意图仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if provider_generate:
        return fail("METHOD_NOT_ALLOWED", "Provider 生成仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/materials/analyze":
        return fail("METHOD_NOT_ALLOWED", "素材分析仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/backend/core-readiness":
        return fail("METHOD_NOT_ALLOWED", "Backend 核心 API readiness 仅支持 GET", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/backend/core-db/summary":
        return fail("METHOD_NOT_ALLOWED", "Backend Core 本地 SQLite 摘要仅支持 GET", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/backend/core-db/init":
        return fail("METHOD_NOT_ALLOWED", "Backend Core 本地 SQLite 初始化仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/backend/core-db/sync-local":
        return fail("METHOD_NOT_ALLOWED", "Backend Core 本地 SQLite 同步仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/backend/core-tasks":
        return fail("METHOD_NOT_ALLOWED", "Backend Core AI Task 列表支持 GET，创建支持 POST", [{"field": "method", "reason": method}], trace_id)

    if backend_core_review_action:
        return fail("METHOD_NOT_ALLOWED", "Backend Core AI Task 审核仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path.startswith("/api/backend/core-tasks/"):
        return fail("METHOD_NOT_ALLOWED", "Backend Core AI Task 详情仅支持 GET，审核仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/labs/generate":
        return fail("METHOD_NOT_ALLOWED", "实验生成仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/labs/import-preview":
        return fail("METHOD_NOT_ALLOWED", "Lab 模板导入预览仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/labs/mock-import":
        return fail("METHOD_NOT_ALLOWED", "Lab 模板 Mock 入库仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/exams/generate-from-lab":
        return fail("METHOD_NOT_ALLOWED", "试题生成仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/exams/import-preview":
        return fail("METHOD_NOT_ALLOWED", "Exam 试题导入预览仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/exams/mock-import":
        return fail("METHOD_NOT_ALLOWED", "Exam 试题 Mock 入库仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/run":
        return fail("METHOD_NOT_ALLOWED", "评分运行仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/readonly-evidence":
        return fail("METHOD_NOT_ALLOWED", "只读评分 evidence 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/controlled-evidence":
        return fail("METHOD_NOT_ALLOWED", "受控 Docker 评分 evidence 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/evidence-merge":
        return fail("METHOD_NOT_ALLOWED", "评分 evidence 合并仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/evidence-auto":
        return fail("METHOD_NOT_ALLOWED", "自动评分 evidence 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/db/init":
        return fail("METHOD_NOT_ALLOWED", "Grading 本地 SQLite 初始化仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/db/sync-local":
        return fail("METHOD_NOT_ALLOWED", "Grading 本地 SQLite 同步仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/workers/run-once":
        return fail("METHOD_NOT_ALLOWED", "Grading 本地 worker 单次运行仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/jobs":
        return fail("METHOD_NOT_ALLOWED", "Grading 评分任务列表支持 GET，创建支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/jobs/run":
        return fail("METHOD_NOT_ALLOWED", "Grading 评分任务运行仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path.startswith("/api/grading/jobs/") and path.endswith("/run"):
        return fail("METHOD_NOT_ALLOWED", "Grading 评分任务运行仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path.startswith("/api/grading/jobs/"):
        return fail("METHOD_NOT_ALLOWED", "Grading 评分任务详情仅支持 GET", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/records":
        return fail("METHOD_NOT_ALLOWED", "Grading 评分记录列表支持 GET，创建支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path.startswith("/api/grading/records/") and path.endswith("/review"):
        return fail("METHOD_NOT_ALLOWED", "Grading 评分记录复核仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path.startswith("/api/grading/records/"):
        return fail("METHOD_NOT_ALLOWED", "Grading 评分记录详情仅支持 GET", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/import-preview":
        return fail("METHOD_NOT_ALLOWED", "Grading 评分规则导入预览仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/grading/mock-import":
        return fail("METHOD_NOT_ALLOWED", "Grading 评分规则 Mock 入库仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/ppt/generate":
        return fail("METHOD_NOT_ALLOWED", "PPT 生成仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/ppt/import-preview":
        return fail("METHOD_NOT_ALLOWED", "PPT 课件导入预览仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/ppt/mock-import":
        return fail("METHOD_NOT_ALLOWED", "PPT 课件 Mock 入库仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/workflow/demo":
        return fail("METHOD_NOT_ALLOWED", "Workflow Demo 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/phase2/workflows/content-generation/run":
        return fail("METHOD_NOT_ALLOWED", "Phase 2 Workflow 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/phase2/workflows/exam-conversion/run":
        return fail("METHOD_NOT_ALLOWED", "Phase 2 Exam Workflow 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/phase2/workflows/grading-generation/run":
        return fail("METHOD_NOT_ALLOWED", "Phase 2 Grading Workflow 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/phase2/workflows/ppt-generation/run":
        return fail("METHOD_NOT_ALLOWED", "Phase 2 PPT Workflow 仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/workflow-registry" or path.startswith("/api/workflow-registry/"):
        return fail("METHOD_NOT_ALLOWED", "Workflow Registry 仅支持 GET", [{"field": "method", "reason": method}], trace_id)

    if method != "GET" and path == "/api/review/real-dsl-preview":
        return fail("METHOD_NOT_ALLOWED", "真实 DSL 审核预览仅支持 GET", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/review/real-dsl-revision":
        return fail("METHOD_NOT_ALLOWED", "真实 DSL 修订草稿仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/review/real-dsl-revision-batch":
        return fail("METHOD_NOT_ALLOWED", "真实 DSL 批量修订草稿仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/review/real-dsl-revision-diff-preview":
        return fail("METHOD_NOT_ALLOWED", "真实 DSL 修订差异预览仅支持 GET", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/review/real-dsl-revision-decision":
        return fail("METHOD_NOT_ALLOWED", "真实 DSL 修订审核决策仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/review/real-dsl-revision-promote":
        return fail("METHOD_NOT_ALLOWED", "真实 DSL 修订候选提升仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/review/real-dsl-revision-enqueue":
        return fail("METHOD_NOT_ALLOWED", "真实 DSL 修订候选入队仅支持 POST", [{"field": "method", "reason": method}], trace_id)

    if method != "GET":
        return fail("METHOD_NOT_ALLOWED", "不支持的 Phase 1 Mock API 方法或路由", [{"field": "method", "reason": method}], trace_id)

    if path == "/api/health":
        return ok("OK", {"status": "UP", "mode": "MOCK_ONLY"}, trace_id)

    if path == "/api/providers":
        try:
            registry = build_provider_registry(ROOT)
        except ProviderError as exc:
            save_provider_call_audit(
                store,
                operation="registry",
                provider_id="mock",
                status=ProviderCallStatus.FAILED,
                actor="backend-mock",
                trace_id=trace_id,
                error_code=exc.code,
                error_field=provider_error_field(exc),
                error_message=exc.message,
            )
            return provider_fail(exc, trace_id, operation="registry", provider_id="mock")
        audit_event = save_provider_call_audit(
            store,
            operation="registry",
            provider_id="mock",
            status=ProviderCallStatus.SUCCESS,
            actor="backend-mock",
            trace_id=trace_id,
            detail={"activeProvider": registry.get("activeProvider"), "providerCount": len(registry.get("providers", []))},
        )
        return ok("查询成功", {**registry, "providerCallAuditEvent": audit_event}, trace_id)

    if provider_health:
        try:
            health = get_provider_health(provider_health, ROOT)
        except ProviderError as exc:
            save_provider_call_audit(
                store,
                operation="health",
                provider_id=provider_health,
                status=ProviderCallStatus.FAILED,
                actor="backend-mock",
                trace_id=trace_id,
                error_code=exc.code,
                error_field=provider_error_field(exc),
                error_message=exc.message,
            )
            return provider_fail(exc, trace_id, operation="health", provider_id=provider_health)
        audit_event = save_provider_call_audit(
            store,
            operation="health",
            provider_id=provider_health,
            status=ProviderCallStatus.SUCCESS,
            actor="backend-mock",
            trace_id=trace_id,
            result=health,
            detail={"providerStatus": health.get("status")},
        )
        return ok("Provider Mock 状态正常", {**health, "providerCallAuditEvent": audit_event}, trace_id)

    if path == "/api/provider-audit-events":
        service = BackendAuditQueryService(store=store, core_service=CORE_SERVICE)
        try:
            result = service.list_provider_call_audit_events(query)
        except BackendAuditQueryServiceError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("查询成功", result, trace_id)

    if path == "/api/mcp-tool-call-records":
        status = query.get("status")
        allowed_statuses = {item.value for item in McpToolCallStatus}
        if status and status not in allowed_statuses:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "status", "reason": "非法状态"}], trace_id)
        records = store.list_mcp_tool_call_records(
            tool_name=query.get("toolName"),
            status=status,
            trace_id=query.get("traceId"),
            actor=query.get("actor"),
            backend_path=query.get("backendPath"),
        )
        return ok(
            "查询成功",
            {
                "items": [record.to_dict() for record in records],
                "total": len(records),
                "filters": {
                    "toolName": query.get("toolName"),
                    "status": status,
                    "traceId": query.get("traceId"),
                    "actor": query.get("actor"),
                    "backendPath": query.get("backendPath"),
                },
                "mode": "MOCK_ONLY",
            },
            trace_id,
        )

    if path == "/api/platform-entities/readiness-report":
        service = BackendAgentEntityService(store=store)
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        try:
            if core_repository is not None:
                grading_records, grading_record_source = read_grading_records_for_platform_readiness(
                    query,
                    source_task_id=query.get("sourceTaskId"),
                )
                return ok(
                    "查询成功",
                    service.readiness_report_from_repository(
                        query,
                        repository=core_repository,
                        db_path_source=core_policy["dbPathSource"],
                        grading_records_override=grading_records,
                        grading_record_source=grading_record_source,
                    ),
                    trace_id,
                )
            return ok("查询成功", service.readiness_report(query), trace_id)
        except (sqlite3.Error, CoreRepositoryError) as exc:
            return fail(
                "BACKEND_CORE_SQLITE_READONLY_ERROR",
                "Backend Core 本地 SQLite 只读查询失败",
                [{"field": "coreDbPath", "reason": str(exc)}],
                trace_id,
            )
        except GradingRepositoryError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        except BackendAgentEntityServiceError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)

    if path == "/api/platform-entities":
        service = BackendAgentEntityService(store=store)
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        try:
            result = service.list_entities(query)
        except BackendAgentEntityServiceError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        if core_repository is not None:
            try:
                items = CORE_SERVICE.list_agent_entity_payloads(
                    core_repository,
                    entity_type=query.get("entityType"),
                    source_task_id=query.get("sourceTaskId"),
                    trace_id=query.get("traceId"),
                )
            except (sqlite3.Error, CoreRepositoryError) as exc:
                return fail(
                    "BACKEND_CORE_SQLITE_READONLY_ERROR",
                    "Backend Core 本地 SQLite 只读查询失败",
                    [{"field": "coreDbPath", "reason": str(exc)}],
                    trace_id,
                )
            result.update(
                {
                    "items": items,
                    "total": len(items),
                    "mode": "LOCAL_SQLITE_BACKEND_CORE_READONLY",
                    "coreDbPath": str(core_repository.db_path),
                    "dbPathSource": core_policy["dbPathSource"],
                    "localSqliteRead": True,
                    "productionDatabaseWritten": False,
                    "productionQueueUsed": False,
                }
            )
        return ok("查询成功", result, trace_id)

    if path == "/api/ai-tasks":
        status = query.get("status")
        task_type = query.get("taskType")
        allowed_statuses = {item.value for item in TaskStatus}
        if status and status not in allowed_statuses:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "status", "reason": "非法状态"}], trace_id)
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        if core_repository is not None:
            try:
                task_payloads = CORE_SERVICE.list_ai_task_payloads(
                    core_repository,
                    status=status,
                    task_type=task_type,
                )
            except (sqlite3.Error, CoreRepositoryError) as exc:
                return fail(
                    "BACKEND_CORE_SQLITE_READONLY_ERROR",
                    "Backend Core 本地 SQLite 只读查询失败",
                    [{"field": "coreDbPath", "reason": str(exc)}],
                    trace_id,
                )
            return ok(
                "查询成功",
                {
                    "items": task_payloads,
                    "total": len(task_payloads),
                    "filters": {"status": status, "taskType": task_type},
                    "mode": "LOCAL_SQLITE_BACKEND_CORE_READONLY",
                    "coreDbPath": str(core_repository.db_path),
                    "dbPathSource": core_policy["dbPathSource"],
                    "localSqliteRead": True,
                    "productionDatabaseWritten": False,
                    "productionQueueUsed": False,
                },
                trace_id,
            )
        tasks = store.list(status=status, task_type=task_type)
        return ok(
            "查询成功",
            {
                "items": [task.to_dict() for task in tasks],
                "total": len(tasks),
                "filters": {"status": status, "taskType": task_type},
            },
            trace_id,
        )

    if path == "/api/review-tasks":
        status = query.get("status", TaskStatus.WAITING_REVIEW.value)
        task_type = query.get("taskType")
        allowed_statuses = {item.value for item in TaskStatus}
        if status and status not in allowed_statuses:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "status", "reason": "非法状态"}], trace_id)
        tasks = store.list(status=status, task_type=task_type)
        return ok(
            "查询成功",
            {
                "items": [task.to_dict() for task in tasks],
                "total": len(tasks),
                "filters": {"status": status, "taskType": task_type},
                "reviewRequired": status == TaskStatus.WAITING_REVIEW.value,
            },
            trace_id,
        )

    if path == "/api/review-task-summary":
        status = query.get("status", TaskStatus.WAITING_REVIEW.value)
        task_type = query.get("taskType")
        workflow_run_id = query.get("workflowRunId")
        limit_value = query.get("limit")
        detail_mode = query.get("detailMode", "full")
        allowed_statuses = {item.value for item in TaskStatus}
        if status and status not in allowed_statuses:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "status", "reason": "非法状态"}], trace_id)
        if detail_mode not in {"full", "light"}:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "detailMode", "reason": "必须是 full 或 light"}], trace_id)
        try:
            limit = int(limit_value) if limit_value else None
        except ValueError:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "limit", "reason": "必须是整数"}], trace_id)
        if limit is not None and limit < 1:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "limit", "reason": "必须大于等于 1"}], trace_id)
        if workflow_run_id and store.get_workflow_run(workflow_run_id) is None:
            return fail(
                "NOT_FOUND",
                "Workflow Run 不存在",
                [{"field": "workflowRunId", "reason": "未找到运行记录"}],
                trace_id,
            )
        summary = build_review_batch_summary(
            store,
            status=status,
            task_type=task_type,
            limit=limit,
            detail_mode=detail_mode,
            agent_report=query.get("agentReport"),
            workflow_run_id=workflow_run_id,
        )
        return ok("查询成功", {"reviewTaskSummary": summary}, trace_id)

    if path == "/api/grading/result-preview":
        report = query.get("report")
        if not report:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "report", "reason": "缺少参数"}], trace_id)
        max_items_value = query.get("maxItems", "8")
        try:
            max_items = int(max_items_value)
        except ValueError:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "maxItems", "reason": "必须是整数"}], trace_id)
        try:
            preview = build_grading_result_preview(
                store,
                report_path=resolve_local_path(report),
                task_id=query.get("taskId"),
                candidate_id=query.get("candidateId"),
                max_items=max_items,
            )
        except GradingResultPreviewError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("查询成功", {"gradingResultPreview": preview}, trace_id)

    if path == "/api/grading/evidence-readiness":
        report_values = parse_qs(parsed.query).get("report") or []
        if not report_values:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "report", "reason": "缺少参数"}], trace_id)
        task_id = query.get("taskId")
        if task_id and store.get(task_id) is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
        report_paths: list[Path] = []
        reports: list[dict[str, Any]] = []
        try:
            for report_value in report_values:
                report_path = resolve_local_path(report_value)
                report_paths.append(report_path)
                reports.append(load_evidence_report(report_path))
            readiness = build_grading_evidence_readiness(
                reports,
                report_paths=report_paths,
                trace_id=trace_id,
            )
        except EvidenceReadinessError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        readiness["taskId"] = task_id
        return ok("查询成功", {"gradingEvidenceReadiness": readiness}, trace_id)

    if path == "/api/review/real-dsl-preview":
        return read_real_dsl_review_preview(query, trace_id)

    if path.startswith("/api/review-tasks/") and path.endswith("/second-confirmation-status"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/second-confirmation-status")
        second_confirmation = build_second_confirmation_status(store, task_id)
        if second_confirmation is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
        if not second_confirmation["eligible"]:
            return fail(
                "VALIDATION_ERROR",
                "任务不需要二次确认",
                [{"field": "taskId", "reason": second_confirmation["message"]}],
                trace_id,
            )
        return ok("查询成功", {"secondConfirmationStatus": second_confirmation}, trace_id)

    if path.startswith("/api/review-tasks/") and path.endswith("/ppt-page-review-status"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/ppt-page-review-status")
        detail = build_review_detail(store, task_id, agent_report=query.get("agentReport"))
        if detail is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
        ppt_page_review = detail["pptPageReview"]
        if ppt_page_review.get("eligible") is False:
            return fail(
                "VALIDATION_ERROR",
                "任务不是 PPT 审核任务",
                [{"field": "taskId", "reason": "仅支持 PPT_GENERATION 或 PPT_ARTIFACT_GENERATION"}],
                trace_id,
            )
        return ok("查询成功", {"pptPageReview": ppt_page_review}, trace_id)

    if path.startswith("/api/review-tasks/") and path.endswith("/revision-requests"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/revision-requests")
        if store.get(task_id) is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
        items = list_review_revision_requests(store, task_id=task_id, actor=query.get("actor"))
        return ok(
            "查询成功",
            {
                "items": items,
                "total": len(items),
                "filters": {"taskId": task_id, "actor": query.get("actor")},
                "mode": "MOCK_ONLY",
            },
            trace_id,
        )

    if path.startswith("/api/review-tasks/") and path.endswith("/core-readiness"):
        task_id = path.removeprefix("/api/review-tasks/").removesuffix("/core-readiness")
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        platform_readiness = None
        if core_repository is not None:
            try:
                grading_records, grading_record_source = read_grading_records_for_platform_readiness(
                    query,
                    source_task_id=task_id,
                )
                platform_readiness = BackendAgentEntityService(store=store).readiness_report_from_repository(
                    {"sourceTaskId": task_id},
                    repository=core_repository,
                    db_path_source=core_policy["dbPathSource"],
                    grading_records_override=grading_records,
                    grading_record_source=grading_record_source,
                )["agentEntityReadinessReport"]
            except (sqlite3.Error, CoreRepositoryError, GradingRepositoryError, BackendAgentEntityServiceError) as exc:
                return fail(
                    getattr(exc, "code", "BACKEND_CORE_SQLITE_READONLY_ERROR"),
                    getattr(exc, "message", "Backend Core 本地 SQLite 只读查询失败"),
                    getattr(exc, "errors", [{"field": "coreDbPath", "reason": str(exc)}]),
                    trace_id,
                )
        report = build_core_readiness_report(
            store,
            task_id,
            platform_readiness_override=platform_readiness,
            include_future_platform_steps=str(query.get("includeFuturePlatformFlow") or "").lower()
            in {"1", "true", "yes"},
        )
        if report is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
        return ok("核心闭环就绪报告已生成", {"coreWorkflowReadinessReport": report}, trace_id)

    if path.startswith("/api/review-tasks/"):
        task_id = path.removeprefix("/api/review-tasks/")
        try:
            grading_records_override, grading_records_source = review_detail_grading_records_override(
                query,
                task_id=task_id,
            )
        except GradingRepositoryError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        detail = build_review_detail(
            store,
            task_id,
            agent_report=query.get("agentReport"),
            grading_records_override=grading_records_override,
            grading_records_source=grading_records_source,
        )
        if detail is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "taskId", "reason": "未找到任务"}], trace_id)
        return ok("查询成功", {"reviewDetail": detail}, trace_id)

    if path == "/api/workflow-runs":
        status = query.get("status")
        allowed_statuses = {item.value for item in WorkflowStatus}
        if status and status not in allowed_statuses:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "status", "reason": "非法状态"}], trace_id)
        runs = store.list_workflow_runs(
            workflow_id=query.get("workflowId"),
            status=status,
            trace_id=query.get("traceId"),
        )
        return ok(
            "查询成功",
            {
                "items": [run.to_dict() for run in runs],
                "total": len(runs),
                "filters": {"workflowId": query.get("workflowId"), "status": status, "traceId": query.get("traceId")},
                "mode": "MOCK_ONLY",
            },
            trace_id,
        )

    if path == "/api/artifacts":
        kind = query.get("kind")
        allowed_kinds = {item.value for item in ArtifactKind}
        if kind and kind not in allowed_kinds:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "kind", "reason": "非法产物类型"}], trace_id)
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        if core_repository is not None:
            try:
                artifact_payloads = CORE_SERVICE.list_artifact_payloads(
                    core_repository,
                    kind=kind,
                    task_id=query.get("taskId"),
                    trace_id=query.get("traceId"),
                    workflow_run_id=query.get("workflowRunId"),
                )
            except (sqlite3.Error, CoreRepositoryError) as exc:
                return fail(
                    "BACKEND_CORE_SQLITE_READONLY_ERROR",
                    "Backend Core 本地 SQLite 只读查询失败",
                    [{"field": "coreDbPath", "reason": str(exc)}],
                    trace_id,
                )
            return ok(
                "查询成功",
                {
                    "items": artifact_payloads,
                    "total": len(artifact_payloads),
                    "filters": {
                        "kind": kind,
                        "taskId": query.get("taskId"),
                        "workflowRunId": query.get("workflowRunId"),
                        "traceId": query.get("traceId"),
                    },
                    "mode": "LOCAL_SQLITE_BACKEND_CORE_READONLY",
                    "coreDbPath": str(core_repository.db_path),
                    "dbPathSource": core_policy["dbPathSource"],
                    "localSqliteRead": True,
                    "productionDatabaseWritten": False,
                    "productionQueueUsed": False,
                },
                trace_id,
            )
        artifacts = store.list_artifacts(
            kind=kind,
            task_id=query.get("taskId"),
            workflow_run_id=query.get("workflowRunId"),
            trace_id=query.get("traceId"),
        )
        return ok(
            "查询成功",
            {
                "items": [artifact.to_dict() for artifact in artifacts],
                "total": len(artifacts),
                "filters": {
                    "kind": kind,
                    "taskId": query.get("taskId"),
                    "workflowRunId": query.get("workflowRunId"),
                    "traceId": query.get("traceId"),
                },
                "mode": "MOCK_ONLY",
            },
            trace_id,
        )

    if path == "/api/review-audit-events":
        service = BackendAuditQueryService(store=store, core_service=CORE_SERVICE)
        try:
            result = service.list_review_audit_events(query)
        except BackendAuditQueryServiceError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("查询成功", result, trace_id)

    if path == "/api/audit-events":
        service = BackendAuditQueryService(store=store, core_service=CORE_SERVICE)
        try:
            result = service.list_operation_audit_events(query)
        except BackendAuditQueryServiceError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("查询成功", result, trace_id)

    if path.startswith("/api/ai-tasks/"):
        task_id = path.removeprefix("/api/ai-tasks/")
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        if core_repository is not None:
            try:
                task_payload = CORE_SERVICE.get_ai_task_payload(core_repository, task_id)
            except (sqlite3.Error, CoreRepositoryError) as exc:
                return fail(
                    "BACKEND_CORE_SQLITE_READONLY_ERROR",
                    "Backend Core 本地 SQLite 只读查询失败",
                    [{"field": "coreDbPath", "reason": str(exc)}],
                    trace_id,
                )
            if task_payload is None:
                return fail("NOT_FOUND", "AI Task 不存在", [{"field": "id", "reason": "未找到任务"}], trace_id)
            return ok(
                "查询成功",
                {
                    "task": task_payload,
                    "mode": "LOCAL_SQLITE_BACKEND_CORE_READONLY",
                    "coreDbPath": str(core_repository.db_path),
                    "dbPathSource": core_policy["dbPathSource"],
                    "localSqliteRead": True,
                    "productionDatabaseWritten": False,
                    "productionQueueUsed": False,
                },
                trace_id,
            )
        task = store.get(task_id)
        if task is None:
            return fail("NOT_FOUND", "AI Task 不存在", [{"field": "id", "reason": "未找到任务"}], trace_id)
        return ok("查询成功", {"task": task.to_dict()}, trace_id)

    if path.startswith("/api/workflow-runs/"):
        run_id = path.removeprefix("/api/workflow-runs/")
        run = store.get_workflow_run(run_id)
        if run is None:
            return fail("NOT_FOUND", "Workflow Run 不存在", [{"field": "id", "reason": "未找到运行记录"}], trace_id)
        return ok("查询成功", {"workflowRun": run.to_dict()}, trace_id)

    if path.startswith("/api/artifacts/"):
        artifact_id = path.removeprefix("/api/artifacts/")
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        if core_repository is not None:
            try:
                artifact_payload = CORE_SERVICE.get_artifact_payload(core_repository, artifact_id)
            except (sqlite3.Error, CoreRepositoryError) as exc:
                return fail(
                    "BACKEND_CORE_SQLITE_READONLY_ERROR",
                    "Backend Core 本地 SQLite 只读查询失败",
                    [{"field": "coreDbPath", "reason": str(exc)}],
                    trace_id,
                )
            if artifact_payload is None:
                return fail("NOT_FOUND", "Artifact 不存在", [{"field": "id", "reason": "未找到产物记录"}], trace_id)
            return ok(
                "查询成功",
                {
                    "artifact": artifact_payload,
                    "mode": "LOCAL_SQLITE_BACKEND_CORE_READONLY",
                    "coreDbPath": str(core_repository.db_path),
                    "dbPathSource": core_policy["dbPathSource"],
                    "localSqliteRead": True,
                    "productionDatabaseWritten": False,
                    "productionQueueUsed": False,
                },
                trace_id,
            )
        artifact = store.get_artifact(artifact_id)
        if artifact is None:
            return fail("NOT_FOUND", "Artifact 不存在", [{"field": "id", "reason": "未找到产物记录"}], trace_id)
        return ok("查询成功", {"artifact": artifact.to_dict()}, trace_id)

    if path.startswith("/api/platform-entities/"):
        entity_id = path.removeprefix("/api/platform-entities/")
        service = BackendAgentEntityService(store=store)
        try:
            core_repository, core_policy = resolve_backend_core_repository(query)
        except CoreRepositoryError as exc:
            return backend_core_repository_error_response(exc, trace_id)
        if core_repository is not None:
            try:
                result = service.get_entity_from_repository(
                    entity_id,
                    repository=core_repository,
                    db_path_source=core_policy["dbPathSource"],
                )
            except (sqlite3.Error, CoreRepositoryError) as exc:
                return fail(
                    "BACKEND_CORE_SQLITE_READONLY_ERROR",
                    "Backend Core 本地 SQLite 只读查询失败",
                    [{"field": "coreDbPath", "reason": str(exc)}],
                    trace_id,
                )
            except BackendAgentEntityServiceError as exc:
                return fail(exc.code, exc.message, exc.errors, trace_id)
            return ok(
                "查询成功",
                result,
                trace_id,
            )
        try:
            result = service.get_entity(entity_id)
        except BackendAgentEntityServiceError as exc:
            return fail(exc.code, exc.message, exc.errors, trace_id)
        return ok("查询成功", result, trace_id)

    if path == "/api/environments":
        status = query.get("status")
        env_type = query.get("type")
        allowed_statuses = {item.value for item in EnvironmentStatus}
        allowed_types = {item.value for item in EnvironmentType}
        if status and status not in allowed_statuses:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "status", "reason": "非法状态"}], trace_id)
        if env_type and env_type not in allowed_types:
            return fail("VALIDATION_ERROR", "参数错误", [{"field": "type", "reason": "非法类型"}], trace_id)
        environments = store.list_environments(status=status, env_type=env_type)
        return ok(
            "查询成功",
            {
                "items": [environment.to_dict() for environment in environments],
                "total": len(environments),
                "filters": {"status": status, "type": env_type},
            },
            trace_id,
        )

    if path.startswith("/api/environments/"):
        env_id = path.removeprefix("/api/environments/")
        environment = store.get_environment(env_id)
        if environment is None:
            return fail("NOT_FOUND", "环境不存在", [{"field": "id", "reason": "未找到环境"}], trace_id)
        return ok("查询成功", {"environment": environment.to_dict()}, trace_id)

    if path == "/api/workflow/report":
        return read_local_report(query, trace_id)

    if path == "/api/grading/report":
        return read_grading_report(query, trace_id, store)

    return fail("NOT_FOUND", "接口不存在", [{"field": "path", "reason": path}], trace_id)
