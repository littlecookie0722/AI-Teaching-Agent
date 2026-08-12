import pytest

from backend.core_repository import BackendCoreSQLiteRepository, CoreRepositoryError, sync_core_repository_from_store
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.ai_task import TaskStatus, create_review_audit_event, create_waiting_review_task, ReviewAction
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.agent_entity import AgentEntityType, create_agent_entity_record
from cli.store import JsonTaskStore


def test_backend_core_sqlite_repository_round_trips_core_records(tmp_path):
    repository = BackendCoreSQLiteRepository(tmp_path / "backend-core.sqlite3")
    init_summary = repository.initialize_schema()
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Backend core task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_repo",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path="examples/output/real-llm-lab.json",
        title="Backend core artifact",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
    )
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
    agent_entity = create_agent_entity_record(
        entity_type=AgentEntityType.LAB_TEMPLATE,
        title="Backend core platform entity",
        payload={"title": "Backend core platform entity"},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="LAB_DSL",
    )

    repository.save_ai_task(task)
    repository.save_artifact(artifact)
    repository.save_review_audit_event(review_event)
    repository.save_operation_audit_event(operation_event)
    repository.save_agent_entity(agent_entity)
    summary = repository.summary()

    assert init_summary["schemaVersion"] == "1"
    assert init_summary["safety"]["localSqliteOnly"] is True
    assert repository.get_ai_task(task.id).id == task.id
    assert repository.get_artifact(artifact.id).id == artifact.id
    assert [item.id for item in repository.list_ai_tasks(status="WAITING_REVIEW")] == [task.id]
    assert [item.id for item in repository.list_artifacts(task_id=task.id)] == [artifact.id]
    assert [item.id for item in repository.list_artifacts(trace_id=task.traceId)] == [artifact.id]
    assert [
        item.id
        for item in repository.list_review_audit_events(task_id=task.id, action="APPROVE", actor="teacher_1")
    ] == [review_event.id]
    assert [
        item.id
        for item in repository.list_operation_audit_events(
            resource_id=task.id,
            action="REVIEW_APPROVE",
            actor="teacher_1",
        )
    ] == [operation_event.id]
    assert repository.get_agent_entity(agent_entity.id).id == agent_entity.id
    assert [item.id for item in repository.list_agent_entities(entity_type="lab_template")] == [agent_entity.id]
    assert [item.id for item in repository.list_agent_entities(source_task_id=task.id)] == [agent_entity.id]
    assert [item.id for item in repository.list_agent_entities(trace_id=task.traceId)] == [agent_entity.id]
    assert summary["taskTotal"] == 1
    assert summary["artifactTotal"] == 1
    assert summary["reviewAuditTotal"] == 1
    assert summary["operationAuditTotal"] == 1
    assert summary["agentEntityTotal"] == 1
    assert summary["tasksByStatus"] == {"WAITING_REVIEW": 1}
    assert summary["tasksByType"] == {"LAB_GENERATION": 1}
    assert summary["artifactsByKind"] == {"LAB_DSL": 1}
    assert summary["agentEntitiesByType"] == {"lab_template": 1}
    assert summary["agentEntitiesByStatus"] == {"DRAFT_CREATED": 1}


def test_sync_backend_core_repository_from_json_store(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    repository = BackendCoreSQLiteRepository(tmp_path / "backend-core.sqlite3")
    task = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Backend core sync task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-ppt.json",
        trace_id="trace_backend_core_sync",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.PPT_DSL,
        path="examples/output/real-llm-ppt.json",
        title="Backend core sync artifact",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
    )
    agent_entity = create_agent_entity_record(
        entity_type=AgentEntityType.PPT_DECK,
        title="Backend core sync PPT deck",
        payload={"title": "Backend core sync PPT deck"},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/ppt-deck-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-ppt.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="PPT_DSL",
    )
    store.save(task)
    store.save_artifact(artifact)
    store.save_agent_entity(agent_entity)

    result = sync_core_repository_from_store(repository=repository, store=store)

    assert result["tasksSynced"] == 1
    assert result["artifactsSynced"] == 1
    assert result["reviewAuditEventsSynced"] == 0
    assert result["operationAuditEventsSynced"] == 0
    assert result["agentEntitiesSynced"] == 1
    assert result["productionDatabaseWritten"] is False
    assert repository.get_ai_task(task.id).taskType == "PPT_GENERATION"
    assert repository.list_artifacts(kind="PPT_DSL")[0].taskId == task.id
    assert repository.list_agent_entities(entity_type="ppt_deck")[0].sourceTaskId == task.id


def test_backend_core_repository_read_methods_do_not_create_missing_db(tmp_path):
    db_path = tmp_path / "missing.sqlite3"
    repository = BackendCoreSQLiteRepository(db_path)

    with pytest.raises(CoreRepositoryError) as exc_info:
        repository.get_ai_task("task_missing")

    assert exc_info.value.code == "BACKEND_CORE_SQLITE_ERROR"
    assert db_path.exists() is False
