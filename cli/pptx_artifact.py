"""Local PPTX and preview rendering for presentation-ready PPT DSL artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
from typing import Any

from quality.ppt_preflight import (
    bullet_character_limit_for_layout,
    hero_subtitle_fallback,
    presentation_duration_label,
    resolve_ppt_layout,
    subtitle_character_limit_for_layout,
    title_character_limit_for_layout,
)


SLIDE_WIDTH = 1280
SLIDE_HEIGHT = 720
SLIDE_WIDTH_INCHES = 13.333333
SLIDE_HEIGHT_INCHES = 7.5
ALLOWED_LAYOUTS = {"hero", "objectives", "concept", "process", "exercise", "summary"}
__all__ = ["PptxArtifactBuildError", "build_pptx_artifact"]

INK = "172033"
MUTED = "667085"
PAPER = "F7F8FA"
WHITE = "FFFFFF"
TEAL = "0F766E"
TEAL_SOFT = "DDF4EE"
CORAL = "E4572E"
CORAL_SOFT = "FCE8E2"
GOLD = "E4B63D"
GOLD_SOFT = "FFF3CF"
BLUE = "2563EB"
BLUE_SOFT = "E8EFFF"
LINE = "D7DEE8"

_FORBIDDEN_CANVAS_PATTERNS = (
    # Legacy teaching decks may discuss WAITING_REVIEW as course content. The
    # product workflow keeps its own review metadata out of visible DSL fields.
    (re.compile(r"\bpoc\b", re.IGNORECASE), "PoC"),
    (re.compile(r"grading[_\s-]*ref", re.IGNORECASE), "gradingRef"),
    (re.compile(r"\banswers?\b|\u7b54\u6848", re.IGNORECASE), "answer"),
    (
        re.compile(r"\b(?:task|artifact|workflow(?:_run)?|trace|slide)_[a-z0-9_-]+\b", re.IGNORECASE),
        "internal ID",
    ),
    (re.compile(r"auto[_\s-]*publish|real[_\s-]*publish|publish[_\s-]*blocked", re.IGNORECASE), "publish policy"),
    (re.compile(r"review[_\s-]*required|manual[_\s-]*approval|review[_\s-]*policy", re.IGNORECASE), "review policy"),
    (re.compile("\u5ba1\u6838\u7b56\u7565|\u53d1\u5e03\u7b56\u7565"), "review or publish policy"),
)


class PptxArtifactBuildError(Exception):
    """Structured error raised when a local PPTX artifact cannot be built."""

    def __init__(self, code: str, message: str, errors: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "errors": self.errors}


@dataclass(frozen=True)
class _Slide:
    index: int
    layout: str
    title: str
    subtitle: str
    bullets: tuple[str, ...]


def build_pptx_artifact(
    dsl: dict[str, Any],
    *,
    pptx_path: str | Path,
    preview_dir: str | Path,
    contact_sheet_path: str | Path,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a 16:9 PPTX plus deterministic local review previews.

    Optional presentation dependencies are imported only when this function is
    called. Review metadata is returned in JSON and never rendered on a slide.
    """

    slides, metadata = _normalize_dsl(dsl)
    dependencies = _load_dependencies()
    pptx_target = Path(pptx_path)
    previews_target = Path(preview_dir)
    contact_target = Path(contact_sheet_path)
    manifest_target = Path(manifest_path) if manifest_path is not None else None
    _validate_targets(pptx_target, previews_target, contact_target, manifest_target)

    try:
        pptx_bytes = _build_pptx_bytes(slides, metadata, dependencies)
        rendered_images = [
            _render_slide(slide, metadata, len(slides), dependencies)
            for slide in slides
        ]
        preview_payloads = [_image_bytes(image) for image in rendered_images]
        contact_image = _build_contact_sheet(rendered_images, slides, dependencies)
        contact_bytes = _image_bytes(contact_image)
    except PptxArtifactBuildError:
        raise
    except Exception as exc:
        raise PptxArtifactBuildError(
            "PPTX_ARTIFACT_BUILD_ERROR",
            "PPTX artifact generation failed",
            [{"field": "artifact", "reason": f"{type(exc).__name__}: {exc}"}],
        ) from exc

    preview_items: list[dict[str, Any]] = []
    for slide, preview_bytes in zip(slides, preview_payloads, strict=True):
        target = previews_target / f"slide-{slide.index:02d}.png"
        preview_items.append(
            {
                "index": slide.index,
                "title": slide.title,
                "layout": slide.layout,
                "path": str(target),
                "imagePath": str(target),
                "thumbnailPath": str(target),
                "width": SLIDE_WIDTH,
                "height": SLIDE_HEIGHT,
                "sizeBytes": len(preview_bytes),
                "bytes": len(preview_bytes),
                "sha256": sha256(preview_bytes).hexdigest(),
                "reviewStatus": "NEEDS_REVIEW",
            }
        )

    result: dict[str, Any] = {
        "pptxPath": str(pptx_target),
        "slideCount": len(slides),
        "sha256": sha256(pptx_bytes).hexdigest(),
        "sizeBytes": len(pptx_bytes),
        "slidePreviews": preview_items,
        "contactSheet": {
            "path": str(contact_target),
            "slideCount": len(slides),
            "width": contact_image.width,
            "height": contact_image.height,
            "sizeBytes": len(contact_bytes),
            "bytes": len(contact_bytes),
            "sha256": sha256(contact_bytes).hexdigest(),
        },
    }
    if manifest_target is not None:
        result["manifestPath"] = str(manifest_target)

    try:
        _atomic_write(pptx_target, pptx_bytes)
        for item, preview_bytes in zip(preview_items, preview_payloads, strict=True):
            _atomic_write(Path(item["path"]), preview_bytes)
        _atomic_write(contact_target, contact_bytes)
        if manifest_target is not None:
            manifest_bytes = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            _atomic_write(manifest_target, manifest_bytes)
    except OSError as exc:
        raise PptxArtifactBuildError(
            "PPTX_ARTIFACT_WRITE_ERROR",
            "PPTX artifact output could not be written",
            [{"field": "output", "reason": f"{type(exc).__name__}: {exc}"}],
        ) from exc

    return result


def _load_dependencies() -> SimpleNamespace:
    missing: list[str] = []
    modules: dict[str, Any] = {}
    for module_name, package_name in (("pptx", "python-pptx"), ("PIL", "Pillow")):
        try:
            modules[module_name] = import_module(module_name)
        except (ImportError, ModuleNotFoundError):
            missing.append(package_name)
    if missing:
        raise PptxArtifactBuildError(
            "PPTX_DEPENDENCY_MISSING",
            "Optional PPTX build dependencies are unavailable",
            [
                {
                    "field": "dependencies",
                    "reason": f"Install the optional packages: {', '.join(missing)}",
                    "missing": missing,
                }
            ],
        )

    try:
        return SimpleNamespace(
            Presentation=modules["pptx"].Presentation,
            Inches=import_module("pptx.util").Inches,
            Pt=import_module("pptx.util").Pt,
            RGBColor=import_module("pptx.dml.color").RGBColor,
            MSO_SHAPE=import_module("pptx.enum.shapes").MSO_SHAPE,
            PP_ALIGN=import_module("pptx.enum.text").PP_ALIGN,
            MSO_ANCHOR=import_module("pptx.enum.text").MSO_ANCHOR,
            Image=import_module("PIL.Image"),
            ImageDraw=import_module("PIL.ImageDraw"),
            ImageFont=import_module("PIL.ImageFont"),
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise PptxArtifactBuildError(
            "PPTX_DEPENDENCY_MISSING",
            "Optional PPTX build dependencies are incomplete",
            [{"field": "dependencies", "reason": f"Import failed: {exc}"}],
        ) from exc


def _normalize_dsl(dsl: dict[str, Any]) -> tuple[list[_Slide], dict[str, str]]:
    if not isinstance(dsl, dict):
        raise _validation_error("dsl", "must be an object")
    metadata_value = dsl.get("metadata")
    metadata_source = metadata_value if isinstance(metadata_value, dict) else {}
    spec = dsl.get("spec")
    if not isinstance(spec, dict):
        raise _validation_error("dsl.spec", "must be an object")
    raw_slides = spec.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        raise _validation_error("dsl.spec.slides", "must contain at least one slide")

    metadata = {
        "title": _text(metadata_source.get("title"), "Teaching deck"),
        "audience": _text(metadata_source.get("audience"), "Learners"),
        "duration": presentation_duration_label(metadata_source.get("durationMinutes")),
    }
    _assert_canvas_text_allowed(metadata["title"], "dsl.metadata.title")
    _assert_canvas_text_allowed(metadata["audience"], "dsl.metadata.audience")

    slides: list[_Slide] = []
    for position, raw_slide in enumerate(raw_slides, start=1):
        if not isinstance(raw_slide, dict):
            raise _validation_error(f"dsl.spec.slides[{position - 1}]", "must be an object")
        slide_type = _text(raw_slide.get("type"), "content").lower()
        title = _text(raw_slide.get("title"), metadata["title"] if position == 1 else f"Section {position}")
        subtitle = _text(raw_slide.get("subtitle"), "")
        raw_bullets = raw_slide.get("bullets", [])
        if raw_bullets is None:
            raw_bullets = []
        if not isinstance(raw_bullets, list):
            raise _validation_error(f"dsl.spec.slides[{position - 1}].bullets", "must be an array")
        bullets = tuple(_text(value, "") for value in raw_bullets if _text(value, ""))
        explicit_layout = _text(raw_slide.get("layout"), "").lower()
        layout = resolve_ppt_layout(
            explicit_layout=explicit_layout,
            index=position,
            total=len(raw_slides),
            slide_type=slide_type,
            title=title,
        )
        if layout not in ALLOWED_LAYOUTS:
            raise _validation_error(
                f"dsl.spec.slides[{position - 1}].layout",
                f"expected one of {', '.join(sorted(ALLOWED_LAYOUTS))}",
            )
        _assert_canvas_text_allowed(title, f"dsl.spec.slides[{position - 1}].title")
        _assert_canvas_text_allowed(subtitle, f"dsl.spec.slides[{position - 1}].subtitle")
        for bullet_index, bullet in enumerate(bullets):
            _assert_canvas_text_allowed(bullet, f"dsl.spec.slides[{position - 1}].bullets[{bullet_index}]")
        slides.append(_Slide(position, layout, title, subtitle, bullets))
    return slides, metadata


def _assert_canvas_text_allowed(value: str, field: str) -> None:
    for pattern, label in _FORBIDDEN_CANVAS_PATTERNS:
        if pattern.search(value):
            raise PptxArtifactBuildError(
                "PPTX_CANVAS_CONTENT_FORBIDDEN",
                "PPTX canvas content contains internal or restricted text",
                [{"field": field, "reason": f"remove restricted canvas text: {label}"}],
            )


def _validation_error(field: str, reason: str) -> PptxArtifactBuildError:
    return PptxArtifactBuildError(
        "PPTX_DSL_INVALID",
        "PPT DSL is invalid for artifact generation",
        [{"field": field, "reason": reason}],
    )


def _validate_targets(
    pptx_path: Path,
    preview_dir: Path,
    contact_sheet_path: Path,
    manifest_path: Path | None,
) -> None:
    targets = [pptx_path.resolve(), contact_sheet_path.resolve()]
    if manifest_path is not None:
        targets.append(manifest_path.resolve())
    if len(set(targets)) != len(targets):
        raise _validation_error("output", "pptx, contact sheet, and manifest paths must be distinct")
    if preview_dir.exists() and not preview_dir.is_dir():
        raise _validation_error("preview_dir", "must be a directory path")


def _build_pptx_bytes(slides: list[_Slide], metadata: dict[str, str], deps: SimpleNamespace) -> bytes:
    presentation = deps.Presentation()
    presentation.slide_width = deps.Inches(SLIDE_WIDTH_INCHES)
    presentation.slide_height = deps.Inches(SLIDE_HEIGHT_INCHES)
    blank_layout = presentation.slide_layouts[6]
    for slide in slides:
        canvas = _PptCanvas(presentation.slides.add_slide(blank_layout), deps)
        _draw_layout(canvas, slide, metadata, len(slides))
    stream = BytesIO()
    presentation.save(stream)
    return stream.getvalue()


def _render_slide(slide: _Slide, metadata: dict[str, str], slide_total: int, deps: SimpleNamespace) -> Any:
    image = deps.Image.new("RGB", (SLIDE_WIDTH, SLIDE_HEIGHT), _pil_color(PAPER))
    canvas = _ImageCanvas(image, deps)
    _draw_layout(canvas, slide, metadata, slide_total)
    return image


def _draw_layout(canvas: Any, slide: _Slide, metadata: dict[str, str], slide_total: int) -> None:
    layouts = {
        "hero": _draw_hero,
        "objectives": _draw_objectives,
        "concept": _draw_concept,
        "process": _draw_process,
        "exercise": _draw_exercise,
        "summary": _draw_summary,
    }
    layouts[slide.layout](canvas, slide, metadata)
    _draw_page_number(canvas, slide.index, slide_total)


def _draw_hero(canvas: Any, slide: _Slide, metadata: dict[str, str]) -> None:
    canvas.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, INK)
    canvas.rect(0, 0, 18, SLIDE_HEIGHT, CORAL)
    canvas.text("TEACHING DECK", 72, 72, 420, 34, 18, GOLD, bold=True)
    title = _rendered_text(slide.title, title_character_limit_for_layout("hero"))
    canvas.text(title, 72, 150, 760, 190, 58, WHITE, bold=True, valign="middle")
    subtitle = _rendered_text(
        slide.subtitle or hero_subtitle_fallback(metadata["audience"], metadata["duration"]),
        subtitle_character_limit_for_layout("hero"),
    )
    canvas.text(subtitle, 76, 366, 700, 80, 25, "D9E2EC")
    canvas.rect(900, 92, 250, 250, TEAL, radius=28)
    canvas.text("01", 930, 116, 190, 120, 74, WHITE, bold=True, align="center")
    canvas.rect(850, 378, 330, 12, GOLD)
    canvas.rect(850, 416, 250, 12, CORAL)
    canvas.rect(850, 454, 290, 12, BLUE)


def _draw_objectives(canvas: Any, slide: _Slide, metadata: dict[str, str]) -> None:
    del metadata
    canvas.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, PAPER)
    title = _rendered_text(slide.title, title_character_limit_for_layout("objectives"))
    _draw_section_heading(canvas, "LEARNING OUTCOMES", title, TEAL)
    items = [
        _rendered_text(item, bullet_character_limit_for_layout("objectives", index))
        for index, item in enumerate(_display_items(slide, 3))
    ]
    colors = ((TEAL, TEAL_SOFT), (CORAL, CORAL_SOFT), (BLUE, BLUE_SOFT))
    for index, item in enumerate(items):
        top = 214 + index * 132
        accent, surface = colors[index % len(colors)]
        canvas.rect(80, top, 1120, 104, surface, radius=16)
        canvas.circle(106, top + 22, 60, accent)
        canvas.text(str(index + 1), 106, top + 22, 60, 60, 25, WHITE, bold=True, align="center", valign="middle")
        canvas.text(item, 198, top + 16, 930, 72, 24, INK, bold=index == 0, valign="middle")


def _draw_concept(canvas: Any, slide: _Slide, metadata: dict[str, str]) -> None:
    del metadata
    canvas.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, WHITE)
    canvas.rect(0, 0, 472, SLIDE_HEIGHT, TEAL)
    canvas.text("CORE IDEA", 58, 62, 300, 34, 17, GOLD, bold=True)
    title = _rendered_text(slide.title, title_character_limit_for_layout("concept"))
    canvas.text(title, 58, 126, 350, 210, 43, WHITE, bold=True, valign="middle")
    if slide.subtitle:
        subtitle = _rendered_text(slide.subtitle, subtitle_character_limit_for_layout("concept"))
        canvas.text(subtitle, 60, 366, 340, 100, 21, "DDF4EE")
    items = [
        _rendered_text(item, bullet_character_limit_for_layout("concept", index))
        for index, item in enumerate(_display_items(slide, 4))
    ]
    for index, item in enumerate(items):
        top = 104 + index * 122
        canvas.rect(540, top, 650, 92, PAPER, radius=12)
        canvas.rect(540, top, 8, 92, (CORAL, GOLD, BLUE, TEAL)[index % 4])
        canvas.text(item, 580, top + 12, 560, 68, 23, INK, bold=index == 0, valign="middle")


def _draw_process(canvas: Any, slide: _Slide, metadata: dict[str, str]) -> None:
    del metadata
    canvas.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, PAPER)
    title = _rendered_text(slide.title, title_character_limit_for_layout("process"))
    _draw_section_heading(canvas, "PROCESS", title, CORAL)
    items = [
        _rendered_text(item, bullet_character_limit_for_layout("process", index))
        for index, item in enumerate(_display_items(slide, 4))
    ]
    count = len(items)
    card_width = 230 if count >= 4 else 280
    gap = 42
    total_width = count * card_width + max(0, count - 1) * gap
    left = (SLIDE_WIDTH - total_width) // 2
    for index, item in enumerate(items):
        x = left + index * (card_width + gap)
        if index < count - 1:
            canvas.rect(x + card_width, 350, gap, 5, LINE)
        canvas.circle(x + card_width // 2 - 34, 258, 68, (TEAL, CORAL, BLUE, GOLD)[index % 4])
        canvas.text(str(index + 1), x + card_width // 2 - 34, 258, 68, 68, 27, WHITE, bold=True, align="center", valign="middle")
        canvas.rect(x, 360, card_width, 174, WHITE, radius=14)
        canvas.text(item, x + 20, 382, card_width - 40, 128, 21, INK, bold=True, align="center", valign="middle")


def _draw_exercise(canvas: Any, slide: _Slide, metadata: dict[str, str]) -> None:
    del metadata
    canvas.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, "EEF2F5")
    canvas.rect(0, 0, SLIDE_WIDTH, 188, CORAL)
    canvas.text("PRACTICE", 70, 44, 250, 30, 17, GOLD_SOFT, bold=True)
    title = _rendered_text(slide.title, title_character_limit_for_layout("exercise"))
    canvas.text(title, 68, 82, 1080, 76, 42, WHITE, bold=True)
    items = [
        _rendered_text(
            item,
            (
                bullet_character_limit_for_layout("exercise", index)
                if slide.bullets
                else subtitle_character_limit_for_layout("exercise")
            ),
        )
        for index, item in enumerate(_display_items(slide, 4))
    ]
    first = items[0]
    rest = items[1:]
    if not rest:
        fallback = slide.subtitle if slide.bullets and slide.subtitle else "Apply the idea to a concrete example."
        rest = [_rendered_text(fallback, bullet_character_limit_for_layout("exercise", 1))]
    canvas.rect(72, 236, 520, 368, WHITE, radius=18)
    canvas.text("TASK", 104, 270, 180, 30, 16, CORAL, bold=True)
    canvas.text(first, 104, 326, 430, 210, 30, INK, bold=True, valign="middle")
    canvas.rect(624, 236, 584, 368, INK, radius=18)
    canvas.text("CHECKPOINTS", 660, 270, 260, 30, 16, GOLD, bold=True)
    for index, item in enumerate(rest[:3]):
        top = 330 + index * 82
        canvas.circle(662, top + 7, 22, TEAL)
        canvas.text(item, 706, top - 3, 438, 58, 21, WHITE, valign="middle")


def _draw_summary(canvas: Any, slide: _Slide, metadata: dict[str, str]) -> None:
    del metadata
    canvas.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, INK)
    canvas.rect(0, 0, SLIDE_WIDTH, 16, GOLD)
    canvas.text("TAKEAWAYS", 72, 62, 260, 30, 17, TEAL_SOFT, bold=True)
    title = _rendered_text(slide.title, title_character_limit_for_layout("summary"))
    canvas.text(title, 70, 108, 1100, 92, 46, WHITE, bold=True)
    items = [
        _rendered_text(item, bullet_character_limit_for_layout("summary", index))
        for index, item in enumerate(_display_items(slide, 3))
    ]
    colors = (TEAL, CORAL, BLUE)
    for index, item in enumerate(items):
        x = 72 + index * 390
        canvas.rect(x, 260, 350, 264, "243147", radius=18)
        canvas.rect(x, 260, 350, 10, colors[index % 3])
        canvas.text(f"0{index + 1}", x + 26, 292, 100, 42, 25, colors[index % 3], bold=True)
        canvas.text(item, x + 26, 354, 298, 130, 24, WHITE, bold=True, valign="middle")
    if slide.subtitle:
        subtitle = _rendered_text(slide.subtitle, subtitle_character_limit_for_layout("summary"))
        canvas.text(subtitle, 72, 570, 1120, 52, 20, "CBD5E1", align="center")


def _draw_section_heading(canvas: Any, kicker: str, title: str, accent: str) -> None:
    canvas.text(kicker, 72, 56, 360, 30, 16, accent, bold=True)
    canvas.text(title, 70, 102, 1080, 76, 40, INK, bold=True)
    canvas.rect(72, 184, 150, 7, accent)


def _draw_page_number(canvas: Any, index: int, total: int) -> None:
    suffix = f" / {total:02d}" if total else ""
    canvas.text(f"{index:02d}{suffix}", 1120, 664, 90, 24, 13, MUTED, align="right")


def _display_items(slide: _Slide, limit: int) -> list[str]:
    items = list(slide.bullets[:limit])
    if not items and slide.subtitle:
        items.append(slide.subtitle)
    if not items:
        items.append(slide.title)
    return items


def _rendered_text(value: str, maximum: int) -> str:
    if len(value) <= maximum:
        return value
    return value[: maximum - 1].rstrip() + "…"


class _PptCanvas:
    def __init__(self, slide: Any, deps: SimpleNamespace) -> None:
        self.slide = slide
        self.deps = deps

    def rect(self, x: int, y: int, width: int, height: int, fill: str, *, radius: int = 0) -> None:
        shape_type = self.deps.MSO_SHAPE.ROUNDED_RECTANGLE if radius else self.deps.MSO_SHAPE.RECTANGLE
        shape = self.slide.shapes.add_shape(shape_type, _emu(x, self.deps), _emu(y, self.deps), _emu(width, self.deps), _emu(height, self.deps))
        shape.fill.solid()
        shape.fill.fore_color.rgb = _ppt_color(fill, self.deps)
        shape.line.fill.background()
        if radius and hasattr(shape, "adjustments") and len(shape.adjustments):
            shape.adjustments[0] = min(0.25, radius / max(1, min(width, height)))

    def circle(self, x: int, y: int, diameter: int, fill: str) -> None:
        shape = self.slide.shapes.add_shape(
            self.deps.MSO_SHAPE.OVAL,
            _emu(x, self.deps),
            _emu(y, self.deps),
            _emu(diameter, self.deps),
            _emu(diameter, self.deps),
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = _ppt_color(fill, self.deps)
        shape.line.fill.background()

    def text(
        self,
        value: str,
        x: int,
        y: int,
        width: int,
        height: int,
        size: int,
        color: str,
        *,
        bold: bool = False,
        align: str = "left",
        valign: str = "top",
    ) -> None:
        box = self.slide.shapes.add_textbox(_emu(x, self.deps), _emu(y, self.deps), _emu(width, self.deps), _emu(height, self.deps))
        frame = box.text_frame
        frame.clear()
        frame.word_wrap = True
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        frame.vertical_anchor = {
            "top": self.deps.MSO_ANCHOR.TOP,
            "middle": self.deps.MSO_ANCHOR.MIDDLE,
            "bottom": self.deps.MSO_ANCHOR.BOTTOM,
        }[valign]
        paragraph = frame.paragraphs[0]
        paragraph.alignment = {
            "left": self.deps.PP_ALIGN.LEFT,
            "center": self.deps.PP_ALIGN.CENTER,
            "right": self.deps.PP_ALIGN.RIGHT,
        }[align]
        run = paragraph.add_run()
        run.text = value
        run.font.name = "Microsoft YaHei" if re.search(r"[\u3400-\u9fff]", value) else "Aptos"
        run.font.size = self.deps.Pt(size * 0.75)
        run.font.bold = bold
        run.font.color.rgb = _ppt_color(color, self.deps)


class _ImageCanvas:
    def __init__(self, image: Any, deps: SimpleNamespace) -> None:
        self.image = image
        self.deps = deps
        self.draw = deps.ImageDraw.Draw(image)

    def rect(self, x: int, y: int, width: int, height: int, fill: str, *, radius: int = 0) -> None:
        bounds = (x, y, x + width, y + height)
        if radius:
            self.draw.rounded_rectangle(bounds, radius=radius, fill=_pil_color(fill))
        else:
            self.draw.rectangle(bounds, fill=_pil_color(fill))

    def circle(self, x: int, y: int, diameter: int, fill: str) -> None:
        self.draw.ellipse((x, y, x + diameter, y + diameter), fill=_pil_color(fill))

    def text(
        self,
        value: str,
        x: int,
        y: int,
        width: int,
        height: int,
        size: int,
        color: str,
        *,
        bold: bool = False,
        align: str = "left",
        valign: str = "top",
    ) -> None:
        font = _load_font(self.deps.ImageFont, size, bold=bold)
        lines = _wrap_lines(self.draw, value, font, width)
        line_height = max(size + 8, _font_height(self.draw, font))
        max_lines = max(1, height // line_height)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = _ellipsize(self.draw, lines[-1], font, width, force=True)
        block_height = len(lines) * line_height
        cursor_y = y if valign == "top" else y + max(0, (height - block_height) // (2 if valign == "middle" else 1))
        for line in lines:
            line_width = self.draw.textlength(line, font=font)
            cursor_x = x
            if align == "center":
                cursor_x = x + max(0, (width - line_width) / 2)
            elif align == "right":
                cursor_x = x + max(0, width - line_width)
            self.draw.text((cursor_x, cursor_y), line, font=font, fill=_pil_color(color))
            cursor_y += line_height


def _build_contact_sheet(images: list[Any], slides: list[_Slide], deps: SimpleNamespace) -> Any:
    columns = min(3, max(1, len(images)))
    rows = (len(images) + columns - 1) // columns
    thumb_width = 368
    thumb_height = 207
    cell_width = 400
    cell_height = 264
    margin = 24
    sheet_width = margin * 2 + columns * cell_width
    sheet_height = margin * 2 + rows * cell_height
    sheet = deps.Image.new("RGB", (sheet_width, sheet_height), _pil_color(WHITE))
    draw = deps.ImageDraw.Draw(sheet)
    font = _load_font(deps.ImageFont, 16, bold=True)
    resampling = getattr(deps.Image, "Resampling", deps.Image).LANCZOS
    for offset, (image, slide) in enumerate(zip(images, slides, strict=True)):
        column = offset % columns
        row = offset // columns
        left = margin + column * cell_width
        top = margin + row * cell_height
        thumbnail = image.resize((thumb_width, thumb_height), resampling)
        sheet.paste(thumbnail, (left, top))
        draw.rectangle((left, top, left + thumb_width, top + thumb_height), outline=_pil_color(LINE), width=1)
        label = f"{slide.index:02d}  {slide.title}"
        draw.text((left, top + thumb_height + 14), _ellipsize(draw, label, font, thumb_width), font=font, fill=_pil_color(INK))
    return sheet


def _image_bytes(image: Any) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".", suffix=".tmp", dir=str(path.parent))
        temporary = Path(temporary_name)
        file = os.fdopen(descriptor, "wb")
        descriptor = None
        with file:
            file.write(payload)
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _load_font(image_font: Any, size: int, *, bold: bool) -> Any:
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = (
        windows / ("msyhbd.ttc" if bold else "msyh.ttc"),
        windows / ("arialbd.ttf" if bold else "arial.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return image_font.truetype(str(candidate), size=size)
    try:
        return image_font.load_default(size=size)
    except TypeError:
        return image_font.load_default()


def _wrap_lines(draw: Any, value: str, font: Any, max_width: int) -> list[str]:
    paragraphs = value.splitlines() or [""]
    lines: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            lines.append("")
            continue
        tokens = re.findall(r"\S+\s*", paragraph) if " " in paragraph else list(paragraph)
        current = ""
        for token in tokens:
            candidate = current + token
            if current and draw.textlength(candidate.rstrip(), font=font) > max_width:
                lines.append(current.rstrip())
                current = token.lstrip()
            else:
                current = candidate
            while current and draw.textlength(current.rstrip(), font=font) > max_width:
                current, overflow = _split_token(draw, current, font, max_width)
                if current:
                    lines.append(current)
                if not overflow:
                    current = ""
                    break
                current = overflow
        if current or not lines:
            lines.append(current.rstrip())
    return lines


def _split_token(draw: Any, value: str, font: Any, max_width: int) -> tuple[str, str]:
    fitting = ""
    for index, character in enumerate(value):
        if fitting and draw.textlength(fitting + character, font=font) > max_width:
            return fitting, value[index:]
        fitting += character
    return fitting, ""


def _ellipsize(draw: Any, value: str, font: Any, max_width: int, *, force: bool = False) -> str:
    if not force and draw.textlength(value, font=font) <= max_width:
        return value
    suffix = "..."
    trimmed = value
    while trimmed and draw.textlength(trimmed + suffix, font=font) > max_width:
        trimmed = trimmed[:-1]
    return trimmed.rstrip() + suffix


def _font_height(draw: Any, font: Any) -> int:
    bounds = draw.textbbox((0, 0), "Ag", font=font)
    return max(1, bounds[3] - bounds[1] + 6)


def _text(value: Any, fallback: str) -> str:
    normalized = " ".join(str(value or "").split())
    return normalized or fallback


def _emu(pixels: int, deps: SimpleNamespace) -> Any:
    return deps.Inches(pixels / 96)


def _ppt_color(value: str, deps: SimpleNamespace) -> Any:
    red, green, blue = _rgb(value)
    return deps.RGBColor(red, green, blue)


def _pil_color(value: str) -> tuple[int, int, int]:
    return _rgb(value)


def _rgb(value: str) -> tuple[int, int, int]:
    clean = value.removeprefix("#")
    return (
        int(clean[0:2], 16),
        int(clean[2:4], 16),
        int(clean[4:6], 16),
    )
