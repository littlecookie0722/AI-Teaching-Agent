from __future__ import annotations

from pathlib import Path

import pytest

from cli.dsl import load_yaml
from quality.ppt_preflight import build_ppt_preflight_report


ROOT = Path(__file__).resolve().parents[1]


def test_course_ppt_preflight_is_clean_but_still_requires_manual_review():
    ppt = load_yaml(ROOT / "templates/ppt/examples/course-ppt.yaml")

    report = build_ppt_preflight_report(ppt)

    assert report["version"] == "ppt-preflight-v1"
    assert report["status"] == "PASS"
    assert report["advisoryOnly"] is True
    assert report["manualReviewRequired"] is True
    assert report["slideTotal"] == 6
    assert report["contentSlideTotal"] == 5
    assert report["issueTotal"] == 0
    assert report["slides"][1]["visualDensity"] == "BALANCED"
    assert report["slides"][1]["renderedBulletTotal"] == 3


def test_ppt_preflight_reports_renderer_truncation_and_dense_text():
    ppt = {
        "spec": {
            "slides": [
                {
                    "id": "slide_1",
                    "type": "title",
                    "title": "A title",
                },
                {
                    "id": "slide_2",
                    "type": "content",
                    "title": "A content slide",
                    "bullets": ["x" * 121 for _ in range(7)],
                },
            ]
        }
    }

    report = build_ppt_preflight_report(ppt)
    content_slide = report["slides"][1]

    assert report["status"] == "NEEDS_REVIEW"
    assert report["blockingIssueTotal"] == 0
    assert report["warningIssueTotal"] == 9
    assert content_slide["layout"] == "summary"
    assert content_slide["layoutSource"] == "INFERRED"
    assert content_slide["renderedBulletTotal"] == 3
    assert content_slide["renderedBulletLimit"] == 3
    assert content_slide["estimatedTextOverflow"] is True
    assert content_slide["visualDensity"] == "HIGH"
    assert {issue["code"] for issue in content_slide["issues"]} == {
        "BULLETS_TRUNCATED_BY_RENDERER",
        "BULLET_TEXT_LONG",
        "SLIDE_CONTENT_DENSE",
    }


def test_ppt_preflight_infers_legacy_layout_before_reporting_capacity():
    report = build_ppt_preflight_report(
        {
            "spec": {
                "slides": [
                    {"id": "slide_1", "type": "title", "title": "课程"},
                    {
                        "id": "slide_2",
                        "type": "content",
                        "title": "学习目标",
                        "bullets": [f"目标 {index}" for index in range(5)],
                    },
                    {"id": "slide_3", "type": "summary", "title": "总结", "bullets": ["回顾"]},
                ]
            }
        }
    )

    objectives = report["slides"][1]
    assert objectives["layout"] == "objectives"
    assert objectives["layoutSource"] == "INFERRED"
    assert objectives["renderedBulletLimit"] == 3
    assert objectives["renderedBulletTotal"] == 3
    assert {issue["code"] for issue in objectives["issues"]} == {"BULLETS_TRUNCATED_BY_RENDERER"}


@pytest.mark.parametrize(
    ("layout", "bullet_total", "rendered_limit"),
    [
        ("objectives", 4, 3),
        ("concept", 5, 4),
        ("process", 5, 4),
        ("exercise", 5, 4),
        ("summary", 4, 3),
    ],
)
def test_ppt_preflight_uses_explicit_layout_capacity(layout, bullet_total, rendered_limit):
    report = build_ppt_preflight_report(
        {
            "spec": {
                "slides": [
                    {
                        "id": "slide_1",
                        "type": "summary" if layout == "summary" else "content",
                        "layout": layout,
                        "title": "Short title",
                        "bullets": [f"item {index}" for index in range(bullet_total)],
                    }
                ]
            }
        }
    )

    slide = report["slides"][0]
    assert report["status"] == "NEEDS_REVIEW"
    assert slide["renderedBulletLimit"] == rendered_limit
    assert slide["renderedBulletTotal"] == rendered_limit
    assert {issue["code"] for issue in slide["issues"]} == {"BULLETS_TRUNCATED_BY_RENDERER"}


def test_ppt_preflight_flags_layout_specific_long_chinese_text():
    report = build_ppt_preflight_report(
        {
            "spec": {
                "slides": [
                    {
                        "id": "slide_1",
                        "type": "title",
                        "layout": "hero",
                        "title": "课" * 25,
                        "subtitle": "学习者" * 20,
                    },
                    {
                        "id": "slide_2",
                        "type": "content",
                        "layout": "process",
                        "title": "实验步骤",
                        "bullets": ["步" * 31],
                    },
                    {
                        "id": "slide_3",
                        "type": "content",
                        "layout": "exercise",
                        "title": "课堂练习",
                        "subtitle": "检查" * 19,
                        "bullets": ["完成主要任务"],
                    },
                ]
            }
        }
    )

    assert report["status"] == "NEEDS_REVIEW"
    assert report["slides"][0]["estimatedTextOverflow"] is True
    assert report["slides"][1]["estimatedTextOverflow"] is True
    assert report["slides"][2]["estimatedTextOverflow"] is True
    assert {issue["code"] for issue in report["issues"]} == {
        "SLIDE_TITLE_LONG",
        "SUBTITLE_TEXT_LONG",
        "BULLET_TEXT_LONG",
    }
    assert sum(issue["code"] == "SUBTITLE_TEXT_LONG" for issue in report["issues"]) == 2


@pytest.mark.parametrize(
    ("layout", "slide_type", "limit"),
    [("hero", "title", 22), ("exercise", "content", 23), ("summary", "summary", 21)],
)
@pytest.mark.parametrize(("extra_characters", "expected_status"), [(0, "PASS"), (1, "NEEDS_REVIEW")])
def test_ppt_preflight_title_limits_match_cross_platform_renderer(
    layout,
    slide_type,
    limit,
    extra_characters,
    expected_status,
):
    slide = {
        "id": "slide_1",
        "type": slide_type,
        "layout": layout,
        "title": "W" * (limit + extra_characters),
    }
    if layout != "hero":
        slide["bullets"] = ["Takeaway"]
    report = build_ppt_preflight_report(
        {
            "spec": {
                "slides": [slide]
            }
        }
    )

    assert report["status"] == expected_status
    assert report["slides"][0]["renderedTitleCharacterLimit"] == limit


def test_ppt_preflight_checks_hero_metadata_fallback_subtitle():
    report = build_ppt_preflight_report(
        {
            "metadata": {"audience": "W" * 49, "durationMinutes": 45},
            "spec": {
                "slides": [
                    {
                        "id": "slide_1",
                        "type": "title",
                        "layout": "hero",
                        "title": "Course title",
                    }
                ]
            },
        }
    )

    slide = report["slides"][0]
    assert report["status"] == "NEEDS_REVIEW"
    assert slide["subtitleSource"] == "METADATA_FALLBACK"
    assert slide["subtitleCharacterTotal"] == len("W" * 49 + "  |  45 min")
    assert slide["estimatedTextOverflow"] is True
    assert slide["issues"] == [
        {
            "code": "SUBTITLE_TEXT_LONG",
            "severity": "WARNING",
            "path": "$.metadata.audience",
            "message": (
                f"Subtitle has {len('W' * 49 + '  |  45 min')} characters; "
                "the renderer's safe limit for this layout is 48."
            ),
        }
    ]


def test_ppt_preflight_marks_missing_title_as_blocking_without_mutating_source():
    ppt = {
        "spec": {
            "slides": [
                {
                    "id": "slide_1",
                    "type": "title",
                    "title": "",
                }
            ]
        }
    }

    report = build_ppt_preflight_report(ppt)

    assert report["status"] == "BLOCKED"
    assert report["blockingIssueTotal"] == 1
    assert report["recommendedAction"] == "repair_ppt_dsl_before_review"
    assert report["issues"][0]["code"] == "SLIDE_TITLE_MISSING"
    assert ppt["spec"]["slides"][0]["title"] == ""


def test_ppt_preflight_returns_json_safe_block_for_missing_slides():
    report = build_ppt_preflight_report({"spec": {}})

    assert report["status"] == "BLOCKED"
    assert report["slideTotal"] == 0
    assert report["blockingIssueTotal"] == 1
    assert report["issues"][0]["path"] == "$.spec.slides"
