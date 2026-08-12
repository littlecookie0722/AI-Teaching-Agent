import json
from pathlib import Path

from backend.grading_job_service import GradingRepositoryPolicy
from backend.grading_record_service import BackendGradingRecordService, BackendGradingRecordServiceError
from backend.grading_repository import GradingSQLiteRepository
from cli.ai_task import create_waiting_review_task
from cli.store import JsonTaskStore


def _service(*, store_path: Path, root: Path, repository=None, policy=None) -> BackendGradingRecordService:
    return BackendGradingRecordService(
        root=root,
        store=JsonTaskStore(store_path),
        repository=repository,
        repository_policy=policy or GradingRepositoryPolicy("JSON_STORE", False),
    )


def _write_report(path: Path) -> Path:
    payload = {
        "id": "grading_report_service_001",
        "mode": "GRADING_EVIDENCE_AUTO",
        "gradingId": "grading_service_001",
        "scorePreview": {
            "status": "NEEDS_CONTROLLED_COMMAND_EVIDENCE",
            "totalScore": 100,
            "earnedScore": 40,
            "coveredScore": 50,
            "missingScore": 50,
            "coverageRatio": 0.5,
            "missingEvidenceTotal": 2,
            "missingCheckIds": ["check_stdout_accuracy", "check_pytest"],
        },
        "manualReviewChecklist": {
            "status": "NEEDS_CONTROLLED_COMMAND_EVIDENCE",
            "decisionNoteRecommendation": {"decision": "needs-evidence"},
        },
        "evidenceCoverage": {
            "coveredScore": 50,
            "coverageRatio": 0.5,
            "readonlyStatic": {"passed": 2},
            "controlledDocker": {"missing": 2},
        },
        "summary": {
            "checkTotal": 6,
            "executed": 4,
            "passedCheckTotal": 2,
            "failedCheckTotal": 2,
            "deferredCheckTotal": 2,
            "manualReviewChecklistStatus": "NEEDS_CONTROLLED_COMMAND_EVIDENCE",
        },
        "safety": {
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_backend_grading_record_service_creates_json_store_record(tmp_path):
    store_path = tmp_path / "store.json"
    report_path = _write_report(tmp_path / "record-service-report.json")
    service = _service(store_path=store_path, root=Path.cwd())

    result = service.create_record(
        {
            "report": str(report_path),
            "submissionId": "submission_record_service_001",
            "candidateId": "candidate_record_service_001",
            "reviewer": "teacher_1",
        },
        trace_id="trace_record_service_create",
    )

    record = result["gradingRecord"]
    audit = result["operationAuditEvent"]
    stored = JsonTaskStore(store_path).get_grading_record(record.id)

    assert record.status.value == "NEEDS_EVIDENCE"
    assert record.submissionId == "submission_record_service_001"
    assert record.earnedScore == 40
    assert record.totalScore == 100
    assert record.coverageRatio == 0.5
    assert record.safety["derivedFromExistingReport"] is True
    assert record.safety["recordCreatesNewExecution"] is False
    assert result["mode"] == "LOCAL_GRADING_RECORD"
    assert result["localSqliteWritten"] is False
    assert audit.action.value == "GRADING_RECORD_CREATE"
    assert audit.detail["component"] == "BackendGradingRecordService"
    assert stored.id == record.id


def test_backend_grading_record_service_reviews_record_without_task_transition(tmp_path):
    store_path = tmp_path / "store.json"
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Service grading record review",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
    )
    store.save(task)
    report_path = _write_report(tmp_path / "record-service-review-report.json")
    service = _service(store_path=store_path, root=Path.cwd())
    created = service.create_record(
        {
            "report": str(report_path),
            "submissionId": "submission_record_review_001",
            "taskId": task.id,
        },
        trace_id="trace_record_service_review_create",
    )

    reviewed = service.review_record(
        created["gradingRecord"].id,
        {"reviewer": "teacher_1", "decision": "approve-ready"},
        trace_id="trace_record_service_review",
    )

    record = reviewed["gradingRecord"]
    audit = reviewed["operationAuditEvent"]
    store = JsonTaskStore(store_path)

    assert record.status.value == "HUMAN_APPROVED"
    assert record.reviewDecision == "approve-ready"
    assert record.reviewedBy == "teacher_1"
    assert reviewed["taskStatusChanged"] is False
    assert audit.action.value == "GRADING_RECORD_REVIEW"
    assert audit.detail["taskStatusChanged"] is False
    assert store.get(task.id).status.value == "WAITING_REVIEW"
    assert store.get_grading_record(record.id).status.value == "HUMAN_APPROVED"


def test_backend_grading_record_service_creates_and_reviews_sqlite_record(tmp_path):
    store_path = tmp_path / "store.json"
    repository = GradingSQLiteRepository(tmp_path / "grading-record.sqlite3")
    service = _service(
        store_path=store_path,
        root=Path.cwd(),
        repository=repository,
        policy=GradingRepositoryPolicy("REQUEST_DB_PATH", False),
    )
    created = service.create_record(
        {
            "report": str(_write_report(tmp_path / "record-service-sqlite-report.json")),
            "submissionId": "submission_record_sqlite_001",
            "reviewer": "teacher_1",
        },
        trace_id="trace_record_service_sqlite_create",
    )
    reviewed = service.review_record(
        created["gradingRecord"].id,
        {
            "reviewer": "teacher_1",
            "decision": "needs-evidence",
            "reason": "等待 controlled command evidence",
        },
        trace_id="trace_record_service_sqlite_review",
    )

    record = reviewed["gradingRecord"]

    assert created["mode"] == "LOCAL_SQLITE_GRADING_RECORD"
    assert created["localSqliteWritten"] is True
    assert reviewed["mode"] == "LOCAL_SQLITE_GRADING_RECORD_REVIEW"
    assert record.status.value == "NEEDS_EVIDENCE"
    assert repository.get_grading_record(record.id).reviewReason == "等待 controlled command evidence"
    assert JsonTaskStore(store_path).get_grading_record(record.id).reviewReason == "等待 controlled command evidence"


def test_backend_grading_record_service_requires_reason_for_needs_revision(tmp_path):
    service = _service(store_path=tmp_path / "store.json", root=Path.cwd())
    created = service.create_record(
        {
            "report": str(_write_report(tmp_path / "record-service-invalid-review-report.json")),
            "submissionId": "submission_record_invalid_001",
        },
        trace_id="trace_record_service_invalid_create",
    )

    try:
        service.review_record(
            created["gradingRecord"].id,
            {"reviewer": "teacher_1", "decision": "needs-revision"},
            trace_id="trace_record_service_invalid_review",
        )
    except BackendGradingRecordServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "reason", "reason": "该复核决策必须填写原因"}]
    else:
        raise AssertionError("expected BackendGradingRecordServiceError")
