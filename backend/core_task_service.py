"""Backend Core task service backed by repository contract.

This service is the first production-shaped replacement for direct JsonTaskStore
usage. It creates and reviews AI tasks through BackendCoreRepositoryContract
without depending on the local HTTP mock router.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cli.ai_task import (
    AiTask,
    ReviewAction,
    TaskStatus,
    create_review_audit_event,
    create_waiting_review_task,
)
from cli.artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event

from backend.core_contract import BackendCoreRepositoryContract
from backend.core_repository import CoreRepositoryError


class BackendCoreTaskServiceError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


@dataclass(frozen=True)
class CoreArtifactInput:
    kind: ArtifactKind
    path: str
    title: str
    status: ArtifactStatus = ArtifactStatus.WAITING_REVIEW
    source_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    mode: str = "BACKEND_CORE_SERVICE"
    real_llm_called: bool = False
    real_cloud_resource_changed: bool = False
    sandbox_executed: bool = False
    contestant_code_executed: bool = False
    real_publish: bool = False


class BackendCoreTaskService:
    def __init__(self, repository: BackendCoreRepositoryContract) -> None:
        self.repository = repository

    def create_waiting_review_task(
        self,
        *,
        task_type: str,
        title: str,
        input_type: str,
        input_ref: str,
        actor: str,
        final_result_path: str | None = None,
        trace_id: str | None = None,
        artifacts: list[CoreArtifactInput] | None = None,
    ) -> dict[str, Any]:
        self._require_text("taskType", task_type)
        self._require_text("title", title)
        self._require_text("inputType", input_type)
        self._require_text("inputRef", input_ref)
        self._require_text("actor", actor)

        task = create_waiting_review_task(
            task_type=task_type,
            title=title,
            input_type=input_type,
            input_ref=input_ref,
            final_result_path=final_result_path,
            trace_id=trace_id,
        )
        task.createdBy = actor
        task.modelName = "backend-core-service"
        task.promptVersion = "backend-core-service"
        saved_artifacts = [
            self._create_artifact(task=task, artifact_input=artifact_input)
            for artifact_input in artifacts or []
        ]
        operation_event = create_operation_audit_event(
            action=OperationAction.BACKEND_CORE_TASK_CREATE,
            resource_type=OperationResourceType.AI_TASK,
            resource_id=task.id,
            actor=actor,
            trace_id=task.traceId,
            after_state=TaskStatus.WAITING_REVIEW.value,
            detail={
                "component": "BackendCoreTaskService",
                "operation": "create_waiting_review_task",
                "artifactTotal": len(saved_artifacts),
                **self._repository_detail(),
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        )

        self.repository.save_ai_task(task)
        for artifact in saved_artifacts:
            self.repository.save_artifact(artifact)
        self.repository.save_operation_audit_event(operation_event)
        return {
            "task": task,
            "artifacts": saved_artifacts,
            "operationAuditEvent": operation_event,
            "safety": self._safety(),
        }

    def review_task(
        self,
        *,
        task_id: str,
        reviewer: str,
        decision: str,
        reason: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_text("taskId", task_id)
        self._require_text("reviewer", reviewer)
        decision_value = decision.strip().upper()
        if decision_value not in {"APPROVE", "REJECT"}:
            raise BackendCoreTaskServiceError(
                "BACKEND_CORE_TASK_REVIEW_DECISION_UNSUPPORTED",
                "Backend Core task review 决策不支持",
                [{"field": "decision", "reason": decision}],
            )
        self.repository.initialize_schema()
        task = self.repository.get_ai_task(task_id)
        if task is None:
            raise BackendCoreTaskServiceError(
                "BACKEND_CORE_TASK_NOT_FOUND",
                "Backend Core AI Task 不存在",
                [{"field": "taskId", "reason": task_id}],
            )

        from_status = task.status
        to_status = TaskStatus.APPROVED if decision_value == "APPROVE" else TaskStatus.REJECTED
        action = ReviewAction.APPROVE if decision_value == "APPROVE" else ReviewAction.REJECT
        operation_action = (
            OperationAction.REVIEW_APPROVE
            if decision_value == "APPROVE"
            else OperationAction.REVIEW_REJECT
        )
        try:
            task.transition_to(to_status, reviewer=reviewer, reason=reason)
        except ValueError as exc:
            raise BackendCoreTaskServiceError(
                "BACKEND_CORE_TASK_STATUS_TRANSITION_INVALID",
                "Backend Core AI Task 状态流转非法",
                [{"field": "status", "reason": str(exc)}],
            ) from exc

        effective_trace_id = trace_id or task.traceId
        review_event = create_review_audit_event(
            task=task,
            action=action,
            actor=reviewer,
            from_status=from_status,
            to_status=to_status,
            trace_id=effective_trace_id,
            reason=reason,
        )
        operation_event = create_operation_audit_event(
            action=operation_action,
            resource_type=OperationResourceType.AI_TASK,
            resource_id=task.id,
            actor=reviewer,
            trace_id=effective_trace_id,
            before_state=from_status.value,
            after_state=to_status.value,
            detail={
                "component": "BackendCoreTaskService",
                "operation": "review_task",
                "decision": decision_value,
                **self._repository_detail(),
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        )

        self.repository.save_ai_task(task)
        self.repository.save_review_audit_event(review_event)
        self.repository.save_operation_audit_event(operation_event)
        return {
            "task": task,
            "reviewAuditEvent": review_event,
            "operationAuditEvent": operation_event,
            "safety": self._safety(),
        }

    def _create_artifact(self, *, task: AiTask, artifact_input: CoreArtifactInput) -> ArtifactRecord:
        return create_artifact_record(
            kind=artifact_input.kind,
            path=artifact_input.path,
            title=artifact_input.title,
            status=artifact_input.status,
            task_id=task.id,
            trace_id=task.traceId,
            source_ref=artifact_input.source_ref or task.inputRef,
            metadata=artifact_input.metadata,
            mode=artifact_input.mode,
            real_llm_called=artifact_input.real_llm_called,
            real_cloud_resource_changed=artifact_input.real_cloud_resource_changed,
            sandbox_executed=artifact_input.sandbox_executed,
            contestant_code_executed=artifact_input.contestant_code_executed,
            real_publish=artifact_input.real_publish,
        )

    def _require_text(self, field: str, value: str) -> None:
        if not str(value or "").strip():
            raise BackendCoreTaskServiceError(
                "BACKEND_CORE_TASK_VALIDATION_ERROR",
                "Backend Core task 参数错误",
                [{"field": field, "reason": "不能为空"}],
            )

    def _safety(self) -> dict[str, Any]:
        return {
            "repositoryContractUsed": True,
            "repositoryDbPath": str(self.repository.db_path) if self.repository.db_path is not None else None,
            "externalRepository": self.repository.db_path is None,
            "jsonStoreWritten": False,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        }

    def _repository_detail(self) -> dict[str, Any]:
        return {
            "repositoryDbPath": str(self.repository.db_path) if self.repository.db_path is not None else None,
            "externalRepository": self.repository.db_path is None,
        }


def backend_core_task_service_error_response(exc: BackendCoreTaskServiceError) -> dict[str, Any]:
    return {
        "success": False,
        "code": exc.code,
        "message": exc.message,
        "errors": exc.errors,
    }


def core_repository_error_response(exc: CoreRepositoryError) -> dict[str, Any]:
    return {
        "success": False,
        "code": exc.code,
        "message": exc.message,
        "errors": exc.errors,
    }
