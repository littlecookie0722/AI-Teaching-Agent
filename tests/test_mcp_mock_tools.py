import subprocess
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.mock_api import handle_request
from cli.ai_task import create_waiting_review_task
from cli.store import JsonTaskStore
from mcp_server import McpToolError, invoke_mcp_tool, list_mcp_tools, load_mcp_manifest


ROOT = Path(__file__).resolve().parents[1]


class RecordingPlatformImportHandler(BaseHTTPRequestHandler):
    requests = []
    quiet = True

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8"))
        self.__class__.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        response = {
            "draftImportId": "draft_import_mcp_test",
            "status": "PENDING_MANUAL_PLATFORM_REVIEW",
            "receivedEntityType": body.get("entityType"),
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        self.__class__.requests.append(
            {
                "method": "GET",
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
            }
        )
        response = {
            "draftImportId": "draft_import_mcp_test",
            "status": "ACCEPTED_FOR_DRAFT",
            "message": "draft import accepted for manual publish review",
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        if self.quiet:
            return
        super().log_message(format, *args)


def start_recording_platform_server():
    RecordingPlatformImportHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingPlatformImportHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def stop_recording_platform_server(server, thread):
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


def fake_controlled_docker_run(args, **kwargs):
    if args[:2] == ["docker", "info"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='"29.5.3"', stderr="")
    if args[:3] == ["docker", "image", "inspect"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:demo", stderr="")
    if "main.py" in args:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="accuracy=0.90\n", stderr="")
    if "pytest" in args:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")
    raise AssertionError(f"unexpected command: {args}")


def test_mcp_mock_tools_list_manifest_tools():
    manifest = load_mcp_manifest(ROOT)
    default_tools = list_mcp_tools(ROOT)
    tools = list_mcp_tools(ROOT, profile="all")

    assert manifest["mode"] == "MOCK_ONLY"
    assert tools
    assert len(default_tools) < len(tools)
    default_names = {tool["name"] for tool in default_tools}
    assert "generate_lab_from_source" in default_names
    assert "run_grading_evidence_auto" in default_names
    for name in [
        "create_grading_job",
        "list_grading_jobs",
        "get_grading_job",
        "run_grading_job",
        "create_grading_record",
        "list_grading_records",
        "get_grading_record",
        "review_grading_record",
    ]:
        assert name in default_names
    assert "list_agent_entities" in default_names
    assert "get_agent_entity" in default_names
    assert "validate_agent_entity_contract" in default_names
    assert "create_agent_entity_import_dry_run" in default_names
    assert "agent_internal_publish_request" not in default_names
    assert "query_agent_publish_status" not in default_names
    assert "publish_lab" not in default_names
    assert "destroy_environment" not in default_names
    assert "workflow_demo" in {tool["name"] for tool in tools}
    assert "list_provider_audit_events" in {tool["name"] for tool in tools}
    assert "list_mcp_tool_call_records" in {tool["name"] for tool in tools}
    assert "list_workflows" in {tool["name"] for tool in tools}
    assert "get_workflow" in {tool["name"] for tool in tools}
    assert "get_second_confirmation_status" in {tool["name"] for tool in tools}
    assert "get_real_llm_runtime_config" in {tool["name"] for tool in tools}
    assert "get_real_dsl_review_preview" in {tool["name"] for tool in tools}
    assert "create_lab_template_import_preview" in {tool["name"] for tool in tools}
    assert "create_exam_question_import_preview" in {tool["name"] for tool in tools}
    assert "create_grading_rule_import_preview" in {tool["name"] for tool in tools}
    assert "create_lab_template_mock_import" in {tool["name"] for tool in tools}
    assert "create_exam_question_mock_import" in {tool["name"] for tool in tools}
    assert "create_grading_rule_mock_import" in {tool["name"] for tool in tools}
    assert "get_agent_entity_readiness_report" in {tool["name"] for tool in tools}
    assert "get_core_workflow_readiness" in {tool["name"] for tool in tools}
    assert "create_agent_entity_import_dry_run" in {tool["name"] for tool in tools}
    assert "agent_internal_publish_request" in {tool["name"] for tool in tools}
    assert "query_agent_publish_status" in {tool["name"] for tool in tools}
    assert "record_agent_entity_publish_result" in {tool["name"] for tool in tools}
    assert "record_agent_entity_signoff" in {tool["name"] for tool in tools}
    assert "record_final_publish_review_decision" in {tool["name"] for tool in tools}
    assert "record_review_decision_note" in {tool["name"] for tool in tools}
    assert "run_readonly_grading_evidence" in {tool["name"] for tool in tools}
    assert "run_grading_evidence_auto" in {tool["name"] for tool in tools}
    assert "run_grading_job" in {tool["name"] for tool in tools}
    assert "review_grading_record" in {tool["name"] for tool in tools}
    assert "get_grading_result_preview" in {tool["name"] for tool in tools}
    assert all(tool["backend"]["path"].startswith("/api/") for tool in tools)
    review_summary = next(tool for tool in tools if tool["name"] == "get_review_task_summary")
    assert review_summary["outputContract"]["dataPath"] == "data.reviewTaskSummary"
    assert "reviewPriorityQueue" in review_summary["outputContract"]["requiredFields"]
    assert "providerQualityTaskSignal" in review_summary["outputContract"]["requiredFields"]
    assert "preApproveReviewCheckSignal" in review_summary["outputContract"]["requiredFields"]
    assert "realDemoReviewQueue" in review_summary["outputContract"]["requiredFields"]
    assert "controlledDockerEvidenceReviewSignal" in review_summary["outputContract"]["requiredFields"]
    assert "notebookEvidenceReviewPlan" in review_summary["outputContract"]["requiredFields"]
    assert review_summary["outputContract"]["reviewPriorityQueue"]["batchStateChangeAllowed"] is False
    assert review_summary["outputContract"]["providerQualityTaskSignal"]["autoApproveAllowed"] is False
    assert review_summary["outputContract"]["providerQualityTaskSignal"]["realPublishAllowed"] is False
    assert "providerQualitySummary" in review_summary["outputContract"]["reviewPriorityQueue"]["itemFields"]
    assert "preApproveReviewCheck" in review_summary["outputContract"]["reviewPriorityQueue"]["itemFields"]
    assert (
        review_summary["outputContract"]["reviewPriorityQueue"]["manualReviewChecklistSummary"]["source"]
        == "reviewDetail.assessmentPlan.manualReviewChecklist"
    )
    real_demo_contract = review_summary["outputContract"]["realDemoReviewQueue"]
    assert real_demo_contract["dataPath"] == "data.reviewTaskSummary.realDemoReviewQueue"
    assert real_demo_contract["purpose"] == "real_llm_demo_human_review_entry_only"
    assert real_demo_contract["readonlyEvidenceReportDetailSource"] == "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    assert real_demo_contract["taskTotal"] == 4
    assert real_demo_contract["waitingReviewTotal"] == 4
    assert real_demo_contract["schemaValidatedTotal"] == 4
    assert real_demo_contract["readonlyEvidenceCollectedTotal"] == 2
    assert real_demo_contract["answerVisibleToCandidate"] is False
    assert real_demo_contract["autoApproveAllowed"] is False
    assert real_demo_contract["batchStateChangeAllowed"] is False
    assert real_demo_contract["realPublishAllowed"] is False
    controlled_contract = review_summary["outputContract"]["controlledDockerEvidenceReviewSignal"]
    assert controlled_contract["dataPath"] == "data.reviewTaskSummary.controlledDockerEvidenceReviewSignal"
    assert controlled_contract["purpose"] == "show_controlled_docker_evidence_coverage_for_human_review_only"
    assert controlled_contract["source"] == "reviewDetail.controlledGradingEvidence or realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_contract["dynamicSource"] == "reviewDetail.controlledGradingEvidence"
    assert controlled_contract["fallbackSource"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_contract["coveredCheckIds"] == ["check_q1", "check_q4"]
    assert controlled_contract["coveredCheckTypes"] == ["stdout_contains", "pytest"]
    assert controlled_contract["earnedScore"] == 40
    assert controlled_contract["totalControlledScore"] == 40
    assert controlled_contract["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert controlled_contract["remainingCheckTypes"] == ["notebook_cell"]
    assert controlled_contract["remainingStatus"] == "STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW"
    assert controlled_contract["notebookEvidenceReviewPlanSource"] == "reviewTaskSummary.notebookEvidenceReviewPlan"
    assert controlled_contract["autoApproveAllowed"] is False
    assert controlled_contract["batchStateChangeAllowed"] is False
    assert controlled_contract["realPublishAllowed"] is False
    assert controlled_contract["hostExecutionAllowed"] is False
    assert controlled_contract["networkAllowed"] is False
    notebook_contract = review_summary["outputContract"]["notebookEvidenceReviewPlan"]
    assert notebook_contract["dataPath"] == "data.reviewTaskSummary.notebookEvidenceReviewPlan"
    assert notebook_contract["purpose"] == "show_notebook_cell_evidence_review_plan_without_execution"
    assert notebook_contract["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert notebook_contract["checkTypes"] == ["notebook_cell"]
    assert notebook_contract["checkTotal"] == 2
    assert notebook_contract["scoreTotal"] == 60
    assert notebook_contract["evidenceStatus"] == "STATIC_NOTEBOOK_EVIDENCE_COLLECTED"
    assert notebook_contract["reviewStrategy"] == "STATIC_NOTEBOOK_JSON_PARSE_REVIEW"
    assert notebook_contract["staticEvidenceReportPath"] == "examples/output/mimo-real-demo-notebook-static-report.json"
    assert notebook_contract["staticEvidenceMethod"] == "STATIC_NOTEBOOK_JSON_PARSE"
    assert notebook_contract["notebookKernelStarted"] is False
    assert notebook_contract["notebookExecuted"] is False
    assert notebook_contract["contestantCodeExecuted"] is False
    assert notebook_contract["autoApproveAllowed"] is False
    runtime_config = next(tool for tool in tools if tool["name"] == "get_real_llm_runtime_config")
    assert runtime_config["backend"]["path"] == "/api/providers/real-llm-runtime-config"
    assert runtime_config["outputContract"]["dataPath"] == "data.realLlmRuntimeConfig"
    assert runtime_config["outputContract"]["component"] == "RealLlmRuntimeConfigSummary"
    assert runtime_config["safety"]["readOnly"] is True
    assert runtime_config["safety"]["requestSent"] is False
    assert runtime_config["safety"]["realLlmCalled"] is False
    assert runtime_config["safety"]["secretValueReturned"] is False
    real_dsl_preview = next(tool for tool in tools if tool["name"] == "get_real_dsl_review_preview")
    assert real_dsl_preview["backend"]["path"] == "/api/review/real-dsl-preview"
    assert real_dsl_preview["outputContract"]["dataPath"] == "data.realDslReviewPreview"
    assert real_dsl_preview["outputContract"]["component"] == "RealDslReviewPreview"
    assert "qualitySignals" in real_dsl_preview["outputContract"]["requiredFields"]
    assert "reviewIssues" in real_dsl_preview["outputContract"]["requiredFields"]
    assert "revisionSuggestions" in real_dsl_preview["outputContract"]["requiredFields"]
    assert "qualityIssueTotal" in real_dsl_preview["outputContract"]["summaryFields"]
    assert real_dsl_preview["safety"]["newLlmRequestSent"] is False
    assert real_dsl_preview["safety"]["secretsRead"] is False
    assert real_dsl_preview["safety"]["networkAccess"] is False
    assert real_dsl_preview["safety"]["answerVisibleToCandidate"] is False
    assert real_dsl_preview["safety"]["gradingRefVisibleToCandidate"] is False
    assert real_dsl_preview["safety"]["realPublishAllowed"] is False
    real_dsl_revision = next(tool for tool in tools if tool["name"] == "create_real_dsl_revision_draft")
    assert real_dsl_revision["backend"]["path"] == "/api/review/real-dsl-revision"
    assert real_dsl_revision["inputSchema"]["required"] == ["kind", "reviewer", "comment"]
    assert real_dsl_revision["inputSchema"]["properties"]["providerMode"]["enum"] == ["local", "real-llm"]
    assert real_dsl_revision["inputSchema"]["properties"]["explicitRealCallOptIn"]["type"] == "boolean"
    assert real_dsl_revision["outputContract"]["dataPath"] == "data.realDslRevisionDraft"
    assert real_dsl_revision["outputContract"]["component"] == "RealDslRevisionDraft"
    assert real_dsl_revision["outputContract"]["realLlmCalledWhenProviderModeRealLlm"] is True
    assert real_dsl_revision["outputContract"]["autoPublishAllowed"] is False
    assert real_dsl_revision["safety"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
    assert real_dsl_revision["safety"]["newLlmRequestSent"] is False
    assert real_dsl_revision["safety"]["realLlmCalled"] is False
    assert real_dsl_revision["safety"]["secretsRead"] is False
    assert real_dsl_revision["safety"]["networkAccess"] is False
    assert real_dsl_revision["safety"]["autoPublishAllowed"] is False
    assert real_dsl_revision["safety"]["realPublishAllowed"] is False
    lab_import_preview = next(tool for tool in tools if tool["name"] == "create_lab_template_import_preview")
    assert lab_import_preview["backend"]["path"] == "/api/labs/import-preview"
    assert lab_import_preview["inputSchema"]["required"] == ["taskId", "reviewer"]
    assert lab_import_preview["outputContract"]["dataPath"] == "data.labTemplateImportPreview"
    assert lab_import_preview["outputContract"]["component"] == "LabTemplateImportPreview"
    assert lab_import_preview["outputContract"]["databaseWritten"] is False
    assert lab_import_preview["outputContract"]["realAgentImport"] is False
    assert lab_import_preview["safety"]["requiresApprovedTask"] is True
    assert lab_import_preview["safety"]["realPublishAllowed"] is False
    real_dsl_revision_batch = next(tool for tool in tools if tool["name"] == "create_real_dsl_revision_batch_from_preview")
    assert real_dsl_revision_batch["backend"]["path"] == "/api/review/real-dsl-revision-batch"
    assert real_dsl_revision_batch["inputSchema"]["required"] == ["reviewer"]
    assert real_dsl_revision_batch["outputContract"]["dataPath"] == "data.realDslRevisionBatch"
    assert real_dsl_revision_batch["outputContract"]["component"] == "RealDslRevisionBatch"
    assert real_dsl_revision_batch["safety"]["newLlmRequestSent"] is False
    assert real_dsl_revision_batch["safety"]["realPublishAllowed"] is False
    real_dsl_revision_diff_preview = next(tool for tool in tools if tool["name"] == "get_real_dsl_revision_diff_preview")
    assert real_dsl_revision_diff_preview["backend"]["method"] == "GET"
    assert real_dsl_revision_diff_preview["backend"]["path"] == "/api/review/real-dsl-revision-diff-preview"
    assert real_dsl_revision_diff_preview["inputSchema"]["required"] == []
    assert real_dsl_revision_diff_preview["outputContract"]["dataPath"] == "data.realDslRevisionDiffPreview"
    assert real_dsl_revision_diff_preview["outputContract"]["component"] == "RealDslRevisionDiffPreview"
    assert real_dsl_revision_diff_preview["safety"]["readOnly"] is True
    assert real_dsl_revision_diff_preview["safety"]["newLlmRequestSent"] is False
    assert real_dsl_revision_diff_preview["safety"]["realPublishAllowed"] is False
    real_dsl_revision_decision = next(tool for tool in tools if tool["name"] == "create_real_dsl_revision_decision")
    assert real_dsl_revision_decision["backend"]["method"] == "POST"
    assert real_dsl_revision_decision["backend"]["path"] == "/api/review/real-dsl-revision-decision"
    assert real_dsl_revision_decision["inputSchema"]["required"] == ["suggestionId", "reviewer", "decision"]
    assert real_dsl_revision_decision["inputSchema"]["properties"]["decision"]["enum"] == [
        "approve",
        "reject",
        "request-change",
    ]
    assert real_dsl_revision_decision["outputContract"]["dataPath"] == "data.realDslRevisionDecision"
    assert real_dsl_revision_decision["outputContract"]["component"] == "RealDslRevisionDecision"
    assert real_dsl_revision_decision["safety"]["sourceDslModified"] is False
    assert real_dsl_revision_decision["safety"]["realPublishAllowed"] is False
    promotion = next(tool for tool in tools if tool["name"] == "promote_real_dsl_revision_candidate")
    assert promotion["backend"]["method"] == "POST"
    assert promotion["backend"]["path"] == "/api/review/real-dsl-revision-promote"
    assert promotion["reviewRequired"] is True
    assert promotion["inputSchema"]["required"] == ["reviewer"]
    assert promotion["outputContract"]["dataPath"] == "data.realDslRevisionPromotion"
    assert promotion["outputContract"]["component"] == "RealDslRevisionPromotion"
    assert promotion["safety"]["sourceDslModified"] is False
    assert promotion["safety"]["realPublishAllowed"] is False
    enqueue = next(tool for tool in tools if tool["name"] == "enqueue_real_dsl_revision_candidate_review")
    assert enqueue["backend"]["method"] == "POST"
    assert enqueue["backend"]["path"] == "/api/review/real-dsl-revision-enqueue"
    assert enqueue["reviewRequired"] is True
    assert enqueue["inputSchema"]["required"] == ["reviewer"]
    assert enqueue["outputContract"]["dataPath"] == "data.promotionReviewQueueItem"
    assert enqueue["outputContract"]["component"] == "RealDslRevisionPromotionReviewQueueItem"
    assert enqueue["safety"]["taskCreated"] is True
    assert enqueue["safety"]["realPublishAllowed"] is False


def test_mcp_mock_tool_default_profile_blocks_paused_tools(tmp_path):
    try:
        invoke_mcp_tool(
            "agent_internal_publish_request",
            {"id": "agent_entity_demo"},
            store_path=tmp_path / "store.json",
            root=ROOT,
            trace_id="trace_mcp_default_profile_blocks_import_send",
        )
    except McpToolError as exc:
        assert exc.code == "MCP_TOOL_NOT_IN_PROFILE"
        assert exc.errors == [
            {"field": "tool", "reason": "agent_internal_publish_request"},
            {"field": "profile", "reason": "local-core-mvp"},
        ]
    else:
        raise AssertionError("expected MCP_TOOL_NOT_IN_PROFILE")


def test_mcp_mock_tool_invokes_backend_mock_and_returns_json(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = invoke_mcp_tool(
        "analyze_material",
        {"input": str(source)},
        store_path=tmp_path / "store.json",
        root=ROOT,
    )

    assert payload["success"] is True
    assert payload["data"]["analysis"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["analysis"]["unknownShellExecuted"] is False
    assert payload["data"]["mcpTool"]["name"] == "analyze_material"
    assert payload["data"]["mcpTool"]["realMcpServerStarted"] is False
    assert payload["data"]["mcpTool"]["realAgentStarted"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "analyze_material"
    assert record["status"] == "SUCCESS"
    assert record["backendCalled"] is True
    assert record["argumentKeys"] == ["input"]
    assert record["realMcpServerStarted"] is False


def test_mcp_mock_tool_gets_real_llm_runtime_config(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-never-return")
    monkeypatch.setenv("OPENAI_MODEL", "mimo-v2.5-pro")

    payload = invoke_mcp_tool(
        "get_real_llm_runtime_config",
        {},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_llm_runtime_config",
    )

    assert payload["success"] is True
    config = payload["data"]["realLlmRuntimeConfig"]
    assert config["component"] == "RealLlmRuntimeConfigSummary"
    assert config["env"]["OPENAI_API_KEY"]["present"] is True
    assert config["env"]["OPENAI_API_KEY"]["valueReturned"] is False
    assert "value" not in config["env"]["OPENAI_API_KEY"]
    assert config["readyForRealLlmCommand"] is True
    assert config["safety"]["requestSent"] is False
    assert config["safety"]["realLlmCalled"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_real_llm_runtime_config"
    assert "sk-test-never-return" not in str(payload)
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_real_llm_runtime_config"
    assert record["backendCalled"] is True
    assert record["realAgentStarted"] is False


def test_mcp_mock_tool_can_query_provider_audit_after_workflow(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    demo = invoke_mcp_tool(
        "workflow_demo",
        {"input": str(source), "reviewer": "teacher_1"},
        store_path=store_path,
        root=ROOT,
    )
    audit = invoke_mcp_tool(
        "list_provider_audit_events",
        {"operation": "generateJson", "traceId": demo["traceId"]},
        store_path=store_path,
        root=ROOT,
    )

    assert demo["success"] is True
    assert demo["data"]["mcpTool"]["name"] == "workflow_demo"
    assert demo["data"]["report"]["providerAdapter"] == "mock_provider_adapter"
    assert audit["success"] is True
    assert audit["data"]["total"] == 4
    assert audit["data"]["mcpTool"]["name"] == "list_provider_audit_events"
    assert {item["detail"]["workflowId"] for item in audit["data"]["items"]} == {"phase1_main_demo"}
    assert all(item["realLlmCalled"] is False for item in audit["data"]["items"])


def test_mcp_mock_tool_gets_review_priority_queue_from_summary(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_lab_for_review_summary",
    )
    invoke_mcp_tool(
        "generate_ppt",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_ppt_for_review_summary",
    )

    payload = invoke_mcp_tool(
        "get_review_task_summary",
        {"status": "WAITING_REVIEW", "limit": 2},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_review_summary",
    )

    assert payload["success"] is True
    summary = payload["data"]["reviewTaskSummary"]
    assert summary["total"] == 2
    provider_signal = summary["providerQualityTaskSignal"]
    assert provider_signal["enabled"] is True
    assert provider_signal["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert provider_signal["taskTotal"] == 2
    assert provider_signal["availableTotal"] == 0
    assert provider_signal["autoApproveAllowed"] is False
    assert provider_signal["batchStateChangeAllowed"] is False
    assert provider_signal["realPublishAllowed"] is False
    priority_queue = summary["reviewPriorityQueue"]
    assert priority_queue["enabled"] is True
    assert priority_queue["summary"]["queueTotal"] == 2
    assert priority_queue["summary"]["providerQualityAvailableTotal"] == 0
    assert priority_queue["summary"]["providerQualityReadyForReviewTotal"] == 0
    assert priority_queue["summary"]["preApproveReviewCheckTaskTotal"] == 0
    assert priority_queue["summary"]["preApproveReviewCheckWarningTotal"] == 0
    assert priority_queue["summary"]["autoApproveAllowed"] is False
    assert priority_queue["summary"]["batchStateChangeAllowed"] is False
    assert {item["reasonCode"] for item in priority_queue["items"]} == {
        "LAB_QUALITY_NEEDS_REVIEW",
        "PPT_SLIDE_PLAN_REVIEW",
    }
    real_demo_queue = summary["realDemoReviewQueue"]
    assert real_demo_queue["component"] == "RealDemoReviewQueue"
    assert real_demo_queue["taskTotal"] == 4
    assert real_demo_queue["waitingReviewTotal"] == 4
    assert real_demo_queue["readonlyEvidenceReportDetailSource"] == "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    assert real_demo_queue["readonlyEvidenceCollectedTotal"] == 2
    assert real_demo_queue["autoApproveAllowed"] is False
    assert real_demo_queue["batchStateChangeAllowed"] is False
    assert real_demo_queue["realPublishAllowed"] is False
    controlled_signal = summary["controlledDockerEvidenceReviewSignal"]
    assert controlled_signal["component"] == "ControlledDockerEvidenceReviewSignal"
    assert controlled_signal["source"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["status"] == "PARTIAL_CONTROLLED_EVIDENCE_COLLECTED"
    assert controlled_signal["coveredCheckIds"] == ["check_q1", "check_q4"]
    assert controlled_signal["coveredCheckTypes"] == ["stdout_contains", "pytest"]
    assert controlled_signal["earnedScore"] == 40
    assert controlled_signal["totalControlledScore"] == 40
    assert controlled_signal["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert controlled_signal["remainingCheckTypes"] == ["notebook_cell"]
    assert controlled_signal["remainingStatus"] == "STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW"
    assert controlled_signal["notebookEvidenceReviewPlanSource"] == "reviewTaskSummary.notebookEvidenceReviewPlan"
    assert controlled_signal["remainingReviewPlanStatus"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert controlled_signal["recommendedAction"] == "review_container_and_static_notebook_evidence_before_approval"
    assert controlled_signal["autoApproveAllowed"] is False
    assert controlled_signal["batchStateChangeAllowed"] is False
    assert controlled_signal["realPublishAllowed"] is False
    notebook_plan = summary["notebookEvidenceReviewPlan"]
    assert notebook_plan["component"] == "NotebookEvidenceReviewPlan"
    assert notebook_plan["status"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert notebook_plan["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert notebook_plan["checkTypes"] == ["notebook_cell"]
    assert notebook_plan["checkTotal"] == 2
    assert notebook_plan["scoreTotal"] == 60
    assert notebook_plan["evidenceStatus"] == "STATIC_NOTEBOOK_EVIDENCE_COLLECTED"
    assert notebook_plan["reviewStrategy"] == "STATIC_NOTEBOOK_JSON_PARSE_REVIEW"
    assert [item["checkId"] for item in notebook_plan["items"]] == ["check_q2", "check_q3"]
    assert notebook_plan["safety"]["notebookKernelStarted"] is False
    assert notebook_plan["safety"]["notebookExecuted"] is False
    assert notebook_plan["safety"]["contestantCodeExecuted"] is False
    assert notebook_plan["safety"]["realPublishAllowed"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_review_task_summary"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_review_task_summary"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review-task-summary"
    assert record["argumentKeys"] == ["limit", "status"]


def test_mcp_mock_tool_gets_review_detail_by_task_id_path(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_lab_for_review_detail",
    )
    task_id = created["data"]["task"]["id"]

    payload = invoke_mcp_tool(
        "get_review_detail",
        {"taskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_review_detail",
    )

    assert payload["success"] is True
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["id"] == task_id
    assert detail["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert detail["reviewPage"]["actionBar"]["requestRevision"]["enabled"] is True
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_review_detail"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_review_detail"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == f"/api/review-tasks/{task_id}"
    assert record["argumentKeys"] == ["taskId"]


def test_mcp_mock_tool_gets_real_dsl_review_preview(tmp_path):
    payload = invoke_mcp_tool(
        "get_real_dsl_review_preview",
        {},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_review_preview",
    )

    assert payload["success"] is True
    preview = payload["data"]["realDslReviewPreview"]
    assert preview["component"] == "RealDslReviewPreview"
    assert preview["summary"]["labStepTotal"] == len(preview["labReview"]["steps"])
    assert preview["summary"]["examQuestionTotal"] == len(preview["examReview"]["candidateQuestions"])
    assert preview["summary"]["gradingPlanTotal"] == len(preview["gradingReview"]["assessmentPlan"])
    assert preview["summary"]["pptSlideTotal"] == len(preview["pptReview"]["slides"])
    assert preview["summary"]["qualityIssueTotal"] == len(preview["reviewIssues"])
    assert preview["summary"]["revisionSuggestionTotal"] == len(preview["revisionSuggestions"])
    assert preview["qualitySignals"]["summary"]["manualReviewRequired"] is True
    assert preview["qualitySignals"]["summary"]["autoApproveAllowed"] is False
    assert preview["qualitySignals"]["summary"]["realPublishAllowed"] is False
    assert preview["revisionSuggestions"]
    assert preview["examReview"]["candidateSafety"]["answerVisibleToCandidate"] is False
    assert preview["examReview"]["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    assert preview["safety"]["teacherOnlyGradingRefVisibleInReview"] is True
    assert payload["data"]["safety"]["newLlmRequestSent"] is False
    assert payload["data"]["safety"]["secretsRead"] is False
    assert payload["data"]["safety"]["networkAccess"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_real_dsl_review_preview"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_real_dsl_review_preview"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review/real-dsl-preview"
    assert record["argumentKeys"] == []


def test_mcp_mock_tool_real_dsl_review_preview_records_backend_failure(tmp_path):
    payload = invoke_mcp_tool(
        "get_real_dsl_review_preview",
        {"lab": str(tmp_path / "missing-lab.json")},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_review_preview_failure",
    )

    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "lab"
    record = payload["mcpToolCallRecord"]
    assert record["toolName"] == "get_real_dsl_review_preview"
    assert record["status"] == "FAILED"
    assert record["backendCalled"] is True
    assert record["errorCode"] == "VALIDATION_ERROR"
    assert record["errorField"] == "lab"
    assert record["argumentKeys"] == ["lab"]


def test_mcp_mock_tool_creates_real_dsl_revision_draft(tmp_path):
    output = tmp_path / "mcp-lab-revision.json"
    report_output = tmp_path / "mcp-lab-revision-report.json"

    payload = invoke_mcp_tool(
        "create_real_dsl_revision_draft",
        {
            "kind": "lab",
            "source": "examples/output/real-llm-lab.json",
            "reviewer": "teacher_1",
            "comment": "请补充验收说明，并保持人工审核。",
            "targetSections": ["steps"],
            "requestedChanges": ["补充验收说明"],
            "output": str(output),
            "reportOutput": str(report_output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision",
        profile="all",
    )

    assert payload["success"] is True
    assert output.exists()
    assert report_output.exists()
    draft = payload["data"]["realDslRevisionDraft"]
    assert draft["component"] == "RealDslRevisionDraft"
    assert draft["kind"] == "lab"
    assert draft["revisedStatus"] == "WAITING_REVIEW"
    assert draft["schemaValidated"] is True
    assert draft["safety"]["realLlmCalled"] is False
    assert draft["safety"]["newLlmRequestSent"] is False
    assert draft["safety"]["secretsRead"] is False
    assert draft["safety"]["networkAccess"] is False
    assert draft["safety"]["realPublishAllowed"] is False
    assert payload["data"]["mcpTool"]["name"] == "create_real_dsl_revision_draft"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "create_real_dsl_revision_draft"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review/real-dsl-revision"
    assert record["argumentKeys"] == [
        "comment",
        "kind",
        "output",
        "reportOutput",
        "requestedChanges",
        "reviewer",
        "source",
        "targetSections",
    ]


def test_mcp_mock_tool_creates_real_dsl_revision_batch_from_preview(tmp_path):
    report_output = tmp_path / "mcp-revision-batch-report.json"

    payload = invoke_mcp_tool(
        "create_real_dsl_revision_batch_from_preview",
        {
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_batch",
        profile="all",
    )

    assert payload["success"] is True
    assert report_output.exists()
    batch = payload["data"]["realDslRevisionBatch"]
    assert batch["component"] == "RealDslRevisionBatch"
    assert batch["draftTotal"] == 3
    assert batch["schemaValidatedTotal"] == 3
    assert batch["allDraftsWaitingReview"] is True
    assert batch["safety"]["realLlmCalled"] is False
    assert batch["safety"]["newLlmRequestSent"] is False
    assert batch["safety"]["realPublishAllowed"] is False
    assert payload["data"]["mcpTool"]["name"] == "create_real_dsl_revision_batch_from_preview"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "create_real_dsl_revision_batch_from_preview"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review/real-dsl-revision-batch"
    assert record["argumentKeys"] == ["outputDir", "preview", "reportOutput", "reviewer"]


def test_mcp_mock_tool_gets_real_dsl_revision_diff_preview(tmp_path):
    report_output = tmp_path / "mcp-revision-batch-report.json"
    batch_payload = invoke_mcp_tool(
        "create_real_dsl_revision_batch_from_preview",
        {
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_batch_for_diff",
        profile="all",
    )
    assert batch_payload["success"] is True

    payload = invoke_mcp_tool(
        "get_real_dsl_revision_diff_preview",
        {"batchReport": str(report_output)},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_diff",
        profile="all",
    )

    assert payload["success"] is True
    preview = payload["data"]["realDslRevisionDiffPreview"]
    assert preview["component"] == "RealDslRevisionDiffPreview"
    assert preview["summary"]["draftTotal"] == 3
    assert preview["summary"]["allDraftsWaitingReview"] is True
    assert preview["safety"]["newLlmRequestSent"] is False
    assert preview["safety"]["realPublishAllowed"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_real_dsl_revision_diff_preview"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_real_dsl_revision_diff_preview"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review/real-dsl-revision-diff-preview"
    assert record["argumentKeys"] == ["batchReport"]


def test_mcp_mock_tool_creates_real_dsl_revision_decision(tmp_path):
    report_output = tmp_path / "mcp-revision-batch-report.json"
    diff_output = tmp_path / "mcp-revision-diff-preview.json"
    decision_output = tmp_path / "mcp-revision-decision.json"
    batch_payload = invoke_mcp_tool(
        "create_real_dsl_revision_batch_from_preview",
        {
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_batch_for_decision",
        profile="all",
    )
    assert batch_payload["success"] is True
    diff_payload = invoke_mcp_tool(
        "get_real_dsl_revision_diff_preview",
        {"batchReport": str(report_output), "output": str(diff_output)},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_diff_for_decision",
        profile="all",
    )
    assert diff_payload["success"] is True

    payload = invoke_mcp_tool(
        "create_real_dsl_revision_decision",
        {
            "diffPreview": str(diff_output),
            "suggestionId": "revise_lab_objective_depth",
            "reviewer": "teacher_1",
            "decision": "approve",
            "reason": "人工确认该修订可进入后续手动合并。",
            "output": str(decision_output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_decision",
        profile="all",
    )

    assert payload["success"] is True
    assert decision_output.exists()
    decision = payload["data"]["realDslRevisionDecision"]
    assert decision["component"] == "RealDslRevisionDecision"
    assert decision["decisionStatus"] == "REVISION_APPROVED_FOR_MANUAL_MERGE"
    assert decision["safety"]["sourceDslModified"] is False
    assert decision["safety"]["realPublishAllowed"] is False
    assert payload["data"]["mcpTool"]["name"] == "create_real_dsl_revision_decision"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "create_real_dsl_revision_decision"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review/real-dsl-revision-decision"
    assert record["argumentKeys"] == ["decision", "diffPreview", "output", "reason", "reviewer", "suggestionId"]


def test_mcp_mock_tool_promotes_real_dsl_revision_candidate(tmp_path):
    report_output = tmp_path / "mcp-revision-batch-report.json"
    diff_output = tmp_path / "mcp-revision-diff-preview.json"
    decision_output = tmp_path / "mcp-revision-decision.json"
    promoted_output = tmp_path / "mcp-revision-promoted.json"
    promotion_report = tmp_path / "mcp-revision-promotion-report.json"
    assert invoke_mcp_tool(
        "create_real_dsl_revision_batch_from_preview",
        {
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_batch_for_promotion",
        profile="all",
    )["success"] is True
    assert invoke_mcp_tool(
        "get_real_dsl_revision_diff_preview",
        {"batchReport": str(report_output), "output": str(diff_output)},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_diff_for_promotion",
        profile="all",
    )["success"] is True
    assert invoke_mcp_tool(
        "create_real_dsl_revision_decision",
        {
            "diffPreview": str(diff_output),
            "suggestionId": "revise_lab_objective_depth",
            "reviewer": "teacher_1",
            "decision": "approve",
            "output": str(decision_output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_decision_for_promotion",
        profile="all",
    )["success"] is True

    payload = invoke_mcp_tool(
        "promote_real_dsl_revision_candidate",
        {
            "decisionReport": str(decision_output),
            "reviewer": "teacher_2",
            "output": str(promoted_output),
            "reportOutput": str(promotion_report),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_promotion",
        profile="all",
    )

    assert payload["success"] is True
    assert promoted_output.exists()
    assert promotion_report.exists()
    promotion = payload["data"]["realDslRevisionPromotion"]
    assert promotion["component"] == "RealDslRevisionPromotion"
    assert promotion["promotedStatus"] == "WAITING_REVIEW"
    assert promotion["schemaValidated"] is True
    assert promotion["safety"]["sourceDslModified"] is False
    assert promotion["safety"]["newLlmRequestSent"] is False
    assert promotion["safety"]["realPublishAllowed"] is False
    assert payload["data"]["mcpTool"]["name"] == "promote_real_dsl_revision_candidate"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "promote_real_dsl_revision_candidate"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review/real-dsl-revision-promote"
    assert record["argumentKeys"] == ["decisionReport", "output", "reportOutput", "reviewer"]


def test_mcp_mock_tool_enqueues_real_dsl_revision_candidate_review(tmp_path):
    store_path = tmp_path / "store.json"
    report_output = tmp_path / "mcp-revision-batch-report.json"
    diff_output = tmp_path / "mcp-revision-diff-preview.json"
    decision_output = tmp_path / "mcp-revision-decision.json"
    promoted_output = tmp_path / "mcp-revision-promoted.json"
    promotion_report = tmp_path / "mcp-revision-promotion-report.json"
    assert invoke_mcp_tool(
        "create_real_dsl_revision_batch_from_preview",
        {
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_batch_for_enqueue",
        profile="all",
    )["success"] is True
    assert invoke_mcp_tool(
        "get_real_dsl_revision_diff_preview",
        {"batchReport": str(report_output), "output": str(diff_output)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_diff_for_enqueue",
        profile="all",
    )["success"] is True
    assert invoke_mcp_tool(
        "create_real_dsl_revision_decision",
        {
            "diffPreview": str(diff_output),
            "suggestionId": "revise_lab_objective_depth",
            "reviewer": "teacher_1",
            "decision": "approve",
            "output": str(decision_output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_decision_for_enqueue",
        profile="all",
    )["success"] is True
    assert invoke_mcp_tool(
        "promote_real_dsl_revision_candidate",
        {
            "decisionReport": str(decision_output),
            "reviewer": "teacher_2",
            "output": str(promoted_output),
            "reportOutput": str(promotion_report),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_promotion_for_enqueue",
        profile="all",
    )["success"] is True

    payload = invoke_mcp_tool(
        "enqueue_real_dsl_revision_candidate_review",
        {"promotionReport": str(promotion_report), "reviewer": "teacher_3"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_real_dsl_revision_enqueue",
        profile="all",
    )

    assert payload["success"] is True
    queue_item = payload["data"]["promotionReviewQueueItem"]
    assert queue_item["component"] == "RealDslRevisionPromotionReviewQueueItem"
    assert queue_item["taskStatus"] == "WAITING_REVIEW"
    assert queue_item["artifactKind"] == "LAB_DSL"
    assert queue_item["safety"]["newLlmRequestSent"] is False
    assert queue_item["safety"]["realPublishAllowed"] is False
    assert payload["data"]["reviewDetail"]["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert payload["data"]["mcpTool"]["name"] == "enqueue_real_dsl_revision_candidate_review"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "enqueue_real_dsl_revision_candidate_review"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/review/real-dsl-revision-enqueue"
    assert record["argumentKeys"] == ["promotionReport", "reviewer"]


def test_mcp_mock_tool_real_dsl_revision_requires_comment(tmp_path):
    store_path = tmp_path / "store.json"

    try:
        invoke_mcp_tool(
            "create_real_dsl_revision_draft",
            {
                "kind": "lab",
                "reviewer": "teacher_1",
            },
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_real_dsl_revision_missing_comment",
            profile="all",
        )
    except McpToolError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "comment"
    else:
        raise AssertionError("expected McpToolError")

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(tool_name="create_real_dsl_revision_draft")
    assert len(records) == 1
    assert records[0].status.value == "FAILED"
    assert records[0].backendCalled is False
    assert records[0].errorCode == "VALIDATION_ERROR"
    assert records[0].errorField == "comment"


def test_mcp_mock_tool_real_dsl_revision_rejects_invalid_boolean_confirmation(tmp_path):
    store_path = tmp_path / "store.json"

    try:
        invoke_mcp_tool(
            "create_real_dsl_revision_draft",
            {
                "kind": "lab",
                "reviewer": "teacher_1",
                "comment": "补充说明",
                "providerMode": "real-llm",
                "explicitRealCallOptIn": "true",
            },
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_real_dsl_revision_bad_boolean",
            profile="all",
        )
    except McpToolError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "explicitRealCallOptIn"
    else:
        raise AssertionError("expected McpToolError")

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(tool_name="create_real_dsl_revision_draft")
    assert len(records) == 1
    assert records[0].backendCalled is False
    assert records[0].errorCode == "VALIDATION_ERROR"
    assert records[0].errorField == "explicitRealCallOptIn"


def test_mcp_mock_tool_review_summary_includes_manual_checklist_summary(tmp_path):
    store_path = tmp_path / "store.json"
    handle_request(
        "POST",
        "/api/phase2/workflows/grading-generation/run",
        store_path=store_path,
        body={
            "exam": "templates/exam/examples/notebook-fill-blank.yaml",
            "reviewer": "teacher_1",
        },
    )

    payload = invoke_mcp_tool(
        "get_review_task_summary",
        {"taskType": "GRADING_GENERATION"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_grading_review_summary",
    )

    assert payload["success"] is True
    priority_queue = payload["data"]["reviewTaskSummary"]["reviewPriorityQueue"]
    assert priority_queue["summary"]["manualReviewChecklistTaskTotal"] == 1
    assert priority_queue["summary"]["manualReviewChecklistNeedsHumanReviewTotal"] == 5
    item = priority_queue["items"][0]
    assert item["priority"] == "URGENT"
    assert item["providerQualitySummary"]["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert item["providerQualitySummary"]["available"] is False
    assert item["providerQualitySummary"]["autoApproveAllowed"] is False
    assert item["providerQualitySummary"]["realPublishAllowed"] is False
    assert item["manualReviewChecklistSummary"]["enabled"] is True
    assert item["manualReviewChecklistSummary"]["needsHumanReviewTotal"] == 5
    assert item["manualReviewChecklistSummary"]["operatorDecision"]["autoApproveAllowed"] is False
    assert item["manualReviewChecklistSummary"]["operatorDecision"]["batchStateChangeAllowed"] is False
    assert item["preApproveReviewCheck"]["applicable"] is True
    assert item["preApproveReviewCheck"]["status"] == "APPROVE_ALLOWED_WITH_WARNINGS"
    assert item["preApproveReviewCheck"]["summary"]["evidenceReady"] is False
    assert item["preApproveReviewCheck"]["summary"]["reviewDecisionNoteRecorded"] is False
    assert item["preApproveReviewCheck"]["summary"]["approveReadyDecision"] is False
    assert item["preApproveReviewCheck"]["summary"]["warningTotal"] == 2
    precheck_signal = payload["data"]["reviewTaskSummary"]["preApproveReviewCheckSignal"]
    assert precheck_signal["component"] == "PreApproveReviewCheckSignal"
    assert precheck_signal["applicableTotal"] == 1
    assert precheck_signal["approveAllowedWithWarningsTotal"] == 1
    assert precheck_signal["warningTotal"] == 2
    assert precheck_signal["autoApproveAllowed"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_review_task_summary"
    assert payload["data"]["mcpToolCallRecord"]["argumentKeys"] == ["taskType"]


def test_mcp_mock_tool_requests_revision_and_regenerates_mock_task(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_revision_source",
    )
    source_task_id = created["data"]["task"]["id"]

    revision = invoke_mcp_tool(
        "request_review_revision",
        {
            "taskId": source_task_id,
            "reviewer": "teacher_1",
            "comment": "补充步骤截图验收标准。",
            "priority": "HIGH",
            "targetSections": ["steps"],
            "requestedChanges": ["增加截图验收说明"],
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_request_revision",
        profile="all",
    )
    revision_request_id = revision["data"]["revisionRequest"]["id"]
    output_path = tmp_path / "mcp-lab-revision.json"

    regeneration = invoke_mcp_tool(
        "regenerate_from_revision_mock",
        {
            "taskId": source_task_id,
            "reviewer": "teacher_1",
            "revisionRequestId": revision_request_id,
            "output": str(output_path),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_regenerate_revision",
        profile="all",
    )

    assert revision["success"] is True
    assert revision["data"]["revisionRequest"]["taskStatusChanged"] is False
    assert revision["data"]["revisionRequest"]["newLlmRequestSent"] is False
    assert revision["data"]["operationAuditEvent"]["action"] == "REVIEW_REVISION_REQUEST"
    assert revision["data"]["mcpTool"]["name"] == "request_review_revision"
    assert revision["data"]["mcpToolCallRecord"]["toolName"] == "request_review_revision"
    assert revision["data"]["mcpToolCallRecord"]["argumentKeys"] == [
        "comment",
        "priority",
        "requestedChanges",
        "reviewer",
        "targetSections",
        "taskId",
    ]
    assert regeneration["success"] is True
    mock_regeneration = regeneration["data"]["mockRegeneration"]
    assert mock_regeneration["sourceTask"]["id"] == source_task_id
    assert mock_regeneration["sourceTask"]["status"] == "WAITING_REVIEW"
    assert mock_regeneration["newTask"]["status"] == "WAITING_REVIEW"
    assert mock_regeneration["newTask"]["taskType"] == "LAB_GENERATION_REVISION"
    assert mock_regeneration["artifact"]["metadata"]["sourceRevisionRequestId"] == revision_request_id
    assert mock_regeneration["artifact"]["metadata"]["contentQualitySummary"]["readyForImportPreview"] is True
    assert mock_regeneration["artifact"]["metadata"]["workflowContentQualitySummary"]["requiresRevisionBeforeImportPreview"] is False
    assert mock_regeneration["workflowRun"]["workflowId"] == "review_mock_regeneration"
    assert mock_regeneration["operationAuditEvent"]["action"] == "REVIEW_MOCK_REGENERATE"
    assert mock_regeneration["safety"]["newLlmRequestSent"] is False
    assert regeneration["data"]["mcpTool"]["name"] == "regenerate_from_revision_mock"
    assert regeneration["data"]["mcpToolCallRecord"]["reviewRequired"] is True
    assert output_path.exists()


def test_mcp_mock_tool_call_records_can_be_queried(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    call = invoke_mcp_tool(
        "analyze_material",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_success",
    )
    audit = invoke_mcp_tool(
        "list_mcp_tool_call_records",
        {"toolName": "analyze_material", "traceId": "trace_mcp_success"},
        store_path=store_path,
        root=ROOT,
    )

    assert call["success"] is True
    assert audit["success"] is True
    assert audit["data"]["total"] == 1
    record = audit["data"]["items"][0]
    assert record["toolName"] == "analyze_material"
    assert record["status"] == "SUCCESS"
    assert record["traceId"] == "trace_mcp_success"
    assert record["backendTraceId"].startswith("trace_")
    assert record["realLlmCalled"] is False
    assert record["networkAccess"] is False


def test_mcp_mock_tool_lists_phase2_workflow_registry(tmp_path):
    payload = invoke_mcp_tool(
        "list_workflows",
        {"category": "ppt_generation"},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_registry_list",
    )

    assert payload["success"] is True
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["workflowId"] == "phase2_ppt_generation"
    assert payload["data"]["safety"]["workflowExecuted"] is False
    assert payload["data"]["safety"]["taskCreated"] is False
    assert payload["data"]["safety"]["artifactCreated"] is False
    assert payload["data"]["mcpTool"]["name"] == "list_workflows"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "list_workflows"
    assert record["status"] == "SUCCESS"
    assert record["backendCalled"] is True
    assert record["backendPath"] == "/api/workflow-registry"
    assert record["argumentKeys"] == ["category"]


def test_mcp_mock_tool_gets_phase2_workflow_registry_detail(tmp_path):
    payload = invoke_mcp_tool(
        "get_workflow",
        {"workflowId": "phase2_content_generation"},
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_registry_get",
    )

    assert payload["success"] is True
    assert payload["data"]["workflow"]["workflowId"] == "phase2_content_generation"
    assert payload["data"]["contract"]["workflowId"] == "phase2_content_generation"
    assert payload["data"]["safety"]["workflowExecuted"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_workflow"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_workflow"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/workflow-registry/phase2_content_generation"
    assert record["argumentKeys"] == ["workflowId"]


def test_mcp_mock_tool_creates_high_risk_publish_intent_without_publishing(tmp_path):
    store_path = tmp_path / "store.json"

    payload = invoke_mcp_tool(
        "publish_exam",
        {"examId": "exam_demo", "reason": "运营申请发布", "actor": "operator_1"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_publish_exam",
        profile="all",
    )

    assert payload["success"] is True
    assert payload["data"]["intent"]["type"] == "publish_exam"
    assert payload["data"]["intent"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["intent"]["realPublish"] is False
    assert payload["data"]["intent"]["autoPublishAllowed"] is False
    assert payload["data"]["task"]["taskType"] == "MCP_PUBLISH_EXAM_INTENT"
    assert payload["data"]["mcpTool"]["name"] == "publish_exam"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "publish_exam"
    assert record["status"] == "SUCCESS"
    assert record["riskLevel"] == "high"
    assert record["reviewRequired"] is True
    tasks = JsonTaskStore(store_path).list(status="WAITING_REVIEW", task_type="MCP_PUBLISH_EXAM_INTENT")
    assert len(tasks) == 1


def test_mcp_mock_tool_creates_destroy_environment_intent_without_destroying(tmp_path):
    store_path = tmp_path / "store.json"

    payload = invoke_mcp_tool(
        "destroy_environment",
        {"environmentId": "env_demo", "reason": "清理申请", "actor": "operator_1"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_destroy_env",
        profile="all",
    )

    assert payload["success"] is True
    assert payload["data"]["intent"]["type"] == "destroy_environment"
    assert payload["data"]["intent"]["requiresSecondConfirmation"] is True
    assert payload["data"]["intent"]["environmentDestroyed"] is False
    assert payload["data"]["intent"]["realCloudResourceChanged"] is False
    assert payload["data"]["operationAuditEvent"]["detail"]["requiresSecondConfirmation"] is True
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "destroy_environment"
    assert record["riskLevel"] == "critical"
    assert record["reviewRequired"] is True


def test_mcp_mock_tool_gets_second_confirmation_status_read_only(tmp_path):
    store_path = tmp_path / "store.json"
    created = invoke_mcp_tool(
        "destroy_environment",
        {"environmentId": "env_demo", "reason": "清理申请", "actor": "operator_1"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_destroy_for_second_confirmation",
        profile="all",
    )
    task_id = created["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = invoke_mcp_tool(
        "get_second_confirmation_status",
        {"taskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_second_confirmation_status",
        profile="all",
    )

    assert payload["success"] is True
    status = payload["data"]["secondConfirmationStatus"]
    assert status["mode"] == "MOCK_ONLY"
    assert status["eligible"] is True
    assert status["intent"]["intentType"] == "destroy_environment"
    assert status["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert status["secondConfirmationRequired"] is True
    assert status["secondConfirmationSatisfied"] is False
    assert status["readOnly"] is True
    assert status["confirmationActionAvailable"] is False
    assert status["confirmationEndpointEnabled"] is False
    assert status["executeRealActionAllowed"] is False
    assert status["destroyRealEnvironmentEnabled"] is False
    assert status["realCloudResourceChanged"] is False
    assert status["environmentDestroyed"] is False
    assert "confirmSecondFactor" in status["blockedActions"]
    assert payload["data"]["mcpTool"]["name"] == "get_second_confirmation_status"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_second_confirmation_status"
    assert record["status"] == "SUCCESS"
    assert record["riskLevel"] == "critical"
    assert record["reviewRequired"] is False
    assert record["backendPath"] == f"/api/review-tasks/{task_id}/second-confirmation-status"
    assert record["argumentKeys"] == ["taskId"]


def test_mcp_mock_tool_second_confirmation_status_rejects_publish_intent(tmp_path):
    store_path = tmp_path / "store.json"
    created = invoke_mcp_tool(
        "publish_lab",
        {"labId": "lab_demo", "reason": "运营申请发布", "actor": "operator_1"},
        store_path=store_path,
        root=ROOT,
        profile="all",
    )
    task_id = created["data"]["task"]["id"]

    payload = invoke_mcp_tool(
        "get_second_confirmation_status",
        {"taskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_second_confirmation_status_failed",
        profile="all",
    )

    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    record = payload["mcpToolCallRecord"]
    assert record["toolName"] == "get_second_confirmation_status"
    assert record["status"] == "FAILED"
    assert record["backendCalled"] is True
    assert record["backendPath"] == f"/api/review-tasks/{task_id}/second-confirmation-status"
    assert record["responseCode"] == "VALIDATION_ERROR"


def test_mcp_mock_tool_creates_lab_template_import_preview(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    output = tmp_path / "mcp-lab-template-import-preview.json"

    payload = invoke_mcp_tool(
        "create_lab_template_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(output)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_lab_template_import_preview",
    )

    assert approved["data"]["task"]["status"] == "APPROVED"
    assert payload["success"] is True
    preview = payload["data"]["labTemplateImportPreview"]
    assert preview["component"] == "LabTemplateImportPreview"
    assert preview["sourceTaskStatus"] == "APPROVED"
    assert preview["labTemplateDraft"]["status"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert preview["importPlan"]["databaseWritePlanned"] is False
    assert preview["safety"]["realAgentImport"] is False
    assert preview["safety"]["realPublishAllowed"] is False
    assert output.exists()
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "create_lab_template_import_preview"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/labs/import-preview"
    assert record["argumentKeys"] == ["output", "reviewer", "taskId"]


def test_mcp_mock_tool_creates_lab_template_mock_import(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    blocked = invoke_mcp_tool(
        "create_lab_template_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "blocked.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_lab_template_mock_import_blocked",
    )
    invoke_mcp_tool(
        "create_lab_template_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "preview.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_lab_template_import_preview_before_mock_import",
    )
    output = tmp_path / "mcp-lab-template-mock-import.json"

    payload = invoke_mcp_tool(
        "create_lab_template_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(output)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_lab_template_mock_import",
    )

    assert blocked["success"] is False
    assert blocked["code"] == "VALIDATION_ERROR"
    assert blocked["mcpToolCallRecord"]["status"] == "FAILED"
    assert blocked["mcpToolCallRecord"]["backendPath"] == "/api/labs/mock-import"
    assert payload["success"] is True
    report = payload["data"]["agentEntityMockImport"]
    entity = payload["data"]["agentEntityRecord"]
    assert report["component"] == "LabTemplateMockImport"
    assert report["safety"]["mockStoreWritten"] is True
    assert report["safety"]["databaseWritten"] is False
    assert entity["entityType"] == "lab_template"
    assert entity["status"] == "DRAFT_CREATED"
    assert output.exists()
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "create_lab_template_mock_import"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/labs/mock-import"
    assert record["argumentKeys"] == ["output", "reviewer", "taskId"]


def test_mcp_mock_tool_creates_exam_and_grading_import_previews(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    task_id = generated["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    exam_output = tmp_path / "mcp-exam-question-import-preview.json"
    grading_output = tmp_path / "mcp-grading-rule-import-preview.json"

    exam_payload = invoke_mcp_tool(
        "create_exam_question_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(exam_output)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_exam_question_import_preview",
    )
    grading_payload = invoke_mcp_tool(
        "create_grading_rule_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(grading_output)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_grading_rule_import_preview",
    )

    assert approved["data"]["task"]["status"] == "APPROVED"
    assert exam_payload["success"] is True
    exam_preview = exam_payload["data"]["examQuestionImportPreview"]
    assert exam_preview["component"] == "ExamQuestionImportPreview"
    assert exam_preview["sourceArtifactKind"] == "EXAM_DSL"
    assert exam_preview["agentEntity"] == "exam_question"
    assert exam_preview["examQuestionDraft"]["candidateAnswerVisible"] is False
    assert exam_preview["safety"]["realPublishAllowed"] is False
    assert exam_output.exists()
    exam_record = exam_payload["data"]["mcpToolCallRecord"]
    assert exam_record["toolName"] == "create_exam_question_import_preview"
    assert exam_record["status"] == "SUCCESS"
    assert exam_record["backendPath"] == "/api/exams/import-preview"
    assert grading_payload["success"] is True
    grading_preview = grading_payload["data"]["gradingRuleImportPreview"]
    assert grading_preview["component"] == "GradingRuleImportPreview"
    assert grading_preview["sourceArtifactKind"] == "GRADING_DSL"
    assert grading_preview["agentEntity"] == "grading_rule"
    assert grading_preview["gradingRuleDraft"]["sandboxRequiredBeforeRealExecution"] is True
    assert grading_preview["safety"]["realAgentImport"] is False
    assert grading_output.exists()
    grading_record = grading_payload["data"]["mcpToolCallRecord"]
    assert grading_record["toolName"] == "create_grading_rule_import_preview"
    assert grading_record["status"] == "SUCCESS"
    assert grading_record["backendPath"] == "/api/grading/import-preview"


def test_mcp_mock_tool_creates_exam_and_grading_mock_imports(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    invoke_mcp_tool(
        "create_exam_question_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-preview.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_exam_question_import_preview_before_mock_import",
    )
    invoke_mcp_tool(
        "create_grading_rule_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-preview.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_grading_rule_import_preview_before_mock_import",
    )

    exam_payload = invoke_mcp_tool(
        "create_exam_question_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-import.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_exam_question_mock_import",
    )
    grading_payload = invoke_mcp_tool(
        "create_grading_rule_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-import.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_grading_rule_mock_import",
    )

    assert exam_payload["success"] is True
    assert exam_payload["data"]["agentEntityRecord"]["entityType"] == "exam_question"
    assert exam_payload["data"]["agentEntityRecord"]["payload"]["candidateAnswerVisible"] is False
    assert exam_payload["data"]["mcpToolCallRecord"]["toolName"] == "create_exam_question_mock_import"
    assert exam_payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/exams/mock-import"
    assert grading_payload["success"] is True
    assert grading_payload["data"]["agentEntityRecord"]["entityType"] == "grading_rule"
    assert grading_payload["data"]["agentEntityRecord"]["payload"]["sandboxRequiredBeforeRealExecution"] is True
    assert grading_payload["data"]["mcpToolCallRecord"]["toolName"] == "create_grading_rule_mock_import"
    assert grading_payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/mock-import"

    listed = handle_request("GET", f"/api/platform-entities?sourceTaskId={task_id}", store_path=store_path)
    assert listed["data"]["total"] == 2
    assert {item["entityType"] for item in listed["data"]["items"]} == {"exam_question", "grading_rule"}


def test_mcp_mock_tool_gets_agent_entity_readiness_report(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    invoke_mcp_tool(
        "create_lab_template_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-preview.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_readiness_lab_preview",
    )
    invoke_mcp_tool(
        "create_lab_template_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-import.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_readiness_lab_mock_import",
    )

    payload = invoke_mcp_tool(
        "get_agent_entity_readiness_report",
        {"sourceTaskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_agent_entity_readiness",
    )

    assert payload["success"] is True
    report = payload["data"]["agentEntityReadinessReport"]
    assert report["component"] == "AgentEntityReadinessReport"
    assert report["sourceTaskId"] == task_id
    assert report["summary"]["requiredTotal"] == 4
    assert report["summary"]["readyForManualAgentReviewTotal"] == 1
    assert report["summary"]["missingPreviewTotal"] == 3
    assert report["safety"]["readOnly"] is True
    assert report["safety"]["databaseWritten"] is False
    assert report["safety"]["realAgentImport"] is False
    lab_item = next(item for item in report["items"] if item["agentEntity"] == "lab_template")
    exam_item = next(item for item in report["items"] if item["agentEntity"] == "exam_question")
    assert lab_item["readyForManualAgentReview"] is True
    assert exam_item["blockers"] == ["IMPORT_PREVIEW_MISSING", "MOCK_IMPORT_ENTITY_MISSING"]
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_agent_entity_readiness_report"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/platform-entities/readiness-report"
    assert record["argumentKeys"] == ["sourceTaskId"]


def test_mcp_mock_tools_list_get_and_validate_local_agent_entities(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    invoke_mcp_tool(
        "create_lab_template_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-preview.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_local_entity_preview",
    )
    imported = invoke_mcp_tool(
        "create_lab_template_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-import.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_local_entity_mock_import",
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]

    listed = invoke_mcp_tool(
        "list_agent_entities",
        {"sourceTaskId": task_id, "entityType": "lab_template"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_list_agent_entities",
    )
    fetched = invoke_mcp_tool(
        "get_agent_entity",
        {"id": entity_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_get_agent_entity",
    )
    validated = invoke_mcp_tool(
        "validate_agent_entity_contract",
        {"contractConfig": "examples/input/platform-contract.json", "entityType": "lab_template"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_validate_platform_contract",
    )

    assert listed["success"] is True
    assert listed["data"]["total"] == 1
    assert listed["data"]["items"][0]["id"] == entity_id
    assert listed["data"]["filters"]["sourceTaskId"] == task_id
    assert listed["data"]["filters"]["entityType"] == "lab_template"
    assert listed["data"]["mode"] == "MOCK_ONLY"
    assert listed["data"]["mcpTool"]["name"] == "list_agent_entities"
    assert listed["data"]["mcpToolCallRecord"]["backendPath"] == "/api/platform-entities"
    assert listed["data"]["mcpToolCallRecord"]["argumentKeys"] == ["entityType", "sourceTaskId"]
    assert fetched["success"] is True
    assert fetched["data"]["agentEntityRecord"]["id"] == entity_id
    assert fetched["data"]["agentEntityImportActivity"]["component"] == "AgentEntityImportActivitySummary"
    assert fetched["data"]["databaseWritten"] is False
    assert fetched["data"]["realAgentImport"] is False
    assert fetched["data"]["mcpTool"]["name"] == "get_agent_entity"
    assert fetched["data"]["mcpToolCallRecord"]["backendPath"] == f"/api/platform-entities/{entity_id}"
    assert validated["success"] is True
    validation = validated["data"]["platformApiContractValidation"]
    assert validation["component"] == "AgentApiContractValidation"
    assert validation["valid"] is True
    assert validated["data"]["mode"] == "LOCAL_PLATFORM_API_CONTRACT_VALIDATION"
    assert validated["data"]["requestSent"] is False
    assert validated["data"]["networkAccess"] is False
    assert validated["data"]["secretsRead"] is False
    assert validated["data"]["realAgentImport"] is False
    assert validated["data"]["mcpTool"]["name"] == "validate_agent_entity_contract"
    assert validated["data"]["mcpToolCallRecord"]["backendPath"] == "/api/platform-entities/contract-validate"
    assert validated["data"]["mcpToolCallRecord"]["argumentKeys"] == ["contractConfig", "entityType"]


def test_mcp_mock_tool_gets_core_workflow_readiness(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_core_readiness_source",
    )
    task_id = created["data"]["task"]["id"]

    payload = invoke_mcp_tool(
        "get_core_workflow_readiness",
        {"taskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_core_readiness",
    )

    assert payload["success"] is True
    report = payload["data"]["coreWorkflowReadinessReport"]
    assert report["component"] == "CoreWorkflowReadinessReport"
    assert report["mode"] == "CORE_WORKFLOW_READINESS_READ_ONLY"
    assert report["taskId"] == task_id
    assert report["taskStatus"] == "WAITING_REVIEW"
    assert report["ready"] is False
    assert report["status"] == "CORE_DEMO_NEEDS_ACTION"
    assert report["recommendedNextAction"] == "approve_generated_content_after_manual_review"
    assert report["summary"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert report["blockedSteps"]
    assert report["nextToolRecommendation"]["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"
    assert report["nextToolRecommendation"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert report["nextToolRecommendation"]["actionType"] == "manual_review"
    assert report["nextToolRecommendation"]["toolAvailable"] is False
    assert report["nextToolRecommendation"]["autoExecuteAllowed"] is False
    assert report["nextToolRecommendation"]["autoApproveAllowed"] is False
    assert report["platformImportPreviewActionSummary"]["component"] == "PlatformImportPreviewActionSummary"
    assert report["platformImportPreviewActionSummary"]["pendingPreviewTotal"] == 1
    assert report["platformImportPreviewActionSummary"]["pendingPlatformEntities"] == ["lab_template"]
    assert "lab import-preview" in report["platformImportPreviewActionSummary"]["pendingCliCommands"][0]
    assert report["safety"]["readOnly"] is True
    assert report["safety"]["autoApproveAllowed"] is False
    assert report["safety"]["autoPublishAllowed"] is False
    assert report["safety"]["realPublish"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_core_workflow_readiness"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_core_workflow_readiness"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == f"/api/review-tasks/{task_id}/core-readiness"
    assert record["argumentKeys"] == ["taskId"]


def test_mcp_mock_tool_creates_agent_entity_import_dry_run(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    invoke_mcp_tool(
        "create_lab_template_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-preview.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_import_dry_run_preview",
    )
    imported = invoke_mcp_tool(
        "create_lab_template_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-import.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_import_dry_run_mock_import",
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    output = tmp_path / "mcp-platform-entity-import-dry-run.json"

    payload = invoke_mcp_tool(
        "create_agent_entity_import_dry_run",
        {"id": entity_id, "reviewer": "teacher_3", "output": str(output)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_agent_entity_import_dry_run",
    )

    assert payload["success"] is True
    assert output.exists()
    dry_run = payload["data"]["agentEntityImportDryRun"]
    assert dry_run["component"] == "AgentEntityImportDryRun"
    assert dry_run["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert dry_run["agentEntityId"] == entity_id
    assert dry_run["entityType"] == "lab_template"
    assert dry_run["targetEndpoint"] == {
        "method": "POST",
        "path": "/api/platform/lab-template/draft-imports",
    }
    assert dry_run["requestPreview"]["idempotencyKey"] == f"dryrun:{entity_id}"
    assert dry_run["validation"]["readyForRealApiImplementation"] is True
    assert dry_run["validation"]["readyForRealApiCall"] is False
    assert dry_run["safety"]["dryRunOnly"] is True
    assert dry_run["safety"]["requestSent"] is False
    assert dry_run["safety"]["networkAccess"] is False
    assert dry_run["safety"]["databaseWritten"] is False
    assert dry_run["safety"]["realAgentImport"] is False
    assert dry_run["safety"]["realPublish"] is False
    assert payload["data"]["artifact"]["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_DRY_RUN"
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "create_agent_entity_import_dry_run"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == f"/api/platform-entities/{entity_id}/import-dry-run"
    assert record["argumentKeys"] == ["id", "output", "reviewer"]


def test_mcp_mock_tool_sends_agent_entity_import_request(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    store_path = tmp_path / "store.json"
    server, thread, base_url = start_recording_platform_server()
    try:
        generated = handle_request(
            "POST",
            "/api/labs/generate",
            store_path=store_path,
            body={"input": "examples/input/demo-source.md"},
        )
        task_id = generated["data"]["task"]["id"]
        handle_request(
            "POST",
            f"/api/ai-tasks/{task_id}/approve",
            store_path=store_path,
            body={"reviewer": "teacher_1"},
        )
        invoke_mcp_tool(
            "create_lab_template_import_preview",
            {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-preview.json")},
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_import_send_preview",
        )
        imported = invoke_mcp_tool(
            "create_lab_template_mock_import",
            {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-import.json")},
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_import_send_mock_import",
        )
        entity_id = imported["data"]["agentEntityRecord"]["id"]
        dry_run = tmp_path / "mcp-platform-entity-import-dry-run.json"
        send_report = tmp_path / "mcp-platform-entity-import-send-report.json"
        invoke_mcp_tool(
            "create_agent_entity_import_dry_run",
            {"id": entity_id, "reviewer": "teacher_3", "output": str(dry_run)},
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_import_send_dry_run",
        )

        payload = invoke_mcp_tool(
            "agent_internal_publish_request",
            {
                "id": entity_id,
                "reviewer": "teacher_4",
                "dryRun": str(dry_run),
                "output": str(send_report),
                "baseUrl": base_url,
                "explicitPlatformCallOptIn": True,
                "confirmDryRunReviewed": True,
                "confirmManualPlatformReview": True,
                "confirmNoAutoPublish": True,
            },
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_agent_entity_import_send",
            profile="all",
        )
        status_report = tmp_path / "mcp-platform-entity-import-status-query.json"
        status_payload = invoke_mcp_tool(
            "query_agent_publish_status",
            {
                "id": entity_id,
                "reviewer": "teacher_5",
                "sendResult": str(send_report),
                "output": str(status_report),
                "explicitPlatformQueryOptIn": True,
            },
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_agent_entity_import_status_query",
            profile="all",
        )
    finally:
        stop_recording_platform_server(server, thread)

    assert payload["success"] is True
    assert send_report.exists()
    post_requests = [item for item in RecordingPlatformImportHandler.requests if item.get("method") != "GET"]
    assert len(post_requests) == 1
    recorded = post_requests[0]
    assert recorded["path"] == "/api/platform/lab-template/draft-imports"
    assert recorded["authorization"] == "Bearer platform-secret-token"
    assert recorded["body"]["entityType"] == "lab_template"
    result = payload["data"]["agentEntityImportSendResult"]
    assert result["component"] == "AgentEntityImportSendResult"
    assert result["mode"] == "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    assert result["agentEntityId"] == entity_id
    assert result["response"]["statusCode"] == 202
    assert result["safety"]["requestSent"] is True
    assert result["safety"]["networkAccess"] is True
    assert result["safety"]["secretValueReturned"] is False
    assert result["safety"]["databaseWrittenByLocalSystem"] is False
    assert result["safety"]["realPublish"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "agent_internal_publish_request"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == f"/api/platform-entities/{entity_id}/import-send"
    assert record["argumentPreview"]["baseUrl"] == base_url
    assert "platform-secret-token" not in json.dumps(payload, ensure_ascii=False)

    entity_payload = handle_request("GET", f"/api/platform-entities/{entity_id}", store_path=store_path)
    activity = entity_payload["data"]["agentEntityImportActivity"]
    assert activity["component"] == "AgentEntityImportActivitySummary"
    assert activity["summary"]["dryRunPrepared"] is True
    assert activity["summary"]["requestSent"] is True
    assert activity["summary"]["latestStatusCode"] == 202
    assert activity["summary"]["secretValueReturned"] is False
    assert activity["summary"]["databaseWrittenByLocalSystem"] is False
    assert activity["summary"]["realPublish"] is False

    assert status_payload["success"] is True
    assert status_report.exists()
    get_requests = [item for item in RecordingPlatformImportHandler.requests if item.get("method") == "GET"]
    assert len(get_requests) == 1
    assert get_requests[0]["path"] == "/api/platform/lab-template/draft-imports/draft_import_mcp_test"
    assert get_requests[0]["authorization"] == "Bearer platform-secret-token"
    status_query = status_payload["data"]["agentEntityImportStatusQuery"]
    assert status_query["component"] == "AgentEntityImportStatusQuery"
    assert status_query["mode"] == "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    assert status_query["agentDraftId"] == "draft_import_mcp_test"
    assert status_query["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_query["suggestedImportResultStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_query["safety"]["requestSent"] is True
    assert status_query["safety"]["mockStoreUpdated"] is False
    assert status_payload["data"]["agentEntityRecord"]["status"] == "DRAFT_CREATED"
    status_mcp_record = status_payload["data"]["mcpToolCallRecord"]
    assert status_mcp_record["toolName"] == "query_agent_publish_status"
    assert status_mcp_record["backendPath"] == f"/api/platform-entities/{entity_id}/import-status"

    result_record = tmp_path / "mcp-platform-entity-import-result-record.json"
    result_payload = invoke_mcp_tool(
        "record_agent_entity_publish_result",
        {
            "id": entity_id,
            "reviewer": "teacher_5",
            "sendResult": str(send_report),
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": str(result_record),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_agent_entity_import_result_record",
        profile="all",
    )
    assert result_payload["success"] is True
    assert result_record.exists()
    record_result = result_payload["data"]["agentEntityImportResultRecord"]
    assert record_result["component"] == "AgentEntityImportResultRecord"
    assert record_result["agentEntityId"] == entity_id
    assert record_result["agentDraftId"] == "draft_import_mcp_test"
    assert record_result["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert record_result["summary"]["acceptedForDraft"] is True
    assert record_result["safety"]["requestSent"] is False
    assert record_result["safety"]["networkAccess"] is False
    assert result_payload["data"]["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    mcp_record = result_payload["data"]["mcpToolCallRecord"]
    assert mcp_record["toolName"] == "record_agent_entity_publish_result"
    assert mcp_record["backendPath"] == f"/api/platform-entities/{entity_id}/import-result"

    entity_payload_after_result = handle_request("GET", f"/api/platform-entities/{entity_id}", store_path=store_path)
    result_activity = entity_payload_after_result["data"]["agentEntityImportActivity"]
    assert result_activity["resultTotal"] == 1
    assert result_activity["summary"]["latestPlatformStatus"] == "ACCEPTED_FOR_DRAFT"

    ready_payload = invoke_mcp_tool(
        "get_agent_entity_readiness_report",
        {"sourceTaskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_agent_entity_readiness_before_signoff",
    )
    ready_report = ready_payload["data"]["agentEntityReadinessReport"]
    ready_item = next(item for item in ready_report["items"] if item["agentEntityId"] == entity_id)
    assert ready_report["summary"]["agentEntitySignoffReadyTotal"] == 1
    assert ready_report["summary"]["agentEntitySignoffRecordedTotal"] == 0
    assert ready_item["signoffState"] == "READY_FOR_PLATFORM_ENTITY_SIGNOFF"
    assert ready_item["readyForAgentEntitySignoff"] is True
    assert ready_item["signoffRecorded"] is False

    signoff_output = tmp_path / "mcp-platform-entity-signoff-record.json"
    signoff_payload = invoke_mcp_tool(
        "record_agent_entity_signoff",
        {
            "id": entity_id,
            "reviewer": "teacher_6",
            "comment": "MCP readiness check should see local signoff record",
            "output": str(signoff_output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_agent_entity_signoff",
        profile="all",
    )
    assert signoff_payload["success"] is True
    assert signoff_output.exists()
    signoff_record = signoff_payload["data"]["agentEntitySignoffRecord"]
    assert signoff_record["component"] == "AgentEntitySignoffRecord"
    assert signoff_record["agentEntityId"] == entity_id
    assert signoff_record["summary"]["signoffRecorded"] is True
    assert signoff_record["safety"]["realPublish"] is False
    assert signoff_payload["data"]["mcpToolCallRecord"]["toolName"] == "record_agent_entity_signoff"
    assert signoff_payload["data"]["mcpToolCallRecord"]["backendPath"] == f"/api/platform-entities/{entity_id}/signoff"

    signed_payload = invoke_mcp_tool(
        "get_agent_entity_readiness_report",
        {"sourceTaskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_agent_entity_readiness_after_signoff",
    )
    signed_report = signed_payload["data"]["agentEntityReadinessReport"]
    signed_item = next(item for item in signed_report["items"] if item["agentEntityId"] == entity_id)
    assert signed_report["summary"]["agentEntitySignoffReadyTotal"] == 0
    assert signed_report["summary"]["agentEntitySignoffRecordedTotal"] == 1
    assert signed_report["summary"]["postSignoffPrePublishReadyTotal"] == 1
    assert signed_item["signoffState"] == "PLATFORM_ENTITY_SIGNOFF_RECORDED"
    assert signed_item["readyForAgentEntitySignoff"] is False
    assert signed_item["signoffRecorded"] is True
    assert signed_item["latestSignoffArtifactId"] == signoff_payload["data"]["artifact"]["id"]
    checklist = signed_item["postSignoffPrePublishChecklist"]
    assert checklist["status"] == "READY_FOR_FINAL_HUMAN_PUBLISH_REVIEW"
    assert checklist["nextRequiredAction"] == "final_human_publish_review_before_any_real_publish"
    assert checklist["entitySpecificReviewFocus"]["component"] == "AgentEntitySpecificPrePublishReviewFocus"
    assert (
        checklist["entitySpecificReviewFocus"]["primaryReviewFocus"]
        == "review_lab_objectives_environment_and_grading_ref_before_publish"
    )
    assert checklist["entitySpecificReviewFocus"]["safety"]["realPublish"] is False
    assert checklist["safety"]["requiresFinalHumanReview"] is True
    assert checklist["safety"]["realPublish"] is False
    assert signed_payload["data"]["mcpToolCallRecord"]["toolName"] == "get_agent_entity_readiness_report"
    assert signed_payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/platform-entities/readiness-report"
    assert "platform-secret-token" not in json.dumps(signed_payload, ensure_ascii=False)

    final_review_output = tmp_path / "mcp-platform-entity-final-review.json"
    final_review_payload = invoke_mcp_tool(
        "record_final_publish_review_decision",
        {
            "id": entity_id,
            "reviewer": "teacher_6",
            "decision": "APPROVED_FOR_PUBLISH_PLANNING",
            "comment": "MCP final review records planning approval only",
            "output": str(final_review_output),
            "confirmNoAutoPublish": True,
            "confirmNoRealPublish": True,
            "confirmFinalHumanReview": True,
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_agent_entity_final_review",
        profile="all",
    )
    assert final_review_payload["success"] is True
    assert final_review_output.exists()
    final_review = final_review_payload["data"]["finalPublishReviewDecision"]
    assert final_review["component"] == "FinalPublishReviewDecision"
    assert final_review["agentEntityId"] == entity_id
    assert final_review["decision"] == "APPROVED_FOR_PUBLISH_PLANNING"
    assert final_review["summary"]["publishExecuted"] is False
    assert final_review["safety"]["realPublish"] is False
    assert final_review_payload["data"]["mcpToolCallRecord"]["toolName"] == "record_final_publish_review_decision"
    assert final_review_payload["data"]["mcpToolCallRecord"]["backendPath"] == (
        f"/api/platform-entities/{entity_id}/final-publish-review-decision"
    )
    assert "platform-secret-token" not in json.dumps(final_review_payload, ensure_ascii=False)


def test_mcp_mock_tool_runs_readonly_grading_evidence(tmp_path):
    output = tmp_path / "readonly-grading-evidence.json"

    payload = invoke_mcp_tool(
        "run_readonly_grading_evidence",
        {
            "grading": "templates/grading/examples/readonly-sandbox.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_readonly_grading_evidence",
    )

    assert payload["success"] is True
    report = payload["data"]["report"]
    assert report["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert report["executionSummary"]["executed"] == 4
    assert report["executionSummary"]["deferred"] == 1
    assert report["score"]["earnedScore"] == 120
    assert report["safety"]["readonlyOnly"] is True
    assert report["safety"]["commandExecuted"] is False
    assert report["safety"]["pytestExecuted"] is False
    assert report["safety"]["notebookExecuted"] is False
    assert report["safety"]["contestantCodeExecuted"] is False
    assert payload["data"]["reportDetail"]["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "READONLY_SANDBOX_RUN"
    assert payload["data"]["mcpToolCallRecord"]["toolName"] == "run_readonly_grading_evidence"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/readonly-evidence"
    assert output.exists()


def test_mcp_mock_tool_runs_controlled_grading_evidence(tmp_path, monkeypatch):
    output = tmp_path / "controlled-grading-evidence.json"
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)

    payload = invoke_mcp_tool(
        "run_controlled_grading_evidence",
        {
            "grading": "templates/grading/examples/controlled-command-sandbox.yaml",
            "submission": "examples/submissions/controlled-command-demo",
            "image": "local-python:demo",
            "output": str(output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_controlled_grading_evidence",
    )

    assert payload["success"] is True
    report = payload["data"]["report"]
    assert report["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert report["runner"]["runtime"] == "docker"
    assert report["runner"]["image"] == "local-python:demo"
    assert report["executionSummary"]["executed"] == 2
    assert report["executionSummary"]["passed"] == 2
    assert report["score"]["earnedScore"] == 100
    assert report["safety"]["readonlyOnly"] is False
    assert report["safety"]["sandboxExecuted"] is True
    assert report["safety"]["commandExecuted"] is True
    assert report["safety"]["pytestExecuted"] is True
    assert report["safety"]["contestantCodeExecuted"] is True
    assert report["safety"]["networkEnabled"] is False
    assert report["safety"]["hostExecutionAllowed"] is False
    assert report["safety"]["realPublish"] is False
    assert payload["data"]["reportDetail"]["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "CONTROLLED_DOCKER_SANDBOX_RUN"
    assert payload["data"]["mcpToolCallRecord"]["toolName"] == "run_controlled_grading_evidence"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/controlled-evidence"
    assert output.exists()


def test_mcp_mock_tool_merges_grading_evidence_reports(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    readonly_output = tmp_path / "readonly-grading-evidence.json"
    controlled_output = tmp_path / "controlled-grading-evidence.json"
    merged_output = tmp_path / "merged-grading-evidence.json"
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)

    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    assert generated["success"] is True
    task_id = generated["data"]["task"]["id"]

    readonly_payload = invoke_mcp_tool(
        "run_readonly_grading_evidence",
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(readonly_output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_merge_readonly",
    )
    assert readonly_payload["success"] is True

    controlled_payload = invoke_mcp_tool(
        "run_controlled_grading_evidence",
        {
            "grading": "templates/grading/examples/controlled-command-sandbox.yaml",
            "submission": "examples/submissions/controlled-command-demo",
            "image": "local-python:demo",
            "output": str(controlled_output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_merge_controlled",
    )
    assert controlled_payload["success"] is True

    payload = invoke_mcp_tool(
        "merge_grading_evidence_reports",
        {
            "reports": [str(readonly_output), str(controlled_output)],
            "output": str(merged_output),
            "taskId": task_id,
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_merge_evidence",
    )

    assert payload["success"] is True
    report = payload["data"]["report"]
    assert report["mode"] == "GRADING_EVIDENCE_MERGE_REPORT"
    assert report["sourceReportTotal"] == 2
    assert report["summary"]["checkTotal"] >= 4
    assert report["summary"]["executed"] >= 2
    assert report["evidenceCoverage"]["controlledDocker"]["checkTotal"] == 2
    assert report["safety"]["mergeExecutedOnlyExistingReports"] is True
    assert payload["data"]["readExistingReportsOnly"] is True
    assert payload["data"]["sandboxExecutedByTool"] is False
    assert payload["data"]["contestantCodeExecutedByTool"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "GRADING_EVIDENCE_MERGE"
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["taskId"] == task_id
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "GRADING_EVIDENCE_MERGE"
    assert payload["data"]["mcpToolCallRecord"]["toolName"] == "merge_grading_evidence_reports"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/evidence-merge"
    assert merged_output.exists()

    detail = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)
    assert detail["success"] is True
    merged = detail["data"]["reviewDetail"]["mergedGradingEvidence"]
    assert merged["visible"] is True
    assert merged["summary"]["latestReportPath"] == str(merged_output)
    assert merged["latestReport"]["artifactPath"] == str(merged_output)
    assert merged["safety"]["mergeExecutedOnlyExistingReports"] is True


def test_mcp_mock_tool_runs_grading_evidence_auto(tmp_path):
    output = tmp_path / "auto-grading-evidence.json"

    payload = invoke_mcp_tool(
        "run_grading_evidence_auto",
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
        },
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_mcp_auto_grading_evidence",
    )

    assert payload["success"] is True
    report = payload["data"]["report"]
    assert report["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert report["sourceMode"] == "EVIDENCE_AUTO"
    assert report["sourceReportTotal"] == 1
    assert report["steps"][0]["id"] == "readonly_static_evidence"
    assert report["steps"][0]["status"] == "COMPLETED"
    assert report["steps"][1]["id"] == "controlled_command_evidence"
    assert report["steps"][1]["status"] == "SKIPPED"
    assert report["evidenceCoverage"]["readonlyStatic"]["checkTotal"] == 4
    assert report["evidenceCoverage"]["controlledDocker"]["checkTotal"] == 0
    assert report["gradingDslCoverageSummary"]["component"] == "GradingDslCoverageSummary"
    assert report["gradingDslCoverageSummary"]["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report["gradingDslCoverageSummary"]["dslCheckTotal"] == 6
    assert report["gradingDslCoverageSummary"]["evidenceReadyTotal"] == 4
    assert report["gradingDslCoverageSummary"]["missingEvidenceTotal"] == 2
    assert set(report["gradingDslCoverageSummary"]["controlledCommandMissingCheckIds"]) == {
        "check_stdout_accuracy",
        "check_pytest",
    }
    assert report["gradingDslCoverageSummary"]["decisionNoteRecommendation"] == "needs-evidence"
    assert report["safety"]["readonlyAlwaysRunsFirst"] is True
    assert report["safety"]["controlledCommandIncluded"] is False
    assert report["safety"]["contestantCodeExecuted"] is False
    assert report["safety"]["commandExecuted"] is False
    assert payload["data"]["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert payload["data"]["sourceMode"] == "EVIDENCE_AUTO"
    assert payload["data"]["operationAuditEvent"]["action"] == "GRADING_EVIDENCE_MERGE"
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "GRADING_EVIDENCE_AUTO"
    assert payload["data"]["mcpToolCallRecord"]["toolName"] == "run_grading_evidence_auto"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/evidence-auto"
    assert output.exists()


def test_mcp_mock_tool_records_review_decision_note(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="MCP review decision note grading task",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_mcp_review_decision_note_setup",
    )
    JsonTaskStore(store_path).save(task)
    task_id = task.id
    output = tmp_path / "review-decision-note.json"

    payload = invoke_mcp_tool(
        "record_review_decision_note",
        {
            "taskId": task_id,
            "reviewer": "teacher_1",
            "decision": "approve-ready",
            "reason": "Evidence has been reviewed by the teacher.",
            "output": str(output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_review_decision_note",
    )

    assert payload["success"] is True
    note = payload["data"]["decisionNote"]
    assert note["component"] == "ReviewDecisionNote"
    assert note["taskId"] == task_id
    assert note["decision"] == "approve-ready"
    assert note["taskStatusBefore"] == note["taskStatusAfter"]
    assert note["statusChanged"] is False
    assert note["safety"]["autoApproveAllowed"] is False
    assert note["safety"]["sandboxExecutedByDecisionNote"] is False
    assert payload["data"]["artifact"]["kind"] == "REVIEW_DECISION_NOTE"
    assert payload["data"]["operationAuditEvent"]["action"] == "REVIEW_DECISION_NOTE_RECORD"
    assert payload["data"]["mcpToolCallRecord"]["toolName"] == "record_review_decision_note"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == f"/api/review-tasks/{task_id}/decision-note"
    assert output.exists()


def test_mcp_mock_tool_gets_grading_result_preview(tmp_path):
    store_path = tmp_path / "store.json"
    report_output = tmp_path / "readonly-grading-evidence.json"
    run_payload = invoke_mcp_tool(
        "run_readonly_grading_evidence",
        {
            "grading": "templates/grading/examples/readonly-sandbox.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_result_preview_report",
    )
    assert run_payload["success"] is True

    payload = invoke_mcp_tool(
        "get_grading_result_preview",
        {"report": str(report_output), "candidateId": "candidate_001", "maxItems": 2},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_result_preview",
    )

    assert payload["success"] is True
    preview = payload["data"]["gradingResultPreview"]
    assert preview["component"] == "GradingResultPreview"
    assert preview["mode"] == "READ_EXISTING_GRADING_REPORT_ONLY"
    assert preview["candidateId"] == "candidate_001"
    assert preview["score"]["earnedScore"] == 120
    assert preview["summary"]["executed"] == 4
    assert preview["evidencePreview"]["totalVisible"] == 2
    assert preview["safety"]["sandboxExecutedByPreview"] is False
    assert preview["safety"]["sourceSandboxExecuted"] is True
    assert preview["safety"]["answerVisibleToCandidate"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_grading_result_preview"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/result-preview"


def test_mcp_mock_tool_gets_grading_evidence_readiness(tmp_path):
    store_path = tmp_path / "store.json"
    report_output = tmp_path / "readonly-grading-evidence.json"
    run_payload = invoke_mcp_tool(
        "run_readonly_grading_evidence",
        {
            "grading": "templates/grading/examples/readonly-sandbox.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_readiness_report",
    )
    assert run_payload["success"] is True

    payload = invoke_mcp_tool(
        "get_grading_evidence_readiness",
        {"report": [str(report_output)]},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_readiness",
    )

    assert payload["success"] is True
    readiness = payload["data"]["gradingEvidenceReadiness"]
    assert readiness["mode"] == "GRADING_EVIDENCE_READINESS"
    assert readiness["summary"]["checkTotal"] == 5
    assert readiness["summary"]["evidenceReadyTotal"] == 4
    assert readiness["summary"]["missingEvidenceTotal"] == 1
    assert readiness["summary"]["readyForApprovalRecommendation"] is False
    assert readiness["safety"]["readExistingReportsOnly"] is True
    assert readiness["safety"]["sandboxExecutedByReadiness"] is False
    assert readiness["safety"]["contestantCodeExecutedByReadiness"] is False
    assert payload["data"]["mcpTool"]["name"] == "get_grading_evidence_readiness"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/evidence-readiness"


def test_mcp_mock_tool_rejects_unknown_and_invalid_arguments(tmp_path):
    try:
        invoke_mcp_tool("missing_tool", {}, store_path=tmp_path / "store.json", root=ROOT)
    except McpToolError as exc:
        assert exc.code == "NOT_FOUND"
        assert exc.errors[0]["field"] == "tool"
    else:
        raise AssertionError("expected McpToolError")

    try:
        store_path = tmp_path / "store.json"
        invoke_mcp_tool("analyze_material", {}, store_path=store_path, root=ROOT, trace_id="trace_mcp_failed")
    except McpToolError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "input"
    else:
        raise AssertionError("expected McpToolError")
    records = JsonTaskStore(store_path).list_mcp_tool_call_records(status="FAILED", trace_id="trace_mcp_failed")
    assert len(records) == 1
    assert records[0].toolName == "analyze_material"
    assert records[0].backendCalled is False
    assert records[0].errorCode == "VALIDATION_ERROR"

    try:
        invoke_mcp_tool("analyze_material", {"input": "demo.md", "extra": True}, store_path=tmp_path / "store.json", root=ROOT)
    except McpToolError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "extra"
    else:
        raise AssertionError("expected McpToolError")

    try:
        store_path = tmp_path / "store.json"
        invoke_mcp_tool("get_workflow", {}, store_path=store_path, root=ROOT, trace_id="trace_mcp_registry_invalid")
    except McpToolError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "workflowId"
    else:
        raise AssertionError("expected McpToolError")
    records = JsonTaskStore(store_path).list_mcp_tool_call_records(status="FAILED", trace_id="trace_mcp_registry_invalid")
    assert len(records) == 1
    assert records[0].toolName == "get_workflow"
    assert records[0].backendCalled is False
    assert records[0].errorCode == "VALIDATION_ERROR"

    try:
        store_path = tmp_path / "store.json"
        invoke_mcp_tool(
            "merge_grading_evidence_reports",
            {"output": str(tmp_path / "merged.json")},
            store_path=store_path,
            root=ROOT,
            trace_id="trace_mcp_merge_invalid",
        )
    except McpToolError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "reports"
    else:
        raise AssertionError("expected McpToolError")
    records = JsonTaskStore(store_path).list_mcp_tool_call_records(status="FAILED", trace_id="trace_mcp_merge_invalid")
    assert len(records) == 1
    assert records[0].toolName == "merge_grading_evidence_reports"
    assert records[0].backendCalled is False
    assert records[0].errorCode == "VALIDATION_ERROR"


def test_mcp_mock_tool_records_backend_failure(tmp_path):
    store_path = tmp_path / "store.json"
    missing = tmp_path / "missing.md"

    payload = invoke_mcp_tool(
        "analyze_material",
        {"input": str(missing)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_backend_failed",
    )

    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    record = payload["mcpToolCallRecord"]
    assert record["toolName"] == "analyze_material"
    assert record["status"] == "FAILED"
    assert record["backendCalled"] is True
    assert record["responseCode"] == "VALIDATION_ERROR"
    assert record["backendTraceId"].startswith("trace_")


def test_mcp_mock_tool_records_workflow_registry_backend_failure(tmp_path):
    store_path = tmp_path / "store.json"

    payload = invoke_mcp_tool(
        "get_workflow",
        {"workflowId": "missing_workflow"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_registry_backend_failed",
    )

    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    record = payload["mcpToolCallRecord"]
    assert record["toolName"] == "get_workflow"
    assert record["status"] == "FAILED"
    assert record["backendCalled"] is True
    assert record["backendPath"] == "/api/workflow-registry/missing_workflow"
    assert record["responseCode"] == "NOT_FOUND"
    assert record["backendTraceId"].startswith("trace_")
