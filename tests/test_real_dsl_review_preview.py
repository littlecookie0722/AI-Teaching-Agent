from pathlib import Path

from ai_workflows.real_dsl_review_preview import (
    RealDslReviewPreviewError,
    build_real_dsl_review_preview_from_files,
)
from cli.dsl import load_yaml


ROOT = Path(__file__).resolve().parents[1]


def test_build_real_dsl_review_preview_from_real_outputs():
    lab = load_yaml(ROOT / "examples/output/real-llm-lab.json")
    exam = load_yaml(ROOT / "examples/output/real-llm-exam.json")
    grading = load_yaml(ROOT / "examples/output/real-llm-grading.json")
    ppt = load_yaml(ROOT / "examples/output/real-llm-ppt.json")
    preview = build_real_dsl_review_preview_from_files(
        lab_path=ROOT / "examples/output/real-llm-lab.json",
        exam_path=ROOT / "examples/output/real-llm-exam.json",
        grading_path=ROOT / "examples/output/real-llm-grading.json",
        ppt_path=ROOT / "examples/output/real-llm-ppt.json",
        candidate_preview_path=ROOT / "examples/output/real-llm-demo-candidate-preview.json",
        root=ROOT,
        trace_id="trace_real_dsl_preview",
    )

    assert preview["component"] == "RealDslReviewPreview"
    assert preview["mode"] == "STATIC_REAL_LLM_DSL_REVIEW_PREVIEW"
    assert preview["summary"]["labStepTotal"] == len(lab["spec"]["steps"])
    assert preview["summary"]["examQuestionTotal"] == len(exam["spec"]["questions"])
    assert preview["summary"]["gradingPlanTotal"] == len(grading["spec"]["assessmentPlan"])
    assert preview["summary"]["gradingCheckTotal"] == len(grading["spec"]["checks"])
    assert preview["summary"]["pptSlideTotal"] == len(ppt["spec"]["slides"])
    assert preview["summary"]["allDslWaitingReview"] is True
    assert preview["summary"]["qualityIssueTotal"] == len(preview["reviewIssues"])
    assert preview["summary"]["revisionSuggestionTotal"] == len(preview["revisionSuggestions"])
    assert preview["summary"]["qualityStatus"] in {"READY_FOR_REVIEW", "NEEDS_REVIEW", "NEEDS_REVISION"}
    assert [step["id"] for step in preview["labReview"]["steps"]] == [step["id"] for step in lab["spec"]["steps"]]
    assert [question["id"] for question in preview["examReview"]["candidateQuestions"]] == [
        question["id"] for question in exam["spec"]["questions"]
    ]
    assert all(
        question["answerVisibleToCandidate"] is False
        and question["gradingRefVisibleToCandidate"] is False
        for question in preview["examReview"]["candidateQuestions"]
    )
    assert preview["examReview"]["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    assert "questions[].gradingRef" in preview["examReview"]["candidateSafety"]["removedFields"]
    assert all(ref["teacherOnly"] is True and ref["candidateVisible"] is False for ref in preview["examReview"]["teacherQuestionRefs"])
    assert [plan["checkId"] for plan in preview["gradingReview"]["assessmentPlan"]] == [
        plan["checkId"] for plan in grading["spec"]["assessmentPlan"]
    ]
    assert preview["gradingReview"]["commandExecutionAllowedFromPage"] is False
    assert preview["gradingReview"]["realSandboxExecutionAllowedFromPage"] is False
    assert [slide["id"] for slide in preview["pptReview"]["slides"]] == [slide["id"] for slide in ppt["spec"]["slides"]]
    assert preview["qualitySignals"]["summary"]["manualReviewRequired"] is True
    assert preview["qualitySignals"]["summary"]["autoApproveAllowed"] is False
    assert preview["qualitySignals"]["summary"]["realPublishAllowed"] is False
    assert preview["qualitySignals"]["coverage"]["candidatePreviewAnswerSafe"] is True
    assert preview["qualitySignals"]["coverage"]["gradingRefsCovered"] is True
    assert any(issue["id"] == "lab_objective_depth" for issue in preview["reviewIssues"])
    assert any(issue["id"] == "grading_sandbox_execution_required" for issue in preview["reviewIssues"])
    assert any(suggestion["kind"] == "lab" for suggestion in preview["revisionSuggestions"])
    assert all(suggestion["keepsWaitingReview"] is True for suggestion in preview["revisionSuggestions"])
    assert all(suggestion["autoPublishAllowed"] is False for suggestion in preview["revisionSuggestions"])
    assert preview["safety"]["gradingRefVisibleToCandidate"] is False
    assert preview["safety"]["teacherOnlyGradingRefVisibleInReview"] is True
    assert preview["safety"]["realPublishAllowed"] is False
    assert preview["traceId"] == "trace_real_dsl_preview"


def test_build_real_dsl_review_preview_rejects_missing_lab(tmp_path):
    try:
        build_real_dsl_review_preview_from_files(
            lab_path=tmp_path / "missing-lab.json",
            exam_path=ROOT / "examples/output/real-llm-exam.json",
            grading_path=ROOT / "examples/output/real-llm-grading.json",
            ppt_path=ROOT / "examples/output/real-llm-ppt.json",
            candidate_preview_path=ROOT / "examples/output/real-llm-demo-candidate-preview.json",
            root=ROOT,
        )
    except RealDslReviewPreviewError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "lab"
    else:
        raise AssertionError("expected RealDslReviewPreviewError")
