import json
from pathlib import Path

from ai_workflows.workflow_registry import (
    get_phase2_workflow,
    list_phase2_workflows,
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


def test_phase2_workflow_registry_contract_is_mock_only_and_local():
    registry = load_json("ai-workflows/phase2-workflow-registry.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed_ids = {command["id"] for command in manifest["allowedCommands"]}

    assert registry["phase"] == "Phase 2"
    assert registry["mode"] == "MOCK_ONLY"
    assert registry["registryId"] == "phase2_workflow_registry"
    assert set(registry["recommendedCommandIds"]).issubset(allowed_ids)
    assert [workflow["workflowId"] for workflow in registry["workflows"]] == [
        "phase2_content_generation",
        "phase2_exam_conversion",
        "phase2_ppt_generation",
        "phase2_grading_generation",
    ]
    for workflow in registry["workflows"]:
        assert workflow["phase"] == "Phase 2"
        assert workflow["mode"] == "MOCK_ONLY"
        assert workflow["status"] == "READY"
        assert workflow["reviewGate"]["reviewRequired"] is True
        assert workflow["reviewGate"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
        assert workflow["reviewGate"]["publishBlockedUntilApproved"] is True
        assert (ROOT / workflow["contractPath"]).exists()
        assert workflow["entrypoints"]["backend"]["method"] == "POST"
        assert workflow["entrypoints"]["backend"]["path"].startswith("/api/phase2/workflows/")
        assert workflow["safety"]["realLlmCalled"] is False
        assert workflow["safety"]["realAgentStarted"] is False
        assert workflow["safety"]["realCloudResourceCreated"] is False
        assert workflow["safety"]["realPublish"] is False
    assert registry["safety"]["realLlmCalled"] is False
    assert registry["safety"]["autoPublishAllowed"] is False
    assert registry["safety"]["workflowExecuted"] is False
    assert registry["safety"]["taskCreated"] is False
    assert registry["safety"]["artifactCreated"] is False


def test_phase2_workflow_registry_helper_lists_and_gets_contracts():
    listed = list_phase2_workflows(root=ROOT)
    detail = get_phase2_workflow("phase2_ppt_generation", root=ROOT)

    assert listed["registryId"] == "phase2_workflow_registry"
    assert listed["total"] == 4
    assert {item["workflowId"] for item in listed["items"]} == {
        "phase2_content_generation",
        "phase2_exam_conversion",
        "phase2_ppt_generation",
        "phase2_grading_generation",
    }
    assert all(item["reviewRequired"] is True for item in listed["items"])
    assert detail["workflow"]["workflowId"] == "phase2_ppt_generation"
    assert detail["contract"]["workflowId"] == "phase2_ppt_generation"
    assert detail["contract"]["documentPolicy"]["pptFileGenerated"] is False
    assert listed["safety"]["workflowExecuted"] is False
    assert listed["safety"]["taskCreated"] is False
    assert listed["safety"]["artifactCreated"] is False
    assert detail["safety"]["workflowExecuted"] is False


def test_phase2_workflow_registry_helper_filters_by_category():
    listed = list_phase2_workflows(root=ROOT, category="exam_conversion")

    assert listed["total"] == 1
    assert listed["filters"]["category"] == "exam_conversion"
    assert listed["items"][0]["workflowId"] == "phase2_exam_conversion"


def test_workflow_registry_cli_list_and_get_return_json(capsys):
    exit_code, listed = run_cli(["workflow", "registry", "list"], capsys)
    detail_code, detail = run_cli(["workflow", "registry", "get", "--workflow-id", "phase2_content_generation"], capsys)

    assert exit_code == 0
    assert detail_code == 0
    assert_json_envelope(listed)
    assert_json_envelope(detail)
    assert listed["data"]["total"] == 4
    assert listed["data"]["items"][0]["workflowId"] == "phase2_content_generation"
    assert detail["data"]["workflow"]["workflowId"] == "phase2_content_generation"
    assert detail["data"]["contract"]["workflowId"] == "phase2_content_generation"
    assert detail["data"]["contract"]["reviewGate"]["defaultGeneratedStatus"] == "WAITING_REVIEW"


def test_workflow_registry_cli_filter_and_not_found_return_json(capsys):
    exit_code, listed = run_cli(["workflow", "registry", "list", "--category", "ppt_generation"], capsys)
    missing_code, missing = run_cli(["workflow", "registry", "get", "--workflow-id", "missing_workflow"], capsys)

    assert exit_code == 0
    assert_json_envelope(listed)
    assert listed["data"]["total"] == 1
    assert listed["data"]["items"][0]["workflowId"] == "phase2_ppt_generation"
    assert missing_code == 1
    assert_json_envelope(missing)
    assert missing["code"] == "NOT_FOUND"
    assert missing["errors"][0]["field"] == "workflowId"
