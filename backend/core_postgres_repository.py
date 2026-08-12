"""PostgreSQL repository adapter for Backend Core persistence.

The adapter mirrors the SQLite staging repository contract but keeps the
driver import lazy. Tests can inject a connector, while real deployments can
install psycopg and register this adapter through BackendCoreRepositoryFactory.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from cli.ai_task import AiTask, ReviewAuditEvent
from cli.artifact import ArtifactRecord
from cli.audit import OperationAuditEvent
from cli.agent_entity import AgentEntityRecord

from backend.core_repository import CoreRepositoryError, SCHEMA_VERSION


PostgreSQLConnector = Callable[[str], Any]


class BackendCorePostgreSQLRepository:
    def __init__(
        self,
        database_url: str,
        *,
        database_url_summary: dict[str, Any] | None = None,
        connector: PostgreSQLConnector | None = None,
    ) -> None:
        self.database_url = database_url
        self.database_url_summary = database_url_summary or {}
        self._connector = connector or _default_postgresql_connector

    @property
    def db_path(self) -> None:
        return None

    def initialize_schema(self) -> dict[str, Any]:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS backend_core_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ai_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL,
                trace_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_backend_ai_tasks_status ON ai_tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_backend_ai_tasks_task_type ON ai_tasks(task_type)",
            "CREATE INDEX IF NOT EXISTS idx_backend_ai_tasks_trace_id ON ai_tasks(trace_id)",
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                trace_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_backend_artifacts_task_id ON artifacts(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_backend_artifacts_kind ON artifacts(kind)",
            "CREATE INDEX IF NOT EXISTS idx_backend_artifacts_trace_id ON artifacts(trace_id)",
            """
            CREATE TABLE IF NOT EXISTS review_audit_events (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                trace_id TEXT,
                raw_json TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_backend_review_audit_task_id ON review_audit_events(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_backend_review_audit_action ON review_audit_events(action)",
            "CREATE INDEX IF NOT EXISTS idx_backend_review_audit_actor ON review_audit_events(actor)",
            """
            CREATE TABLE IF NOT EXISTS operation_audit_events (
                id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                trace_id TEXT,
                raw_json TEXT NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_backend_operation_audit_resource
                ON operation_audit_events(resource_type, resource_id)
            """,
            "CREATE INDEX IF NOT EXISTS idx_backend_operation_audit_action ON operation_audit_events(action)",
            "CREATE INDEX IF NOT EXISTS idx_backend_operation_audit_actor ON operation_audit_events(actor)",
            """
            CREATE TABLE IF NOT EXISTS agent_entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                status TEXT NOT NULL,
                source_task_id TEXT NOT NULL,
                trace_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_entity_type
                ON agent_entities(entity_type)
            """,
            "CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_status ON agent_entities(status)",
            """
            CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_source_task_id
                ON agent_entities(source_task_id)
            """,
            "CREATE INDEX IF NOT EXISTS idx_backend_agent_entities_trace_id ON agent_entities(trace_id)",
        ]
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    for statement in statements:
                        cursor.execute(statement)
                    cursor.execute(
                        """
                        INSERT INTO backend_core_meta (key, value, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO UPDATE
                            SET value = EXCLUDED.value,
                                updated_at = CURRENT_TIMESTAMP
                        """,
                        ("schema_version", SCHEMA_VERSION),
                    )
        except CoreRepositoryError:
            raise
        except Exception as exc:
            raise self._postgresql_error(exc) from exc
        return self.summary()

    def save_ai_task(self, task: AiTask) -> AiTask:
        self.initialize_schema()
        payload = task.to_dict()
        self._upsert_raw_json(
            "ai_tasks",
            {
                "id": task.id,
                "task_type": task.taskType,
                "status": task.status.value,
                "trace_id": task.traceId,
                "created_at": task.createdAt,
                "updated_at": task.updatedAt,
                "raw_json": json.dumps(payload, ensure_ascii=False),
            },
        )
        return task

    def save_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        self.initialize_schema()
        payload = artifact.to_dict()
        self._upsert_raw_json(
            "artifacts",
            {
                "id": artifact.id,
                "task_id": artifact.taskId,
                "kind": artifact.kind.value,
                "status": artifact.status.value,
                "trace_id": artifact.traceId,
                "created_at": artifact.createdAt,
                "updated_at": artifact.updatedAt,
                "raw_json": json.dumps(payload, ensure_ascii=False),
            },
        )
        return artifact

    def save_review_audit_event(self, event: ReviewAuditEvent) -> ReviewAuditEvent:
        self.initialize_schema()
        payload = event.to_dict()
        self._upsert_raw_json(
            "review_audit_events",
            {
                "id": event.id,
                "task_id": event.taskId,
                "task_type": event.taskType,
                "action": event.action.value,
                "actor": event.actor,
                "occurred_at": event.occurredAt,
                "trace_id": event.traceId,
                "raw_json": json.dumps(payload, ensure_ascii=False),
            },
        )
        return event

    def save_operation_audit_event(self, event: OperationAuditEvent) -> OperationAuditEvent:
        self.initialize_schema()
        payload = event.to_dict()
        self._upsert_raw_json(
            "operation_audit_events",
            {
                "id": event.id,
                "resource_type": event.resourceType.value,
                "resource_id": event.resourceId,
                "action": event.action.value,
                "actor": event.actor,
                "occurred_at": event.occurredAt,
                "trace_id": event.traceId,
                "raw_json": json.dumps(payload, ensure_ascii=False),
            },
        )
        return event

    def save_agent_entity(self, entity: AgentEntityRecord) -> AgentEntityRecord:
        self.initialize_schema()
        payload = entity.to_dict()
        self._upsert_raw_json(
            "agent_entities",
            {
                "id": entity.id,
                "entity_type": entity.entityType.value,
                "status": entity.status.value,
                "source_task_id": entity.sourceTaskId,
                "trace_id": entity.traceId,
                "created_at": entity.createdAt,
                "updated_at": entity.updatedAt,
                "raw_json": json.dumps(payload, ensure_ascii=False),
            },
        )
        return entity

    def get_ai_task(self, task_id: str) -> AiTask | None:
        payload = self._get_raw_json("ai_tasks", task_id)
        return AiTask.from_dict(payload) if payload is not None else None

    def list_ai_tasks(self, *, status: str | None = None, task_type: str | None = None) -> list[AiTask]:
        payloads = self._list_raw_json(
            "ai_tasks",
            filters={"status": status, "task_type": task_type},
            order_by="created_at",
        )
        return [AiTask.from_dict(payload) for payload in payloads]

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        payload = self._get_raw_json("artifacts", artifact_id)
        return ArtifactRecord.from_dict(payload) if payload is not None else None

    def list_artifacts(
        self,
        *,
        kind: str | None = None,
        task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[ArtifactRecord]:
        payloads = self._list_raw_json(
            "artifacts",
            filters={"kind": kind, "task_id": task_id, "trace_id": trace_id},
            order_by="created_at",
        )
        return [ArtifactRecord.from_dict(payload) for payload in payloads]

    def list_review_audit_events(
        self,
        *,
        task_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[ReviewAuditEvent]:
        payloads = self._list_raw_json(
            "review_audit_events",
            filters={"task_id": task_id, "action": action, "actor": actor},
            order_by="occurred_at",
        )
        return [ReviewAuditEvent.from_dict(payload) for payload in payloads]

    def list_operation_audit_events(
        self,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[OperationAuditEvent]:
        payloads = self._list_raw_json(
            "operation_audit_events",
            filters={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "actor": actor,
            },
            order_by="occurred_at",
        )
        return [OperationAuditEvent.from_dict(payload) for payload in payloads]

    def get_agent_entity(self, entity_id: str) -> AgentEntityRecord | None:
        payload = self._get_raw_json("agent_entities", entity_id)
        return AgentEntityRecord.from_dict(payload) if payload is not None else None

    def list_agent_entities(
        self,
        *,
        entity_type: str | None = None,
        source_task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[AgentEntityRecord]:
        payloads = self._list_raw_json(
            "agent_entities",
            filters={
                "entity_type": entity_type,
                "source_task_id": source_task_id,
                "trace_id": trace_id,
            },
            order_by="created_at",
        )
        return [AgentEntityRecord.from_dict(payload) for payload in payloads]

    def summary(self) -> dict[str, Any]:
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
                schema_version = _schema_version(connection)
        except CoreRepositoryError:
            raise
        except Exception as exc:
            raise self._postgresql_error(exc) from exc
        return {
            "databaseUrlSummary": self.database_url_summary,
            "schemaVersion": schema_version or SCHEMA_VERSION,
            "tables": [
                "backend_core_meta",
                "ai_tasks",
                "artifacts",
                "review_audit_events",
                "operation_audit_events",
                "agent_entities",
            ],
            "mode": "POSTGRESQL_BACKEND_CORE_REPOSITORY",
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
            "safety": {
                "externalDatabase": True,
                "localSqliteOnly": False,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
                "autoApproveAllowed": False,
                "realPublish": False,
                "databaseUrlValueReturned": False,
            },
        }

    def _connect(self) -> Any:
        try:
            return self._connector(self.database_url)
        except CoreRepositoryError:
            raise
        except Exception as exc:
            raise CoreRepositoryError(
                "BACKEND_CORE_POSTGRESQL_CONNECTION_ERROR",
                "Backend Core PostgreSQL 连接失败",
                [{"field": "databaseUrl", "reason": type(exc).__name__}],
            ) from exc

    def _upsert_raw_json(self, table: str, values_by_column: dict[str, Any]) -> None:
        columns = list(values_by_column)
        placeholders = ", ".join(["%s"] * len(columns))
        updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in columns if column != "id")
        query = f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET {updates}
        """
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, tuple(values_by_column[column] for column in columns))
        except CoreRepositoryError:
            raise
        except Exception as exc:
            raise self._postgresql_error(exc) from exc

    def _get_raw_json(self, table: str, record_id: str) -> dict[str, Any] | None:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT raw_json FROM {table} WHERE id = %s", (record_id,))
                    row = cursor.fetchone()
        except CoreRepositoryError:
            raise
        except Exception as exc:
            raise self._postgresql_error(exc) from exc
        if row is None:
            return None
        return json.loads(str(_row_value(row, "raw_json", 0)))

    def _list_raw_json(
        self,
        table: str,
        *,
        filters: dict[str, str | None],
        order_by: str,
    ) -> list[dict[str, Any]]:
        where, values = _filters(filters)
        query = f"SELECT raw_json FROM {table}"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += f" ORDER BY {order_by} DESC"
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, tuple(values))
                    rows = cursor.fetchall()
        except CoreRepositoryError:
            raise
        except Exception as exc:
            raise self._postgresql_error(exc) from exc
        return [json.loads(str(_row_value(row, "raw_json", 0))) for row in rows]

    def _postgresql_error(self, exc: Exception) -> CoreRepositoryError:
        return CoreRepositoryError(
            "BACKEND_CORE_POSTGRESQL_ERROR",
            "Backend Core PostgreSQL 操作失败",
            [{"field": "databaseUrl", "reason": type(exc).__name__}],
        )


def create_backend_core_postgresql_repository(
    database_url: str,
    *,
    database_url_summary: dict[str, Any] | None = None,
    connector: PostgreSQLConnector | None = None,
) -> BackendCorePostgreSQLRepository:
    return BackendCorePostgreSQLRepository(
        database_url,
        database_url_summary=database_url_summary,
        connector=connector,
    )


def _default_postgresql_connector(database_url: str) -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise CoreRepositoryError(
            "BACKEND_CORE_POSTGRESQL_DRIVER_MISSING",
            "Backend Core PostgreSQL driver 未安装",
            [{"field": "psycopg", "reason": "install psycopg[binary] before registering PostgreSQL adapter"}],
        ) from exc
    return psycopg.connect(database_url)


def _filters(filters: dict[str, str | None]) -> tuple[list[str], list[str]]:
    where: list[str] = []
    values: list[str] = []
    for column, value in filters.items():
        if value is None:
            continue
        where.append(f"{column} = %s")
        values.append(value)
    return where, values


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        pass
    if isinstance(row, (list, tuple)):
        return row[index]
    return getattr(row, key)


def _count(connection: Any, table: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS total FROM {table}")
        row = cursor.fetchone()
    return int(_row_value(row, "total", 0)) if row else 0


def _count_by_column(connection: Any, table: str, column: str) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} AS value, COUNT(*) AS total FROM {table} GROUP BY {column}")
        rows = cursor.fetchall()
    return {str(_row_value(row, "value", 0)): int(_row_value(row, "total", 1)) for row in rows}


def _schema_version(connection: Any) -> str | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT value FROM backend_core_meta WHERE key = %s", ("schema_version",))
        row = cursor.fetchone()
    return str(_row_value(row, "value", 0)) if row else None
