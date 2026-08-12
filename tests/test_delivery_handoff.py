import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_handoff():
    with (ROOT / "delivery/phase1-handoff.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scripts_manifest():
    with (ROOT / "scripts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_delivery_handoff_is_phase1_mock_only():
    handoff = load_handoff()

    assert handoff["phase"] == "Phase 1"
    assert handoff["mode"] == "MOCK_ONLY"
    assert handoff["safety"]["realLlmCalled"] is False
    assert handoff["safety"]["realAgentStarted"] is False
    assert handoff["safety"]["realCloudResourceCreated"] is False
    assert handoff["safety"]["sandboxExecuted"] is False
    assert handoff["safety"]["contestantCodeExecuted"] is False
    assert handoff["safety"]["unknownShellExecuted"] is False
    assert handoff["safety"]["autoPublishAllowed"] is False
    assert handoff["safety"]["realPublish"] is False
    assert handoff["safety"]["remoteUploadAllowed"] is False
    assert handoff["safety"]["secretVisibleInFrontend"] is False


def test_delivery_handoff_inputs_outputs_and_items_exist():
    handoff = load_handoff()
    item_ids = [item["id"] for item in handoff["handoffItems"]]

    assert len(item_ids) == len(set(item_ids))
    assert {
        "read_project_readme",
        "read_delivery_readme",
        "read_delivery_faq",
        "read_demo_runbook",
        "read_demo_script_checklist",
        "read_high_risk_mcp_handoff",
        "read_final_signoff",
        "read_operations_manual",
        "read_operations_skill_pack",
        "read_standalone_agent_delivery",
        "read_access_entrypoints",
        "read_phase5_mock_baseline",
        "open_operations_launchpad",
        "open_access_preview",
        "open_operations_presenter",
        "open_operations_demo_script",
        "open_console_preview",
        "open_delivery_preview",
        "run_phase1_check",
        "export_delivery_package",
        "render_acceptance_report",
        "run_handoff_tests",
        "run_high_risk_mcp_handoff_tests",
        "run_final_signoff_tests",
        "run_operations_manual_tests",
        "run_operations_skill_pack_tests",
        "run_standalone_agent_delivery_tests",
        "run_access_entrypoints_tests",
        "run_phase5_mock_baseline_tests",
        "run_real_sdk_enablement_tests",
        "run_real_sdk_minimal_impl_tests",
        "run_real_sdk_dependency_env_gate_tests",
        "confirm_review_gate",
        "confirm_no_real_execution",
    } <= set(item_ids)

    for entry in [*handoff["inputs"], *handoff["outputs"]]:
        if not entry.get("generated", False):
            assert (ROOT / entry["path"]).exists()
        assert entry.get("localOnly", True) is True

    for item in handoff["handoffItems"]:
        assert item["required"] is True
        assert item["title"]
        assert item["expectedSignal"]
        if "path" in item and item["evidenceType"] != "package_field":
            assert (ROOT / item["path"]).exists()
            assert not item["path"].startswith(("http://", "https://"))
        if "generatedPath" in item:
            assert item["generatedPath"].startswith("examples/output/")


def test_delivery_handoff_commands_are_allowlisted_and_safe():
    handoff = load_handoff()
    manifest = load_scripts_manifest()
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}
    blocked_patterns = [pattern.lower() for pattern in manifest["blockedPatterns"]]

    assert set(handoff["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_enablement" in handoff["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in handoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in handoff["recommendedCommandIds"]
    for command_id in handoff["recommendedCommandIds"]:
        command = allowed[command_id]
        command_text = command["command"].lower()
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert not any(pattern in command_text for pattern in blocked_patterns)

    for item in handoff["handoffItems"]:
        if item["evidenceType"] == "allowlisted_command":
            command = allowed[item["commandId"]]
            assert command["requiresNetwork"] is False
            assert command["command"].startswith("python ")
        if item["evidenceType"] == "static_preview":
            assert item["manualOnly"] is True
            assert item["path"].startswith("frontend/")


def test_delivery_handoff_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/HANDOFF.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 交接检查", "## 测试方式", "## 限制说明"]:
        assert heading in content
    assert "frontend/operations-launchpad.html" in content
    assert "frontend/operations-presenter.html" in content
    assert "frontend/operations-demo-script.html" in content
    assert "start .\\frontend\\operations-launchpad.html" in content
    assert "start .\\frontend\\operations-presenter.html" in content
    assert "start .\\frontend\\operations-demo-script.html" in content
    assert "python lab_cli.py phase1 check" in content
    assert "DEMO_SCRIPT_CHECKLIST.md" in content
    assert "python -m pytest tests/test_demo_script_checklist.py" in content
    assert "HIGH_RISK_MCP_HANDOFF.md" in content
    assert "python -m pytest tests/test_high_risk_mcp_handoff.py" in content
    assert "FINAL_SIGNOFF.md" in content
    assert "python -m pytest tests/test_final_signoff.py" in content
    assert "OPERATIONS_MANUAL.md" in content
    assert "python -m pytest tests/test_operations_manual.py" in content
    assert "operations-skill-pack" in content
    assert "python -m pytest tests/test_operations_skill_pack.py" in content
    assert "STANDALONE_AGENT_DELIVERY.md" in content
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in content
    assert "ACCESS_ENTRYPOINTS.md" in content
    assert "frontend/access.html" in content
    assert "python -m pytest tests/test_access_entrypoints.py" in content
    assert "PHASE5_MOCK_BASELINE.md" in content
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in content
    assert "python -m pytest tests/test_real_sdk_enablement.py" in content
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in content
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in content
    assert "python -m pytest tests/test_delivery_handoff.py" in content
    assert "WAITING_REVIEW" in content
    assert "MOCK_ONLY" in content
    assert "不接入真实大模型" in content
    assert "不执行未知 Shell" in content


def test_delivery_handoff_ready_and_not_ready_rules_cover_safety():
    handoff = load_handoff()
    ready_text = " ".join(handoff["handoffDecision"]["readyWhen"])
    not_ready_text = " ".join(handoff["handoffDecision"]["notReadyWhen"])

    assert "missingRequired=0" in ready_text
    assert "defaultProvider=mock" in ready_text
    assert "Real SDK minimal implementation shell is present" in ready_text
    assert "Real SDK dependency/env gate is registered" in ready_text
    assert "Safety assertions" in ready_text
    assert "real LLM PoC gate" in not_ready_text
    assert "real provider" in not_ready_text
    assert "real cloud" in not_ready_text
    assert "unknown Shell" in not_ready_text
    assert "WAITING_REVIEW" in not_ready_text
