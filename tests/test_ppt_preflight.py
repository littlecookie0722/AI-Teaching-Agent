from __future__ import annotations

from pathlib import Path

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
    assert report["slideTotal"] == 2
    assert report["contentSlideTotal"] == 1
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
                    "bullets": ["x" * 120 for _ in range(7)],
                },
            ]
        }
    }

    report = build_ppt_preflight_report(ppt)
    content_slide = report["slides"][1]

    assert report["status"] == "NEEDS_REVIEW"
    assert report["blockingIssueTotal"] == 0
    assert report["warningIssueTotal"] == 9
    assert content_slide["renderedBulletTotal"] == 6
    assert content_slide["estimatedTextOverflow"] is True
    assert content_slide["visualDensity"] == "HIGH"
    assert {issue["code"] for issue in content_slide["issues"]} == {
        "BULLETS_TRUNCATED_BY_RENDERER",
        "BULLET_TEXT_LONG",
        "SLIDE_CONTENT_DENSE",
    }


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
