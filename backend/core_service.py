"""Service helpers for Backend Core staging persistence.

This module keeps Backend Core repository resolution, read-only queries, and
write-through summaries out of the HTTP mock router. It is still a local
SQLite staging boundary, not a production database service.
"""

from __future__ import annotations

import os
import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from cli.ai_task import AiTask, ReviewAuditEvent
from cli.artifact import ArtifactRecord
from cli.audit import OperationAuditEvent
from cli.agent_entity import AgentEntityRecord

from backend.core_contract import (
    BACKEND_CORE_EXTERNAL_REPOSITORY_KINDS,
    BACKEND_CORE_REPOSITORY_KIND_MYSQL,
    BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
    BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL,
    BackendCoreRepositoryConfig,
    BackendCoreRepositoryContract,
    BackendCoreRepositoryFactory,
)
from backend.core_repository import DEFAULT_CORE_DB_PATH, CoreRepositoryError


BACKEND_CORE_REPOSITORY_KIND_ENV = "LAB_BACKEND_CORE_REPOSITORY_KIND"
BACKEND_CORE_DATABASE_URL_ENV = "LAB_BACKEND_CORE_DATABASE_URL"
BACKEND_CORE_DATABASE_URL_SOURCE = "ENV_DATABASE_URL"


class BackendCoreDatabaseUrlResolution:
    def __init__(
        self,
        *,
        repository_kind: str,
        db_path: Path | None,
        source: str,
        summary: dict[str, Any],
        database_url: str | None,
    ) -> None:
        self.repository_kind = repository_kind
        self.db_path = db_path
        self.source = source
        self.summary = summary
        self.database_url = database_url


class BackendCoreService:
    def __init__(self, root: Path, repository_factory: BackendCoreRepositoryFactory | None = None) -> None:
        self.root = root
        self.repository_factory = repository_factory or BackendCoreRepositoryFactory()

    def resolve_local_path(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.root / path
        return path

    def resolve_repository(
        self,
        payload: dict[str, Any],
        *,
        fallback_to_builtin: bool = False,
    ) -> tuple[BackendCoreRepositoryContract | None, dict[str, Any]]:
        requested_db_path = str(payload.get("coreDbPath") or payload.get("dbPath") or "").strip()
        db_path: Path | None = None
        db_path_source = "NOT_CONFIGURED"
        database_url_resolution: BackendCoreDatabaseUrlResolution | None = None
        if requested_db_path:
            db_path = self.resolve_local_path(requested_db_path)
            db_path_source = "REQUEST_CORE_DB_PATH"
        else:
            database_url = os.environ.get(BACKEND_CORE_DATABASE_URL_ENV, "").strip()
            if database_url:
                database_url_resolution = self.resolve_database_url(database_url)
                db_path = database_url_resolution.db_path
                db_path_source = database_url_resolution.source
        if db_path is None and fallback_to_builtin:
            db_path = self.resolve_local_path(DEFAULT_CORE_DB_PATH)
            db_path_source = "BUILTIN_DEFAULT_CORE_DB_PATH"
        policy = self._repository_policy(
            db_path=db_path,
            db_path_source=db_path_source,
            database_url_summary=database_url_resolution.summary if database_url_resolution else None,
        )
        if db_path is None:
            if database_url_resolution is None:
                return None, policy
            config = self._repository_config(
                db_path=None,
                db_path_source=db_path_source,
                database_url=database_url_resolution.database_url,
                database_url_summary=database_url_resolution.summary,
                repository_kind_override=database_url_resolution.repository_kind,
            )
            return self.repository_factory.create(config), policy
        config = self._repository_config(
            db_path,
            db_path_source,
            database_url=database_url_resolution.database_url if database_url_resolution else None,
            database_url_summary=database_url_resolution.summary if database_url_resolution else None,
            repository_kind_override=database_url_resolution.repository_kind if database_url_resolution else None,
        )
        return self.repository_factory.create(config), policy

    def create_repository(self, payload: dict[str, Any]) -> BackendCoreRepositoryContract:
        repository, _policy = self.resolve_repository(payload, fallback_to_builtin=True)
        if repository is None:
            return self.repository_factory.create(
                self._repository_config(
                    self.resolve_local_path(DEFAULT_CORE_DB_PATH),
                    "BUILTIN_DEFAULT_CORE_DB_PATH",
                )
            )
        return repository

    def resolve_database_url(self, database_url: str) -> BackendCoreDatabaseUrlResolution:
        parsed = urlparse(database_url)
        scheme = parsed.scheme.strip().lower()
        if scheme in {"postgres", "postgresql"}:
            return BackendCoreDatabaseUrlResolution(
                repository_kind=BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
                db_path=None,
                source=BACKEND_CORE_DATABASE_URL_SOURCE,
                summary=self._database_url_summary(parsed, repository_kind=BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL),
                database_url=database_url,
            )
        if scheme in {"mysql", "mariadb"}:
            return BackendCoreDatabaseUrlResolution(
                repository_kind=BACKEND_CORE_REPOSITORY_KIND_MYSQL,
                db_path=None,
                source=BACKEND_CORE_DATABASE_URL_SOURCE,
                summary=self._database_url_summary(parsed, repository_kind=BACKEND_CORE_REPOSITORY_KIND_MYSQL),
                database_url=database_url,
            )
        if scheme != "sqlite":
            reason = f"unsupported scheme: {scheme or 'missing'}"
            raise CoreRepositoryError(
                "BACKEND_CORE_DATABASE_URL_UNSUPPORTED",
                "Backend Core database URL 目前只支持本地 sqlite",
                [{"field": BACKEND_CORE_DATABASE_URL_ENV, "reason": reason}],
            )
        if parsed.netloc:
            raise CoreRepositoryError(
                "BACKEND_CORE_DATABASE_URL_UNSUPPORTED",
                "Backend Core database URL 目前只支持本地 sqlite",
                [{"field": BACKEND_CORE_DATABASE_URL_ENV, "reason": "sqlite URL must not include host"}],
            )
        raw_path = unquote(parsed.path or "")
        if raw_path in {"", "/", ":memory:", "/:memory:"}:
            raise CoreRepositoryError(
                "BACKEND_CORE_DATABASE_URL_UNSUPPORTED",
                "Backend Core database URL 目前只支持本地 sqlite",
                [{"field": BACKEND_CORE_DATABASE_URL_ENV, "reason": "sqlite path is required"}],
            )
        if raw_path.startswith("//"):
            raw_path = "/" + raw_path.lstrip("/")
        if raw_path.startswith("/") and _looks_like_windows_drive_path(raw_path[1:]):
            raw_path = raw_path[1:]
        elif raw_path.startswith("/./") or raw_path.startswith("/../"):
            raw_path = raw_path[1:]
        db_path = self.resolve_local_path(raw_path)
        return BackendCoreDatabaseUrlResolution(
            repository_kind=BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL,
            db_path=db_path,
            source=BACKEND_CORE_DATABASE_URL_SOURCE,
            summary=self._database_url_summary(parsed, repository_kind=BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL),
            database_url=database_url,
        )

    def resolve_database_url_path(self, database_url: str) -> Path:
        resolution = self.resolve_database_url(database_url)
        if resolution.db_path is None:
            raise CoreRepositoryError(
                "BACKEND_CORE_DATABASE_URL_UNSUPPORTED",
                "Backend Core database URL 不是本地 sqlite 路径",
                [{"field": BACKEND_CORE_DATABASE_URL_ENV, "reason": f"{resolution.repository_kind} has no local path"}],
            )
        return resolution.db_path

    def _repository_config(
        self,
        db_path: Path | None,
        db_path_source: str,
        *,
        database_url: str | None = None,
        database_url_summary: dict[str, Any] | None = None,
        repository_kind_override: str | None = None,
    ) -> BackendCoreRepositoryConfig:
        repository_kind = (
            repository_kind_override
            or os.environ.get(BACKEND_CORE_REPOSITORY_KIND_ENV, BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL).strip()
        )
        if not repository_kind:
            repository_kind = BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL
        if db_path is not None and repository_kind in BACKEND_CORE_EXTERNAL_REPOSITORY_KINDS:
            raise CoreRepositoryError(
                "BACKEND_CORE_REPOSITORY_KIND_UNSUPPORTED",
                "Backend Core repository 类型与本地 coreDbPath 不匹配",
                [{"field": BACKEND_CORE_REPOSITORY_KIND_ENV, "reason": f"{repository_kind} requires database URL"}],
            )
        if repository_kind not in {BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL, *BACKEND_CORE_EXTERNAL_REPOSITORY_KINDS}:
            raise CoreRepositoryError(
                "BACKEND_CORE_REPOSITORY_KIND_UNSUPPORTED",
                "Backend Core repository 类型暂不支持",
                [{"field": BACKEND_CORE_REPOSITORY_KIND_ENV, "reason": repository_kind}],
            )
        return BackendCoreRepositoryConfig(
            kind=repository_kind,
            db_path=db_path if db_path is None or db_path.is_absolute() else self.resolve_local_path(str(db_path)),
            source=db_path_source,
            database_url=database_url,
            database_url_summary=database_url_summary,
        )

    def _repository_policy(
        self,
        *,
        db_path: Path | None,
        db_path_source: str,
        database_url_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repository_kind = os.environ.get(BACKEND_CORE_REPOSITORY_KIND_ENV, BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL).strip()
        if not repository_kind:
            repository_kind = BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL
        if database_url_summary and database_url_summary.get("repositoryKind"):
            repository_kind = str(database_url_summary["repositoryKind"])
        database_url_configured = bool(os.environ.get(BACKEND_CORE_DATABASE_URL_ENV, "").strip())
        policy = {
            "repositoryKind": repository_kind,
            "dbPath": str(db_path) if db_path is not None else None,
            "dbPathSource": db_path_source,
            "builtinDefaultDbPath": DEFAULT_CORE_DB_PATH,
            "databaseUrlConfigured": database_url_configured,
            "databaseUrlEnv": BACKEND_CORE_DATABASE_URL_ENV if database_url_configured else None,
            "databaseUrlSummary": database_url_summary,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }
        return policy

    def _database_url_summary(self, parsed: Any, *, repository_kind: str) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "repositoryKind": repository_kind,
            "scheme": parsed.scheme.strip().lower(),
            "hostPresent": bool(parsed.hostname),
            "portPresent": parsed.port is not None,
            "databaseNamePresent": bool((parsed.path or "").strip("/")),
            "usernamePresent": bool(parsed.username),
            "passwordPresent": bool(parsed.password),
            "valueReturned": False,
            "networkDatabase": repository_kind != BACKEND_CORE_REPOSITORY_KIND_SQLITE_LOCAL,
        }
        return summary

    def prepare_write_through(
        self,
        payload: dict[str, Any],
    ) -> tuple[BackendCoreRepositoryContract | None, dict[str, Any] | None]:
        repository, policy = self.resolve_repository(payload)
        if repository is None:
            return None, None
        is_local_sqlite = repository.db_path is not None
        return repository, {
            "mode": (
                "LOCAL_SQLITE_BACKEND_CORE_WRITE_THROUGH"
                if is_local_sqlite
                else "BACKEND_CORE_REPOSITORY_WRITE_THROUGH"
            ),
            "repositoryKind": policy["repositoryKind"],
            "coreDbPath": str(repository.db_path) if repository.db_path is not None else None,
            "dbPathSource": policy["dbPathSource"],
            "databaseUrlSummary": policy.get("databaseUrlSummary"),
            "localSqliteWritten": False,
            "externalDatabaseWritten": False,
            "taskWritten": False,
            "agentEntityWritten": False,
            "artifactsWritten": 0,
            "reviewAuditEventWritten": False,
            "operationAuditEventWritten": False,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        }

    def write_through(
        self,
        repository: BackendCoreRepositoryContract | None,
        summary: dict[str, Any] | None,
        *,
        task: AiTask | None = None,
        agent_entity: AgentEntityRecord | None = None,
        artifacts: list[ArtifactRecord | dict[str, Any]] | None = None,
        review_audit_event: ReviewAuditEvent | None = None,
        operation_audit_event: OperationAuditEvent | None = None,
    ) -> None:
        if repository is None or summary is None:
            return
        if task is not None:
            repository.save_ai_task(task)
            summary["taskWritten"] = True
        if agent_entity is not None:
            repository.save_agent_entity(agent_entity)
            summary["agentEntityWritten"] = True
        for artifact_value in artifacts or []:
            artifact = (
                artifact_value
                if isinstance(artifact_value, ArtifactRecord)
                else ArtifactRecord.from_dict(artifact_value)
            )
            repository.save_artifact(artifact)
            summary["artifactsWritten"] = int(summary.get("artifactsWritten", 0)) + 1
        if review_audit_event is not None:
            repository.save_review_audit_event(review_audit_event)
            summary["reviewAuditEventWritten"] = True
        if operation_audit_event is not None:
            repository.save_operation_audit_event(operation_audit_event)
            summary["operationAuditEventWritten"] = True
        summary["localSqliteWritten"] = (
            summary["coreDbPath"] is not None
            and (
                summary["taskWritten"]
                or summary.get("agentEntityWritten") is True
                or int(summary.get("artifactsWritten", 0)) > 0
                or summary["reviewAuditEventWritten"]
                or summary["operationAuditEventWritten"]
            )
        )
        summary["externalDatabaseWritten"] = (
            summary["coreDbPath"] is None
            and (
                summary["taskWritten"]
                or summary.get("agentEntityWritten") is True
                or int(summary.get("artifactsWritten", 0)) > 0
                or summary["reviewAuditEventWritten"]
                or summary["operationAuditEventWritten"]
            )
        )

    def repository_summary(self, repository: BackendCoreRepositoryContract | None) -> dict[str, Any]:
        if repository is None:
            return {
                "available": False,
                "reason": "coreDbPath not configured",
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
            }
        if repository.db_path is None:
            try:
                summary = repository.summary()
            except CoreRepositoryError as exc:
                return {
                    "available": False,
                    "errorCode": exc.code,
                    "errors": exc.errors,
                    "productionDatabaseWritten": False,
                    "productionQueueUsed": False,
                }
            return {
                "available": True,
                **summary,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
            }
        if not repository.db_path.exists():
            return {
                "available": False,
                "dbPath": str(repository.db_path),
                "reason": "backend core sqlite staging file does not exist",
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
            }
        try:
            connection = _connect_readonly_sqlite(repository.db_path)
            try:
                tables = _readonly_sqlite_tables(connection)
                task_total = _readonly_sqlite_count(connection, "ai_tasks") if "ai_tasks" in tables else 0
                artifact_total = _readonly_sqlite_count(connection, "artifacts") if "artifacts" in tables else 0
                review_audit_total = (
                    _readonly_sqlite_count(connection, "review_audit_events")
                    if "review_audit_events" in tables
                    else 0
                )
                operation_audit_total = (
                    _readonly_sqlite_count(connection, "operation_audit_events")
                    if "operation_audit_events" in tables
                    else 0
                )
                agent_entity_total = (
                    _readonly_sqlite_count(connection, "agent_entities")
                    if "agent_entities" in tables
                    else 0
                )
                tasks_by_status = (
                    _readonly_sqlite_count_by_column(connection, "ai_tasks", "status")
                    if "ai_tasks" in tables
                    else {}
                )
                tasks_by_type = (
                    _readonly_sqlite_count_by_column(connection, "ai_tasks", "task_type")
                    if "ai_tasks" in tables
                    else {}
                )
                artifacts_by_kind = (
                    _readonly_sqlite_count_by_column(connection, "artifacts", "kind")
                    if "artifacts" in tables
                    else {}
                )
                agent_entities_by_type = (
                    _readonly_sqlite_count_by_column(connection, "agent_entities", "entity_type")
                    if "agent_entities" in tables
                    else {}
                )
                agent_entities_by_status = (
                    _readonly_sqlite_count_by_column(connection, "agent_entities", "status")
                    if "agent_entities" in tables
                    else {}
                )
                schema_version = (
                    _readonly_backend_core_schema_version(connection)
                    if "backend_core_meta" in tables
                    else None
                )
            finally:
                connection.close()
        except sqlite3.Error as exc:
            return {
                "available": False,
                "dbPath": str(repository.db_path),
                "errorCode": "BACKEND_CORE_SQLITE_READONLY_ERROR",
                "errors": [{"field": "coreDbPath", "reason": str(exc)}],
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
            }
        return {
            "available": True,
            "dbPath": str(repository.db_path),
            "schemaVersion": schema_version,
            "tables": tables,
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
            "mode": "LOCAL_SQLITE_BACKEND_CORE_REPOSITORY_READONLY",
            "safety": {
                "localSqliteOnly": True,
                "readOnly": True,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }

    def list_ai_task_payloads(
        self,
        repository: BackendCoreRepositoryContract,
        *,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_readonly_available(repository)
        return [task.to_dict() for task in repository.list_ai_tasks(status=status, task_type=task_type)]

    def get_ai_task_payload(
        self,
        repository: BackendCoreRepositoryContract,
        task_id: str,
    ) -> dict[str, Any] | None:
        self.ensure_readonly_available(repository)
        task = repository.get_ai_task(task_id)
        return task.to_dict() if task is not None else None

    def list_artifact_payloads(
        self,
        repository: BackendCoreRepositoryContract,
        *,
        kind: str | None = None,
        task_id: str | None = None,
        trace_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_readonly_available(repository)
        artifacts = [
            artifact.to_dict()
            for artifact in repository.list_artifacts(kind=kind, task_id=task_id, trace_id=trace_id)
        ]
        if workflow_run_id is None:
            return artifacts
        return [artifact for artifact in artifacts if artifact.get("workflowRunId") == workflow_run_id]

    def get_artifact_payload(
        self,
        repository: BackendCoreRepositoryContract,
        artifact_id: str,
    ) -> dict[str, Any] | None:
        self.ensure_readonly_available(repository)
        artifact = repository.get_artifact(artifact_id)
        return artifact.to_dict() if artifact is not None else None

    def list_review_audit_event_payloads(
        self,
        repository: BackendCoreRepositoryContract,
        *,
        task_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_readonly_available(repository)
        return [
            event.to_dict()
            for event in repository.list_review_audit_events(task_id=task_id, action=action, actor=actor)
        ]

    def list_operation_audit_event_payloads(
        self,
        repository: BackendCoreRepositoryContract,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_readonly_available(repository)
        return [
            event.to_dict()
            for event in repository.list_operation_audit_events(
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                actor=actor,
            )
        ]

    def list_agent_entity_payloads(
        self,
        repository: BackendCoreRepositoryContract,
        *,
        entity_type: str | None = None,
        source_task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_readonly_available(repository)
        return [
            entity.to_dict()
            for entity in repository.list_agent_entities(
                entity_type=entity_type,
                source_task_id=source_task_id,
                trace_id=trace_id,
            )
        ]

    def get_agent_entity_payload(
        self,
        repository: BackendCoreRepositoryContract,
        entity_id: str,
    ) -> dict[str, Any] | None:
        self.ensure_readonly_available(repository)
        entity = repository.get_agent_entity(entity_id)
        return entity.to_dict() if entity is not None else None

    def ensure_readonly_available(self, repository: BackendCoreRepositoryContract) -> None:
        if repository.db_path is None:
            repository.summary()
            return
        _connect_readonly_sqlite(repository.db_path).close()

    def readonly_query(
        self,
        repository: BackendCoreRepositoryContract,
        table: str,
        *,
        filters: dict[str, str | None] | None = None,
        order_by: str,
    ) -> list[dict[str, Any]]:
        return self._readonly_query(repository, table, filters=filters, order_by=order_by)

    def _readonly_query(
        self,
        repository: BackendCoreRepositoryContract,
        table: str,
        *,
        filters: dict[str, str | None] | None = None,
        order_by: str,
    ) -> list[dict[str, Any]]:
        if repository.db_path is None:
            raise CoreRepositoryError(
                "BACKEND_CORE_REPOSITORY_READONLY_UNSUPPORTED",
                "Backend Core repository 不支持 SQLite 原生只读查询",
                [{"field": "repositoryKind", "reason": "adapter-specific repository"}],
            )
        connection = _connect_readonly_sqlite(repository.db_path)
        try:
            tables = _readonly_sqlite_tables(connection)
            if table not in tables:
                return []
            query = f"SELECT raw_json FROM {table}"
            values: list[Any] = []
            where: list[str] = []
            for column, value in (filters or {}).items():
                if value is None:
                    continue
                where.append(f"{column} = ?")
                values.append(value)
            if where:
                query += " WHERE " + " AND ".join(where)
            query += f" ORDER BY {order_by} DESC"
            rows = connection.execute(query, values).fetchall()
        finally:
            connection.close()
        return [json.loads(row["raw_json"]) for row in rows]

    def readonly_get(
        self,
        repository: BackendCoreRepositoryContract,
        table: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self._readonly_get(repository, table, record_id)

    def _readonly_get(
        self,
        repository: BackendCoreRepositoryContract,
        table: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        if repository.db_path is None:
            raise CoreRepositoryError(
                "BACKEND_CORE_REPOSITORY_READONLY_UNSUPPORTED",
                "Backend Core repository 不支持 SQLite 原生只读查询",
                [{"field": "repositoryKind", "reason": "adapter-specific repository"}],
            )
        connection = _connect_readonly_sqlite(repository.db_path)
        try:
            tables = _readonly_sqlite_tables(connection)
            if table not in tables:
                return None
            row = connection.execute(f"SELECT raw_json FROM {table} WHERE id = ?", (record_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return json.loads(row["raw_json"])


def _connect_readonly_sqlite(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _looks_like_windows_drive_path(value: str) -> bool:
    return len(value) >= 3 and value[0].isalpha() and value[1] == ":" and value[2] in {"/", "\\"}


def _readonly_sqlite_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return [str(row["name"]) for row in rows]


def _readonly_sqlite_count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    return int(row["total"]) if row is not None else 0


def _readonly_sqlite_count_by_column(connection: sqlite3.Connection, table: str, column: str) -> dict[str, int]:
    rows = connection.execute(f"SELECT {column} AS value, COUNT(*) AS total FROM {table} GROUP BY {column}").fetchall()
    return {str(row["value"]): int(row["total"]) for row in rows}


def _readonly_backend_core_schema_version(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT value FROM backend_core_meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        return None
    return str(row["value"])
