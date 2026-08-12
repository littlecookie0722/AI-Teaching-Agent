import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_example():
    with (ROOT / "examples/review-detail/lab-review-detail.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_review_detail_example_is_phase1_mock_only():
    example = load_example()

    assert example["mode"] == "MOCK_ONLY"
    assert example["task"]["status"] == "WAITING_REVIEW"
    assert example["reviewPolicy"]["reviewRequired"] is True
    assert example["reviewPolicy"]["publishBlockedUntilApproved"] is True
    assert example["reviewPolicy"]["autoPublishAllowed"] is False
    assert example["safety"]["realLlmCalled"] is False
    assert example["safety"]["realCloudResourceChanged"] is False
    assert example["safety"]["sandboxExecuted"] is False
    assert example["safety"]["contestantCodeExecuted"] is False
    assert example["safety"]["realPublish"] is False


def test_review_detail_example_has_frontend_page_model():
    example = load_example()
    review_page = example["reviewPage"]

    assert review_page["header"]["taskId"] == example["task"]["id"]
    assert review_page["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert (ROOT / review_page["dslPreview"]["path"]).exists()
    assert review_page["riskSummary"]["unknownShellExecuted"] is False
    assert review_page["riskSummary"]["answerVisibleToCandidate"] is False
    assert review_page["actionBar"]["approve"]["enabled"] is True
    assert review_page["actionBar"]["reject"]["requiresReason"] is True
    assert review_page["actionBar"]["mockPublish"]["enabled"] is False
    assert review_page["actionBar"]["mockPublish"]["realPublish"] is False


def test_review_detail_example_artifacts_are_safe():
    example = load_example()

    assert example["summary"]["artifactTotal"] == len(example["artifacts"])
    for artifact in example["artifacts"]:
        assert artifact["mode"] == "MOCK_ONLY"
        assert artifact["realLlmCalled"] is False
        assert artifact["realCloudResourceChanged"] is False
        assert artifact["sandboxExecuted"] is False
        assert artifact["contestantCodeExecuted"] is False
        assert artifact["realPublish"] is False
