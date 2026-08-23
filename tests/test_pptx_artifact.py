from __future__ import annotations

from hashlib import sha256
from importlib import util
import json
from pathlib import Path
import re
import zipfile

import pytest

from cli import pptx_artifact
from cli.pptx_artifact import PptxArtifactBuildError, build_pptx_artifact


OPTIONAL_DEPENDENCIES_AVAILABLE = util.find_spec("pptx") is not None and util.find_spec("PIL") is not None


def six_slide_dsl() -> dict:
    return {
        "version": "1.0",
        "kind": "PPT",
        "metadata": {
            "id": "ppt_internal_42",
            "title": "Reliable Data Pipelines",
            "audience": "Engineering students",
            "durationMinutes": 45,
        },
        "status": "DRAFT",
        "spec": {
            "theme": {"style": "professional", "language": "en"},
            "slides": [
                {
                    "id": "internal_slide_1",
                    "type": "title",
                    "title": "Reliable Data Pipelines",
                    "subtitle": "From raw input to trusted output",
                },
                {
                    "id": "internal_slide_2",
                    "type": "content",
                    "layout": "objectives",
                    "title": "Learning objectives",
                    "bullets": [
                        "Recognize the stages of a deterministic pipeline",
                        "Separate transformation from verification",
                        "Explain failures with useful evidence",
                    ],
                },
                {
                    "id": "internal_slide_3",
                    "type": "content",
                    "layout": "concept",
                    "title": "A dependable pipeline has boundaries",
                    "subtitle": "Each stage owns one observable responsibility.",
                    "bullets": [
                        "Input contracts make assumptions explicit",
                        "Transformations preserve traceable decisions",
                        "Validation catches drift before handoff",
                    ],
                },
                {
                    "id": "internal_slide_4",
                    "type": "content",
                    "layout": "process",
                    "title": "Four-stage workflow",
                    "bullets": ["Inspect", "Normalize", "Validate", "Export"],
                },
                {
                    "id": "internal_slide_5",
                    "type": "content",
                    "layout": "exercise",
                    "title": "Practice: diagnose a broken import",
                    "bullets": [
                        "Locate the first invalid record",
                        "State the failed contract",
                        "Propose a deterministic correction",
                        "Retain reproducible evidence",
                    ],
                },
                {
                    "id": "internal_slide_6",
                    "type": "summary",
                    "title": "Three habits to keep",
                    "subtitle": "Small contracts create dependable systems.",
                    "bullets": [
                        "Make assumptions visible",
                        "Validate every handoff",
                        "Keep evidence reproducible",
                    ],
                },
            ],
        },
    }


@pytest.mark.skipif(not OPTIONAL_DEPENDENCIES_AVAILABLE, reason="requires python-pptx and Pillow")
def test_build_pptx_artifact_creates_six_slide_deck_and_consistent_previews(tmp_path: Path) -> None:
    pptx_path = tmp_path / "course.pptx"
    preview_dir = tmp_path / "previews"
    contact_sheet = tmp_path / "contact-sheet.png"
    manifest_path = tmp_path / "manifest.json"

    result = build_pptx_artifact(
        six_slide_dsl(),
        pptx_path=pptx_path,
        preview_dir=preview_dir,
        contact_sheet_path=contact_sheet,
        manifest_path=manifest_path,
    )

    assert result["slideCount"] == 6
    assert result["pptxPath"] == str(pptx_path)
    assert result["sha256"] == sha256(pptx_path.read_bytes()).hexdigest()
    assert result["sizeBytes"] == pptx_path.stat().st_size > 0
    assert result["manifestPath"] == str(manifest_path)
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == result
    assert [item["layout"] for item in result["slidePreviews"]] == [
        "hero",
        "objectives",
        "concept",
        "process",
        "exercise",
        "summary",
    ]
    assert {item["reviewStatus"] for item in result["slidePreviews"]} == {"NEEDS_REVIEW"}
    assert all(item["imagePath"] == item["thumbnailPath"] == item["path"] for item in result["slidePreviews"])
    assert all(item["bytes"] == item["sizeBytes"] for item in result["slidePreviews"])
    assert len({item["sha256"] for item in result["slidePreviews"]}) >= 3

    forbidden = ("waiting_review", "needs_review", "poc", "internal_slide", "ppt_internal", "gradingref", "answer", "reviewrequired", "autopublish", "realpublish")
    with zipfile.ZipFile(pptx_path) as archive:
        slide_members = sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
        assert len(slide_members) == 6
        visible_xml = "\n".join(archive.read(name).decode("utf-8").lower() for name in slide_members)
        assert all(term not in visible_xml for term in forbidden)
        presentation_xml = archive.read("ppt/presentation.xml").decode("utf-8")
        size_match = re.search(r"<p:sldSz[^>]+cx=\"(\d+)\"[^>]+cy=\"(\d+)\"", presentation_xml)
        assert size_match is not None
        width, height = map(int, size_match.groups())
        assert width / height == pytest.approx(16 / 9, rel=1e-4)

    image_module = pytest.importorskip("PIL.Image")
    for item in result["slidePreviews"]:
        preview_path = Path(item["path"])
        assert preview_path.is_file()
        assert item["sha256"] == sha256(preview_path.read_bytes()).hexdigest()
        with image_module.open(preview_path) as image:
            assert image.size == (1280, 720)
            extrema = image.convert("RGB").getextrema()
            assert any(low != high for low, high in extrema)

    assert result["contactSheet"]["path"] == str(contact_sheet)
    assert result["contactSheet"]["slideCount"] == 6
    assert result["contactSheet"]["sha256"] == sha256(contact_sheet.read_bytes()).hexdigest()
    with image_module.open(contact_sheet) as image:
        assert image.width > 0 and image.height > 0
        assert any(low != high for low, high in image.convert("RGB").getextrema())


def test_build_pptx_artifact_reports_missing_optional_dependencies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    real_import = pptx_artifact.import_module

    def missing_pptx(name: str):
        if name == "pptx":
            raise ModuleNotFoundError("No module named 'pptx'")
        return real_import(name)

    monkeypatch.setattr(pptx_artifact, "import_module", missing_pptx)

    with pytest.raises(PptxArtifactBuildError) as captured:
        build_pptx_artifact(
            six_slide_dsl(),
            pptx_path=tmp_path / "course.pptx",
            preview_dir=tmp_path / "previews",
            contact_sheet_path=tmp_path / "contact.png",
        )

    error = captured.value
    assert error.code == "PPTX_DEPENDENCY_MISSING"
    assert error.message == "Optional PPTX build dependencies are unavailable"
    assert error.errors[0]["field"] == "dependencies"
    assert "python-pptx" in error.errors[0]["missing"]


def test_build_pptx_artifact_rejects_internal_canvas_text_before_loading_dependencies(tmp_path: Path) -> None:
    dsl = six_slide_dsl()
    dsl["spec"]["slides"][2]["bullets"][0] = "Expose gradingRef and answer"

    with pytest.raises(PptxArtifactBuildError) as captured:
        build_pptx_artifact(
            dsl,
            pptx_path=tmp_path / "course.pptx",
            preview_dir=tmp_path / "previews",
            contact_sheet_path=tmp_path / "contact.png",
        )

    assert captured.value.code == "PPTX_CANVAS_CONTENT_FORBIDDEN"
    assert captured.value.errors[0]["field"] == "dsl.spec.slides[2].bullets[0]"
    assert not (tmp_path / "course.pptx").exists()


@pytest.mark.skipif(not OPTIONAL_DEPENDENCIES_AVAILABLE, reason="requires python-pptx and Pillow")
def test_build_pptx_artifact_allows_review_status_as_legacy_course_content(tmp_path: Path) -> None:
    dsl = six_slide_dsl()
    dsl["spec"]["slides"][2]["bullets"][0] = "WAITING_REVIEW is a manual checkpoint"
    pptx_path = tmp_path / "legacy-review-course.pptx"

    build_pptx_artifact(
        dsl,
        pptx_path=pptx_path,
        preview_dir=tmp_path / "previews",
        contact_sheet_path=tmp_path / "contact.png",
    )

    with zipfile.ZipFile(pptx_path) as archive:
        visible_xml = "\n".join(
            archive.read(name).decode("utf-8").lower()
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
    assert "waiting_review is a manual checkpoint" in visible_xml


def test_atomic_write_uses_a_short_same_directory_temporary_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "presentation.pptx"
    sources: list[Path] = []
    real_replace = pptx_artifact.os.replace

    def recording_replace(source, destination) -> None:
        sources.append(Path(source))
        real_replace(source, destination)

    monkeypatch.setattr(pptx_artifact.os, "replace", recording_replace)
    pptx_artifact._atomic_write(target, b"pptx")

    assert target.read_bytes() == b"pptx"
    assert len(sources) == 1
    assert sources[0].parent == target.parent
    assert len(sources[0].name) <= 16
