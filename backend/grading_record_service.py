"""Backend grading record service.

This service owns local grading record creation and human review updates. It
keeps write-side business rules out of the HTTP router while preserving the
current JSON store behavior and optional local SQLite staging mirror.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.grading_record import (
    GradingRecord,
    GradingRecordError,
    apply_grading_record_review,
    build_grading_record_from_report,
    load_grading_report,
)
from cli.store import JsonTaskStore

from backend.grading_job_service import GradingRepositoryPolicy
from backend.grading_repository import GradingRepositoryError, GradingSQLiteRepository


class BackendGradingRecordServiceError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class BackendGradingRecordService:
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

    def create_record(self, payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
        report_path = self._required_report_path(payload)
        submission_id = self._required_string(payload, "submissionId")
        task_id = str(payload.get("taskId") or "").strip() or None
        if task_id and self.store.get(task_id) is None:
            raise BackendGradingRecordServiceError(
                "NOT_FOUND",
                "AI Task 不存在",
                [{"field": "taskId", "reason": "未找到任务"}],
            )
        try:
            report = load_grading_report(report_path)
            record = build_grading_record_from_report(
                report,
                report_path=report_path,
                submission_id=submission_id,
                trace_id=trace_id,
                task_id=task_id,
                candidate_id=str(payload.get("candidateId") or "").strip() or None,
                reviewer=str(payload.get("reviewer") or "").strip() or None,
            )
        except GradingRecordError as exc:
            raise BackendGradingRecordServiceError(exc.code, exc.message, exc.errors) from exc
        record = self._save_record(record, local_sqlite_written=self.repository is not None)
        operation_audit_event = self._create_record_audit(
            record,
            actor=str(payload.get("reviewer") or "backend-mock"),
            trace_id=trace_id,
        )
        self.store.save_operation_audit_event(operation_audit_event)
        return {
            "gradingRecord": record,
            "operationAuditEvent": operation_audit_event,
            "mode": "LOCAL_SQLITE_GRADING_RECORD" if self.repository else "LOCAL_GRADING_RECORD",
            "recordCreatesNewExecution": False,
            **self._storage_summary(local_sqlite_written=self.repository is not None),
        }

    def review_record(self, record_id: str, payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
        record = self._get_record(record_id)
        if record is None:
            raise BackendGradingRecordServiceError(
                "NOT_FOUND",
                "Grading 评分记录不存在",
                [{"field": "id", "reason": "未找到记录"}],
            )
        before_status = record.status.value
        try:
            apply_grading_record_review(
                record,
                reviewer=str(payload.get("reviewer") or ""),
                decision=str(payload.get("decision") or ""),
                reason=payload.get("reason"),
            )
        except GradingRecordError as exc:
            raise BackendGradingRecordServiceError(exc.code, exc.message, exc.errors) from exc
        record = self._save_record(record, local_sqlite_written=self.repository is not None)
        operation_audit_event = self._review_record_audit(
            record,
            actor=str(payload.get("reviewer") or "backend-mock"),
            trace_id=trace_id,
            before_status=before_status,
        )
        self.store.save_operation_audit_event(operation_audit_event)
        return {
            "gradingRecord": record,
            "operationAuditEvent": operation_audit_event,
            "mode": "LOCAL_SQLITE_GRADING_RECORD_REVIEW" if self.repository else "LOCAL_GRADING_RECORD_REVIEW",
            "taskStatusChanged": False,
            "recordCreatesNewExecution": False,
            **self._storage_summary(local_sqlite_written=self.repository is not None),
        }

    def _get_record(self, record_id: str) -> GradingRecord | None:
        if self.repository is not None:
            try:
                record = self.repository.get_grading_record(record_id)
            except GradingRepositoryError as exc:
                raise self._repo_error(exc) from exc
            if record is not None:
                return record
        return self.store.get_grading_record(record_id)

    def _save_record(self, record: GradingRecord, *, local_sqlite_written: bool) -> GradingRecord:
        record.safety = {
            **record.safety,
            "localSqliteWritten": local_sqlite_written,
            "localSqliteOnly": local_sqlite_written,
            "databaseWritten": False,
            "productionDatabaseWritten": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        }
        if self.repository is not None:
            try:
                self.repository.save_grading_record(record)
            except GradingRepositoryError as exc:
                raise self._repo_error(exc) from exc
        self.store.save_grading_record(record)
        return record

    def _create_record_audit(self, record: GradingRecord, *, actor: str, trace_id: str):
        return create_operation_audit_event(
            action=OperationAction.GRADING_RECORD_CREATE,
            resource_type=OperationResourceType.GRADING_RECORD,
            resource_id=record.id,
            actor=actor,
            trace_id=trace_id,
            after_state=record.status.value,
            detail={
                "component": "BackendGradingRecordService",
                "operation": "create_record",
                "recordId": record.id,
                "submissionId": record.submissionId,
                "candidateId": record.candidateId,
                "taskId": record.taskId,
                "reportPath": record.reportPath,
                "reportMode": record.reportMode,
                "sourceReportId": record.sourceReportId,
                "score": self._score_summary(record),
                "status": record.status.value,
                "safety": record.safety,
                "dbPath": str(self.repository.db_path) if self.repository else None,
                "dbPathSource": self.repository_policy.db_path_source,
                "backendDefaultSqliteEnabled": self.repository_policy.backend_default_sqlite_enabled,
                "localSqliteWritten": self.repository is not None,
                "databaseWritten": False,
                "productionDatabaseWritten": False,
                "recordCreatesNewExecution": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        )

    def _review_record_audit(self, record: GradingRecord, *, actor: str, trace_id: str, before_status: str):
        return create_operation_audit_event(
            action=OperationAction.GRADING_RECORD_REVIEW,
            resource_type=OperationResourceType.GRADING_RECORD,
            resource_id=record.id,
            actor=actor,
            trace_id=trace_id,
            before_state=before_status,
            after_state=record.status.value,
            detail={
                "component": "BackendGradingRecordService",
                "operation": "review_record",
                "recordId": record.id,
                "submissionId": record.submissionId,
                "candidateId": record.candidateId,
                "taskId": record.taskId,
                "decision": record.reviewDecision,
                "reason": record.reviewReason,
                "score": self._score_summary(record),
                "statusChangedByRecordReview": True,
                "taskStatusChanged": False,
                "dbPath": str(self.repository.db_path) if self.repository else None,
                "dbPathSource": self.repository_policy.db_path_source,
                "backendDefaultSqliteEnabled": self.repository_policy.backend_default_sqlite_enabled,
                "localSqliteWritten": self.repository is not None,
                "databaseWritten": False,
                "productionDatabaseWritten": False,
                "autoApproveAllowed": False,
                "realPublishAllowed": False,
                "realPublish": False,
            },
        )

    def _storage_summary(self, *, local_sqlite_written: bool) -> dict[str, Any]:
        return {
            "dbPath": str(self.repository.db_path) if self.repository else None,
            "dbPathSource": self.repository_policy.db_path_source,
            "backendDefaultSqliteEnabled": self.repository_policy.backend_default_sqlite_enabled,
            "localSqliteWritten": local_sqlite_written,
            "databaseWritten": False,
            "productionDatabaseWritten": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        }

    def _required_report_path(self, payload: dict[str, Any]) -> Path:
        value = str(payload.get("report") or "").strip()
        if not value:
            raise BackendGradingRecordServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "report", "reason": "缺少参数"}],
            )
        return self._resolve_local_path(value)

    def _required_string(self, payload: dict[str, Any], field: str) -> str:
        value = str(payload.get(field) or "").strip()
        if not value:
            raise BackendGradingRecordServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": field, "reason": "缺少参数"}],
            )
        return value

    def _resolve_local_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.root / path

    def _repo_error(self, exc: GradingRepositoryError) -> BackendGradingRecordServiceError:
        return BackendGradingRecordServiceError(exc.code, exc.message, exc.errors)

    def _score_summary(self, record: GradingRecord) -> dict[str, Any]:
        return {
            "earnedScore": record.earnedScore,
            "totalScore": record.totalScore,
            "coveredScore": record.coveredScore,
            "missingScore": record.missingScore,
            "coverageRatio": record.coverageRatio,
        }
