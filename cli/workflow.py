"""Local workflow run model for Phase 1 mock orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class WorkflowStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class WorkflowStep:
    name: str
    status: WorkflowStatus
    order: int
    detail: dict[str, Any] = field(default_factory=dict)
    startedAt: str = field(default_factory=utc_now)
    finishedAt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowStep":
        payload = dict(data)
        payload["status"] = WorkflowStatus(payload["status"])
        return cls(**payload)


@dataclass
class WorkflowRun:
    workflowId: str
    inputRef: str
    reviewer: str
    steps: list[WorkflowStep]
    id: str = field(default_factory=lambda: f"workflow_run_{uuid4().hex[:12]}")
    status: WorkflowStatus = WorkflowStatus.COMPLETED
    mode: str = "MOCK_ONLY"
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    createdAt: str = field(default_factory=utc_now)
    updatedAt: str = field(default_factory=utc_now)
    reportPath: str | None = None
    reviewRequired: bool = True
    publishBlockedUntilApproved: bool = True
    realLlmCalled: bool = False
    realCloudResourceChanged: bool = False
    sandboxExecuted: bool = False
    contestantCodeExecuted: bool = False
    realPublish: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["steps"] = [step.to_dict() for step in self.steps]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowRun":
        payload = dict(data)
        payload["status"] = WorkflowStatus(payload["status"])
        payload["steps"] = [WorkflowStep.from_dict(step) for step in payload.get("steps", [])]
        return cls(**payload)


def create_workflow_step(name: str, order: int, detail: dict[str, Any] | None = None) -> WorkflowStep:
    timestamp = utc_now()
    return WorkflowStep(
        name=name,
        order=order,
        status=WorkflowStatus.COMPLETED,
        detail=detail or {},
        startedAt=timestamp,
        finishedAt=timestamp,
    )


def create_workflow_run(
    *,
    workflow_id: str,
    input_ref: str,
    reviewer: str,
    trace_id: str,
    report_path: str | None,
    steps: list[WorkflowStep],
) -> WorkflowRun:
    return WorkflowRun(
        workflowId=workflow_id,
        inputRef=input_ref,
        reviewer=reviewer,
        steps=steps,
        traceId=trace_id,
        reportPath=report_path,
    )
