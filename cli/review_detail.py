"""Review detail aggregation for Phase 1 human review screens."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_workflows.exam_candidate_preview import (
    ExamCandidatePreviewError,
    build_exam_candidate_preview_from_file,
)

from .ai_task import TaskStatus, create_waiting_review_task
from .artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationResourceType, create_operation_audit_event
from .dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from .grading_record import GradingRecord
from .agent_entity_readiness import build_agent_entity_readiness_report
from .agent_publish_activity import build_agent_entity_publish_activity_summary_for_task
from .store import JsonTaskStore
from .workflow import create_workflow_run, create_workflow_step


ROOT = Path(__file__).resolve().parents[1]
DSL_ARTIFACT_KINDS = {"LAB_DSL", "EXAM_DSL", "GRADING_DSL", "PPT_DSL"}
TASK_TYPE_BY_DSL_ARTIFACT_KIND = {
    "LAB_DSL": "LAB_GENERATION_REVISION",
    "EXAM_DSL": "EXAM_GENERATION_REVISION",
    "GRADING_DSL": "GRADING_GENERATION_REVISION",
    "PPT_DSL": "PPT_GENERATION_REVISION",
}
DSL_KIND_BY_ARTIFACT_KIND = {
    "LAB_DSL": "Lab",
    "EXAM_DSL": "Exam",
    "GRADING_DSL": "Grading",
    "PPT_DSL": "PPT",
}
DSL_SCHEMA_KIND_BY_ARTIFACT_KIND = {
    "LAB_DSL": "lab",
    "EXAM_DSL": "exam",
    "GRADING_DSL": "grading",
    "PPT_DSL": "ppt",
}
PLATFORM_IMPORT_PREVIEW_COMPONENTS = {
    "LabTemplateImportPreview": {
        "draftKey": "labTemplateDraft",
        "agentEntity": "lab_template",
        "sourceArtifactKind": "LAB_DSL",
    },
    "ExamQuestionImportPreview": {
        "draftKey": "examQuestionDraft",
        "agentEntity": "exam_question",
        "sourceArtifactKind": "EXAM_DSL",
    },
    "GradingRuleImportPreview": {
        "draftKey": "gradingRuleDraft",
        "agentEntity": "grading_rule",
        "sourceArtifactKind": "GRADING_DSL",
    },
}
GRADING_REVIEW_TASK_TYPES = {"GRADING_GENERATION", "GRADING_GENERATION_REVISION"}
PLATFORM_IMPORT_PREVIEW_ACTIONS = {
    "LAB_DSL": {
        "component": "LabTemplateImportPreviewAction",
        "previewComponent": "LabTemplateImportPreview",
        "agentEntity": "lab_template",
        "cliSubcommand": "lab import-preview",
        "apiEndpoint": "POST /api/labs/import-preview",
        "mcpTool": "create_lab_template_import_preview",
        "outputSuggestion": "examples/output/lab-template-import-preview.json",
        "nextRequiredAction": "create_lab_template_import_preview_for_manual_review",
    },
    "EXAM_DSL": {
        "component": "ExamQuestionImportPreviewAction",
        "previewComponent": "ExamQuestionImportPreview",
        "agentEntity": "exam_question",
        "cliSubcommand": "exam import-preview",
        "apiEndpoint": "POST /api/exams/import-preview",
        "mcpTool": "create_exam_question_import_preview",
        "outputSuggestion": "examples/output/exam-question-import-preview.json",
        "nextRequiredAction": "create_exam_question_import_preview_for_manual_review",
    },
    "GRADING_DSL": {
        "component": "GradingRuleImportPreviewAction",
        "previewComponent": "GradingRuleImportPreview",
        "agentEntity": "grading_rule",
        "cliSubcommand": "grade import-preview",
        "apiEndpoint": "POST /api/grading/import-preview",
        "mcpTool": "create_grading_rule_import_preview",
        "outputSuggestion": "examples/output/grading-rule-import-preview.json",
        "nextRequiredAction": "create_grading_rule_import_preview_for_manual_review",
    },
}
PLATFORM_IMPORT_PREVIEW_SIGNOFF_CHECKS = {
    "lab_template": {
        "component": "LabTemplateImportPreviewSignoff",
        "entityCheckId": "confirm_objectives_steps_environment_and_grading_ref",
        "entityCheckLabel": "确认教学目标、实验步骤、环境配置和评分引用可导入平台",
        "requiredReviewerAction": "signoff_lab_template_import_preview_after_manual_check",
    },
    "exam_question": {
        "component": "ExamQuestionImportPreviewSignoff",
        "entityCheckId": "confirm_candidate_answer_hidden_and_grading_refs_teacher_only",
        "entityCheckLabel": "确认标准答案不展示给选手端，评分引用仅教师与平台审核可见",
        "requiredReviewerAction": "signoff_exam_question_import_preview_after_manual_check",
    },
    "grading_rule": {
        "component": "GradingRuleImportPreviewSignoff",
        "entityCheckId": "confirm_sandbox_required_before_real_execution",
        "entityCheckLabel": "确认真实评分执行前仍必须进入沙箱与人工审核边界",
        "requiredReviewerAction": "signoff_grading_rule_import_preview_after_manual_check",
    },
}
PPT_REVIEW_TASK_TYPES = {"PPT_GENERATION", "PPT_ARTIFACT_GENERATION"}
PPT_PAGE_REVIEW_STATUSES = {"APPROVED", "NEEDS_REVIEW", "REVISE_REQUIRED"}
REVISION_REQUEST_PRIORITIES = {"LOW", "NORMAL", "HIGH"}
REAL_DEMO_REPORT_TASK_TYPES = {
    "lab": ("LAB_GENERATION", "markdown", "LAB_DSL", "Lab", "Real LLM Lab DSL"),
    "exam": ("EXAM_GENERATION", "lab_dsl", "EXAM_DSL", "Exam", "Real LLM Exam DSL"),
    "grading": ("GRADING_GENERATION", "exam_dsl", "GRADING_DSL", "Grading", "Real LLM Grading DSL"),
    "ppt": ("PPT_GENERATION", "markdown", "PPT_DSL", "PPT", "Real LLM PPT DSL"),
}
REAL_DEMO_REPORT_FALLBACK_TASK_IDS = {
    "lab": "real_demo_lab",
    "exam": "real_demo_exam",
    "grading": "real_demo_grading",
    "ppt": "real_demo_ppt",
}


class PptPageReviewUpdateError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


class ReviewRevisionRequestError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


class ReviewMockRegenerationError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


class PromotionReviewEnqueueError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]
    return [str(item).strip() for item in raw_items if str(item).strip()]
HIGH_RISK_MCP_INTENT_TASKS = {
    "MCP_PUBLISH_LAB_INTENT": {
        "intentType": "publish_lab",
        "toolName": "publish_lab",
        "resourceType": OperationResourceType.LAB.value,
        "riskLevel": "high",
        "requiresSecondConfirmation": False,
    },
    "MCP_PUBLISH_EXAM_INTENT": {
        "intentType": "publish_exam",
        "toolName": "publish_exam",
        "resourceType": OperationResourceType.EXAM.value,
        "riskLevel": "high",
        "requiresSecondConfirmation": False,
    },
    "MCP_DESTROY_ENVIRONMENT_INTENT": {
        "intentType": "destroy_environment",
        "toolName": "destroy_environment",
        "resourceType": OperationResourceType.ENVIRONMENT.value,
        "riskLevel": "critical",
        "requiresSecondConfirmation": True,
    },
}


def _is_high_risk_mcp_intent(task_type: str | None) -> bool:
    return task_type in HIGH_RISK_MCP_INTENT_TASKS


def _allowed_actions(status: TaskStatus, task_type: str | None = None) -> list[str]:
    if status == TaskStatus.WAITING_REVIEW:
        return ["approve", "reject", "request_revision"]
    if status == TaskStatus.APPROVED and not _is_high_risk_mcp_intent(task_type):
        return ["mock_publish"]
    return []


def _status_value(status: TaskStatus | str) -> str:
    return status.value if isinstance(status, TaskStatus) else status


def _high_risk_post_review_disposition(
    status: TaskStatus | str,
    *,
    requires_second_confirmation: bool,
) -> dict[str, Any]:
    status_value = _status_value(status)
    review_completed = status_value in {
        TaskStatus.APPROVED.value,
        TaskStatus.REJECTED.value,
        TaskStatus.COMPLETED.value,
    }

    if status_value == TaskStatus.WAITING_REVIEW.value:
        state = "WAITING_HUMAN_REVIEW"
        next_required_action = "approve_or_reject"
    elif status_value == TaskStatus.APPROVED.value and requires_second_confirmation:
        state = "APPROVED_PENDING_SECOND_CONFIRMATION"
        next_required_action = "second_confirmation"
    elif status_value == TaskStatus.APPROVED.value:
        state = "APPROVED_EXECUTION_BLOCKED"
        next_required_action = "mock_disposition_only"
    elif status_value == TaskStatus.REJECTED.value:
        state = "REJECTED_CLOSED"
        next_required_action = "none"
    elif status_value == TaskStatus.COMPLETED.value:
        state = "COMPLETED_WITHOUT_REAL_ACTION"
        next_required_action = "none"
    else:
        state = "EXECUTION_BLOCKED"
        next_required_action = "review_or_close"

    return {
        "mode": "MOCK_ONLY",
        "state": state,
        "sourceStatus": status_value,
        "reviewCompleted": review_completed,
        "nextRequiredAction": next_required_action,
        "secondConfirmationRequired": requires_second_confirmation,
        "secondConfirmationSatisfied": False,
        "executionBlocked": True,
        "executeRealActionAllowed": False,
        "executeRealPublishEnabled": False,
        "destroyRealEnvironmentEnabled": False,
        "bypassReviewEnabled": False,
        "realActionExecuted": False,
        "realPublish": False,
        "realCloudResourceChanged": False,
        "environmentDestroyed": False,
        "autoPublishAllowed": False,
    }


def build_review_policy(status: TaskStatus, task_type: str | None = None) -> dict[str, Any]:
    high_risk_intent = _is_high_risk_mcp_intent(task_type)
    config = HIGH_RISK_MCP_INTENT_TASKS.get(task_type or "")
    requires_second_confirmation = bool(config.get("requiresSecondConfirmation")) if config else False
    disposition_state = (
        _high_risk_post_review_disposition(
            status,
            requires_second_confirmation=requires_second_confirmation,
        )["state"]
        if high_risk_intent
        else None
    )
    return {
        "reviewRequired": status == TaskStatus.WAITING_REVIEW,
        "rejectRequiresReason": True,
        "publishBlockedUntilApproved": status not in {TaskStatus.APPROVED, TaskStatus.COMPLETED},
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "allowedActions": _allowed_actions(status, task_type),
        "generatedContentStatus": status.value,
        "highRiskIntent": high_risk_intent,
        "reviewIntentOnly": high_risk_intent,
        "executeRealActionAllowed": False,
        "highRiskIntentExecutionBlocked": high_risk_intent,
        "postReviewDispositionRequired": high_risk_intent,
        "postReviewDispositionState": disposition_state,
        "secondConfirmationRequired": requires_second_confirmation,
        "secondConfirmationSatisfied": False,
    }


def build_review_safety(artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    artifacts = artifacts or []
    real_llm_called = any(bool(artifact.get("realLlmCalled", False)) for artifact in artifacts)
    demo_artifact = any(
        artifact.get("mode") == "REAL_LLM_DEMO_DSL_GENERATION"
        or artifact.get("metadata", {}).get("providerAdapter") == "openai_responses_sdk_demo_adapter"
        for artifact in artifacts
    )
    if demo_artifact:
        mode = "REAL_LLM_DEMO_WORKFLOW"
    elif real_llm_called:
        artifact_kinds = {artifact.get("kind") for artifact in artifacts}
        if {"EXAM_DSL", "GRADING_DSL"}.issubset(artifact_kinds):
            mode = "REAL_LLM_EXAM_GRADING_WORKFLOW"
        elif "LAB_DSL" in artifact_kinds:
            mode = "REAL_LLM_MINIMAL_LAB_WORKFLOW"
        elif "PPT_DSL" in artifact_kinds:
            mode = "REAL_LLM_PPT_WORKFLOW"
        else:
            mode = "REAL_LLM_WORKFLOW"
    else:
        mode = "MOCK_ONLY"
    return {
        "mode": mode,
        "realLlmCalled": real_llm_called,
        "realCloudResourceChanged": False,
        "realCloudResourceCreated": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "realActionExecuted": False,
        "realPublish": False,
        "autoPublishAllowed": False,
        "highRiskIntentExecutionAllowed": False,
        "environmentDestroyed": False,
        "bypassReviewAllowed": False,
        "answerVisibleToCandidate": False,
    }


def _primary_artifact(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    for artifact in artifacts:
        if artifact["kind"] in DSL_ARTIFACT_KINDS:
            return artifact
    return artifacts[0] if artifacts else None


def _promotion_review_artifact(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    for artifact in artifacts:
        metadata = artifact.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("component") == "RealDslRevisionPromotionReviewQueueItem":
            return artifact
    return None


def build_promotion_review_disposition(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    review_policy: dict[str, Any],
) -> dict[str, Any] | None:
    artifact = _promotion_review_artifact(artifacts)
    if artifact is None:
        return None

    status = str(task.get("status") or "")
    if status == TaskStatus.WAITING_REVIEW.value:
        state = "WAITING_HUMAN_REVIEW"
        next_required_action = "approve_or_reject_promoted_candidate"
        review_completed = False
    elif status == TaskStatus.APPROVED.value:
        state = "APPROVED_FOR_MOCK_PUBLISH_ONLY"
        next_required_action = "optional_mock_publish_or_manual_platform_import"
        review_completed = True
    elif status == TaskStatus.REJECTED.value:
        state = "REJECTED_CLOSED"
        next_required_action = "revise_again_or_stop"
        review_completed = True
    elif status == TaskStatus.COMPLETED.value:
        state = "MOCK_PUBLISH_COMPLETED_NO_REAL_PUBLISH"
        next_required_action = "none"
        review_completed = True
    else:
        state = "REVIEW_DISPOSITION_BLOCKED"
        next_required_action = "inspect_task_status"
        review_completed = False

    metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
    return {
        "component": "RealDslRevisionPromotionReviewDisposition",
        "mode": "LOCAL_REAL_DSL_REVISION_PROMOTION_REVIEW",
        "taskId": task.get("id"),
        "taskType": task.get("taskType"),
        "taskStatus": status,
        "state": state,
        "reviewCompleted": review_completed,
        "nextRequiredAction": next_required_action,
        "artifactId": artifact.get("id"),
        "artifactKind": artifact.get("kind"),
        "artifactStatus": artifact.get("status"),
        "promotedPath": artifact.get("path"),
        "promotionReportPath": metadata.get("promotionReportPath"),
        "suggestionId": metadata.get("suggestionId"),
        "schemaValidated": bool(metadata.get("schemaValidated")),
        "allowedActions": review_policy.get("allowedActions", []),
        "mockPublishAvailable": "mock_publish" in set(review_policy.get("allowedActions", [])),
        "manualReviewRequired": status == TaskStatus.WAITING_REVIEW.value,
        "publishBlockedUntilApproved": review_policy.get("publishBlockedUntilApproved", True),
        "realPublishAllowed": False,
        "autoPublishAllowed": False,
        "safety": {
            "realLlmCalled": False,
            "newLlmRequestSent": False,
            "secretsRead": False,
            "networkAccess": False,
            "sourceDslModified": False,
            "revisedDslModified": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
    }


def _platform_import_preview_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for artifact in artifacts:
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        component = metadata.get("component")
        if (
            artifact.get("kind") == "WORKFLOW_REPORT"
            and artifact.get("mode") == "LOCAL_PLATFORM_IMPORT_PREVIEW"
            and component in PLATFORM_IMPORT_PREVIEW_COMPONENTS
        ):
            items.append(artifact)
    return sorted(items, key=lambda item: item.get("createdAt") or "")


def _load_platform_import_preview_payload(artifact: dict[str, Any]) -> dict[str, Any] | None:
    path = _resolve_local_path(artifact.get("path"))
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _operation_event_for_preview_artifact(
    operation_audit_events: list[dict[str, Any]],
    *,
    artifact_id: str | None,
    component: str,
) -> dict[str, Any] | None:
    for event in operation_audit_events:
        detail = event.get("detail", {}) if isinstance(event.get("detail"), dict) else {}
        if artifact_id and detail.get("previewArtifactId") == artifact_id:
            return event
        if detail.get("component") == component:
            return event
    return None


def build_platform_import_preview_summary(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    operation_audit_events: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for artifact in _platform_import_preview_artifacts(artifacts):
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        component = str(metadata.get("component") or "")
        component_config = PLATFORM_IMPORT_PREVIEW_COMPONENTS[component]
        payload = _load_platform_import_preview_payload(artifact) or {}
        draft_key = component_config["draftKey"]
        draft = payload.get(draft_key, {}) if isinstance(payload.get(draft_key), dict) else {}
        import_plan = payload.get("importPlan", {}) if isinstance(payload.get("importPlan"), dict) else {}
        controlled_evidence_next_action = (
            payload.get("controlledEvidenceNextAction")
            if isinstance(payload.get("controlledEvidenceNextAction"), dict)
            else None
        )
        source_artifact_kind = (
            payload.get("sourceArtifactKind")
            or metadata.get("sourceArtifactKind")
            or component_config["sourceArtifactKind"]
        )
        event = _operation_event_for_preview_artifact(
            operation_audit_events,
            artifact_id=artifact.get("id"),
            component=component,
        )
        items.append(
            {
                "component": component,
                "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW",
                "artifactId": artifact.get("id"),
                "artifactPath": artifact.get("path"),
                "artifactStatus": artifact.get("status"),
                "agentEntity": payload.get("agentEntity")
                or metadata.get("agentEntity")
                or component_config["agentEntity"],
                "sourceArtifactId": payload.get("sourceArtifactId") or metadata.get("sourceArtifactId"),
                "sourceArtifactKind": source_artifact_kind,
                "sourceDslPath": payload.get("sourceDslPath") or artifact.get("sourceRef"),
                "schemaValidated": bool(payload.get("schemaValidated") or metadata.get("schemaValidated")),
                "draftKey": draft_key,
                "draftId": draft.get("id"),
                "draftTitle": draft.get("title"),
                "draftStatus": draft.get("status"),
                "reviewChecklist": draft.get("reviewChecklist", []),
                "importPlan": {
                    "strategy": import_plan.get("strategy", "manual_platform_import_after_review"),
                    "writeTarget": import_plan.get("writeTarget", "local_preview_only"),
                    "databaseWritePlanned": bool(import_plan.get("databaseWritePlanned", False)),
                    "apiCallPlanned": bool(import_plan.get("apiCallPlanned", False)),
                    "realAgentImport": bool(import_plan.get("realAgentImport", False)),
                    "manualReviewRequired": bool(import_plan.get("manualReviewRequired", True)),
                    "nextRequiredAction": import_plan.get(
                        "nextRequiredAction",
                        "review_platform_import_preview_before_real_import",
                    ),
                    "evidenceAutoRequiredBeforeFinalImportReview": bool(
                        import_plan.get("evidenceAutoRequiredBeforeFinalImportReview", False)
                    ),
                },
                "controlledEvidenceNextAction": controlled_evidence_next_action,
                "operationAuditEventId": event.get("id") if event else None,
                "databaseWritten": False,
                "realAgentImport": False,
                "realPublishAllowed": False,
            }
        )

    next_required_actions = sorted(
        {
            str(item["importPlan"]["nextRequiredAction"])
            for item in items
            if item.get("importPlan", {}).get("nextRequiredAction")
        }
    )
    return {
        "component": "AgentImportPreviewSummary",
        "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW",
        "visible": bool(items),
        "taskId": task.get("id"),
        "taskStatus": task.get("status"),
        "total": len(items),
        "items": items,
        "agentEntities": sorted({str(item["agentEntity"]) for item in items if item.get("agentEntity")}),
        "sourceArtifactKinds": sorted({str(item["sourceArtifactKind"]) for item in items if item.get("sourceArtifactKind")}),
        "controlledEvidenceNextActionTotal": sum(1 for item in items if item.get("controlledEvidenceNextAction")),
        "nextRequiredActions": next_required_actions,
        "databaseWritten": False,
        "realAgentImport": False,
        "realPublishAllowed": False,
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
    }


def _platform_import_preview_source_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [artifact for artifact in artifacts if artifact.get("kind") in PLATFORM_IMPORT_PREVIEW_ACTIONS]
    return sorted(items, key=lambda item: (item.get("createdAt") or "", item.get("kind") or ""))


def _content_quality_item_for_artifact_kind(
    content_quality_summary: dict[str, Any] | None,
    artifact_kind: str,
) -> dict[str, Any] | None:
    if not isinstance(content_quality_summary, dict) or not content_quality_summary.get("available"):
        return None
    dsl_kind = DSL_SCHEMA_KIND_BY_ARTIFACT_KIND.get(artifact_kind)
    items = content_quality_summary.get("items")
    if not dsl_kind or not isinstance(items, dict):
        return None
    item = items.get(dsl_kind)
    return item if isinstance(item, dict) else None


def _content_quality_recommended_import_action(
    *,
    item: dict[str, Any] | None,
    enabled: bool,
    preview_already_created: bool,
    default_next_action: str,
) -> str:
    if item is None:
        return "review_source_dsl_content_before_import_preview"
    if int(item.get("blockingIssueTotal", 0) or 0) > 0 or item.get("readyForImportPreview") is False:
        return "revise_real_dsl_before_import_preview"
    if preview_already_created:
        return "review_existing_import_preview"
    if not enabled:
        return "approve_task_then_create_import_preview"
    return default_next_action


def build_platform_import_preview_action_panel(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    review_policy: dict[str, Any],
    platform_import_preview: dict[str, Any] | None = None,
    content_quality_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    platform_import_preview = platform_import_preview or build_platform_import_preview_summary(task, artifacts, [])
    content_quality_summary = content_quality_summary if isinstance(content_quality_summary, dict) else _content_quality_summary(artifacts)
    created_preview_components = {
        str(item.get("component"))
        for item in platform_import_preview.get("items", [])
        if item.get("component")
    }
    task_status = str(task.get("status") or "")
    task_id = str(task.get("id") or "<task_id>")
    enabled_by_status = task_status == TaskStatus.APPROVED.value
    items: list[dict[str, Any]] = []

    for artifact in _platform_import_preview_source_artifacts(artifacts):
        artifact_kind = str(artifact.get("kind") or "")
        action_config = PLATFORM_IMPORT_PREVIEW_ACTIONS[artifact_kind]
        preview_component = action_config["previewComponent"]
        enabled = enabled_by_status
        output_suggestion = action_config["outputSuggestion"]
        preview_already_created = preview_component in created_preview_components
        content_quality_item = _content_quality_item_for_artifact_kind(content_quality_summary, artifact_kind)
        content_quality_available = content_quality_item is not None
        content_quality_ready = bool(
            content_quality_item.get("readyForImportPreview") is True if content_quality_item else False
        )
        content_quality_issues = (
            content_quality_item.get("issues", [])
            if isinstance(content_quality_item, dict) and isinstance(content_quality_item.get("issues"), list)
            else []
        )
        cli_command = (
            f"python lab_cli.py {action_config['cliSubcommand']} "
            f"--task-id {task_id} --reviewer <reviewer> --output {output_suggestion}"
        )
        items.append(
            {
                "component": action_config["component"],
                "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW_ACTIONS",
                "enabled": enabled,
                "disabledReason": None if enabled else "requires_approved_task",
                "taskId": task.get("id"),
                "taskStatus": task_status,
                "sourceArtifactId": artifact.get("id"),
                "sourceArtifactKind": artifact_kind,
                "sourceDslPath": artifact.get("path"),
                "sourceArtifactStatus": artifact.get("status"),
                "agentEntity": action_config["agentEntity"],
                "previewComponent": preview_component,
                "previewAlreadyCreated": preview_already_created,
                "cliCommand": cli_command,
                "apiEndpoint": action_config["apiEndpoint"],
                "mcpTool": action_config["mcpTool"],
                "outputSuggestion": output_suggestion,
                "nextRequiredAction": action_config["nextRequiredAction"],
                "contentQualityAvailable": content_quality_available,
                "contentQualityStatus": content_quality_item.get("status") if content_quality_item else None,
                "contentQualityReadyForManualReview": bool(
                    content_quality_item.get("readyForManualReview") is True if content_quality_item else False
                ),
                "contentQualityReadyForImportPreview": content_quality_ready,
                "contentQualityIssueTotal": int(content_quality_item.get("issueTotal", 0) or 0)
                if content_quality_item
                else 0,
                "contentQualityBlockingIssueTotal": int(content_quality_item.get("blockingIssueTotal", 0) or 0)
                if content_quality_item
                else 0,
                "contentQualityIssues": content_quality_issues[:5],
                "contentQualityRecommendedAction": _content_quality_recommended_import_action(
                    item=content_quality_item,
                    enabled=enabled,
                    preview_already_created=preview_already_created,
                    default_next_action=action_config["nextRequiredAction"],
                ),
                "contentQualityAdvisoryOnly": True,
                "requiresReviewer": True,
                "requiresApprovedTask": True,
                "databaseWritten": False,
                "realAgentImport": False,
                "realPublishAllowed": False,
            }
        )

    ready_kinds = [
        DSL_SCHEMA_KIND_BY_ARTIFACT_KIND.get(str(item.get("sourceArtifactKind") or ""))
        for item in items
        if item.get("contentQualityReadyForImportPreview") is True
    ]
    blocked_kinds = [
        DSL_SCHEMA_KIND_BY_ARTIFACT_KIND.get(str(item.get("sourceArtifactKind") or ""))
        for item in items
        if item.get("contentQualityAvailable") is True and item.get("contentQualityReadyForImportPreview") is not True
    ]
    return {
        "component": "AgentImportPreviewActionPanel",
        "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW_ACTIONS",
        "visible": bool(items),
        "enabled": any(bool(item["enabled"]) for item in items),
        "taskId": task.get("id"),
        "taskStatus": task_status,
        "reviewPolicyAllowedActions": review_policy.get("allowedActions", []),
        "total": len(items),
        "enabledTotal": sum(1 for item in items if item["enabled"]),
        "previewAlreadyCreatedTotal": sum(1 for item in items if item["previewAlreadyCreated"]),
        "contentQualityAvailable": bool(content_quality_summary.get("available")) if content_quality_summary else False,
        "contentQualityStatus": content_quality_summary.get("status") if content_quality_summary else None,
        "contentQualityAdvisoryOnly": True,
        "contentQualityReadyTotal": sum(1 for item in items if item.get("contentQualityReadyForImportPreview") is True),
        "contentQualityBlockedTotal": sum(
            1
            for item in items
            if item.get("contentQualityAvailable") is True
            and item.get("contentQualityReadyForImportPreview") is not True
        ),
        "contentQualityIssueTotal": sum(int(item.get("contentQualityIssueTotal", 0) or 0) for item in items),
        "contentQualityBlockingIssueTotal": sum(
            int(item.get("contentQualityBlockingIssueTotal", 0) or 0) for item in items
        ),
        "contentQualityReadyForImportPreviewKinds": [kind for kind in ready_kinds if kind],
        "contentQualityBlockedForImportPreviewKinds": [kind for kind in blocked_kinds if kind],
        "approvalStillRequired": True,
        "items": items,
        "nextRequiredActions": [
            item["nextRequiredAction"] for item in items if item.get("enabled") and not item.get("previewAlreadyCreated")
        ],
        "databaseWritten": False,
        "realAgentImport": False,
        "realPublishAllowed": False,
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
    }


def _platform_import_preview_signoff_checks(item: dict[str, Any]) -> list[dict[str, Any]]:
    agent_entity = str(item.get("agentEntity") or "")
    entity_config = PLATFORM_IMPORT_PREVIEW_SIGNOFF_CHECKS.get(agent_entity, {})
    checks = [
        {
            "id": "confirm_draft_title_and_entity",
            "label": "确认平台草稿标题、实体类型和来源 DSL 对应正确",
            "status": "NEEDS_HUMAN_SIGNOFF",
            "evidence": {
                "draftTitle": item.get("draftTitle"),
                "draftStatus": item.get("draftStatus"),
                "agentEntity": item.get("agentEntity"),
            },
        },
        {
            "id": "confirm_source_dsl_and_schema",
            "label": "确认源 DSL 已通过 Schema 校验且与导入预览一致",
            "status": "NEEDS_HUMAN_SIGNOFF",
            "evidence": {
                "sourceArtifactKind": item.get("sourceArtifactKind"),
                "sourceDslPath": item.get("sourceDslPath"),
                "schemaValidated": bool(item.get("schemaValidated")),
            },
        },
        {
            "id": "confirm_import_plan_manual_only",
            "label": "确认当前导入计划仅用于人工审核后的手动导入预览",
            "status": "NEEDS_HUMAN_SIGNOFF",
            "evidence": item.get("importPlan", {}),
        },
        {
            "id": "confirm_no_database_write_or_publish",
            "label": "确认本次预览未写真实数据库、未调用真实平台、未允许发布",
            "status": "NEEDS_HUMAN_SIGNOFF",
            "evidence": {
                "databaseWritten": bool(item.get("databaseWritten", False)),
                "realAgentImport": bool(item.get("realAgentImport", False)),
                "realPublishAllowed": bool(item.get("realPublishAllowed", False)),
            },
        },
    ]
    if entity_config:
        checks.append(
            {
                "id": entity_config["entityCheckId"],
                "label": entity_config["entityCheckLabel"],
                "status": "NEEDS_HUMAN_SIGNOFF",
                "evidence": {
                    "agentEntity": agent_entity,
                    "previewComponent": item.get("component"),
                    "reviewChecklist": item.get("reviewChecklist", []),
                },
            }
        )
    if agent_entity == "grading_rule" and item.get("controlledEvidenceNextAction"):
        checks.append(
            {
                "id": "confirm_controlled_grading_evidence_next_action_before_platform_import",
                "label": "确认评分规则最终导入复核前先生成受控评分 evidence 并人工查看报告",
                "status": "NEEDS_HUMAN_SIGNOFF",
                "evidence": item.get("controlledEvidenceNextAction"),
            }
        )
    return checks


def _pre_approve_review_check_signoff_summary(pre_approve_review_check: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(pre_approve_review_check, dict):
        return {
            "available": False,
            "applicable": False,
            "status": "NOT_AVAILABLE",
            "evidenceReady": False,
            "reviewDecisionNoteRecorded": False,
            "approveReadyDecision": False,
            "warningTotal": 0,
            "recommendedWarnings": [],
            "latestDecision": None,
            "blocking": False,
            "approvalStillAllowed": True,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        }
    summary = pre_approve_review_check.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "available": True,
        "applicable": bool(pre_approve_review_check.get("applicable")),
        "status": pre_approve_review_check.get("status"),
        "evidenceReady": bool(summary.get("evidenceReady")),
        "reviewDecisionNoteRecorded": bool(summary.get("reviewDecisionNoteRecorded")),
        "approveReadyDecision": bool(summary.get("approveReadyDecision")),
        "warningTotal": int(summary.get("warningTotal", 0) or 0),
        "recommendedWarnings": summary.get("recommendedWarnings", []),
        "latestDecision": summary.get("latestDecision"),
        "blocking": bool(pre_approve_review_check.get("blocking")),
        "approvalStillAllowed": bool(pre_approve_review_check.get("approvalStillAllowed", True)),
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _grading_rule_import_preview_present(
    platform_import_preview: dict[str, Any],
    platform_import_preview_actions: dict[str, Any],
) -> bool:
    preview_items = platform_import_preview.get("items") if isinstance(platform_import_preview.get("items"), list) else []
    action_items = (
        platform_import_preview_actions.get("items")
        if isinstance(platform_import_preview_actions.get("items"), list)
        else []
    )
    return any(
        isinstance(item, dict)
        and (
            item.get("agentEntity") == "grading_rule"
            or item.get("previewComponent") == "GradingRuleImportPreview"
            or item.get("component") == "GradingRuleImportPreview"
            or item.get("component") == "GradingRuleImportPreviewAction"
        )
        for item in [*preview_items, *action_items]
    )


def _pre_approve_review_check_signoff_context_summary(
    pre_approve_review_check: dict[str, Any] | None,
    *,
    grading_rule_import_present: bool,
) -> dict[str, Any]:
    summary = _pre_approve_review_check_signoff_summary(pre_approve_review_check)
    if not grading_rule_import_present or summary["applicable"]:
        return summary
    recommended_warnings = [
        "grading_evidence_missing_before_approve",
        "review_decision_note_missing_before_approve",
    ]
    return {
        **summary,
        "applicable": True,
        "status": "APPROVE_ALLOWED_WITH_WARNINGS",
        "warningTotal": len(recommended_warnings),
        "recommendedWarnings": recommended_warnings,
        "context": "grading_rule_import_preview",
    }


def _grading_evidence_report_signoff_summary(merged_grading_evidence: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(merged_grading_evidence, dict) or merged_grading_evidence.get("visible") is not True:
        return {
            "available": False,
            "status": "EVIDENCE_REPORT_MISSING",
            "latestReportType": None,
            "latestReportPath": None,
            "checkEvidenceReviewItemTotal": 0,
            "evidenceReady": False,
            "readyForDecisionNote": False,
            "reviewDecisionHint": "NEEDS_EVIDENCE",
            "decisionNoteRecommendation": None,
            "manualReviewChecklistStatus": None,
            "nextRequiredAction": "run_grading_evidence_auto_before_final_grading_rule_import_review",
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        }
    summary = merged_grading_evidence.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    decision_hints = merged_grading_evidence.get("reviewDecisionHints")
    if not isinstance(decision_hints, dict):
        decision_hints = {}
    latest_report_type = summary.get("latestReportType") or merged_grading_evidence.get("latestReportType")
    check_total = int(summary.get("checkEvidenceReviewItemTotal", 0) or 0)
    evidence_missing_total = int(summary.get("reviewDecisionEvidenceMissingTotal", 0) or 0)
    review_decision_hint = (
        summary.get("reviewDecisionHint")
        or decision_hints.get("overallHint")
        or "NEEDS_EVIDENCE"
    )
    decision_note_recommendation = summary.get("decisionNoteRecommendation")
    manual_checklist_status = summary.get("manualReviewChecklistStatus")
    evidence_ready = check_total > 0 and evidence_missing_total == 0
    ready_for_decision_note = evidence_ready and review_decision_hint == "READY_FOR_MANUAL_REVIEW_DECISION"
    return {
        "available": True,
        "status": "READY_FOR_DECISION_NOTE" if ready_for_decision_note else "NEEDS_EVIDENCE_REVIEW",
        "latestReportType": latest_report_type,
        "latestReportPath": summary.get("latestReportPath"),
        "latestReportMode": summary.get("latestReportMode"),
        "autoEvidenceReport": bool(summary.get("autoEvidenceReport") or latest_report_type == "GRADING_EVIDENCE_AUTO"),
        "checkEvidenceReviewItemTotal": check_total,
        "manualCheckReviewTotal": int(summary.get("manualCheckReviewTotal", 0) or 0),
        "earnedScore": summary.get("earnedScore", 0),
        "totalScore": summary.get("totalScore", 0),
        "coverageRatio": summary.get("coverageRatio", 0),
        "evidenceReady": evidence_ready,
        "readyForDecisionNote": ready_for_decision_note,
        "reviewDecisionHint": review_decision_hint,
        "decisionNoteRecommendation": decision_note_recommendation,
        "manualReviewChecklistStatus": manual_checklist_status,
        "manualReviewChecklistReadyTotal": summary.get("manualReviewChecklistReadyTotal", 0),
        "manualReviewChecklistTotal": summary.get("manualReviewChecklistTotal", 0),
        "nextRequiredAction": (
            "record_approve_ready_decision_note_before_manual_approve"
            if ready_for_decision_note
            else "record_needs_evidence_decision_note_or_collect_more_evidence"
            if decision_note_recommendation == "needs-evidence"
            else "record_needs_revision_decision_note_or_request_revision"
            if decision_note_recommendation == "needs-revision"
            else "review_or_regenerate_grading_evidence_before_import_signoff"
        ),
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def build_platform_import_preview_signoff_checklist(
    task: dict[str, Any],
    platform_import_preview: dict[str, Any],
    platform_import_preview_actions: dict[str, Any],
    pre_approve_review_check: dict[str, Any] | None = None,
    merged_grading_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pre_approve_summary = _pre_approve_review_check_signoff_context_summary(
        pre_approve_review_check,
        grading_rule_import_present=_grading_rule_import_preview_present(
            platform_import_preview,
            platform_import_preview_actions,
        ),
    )
    grading_evidence_summary = _grading_evidence_report_signoff_summary(merged_grading_evidence)
    items: list[dict[str, Any]] = []
    for preview_item in platform_import_preview.get("items", []):
        if not isinstance(preview_item, dict):
            continue
        agent_entity = str(preview_item.get("agentEntity") or "")
        entity_config = PLATFORM_IMPORT_PREVIEW_SIGNOFF_CHECKS.get(agent_entity, {})
        checks = _platform_import_preview_signoff_checks(preview_item)
        if agent_entity == "grading_rule":
            checks.append(
                {
                    "id": "confirm_pre_approve_review_check_before_grading_rule_import",
                    "label": "确认评分规则导入预览前已查看 evidence 与人工决策 readiness",
                    "status": "NEEDS_HUMAN_SIGNOFF",
                    "evidence": pre_approve_summary,
                }
            )
            checks.append(
                {
                    "id": "confirm_grading_evidence_report_before_grading_rule_import",
                    "label": "确认评分规则最终导入复核前已查看最新评分 evidence 报告",
                    "status": "NEEDS_HUMAN_SIGNOFF",
                    "evidence": grading_evidence_summary,
                }
            )
        required_action = entity_config.get(
            "requiredReviewerAction",
            "signoff_platform_import_preview_after_manual_check",
        )
        items.append(
            {
                "id": f"signoff_{agent_entity or 'agent_entity'}_{preview_item.get('artifactId') or len(items) + 1}",
                "component": entity_config.get("component", "AgentImportPreviewItemSignoff"),
                "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW_SIGNOFF",
                "status": "NEEDS_HUMAN_SIGNOFF",
                "taskId": task.get("id"),
                "taskStatus": task.get("status"),
                "agentEntity": preview_item.get("agentEntity"),
                "sourceArtifactKind": preview_item.get("sourceArtifactKind"),
                "sourceDslPath": preview_item.get("sourceDslPath"),
                "previewComponent": preview_item.get("component"),
                "previewArtifactId": preview_item.get("artifactId"),
                "draftId": preview_item.get("draftId"),
                "draftTitle": preview_item.get("draftTitle"),
                "draftStatus": preview_item.get("draftStatus"),
                "checks": checks,
                "requiredReviewerActions": [required_action],
                "preApproveReviewCheckSummary": pre_approve_summary if agent_entity == "grading_rule" else None,
                "gradingEvidenceReportSummary": grading_evidence_summary if agent_entity == "grading_rule" else None,
                "controlledEvidenceNextAction": (
                    preview_item.get("controlledEvidenceNextAction") if agent_entity == "grading_rule" else None
                ),
                "databaseWritten": False,
                "realAgentImport": False,
                "realPublishAllowed": False,
            }
        )

    missing_preview_actions = [
        {
            "component": item.get("component"),
            "sourceArtifactKind": item.get("sourceArtifactKind"),
            "sourceDslPath": item.get("sourceDslPath"),
            "agentEntity": item.get("agentEntity"),
            "previewComponent": item.get("previewComponent"),
            "cliCommand": item.get("cliCommand"),
            "apiEndpoint": item.get("apiEndpoint"),
            "mcpTool": item.get("mcpTool"),
            "nextRequiredAction": item.get("nextRequiredAction"),
        }
        for item in platform_import_preview_actions.get("items", [])
        if isinstance(item, dict) and not item.get("previewAlreadyCreated")
    ]
    required_reviewer_actions = sorted(
        {
            action
            for item in items
            for action in item.get("requiredReviewerActions", [])
            if action
        }
        | {
            str(item.get("nextRequiredAction"))
            for item in missing_preview_actions
            if item.get("nextRequiredAction")
        }
    )
    blocked_total = len(missing_preview_actions)
    return {
        "component": "AgentImportPreviewSignoffChecklist",
        "mode": "LOCAL_PLATFORM_IMPORT_PREVIEW_SIGNOFF",
        "visible": bool(items or missing_preview_actions),
        "readyForHumanSignoff": bool(items) and blocked_total == 0,
        "taskId": task.get("id"),
        "taskStatus": task.get("status"),
        "total": len(items),
        "passedTotal": 0,
        "needsHumanSignoffTotal": len(items),
        "blockedTotal": blocked_total,
        "missingPreviewTotal": blocked_total,
        "items": items,
        "missingPreviewActions": missing_preview_actions,
        "requiredReviewerActions": required_reviewer_actions,
        "preApproveReviewCheckSummary": pre_approve_summary,
        "gradingEvidenceReportSummary": grading_evidence_summary,
        "summary": {
            "previewTotal": platform_import_preview.get("total", 0),
            "actionTotal": platform_import_preview_actions.get("total", 0),
            "signoffItemTotal": len(items),
            "missingPreviewTotal": blocked_total,
            "readyForHumanSignoff": bool(items) and blocked_total == 0,
            "preApproveReviewCheckApplicable": pre_approve_summary["applicable"],
            "preApproveReviewCheckApproveReadyDecision": pre_approve_summary["approveReadyDecision"],
            "preApproveReviewCheckWarningTotal": pre_approve_summary["warningTotal"],
            "controlledEvidenceNextActionTotal": sum(
                1 for item in items if item.get("controlledEvidenceNextAction")
            ),
            "gradingEvidenceReportAvailable": grading_evidence_summary["available"],
            "gradingEvidenceReportReadyForDecisionNote": grading_evidence_summary["readyForDecisionNote"],
            "gradingEvidenceReportLatestType": grading_evidence_summary["latestReportType"],
        },
        "databaseWritten": False,
        "realAgentImport": False,
        "realPublishAllowed": False,
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
    }


def build_agent_entity_mock_import_summary(
    task: dict[str, Any],
    agent_entities: list[dict[str, Any]],
    operation_audit_events: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for entity in agent_entities:
        if not isinstance(entity, dict):
            continue
        event = next(
            (
                item
                for item in operation_audit_events
                if item.get("resourceType") == "PLATFORM_ENTITY" and item.get("resourceId") == entity.get("id")
            ),
            None,
        )
        items.append(
            {
                "component": "AgentEntityMockImportItem",
                "mode": "LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
                "id": entity.get("id"),
                "entityType": entity.get("entityType"),
                "status": entity.get("status"),
                "title": entity.get("title"),
                "sourceTaskId": entity.get("sourceTaskId"),
                "sourcePreviewArtifactId": entity.get("sourcePreviewArtifactId"),
                "sourcePreviewPath": entity.get("sourcePreviewPath"),
                "sourceDslPath": entity.get("sourceDslPath"),
                "reviewer": entity.get("reviewer"),
                "operationAuditEventId": event.get("id") if event else None,
                "mockStoreWritten": bool(entity.get("mockStoreWritten")),
                "databaseWritten": False,
                "realAgentImport": False,
                "realPublishAllowed": False,
            }
        )
    entity_types = sorted({str(item.get("entityType")) for item in items if item.get("entityType")})
    return {
        "component": "AgentEntityMockImportSummary",
        "mode": "LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
        "visible": bool(items),
        "taskId": task.get("id"),
        "taskStatus": task.get("status"),
        "total": len(items),
        "entityTypes": entity_types,
        "items": items,
        "summary": {
            "mockStoreWrittenTotal": sum(1 for item in items if item.get("mockStoreWritten") is True),
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublishAllowed": False,
        },
        "safety": {
            "newLlmRequestSent": False,
            "secretsRead": False,
            "networkAccess": False,
            "mockStoreWritten": bool(items),
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def _artifact_groups(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        groups.setdefault(artifact["kind"], []).append(artifact)
    return [
        {"kind": kind, "total": len(items), "items": items}
        for kind, items in sorted(groups.items())
    ]


def _risk_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    material_artifacts = [artifact for artifact in artifacts if artifact["kind"] == "MATERIAL_ANALYSIS"]
    risk_count = sum(int(artifact.get("metadata", {}).get("riskCount", 0)) for artifact in material_artifacts)
    unknown_shell_executed = any(
        bool(artifact.get("metadata", {}).get("unknownShellExecuted")) for artifact in material_artifacts
    )
    answer_visible = any(
        artifact.get("metadata", {}).get("answerVisibleToCandidate") is True for artifact in artifacts
    )
    return {
        "riskCount": risk_count,
        "requiresHumanReview": True,
        "unknownShellExecuted": unknown_shell_executed,
        "answerVisibleToCandidate": answer_visible,
    }


def _step_details(workflow_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [step.get("detail", {}) for step in workflow_steps if isinstance(step.get("detail"), dict)]


def _first_artifact_metadata(artifacts: list[dict[str, Any]], key: str) -> Any:
    for artifact in artifacts:
        metadata = artifact.get("metadata", {})
        if isinstance(metadata, dict) and key in metadata:
            return metadata[key]
    return None


def _first_step_detail(workflow_steps: list[dict[str, Any]], key: str) -> Any:
    for detail in _step_details(workflow_steps):
        if key in detail:
            return detail[key]
    return None


def _unique_preserve_order(values: list[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _resolve_local_path(path_value: Any) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    if "://" in path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def _load_dsl_preview_document(path_value: Any) -> tuple[dict[str, Any] | None, str | None]:
    path = _resolve_local_path(path_value)
    if path is None:
        return None, "path_not_local"
    if not path.exists() or not path.is_file():
        return None, "file_not_found"
    try:
        document = load_yaml(path)
    except Exception:
        return None, "parse_failed"
    if not isinstance(document, dict):
        return None, "document_not_object"
    return document, None


def _string_values(values: Any, limit: int = 4) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        result.append(str(value))
        if len(result) >= limit:
            break
    return result


def _dsl_preview_title(document: dict[str, Any]) -> str | None:
    metadata = document.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("title"):
        return str(metadata["title"])
    spec = document.get("spec", {})
    if isinstance(spec, dict) and spec.get("title"):
        return str(spec["title"])
    return None


def _lab_dsl_preview(document: dict[str, Any]) -> dict[str, Any]:
    spec = document.get("spec", {}) if isinstance(document.get("spec"), dict) else {}
    steps = spec.get("steps", []) if isinstance(spec.get("steps"), list) else []
    objectives = spec.get("objectives", []) if isinstance(spec.get("objectives"), list) else []
    environment = spec.get("environment", {}) if isinstance(spec.get("environment"), dict) else {}
    materials = spec.get("materials", []) if isinstance(spec.get("materials"), list) else []
    return {
        "summary": {
            "stepTotal": len(steps),
            "objectiveTotal": len(objectives),
            "materialTotal": len(materials),
            "environmentType": environment.get("type"),
            "environmentImage": environment.get("image"),
        },
        "safePreview": {
            "objectives": _string_values(objectives),
            "stepTitles": _string_values([step.get("title") for step in steps if isinstance(step, dict)]),
            "materialTypes": _string_values([item.get("type") for item in materials if isinstance(item, dict)]),
        },
        "candidateSafety": {},
    }


def _exam_dsl_preview(document: dict[str, Any]) -> dict[str, Any]:
    spec = document.get("spec", {}) if isinstance(document.get("spec"), dict) else {}
    questions = spec.get("questions", []) if isinstance(spec.get("questions"), list) else []
    teacher_ref_total = 0
    answer_total = 0
    safe_questions: list[dict[str, Any]] = []
    for question in questions:
        if not isinstance(question, dict):
            continue
        if "gradingRef" in question:
            teacher_ref_total += 1
        if "answer" in question:
            answer_total += 1
        safe_questions.append(
            {
                "id": question.get("id"),
                "title": question.get("title"),
                "score": question.get("score"),
                "type": question.get("type") or spec.get("questionType"),
                "gradingRefPresent": "gradingRef" in question,
                "answerPresent": "answer" in question,
            }
        )
    return {
        "summary": {
            "questionTotal": len(questions),
            "totalScore": spec.get("totalScore"),
            "questionType": spec.get("questionType"),
            "teacherGradingRefTotal": teacher_ref_total,
            "answerFieldTotal": answer_total,
        },
        "safePreview": {
            "questions": safe_questions[:6],
        },
        "candidateSafety": {
            "answersRemovedFromSafePreview": True,
            "gradingRefsTeacherOnly": True,
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "teacherGradingRefTotal": teacher_ref_total,
            "answerFieldTotal": answer_total,
        },
    }


def _grading_dsl_preview(document: dict[str, Any]) -> dict[str, Any]:
    spec = document.get("spec", {}) if isinstance(document.get("spec"), dict) else {}
    checks = spec.get("checks", []) if isinstance(spec.get("checks"), list) else []
    assessment_plan = spec.get("assessmentPlan", []) if isinstance(spec.get("assessmentPlan"), list) else []
    check_types = _unique_preserve_order(
        [check.get("type") for check in checks if isinstance(check, dict) and check.get("type")]
    )
    strategies = _unique_preserve_order(
        [
            item.get("executionPlan", {}).get("strategy")
            for item in assessment_plan
            if isinstance(item, dict) and isinstance(item.get("executionPlan"), dict)
        ]
    )
    sandbox_required = any(
        bool(item.get("sandboxRequiredBeforeRealExecution"))
        or bool(item.get("executionPlan", {}).get("wouldRunInsideRealSandbox"))
        for item in assessment_plan
        if isinstance(item, dict)
    )
    return {
        "summary": {
            "checkTotal": len(checks),
            "assessmentPlanTotal": len(assessment_plan),
            "totalScore": spec.get("totalScore"),
            "timeoutSeconds": spec.get("timeoutSeconds"),
            "checkTypes": [str(value) for value in check_types],
            "executionStrategies": [str(value) for value in strategies if value],
            "sandboxRequiredBeforeRealExecution": sandbox_required,
        },
        "safePreview": {
            "checks": [
                {
                    "id": check.get("id"),
                    "type": check.get("type"),
                    "score": check.get("score"),
                    "expectedVisibleInTeacherReview": "expected" in check,
                }
                for check in checks
                if isinstance(check, dict)
            ][:6],
            "assessmentPlanCheckIds": _string_values(
                [item.get("checkId") for item in assessment_plan if isinstance(item, dict)],
                limit=6,
            ),
        },
        "candidateSafety": {
            "standardAnswerVisibleToCandidate": False,
            "gradingRulesTeacherOnly": True,
        },
    }


def _ppt_dsl_preview(document: dict[str, Any]) -> dict[str, Any]:
    spec = document.get("spec", {}) if isinstance(document.get("spec"), dict) else {}
    slides = spec.get("slides", []) if isinstance(spec.get("slides"), list) else []
    slide_types = _unique_preserve_order(
        [slide.get("type") for slide in slides if isinstance(slide, dict) and slide.get("type")]
    )
    return {
        "summary": {
            "slideTotal": len(slides),
            "slideTypes": [str(value) for value in slide_types],
            "themeStyle": (spec.get("theme") or {}).get("style") if isinstance(spec.get("theme"), dict) else None,
            "language": (spec.get("theme") or {}).get("language") if isinstance(spec.get("theme"), dict) else None,
        },
        "safePreview": {
            "slideTitles": _string_values([slide.get("title") for slide in slides if isinstance(slide, dict)], limit=8),
        },
        "candidateSafety": {},
    }


def _dsl_content_preview(
    artifact_kind: str,
    path_value: Any,
    *,
    schema_kind: str | None,
) -> dict[str, Any]:
    document, unavailable_reason = _load_dsl_preview_document(path_value)
    base: dict[str, Any] = {
        "contentLoaded": document is not None,
        "contentSource": "local_dsl_file",
        "unavailableReason": unavailable_reason,
        "schemaValidated": False,
        "schemaValidationErrors": [],
        "documentKind": None,
        "documentStatus": None,
        "title": None,
        "summary": {},
        "safePreview": {},
        "candidateSafety": {
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
        },
        "reviewSafety": {
            "readOnly": True,
            "secretsRead": False,
            "networkAccess": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }
    if document is None:
        return base

    schema_errors: list[dict[str, str]] = []
    if schema_kind:
        try:
            validate_dsl(document, load_schema(schema_kind, ROOT))
            schema_validated = True
        except DslValidationError as exc:
            schema_validated = False
            schema_errors = exc.errors[:8]
        except Exception as exc:
            schema_validated = False
            schema_errors = [{"field": "$", "reason": type(exc).__name__}]
    else:
        schema_validated = False

    if artifact_kind == "LAB_DSL":
        detail = _lab_dsl_preview(document)
    elif artifact_kind == "EXAM_DSL":
        detail = _exam_dsl_preview(document)
    elif artifact_kind == "GRADING_DSL":
        detail = _grading_dsl_preview(document)
    elif artifact_kind == "PPT_DSL":
        detail = _ppt_dsl_preview(document)
    else:
        detail = {"summary": {}, "safePreview": {}, "candidateSafety": {}}

    return {
        **base,
        "schemaValidated": schema_validated,
        "schemaValidationErrors": schema_errors,
        "documentKind": document.get("kind"),
        "documentStatus": document.get("status"),
        "title": _dsl_preview_title(document),
        "summary": detail["summary"],
        "safePreview": detail["safePreview"],
        "candidateSafety": {
            **base["candidateSafety"],
            **detail.get("candidateSafety", {}),
        },
    }


def _load_real_demo_workflow_report(report_path: str | None) -> dict[str, Any] | None:
    path = _resolve_local_path(report_path)
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("generatedDsl"), dict):
        return None
    payload["_localReportPath"] = str(path)
    return payload


def _real_demo_report_kind_for_task(report: dict[str, Any], task_id: str) -> str | None:
    generated = report.get("generatedDsl") if isinstance(report.get("generatedDsl"), dict) else {}
    for kind, item in generated.items():
        if not isinstance(item, dict):
            continue
        item_task_id = str(item.get("taskId") or REAL_DEMO_REPORT_FALLBACK_TASK_IDS.get(str(kind), ""))
        if item_task_id == task_id:
            return str(kind)
    return None


def _real_demo_report_generated_item(report: dict[str, Any], kind: str) -> dict[str, Any]:
    generated = report.get("generatedDsl") if isinstance(report.get("generatedDsl"), dict) else {}
    item = generated.get(kind)
    return item if isinstance(item, dict) else {}


def _real_demo_report_workflow_steps(report: dict[str, Any], task_id: str) -> list[dict[str, Any]]:
    steps = report.get("steps") if isinstance(report.get("steps"), list) else []
    result: list[dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        kind = step.get("kind")
        step_task_id = step.get("taskId")
        if step_task_id and str(step_task_id) != task_id:
            continue
        result.append(
            {
                "id": f"{report.get('id', 'real_report')}_step_{index}",
                "workflowRunId": report.get("id"),
                "workflowId": report.get("workflowId", "phase2_content_generation"),
                "name": step.get("name") or f"generate_{kind or 'dsl'}",
                "status": step.get("status") or "COMPLETED",
                "order": index,
                "startedAt": step.get("startedAt"),
                "finishedAt": step.get("finishedAt"),
                "detail": {
                    "taskId": task_id,
                    "kind": kind,
                    "source": "agentReport.generatedDsl",
                    "agentReportPath": report.get("_localReportPath"),
                },
            }
        )
    return result


def _real_demo_report_artifact(
    *,
    report: dict[str, Any],
    kind: str,
    task_id: str,
    trace_id: str,
) -> dict[str, Any] | None:
    task_type, _input_type, artifact_kind, dsl_kind, title = REAL_DEMO_REPORT_TASK_TYPES[kind]
    generated_item = _real_demo_report_generated_item(report, kind)
    dsl_path = generated_item.get("dslPath")
    if not dsl_path:
        return None
    metadata = {
        "dslKind": dsl_kind,
        "providerAdapter": generated_item.get("provider", {}).get("adapterId")
        if isinstance(generated_item.get("provider"), dict)
        else None,
        "workflowId": report.get("workflowId"),
        "workflowReportPath": report.get("_localReportPath"),
        "contentQualitySummary": generated_item.get("contentQualitySummary"),
        "workflowContentQualitySummary": report.get("contentQualitySummary"),
        "qualitySummary": generated_item.get("qualitySummary"),
        "realLlmCalled": True,
        "answerVisibleToCandidate": False,
    }
    artifact = create_artifact_record(
        kind=ArtifactKind[artifact_kind],
        path=str(dsl_path),
        title=title,
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=trace_id,
        task_id=task_id,
        workflow_run_id=str(report.get("id") or ""),
        source_ref=str(report.get("input") or ""),
        metadata={key: value for key, value in metadata.items() if value is not None},
    ).to_dict()
    artifact["mode"] = "AGENT_REPORT_REAL_LLM_ARTIFACT"
    artifact["realLlmCalled"] = True
    artifact["syntheticFromAgentReport"] = True
    artifact["taskType"] = task_type
    return artifact


def _real_demo_report_workflow_artifact(report: dict[str, Any], trace_id: str, task_id: str) -> dict[str, Any]:
    artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path=str(report.get("_localReportPath") or ""),
        title="Real LLM workflow report",
        status=ArtifactStatus.COMPLETED,
        trace_id=trace_id,
        task_id=task_id,
        workflow_run_id=str(report.get("id") or ""),
        source_ref=str(report.get("input") or ""),
        metadata={
            "workflowId": report.get("workflowId"),
            "providerMode": report.get("providerMode"),
            "mode": report.get("mode"),
            "reviewRequired": True,
            "agentReportPath": report.get("_localReportPath"),
        },
    ).to_dict()
    artifact["mode"] = "AGENT_REPORT_REAL_LLM_WORKFLOW_REPORT"
    artifact["realLlmCalled"] = True
    artifact["syntheticFromAgentReport"] = True
    return artifact


def _synthetic_real_demo_review_detail_from_report(
    report_path: str | None,
    task_id: str,
) -> dict[str, Any] | None:
    report = _load_real_demo_workflow_report(report_path)
    if report is None:
        return None
    kind = _real_demo_report_kind_for_task(report, task_id)
    if kind not in REAL_DEMO_REPORT_TASK_TYPES:
        return None

    task_type, input_type, _artifact_kind, _dsl_kind, _artifact_title = REAL_DEMO_REPORT_TASK_TYPES[kind]
    generated_item = _real_demo_report_generated_item(report, kind)
    trace_id = str(report.get("traceId") or f"trace_{uuid4().hex[:12]}")
    task_payload = {
        "id": task_id,
        "taskType": task_type,
        "title": f"真实批次 {kind.upper()} 审核",
        "inputType": input_type,
        "inputRef": str(report.get("input") or ""),
        "status": str(generated_item.get("status") or TaskStatus.WAITING_REVIEW.value),
        "modelName": generated_item.get("provider", {}).get("model")
        if isinstance(generated_item.get("provider"), dict)
        else report.get("model"),
        "promptVersion": str(generated_item.get("promptId") or "real-llm-workflow"),
        "intermediateResultPath": str(report.get("_localReportPath") or ""),
        "finalResultPath": str(generated_item.get("dslPath") or ""),
        "errorMessage": None,
        "createdBy": str(report.get("reviewer") or "lab-cli"),
        "createdAt": None,
        "updatedAt": None,
        "traceId": trace_id,
    }
    artifacts = [
        item
        for item in [
            _real_demo_report_artifact(report=report, kind=kind, task_id=task_id, trace_id=trace_id),
            _real_demo_report_workflow_artifact(report, trace_id, task_id),
        ]
        if item is not None
    ]
    workflow_steps = _real_demo_report_workflow_steps(report, task_id)
    provider_event = generated_item.get("providerCallAuditEvent")
    provider_call_audit_events = [provider_event] if isinstance(provider_event, dict) else []
    review_policy = build_review_policy(TaskStatus.WAITING_REVIEW, task_type)
    content_quality_summary = report.get("contentQualitySummary")
    if not isinstance(content_quality_summary, dict):
        content_quality_summary = {
            "available": bool(generated_item.get("contentQualitySummary")),
            "items": {kind: generated_item.get("contentQualitySummary")}
            if isinstance(generated_item.get("contentQualitySummary"), dict)
            else {},
        }
    safety = build_review_safety(artifacts)
    safety = {
        **safety,
        "mode": str(report.get("mode") or "REAL_LLM_WORKFLOW"),
        "realLlmCalled": True,
        "realCloudResourceChanged": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "realPublish": False,
    }
    assessment_plan = build_assessment_plan_review_model(task_payload, artifacts, workflow_steps)
    candidate_preview = _candidate_preview_summary(task_payload, artifacts)
    platform_import_preview = build_platform_import_preview_summary(task_payload, artifacts, [])
    platform_import_preview_actions = build_platform_import_preview_action_panel(
        task_payload,
        artifacts,
        review_policy,
        platform_import_preview,
        content_quality_summary,
    )
    platform_import_preview_signoff = build_platform_import_preview_signoff_checklist(
        task_payload,
        platform_import_preview,
        platform_import_preview_actions,
    )
    controlled_grading_evidence = build_controlled_grading_evidence_review_model(task_payload, artifacts, [])
    merged_grading_evidence = build_merged_grading_evidence_review_model(task_payload, artifacts, [])
    review_decision_notes = build_review_decision_note_summary(artifacts, [])
    pre_approve_review_check = build_pre_approve_review_check_from_models(
        task_payload,
        merged_grading_evidence,
        review_decision_notes,
    )
    review_page = build_review_page_model(
        task_payload,
        artifacts,
        workflow_steps,
        [],
        [],
        review_policy,
        assessment_plan=assessment_plan,
        provider_call_audit_events=provider_call_audit_events,
        candidate_preview=candidate_preview,
        platform_import_preview=platform_import_preview,
        platform_import_preview_actions=platform_import_preview_actions,
        platform_import_preview_signoff=platform_import_preview_signoff,
        controlled_grading_evidence=controlled_grading_evidence,
        merged_grading_evidence=merged_grading_evidence,
        review_decision_notes=review_decision_notes,
        pre_approve_review_check=pre_approve_review_check,
        content_quality_summary=content_quality_summary,
    )
    dsl_preview = review_page.get("dslPreview") or {}
    return {
        "mode": safety["mode"],
        "source": "agentReport.generatedDsl",
        "agentReportPath": report.get("_localReportPath"),
        "task": task_payload,
        "highRiskIntent": None,
        "assessmentPlan": assessment_plan,
        "candidatePreview": candidate_preview,
        "pptPageReview": build_ppt_page_review_model(task_payload, artifacts),
        "promotionReviewDisposition": None,
        "platformImportPreview": platform_import_preview,
        "platformImportPreviewActions": platform_import_preview_actions,
        "platformImportPreviewSignoff": platform_import_preview_signoff,
        "agentEntityMockImport": {"visible": False, "total": 0, "items": []},
        "agentEntityImportActivity": {"visible": False, "items": [], "summary": {}, "sendTotal": 0},
        "agentEntityReadinessReport": {
            "component": "AgentEntityReadinessReport",
            "mode": "LOCAL_AGENT_ENTITY_READINESS_REPORT",
            "sourceTaskId": task_id,
            "items": [],
            "summary": {
                "requiredTotal": 0,
                "agentEntitySignoffReadyTotal": 0,
                "agentEntitySignoffRecordedTotal": 0,
            },
        },
        "gradingJobs": {
            "component": "GradingJobSummary",
            "visible": False,
            "total": 0,
            "items": [],
            "latest": None,
            "summary": {"latestStatus": None, "latestEarnedScore": None, "latestTotalScore": None},
        },
        "gradingRecords": {
            "component": "GradingRecordSummary",
            "visible": False,
            "total": 0,
            "items": [],
            "latest": None,
            "summary": {
                "humanReviewRecordedTotal": 0,
                "readyForAgentReview": False,
                "latestStatus": None,
                "latestEarnedScore": None,
                "latestTotalScore": None,
                "platformReviewState": "NO_GRADING_RECORD",
                "platformReviewNextRequiredAction": "create_grading_record_from_latest_evidence_report",
            },
            "reviewIntegration": {
                "component": "GradingRecordReviewIntegration",
                "state": "NO_GRADING_RECORD",
                "readyForAgentReview": False,
                "blockingReasons": ["grading_record_missing"],
            },
        },
        "controlledGradingEvidence": controlled_grading_evidence,
        "mergedGradingEvidence": merged_grading_evidence,
        "reviewDecisionNotes": review_decision_notes,
        "preApproveReviewCheck": pre_approve_review_check,
        "contentQualitySummary": content_quality_summary,
        "agentEntities": [],
        "artifacts": artifacts,
        "workflowRuns": [{"id": report.get("id"), "workflowId": report.get("workflowId"), "status": "COMPLETED"}],
        "workflowSteps": workflow_steps,
        "reviewAuditEvents": [],
        "operationAuditEvents": [],
        "providerCallAuditEvents": provider_call_audit_events,
        "reviewPolicy": review_policy,
        "revisionRequests": build_review_revision_request_summary([]),
        "reviewPage": review_page,
        "safety": safety,
        "summary": {
            "artifactTotal": len(artifacts),
            "workflowRunTotal": 1,
            "workflowStepTotal": len(workflow_steps),
            "reviewAuditEventTotal": 0,
            "operationAuditEventTotal": 0,
            "revisionRequestTotal": 0,
            "providerCallAuditEventTotal": len(provider_call_audit_events),
            "contentQualityAvailable": content_quality_summary.get("available") is True,
            "contentQualityStatus": content_quality_summary.get("status"),
            "contentQualityIssueTotal": content_quality_summary.get("issueTotal", 0),
            "contentQualityBlockingIssueTotal": content_quality_summary.get("blockingIssueTotal", 0),
            "dslPreviewContentLoaded": bool(dsl_preview.get("contentLoaded")),
            "dslPreviewSchemaValidated": bool(dsl_preview.get("schemaValidated")),
            "dslPreviewTitle": dsl_preview.get("title"),
            "platformImportPreviewVisible": platform_import_preview["visible"],
            "platformImportPreviewTotal": platform_import_preview["total"],
            "platformImportPreviewActionVisible": platform_import_preview_actions["visible"],
            "platformImportPreviewActionTotal": platform_import_preview_actions["total"],
            "platformImportPreviewActionEnabledTotal": platform_import_preview_actions["enabledTotal"],
            "controlledGradingEvidenceVisible": controlled_grading_evidence["visible"],
            "mergedGradingEvidenceVisible": merged_grading_evidence["visible"],
            "reviewDecisionNoteTotal": 0,
            "preApproveReviewCheckVisible": pre_approve_review_check["applicable"],
        },
    }


def _grading_artifact(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    for artifact in artifacts:
        if artifact.get("kind") == "GRADING_DSL":
            return artifact
    return None


def _pptx_artifact(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    for artifact in artifacts:
        if artifact.get("kind") == "PPTX_FILE":
            return artifact
    return None


def _ppt_slide_reviews(slide_previews: list[Any]) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    for position, slide in enumerate(slide_previews, start=1):
        if not isinstance(slide, dict):
            continue
        status = str(slide.get("reviewStatus") or "NEEDS_REVIEW")
        manual_comment = slide.get("manualComment")
        if not isinstance(manual_comment, dict):
            manual_comment = {}
        comment_required = bool(
            manual_comment.get("required", status in {"NEEDS_REVIEW", "REVISE_REQUIRED"})
        )
        qa_signals = slide.get("qaSignals")
        if not isinstance(qa_signals, dict):
            qa_signals = {
                "layout": "NEEDS_REVIEW",
                "textOverflow": False,
                "visualDensity": "UNKNOWN",
                "contrast": "NEEDS_REVIEW",
                "reviewFocus": "manual_review_required",
            }
        reviews.append(
            {
                "index": int(slide.get("index") or position),
                "id": slide.get("id") or f"slide_{position}",
                "title": slide.get("title") or f"Slide {position}",
                "imagePath": slide.get("imagePath"),
                "reviewStatus": status,
                "manualComment": {
                    "required": comment_required,
                    "text": manual_comment.get("text") or (
                        "请人工确认本页内容、版式和课程目标是否匹配。" if comment_required else ""
                    ),
                    "reviewer": manual_comment.get("reviewer"),
                    "updatedAt": manual_comment.get("updatedAt"),
                },
                "qaSignals": qa_signals,
            }
        )
    return reviews


def _ppt_page_review_summary(slide_reviews: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(slide_reviews)
    approved = sum(1 for slide in slide_reviews if slide.get("reviewStatus") == "APPROVED")
    revise_required = sum(1 for slide in slide_reviews if slide.get("reviewStatus") == "REVISE_REQUIRED")
    needs_review = sum(1 for slide in slide_reviews if slide.get("reviewStatus") == "NEEDS_REVIEW")
    manual_comment_total = sum(
        1 for slide in slide_reviews if slide.get("manualComment", {}).get("required") is True
    )
    if revise_required:
        status = "REVISE_REQUIRED"
    elif needs_review or total == 0:
        status = "NEEDS_REVIEW"
    else:
        status = "APPROVED"
    return {
        "status": status,
        "total": total,
        "approved": approved,
        "needsReview": needs_review,
        "reviseRequired": revise_required,
        "manualCommentTotal": manual_comment_total,
        "qaSignalStatus": "NEEDS_REVIEW" if manual_comment_total or revise_required or needs_review else "PASS",
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _pptx_artifact_record(store: JsonTaskStore, task_id: str) -> ArtifactRecord | None:
    for artifact in store.list_artifacts(task_id=task_id, kind="PPTX_FILE"):
        return artifact
    return None


def build_ppt_page_review_model(task: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    pptx_artifact = _pptx_artifact(artifacts)
    eligible = task.get("taskType") in PPT_REVIEW_TASK_TYPES or pptx_artifact is not None
    if not eligible:
        return {
            "visible": False,
            "eligible": False,
            "available": False,
            "message": "当前任务不是 PPT 审核任务",
        }

    if pptx_artifact is None:
        return {
            "visible": True,
            "eligible": True,
            "available": False,
            "taskId": task.get("id"),
            "message": "当前 PPT 审核任务尚未关联 PPTX_FILE Artifact",
            "pageReviewSummary": _ppt_page_review_summary([]),
            "slideReviews": [],
            "operatorDecision": {
                "manualDecisionRequired": True,
                "autoApproveAllowed": False,
                "batchStateChangeAllowed": False,
                "realPublishAllowed": False,
            },
        }

    metadata = pptx_artifact.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    slide_previews = metadata.get("slidePreviews")
    if not isinstance(slide_previews, list):
        preview = metadata.get("preview", {})
        slide_previews = preview.get("slidePreviews", []) if isinstance(preview, dict) else []
    slide_reviews = _ppt_slide_reviews(slide_previews)
    summary = metadata.get("pageReviewSummary")
    if not isinstance(summary, dict):
        summary = _ppt_page_review_summary(slide_reviews)

    return {
        "visible": True,
        "eligible": True,
        "available": True,
        "mode": "MOCK_ONLY",
        "source": "artifact.metadata.pageReviewSummary + artifact.metadata.slidePreviews",
        "taskId": task.get("id"),
        "artifactId": pptx_artifact.get("id"),
        "artifactKind": pptx_artifact.get("kind"),
        "artifactStatus": pptx_artifact.get("status"),
        "artifactPath": pptx_artifact.get("path"),
        "pageReviewSummary": summary,
        "slideReviews": slide_reviews,
        "operatorDecision": {
            "manualDecisionRequired": bool(slide_reviews),
            "approveAllowedAfterPageReview": bool(slide_reviews),
            "rejectRequiresReason": True,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
        },
        "safety": {
            "realLlmCalled": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }


def update_ppt_page_review_status(
    store: JsonTaskStore,
    *,
    task_id: str,
    slide_index: int,
    review_status: str,
    reviewer: str,
    comment: str | None,
    trace_id: str,
) -> dict[str, Any]:
    if review_status not in PPT_PAGE_REVIEW_STATUSES:
        raise PptPageReviewUpdateError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewStatus", "reason": f"必须是 {sorted(PPT_PAGE_REVIEW_STATUSES)} 之一"}],
        )
    if slide_index < 1:
        raise PptPageReviewUpdateError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "slideIndex", "reason": "必须大于等于 1"}],
        )
    if not reviewer:
        raise PptPageReviewUpdateError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    if review_status == "REVISE_REQUIRED" and not comment:
        raise PptPageReviewUpdateError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "comment", "reason": "REVISE_REQUIRED 必须填写人工批注"}],
        )

    task = store.get(task_id)
    if task is None:
        raise PptPageReviewUpdateError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )
    if task.taskType not in PPT_REVIEW_TASK_TYPES:
        raise PptPageReviewUpdateError(
            "VALIDATION_ERROR",
            "任务不是 PPT 审核任务",
            [{"field": "taskId", "reason": "仅支持 PPT_GENERATION 或 PPT_ARTIFACT_GENERATION"}],
        )
    if task.status != TaskStatus.WAITING_REVIEW:
        raise PptPageReviewUpdateError(
            "STATE_TRANSITION_ERROR",
            "PPT 页级审核状态非法流转",
            [{"field": "status", "reason": "只有 WAITING_REVIEW 任务允许更新页级审核状态"}],
        )

    artifact = _pptx_artifact_record(store, task_id)
    if artifact is None:
        raise PptPageReviewUpdateError(
            "VALIDATION_ERROR",
            "PPTX Artifact 不存在",
            [{"field": "taskId", "reason": "当前任务尚未关联 PPTX_FILE Artifact"}],
        )

    metadata = artifact.metadata if isinstance(artifact.metadata, dict) else {}
    slide_previews = metadata.get("slidePreviews")
    if not isinstance(slide_previews, list):
        preview = metadata.get("preview", {})
        slide_previews = preview.get("slidePreviews", []) if isinstance(preview, dict) else []
    slide_reviews = _ppt_slide_reviews(slide_previews)
    target = next((slide for slide in slide_reviews if slide.get("index") == slide_index), None)
    if target is None:
        raise PptPageReviewUpdateError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "slideIndex", "reason": "未找到对应页"}],
        )

    before_status = str(target.get("reviewStatus"))
    before_summary = _ppt_page_review_summary(slide_reviews)
    target["reviewStatus"] = review_status
    target["manualComment"] = {
        "required": review_status in {"NEEDS_REVIEW", "REVISE_REQUIRED"},
        "text": comment or target.get("manualComment", {}).get("text") or "",
        "reviewer": reviewer,
        "updatedAt": None,
    }
    qa_signals = target.get("qaSignals", {})
    if not isinstance(qa_signals, dict):
        qa_signals = {}
    qa_signals["reviewFocus"] = "manual_page_review_updated"
    qa_signals["layout"] = "NEEDS_REVIEW" if review_status != "APPROVED" else qa_signals.get("layout", "PASS")
    target["qaSignals"] = qa_signals

    summary = _ppt_page_review_summary(slide_reviews)
    artifact.metadata = {
        **metadata,
        "slidePreviews": slide_reviews,
        "pageReviewSummary": summary,
        "reviewRequired": True,
        "generatedStatus": TaskStatus.WAITING_REVIEW.value,
        "autoPublishAllowed": False,
        "realPublish": False,
    }
    store.save_artifact(artifact)
    operation_event = create_operation_audit_event(
        action=OperationAction.PPT_PAGE_REVIEW_UPDATE,
        resource_type=OperationResourceType.ARTIFACT,
        resource_id=artifact.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=before_summary["status"],
        after_state=summary["status"],
        detail={
            "taskId": task.id,
            "artifactId": artifact.id,
            "slideIndex": slide_index,
            "fromReviewStatus": before_status,
            "toReviewStatus": review_status,
            "comment": comment,
            "pageReviewSummary": summary,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    )
    store.save_operation_audit_event(operation_event)
    detail = build_review_detail(store, task_id)
    ppt_page_review = detail["pptPageReview"] if detail else build_ppt_page_review_model(task.to_dict(), [artifact.to_dict()])
    return {
        "mode": "MOCK_ONLY",
        "task": task.to_dict(),
        "artifact": artifact.to_dict(),
        "pptPageReview": ppt_page_review,
        "operationAuditEvent": operation_event.to_dict(),
        "safety": {
            "taskStatusChanged": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "realLlmCalled": False,
        },
    }


def _assessment_plan_from_quality_signals(
    artifacts: list[dict[str, Any]],
    workflow_steps: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None, dict[str, Any]]:
    signal_sources: list[tuple[str, dict[str, Any]]] = []
    for artifact in artifacts:
        metadata = artifact.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        for key in ("workflowQualitySignals", "qualitySignals"):
            signals = metadata.get(key)
            if isinstance(signals, dict):
                signal_sources.append((f"artifact.metadata.{key}", signals))
    for detail in _step_details(workflow_steps):
        signals = detail.get("qualitySignals")
        if isinstance(signals, dict):
            signal_sources.append(("workflowStep.detail.qualitySignals", signals))

    for source, signals in signal_sources:
        grading_signals = signals.get("grading", signals)
        if not isinstance(grading_signals, dict):
            continue
        plan = grading_signals.get("assessmentPlan")
        if isinstance(plan, list):
            return [item for item in plan if isinstance(item, dict)], source, signals
    return [], None, {}


def _assessment_plan_from_grading_dsl(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None, bool | None]:
    grading_artifact = _grading_artifact(artifacts)
    path = _resolve_local_path(
        (grading_artifact or {}).get("path") or task.get("finalResultPath")
    )
    if path is None or not path.exists():
        return [], None, None
    try:
        document = load_yaml(path)
    except Exception:
        return [], None, None
    if not isinstance(document, dict):
        return [], None, None
    spec = document.get("spec", {})
    if not isinstance(spec, dict):
        return [], None, None
    plan = spec.get("assessmentPlan")
    if not isinstance(plan, list):
        return [], None, None
    checks = spec.get("checks", [])
    check_ids = [str(check.get("id")) for check in checks if isinstance(check, dict) and check.get("id")]
    plan_check_ids = [str(item.get("checkId")) for item in plan if isinstance(item, dict) and item.get("checkId")]
    aligned = bool(check_ids) and plan_check_ids == check_ids
    return [item for item in plan if isinstance(item, dict)], str(path), aligned


def _assessment_plan_summary(
    plan: list[dict[str, Any]],
    *,
    source: str | None,
    workflow_signals: dict[str, Any],
    aligned_with_checks: bool | None,
) -> dict[str, Any]:
    coverage = workflow_signals.get("coverage", {}) if isinstance(workflow_signals, dict) else {}
    explainability = coverage.get("explainability", {}) if isinstance(coverage, dict) else {}
    if aligned_with_checks is None and isinstance(explainability, dict):
        aligned_with_checks = explainability.get("assessmentPlanAlignedWithChecks")

    execution_strategies = _unique_preserve_order(
        [
            item.get("executionPlan", {}).get("strategy")
            for item in plan
            if isinstance(item.get("executionPlan"), dict) and item.get("executionPlan", {}).get("strategy")
        ]
    )
    mock_evidence_statuses = _unique_preserve_order(
        [
            item.get("mockEvidence", {}).get("status")
            for item in plan
            if isinstance(item.get("mockEvidence"), dict) and item.get("mockEvidence", {}).get("status")
        ]
    )
    required_limit_names: set[str] = set()
    for item in plan:
        execution_plan = item.get("executionPlan", {})
        if not isinstance(execution_plan, dict):
            continue
        required_limits = execution_plan.get("requiredLimits", {})
        if isinstance(required_limits, dict):
            required_limit_names.update(str(limit) for limit in required_limits)
    return {
        "available": bool(plan),
        "source": source,
        "planTotal": len(plan),
        "checkIds": [str(item.get("checkId")) for item in plan if item.get("checkId")],
        "checkTypes": _unique_preserve_order([str(item.get("type")) for item in plan if item.get("type")]),
        "runnerTypes": _unique_preserve_order([str(item.get("runner")) for item in plan if item.get("runner")]),
        "totalScore": sum(float(item.get("score", 0)) for item in plan if isinstance(item.get("score"), (int, float))),
        "riskLevels": _unique_preserve_order([str(item.get("riskLevel")) for item in plan if item.get("riskLevel")]),
        "executionStrategies": execution_strategies,
        "mockEvidenceStatuses": mock_evidence_statuses,
        "requiredLimits": sorted(required_limit_names),
        "alignedWithChecks": bool(aligned_with_checks),
        "sandboxRequiredBeforeRealExecution": any(
            bool(item.get("sandboxRequiredBeforeRealExecution")) for item in plan
        ),
        "realSandboxEvidenceRequired": bool(plan),
        "reviewFocus": [
            "checkId",
            "runner",
            "inputSummary",
            "executionPlan.requiredLimits",
            "mockEvidence.status",
            "riskLevel",
        ],
    }


def _assessment_plan_manual_review_checklist(
    task: dict[str, Any],
    assessment_plan: dict[str, Any],
) -> dict[str, Any]:
    summary = assessment_plan.get("summary", {})
    items = assessment_plan.get("items", [])
    visible = bool(assessment_plan.get("visible")) and bool(summary.get("available"))
    task_id = str(task.get("id", ""))
    mock_evidence_statuses = summary.get("mockEvidenceStatuses", [])
    required_limits = summary.get("requiredLimits", [])
    has_mock_evidence_gap = "MOCK_EVIDENCE_NOT_COLLECTED" in mock_evidence_statuses
    has_required_limits = all(
        limit in required_limits for limit in ["timeout", "cpu", "memory", "network", "filesystem", "process"]
    )

    checklist = [
        {
            "id": "verify_assessment_plan_aligned_with_checks",
            "title": "Confirm assessmentPlan matches Grading checks",
            "expected": "assessmentPlanAlignedWithChecks=true",
            "evidence": [
                "reviewDetail.assessmentPlan.summary",
                "reviewDetail.assessmentPlan.items",
            ],
            "matched": bool(summary.get("alignedWithChecks")),
            "status": "NEEDS_HUMAN_REVIEW",
        },
        {
            "id": "confirm_mock_evidence_not_collected",
            "title": "Confirm real execution evidence is not present in Mock phase",
            "expected": "mockEvidence.status=MOCK_EVIDENCE_NOT_COLLECTED",
            "evidence": [
                "reviewDetail.assessmentPlan.summary.mockEvidenceStatuses",
                "reviewDetail.assessmentPlan.items[].mockEvidence.status",
            ],
            "matched": has_mock_evidence_gap,
            "status": "NEEDS_HUMAN_REVIEW",
        },
        {
            "id": "confirm_real_sandbox_evidence_required_before_real_execution",
            "title": "Confirm real sandbox evidence is required before real grading",
            "expected": "realSandboxEvidenceRequired=true",
            "evidence": [
                "reviewDetail.assessmentPlan.summary.realSandboxEvidenceRequired",
                "reviewDetail.assessmentPlan.items[].sandboxRequiredBeforeRealExecution",
            ],
            "matched": bool(summary.get("realSandboxEvidenceRequired"))
            and any(bool(item.get("sandboxRequiredBeforeRealExecution")) for item in items),
            "status": "NEEDS_HUMAN_REVIEW",
        },
        {
            "id": "verify_required_limits_present",
            "title": "Confirm required execution limits are declared",
            "expected": "requiredLimits=timeout/cpu/memory/network/filesystem/process",
            "evidence": [
                "reviewDetail.assessmentPlan.summary.requiredLimits",
                "reviewDetail.assessmentPlan.items[].executionPlan.requiredLimits",
            ],
            "matched": has_required_limits,
            "status": "NEEDS_HUMAN_REVIEW",
        },
        {
            "id": "confirm_no_execution_or_publish",
            "title": "Confirm review does not execute code or publish content",
            "expected": "sandboxExecuted=false, contestantCodeExecuted=false, realSandboxRunEnabled=false, realPublishAllowed=false",
            "evidence": [
                "reviewDetail.safety.sandboxExecuted=false",
                "reviewDetail.safety.contestantCodeExecuted=false",
                "reviewDetail.reviewPolicy.realPublishAllowed=false",
            ],
            "matched": True,
            "status": "NEEDS_HUMAN_REVIEW",
        },
    ]
    return {
        "enabled": visible,
        "source": "reviewDetail.assessmentPlan",
        "taskId": task_id,
        "entryRoute": f"/grading/:id/review?taskId={task_id}" if task_id else "/grading/:id/review",
        "primaryReviewFocus": "review_assessment_plan_before_approval",
        "status": "NEEDS_HUMAN_REVIEW" if visible else "NOT_AVAILABLE",
        "checklist": checklist if visible else [],
        "operatorDecision": {
            "manualDecisionRequired": visible,
            "approveAllowedAfterChecklist": visible,
            "rejectRequiresReason": True,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realSandboxRunEnabled": False,
            "contestantCodeExecuted": False,
            "realPublishAllowed": False,
        },
    }


def build_assessment_plan_review_model(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    workflow_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    plan, source, workflow_signals = _assessment_plan_from_quality_signals(artifacts, workflow_steps)
    aligned_with_checks: bool | None = None
    if not plan:
        plan, source, aligned_with_checks = _assessment_plan_from_grading_dsl(task, artifacts)

    visible = task.get("taskType") in GRADING_REVIEW_TASK_TYPES or bool(plan)
    summary = _assessment_plan_summary(
        plan,
        source=source,
        workflow_signals=workflow_signals,
        aligned_with_checks=aligned_with_checks,
    )
    model = {
        "visible": visible,
        "summary": summary,
        "items": plan,
        "emptyState": visible and not bool(plan),
        "message": None if plan else "当前审核任务未关联 Grading assessmentPlan",
    }
    model["manualReviewChecklist"] = _assessment_plan_manual_review_checklist(task, model)
    return model


def _load_json_artifact_payload(artifact: dict[str, Any]) -> dict[str, Any] | None:
    path = _resolve_local_path(artifact.get("path"))
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def build_review_decision_note_summary(
    artifacts: list[dict[str, Any]],
    operation_audit_events: list[dict[str, Any]],
) -> dict[str, Any]:
    audit_by_id = {event.get("id"): event for event in operation_audit_events if event.get("id")}
    items: list[dict[str, Any]] = []
    for artifact in artifacts:
        if artifact.get("kind") != "REVIEW_DECISION_NOTE":
            continue
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        payload = _load_json_artifact_payload(artifact) or {}
        note = payload if payload.get("component") == "ReviewDecisionNote" else {}
        operation_event = note.get("operationAuditEvent") if isinstance(note.get("operationAuditEvent"), dict) else None
        operation_event_id = operation_event.get("id") if operation_event else metadata.get("operationAuditEventId")
        items.append(
            {
                "artifactId": artifact.get("id"),
                "artifactPath": artifact.get("path"),
                "artifactStatus": artifact.get("status"),
                "noteId": note.get("id"),
                "taskId": artifact.get("taskId") or note.get("taskId"),
                "reviewer": note.get("reviewer") or metadata.get("reviewer"),
                "decision": note.get("decision") or metadata.get("decision"),
                "reason": note.get("reason"),
                "taskStatusBefore": note.get("taskStatusBefore"),
                "taskStatusAfter": note.get("taskStatusAfter"),
                "statusChanged": bool(note.get("statusChanged", False)),
                "taskStatusUnchanged": bool(note.get("taskStatusUnchanged", True)),
                "source": note.get("source") or "reviewDetail.mergedGradingEvidence.reviewDecisionHints",
                "reviewDecisionHintsSnapshot": note.get("reviewDecisionHintsSnapshot", {})
                if isinstance(note.get("reviewDecisionHintsSnapshot"), dict)
                else {},
                "safety": note.get("safety", {}) if isinstance(note.get("safety"), dict) else {},
                "operationAuditEvent": audit_by_id.get(operation_event_id) or operation_event,
                "createdAt": artifact.get("createdAt"),
            }
        )
    items = sorted(items, key=lambda item: item.get("createdAt") or "", reverse=True)
    latest = items[0] if items else None
    return {
        "component": "ReviewDecisionNoteSummary",
        "visible": bool(items),
        "total": len(items),
        "latest": latest,
        "items": items,
        "source": "ArtifactKind.REVIEW_DECISION_NOTE",
        "safety": {
            "statusChanged": False,
            "taskStatusUnchanged": True,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def build_controlled_grading_evidence_review_model(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    operation_audit_events: list[dict[str, Any]],
) -> dict[str, Any]:
    report_items: list[dict[str, Any]] = []
    plan_items: list[dict[str, Any]] = []
    audit_by_id = {event.get("id"): event for event in operation_audit_events if event.get("id")}
    audit_by_resource_id = {
        event.get("resourceId"): event
        for event in operation_audit_events
        if event.get("resourceId")
    }

    for artifact in artifacts:
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        report_type = metadata.get("reportType")
        if artifact.get("kind") == "GRADING_DSL" and report_type == "CONTROLLED_DOCKER_GRADING_PLAN":
            summary = metadata.get("summary", {}) if isinstance(metadata.get("summary"), dict) else {}
            plan_items.append(
                {
                    "artifactId": artifact.get("id"),
                    "artifactPath": artifact.get("path"),
                    "artifactStatus": artifact.get("status"),
                    "sourceGradingPath": artifact.get("sourceRef"),
                    "summary": summary,
                    "patches": metadata.get("patches", []) if isinstance(metadata.get("patches"), list) else [],
                    "deferredChecks": metadata.get("deferredChecks", [])
                    if isinstance(metadata.get("deferredChecks"), list)
                    else [],
                    "selectedCheckTotal": summary.get("selectedCheckTotal", 0),
                    "deferredCheckTotal": summary.get("deferredCheckTotal", 0),
                    "executableScore": summary.get("executableScore"),
                    "deferredScore": summary.get("deferredScore"),
                    "manualReviewRequired": bool(metadata.get("reviewRequired", True)),
                    "sandboxRequiredBeforeExecution": bool(metadata.get("sandboxRequiredBeforeExecution", True)),
                    "operationAuditEvent": audit_by_resource_id.get(artifact.get("path"))
                    or audit_by_resource_id.get(metadata.get("sourceGradingId")),
                }
            )
        if artifact.get("kind") != "GRADING_REPORT" or report_type != "CONTROLLED_DOCKER_SANDBOX_RUN":
            continue
        payload = _load_json_artifact_payload(artifact) or {}
        safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else metadata.get("safety", {})
        if not isinstance(safety, dict):
            safety = {}
        execution_summary = (
            payload.get("executionSummary")
            if isinstance(payload.get("executionSummary"), dict)
            else metadata.get("executionSummary", {})
        )
        if not isinstance(execution_summary, dict):
            execution_summary = {}
        score = payload.get("score") if isinstance(payload.get("score"), dict) else metadata.get("score", {})
        if not isinstance(score, dict):
            score = {}
        check_summary = (
            payload.get("checkSummary")
            if isinstance(payload.get("checkSummary"), dict)
            else metadata.get("checkSummary", {})
        )
        if not isinstance(check_summary, dict):
            check_summary = {}
        report_detail = payload.get("reportDetail") if isinstance(payload.get("reportDetail"), dict) else {}
        report_items.append(
            {
                "artifactId": artifact.get("id"),
                "artifactPath": artifact.get("path"),
                "artifactStatus": artifact.get("status"),
                "sourcePlanPath": artifact.get("sourceRef"),
                "reportId": payload.get("id"),
                "mode": payload.get("mode") or "CONTROLLED_DOCKER_SANDBOX_POC",
                "gradingId": payload.get("gradingId") or metadata.get("gradingId"),
                "submissionRoot": payload.get("submissionRoot") or metadata.get("submissionRoot"),
                "runner": payload.get("runner", {}) if isinstance(payload.get("runner"), dict) else {},
                "executionSummary": execution_summary,
                "score": score,
                "checkSummary": check_summary,
                "checks": [
                    {
                        "id": check.get("id"),
                        "type": check.get("type"),
                        "status": check.get("status"),
                        "passed": check.get("passed"),
                        "score": check.get("score"),
                        "earnedScore": check.get("earnedScore"),
                    }
                    for check in payload.get("checks", [])
                    if isinstance(check, dict)
                ],
                "assessmentPlanSummary": payload.get("assessmentPlanSummary", {})
                if isinstance(payload.get("assessmentPlanSummary"), dict)
                else metadata.get("assessmentPlanSummary", {}),
                "safety": safety,
                "reportDetail": {
                    "source": report_detail.get("source"),
                    "mode": report_detail.get("mode"),
                    "checkSummary": report_detail.get("checkSummary", {}),
                    "safety": report_detail.get("safety", {}),
                },
                "operationAuditEvent": audit_by_id.get(
                    (payload.get("operationAuditEvent") or {}).get("id")
                    if isinstance(payload.get("operationAuditEvent"), dict)
                    else None
                )
                or audit_by_resource_id.get(payload.get("id")),
            }
        )

    executed_total = sum(
        int(item.get("executionSummary", {}).get("executed", 0) or 0)
        for item in report_items
    )
    passed_total = sum(
        int(item.get("executionSummary", {}).get("passed", 0) or 0)
        for item in report_items
    )
    earned_score = sum(
        float(item.get("score", {}).get("earnedScore", 0) or 0)
        for item in report_items
    )
    total_score = sum(
        float(item.get("score", {}).get("totalScore", 0) or 0)
        for item in report_items
    )
    sandbox_executed = any(bool(item.get("safety", {}).get("sandboxExecuted")) for item in report_items)
    contestant_code_executed = any(bool(item.get("safety", {}).get("contestantCodeExecuted")) for item in report_items)
    command_executed = any(bool(item.get("safety", {}).get("commandExecuted")) for item in report_items)
    pytest_executed = any(bool(item.get("safety", {}).get("pytestExecuted")) for item in report_items)
    network_enabled = any(bool(item.get("safety", {}).get("networkEnabled")) for item in report_items)
    visible = bool(report_items or plan_items)
    return {
        "visible": visible,
        "source": "reviewDetail.artifacts.GRADING_REPORT[metadata.reportType=CONTROLLED_DOCKER_SANDBOX_RUN]",
        "taskId": task.get("id"),
        "mode": "CONTROLLED_DOCKER_EVIDENCE_REVIEW",
        "planTotal": len(plan_items),
        "reportTotal": len(report_items),
        "plans": plan_items,
        "reports": report_items,
        "summary": {
            "available": visible,
            "planTotal": len(plan_items),
            "reportTotal": len(report_items),
            "executedTotal": executed_total,
            "passedTotal": passed_total,
            "earnedScore": earned_score,
            "totalScore": total_score,
            "sandboxExecuted": sandbox_executed,
            "contestantCodeExecuted": contestant_code_executed,
            "commandExecuted": command_executed,
            "pytestExecuted": pytest_executed,
            "networkEnabled": network_enabled,
            "manualReviewRequired": visible,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "safety": {
            "sandboxExecuted": sandbox_executed,
            "contestantCodeExecuted": contestant_code_executed,
            "commandExecuted": command_executed,
            "pytestExecuted": pytest_executed,
            "networkEnabled": network_enabled,
            "hostExecutionAllowed": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
        "emptyState": not visible,
        "message": None if visible else "当前审核任务未关联受控 Docker 评分证据",
    }


def _merged_evidence_source_kind(report_mode: Any) -> str:
    if report_mode == "CONTROLLED_DOCKER_SANDBOX_POC":
        return "controlledDocker"
    if report_mode == "READONLY_REAL_SANDBOX_POC":
        return "readonlyStatic"
    return "unknown"


def _merged_evidence_recommended_action(item: dict[str, Any], source_kind: str) -> str:
    status = str(item.get("status") or "UNKNOWN")
    passed = item.get("passed")
    if status == "DEFERRED" or passed is None:
        return "collect_missing_evidence_or_manual_review"
    if passed is False or status in {"FAILED", "ERROR"}:
        return "review_failed_check_evidence_before_decision"
    if source_kind == "controlledDocker":
        return "verify_controlled_docker_output_and_score"
    if source_kind == "readonlyStatic":
        return "verify_static_evidence_and_score"
    return "verify_merged_evidence_source_and_score"


def _merged_evidence_review_items(checks: Any) -> list[dict[str, Any]]:
    if not isinstance(checks, list):
        return []
    items: list[dict[str, Any]] = []
    for index, check in enumerate(item for item in checks if isinstance(item, dict)):
        source = check.get("evidenceSource") if isinstance(check.get("evidenceSource"), dict) else {}
        source_kind = _merged_evidence_source_kind(source.get("reportMode"))
        status = str(check.get("status") or "UNKNOWN")
        passed = check.get("passed")
        items.append(
            {
                "index": index,
                "checkId": str(check.get("id") or ""),
                "checkType": str(check.get("type") or "unknown"),
                "status": status,
                "passed": passed if isinstance(passed, bool) else None,
                "score": check.get("score", 0),
                "earnedScore": check.get("earnedScore", 0),
                "evidenceSourceKind": source_kind,
                "evidenceSource": {
                    "reportIndex": source.get("reportIndex"),
                    "sourcePath": source.get("sourcePath"),
                    "reportId": source.get("reportId"),
                    "reportMode": source.get("reportMode"),
                    "runnerId": source.get("runnerId"),
                },
                "recommendedAction": _merged_evidence_recommended_action(check, source_kind),
                "manualReviewRequired": passed is not True or status not in {"PASSED", "OK"},
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
                "safety": {
                    "mergeExecutedOnlyExistingReports": True,
                    "sourceReportMode": source.get("reportMode"),
                    "controlledDockerEvidence": source_kind == "controlledDocker",
                    "readonlyStaticEvidence": source_kind == "readonlyStatic",
                    "contestantCodeExecutedByMergeTool": False,
                    "commandExecutedByMergeTool": False,
                    "notebookExecutedByMergeTool": False,
                    "networkAllowed": False,
                    "hostExecutionAllowed": False,
                },
            }
        )
    return items


def _merged_evidence_review_decision_hints(
    check_items: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    hints: list[dict[str, Any]] = []
    approve_ready_total = 0
    revise_required_total = 0
    evidence_missing_total = 0

    for item in (entry for entry in check_items if isinstance(entry, dict)):
        check_id = str(item.get("checkId") or "unknown_check")
        status = str(item.get("status") or "UNKNOWN").upper()
        passed = item.get("passed")
        earned_score = item.get("earnedScore", 0)
        score = item.get("score", 0)
        evidence_source_kind = str(item.get("evidenceSourceKind") or "unknown")
        recommended_action = str(item.get("recommendedAction") or "manual_review")
        severity = "info"
        decision_hint = "CAN_REVIEW_PASS"
        reason = "evidence_passed_and_manual_review_required"

        if evidence_source_kind == "unknown":
            severity = "warning"
            decision_hint = "NEEDS_EVIDENCE"
            reason = "missing_check_evidence_source"
            evidence_missing_total += 1
        elif status in {"FAILED", "ERROR"} or passed is False:
            severity = "error"
            decision_hint = "NEEDS_REVISION"
            reason = "check_failed_or_error"
            revise_required_total += 1
        elif passed is not True or status not in {"PASSED", "OK"}:
            severity = "warning"
            decision_hint = "NEEDS_MANUAL_VERIFICATION"
            reason = "check_not_explicitly_passed"
        else:
            approve_ready_total += 1

        hints.append(
            {
                "checkId": check_id,
                "checkType": item.get("checkType"),
                "status": status,
                "passed": passed if isinstance(passed, bool) else None,
                "earnedScore": earned_score,
                "score": score,
                "evidenceSourceKind": evidence_source_kind,
                "recommendedAction": recommended_action,
                "decisionHint": decision_hint,
                "severity": severity,
                "reason": reason,
                "manualReviewRequired": True,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
            }
        )

    total = len(hints)
    if total == 0:
        overall_hint = "NEEDS_EVIDENCE"
        next_action = "run_grading_evidence_before_review_decision"
    elif revise_required_total > 0:
        overall_hint = "NEEDS_REVISION"
        next_action = "request_revision_for_failed_checks"
    elif evidence_missing_total > 0:
        overall_hint = "NEEDS_EVIDENCE"
        next_action = "collect_missing_check_evidence"
    else:
        overall_hint = "READY_FOR_MANUAL_REVIEW_DECISION"
        next_action = "review_all_check_evidence_before_approval"

    return {
        "available": total > 0,
        "source": "reviewDetail.mergedGradingEvidence.checkEvidenceReviewItems",
        "mode": "DETERMINISTIC_REVIEW_DECISION_HINTS",
        "overallHint": overall_hint,
        "nextRecommendedAction": next_action,
        "hintTotal": total,
        "approveReadyTotal": approve_ready_total,
        "reviseRequiredTotal": revise_required_total,
        "evidenceMissingTotal": evidence_missing_total,
        "earnedScore": summary.get("earnedScore", 0),
        "totalScore": summary.get("totalScore", 0),
        "items": hints,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
    }


def _manual_checklist_review_decision_hints(
    manual_checklist: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    checklist_summary = (
        manual_checklist.get("summary")
        if isinstance(manual_checklist.get("summary"), dict)
        else {}
    )
    recommendation = (
        manual_checklist.get("decisionNoteRecommendation")
        if isinstance(manual_checklist.get("decisionNoteRecommendation"), dict)
        else {}
    )
    items = manual_checklist.get("items") if isinstance(manual_checklist.get("items"), list) else []
    hints: list[dict[str, Any]] = []
    approve_ready_total = 0
    revise_required_total = 0
    evidence_missing_total = 0

    for item in (entry for entry in items if isinstance(entry, dict)):
        recommended_decision = str(item.get("recommendedDecision") or "needs-evidence")
        if recommended_decision == "approve-ready":
            decision_hint = "CAN_REVIEW_PASS"
            reason = "manual_checklist_ready_for_approve_ready_decision"
            severity = "info"
            approve_ready_total += 1
        elif recommended_decision == "needs-revision":
            decision_hint = "NEEDS_REVISION"
            reason = "manual_checklist_recommends_revision"
            severity = "error"
            revise_required_total += 1
        else:
            decision_hint = "NEEDS_EVIDENCE"
            reason = "manual_checklist_recommends_more_evidence"
            severity = "warning"
            evidence_missing_total += 1
        hints.append(
            {
                "checkId": item.get("checkId"),
                "checkType": item.get("checkType"),
                "status": item.get("selectedEvidenceStatus") or manual_checklist.get("status"),
                "passed": None,
                "earnedScore": item.get("earnedScore", 0),
                "score": item.get("score", 0),
                "evidenceSourceKind": item.get("selectedEvidenceMode") or "manualChecklist",
                "recommendedAction": item.get("recommendedReviewAction") or "manual_review",
                "recommendedDecision": recommended_decision,
                "readyForDecision": bool(item.get("readyForDecision") is True),
                "decisionHint": decision_hint,
                "severity": severity,
                "reason": reason,
                "manualReviewRequired": True,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
            }
        )

    recommendation_decision = str(recommendation.get("decision") or "needs-evidence")
    if recommendation_decision == "approve-ready":
        overall_hint = "READY_FOR_MANUAL_REVIEW_DECISION"
        next_action = "record_approve_ready_decision_note_before_manual_approve"
    elif recommendation_decision == "needs-revision":
        overall_hint = "NEEDS_REVISION"
        next_action = "record_needs_revision_decision_note_or_request_revision"
    else:
        overall_hint = "NEEDS_EVIDENCE"
        next_action = "collect_or_review_grading_evidence_before_decision_note"

    return {
        "available": bool(items),
        "source": "GRADING_EVIDENCE_AUTO_REPORT.manualReviewChecklist",
        "mode": "DETERMINISTIC_REVIEW_DECISION_HINTS_FROM_MANUAL_CHECKLIST",
        "overallHint": overall_hint,
        "nextRecommendedAction": next_action,
        "hintTotal": len(hints),
        "approveReadyTotal": approve_ready_total,
        "reviseRequiredTotal": revise_required_total,
        "evidenceMissingTotal": evidence_missing_total,
        "manualChecklistStatus": manual_checklist.get("status"),
        "manualChecklistReadyForDecisionTotal": checklist_summary.get("readyForDecisionTotal", 0),
        "decisionNoteRecommendation": recommendation_decision,
        "decisionNoteReason": recommendation.get("reason"),
        "earnedScore": summary.get("earnedScore", 0),
        "totalScore": summary.get("totalScore", 0),
        "items": hints,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
    }


def build_merged_grading_evidence_review_model(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    operation_audit_events: list[dict[str, Any]],
) -> dict[str, Any]:
    report_items: list[dict[str, Any]] = []
    audit_by_id = {event.get("id"): event for event in operation_audit_events if event.get("id")}
    audit_by_resource_id = {
        event.get("resourceId"): event
        for event in operation_audit_events
        if event.get("resourceId")
    }

    for artifact in artifacts:
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        report_type = metadata.get("reportType")
        if artifact.get("kind") != "GRADING_REPORT" or report_type not in {
            "GRADING_EVIDENCE_MERGE",
            "GRADING_EVIDENCE_AUTO",
        }:
            continue
        payload = _load_json_artifact_payload(artifact) or {}
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else metadata.get("summary", {})
        if not isinstance(summary, dict):
            summary = {}
        coverage = (
            payload.get("evidenceCoverage")
            if isinstance(payload.get("evidenceCoverage"), dict)
            else metadata.get("evidenceCoverage", {})
        )
        if not isinstance(coverage, dict):
            coverage = {}
        safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else metadata.get("safety", {})
        if not isinstance(safety, dict):
            safety = {}
        operation_event_id = (
            payload.get("operationAuditEvent", {}).get("id")
            if isinstance(payload.get("operationAuditEvent"), dict)
            else None
        )
        check_evidence_review_items = _merged_evidence_review_items(payload.get("checks"))
        score_preview = (
            payload.get("scorePreview")
            if isinstance(payload.get("scorePreview"), dict)
            else metadata.get("scorePreview")
        )
        if not isinstance(score_preview, dict):
            score_preview = {}
        report_items.append(
            {
                "artifactId": artifact.get("id"),
                "artifactPath": artifact.get("path"),
                "artifactStatus": artifact.get("status"),
                "artifactReportType": report_type,
                "sourceReportRef": artifact.get("sourceRef"),
                "reportId": payload.get("id"),
                "mode": payload.get("mode") or "GRADING_EVIDENCE_MERGE_REPORT",
                "sourceMode": payload.get("sourceMode"),
                "sourceReportTotal": payload.get("sourceReportTotal")
                or metadata.get("sourceReportTotal")
                or 0,
                "sourceReports": payload.get("sourceReports", [])
                if isinstance(payload.get("sourceReports"), list)
                else [],
                "summary": summary,
                "evidenceCoverage": coverage,
                "checkEvidenceReviewItems": check_evidence_review_items,
                "scorePreview": score_preview,
                "mergeWarnings": payload.get("mergeWarnings", [])
                if isinstance(payload.get("mergeWarnings"), list)
                else [],
                "warnings": payload.get("warnings", [])
                if isinstance(payload.get("warnings"), list)
                else [],
                "manualReviewChecklist": payload.get("manualReviewChecklist")
                if isinstance(payload.get("manualReviewChecklist"), dict)
                else None,
                "steps": payload.get("steps", [])
                if isinstance(payload.get("steps"), list)
                else [],
                "safety": safety,
                "operationAuditEvent": audit_by_id.get(operation_event_id)
                or audit_by_resource_id.get(payload.get("id")),
            }
        )

    visible = bool(report_items)
    latest = report_items[0] if report_items else {}
    latest_summary = latest.get("summary", {}) if isinstance(latest.get("summary"), dict) else {}
    latest_coverage = latest.get("evidenceCoverage", {}) if isinstance(latest.get("evidenceCoverage"), dict) else {}
    controlled_coverage = (
        latest_coverage.get("controlledDocker", {})
        if isinstance(latest_coverage.get("controlledDocker"), dict)
        else {}
    )
    readonly_coverage = (
        latest_coverage.get("readonlyStatic", {})
        if isinstance(latest_coverage.get("readonlyStatic"), dict)
        else {}
    )
    latest_safety = latest.get("safety", {}) if isinstance(latest.get("safety"), dict) else {}
    latest_manual_checklist = (
        latest.get("manualReviewChecklist")
        if isinstance(latest.get("manualReviewChecklist"), dict)
        else {}
    )
    latest_manual_checklist_summary = (
        latest_manual_checklist.get("summary")
        if isinstance(latest_manual_checklist.get("summary"), dict)
        else {}
    )
    latest_manual_decision = (
        latest_manual_checklist.get("decisionNoteRecommendation")
        if isinstance(latest_manual_checklist.get("decisionNoteRecommendation"), dict)
        else {}
    )
    latest_score_preview = (
        latest.get("scorePreview")
        if isinstance(latest.get("scorePreview"), dict)
        else {}
    )
    latest_check_items = (
        latest.get("checkEvidenceReviewItems", [])
        if isinstance(latest.get("checkEvidenceReviewItems"), list)
        else []
    )
    manual_check_items = [
        item
        for item in latest_check_items
        if isinstance(item, dict) and item.get("manualReviewRequired") is True
    ]
    review_decision_hints = (
        _manual_checklist_review_decision_hints(latest_manual_checklist, latest_summary)
        if latest_manual_checklist
        else _merged_evidence_review_decision_hints(
            latest_check_items,
            latest_summary,
        )
    )
    return {
        "visible": visible,
        "source": "reviewDetail.artifacts.GRADING_REPORT[metadata.reportType=GRADING_EVIDENCE_MERGE|GRADING_EVIDENCE_AUTO]",
        "taskId": task.get("id"),
        "mode": "GRADING_EVIDENCE_MERGE_REVIEW",
        "latestReportType": latest.get("artifactReportType"),
        "latestReportMode": latest.get("mode"),
        "latestSourceMode": latest.get("sourceMode"),
        "reportTotal": len(report_items),
        "reports": report_items,
        "latestReport": latest if visible else None,
        "checkEvidenceReviewItems": latest_check_items,
        "reviewDecisionHints": review_decision_hints,
        "summary": {
            "available": visible,
            "reportTotal": len(report_items),
            "latestReportPath": latest.get("artifactPath"),
            "latestReportId": latest.get("reportId"),
            "latestReportType": latest.get("artifactReportType"),
            "latestReportMode": latest.get("mode"),
            "latestSourceMode": latest.get("sourceMode"),
            "sourceReportTotal": int(latest.get("sourceReportTotal") or 0),
            "checkTotal": int(latest_summary.get("checkTotal") or 0),
            "executedTotal": int(latest_summary.get("executed") or 0),
            "passedCheckTotal": int(latest_summary.get("passedCheckTotal") or 0),
            "failedCheckTotal": int(latest_summary.get("failedCheckTotal") or latest_summary.get("failed") or 0),
            "deferredCheckTotal": int(latest_summary.get("deferredCheckTotal") or latest_summary.get("deferred") or 0),
            "earnedScore": latest_summary.get("earnedScore", 0),
            "totalScore": latest_summary.get("totalScore", 0),
            "coverageRatio": latest_coverage.get("coverageRatio", 0),
            "controlledDockerCheckTotal": int(controlled_coverage.get("checkTotal") or 0),
            "readonlyStaticCheckTotal": int(readonly_coverage.get("checkTotal") or 0),
            "checkEvidenceReviewItemTotal": len(latest_check_items),
            "manualCheckReviewTotal": len(manual_check_items),
            "autoEvidenceReport": latest.get("artifactReportType") == "GRADING_EVIDENCE_AUTO",
            "scorePreviewAvailable": bool(latest_score_preview),
            "scorePreviewStatus": latest_score_preview.get("status"),
            "scorePreviewEarnedScore": latest_score_preview.get("earnedScore"),
            "scorePreviewTotalScore": latest_score_preview.get("totalScore"),
            "scorePreviewCoveredScore": latest_score_preview.get("coveredScore"),
            "scorePreviewMissingScore": latest_score_preview.get("missingScore"),
            "scorePreviewCoverageRatio": latest_score_preview.get("coverageRatio"),
            "scorePreviewPassRate": latest_score_preview.get("passRate"),
            "scorePreviewReadyForDecisionNote": latest_score_preview.get("readyForDecisionNote"),
            "scorePreviewMissingEvidenceTotal": latest_score_preview.get("missingEvidenceTotal"),
            "scorePreviewMissingCheckIds": latest_score_preview.get("missingCheckIds", []),
            "autoEvidenceStepTotal": len(latest.get("steps") if isinstance(latest.get("steps"), list) else []),
            "autoEvidenceWarningTotal": len(
                latest.get("warnings") if isinstance(latest.get("warnings"), list) else []
            ),
            "manualReviewChecklistAvailable": bool(latest_manual_checklist),
            "manualReviewChecklistStatus": latest_manual_checklist.get("status"),
            "manualReviewChecklistTotal": latest_manual_checklist_summary.get("itemTotal", 0),
            "manualReviewChecklistReadyTotal": latest_manual_checklist_summary.get("readyForDecisionTotal", 0),
            "manualReviewChecklistMissingEvidenceTotal": latest_manual_checklist_summary.get(
                "missingEvidenceTotal", 0
            ),
            "decisionNoteRecommendation": latest_manual_decision.get("decision"),
            "decisionNoteRecommendationReason": latest_manual_decision.get("reason"),
            "nextDecisionNoteAction": review_decision_hints.get("nextRecommendedAction"),
            "manualReviewRequired": visible,
            "reviewDecisionHint": review_decision_hints["overallHint"],
            "reviewDecisionHintTotal": review_decision_hints["hintTotal"],
            "reviewDecisionReviseRequiredTotal": review_decision_hints["reviseRequiredTotal"],
            "reviewDecisionEvidenceMissingTotal": review_decision_hints["evidenceMissingTotal"],
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "safety": {
            "sandboxExecuted": bool(latest_safety.get("sandboxExecuted", False)),
            "readonlyOnly": bool(latest_safety.get("readonlyOnly", False)),
            "contestantCodeExecuted": bool(latest_safety.get("contestantCodeExecuted", False)),
            "commandExecuted": bool(latest_safety.get("commandExecuted", False)),
            "pytestExecuted": bool(latest_safety.get("pytestExecuted", False)),
            "notebookExecuted": bool(latest_safety.get("notebookExecuted", False)),
            "networkEnabled": bool(latest_safety.get("networkEnabled", False)),
            "hostExecutionAllowed": bool(latest_safety.get("hostExecutionAllowed", False)),
            "mergeExecutedOnlyExistingReports": bool(latest_safety.get("mergeExecutedOnlyExistingReports", visible)),
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
        "emptyState": not visible,
        "message": None if visible else "当前审核任务未关联合并评分 evidence 报告",
    }


def _generation_profile(artifacts: list[dict[str, Any]], workflow_steps: list[dict[str, Any]]) -> dict[str, Any]:
    context = _first_artifact_metadata(artifacts, "generationContext")
    if context is None:
        context = _first_step_detail(workflow_steps, "labGenerationContext")
    return {
        "available": isinstance(context, dict),
        "context": context if isinstance(context, dict) else {},
    }


def _quality_signal_summary(artifacts: list[dict[str, Any]], workflow_steps: list[dict[str, Any]]) -> dict[str, Any]:
    workflow_signals = _first_artifact_metadata(artifacts, "workflowQualitySignals")
    lab_signals = _first_artifact_metadata(artifacts, "qualitySignals")
    summary = _first_artifact_metadata(artifacts, "qualitySignalSummary")
    highlights = _first_artifact_metadata(artifacts, "reviewHighlights")
    material_coverage = None
    if isinstance(workflow_signals, dict):
        lab_signals = lab_signals or workflow_signals.get("lab")
        summary = summary or workflow_signals.get("overall")
        highlights = highlights or workflow_signals.get("reviewHighlights")
        material_coverage = workflow_signals.get("materialCoverage")
    if lab_signals is None:
        step_signals = _first_step_detail(workflow_steps, "qualitySignals")
        lab_signals = step_signals.get("lab") if isinstance(step_signals, dict) else None
        summary = summary or (step_signals.get("overall") if isinstance(step_signals, dict) else None)
        highlights = highlights or (step_signals.get("reviewHighlights") if isinstance(step_signals, dict) else None)
        material_coverage = material_coverage or (
            step_signals.get("materialCoverage") if isinstance(step_signals, dict) else None
        )
    return {
        "available": isinstance(lab_signals, dict) or isinstance(summary, dict),
        "overall": summary if isinstance(summary, dict) else {},
        "lab": lab_signals if isinstance(lab_signals, dict) else {},
        "materialCoverage": material_coverage if isinstance(material_coverage, dict) else {},
        "reviewHighlights": highlights if isinstance(highlights, list) else [],
    }


def _total_tokens(usage: Any) -> int | None:
    if not isinstance(usage, dict):
        return None
    total = usage.get("total_tokens", usage.get("totalTokens"))
    return int(total) if isinstance(total, int) else None


def _provider_events_for_task(
    store: JsonTaskStore,
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    workflow_steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    task_id = str(task.get("id") or "")
    trace_id = task.get("traceId")
    artifact_paths = {
        str(artifact.get("path"))
        for artifact in artifacts
        if artifact.get("path")
    }
    by_id: dict[str, dict[str, Any]] = {}

    for detail in _step_details(workflow_steps):
        embedded_event = detail.get("providerCallAuditEvent")
        if isinstance(embedded_event, dict) and embedded_event.get("id"):
            by_id[str(embedded_event["id"])] = embedded_event

    for event in store.list_provider_call_audit_events(trace_id=str(trace_id) if trace_id else None):
        payload = event.to_dict()
        detail = payload.get("detail", {}) if isinstance(payload.get("detail"), dict) else {}
        if (
            payload.get("id") in by_id
            or detail.get("taskId") == task_id
            or (payload.get("dslPath") and payload.get("dslPath") in artifact_paths)
        ):
            by_id[payload["id"]] = payload

    return sorted(by_id.values(), key=lambda item: item.get("occurredAt") or "", reverse=True)


def _provider_call_summary(event: dict[str, Any]) -> dict[str, Any]:
    detail = event.get("detail", {}) if isinstance(event.get("detail"), dict) else {}
    usage = detail.get("usage") if isinstance(detail.get("usage"), dict) else None
    response_id = detail.get("responseId")
    return {
        "id": event.get("id"),
        "operation": event.get("operation"),
        "providerId": event.get("providerId"),
        "adapterId": event.get("adapterId"),
        "mode": event.get("mode"),
        "status": event.get("status"),
        "promptId": event.get("promptId"),
        "outputKind": event.get("outputKind"),
        "dslId": event.get("dslId"),
        "dslPath": event.get("dslPath"),
        "responseId": response_id,
        "model": detail.get("model"),
        "apiSurface": detail.get("apiSurface"),
        "normalization": detail.get("normalization") if isinstance(detail.get("normalization"), dict) else None,
        "qualitySummary": detail.get("qualitySummary") if isinstance(detail.get("qualitySummary"), dict) else None,
        "usage": usage,
        "totalTokens": _total_tokens(usage),
        "realLlmCalled": bool(event.get("realLlmCalled", False)),
        "secretsRead": bool(event.get("secretsRead", False)),
        "networkAccess": bool(event.get("networkAccess", False)),
        "generatedContentCreated": bool(event.get("generatedContentCreated", False)),
        "taskCreated": bool(event.get("taskCreated", False)),
        "reviewBypassed": bool(event.get("reviewBypassed", False)),
        "autoPublishAllowed": bool(event.get("autoPublishAllowed", False)),
        "realPublish": bool(event.get("realPublish", False)),
        "workflowId": detail.get("workflowId"),
        "workflowStep": detail.get("workflowStep"),
    }


def _artifact_provider_quality_summaries(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for artifact in artifacts:
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        provider_summary = metadata.get("providerSummary") if isinstance(metadata.get("providerSummary"), dict) else {}
        quality_summary = provider_summary.get("qualitySummary") if isinstance(provider_summary, dict) else None
        if isinstance(quality_summary, dict):
            summaries.append(quality_summary)
    return summaries


def _artifact_content_quality_summaries(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for artifact in artifacts:
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        summary = metadata.get("contentQualitySummary")
        if isinstance(summary, dict) and summary:
            summaries.append(summary)
    return summaries


def _content_quality_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    workflow_summary = None
    items: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        candidate = metadata.get("workflowContentQualitySummary")
        if isinstance(candidate, dict) and candidate:
            workflow_summary = candidate
        item = metadata.get("contentQualitySummary")
        dsl_kind = str(metadata.get("dslKind") or "").strip().lower()
        if isinstance(item, dict) and item and dsl_kind:
            items[dsl_kind] = item

    if isinstance(workflow_summary, dict) and workflow_summary:
        merged = dict(workflow_summary)
        if items:
            merged["items"] = {**workflow_summary.get("items", {}), **items} if isinstance(workflow_summary.get("items"), dict) else items
        merged["available"] = True
        return merged

    summaries = _artifact_content_quality_summaries(artifacts)
    if not summaries:
        return {"available": False, "itemTotal": 0}
    issue_total = sum(int(item.get("issueTotal", 0) or 0) for item in summaries)
    blocking_total = sum(int(item.get("blockingIssueTotal", 0) or 0) for item in summaries)
    return {
        "available": True,
        "component": "RealDslContentQualitySummary",
        "source": "artifact.metadata.contentQualitySummary",
        "status": (
            "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
            if blocking_total
            else ("REVIEW_WITH_WARNINGS" if issue_total else "READY_FOR_MANUAL_REVIEW")
        ),
        "itemTotal": len(summaries),
        "issueTotal": issue_total,
        "blockingIssueTotal": blocking_total,
        "readyForReviewTotal": sum(1 for item in summaries if item.get("readyForManualReview") is True),
        "readyForImportPreviewKinds": [
            str(item.get("kind"))
            for item in summaries
            if item.get("readyForImportPreview") is True and item.get("kind")
        ],
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "items": {str(item.get("kind")): item for item in summaries if item.get("kind")},
    }


def _provider_quality_summary(quality_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if not quality_summaries:
        return {"available": False, "itemCount": 0}
    if len(quality_summaries) == 1:
        return {"available": True, **quality_summaries[0]}

    patch_total = sum(
        int(summary.get("normalizationPatchCount"))
        for summary in quality_summaries
        if isinstance(summary.get("normalizationPatchCount"), int)
    )
    repair_error_total = sum(
        int(summary.get("schemaRepairErrorCount"))
        for summary in quality_summaries
        if isinstance(summary.get("schemaRepairErrorCount"), int)
    )
    issue_total = sum(
        int(summary.get("issueCount"))
        for summary in quality_summaries
        if isinstance(summary.get("issueCount"), int)
    )
    return {
        "available": True,
        "kind": "mixed",
        "itemCount": len(quality_summaries),
        "readyForReview": all(bool(summary.get("readyForReview")) for summary in quality_summaries),
        "needsManualReview": any(bool(summary.get("needsManualReview")) for summary in quality_summaries),
        "normalizationApplied": any(bool(summary.get("normalizationApplied")) for summary in quality_summaries),
        "normalizationPatchCount": patch_total,
        "schemaRepairAttempted": any(bool(summary.get("schemaRepairAttempted")) for summary in quality_summaries),
        "schemaRepairApplied": any(bool(summary.get("schemaRepairApplied")) for summary in quality_summaries),
        "schemaRepairErrorCount": repair_error_total,
        "issueCount": issue_total,
    }


def _provider_summary(
    artifacts: list[dict[str, Any]],
    workflow_steps: list[dict[str, Any]],
    provider_call_audit_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    provider_call_audit_events = provider_call_audit_events or []
    provider_adapters = sorted(
        {
            str(artifact.get("metadata", {}).get("providerAdapter"))
            for artifact in artifacts
            if artifact.get("metadata", {}).get("providerAdapter")
        }
    )
    modes = sorted(
        {
            str(artifact.get("mode"))
            for artifact in artifacts
            if artifact.get("mode")
        }
    )
    response_ids: list[str] = []
    provider_ids: set[str] = set()
    models: list[str] = []
    api_surfaces: list[str] = []
    usage_items: list[dict[str, Any]] = []
    for detail in _step_details(workflow_steps):
        provider = detail.get("provider")
        if isinstance(provider, dict):
            if provider.get("providerId"):
                provider_ids.add(str(provider["providerId"]))
            if provider.get("responseId"):
                response_ids.append(str(provider["responseId"]))
            if provider.get("model"):
                models.append(str(provider["model"]))
            if provider.get("apiSurface"):
                api_surfaces.append(str(provider["apiSurface"]))
        generation = detail.get("generation")
        if isinstance(generation, dict):
            usage = generation.get("usage")
            if isinstance(usage, dict):
                usage_items.append(
                    {
                        "source": "workflowStep",
                        "outputKind": generation.get("outputKind"),
                        "responseId": generation.get("responseId"),
                        "usage": usage,
                        "totalTokens": _total_tokens(usage),
                    }
                )

    calls = [_provider_call_summary(event) for event in provider_call_audit_events]
    quality_summaries = [
        call["qualitySummary"]
        for call in calls
        if isinstance(call.get("qualitySummary"), dict)
    ]
    if not quality_summaries:
        quality_summaries = _artifact_provider_quality_summaries(artifacts)
    for call in calls:
        if call.get("providerId"):
            provider_ids.add(str(call["providerId"]))
        if call.get("adapterId"):
            provider_adapters.append(str(call["adapterId"]))
        if call.get("responseId"):
            response_ids.append(str(call["responseId"]))
        if call.get("model"):
            models.append(str(call["model"]))
        if call.get("apiSurface"):
            api_surfaces.append(str(call["apiSurface"]))
        if isinstance(call.get("usage"), dict):
            usage_items.append(
                {
                    "source": "providerCallAudit",
                    "outputKind": call.get("outputKind"),
                    "responseId": call.get("responseId"),
                    "usage": call.get("usage"),
                    "totalTokens": call.get("totalTokens"),
                }
            )
    usage_total = sum(
        int(item["totalTokens"])
        for item in usage_items
        if isinstance(item.get("totalTokens"), int)
    )
    return {
        "realLlmCalled": any(bool(artifact.get("realLlmCalled", False)) for artifact in artifacts)
        or any(bool(event.get("realLlmCalled", False)) for event in provider_call_audit_events),
        "providerAdapters": sorted(set(provider_adapters)),
        "providerIds": sorted(provider_ids),
        "modes": modes,
        "models": _unique_preserve_order(models),
        "apiSurfaces": _unique_preserve_order(api_surfaces),
        "responseIds": _unique_preserve_order(response_ids),
        "responseIdCount": len(_unique_preserve_order(response_ids)),
        "providerCallAuditEventIds": [str(event["id"]) for event in provider_call_audit_events if event.get("id")],
        "promptIds": _unique_preserve_order(
            [str(event["promptId"]) for event in provider_call_audit_events if event.get("promptId")]
        ),
        "outputKinds": _unique_preserve_order(
            [str(event["outputKind"]) for event in provider_call_audit_events if event.get("outputKind")]
        ),
        "usage": {
            "available": bool(usage_items),
            "totalTokens": usage_total,
            "items": usage_items,
        },
        "qualitySummary": _provider_quality_summary(quality_summaries),
        "qualitySummaries": quality_summaries,
        "auditSummary": {
            "total": len(provider_call_audit_events),
            "success": sum(1 for event in provider_call_audit_events if event.get("status") == "SUCCESS"),
            "failed": sum(1 for event in provider_call_audit_events if event.get("status") == "FAILED"),
            "realLlmCalled": sum(1 for event in provider_call_audit_events if event.get("realLlmCalled")),
            "networkAccess": sum(1 for event in provider_call_audit_events if event.get("networkAccess")),
            "secretsRead": sum(1 for event in provider_call_audit_events if event.get("secretsRead")),
            "taskCreated": sum(1 for event in provider_call_audit_events if event.get("taskCreated")),
        },
        "calls": calls,
    }


def _exam_artifact(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    for artifact in artifacts:
        if artifact.get("kind") == "EXAM_DSL":
            return artifact
    return None


def _candidate_preview_summary(task: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    exam_artifact = _exam_artifact(artifacts)
    visible = task.get("taskType") == "EXAM_GENERATION" or exam_artifact is not None
    if not visible:
        return {"visible": False, "available": False}
    if exam_artifact is None:
        return {
            "visible": True,
            "available": False,
            "error": {"code": "EXAM_ARTIFACT_NOT_FOUND", "errors": []},
        }

    path = _resolve_local_path(exam_artifact.get("path"))
    if path is None:
        return {
            "visible": True,
            "available": False,
            "artifactId": exam_artifact.get("id"),
            "source": exam_artifact.get("path"),
            "error": {"code": "EXAM_ARTIFACT_PATH_INVALID", "errors": []},
        }

    try:
        preview = build_exam_candidate_preview_from_file(path, root=ROOT, trace_id=task.get("traceId"))
    except ExamCandidatePreviewError as exc:
        return {
            "visible": True,
            "available": False,
            "artifactId": exam_artifact.get("id"),
            "source": str(path),
            "error": {"code": exc.code, "message": exc.message, "errors": exc.errors},
        }

    redaction = preview.get("redaction", {}) if isinstance(preview.get("redaction"), dict) else {}
    return {
        "visible": True,
        "available": True,
        "kind": preview.get("kind"),
        "artifactId": exam_artifact.get("id"),
        "source": str(path),
        "sourceExamId": preview.get("sourceExamId"),
        "sourceExamTitle": preview.get("sourceExamTitle"),
        "sourceLabId": preview.get("sourceLabId"),
        "sourceStatus": preview.get("sourceStatus"),
        "questionType": preview.get("questionType"),
        "questionCount": len(preview.get("questions", [])) if isinstance(preview.get("questions"), list) else 0,
        "totalScore": preview.get("totalScore"),
        "answersRemoved": bool(preview.get("answersRemoved", False)),
        "answerVisibleToCandidate": bool(preview.get("answerVisibleToCandidate", True)),
        "answerFieldsRemoved": redaction.get("answerFieldsRemoved", 0),
        "removedFields": redaction.get("removedFields", []),
        "answerLeakDetected": bool(redaction.get("answerLeakDetected", False)),
        "reviewRequired": bool(preview.get("reviewRequired", True)),
        "publishBlockedUntilApproved": bool(preview.get("publishBlockedUntilApproved", True)),
        "error": None,
    }


def _operation_events_for_task(store: JsonTaskStore, task_id: str) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for event in store.list_operation_audit_events(
        resource_type=OperationResourceType.AI_TASK.value,
        resource_id=task_id,
    ):
        by_id[event.id] = event.to_dict()
    for event in store.list_operation_audit_events():
        payload = event.to_dict()
        if payload.get("detail", {}).get("createdTaskId") == task_id:
            by_id[event.id] = payload
        if payload.get("detail", {}).get("taskId") == task_id:
            by_id[event.id] = payload
    return sorted(by_id.values(), key=lambda item: item.get("occurredAt") or "", reverse=True)


def _revision_request_payload(event: dict[str, Any]) -> dict[str, Any]:
    detail = event.get("detail", {}) if isinstance(event.get("detail"), dict) else {}
    return {
        "id": event["id"],
        "taskId": event["resourceId"],
        "reviewer": event["actor"],
        "comment": detail.get("comment", ""),
        "priority": detail.get("priority", "NORMAL"),
        "targetSections": detail.get("targetSections", []),
        "requestedChanges": detail.get("requestedChanges", []),
        "statusUnchanged": bool(detail.get("statusUnchanged", True)),
        "taskStatusChanged": bool(detail.get("taskStatusChanged", False)),
        "realLlmCalled": bool(event.get("realLlmCalled", False)),
        "newLlmRequestSent": bool(detail.get("newLlmRequestSent", False)),
        "autoApproveAllowed": bool(detail.get("autoApproveAllowed", False)),
        "realPublishAllowed": bool(detail.get("realPublishAllowed", False)),
        "beforeState": event.get("beforeState"),
        "afterState": event.get("afterState"),
        "occurredAt": event.get("occurredAt"),
        "traceId": event.get("traceId"),
    }


def list_review_revision_requests(
    store: JsonTaskStore,
    *,
    task_id: str | None = None,
    actor: str | None = None,
) -> list[dict[str, Any]]:
    events = store.list_operation_audit_events(
        resource_type=OperationResourceType.AI_TASK.value,
        resource_id=task_id,
        action=OperationAction.REVIEW_REVISION_REQUEST.value,
        actor=actor,
    )
    return [_revision_request_payload(event.to_dict()) for event in events]


def build_review_revision_request_summary(
    operation_audit_events: list[dict[str, Any]],
) -> dict[str, Any]:
    items = [
        _revision_request_payload(event)
        for event in operation_audit_events
        if event.get("action") == OperationAction.REVIEW_REVISION_REQUEST.value
    ]
    high_priority_count = sum(1 for item in items if item["priority"] == "HIGH")
    latest = items[0] if items else None
    return {
        "items": items,
        "total": len(items),
        "highPriorityCount": high_priority_count,
        "latest": latest,
        "statusUnchanged": all(item["statusUnchanged"] for item in items),
        "realLlmCalled": any(item["realLlmCalled"] for item in items),
        "newLlmRequestSent": any(item["newLlmRequestSent"] for item in items),
    }


def create_review_revision_request(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    comment: str,
    priority: str = "NORMAL",
    target_sections: Any = None,
    requested_changes: Any = None,
    trace_id: str,
) -> dict[str, Any]:
    task = store.get(task_id)
    if task is None:
        raise ReviewRevisionRequestError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )
    if task.status != TaskStatus.WAITING_REVIEW:
        raise ReviewRevisionRequestError(
            "REVIEW_REVISION_REQUEST_INVALID_STATUS",
            "只有待审核任务可以提出修改意见",
            [{"field": "status", "reason": f"当前状态为 {task.status.value}"}],
        )

    reviewer = str(reviewer).strip()
    comment = str(comment).strip()
    priority = str(priority or "NORMAL").strip().upper()
    if not reviewer:
        raise ReviewRevisionRequestError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    if not comment:
        raise ReviewRevisionRequestError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "comment", "reason": "缺少参数"}],
        )
    if priority not in REVISION_REQUEST_PRIORITIES:
        raise ReviewRevisionRequestError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "priority", "reason": f"必须是 {sorted(REVISION_REQUEST_PRIORITIES)} 之一"}],
        )

    target_sections = _normalize_string_list(target_sections)
    requested_changes = _normalize_string_list(requested_changes)
    event = create_operation_audit_event(
        action=OperationAction.REVIEW_REVISION_REQUEST,
        resource_type=OperationResourceType.AI_TASK,
        resource_id=task.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=task.status.value,
        after_state=task.status.value,
        detail={
            "component": "ReviewRevisionRequest",
            "taskId": task.id,
            "taskType": task.taskType,
            "comment": comment,
            "priority": priority,
            "targetSections": target_sections,
            "requestedChanges": requested_changes,
            "statusUnchanged": True,
            "taskStatusChanged": False,
            "newLlmRequestSent": False,
            "realLlmCalled": False,
            "regenerationAllowed": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    )
    store.save_operation_audit_event(event)
    revision_request = _revision_request_payload(event.to_dict())
    return {
        "revisionRequest": revision_request,
        "task": task.to_dict(),
        "operationAuditEvent": event.to_dict(),
        "safety": {
            "mode": "MOCK_ONLY",
            "taskStatusChanged": False,
            "statusUnchanged": True,
            "realLlmCalled": False,
            "newLlmRequestSent": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _resolve_revision_request(
    store: JsonTaskStore,
    *,
    task_id: str,
    revision_request_id: str | None = None,
) -> dict[str, Any]:
    requests = list_review_revision_requests(store, task_id=task_id)
    if revision_request_id:
        request = next((item for item in requests if item["id"] == revision_request_id), None)
        if request is None:
            raise ReviewMockRegenerationError(
                "REVISION_REQUEST_NOT_FOUND",
                "修改意见不存在",
                [{"field": "revisionRequestId", "reason": "未找到指定修改意见"}],
            )
        return request
    if not requests:
        raise ReviewMockRegenerationError(
            "REVISION_REQUEST_NOT_FOUND",
            "任务尚无修改意见",
            [{"field": "taskId", "reason": "请先提交 review revision-request"}],
        )
    return requests[0]


def _load_primary_dsl_for_task(store: JsonTaskStore, task_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts = [artifact.to_dict() for artifact in store.list_artifacts(task_id=task_id)]
    task = store.get(task_id)
    final_result_path = str(task.finalResultPath or "") if task else ""
    primary = None
    if final_result_path:
        primary = next(
            (
                artifact
                for artifact in artifacts
                if artifact.get("kind") in DSL_ARTIFACT_KINDS and str(artifact.get("path") or "") == final_result_path
            ),
            None,
        )
    primary = primary or _primary_artifact(artifacts)
    if primary is None or primary.get("kind") not in DSL_ARTIFACT_KINDS:
        raise ReviewMockRegenerationError(
            "SOURCE_DSL_NOT_FOUND",
            "未找到可修订的 DSL 产物",
            [{"field": "taskId", "reason": "任务需要关联 Lab/Exam/Grading/PPT DSL Artifact"}],
        )
    source_path = _resolve_local_path(primary.get("path"))
    if source_path is None:
        raise ReviewMockRegenerationError(
            "SOURCE_DSL_PATH_INVALID",
            "源 DSL 路径无效",
            [{"field": "artifact.path", "reason": str(primary.get("path"))}],
        )
    try:
        dsl = load_yaml(source_path)
    except OSError as exc:
        raise ReviewMockRegenerationError(
            "SOURCE_DSL_READ_ERROR",
            "源 DSL 读取失败",
            [{"field": "artifact.path", "reason": str(exc)}],
        ) from exc
    if not isinstance(dsl, dict):
        raise ReviewMockRegenerationError(
            "SOURCE_DSL_INVALID",
            "源 DSL 格式错误",
            [{"field": "$", "reason": "root must be object"}],
        )
    return dsl, primary


def _apply_mock_revision_metadata(
    source_dsl: dict[str, Any],
    *,
    source_task_id: str,
    revision_request: dict[str, Any],
) -> dict[str, Any]:
    revised = json.loads(json.dumps(source_dsl, ensure_ascii=False))
    metadata = revised.setdefault("metadata", {})
    original_id = str(metadata.get("id") or source_task_id)
    metadata["id"] = f"{original_id}_rev_{uuid4().hex[:8]}"
    metadata["title"] = f"{metadata.get('title', 'AI 生成内容')}（修订草稿）"
    revised["status"] = TaskStatus.WAITING_REVIEW.value
    return revised


def _mock_revision_content_quality_summary(
    *,
    artifact_kind: str,
    revision_request: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    dsl_kind = DSL_SCHEMA_KIND_BY_ARTIFACT_KIND[artifact_kind]
    import_preview_kinds = {"lab", "exam", "grading"}
    ready_for_import_preview = dsl_kind in import_preview_kinds
    item = {
        "component": "RealDslContentQualityItem",
        "kind": dsl_kind,
        "source": "review_mock_regeneration",
        "status": "READY_FOR_MANUAL_REVIEW",
        "decisionStatus": "READY_FOR_MANUAL_REVIEW",
        "recommendedAction": "approve_task_then_create_import_preview",
        "readyForManualReview": True,
        "readyForImportPreview": ready_for_import_preview,
        "requiresRevisionBeforeImportPreview": False,
        "requiresEvidenceBeforeFinalApproval": False,
        "issueTotal": 0,
        "blockingIssueTotal": 0,
        "warningIssueTotal": 0,
        "revisionRequestId": revision_request["id"],
        "revisionApplied": True,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }
    workflow_summary = {
        "available": True,
        "component": "RealDslContentQualitySummary",
        "source": "review_mock_regeneration",
        "status": "READY_FOR_MANUAL_REVIEW",
        "decisionStatus": "READY_FOR_MANUAL_REVIEW",
        "recommendedAction": "approve_task_then_create_import_preview",
        "requiresRevisionBeforeImportPreview": False,
        "requiresEvidenceBeforeFinalApproval": False,
        "itemTotal": 1,
        "issueTotal": 0,
        "blockingIssueTotal": 0,
        "warningIssueTotal": 0,
        "readyForReviewTotal": 1,
        "readyForImportPreviewKinds": [dsl_kind] if ready_for_import_preview else [],
        "blockedForImportPreviewKinds": [],
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "items": {dsl_kind: item},
    }
    return item, workflow_summary


def _write_revised_dsl(
    revised_dsl: dict[str, Any],
    *,
    output_path: Path | None,
    source_task_id: str,
    artifact_kind: str,
) -> Path:
    if output_path is None:
        suffix = DSL_SCHEMA_KIND_BY_ARTIFACT_KIND[artifact_kind]
        output_path = ROOT / "examples" / "output" / f"{source_task_id}-{suffix}-revision-{uuid4().hex[:8]}.json"
    output_path = output_path if output_path.is_absolute() else ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(revised_dsl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def create_review_mock_regeneration(
    store: JsonTaskStore,
    *,
    task_id: str,
    reviewer: str,
    revision_request_id: str | None = None,
    output_path: Path | None = None,
    trace_id: str,
) -> dict[str, Any]:
    source_task = store.get(task_id)
    if source_task is None:
        raise ReviewMockRegenerationError(
            "NOT_FOUND",
            "AI Task 不存在",
            [{"field": "taskId", "reason": "未找到任务"}],
        )
    if source_task.status != TaskStatus.WAITING_REVIEW:
        raise ReviewMockRegenerationError(
            "REVIEW_REGENERATION_INVALID_STATUS",
            "只有待审核任务可以基于修改意见生成修订草稿",
            [{"field": "status", "reason": f"当前状态为 {source_task.status.value}"}],
        )
    reviewer = str(reviewer).strip()
    if not reviewer:
        raise ReviewMockRegenerationError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )

    revision_request = _resolve_revision_request(
        store,
        task_id=task_id,
        revision_request_id=revision_request_id,
    )
    source_dsl, source_artifact = _load_primary_dsl_for_task(store, task_id)
    artifact_kind = source_artifact["kind"]
    revised_dsl = _apply_mock_revision_metadata(
        source_dsl,
        source_task_id=task_id,
        revision_request=revision_request,
    )
    try:
        validate_dsl(revised_dsl, load_schema(DSL_SCHEMA_KIND_BY_ARTIFACT_KIND[artifact_kind], ROOT))
    except DslValidationError as exc:
        raise ReviewMockRegenerationError(
            "SCHEMA_VALIDATION_ERROR",
            "修订版 DSL Schema 校验失败",
            exc.errors,
        ) from exc

    written_path = _write_revised_dsl(
        revised_dsl,
        output_path=output_path,
        source_task_id=task_id,
        artifact_kind=artifact_kind,
    )
    new_task = create_waiting_review_task(
        task_type=TASK_TYPE_BY_DSL_ARTIFACT_KIND[artifact_kind],
        title=f"Mock revision for {source_task.title}",
        input_type="review_revision_request",
        input_ref=revision_request["id"],
        final_result_path=str(written_path),
        trace_id=trace_id,
    )
    store.save(new_task)
    workflow_steps = [
        create_workflow_step(
            "load_revision_request",
            1,
            {
                "sourceTaskId": task_id,
                "revisionRequestId": revision_request["id"],
                "reviewer": revision_request["reviewer"],
            },
        ),
        create_workflow_step(
            "load_source_dsl",
            2,
            {
                "sourceTaskId": task_id,
                "sourceArtifactId": source_artifact["id"],
                "sourceArtifactKind": artifact_kind,
                "sourcePath": source_artifact["path"],
            },
        ),
        create_workflow_step(
            "write_mock_revised_dsl",
            3,
            {
                "taskId": new_task.id,
                "sourceTaskId": task_id,
                "outputPath": str(written_path),
                "schemaValidated": True,
                "realLlmCalled": False,
            },
        ),
    ]
    workflow_run = create_workflow_run(
        workflow_id="review_mock_regeneration",
        input_ref=revision_request["id"],
        reviewer=reviewer,
        trace_id=trace_id,
        report_path=None,
        steps=workflow_steps,
    )
    store.save_workflow_run(workflow_run)
    content_quality_item, workflow_content_quality_summary = _mock_revision_content_quality_summary(
        artifact_kind=artifact_kind,
        revision_request=revision_request,
    )
    artifact = create_artifact_record(
        kind=ArtifactKind(artifact_kind),
        path=str(written_path),
        title=f"Mock Revised {DSL_KIND_BY_ARTIFACT_KIND[artifact_kind]} DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=trace_id,
        task_id=new_task.id,
        workflow_run_id=workflow_run.id,
        source_ref=source_artifact["path"],
        metadata={
            "dslKind": DSL_KIND_BY_ARTIFACT_KIND[artifact_kind],
            "reviewRequired": True,
            "sourceTaskId": task_id,
            "sourceArtifactId": source_artifact["id"],
            "sourceRevisionRequestId": revision_request["id"],
            "revisionComment": revision_request["comment"],
            "mockRegenerated": True,
            "realLlmCalled": False,
            "autoPublishAllowed": False,
            "contentQualitySummary": content_quality_item,
            "workflowContentQualitySummary": workflow_content_quality_summary,
        },
    )
    store.save_artifact(artifact)
    operation_event = create_operation_audit_event(
        action=OperationAction.REVIEW_MOCK_REGENERATE,
        resource_type=OperationResourceType.AI_TASK,
        resource_id=new_task.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=TaskStatus.WAITING_REVIEW.value,
        after_state=TaskStatus.WAITING_REVIEW.value,
        detail={
            "component": "ReviewMockRegeneration",
            "sourceTaskId": task_id,
            "newTaskId": new_task.id,
            "sourceArtifactId": source_artifact["id"],
            "sourceArtifactKind": artifact_kind,
            "sourceRevisionRequestId": revision_request["id"],
            "workflowRunId": workflow_run.id,
            "artifactId": artifact.id,
            "outputPath": str(written_path),
            "schemaValidated": True,
            "reviewRequired": True,
            "sourceTaskStatusUnchanged": True,
            "newTaskStatus": TaskStatus.WAITING_REVIEW.value,
            "contentQualityDecisionStatus": workflow_content_quality_summary["decisionStatus"],
            "contentQualityReadyForImportPreview": True,
            "contentQualityRequiresRevisionBeforeImportPreview": False,
            "realLlmCalled": False,
            "newLlmRequestSent": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    )
    store.save_operation_audit_event(operation_event)
    return {
        "sourceTask": source_task.to_dict(),
        "newTask": new_task.to_dict(),
        "revisionRequest": revision_request,
        "artifact": artifact.to_dict(),
        "workflowRun": workflow_run.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
        "dsl": revised_dsl,
        "dslPath": str(written_path),
        "safety": {
            "mode": "MOCK_ONLY",
            "sourceTaskStatusUnchanged": True,
            "newTaskStatus": TaskStatus.WAITING_REVIEW.value,
            "realLlmCalled": False,
            "newLlmRequestSent": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    }


def enqueue_promoted_revision_for_review(
    store: JsonTaskStore,
    *,
    promotion_report_path: Path,
    reviewer: str,
    trace_id: str,
) -> dict[str, Any]:
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise PromotionReviewEnqueueError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reviewer", "reason": "缺少参数"}],
        )
    if not promotion_report_path.exists() or not promotion_report_path.is_file():
        raise PromotionReviewEnqueueError(
            "VALIDATION_ERROR",
            "修订候选提升报告不存在",
            [{"field": "promotionReport", "reason": "文件不存在"}],
        )
    try:
        promotion = json.loads(promotion_report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PromotionReviewEnqueueError(
            "VALIDATION_ERROR",
            "修订候选提升报告 JSON 解析失败",
            [{"field": "promotionReport", "reason": str(exc)}],
        ) from exc
    if not isinstance(promotion, dict) or promotion.get("component") != "RealDslRevisionPromotion":
        raise PromotionReviewEnqueueError(
            "VALIDATION_ERROR",
            "修订候选提升报告格式错误",
            [{"field": "promotionReport.component", "reason": "expected RealDslRevisionPromotion"}],
        )
    if promotion.get("promotedStatus") != TaskStatus.WAITING_REVIEW.value:
        raise PromotionReviewEnqueueError(
            "VALIDATION_ERROR",
            "修订候选版状态不可入队",
            [{"field": "promotedStatus", "reason": "expected WAITING_REVIEW"}],
        )

    dsl_kind = str(promotion.get("kind") or "").strip().lower()
    artifact_kind_by_dsl_kind = {
        "lab": ArtifactKind.LAB_DSL,
        "exam": ArtifactKind.EXAM_DSL,
        "grading": ArtifactKind.GRADING_DSL,
        "ppt": ArtifactKind.PPT_DSL,
    }
    artifact_kind = artifact_kind_by_dsl_kind.get(dsl_kind)
    if artifact_kind is None:
        raise PromotionReviewEnqueueError(
            "VALIDATION_ERROR",
            "修订候选版 kind 不支持入队",
            [{"field": "kind", "reason": "expected one of lab/exam/grading/ppt"}],
        )

    promoted_path = _resolve_local_path(promotion.get("promotedPath"))
    if promoted_path is None or not promoted_path.exists() or not promoted_path.is_file():
        raise PromotionReviewEnqueueError(
            "VALIDATION_ERROR",
            "修订候选版 DSL 文件不存在",
            [{"field": "promotedPath", "reason": "文件不存在"}],
        )
    try:
        promoted_dsl = load_yaml(promoted_path)
        validate_dsl(promoted_dsl, load_schema(DSL_SCHEMA_KIND_BY_ARTIFACT_KIND[artifact_kind.value], ROOT))
    except DslValidationError as exc:
        raise PromotionReviewEnqueueError(
            "SCHEMA_VALIDATION_ERROR",
            "修订候选版 DSL Schema 校验失败",
            exc.errors,
        ) from exc

    task = create_waiting_review_task(
        task_type=TASK_TYPE_BY_DSL_ARTIFACT_KIND[artifact_kind.value],
        title=f"Promoted real DSL revision candidate: {promotion.get('suggestionId')}",
        input_type="real_dsl_revision_promotion",
        input_ref=str(promotion_report_path),
        final_result_path=str(promoted_path),
        trace_id=trace_id,
    )
    store.save(task)
    workflow_steps = [
        create_workflow_step(
            "load_promotion_report",
            1,
            {
                "taskId": task.id,
                "promotionReportPath": str(promotion_report_path),
                "suggestionId": promotion.get("suggestionId"),
            },
        ),
        create_workflow_step(
            "validate_promoted_candidate_dsl",
            2,
            {
                "taskId": task.id,
                "promotedPath": str(promoted_path),
                "schemaValidated": True,
                "status": TaskStatus.WAITING_REVIEW.value,
            },
        ),
        create_workflow_step(
            "enqueue_promoted_candidate_for_review",
            3,
            {
                "taskId": task.id,
                "reviewer": reviewer,
                "realLlmCalled": False,
                "autoPublishAllowed": False,
                "realPublishAllowed": False,
            },
        ),
    ]
    workflow_run = create_workflow_run(
        workflow_id="real_dsl_revision_promotion_review_enqueue",
        input_ref=str(promotion_report_path),
        reviewer=reviewer,
        trace_id=trace_id,
        report_path=str(promotion_report_path),
        steps=workflow_steps,
    )
    store.save_workflow_run(workflow_run)
    metadata = {
        "component": "RealDslRevisionPromotionReviewQueueItem",
        "dslKind": DSL_KIND_BY_ARTIFACT_KIND[artifact_kind.value],
        "reviewRequired": True,
        "promotionReportPath": str(promotion_report_path),
        "sourceDecisionReportPath": promotion.get("sourceDecisionReportPath"),
        "suggestionId": promotion.get("suggestionId"),
        "sourceDslId": promotion.get("sourceDslId"),
        "revisedDslId": promotion.get("revisedDslId"),
        "promotedDslId": promotion.get("promotedDslId"),
        "decisionStatus": promotion.get("decisionStatus"),
        "schemaValidated": True,
        "promotedCandidateQueued": True,
        "realLlmCalled": False,
        "newLlmRequestSent": False,
        "sourceDslModified": False,
        "revisedDslModified": False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }
    artifact = create_artifact_record(
        kind=artifact_kind,
        path=str(promoted_path),
        title=f"Promoted {DSL_KIND_BY_ARTIFACT_KIND[artifact_kind.value]} DSL Candidate",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=trace_id,
        task_id=task.id,
        workflow_run_id=workflow_run.id,
        source_ref=str(promotion_report_path),
        metadata=metadata,
        mode="LOCAL_REAL_DSL_REVISION_PROMOTION",
    )
    store.save_artifact(artifact)
    operation_event = create_operation_audit_event(
        action=OperationAction.REAL_DSL_REVISION_PROMOTION_ENQUEUE,
        resource_type=OperationResourceType.AI_TASK,
        resource_id=task.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=None,
        after_state=TaskStatus.WAITING_REVIEW.value,
        detail={
            "component": "RealDslRevisionPromotionReviewEnqueue",
            "taskId": task.id,
            "artifactId": artifact.id,
            "workflowRunId": workflow_run.id,
            "promotionReportPath": str(promotion_report_path),
            "promotedPath": str(promoted_path),
            "suggestionId": promotion.get("suggestionId"),
            "schemaValidated": True,
            "reviewRequired": True,
            "newTaskStatus": TaskStatus.WAITING_REVIEW.value,
            "realLlmCalled": False,
            "newLlmRequestSent": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    )
    store.save_operation_audit_event(operation_event)
    return {
        "promotionReviewQueueItem": {
            "component": "RealDslRevisionPromotionReviewQueueItem",
            "mode": "LOCAL_REAL_DSL_REVISION_PROMOTION_REVIEW_QUEUE",
            "taskId": task.id,
            "taskType": task.taskType,
            "taskStatus": task.status.value,
            "artifactId": artifact.id,
            "artifactKind": artifact.kind.value,
            "artifactStatus": artifact.status.value,
            "workflowRunId": workflow_run.id,
            "promotionReportPath": str(promotion_report_path),
            "promotedPath": str(promoted_path),
            "suggestionId": promotion.get("suggestionId"),
            "schemaValidated": True,
            "manualReviewRequired": True,
            "publishBlockedUntilApproved": True,
            "nextRequiredAction": "open_review_detail_and_approve_or_reject",
            "safety": {
                "realLlmCalled": False,
                "newLlmRequestSent": False,
                "secretsRead": False,
                "networkAccess": False,
                "sourceDslModified": False,
                "revisedDslModified": False,
                "autoApproveAllowed": False,
                "autoPublishAllowed": False,
                "realPublishAllowed": False,
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
            },
        },
        "task": task.to_dict(),
        "artifact": artifact.to_dict(),
        "workflowRun": workflow_run.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
        "reviewDetail": build_review_detail(store, task.id),
    }


def _high_risk_intent_summary(
    task: dict[str, Any],
    operation_audit_events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    config = HIGH_RISK_MCP_INTENT_TASKS.get(task.get("taskType"))
    if config is None:
        return None

    linked_event = next(
        (
            event
            for event in operation_audit_events
            if event.get("detail", {}).get("createdTaskId") == task["id"]
        ),
        None,
    )
    detail = linked_event.get("detail", {}) if linked_event else {}
    requires_second_confirmation = bool(
        detail.get("requiresSecondConfirmation", config["requiresSecondConfirmation"])
    )
    return {
        "intentType": detail.get("intentType", config["intentType"]),
        "toolName": config["toolName"],
        "resourceType": config["resourceType"],
        "resourceId": task.get("inputRef"),
        "riskLevel": detail.get("riskLevel", config["riskLevel"]),
        "status": task["status"],
        "reviewRequired": task["status"] == TaskStatus.WAITING_REVIEW.value,
        "reviewIntentOnly": True,
        "requiresSecondConfirmation": requires_second_confirmation,
        "postReviewDisposition": _high_risk_post_review_disposition(
            task["status"],
            requires_second_confirmation=requires_second_confirmation,
        ),
        "operationAuditEventId": linked_event.get("id") if linked_event else None,
        "requestId": detail.get("requestId") or task.get("intermediateResultPath"),
        "reason": detail.get("reason"),
        "blockedUntilApproved": detail.get("blockedUntilApproved", True),
        "blockedActions": detail.get(
            "blockedActions",
            ["realPublish", "autoPublish", "destroyRealCloudResource", "bypassHumanReview"],
        ),
        "realActionExecuted": False,
        "realPublish": False,
        "realCloudResourceChanged": False,
        "environmentDestroyed": False,
        "autoPublishAllowed": False,
    }


def _timeline(
    task: dict[str, Any],
    workflow_steps: list[dict[str, Any]],
    review_audit_events: list[dict[str, Any]],
    operation_audit_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items = [
        {
            "type": "TASK_CREATED",
            "title": "AI Task created",
            "status": task["status"],
            "occurredAt": task["createdAt"],
            "refId": task["id"],
        }
    ]
    for step in workflow_steps:
        items.append(
            {
                "type": "WORKFLOW_STEP",
                "title": step["name"],
                "status": step["status"],
                "occurredAt": step.get("finishedAt") or step.get("startedAt"),
                "refId": step.get("workflowRunId"),
                "order": step["order"],
            }
        )
    for event in review_audit_events:
        items.append(
            {
                "type": "REVIEW_AUDIT",
                "title": event["action"],
                "status": event["toStatus"],
                "occurredAt": event["occurredAt"],
                "refId": event["id"],
                "actor": event["actor"],
            }
        )
    for event in operation_audit_events:
        items.append(
            {
                "type": "OPERATION_AUDIT",
                "title": event["action"],
                "status": event.get("afterState"),
                "occurredAt": event["occurredAt"],
                "refId": event["id"],
                "actor": event["actor"],
            }
        )
    return sorted(items, key=lambda item: (item.get("occurredAt") or "", item.get("order", 0)))


def build_review_page_model(
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
    workflow_steps: list[dict[str, Any]],
    review_audit_events: list[dict[str, Any]],
    operation_audit_events: list[dict[str, Any]],
    review_policy: dict[str, Any],
    high_risk_intent: dict[str, Any] | None = None,
    assessment_plan: dict[str, Any] | None = None,
    provider_call_audit_events: list[dict[str, Any]] | None = None,
    candidate_preview: dict[str, Any] | None = None,
    promotion_review_disposition: dict[str, Any] | None = None,
    platform_import_preview: dict[str, Any] | None = None,
    platform_import_preview_actions: dict[str, Any] | None = None,
    platform_import_preview_signoff: dict[str, Any] | None = None,
    agent_entity_mock_import: dict[str, Any] | None = None,
    agent_entity_import_activity: dict[str, Any] | None = None,
    agent_entity_readiness_report: dict[str, Any] | None = None,
    grading_jobs: dict[str, Any] | None = None,
    grading_records: dict[str, Any] | None = None,
    controlled_grading_evidence: dict[str, Any] | None = None,
    merged_grading_evidence: dict[str, Any] | None = None,
    review_decision_notes: dict[str, Any] | None = None,
    pre_approve_review_check: dict[str, Any] | None = None,
    content_quality_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    primary_artifact = _primary_artifact(artifacts)
    allowed_actions = set(review_policy["allowedActions"])
    high_risk_disposition = (
        high_risk_intent.get("postReviewDisposition") if high_risk_intent else None
    )
    assessment_plan = assessment_plan or build_assessment_plan_review_model(task, artifacts, workflow_steps)
    candidate_preview = candidate_preview or _candidate_preview_summary(task, artifacts)
    ppt_page_review = build_ppt_page_review_model(task, artifacts)
    revision_requests = build_review_revision_request_summary(operation_audit_events)
    promotion_review_disposition = promotion_review_disposition or build_promotion_review_disposition(
        task,
        artifacts,
        review_policy,
    )
    platform_import_preview = platform_import_preview or build_platform_import_preview_summary(
        task,
        artifacts,
        operation_audit_events,
    )
    platform_import_preview_actions = platform_import_preview_actions or build_platform_import_preview_action_panel(
        task,
        artifacts,
        review_policy,
        platform_import_preview,
    )
    platform_import_preview_signoff = (
        platform_import_preview_signoff
        or build_platform_import_preview_signoff_checklist(
            task,
            platform_import_preview,
            platform_import_preview_actions,
        )
    )
    agent_entity_import_activity = agent_entity_import_activity or {
        "visible": False,
        "items": [],
        "summary": {},
    }
    agent_entity_readiness_report = agent_entity_readiness_report or {
        "component": "AgentEntityReadinessReport",
        "mode": "LOCAL_AGENT_ENTITY_READINESS_REPORT",
        "sourceTaskId": task.get("id"),
        "items": [],
        "summary": {
            "requiredTotal": 0,
            "agentEntitySignoffReadyTotal": 0,
            "agentEntitySignoffRecordedTotal": 0,
        },
        "safety": {
            "readOnly": True,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }
    grading_records = grading_records or {
        "component": "GradingRecordSummary",
        "visible": False,
        "total": 0,
        "items": [],
        "latest": None,
        "summary": {
            "recordReadyForHumanReviewTotal": 0,
            "humanApprovedTotal": 0,
            "needsEvidenceTotal": 0,
            "needsRevisionTotal": 0,
            "humanReviewRecordedTotal": 0,
            "readyForAgentReview": False,
            "platformReviewState": "NO_GRADING_RECORD",
            "platformReviewNextRequiredAction": "create_grading_record_from_latest_evidence_report",
            "latestStatus": None,
            "latestReviewDecision": None,
            "latestReviewReason": None,
            "latestReviewedBy": None,
            "latestReviewedAt": None,
            "latestEarnedScore": None,
            "latestTotalScore": None,
            "latestCoverageRatio": None,
        },
        "reviewIntegration": {
            "component": "GradingRecordReviewIntegration",
            "source": "JsonTaskStore.gradingRecords",
            "taskId": task.get("id"),
            "state": "NO_GRADING_RECORD",
            "readyForAgentReview": False,
            "manualRecordReviewRequired": False,
            "nextRequiredAction": "create_grading_record_from_latest_evidence_report",
            "latestRecordId": None,
            "latestStatus": None,
            "latestDecision": None,
            "humanReviewRecordedTotal": 0,
            "blockingReasons": ["grading_record_missing"],
            "recordReviewChangesTaskStatus": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
        "safety": {
            "readOnly": True,
            "recordCreatesNewExecution": False,
            "sandboxExecutedByRecord": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    }
    grading_jobs = grading_jobs or {
        "component": "GradingJobSummary",
        "visible": False,
        "total": 0,
        "items": [],
        "latest": None,
        "summary": {
            "queuedTotal": 0,
            "runningTotal": 0,
            "waitingReviewTotal": 0,
            "failedTotal": 0,
        },
        "safety": {
            "readOnly": True,
            "databaseWritten": False,
            "workerStarted": False,
            "queuePersistedToProduction": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }
    controlled_grading_evidence = controlled_grading_evidence or build_controlled_grading_evidence_review_model(
        task,
        artifacts,
        operation_audit_events,
    )
    merged_grading_evidence = merged_grading_evidence or build_merged_grading_evidence_review_model(
        task,
        artifacts,
        operation_audit_events,
    )
    review_decision_notes = review_decision_notes or build_review_decision_note_summary(
        artifacts,
        operation_audit_events,
    )
    pre_approve_review_check = pre_approve_review_check or build_pre_approve_review_check_from_models(
        task,
        merged_grading_evidence,
        review_decision_notes,
    )
    dsl_preview = None
    if primary_artifact and primary_artifact["kind"] in DSL_ARTIFACT_KINDS:
        schema_kind = DSL_SCHEMA_KIND_BY_ARTIFACT_KIND.get(primary_artifact["kind"])
        content_preview = _dsl_content_preview(
            primary_artifact["kind"],
            primary_artifact["path"],
            schema_kind=schema_kind,
        )
        dsl_preview = {
            "kind": primary_artifact.get("metadata", {}).get("dslKind"),
            "artifactKind": primary_artifact["kind"],
            "artifactId": primary_artifact["id"],
            "path": primary_artifact["path"],
            "status": primary_artifact["status"],
            "schemaKind": schema_kind,
            **content_preview,
        }
        if not dsl_preview.get("kind") and content_preview.get("documentKind"):
            dsl_preview["kind"] = content_preview["documentKind"]
        if primary_artifact["kind"] == "GRADING_DSL":
            assessment_summary = assessment_plan["summary"]
            dsl_preview.update(
                {
                    "assessmentPlanTotal": assessment_summary["planTotal"],
                    "assessmentPlanSource": assessment_summary["source"],
                    "assessmentPlanAlignedWithChecks": assessment_summary["alignedWithChecks"],
                }
            )

    return {
        "header": {
            "taskId": task["id"],
            "taskType": task["taskType"],
            "title": task["title"],
            "status": task["status"],
            "promptVersion": task["promptVersion"],
            "traceId": task["traceId"],
        },
        "source": {
            "inputType": task["inputType"],
            "inputRef": task["inputRef"],
            "finalResultPath": task.get("finalResultPath"),
        },
        "dslPreview": dsl_preview,
        "generationProfile": _generation_profile(artifacts, workflow_steps),
        "qualitySignals": _quality_signal_summary(artifacts, workflow_steps),
        "contentQualitySummary": content_quality_summary or _content_quality_summary(artifacts),
        "assessmentPlan": assessment_plan,
        "assessmentPlanManualReviewChecklist": assessment_plan.get("manualReviewChecklist", {}),
        "pptPageReview": ppt_page_review,
        "revisionRequests": revision_requests,
        "promotionReviewDisposition": promotion_review_disposition,
        "platformImportPreview": platform_import_preview,
        "platformImportPreviewActions": platform_import_preview_actions,
        "platformImportPreviewSignoff": platform_import_preview_signoff,
        "agentEntityMockImport": agent_entity_mock_import,
        "agentEntityImportActivity": agent_entity_import_activity,
        "agentEntityReadinessReport": agent_entity_readiness_report,
        "gradingJobs": grading_jobs,
        "gradingRecords": grading_records,
        "controlledGradingEvidence": controlled_grading_evidence,
        "mergedGradingEvidence": merged_grading_evidence,
        "reviewDecisionNotes": review_decision_notes,
        "preApproveReviewCheck": pre_approve_review_check,
        "candidatePreview": candidate_preview,
        "providerSummary": _provider_summary(artifacts, workflow_steps, provider_call_audit_events),
        "artifactGroups": _artifact_groups(artifacts),
        "riskSummary": _risk_summary(artifacts),
        "timeline": _timeline(task, workflow_steps, review_audit_events, operation_audit_events),
        "actionBar": {
            "approve": {"enabled": "approve" in allowed_actions, "requiresReviewer": True},
            "reject": {
                "enabled": "reject" in allowed_actions,
                "requiresReviewer": True,
                "requiresReason": review_policy["rejectRequiresReason"],
            },
            "requestRevision": {
                "enabled": "request_revision" in allowed_actions,
                "requiresReviewer": True,
                "requiresComment": True,
                "changesTaskStatus": False,
                "triggersLlm": False,
            },
            "mockPublish": {
                "enabled": "mock_publish" in allowed_actions,
                "blockedUntilApproved": review_policy["publishBlockedUntilApproved"],
                "realPublish": False,
            },
        },
        "highRiskIntentPanel": {
            "visible": high_risk_intent is not None,
            "intent": high_risk_intent,
            "postReviewDisposition": high_risk_disposition,
            "postReviewState": high_risk_disposition.get("state") if high_risk_disposition else None,
            "reviewIntentOnly": high_risk_intent is not None,
            "executionBlocked": bool(high_risk_disposition.get("executionBlocked")) if high_risk_disposition else False,
            "secondConfirmationRequired": (
                bool(high_risk_disposition.get("secondConfirmationRequired")) if high_risk_disposition else False
            ),
            "secondConfirmationSatisfied": (
                bool(high_risk_disposition.get("secondConfirmationSatisfied")) if high_risk_disposition else False
            ),
            "executeRealActionEnabled": False,
            "executeRealPublishEnabled": False,
            "destroyRealEnvironmentEnabled": False,
            "bypassReviewEnabled": False,
        },
        "emptyStates": {
            "noArtifacts": len(artifacts) == 0,
            "noWorkflowSteps": len(workflow_steps) == 0,
            "noAuditEvents": len(review_audit_events) + len(operation_audit_events) == 0,
        },
    }


def build_pre_approve_review_check_from_models(
    task: dict[str, Any],
    merged_grading_evidence: dict[str, Any],
    review_decision_notes: dict[str, Any],
) -> dict[str, Any]:
    task_type = str(task.get("taskType") or "")
    task_id = str(task.get("id") or "")
    merged_summary = (
        merged_grading_evidence.get("summary")
        if isinstance(merged_grading_evidence.get("summary"), dict)
        else {}
    )
    evidence_ready = bool(
        merged_grading_evidence.get("visible") is True
        and int(merged_summary.get("checkEvidenceReviewItemTotal", 0) or 0) > 0
    )
    decision_note_recommendation = merged_summary.get("decisionNoteRecommendation")
    manual_checklist_status = merged_summary.get("manualReviewChecklistStatus")
    score_preview_available = bool(merged_summary.get("scorePreviewAvailable"))
    score_preview_ready = merged_summary.get("scorePreviewReadyForDecisionNote")
    note_recorded = bool(int(review_decision_notes.get("total", 0) or 0) > 0)
    latest_note = (
        review_decision_notes.get("latest")
        if isinstance(review_decision_notes.get("latest"), dict)
        else {}
    )
    latest_decision = latest_note.get("decision")
    approve_ready_decision = latest_decision == "approve-ready"
    applicable = task_type in GRADING_REVIEW_TASK_TYPES
    recommended_warnings: list[str] = []
    if applicable and not evidence_ready:
        recommended_warnings.append("grading_evidence_missing_before_approve")
    if applicable and score_preview_available and score_preview_ready is not True:
        recommended_warnings.append("grading_score_preview_not_ready_for_decision_note")
    if applicable and not note_recorded:
        recommended_warnings.append("review_decision_note_missing_before_approve")
    if applicable and note_recorded and not approve_ready_decision:
        recommended_warnings.append("review_decision_note_not_approve_ready_before_approve")
    return {
        "component": "PreApproveReviewCheck",
        "source": "reviewDetail.mergedGradingEvidence + reviewDetail.reviewDecisionNotes",
        "taskId": task_id,
        "taskType": task_type,
        "applicable": applicable,
        "status": "READY_FOR_HUMAN_APPROVE" if not recommended_warnings else "APPROVE_ALLOWED_WITH_WARNINGS",
        "blocking": False,
        "approvalStillAllowed": True,
        "summary": {
            "evidenceReady": evidence_ready,
            "reviewDecisionNoteRecorded": note_recorded,
            "approveReadyDecision": approve_ready_decision,
            "warningTotal": len(recommended_warnings),
            "recommendedWarnings": recommended_warnings,
            "mergedEvidenceReportTotal": merged_grading_evidence.get("reportTotal", 0),
            "checkEvidenceReviewItemTotal": merged_summary.get("checkEvidenceReviewItemTotal", 0),
            "scorePreviewAvailable": score_preview_available,
            "scorePreviewStatus": merged_summary.get("scorePreviewStatus"),
            "scorePreviewEarnedScore": merged_summary.get("scorePreviewEarnedScore"),
            "scorePreviewTotalScore": merged_summary.get("scorePreviewTotalScore"),
            "scorePreviewCoveredScore": merged_summary.get("scorePreviewCoveredScore"),
            "scorePreviewMissingScore": merged_summary.get("scorePreviewMissingScore"),
            "scorePreviewCoverageRatio": merged_summary.get("scorePreviewCoverageRatio"),
            "scorePreviewPassRate": merged_summary.get("scorePreviewPassRate"),
            "scorePreviewReadyForDecisionNote": score_preview_ready,
            "scorePreviewMissingEvidenceTotal": merged_summary.get("scorePreviewMissingEvidenceTotal"),
            "scorePreviewMissingCheckIds": merged_summary.get("scorePreviewMissingCheckIds", []),
            "manualReviewChecklistStatus": manual_checklist_status,
            "manualReviewChecklistReadyTotal": merged_summary.get("manualReviewChecklistReadyTotal", 0),
            "manualReviewChecklistTotal": merged_summary.get("manualReviewChecklistTotal", 0),
            "decisionNoteRecommendation": decision_note_recommendation,
            "decisionNoteRecommendationReason": merged_summary.get("decisionNoteRecommendationReason"),
            "nextDecisionNoteAction": merged_summary.get("nextDecisionNoteAction"),
            "latestDecision": latest_decision,
        },
        "safety": {
            "readOnly": True,
            "statusChangeBlocked": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def _build_grading_record_review_integration(
    *,
    task_id: str,
    records: list[dict[str, Any]],
    latest: dict[str, Any] | None,
    source: str = "JsonTaskStore.gradingRecords",
) -> dict[str, Any]:
    human_review_recorded_total = sum(1 for record in records if record.get("reviewDecision"))
    if latest is None:
        return {
            "component": "GradingRecordReviewIntegration",
            "source": source,
            "taskId": task_id,
            "state": "NO_GRADING_RECORD",
            "readyForAgentReview": False,
            "manualRecordReviewRequired": False,
            "nextRequiredAction": "create_grading_record_from_latest_evidence_report",
            "latestRecordId": None,
            "latestStatus": None,
            "latestDecision": None,
            "latestReviewedBy": None,
            "latestReviewedAt": None,
            "humanReviewRecordedTotal": 0,
            "blockingReasons": ["grading_record_missing"],
            "recordReviewChangesTaskStatus": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        }

    latest_status = str(latest.get("status") or "")
    latest_decision = latest.get("reviewDecision")
    blocking_reasons: list[str] = []
    if latest_status == "HUMAN_APPROVED" and latest_decision == "approve-ready":
        state = "READY_FOR_PLATFORM_REVIEW"
        ready_for_platform_review = True
        manual_record_review_required = False
        next_required_action = "continue_platform_review_after_grading_record_approved"
    elif latest_status == "NEEDS_EVIDENCE" or latest_decision == "needs-evidence":
        state = "NEEDS_MORE_EVIDENCE"
        ready_for_platform_review = False
        manual_record_review_required = True
        next_required_action = "collect_more_evidence_for_grading_record_review"
        blocking_reasons.append("latest_grading_record_needs_more_evidence")
    elif latest_status == "NEEDS_REVISION" or latest_decision == "needs-revision":
        state = "NEEDS_REVISION"
        ready_for_platform_review = False
        manual_record_review_required = True
        next_required_action = "revise_grading_or_submission_before_platform_review"
        blocking_reasons.append("latest_grading_record_needs_revision")
    else:
        state = "WAITING_GRADING_RECORD_REVIEW"
        ready_for_platform_review = False
        manual_record_review_required = True
        next_required_action = "review_latest_grading_record_for_platform_review"
        blocking_reasons.append("latest_grading_record_waiting_human_review")

    latest_record_id = latest.get("id")
    return {
        "component": "GradingRecordReviewIntegration",
        "source": source,
        "taskId": task_id,
        "state": state,
        "readyForAgentReview": ready_for_platform_review,
        "manualRecordReviewRequired": manual_record_review_required,
        "nextRequiredAction": next_required_action,
        "latestRecordId": latest_record_id,
        "latestSubmissionId": latest.get("submissionId"),
        "latestCandidateId": latest.get("candidateId"),
        "latestReportPath": latest.get("reportPath"),
        "latestStatus": latest_status,
        "latestDecision": latest_decision,
        "latestReason": latest.get("reviewReason"),
        "latestReviewedBy": latest.get("reviewedBy"),
        "latestReviewedAt": latest.get("reviewedAt"),
        "latestEarnedScore": latest.get("earnedScore"),
        "latestTotalScore": latest.get("totalScore"),
        "latestCoverageRatio": latest.get("coverageRatio"),
        "humanReviewRecordedTotal": human_review_recorded_total,
        "blockingReasons": blocking_reasons,
        "reviewCommand": (
            f"python lab_cli.py grade record-review --id {latest_record_id} "
            "--reviewer <reviewer> --decision approve-ready"
        )
        if latest_record_id and not ready_for_platform_review
        else None,
        "recordReviewChangesTaskStatus": False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "realPublish": False,
    }


def build_grading_record_summary(
    store: JsonTaskStore,
    task_id: str,
    *,
    records_override: list[GradingRecord | dict[str, Any]] | None = None,
    source: str = "JsonTaskStore.gradingRecords",
) -> dict[str, Any]:
    records = (
        [
            record.to_dict() if isinstance(record, GradingRecord) else dict(record)
            for record in records_override
        ]
        if records_override is not None
        else [record.to_dict() for record in store.list_grading_records(task_id=task_id)]
    )
    latest = records[0] if records else None
    review_integration = _build_grading_record_review_integration(
        task_id=task_id,
        records=records,
        latest=latest,
        source=source,
    )
    return {
        "component": "GradingRecordSummary",
        "source": source,
        "taskId": task_id,
        "visible": bool(records),
        "total": len(records),
        "latest": latest,
        "items": records,
        "summary": {
            "recordReadyForHumanReviewTotal": sum(
                1 for record in records if record.get("status") == "READY_FOR_HUMAN_REVIEW"
            ),
            "humanApprovedTotal": sum(1 for record in records if record.get("status") == "HUMAN_APPROVED"),
            "needsEvidenceTotal": sum(1 for record in records if record.get("status") == "NEEDS_EVIDENCE"),
            "needsRevisionTotal": sum(1 for record in records if record.get("status") == "NEEDS_REVISION"),
            "humanReviewRecordedTotal": review_integration["humanReviewRecordedTotal"],
            "readyForAgentReview": review_integration["readyForAgentReview"],
            "platformReviewState": review_integration["state"],
            "platformReviewNextRequiredAction": review_integration["nextRequiredAction"],
            "latestStatus": latest.get("status") if latest else None,
            "latestReviewDecision": latest.get("reviewDecision") if latest else None,
            "latestReviewReason": latest.get("reviewReason") if latest else None,
            "latestReviewedBy": latest.get("reviewedBy") if latest else None,
            "latestReviewedAt": latest.get("reviewedAt") if latest else None,
            "latestEarnedScore": latest.get("earnedScore") if latest else None,
            "latestTotalScore": latest.get("totalScore") if latest else None,
            "latestCoverageRatio": latest.get("coverageRatio") if latest else None,
        },
        "reviewIntegration": review_integration,
        "safety": {
            "readOnly": True,
            "recordCreatesNewExecution": False,
            "sandboxExecutedByRecord": False,
            "contestantCodeExecutedByRecord": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def build_grading_job_summary(store: JsonTaskStore, task_id: str) -> dict[str, Any]:
    jobs = [job.to_dict() for job in store.list_grading_jobs(task_id=task_id)]
    latest = jobs[0] if jobs else None
    return {
        "component": "GradingJobSummary",
        "source": "JsonTaskStore.gradingJobs",
        "taskId": task_id,
        "visible": bool(jobs),
        "total": len(jobs),
        "latest": latest,
        "items": jobs,
        "summary": {
            "queuedTotal": sum(1 for job in jobs if job.get("status") == "QUEUED"),
            "runningTotal": sum(1 for job in jobs if job.get("status") == "RUNNING"),
            "waitingReviewTotal": sum(1 for job in jobs if job.get("status") == "WAITING_REVIEW"),
            "failedTotal": sum(1 for job in jobs if job.get("status") == "FAILED"),
            "latestStatus": latest.get("status") if latest else None,
            "latestReportPath": latest.get("reportPath") if latest else None,
            "latestGradingRecordId": latest.get("gradingRecordId") if latest else None,
            "latestEarnedScore": latest.get("summary", {}).get("earnedScore") if latest else None,
            "latestTotalScore": latest.get("summary", {}).get("totalScore") if latest else None,
            "latestCoverageRatio": latest.get("summary", {}).get("coverageRatio") if latest else None,
        },
        "safety": {
            "readOnly": True,
            "localStagingJob": True,
            "databaseWritten": False,
            "workerStarted": False,
            "queuePersistedToProduction": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def build_review_detail(
    store: JsonTaskStore,
    task_id: str,
    *,
    agent_report: str | None = None,
    grading_records_override: list[GradingRecord | dict[str, Any]] | None = None,
    grading_records_source: str = "JsonTaskStore.gradingRecords",
) -> dict[str, Any] | None:
    if agent_report:
        synthetic_detail = _synthetic_real_demo_review_detail_from_report(agent_report, task_id)
        if synthetic_detail is not None:
            return synthetic_detail

    task = store.get(task_id)
    if task is None:
        return _synthetic_real_demo_review_detail_from_report(agent_report, task_id)

    task_payload = task.to_dict()
    artifacts = [artifact.to_dict() for artifact in store.list_artifacts(task_id=task_id)]
    artifact_run_ids = {artifact["workflowRunId"] for artifact in artifacts if artifact.get("workflowRunId")}
    workflow_runs: list[dict[str, Any]] = []
    workflow_steps: list[dict[str, Any]] = []

    for run in store.list_workflow_runs():
        matching_steps = []
        for step in run.steps:
            if step.detail.get("taskId") == task_id:
                step_payload = step.to_dict()
                step_payload["workflowRunId"] = run.id
                step_payload["workflowId"] = run.workflowId
                matching_steps.append(step_payload)

        if matching_steps or run.id in artifact_run_ids:
            workflow_runs.append(run.to_dict())
            workflow_steps.extend(matching_steps)

    review_audit_events = [
        event.to_dict() for event in store.list_review_audit_events(task_id=task_id)
    ]
    operation_audit_events = _operation_events_for_task(store, task_id)
    agent_entities = [entity.to_dict() for entity in store.list_agent_entities(source_task_id=task_id)]
    review_policy = build_review_policy(task.status, task.taskType)
    revision_requests = build_review_revision_request_summary(operation_audit_events)
    high_risk_intent = _high_risk_intent_summary(task_payload, operation_audit_events)
    safety = build_review_safety(artifacts)
    assessment_plan = build_assessment_plan_review_model(task_payload, artifacts, workflow_steps)
    provider_call_audit_events = _provider_events_for_task(store, task_payload, artifacts, workflow_steps)
    candidate_preview = _candidate_preview_summary(task_payload, artifacts)
    ppt_page_review = build_ppt_page_review_model(task_payload, artifacts)
    promotion_review_disposition = build_promotion_review_disposition(task_payload, artifacts, review_policy)
    platform_import_preview = build_platform_import_preview_summary(task_payload, artifacts, operation_audit_events)
    content_quality_summary = _content_quality_summary(artifacts)
    platform_import_preview_actions = build_platform_import_preview_action_panel(
        task_payload,
        artifacts,
        review_policy,
        platform_import_preview,
        content_quality_summary,
    )
    agent_entity_mock_import = build_agent_entity_mock_import_summary(
        task_payload,
        agent_entities,
        operation_audit_events,
    )
    agent_entity_import_activity = build_agent_entity_publish_activity_summary_for_task(store, task_id)
    agent_entity_readiness_report = build_agent_entity_readiness_report(store, source_task_id=task_id)
    grading_jobs = build_grading_job_summary(store, task_id)
    grading_records = build_grading_record_summary(
        store,
        task_id,
        records_override=grading_records_override,
        source=grading_records_source,
    )
    controlled_grading_evidence = build_controlled_grading_evidence_review_model(
        task_payload,
        artifacts,
        operation_audit_events,
    )
    merged_grading_evidence = build_merged_grading_evidence_review_model(
        task_payload,
        artifacts,
        operation_audit_events,
    )
    review_decision_notes = build_review_decision_note_summary(artifacts, operation_audit_events)
    pre_approve_review_check = build_pre_approve_review_check_from_models(
        task_payload,
        merged_grading_evidence,
        review_decision_notes,
    )
    platform_import_preview_signoff = build_platform_import_preview_signoff_checklist(
        task_payload,
        platform_import_preview,
        platform_import_preview_actions,
        pre_approve_review_check=pre_approve_review_check,
        merged_grading_evidence=merged_grading_evidence,
    )
    if controlled_grading_evidence["visible"]:
        controlled_safety = controlled_grading_evidence["safety"]
        safety = {
            **safety,
            "sandboxExecuted": controlled_safety["sandboxExecuted"],
            "contestantCodeExecuted": controlled_safety["contestantCodeExecuted"],
            "commandExecuted": controlled_safety["commandExecuted"],
            "pytestExecuted": controlled_safety["pytestExecuted"],
            "networkEnabledForControlledGrading": controlled_safety["networkEnabled"],
            "realPublish": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }
    if merged_grading_evidence["visible"]:
        merged_safety = merged_grading_evidence["safety"]
        safety = {
            **safety,
            "sandboxExecuted": bool(safety.get("sandboxExecuted", False)) or merged_safety["sandboxExecuted"],
            "contestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False))
            or merged_safety["contestantCodeExecuted"],
            "commandExecuted": bool(safety.get("commandExecuted", False)) or merged_safety["commandExecuted"],
            "pytestExecuted": bool(safety.get("pytestExecuted", False)) or merged_safety["pytestExecuted"],
            "networkEnabledForMergedGrading": merged_safety["networkEnabled"],
            "mergeExecutedOnlyExistingReports": merged_safety["mergeExecutedOnlyExistingReports"],
            "realPublish": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }

    review_page = build_review_page_model(
        task_payload,
        artifacts,
        workflow_steps,
        review_audit_events,
        operation_audit_events,
        review_policy,
        high_risk_intent=high_risk_intent,
        assessment_plan=assessment_plan,
        provider_call_audit_events=provider_call_audit_events,
        candidate_preview=candidate_preview,
        promotion_review_disposition=promotion_review_disposition,
        platform_import_preview=platform_import_preview,
        platform_import_preview_actions=platform_import_preview_actions,
        platform_import_preview_signoff=platform_import_preview_signoff,
        agent_entity_mock_import=agent_entity_mock_import,
        agent_entity_import_activity=agent_entity_import_activity,
        agent_entity_readiness_report=agent_entity_readiness_report,
        grading_jobs=grading_jobs,
        grading_records=grading_records,
        controlled_grading_evidence=controlled_grading_evidence,
        merged_grading_evidence=merged_grading_evidence,
        review_decision_notes=review_decision_notes,
        pre_approve_review_check=pre_approve_review_check,
        content_quality_summary=content_quality_summary,
    )
    dsl_preview = review_page.get("dslPreview") or {}

    return {
        "mode": safety["mode"],
        "task": task_payload,
        "highRiskIntent": high_risk_intent,
        "assessmentPlan": assessment_plan,
        "candidatePreview": candidate_preview,
        "pptPageReview": ppt_page_review,
        "promotionReviewDisposition": promotion_review_disposition,
        "platformImportPreview": platform_import_preview,
        "platformImportPreviewActions": platform_import_preview_actions,
        "platformImportPreviewSignoff": platform_import_preview_signoff,
        "agentEntityMockImport": agent_entity_mock_import,
        "agentEntityImportActivity": agent_entity_import_activity,
        "agentEntityReadinessReport": agent_entity_readiness_report,
        "gradingJobs": grading_jobs,
        "gradingRecords": grading_records,
        "controlledGradingEvidence": controlled_grading_evidence,
        "mergedGradingEvidence": merged_grading_evidence,
        "reviewDecisionNotes": review_decision_notes,
        "preApproveReviewCheck": pre_approve_review_check,
        "contentQualitySummary": content_quality_summary,
        "agentEntities": agent_entities,
        "artifacts": artifacts,
        "workflowRuns": workflow_runs,
        "workflowSteps": workflow_steps,
        "reviewAuditEvents": review_audit_events,
        "operationAuditEvents": operation_audit_events,
        "providerCallAuditEvents": provider_call_audit_events,
        "reviewPolicy": review_policy,
        "revisionRequests": revision_requests,
        "reviewPage": review_page,
        "safety": safety,
        "summary": {
            "artifactTotal": len(artifacts),
            "workflowRunTotal": len(workflow_runs),
            "workflowStepTotal": len(workflow_steps),
            "reviewAuditEventTotal": len(review_audit_events),
            "operationAuditEventTotal": len(operation_audit_events),
            "revisionRequestTotal": revision_requests["total"],
            "providerCallAuditEventTotal": len(provider_call_audit_events),
            "contentQualityAvailable": content_quality_summary.get("available") is True,
            "contentQualityStatus": content_quality_summary.get("status"),
            "contentQualityIssueTotal": content_quality_summary.get("issueTotal", 0),
            "contentQualityBlockingIssueTotal": content_quality_summary.get("blockingIssueTotal", 0),
            "dslPreviewContentLoaded": bool(dsl_preview.get("contentLoaded")),
            "dslPreviewSchemaValidated": bool(dsl_preview.get("schemaValidated")),
            "dslPreviewTitle": dsl_preview.get("title"),
            "highRiskIntentAuditEventTotal": 1 if high_risk_intent else 0,
            "promotionReviewDispositionVisible": promotion_review_disposition is not None,
            "platformImportPreviewVisible": platform_import_preview["visible"],
            "platformImportPreviewTotal": platform_import_preview["total"],
            "platformImportPreviewActionVisible": platform_import_preview_actions["visible"],
            "platformImportPreviewActionTotal": platform_import_preview_actions["total"],
            "platformImportPreviewActionEnabledTotal": platform_import_preview_actions["enabledTotal"],
            "platformImportPreviewSignoffVisible": platform_import_preview_signoff["visible"],
            "platformImportPreviewSignoffTotal": platform_import_preview_signoff["total"],
            "platformImportPreviewSignoffBlockedTotal": platform_import_preview_signoff["blockedTotal"],
            "platformImportPreviewSignoffReady": platform_import_preview_signoff["readyForHumanSignoff"],
            "agentEntityMockImportVisible": agent_entity_mock_import["visible"],
            "agentEntityMockImportTotal": agent_entity_mock_import["total"],
            "agentEntityImportActivityVisible": agent_entity_import_activity["visible"],
            "agentEntityImportActivitySendTotal": agent_entity_import_activity["sendTotal"],
            "agentEntityReadinessReportVisible": True,
            "agentEntityReadinessRequiredTotal": agent_entity_readiness_report["summary"]["requiredTotal"],
            "agentEntitySignoffReadyTotal": agent_entity_readiness_report["summary"][
                "agentEntitySignoffReadyTotal"
            ],
            "agentEntitySignoffRecordedTotal": agent_entity_readiness_report["summary"][
                "agentEntitySignoffRecordedTotal"
            ],
            "gradingJobVisible": grading_jobs["visible"],
            "gradingJobTotal": grading_jobs["total"],
            "gradingJobLatestStatus": grading_jobs["summary"]["latestStatus"],
            "gradingJobLatestEarnedScore": grading_jobs["summary"]["latestEarnedScore"],
            "gradingJobLatestTotalScore": grading_jobs["summary"]["latestTotalScore"],
            "gradingRecordVisible": grading_records["visible"],
            "gradingRecordTotal": grading_records["total"],
            "gradingRecordLatestStatus": grading_records["summary"]["latestStatus"],
            "gradingRecordLatestEarnedScore": grading_records["summary"]["latestEarnedScore"],
            "gradingRecordLatestTotalScore": grading_records["summary"]["latestTotalScore"],
            "gradingRecordHumanReviewRecordedTotal": grading_records["summary"][
                "humanReviewRecordedTotal"
            ],
            "gradingRecordReadyForPlatformReview": grading_records["summary"][
                "readyForAgentReview"
            ],
            "gradingRecordPlatformReviewState": grading_records["summary"]["platformReviewState"],
            "gradingRecordPlatformReviewNextRequiredAction": grading_records["summary"][
                "platformReviewNextRequiredAction"
            ],
            "controlledGradingEvidenceVisible": controlled_grading_evidence["visible"],
            "controlledGradingEvidenceReportTotal": controlled_grading_evidence["reportTotal"],
            "controlledGradingEvidenceExecutedTotal": controlled_grading_evidence["summary"]["executedTotal"],
            "controlledGradingEvidenceEarnedScore": controlled_grading_evidence["summary"]["earnedScore"],
            "mergedGradingEvidenceVisible": merged_grading_evidence["visible"],
            "mergedGradingEvidenceReportTotal": merged_grading_evidence["reportTotal"],
            "mergedGradingEvidenceExecutedTotal": merged_grading_evidence["summary"]["executedTotal"],
            "mergedGradingEvidenceEarnedScore": merged_grading_evidence["summary"]["earnedScore"],
            "mergedGradingEvidenceTotalScore": merged_grading_evidence["summary"]["totalScore"],
            "mergedGradingEvidenceCoverageRatio": merged_grading_evidence["summary"]["coverageRatio"],
            "reviewDecisionNoteTotal": review_decision_notes["total"],
            "reviewDecisionNoteVisible": review_decision_notes["visible"],
            "preApproveReviewCheckVisible": pre_approve_review_check["applicable"],
            "preApproveReviewCheckWarningTotal": pre_approve_review_check["summary"]["warningTotal"],
            "preApproveReviewCheckApproveReadyDecision": pre_approve_review_check["summary"][
                "approveReadyDecision"
            ],
        },
    }


def build_second_confirmation_status(
    store: JsonTaskStore,
    task_id: str,
) -> dict[str, Any] | None:
    detail = build_review_detail(store, task_id)
    if detail is None:
        return None

    high_risk_intent = detail.get("highRiskIntent")
    disposition = (high_risk_intent or {}).get("postReviewDisposition")
    if high_risk_intent is None or disposition is None:
        return {
            "mode": "MOCK_ONLY",
            "taskId": task_id,
            "eligible": False,
            "code": "NOT_HIGH_RISK_MCP_INTENT",
            "message": "任务不是高风险 MCP 审核意图",
            "task": detail["task"],
            "secondConfirmationRequired": False,
            "secondConfirmationSatisfied": False,
            "state": None,
            "nextRequiredAction": "none",
            "readOnly": True,
            "confirmationActionAvailable": False,
            "executeRealActionAllowed": False,
            "destroyRealEnvironmentEnabled": False,
            "realActionExecuted": False,
            "realCloudResourceChanged": False,
            "environmentDestroyed": False,
            "bypassReviewAllowed": False,
        }
    if not disposition["secondConfirmationRequired"]:
        return {
            "mode": "MOCK_ONLY",
            "taskId": task_id,
            "eligible": False,
            "code": "SECOND_CONFIRMATION_NOT_REQUIRED",
            "message": "高风险 MCP 意图不需要二次确认",
            "task": detail["task"],
            "intent": {
                "intentType": high_risk_intent["intentType"],
                "toolName": high_risk_intent["toolName"],
                "resourceType": high_risk_intent["resourceType"],
                "resourceId": high_risk_intent["resourceId"],
                "riskLevel": high_risk_intent["riskLevel"],
            },
            "state": disposition["state"],
            "sourceStatus": disposition["sourceStatus"],
            "reviewCompleted": disposition["reviewCompleted"],
            "nextRequiredAction": disposition["nextRequiredAction"],
            "secondConfirmationRequired": False,
            "secondConfirmationSatisfied": False,
            "readOnly": True,
            "confirmationActionAvailable": False,
            "executeRealActionAllowed": False,
            "executeRealPublishEnabled": False,
            "destroyRealEnvironmentEnabled": False,
            "bypassReviewEnabled": False,
            "realActionExecuted": False,
            "realPublish": False,
            "realCloudResourceChanged": False,
            "environmentDestroyed": False,
            "autoPublishAllowed": False,
        }

    return {
        "mode": "MOCK_ONLY",
        "taskId": task_id,
        "eligible": True,
        "code": "OK",
        "message": "二次确认状态仅供查询，不执行真实动作",
        "task": detail["task"],
        "intent": {
            "intentType": high_risk_intent["intentType"],
            "toolName": high_risk_intent["toolName"],
            "resourceType": high_risk_intent["resourceType"],
            "resourceId": high_risk_intent["resourceId"],
            "riskLevel": high_risk_intent["riskLevel"],
            "operationAuditEventId": high_risk_intent.get("operationAuditEventId"),
            "requestId": high_risk_intent.get("requestId"),
        },
        "state": disposition["state"],
        "sourceStatus": disposition["sourceStatus"],
        "reviewCompleted": disposition["reviewCompleted"],
        "nextRequiredAction": disposition["nextRequiredAction"],
        "secondConfirmationRequired": disposition["secondConfirmationRequired"],
        "secondConfirmationSatisfied": disposition["secondConfirmationSatisfied"],
        "readOnly": True,
        "confirmationActionAvailable": False,
        "confirmationEndpointEnabled": False,
        "executionBlocked": disposition["executionBlocked"],
        "executeRealActionAllowed": False,
        "executeRealPublishEnabled": False,
        "destroyRealEnvironmentEnabled": False,
        "bypassReviewEnabled": False,
        "realActionExecuted": False,
        "realPublish": False,
        "realCloudResourceChanged": False,
        "environmentDestroyed": False,
        "autoPublishAllowed": False,
        "blockedActions": [
            "confirmSecondFactor",
            "executeRealAction",
            "executeRealPublish",
            "destroyRealEnvironment",
            "bypassHumanReview",
        ],
        "reviewDetailRef": {
            "taskId": task_id,
            "postReviewDispositionState": detail["reviewPolicy"]["postReviewDispositionState"],
        },
    }
