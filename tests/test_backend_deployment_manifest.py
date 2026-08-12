import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manifest():
    with (ROOT / "backend/deployment.manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_backend_deployment_manifest_registers_core_entrypoints():
    manifest = load_manifest()
    entrypoints = {entry["id"]: entry for entry in manifest["entrypoints"]}

    assert manifest["kind"] == "BackendDeploymentManifest"
    assert manifest["status"] == "LOCAL_STAGING_READY"
    assert entrypoints["standard_library_http_dev"]["command"] == (
        "python -m backend.mock_http_server --host 127.0.0.1 --port 8000"
    )
    assert entrypoints["standard_library_http_dev"]["productionReady"] is False
    assert entrypoints["framework_neutral_backend_app"]["module"] == "backend.app"
    assert entrypoints["framework_neutral_backend_app"]["class"] == "BackendApiApp"
    assert entrypoints["asgi_app"]["target"] == "backend.asgi_app:app"
    assert entrypoints["asgi_app"]["requiresExternalAsgiServer"] is True


def test_backend_deployment_manifest_documents_env_without_secret_values():
    manifest = load_manifest()
    variables = {item["name"]: item for item in manifest["environmentVariables"]}

    assert variables["LAB_BACKEND_API_TOKEN"]["secret"] is True
    assert variables["LAB_BACKEND_API_TOKEN"]["responseEchoAllowed"] is False
    assert variables["LAB_BACKEND_CORE_DATABASE_URL"]["secret"] is True
    assert "postgresql" in variables["LAB_BACKEND_CORE_DATABASE_URL"]["allowedSchemes"]
    assert variables["LAB_BACKEND_CORE_POSTGRESQL_SMOKE"]["secret"] is False

    raw = json.dumps(manifest, ensure_ascii=False)
    assert "sk-" not in raw
    assert "api_key" not in raw.lower()
    assert "token=" not in raw.lower()


def test_backend_deployment_manifest_links_ci_and_safety_stop_line():
    manifest = load_manifest()

    assert (ROOT / manifest["ci"]["postgresqlSmokeWorkflow"]).exists()
    assert (ROOT / manifest["ci"]["coreRegressionMatrixWorkflow"]).exists()
    assert manifest["ci"]["usesEphemeralPostgresService"] is True
    assert manifest["ci"]["requiresRepositorySecrets"] is False
    assert manifest["ci"]["coreRegressionMatrixCommand"] == (
        "python lab_cli.py quality regression-matrix --profile core --stop-on-failure "
        "--output examples/output/regression-matrix-core.json"
    )
    assert manifest["ci"]["coreRegressionMatrixArtifact"] == "core-regression-matrix-report"
    assert manifest["ci"]["externalCiResultRecorded"] is False
    assert manifest["ci"]["asgiMountSmokeCommand"] == "python -m pytest tests/test_backend_asgi_mount_smoke.py -q"
    assert manifest["ci"]["asgiMountSmokeEvidenceCommand"] == (
        "python lab_cli.py backend-core asgi-smoke --output examples/output/backend-asgi-smoke-report.json"
    )
    assert manifest["safety"]["productionDatabaseWritten"] is False
    assert manifest["safety"]["autoPublishAllowed"] is False
    assert "Do not add another deployment shell" in manifest["stopLine"]


def test_backend_deployment_manifest_registers_asgi_mount_smoke():
    manifest = load_manifest()
    mount = manifest["testEnvironmentMount"]

    assert mount["status"] == "IN_PROCESS_ASGI_SMOKE_READY"
    assert mount["target"] == "backend.asgi_app:app"
    assert (ROOT / mount["smokeTest"]).exists()
    assert mount["smokeEvidenceCommand"] == (
        "python lab_cli.py backend-core asgi-smoke --output examples/output/backend-asgi-smoke-report.json"
    )
    assert mount["coveredApiGroups"] == [
        "health",
        "backend-core-readiness",
        "backend-core-db",
        "mcp-server",
        "ai-tasks-auth",
    ]
    assert mount["networkListenerStartedBySmoke"] is False
    assert mount["productionDatabaseWritten"] is False
    assert mount["requiresRepositorySecrets"] is False
    assert "Do not add another ASGI mount shell" in mount["stopLine"]
