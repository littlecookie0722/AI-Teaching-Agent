import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "mcp-server/high-risk-tool-safety.contract.json"
HIGH_RISK_INTENT_TOOLS = {"publish_lab", "publish_exam", "destroy_environment"}
SCOPE = HIGH_RISK_INTENT_TOOLS | {"get_second_confirmation_status"}


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_contract():
    return load_json(CONTRACT_PATH)


def matrix_by_name(contract):
    return {row["name"]: row for row in contract["matrix"]}


def test_high_risk_safety_contract_is_phase4_mock_only():
    contract = load_contract()

    assert contract["phase"] == "Phase 4"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["title"] == "High-Risk MCP Tool Safety Matrix"
    assert (ROOT / contract["sourceManifest"]).exists()
    assert (ROOT / contract["frontendMockData"]).exists()
    assert all((ROOT / path).exists() for path in contract["relatedContracts"])
    assert set(contract["scope"]) == SCOPE
    assert set(matrix_by_name(contract)) == SCOPE
    assert all(value is False for value in contract["globalSafetyAssertions"].values())


def test_high_risk_safety_matrix_matches_mcp_manifest():
    contract = load_contract()
    manifest = load_json(contract["sourceManifest"])
    manifest_tools = {tool["name"]: tool for tool in manifest["tools"]}

    for name, row in matrix_by_name(contract).items():
        tool = manifest_tools[name]

        assert row["riskLevel"] == tool["riskLevel"]
        assert row["reviewRequired"] == tool["reviewRequired"]
        assert row["backend"] == tool["backend"]
        assert tool["safety"]["mode"] == "MOCK_ONLY"

        for key, expected in row["expectedManifestSafety"].items():
            assert tool["safety"][key] == expected


def test_high_risk_intent_tools_create_review_tasks_only():
    contract = load_contract()
    rows = matrix_by_name(contract)
    allowed_states = set(contract["postReviewDispositionStates"])

    expected_task_types = {
        "publish_lab": "MCP_PUBLISH_LAB_INTENT",
        "publish_exam": "MCP_PUBLISH_EXAM_INTENT",
        "destroy_environment": "MCP_DESTROY_ENVIRONMENT_INTENT",
    }

    for name in HIGH_RISK_INTENT_TOOLS:
        row = rows[name]

        assert row["toolCategory"] == "high_risk_review_intent"
        assert row["createsAiTask"] is True
        assert row["createdTaskType"] == expected_task_types[name]
        assert row["createdTaskStatus"] == "WAITING_REVIEW"
        assert row["reviewIntentOnly"] is True
        assert row["readOnly"] is False
        assert set(row["allowedPostReviewDispositionStates"]) <= allowed_states
        assert "bypassHumanReview" in row["blockedActions"]
        assert row["expectedRuntimeSafety"]["realActionExecuted"] is False
        assert row["expectedRuntimeSafety"]["realPublish"] is False
        assert row["expectedRuntimeSafety"]["realCloudResourceChanged"] is False

    assert rows["publish_lab"]["requiresSecondConfirmation"] is False
    assert rows["publish_exam"]["requiresSecondConfirmation"] is False
    assert rows["destroy_environment"]["requiresSecondConfirmation"] is True
    assert "confirmSecondFactor" in rows["destroy_environment"]["blockedActions"]
    assert rows["destroy_environment"]["expectedRuntimeSafety"]["confirmationEndpointEnabled"] is False
    assert rows["destroy_environment"]["expectedRuntimeSafety"]["environmentDestroyed"] is False


def test_second_confirmation_status_tool_is_read_only_query_only():
    row = matrix_by_name(load_contract())["get_second_confirmation_status"]

    assert row["toolCategory"] == "read_only_second_confirmation_status"
    assert row["backend"]["method"] == "GET"
    assert row["reviewRequired"] is False
    assert row["createsAiTask"] is False
    assert row["createdTaskType"] is None
    assert row["createdTaskStatus"] is None
    assert row["reviewIntentOnly"] is True
    assert row["readOnly"] is True
    assert row["requiresSecondConfirmation"] is True
    assert row["allowedPostReviewDispositionStates"] == ["APPROVED_PENDING_SECOND_CONFIRMATION"]
    assert {"confirmSecondFactor", "executeRealAction", "destroyRealEnvironment", "bypassHumanReview"} <= set(row["blockedActions"])
    assert row["expectedRuntimeSafety"]["confirmationActionAvailable"] is False
    assert row["expectedRuntimeSafety"]["confirmationEndpointEnabled"] is False
    assert row["expectedRuntimeSafety"]["executeRealActionAllowed"] is False
    assert row["expectedRuntimeSafety"]["destroyRealEnvironmentEnabled"] is False
    assert row["expectedRuntimeSafety"]["environmentDestroyed"] is False


def test_safety_matrix_matches_frontend_mock_evidence():
    contract = load_contract()
    mock_data = load_json(contract["frontendMockData"])
    rows = matrix_by_name(contract)
    intent_items = {item["toolName"]: item for item in mock_data["highRiskMcpIntentPrototype"]["items"]}
    call_records = {record["id"]: record for record in mock_data["mcpToolCallRecords"]}

    assert set(intent_items) == HIGH_RISK_INTENT_TOOLS
    assert mock_data["highRiskMcpIntentPrototype"]["safety"]["reviewIntentOnly"] is True
    assert mock_data["highRiskMcpIntentPrototype"]["safety"]["realPublish"] is False
    assert mock_data["highRiskMcpIntentPrototype"]["safety"]["environmentDestroyed"] is False

    for name in HIGH_RISK_INTENT_TOOLS:
        row = rows[name]
        item = intent_items[name]
        record = call_records[row["frontendEvidence"]["mcpToolCallRecordId"]]

        assert item["taskType"] == row["createdTaskType"]
        assert item["riskLevel"] == row["riskLevel"]
        assert item["requiresSecondConfirmation"] == row["requiresSecondConfirmation"]
        assert item["postReviewDisposition"]["state"] == row["frontendEvidence"]["expectedMockDisposition"]
        assert item["postReviewDisposition"]["realActionExecuted"] is False
        assert item["postReviewDisposition"]["realPublish"] is False
        assert item["postReviewDisposition"]["environmentDestroyed"] is False
        assert record["toolName"] == name
        assert record["riskLevel"] == row["riskLevel"]
        assert record["reviewRequired"] is True
        assert record["realMcpServerStarted"] is False
        assert record["realAgentStarted"] is False
        assert record["realActionExecuted"] is False
        assert record["realPublish"] is False

    status_row = rows["get_second_confirmation_status"]
    status = mock_data["secondConfirmationStatusPrototype"]
    status_record = call_records[status_row["frontendEvidence"]["mcpToolCallRecordId"]]

    assert status["mcpToolName"] == "get_second_confirmation_status"
    assert status["readOnly"] is True
    assert status["state"] == status_row["frontendEvidence"]["expectedMockDisposition"]
    assert status["confirmationActionAvailable"] is False
    assert status["confirmationEndpointEnabled"] is False
    assert status["destroyRealEnvironmentEnabled"] is False
    assert status["environmentDestroyed"] is False
    assert status_record["toolName"] == "get_second_confirmation_status"
    assert status_record["reviewRequired"] is False
    assert status_record["readOnly"] is True
    assert status_record["confirmationEndpointEnabled"] is False
    assert status_record["destroyRealEnvironmentEnabled"] is False
    assert status_record["environmentDestroyed"] is False


def test_high_risk_contract_references_allowlisted_commands():
    contract = load_contract()
    scripts_manifest = load_json("scripts/manifest.json")
    allowed_ids = {command["id"] for command in scripts_manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]) <= allowed_ids
