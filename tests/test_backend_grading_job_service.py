from pathlib import Path

from backend.grading_job_service import (
    BackendGradingJobService,
    BackendGradingJobServiceError,
    GradingRepositoryPolicy,
)
from backend.grading_repository import GradingSQLiteRepository
from cli.ai_task import create_waiting_review_task
from cli.store import JsonTaskStore


def _service(*, store_path: Path, root: Path, repository=None, policy=None) -> BackendGradingJobService:
    return BackendGradingJobService(
        root=root,
        store=JsonTaskStore(store_path),
        repository=repository,
        repository_policy=policy or GradingRepositoryPolicy("JSON_STORE", False),
    )


def test_backend_grading_job_service_creates_json_store_job(tmp_path):
    service = _service(store_path=tmp_path / "store.json", root=Path.cwd())

    result = service.create_job(
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(tmp_path / "service-evidence-auto.json"),
            "submissionId": "submission_service_001",
            "reviewer": "teacher_1",
        },
        trace_id="trace_service_create",
    )

    job = result["gradingJob"]
    audit = result["operationAuditEvent"]
    stored = JsonTaskStore(tmp_path / "store.json").get_grading_job(job.id)

    assert job.status.value == "QUEUED"
    assert job.submissionId == "submission_service_001"
    assert audit.action.value == "GRADING_JOB_CREATE"
    assert audit.detail["component"] == "BackendGradingJobService"
    assert result["mode"] == "LOCAL_GRADING_JOB"
    assert result["localSqliteWritten"] is False
    assert stored.id == job.id


def test_backend_grading_job_service_runs_json_store_job_and_writes_report_artifact(tmp_path):
    store_path = tmp_path / "store.json"
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Service grading task",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
    )
    store.save(task)
    service = _service(store_path=store_path, root=Path.cwd())

    result = service.run_job(
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(tmp_path / "service-run-evidence-auto.json"),
            "submissionId": "submission_service_run_001",
            "taskId": task.id,
            "candidateId": "candidate_service_001",
            "reviewer": "teacher_1",
        },
        trace_id="trace_service_run",
    )

    job = result["gradingJob"]
    record = result["gradingRecord"]
    artifact = result["artifact"]
    store = JsonTaskStore(store_path)

    assert job["status"] == "WAITING_REVIEW"
    assert record["submissionId"] == "submission_service_run_001"
    assert result["operationAuditEvent"]["action"] == "GRADING_JOB_RUN"
    assert artifact["kind"] == "GRADING_REPORT"
    assert artifact["metadata"]["submissionId"] == "submission_service_run_001"
    assert Path(job["reportPath"]).exists()
    assert store.get_grading_job(job["id"]).status.value == "WAITING_REVIEW"
    assert store.get_grading_record(record["id"]).id == record["id"]
    assert store.get_artifact(artifact["id"]).id == artifact["id"]


def test_backend_grading_job_service_creates_and_runs_sqlite_job(tmp_path):
    store_path = tmp_path / "store.json"
    repository = GradingSQLiteRepository(tmp_path / "grading.sqlite3")
    service = _service(
        store_path=store_path,
        root=Path.cwd(),
        repository=repository,
        policy=GradingRepositoryPolicy("REQUEST_DB_PATH", False),
    )

    created = service.create_job(
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(tmp_path / "service-sqlite-evidence-auto.json"),
            "submissionId": "submission_service_sqlite_001",
            "reviewer": "teacher_1",
        },
        trace_id="trace_service_sqlite_create",
    )
    run = service.run_job(
        {"id": created["gradingJob"].id, "reviewer": "teacher_1", "leaseSeconds": 120, "maxAttempts": 5},
        trace_id="trace_service_sqlite_run",
    )

    assert created["mode"] == "LOCAL_SQLITE_GRADING_JOB"
    assert created["localSqliteWritten"] is True
    assert repository.get_grading_job(created["gradingJob"].id).id == created["gradingJob"].id
    assert run["mode"] == "LOCAL_SQLITE_GRADING_WORKER_ONCE"
    assert run["workerRun"]["status"] == "COMPLETED"
    assert run["workerRun"]["leaseSeconds"] == 120
    assert run["workerRun"]["maxAttempts"] == 5
    assert run["gradingJob"]["status"] == "WAITING_REVIEW"
    assert repository.get_grading_record(run["gradingRecord"]["id"]).id == run["gradingRecord"]["id"]


def test_backend_grading_job_service_validates_required_fields(tmp_path):
    service = _service(store_path=tmp_path / "store.json", root=Path.cwd())

    try:
        service.create_job(
            {
                "grading": "templates/grading/examples/mixed-checks.yaml",
                "submission": "examples/submissions/readonly-demo",
                "output": str(tmp_path / "missing-submission-id.json"),
            },
            trace_id="trace_service_validation",
        )
    except BackendGradingJobServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "submissionId"
    else:
        raise AssertionError("expected BackendGradingJobServiceError")
