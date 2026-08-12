import os
from pathlib import Path

import pytest

from backend.core_service import (
    BACKEND_CORE_DATABASE_URL_ENV,
    BACKEND_CORE_DATABASE_URL_SOURCE,
    BackendCoreService,
)
from backend.core_contract import BackendCoreRepositoryConfig, BackendCoreRepositoryContract
from backend.core_repository import CoreRepositoryError
from cli.ai_task import ReviewAction, TaskStatus, create_review_audit_event, create_waiting_review_task
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.agent_entity import AgentEntityType, create_agent_entity_record


class RecordingRepositoryFactory:
    def __init__(self) -> None:
        self.configs: list[BackendCoreRepositoryConfig] = []

    def create(self, config: BackendCoreRepositoryConfig) -> BackendCoreRepositoryContract:
        self.configs.append(config)
        from backend.core_contract import BackendCoreRepositoryFactory

        return BackendCoreRepositoryFactory().create(config)


def test_backend_core_service_write_through_and_readonly_queries(tmp_path):
    service = BackendCoreService(tmp_path)
    db_path = tmp_path / "backend-core-service.sqlite3"
    repository, write_summary = service.prepare_write_through({"coreDbPath": str(db_path)})
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Service write-through task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_service",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path="examples/output/real-llm-lab.json",
        title="Service Lab DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
    )
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
    review_audit = create_review_audit_event(
        task=task,
        action=ReviewAction.APPROVE,
        actor="teacher_1",
        from_status=TaskStatus.WAITING_REVIEW,
        to_status=TaskStatus.APPROVED,
        trace_id=task.traceId,
    )
    operation_audit = create_operation_audit_event(
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
        title="Service platform entity",
        payload={"title": "Service platform entity"},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="LAB_DSL",
    )

    service.write_through(
        repository,
        write_summary,
        task=task,
        artifacts=[artifact.to_dict()],
        review_audit_event=review_audit,
        operation_audit_event=operation_audit,
    )
    repository.save_agent_entity(agent_entity)
    summary = service.repository_summary(repository)
    tasks = service.list_ai_task_payloads(
        repository,
        status="APPROVED",
        task_type="LAB_GENERATION",
    )
    task_payload = service.get_ai_task_payload(repository, task.id)
    artifacts = service.list_artifact_payloads(
        repository,
        kind="LAB_DSL",
        task_id=task.id,
    )
    review_events = service.list_review_audit_event_payloads(
        repository,
        task_id=task.id,
        action="APPROVE",
    )
    operation_events = service.list_operation_audit_event_payloads(
        repository,
        resource_type="AI_TASK",
        resource_id=task.id,
    )
    agent_entities = service.list_agent_entity_payloads(
        repository,
        entity_type="lab_template",
        source_task_id=task.id,
    )
    agent_entity_payload = service.get_agent_entity_payload(repository, agent_entity.id)

    assert repository is not None
    assert write_summary["mode"] == "LOCAL_SQLITE_BACKEND_CORE_WRITE_THROUGH"
    assert write_summary["localSqliteWritten"] is True
    assert write_summary["taskWritten"] is True
    assert write_summary["artifactsWritten"] == 1
    assert write_summary["reviewAuditEventWritten"] is True
    assert write_summary["operationAuditEventWritten"] is True
    assert write_summary["productionDatabaseWritten"] is False
    assert db_path.exists()

    assert summary["available"] is True
    assert summary["taskTotal"] == 1
    assert summary["artifactTotal"] == 1
    assert summary["reviewAuditTotal"] == 1
    assert summary["operationAuditTotal"] == 1
    assert summary["agentEntityTotal"] == 1
    assert summary["tasksByStatus"] == {"APPROVED": 1}
    assert summary["artifactsByKind"] == {"LAB_DSL": 1}
    assert summary["agentEntitiesByType"] == {"lab_template": 1}
    assert summary["safety"]["readOnly"] is True

    assert [item["id"] for item in tasks] == [task.id]
    assert task_payload["id"] == task.id
    assert task_payload["status"] == "APPROVED"
    assert [item["id"] for item in artifacts] == [artifact.id]
    assert [item["id"] for item in review_events] == [review_audit.id]
    assert [item["id"] for item in operation_events] == [operation_audit.id]
    assert [item["id"] for item in agent_entities] == [agent_entity.id]
    assert agent_entity_payload["sourceTaskId"] == task.id


def test_backend_core_service_missing_readonly_file_does_not_create_db(tmp_path):
    service = BackendCoreService(tmp_path)
    missing_db = tmp_path / "missing.sqlite3"
    repository, policy = service.resolve_repository({"coreDbPath": str(missing_db)})

    summary = service.repository_summary(repository)

    assert policy["dbPathSource"] == "REQUEST_CORE_DB_PATH"
    assert summary["available"] is False
    assert summary["reason"] == "backend core sqlite staging file does not exist"
    assert missing_db.exists() is False


def test_backend_core_service_resolve_repository_default_policy(tmp_path):
    service = BackendCoreService(tmp_path)
    repository, policy = service.resolve_repository({})
    default_repository = service.create_repository({})

    assert repository is None
    assert policy["dbPath"] is None
    assert policy["dbPathSource"] == "NOT_CONFIGURED"
    assert str(default_repository.db_path).endswith("examples\\output\\backend-core-local.sqlite3") or str(
        default_repository.db_path
    ).endswith("examples/output/backend-core-local.sqlite3")


def test_backend_core_service_uses_repository_factory_config(tmp_path):
    factory = RecordingRepositoryFactory()
    service = BackendCoreService(tmp_path, repository_factory=factory)
    db_path = tmp_path / "factory-service.sqlite3"

    repository, policy = service.resolve_repository({"coreDbPath": str(db_path)})

    assert repository is not None
    assert factory.configs[0].kind == "sqlite-local"
    assert factory.configs[0].db_path == db_path
    assert factory.configs[0].source == "REQUEST_CORE_DB_PATH"
    assert policy["repositoryKind"] == "sqlite-local"
    assert policy["productionDatabaseWritten"] is False


def test_backend_core_service_uses_sqlite_database_url_env(tmp_path, monkeypatch):
    db_path = tmp_path / "database-url-service.sqlite3"
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, f"sqlite:///{db_path.as_posix()}")
    service = BackendCoreService(tmp_path)

    repository, policy = service.resolve_repository({})

    assert repository is not None
    assert repository.db_path == db_path
    assert policy["dbPath"] == str(db_path)
    assert policy["dbPathSource"] == BACKEND_CORE_DATABASE_URL_SOURCE
    assert policy["databaseUrlConfigured"] is True
    assert policy["databaseUrlEnv"] == BACKEND_CORE_DATABASE_URL_ENV
    assert db_path.exists() is False


@pytest.mark.skipif(os.name == "nt", reason="POSIX absolute path semantics")
def test_backend_core_service_normalizes_posix_absolute_sqlite_url(tmp_path):
    service = BackendCoreService(tmp_path)

    resolution = service.resolve_database_url("sqlite:////tmp/backend-core.sqlite3")

    assert resolution.db_path == Path("/tmp/backend-core.sqlite3")


def test_backend_core_service_request_path_overrides_database_url_env(tmp_path, monkeypatch):
    env_db_path = tmp_path / "env-service.sqlite3"
    request_db_path = tmp_path / "request-service.sqlite3"
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, f"sqlite:///{env_db_path.as_posix()}")
    service = BackendCoreService(tmp_path)

    repository, policy = service.resolve_repository({"coreDbPath": str(request_db_path)})

    assert repository is not None
    assert repository.db_path == request_db_path
    assert policy["dbPath"] == str(request_db_path)
    assert policy["dbPathSource"] == "REQUEST_CORE_DB_PATH"


def test_backend_core_service_recognizes_external_database_url_without_secret_leak(tmp_path, monkeypatch):
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, "postgresql://user:secret@example.invalid/prod")
    service = BackendCoreService(tmp_path)

    try:
        service.resolve_repository({})
    except CoreRepositoryError as exc:
        assert exc.code == "BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE"
        assert exc.errors == [{"field": "repositoryKind", "reason": "postgresql adapter not registered"}]
        assert "secret" not in str(exc.errors)
        assert "example.invalid" not in str(exc.errors)
    else:
        raise AssertionError("expected CoreRepositoryError")


def test_backend_core_service_database_url_summary_redacts_external_url(tmp_path, monkeypatch):
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, "postgresql://user:secret@example.invalid/prod")
    service = BackendCoreService(tmp_path)

    try:
        service.resolve_repository({})
    except CoreRepositoryError:
        resolution = service.resolve_database_url("postgresql://user:secret@example.invalid/prod")
        summary = resolution.summary
        assert resolution.repository_kind == "postgresql"
        assert resolution.db_path is None
        assert summary["scheme"] == "postgresql"
        assert summary["hostPresent"] is True
        assert summary["usernamePresent"] is True
        assert summary["passwordPresent"] is True
        assert summary["valueReturned"] is False
        assert "secret" not in str(summary)
        assert "example.invalid" not in str(summary)
    else:
        raise AssertionError("expected CoreRepositoryError")


def test_backend_core_service_rejects_sqlite_database_url_with_host(tmp_path, monkeypatch):
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, "sqlite://server/path/to/backend-core.sqlite3")
    service = BackendCoreService(tmp_path)

    try:
        service.resolve_repository({})
    except CoreRepositoryError as exc:
        assert exc.code == "BACKEND_CORE_DATABASE_URL_UNSUPPORTED"
        assert exc.errors[0]["field"] == BACKEND_CORE_DATABASE_URL_ENV
        assert exc.errors[0]["reason"] == "sqlite URL must not include host"
    else:
        raise AssertionError("expected CoreRepositoryError")


def test_backend_core_service_rejects_unsupported_repository_kind_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_CORE_REPOSITORY_KIND", "postgres")
    service = BackendCoreService(tmp_path)

    try:
        service.resolve_repository({"coreDbPath": str(tmp_path / "backend-core.sqlite3")})
    except CoreRepositoryError as exc:
        assert exc.code == "BACKEND_CORE_REPOSITORY_KIND_UNSUPPORTED"
        assert exc.errors[0]["field"] == "LAB_BACKEND_CORE_REPOSITORY_KIND"
    else:
        raise AssertionError("expected CoreRepositoryError")
