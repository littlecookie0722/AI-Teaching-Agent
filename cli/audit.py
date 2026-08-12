"""Local operation audit model for Phase 1 mock actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class OperationAction(StrEnum):
    REVIEW_APPROVE = "REVIEW_APPROVE"
    REVIEW_REJECT = "REVIEW_REJECT"
    REVIEW_REVISION_REQUEST = "REVIEW_REVISION_REQUEST"
    REVIEW_MOCK_REGENERATE = "REVIEW_MOCK_REGENERATE"
    REAL_DSL_REVISION_PROMOTION_ENQUEUE = "REAL_DSL_REVISION_PROMOTION_ENQUEUE"
    LAB_TEMPLATE_IMPORT_PREVIEW = "LAB_TEMPLATE_IMPORT_PREVIEW"
    EXAM_QUESTION_IMPORT_PREVIEW = "EXAM_QUESTION_IMPORT_PREVIEW"
    GRADING_RULE_IMPORT_PREVIEW = "GRADING_RULE_IMPORT_PREVIEW"
    PPT_DECK_IMPORT_PREVIEW = "PPT_DECK_IMPORT_PREVIEW"
    LAB_TEMPLATE_MOCK_IMPORT = "LAB_TEMPLATE_MOCK_IMPORT"
    EXAM_QUESTION_MOCK_IMPORT = "EXAM_QUESTION_MOCK_IMPORT"
    GRADING_RULE_MOCK_IMPORT = "GRADING_RULE_MOCK_IMPORT"
    PPT_DECK_MOCK_IMPORT = "PPT_DECK_MOCK_IMPORT"
    PLATFORM_ENTITY_IMPORT_DRY_RUN = "PLATFORM_ENTITY_IMPORT_DRY_RUN"
    PLATFORM_ENTITY_IMPORT_SEND = "PLATFORM_ENTITY_IMPORT_SEND"
    PLATFORM_ENTITY_IMPORT_STATUS_QUERY = "PLATFORM_ENTITY_IMPORT_STATUS_QUERY"
    PLATFORM_ENTITY_IMPORT_RESULT_RECORD = "PLATFORM_ENTITY_IMPORT_RESULT_RECORD"
    PLATFORM_ENTITY_SIGNOFF_RECORD = "PLATFORM_ENTITY_SIGNOFF_RECORD"
    PLATFORM_ENTITY_FINAL_PUBLISH_REVIEW_DECISION = "PLATFORM_ENTITY_FINAL_PUBLISH_REVIEW_DECISION"
    MOCK_PUBLISH = "MOCK_PUBLISH"
    ENV_CREATE = "ENV_CREATE"
    ENV_START = "ENV_START"
    ENV_STOP = "ENV_STOP"
    ENV_RESET = "ENV_RESET"
    MOCK_GRADING_RUN = "MOCK_GRADING_RUN"
    READONLY_SANDBOX_RUN = "READONLY_SANDBOX_RUN"
    CONTROLLED_GRADING_PLAN_BUILD = "CONTROLLED_GRADING_PLAN_BUILD"
    CONTROLLED_SANDBOX_RUN = "CONTROLLED_SANDBOX_RUN"
    GRADING_JOB_CREATE = "GRADING_JOB_CREATE"
    GRADING_JOB_RUN = "GRADING_JOB_RUN"
    GRADING_WORKER_DRAIN = "GRADING_WORKER_DRAIN"
    GRADING_REPOSITORY_INIT = "GRADING_REPOSITORY_INIT"
    GRADING_REPOSITORY_SYNC_LOCAL = "GRADING_REPOSITORY_SYNC_LOCAL"
    BACKEND_CORE_REPOSITORY_INIT = "BACKEND_CORE_REPOSITORY_INIT"
    BACKEND_CORE_REPOSITORY_SYNC_LOCAL = "BACKEND_CORE_REPOSITORY_SYNC_LOCAL"
    BACKEND_CORE_TASK_CREATE = "BACKEND_CORE_TASK_CREATE"
    GRADING_EVIDENCE_MERGE = "GRADING_EVIDENCE_MERGE"
    GRADING_RECORD_CREATE = "GRADING_RECORD_CREATE"
    GRADING_RECORD_REVIEW = "GRADING_RECORD_REVIEW"
    REVIEW_DECISION_NOTE_RECORD = "REVIEW_DECISION_NOTE_RECORD"
    PPTX_ARTIFACT_BUILD = "PPTX_ARTIFACT_BUILD"
    PPT_PAGE_REVIEW_UPDATE = "PPT_PAGE_REVIEW_UPDATE"
    PUBLISH_LAB_INTENT = "PUBLISH_LAB_INTENT"
    PUBLISH_EXAM_INTENT = "PUBLISH_EXAM_INTENT"
    DESTROY_ENVIRONMENT_INTENT = "DESTROY_ENVIRONMENT_INTENT"


class OperationResourceType(StrEnum):
    AI_TASK = "AI_TASK"
    LAB = "LAB"
    EXAM = "EXAM"
    PPT = "PPT"
    ENVIRONMENT = "ENVIRONMENT"
    ARTIFACT = "ARTIFACT"
    GRADING_JOB = "GRADING_JOB"
    GRADING_REPORT = "GRADING_REPORT"
    GRADING_RECORD = "GRADING_RECORD"
    GRADING_REPOSITORY = "GRADING_REPOSITORY"
    BACKEND_CORE_REPOSITORY = "BACKEND_CORE_REPOSITORY"
    PLATFORM_ENTITY = "PLATFORM_ENTITY"


@dataclass
class OperationAuditEvent:
    action: OperationAction
    resourceType: OperationResourceType
    resourceId: str
    actor: str
    beforeState: str | None = None
    afterState: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"op_audit_{uuid4().hex[:12]}")
    occurredAt: str = field(default_factory=utc_now)
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    mode: str = "MOCK_ONLY"
    realLlmCalled: bool = False
    realCloudResourceChanged: bool = False
    contestantCodeExecuted: bool = False
    realPublish: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["resourceType"] = self.resourceType.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OperationAuditEvent":
        payload = dict(data)
        payload["action"] = OperationAction(payload["action"])
        payload["resourceType"] = OperationResourceType(payload["resourceType"])
        return cls(**payload)


def create_operation_audit_event(
    *,
    action: OperationAction,
    resource_type: OperationResourceType,
    resource_id: str,
    actor: str,
    trace_id: str,
    before_state: str | None = None,
    after_state: str | None = None,
    detail: dict[str, Any] | None = None,
) -> OperationAuditEvent:
    return OperationAuditEvent(
        action=action,
        resourceType=resource_type,
        resourceId=resource_id,
        actor=actor,
        beforeState=before_state,
        afterState=after_state,
        detail=detail or {},
        traceId=trace_id,
    )
