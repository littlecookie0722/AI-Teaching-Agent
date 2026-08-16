"""Deterministic, advisory quality checks for generated PPT DSL artifacts."""

from __future__ import annotations

from typing import Any


MAX_RENDERED_BULLETS = 6
MAX_TITLE_CHARACTERS = 32
MAX_BULLET_CHARACTERS = 96
MAX_BODY_CHARACTERS = 360


def build_ppt_preflight_report(ppt: dict[str, Any]) -> dict[str, Any]:
    """Build a review-oriented quality report without rendering or publishing.

    The PPTX renderer currently truncates content slides to six bullets. These
    checks make that behavior visible to a reviewer and catch empty or overly
    dense source content before it is mistaken for a finished deck. The report
    is intentionally advisory: it never changes the DSL or review status.
    """

    spec = ppt.get("spec") if isinstance(ppt, dict) else None
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
        _build_slide_report(slide, index=index)
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


def _build_slide_report(slide: dict[str, Any], *, index: int) -> dict[str, Any]:
    slide_type = str(slide.get("type") or ("title" if index == 1 else "content"))
    title = _normalize_text(slide.get("title"))
    subtitle = _normalize_text(slide.get("subtitle"))
    bullets = [
        _normalize_text(item)
        for item in slide.get("bullets", [])
        if _normalize_text(item)
    ] if isinstance(slide.get("bullets"), list) else []
    body_items = bullets or ([subtitle] if subtitle else [])
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
    if len(title) > MAX_TITLE_CHARACTERS:
        issues.append(
            _issue(
                "SLIDE_TITLE_LONG",
                "WARNING",
                f"$.spec.slides[{index - 1}].title",
                f"Title has {len(title)} characters; review possible title wrapping.",
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
    if len(bullets) > MAX_RENDERED_BULLETS:
        issues.append(
            _issue(
                "BULLETS_TRUNCATED_BY_RENDERER",
                "WARNING",
                f"$.spec.slides[{index - 1}].bullets",
                f"The renderer displays at most {MAX_RENDERED_BULLETS} bullets.",
            )
        )
    for bullet_index, bullet in enumerate(bullets):
        if len(bullet) > MAX_BULLET_CHARACTERS:
            issues.append(
                _issue(
                    "BULLET_TEXT_LONG",
                    "WARNING",
                    f"$.spec.slides[{index - 1}].bullets[{bullet_index}]",
                    f"Bullet has {len(bullet)} characters; review possible text wrapping.",
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
        "isTitleSlide": index == 1 or slide_type == "title",
        "titleCharacterTotal": len(title),
        "bulletTotal": len(bullets),
        "renderedBulletTotal": min(len(bullets), MAX_RENDERED_BULLETS),
        "bodyCharacterTotal": body_characters,
        "visualDensity": _visual_density(len(body_items), body_characters),
        "estimatedTextOverflow": any(
            issue["code"] in {"SLIDE_TITLE_LONG", "BULLET_TEXT_LONG", "SLIDE_CONTENT_DENSE"}
            for issue in issues
        ),
        "status": quality_status,
        "issues": issues,
    }


def _issue(code: str, severity: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "path": path, "message": message}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _visual_density(body_item_total: int, body_characters: int) -> str:
    if body_item_total == 0:
        return "LOW"
    if body_item_total >= 5 or body_characters > 280:
        return "HIGH"
    if body_item_total >= 2 or body_characters > 100:
        return "BALANCED"
    return "LOW"
