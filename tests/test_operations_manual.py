import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_operations_manual_is_phase5_mock_only():
    contract = load_json("delivery/operations-manual.json")

    assert contract["phase"] == "Phase 5"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["id"] == "phase5_operations_manual"
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["readOnly"] is True
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["realProviderEnabled"] is False
    assert contract["safety"]["realMcpServerStarted"] is False
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["realCloudResourceChanged"] is False
    assert contract["safety"]["realCloudResourceCreated"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["unknownShellExecuted"] is False
    assert contract["safety"]["autoPublishAllowed"] is False
    assert contract["safety"]["realPublish"] is False
    assert contract["safety"]["remoteUploadAllowed"] is False
    assert contract["safety"]["secretVisibleInFrontend"] is False
    assert contract["safety"]["answerVisibleToCandidate"] is False


def test_operations_manual_inputs_outputs_and_evidence_exist():
    contract = load_json("delivery/operations-manual.json")

    for entry in [*contract["inputs"], *contract["outputs"]]:
        assert entry.get("required") is True or entry.get("requiredForOperation") is True
        assert (ROOT / entry["path"]).exists()
        assert not entry["path"].startswith(("http://", "https://"))

    for output in contract["generatedEvidence"]:
        assert output["path"].startswith("examples/output/")
        assert output["trackedInGit"] is False
        assert output["commandId"] in contract["recommendedCommandIds"]


def test_operations_manual_commands_are_allowlisted_and_workflows_are_safe():
    contract = load_json("delivery/operations-manual.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_operations_manual" in contract["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in contract["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in contract["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in contract["recommendedCommandIds"]

    workflow_ids = {workflow["id"] for workflow in contract["manualWorkflows"]}
    assert {
        "daily_readiness_check",
        "content_generation_review",
        "high_risk_mcp_review",
        "real_llm_poc_readiness_review",
    } <= workflow_ids

    for workflow in contract["manualWorkflows"]:
        assert workflow["required"] is True
        assert set(workflow["recommendedCommandIds"]).issubset(allowed)
        assert workflow["expectedSignals"]

    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert "|" not in command["command"]


def test_operations_manual_is_registered_in_delivery_and_signoff_contracts():
    delivery_contract = load_json("config/delivery-package.contract.json")
    delivery_index = load_json("delivery/phase1-delivery-index.json")
    final_signoff = load_json("delivery/final-signoff.json")

    deliverable_ids = {item["id"] for item in delivery_contract["deliverables"]}
    entry_ids = {item["id"] for item in delivery_index["entryPoints"]}
    signoff_input_ids = {item["id"] for item in final_signoff["inputs"]}

    assert "operations_manual_md" in deliverable_ids
    assert "operations_manual_contract" in deliverable_ids
    assert "operations_skill_pack_md" in deliverable_ids
    assert "operations_skill_pack_contract" in deliverable_ids
    assert "standalone_agent_delivery_md" in deliverable_ids
    assert "standalone_agent_delivery_contract" in deliverable_ids
    assert "phase5_mock_baseline_md" in deliverable_ids
    assert "phase5_mock_baseline_contract" in deliverable_ids
    assert "real_sdk_enablement" in deliverable_ids
    assert "real_sdk_enablement_contract" in deliverable_ids
    assert "real_sdk_minimal_impl" in deliverable_ids
    assert "real_sdk_minimal_impl_contract" in deliverable_ids
    assert "real_sdk_dependency_env_gate" in deliverable_ids
    assert "real_sdk_dependency_env_gate_contract" in deliverable_ids
    assert "operations_manual" in entry_ids
    assert "operations_manual_contract" in entry_ids
    assert "phase5_mock_baseline" in entry_ids
    assert "phase5_mock_baseline_contract" in entry_ids
    assert "operations_manual" in signoff_input_ids
    assert "operations_manual_contract" in signoff_input_ids
    assert "standalone_agent_delivery" in signoff_input_ids
    assert "standalone_agent_delivery_contract" in signoff_input_ids
    assert "phase5_mock_baseline" in signoff_input_ids
    assert "phase5_mock_baseline_contract" in signoff_input_ids
    assert "real_sdk_enablement" in signoff_input_ids
    assert "real_sdk_enablement_contract" in signoff_input_ids
    assert "real_sdk_minimal_impl" in signoff_input_ids
    assert "real_sdk_minimal_impl_contract" in signoff_input_ids
    assert "real_sdk_dependency_env_gate" in signoff_input_ids
    assert "real_sdk_dependency_env_gate_contract" in signoff_input_ids
    assert "test_operations_manual" in delivery_index["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in delivery_index["recommendedCommandIds"]
    assert "test_operations_manual" in final_signoff["recommendedCommandIds"]
    assert "test_standalone_agent_delivery" in final_signoff["recommendedCommandIds"]
    assert "test_access_entrypoints" in final_signoff["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in final_signoff["recommendedCommandIds"]

    core = next(item for item in delivery_contract["acceptanceChecklist"] if item["id"] == "core_deliverables_present")
    assert "operations_manual_md" in core["source"]["ids"]
    assert "operations_manual_contract" in core["source"]["ids"]
    assert "operations_skill_pack_md" in core["source"]["ids"]
    assert "operations_skill_pack_contract" in core["source"]["ids"]
    assert "standalone_agent_delivery_md" in core["source"]["ids"]
    assert "standalone_agent_delivery_contract" in core["source"]["ids"]
    assert "access_entrypoints_md" in core["source"]["ids"]
    assert "access_entrypoints_contract" in core["source"]["ids"]
    assert "frontend_access_entrypoints_prototype" in core["source"]["ids"]
    assert "phase5_mock_baseline_md" in core["source"]["ids"]
    assert "phase5_mock_baseline_contract" in core["source"]["ids"]
    assert "real_sdk_enablement" in core["source"]["ids"]
    assert "real_sdk_enablement_contract" in core["source"]["ids"]
    assert "real_sdk_minimal_impl" in core["source"]["ids"]
    assert "real_sdk_minimal_impl_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate_contract" in core["source"]["ids"]
    assert "python -m pytest tests/test_operations_manual.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_operations_skill_pack.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_access_entrypoints.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_enablement.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in delivery_contract["recommendedCommands"]


def test_operations_manual_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/OPERATIONS_MANUAL.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 运营流程", "## 命令示例", "## 测试方式", "## 限制说明"]:
        assert heading in content

    assert "frontend/operations-launchpad.html" in content
    assert "frontend/operations-signoff.html" in content
    assert "delivery/FINAL_SIGNOFF.md" in content
    assert "skills/operations-skill-pack/SKILL.md" in content
    assert "delivery/STANDALONE_AGENT_DELIVERY.md" in content
    assert "delivery/ACCESS_ENTRYPOINTS.md" in content
    assert "delivery/PHASE5_MOCK_BASELINE.md" in content
    assert "frontend/access.html" in content
    assert "delivery/HIGH_RISK_MCP_HANDOFF.md" in content
    assert "scripts/manifest.json" in content
    assert "python lab_cli.py phase1 check" in content
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert (
        "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json "
        "--output examples/output/phase1-acceptance-report.md"
    ) in content
    assert "python -m pytest tests/test_operations_manual.py" in content
    assert "python -m pytest tests/test_operations_skill_pack.py" in content
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in content
    assert "python -m pytest tests/test_access_entrypoints.py" in content
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in content
    assert "python -m pytest tests/test_real_sdk_enablement.py" in content
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in content
    assert "WAITING_REVIEW" in content
    assert "不接入真实大模型" in content
    assert "不启动真实智能体或真实 MCP Server" in content
    assert "不启动真实 HTTP 服务" in content


def test_operations_manual_roles_block_high_risk_actions():
    contract = load_json("delivery/operations-manual.json")
    role_text = " ".join(
        action
        for role in contract["operatorRoles"]
        for action in [*role["allowedActions"], *role["blockedActions"]]
    )

    assert "Open local static previews" in role_text
    assert "Start real Agent" in role_text
    assert "Enable real Provider" in role_text
    assert "Turn high-risk MCP intent into real execution" in role_text
