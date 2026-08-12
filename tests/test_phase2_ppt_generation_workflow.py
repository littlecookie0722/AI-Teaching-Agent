import json
from pathlib import Path

from ai_workflows.ppt_generation_workflow import (
    PHASE2_PPT_WORKFLOW_ID,
    PptWorkflowInputError,
    run_phase2_ppt_generation,
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


def test_phase2_ppt_generation_contract_is_mock_only_and_local():
    contract = load_json("ai-workflows/phase2-ppt-generation.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed_ids = {command["id"] for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["workflowId"] == PHASE2_PPT_WORKFLOW_ID
    assert contract["documentPolicy"]["directPdfToPptAllowed"] is False
    assert contract["documentPolicy"]["slidePlanRequiredBeforePpt"] is True
    assert contract["documentPolicy"]["pptFileGenerated"] is False
    assert contract["documentPolicy"]["artifactGenerated"] is False
    assert contract["providerAdapter"]["activeProvider"] == "mock"
    assert contract["providerAdapter"]["realLlmCalled"] is False
    assert contract["reviewGate"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
    assert set(contract["recommendedCommandIds"]).issubset(allowed_ids)
    for item in contract["inputs"]:
        assert item["localOnly"] is True
        assert (ROOT / item["path"]).exists()
    for output in contract["outputs"]:
        if not output.get("generated", False):
            assert (ROOT / output["path"]).exists()
        if output["kind"] == "PPT":
            assert output["status"] == "WAITING_REVIEW"
            assert output["reviewRequired"] is True
            assert output["artifactGenerated"] is False
            assert output["pptFileGenerated"] is False
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["realPublish"] is False
    assert contract["safety"]["realPptFileCreated"] is False


def test_run_phase2_ppt_generation_builds_slide_plan_before_dsl():
    report = run_phase2_ppt_generation(
        input_path=ROOT / "examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_ppt",
        root=ROOT,
    )

    assert report["workflowId"] == PHASE2_PPT_WORKFLOW_ID
    assert report["phase"] == "Phase 2"
    assert report["mode"] == "MOCK_ONLY"
    assert [step["name"] for step in report["steps"]] == [
        "validate_input",
        "analyze_material",
        "build_chapter_tree",
        "extract_key_points",
        "build_slide_plan",
        "generate_ppt_dsl",
        "assemble_ppt_review_bundle",
    ]
    assert report["slidePlan"]["slides"]
    assert report["slidePlan"]["artifactGenerated"] is False
    assert report["slidePlan"]["pptFileGenerated"] is False
    assert set(report["generatedDsl"]) == {"ppt"}
    assert report["generatedDsl"]["ppt"]["status"] == "WAITING_REVIEW"
    assert report["generatedDsl"]["ppt"]["artifactGenerated"] is False
    assert report["reviewSummary"]["pptFileGenerated"] is False
    assert report["acceptanceSignals"]["slidePlanBuiltBeforePptDsl"] is True
    assert report["acceptanceSignals"]["artifactGenerationDeferred"] is True
    assert report["safety"]["realLlmCalled"] is False
    assert report["safety"]["realPptFileCreated"] is False


def test_run_phase2_ppt_generation_rejects_non_markdown(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("plain text", encoding="utf-8")

    try:
        run_phase2_ppt_generation(
            input_path=source,
            reviewer="teacher_1",
            trace_id="trace_bad_ppt",
            root=ROOT,
        )
    except PptWorkflowInputError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "input"
    else:
        raise AssertionError("expected PptWorkflowInputError")


def test_phase2_ppt_generate_cli_run_records_review_bundle(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "ppt-report.json"
    slide_plan_path = tmp_path / "slide-plan.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "ppt-generate",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--slide-plan-output",
            str(slide_plan_path),
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    assert slide_plan_path.exists()
    assert payload["data"]["workflowId"] == PHASE2_PPT_WORKFLOW_ID
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["slidePlanPath"] == str(slide_plan_path)
    assert payload["data"]["slidePlan"]["pptFileGenerated"] is False
    assert payload["data"]["reviewSummary"]["artifactGenerated"] is False
    assert payload["data"]["reviewSummary"]["pptFileGenerated"] is False
    assert payload["data"]["generatedDsl"]["ppt"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["generatedDsl"]["ppt"]["artifactGenerated"] is False
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == ["PPT_GENERATION"]
    assert {task["status"] for task in payload["data"]["createdTasks"]} == {"WAITING_REVIEW"}
    assert set(payload["data"]["providerCallAuditEvents"]) == {"ppt"}
    assert payload["data"]["providerCallAuditEvents"]["ppt"]["detail"]["workflowId"] == PHASE2_PPT_WORKFLOW_ID
    assert payload["data"]["workflowRun"]["workflowId"] == PHASE2_PPT_WORKFLOW_ID
    assert payload["data"]["workflowRun"]["realLlmCalled"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "MATERIAL_ANALYSIS",
        "PPT_DSL",
        "WORKFLOW_REPORT",
    }
    assert any(
        artifact["metadata"].get("artifactType") == "slide_plan"
        for artifact in payload["data"]["artifacts"]
    )

    saved_slide_plan = json.loads(slide_plan_path.read_text(encoding="utf-8"))
    assert saved_slide_plan["id"] == payload["data"]["slidePlan"]["id"]
    _, listed = run_cli(["workflow", "list", "--workflow-id", PHASE2_PPT_WORKFLOW_ID], capsys)
    _, audit = run_cli(["provider", "audit", "--trace-id", payload["traceId"]], capsys)
    assert listed["data"]["total"] == 1
    assert audit["data"]["total"] == 1


def test_phase2_ppt_generate_cli_report_reads_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "ppt-report.json"
    slide_plan_path = tmp_path / "slide-plan.json"
    run_cli(
        [
            "phase2",
            "ppt-generate",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--slide-plan-output",
            str(slide_plan_path),
            "--output",
            str(report_path),
        ],
        capsys,
    )

    exit_code, payload = run_cli(["phase2", "ppt-generate", "report", "--file", str(report_path)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["summary"]["workflowId"] == PHASE2_PPT_WORKFLOW_ID
    assert payload["data"]["summary"]["artifactGenerated"] is False
    assert payload["data"]["summary"]["pptFileGenerated"] is False
    assert payload["data"]["summary"]["generatedDsl"]["ppt"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["summary"]["safety"]["realPptFileCreated"] is False


def test_phase2_ppt_generate_cli_missing_input_returns_json(tmp_path, capsys):
    report_path = tmp_path / "ppt-report.json"
    slide_plan_path = tmp_path / "slide-plan.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "ppt-generate",
            "run",
            "--input",
            "missing.md",
            "--slide-plan-output",
            str(slide_plan_path),
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"
    assert not report_path.exists()
    assert not slide_plan_path.exists()


def test_phase2_ppt_generate_report_rejects_wrong_workflow(tmp_path, capsys):
    report_path = tmp_path / "bad-report.json"
    report_path.write_text(json.dumps({"phase": "Phase 2", "mode": "MOCK_ONLY", "workflowId": "phase2_content_generation"}), encoding="utf-8")

    exit_code, payload = run_cli(["phase2", "ppt-generate", "report", "--file", str(report_path)], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "workflowId"
