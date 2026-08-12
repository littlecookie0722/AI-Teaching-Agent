"""Local mock AI Task model and state transitions for Phase 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_REVIEW = "WAITING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReviewAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MOCK_PUBLISH = "MOCK_PUBLISH"


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.RUNNING: {TaskStatus.WAITING_REVIEW, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.WAITING_REVIEW: {TaskStatus.APPROVED, TaskStatus.REJECTED},
    TaskStatus.APPROVED: {TaskStatus.COMPLETED},
    TaskStatus.REJECTED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.COMPLETED: set(),
    TaskStatus.CANCELLED: set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class AiTask:
    taskType: str
    title: str
    inputType: str
    inputRef: str
    id: str = field(default_factory=lambda: f"task_{uuid4().hex[:12]}")
    status: TaskStatus = TaskStatus.WAITING_REVIEW
    modelName: str = "mock"
    promptVersion: str = "phase1-mock"
    intermediateResultPath: str | None = None
    finalResultPath: str | None = None
    errorMessage: str | None = None
    createdBy: str = "lab-cli"
    createdAt: str = field(default_factory=utc_now)
    updatedAt: str = field(default_factory=utc_now)
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    reviewer: str | None = None
    reviewedAt: str | None = None
    reviewReason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AiTask":
        payload = dict(data)
        payload["status"] = TaskStatus(payload["status"])
        return cls(**payload)

    def transition_to(
        self,
        next_status: TaskStatus,
        *,
        reviewer: str | None = None,
        reason: str | None = None,
    ) -> None:
        if next_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"Illegal AI task status transition: {self.status.value} -> {next_status.value}")
        if next_status == TaskStatus.REJECTED and not reason:
            raise ValueError("Reject transition requires a reason")
        if next_status in {TaskStatus.APPROVED, TaskStatus.REJECTED} and not reviewer:
            raise ValueError("Review transition requires a reviewer")
        self.status = next_status
        if next_status in {TaskStatus.APPROVED, TaskStatus.REJECTED}:
            self.reviewer = reviewer
            self.reviewedAt = utc_now()
            self.reviewReason = reason
        self.updatedAt = utc_now()


@dataclass
class ReviewAuditEvent:
    taskId: str
    taskType: str
    action: ReviewAction
    actor: str
    fromStatus: TaskStatus
    toStatus: TaskStatus
    reason: str | None = None
    id: str = field(default_factory=lambda: f"audit_{uuid4().hex[:12]}")
    occurredAt: str = field(default_factory=utc_now)
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    mode: str = "MOCK_ONLY"
    realPublish: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["fromStatus"] = self.fromStatus.value
        data["toStatus"] = self.toStatus.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewAuditEvent":
        payload = dict(data)
        payload["action"] = ReviewAction(payload["action"])
        payload["fromStatus"] = TaskStatus(payload["fromStatus"])
        payload["toStatus"] = TaskStatus(payload["toStatus"])
        return cls(**payload)


def create_review_audit_event(
    *,
    task: AiTask,
    action: ReviewAction,
    actor: str,
    from_status: TaskStatus,
    to_status: TaskStatus,
    trace_id: str,
    reason: str | None = None,
) -> ReviewAuditEvent:
    return ReviewAuditEvent(
        taskId=task.id,
        taskType=task.taskType,
        action=action,
        actor=actor,
        fromStatus=from_status,
        toStatus=to_status,
        reason=reason,
        traceId=trace_id,
    )


def create_waiting_review_task(
    *,
    task_type: str,
    title: str,
    input_type: str,
    input_ref: str,
    final_result_path: str | None = None,
    trace_id: str | None = None,
) -> AiTask:
    task = AiTask(
        taskType=task_type,
        title=title,
        inputType=input_type,
        inputRef=input_ref,
        finalResultPath=final_result_path,
    )
    if trace_id:
        task.traceId = trace_id
    return task
