"""Single-run local grading worker backed by the SQLite grading repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.grading_job import GradingJobError, GradingJobStatus, run_grading_job
from cli.store import JsonTaskStore

from .grading_repository import (
    DEFAULT_CLAIM_LEASE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    GradingRepositoryError,
    GradingSQLiteRepository,
)

DEFAULT_WORKER_DRAIN_LIMIT = 5
MAX_WORKER_DRAIN_LIMIT = 20


class GradingWorkerError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def run_next_grading_job_once(
    *,
    repository: GradingSQLiteRepository,
    store: JsonTaskStore,
    root: Path,
    trace_id: str,
    actor: str = "local-grading-worker",
    job_id: str | None = None,
    lease_seconds: int = DEFAULT_CLAIM_LEASE_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    lease_seconds = _positive_int(lease_seconds, DEFAULT_CLAIM_LEASE_SECONDS)
    max_attempts = _positive_int(max_attempts, DEFAULT_MAX_ATTEMPTS)
    try:
        repository.initialize_schema()
        claim_recovery = repository.recover_expired_grading_job_claims(max_attempts=max_attempts)
        job = repository.claim_next_runnable_grading_job(
            actor=actor,
            job_id=job_id,
            lease_seconds=lease_seconds,
            max_attempts=max_attempts,
        )
    except GradingRepositoryError as exc:
        raise GradingWorkerError(exc.code, exc.message, exc.errors) from exc
    if job is None:
        if job_id:
            try:
                existing_job = repository.get_grading_job(job_id)
            except GradingRepositoryError as exc:
                raise GradingWorkerError(exc.code, exc.message, exc.errors) from exc
            if existing_job is not None and existing_job.status not in {GradingJobStatus.QUEUED, GradingJobStatus.FAILED}:
                raise GradingWorkerError(
                    "STATE_TRANSITION_ERROR",
                    "Grading 评分任务状态非法流转",
                    [{"field": "status", "reason": f"cannot claim from {existing_job.status.value}"}],
                )
            if existing_job is not None and int(existing_job.attemptCount or 0) >= int(max_attempts):
                raise GradingWorkerError(
                    "GRADING_JOB_RETRY_LIMIT_EXCEEDED",
                    "Grading 评分任务重试次数已达上限",
                    [{"field": "attemptCount", "reason": f"max attempts {max_attempts} reached"}],
                )
        return {
            "workerRun": {
                "status": "NOOP",
                "jobFound": False,
                "jobId": job_id,
                "leaseSeconds": lease_seconds,
                "maxAttempts": max_attempts,
                "message": "没有可执行的本地 SQLite GradingJob",
            },
            "claimRecovery": claim_recovery,
            "summary": repository.summary(),
            "mode": "LOCAL_SQLITE_GRADING_WORKER_ONCE",
            "safety": _worker_safety(
                job_executed=False,
                record_created=False,
                worker_started=False,
                max_attempts=max_attempts,
            ),
        }
    if job.status is not GradingJobStatus.RUNNING:
        raise GradingWorkerError(
            "STATE_TRANSITION_ERROR",
            "Grading 评分任务状态非法流转",
            [{"field": "status", "reason": f"cannot run after claim from {job.status.value}"}],
        )

    before_status = str(job.safety.get("claimBeforeStatus") or GradingJobStatus.QUEUED.value)
    try:
        job, report, record = run_grading_job(job, root=root)
    except GradingJobError as exc:
        try:
            repository.save_grading_job(job)
        except GradingRepositoryError as repo_exc:
            raise GradingWorkerError(repo_exc.code, repo_exc.message, repo_exc.errors) from repo_exc
        store.save_grading_job(job)
        audit_event = _save_worker_audit(
            store=store,
            actor=actor,
            trace_id=trace_id,
            job_id=job.id,
            before_status=before_status,
            after_status=job.status.value,
            detail={
                "component": "GradingSQLiteWorkerRunOnce",
                "jobId": job.id,
                "dbPath": str(repository.db_path),
                "errorCode": exc.code,
                "errors": exc.errors,
                "recordCreated": False,
                "claimOwner": job.claimOwner,
                "claimedAt": job.claimedAt,
                "claimExpiresAt": job.claimExpiresAt,
                "attemptCount": job.attemptCount,
                "maxAttempts": max_attempts,
                "claimRecovery": claim_recovery,
                "workerStarted": True,
                "queuePersistedToProduction": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        )
        raise GradingWorkerError(
            exc.code,
            exc.message,
            exc.errors + [{"field": "operationAuditEventId", "reason": audit_event["id"]}],
        ) from exc

    try:
        repository.save_grading_job(job)
        repository.save_grading_record(record)
    except GradingRepositoryError as exc:
        raise GradingWorkerError(exc.code, exc.message, exc.errors) from exc
    store.save_grading_job(job)
    store.save_grading_record(record)
    audit_event = _save_worker_audit(
        store=store,
        actor=actor,
        trace_id=trace_id,
        job_id=job.id,
        before_status=before_status,
        after_status=job.status.value,
        detail={
            "component": "GradingSQLiteWorkerRunOnce",
            "jobId": job.id,
            "dbPath": str(repository.db_path),
            "submissionId": job.submissionId,
            "taskId": job.taskId,
            "candidateId": job.candidateId,
            "reportId": job.reportId,
            "reportPath": job.reportPath,
            "gradingRecordId": record.id,
            "summary": job.summary,
            "claimOwner": job.claimOwner,
            "claimedAt": job.claimedAt,
            "claimExpiresAt": job.claimExpiresAt,
            "attemptCount": job.attemptCount,
            "maxAttempts": max_attempts,
            "claimRecovery": claim_recovery,
            "workerStarted": True,
            "queuePersistedToProduction": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    )
    return {
        "workerRun": {
            "status": "COMPLETED",
            "jobFound": True,
            "jobId": job.id,
            "beforeStatus": before_status,
            "afterStatus": job.status.value,
            "claimOwner": job.claimOwner,
            "claimedAt": job.claimedAt,
            "claimExpiresAt": job.claimExpiresAt,
            "attemptCount": job.attemptCount,
            "leaseSeconds": lease_seconds,
            "maxAttempts": max_attempts,
            "gradingRecordId": record.id,
            "reportPath": job.reportPath,
        },
        "claimRecovery": claim_recovery,
        "gradingJob": job.to_dict(),
        "gradingRecord": record.to_dict(),
        "report": report,
        "operationAuditEvent": audit_event,
        "summary": repository.summary(),
        "mode": "LOCAL_SQLITE_GRADING_WORKER_ONCE",
        "safety": _worker_safety(
            job_executed=True,
            record_created=True,
            worker_started=True,
            claim_lease_used=True,
            max_attempts=max_attempts,
            sandbox_executed=bool(job.safety.get("sandboxExecuted")),
            contestant_code_executed=bool(job.safety.get("contestantCodeExecuted")),
        ),
    }


def drain_grading_jobs_once(
    *,
    repository: GradingSQLiteRepository,
    store: JsonTaskStore,
    root: Path,
    trace_id: str,
    actor: str = "local-grading-worker",
    limit: int = DEFAULT_WORKER_DRAIN_LIMIT,
    lease_seconds: int = DEFAULT_CLAIM_LEASE_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    requested_limit = _positive_int(limit, DEFAULT_WORKER_DRAIN_LIMIT)
    effective_limit = min(requested_limit, MAX_WORKER_DRAIN_LIMIT)
    lease_seconds = _positive_int(lease_seconds, DEFAULT_CLAIM_LEASE_SECONDS)
    max_attempts = _positive_int(max_attempts, DEFAULT_MAX_ATTEMPTS)
    worker_runs: list[dict[str, Any]] = []
    executed_total = 0
    failed_total = 0
    noop_reached = False
    stopped_on_error = False
    retained_report_paths: list[str] = []
    retained_record_ids: list[str] = []

    for index in range(effective_limit):
        try:
            result = run_next_grading_job_once(
                repository=repository,
                store=store,
                root=root,
                trace_id=trace_id,
                actor=actor,
                lease_seconds=lease_seconds,
                max_attempts=max_attempts,
            )
        except GradingWorkerError as exc:
            failed_total += 1
            stopped_on_error = True
            worker_runs.append(
                {
                    "index": index,
                    "status": "FAILED",
                    "code": exc.code,
                    "message": exc.message,
                    "errors": exc.errors,
                }
            )
            break

        worker_run = result.get("workerRun", {})
        compact_run = {
            "index": index,
            "status": worker_run.get("status"),
            "jobFound": bool(worker_run.get("jobFound")),
            "jobId": worker_run.get("jobId"),
            "beforeStatus": worker_run.get("beforeStatus"),
            "afterStatus": worker_run.get("afterStatus"),
            "claimOwner": worker_run.get("claimOwner"),
            "attemptCount": worker_run.get("attemptCount"),
            "leaseSeconds": worker_run.get("leaseSeconds"),
            "maxAttempts": worker_run.get("maxAttempts"),
            "gradingRecordId": worker_run.get("gradingRecordId"),
            "reportPath": worker_run.get("reportPath"),
            "claimRecovery": result.get("claimRecovery"),
        }
        worker_runs.append(compact_run)
        if worker_run.get("status") == "NOOP":
            noop_reached = True
            break
        if worker_run.get("status") == "COMPLETED":
            executed_total += 1
            if worker_run.get("reportPath"):
                retained_report_paths.append(str(worker_run["reportPath"]))
            if worker_run.get("gradingRecordId"):
                retained_record_ids.append(str(worker_run["gradingRecordId"]))

    status = "COMPLETED"
    if stopped_on_error:
        status = "PARTIAL_FAILED" if executed_total else "FAILED"
    elif noop_reached and executed_total == 0:
        status = "NOOP"
    quota = _worker_drain_quota(
        requested_limit=requested_limit,
        effective_limit=effective_limit,
        executed_total=executed_total,
        failed_total=failed_total,
        noop_reached=noop_reached,
        stopped_on_error=stopped_on_error,
    )
    resource_cleanup = _worker_drain_resource_cleanup(
        report_paths=retained_report_paths,
        record_ids=retained_record_ids,
        executed_total=executed_total,
    )
    summary = repository.summary()
    operation_audit_event = _save_worker_drain_audit(
        store=store,
        actor=actor,
        trace_id=trace_id,
        repository=repository,
        status=status,
        quota=quota,
        resource_cleanup=resource_cleanup,
        executed_total=executed_total,
        failed_total=failed_total,
        noop_reached=noop_reached,
        stopped_on_error=stopped_on_error,
        summary=summary,
    )

    return {
        "workerDrain": {
            "status": status,
            "requestedLimit": requested_limit,
            "limit": effective_limit,
            "maxLimit": MAX_WORKER_DRAIN_LIMIT,
            "executedTotal": executed_total,
            "failedTotal": failed_total,
            "noopReached": noop_reached,
            "stoppedOnError": stopped_on_error,
            "actor": actor,
            "leaseSeconds": lease_seconds,
            "maxAttempts": max_attempts,
            "quota": quota,
            "resourceCleanup": resource_cleanup,
        },
        "workerRuns": worker_runs,
        "operationAuditEvent": operation_audit_event,
        "summary": summary,
        "mode": "LOCAL_SQLITE_GRADING_WORKER_DRAIN_ONCE",
        "safety": _worker_safety(
            job_executed=executed_total > 0,
            record_created=executed_total > 0,
            worker_started=True,
            claim_lease_used=executed_total > 0,
            max_attempts=max_attempts,
        )
        | {
            "singleProcessSequentialDrain": True,
            "persistentBackgroundWorker": False,
            "concurrentWorkersStarted": False,
            "drainLimit": effective_limit,
            "maxDrainLimit": MAX_WORKER_DRAIN_LIMIT,
            "quotaEnforced": True,
            "resourceCleanupPlanned": True,
        },
    }


def _worker_drain_quota(
    *,
    requested_limit: int,
    effective_limit: int,
    executed_total: int,
    failed_total: int,
    noop_reached: bool,
    stopped_on_error: bool,
) -> dict[str, Any]:
    remaining_slots = max(effective_limit - executed_total - failed_total, 0)
    return {
        "component": "GradingWorkerDrainQuota",
        "requestedLimit": requested_limit,
        "effectiveLimit": effective_limit,
        "maxLimit": MAX_WORKER_DRAIN_LIMIT,
        "executedTotal": executed_total,
        "failedTotal": failed_total,
        "remainingSlots": remaining_slots,
        "limitReached": executed_total + failed_total >= effective_limit and not noop_reached and not stopped_on_error,
        "queueMayStillHaveRunnableJobs": executed_total + failed_total >= effective_limit and not noop_reached,
        "noopReached": noop_reached,
        "stoppedOnError": stopped_on_error,
    }


def _worker_drain_resource_cleanup(
    *,
    report_paths: list[str],
    record_ids: list[str],
    executed_total: int,
) -> dict[str, Any]:
    return {
        "component": "GradingWorkerDrainResourceCleanupPlan",
        "cleanupExecuted": False,
        "manualCleanupRequired": False,
        "retainedReportTotal": len(report_paths),
        "retainedGradingRecordTotal": len(record_ids),
        "retainedReports": report_paths,
        "retainedGradingRecordIds": record_ids,
        "outputRetentionReason": "reports_and_records_wait_for_human_review",
        "temporaryContainerCleanupVerified": False,
        "temporaryContainerCleanupReason": "no_persistent_worker_or_container_manager_in_local_sqlite_staging",
        "persistentWorkerStopped": True,
        "productionResourceDeleted": False,
        "realCloudResourceChanged": False,
        "resourceLeakSuspected": False,
        "executedTotal": executed_total,
    }


def _save_worker_drain_audit(
    *,
    store: JsonTaskStore,
    actor: str,
    trace_id: str,
    repository: GradingSQLiteRepository,
    status: str,
    quota: dict[str, Any],
    resource_cleanup: dict[str, Any],
    executed_total: int,
    failed_total: int,
    noop_reached: bool,
    stopped_on_error: bool,
    summary: dict[str, Any],
) -> dict[str, Any]:
    event = create_operation_audit_event(
        action=OperationAction.GRADING_WORKER_DRAIN,
        resource_type=OperationResourceType.GRADING_REPOSITORY,
        resource_id=str(repository.db_path),
        actor=actor,
        trace_id=trace_id,
        after_state=status,
        detail={
            "component": "GradingSQLiteWorkerDrainOnce",
            "dbPath": str(repository.db_path),
            "status": status,
            "executedTotal": executed_total,
            "failedTotal": failed_total,
            "noopReached": noop_reached,
            "stoppedOnError": stopped_on_error,
            "quota": quota,
            "resourceCleanup": resource_cleanup,
            "summary": summary,
            "singleProcessSequentialDrain": True,
            "persistentBackgroundWorker": False,
            "concurrentWorkersStarted": False,
            "productionQueueUsed": False,
            "productionDatabaseWritten": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    )
    store.save_operation_audit_event(event)
    return event.to_dict()


def _save_worker_audit(
    *,
    store: JsonTaskStore,
    actor: str,
    trace_id: str,
    job_id: str,
    before_status: str,
    after_status: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    event = create_operation_audit_event(
        action=OperationAction.GRADING_JOB_RUN,
        resource_type=OperationResourceType.GRADING_JOB,
        resource_id=job_id,
        actor=actor,
        trace_id=trace_id,
        before_state=before_status,
        after_state=after_status,
        detail=detail,
    )
    store.save_operation_audit_event(event)
    return event.to_dict()


def _positive_int(value: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _worker_safety(
    *,
    job_executed: bool,
    record_created: bool,
    worker_started: bool,
    claim_lease_used: bool = False,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    sandbox_executed: bool = False,
    contestant_code_executed: bool = False,
) -> dict[str, Any]:
    return {
        "localSqliteOnly": True,
        "jobExecuted": job_executed,
        "recordCreated": record_created,
        "workerStarted": worker_started,
        "claimLeaseUsed": claim_lease_used,
        "expiredClaimRecoveryEnabled": True,
        "maxAttempts": max_attempts,
        "persistentBackgroundWorker": False,
        "productionQueueUsed": False,
        "productionDatabaseWritten": False,
        "sandboxExecuted": sandbox_executed,
        "contestantCodeExecuted": contestant_code_executed,
        "autoApproveAllowed": False,
        "realPublish": False,
    }
