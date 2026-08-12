"""Repository contract for Backend Core service persistence.

The contract keeps BackendCoreService independent from the current local
SQLite staging implementation. Future real database adapters should implement
this interface before being wired into HTTP routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

from cli.ai_task import AiTask, ReviewAuditEvent
from cli.artifact import ArtifactRecord
from cli.audit import OperationAuditEvent
from cli.agent_entity import AgentEntityRecord

from backend.core_repository import BackendCoreSQLiteRepository, CoreRepositoryError


BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL = "sqlite-local"
BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL = "postgresql"
BACKEND_CORE_REPOSITORY_KIND_MYSQL = "mysql"
BACKEND_CORE_EXTERNAL_REPOSITORY_KINDS = {
    BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
    BACKEND_CORE_REPOSITORY_KIND_MYSQL,
}


@dataclass(frozen=True)
class BackendCoreRepositoryConfig:
    kind: str
    db_path: Path | None
    source: str
    database_url: str | None = None
    database_url_summary: dict[str, Any] | None = None

    def to_policy(self) -> dict[str, Any]:
        return {
            "repositoryKind": self.kind,
            "dbPath": str(self.db_path) if self.db_path is not None else None,
            "dbPathSource": self.source,
            "databaseUrlSummary": self.database_url_summary,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }


@runtime_checkable
class BackendCoreRepositoryContract(Protocol):
    @property
    def db_path(self) -> Path | None:
        """Local staging path; external adapters return None."""

    def initialize_schema(self) -> dict[str, Any]:
        """Prepare persistence schema and return a repository summary."""

    def save_ai_task(self, task: AiTask) -> AiTask:
        """Persist an AI task record."""

    def save_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        """Persist a generated artifact record."""

    def save_review_audit_event(self, event: ReviewAuditEvent) -> ReviewAuditEvent:
        """Persist a review audit event."""

    def save_operation_audit_event(self, event: OperationAuditEvent) -> OperationAuditEvent:
        """Persist an operation audit event."""

    def save_agent_entity(self, entity: AgentEntityRecord) -> AgentEntityRecord:
        """Persist a local platform entity staging record."""

    def get_ai_task(self, task_id: str) -> AiTask | None:
        """Load one AI task by id."""

    def list_ai_tasks(self, *, status: str | None = None, task_type: str | None = None) -> list[AiTask]:
        """List AI tasks with optional status/type filters."""

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        """Load one artifact by id."""

    def list_artifacts(
        self,
        *,
        kind: str | None = None,
        task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[ArtifactRecord]:
        """List artifacts with optional filters."""

    def list_review_audit_events(
        self,
        *,
        task_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[ReviewAuditEvent]:
        """List review audit events with optional filters."""

    def list_operation_audit_events(
        self,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[OperationAuditEvent]:
        """List operation audit events with optional filters."""

    def get_agent_entity(self, entity_id: str) -> AgentEntityRecord | None:
        """Load one platform entity by id."""

    def list_agent_entities(
        self,
        *,
        entity_type: str | None = None,
        source_task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[AgentEntityRecord]:
        """List platform entities with optional filters."""

    def summary(self) -> dict[str, Any]:
        """Return repository counters and safety metadata."""


class BackendCoreSQLiteRepositoryAdapter:
    def __init__(self, repository: BackendCoreSQLiteRepository) -> None:
        self.repository = repository

    @property
    def db_path(self) -> Path:
        return self.repository.db_path

    def initialize_schema(self) -> dict[str, Any]:
        return self.repository.initialize_schema()

    def save_ai_task(self, task: AiTask) -> AiTask:
        return self.repository.save_ai_task(task)

    def save_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        return self.repository.save_artifact(artifact)

    def save_review_audit_event(self, event: ReviewAuditEvent) -> ReviewAuditEvent:
        return self.repository.save_review_audit_event(event)

    def save_operation_audit_event(self, event: OperationAuditEvent) -> OperationAuditEvent:
        return self.repository.save_operation_audit_event(event)

    def save_agent_entity(self, entity: AgentEntityRecord) -> AgentEntityRecord:
        return self.repository.save_agent_entity(entity)

    def get_ai_task(self, task_id: str) -> AiTask | None:
        return self.repository.get_ai_task(task_id)

    def list_ai_tasks(self, *, status: str | None = None, task_type: str | None = None) -> list[AiTask]:
        return self.repository.list_ai_tasks(status=status, task_type=task_type)

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        return self.repository.get_artifact(artifact_id)

    def list_artifacts(
        self,
        *,
        kind: str | None = None,
        task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[ArtifactRecord]:
        return self.repository.list_artifacts(kind=kind, task_id=task_id, trace_id=trace_id)

    def list_review_audit_events(
        self,
        *,
        task_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[ReviewAuditEvent]:
        return self.repository.list_review_audit_events(task_id=task_id, action=action, actor=actor)

    def list_operation_audit_events(
        self,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[OperationAuditEvent]:
        return self.repository.list_operation_audit_events(
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            actor=actor,
        )

    def get_agent_entity(self, entity_id: str) -> AgentEntityRecord | None:
        return self.repository.get_agent_entity(entity_id)

    def list_agent_entities(
        self,
        *,
        entity_type: str | None = None,
        source_task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[AgentEntityRecord]:
        return self.repository.list_agent_entities(
            entity_type=entity_type,
            source_task_id=source_task_id,
            trace_id=trace_id,
        )

    def summary(self) -> dict[str, Any]:
        return self.repository.summary()


def create_backend_core_sqlite_repository(db_path: Path) -> BackendCoreRepositoryContract:
    return BackendCoreSQLiteRepositoryAdapter(BackendCoreSQLiteRepository(db_path))


class BackendCoreRepositoryFactory:
    def __init__(
        self,
        adapters: dict[str, Callable[[BackendCoreRepositoryConfig], BackendCoreRepositoryContract]] | None = None,
    ) -> None:
        self._adapters: dict[str, Callable[[BackendCoreRepositoryConfig], BackendCoreRepositoryContract]] = {
            BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL: self._create_sqlite_repository,
        }
        self._adapters.update(adapters or {})

    def create(self, config: BackendCoreRepositoryConfig) -> BackendCoreRepositoryContract:
        adapter = self._adapters.get(config.kind)
        if adapter is not None:
            return adapter(config)
        if config.kind in BACKEND_CORE_EXTERNAL_REPOSITORY_KINDS:
            raise CoreRepositoryError(
                "BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE",
                "Backend Core repository adapter 未配置",
                [{"field": "repositoryKind", "reason": f"{config.kind} adapter not registered"}],
            )
        raise CoreRepositoryError(
            "BACKEND_CORE_REPOSITORY_KIND_UNSUPPORTED",
            "Backend Core repository 类型暂不支持",
            [{"field": "repositoryKind", "reason": config.kind}],
        )

    def _create_sqlite_repository(self, config: BackendCoreRepositoryConfig) -> BackendCoreRepositoryContract:
        if config.db_path is None:
            raise CoreRepositoryError(
                "BACKEND_CORE_DATABASE_URL_UNSUPPORTED",
                "Backend Core sqlite repository 缺少本地路径",
                [{"field": "dbPath", "reason": "required for sqlite-local repository"}],
            )
        return create_backend_core_sqlite_repository(config.db_path)
