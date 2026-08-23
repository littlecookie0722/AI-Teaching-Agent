"""Deterministic, advisory quality checks for generated PPT DSL artifacts."""

from __future__ import annotations

from typing import Any


MAX_RENDERED_BULLETS = 6
MAX_TITLE_CHARACTERS = 32
MAX_SUBTITLE_CHARACTERS = 96
MAX_BULLET_CHARACTERS = 96
MAX_BODY_CHARACTERS = 360

# Layout-specific limits mirror the fixed renderer slots. Layout-less DSLs use
# the same deterministic layout inference as the renderer.
LAYOUT_RENDERED_BULLET_LIMITS = {
    "hero": 0,
    "objectives": 3,
    "concept": 4,
    "process": 4,
    "exercise": 4,
    "summary": 3,
}
LAYOUT_TITLE_CHARACTER_LIMITS = {
    "hero": 22,
    "objectives": 24,
    "concept": 24,
    "process": 24,
    "exercise": 23,
    "summary": 21,
}
LAYOUT_SUBTITLE_CHARACTER_LIMITS = {
    "hero": 48,
    "objectives": 64,
    "concept": 40,
    "process": 30,
    "exercise": 36,
    "summary": 40,
}
LAYOUT_BULLET_CHARACTER_LIMITS = {
    "objectives": (64, 64, 64),
    "concept": (40, 40, 40, 40),
    "process": (30, 30, 30, 30),
    "exercise": (60, 36, 36, 36),
    "summary": (40, 40, 40),
}


def build_ppt_preflight_report(ppt: dict[str, Any]) -> dict[str, Any]:
    """Build a review-oriented quality report without rendering or publishing.

    The PPTX renderer uses fixed slots for teaching layouts and deterministic
    layout inference for legacy DSLs. These checks make truncation visible to a
    reviewer and catch empty or overly dense source content before it is
    mistaken for a finished deck. The report is intentionally advisory: it
    never changes the DSL or review status.
    """

    spec = ppt.get("spec") if isinstance(ppt, dict) else None
    metadata = ppt.get("metadata") if isinstance(ppt, dict) else None
    metadata_source = metadata if isinstance(metadata, dict) else {}
    hero_fallback = hero_subtitle_fallback(
        metadata_source.get("audience"),
        presentation_duration_label(metadata_source.get("durationMinutes")),
    )
    slides = spec.get("slides") if isinstance(spec, dict) else None
    if not isinstance(slides, list):
        return {
            "version": "ppt-preflight-v1",
            "status": "BLOCKED",
            "advisoryOnly": True,
            "manualReviewRequired": True,
            "slideTotal": 0,
            "blockingIssueTotal": 1,
            "warningIssueTotal": 0,
            "issueTotal": 1,
            "recommendedAction": "repair_ppt_dsl_before_review",
            "issues": [
                {
                    "code": "SLIDES_MISSING",
                    "severity": "BLOCKING",
                    "path": "$.spec.slides",
                    "message": "PPT DSL must contain a slide array.",
                }
            ],
            "slides": [],
        }

    slide_reports = [
        _build_slide_report(slide, index=index, total=len(slides), hero_fallback=hero_fallback)
        for index, slide in enumerate(slides, start=1)
        if isinstance(slide, dict)
    ]
    issues = [issue for slide in slide_reports for issue in slide["issues"]]
    blocking_total = sum(issue["severity"] == "BLOCKING" for issue in issues)
    warning_total = sum(issue["severity"] == "WARNING" for issue in issues)
    if blocking_total:
        status = "BLOCKED"
        recommended_action = "repair_ppt_dsl_before_review"
    elif warning_total:
        status = "NEEDS_REVIEW"
        recommended_action = "review_ppt_quality_warnings"
    else:
        status = "PASS"
        recommended_action = "review_pptx_pages"

    return {
        "version": "ppt-preflight-v1",
        "status": status,
        "advisoryOnly": True,
        "manualReviewRequired": True,
        "slideTotal": len(slides),
        "reportedSlideTotal": len(slide_reports),
        "titleSlideTotal": sum(slide["isTitleSlide"] for slide in slide_reports),
        "contentSlideTotal": sum(not slide["isTitleSlide"] for slide in slide_reports),
        "blockingIssueTotal": blocking_total,
        "warningIssueTotal": warning_total,
        "issueTotal": len(issues),
        "recommendedAction": recommended_action,
        "issues": issues,
        "slides": slide_reports,
    }


def _build_slide_report(
    slide: dict[str, Any],
    *,
    index: int,
    total: int,
    hero_fallback: str,
) -> dict[str, Any]:
    slide_type = str(slide.get("type") or ("title" if index == 1 else "content")).lower()
    explicit_layout = _normalize_layout(slide.get("layout"))
    title = _normalize_text(slide.get("title"))
    layout = resolve_ppt_layout(
        explicit_layout=explicit_layout,
        index=index,
        total=total,
        slide_type=slide_type,
        title=title,
    )
    rendered_bullet_limit = rendered_bullet_limit_for_layout(layout)
    title_character_limit = title_character_limit_for_layout(layout)
    subtitle_character_limit = subtitle_character_limit_for_layout(layout)
    source_subtitle = _normalize_text(slide.get("subtitle"))
    subtitle = source_subtitle or (hero_fallback if layout == "hero" else "")
    subtitle_source = "SLIDE" if source_subtitle else "METADATA_FALLBACK" if layout == "hero" else "NONE"
    subtitle_path = f"$.spec.slides[{index - 1}].subtitle" if source_subtitle else "$.metadata.audience"
    bullets = [
        _normalize_text(item)
        for item in slide.get("bullets", [])
        if _normalize_text(item)
    ] if isinstance(slide.get("bullets"), list) else []
    rendered_bullets = bullets[:rendered_bullet_limit]
    body_items = rendered_bullets or ([subtitle] if subtitle else [])
    body_characters = sum(len(item) for item in body_items)
    issues: list[dict[str, Any]] = []

    if not title:
        issues.append(
            _issue(
                "SLIDE_TITLE_MISSING",
                "BLOCKING",
                f"$.spec.slides[{index - 1}].title",
                "Every slide needs a non-empty title.",
            )
        )
    if len(title) > title_character_limit:
        issues.append(
            _issue(
                "SLIDE_TITLE_LONG",
                "WARNING",
                f"$.spec.slides[{index - 1}].title",
                (
                    f"Title has {len(title)} characters; the renderer's safe limit "
                    f"for this layout is {title_character_limit}."
                ),
            )
        )
    if len(subtitle) > subtitle_character_limit:
        issues.append(
            _issue(
                "SUBTITLE_TEXT_LONG",
                "WARNING",
                subtitle_path,
                (
                    f"Subtitle has {len(subtitle)} characters; the renderer's safe limit "
                    f"for this layout is {subtitle_character_limit}."
                ),
            )
        )
    if not body_items and slide_type != "title":
        issues.append(
            _issue(
                "SLIDE_BODY_MISSING",
                "WARNING",
                f"$.spec.slides[{index - 1}]",
                "Content and summary slides should include bullets or a subtitle.",
            )
        )
    if len(bullets) > rendered_bullet_limit:
        layout_label = f"{layout} layout" if layout else "legacy renderer"
        issues.append(
            _issue(
                "BULLETS_TRUNCATED_BY_RENDERER",
                "WARNING",
                f"$.spec.slides[{index - 1}].bullets",
                f"The {layout_label} displays at most {rendered_bullet_limit} bullets.",
            )
        )
    for bullet_index, bullet in enumerate(bullets):
        bullet_character_limit = bullet_character_limit_for_layout(layout, bullet_index)
        if len(bullet) > bullet_character_limit:
            issues.append(
                _issue(
                    "BULLET_TEXT_LONG",
                    "WARNING",
                    f"$.spec.slides[{index - 1}].bullets[{bullet_index}]",
                    (
                        f"Bullet has {len(bullet)} characters; the renderer's safe limit "
                        f"for this slot is {bullet_character_limit}."
                    ),
                )
            )
    if body_characters > MAX_BODY_CHARACTERS:
        issues.append(
            _issue(
                "SLIDE_CONTENT_DENSE",
                "WARNING",
                f"$.spec.slides[{index - 1}]",
                f"Rendered body content has {body_characters} characters; reduce density before approval.",
            )
        )

    blocking = any(issue["severity"] == "BLOCKING" for issue in issues)
    quality_status = "BLOCKED" if blocking else "WARNING" if issues else "PASS"
    return {
        "index": index,
        "id": slide.get("id"),
        "type": slide_type,
        "layout": layout,
        "layoutSource": "EXPLICIT" if explicit_layout else "INFERRED",
        "isTitleSlide": index == 1 or slide_type == "title",
        "titleCharacterTotal": len(title),
        "renderedTitleCharacterLimit": title_character_limit,
        "subtitleCharacterTotal": len(subtitle),
        "renderedSubtitleCharacterLimit": subtitle_character_limit,
        "subtitleSource": subtitle_source,
        "bulletTotal": len(bullets),
        "renderedBulletLimit": rendered_bullet_limit,
        "renderedBulletTotal": len(rendered_bullets),
        "bodyCharacterTotal": body_characters,
        "visualDensity": _visual_density(len(body_items), body_characters),
        "estimatedTextOverflow": any(
            issue["code"] in {
                "SLIDE_TITLE_LONG",
                "SUBTITLE_TEXT_LONG",
                "BULLET_TEXT_LONG",
                "SLIDE_CONTENT_DENSE",
            }
            for issue in issues
        ),
        "status": quality_status,
        "issues": issues,
    }


def rendered_bullet_limit_for_layout(layout: Any) -> int:
    return LAYOUT_RENDERED_BULLET_LIMITS.get(_normalize_layout(layout), MAX_RENDERED_BULLETS)


def title_character_limit_for_layout(layout: Any) -> int:
    return LAYOUT_TITLE_CHARACTER_LIMITS.get(_normalize_layout(layout), MAX_TITLE_CHARACTERS)


def subtitle_character_limit_for_layout(layout: Any) -> int:
    return LAYOUT_SUBTITLE_CHARACTER_LIMITS.get(_normalize_layout(layout), MAX_SUBTITLE_CHARACTERS)


def bullet_character_limit_for_layout(layout: Any, bullet_index: int) -> int:
    limits = LAYOUT_BULLET_CHARACTER_LIMITS.get(_normalize_layout(layout))
    if not limits:
        return MAX_BULLET_CHARACTERS
    return limits[min(max(0, bullet_index), len(limits) - 1)]


def resolve_ppt_layout(
    *,
    explicit_layout: Any,
    index: int,
    total: int,
    slide_type: str,
    title: str,
) -> str:
    layout = _normalize_layout(explicit_layout)
    if layout:
        return layout
    normalized_title = _normalize_text(title).casefold()
    if index == 1 or slide_type == "title":
        return "hero"
    if slide_type == "summary" or index == total:
        return "summary"
    if any(token in normalized_title for token in ("objective", "goal", "learning outcome", "目标")):
        return "objectives"
    if any(token in normalized_title for token in ("process", "workflow", "steps", "流程", "步骤")):
        return "process"
    if any(token in normalized_title for token in ("exercise", "practice", "task", "练习", "实践")):
        return "exercise"
    return "concept"


def presentation_duration_label(value: Any) -> str:
    if isinstance(value, bool):
        return "Course session"
    if isinstance(value, (int, float)) and value > 0:
        return f"{int(value)} min"
    return "Course session"


def hero_subtitle_fallback(audience: Any, duration: Any) -> str:
    audience_text = _normalize_text(audience) or "Learners"
    duration_text = _normalize_text(duration) or "Course session"
    return f"{audience_text}  |  {duration_text}"


def _issue(code: str, severity: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "path": path, "message": message}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_layout(value: Any) -> str:
    return _normalize_text(value).lower()


def _visual_density(body_item_total: int, body_characters: int) -> str:
    if body_item_total == 0:
        return "LOW"
    if body_item_total >= 5 or body_characters > 280:
        return "HIGH"
    if body_item_total >= 2 or body_characters > 100:
        return "BALANCED"
    return "LOW"
