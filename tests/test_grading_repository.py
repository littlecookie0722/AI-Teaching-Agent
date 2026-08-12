from pathlib import Path

from backend.grading_repository import (
    DEFAULT_MAX_ATTEMPTS,
    GradingSQLiteRepository,
    sync_grading_repository_from_store,
)
from backend.grading_worker import GradingWorkerError, drain_grading_jobs_once, run_next_grading_job_once
from cli.grading_job import GradingJob, GradingJobStatus
from cli.grading_record import GradingRecord, GradingRecordStatus
from cli.store import JsonTaskStore


def test_grading_sqlite_repository_round_trips_jobs_and_records(tmp_path):
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    init_summary = repository.initialize_schema()
    repository.initialize_schema()
    job = GradingJob(
        id="grading_job_repo_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath="examples/output/grading-job-evidence-auto.json",
        submissionId="submission_repo_001",
        taskId="task_repo_001",
        candidateId="candidate_repo_001",
        reviewer="teacher_1",
        status=GradingJobStatus.WAITING_REVIEW,
        summary={"earnedScore": 80, "totalScore": 100},
        safety={"localStagingJob": True, "databaseWritten": True},
        claimOwner="worker_a",
        claimedAt="2026-06-22T00:00:00Z",
        claimExpiresAt="2026-06-22T00:05:00Z",
        attemptCount=2,
    )
    record = GradingRecord(
        id="grading_record_repo_001",
        submissionId="submission_repo_001",
        gradingId="grading_mixed",
        reportPath="examples/output/grading-job-evidence-auto.json",
        reportMode="GRADING_EVIDENCE_AUTO_REPORT",
        status=GradingRecordStatus.READY_FOR_HUMAN_REVIEW,
        totalScore=100,
        earnedScore=80,
        coveredScore=100,
        missingScore=0,
        coverageRatio=1.0,
        taskId="task_repo_001",
        candidateId="candidate_repo_001",
        reviewer="teacher_1",
        evidenceSummary={"checkTotal": 3, "missingCheckIds": []},
        safety={"derivedFromExistingReport": True, "databaseWritten": True},
    )

    repository.save_grading_job(job)
    repository.save_grading_record(record)
    loaded_job = repository.get_grading_job(job.id)
    loaded_record = repository.get_grading_record(record.id)
    summary = repository.summary()

    assert init_summary["safety"]["localSqliteOnly"] is True
    assert init_summary["safety"]["productionDatabaseWritten"] is False
    assert loaded_job is not None
    assert loaded_job.id == job.id
    assert loaded_job.status == GradingJobStatus.WAITING_REVIEW
    assert loaded_job.summary["earnedScore"] == 80
    assert loaded_job.claimOwner == "worker_a"
    assert loaded_job.claimedAt == "2026-06-22T00:00:00Z"
    assert loaded_job.claimExpiresAt == "2026-06-22T00:05:00Z"
    assert loaded_job.attemptCount == 2
    assert loaded_record is not None
    assert loaded_record.id == record.id
    assert loaded_record.status == GradingRecordStatus.READY_FOR_HUMAN_REVIEW
    assert loaded_record.evidenceSummary["checkTotal"] == 3
    assert [item.id for item in repository.list_grading_jobs(task_id="task_repo_001")] == [job.id]
    assert [item.id for item in repository.list_grading_records(submission_id="submission_repo_001")] == [record.id]
    assert summary["jobTotal"] == 1
    assert summary["recordTotal"] == 1
    assert summary["jobsByStatus"] == {"WAITING_REVIEW": 1}
    assert summary["recordsByStatus"] == {"READY_FOR_HUMAN_REVIEW": 1}


def test_sync_grading_repository_from_json_store(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    job = GradingJob(
        id="grading_job_sync_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath="examples/output/grading-job-evidence-auto.json",
        submissionId="submission_sync_001",
        taskId="task_sync_001",
        status=GradingJobStatus.QUEUED,
    )
    record = GradingRecord(
        id="grading_record_sync_001",
        submissionId="submission_sync_001",
        gradingId=None,
        reportPath="examples/output/grading-job-evidence-auto.json",
        reportMode="GRADING_EVIDENCE_AUTO_REPORT",
        status=GradingRecordStatus.NEEDS_EVIDENCE,
        totalScore=100,
        earnedScore=50,
        coveredScore=50,
        missingScore=50,
        coverageRatio=0.5,
        taskId="task_sync_001",
    )
    store.save_grading_job(job)
    store.save_grading_record(record)

    result = sync_grading_repository_from_store(repository=repository, store=store)

    assert result["jobsSynced"] == 1
    assert result["recordsSynced"] == 1
    assert result["safety"]["localSqliteOnly"] is True
    assert result["safety"]["productionDatabaseWritten"] is False
    assert repository.get_grading_job(job.id).submissionId == "submission_sync_001"
    assert repository.get_grading_record(record.id).earnedScore == 50


def test_claim_next_runnable_grading_job_marks_running_and_prevents_duplicate_claim(tmp_path):
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    job = GradingJob(
        id="grading_job_claim_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath="examples/output/grading-job-evidence-auto.json",
        submissionId="submission_claim_001",
        taskId="task_claim_001",
        status=GradingJobStatus.QUEUED,
    )
    repository.save_grading_job(job)

    claimed = repository.claim_next_runnable_grading_job(actor="worker_a", lease_seconds=60)
    duplicate = repository.claim_next_runnable_grading_job(actor="worker_b", job_id=job.id, lease_seconds=60)
    loaded = repository.get_grading_job(job.id)
    summary = repository.summary()

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == GradingJobStatus.RUNNING
    assert claimed.claimOwner == "worker_a"
    assert claimed.claimedAt
    assert claimed.claimExpiresAt
    assert claimed.attemptCount == 1
    assert claimed.safety["claimLeaseActive"] is True
    assert claimed.safety["claimBeforeStatus"] == "QUEUED"
    assert duplicate is None
    assert loaded.status == GradingJobStatus.RUNNING
    assert loaded.claimOwner == "worker_a"
    assert loaded.attemptCount == 1
    assert summary["jobsByStatus"] == {"RUNNING": 1}
    assert summary["safety"]["claimLeaseEnabled"] is True


def test_recover_expired_grading_job_claim_requeues_before_retry_limit(tmp_path):
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    job = GradingJob(
        id="grading_job_expired_requeue_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath="examples/output/grading-job-evidence-auto.json",
        submissionId="submission_expired_requeue_001",
        taskId="task_expired_requeue_001",
        status=GradingJobStatus.RUNNING,
        claimOwner="worker_old",
        claimedAt="2000-01-01T00:00:00Z",
        claimExpiresAt="2000-01-01T00:05:00Z",
        attemptCount=1,
        safety={"claimLeaseActive": True},
    )
    repository.save_grading_job(job)

    recovery = repository.recover_expired_grading_job_claims(max_attempts=DEFAULT_MAX_ATTEMPTS)
    loaded = repository.get_grading_job(job.id)

    assert recovery["expiredClaimTotal"] == 1
    assert recovery["requeuedTotal"] == 1
    assert recovery["failedTotal"] == 0
    assert recovery["requeuedJobIds"] == [job.id]
    assert loaded.status == GradingJobStatus.QUEUED
    assert loaded.claimOwner is None
    assert loaded.claimedAt is None
    assert loaded.claimExpiresAt is None
    assert loaded.attemptCount == 1
    assert loaded.errorCode is None
    assert loaded.safety["expiredClaimRecovered"] is True
    assert loaded.safety["expiredClaimRecoveryAction"] == "REQUEUED"


def test_recover_expired_grading_job_claim_fails_at_retry_limit(tmp_path):
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    job = GradingJob(
        id="grading_job_expired_failed_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath="examples/output/grading-job-evidence-auto.json",
        submissionId="submission_expired_failed_001",
        taskId="task_expired_failed_001",
        status=GradingJobStatus.RUNNING,
        claimOwner="worker_old",
        claimedAt="2000-01-01T00:00:00Z",
        claimExpiresAt="2000-01-01T00:05:00Z",
        attemptCount=3,
        safety={"claimLeaseActive": True},
    )
    repository.save_grading_job(job)

    recovery = repository.recover_expired_grading_job_claims(max_attempts=3)
    loaded = repository.get_grading_job(job.id)

    assert recovery["expiredClaimTotal"] == 1
    assert recovery["requeuedTotal"] == 0
    assert recovery["failedTotal"] == 1
    assert recovery["failedJobIds"] == [job.id]
    assert loaded.status == GradingJobStatus.FAILED
    assert loaded.claimOwner is None
    assert loaded.claimExpiresAt is None
    assert loaded.errorCode == "GRADING_JOB_RETRY_LIMIT_EXCEEDED"
    assert loaded.finishedAt
    assert loaded.safety["expiredClaimRecoveryAction"] == "FAILED_MAX_ATTEMPTS"


def test_claim_next_runnable_grading_job_skips_retry_limit_jobs(tmp_path):
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    job = GradingJob(
        id="grading_job_retry_limit_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath="examples/output/grading-job-evidence-auto.json",
        submissionId="submission_retry_limit_001",
        taskId="task_retry_limit_001",
        status=GradingJobStatus.FAILED,
        attemptCount=3,
        errorCode="SCHEMA_VALIDATION_ERROR",
        errorMessage="previous failure",
        errors=[{"field": "grading", "reason": "previous failure"}],
    )
    repository.save_grading_job(job)

    claimed = repository.claim_next_runnable_grading_job(actor="worker_a", job_id=job.id, max_attempts=3)
    loaded = repository.get_grading_job(job.id)

    assert claimed is None
    assert loaded.status == GradingJobStatus.FAILED
    assert loaded.attemptCount == 3
    assert loaded.errorCode == "SCHEMA_VALIDATION_ERROR"


def test_grading_worker_run_once_executes_next_sqlite_job_and_mirrors_to_store(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    output = tmp_path / "worker-evidence-auto.json"
    job = GradingJob(
        id="grading_job_worker_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath=str(output),
        submissionId="submission_worker_001",
        taskId="task_worker_001",
        status=GradingJobStatus.QUEUED,
    )
    repository.save_grading_job(job)

    result = run_next_grading_job_once(
        repository=repository,
        store=store,
        root=Path.cwd(),
        trace_id="trace_worker_001",
    )
    loaded_job = repository.get_grading_job(job.id)
    loaded_record = repository.get_grading_record(result["gradingRecord"]["id"])
    mirrored_job = store.get_grading_job(job.id)
    mirrored_record = store.get_grading_record(result["gradingRecord"]["id"])

    assert result["workerRun"]["status"] == "COMPLETED"
    assert result["workerRun"]["jobId"] == job.id
    assert result["workerRun"]["beforeStatus"] == "QUEUED"
    assert result["workerRun"]["claimOwner"] == "local-grading-worker"
    assert result["workerRun"]["attemptCount"] == 1
    assert result["workerRun"]["maxAttempts"] == DEFAULT_MAX_ATTEMPTS
    assert result["claimRecovery"]["expiredClaimTotal"] == 0
    assert result["safety"]["workerStarted"] is True
    assert result["safety"]["claimLeaseUsed"] is True
    assert result["safety"]["expiredClaimRecoveryEnabled"] is True
    assert result["safety"]["productionQueueUsed"] is False
    assert result["safety"]["productionDatabaseWritten"] is False
    assert loaded_job.status == GradingJobStatus.WAITING_REVIEW
    assert loaded_job.claimOwner == "local-grading-worker"
    assert loaded_job.attemptCount == 1
    assert loaded_job.gradingRecordId == loaded_record.id
    assert loaded_record.status == GradingRecordStatus.NEEDS_EVIDENCE
    assert mirrored_job.status == GradingJobStatus.WAITING_REVIEW
    assert mirrored_record.id == loaded_record.id
    assert output.exists()

    second_result = run_next_grading_job_once(
        repository=repository,
        store=store,
        root=Path.cwd(),
        trace_id="trace_worker_002",
    )
    assert second_result["workerRun"]["status"] == "NOOP"
    assert second_result["workerRun"]["jobFound"] is False
    assert second_result["claimRecovery"]["expiredClaimTotal"] == 0


def test_grading_worker_recovers_expired_claim_before_running_job(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    output = tmp_path / "worker-recovered-evidence-auto.json"
    job = GradingJob(
        id="grading_job_worker_recover_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath=str(output),
        submissionId="submission_worker_recover_001",
        taskId="task_worker_recover_001",
        status=GradingJobStatus.RUNNING,
        claimOwner="worker_old",
        claimedAt="2000-01-01T00:00:00Z",
        claimExpiresAt="2000-01-01T00:05:00Z",
        attemptCount=1,
    )
    repository.save_grading_job(job)

    result = run_next_grading_job_once(
        repository=repository,
        store=store,
        root=Path.cwd(),
        trace_id="trace_worker_recover_001",
        actor="worker_new",
        max_attempts=3,
    )
    loaded = repository.get_grading_job(job.id)

    assert result["claimRecovery"]["expiredClaimTotal"] == 1
    assert result["claimRecovery"]["requeuedTotal"] == 1
    assert result["workerRun"]["status"] == "COMPLETED"
    assert result["workerRun"]["beforeStatus"] == "QUEUED"
    assert result["workerRun"]["claimOwner"] == "worker_new"
    assert result["workerRun"]["attemptCount"] == 2
    assert loaded.status == GradingJobStatus.WAITING_REVIEW
    assert loaded.attemptCount == 2
    assert loaded.claimOwner == "worker_new"
    assert output.exists()


def test_grading_worker_rejects_explicit_job_at_retry_limit(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    job = GradingJob(
        id="grading_job_worker_retry_limit_001",
        gradingPath="templates/grading/examples/mixed-checks.yaml",
        submissionPath="examples/submissions/readonly-demo",
        outputPath="examples/output/grading-job-evidence-auto.json",
        submissionId="submission_worker_retry_limit_001",
        taskId="task_worker_retry_limit_001",
        status=GradingJobStatus.FAILED,
        attemptCount=3,
    )
    repository.save_grading_job(job)

    try:
        run_next_grading_job_once(
            repository=repository,
            store=store,
            root=Path.cwd(),
            trace_id="trace_worker_retry_limit_001",
            job_id=job.id,
            max_attempts=3,
        )
    except GradingWorkerError as exc:
        assert exc.code == "GRADING_JOB_RETRY_LIMIT_EXCEEDED"
        assert exc.errors[0]["field"] == "attemptCount"
    else:
        raise AssertionError("expected retry limit error")


def test_grading_worker_run_once_noop_when_no_runnable_job(tmp_path):
    result = run_next_grading_job_once(
        repository=GradingSQLiteRepository(tmp_path / "grading.sqlite3"),
        store=JsonTaskStore(tmp_path / "store.json"),
        root=Path.cwd(),
        trace_id="trace_worker_noop",
    )

    assert result["workerRun"]["status"] == "NOOP"
    assert result["workerRun"]["jobFound"] is False
    assert result["claimRecovery"]["expiredClaimTotal"] == 0
    assert result["safety"]["workerStarted"] is False
    assert result["safety"]["productionDatabaseWritten"] is False


def test_grading_worker_drain_once_executes_until_queue_empty(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    for index in range(2):
        repository.save_grading_job(
            GradingJob(
                id=f"grading_job_worker_drain_{index}",
                gradingPath="templates/grading/examples/mixed-checks.yaml",
                submissionPath="examples/submissions/readonly-demo",
                outputPath=str(tmp_path / f"worker-drain-{index}.json"),
                submissionId=f"submission_worker_drain_{index}",
                taskId="task_worker_drain",
                status=GradingJobStatus.QUEUED,
            )
        )

    result = drain_grading_jobs_once(
        repository=repository,
        store=store,
        root=Path.cwd(),
        trace_id="trace_worker_drain",
        limit=5,
        lease_seconds=120,
        max_attempts=4,
    )

    assert result["workerDrain"]["status"] == "COMPLETED"
    assert result["workerDrain"]["executedTotal"] == 2
    assert result["workerDrain"]["failedTotal"] == 0
    assert result["workerDrain"]["noopReached"] is True
    assert result["workerDrain"]["limit"] == 5
    assert result["workerDrain"]["leaseSeconds"] == 120
    assert result["workerDrain"]["maxAttempts"] == 4
    assert result["workerDrain"]["quota"]["limitReached"] is False
    assert result["workerDrain"]["quota"]["queueMayStillHaveRunnableJobs"] is False
    assert result["workerDrain"]["resourceCleanup"]["cleanupExecuted"] is False
    assert result["workerDrain"]["resourceCleanup"]["retainedReportTotal"] == 2
    assert result["workerDrain"]["resourceCleanup"]["retainedGradingRecordTotal"] == 2
    assert result["operationAuditEvent"]["action"] == "GRADING_WORKER_DRAIN"
    assert result["operationAuditEvent"]["resourceType"] == "GRADING_REPOSITORY"
    assert result["operationAuditEvent"]["detail"]["quota"]["effectiveLimit"] == 5
    assert result["operationAuditEvent"]["detail"]["resourceCleanup"]["productionResourceDeleted"] is False
    assert [item["status"] for item in result["workerRuns"]] == ["COMPLETED", "COMPLETED", "NOOP"]
    assert result["summary"]["jobsByStatus"] == {"WAITING_REVIEW": 2}
    assert result["summary"]["recordsByStatus"] == {"NEEDS_EVIDENCE": 2}
    assert result["safety"]["singleProcessSequentialDrain"] is True
    assert result["safety"]["persistentBackgroundWorker"] is False
    assert result["safety"]["concurrentWorkersStarted"] is False
    assert result["safety"]["productionQueueUsed"] is False


def test_grading_worker_drain_once_respects_limit(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    for index in range(3):
        repository.save_grading_job(
            GradingJob(
                id=f"grading_job_worker_drain_limited_{index}",
                gradingPath="templates/grading/examples/mixed-checks.yaml",
                submissionPath="examples/submissions/readonly-demo",
                outputPath=str(tmp_path / f"worker-drain-limited-{index}.json"),
                submissionId=f"submission_worker_drain_limited_{index}",
                taskId="task_worker_drain_limited",
                status=GradingJobStatus.QUEUED,
            )
        )

    result = drain_grading_jobs_once(
        repository=repository,
        store=store,
        root=Path.cwd(),
        trace_id="trace_worker_drain_limited",
        limit=2,
    )

    assert result["workerDrain"]["status"] == "COMPLETED"
    assert result["workerDrain"]["executedTotal"] == 2
    assert result["workerDrain"]["noopReached"] is False
    assert result["workerDrain"]["quota"]["limitReached"] is True
    assert result["workerDrain"]["quota"]["queueMayStillHaveRunnableJobs"] is True
    assert result["workerDrain"]["resourceCleanup"]["retainedReportTotal"] == 2
    assert len(result["workerRuns"]) == 2
    assert result["summary"]["jobsByStatus"] == {"QUEUED": 1, "WAITING_REVIEW": 2}
