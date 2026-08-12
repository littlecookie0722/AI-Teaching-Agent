import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_PATH = "delivery/high-risk-mcp-handoff.json"
SCOPE = {"publish_lab", "publish_exam", "destroy_environment", "get_second_confirmation_status"}


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_handoff():
    return load_json(HANDOFF_PATH)


def test_high_risk_mcp_handoff_is_mock_only():
    handoff = load_handoff()

    assert handoff["phase"] == "Phase 5"
    assert handoff["mode"] == "MOCK_ONLY"
    assert handoff["id"] == "high_risk_mcp_handoff"
    assert handoff["safety"]["manualOnly"] is True
    assert handoff["safety"]["readOnly"] is True
    assert handoff["safety"]["realMcpServerStarted"] is False
    assert handoff["safety"]["realAgentStarted"] is False
    assert handoff["safety"]["realLlmCalled"] is False
    assert handoff["safety"]["realCloudResourceChanged"] is False
    assert handoff["safety"]["autoPublishAllowed"] is False
    assert handoff["safety"]["realPublish"] is False
    assert handoff["safety"]["environmentDestroyed"] is False


def test_high_risk_mcp_handoff_matches_safety_matrix_scope():
    handoff = load_handoff()
    matrix = load_json(handoff["sourceSafetyMatrix"])

    assert set(handoff["scope"]) == SCOPE
    assert set(handoff["scope"]) == set(matrix["scope"])
    assert handoff["sourceManifest"] == matrix["sourceManifest"]
    assert (ROOT / handoff["sourceSafetyMatrix"]).exists()
    assert (ROOT / handoff["sourceManifest"]).exists()


def test_high_risk_mcp_handoff_inputs_outputs_and_items_exist():
    handoff = load_handoff()
    item_ids = {item["id"] for item in handoff["handoffItems"]}

    assert {
        "read_safety_matrix",
        "confirm_publish_intents_review_only",
        "confirm_destroy_intent_blocked",
        "confirm_second_confirmation_query_read_only",
        "open_review_center",
        "open_audit_observability",
        "run_safety_matrix_tests",
        "run_handoff_tests",
    } <= item_ids

    for entry in handoff["inputs"]:
        assert entry["required"] is True
        assert (ROOT / entry["path"]).exists()

    for entry in handoff["outputs"]:
        assert entry["localOnly"] is True
        assert entry["generated"] is False

    for item in handoff["handoffItems"]:
        assert item["required"] is True
        assert item["expectedSignal"]
        if item["evidenceType"] in {"local_file", "static_preview"}:
            assert (ROOT / item["path"]).exists()
        if item["evidenceType"] == "static_preview":
            assert item["manualOnly"] is True


def test_high_risk_mcp_handoff_commands_are_allowlisted():
    handoff = load_handoff()
    scripts_manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in scripts_manifest["allowedCommands"]}

    assert set(handoff["recommendedCommandIds"]) <= set(allowed)
    for command_id in handoff["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["command"].startswith("python ")
        assert command["requiresNetwork"] is False
        assert command["writesToWorkspace"] is False

    for item in handoff["handoffItems"]:
        if item["evidenceType"] == "allowlisted_command":
            assert item["commandId"] in allowed


def test_high_risk_mcp_handoff_policy_blocks_real_actions():
    handoff = load_handoff()
    blocked = set(handoff["operationPolicy"]["blockedActions"])
    allowed = set(handoff["operationPolicy"]["allowedReadOnlyActions"])

    assert {"readSafetyMatrix", "openReviewCenter", "openAuditObservability", "runAllowlistedTests"} <= allowed
    assert {
        "startRealMcpServer",
        "startRealAgent",
        "callRealLlm",
        "executeRealPublish",
        "destroyRealEnvironment",
        "confirmSecondFactor",
        "bypassHumanReview",
    } <= blocked
    assert handoff["operationPolicy"]["requiresNewTaskBeforeRealEnablement"] is True


def test_high_risk_mcp_handoff_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/HIGH_RISK_MCP_HANDOFF.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 交接检查", "## 测试方式", "## 限制说明"]:
        assert heading in content
    for tool_name in SCOPE:
        assert tool_name in content
    assert "mcp-server/high-risk-tool-safety.contract.json" in content
    assert "python -m pytest tests/test_high_risk_mcp_safety_contract.py" in content
    assert "python -m pytest tests/test_high_risk_mcp_handoff.py" in content
    assert "不启动真实 MCP Server" in content
    assert "不执行真实发布" in content
    assert "不销毁真实环境" in content
