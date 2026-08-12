"""Backend Core PostgreSQL migration helpers.

This module turns the PostgreSQL repository adapter into an explicit migration
entry point for test/staging databases. It does not register the adapter in the
default HTTP mock app, so external database access remains opt-in.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from cli.artifact import ArtifactKind

from backend.core_contract import (
    BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
    BackendCoreRepositoryConfig,
    BackendCoreRepositoryFactory,
)
from backend.core_postgres_repository import (
    PostgreSQLConnector,
    create_backend_core_postgresql_repository,
)
from backend.core_repository import CoreRepositoryError
from backend.core_service import BACKEND_CORE_DATABASE_URL_ENV, BACKEND_CORE_DATABASE_URL_SOURCE, BackendCoreService
from backend.core_task_service import BackendCoreTaskService, CoreArtifactInput


BACKEND_CORE_POSTGRESQL_MIGRATION_PLAN_MODE = "BACKEND_CORE_POSTGRESQL_MIGRATION_PLAN"
BACKEND_CORE_POSTGRESQL_SCHEMA_INIT_MODE = "BACKEND_CORE_POSTGRESQL_SCHEMA_INIT"
BACKEND_CORE_POSTGRESQL_SCHEMA_SUMMARY_MODE = "BACKEND_CORE_POSTGRESQL_SCHEMA_SUMMARY"
BACKEND_CORE_POSTGRESQL_SMOKE_MODE = "BACKEND_CORE_POSTGRESQL_SMOKE"


def build_postgresql_repository_factory(
    *,
    connector: PostgreSQLConnector | None = None,
) -> BackendCoreRepositoryFactory:
    return BackendCoreRepositoryFactory(
        adapters={
            BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL: lambda config: create_backend_core_postgresql_repository(
                config.database_url or "",
                database_url_summary=config.database_url_summary,
                connector=connector,
            )
        }
    )


def build_postgresql_migration_plan(
    root: Path,
    *,
    database_url_env: str = BACKEND_CORE_DATABASE_URL_ENV,
) -> dict[str, Any]:
    database_url = _require_database_url(database_url_env)
    service = BackendCoreService(root)
    resolution = service.resolve_database_url(database_url)
    if resolution.repository_kind != BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL:
        raise CoreRepositoryError(
            "BACKEND_CORE_POSTGRESQL_DATABASE_URL_UNSUPPORTED",
            "Backend Core PostgreSQL 迁移只接受 postgresql URL",
            [
                {
                    "field": database_url_env,
                    "reason": f"expected postgresql, got {resolution.repository_kind}",
                }
            ],
        )
    return {
        "mode": BACKEND_CORE_POSTGRESQL_MIGRATION_PLAN_MODE,
        "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
        "databaseUrlEnv": database_url_env,
        "databaseUrlConfigured": True,
        "databaseUrlSummary": resolution.summary,
        "adapter": {
            "module": "backend.core_postgres_repository",
            "factory": "create_backend_core_postgresql_repository",
            "registeredByDefaultInHttpMock": False,
        },
        "driver": {
            "package": "psycopg[binary]",
            "module": "psycopg",
            "installed": importlib.util.find_spec("psycopg") is not None,
        },
        "plannedActions": [
            "register_postgresql_adapter_in_factory",
            "initialize_backend_core_schema",
            "read_backend_core_summary",
        ],
        "schemaTables": [
            "backend_core_meta",
            "ai_tasks",
            "artifacts",
            "review_audit_events",
            "operation_audit_events",
            "agent_entities",
        ],
        "requiresTestDatabase": True,
        "requiresExplicitInitCommand": True,
        "networkAccess": False,
        "schemaWritePlanned": False,
        "productionDatabaseWritten": False,
        "productionQueueUsed": False,
        "secretValueReturned": False,
    }


def initialize_postgresql_backend_core_repository(
    root: Path,
    *,
    database_url_env: str = BACKEND_CORE_DATABASE_URL_ENV,
    connector: PostgreSQLConnector | None = None,
) -> dict[str, Any]:
    plan = build_postgresql_migration_plan(root, database_url_env=database_url_env)
    repository = _create_postgresql_repository(root, database_url_env=database_url_env, connector=connector)
    summary = repository.initialize_schema()
    return {
        "mode": BACKEND_CORE_POSTGRESQL_SCHEMA_INIT_MODE,
        "postgresqlMigrationPlan": plan,
        "backendCoreRepository": summary,
        "schemaInitialized": True,
        "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
        "databaseUrlEnv": database_url_env,
        "databaseUrlSummary": plan["databaseUrlSummary"],
        "networkAccess": True,
        "externalDatabaseWritten": True,
        "productionDatabaseWritten": False,
        "productionQueueUsed": False,
        "secretValueReturned": False,
        "autoApproveAllowed": False,
        "realPublish": False,
    }


def summarize_postgresql_backend_core_repository(
    root: Path,
    *,
    database_url_env: str = BACKEND_CORE_DATABASE_URL_ENV,
    connector: PostgreSQLConnector | None = None,
) -> dict[str, Any]:
    plan = build_postgresql_migration_plan(root, database_url_env=database_url_env)
    repository = _create_postgresql_repository(root, database_url_env=database_url_env, connector=connector)
    summary = repository.summary()
    return {
        "mode": BACKEND_CORE_POSTGRESQL_SCHEMA_SUMMARY_MODE,
        "postgresqlMigrationPlan": plan,
        "backendCoreRepository": summary,
        "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
        "databaseUrlEnv": database_url_env,
        "databaseUrlSummary": plan["databaseUrlSummary"],
        "networkAccess": True,
        "externalDatabaseRead": True,
        "externalDatabaseWritten": False,
        "productionDatabaseWritten": False,
        "productionQueueUsed": False,
        "secretValueReturned": False,
        "autoApproveAllowed": False,
        "realPublish": False,
    }


def run_postgresql_backend_core_smoke(
    root: Path,
    *,
    database_url_env: str = BACKEND_CORE_DATABASE_URL_ENV,
    reviewer: str = "backend_core_postgresql_smoke",
    connector: PostgreSQLConnector | None = None,
) -> dict[str, Any]:
    plan = build_postgresql_migration_plan(root, database_url_env=database_url_env)
    repository = _create_postgresql_repository(root, database_url_env=database_url_env, connector=connector)
    init_summary = repository.initialize_schema()
    service = BackendCoreTaskService(repository)
    created = service.create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Backend Core PostgreSQL smoke task",
        input_type="smoke",
        input_ref="backend-core-postgresql-smoke",
        actor=reviewer,
        final_result_path="examples/output/backend-core-postgresql-smoke-lab.json",
        artifacts=[
            CoreArtifactInput(
                kind=ArtifactKind.LAB_DSL,
                path="examples/output/backend-core-postgresql-smoke-lab.json",
                title="Backend Core PostgreSQL smoke Lab DSL",
                metadata={
                    "schemaValidated": True,
                    "smokeTest": True,
                    "databaseUrlEnv": database_url_env,
                },
                mode=BACKEND_CORE_POSTGRESQL_SMOKE_MODE,
            )
        ],
    )
    reviewed = service.review_task(
        task_id=created["task"].id,
        reviewer=reviewer,
        decision="approve",
        trace_id=created["task"].traceId,
    )
    summary = repository.summary()
    task = repository.get_ai_task(created["task"].id)
    artifacts = repository.list_artifacts(task_id=created["task"].id)
    review_audits = repository.list_review_audit_events(task_id=created["task"].id)
    operation_audits = repository.list_operation_audit_events(
        resource_type="AI_TASK",
        resource_id=created["task"].id,
    )
    return {
        "mode": BACKEND_CORE_POSTGRESQL_SMOKE_MODE,
        "postgresqlMigrationPlan": plan,
        "initSummary": init_summary,
        "backendCoreRepository": summary,
        "repositoryKind": BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
        "databaseUrlEnv": database_url_env,
        "databaseUrlSummary": plan["databaseUrlSummary"],
        "createdTask": {
            "id": created["task"].id,
            "status": created["task"].status.value,
            "artifactTotal": len(created["artifacts"]),
            "operationAuditEventId": created["operationAuditEvent"].id,
        },
        "reviewedTask": {
            "id": reviewed["task"].id,
            "status": reviewed["task"].status.value,
            "reviewAuditEventId": reviewed["reviewAuditEvent"].id,
            "operationAuditEventId": reviewed["operationAuditEvent"].id,
        },
        "roundTrip": {
            "taskLoaded": task is not None,
            "taskStatus": task.status.value if task is not None else None,
            "artifactListed": len(artifacts) >= 1,
            "reviewAuditListed": len(review_audits) >= 1,
            "operationAuditListed": len(operation_audits) >= 2,
        },
        "networkAccess": True,
        "externalDatabaseWritten": True,
        "externalDatabaseRead": True,
        "productionDatabaseWritten": False,
        "productionQueueUsed": False,
        "secretValueReturned": False,
        "autoApproveAllowed": False,
        "realPublish": False,
    }


def _create_postgresql_repository(
    root: Path,
    *,
    database_url_env: str,
    connector: PostgreSQLConnector | None,
):
    database_url = _require_database_url(database_url_env)
    service = BackendCoreService(root)
    resolution = service.resolve_database_url(database_url)
    config = BackendCoreRepositoryConfig(
        kind=BACKEND_CORE_REPOSITORY_KIND_POSTGRESQL,
        db_path=None,
        source=BACKEND_CORE_DATABASE_URL_SOURCE,
        database_url=database_url,
        database_url_summary=resolution.summary,
    )
    return build_postgresql_repository_factory(connector=connector).create(config)


def _require_database_url(database_url_env: str) -> str:
    database_url = os.environ.get(database_url_env, "").strip()
    if not database_url:
        raise CoreRepositoryError(
            "BACKEND_CORE_POSTGRESQL_DATABASE_URL_MISSING",
            "Backend Core PostgreSQL database URL 未配置",
            [{"field": database_url_env, "reason": "environment variable is required"}],
        )
    return database_url
