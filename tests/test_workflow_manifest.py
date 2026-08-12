import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manifest():
    with (ROOT / "ai-workflows/workflow.manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_workflow_manifest_is_phase1_mock_only():
    manifest = load_manifest()

    assert manifest["phase"] == "Phase 1"
    assert manifest["mode"] == "MOCK_ONLY"
    assert manifest["providerAdapter"]["adapterId"] == "mock_provider_adapter"
    assert manifest["providerAdapter"]["interfaceName"] == "LLMProvider"
    assert manifest["providerAdapter"]["activeProvider"] == "mock"
    assert manifest["providerAdapter"]["operation"] == "generateJson"
    assert manifest["providerAdapter"]["streamGenerateEnabled"] is False
    assert (ROOT / manifest["providerAdapter"]["helper"]).exists()
    assert (ROOT / manifest["providerAdapter"]["contract"]).exists()
    assert (ROOT / "ai-workflows/provider-audit-workflow.contract.json").exists()
    assert manifest["globalSafety"]["realLlmCalled"] is False
    assert manifest["globalSafety"]["realCloudResourceCreated"] is False
    assert manifest["globalSafety"]["contestantCodeExecuted"] is False
    assert manifest["globalSafety"]["autoPublishAllowed"] is False


def test_workflow_manifest_ids_are_unique():
    manifest = load_manifest()
    ids = [workflow["id"] for workflow in manifest["workflows"]]

    assert len(ids) == len(set(ids))


def test_workflow_manifest_entrypoints_map_to_cli_and_backend_mock():
    manifest = load_manifest()

    for workflow in manifest["workflows"]:
        entrypoint = workflow["entrypoint"]
        assert entrypoint["cli"].startswith("python lab_cli.py ")
        assert entrypoint["backend"]["method"] == "POST"
        assert entrypoint["backend"]["path"].startswith("/api/")


def test_workflow_manifest_outputs_reference_existing_dsl_examples():
    manifest = load_manifest()
    dsl_kinds = {"Lab", "Exam", "Grading", "PPT"}

    for workflow in manifest["workflows"]:
        for output in workflow["outputs"]:
            if output["kind"] in dsl_kinds:
                path = ROOT / output["path"]
                assert path.exists(), output["path"]
                assert output["status"] == "WAITING_REVIEW"


def test_workflow_manifest_generated_outputs_require_review_gate():
    manifest = load_manifest()

    for workflow in manifest["workflows"]:
        generated_outputs = [
            output for output in workflow["outputs"] if output["kind"] in {"Lab", "Exam", "Grading", "PPT"}
        ]
        if generated_outputs:
            assert workflow["reviewGate"]["required"] is True
            assert workflow["reviewGate"]["publishBlockedUntilApproved"] is True
            assert workflow["reviewGate"]["rejectRequiresReason"] is True
            assert workflow["safety"]["autoPublishAllowed"] is False


def test_main_workflow_contains_expected_ordered_steps():
    manifest = load_manifest()
    workflows = {workflow["id"]: workflow for workflow in manifest["workflows"]}
    main = workflows["phase1_main_demo"]

    assert [step["name"] for step in main["steps"]] == [
        "validate_input",
        "analyze_material",
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
        "mock_grade_run",
    ]
    analyze_step = main["steps"][1]
    assert analyze_step["type"] == "static_analysis"
    assert analyze_step["realLlmCalled"] is False
    assert analyze_step["unknownShellExecuted"] is False
    assert main["safety"]["sandboxExecuted"] is False
    assert main["safety"]["answerVisibleToCandidate"] is False
    provider_steps = [step for step in main["steps"] if step["name"].startswith("generate_") and step["name"].endswith("_dsl")]
    assert provider_steps
    assert all(step["type"] == "provider_adapter_generation" for step in provider_steps)
    assert all(step["providerAdapter"] == "mock_provider_adapter" for step in provider_steps)
    assert {step["promptId"] for step in provider_steps} == {
        "lab_generation_v0",
        "exam_generation_v0",
        "grading_generation_v0",
        "ppt_generation_v0",
    }


def test_main_workflow_declares_queryable_run_log():
    manifest = load_manifest()
    workflows = {workflow["id"]: workflow for workflow in manifest["workflows"]}
    run_log = workflows["phase1_main_demo"]["runLog"]

    assert run_log["enabled"] is True
    assert run_log["mode"] == "MOCK_ONLY"
    assert run_log["recordsTraceId"] is True
    assert run_log["recordsStepOrder"] is True
    assert run_log["cliList"].startswith("python lab_cli.py workflow list")
    assert run_log["backendList"]["path"] == "/api/workflow-runs"
    assert run_log["backendGet"]["path"] == "/api/workflow-runs/{id}"
