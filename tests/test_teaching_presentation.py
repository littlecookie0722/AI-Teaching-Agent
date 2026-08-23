from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from backend.app import BackendApiApp
from backend.mock_api import handle_request
from cli.ai_task import TaskStatus
from cli.ai_task import create_waiting_review_task
from cli.artifact import ArtifactKind, ArtifactStatus
from cli.review_batch import build_teaching_package_review_summary
from cli.review_detail import build_ppt_approval_gate
from cli.store import JsonTaskStore
from cli.teaching_package_export import ENTRY_NAMES, export_teaching_package
from cli.teaching_presentation import TeachingPresentationError, generate_teaching_presentation


CORE_ARTIFACT_KINDS = {
    "lab": ArtifactKind.LAB_DSL,
    "exam": ArtifactKind.EXAM_DSL,
    "grading": ArtifactKind.GRADING_DSL,
}


def _create_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
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
            "artifactProfile": "teaching-core",
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


def _fake_builder(
    dsl: dict,
    *,
    pptx_path: Path,
    preview_dir: Path,
    contact_sheet_path: Path,
    manifest_path: Path | None = None,
) -> dict:
    pptx_path = Path(pptx_path)
    preview_dir = Path(preview_dir)
    contact_sheet_path = Path(contact_sheet_path)
    pptx_path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    pptx_path.write_bytes(b"test-pptx-content")

    previews = []
    for index, slide in enumerate(dsl["spec"]["slides"], start=1):
        preview_path = preview_dir / f"slide-{index:02d}.png"
        preview_path.write_bytes(f"preview-{index}".encode("ascii"))
        previews.append(
            {
                "index": index,
                "title": slide["title"],
                "imagePath": str(preview_path),
                "width": 1280,
                "height": 720,
            }
        )

    contact_sheet_path.write_bytes(b"test-contact-sheet")
    if manifest_path is not None:
        Path(manifest_path).write_text("{}\n", encoding="utf-8")
    return {
        "slideCount": len(previews),
        "sha256": "builder-value-is-recomputed",
        "sizeBytes": -1,
        "generator": "test-builder",
        "slidePreviews": previews,
        "contactSheet": {"path": str(contact_sheet_path)},
    }


def _assert_error(exc: pytest.ExceptionInfo[TeachingPresentationError], code: str) -> None:
    assert exc.value.code == code
    assert exc.value.errors


def test_generate_default_deck_stays_review_gated_and_preserves_parent_export(tmp_path, monkeypatch):
    store, generated, workspace = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]
    output_root = tmp_path / "presentation-output"

    result = generate_teaching_presentation(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_ppt",
        output_root=output_root,
        trace_id="trace_teaching_presentation",
        builder=_fake_builder,
    )

    child_run = result["childWorkflowRun"]
    assert result["component"] == "TeachingPresentationGenerationResult"
    assert result["slideCount"] == 6
    assert len(result["presentationDsl"]["spec"]["slides"]) == 6
    assert result["qualityReport"]["blockingIssueTotal"] == 0
    assert result["candidateSafety"] == {
        "candidateSafe": True,
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
    }
    assert result["task"]["status"] == TaskStatus.WAITING_REVIEW.value
    assert child_run["id"] != run_id
    assert child_run["workflowId"] == "teaching_presentation_generation"
    assert child_run["inputRef"] == run_id
    assert child_run["reviewRequired"] is True
    assert child_run["realPublish"] is False

    output_dir = Path(result["outputDirectory"])
    assert output_dir.parent == output_root
    assert Path(result["presentationDslPath"]).is_file()
    pptx_metadata = result["pptxArtifact"]["metadata"]
    assert Path(result["pptxArtifact"]["path"]).read_bytes() == b"test-pptx-content"
    assert pptx_metadata["slideCount"] == 6
    assert len(pptx_metadata["slidePreviews"]) == 6
    assert all(Path(item["imagePath"]).is_file() for item in pptx_metadata["slidePreviews"])
    assert Path(pptx_metadata["contactSheet"]["path"]).is_file()
    assert Path(pptx_metadata["manifestPath"]).is_file()
    assert pptx_metadata["pageReviewSummary"]["status"] == "NEEDS_REVIEW"
    assert pptx_metadata["pageReviewSummary"]["autoApproveAllowed"] is False

    child_artifacts = store.list_artifacts(workflow_run_id=child_run["id"])
    assert {artifact.kind for artifact in child_artifacts} == {
        ArtifactKind.PPT_DSL,
        ArtifactKind.PPTX_FILE,
    }
    assert {artifact.status for artifact in child_artifacts} == {ArtifactStatus.WAITING_REVIEW}
    assert all(artifact.workflowRunId == child_run["id"] for artifact in child_artifacts)
    assert not any(
        artifact.kind in {ArtifactKind.PPT_DSL, ArtifactKind.PPTX_FILE}
        for artifact in store.list_artifacts(workflow_run_id=run_id)
    )

    parent_summary = build_teaching_package_review_summary(store, run_id)
    assert parent_summary is not None
    assert parent_summary["available"] is True
    assert parent_summary["exportReady"] is True
    exported = export_teaching_package(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_export",
        trace_id="trace_after_ppt_generation",
    )
    with ZipFile(exported["outputPath"]) as archive:
        assert tuple(archive.namelist()) == ENTRY_NAMES
    assert Path(exported["outputPath"]).parent == workspace / "examples" / "output" / "teaching-packages"


def test_generate_constrains_long_hero_subtitle_before_preflight(tmp_path, monkeypatch):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]
    lab_artifact = next(
        artifact
        for artifact in store.list_artifacts(workflow_run_id=run_id)
        if artifact.kind == ArtifactKind.LAB_DSL
    )
    lab_path = Path(lab_artifact.path)
    lab = json.loads(lab_path.read_text(encoding="utf-8"))
    lab["spec"]["targetUsers"] = ["学习者" * 20]
    lab_path.write_text(json.dumps(lab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = generate_teaching_presentation(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_ppt",
        output_root=tmp_path / "presentation-output",
        builder=_fake_builder,
    )

    hero = result["presentationDsl"]["spec"]["slides"][0]
    hero_quality = result["qualityReport"]["slides"][0]
    assert len(hero["subtitle"]) == 48
    assert hero["subtitle"].endswith("…")
    assert hero_quality["subtitleCharacterTotal"] == 48
    assert hero_quality["renderedSubtitleCharacterLimit"] == 48
    assert hero_quality["estimatedTextOverflow"] is False
    assert result["qualityReport"]["status"] == "PASS"


@pytest.mark.parametrize("slide_count", [5, 6, 8])
def test_generate_with_default_builder_preserves_all_dsl_text_in_pptx_and_png_reviews(
    tmp_path,
    monkeypatch,
    slide_count,
):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]

    result = generate_teaching_presentation(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_ppt",
        slide_count=slide_count,
        output_root=tmp_path / "presentation-output",
    )

    presentation_module = pytest.importorskip("pptx")
    image_module = pytest.importorskip("PIL.Image")
    pptx_path = Path(result["pptxArtifact"]["path"])
    presentation = presentation_module.Presentation(pptx_path)
    assert len(presentation.slides) == slide_count
    assert presentation.slide_width / presentation.slide_height == pytest.approx(16 / 9, rel=1e-4)

    source_slides = result["presentationDsl"]["spec"]["slides"]
    quality_slides = result["qualityReport"]["slides"]
    assert result["qualityReport"]["status"] == "PASS"
    for source_slide, quality_slide, rendered_slide in zip(
        source_slides,
        quality_slides,
        presentation.slides,
        strict=True,
    ):
        visible_text = "\n".join(
            text
            for shape in rendered_slide.shapes
            if (text := str(getattr(shape, "text", "")).strip())
        )
        assert source_slide["title"] in visible_text
        assert all(bullet in visible_text for bullet in source_slide.get("bullets", []))
        assert quality_slide["bulletTotal"] == quality_slide["renderedBulletTotal"]

    metadata = result["pptxArtifact"]["metadata"]
    for preview in metadata["slidePreviews"]:
        with image_module.open(preview["imagePath"]) as image:
            assert image.size == (1280, 720)
            assert any(low != high for low, high in image.convert("RGB").getextrema())
    with image_module.open(metadata["contactSheet"]["path"]) as contact_sheet:
        assert contact_sheet.width > 0
        assert contact_sheet.height > 0


@pytest.mark.parametrize("slide_count", [5, 6, 7, 8])
def test_generate_supports_five_to_eight_slide_product_range(tmp_path, monkeypatch, slide_count):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]

    result = generate_teaching_presentation(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_ppt",
        slide_count=slide_count,
        output_root=tmp_path / "presentation-output",
        builder=_fake_builder,
    )

    slides = result["presentationDsl"]["spec"]["slides"]
    slide_ids = [slide["id"] for slide in slides]
    assert len(slides) == slide_count
    assert len(set(slide_ids)) == slide_count
    assert slides[0]["type"] == "title"
    assert slides[-1]["type"] == "summary"
    assert all(any(role in slide_id for slide_id in slide_ids) for role in ("hero", "objectives", "concept", "process", "exercise", "summary"))
    assert result["qualityReport"]["status"] == "PASS"
    assert all(slide.get("layout") for slide in slides)
    assert all(
        report["bulletTotal"] == report["renderedBulletTotal"]
        for report in result["qualityReport"]["slides"]
    )


@pytest.mark.parametrize(
    ("slide_count", "step_total", "direct_step_total", "aggregate_range"),
    [
        (5, 5, 2, "步骤 3-5"),
        (6, 5, 3, "步骤 4-5"),
        (8, 9, 7, "步骤 8-9"),
    ],
)
def test_generate_aggregates_source_steps_that_exceed_process_layout_slots(
    tmp_path,
    monkeypatch,
    slide_count,
    step_total,
    direct_step_total,
    aggregate_range,
):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]
    lab_artifact = next(
        artifact
        for artifact in store.list_artifacts(workflow_run_id=run_id)
        if artifact.kind == ArtifactKind.LAB_DSL
    )
    lab_path = Path(lab_artifact.path)
    lab = json.loads(lab_path.read_text(encoding="utf-8"))
    lab["spec"]["steps"] = [
        {
            "id": f"step_{index}",
            "title": f"操作{index}",
            "instruction": f"完成普通知识任务{index}",
            "expectedResult": f"得到普通验证结果{index}",
        }
        for index in range(1, step_total + 1)
    ]
    lab_path.write_text(json.dumps(lab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = generate_teaching_presentation(
        store,
        workflow_run_id=run_id,
        reviewer="teacher_ppt",
        slide_count=slide_count,
        output_root=tmp_path / f"presentation-output-{slide_count}",
        builder=_fake_builder,
    )

    slides = result["presentationDsl"]["spec"]["slides"]
    process_slides = [slide for slide in slides if slide.get("layout") == "process"]
    assert process_slides
    assert all(len(slide.get("bullets", [])) == 4 for slide in process_slides)
    process_bullets = []
    for slide in process_slides:
        bullets = slide.get("bullets", [])
        process_bullets.extend(bullets[1:] if slide["id"].endswith("_concept_process") else bullets)
    rendered_process = "\n".join(process_bullets)
    for index in range(1, direct_step_total + 1):
        assert f"操作{index}" in rendered_process
    aggregate_bullet = next(bullet for bullet in process_bullets if aggregate_range in bullet)
    assert aggregate_bullet == (
        f"{aggregate_range}：完成其余 {step_total - direct_step_total} 步并整理结果"
    )
    assert not aggregate_bullet.endswith("…")
    assert all(len(bullet) <= 30 for bullet in process_bullets)

    summary = next(slide for slide in slides if slide["layout"] == "summary")
    assert f"覆盖全部 {step_total} 个实验步骤" in "\n".join(summary["bullets"])
    assert result["qualityReport"]["status"] == "PASS"
    process_quality = [
        report for report in result["qualityReport"]["slides"] if report["layout"] == "process"
    ]
    assert all(
        report["bulletTotal"] == report["renderedBulletTotal"] == report["renderedBulletLimit"] == 4
        and report["estimatedTextOverflow"] is False
        for report in process_quality
    )
    assert all(
        report["bulletTotal"] == report["renderedBulletTotal"]
        for report in result["qualityReport"]["slides"]
    )


@pytest.mark.parametrize("slide_count", [4, 9])
def test_generate_rejects_out_of_range_slide_count_before_builder(tmp_path, slide_count):
    builder_called = False

    def unexpected_builder(*args, **kwargs):
        nonlocal builder_called
        builder_called = True
        raise AssertionError("builder must not be called")

    store = JsonTaskStore(tmp_path / "store.json")
    with pytest.raises(TeachingPresentationError) as exc:
        generate_teaching_presentation(
            store,
            workflow_run_id="workflow_run_source",
            reviewer="teacher_ppt",
            slide_count=slide_count,
            output_root=tmp_path / "presentation-output",
            builder=unexpected_builder,
        )
    _assert_error(exc, "VALIDATION_ERROR")
    assert builder_called is False


def test_generate_blocks_unapproved_and_missing_source_artifacts(tmp_path, monkeypatch):
    pending_store, pending, _ = _create_workflow(tmp_path / "pending", monkeypatch)
    pending_run_id = pending["data"]["workflowRun"]["id"]
    with pytest.raises(TeachingPresentationError) as pending_error:
        generate_teaching_presentation(
            pending_store,
            workflow_run_id=pending_run_id,
            reviewer="teacher_ppt",
            output_root=tmp_path / "pending-output",
            builder=_fake_builder,
        )
    _assert_error(pending_error, "TEACHING_PACKAGE_EXPORT_NOT_READY")

    missing_store, missing, _ = _create_workflow(tmp_path / "missing", monkeypatch, approve=True)
    missing_run_id = missing["data"]["workflowRun"]["id"]
    lab_artifact = next(
        artifact
        for artifact in missing_store.list_artifacts(workflow_run_id=missing_run_id)
        if artifact.kind == ArtifactKind.LAB_DSL
    )
    Path(lab_artifact.path).unlink()
    with pytest.raises(TeachingPresentationError) as missing_error:
        generate_teaching_presentation(
            missing_store,
            workflow_run_id=missing_run_id,
            reviewer="teacher_ppt",
            output_root=tmp_path / "missing-output",
            builder=_fake_builder,
        )
    _assert_error(missing_error, "TEACHING_PACKAGE_ARTIFACT_NOT_FOUND")


def test_builder_failure_leaves_no_child_state_or_partial_output(tmp_path, monkeypatch):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]
    before_tasks = {task.id for task in store.list()}
    before_runs = {run.id for run in store.list_workflow_runs()}
    before_artifacts = {artifact.id for artifact in store.list_artifacts()}
    output_root = tmp_path / "presentation-output"

    def failing_builder(*args, **kwargs):
        Path(kwargs["pptx_path"]).write_bytes(b"partial")
        raise RuntimeError("renderer unavailable")

    with pytest.raises(TeachingPresentationError) as exc:
        generate_teaching_presentation(
            store,
            workflow_run_id=run_id,
            reviewer="teacher_ppt",
            output_root=output_root,
            builder=failing_builder,
        )
    _assert_error(exc, "TEACHING_PRESENTATION_BUILD_ERROR")
    assert {task.id for task in store.list()} == before_tasks
    assert {run.id for run in store.list_workflow_runs()} == before_runs
    assert {artifact.id for artifact in store.list_artifacts()} == before_artifacts
    assert output_root.is_dir()
    assert list(output_root.iterdir()) == []


def test_answer_text_leak_is_blocked_without_echoing_sensitive_value(tmp_path, monkeypatch):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]
    artifacts = store.list_artifacts(workflow_run_id=run_id)
    lab_artifact = next(item for item in artifacts if item.kind == ArtifactKind.LAB_DSL)
    exam_artifact = next(item for item in artifacts if item.kind == ArtifactKind.EXAM_DSL)
    lab = json.loads(Path(lab_artifact.path).read_text(encoding="utf-8"))
    exam = json.loads(Path(exam_artifact.path).read_text(encoding="utf-8"))
    sensitive_answer = lab["spec"]["objectives"][0]
    exam["spec"]["questions"][0]["answer"] = sensitive_answer
    Path(exam_artifact.path).write_text(
        json.dumps(exam, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(TeachingPresentationError) as exc:
        generate_teaching_presentation(
            store,
            workflow_run_id=run_id,
            reviewer="teacher_ppt",
            output_root=tmp_path / "presentation-output",
            builder=_fake_builder,
        )
    _assert_error(exc, "TEACHING_PRESENTATION_CANDIDATE_LEAK_DETECTED")
    safe_error = json.dumps(
        {"message": exc.value.message, "errors": exc.value.errors},
        ensure_ascii=False,
    )
    assert sensitive_answer not in safe_error
    assert store.list_workflow_runs(workflow_id="teaching_presentation_generation") == []
    assert store.list_artifacts(kind=ArtifactKind.PPT_DSL.value) == []
    assert store.list_artifacts(kind=ArtifactKind.PPTX_FILE.value) == []


@pytest.mark.parametrize(
    ("source_text", "sensitive_answer"),
    [
        ("计算结果：42", "42"),
        ("结论：是", "是"),
        ("结果：√", "√"),
        ("ANSWER-" + ("x" * 120), "ANSWER-" + ("x" * 120)),
    ],
)
def test_short_or_truncated_source_answer_leak_is_blocked(
    tmp_path,
    monkeypatch,
    source_text,
    sensitive_answer,
):
    store, generated, _ = _create_workflow(tmp_path, monkeypatch, approve=True)
    run_id = generated["data"]["workflowRun"]["id"]
    artifacts = store.list_artifacts(workflow_run_id=run_id)
    lab_artifact = next(item for item in artifacts if item.kind == ArtifactKind.LAB_DSL)
    exam_artifact = next(item for item in artifacts if item.kind == ArtifactKind.EXAM_DSL)
    lab = json.loads(Path(lab_artifact.path).read_text(encoding="utf-8"))
    exam = json.loads(Path(exam_artifact.path).read_text(encoding="utf-8"))
    lab["spec"]["objectives"][0] = source_text
    exam["spec"]["questions"][0]["answer"] = sensitive_answer
    Path(lab_artifact.path).write_text(json.dumps(lab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(exam_artifact.path).write_text(json.dumps(exam, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(TeachingPresentationError) as captured:
        generate_teaching_presentation(
            store,
            workflow_run_id=run_id,
            reviewer="teacher_ppt",
            output_root=tmp_path / "presentation-output",
            builder=_fake_builder,
        )

    _assert_error(captured, "TEACHING_PRESENTATION_CANDIDATE_LEAK_DETECTED")
    safe_error = json.dumps(
        {"message": captured.value.message, "errors": captured.value.errors},
        ensure_ascii=False,
    )
    assert sensitive_answer not in safe_error
    assert store.list_workflow_runs(workflow_id="teaching_presentation_generation") == []


def test_product_deck_approval_gate_fails_closed_without_registered_pptx(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    product_task = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Product teaching deck",
        input_type="teaching_package_workflow",
        input_ref="workflow_run_source",
        trace_id="trace_product_deck_missing_artifact",
    )
    legacy_task = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Legacy PPT DSL",
        input_type="markdown",
        input_ref="source.md",
        trace_id="trace_legacy_ppt",
    )
    store.save(product_task)
    store.save(legacy_task)

    product_gate = build_ppt_approval_gate(store, product_task.id)
    legacy_gate = build_ppt_approval_gate(store, legacy_task.id)

    assert product_gate["applicable"] is True
    assert product_gate["approveReady"] is False
    assert product_gate["reasonCode"] == "PRESENTATION_DECK_ARTIFACT_MISSING"
    assert legacy_gate["applicable"] is False
    assert legacy_gate["approveReady"] is True
    assert legacy_gate["reasonCode"] == "LEGACY_PPT_TASK_WITHOUT_PRODUCT_DECK"


def test_complete_presentation_review_and_download_keeps_parent_package_contract(tmp_path, monkeypatch):
    store, generated, workspace = _create_workflow(tmp_path, monkeypatch, approve=True)
    store_path = store.path
    parent_run_id = generated["data"]["workflowRun"]["id"]

    response = handle_request(
        "POST",
        "/api/teaching-presentations/generate",
        store_path=store_path,
        body={
            "workflowRunId": parent_run_id,
            "reviewer": "teacher_ppt",
            "slideCount": 6,
        },
    )
    assert response["success"] is True
    presentation = response["data"]["teachingPresentation"]
    child_run_id = presentation["childWorkflowRun"]["id"]
    task_id = presentation["task"]["id"]
    artifact_id = presentation["pptxArtifact"]["id"]

    blocked = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_review"},
    )
    assert blocked["success"] is False
    assert blocked["code"] == "PPT_PAGE_REVIEW_INCOMPLETE"

    for slide_index in range(1, 7):
        page_update = handle_request(
            "POST",
            f"/api/review-tasks/{task_id}/ppt-page-review-status",
            store_path=store_path,
            body={
                "slideIndex": slide_index,
                "reviewStatus": "APPROVED",
                "reviewer": "teacher_review",
                "comment": "内容与版式已人工确认",
            },
        )
        assert page_update["success"] is True
        if slide_index == 1:
            preview_after_review = BackendApiApp(store_path=store_path).handle(
                "GET",
                f"/api/ppt-artifacts/{artifact_id}/previews/1",
            )
            preview_path = presentation["pptxArtifact"]["metadata"]["slidePreviews"][0]["imagePath"]
            assert preview_after_review.status == 200
            assert preview_after_review.content_type == "image/png"
            assert preview_after_review.body == Path(preview_path).read_bytes()

    child_summary = handle_request(
        "GET",
        f"/api/review-task-summary?detailMode=light&workflowRunId={child_run_id}",
        store_path=store_path,
    )
    deck_review = child_summary["data"]["reviewTaskSummary"]["presentationDeckReview"]
    assert deck_review["pageReviewSummary"]["status"] == "APPROVED"
    assert deck_review["approveReady"] is True
    assert deck_review["downloadReady"] is False

    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_review"},
    )
    assert approved["success"] is True
    assert approved["data"]["task"]["status"] == TaskStatus.APPROVED.value

    download = BackendApiApp(store_path=store_path).handle(
        "GET",
        f"/api/ppt-artifacts/{artifact_id}/download",
    )
    assert download.status == 200
    assert download.content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert download.body == Path(presentation["pptxArtifact"]["path"]).read_bytes()

    parent_summary = build_teaching_package_review_summary(JsonTaskStore(store_path), parent_run_id)
    assert parent_summary is not None
    assert parent_summary["exportReady"] is True
    assert parent_summary["reviewProgress"]["total"] == 3
    package = export_teaching_package(
        JsonTaskStore(store_path),
        workflow_run_id=parent_run_id,
        reviewer="teacher_export",
        output_path=workspace / "parent-package.zip",
        trace_id="trace_parent_package_after_ppt_approval",
    )
    with ZipFile(package["outputPath"]) as archive:
        assert tuple(archive.namelist()) == ENTRY_NAMES
