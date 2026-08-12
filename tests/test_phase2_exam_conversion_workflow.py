import json
from pathlib import Path

from ai_workflows.exam_conversion_workflow import (
    PHASE2_EXAM_WORKFLOW_ID,
    ExamConversionInputError,
    run_phase2_exam_conversion,
)
from cli.lab_cli import main


ROOT = Path(__file__).resolve().parents[1]


def run_cli(args, capsys):
    exit_code = main(args)
    output = capsys.readouterr().out
    payload = json.loads(output)
    return exit_code, payload


def assert_json_envelope(payload):
    assert set(payload) >= {"success", "code", "message", "traceId"}
    assert payload["traceId"].startswith("trace_")
    if payload["success"]:
        assert "data" in payload
    else:
        assert "errors" in payload


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_phase2_exam_conversion_contract_is_mock_only_and_local():
    contract = load_json("ai-workflows/phase2-exam-conversion.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed_ids = {command["id"] for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["workflowId"] == PHASE2_EXAM_WORKFLOW_ID
    assert set(contract["recommendedCommandIds"]).issubset(allowed_ids)
    for item in contract["inputs"]:
        assert item["localOnly"] is True
        assert (ROOT / item["path"]).exists()
    for output in contract["outputs"]:
        if not output.get("generated", False):
            assert (ROOT / output["path"]).exists()
        if output["kind"] in {"Exam", "Grading"}:
            assert output["status"] == "WAITING_REVIEW"
            assert output["reviewRequired"] is True
    assert contract["candidateDataPolicy"]["candidatePreviewRemovesAnswer"] is True
    assert contract["candidateDataPolicy"]["answerVisibleToCandidate"] is False
    assert contract["qualitySignals"]["reviewRequired"] is True
    assert "coverage.questionGradingRefCoverage" in contract["qualitySignals"]["fields"]
    assert "coverage.explainability" in contract["qualitySignals"]["fields"]
    assert "grading.assessmentPlan" in contract["qualitySignals"]["fields"]
    assert "coverage.explainability.assessmentPlanAlignedWithChecks" in contract["qualitySignals"]["fields"]
    assert "coverage.explainability.assessmentPlanHasReportDetailFields" in contract["qualitySignals"]["fields"]
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["realPublish"] is False


def test_run_phase2_exam_conversion_parses_notebook_without_execution():
    report = run_phase2_exam_conversion(
        lab_path=ROOT / "templates/lab/examples/basic-lab.yaml",
        notebook_path=ROOT / "examples/notebooks/demo-lab.ipynb",
        reviewer="teacher_1",
        trace_id="trace_exam",
        root=ROOT,
    )

    assert report["workflowId"] == PHASE2_EXAM_WORKFLOW_ID
    assert report["phase"] == "Phase 2"
    assert report["mode"] == "MOCK_ONLY"
    assert report["labDslInput"]["labId"] == "lab_demo"
    assert report["notebookInput"]["cellCount"] == 2
    assert report["notebookInput"]["executionDisabled"] is True
    assert report["notebookInput"]["contestantCodeExecuted"] is False
    assert set(report["generatedDsl"]) == {"exam", "grading"}
    assert {item["status"] for item in report["generatedDsl"].values()} == {"WAITING_REVIEW"}
    assert report["generatedDsl"]["exam"]["answerVisibleToCandidate"] is False
    assert report["candidateSafeExamPreview"]["answersRemoved"] is True
    assert "answer" not in report["candidateSafeExamPreview"]["questions"][0]
    assert report["qualitySignals"]["overall"]["answerHiddenFromCandidatePreview"] is True
    assert report["qualitySignals"]["exam"]["answersStoredInDsl"] is True
    assert report["qualitySignals"]["exam"]["answerHiddenFromCandidatePreview"] is True
    assert report["qualitySignals"]["coverage"]["questionGradingRefCoverage"]["matched"] is True
    assert report["qualitySignals"]["coverage"]["scoreCoverage"]["matched"] is True
    assert report["qualitySignals"]["coverage"]["explainability"]["matched"] is True
    assert report["qualitySignals"]["coverage"]["explainability"]["assessmentPlanAlignedWithChecks"] is True
    assert report["qualitySignals"]["coverage"]["explainability"]["assessmentPlanHasReportDetailFields"] is True
    assert report["qualitySignals"]["coverage"]["explainability"]["executionStrategy"] == "MOCK_PLAN_ONLY"
    assert report["qualitySignals"]["coverage"]["explainability"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert report["qualitySignals"]["grading"]["sandboxRequiredBeforeRealExecution"] is True
    assessment_plan = report["qualitySignals"]["grading"]["assessmentPlan"]
    assert [plan["checkId"] for plan in assessment_plan] == report["qualitySignals"]["grading"]["checkIds"]
    assert all(plan["inputSummary"] for plan in assessment_plan)
    assert all(plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in assessment_plan)
    assert all(plan["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default" for plan in assessment_plan)
    assert all(plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for plan in assessment_plan)
    assert all(plan["sandboxRequiredBeforeRealExecution"] is True for plan in assessment_plan)
    assert report["acceptanceSignals"]["answerHiddenFromCandidatePreview"] is True
    assert report["acceptanceSignals"]["gradingRefsCovered"] is True
    assert report["acceptanceSignals"]["gradingPlanExplainable"] is True
    assert report["safety"]["realLlmCalled"] is False
    assert report["safety"]["sandboxExecuted"] is False
    assert report["safety"]["contestantCodeExecuted"] is False


def test_run_phase2_exam_conversion_rejects_invalid_notebook(tmp_path):
    bad_notebook = tmp_path / "bad.ipynb"
    bad_notebook.write_text("not json", encoding="utf-8")

    try:
        run_phase2_exam_conversion(
            lab_path=ROOT / "templates/lab/examples/basic-lab.yaml",
            notebook_path=bad_notebook,
            reviewer="teacher_1",
            trace_id="trace_bad",
            root=ROOT,
        )
    except ExamConversionInputError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "notebook"
    else:
        raise AssertionError("expected ExamConversionInputError")


def test_phase2_exam_convert_cli_run_records_review_bundle(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "exam-report.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "exam-convert",
            "run",
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--notebook",
            "examples/notebooks/demo-lab.ipynb",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    assert payload["data"]["workflowId"] == PHASE2_EXAM_WORKFLOW_ID
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["candidateSafeExamPreview"]["answersRemoved"] is True
    assert "answer" not in payload["data"]["candidateSafeExamPreview"]["questions"][0]
    assert payload["data"]["qualitySignals"]["coverage"]["questionGradingRefCoverage"]["matched"] is True
    assert payload["data"]["qualitySignals"]["coverage"]["scoreCoverage"]["matched"] is True
    assert payload["data"]["summary"]["qualitySignals"]["coverage"]["explainability"]["matched"] is True
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == [
        "EXAM_GENERATION",
        "GRADING_GENERATION",
    ]
    assert {task["status"] for task in payload["data"]["createdTasks"]} == {"WAITING_REVIEW"}
    assert set(payload["data"]["providerCallAuditEvents"]) == {"exam", "grading"}
    assert {event["detail"]["workflowId"] for event in payload["data"]["providerCallAuditEvents"].values()} == {
        PHASE2_EXAM_WORKFLOW_ID
    }
    assert payload["data"]["workflowRun"]["workflowId"] == PHASE2_EXAM_WORKFLOW_ID
    assert payload["data"]["workflowRun"]["realLlmCalled"] is False
    assert payload["data"]["workflowRun"]["sandboxExecuted"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "LAB_DSL",
        "MATERIAL_ANALYSIS",
        "EXAM_DSL",
        "GRADING_DSL",
        "WORKFLOW_REPORT",
    }
    exam_artifact = next(artifact for artifact in payload["data"]["artifacts"] if artifact["kind"] == "EXAM_DSL")
    grading_artifact = next(artifact for artifact in payload["data"]["artifacts"] if artifact["kind"] == "GRADING_DSL")
    assert exam_artifact["metadata"]["workflowQualitySignals"]["exam"]["answerHiddenFromCandidatePreview"] is True
    assert grading_artifact["metadata"]["workflowQualitySignals"]["coverage"]["explainability"]["matched"] is True
    assert grading_artifact["metadata"]["workflowQualitySignals"]["coverage"]["explainability"]["assessmentPlanHasReportDetailFields"] is True

    _, listed = run_cli(["workflow", "list", "--workflow-id", PHASE2_EXAM_WORKFLOW_ID], capsys)
    _, audit = run_cli(["provider", "audit", "--trace-id", payload["traceId"]], capsys)
    assert listed["data"]["total"] == 1
    assert audit["data"]["total"] == 2


def test_phase2_exam_convert_cli_grading_review_detail_includes_assessment_plan(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "exam-report.json"

    _, payload = run_cli(
        [
            "phase2",
            "exam-convert",
            "run",
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--notebook",
            "examples/notebooks/demo-lab.ipynb",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )
    grading_task = next(
        task for task in payload["data"]["createdTasks"] if task["taskType"] == "GRADING_GENERATION"
    )

    exit_code, detail_payload = run_cli(["review", "detail", "--task-id", grading_task["id"]], capsys)

    assert exit_code == 0
    assert_json_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["assessmentPlan"]["visible"] is True
    assert detail["assessmentPlan"]["summary"]["planTotal"] == 1
    assert detail["assessmentPlan"]["summary"]["checkIds"] == ["check_pytest"]
    assert detail["assessmentPlan"]["summary"]["runnerTypes"] == ["PytestGrader"]
    assert detail["assessmentPlan"]["summary"]["alignedWithChecks"] is True
    assert detail["assessmentPlan"]["items"][0]["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert detail["reviewPage"]["assessmentPlan"] == detail["assessmentPlan"]
    assert detail["reviewPage"]["dslPreview"]["assessmentPlanTotal"] == 1


def test_phase2_exam_conversion_assessment_plan_matches_grade_runner_report_detail_contract():
    report = run_phase2_exam_conversion(
        lab_path=ROOT / "templates/lab/examples/basic-lab.yaml",
        notebook_path=ROOT / "examples/notebooks/demo-lab.ipynb",
        reviewer="teacher_1",
        trace_id="trace_contract",
        root=ROOT,
    )
    grade_runner_contract = load_json("sandbox/grade-runner.contract.json")
    report_detail_contract = grade_runner_contract["reportDetailContract"]
    check_plan_fields = set(report_detail_contract["checkPlanFields"])
    assessment_plan = report["qualitySignals"]["grading"]["assessmentPlan"]

    assert report_detail_contract["safetyAssertions"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert {"inputSummary", "executionPlan", "executionPlan.strategy", "executionPlan.requiredLimits", "mockEvidence", "mockEvidence.status", "riskLevel"}.issubset(
        check_plan_fields
    )
    assert assessment_plan
    for plan in assessment_plan:
        assert plan["checkId"]
        assert plan["type"]
        assert plan["runner"]
        assert plan["score"] > 0
        assert plan["inputSummary"]
        assert plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY"
        assert plan["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default"
        assert plan["mockEvidence"]["status"] == report_detail_contract["safetyAssertions"]["mockEvidenceStatus"]
        assert plan["riskLevel"] in {"low", "medium", "high"}
        assert plan["sandboxRequiredBeforeRealExecution"] is True


def test_phase2_exam_convert_cli_report_reads_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "exam-report.json"
    run_cli(
        [
            "phase2",
            "exam-convert",
            "run",
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--notebook",
            "examples/notebooks/demo-lab.ipynb",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    exit_code, payload = run_cli(["phase2", "exam-convert", "report", "--file", str(report_path)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["summary"]["workflowId"] == PHASE2_EXAM_WORKFLOW_ID
    assert payload["data"]["summary"]["answerVisibleToCandidate"] is False
    assert payload["data"]["summary"]["qualitySignals"]["overall"]["answerHiddenFromCandidatePreview"] is True
    assert payload["data"]["summary"]["qualitySignals"]["coverage"]["scoreCoverage"]["matched"] is True
    assert payload["data"]["summary"]["generatedDsl"]["exam"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["summary"]["safety"]["contestantCodeExecuted"] is False


def test_phase2_exam_convert_cli_missing_lab_returns_json(tmp_path, capsys):
    report_path = tmp_path / "exam-report.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "exam-convert",
            "run",
            "--lab",
            "missing.yaml",
            "--notebook",
            "examples/notebooks/demo-lab.ipynb",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "lab"
    assert not report_path.exists()


def test_phase2_exam_convert_report_rejects_wrong_workflow(tmp_path, capsys):
    report_path = tmp_path / "bad-report.json"
    report_path.write_text(json.dumps({"phase": "Phase 2", "mode": "MOCK_ONLY", "workflowId": "phase2_content_generation"}), encoding="utf-8")

    exit_code, payload = run_cli(["phase2", "exam-convert", "report", "--file", str(report_path)], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "workflowId"
