"""Local SQLite repository for core backend API MVP data.

This module is a development/staging persistence boundary for the future real
backend API. It writes only to an explicit local SQLite file and keeps the
existing JSON model payloads as raw_json for safe round-trip migration.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from cli.ai_task import AiTask, ReviewAuditEvent
from cli.artifact import ArtifactRecord
from cli.audit import OperationAuditEvent
from cli.agent_entity import AgentEntityRecord
from cli.store import JsonTaskStore


DEFAULT_CORE_DB_PATH = "examples/output/backend-core-local.sqlite3"
SCHEMA_VERSION = "1"


class CoreRepositoryError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class BackendCoreSQLiteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize_schema(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                # Backward compatibility: migrate old platform_entities table
                if _table_exists(connection, "platform_entities") and not _table_exists(connection, "agent_entities"):
                    connection.execute("ALTER TABLE platform_entities RENAME TO agent_entities")
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS backend_core_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS ai_tasks (
                        id TEXT PRIMARY KEY,
                        task_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        trace_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        raw_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_backend_ai_tasks_status
                        ON ai_tasks(status);
                    CREATE INDEX IF NOT EXISTS idx_backend_ai_tasks_task_type
                        ON ai_tasks(task_type);
                    CREATE INDEX IF NOT EXISTS idx_backend_ai_tasks_trace_id
                        ON ai_tasks(trace_id);

                    CREATE TABLE IF NOT EXISTS artifacts (
                        id TEXT PRIMARY KEY,
                        task_id TEXT,
                        kind TEXT NOT NULL,
                        status TEXT NOT NULL,
                        trace_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        raw_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_backend_artifacts_task_id
                        ON artifacts(task_id);
                    CREATE INDEX IF NOT EXISTS idx_backend_artifacts_kind
                        ON artifacts(kind);
                    CREATE INDEX IF NOT EXISTS idx_backend_artifacts_trace_id
                        ON artifacts(trace_id);

                    CREATE TABLE IF NOT EXISTS review_audit_events (
                        id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        action TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        occurred_at TEXT NOT NULL,
                        trace_id TEXT,
                        raw_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_backend_review_audit_task_id
                        ON review_audit_events(task_id);
                    CREATE INDEX IF NOT EXISTS idx_backend_review_audit_action
                        ON review_audit_events(action);
                    CREATE INDEX IF NOT EXISTS idx_backend_review_audit_actor
                        ON review_audit_events(actor);

                    CREATE TABLE IF NOT EXISTS operation_audit_events (
                        id TEXT PRIMARY KEY,
                        resource_type TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        occurred_at TEXT NOT NULL,
                        trace_id TEXT,
                        raw_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_backend_operation_audit_resource
                        ON operation_audit_events(resource_type, resource_id);
                    CREATE INDEX IF NOT EXISTS idx_backend_operation_audit_action
                        ON operation_audit_events(action);
                    CREATE INDEX IF NOT EXISTS idx_backend_operation_audit_actor
                        ON operation_audit_events(actor);

                    CREATE TABLE IF NOT EXISTS agent_entities (
                        id TEXT PRIMARY KEY,
                        entity_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        source_task_id TEXT NOT NULL,
                        trace_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        raw_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_entity_type
                        ON agent_entities(entity_type);
                    CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_status
                        ON agent_entities(status);
                    CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_source_task_id
                        ON agent_entities(source_task_id);
                    CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_trace_id
                        ON agent_entities(trace_id);
                    """
                )
                connection.execute(
                    """
                    INSERT OR REPLACE INTO backend_core_meta (key, value, updated_at)
                    VALUES ('schema_version', ?, CURRENT_TIMESTAMP)
                    """,
                    (SCHEMA_VERSION,),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return self._schema_summary()

    def save_ai_task(self, task: AiTask) -> AiTask:
        self.initialize_schema()
        payload = task.to_dict()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO ai_tasks (
                        id, task_type, status, trace_id, created_at, updated_at, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        task.taskType,
                        task.status.value,
                        task.traceId,
                        task.createdAt,
                        task.updatedAt,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return task

    def save_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        self.initialize_schema()
        payload = artifact.to_dict()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO artifacts (
                        id, task_id, kind, status, trace_id, created_at, updated_at, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact.id,
                        artifact.taskId,
                        artifact.kind.value,
                        artifact.status.value,
                        artifact.traceId,
                        artifact.createdAt,
                        artifact.updatedAt,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return artifact

    def save_review_audit_event(self, event: ReviewAuditEvent) -> ReviewAuditEvent:
        self.initialize_schema()
        payload = event.to_dict()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO review_audit_events (
                        id, task_id, task_type, action, actor, occurred_at, trace_id, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.taskId,
                        event.taskType,
                        event.action.value,
                        event.actor,
                        event.occurredAt,
                        event.traceId,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return event

    def save_operation_audit_event(self, event: OperationAuditEvent) -> OperationAuditEvent:
        self.initialize_schema()
        payload = event.to_dict()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO operation_audit_events (
                        id, resource_type, resource_id, action, actor, occurred_at, trace_id, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.resourceType.value,
                        event.resourceId,
                        event.action.value,
                        event.actor,
                        event.occurredAt,
                        event.traceId,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return event

    def save_agent_entity(self, entity: AgentEntityRecord) -> AgentEntityRecord:
        self.initialize_schema()
        payload = entity.to_dict()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO agent_entities (
                        id, entity_type, status, source_task_id, trace_id, created_at, updated_at, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.id,
                        entity.entityType.value,
                        entity.status.value,
                        entity.sourceTaskId,
                        entity.traceId,
                        entity.createdAt,
                        entity.updatedAt,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return entity

    def get_ai_task(self, task_id: str) -> AiTask | None:
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "ai_tasks"):
                    return None
                row = connection.execute("SELECT raw_json FROM ai_tasks WHERE id = ?", (task_id,)).fetchone()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        if row is None:
            return None
        return AiTask.from_dict(json.loads(row["raw_json"]))

    def list_ai_tasks(self, *, status: str | None = None, task_type: str | None = None) -> list[AiTask]:
        query = "SELECT raw_json FROM ai_tasks"
        where, values = _filters({"status": status, "task_type": task_type})
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC"
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "ai_tasks"):
                    return []
                rows = connection.execute(query, values).fetchall()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return [AiTask.from_dict(json.loads(row["raw_json"])) for row in rows]

    def list_artifacts(
        self,
        *,
        kind: str | None = None,
        task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[ArtifactRecord]:
        query = "SELECT raw_json FROM artifacts"
        where, values = _filters({"kind": kind, "task_id": task_id, "trace_id": trace_id})
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC"
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "artifacts"):
                    return []
                rows = connection.execute(query, values).fetchall()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return [ArtifactRecord.from_dict(json.loads(row["raw_json"])) for row in rows]

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "artifacts"):
                    return None
                row = connection.execute("SELECT raw_json FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        if row is None:
            return None
        return ArtifactRecord.from_dict(json.loads(row["raw_json"]))

    def list_review_audit_events(
        self,
        *,
        task_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[ReviewAuditEvent]:
        query = "SELECT raw_json FROM review_audit_events"
        where, values = _filters({"task_id": task_id, "action": action, "actor": actor})
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY occurred_at DESC"
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "review_audit_events"):
                    return []
                rows = connection.execute(query, values).fetchall()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return [ReviewAuditEvent.from_dict(json.loads(row["raw_json"])) for row in rows]

    def list_operation_audit_events(
        self,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[OperationAuditEvent]:
        query = "SELECT raw_json FROM operation_audit_events"
        where, values = _filters(
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "actor": actor,
            }
        )
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY occurred_at DESC"
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "operation_audit_events"):
                    return []
                rows = connection.execute(query, values).fetchall()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return [OperationAuditEvent.from_dict(json.loads(row["raw_json"])) for row in rows]

    def get_agent_entity(self, entity_id: str) -> AgentEntityRecord | None:
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "agent_entities"):
                    return None
                row = connection.execute("SELECT raw_json FROM agent_entities WHERE id = ?", (entity_id,)).fetchone()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        if row is None:
            return None
        return AgentEntityRecord.from_dict(json.loads(row["raw_json"]))

    def list_agent_entities(
        self,
        *,
        entity_type: str | None = None,
        source_task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[AgentEntityRecord]:
        query = "SELECT raw_json FROM agent_entities"
        where, values = _filters({"entity_type": entity_type, "source_task_id": source_task_id, "trace_id": trace_id})
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC"
        try:
            with self._connect_readonly() as connection:
                if not _table_exists(connection, "agent_entities"):
                    return []
                rows = connection.execute(query, values).fetchall()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return [AgentEntityRecord.from_dict(json.loads(row["raw_json"])) for row in rows]

    def summary(self) -> dict[str, Any]:
        self.initialize_schema()
        try:
            with self._connect() as connection:
                task_total = _count(connection, "ai_tasks")
                artifact_total = _count(connection, "artifacts")
                review_audit_total = _count(connection, "review_audit_events")
                operation_audit_total = _count(connection, "operation_audit_events")
                agent_entity_total = _count(connection, "agent_entities")
                tasks_by_status = _count_by_column(connection, "ai_tasks", "status")
                tasks_by_type = _count_by_column(connection, "ai_tasks", "task_type")
                artifacts_by_kind = _count_by_column(connection, "artifacts", "kind")
                agent_entities_by_type = _count_by_column(connection, "agent_entities", "entity_type")
                agent_entities_by_status = _count_by_column(connection, "agent_entities", "status")
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return {
            **self._schema_summary(),
            "taskTotal": task_total,
            "artifactTotal": artifact_total,
            "reviewAuditTotal": review_audit_total,
            "operationAuditTotal": operation_audit_total,
            "agentEntityTotal": agent_entity_total,
            "tasksByStatus": tasks_by_status,
            "tasksByType": tasks_by_type,
            "artifactsByKind": artifacts_by_kind,
            "agentEntitiesByType": agent_entities_by_type,
            "agentEntitiesByStatus": agent_entities_by_status,
        }

    def _connect(self) -> sqlite3.Connection:
        if self.db_path.exists() and self.db_path.is_dir():
            raise CoreRepositoryError(
                "BACKEND_CORE_SQLITE_PATH_ERROR",
                "Backend Core 本地 SQLite 路径不能是目录",
                [{"field": "dbPath", "reason": "path is directory"}],
            )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _connect_readonly(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _schema_summary(self) -> dict[str, Any]:
        return {
            "dbPath": str(self.db_path),
            "schemaVersion": SCHEMA_VERSION,
            "tables": [
                "backend_core_meta",
                "ai_tasks",
                "artifacts",
                "review_audit_events",
                "operation_audit_events",
                "agent_entities",
            ],
            "mode": "LOCAL_SQLITE_BACKEND_CORE_REPOSITORY",
            "safety": {
                "localSqliteOnly": True,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        }

    def _sqlite_error(self, exc: sqlite3.Error) -> CoreRepositoryError:
        return CoreRepositoryError(
            "BACKEND_CORE_SQLITE_ERROR",
            "Backend Core 本地 SQLite 操作失败",
            [{"field": "dbPath", "reason": str(exc)}],
        )


def sync_core_repository_from_store(
    *,
    repository: BackendCoreSQLiteRepository,
    store: JsonTaskStore,
) -> dict[str, Any]:
    repository.initialize_schema()
    tasks = store.list()
    artifacts = store.list_artifacts()
    review_audit_events = store.list_review_audit_events()
    operation_audit_events = store.list_operation_audit_events()
    agent_entities = store.list_agent_entities()
    for task in tasks:
        repository.save_ai_task(task)
    for artifact in artifacts:
        repository.save_artifact(artifact)
    for event in review_audit_events:
        repository.save_review_audit_event(event)
    for event in operation_audit_events:
        repository.save_operation_audit_event(event)
    for entity in agent_entities:
        repository.save_agent_entity(entity)
    return {
        "tasksSynced": len(tasks),
        "artifactsSynced": len(artifacts),
        "reviewAuditEventsSynced": len(review_audit_events),
        "operationAuditEventsSynced": len(operation_audit_events),
        "agentEntitiesSynced": len(agent_entities),
        "mode": "LOCAL_SQLITE_BACKEND_CORE_SYNC",
        "productionDatabaseWritten": False,
        "productionQueueUsed": False,
        "autoApproveAllowed": False,
        "realPublish": False,
    }


def _filters(filters: dict[str, str | None]) -> tuple[list[str], list[str]]:
    where: list[str] = []
    values: list[str] = []
    for column, value in filters.items():
        if value is None:
            continue
        where.append(f"{column} = ?")
        values.append(value)
    return where, values


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    return int(row["total"]) if row else 0


def _count_by_column(connection: sqlite3.Connection, table: str, column: str) -> dict[str, int]:
    rows = connection.execute(f"SELECT {column} AS value, COUNT(*) AS total FROM {table} GROUP BY {column}").fetchall()
    return {str(row["value"]): int(row["total"]) for row in rows}
