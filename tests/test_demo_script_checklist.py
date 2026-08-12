import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_checklist():
    with (ROOT / "delivery/phase1-demo-script-checklist.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scripts_manifest():
    with (ROOT / "scripts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_demo_script_checklist_is_phase1_mock_only():
    checklist = load_checklist()

    assert checklist["phase"] == "Phase 1"
    assert checklist["mode"] == "MOCK_ONLY"
    assert checklist["safety"]["manualOnly"] is True
    assert checklist["safety"]["realLlmCalled"] is False
    assert checklist["safety"]["realMcpServerStarted"] is False
    assert checklist["safety"]["realAgentStarted"] is False
    assert checklist["safety"]["realCloudResourceCreated"] is False
    assert checklist["safety"]["realCloudResourceChanged"] is False
    assert checklist["safety"]["sandboxExecuted"] is False
    assert checklist["safety"]["contestantCodeExecuted"] is False
    assert checklist["safety"]["unknownShellExecuted"] is False
    assert checklist["safety"]["remoteUploadAllowed"] is False
    assert checklist["safety"]["autoPublishAllowed"] is False
    assert checklist["safety"]["realPublish"] is False
    assert checklist["safety"]["secretVisibleInFrontend"] is False
    assert checklist["safety"]["answerVisibleToCandidate"] is False


def test_demo_script_checklist_inputs_outputs_exist():
    checklist = load_checklist()

    for item in [*checklist["inputs"], *checklist["outputs"]]:
        if not item.get("generated", False):
            assert (ROOT / item["path"]).exists()
        assert not item["path"].startswith(("http://", "https://"))


def test_demo_script_checklist_flow_is_ordered_manual_and_local():
    checklist = load_checklist()
    flow = checklist["demoFlow"]
    orders = [step["order"] for step in flow]
    ids = [step["id"] for step in flow]

    assert orders == sorted(orders)
    assert len(ids) == len(set(ids))
    assert ids[:4] == ["read_rules", "open_launchpad", "open_demo_map", "open_runbook"]
    assert "validate_cli_review_priority_queue" in ids
    assert "validate_backend_mcp_review_priority_queue" in ids
    assert ids[-2:] == ["confirm_review_gate", "confirm_blocked_actions"]
    assert all(step["manualOnly"] is True for step in flow)
    assert all(step["expectedSignal"] for step in flow)
    assert all(step["speakerCue"] for step in flow)

    for step in flow:
        action = step.get("operatorAction")
        if action:
            assert action.startswith(("start .\\frontend\\", "python lab_cli.py "))
        if step.get("evidencePath"):
            assert (ROOT / step["evidencePath"]).exists()
        if step.get("generatedEvidencePath"):
            assert step["generatedEvidencePath"].startswith("examples/output/")


def test_demo_script_checklist_references_allowlisted_validation_commands():
    checklist = load_checklist()
    manifest = load_scripts_manifest()
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(checklist["recommendedCommandIds"]).issubset(allowed)
    command_steps = [step for step in checklist["demoFlow"] if step.get("commandId")]
    assert {step["commandId"] for step in command_steps} == {
        "phase1_check",
        "phase1_export",
        "phase1_report",
        "test_backend_mock_api",
        "test_cli",
    }
    for step in command_steps:
        command = allowed[step["commandId"]]
        if step["operatorAction"].startswith("python -m pytest "):
            assert step["operatorAction"] == command["command"]
        assert command["requiresNetwork"] is False
    secondary_steps = [step for step in checklist["demoFlow"] if step.get("secondaryCommandId")]
    assert {step["secondaryCommandId"] for step in secondary_steps} == {"test_mcp_mock_tools"}
    assert all(step["secondaryCommandId"] in allowed for step in secondary_steps)


def test_demo_script_checklist_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/DEMO_SCRIPT_CHECKLIST.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 演示顺序", "## 测试方式", "## 限制说明"]:
        assert heading in content
    assert "frontend/operations-launchpad.html" in content
    assert "frontend/operations-demo-map.html" in content
    assert "frontend/operations-presenter.html" in content
    assert "frontend/operations-demo-script.html" in content
    assert "start .\\frontend\\operations-presenter.html" in content
    assert "start .\\frontend\\operations-demo-script.html" in content
    assert "python lab_cli.py phase1 check" in content
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in content
    assert "python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py" in content
    assert "python -m pytest tests/test_cli.py" in content
    assert "reviewPriorityQueue" in content
    assert "GET /api/review-task-summary" in content
    assert "MCP `get_review_task_summary`" in content
    assert "python -m pytest tests/test_demo_script_checklist.py" in content
    assert "WAITING_REVIEW" in content
    assert "MOCK_ONLY" in content
    assert "不接入真实大模型" in content
    assert "不上传交付包" in content
    assert "不执行未知 Shell" in content


def test_demo_script_checklist_acceptance_signals_and_blocked_actions_cover_risks():
    checklist = load_checklist()
    signal_ids = {signal["id"] for signal in checklist["acceptanceSignals"]}
    blocked_text = " ".join(checklist["blockedActions"])

    assert {
        "launchpad_first",
        "phase1_check_passed",
        "delivery_manifest_ready",
        "acceptance_report_ready",
        "review_gate_visible",
        "review_priority_queue_visible",
        "real_actions_disabled",
    } <= signal_ids
    for phrase in [
        "unknown Shell",
        "contestant code",
        "real agent",
        "real LLM",
        "real cloud",
        "upload",
        "auto-publish",
        "secrets",
    ]:
        assert phrase in blocked_text
