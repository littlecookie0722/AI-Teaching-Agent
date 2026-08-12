"""Local mock agent entity model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class AgentEntityType(StrEnum):
    LAB_TEMPLATE = "lab_template"
    EXAM_QUESTION = "exam_question"
    GRADING_RULE = "grading_rule"
    PPT_DECK = "ppt_deck"


class AgentEntityStatus(StrEnum):
    DRAFT_CREATED = "DRAFT_CREATED"
    PUBLISH_PENDING = "PUBLISH_PENDING"
    PUBLISH_REVIEWING = "PUBLISH_REVIEWING"
    PUBLISH_ACCEPTED = "PUBLISH_ACCEPTED"
    PUBLISH_REJECTED = "PUBLISH_REJECTED"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    REAL_IMPORT_PENDING_REVIEW = "REAL_IMPORT_PENDING_REVIEW"
    REAL_IMPORT_DRAFT_ACCEPTED = "REAL_IMPORT_DRAFT_ACCEPTED"
    REAL_IMPORT_REJECTED = "REAL_IMPORT_REJECTED"
    REAL_IMPORT_FAILED = "REAL_IMPORT_FAILED"


@dataclass
class AgentEntityRecord:
    entityType: AgentEntityType
    title: str
    payload: dict[str, Any]
    sourceTaskId: str
    sourcePreviewArtifactId: str
    sourcePreviewPath: str
    reviewer: str
    id: str = field(default_factory=lambda: f"agent_entity_{uuid4().hex[:12]}")
    status: AgentEntityStatus = AgentEntityStatus.DRAFT_CREATED
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    sourceDslPath: str | None = None
    sourceArtifactId: str | None = None
    sourceArtifactKind: str | None = None
    mockStoreWritten: bool = True
    databaseWritten: bool = False
    realAgentImport: bool = False
    realPublish: bool = False
    createdAt: str = field(default_factory=utc_now)
    updatedAt: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entityType"] = self.entityType.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentEntityRecord":
        payload = dict(data)
        # Backward compatibility: migrate old field names
        if "realPlatformImport" in payload and "realAgentImport" not in payload:
            payload["realAgentImport"] = payload.pop("realPlatformImport")
        payload["entityType"] = AgentEntityType(payload["entityType"])
        payload["status"] = AgentEntityStatus(payload["status"])
        return cls(**payload)


def create_agent_entity_record(
    *,
    entity_type: AgentEntityType,
    title: str,
    payload: dict[str, Any],
    source_task_id: str,
    source_preview_artifact_id: str,
    source_preview_path: str,
    reviewer: str,
    trace_id: str,
    source_dsl_path: str | None = None,
    source_artifact_id: str | None = None,
    source_artifact_kind: str | None = None,
) -> AgentEntityRecord:
    return AgentEntityRecord(
        entityType=entity_type,
        title=title,
        payload=payload,
        sourceTaskId=source_task_id,
        sourcePreviewArtifactId=source_preview_artifact_id,
        sourcePreviewPath=source_preview_path,
        reviewer=reviewer,
        traceId=trace_id,
        sourceDslPath=source_dsl_path,
        sourceArtifactId=source_artifact_id,
        sourceArtifactKind=source_artifact_kind,
    )
