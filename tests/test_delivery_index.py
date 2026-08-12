import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_index():
    with (ROOT / "delivery/phase1-delivery-index.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scripts_manifest():
    with (ROOT / "scripts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_delivery_index_is_phase1_mock_only():
    index = load_index()

    assert index["phase"] == "Phase 1"
    assert index["mode"] == "MOCK_ONLY"
    assert index["safety"]["realLlmCalled"] is False
    assert index["safety"]["realAgentStarted"] is False
    assert index["safety"]["realCloudResourceCreated"] is False
    assert index["safety"]["sandboxExecuted"] is False
    assert index["safety"]["contestantCodeExecuted"] is False
    assert index["safety"]["unknownShellExecuted"] is False
    assert index["safety"]["autoPublishAllowed"] is False
    assert index["safety"]["realPublish"] is False
    assert index["safety"]["remoteUploadAllowed"] is False
    assert index["safety"]["secretVisibleInFrontend"] is False


def test_delivery_index_entry_points_exist_and_are_local():
    index = load_index()
    ids = [entry["id"] for entry in index["entryPoints"]]

    assert len(ids) == len(set(ids))
    assert {
        "operations_launchpad",
        "access_preview",
        "operations_presenter",
        "operations_demo_script",
        "console",
        "delivery_preview",
        "runbook",
        "delivery_contract",
        "high_risk_mcp_handoff",
        "high_risk_mcp_handoff_contract",
        "high_risk_mcp_safety_matrix",
        "final_signoff",
        "final_signoff_contract",
        "operations_manual",
        "operations_manual_contract",
        "operations_skill_pack",
        "operations_skill_pack_contract",
        "standalone_agent_delivery",
        "standalone_agent_delivery_contract",
        "access_entrypoints",
        "access_entrypoints_contract",
        "phase5_mock_baseline",
        "phase5_mock_baseline_contract",
        "demo_script_checklist",
        "demo_script_checklist_contract",
        "faq",
        "faq_contract",
        "handoff",
        "handoff_contract",
        "phase2_readiness",
        "phase2_readiness_contract",
        "phase2_provider_plan",
        "phase2_provider_plan_contract",
    } <= set(ids)
    for entry in index["entryPoints"]:
        assert entry["required"] is True
        assert (ROOT / entry["path"]).exists()
        assert not entry["path"].startswith(("http://", "https://"))


def test_delivery_index_promotes_operations_launchpad_as_primary_preview():
    index = load_index()
    entry = index["entryPoints"][0]

    assert entry["id"] == "operations_launchpad"
    assert entry["type"] == "static_preview"
    assert entry["path"] == "frontend/operations-launchpad.html"
    assert entry["route"] == "/operations/launchpad"
    assert entry["manualOnly"] is True
    assert index["manualPreviewCommands"][0] == "start .\\frontend\\operations-launchpad.html"
    assert "start .\\frontend\\access.html" in index["manualPreviewCommands"]
    assert "start .\\frontend\\operations-presenter.html" in index["manualPreviewCommands"]
    assert "start .\\frontend\\operations-demo-script.html" in index["manualPreviewCommands"]
    assert "Open frontend/operations-launchpad.html as the primary operator launchpad." in index["handoffChecklist"]
    assert "Open frontend/operations-presenter.html for the one-page presenter view before the detailed demo script." in index["handoffChecklist"]
    assert "Open frontend/operations-demo-script.html to follow the operator demo script page." in index["handoffChecklist"]
    assert "Read delivery/HIGH_RISK_MCP_HANDOFF.md before demonstrating or changing high-risk MCP tools." in index[
        "handoffChecklist"
    ]
    assert "Read delivery/FINAL_SIGNOFF.md before final operation signoff." in index["handoffChecklist"]
    assert "Read delivery/OPERATIONS_MANUAL.md before handing the package to operators." in index["handoffChecklist"]
    assert "Read skills/operations-skill-pack/SKILL.md before reusing operations Skills." in index["handoffChecklist"]
    assert "Read delivery/STANDALONE_AGENT_DELIVERY.md before planning Standalone Agent handoff." in index["handoffChecklist"]
    assert "Read delivery/ACCESS_ENTRYPOINTS.md before sharing any IP or port access guidance." in index["handoffChecklist"]
    assert "Read delivery/PHASE5_MOCK_BASELINE.md before starting any real LLM provider PoC." in index[
        "handoffChecklist"
    ]


def test_delivery_index_commands_are_allowlisted():
    index = load_index()
    manifest = load_scripts_manifest()
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(index["recommendedCommandIds"]).issubset(allowed)
    for command_id in index["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")


def test_delivery_index_generated_outputs_are_scoped_and_untracked():
    index = load_index()

    for output in index["generatedOutputs"]:
        assert output["path"].startswith("examples/output/")
        assert output["trackedInGit"] is False
        assert output["requiredForAcceptance"] is True
        assert output["commandId"] in index["recommendedCommandIds"]


def test_delivery_index_readme_documents_usage_and_limits():
    content = (ROOT / "delivery/README.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 测试方式", "## 限制说明"]:
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
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in content
    assert "python -m pytest tests/test_provider_adapter_workflow.py" in content
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
    assert "python -m pytest tests/test_access_entrypoints.py" in content
    assert "PHASE5_MOCK_BASELINE.md" in content
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in content
    assert "不接入真实大模型" in content
