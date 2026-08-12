import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_standalone_agent_delivery_is_phase5_mock_only():
    contract = load_json("delivery/standalone-agent-delivery.json")

    assert contract["phase"] == "Phase 5"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["id"] == "phase5_standalone_agent_delivery"
    assert contract["runtimeTarget"]["name"] == "standalone-agent"
    assert contract["runtimeTarget"]["displayName"] == "独立智能体"
    assert contract["runtimeTarget"]["connectionMode"] == "LOCAL_MOCK_ONLY"
    assert contract["runtimeTarget"]["externalPlatformConnected"] is False
    assert contract["runtimeTarget"]["credentialsRequired"] is False
    assert contract["runtimeTarget"]["credentialsStored"] is False
    assert contract["runtimeTarget"]["deploymentPackageGenerated"] is False
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["readOnly"] is True
    assert contract["safety"]["externalPlatformConnected"] is False
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["realProviderEnabled"] is False
    assert contract["safety"]["realMcpServerStarted"] is False
    assert contract["safety"]["networkAccess"] is False
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
    assert contract["safety"]["highRiskToolDirectExecutionAllowed"] is False
    assert contract["safety"]["promptMayBeEmbeddedInBusinessCode"] is False


def test_standalone_agent_delivery_inputs_outputs_exist_and_are_local():
    contract = load_json("delivery/standalone-agent-delivery.json")

    for entry in [*contract["inputs"], *contract["outputs"]]:
        assert entry.get("required") is True or entry.get("requiredForOperation") is True
        assert (ROOT / entry["path"]).exists(), entry["path"]
        assert not entry["path"].startswith(("http://", "https://"))


def test_standalone_agent_delivery_tool_policy_matches_mcp_manifest():
    contract = load_json("delivery/standalone-agent-delivery.json")
    mcp_manifest = load_json("mcp-server/tools.manifest.json")
    tool_names = {tool["name"] for tool in mcp_manifest["tools"]}
    tools = {tool["name"]: tool for tool in mcp_manifest["tools"]}

    assert set(contract["agentSpec"]["allowedToolNames"]).issubset(tool_names)
    assert set(contract["agentSpec"]["blockedToolNames"]) == {"publish_lab", "publish_exam", "destroy_environment"}
    assert set(contract["agentSpec"]["blockedToolNames"]).issubset(tool_names)
    assert set(contract["agentSpec"]["readOnlyHighRiskToolNames"]) == {"get_second_confirmation_status"}
    assert set(contract["agentSpec"]["readOnlyHighRiskToolNames"]).issubset(tool_names)

    for tool_name in contract["agentSpec"]["blockedToolNames"]:
        tool = tools[tool_name]
        assert tool["reviewRequired"] is True
        assert tool["safety"]["reviewIntentOnly"] is True
        assert tool["safety"]["realActionExecuted"] is False
        assert tool["safety"]["autoPublishAllowed"] is False

    second_confirmation = tools["get_second_confirmation_status"]
    assert second_confirmation["safety"]["readOnly"] is True
    assert second_confirmation["safety"]["executeRealActionAllowed"] is False
    assert second_confirmation["safety"]["environmentDestroyed"] is False


def test_standalone_agent_delivery_workflows_and_json_contract_are_valid():
    contract = load_json("delivery/standalone-agent-delivery.json")
    workflow_manifest = load_json("ai-workflows/workflow.manifest.json")
    workflow_registry = load_json("ai-workflows/phase2-workflow-registry.contract.json")
    workflow_ids = {workflow["id"] for workflow in workflow_manifest["workflows"]} | {
        workflow["workflowId"] for workflow in workflow_registry["workflows"]
    }

    assert set(contract["agentSpec"]["workflowIds"]).issubset(workflow_ids)
    assert contract["agentSpec"]["inputSchema"]["additionalProperties"] is False
    assert contract["agentSpec"]["outputSchema"]["required"] == ["success", "code", "message", "traceId"]
    assert contract["agentSpec"]["stateModel"]["conversationMemoryMayBeSoleState"] is False
    assert "record_audit_evidence" in contract["agentSpec"]["planningSteps"]
    assert "high_risk_tool_requested" in contract["agentSpec"]["errorModes"]
    assert contract["reviewGate"]["generatedContentDefaultStatus"] == "WAITING_REVIEW"
    assert contract["reviewGate"]["publishBlockedUntilApproved"] is True
    assert contract["reviewGate"]["highRiskToolDirectExecutionAllowed"] is False


def test_standalone_agent_delivery_commands_are_allowlisted():
    contract = load_json("delivery/standalone-agent-delivery.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_standalone_agent_delivery" in contract["recommendedCommandIds"]

    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert "|" not in command["command"]
        assert "docker run" not in command["command"]


def test_standalone_agent_delivery_is_registered_for_delivery_and_signoff():
    delivery_contract = load_json("config/delivery-package.contract.json")
    delivery_index = load_json("delivery/phase1-delivery-index.json")
    operations_manual = load_json("delivery/operations-manual.json")
    final_signoff = load_json("delivery/final-signoff.json")

    deliverable_ids = {item["id"] for item in delivery_contract["deliverables"]}
    entry_ids = {item["id"] for item in delivery_index["entryPoints"]}
    operations_input_ids = {item["id"] for item in operations_manual["inputs"]}
    signoff_input_ids = {item["id"] for item in final_signoff["inputs"]}

    assert "standalone_agent_delivery_md" in deliverable_ids
    assert "standalone_agent_delivery_contract" in deliverable_ids
    assert "standalone_agent_delivery" in entry_ids
    assert "standalone_agent_delivery_contract" in entry_ids
    assert "standalone_agent_delivery" in operations_input_ids
    assert "standalone_agent_delivery_contract" in operations_input_ids
    assert "standalone_agent_delivery" in signoff_input_ids
    assert "standalone_agent_delivery_contract" in signoff_input_ids
    assert "test_standalone_agent_delivery" in delivery_index["recommendedCommandIds"]
    assert "test_standalone_agent_delivery" in operations_manual["recommendedCommandIds"]
    assert "test_standalone_agent_delivery" in final_signoff["recommendedCommandIds"]

    core = next(item for item in delivery_contract["acceptanceChecklist"] if item["id"] == "core_deliverables_present")
    assert "standalone_agent_delivery_md" in core["source"]["ids"]
    assert "standalone_agent_delivery_contract" in core["source"]["ids"]
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in delivery_contract["recommendedCommands"]


def test_standalone_agent_delivery_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/STANDALONE_AGENT_DELIVERY.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## Mock 智能体规格", "## 交付流程", "## 命令示例", "## 测试方式", "## 限制说明"]:
        assert heading in content

    assert "本地操作者" in content
    assert "mcp-server/tools.manifest.json" in content
    assert "ai-workflows/workflow.manifest.json" in content
    assert "ai-workflows/phase2-workflow-registry.contract.json" in content
    assert "skills/operations-skill-pack/SKILL.md" in content
    assert "delivery/HIGH_RISK_MCP_HANDOFF.md" in content
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in content
    assert "统一 JSON" in content
    assert "WAITING_REVIEW" in content
    assert "不创建或启动真实 Agent" in content
    assert "不连接真实外部平台" in content
