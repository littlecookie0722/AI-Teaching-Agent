from backend.core_contract import create_backend_core_sqlite_repository
from backend.core_task_service import (
    BackendCoreTaskService,
    BackendCoreTaskServiceError,
    CoreArtifactInput,
    backend_core_task_service_error_response,
)
from cli.artifact import ArtifactKind


def test_backend_core_task_service_creates_waiting_review_task_with_artifact(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "core-task-service.sqlite3")
    service = BackendCoreTaskService(repository)

    result = service.create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Core service lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/core-service-lab.json",
        actor="teacher_1",
        trace_id="trace_core_task_service_create",
        artifacts=[
            CoreArtifactInput(
                kind=ArtifactKind.LAB_DSL,
                path="examples/output/core-service-lab.json",
                title="Core service Lab DSL",
                metadata={"schemaValidated": True},
            )
        ],
    )

    task = result["task"]
    artifact = result["artifacts"][0]
    operation_event = result["operationAuditEvent"]
    summary = repository.summary()

    assert task.status.value == "WAITING_REVIEW"
    assert task.createdBy == "teacher_1"
    assert task.modelName == "backend-core-service"
    assert artifact.taskId == task.id
    assert artifact.kind.value == "LAB_DSL"
    assert artifact.metadata["schemaValidated"] is True
    assert operation_event.action.value == "BACKEND_CORE_TASK_CREATE"
    assert operation_event.resourceId == task.id
    assert result["safety"]["repositoryContractUsed"] is True
    assert result["safety"]["jsonStoreWritten"] is False
    assert summary["taskTotal"] == 1
    assert summary["artifactTotal"] == 1
    assert summary["operationAuditTotal"] == 1
    assert repository.get_ai_task(task.id).id == task.id
    assert repository.list_artifacts(task_id=task.id)[0].id == artifact.id


def test_backend_core_task_service_approves_task_and_writes_audit(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "core-task-approve.sqlite3")
    service = BackendCoreTaskService(repository)
    created = service.create_waiting_review_task(
        task_type="EXAM_GENERATION",
        title="Core service exam",
        input_type="lab-dsl",
        input_ref="examples/output/core-service-lab.json",
        actor="teacher_1",
    )

    reviewed = service.review_task(
        task_id=created["task"].id,
        reviewer="teacher_2",
        decision="approve",
        trace_id="trace_core_task_service_approve",
    )

    task = reviewed["task"]
    review_event = reviewed["reviewAuditEvent"]
    operation_event = reviewed["operationAuditEvent"]
    summary = repository.summary()

    assert task.status.value == "APPROVED"
    assert task.reviewer == "teacher_2"
    assert review_event.action.value == "APPROVE"
    assert review_event.fromStatus.value == "WAITING_REVIEW"
    assert review_event.toStatus.value == "APPROVED"
    assert operation_event.action.value == "REVIEW_APPROVE"
    assert operation_event.beforeState == "WAITING_REVIEW"
    assert operation_event.afterState == "APPROVED"
    assert summary["tasksByStatus"] == {"APPROVED": 1}
    assert summary["reviewAuditTotal"] == 1
    assert summary["operationAuditTotal"] == 2
    assert repository.get_ai_task(task.id).status.value == "APPROVED"


def test_backend_core_task_service_reject_requires_reason(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "core-task-reject.sqlite3")
    service = BackendCoreTaskService(repository)
    created = service.create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Core service grading",
        input_type="exam-dsl",
        input_ref="examples/output/core-service-exam.json",
        actor="teacher_1",
    )

    try:
        service.review_task(
            task_id=created["task"].id,
            reviewer="teacher_2",
            decision="reject",
        )
    except BackendCoreTaskServiceError as exc:
        assert exc.code == "BACKEND_CORE_TASK_STATUS_TRANSITION_INVALID"
        assert exc.errors[0]["field"] == "status"
        assert "Reject transition requires a reason" in exc.errors[0]["reason"]
    else:
        raise AssertionError("expected BackendCoreTaskServiceError")


def test_backend_core_task_service_rejects_invalid_decision(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "core-task-invalid-decision.sqlite3")
    service = BackendCoreTaskService(repository)
    created = service.create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Core service ppt",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        actor="teacher_1",
    )

    try:
        service.review_task(task_id=created["task"].id, reviewer="teacher_2", decision="publish")
    except BackendCoreTaskServiceError as exc:
        assert exc.code == "BACKEND_CORE_TASK_REVIEW_DECISION_UNSUPPORTED"
        assert exc.errors[0]["field"] == "decision"
    else:
        raise AssertionError("expected BackendCoreTaskServiceError")


def test_backend_core_task_service_rejects_missing_task(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "core-task-missing.sqlite3")
    service = BackendCoreTaskService(repository)

    try:
        service.review_task(task_id="task_missing", reviewer="teacher_2", decision="approve")
    except BackendCoreTaskServiceError as exc:
        assert exc.code == "BACKEND_CORE_TASK_NOT_FOUND"
        assert exc.errors[0]["field"] == "taskId"
    else:
        raise AssertionError("expected BackendCoreTaskServiceError")


def test_backend_core_task_service_blocks_repeated_review(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "core-task-repeated-review.sqlite3")
    service = BackendCoreTaskService(repository)
    created = service.create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Core service repeated review",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        actor="teacher_1",
    )
    service.review_task(task_id=created["task"].id, reviewer="teacher_2", decision="approve")

    try:
        service.review_task(task_id=created["task"].id, reviewer="teacher_2", decision="reject", reason="重复审核")
    except BackendCoreTaskServiceError as exc:
        assert exc.code == "BACKEND_CORE_TASK_STATUS_TRANSITION_INVALID"
        assert "APPROVED -> REJECTED" in exc.errors[0]["reason"]
    else:
        raise AssertionError("expected BackendCoreTaskServiceError")


def test_backend_core_task_service_validates_required_fields(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "core-task-validation.sqlite3")
    service = BackendCoreTaskService(repository)

    try:
        service.create_waiting_review_task(
            task_type="",
            title="Missing type",
            input_type="markdown",
            input_ref="examples/input/demo-source.md",
            actor="teacher_1",
        )
    except BackendCoreTaskServiceError as exc:
        payload = backend_core_task_service_error_response(exc)
        assert payload["success"] is False
        assert payload["code"] == "BACKEND_CORE_TASK_VALIDATION_ERROR"
        assert payload["errors"][0]["field"] == "taskType"
    else:
        raise AssertionError("expected BackendCoreTaskServiceError")
