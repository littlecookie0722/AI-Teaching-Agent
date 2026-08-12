import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_gate():
    with (ROOT / "delivery/phase2-readiness-gate.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scripts_manifest():
    with (ROOT / "scripts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_phase2_readiness_gate_is_phase1_mock_only():
    gate = load_gate()

    assert gate["phase"] == "Phase 1"
    assert gate["targetPhase"] == "Phase 2"
    assert gate["mode"] == "MOCK_ONLY"
    assert gate["safety"]["realLlmCalled"] is False
    assert gate["safety"]["realAgentStarted"] is False
    assert gate["safety"]["realCloudResourceCreated"] is False
    assert gate["safety"]["sandboxExecuted"] is False
    assert gate["safety"]["contestantCodeExecuted"] is False
    assert gate["safety"]["unknownShellExecuted"] is False
    assert gate["safety"]["autoPublishAllowed"] is False
    assert gate["safety"]["realPublish"] is False
    assert gate["safety"]["remoteUploadAllowed"] is False
    assert gate["safety"]["secretVisibleInFrontend"] is False


def test_phase2_readiness_gate_inputs_outputs_and_checks_exist():
    gate = load_gate()
    check_ids = [check["id"] for check in gate["gateChecks"]]

    assert len(check_ids) == len(set(check_ids))
    assert {
        "phase1_check_passed",
        "delivery_package_ready",
        "acceptance_summary_passed",
        "safety_assertions_passed",
        "generated_content_review_gated",
        "publish_blocked_until_approved",
        "handoff_contract_present",
        "faq_contract_present",
        "test_phase2_readiness_passes",
    } <= set(check_ids)

    for entry in [*gate["inputs"], *gate["outputs"]]:
        if not entry.get("generated", False):
            assert (ROOT / entry["path"]).exists()
        assert entry.get("localOnly", True) is True

    for check in gate["gateChecks"]:
        assert check["required"] is True
        assert check["title"]
        assert check["source"]["type"] in {"command", "package_field", "local_file"}
        if check["source"]["type"] == "local_file":
            assert (ROOT / check["source"]["path"]).exists()
        if check["source"]["type"] == "package_field":
            assert "expected" in check["source"]


def test_phase2_readiness_gate_commands_are_allowlisted_and_safe():
    gate = load_gate()
    manifest = load_scripts_manifest()
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}
    blocked_patterns = [pattern.lower() for pattern in manifest["blockedPatterns"]]

    assert set(gate["recommendedCommandIds"]).issubset(allowed)
    assert "test_provider_adapter_workflow" in gate["recommendedCommandIds"]
    for command_id in gate["recommendedCommandIds"]:
        command = allowed[command_id]
        command_text = command["command"].lower()
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert not any(pattern in command_text for pattern in blocked_patterns)

    for check in gate["gateChecks"]:
        if check["source"]["type"] == "command":
            command = allowed[check["source"]["commandId"]]
            assert command["requiresNetwork"] is False
            assert command["command"].startswith("python ")


def test_phase2_readiness_gate_allows_only_safe_next_steps():
    gate = load_gate()
    allowed_ids = {item["id"]: item for item in gate["allowedNextSteps"]}
    blocked_ids = {item["id"]: item for item in gate["blockedNextSteps"]}

    assert set(allowed_ids) == {
        "phase2_mock_provider_design",
        "phase2_prompt_workflow_design",
        "phase2_mock_workflow_extension",
    }
    assert all(item["allowed"] is True for item in allowed_ids.values())
    assert all(item["requiresHumanApproval"] is True for item in allowed_ids.values())

    for blocked_id in [
        "enable_real_llm",
        "create_real_cloud_resource",
        "run_real_sandbox_or_contestant_code",
        "auto_publish_generated_content",
        "start_real_agent",
    ]:
        assert blocked_ids[blocked_id]["blocked"] is True
        assert blocked_ids[blocked_id]["reason"]


def test_phase2_readiness_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/PHASE2_READINESS.md").read_text(encoding="utf-8")

    for heading in [
        "## 输入说明",
        "## 输出说明",
        "## 命令示例",
        "## 准入条件",
        "## 允许下一步",
        "## 阻断项",
        "## 测试方式",
        "## 限制说明",
    ]:
        assert heading in content
    assert "python lab_cli.py phase1 check" in content
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in content
    assert "python -m pytest tests/test_phase2_readiness_gate.py" in content
    assert "python -m pytest tests/test_phase2_provider_plan.py" in content
    assert "python -m pytest tests/test_provider_adapter.py" in content
    assert "python -m pytest tests/test_provider_adapter_workflow.py" in content
    assert "WAITING_REVIEW" in content or "reviewRequired=true" in content
    assert "MOCK_ONLY" in content
    assert "不接入真实大模型" in content
    assert "不允许直接启用真实 LLM Provider" in content
