from backend.core_contract import (
    BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
    BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL,
    BackendCoreRepositoryConfig,
    BackendCoreRepositoryContract,
    BackendCoreRepositoryFactory,
    BackendCoreSQLiteRepositoryAdapter,
    create_backend_core_sqlite_repository,
)
from backend.core_repository import BackendCoreSQLiteRepository
from backend.core_repository import CoreRepositoryError
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.ai_task import ReviewAction, TaskStatus, create_review_audit_event, create_waiting_review_task
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.agent_entity import AgentEntityType, create_agent_entity_record


def test_backend_core_sqlite_adapter_satisfies_contract_and_forwards_writes(tmp_path):
    db_path = tmp_path / "backend-core-contract.sqlite3"
    adapter = BackendCoreSQLiteRepositoryAdapter(BackendCoreSQLiteRepository(db_path))
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Contract task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_contract",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path="examples/output/real-llm-lab.json",
        title="Contract Lab DSL",
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
    )
    agent_entity = create_agent_entity_record(
        entity_type=AgentEntityType.LAB_TEMPLATE,
        title="Contract platform entity",
        payload={"title": "Contract platform entity"},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="LAB_DSL",
    )

    adapter.initialize_schema()
    adapter.save_ai_task(task)
    adapter.save_artifact(artifact)
    adapter.save_review_audit_event(review_event)
    adapter.save_operation_audit_event(operation_event)
    adapter.save_agent_entity(agent_entity)
    summary = adapter.summary()

    assert isinstance(adapter, BackendCoreRepositoryContract)
    assert adapter.db_path == db_path
    assert db_path.exists()
    assert summary["taskTotal"] == 1
    assert summary["artifactTotal"] == 1
    assert adapter.get_ai_task(task.id).id == task.id
    assert adapter.get_artifact(artifact.id).id == artifact.id
    assert adapter.list_ai_tasks(task_type="LAB_GENERATION")[0].id == task.id
    assert adapter.list_artifacts(kind="LAB_DSL", trace_id=task.traceId)[0].id == artifact.id
    assert adapter.list_review_audit_events(action="APPROVE", actor="teacher_1")[0].id == review_event.id
    assert adapter.list_operation_audit_events(action="REVIEW_APPROVE", actor="teacher_1")[0].id == operation_event.id
    assert adapter.get_agent_entity(agent_entity.id).id == agent_entity.id
    assert adapter.list_agent_entities(entity_type="lab_template")[0].id == agent_entity.id
    assert summary["tasksByType"] == {"LAB_GENERATION": 1}
    assert summary["artifactsByKind"] == {"LAB_DSL": 1}
    assert summary["agentEntitiesByType"] == {"lab_template": 1}


def test_backend_core_sqlite_repository_factory_returns_contract(tmp_path):
    repository = create_backend_core_sqlite_repository(tmp_path / "factory.sqlite3")

    assert isinstance(repository, BackendCoreRepositoryContract)
    assert repository.summary()["mode"] == "LOCAL_SQLITE_BACKEND_CORE_REPOSITORY"


def test_backend_core_repository_factory_uses_explicit_config(tmp_path):
    db_path = tmp_path / "factory-config.sqlite3"
    config = BackendCoreRepositoryConfig(
        kind=BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL,
        db_path=db_path,
        source="REQUEST_CORE_DB_PATH",
    )
    repository = BackendCoreRepositoryFactory().create(config)

    assert isinstance(repository, BackendCoreRepositoryContract)
    assert repository.db_path == db_path
    assert config.to_policy()["repositoryKind"] == "sqlite-local"


def test_backend_core_repository_factory_rejects_unknown_kind(tmp_path):
    config = BackendCoreRepositoryConfig(
        kind="oracle",
        db_path=tmp_path / "not-used.sqlite3",
        source="REQUEST_CORE_DB_PATH",
    )

    try:
        BackendCoreRepositoryFactory().create(config)
    except CoreRepositoryError as exc:
        assert exc.code == "BACKEND_CORE_REPOSITORY_KIND_UNSUPPORTED"
        assert exc.errors[0]["field"] == "repositoryKind"
    else:
        raise AssertionError("expected CoreRepositoryError")


def test_backend_core_repository_factory_reports_unregistered_external_adapter():
    config = BackendCoreRepositoryConfig(
        kind=BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
        db_path=None,
        source="ENV_DATABASE_URL",
        database_url="postgresql://user:secret@example.invalid/prod",
        database_url_summary={
            "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
            "scheme": "postgresql",
            "valueReturned": False,
        },
    )

    try:
        BackendCoreRepositoryFactory().create(config)
    except CoreRepositoryError as exc:
        assert exc.code == "BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE"
        assert exc.errors == [
            {"field": "repositoryKind", "reason": "postgresql adapter not registered"}
        ]
        assert "secret" not in str(exc.errors)
    else:
        raise AssertionError("expected CoreRepositoryError")


def test_backend_core_repository_factory_uses_registered_external_adapter(tmp_path):
    calls = []

    def fake_postgresql_adapter(config: BackendCoreRepositoryConfig) -> BackendCoreRepositoryContract:
        calls.append(config)
        return create_backend_core_sqlite_repository(tmp_path / "fake-postgresql-adapter.sqlite3")

    config = BackendCoreRepositoryConfig(
        kind=BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
        db_path=None,
        source="ENV_DATABASE_URL",
        database_url="postgresql://user:secret@example.invalid/prod",
        database_url_summary={
            "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
            "scheme": "postgresql",
            "valueReturned": False,
        },
    )

    repository = BackendCoreRepositoryFactory(
        adapters={BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL: fake_postgresql_adapter}
    ).create(config)

    assert isinstance(repository, BackendCoreRepositoryContract)
    assert calls == [config]
    assert "secret" not in str(config.to_policy())
