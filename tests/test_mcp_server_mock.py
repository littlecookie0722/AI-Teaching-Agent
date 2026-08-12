from pathlib import Path

from backend.mock_api import handle_request
from cli.store import JsonTaskStore
from mcp_server import call_server_tool, initialize_mcp_server, list_server_tools


ROOT = Path(__file__).resolve().parents[1]


def test_mcp_server_mock_initializes_without_real_server():
    payload = initialize_mcp_server(ROOT)

    assert payload["server"]["id"] == "ai_training_platform_mcp_mock"
    assert payload["server"]["phase"] == "Phase 4"
    assert payload["server"]["mode"] == "MOCK_ONLY"
    assert payload["server"]["transport"] == "local_function_only"
    assert payload["capabilities"]["listTools"] is True
    assert payload["capabilities"]["callTool"] is True
    assert payload["capabilities"]["streaming"] is False
    assert payload["safety"]["realMcpServerStarted"] is False
    assert payload["safety"]["networkListenerStarted"] is False
    assert payload["safety"]["realAgentStarted"] is False


def test_mcp_server_mock_lists_manifest_tools():
    payload = list_server_tools(ROOT)

    assert payload["server"]["phase"] == "Phase 4"
    assert payload["total"] == payload["server"]["toolCount"]
    assert payload["server"]["toolProfile"] == "local-core-mvp"
    assert payload["server"]["manifestToolCount"] > payload["server"]["toolCount"]
    assert payload["toolPolicy"]["realPlatformBackendToolsEnabledByDefault"] is False
    assert payload["toolProfile"]["profile"] == "local-core-mvp"
    assert payload["toolPolicy"]["toolsCallBackendMockOnly"] is True
    assert payload["toolPolicy"]["returnsUnifiedJson"] is True
    names = {tool["name"] for tool in payload["items"]}
    assert "analyze_material" in names
    assert "run_grading_evidence_auto" in names
    assert "create_grading_job" in names
    assert "run_grading_job" in names
    assert "review_grading_record" in names
    assert "list_agent_entities" in names
    assert "get_agent_entity" in names
    assert "validate_agent_entity_contract" in names
    assert "create_agent_entity_import_dry_run" in names
    assert "agent_internal_publish_request" not in names
    assert "query_agent_publish_status" not in names
    assert "publish_lab" not in names
    assert "destroy_environment" not in names


def test_mcp_server_mock_calls_tool_and_records_audit(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = call_server_tool(
        "analyze_material",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_call",
    )

    assert payload["success"] is True
    assert payload["data"]["analysis"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["mcpServer"]["id"] == "ai_training_platform_mcp_mock"
    assert payload["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert payload["data"]["mcpTool"]["realAgentStarted"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "analyze_material"
    assert record["actor"] == "mcp-server-mock"
    assert record["status"] == "SUCCESS"
    records = JsonTaskStore(store_path).list_mcp_tool_call_records(trace_id="trace_mcp_server_call")
    assert len(records) == 1
    assert records[0].toolName == "analyze_material"


def test_mcp_server_mock_calls_review_summary_with_priority_queue(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    call_server_tool(
        "generate_lab_from_source",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_lab_for_review_summary",
    )

    payload = call_server_tool(
        "get_review_task_summary",
        {"status": "WAITING_REVIEW", "taskType": "LAB_GENERATION", "limit": 1},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_review_summary",
    )

    assert payload["success"] is True
    summary = payload["data"]["reviewTaskSummary"]
    assert summary["filters"]["taskType"] == "LAB_GENERATION"
    assert summary["reviewPriorityQueue"]["summary"]["queueTotal"] == 1
    assert summary["reviewPriorityQueue"]["items"][0]["reasonCode"] == "LAB_QUALITY_NEEDS_REVIEW"
    assert summary["reviewPriorityQueue"]["summary"]["batchStateChangeAllowed"] is False
    merged_signal = summary["mergedGradingEvidenceReviewSignal"]
    assert merged_signal["component"] == "MergedGradingEvidenceReviewSignal"
    assert merged_signal["source"] == "reviewDetail.mergedGradingEvidence"
    assert merged_signal["sourceMode"] == "NO_MERGED_EVIDENCE_REPORT"
    assert merged_signal["available"] is False
    assert merged_signal["autoApproveAllowed"] is False
    assert merged_signal["batchStateChangeAllowed"] is False
    assert merged_signal["realPublishAllowed"] is False
    assert payload["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_review_task_summary"
    assert record["actor"] == "mcp-server-mock"
    assert record["status"] == "SUCCESS"


def test_mcp_server_mock_calls_merge_grading_evidence_reports(tmp_path):
    store_path = tmp_path / "store.json"
    readonly = tmp_path / "readonly-report.json"
    controlled = tmp_path / "controlled-report.json"
    output = tmp_path / "merged-report.json"
    readonly.write_text(
        """{
  "id": "readonly_report",
  "mode": "READONLY_REAL_SANDBOX_POC",
  "gradingId": "grading_demo",
  "reportDetail": {
    "checkPlans": [
      {"id": "check_file", "type": "file_exists", "status": "PASSED", "passed": true, "score": 40, "earnedScore": 40}
    ]
  },
  "safety": {
    "sandboxExecuted": true,
    "readonlyOnly": true,
    "contestantCodeExecuted": false,
    "commandExecuted": false,
    "pytestExecuted": false,
    "notebookExecuted": false,
    "networkEnabled": false,
    "hostExecutionAllowed": false,
    "realPublish": false
  }
}
""",
        encoding="utf-8",
    )
    controlled.write_text(
        """{
  "id": "controlled_report",
  "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
  "gradingId": "grading_demo",
  "reportDetail": {
    "checkPlans": [
      {"id": "check_pytest", "type": "pytest", "status": "PASSED", "passed": true, "score": 60, "earnedScore": 60}
    ]
  },
  "safety": {
    "sandboxExecuted": true,
    "readonlyOnly": false,
    "contestantCodeExecuted": true,
    "commandExecuted": true,
    "pytestExecuted": true,
    "notebookExecuted": false,
    "networkEnabled": false,
    "hostExecutionAllowed": false,
    "realPublish": false
  }
}
""",
        encoding="utf-8",
    )

    payload = call_server_tool(
        "merge_grading_evidence_reports",
        {"reports": [str(readonly), str(controlled)], "output": str(output)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_merge_evidence",
    )

    assert payload["success"] is True
    report = payload["data"]["report"]
    assert report["mode"] == "GRADING_EVIDENCE_MERGE_REPORT"
    assert report["summary"]["checkTotal"] == 2
    assert report["summary"]["earnedScore"] == 100
    assert report["evidenceCoverage"]["coverageRatio"] == 1.0
    assert report["safety"]["mergeExecutedOnlyExistingReports"] is True
    assert payload["data"]["sandboxExecutedByTool"] is False
    assert payload["data"]["contestantCodeExecutedByTool"] is False
    assert payload["data"]["mcpServer"]["id"] == "ai_training_platform_mcp_mock"
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert payload["data"]["mcpToolCallRecord"]["toolName"] == "merge_grading_evidence_reports"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/evidence-merge"
    assert output.exists()


def test_mcp_server_mock_calls_grading_evidence_auto(tmp_path):
    store_path = tmp_path / "store.json"
    output = tmp_path / "auto-report.json"

    payload = call_server_tool(
        "run_grading_evidence_auto",
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_auto_evidence",
    )

    assert payload["success"] is True
    report = payload["data"]["report"]
    assert report["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert report["sourceMode"] == "EVIDENCE_AUTO"
    assert report["steps"][0]["id"] == "readonly_static_evidence"
    assert report["steps"][0]["status"] == "COMPLETED"
    assert report["steps"][1]["id"] == "controlled_command_evidence"
    assert report["steps"][1]["status"] == "SKIPPED"
    assert report["safety"]["controlledCommandIncluded"] is False
    assert payload["data"]["mcpServer"]["id"] == "ai_training_platform_mcp_mock"
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert payload["data"]["mcpToolCallRecord"]["toolName"] == "run_grading_evidence_auto"
    assert payload["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/evidence-auto"
    assert output.exists()


def test_mcp_server_mock_calls_grading_job_and_record_tools(tmp_path):
    store_path = tmp_path / "store.json"
    output = tmp_path / "mcp-grading-job-evidence-auto.json"

    created = call_server_tool(
        "create_grading_job",
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
            "submissionId": "submission_mcp_job_001",
            "reviewer": "teacher_1",
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_create_grading_job",
    )

    assert created["success"] is True
    job = created["data"]["gradingJob"]
    assert job["status"] == "QUEUED"
    assert created["data"]["mcpToolCallRecord"]["toolName"] == "create_grading_job"
    assert created["data"]["mcpToolCallRecord"]["backendPath"] == "/api/grading/jobs"

    listed_jobs = call_server_tool(
        "list_grading_jobs",
        {"submissionId": "submission_mcp_job_001"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_list_grading_jobs",
    )
    assert listed_jobs["success"] is True
    assert listed_jobs["data"]["total"] == 1
    assert listed_jobs["data"]["items"][0]["id"] == job["id"]
    assert listed_jobs["data"]["mcpToolCallRecord"]["toolName"] == "list_grading_jobs"

    got_job = call_server_tool(
        "get_grading_job",
        {"id": job["id"]},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_get_grading_job",
    )
    assert got_job["success"] is True
    assert got_job["data"]["gradingJob"]["id"] == job["id"]

    run = call_server_tool(
        "run_grading_job",
        {"id": job["id"], "reviewer": "teacher_1"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_run_grading_job",
    )
    assert run["success"] is True
    assert run["data"]["gradingJob"]["status"] == "WAITING_REVIEW"
    assert run["data"]["gradingRecord"]["status"] in {"WAITING_REVIEW", "NEEDS_EVIDENCE"}
    assert run["data"]["autoApproveAllowed"] is False
    assert run["data"]["mcpToolCallRecord"]["toolName"] == "run_grading_job"
    assert output.exists()

    created_record = call_server_tool(
        "create_grading_record",
        {
            "report": str(output),
            "submissionId": "submission_mcp_record_001",
            "candidateId": "candidate_mcp_001",
            "reviewer": "teacher_1",
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_create_grading_record",
    )
    assert created_record["success"] is True
    record = created_record["data"]["gradingRecord"]
    assert record["submissionId"] == "submission_mcp_record_001"
    assert record["status"] in {"WAITING_REVIEW", "NEEDS_EVIDENCE"}
    assert created_record["data"]["recordCreatesNewExecution"] is False

    listed_records = call_server_tool(
        "list_grading_records",
        {"submissionId": "submission_mcp_record_001"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_list_grading_records",
    )
    assert listed_records["success"] is True
    assert listed_records["data"]["total"] == 1
    assert listed_records["data"]["items"][0]["id"] == record["id"]

    got_record = call_server_tool(
        "get_grading_record",
        {"id": record["id"]},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_get_grading_record",
    )
    assert got_record["success"] is True
    assert got_record["data"]["gradingRecord"]["id"] == record["id"]

    reviewed = call_server_tool(
        "review_grading_record",
        {
            "id": record["id"],
            "reviewer": "teacher_1",
            "decision": "approve-ready",
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_review_grading_record",
    )
    assert reviewed["success"] is True
    assert reviewed["data"]["gradingRecord"]["reviewDecision"] == "approve-ready"
    assert reviewed["data"]["taskStatusChanged"] is False
    assert reviewed["data"]["recordCreatesNewExecution"] is False
    assert reviewed["data"]["mcpToolCallRecord"]["toolName"] == "review_grading_record"
    records = JsonTaskStore(store_path).list_mcp_tool_call_records()
    assert {record.toolName for record in records} >= {
        "create_grading_job",
        "list_grading_jobs",
        "get_grading_job",
        "run_grading_job",
        "create_grading_record",
        "list_grading_records",
        "get_grading_record",
        "review_grading_record",
    }


def test_mcp_server_mock_gets_agent_entity_readiness_report(tmp_path):
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
    call_server_tool(
        "create_lab_template_import_preview",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-preview.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_readiness_preview",
    )
    call_server_tool(
        "create_lab_template_mock_import",
        {"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-import.json")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_readiness_import",
    )

    payload = call_server_tool(
        "get_agent_entity_readiness_report",
        {"sourceTaskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_agent_entity_readiness",
    )

    assert payload["success"] is True
    assert payload["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    report = payload["data"]["agentEntityReadinessReport"]
    assert report["component"] == "AgentEntityReadinessReport"
    assert report["sourceTaskId"] == task_id
    assert report["summary"]["readyForManualAgentReviewTotal"] == 1
    assert report["safety"]["readOnly"] is True
    assert report["safety"]["databaseWritten"] is False
    assert report["safety"]["realAgentImport"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_agent_entity_readiness_report"
    assert record["actor"] == "mcp-server-mock"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == "/api/platform-entities/readiness-report"
    assert record["argumentKeys"] == ["sourceTaskId"]


def test_mcp_server_mock_gets_core_workflow_readiness(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = call_server_tool(
        "generate_lab_from_source",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_core_readiness_source",
    )
    task_id = created["data"]["task"]["id"]

    payload = call_server_tool(
        "get_core_workflow_readiness",
        {"taskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_core_readiness",
    )

    assert payload["success"] is True
    assert payload["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    report = payload["data"]["coreWorkflowReadinessReport"]
    assert report["component"] == "CoreWorkflowReadinessReport"
    assert report["taskId"] == task_id
    assert report["taskStatus"] == "WAITING_REVIEW"
    assert report["recommendedNextAction"] == "approve_generated_content_after_manual_review"
    assert report["summary"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert report["nextToolRecommendation"]["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"
    assert report["nextToolRecommendation"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert report["nextToolRecommendation"]["toolAvailable"] is False
    assert report["nextToolRecommendation"]["autoExecuteAllowed"] is False
    assert report["platformImportPreviewActionSummary"]["pendingPreviewTotal"] == 1
    assert report["platformImportPreviewActionSummary"]["pendingPlatformEntities"] == ["lab_template"]
    assert report["safety"]["readOnly"] is True
    assert report["safety"]["realPublish"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_core_workflow_readiness"
    assert record["actor"] == "mcp-server-mock"
    assert record["status"] == "SUCCESS"
    assert record["backendPath"] == f"/api/review-tasks/{task_id}/core-readiness"
    assert record["argumentKeys"] == ["taskId"]


def test_mcp_server_mock_calls_review_revision_loop_tools(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = call_server_tool(
        "generate_lab_from_source",
        {"input": str(source)},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_revision_source",
    )
    source_task_id = created["data"]["task"]["id"]

    revision = call_server_tool(
        "request_review_revision",
        {
            "taskId": source_task_id,
            "reviewer": "teacher_1",
            "comment": "补充步骤截图验收标准。",
            "priority": "HIGH",
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_revision_request",
        profile="all",
    )
    regeneration = call_server_tool(
        "regenerate_from_revision_mock",
        {
            "taskId": source_task_id,
            "reviewer": "teacher_1",
            "revisionRequestId": revision["data"]["revisionRequest"]["id"],
        },
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_revision_regenerate",
        profile="all",
    )

    assert revision["success"] is True
    assert revision["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert revision["data"]["mcpToolCallRecord"]["actor"] == "mcp-server-mock"
    assert revision["data"]["revisionRequest"]["newLlmRequestSent"] is False
    assert regeneration["success"] is True
    assert regeneration["data"]["mockRegeneration"]["newTask"]["status"] == "WAITING_REVIEW"
    assert regeneration["data"]["mockRegeneration"]["artifact"]["metadata"]["contentQualitySummary"][
        "readyForImportPreview"
    ] is True
    assert regeneration["data"]["mockRegeneration"]["artifact"]["metadata"]["workflowContentQualitySummary"][
        "requiresRevisionBeforeImportPreview"
    ] is False
    assert regeneration["data"]["mockRegeneration"]["safety"]["newLlmRequestSent"] is False
    assert regeneration["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert regeneration["data"]["mcpToolCallRecord"]["toolName"] == "regenerate_from_revision_mock"


def test_mcp_server_mock_calls_high_risk_tool_as_review_intent(tmp_path):
    store_path = tmp_path / "store.json"

    payload = call_server_tool(
        "publish_lab",
        {"labId": "lab_demo", "reason": "运营申请发布"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_publish_lab",
        profile="all",
    )

    assert payload["success"] is True
    assert payload["data"]["intent"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["intent"]["realPublish"] is False
    assert payload["data"]["intent"]["autoPublishAllowed"] is False
    assert payload["data"]["task"]["taskType"] == "MCP_PUBLISH_LAB_INTENT"
    assert payload["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "publish_lab"
    assert record["actor"] == "mcp-server-mock"
    assert record["reviewRequired"] is True


def test_mcp_server_mock_gets_second_confirmation_status_read_only(tmp_path):
    store_path = tmp_path / "store.json"
    created = call_server_tool(
        "destroy_environment",
        {"environmentId": "env_demo", "reason": "清理申请"},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_destroy_env",
        profile="all",
    )
    task_id = created["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = call_server_tool(
        "get_second_confirmation_status",
        {"taskId": task_id},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_mcp_server_second_confirmation",
        profile="all",
    )

    assert payload["success"] is True
    status = payload["data"]["secondConfirmationStatus"]
    assert status["readOnly"] is True
    assert status["secondConfirmationRequired"] is True
    assert status["secondConfirmationSatisfied"] is False
    assert status["confirmationActionAvailable"] is False
    assert status["destroyRealEnvironmentEnabled"] is False
    assert status["environmentDestroyed"] is False
    assert payload["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert payload["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    record = payload["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_second_confirmation_status"
    assert record["actor"] == "mcp-server-mock"
    assert record["reviewRequired"] is False
    assert record["riskLevel"] == "critical"


def test_mcp_server_contract_is_mock_only():
    import json

    with (ROOT / "mcp-server/server.contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    assert contract["phase"] == "Phase 4"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["server"]["transport"] == "local_function_only"
    assert contract["capabilities"]["callTool"] is True
    assert contract["capabilities"]["streaming"] is False
    assert contract["safetyAssertions"]["realMcpServerStarted"] is False
    assert contract["safetyAssertions"]["networkListenerStarted"] is False
    assert contract["toolPolicy"]["auditRequired"] is True
    assert contract["toolPolicy"]["defaultToolProfile"] == "local-core-mvp"
    assert contract["toolPolicy"]["realPlatformBackendToolsEnabledByDefault"] is False
