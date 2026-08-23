from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import pytest

from backend.mock_api import handle_request
from cli.ai_task import TaskStatus
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.audit import OperationAction
from cli.store import JsonTaskStore
from cli.teaching_package_export import (
    ENTRY_NAMES,
    TeachingPackageExportError,
    export_teaching_package,
)


CORE_ARTIFACT_KINDS = {
    "lab": ArtifactKind.LAB_DSL,
    "exam": ArtifactKind.EXAM_DSL,
    "grading": ArtifactKind.GRADING_DSL,
}


def _create_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    artifact_profile: str = "teaching-core",
    approve: bool = False,
) -> tuple[JsonTaskStore, dict, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    workspace = tmp_path / "workspace"
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Validation Lab\n\nTeach a small Python validation workflow.\n", encoding="utf-8")
    monkeypatch.setenv("LAB_CLI_WORKSPACE", str(workspace))

    generated = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={
            "input": str(source),
            "reviewer": "teacher_generate",
            "artifactProfile": artifact_profile,
        },
    )
    assert generated["success"] is True
    run_id = generated["data"]["workflowRun"]["id"]
    store = JsonTaskStore(store_path)

    provider_generations = generated["data"]["report"]["providerGenerations"]
    for kind, artifact_kind in CORE_ARTIFACT_KINDS.items():
        dsl_path = tmp_path / f"{run_id}-{kind}.json"
        dsl_path.write_text(
            json.dumps(provider_generations[kind]["dsl"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        artifact = next(
            item
            for item in store.list_artifacts(workflow_run_id=run_id)
            if item.kind == artifact_kind
        )
        artifact.path = str(dsl_path)
        store.save_artifact(artifact)

    if approve:
        for task in generated["data"]["createdTasks"]:
            approved = handle_request(
                "POST",
                f"/api/ai-tasks/{task['id']}/approve",
                store_path=store_path,
                body={"reviewer": "teacher_review"},
            )
            assert approved["success"] is True

    return store, generated, workspace


def _json_entry(archive: ZipFile, name: str) -> dict:
    return json.loads(archive.read(name).decode("utf-8"))


def _iter_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _iter_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


def _assert_error(exc: pytest.ExceptionInfo[TeachingPackageExportError], code: str) -> None:
    assert exc.value.code == code
    assert exc.value.errors


def test_export_builds_deterministic_six_file_package_and_audits_each_export(tmp_path, monkeypatch):
    store, generated, workspace = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]

    first = export_teaching_package(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_export_1",
        trace_id="trace_export_first",
    )
    second = export_teaching_package(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_export_2",
        trace_id="trace_export_second",
    )

    output = Path(first["outputPath"])
    assert output == workspace / "examples" / "output" / "teaching-packages" / f"{run_id}.zip"
    assert output.is_file()
    assert first["fileName"] == output.name
    assert first["sha256"] == second["sha256"] == sha256(output.read_bytes()).hexdigest()
    assert first["sizeBytes"] == second["sizeBytes"] == output.stat().st_size
    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert first["artifactId"] == second["artifactId"]
    assert first["operationAuditEventId"] != second["operationAuditEventId"]
    assert first["candidateSafety"] == {
        "candidateSafe": True,
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
    }
    assert first["safety"]["networkAccess"] is False
    assert first["safety"]["sandboxExecuted"] is False
    assert first["safety"]["contestantCodeExecuted"] is False
    assert first["safety"]["taskStatusChanged"] is False
    assert first["safety"]["realPublish"] is False

    with ZipFile(output) as archive:
        assert tuple(archive.namelist()) == ENTRY_NAMES
        assert {info.date_time for info in archive.infolist()} == {(1980, 1, 1, 0, 0, 0)}
        manifest = _json_entry(archive, "manifest.json")
        lab = _json_entry(archive, "lab.json")
        exam = _json_entry(archive, "exam.json")
        grading = _json_entry(archive, "grading.json")
        preview = _json_entry(archive, "exam-candidate-preview.json")
        review = _json_entry(archive, "review-summary.json")

    assert manifest["entryNames"] == list(ENTRY_NAMES)
    assert manifest["entryCount"] == 6
    assert "reviewer" not in manifest
    assert "exportedAt" not in manifest
    assert manifest["safety"]["networkAccess"] is False
    assert exam["metadata"]["sourceLabId"] == lab["metadata"]["id"]
    assert grading["metadata"]["sourceExamId"] == exam["metadata"]["id"]
    assert lab["spec"]["grading"]["ref"] == grading["metadata"]["id"]
    assert "answer" in exam["spec"]["questions"][0]
    assert "gradingRef" in exam["spec"]["questions"][0]
    assert not ({"answer", "standardAnswer", "solution", "referenceAnswer", "gradingRef"} & set(_iter_keys(preview)))
    assert preview["redaction"]["candidateSafe"] is True
    assert review["status"] == "APPROVED"
    assert review["exportReady"] is True
    assert {item["status"] for item in review["artifacts"].values()} == {"APPROVED"}

    package_artifacts = store.list_artifacts(
        kind=ArtifactKind.TEACHING_PACKAGE_ZIP.value,
        workflow_run_id=run_id,
    )
    export_audits = store.list_operation_audit_events(action=OperationAction.TEACHING_PACKAGE_EXPORT.value)
    assert len(package_artifacts) == 1
    assert package_artifacts[0].status == ArtifactStatus.COMPLETED
    assert [event.actor for event in export_audits] == ["teacher_export_2", "teacher_export_1"]
    assert {store.get(task["id"]).status for task in generated["data"]["createdTasks"]} == {TaskStatus.APPROVED}


def test_export_blocks_unknown_unapproved_and_legacy_runs_without_output(tmp_path, monkeypatch):
    empty_store = JsonTaskStore(tmp_path / "empty-store.json")
    with pytest.raises(TeachingPackageExportError) as unknown:
        export_teaching_package(empty_store, workflow_run_id="workflow_run_missing", reviewer="teacher")
    _assert_error(unknown, "NOT_FOUND")

    store, generated, workspace = _create_workflow(tmp_path / "pending", monkeypatch)
    run_id = generated["data"]["workflowRun"]["id"]
    with pytest.raises(TeachingPackageExportError) as pending:
        export_teaching_package(store, workflow_run_id=run_id, reviewer="teacher")
    _assert_error(pending, "TEACHING_PACKAGE_EXPORT_NOT_READY")
    assert not (workspace / "examples" / "output" / "teaching-packages" / f"{run_id}.zip").exists()
    assert store.list_artifacts(kind=ArtifactKind.TEACHING_PACKAGE_ZIP.value) == []
    assert store.list_operation_audit_events(action=OperationAction.TEACHING_PACKAGE_EXPORT.value) == []

    rejected = handle_request(
        "POST",
        f"/api/ai-tasks/{generated['data']['createdTasks'][0]['id']}/reject",
        store_path=tmp_path / "pending" / "store.json",
        body={"reviewer": "teacher_review", "reason": "needs revision"},
    )
    assert rejected["success"] is True
    with pytest.raises(TeachingPackageExportError) as rejected_error:
        export_teaching_package(store, workflow_run_id=run_id, reviewer="teacher")
    _assert_error(rejected_error, "TEACHING_PACKAGE_EXPORT_NOT_READY")

    legacy_store, legacy, legacy_workspace = _create_workflow(
        tmp_path / "legacy",
        monkeypatch,
        artifact_profile="legacy-all",
        approve=True,
    )
    legacy_run_id = legacy["data"]["workflowRun"]["id"]
    with pytest.raises(TeachingPackageExportError) as legacy_error:
        export_teaching_package(legacy_store, workflow_run_id=legacy_run_id, reviewer="teacher")
    _assert_error(legacy_error, "TEACHING_PACKAGE_NOT_EXPORTABLE")
    assert not (legacy_workspace / "examples" / "output" / "teaching-packages" / f"{legacy_run_id}.zip").exists()


def test_export_blocks_missing_and_schema_invalid_artifacts_without_partial_package(tmp_path, monkeypatch):
    missing_store, missing, missing_workspace = _create_workflow(tmp_path / "missing", monkeypatch, approve=True)
    missing_run_id = missing["data"]["workflowRun"]["id"]
    exam_artifact = next(
        item
        for item in missing_store.list_artifacts(workflow_run_id=missing_run_id)
        if item.kind == ArtifactKind.EXAM_DSL
    )
    Path(exam_artifact.path).unlink()
    with pytest.raises(TeachingPackageExportError) as missing_error:
        export_teaching_package(missing_store, workflow_run_id=missing_run_id, reviewer="teacher")
    _assert_error(missing_error, "TEACHING_PACKAGE_ARTIFACT_NOT_FOUND")
    assert not (missing_workspace / "examples" / "output" / "teaching-packages" / f"{missing_run_id}.zip").exists()

    schema_store, schema, schema_workspace = _create_workflow(tmp_path / "schema", monkeypatch, approve=True)
    schema_run_id = schema["data"]["workflowRun"]["id"]
    lab_artifact = next(
        item
        for item in schema_store.list_artifacts(workflow_run_id=schema_run_id)
        if item.kind == ArtifactKind.LAB_DSL
    )
    lab = json.loads(Path(lab_artifact.path).read_text(encoding="utf-8"))
    del lab["metadata"]["title"]
    Path(lab_artifact.path).write_text(json.dumps(lab), encoding="utf-8")
    with pytest.raises(TeachingPackageExportError) as schema_error:
        export_teaching_package(schema_store, workflow_run_id=schema_run_id, reviewer="teacher")
    _assert_error(schema_error, "SCHEMA_VALIDATION_ERROR")
    assert not (schema_workspace / "examples" / "output" / "teaching-packages" / f"{schema_run_id}.zip").exists()


def test_export_blocks_cross_reference_and_candidate_grading_ref_leaks(tmp_path, monkeypatch):
    contract_store, contract, contract_workspace = _create_workflow(tmp_path / "contract", monkeypatch, approve=True)
    contract_run_id = contract["data"]["workflowRun"]["id"]
    exam_artifact = next(
        item
        for item in contract_store.list_artifacts(workflow_run_id=contract_run_id)
        if item.kind == ArtifactKind.EXAM_DSL
    )
    exam = json.loads(Path(exam_artifact.path).read_text(encoding="utf-8"))
    exam["metadata"]["sourceLabId"] = "lab_wrong"
    Path(exam_artifact.path).write_text(json.dumps(exam), encoding="utf-8")
    with pytest.raises(TeachingPackageExportError) as contract_error:
        export_teaching_package(contract_store, workflow_run_id=contract_run_id, reviewer="teacher")
    _assert_error(contract_error, "TEACHING_PACKAGE_CONTRACT_VALIDATION_ERROR")
    assert not (contract_workspace / "examples" / "output" / "teaching-packages" / f"{contract_run_id}.zip").exists()

    leak_store, leak, leak_workspace = _create_workflow(tmp_path / "leak", monkeypatch, approve=True)
    leak_run_id = leak["data"]["workflowRun"]["id"]
    leak_exam_artifact = next(
        item
        for item in leak_store.list_artifacts(workflow_run_id=leak_run_id)
        if item.kind == ArtifactKind.EXAM_DSL
    )
    leak_exam = json.loads(Path(leak_exam_artifact.path).read_text(encoding="utf-8"))
    grading_ref = leak_exam["spec"]["questions"][0]["gradingRef"]
    leak_exam["spec"]["questions"][0]["stem"] = f"Internal reference: {grading_ref}"
    Path(leak_exam_artifact.path).write_text(json.dumps(leak_exam), encoding="utf-8")
    with pytest.raises(TeachingPackageExportError) as leak_error:
        export_teaching_package(leak_store, workflow_run_id=leak_run_id, reviewer="teacher")
    _assert_error(leak_error, "CANDIDATE_PREVIEW_ANSWER_LEAK_DETECTED")
    assert not (leak_workspace / "examples" / "output" / "teaching-packages" / f"{leak_run_id}.zip").exists()


def test_export_rejects_duplicate_sources_invalid_extension_and_output_conflict(tmp_path, monkeypatch):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]
    explicit_output = tmp_path / "package.zip"
    first = export_teaching_package(
        store,
        workflow_run_id=run_id,
        reviewer="teacher",
        output_path=explicit_output,
    )
    assert first["outputPath"] == str(explicit_output.resolve())

    explicit_output.write_bytes(b"different package")
    with pytest.raises(TeachingPackageExportError) as conflict:
        export_teaching_package(
            store,
            workflow_run_id=run_id,
            reviewer="teacher",
            output_path=explicit_output,
        )
    _assert_error(conflict, "TEACHING_PACKAGE_EXPORT_CONFLICT")
    assert explicit_output.read_bytes() == b"different package"

    with pytest.raises(TeachingPackageExportError) as invalid_extension:
        export_teaching_package(
            store,
            workflow_run_id=run_id,
            reviewer="teacher",
            output_path=tmp_path / "package.json",
        )
    _assert_error(invalid_extension, "VALIDATION_ERROR")

    lab_artifact = next(
        item
        for item in store.list_artifacts(workflow_run_id=run_id)
        if item.kind == ArtifactKind.LAB_DSL
    )
    duplicate = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path=lab_artifact.path,
        title="Duplicate Lab DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id="trace_duplicate",
        task_id=lab_artifact.taskId,
        workflow_run_id=run_id,
        metadata={"artifactProfile": "teaching-core", "schemaValidated": True},
    )
    store.save_artifact(duplicate)
    with pytest.raises(TeachingPackageExportError) as duplicate_error:
        export_teaching_package(
            store,
            workflow_run_id=run_id,
            reviewer="teacher",
            output_path=tmp_path / "duplicate.zip",
        )
    _assert_error(duplicate_error, "TEACHING_PACKAGE_EXPORT_NOT_READY")
    assert not (tmp_path / "duplicate.zip").exists()
