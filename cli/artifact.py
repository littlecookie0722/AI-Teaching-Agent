"""Local artifact manifest model for Phase 1 mock outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class ArtifactKind(StrEnum):
    MATERIAL_ANALYSIS = "MATERIAL_ANALYSIS"
    LAB_DSL = "LAB_DSL"
    EXAM_DSL = "EXAM_DSL"
    GRADING_DSL = "GRADING_DSL"
    PPT_DSL = "PPT_DSL"
    PPTX_FILE = "PPTX_FILE"
    GRADING_REPORT = "GRADING_REPORT"
    REVIEW_DECISION_NOTE = "REVIEW_DECISION_NOTE"
    WORKFLOW_REPORT = "WORKFLOW_REPORT"


class ArtifactStatus(StrEnum):
    READY = "READY"
    WAITING_REVIEW = "WAITING_REVIEW"
    COMPLETED = "COMPLETED"


@dataclass
class ArtifactRecord:
    kind: ArtifactKind
    path: str
    title: str
    status: ArtifactStatus
    id: str = field(default_factory=lambda: f"artifact_{uuid4().hex[:12]}")
    taskId: str | None = None
    workflowRunId: str | None = None
    sourceRef: str | None = None
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    metadata: dict[str, Any] = field(default_factory=dict)
    mode: str = "MOCK_ONLY"
    realLlmCalled: bool = False
    realCloudResourceChanged: bool = False
    sandboxExecuted: bool = False
    contestantCodeExecuted: bool = False
    realPublish: bool = False
    createdAt: str = field(default_factory=utc_now)
    updatedAt: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRecord":
        payload = dict(data)
        payload["kind"] = ArtifactKind(payload["kind"])
        payload["status"] = ArtifactStatus(payload["status"])
        return cls(**payload)


def create_artifact_record(
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
    mode: str = "MOCK_ONLY",
    real_llm_called: bool = False,
    real_cloud_resource_changed: bool = False,
    sandbox_executed: bool = False,
    contestant_code_executed: bool = False,
    real_publish: bool = False,
) -> ArtifactRecord:
    return ArtifactRecord(
        kind=kind,
        path=path,
        title=title,
        status=status,
        taskId=task_id,
        workflowRunId=workflow_run_id,
        sourceRef=source_ref,
        traceId=trace_id,
        metadata=metadata or {},
        mode=mode,
        realLlmCalled=real_llm_called,
        realCloudResourceChanged=real_cloud_resource_changed,
        sandboxExecuted=sandbox_executed,
        contestantCodeExecuted=contestant_code_executed,
        realPublish=real_publish,
    )
