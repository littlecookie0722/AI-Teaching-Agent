"""Backend grading job service.

This service keeps grading job creation and synchronous local execution out of
the HTTP router. It preserves the current local JSON / SQLite staging behavior
while making the next real backend API migration smaller.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.grading_job import GradingJob, GradingJobError, GradingJobStatus, create_grading_job, run_grading_job
from cli.store import JsonTaskStore
from sandbox.controlled_command_executor import DEFAULT_IMAGE as DEFAULT_CONTROLLED_DOCKER_IMAGE

from backend.grading_repository import (
    DEFAULT_CLAIM_LEASE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    GradingRepositoryError,
    GradingSQLiteRepository,
)
from backend.grading_worker import GradingWorkerError, run_next_grading_job_once


class BackendGradingJobServiceError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


@dataclass(frozen=True)
class GradingRepositoryPolicy:
    db_path_source: str
    backend_default_sqlite_enabled: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GradingRepositoryPolicy":
        return cls(
            db_path_source=str(value.get("dbPathSource") or "JSON_STORE"),
            backend_default_sqlite_enabled=value.get("backendDefaultSqliteEnabled") is True,
        )


class BackendGradingJobService:
    def __init__(
        self,
        *,
        root: Path,
        store: JsonTaskStore,
        repository: GradingSQLiteRepository | None,
        repository_policy: GradingRepositoryPolicy,
    ) -> None:
        self.root = root
        self.store = store
        self.repository = repository
        self.repository_policy = repository_policy

    def create_job(self, payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
        job = self._create_job_from_payload(payload, trace_id=trace_id)
        if self.repository is not None:
            job = self._save_job_to_sqlite(job)
        else:
            self.store.save_grading_job(job)
        operation_audit_event = self._create_job_audit(
            job,
            actor=str(payload.get("reviewer") or "backend-mock"),
            trace_id=trace_id,
            created_by_run_request=False,
        )
        self.store.save_operation_audit_event(operation_audit_event)
        return {
            "gradingJob": job,
            "operationAuditEvent": operation_audit_event,
            "mode": "LOCAL_SQLITE_GRADING_JOB" if self.repository else "LOCAL_GRADING_JOB",
            **self._storage_summary(local_sqlite_written=self.repository is not None),
        }

    def run_job(self, payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
        if self.repository is not None:
            return self._run_sqlite_job(payload, trace_id=trace_id)
        return self._run_json_store_job(payload, trace_id=trace_id)

    def _run_sqlite_job(self, payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
        lease_seconds = self._optional_positive_int(payload, "leaseSeconds", DEFAULT_CLAIM_LEASE_SECONDS)
        max_attempts = self._optional_positive_int(payload, "maxAttempts", DEFAULT_MAX_ATTEMPTS)
        job_id = str(payload.get("id") or "").strip()
        if job_id:
            try:
                existing_job = self.repository.get_grading_job(job_id)
            except GradingRepositoryError as exc:
                raise self._repo_error(exc) from exc
            if existing_job is None:
                raise BackendGradingJobServiceError(
                    "NOT_FOUND",
                    "Grading 评分任务不存在",
                    [{"field": "id", "reason": "未找到任务"}],
                )
        else:
            job = self._create_job_from_payload(payload, trace_id=trace_id)
            try:
                self._save_job_to_sqlite(job)
            except GradingRepositoryError as exc:
                raise self._repo_error(exc) from exc
            create_event = self._create_job_audit(
                job,
                actor=str(payload.get("reviewer") or "backend-mock"),
                trace_id=trace_id,
                created_by_run_request=True,
            )
            self.store.save_operation_audit_event(create_event)
            job_id = job.id
        try:
            result = run_next_grading_job_once(
                repository=self.repository,
                store=self.store,
                root=self.root,
                trace_id=trace_id,
                actor=str(payload.get("reviewer") or "backend-grading-worker"),
                job_id=job_id,
                lease_seconds=lease_seconds,
                max_attempts=max_attempts,
            )
        except GradingWorkerError as exc:
            raise BackendGradingJobServiceError(exc.code, exc.message, exc.errors) from exc
        return {
            **result,
            "mode": "LOCAL_SQLITE_GRADING_WORKER_ONCE",
            **self._storage_summary(local_sqlite_written=bool(result.get("workerRun", {}).get("jobFound"))),
        }

    def _run_json_store_job(self, payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
        job_id = str(payload.get("id") or "").strip()
        if job_id:
            job = self.store.get_grading_job(job_id)
            if job is None:
                raise BackendGradingJobServiceError(
                    "NOT_FOUND",
                    "Grading 评分任务不存在",
                    [{"field": "id", "reason": "未找到任务"}],
                )
        else:
            job = self._create_job_from_payload(payload, trace_id=trace_id)
            self.store.save_grading_job(job)
            create_event = self._create_job_audit(
                job,
                actor=str(payload.get("reviewer") or "backend-mock"),
                trace_id=trace_id,
                created_by_run_request=True,
            )
            self.store.save_operation_audit_event(create_event)
        if job.status not in {GradingJobStatus.QUEUED, GradingJobStatus.FAILED}:
            raise BackendGradingJobServiceError(
                "STATE_TRANSITION_ERROR",
                "Grading 评分任务状态非法流转",
                [{"field": "status", "reason": f"cannot run from {job.status.value}"}],
            )
        before_status = job.status.value
        try:
            job, report, record = run_grading_job(job, root=self.root)
        except GradingJobError as exc:
            self.store.save_grading_job(job)
            operation_audit_event = self._run_job_audit(
                job,
                before_status=before_status,
                trace_id=trace_id,
                detail={
                    "component": "GradingJobRun",
                    "jobId": job.id,
                    "taskId": job.taskId,
                    "submissionId": job.submissionId,
                    "errorCode": exc.code,
                    "errors": exc.errors,
                    "recordCreated": False,
                    "autoApproveAllowed": False,
                    "realPublish": False,
                },
            )
            self.store.save_operation_audit_event(operation_audit_event)
            error = BackendGradingJobServiceError(exc.code, exc.message, exc.errors)
            error.data = {
                "gradingJob": job.to_dict(),
                "operationAuditEvent": operation_audit_event.to_dict(),
            }
            error.provider_error_context = {
                "adapterId": "local_grading_job_executor",
                "interfaceName": "GradingJob",
                "operation": "run",
                "mode": "LOCAL_GRADING_JOB_SYNC_RUN",
                "jobId": job.id,
                "status": job.status.value,
                "recordCreated": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            }
            raise error from exc
        self.store.save_grading_job(job)
        self.store.save_grading_record(record)
        operation_audit_event = self._run_job_audit(
            job,
            before_status=before_status,
            trace_id=trace_id,
            detail={
                "component": "GradingJobRun",
                "jobId": job.id,
                "taskId": job.taskId,
                "submissionId": job.submissionId,
                "candidateId": job.candidateId,
                "reportId": job.reportId,
                "reportPath": job.reportPath,
                "gradingRecordId": job.gradingRecordId,
                "summary": job.summary,
                "safety": job.safety,
            },
        )
        self.store.save_operation_audit_event(operation_audit_event)
        artifact = create_artifact_record(
            kind=ArtifactKind.GRADING_REPORT,
            path=str(job.reportPath),
            title="Grading Job Evidence Report",
            status=ArtifactStatus.COMPLETED,
            trace_id=trace_id,
            task_id=job.taskId,
            source_ref=job.gradingPath,
            metadata={
                "reportType": "GRADING_EVIDENCE_AUTO",
                "gradingJobId": job.id,
                "gradingRecordId": record.id,
                "submissionId": job.submissionId,
                "candidateId": job.candidateId,
                "summary": job.summary,
                "safety": job.safety,
            },
            sandbox_executed=bool(job.safety.get("sandboxExecuted")),
            contestant_code_executed=bool(job.safety.get("contestantCodeExecuted")),
        )
        self.store.save_artifact(artifact)
        artifact_payload = artifact.to_dict()
        report["operationAuditEvent"] = operation_audit_event.to_dict()
        report["artifact"] = artifact_payload
        Path(str(job.reportPath)).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {
            "gradingJob": job.to_dict(),
            "gradingRecord": record.to_dict(),
            "report": report,
            "artifact": artifact_payload,
            "operationAuditEvent": operation_audit_event.to_dict(),
            "mode": "LOCAL_GRADING_JOB_SYNC_RUN",
            "databaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        }

    def _create_job_from_payload(self, payload: dict[str, Any], *, trace_id: str) -> GradingJob:
        for field in ("grading", "submission", "output"):
            if not str(payload.get(field) or "").strip():
                raise BackendGradingJobServiceError(
                    "VALIDATION_ERROR",
                    "参数错误",
                    [{"field": field, "reason": "缺少参数"}],
                )
        task_id = str(payload.get("taskId") or "").strip() or None
        if task_id and self.store.get(task_id) is None:
            raise BackendGradingJobServiceError(
                "NOT_FOUND",
                "AI Task 不存在",
                [{"field": "taskId", "reason": "未找到任务"}],
            )
        grading_path = self._resolve_local_path(str(payload["grading"]))
        submission_path = self._resolve_local_path(str(payload["submission"]))
        if not grading_path.exists() or not grading_path.is_file():
            raise BackendGradingJobServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "grading", "reason": "文件不存在"}],
            )
        if not submission_path.exists() or not submission_path.is_dir():
            raise BackendGradingJobServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "submission", "reason": "目录不存在"}],
            )
        try:
            return create_grading_job(
                grading_path=grading_path,
                submission_path=submission_path,
                output_path=self._resolve_local_path(str(payload["output"])),
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
            raise BackendGradingJobServiceError(exc.code, exc.message, exc.errors) from exc

    def _save_job_to_sqlite(self, job: GradingJob) -> GradingJob:
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
        try:
            self.repository.save_grading_job(job)
        except GradingRepositoryError as exc:
            raise self._repo_error(exc) from exc
        self.store.save_grading_job(job)
        return job

    def _create_job_audit(
        self,
        job: GradingJob,
        *,
        actor: str,
        trace_id: str,
        created_by_run_request: bool,
    ):
        detail = {
            "component": "BackendGradingJobService",
            "operation": "create_job",
            "jobId": job.id,
            "taskId": job.taskId,
            "submissionId": job.submissionId,
            "candidateId": job.candidateId,
            "gradingPath": job.gradingPath,
            "submissionPath": job.submissionPath,
            "outputPath": job.outputPath,
            "includeControlledCommand": job.includeControlledCommand,
            "localStagingJob": True,
            "dbPath": str(self.repository.db_path) if self.repository else None,
            "dbPathSource": self.repository_policy.db_path_source,
            "backendDefaultSqliteEnabled": self.repository_policy.backend_default_sqlite_enabled,
            "localSqliteWritten": self.repository is not None,
            "databaseWritten": False,
            "productionDatabaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        }
        if created_by_run_request:
            detail["createdByRunRequest"] = True
        return create_operation_audit_event(
            action=OperationAction.GRADING_JOB_CREATE,
            resource_type=OperationResourceType.GRADING_JOB,
            resource_id=job.id,
            actor=actor,
            trace_id=trace_id,
            after_state=job.status.value,
            detail=detail,
        )

    def _run_job_audit(
        self,
        job: GradingJob,
        *,
        before_status: str,
        trace_id: str,
        detail: dict[str, Any],
    ):
        return create_operation_audit_event(
            action=OperationAction.GRADING_JOB_RUN,
            resource_type=OperationResourceType.GRADING_JOB,
            resource_id=job.id,
            actor=job.reviewer or "backend-mock",
            trace_id=trace_id,
            before_state=before_status,
            after_state=job.status.value,
            detail=detail,
        )

    def _storage_summary(self, *, local_sqlite_written: bool) -> dict[str, Any]:
        return {
            "dbPath": str(self.repository.db_path) if self.repository else None,
            "dbPathSource": self.repository_policy.db_path_source,
            "backendDefaultSqliteEnabled": self.repository_policy.backend_default_sqlite_enabled,
            "localSqliteWritten": local_sqlite_written,
            "databaseWritten": False,
            "productionDatabaseWritten": False,
            "queuePersistedToProduction": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        }

    def _optional_positive_int(self, payload: dict[str, Any], field: str, default: int) -> int:
        if field not in payload or payload.get(field) in (None, ""):
            return default
        try:
            value = int(payload[field])
        except (TypeError, ValueError) as exc:
            raise BackendGradingJobServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": field, "reason": "必须是正整数"}],
            ) from exc
        if value <= 0:
            raise BackendGradingJobServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": field, "reason": "必须是正整数"}],
            )
        return value

    def _resolve_local_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.root / path

    def _repo_error(self, exc: GradingRepositoryError) -> BackendGradingJobServiceError:
        return BackendGradingJobServiceError(exc.code, exc.message, exc.errors)
