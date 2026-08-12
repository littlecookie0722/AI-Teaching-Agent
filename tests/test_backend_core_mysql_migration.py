import json

import pytest

from backend.core_mysql_migration import (
    build_mysql_migration_plan,
    initialize_mysql_backend_core_repository,
    run_mysql_backend_core_smoke,
    summarize_mysql_backend_core_repository,
)
from backend.core_repository import CoreRepositoryError
from backend.core_service import BACKEND_CORE_DATABASE_URL_ENV
from tests.fakes_backend_mysql import FakeMySQLDatabase


def test_mysql_migration_plan_is_redacted_and_does_not_connect(monkeypatch, tmp_path):
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, "mysql://user:secret@example.invalid/prod")

    plan = build_mysql_migration_plan(tmp_path)

    assert plan["mode"] == "BACKEND_CORE_MYSQL_MIGRATION_PLAN"
    assert plan["repositoryKind"] == "mysql"
    assert plan["databaseUrlSummary"]["valueReturned"] is False
    assert plan["adapter"]["registeredByDefaultInHttpMock"] is False
    assert plan["requiresTestDatabase"] is True
    assert plan["networkAccess"] is False
    assert plan["schemaWritePlanned"] is False
    assert "user:secret" not in json.dumps(plan, ensure_ascii=False)


def test_mysql_migration_init_and_summary_use_connector(monkeypatch, tmp_path):
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, "mysql://user:secret@example.invalid/prod")
    database = FakeMySQLDatabase()

    init_result = initialize_mysql_backend_core_repository(
        tmp_path,
        connector=database.connect,
    )
    summary_result = summarize_mysql_backend_core_repository(
        tmp_path,
        connector=database.connect,
    )

    assert init_result["mode"] == "BACKEND_CORE_MYSQL_SCHEMA_INIT"
    assert init_result["schemaInitialized"] is True
    assert init_result["externalDatabaseWritten"] is True
    assert init_result["productionDatabaseWritten"] is False
    assert "ai_tasks" in database.tables
    assert summary_result["mode"] == "BACKEND_CORE_MYSQL_SCHEMA_SUMMARY"
    assert summary_result["backendCoreRepository"]["schemaVersion"] == "1"
    assert summary_result["backendCoreRepository"]["taskTotal"] == 0
    assert "user:secret" not in json.dumps(init_result, ensure_ascii=False)
    assert "user:secret" not in json.dumps(summary_result, ensure_ascii=False)


def test_mysql_smoke_round_trips_task_artifact_and_audit(monkeypatch, tmp_path):
    monkeypatch.setenv(BACKEND_CORE_DATABASE_URL_ENV, "mysql://user:secret@example.invalid/prod")
    database = FakeMySQLDatabase()

    smoke = run_mysql_backend_core_smoke(
        tmp_path,
        reviewer="teacher_smoke",
        connector=database.connect,
    )

    assert smoke["mode"] == "BACKEND_CORE_MYSQL_SMOKE"
    assert smoke["createdTask"]["status"] == "WAITING_REVIEW"
    assert smoke["reviewedTask"]["status"] == "APPROVED"
    assert smoke["roundTrip"] == {
        "taskLoaded": True,
        "taskStatus": "APPROVED",
        "artifactListed": True,
        "reviewAuditListed": True,
        "operationAuditListed": True,
    }
    assert smoke["backendCoreRepository"]["taskTotal"] == 1
    assert smoke["backendCoreRepository"]["artifactTotal"] == 1
    assert smoke["backendCoreRepository"]["reviewAuditTotal"] == 1
    assert smoke["backendCoreRepository"]["operationAuditTotal"] == 2
    assert smoke["externalDatabaseWritten"] is True
    assert smoke["productionDatabaseWritten"] is False
    assert "user:secret" not in json.dumps(smoke, ensure_ascii=False)


def test_mysql_migration_rejects_missing_database_url(monkeypatch, tmp_path):
    monkeypatch.delenv(BACKEND_CORE_DATABASE_URL_ENV, raising=False)

    with pytest.raises(CoreRepositoryError) as exc_info:
        build_mysql_migration_plan(tmp_path)

    assert exc_info.value.code == "BACKEND_CORE_MYSQL_DATABASE_URL_MISSING"
    assert exc_info.value.errors == [
        {"field": BACKEND_CORE_DATABASE_URL_ENV, "reason": "environment variable is required"}
    ]
