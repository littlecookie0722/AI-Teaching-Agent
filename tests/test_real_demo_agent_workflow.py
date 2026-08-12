import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_real_demo_agent_workflow_is_design_only_and_safe():
    contract = load_json("delivery/real-demo-agent-workflow.json")

    assert contract["phase"] == "Phase 2 Demo"
    assert contract["mode"] == "MOCK_AGENT_RUNNER"
    assert contract["safety"]["designOnly"] is False
    assert contract["safety"]["mockRunnerImplemented"] is True
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["externalPlatformConnected"] is False
    assert contract["safety"]["newLlmRequestSent"] is False
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert contract["safety"]["realMcpServerStarted"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["autoApproveAllowed"] is False
    assert contract["safety"]["batchStateChangeAllowed"] is False
    assert contract["safety"]["realPublish"] is False
    assert contract["safety"]["blockedHighRiskToolsDirectExecution"] is True
    assert contract["implementationCutover"]["doNotAddNewGate"] is True
    assert contract["implementationCutover"]["requiresRealLlm"] is False
    assert contract["implementationCutover"]["requiresRealMcpServer"] is False


def test_real_demo_agent_workflow_inputs_outputs_exist_and_are_local():
    contract = load_json("delivery/real-demo-agent-workflow.json")

    for entry in [*contract["inputs"], *contract["outputs"]]:
        assert (ROOT / entry["path"]).exists(), entry["path"]
        assert not entry["path"].startswith(("http://", "https://"))


def test_real_demo_agent_workflow_tool_policy_matches_mcp_manifest():
    contract = load_json("delivery/real-demo-agent-workflow.json")
    manifest = load_json("mcp-server/tools.manifest.json")
    tools = {tool["name"]: tool for tool in manifest["tools"]}

    assert set(contract["allowedMcpTools"]).issubset(tools)
    assert set(contract["blockedMcpTools"]) == {"publish_lab", "publish_exam", "destroy_environment"}
    assert set(contract["blockedMcpTools"]).issubset(tools)
    assert set(contract["allowedMcpTools"]).isdisjoint(contract["blockedMcpTools"])
    assert tools["request_review_revision"]["safety"]["newLlmRequestSent"] is False
    assert tools["regenerate_from_revision_mock"]["safety"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
    assert tools["regenerate_from_revision_mock"]["safety"]["realPublish"] is False
    assert tools["create_lab_template_import_preview"]["safety"]["requiresApprovedTask"] is True
    assert tools["create_lab_template_import_preview"]["safety"]["databaseWritten"] is False
    assert tools["create_lab_template_import_preview"]["safety"]["realAgentImport"] is False
    assert tools["create_lab_template_import_preview"]["safety"]["realPublishAllowed"] is False
    assert tools["create_exam_question_import_preview"]["safety"]["requiresApprovedTask"] is True
    assert tools["create_exam_question_import_preview"]["safety"]["answerVisibleToCandidate"] is False
    assert tools["create_exam_question_import_preview"]["safety"]["realAgentImport"] is False
    assert tools["create_grading_rule_import_preview"]["safety"]["requiresApprovedTask"] is True
    assert tools["create_grading_rule_import_preview"]["safety"]["sandboxExecuted"] is False
    assert tools["create_grading_rule_import_preview"]["safety"]["contestantCodeExecuted"] is False
    assert tools["create_lab_template_mock_import"]["safety"]["requiresImportPreview"] is True
    assert tools["create_lab_template_mock_import"]["safety"]["mockStoreWritten"] is True
    assert tools["create_lab_template_mock_import"]["safety"]["databaseWritten"] is False
    assert tools["create_lab_template_mock_import"]["safety"]["realAgentImport"] is False
    assert tools["create_exam_question_mock_import"]["safety"]["answerVisibleToCandidate"] is False
    assert tools["create_exam_question_mock_import"]["safety"]["databaseWritten"] is False
    assert tools["create_exam_question_mock_import"]["safety"]["realAgentImport"] is False
    assert tools["create_grading_rule_mock_import"]["safety"]["sandboxExecuted"] is False
    assert tools["create_grading_rule_mock_import"]["safety"]["contestantCodeExecuted"] is False
    assert tools["create_grading_rule_mock_import"]["safety"]["realAgentImport"] is False
    assert tools["get_agent_entity_readiness_report"]["safety"]["readOnly"] is True
    assert tools["get_agent_entity_readiness_report"]["safety"]["databaseWritten"] is False
    assert tools["get_agent_entity_readiness_report"]["safety"]["realAgentImport"] is False
    assert tools["get_agent_entity_readiness_report"]["safety"]["realPublish"] is False
    assert tools["run_readonly_grading_evidence"]["safety"]["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert tools["run_readonly_grading_evidence"]["safety"]["readonlyOnly"] is True
    assert tools["run_readonly_grading_evidence"]["safety"]["commandExecuted"] is False
    assert tools["run_readonly_grading_evidence"]["safety"]["pytestExecuted"] is False
    assert tools["run_readonly_grading_evidence"]["safety"]["notebookExecuted"] is False
    assert tools["run_readonly_grading_evidence"]["safety"]["contestantCodeExecuted"] is False
    assert tools["run_controlled_grading_evidence"]["safety"]["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert tools["run_controlled_grading_evidence"]["safety"]["readonlyOnly"] is False
    assert tools["run_controlled_grading_evidence"]["safety"]["commandExecuted"] is True
    assert tools["run_controlled_grading_evidence"]["safety"]["pytestExecuted"] is True
    assert tools["run_controlled_grading_evidence"]["safety"]["notebookExecuted"] is False
    assert tools["run_controlled_grading_evidence"]["safety"]["contestantCodeExecuted"] is True
    assert tools["run_controlled_grading_evidence"]["safety"]["networkEnabled"] is False
    assert tools["get_core_workflow_readiness"]["safety"]["readOnly"] is True
    assert tools["get_core_workflow_readiness"]["safety"]["autoApproveAllowed"] is False
    assert tools["get_core_workflow_readiness"]["safety"]["autoPublishAllowed"] is False
    assert tools["get_core_workflow_readiness"]["safety"]["realPublish"] is False
    for blocked in contract["blockedMcpTools"]:
        assert tools[blocked]["reviewRequired"] is True
        assert tools[blocked]["safety"]["reviewIntentOnly"] is True
        assert tools[blocked]["safety"]["autoPublishAllowed"] is False


def test_real_demo_agent_workflow_steps_have_state_checks_and_review_stops():
    contract = load_json("delivery/real-demo-agent-workflow.json")
    steps = contract["workflowSteps"]

    assert [step["order"] for step in steps] == list(range(1, 24))
    assert [step["id"] for step in steps] == [
        "open_static_demo",
        "summarize_review_queue",
        "create_local_lab_task",
        "triage_provider_quality",
        "inspect_review_detail",
        "request_revision",
        "create_mock_revision",
        "inspect_audit",
        "inspect_approved_lab_detail",
        "create_lab_import_preview",
        "inspect_lab_import_preview_signoff",
        "create_lab_mock_import",
        "inspect_approved_exam_detail",
        "create_exam_import_preview",
        "inspect_exam_import_preview_signoff",
        "create_exam_mock_import",
        "inspect_approved_grading_detail",
        "create_grading_import_preview",
        "inspect_grading_import_preview_signoff",
        "create_grading_mock_import",
        "collect_readonly_grading_evidence",
        "collect_controlled_grading_evidence",
        "summarize_agent_entity_readiness",
    ]
    assert all(step["stateCheck"] for step in steps)
    required_mutating_steps = [step for step in steps if step["mutatesState"] and not step.get("optional")]
    assert {step["tool"] for step in required_mutating_steps} == {
        "generate_lab_from_source",
        "request_review_revision",
        "regenerate_from_revision_mock",
    }
    assert all(step["humanReviewStop"] is True for step in required_mutating_steps)
    optional_steps = [step for step in steps if step.get("optional")]
    assert [step["tool"] for step in optional_steps] == [
        "get_review_detail",
        "create_lab_template_import_preview",
        "get_review_detail",
        "create_lab_template_mock_import",
        "get_review_detail",
        "create_exam_question_import_preview",
        "get_review_detail",
        "create_exam_question_mock_import",
        "get_review_detail",
        "create_grading_rule_import_preview",
        "get_review_detail",
        "create_grading_rule_mock_import",
        "run_readonly_grading_evidence",
        "run_controlled_grading_evidence",
        "get_agent_entity_readiness_report",
    ]
    assert optional_steps[1]["mutatesState"] is True
    assert optional_steps[1]["humanReviewStop"] is True
    assert optional_steps[1]["stateCheck"] == "labTemplateImportPreview.databaseWritten == false"
    assert optional_steps[3]["stateCheck"] == "labTemplateMockImport.databaseWritten == false"
    assert optional_steps[5]["stateCheck"] == "examQuestionImportPreview.answerVisibleToCandidate == false"
    assert optional_steps[7]["stateCheck"] == "examQuestionMockImport.answerVisibleToCandidate == false"
    assert optional_steps[9]["stateCheck"] == "gradingRuleImportPreview.sandboxExecuted == false"
    assert optional_steps[11]["stateCheck"] == "gradingRuleMockImport.sandboxExecuted == false"
    assert optional_steps[12]["stateCheck"] == "readonly grading evidence keeps contestantCodeExecuted == false"
    assert optional_steps[13]["stateCheck"] == "controlled grading evidence keeps networkEnabled == false"
    assert optional_steps[14]["stateCheck"] == "agentEntityReadinessReport is read-only and realAgentImport == false"
    assert steps[3]["tool"] == "get_review_task_summary"
    assert steps[3]["mutatesState"] is False
    assert steps[3]["humanReviewStop"] is True
    assert steps[3]["stateCheck"] == "providerQualityTaskSignal drives manual review recommendation"
    assert steps[4]["tool"] == "get_review_detail"
    assert steps[4]["mutatesState"] is False
    assert steps[4]["humanReviewStop"] is True
    assert steps[4]["stateCheck"] == "reviewDetail.reviewPage.actionBar keeps publish blocked"
    assert steps[5]["stateCheck"] == "revisionRequest.taskStatusChanged == false"
    assert steps[6]["stateCheck"] == "mockRegeneration.newTask.status == WAITING_REVIEW"


def test_real_demo_agent_workflow_state_errors_and_validation_are_explicit():
    contract = load_json("delivery/real-demo-agent-workflow.json")

    assert contract["inputSchema"]["additionalProperties"] is False
    assert contract["outputSchema"]["required"] == ["success", "code", "message", "traceId"]
    assert contract["stateModel"]["conversationMemoryMayBeSoleState"] is False
    assert {"TASK_ID", "REVISION_REQUEST_ID"} <= set(contract["stateModel"]["requestState"])
    assert {"PROVIDER_QUALITY_TASK_SIGNAL", "AGENT_REVIEW_TRIAGE"} <= set(contract["stateModel"]["requestState"])
    assert "AGENT_REVIEW_DETAIL_GUIDANCE" in contract["stateModel"]["requestState"]
    assert {"APPROVED_LAB_TASK_ID", "LAB_IMPORT_PREVIEW_ID"} <= set(contract["stateModel"]["requestState"])
    assert {"APPROVED_EXAM_TASK_ID", "EXAM_IMPORT_PREVIEW_ID"} <= set(contract["stateModel"]["requestState"])
    assert {"APPROVED_GRADING_TASK_ID", "GRADING_IMPORT_PREVIEW_ID"} <= set(contract["stateModel"]["requestState"])
    assert {"LAB_MOCK_IMPORT_ID", "EXAM_MOCK_IMPORT_ID", "GRADING_MOCK_IMPORT_ID"} <= set(contract["stateModel"]["requestState"])
    assert "PLATFORM_ENTITY_READINESS_REPORT" in contract["stateModel"]["requestState"]
    assert {"READONLY_GRADING_SUBMISSION", "READONLY_GRADING_EVIDENCE_ID"} <= set(contract["stateModel"]["requestState"])
    assert {"AGENT_CORE_NEXT_TOOL_PLAN", "AGENT_CORE_NEXT_TOOL_EXECUTION"} <= set(contract["stateModel"]["requestState"])
    assert "JsonTaskStore.mcpToolCallRecords" in contract["stateModel"]["persistentState"]
    assert {error["code"] for error in contract["errorModes"]} == {
        "MISSING_TASK_ID",
        "REVISION_REQUEST_NOT_FOUND",
        "TASK_NOT_WAITING_REVIEW",
        "BLOCKED_TOOL_REQUESTED",
        "APPROVED_LAB_TASK_REQUIRED",
        "APPROVED_EXAM_TASK_REQUIRED",
        "APPROVED_GRADING_TASK_REQUIRED",
        "IMPORT_PREVIEW_ACTION_NOT_AVAILABLE",
        "CORE_READINESS_TASK_REQUIRED",
        "CONFIRM_RECOMMENDED_TOOL_REQUIRED",
        "NEXT_TOOL_MANUAL_ACTION_REQUIRED",
        "RECOMMENDED_TOOL_ARGUMENTS_INCOMPLETE",
    }
    assert contract["validation"]["deterministic"] is True
    assert "python -m pytest tests/test_real_demo_agent_runner.py" in contract["validation"]["commands"]
    assert "source task remains WAITING_REVIEW" in contract["validation"]["successSignals"]
    assert "new revision task remains WAITING_REVIEW" in contract["validation"]["successSignals"]
    assert "agent review triage uses providerQualityTaskSignal" in contract["validation"]["successSignals"]
    assert "agent review detail guidance keeps publish blocked" in contract["validation"]["successSignals"]
    assert "optional lab import preview keeps databaseWritten=false" in contract["validation"]["successSignals"]
    assert "optional exam import preview keeps answerVisibleToCandidate=false" in contract["validation"]["successSignals"]
    assert "optional grading import preview keeps sandboxExecuted=false" in contract["validation"]["successSignals"]
    assert "optional lab mock import keeps databaseWritten=false" in contract["validation"]["successSignals"]
    assert "optional exam mock import keeps answerVisibleToCandidate=false" in contract["validation"]["successSignals"]
    assert "optional grading mock import keeps sandboxExecuted=false" in contract["validation"]["successSignals"]
    assert "optional platform entity readiness report keeps realAgentImport=false" in contract["validation"]["successSignals"]
    assert "optional readonly grading evidence keeps contestantCodeExecuted=false" in contract["validation"]["successSignals"]
    assert "core next tool plan reads readiness only and keeps recommendedToolCalled=false" in contract["validation"]["successSignals"]
    assert "core next tool executor calls exactly one confirmed recommended tool" in contract["validation"]["successSignals"]


def test_real_demo_agent_workflow_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/REAL_DEMO_AGENT_WORKFLOW.md").read_text(encoding="utf-8")

    for heading in [
        "## 输入说明",
        "## 输出说明",
        "## Agent 目标",
        "## 允许工具",
        "## 禁止工具",
        "## 状态模型",
        "## 编排步骤",
        "## 错误处理",
        "## 验证方式",
        "## 限制说明",
    ]:
        assert heading in content
    assert "request_review_revision" in content
    assert "regenerate_from_revision_mock" in content
    assert "list_mcp_tool_call_records" in content
    assert "publish_lab" in content
    assert "destroy_environment" in content
    assert "WAITING_REVIEW" in content
    assert "providerQualityTaskSignal" in content
    assert "agentReviewTriage" in content
    assert "agentReviewDetailGuidance" in content
    assert "agentLabImportPreviewGuidance" in content
    assert "agentExamImportPreviewGuidance" in content
    assert "agentGradingImportPreviewGuidance" in content
    assert "approvedLabTaskId" in content
    assert "reviewPage.actionBar" in content
    assert "create_lab_template_import_preview" in content
    assert "create_lab_template_mock_import" in content
    assert "create_exam_question_import_preview" in content
    assert "create_exam_question_mock_import" in content
    assert "create_grading_rule_import_preview" in content
    assert "create_grading_rule_mock_import" in content
    assert "get_agent_entity_readiness_report" in content
    assert "agentAgentEntityReadinessGuidance" in content
    assert "agentLabMockImportGuidance" in content
    assert "agentExamMockImportGuidance" in content
    assert "agentGradingMockImportGuidance" in content
    assert "run_readonly_grading_evidence" in content
    assert "agentReadonlyGradingEvidenceGuidance" in content
    assert "databaseWritten=false" in content
    assert "answerVisibleToCandidate=false" in content
    assert "sandboxExecuted=false" in content
    assert "contestantCodeExecuted=false" in content
    assert "agents/real_demo_runner.py" in content
    assert "python lab_cli.py agent real-demo run" in content
    assert "python -m pytest tests/test_real_demo_agent_runner.py" in content
    assert "python -m pytest tests/test_real_demo_agent_workflow.py" in content
    assert "不创建或启动真实 Agent" in content
    assert "不发送新的真实 LLM 请求" in content
    assert "不自动通过、不批量变更、不自动发布、不真实发布" in content
    assert re.search(r"sk-[A-Za-z0-9]{20,}", content) is None
