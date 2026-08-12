import json
from pathlib import Path

from ai_workflows.grading_generation_workflow import (
    PHASE2_GRADING_WORKFLOW_ID,
    GradingGenerationInputError,
    run_phase2_grading_generation,
)
from backend.mock_api import handle_request
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


def test_phase2_grading_generation_contract_is_mock_only_and_local():
    contract = load_json("ai-workflows/phase2-grading-generation.contract.json")
    registry = load_json("ai-workflows/phase2-workflow-registry.contract.json")

    assert contract["workflowId"] == PHASE2_GRADING_WORKFLOW_ID
    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["inputs"][0]["kind"] == "Exam"
    assert (ROOT / contract["inputs"][0]["path"]).exists()
    assert contract["outputs"][0]["kind"] == "Grading"
    assert contract["outputs"][0]["status"] == "WAITING_REVIEW"
    assert "grading.assessmentPlan" in contract["qualitySignals"]["fields"]
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["realPublish"] is False
    assert PHASE2_GRADING_WORKFLOW_ID in {workflow["workflowId"] for workflow in registry["workflows"]}


def test_run_phase2_grading_generation_builds_review_bundle():
    report = run_phase2_grading_generation(
        exam_path=ROOT / "templates/exam/examples/notebook-fill-blank.yaml",
        reviewer="teacher_1",
        trace_id="trace_grading",
        root=ROOT,
    )

    assert report["workflowId"] == PHASE2_GRADING_WORKFLOW_ID
    assert report["phase"] == "Phase 2"
    assert report["mode"] == "MOCK_ONLY"
    assert report["examDslInput"]["examId"] == "exam_demo"
    assert set(report["generatedDsl"]) == {"grading"}
    assert report["generatedDsl"]["grading"]["status"] == "WAITING_REVIEW"
    assert report["qualitySignals"]["overall"]["reviewRequired"] is True
    assert report["qualitySignals"]["coverage"]["gradingRefCoverage"]["matched"] is True
    assert report["qualitySignals"]["coverage"]["scoreCoverage"]["matched"] is True
    assert report["qualitySignals"]["coverage"]["explainability"]["matched"] is True
    assert report["qualitySignals"]["coverage"]["explainability"]["assessmentPlanAlignedWithChecks"] is True
    assert report["qualitySignals"]["coverage"]["explainability"]["assessmentPlanHasReportDetailFields"] is True
    assessment_plan = report["qualitySignals"]["grading"]["assessmentPlan"]
    assert [plan["checkId"] for plan in assessment_plan] == report["qualitySignals"]["grading"]["checkIds"]
    assert all(plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in assessment_plan)
    assert all(plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for plan in assessment_plan)
    assert all(plan["sandboxRequiredBeforeRealExecution"] is True for plan in assessment_plan)
    assert report["safety"]["realLlmCalled"] is False
    assert report["safety"]["sandboxExecuted"] is False
    assert report["safety"]["contestantCodeExecuted"] is False


def test_run_phase2_grading_generation_rejects_invalid_exam(tmp_path):
    bad_exam = tmp_path / "bad.yaml"
    bad_exam.write_text("kind: Exam\n", encoding="utf-8")

    try:
        run_phase2_grading_generation(
            exam_path=bad_exam,
            reviewer="teacher_1",
            trace_id="trace_bad",
            root=ROOT,
        )
    except GradingGenerationInputError as exc:
        assert exc.code == "SCHEMA_VALIDATION_ERROR"
    else:
        raise AssertionError("expected GradingGenerationInputError")


def test_phase2_grading_generate_cli_run_records_review_bundle(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "grading-report.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "grading-generate",
            "run",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
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
    assert payload["data"]["workflowId"] == PHASE2_GRADING_WORKFLOW_ID
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["summary"]["qualitySignals"]["coverage"]["explainability"]["matched"] is True
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == ["GRADING_GENERATION"]
    assert payload["data"]["createdTasks"][0]["status"] == "WAITING_REVIEW"
    assert set(payload["data"]["providerCallAuditEvents"]) == {"grading"}
    assert payload["data"]["workflowRun"]["workflowId"] == PHASE2_GRADING_WORKFLOW_ID
    assert payload["data"]["workflowRun"]["sandboxExecuted"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "EXAM_DSL",
        "GRADING_DSL",
        "WORKFLOW_REPORT",
    }
    grading_artifact = next(artifact for artifact in payload["data"]["artifacts"] if artifact["kind"] == "GRADING_DSL")
    assert grading_artifact["metadata"]["workflowQualitySignals"]["coverage"]["explainability"]["matched"] is True
    assert grading_artifact["metadata"]["workflowQualitySignals"]["coverage"]["explainability"]["assessmentPlanHasReportDetailFields"] is True

    _, listed = run_cli(["workflow", "list", "--workflow-id", PHASE2_GRADING_WORKFLOW_ID], capsys)
    _, audit = run_cli(["provider", "audit", "--trace-id", payload["traceId"]], capsys)
    assert listed["data"]["total"] == 1
    assert audit["data"]["total"] == 1


def test_phase2_grading_generate_cli_review_detail_includes_assessment_plan(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, payload = run_cli(
        [
            "phase2",
            "grading-generate",
            "run",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--output",
            str(tmp_path / "grading-report.json"),
        ],
        capsys,
    )
    grading_task = payload["data"]["createdTasks"][0]

    exit_code, detail_payload = run_cli(["review", "detail", "--task-id", grading_task["id"]], capsys)

    assert exit_code == 0
    assert_json_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["assessmentPlan"]["visible"] is True
    assert detail["assessmentPlan"]["summary"]["planTotal"] == 1
    assert detail["assessmentPlan"]["summary"]["checkIds"] == ["check_pytest"]
    assert detail["assessmentPlan"]["summary"]["alignedWithChecks"] is True
    assert detail["assessmentPlan"]["items"][0]["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"


def test_phase2_grading_generate_cli_report_reads_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "grading-report.json"
    run_cli(
        [
            "phase2",
            "grading-generate",
            "run",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    exit_code, payload = run_cli(["phase2", "grading-generate", "report", "--file", str(report_path)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["summary"]["workflowId"] == PHASE2_GRADING_WORKFLOW_ID
    assert payload["data"]["summary"]["generatedDsl"]["grading"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["summary"]["qualitySignals"]["coverage"]["scoreCoverage"]["matched"] is True
    assert payload["data"]["summary"]["safety"]["sandboxExecuted"] is False


def test_phase2_grading_generate_cli_missing_exam_returns_json(tmp_path, capsys):
    report_path = tmp_path / "grading-report.json"

    exit_code, payload = run_cli(
        ["phase2", "grading-generate", "run", "--exam", "missing.yaml", "--output", str(report_path)],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "exam"
    assert not report_path.exists()


def test_phase2_grading_generation_backend_creates_review_bundle(tmp_path):
    store_path = tmp_path / "store.json"

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/grading-generation/run",
        store_path=store_path,
        body={"exam": "templates/exam/examples/notebook-fill-blank.yaml", "reviewer": "teacher_1"},
    )

    assert_json_envelope(payload)
    assert payload["data"]["report"]["workflowId"] == PHASE2_GRADING_WORKFLOW_ID
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"
    assert [step["name"] for step in payload["data"]["report"]["steps"]] == [
        "validate_exam_dsl",
        "generate_grading_dsl",
        "assemble_grading_review_bundle",
    ]
    assert payload["data"]["generatedDsl"]["grading"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["reviewSummary"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["safety"]["realLlmCalled"] is False
    assert payload["data"]["safety"]["sandboxExecuted"] is False
    assert payload["data"]["createdTasks"][0]["taskType"] == "GRADING_GENERATION"
    assert payload["data"]["workflowRun"]["workflowId"] == PHASE2_GRADING_WORKFLOW_ID
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "EXAM_DSL",
        "GRADING_DSL",
        "WORKFLOW_REPORT",
    }

    audit = handle_request("GET", f"/api/provider-audit-events?traceId={payload['traceId']}", store_path=store_path)
    runs = handle_request("GET", f"/api/workflow-runs?workflowId={PHASE2_GRADING_WORKFLOW_ID}", store_path=store_path)
    assert audit["data"]["total"] == 1
    assert runs["data"]["total"] == 1
