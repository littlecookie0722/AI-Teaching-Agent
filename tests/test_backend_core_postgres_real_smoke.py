import json
import os

import pytest

from backend.core_postgres_migration import run_postgresql_backend_core_smoke
from backend.core_service import BACKEND_CORE_DATABASE_URL_ENV


@pytest.mark.integration
def test_backend_core_postgresql_real_smoke(tmp_path):
    if os.environ.get("LAB_BACKEND_CORE_POSTGRESQL_SMOKE") != "1":
        pytest.skip("set LAB_BACKEND_CORE_POSTGRESQL_SMOKE=1 to run real PostgreSQL smoke")
    if not os.environ.get(BACKEND_CORE_DATABASE_URL_ENV):
        pytest.skip(f"set {BACKEND_CORE_DATABASE_URL_ENV} to a test/staging PostgreSQL URL")

    result = run_postgresql_backend_core_smoke(
        tmp_path,
        reviewer=os.environ.get("LAB_BACKEND_CORE_POSTGRESQL_SMOKE_REVIEWER", "postgresql_smoke_ci"),
    )

    assert result["mode"] == "BACKEND_CORE_POSTGRESQL_SMOKE"
    assert result["roundTrip"]["taskLoaded"] is True
    assert result["roundTrip"]["taskStatus"] == "APPROVED"
    assert result["roundTrip"]["artifactListed"] is True
    assert result["roundTrip"]["reviewAuditListed"] is True
    assert result["roundTrip"]["operationAuditListed"] is True
    assert result["backendCoreRepository"]["schemaVersion"] == "1"
    assert result["backendCoreRepository"]["taskTotal"] >= 1
    assert result["productionDatabaseWritten"] is False
    assert result["secretValueReturned"] is False
    assert os.environ[BACKEND_CORE_DATABASE_URL_ENV] not in json.dumps(result, ensure_ascii=False)
