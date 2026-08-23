from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from backend.app import BackendApiApp
from cli.ai_task import TaskStatus, create_waiting_review_task
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.store import JsonTaskStore


PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _json_payload(response) -> dict:
    assert response.content_type == "application/json; charset=utf-8"
    return json.loads(response.body.decode("utf-8"))


@pytest.fixture
def ppt_artifact_route_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    workspace = tmp_path / "workspace"
    artifact_dir = workspace / "examples" / "output" / "teaching-presentations" / "deck_001"
    preview_dir = artifact_dir / "previews"
    preview_dir.mkdir(parents=True)
    monkeypatch.setenv("LAB_CLI_WORKSPACE", str(workspace))

    pptx_path = artifact_dir / "deck.pptx"
    contact_sheet_path = artifact_dir / "contact-sheet.png"
    preview_path = preview_dir / "slide-01.png"
    pptx_path.write_bytes(b"pptx-binary-content")
    contact_sheet_path.write_bytes(b"contact-sheet-png")
    preview_path.write_bytes(b"slide-preview-png")

    store_path = tmp_path / "store.json"
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Teaching presentation",
        input_type="TEACHING_PACKAGE",
        input_ref="workflow_source_001",
        final_result_path=str(pptx_path),
        trace_id="trace_ppt_routes_001",
    )
    store.save(task)
    artifact = create_artifact_record(
        kind=ArtifactKind.PPTX_FILE,
        path=str(pptx_path),
        title="Teaching presentation PPTX",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id=task.traceId,
        task_id=task.id,
        workflow_run_id="workflow_presentation_001",
        metadata={
            "artifactProfile": "presentation-deck",
            "slideCount": 1,
            "sha256": sha256(pptx_path.read_bytes()).hexdigest(),
            "slidePreviews": [
                {
                    "index": 1,
                    "imagePath": str(preview_path),
                    "sha256": sha256(preview_path.read_bytes()).hexdigest(),
                }
            ],
            "contactSheet": {
                "path": str(contact_sheet_path),
                "sha256": sha256(contact_sheet_path.read_bytes()).hexdigest(),
            },
        },
    )
    store.save_artifact(artifact)

    return {
        "app": BackendApiApp(store_path=store_path),
        "artifact": artifact,
        "store": store,
        "task": task,
        "workspace": workspace,
        "pptxPath": pptx_path,
        "contactSheetPath": contact_sheet_path,
        "previewPath": preview_path,
    }


def test_ppt_artifact_route_rejects_unknown_artifact(tmp_path: Path) -> None:
    response = BackendApiApp(store_path=tmp_path / "store.json").handle(
        "GET",
        "/api/ppt-artifacts/artifact_missing/contact-sheet",
    )

    payload = _json_payload(response)
    assert response.status == 404
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"] == [{"field": "artifactId", "reason": "not found"}]


def test_ppt_artifact_routes_require_configured_backend_token(
    ppt_artifact_route_fixture: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = ppt_artifact_route_fixture["app"]
    artifact = ppt_artifact_route_fixture["artifact"]
    route = f"/api/ppt-artifacts/{artifact.id}/previews/1"
    monkeypatch.setenv("LAB_BACKEND_API_TOKEN", "ppt-route-token")

    missing = app.handle("GET", route)
    invalid = app.handle("GET", route, headers={"Authorization": "Bearer wrong-token"})
    authorized = app.handle("GET", route, headers={"Authorization": "Bearer ppt-route-token"})

    assert missing.status == 401
    assert _json_payload(missing)["code"] == "AUTH_REQUIRED"
    assert invalid.status == 401
    assert _json_payload(invalid)["code"] == "AUTH_INVALID"
    assert authorized.status == 200
    assert authorized.body == ppt_artifact_route_fixture["previewPath"].read_bytes()
    assert b"ppt-route-token" not in missing.body + invalid.body + authorized.body


@pytest.mark.parametrize("slide_index", [0, 2, 999])
def test_ppt_preview_route_rejects_out_of_bounds_slide_index(
    ppt_artifact_route_fixture: dict,
    slide_index: int,
) -> None:
    artifact = ppt_artifact_route_fixture["artifact"]
    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{artifact.id}/previews/{slide_index}",
    )

    payload = _json_payload(response)
    assert response.status == 404
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"] == [{"field": "artifactId", "reason": artifact.id}]


@pytest.mark.parametrize(
    ("route", "registered_field"),
    [
        ("download", "pptx"),
        ("contact-sheet", "contactSheet"),
        ("previews/1", "preview"),
    ],
)
def test_ppt_artifact_routes_reject_registered_paths_outside_workspace(
    ppt_artifact_route_fixture: dict,
    tmp_path: Path,
    route: str,
    registered_field: str,
) -> None:
    store = ppt_artifact_route_fixture["store"]
    task = ppt_artifact_route_fixture["task"]
    artifact = ppt_artifact_route_fixture["artifact"]
    outside_path = tmp_path / "outside" / ("deck.pptx" if registered_field == "pptx" else "preview.png")
    outside_path.parent.mkdir(parents=True, exist_ok=True)
    outside_path.write_bytes(b"must-not-be-served")

    if registered_field == "pptx":
        task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
        store.save(task)
        artifact.path = str(outside_path)
    elif registered_field == "contactSheet":
        artifact.metadata["contactSheet"] = {"path": str(outside_path)}
    else:
        artifact.metadata["slidePreviews"][0]["imagePath"] = str(outside_path)
    store.save_artifact(artifact)

    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{artifact.id}/{route}",
    )

    payload = _json_payload(response)
    assert response.status == 404
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"] == [{"field": "artifactId", "reason": artifact.id}]
    assert b"must-not-be-served" not in response.body


def test_ppt_preview_and_contact_sheet_routes_return_png_mime(
    ppt_artifact_route_fixture: dict,
) -> None:
    app = ppt_artifact_route_fixture["app"]
    artifact = ppt_artifact_route_fixture["artifact"]

    preview = app.handle("GET", f"/api/ppt-artifacts/{artifact.id}/previews/1")
    contact_sheet = app.handle("GET", f"/api/ppt-artifacts/{artifact.id}/contact-sheet")

    assert preview.status == 200
    assert preview.content_type == "image/png"
    assert preview.body == ppt_artifact_route_fixture["previewPath"].read_bytes()
    assert contact_sheet.status == 200
    assert contact_sheet.content_type == "image/png"
    assert contact_sheet.body == ppt_artifact_route_fixture["contactSheetPath"].read_bytes()


def test_ppt_download_is_blocked_until_deck_task_is_approved(
    ppt_artifact_route_fixture: dict,
) -> None:
    artifact = ppt_artifact_route_fixture["artifact"]
    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{artifact.id}/download",
    )

    payload = _json_payload(response)
    assert response.status == 400
    assert payload["success"] is False
    assert payload["code"] == "PPT_ARTIFACT_DOWNLOAD_BLOCKED"
    assert payload["errors"] == [{"field": "task.status", "reason": "must be APPROVED"}]
    assert response.body != ppt_artifact_route_fixture["pptxPath"].read_bytes()


def test_ppt_download_returns_binary_after_deck_task_is_approved(
    ppt_artifact_route_fixture: dict,
) -> None:
    store = ppt_artifact_route_fixture["store"]
    task = ppt_artifact_route_fixture["task"]
    artifact = ppt_artifact_route_fixture["artifact"]
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
    store.save(task)

    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{artifact.id}/download",
    )

    assert response.status == 200
    assert response.content_type == PPTX_MIME
    assert response.payload is None
    assert response.body == ppt_artifact_route_fixture["pptxPath"].read_bytes()


@pytest.mark.parametrize(
    ("route", "path_key"),
    [
        ("previews/1", "previewPath"),
        ("contact-sheet", "contactSheetPath"),
        ("download", "pptxPath"),
    ],
)
def test_product_ppt_artifact_routes_reject_tampered_registered_bytes(
    ppt_artifact_route_fixture: dict,
    route: str,
    path_key: str,
) -> None:
    if route == "download":
        task = ppt_artifact_route_fixture["task"]
        task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
        ppt_artifact_route_fixture["store"].save(task)
    ppt_artifact_route_fixture[path_key].write_bytes(b"tampered-after-review")

    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{ppt_artifact_route_fixture['artifact'].id}/{route}",
    )

    payload = _json_payload(response)
    assert response.status == 400
    assert payload["code"] == "PPT_ARTIFACT_INTEGRITY_ERROR"
    assert payload["errors"] == [{"field": "artifactId", "reason": "registered SHA-256 mismatch"}]
    assert b"tampered-after-review" not in response.body


def test_product_ppt_download_fails_closed_without_registered_digest(
    ppt_artifact_route_fixture: dict,
) -> None:
    store = ppt_artifact_route_fixture["store"]
    task = ppt_artifact_route_fixture["task"]
    artifact = ppt_artifact_route_fixture["artifact"]
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
    store.save(task)
    artifact.metadata.pop("sha256")
    store.save_artifact(artifact)

    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{artifact.id}/download",
    )

    payload = _json_payload(response)
    assert response.status == 400
    assert payload["code"] == "PPT_ARTIFACT_INTEGRITY_ERROR"
    assert payload["errors"] == [{"field": "artifactId", "reason": "registered SHA-256 is required"}]


def test_product_ppt_preview_cannot_downgrade_integrity_by_removing_profile(
    ppt_artifact_route_fixture: dict,
) -> None:
    store = ppt_artifact_route_fixture["store"]
    task = ppt_artifact_route_fixture["task"]
    artifact = ppt_artifact_route_fixture["artifact"]
    task.inputType = "teaching_package_workflow"
    store.save(task)
    artifact.metadata.pop("artifactProfile")
    artifact.metadata["slidePreviews"][0].pop("sha256")
    store.save_artifact(artifact)

    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{artifact.id}/previews/1",
    )

    payload = _json_payload(response)
    assert response.status == 400
    assert payload["code"] == "PPT_ARTIFACT_INTEGRITY_ERROR"
    assert payload["errors"] == [{"field": "artifactId", "reason": "registered SHA-256 is required"}]


def test_legacy_ppt_preview_without_digest_remains_compatible(
    ppt_artifact_route_fixture: dict,
) -> None:
    store = ppt_artifact_route_fixture["store"]
    artifact = ppt_artifact_route_fixture["artifact"]
    artifact.metadata.pop("artifactProfile")
    artifact.metadata["slidePreviews"][0].pop("sha256")
    store.save_artifact(artifact)

    response = ppt_artifact_route_fixture["app"].handle(
        "GET",
        f"/api/ppt-artifacts/{artifact.id}/previews/1",
    )

    assert response.status == 200
    assert response.body == ppt_artifact_route_fixture["previewPath"].read_bytes()
