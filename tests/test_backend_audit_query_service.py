from pathlib import Path

from backend.audit_query_service import BackendAuditQueryService, BackendAuditQueryServiceError
from backend.core_service import BackendCoreService
from cli.ai_task import ReviewAction, TaskStatus, create_review_audit_event, create_waiting_review_task
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.provider_audit import ProviderCallStatus, create_provider_call_audit_event
from cli.store import JsonTaskStore


def _service(store_path: Path, root: Path) -> BackendAuditQueryService:
    return BackendAuditQueryService(
        store=JsonTaskStore(store_path),
        core_service=BackendCoreService(root),
    )


def _seed_task_audits(store: JsonTaskStore):
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Audit service task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        trace_id="trace_audit_service_task",
    )
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
    review_event = create_review_audit_event(
        task=task,
        action=ReviewAction.APPROVE,
        actor="teacher_1",
        from_status=TaskStatus.WAITING_REVIEW,
        to_status=TaskStatus.APPROVED,
        trace_id=task.traceId,
    )
    operation_event = create_operation_audit_event(
        action=OperationAction.REVIEW_APPROVE,
        resource_type=OperationResourceType.AI_TASK,
        resource_id=task.id,
        actor="teacher_1",
        trace_id=task.traceId,
        before_state="WAITING_REVIEW",
        after_state="APPROVED",
    )
    store.save(task)
    store.save_review_audit_event(review_event)
    store.save_operation_audit_event(operation_event)
    return task, review_event, operation_event


def test_backend_audit_query_service_lists_provider_audits_from_json_store(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    event = create_provider_call_audit_event(
        operation="generateJson",
        provider_id="mock",
        status=ProviderCallStatus.FAILED,
        actor="backend-mock",
        trace_id="trace_provider_audit_service",
        prompt_id="missing_prompt",
        error_code="NOT_FOUND",
        error_field="promptId",
        error_message="Prompt 不存在",
    )
    store.save_provider_call_audit_event(event)
    service = _service(store.path, tmp_path)

    result = service.list_provider_call_audit_events({"status": "FAILED", "operation": "generateJson"})

    assert result["mode"] == "MOCK_ONLY"
    assert result["total"] == 1
    assert result["items"][0]["id"] == event.id
    assert result["items"][0]["errorCode"] == "NOT_FOUND"
    assert result["filters"]["status"] == "FAILED"


def test_backend_audit_query_service_rejects_invalid_provider_status(tmp_path):
    service = _service(tmp_path / "store.json", tmp_path)

    try:
        service.list_provider_call_audit_events({"status": "BAD"})
    except BackendAuditQueryServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "status", "reason": "非法状态"}]
    else:
        raise AssertionError("expected BackendAuditQueryServiceError")


def test_backend_audit_query_service_lists_review_and_operation_audits_from_json_store(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    task, review_event, operation_event = _seed_task_audits(store)
    service = _service(store.path, tmp_path)

    review_result = service.list_review_audit_events({"taskId": task.id, "action": "APPROVE"})
    operation_result = service.list_operation_audit_events(
        {
            "resourceType": "AI_TASK",
            "resourceId": task.id,
            "action": "REVIEW_APPROVE",
        }
    )

    assert review_result["mode"] == "MOCK_ONLY"
    assert review_result["items"][0]["id"] == review_event.id
    assert review_result["filters"] == {"taskId": task.id, "action": "APPROVE", "actor": None}
    assert operation_result["mode"] == "MOCK_ONLY"
    assert operation_result["items"][0]["id"] == operation_event.id
    assert operation_result["filters"]["resourceId"] == task.id


def test_backend_audit_query_service_reads_review_and_operation_audits_from_core_sqlite(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    task, review_event, operation_event = _seed_task_audits(store)
    core_service = BackendCoreService(tmp_path)
    repository, write_summary = core_service.prepare_write_through({"coreDbPath": str(tmp_path / "core.sqlite3")})
    core_service.write_through(
        repository,
        write_summary,
        task=task,
        review_audit_event=review_event,
        operation_audit_event=operation_event,
    )
    service = BackendAuditQueryService(store=store, core_service=core_service)

    review_result = service.list_review_audit_events(
        {"coreDbPath": str(tmp_path / "core.sqlite3"), "taskId": task.id, "action": "APPROVE"}
    )
    operation_result = service.list_operation_audit_events(
        {
            "coreDbPath": str(tmp_path / "core.sqlite3"),
            "resourceType": "AI_TASK",
            "resourceId": task.id,
            "action": "REVIEW_APPROVE",
        }
    )

    assert review_result["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert review_result["coreDbPath"] == str(tmp_path / "core.sqlite3")
    assert review_result["localSqliteRead"] is True
    assert review_result["items"][0]["id"] == review_event.id
    assert operation_result["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert operation_result["items"][0]["id"] == operation_event.id
    assert operation_result["productionDatabaseWritten"] is False


def test_backend_audit_query_service_rejects_invalid_review_and_operation_filters(tmp_path):
    service = _service(tmp_path / "store.json", tmp_path)

    try:
        service.list_review_audit_events({"action": "UNKNOWN"})
    except BackendAuditQueryServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "action", "reason": "非法动作"}]
    else:
        raise AssertionError("expected review action validation error")

    try:
        service.list_operation_audit_events({"resourceType": "UNKNOWN"})
    except BackendAuditQueryServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "resourceType", "reason": "非法资源类型"}]
    else:
        raise AssertionError("expected resource type validation error")
