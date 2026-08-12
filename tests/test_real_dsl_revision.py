import json
from pathlib import Path

from ai_workflows.real_dsl_revision import (
    RealDslRevisionError,
    build_real_dsl_revision_diff_preview,
    create_real_dsl_revision_decision,
    create_real_dsl_revision_batch_from_preview,
    create_real_dsl_revision_draft,
    promote_real_dsl_revision_candidate,
)
from cli.dsl import load_schema, load_yaml, validate_dsl
from tests.test_real_llm_demo_dsl import FakeClient, lab_dsl_with_shape_drift


ROOT = Path(__file__).resolve().parents[1]


def test_create_real_dsl_revision_draft_keeps_schema_and_review_boundary(tmp_path):
    output = tmp_path / "lab-revision.json"
    report_output = tmp_path / "lab-revision-report.json"

    result = create_real_dsl_revision_draft(
        kind="lab",
        source_path=ROOT / "examples/output/real-llm-lab.json",
        reviewer="teacher_1",
        comment="请补充实验验收说明，并强调人工复核。",
        target_sections=["steps"],
        requested_changes=["补充验收标准"],
        output_path=output,
        report_output_path=report_output,
        root=ROOT,
        trace_id="trace_real_dsl_revision",
    )

    assert output.exists()
    assert report_output.exists()
    revised = load_yaml(output)
    validate_dsl(revised, load_schema("lab", ROOT))
    report = json.loads(report_output.read_text(encoding="utf-8"))
    assert result["realDslRevisionDraft"] == report
    assert report["component"] == "RealDslRevisionDraft"
    assert report["mode"] == "LOCAL_REAL_DSL_REVISION_DRAFT"
    assert report["kind"] == "lab"
    assert report["revisedStatus"] == "WAITING_REVIEW"
    assert report["schemaValidated"] is True
    assert report["manualReviewRequired"] is True
    assert "$.spec.steps[0].instruction" in report["changedFields"]
    assert report["safety"]["realLlmCalled"] is False
    assert report["safety"]["newLlmRequestSent"] is False
    assert report["safety"]["secretsRead"] is False
    assert report["safety"]["networkAccess"] is False
    assert report["safety"]["autoApproveAllowed"] is False
    assert report["safety"]["autoPublishAllowed"] is False
    assert report["safety"]["realPublishAllowed"] is False
    assert "人工复核" in revised["spec"]["steps"][0]["instruction"]


def test_create_real_dsl_revision_draft_supports_exam_teacher_only_grading_ref(tmp_path):
    output = tmp_path / "exam-revision.json"
    report_output = tmp_path / "exam-revision-report.json"

    result = create_real_dsl_revision_draft(
        kind="exam",
        source_path=ROOT / "examples/output/real-llm-exam.json",
        reviewer="teacher_1",
        comment="请强化评分参考说明，不要展示给选手。",
        output_path=output,
        report_output_path=report_output,
        root=ROOT,
    )

    revised = result["revisedDsl"]
    validate_dsl(revised, load_schema("exam", ROOT))
    assert revised["status"] == "WAITING_REVIEW"
    assert "不要展示给选手" in revised["spec"]["questions"][0]["gradingRef"]
    assert result["realDslRevisionDraft"]["safety"]["answerVisibleToCandidate"] is False
    assert result["realDslRevisionDraft"]["safety"]["gradingRefVisibleToCandidate"] is False


def test_create_real_dsl_revision_batch_from_preview_creates_waiting_review_drafts(tmp_path):
    report_output = tmp_path / "revision-batch-report.json"

    result = create_real_dsl_revision_batch_from_preview(
        preview_path=ROOT / "examples/output/real-llm-demo-real-dsl-review-preview.json",
        reviewer="teacher_1",
        output_dir=tmp_path,
        report_output_path=report_output,
        root=ROOT,
        trace_id="trace_real_dsl_revision_batch",
    )

    assert report_output.exists()
    batch = result["realDslRevisionBatch"]
    assert batch["component"] == "RealDslRevisionBatch"
    assert batch["mode"] == "LOCAL_REAL_DSL_REVISION_BATCH"
    assert batch["draftTotal"] == 3
    assert batch["schemaValidatedTotal"] == 3
    assert batch["allDraftsWaitingReview"] is True
    assert batch["draftKinds"] == ["grading", "lab", "ppt"]
    assert batch["safety"]["realLlmCalled"] is False
    assert batch["safety"]["newLlmRequestSent"] is False
    assert batch["safety"]["secretsRead"] is False
    assert batch["safety"]["networkAccess"] is False
    assert batch["safety"]["realPublishAllowed"] is False
    for draft in batch["drafts"]:
        output_path = ROOT / draft["outputPath"]
        if not output_path.exists():
            output_path = tmp_path / Path(draft["outputPath"]).name
        assert output_path.exists()
        revised = load_yaml(output_path)
        validate_dsl(revised, load_schema(draft["kind"], ROOT))
        assert revised["status"] == "WAITING_REVIEW"


def test_build_real_dsl_revision_diff_preview_summarizes_changed_fields(tmp_path):
    batch_report = tmp_path / "revision-batch-report.json"
    diff_output = tmp_path / "revision-diff-preview.json"
    create_real_dsl_revision_batch_from_preview(
        preview_path=ROOT / "examples/output/real-llm-demo-real-dsl-review-preview.json",
        reviewer="teacher_1",
        output_dir=tmp_path,
        report_output_path=batch_report,
        root=ROOT,
    )

    result = build_real_dsl_revision_diff_preview(
        batch_report_path=batch_report,
        output_path=diff_output,
        root=ROOT,
        trace_id="trace_real_dsl_revision_diff",
    )

    assert diff_output.exists()
    preview = result["realDslRevisionDiffPreview"]
    assert preview["component"] == "RealDslRevisionDiffPreview"
    assert preview["mode"] == "LOCAL_REAL_DSL_REVISION_DIFF_PREVIEW"
    assert preview["summary"]["draftTotal"] == 3
    assert preview["summary"]["diffTotal"] >= 12
    assert preview["summary"]["allDraftsWaitingReview"] is True
    assert preview["summary"]["manualReviewRequired"] is True
    assert {draft["kind"] for draft in preview["draftDiffs"]} == {"lab", "grading", "ppt"}
    first_diff = preview["draftDiffs"][0]["fieldDiffs"][0]
    assert first_diff["field"].startswith("$.")
    assert first_diff["changed"] is True
    assert preview["safety"]["realLlmCalled"] is False
    assert preview["safety"]["newLlmRequestSent"] is False
    assert preview["safety"]["secretsRead"] is False
    assert preview["safety"]["networkAccess"] is False
    assert preview["safety"]["realPublishAllowed"] is False


def test_create_real_dsl_revision_decision_records_manual_decision_without_publish(tmp_path):
    batch_report = tmp_path / "revision-batch-report.json"
    diff_output = tmp_path / "revision-diff-preview.json"
    decision_output = tmp_path / "revision-decision.json"
    create_real_dsl_revision_batch_from_preview(
        preview_path=ROOT / "examples/output/real-llm-demo-real-dsl-review-preview.json",
        reviewer="teacher_1",
        output_dir=tmp_path,
        report_output_path=batch_report,
        root=ROOT,
    )
    build_real_dsl_revision_diff_preview(
        batch_report_path=batch_report,
        output_path=diff_output,
        root=ROOT,
    )

    result = create_real_dsl_revision_decision(
        diff_preview_path=diff_output,
        suggestion_id="revise_lab_objective_depth",
        reviewer="teacher_1",
        decision="approve",
        reason="人工确认该修订可进入后续手动合并。",
        output_path=decision_output,
        root=ROOT,
        trace_id="trace_real_dsl_revision_decision",
    )

    assert decision_output.exists()
    decision = result["realDslRevisionDecision"]
    assert decision["component"] == "RealDslRevisionDecision"
    assert decision["decision"] == "approve"
    assert decision["decisionStatus"] == "REVISION_APPROVED_FOR_MANUAL_MERGE"
    assert decision["suggestionId"] == "revise_lab_objective_depth"
    assert decision["manualMergeRequired"] is True
    assert decision["sourceDslModified"] is False
    assert decision["revisedDslModified"] is False
    assert decision["safety"]["newLlmRequestSent"] is False
    assert decision["safety"]["autoApproveAllowed"] is False
    assert decision["safety"]["realPublishAllowed"] is False


def test_create_real_dsl_revision_decision_requires_reason_for_reject(tmp_path):
    diff_output = tmp_path / "revision-diff-preview.json"
    batch_report = tmp_path / "revision-batch-report.json"
    create_real_dsl_revision_batch_from_preview(
        preview_path=ROOT / "examples/output/real-llm-demo-real-dsl-review-preview.json",
        reviewer="teacher_1",
        output_dir=tmp_path,
        report_output_path=batch_report,
        root=ROOT,
    )
    build_real_dsl_revision_diff_preview(batch_report_path=batch_report, output_path=diff_output, root=ROOT)

    try:
        create_real_dsl_revision_decision(
            diff_preview_path=diff_output,
            suggestion_id="revise_lab_objective_depth",
            reviewer="teacher_1",
            decision="reject",
            root=ROOT,
        )
    except RealDslRevisionError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "reason"
    else:
        raise AssertionError("expected RealDslRevisionError")


def test_promote_real_dsl_revision_candidate_copies_approved_revision_as_waiting_review(tmp_path):
    batch_report = tmp_path / "revision-batch-report.json"
    diff_output = tmp_path / "revision-diff-preview.json"
    decision_output = tmp_path / "revision-decision.json"
    promoted_output = tmp_path / "revision-promoted.json"
    promotion_report = tmp_path / "revision-promotion-report.json"
    create_real_dsl_revision_batch_from_preview(
        preview_path=ROOT / "examples/output/real-llm-demo-real-dsl-review-preview.json",
        reviewer="teacher_1",
        output_dir=tmp_path,
        report_output_path=batch_report,
        root=ROOT,
    )
    build_real_dsl_revision_diff_preview(batch_report_path=batch_report, output_path=diff_output, root=ROOT)
    create_real_dsl_revision_decision(
        diff_preview_path=diff_output,
        suggestion_id="revise_lab_objective_depth",
        reviewer="teacher_1",
        decision="approve",
        output_path=decision_output,
        root=ROOT,
    )

    result = promote_real_dsl_revision_candidate(
        decision_report_path=decision_output,
        reviewer="teacher_2",
        output_path=promoted_output,
        report_output_path=promotion_report,
        root=ROOT,
        trace_id="trace_real_dsl_revision_promotion",
    )

    assert promoted_output.exists()
    assert promotion_report.exists()
    promoted = load_yaml(promoted_output)
    validate_dsl(promoted, load_schema("lab", ROOT))
    assert promoted["status"] == "WAITING_REVIEW"
    assert "_candidate_" in promoted["metadata"]["id"]
    promotion = result["realDslRevisionPromotion"]
    assert promotion["component"] == "RealDslRevisionPromotion"
    assert promotion["mode"] == "LOCAL_REAL_DSL_REVISION_PROMOTION"
    assert promotion["suggestionId"] == "revise_lab_objective_depth"
    assert promotion["promotedStatus"] == "WAITING_REVIEW"
    assert promotion["schemaValidated"] is True
    assert promotion["manualReviewRequired"] is True
    assert promotion["safety"]["sourceDslModified"] is False
    assert promotion["safety"]["revisedDslModified"] is False
    assert promotion["safety"]["promotedCandidateWritten"] is True
    assert promotion["safety"]["newLlmRequestSent"] is False
    assert promotion["safety"]["realPublishAllowed"] is False


def test_promote_real_dsl_revision_candidate_rejects_non_approved_decision(tmp_path):
    decision_output = tmp_path / "revision-rejected-decision.json"
    decision_output.write_text(
        json.dumps(
            {
                "component": "RealDslRevisionDecision",
                "decision": "request-change",
                "decisionStatus": "REVISION_CHANGE_REQUESTED",
                "kind": "lab",
                "revisedPath": "examples/output/real-llm-lab.json",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        promote_real_dsl_revision_candidate(
            decision_report_path=decision_output,
            reviewer="teacher_1",
            root=ROOT,
        )
    except RealDslRevisionError as exc:
        assert exc.code == "REVISION_NOT_APPROVED"
        assert exc.errors[0]["field"] == "decision"
    else:
        raise AssertionError("expected RealDslRevisionError")


def test_create_real_dsl_revision_draft_can_use_real_llm_provider_mode(tmp_path, monkeypatch):
    output = tmp_path / "lab-real-provider-revision.json"
    report_output = tmp_path / "lab-real-provider-revision-report.json"
    fake_client = FakeClient(lab_dsl_with_shape_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = create_real_dsl_revision_draft(
        kind="lab",
        source_path=ROOT / "examples/output/real-llm-lab.json",
        reviewer="teacher_1",
        comment="请用真实 LLM 重新组织步骤说明。",
        output_path=output,
        report_output_path=report_output,
        provider_mode="real-llm",
        model="test-model",
        base_url="https://example.test/v1",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
        root=ROOT,
        trace_id="trace_real_dsl_revision_provider",
        client_factory=lambda **_: fake_client,
    )

    assert output.exists()
    assert report_output.exists()
    assert len(fake_client.responses.calls) == 1
    call = fake_client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text"]["format"]["type"] == "json_schema"
    assert "reviewFeedback" in call["input"]
    assert "sourceDsl" in call["input"]
    revised = load_yaml(output)
    validate_dsl(revised, load_schema("lab", ROOT))
    draft = result["realDslRevisionDraft"]
    assert draft["mode"] == "REAL_LLM_DSL_REVISION_DRAFT"
    assert draft["providerMode"] == "real-llm"
    assert draft["provider"]["apiSurface"] == "responses"
    assert draft["provider"]["responseId"] == "resp_fake_real_demo_provider"
    assert draft["revisedStatus"] == "WAITING_REVIEW"
    assert draft["schemaValidated"] is True
    assert draft["safety"]["realLlmCalled"] is True
    assert draft["safety"]["newLlmRequestSent"] is True
    assert draft["safety"]["secretsRead"] is True
    assert draft["safety"]["networkAccess"] is True
    assert draft["safety"]["autoApproveAllowed"] is False
    assert draft["safety"]["autoPublishAllowed"] is False
    assert draft["safety"]["realPublishAllowed"] is False


def test_create_real_dsl_revision_draft_rejects_missing_source(tmp_path):
    try:
        create_real_dsl_revision_draft(
            kind="lab",
            source_path=tmp_path / "missing-lab.json",
            reviewer="teacher_1",
            comment="补充说明",
            output_path=tmp_path / "out.json",
            report_output_path=tmp_path / "report.json",
            root=ROOT,
        )
    except RealDslRevisionError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "source"
    else:
        raise AssertionError("expected RealDslRevisionError")
