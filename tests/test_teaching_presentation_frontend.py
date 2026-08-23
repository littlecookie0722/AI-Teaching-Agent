import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def presentation_logic() -> str:
    script = read_text("frontend/review-center-data.js")
    return script.split("function postPresentationJson", 1)[1].split("function packagePill", 1)[0]


def function_source(script: str, name: str, next_name: str) -> str:
    return script.split(f"function {name}", 1)[1].split(f"function {next_name}", 1)[0]


def test_review_center_has_responsive_presentation_review_workspace():
    html = read_text("frontend/review-center.html")

    required_ids = {
        "teaching-presentation-generation-action",
        "teaching-presentation-generation-status",
        "teaching-presentation-generate-button",
        "presentation-deck-review",
        "presentation-deck-slide-total",
        "presentation-deck-schema",
        "presentation-deck-quality",
        "presentation-deck-page-progress",
        "presentation-active-preview",
        "presentation-preview-empty",
        "presentation-thumbnail-list",
        "presentation-contact-sheet-image",
        "presentation-deck-reviewer",
        "presentation-slide-comment",
        "presentation-deck-reject-reason",
        "presentation-deck-approve-button",
        "presentation-deck-reject-button",
        "presentation-deck-download",
    }
    for element_id in required_ids:
        assert f'id="{element_id}"' in html

    assert "aspect-ratio: 16 / 9" in html
    assert "@media (max-width: 920px)" in html
    assert "@media (max-width: 620px)" in html
    assert html.count('data-presentation-slide-status="') == 3
    assert 'data-presentation-slide-status="APPROVED"' in html
    assert 'data-presentation-slide-status="NEEDS_REVIEW"' in html
    assert 'data-presentation-slide-status="REVISE_REQUIRED"' in html
    assert 'id="teaching-presentation-generation-action" hidden' in html
    assert 'id="presentation-deck-review" aria-labelledby="presentation-deck-title" hidden' in html


def test_approved_teaching_package_generates_six_slide_child_workflow():
    script = read_text("frontend/review-center-data.js")
    generation = function_source(
        script,
        "applyTeachingPresentationGenerationState",
        "generateTeachingPresentation",
    )
    request = function_source(
        script,
        "generateTeachingPresentation",
        "setupTeachingPresentationGenerationAction",
    )

    assert 'teachingPresentationGeneratePath: "/api/teaching-presentations/generate"' in script
    assert 'packageReview.status === "APPROVED"' in generation
    assert "packageReview.exportReady === true" in generation
    assert "action.hidden = !available" in generation
    assert re.search(
        r"postPresentationJson\(state\.teachingPresentationGeneratePath,\s*\{\s*"
        r"workflowRunId: workflowRunId,\s*reviewer: reviewer,\s*slideCount: 6\s*\}\)",
        request,
    )
    assert "result.childWorkflowRun && result.childWorkflowRun.id" in request
    assert "result.task && result.task.id" in request
    assert 'target.searchParams.set("workflowRunId", childWorkflowRunId)' in request
    assert 'target.searchParams.set("taskId", taskId)' in request
    assert "window.location.assign(target.toString())" in request


def test_presentation_review_consumes_summary_and_only_returned_safe_urls():
    script = read_text("frontend/review-center-data.js")
    logic = presentation_logic()
    apply_summary = function_source(script, "applySummary", "applyDetail")

    assert "summary.presentationDeckReview || null" in apply_summary
    assert "applyPresentationDeckReview" in apply_summary
    assert "deck.slidePreviews" in logic
    assert "slide.imageUrl" in logic
    assert "deck.contactSheetUrl" in logic
    assert "deck.pptxArtifact && deck.pptxArtifact.downloadUrl" in logic
    assert 'url.origin !== window.location.origin' in logic
    assert 'url.pathname.indexOf("/api/ppt-artifacts/") !== 0' in logic
    assert 'image.setAttribute("src", safeUrl)' in logic
    assert 'download.setAttribute("href", downloadUrl)' in logic
    assert "imagePath" not in logic
    assert "outputPath" not in logic


def test_page_review_requires_manual_revision_comment_and_refreshes_summary():
    script = read_text("frontend/review-center-data.js")
    page_review = function_source(
        script,
        "updatePresentationSlideReviewStatus",
        "reviewPresentationDeck",
    )

    assert (
        'presentationPageReviewPathTemplate: "/api/review-tasks/{id}/ppt-page-review-status"'
        in script
    )
    for status in ("APPROVED", "NEEDS_REVIEW", "REVISE_REQUIRED"):
        assert f'"{status}"' in page_review
    assert 'reviewStatus === "REVISE_REQUIRED" && !comment' in page_review
    assert '"comment is required for REVISE_REQUIRED"' in page_review
    assert "slideIndex: Number(slide.index)" in page_review
    assert "reviewStatus: reviewStatus" in page_review
    assert "reviewer: reviewer" in page_review
    assert "comment: comment || null" in page_review
    assert "return loadReviewCenterData()" in page_review


def test_task_decisions_keep_all_page_approval_and_reject_reason_gates():
    script = read_text("frontend/review-center-data.js")
    approval_gate = function_source(
        script,
        "presentationTaskApproveAllowed",
        "updatePresentationReviewControls",
    )
    task_review = function_source(script, "reviewPresentationDeck", "setupPresentationReviewActions")

    assert 'presentationTaskActionPathTemplate: "/api/ai-tasks/{id}/{action}"' in script
    assert "state.presentationApproveReady === true" in approval_gate
    assert "deck.approveReady === true" in approval_gate
    assert 'deck.status === "WAITING_REVIEW"' in approval_gate
    assert "deck.schemaValidated === true" in approval_gate
    assert "presentationSlideCountIsValid" in approval_gate
    assert "presentationAllSlidesApproved" in approval_gate
    assert "presentationPreviewUrlsAreSafe" in approval_gate
    assert 'action === "approve" && !presentationTaskApproveAllowed()' in task_review
    assert 'action === "reject" && !reason' in task_review
    assert '"reason is required for reject"' in task_review
    assert "body.reason = reason" in task_review
    assert "return loadReviewCenterData()" in task_review


def test_download_requires_returned_safe_url_and_approved_task():
    script = read_text("frontend/review-center-data.js")
    controls = function_source(
        script,
        "updatePresentationReviewControls",
        "resetPresentationDeckReview",
    )
    logic = presentation_logic()

    assert "state.presentationDownloadReady === true" in controls
    assert "deck.downloadReady === true" in controls
    assert 'deck.status === "APPROVED"' in controls
    assert "Boolean(downloadUrl)" in controls
    assert 'download.removeAttribute("href")' in controls
    assert 'download.setAttribute("aria-disabled", "true")' in controls
    assert "new Blob" not in logic
    assert "createObjectURL" not in logic


def test_new_presentation_flow_does_not_reopen_old_ppt_or_platform_import_pages():
    logic = presentation_logic()

    assert "ppt-review.html" not in logic
    assert "ppt-generation.html" not in logic
    assert "/api/ppt/import-preview" not in logic
    assert "/api/ppt/mock-import" not in logic
    assert "/import-send" not in logic
    assert "/import-status" not in logic
    assert "/publish" not in logic
