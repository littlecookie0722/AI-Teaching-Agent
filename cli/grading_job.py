"""Local grading job model and synchronous executor."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from sandbox.evidence_auto import GradingEvidenceAutoError, build_grading_evidence_auto_report
from sandbox.evidence_merge import EvidenceMergeError
from sandbox.readonly_sandbox_executor import ReadonlySandboxExecutorError

from .ai_task import utc_now
from .dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from .grading_record import GradingRecord, build_grading_record_from_report


class GradingJobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_REVIEW = "WAITING_REVIEW"
    FAILED = "FAILED"


@dataclass
class GradingJob:
    gradingPath: str
    submissionPath: str
    outputPath: str
    submissionId: str
    status: GradingJobStatus = GradingJobStatus.QUEUED
    taskId: str | None = None
    candidateId: str | None = None
    reviewer: str | None = None
    includeControlledCommand: bool = False
    failOnControlledUnavailable: bool = False
    image: str = "ai-grading-python:0.1"
    reportId: str | None = None
    reportPath: str | None = None
    gradingRecordId: str | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    errors: list[dict[str, str]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"grading_job_{uuid4().hex[:12]}")
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    createdAt: str = field(default_factory=utc_now)
    updatedAt: str = field(default_factory=utc_now)
    startedAt: str | None = None
    finishedAt: str | None = None
    claimOwner: str | None = None
    claimedAt: str | None = None
    claimExpiresAt: str | None = None
    attemptCount: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GradingJob":
        payload = dict(data)
        payload["status"] = GradingJobStatus(payload["status"])
        return cls(**payload)


class GradingJobError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def create_grading_job(
    *,
    grading_path: Path,
    submission_path: Path,
    output_path: Path,
    submission_id: str,
    trace_id: str,
    task_id: str | None = None,
    candidate_id: str | None = None,
    reviewer: str | None = None,
    include_controlled_command: bool = False,
    fail_on_controlled_unavailable: bool = False,
    image: str = "ai-grading-python:0.1",
) -> GradingJob:
    submission_id = submission_id.strip()
    if not submission_id:
        raise GradingJobError("VALIDATION_ERROR", "参数错误", [{"field": "submissionId", "reason": "缺少参数"}])
    return GradingJob(
        gradingPath=str(grading_path),
        submissionPath=str(submission_path),
        outputPath=str(output_path),
        submissionId=submission_id,
        taskId=task_id,
        candidateId=candidate_id,
        reviewer=reviewer,
        includeControlledCommand=include_controlled_command,
        failOnControlledUnavailable=fail_on_controlled_unavailable,
        image=image,
        traceId=trace_id,
        safety={
            "localStagingJob": True,
            "databaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    )


def run_grading_job(
    job: GradingJob,
    *,
    root: Path,
) -> tuple[GradingJob, dict[str, Any], GradingRecord]:
    job.status = GradingJobStatus.RUNNING
    job.startedAt = utc_now()
    job.updatedAt = job.startedAt
    grading_path = _resolve_local_path(job.gradingPath, root)
    submission_path = _resolve_local_path(job.submissionPath, root)
    output_path = _resolve_local_path(job.outputPath, root)
    try:
        _ensure_grading_inputs(grading_path, submission_path)
        grading = load_yaml(grading_path)
        validate_dsl(grading, load_schema("grading", root))
        auto_payload = build_grading_evidence_auto_report(
            grading,
            submission_path,
            trace_id=job.traceId,
            include_controlled_command=job.includeControlledCommand,
            image=job.image,
            fail_on_controlled_unavailable=job.failOnControlledUnavailable,
        )
    except GradingJobError as exc:
        return _fail_job(job, exc.code, exc.message, exc.errors)
    except DslValidationError as exc:
        return _fail_job(job, "SCHEMA_VALIDATION_ERROR", "DSL Schema 校验失败", exc.errors)
    except (GradingEvidenceAutoError, ReadonlySandboxExecutorError, EvidenceMergeError) as exc:
        return _fail_job(job, exc.code, exc.message, exc.errors)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    auto_payload["reportPath"] = str(output_path)
    auto_payload["gradingJobId"] = job.id
    auto_payload["taskId"] = job.taskId
    output_path.write_text(json.dumps(auto_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record = build_grading_record_from_report(
        auto_payload,
        report_path=output_path,
        submission_id=job.submissionId,
        trace_id=job.traceId,
        task_id=job.taskId,
        candidate_id=job.candidateId,
        reviewer=job.reviewer,
    )
    job.status = GradingJobStatus.WAITING_REVIEW
    job.reportId = str(auto_payload.get("id") or "")
    job.reportPath = str(output_path)
    job.gradingRecordId = record.id
    job.summary = {
        "mode": auto_payload.get("mode"),
        "sourceMode": auto_payload.get("sourceMode"),
        "earnedScore": record.earnedScore,
        "totalScore": record.totalScore,
        "coveredScore": record.coveredScore,
        "missingScore": record.missingScore,
        "coverageRatio": record.coverageRatio,
        "recordStatus": record.status.value,
        "manualReviewRequired": True,
    }
    job.safety = {
        **job.safety,
        **(auto_payload.get("safety") if isinstance(auto_payload.get("safety"), dict) else {}),
        "localStagingJob": True,
        "databaseWritten": False,
        "queuePersistedToProduction": False,
        "workerStarted": False,
        "recordCreated": True,
        "recordCreatesNewExecution": False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "realPublish": False,
    }
    job.finishedAt = utc_now()
    job.updatedAt = job.finishedAt
    return job, auto_payload, record


def _fail_job(
    job: GradingJob,
    code: str,
    message: str,
    errors: list[dict[str, str]],
) -> tuple[GradingJob, dict[str, Any], GradingRecord]:
    job.status = GradingJobStatus.FAILED
    job.errorCode = code
    job.errorMessage = message
    job.errors = errors
    job.finishedAt = utc_now()
    job.updatedAt = job.finishedAt
    job.safety = {
        **job.safety,
        "localStagingJob": True,
        "recordCreated": False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "realPublish": False,
    }
    raise GradingJobError(code, message, errors)


def _ensure_grading_inputs(grading_path: Path, submission_path: Path) -> None:
    if not grading_path.exists() or not grading_path.is_file():
        raise GradingJobError("VALIDATION_ERROR", "参数错误", [{"field": "grading", "reason": "文件不存在"}])
    if not submission_path.exists() or not submission_path.is_dir():
        raise GradingJobError("VALIDATION_ERROR", "参数错误", [{"field": "submission", "reason": "目录不存在"}])


def _resolve_local_path(value: str, root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path
