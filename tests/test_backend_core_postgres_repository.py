import pytest

from backend.core_contract import (
    BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
    BackendCoreRepositoryConfig,
    BackendCoreRepositoryContract,
    BackendCoreRepositoryFactory,
)
from backend.core_postgres_repository import (
    BackendCorePostgreSQLRepository,
    create_backend_core_postgresql_repository,
)
from backend.core_repository import CoreRepositoryError
from backend.core_service import BACKEND_CORE_DATABASE_URL_ENV, BackendCoreService
from cli.ai_task import ReviewAction, TaskStatus, create_review_audit_event, create_waiting_review_task
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.agent_entity import AgentEntityType, create_agent_entity_record
from tests.fakes_backend_postgres import FakePostgreSQLDatabase


def test_postgresql_repository_round_trips_core_records_with_fake_connector():
    database = FakePostgreSQLDatabase()
    repository = BackendCorePostgreSQLRepository(
        "postgresql://user:secret@example.invalid/prod",
        database_url_summary={
            "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
            "scheme": "postgresql",
            "valueReturned": False,
        },
        connector=database.connect,
    )
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="PostgreSQL task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_postgres",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path="examples/output/real-llm-lab.json",
        title="PostgreSQL Lab DSL",
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
        title="PostgreSQL platform entity",
        payload={"title": "PostgreSQL platform entity"},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="LAB_DSL",
    )

    repository.initialize_schema()
    repository.save_ai_task(task)
    repository.save_artifact(artifact)
    repository.save_review_audit_event(review_event)
    repository.save_operation_audit_event(operation_event)
    repository.save_agent_entity(agent_entity)
    summary = repository.summary()

    assert isinstance(repository, BackendCoreRepositoryContract)
    assert repository.db_path is None
    assert summary["mode"] == "POSTGRESQL_BACKEND_CORE_REPOSITORY"
    assert summary["taskTotal"] == 1
    assert summary["artifactTotal"] == 1
    assert summary["reviewAuditTotal"] == 1
    assert summary["operationAuditTotal"] == 1
    assert summary["agentEntityTotal"] == 1
    assert repository.get_ai_task(task.id).id == task.id
    assert repository.get_artifact(artifact.id).id == artifact.id
    assert repository.list_ai_tasks(task_type="LAB_GENERATION")[0].id == task.id
    assert repository.list_artifacts(kind="LAB_DSL", trace_id=task.traceId)[0].id == artifact.id
    assert repository.list_review_audit_events(action="APPROVE", actor="teacher_1")[0].id == review_event.id
    assert repository.list_operation_audit_events(action="REVIEW_APPROVE", actor="teacher_1")[0].id == operation_event.id
    assert repository.get_agent_entity(agent_entity.id).id == agent_entity.id
    assert repository.list_agent_entities(entity_type="lab_template")[0].id == agent_entity.id
    assert summary["tasksByType"] == {"LAB_GENERATION": 1}
    assert summary["artifactsByKind"] == {"LAB_DSL": 1}
    assert summary["agentEntitiesByType"] == {"lab_template": 1}
    assert summary["safety"]["externalDatabase"] is True
    assert summary["safety"]["productionDatabaseWritten"] is False
    assert "secret" not in str(summary)


def test_postgresql_repository_factory_can_register_real_adapter_with_connector():
    database = FakePostgreSQLDatabase()
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
        adapters={
            BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL: lambda value: create_backend_core_postgresql_repository(
                value.database_url or "",
                database_url_summary=value.database_url_summary,
                connector=database.connect,
            )
        }
    ).create(config)

    assert isinstance(repository, BackendCoreRepositoryContract)
    assert repository.db_path is None
    assert repository.initialize_schema()["mode"] == "POSTGRESQL_BACKEND_CORE_REPOSITORY"
    assert "secret" not in str(config.to_policy())


def test_backend_core_service_can_resolve_registered_postgresql_adapter(monkeypatch, tmp_path):
    database = FakePostgreSQLDatabase()
    database_url = "postgresql://user:secret@example.invalid/prod"
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, database_url)
    service = BackendCoreService(
        tmp_path,
        BackendCoreRepositoryFactory(
            adapters={
                BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL: lambda value: create_backend_core_postgresql_repository(
                    value.database_url or "",
                    database_url_summary=value.database_url_summary,
                    connector=database.connect,
                )
            }
        ),
    )
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Service PostgreSQL task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_service_postgres",
    )

    repository, policy = service.resolve_repository({})
    repository_for_write, write_summary = service.prepare_write_through({})
    service.write_through(repository_for_write, write_summary, task=task)
    summary = service.repository_summary(repository)

    assert repository.db_path is None
    assert policy["repositoryKind"] == BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL
    assert policy["databaseUrlSummary"]["valueReturned"] is False
    assert write_summary["mode"] == "BACKEND_CORE_REPOSITORY_WRITE_THROUGH"
    assert write_summary["coreDbPath"] is None
    assert write_summary["localSqliteWritten"] is False
    assert write_summary["externalDatabaseWritten"] is True
    assert summary["available"] is True
    assert summary["taskTotal"] == 1
    assert "secret" not in str(policy)
    assert "secret" not in str(summary)


def test_postgresql_repository_connection_errors_are_redacted():
    def broken_connector(_database_url: str):
        raise RuntimeError("cannot connect")

    repository = create_backend_core_postgresql_repository(
        "postgresql://user:secret@example.invalid/prod",
        database_url_summary={
            "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
            "scheme": "postgresql",
            "valueReturned": False,
        },
        connector=broken_connector,
    )

    with pytest.raises(CoreRepositoryError) as exc_info:
        repository.summary()

    assert exc_info.value.code == "BACKEND_CORE_POSTGRESQL_CONNECTION_ERROR"
    assert exc_info.value.errors == [{"field": "databaseUrl", "reason": "RuntimeError"}]
    assert "secret" not in str(exc_info.value.errors)
