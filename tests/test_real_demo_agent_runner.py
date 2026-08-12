from pathlib import Path
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.mock_api import handle_request
from agents import (
    RealDemoAgentRunnerError,
    execute_core_next_tool_from_readiness,
    plan_core_next_tool_from_readiness,
    run_real_demo_agent_workflow,
)
from agents.real_demo_runner import _build_agent_entity_readiness_guidance, _build_quality_aware_review_triage
from cli.ai_task import create_waiting_review_task
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.store import JsonTaskStore
from mcp_server import invoke_mcp_tool


ROOT = Path(__file__).resolve().parents[1]


def _create_reviewed_revision_task(
    tmp_path,
    *,
    store_path,
    source_task_id: str,
    reviewer: str = "teacher_1",
) -> str:
    revision = handle_request(
        "POST",
        f"/api/review-tasks/{source_task_id}/revision-request",
        store_path=store_path,
        body={"reviewer": reviewer, "comment": "按内容质量摘要生成修订草稿。", "priority": "HIGH"},
    )
    regeneration = handle_request(
        "POST",
        f"/api/review-tasks/{source_task_id}/regenerate-mock",
        store_path=store_path,
        body={
            "reviewer": reviewer,
            "revisionRequestId": revision["data"]["revisionRequest"]["id"],
            "output": str(tmp_path / f"{source_task_id}-revision.json"),
        },
    )
    revision_task_id = regeneration["data"]["mockRegeneration"]["newTask"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{revision_task_id}/approve",
        store_path=store_path,
        body={"reviewer": reviewer},
    )
    assert revision["success"] is True
    assert regeneration["success"] is True
    assert approved["success"] is True
    assert approved["data"]["task"]["status"] == "APPROVED"
    return revision_task_id


def _attach_ready_grading_evidence(store_path, tmp_path, *, task_id: str) -> None:
    report_path = tmp_path / f"{task_id}-ready-grading-evidence.json"
    report = {
        "id": f"ready_evidence_{task_id}",
        "mode": "GRADING_EVIDENCE_MERGE_REPORT",
        "summary": {
            "checkTotal": 1,
            "executedTotal": 1,
            "passedTotal": 1,
            "earnedScore": 100,
            "totalScore": 100,
            "coverageRatio": 1.0,
        },
        "evidenceCoverage": {"controlledDocker": {"checkTotal": 1}, "readonlyStatic": {"checkTotal": 0}},
        "checks": [
            {
                "id": "check_ready",
                "checkId": "check_ready",
                "type": "pytest",
                "score": 100,
                "earnedScore": 100,
                "passed": True,
                "executed": True,
                "evidenceSourceKind": "controlledDocker",
                "manualReviewRequired": False,
            }
        ],
        "scorePreview": {
            "status": "READY_FOR_HUMAN_SCORE_REVIEW",
            "earnedScore": 100,
            "totalScore": 100,
            "coveredScore": 100,
            "missingScore": 0,
            "coverageRatio": 1.0,
            "passRate": 1.0,
            "readyForDecisionNote": True,
            "missingEvidenceTotal": 0,
            "missingCheckIds": [],
        },
        "safety": {"mergeExecutedOnlyExistingReports": True, "hostExecutionAllowed": False, "networkAllowed": False},
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    store = JsonTaskStore(store_path)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_REPORT,
            path=str(report_path),
            title="Ready Grading Evidence Merge",
            status=ArtifactStatus.COMPLETED,
            trace_id="trace_agent_ready_grading_evidence",
            task_id=task_id,
            source_ref=str(report_path),
            metadata={
                "reportType": "GRADING_EVIDENCE_MERGE",
                "summary": report["summary"],
                "evidenceCoverage": report["evidenceCoverage"],
                "scorePreview": report["scorePreview"],
                "safety": report["safety"],
            },
        )
    )


class RecordingPlatformImportHandler(BaseHTTPRequestHandler):
    requests = []
    quiet = True

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8"))
        self.__class__.requests.append(
            {
                "method": "POST",
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        response = {
            "draftImportId": "draft_import_agent_test",
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
            "draftImportId": "draft_import_agent_test",
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
    import subprocess

    if args[:2] == ["docker", "info"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='"29.5.3"', stderr="")
    if args[:3] == ["docker", "image", "inspect"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:demo", stderr="")
    if "main.py" in args:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="accuracy=0.90\n", stderr="")
    if "pytest" in args:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")
    raise AssertionError(f"unexpected command: {args}")


def test_real_demo_agent_core_next_tool_planner_reads_recommendation_without_calling_tool(tmp_path):
    store_path = tmp_path / "store.json"
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_source",
    )
    task_id = created["data"]["task"]["id"]

    result = plan_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_core_next_tool",
    )

    assert result["component"] == "RealDemoAgentCoreNextToolPlanner"
    assert result["mode"] == "MOCK_AGENT_RUNNER_READ_ONLY_PLAN"
    assert result["summary"]["taskStatus"] == "WAITING_REVIEW"
    assert result["summary"]["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"
    assert result["summary"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert result["summary"]["recommendedToolName"] is None
    assert result["summary"]["manualActionRequired"] is True
    assert result["summary"]["recommendedToolCalled"] is False
    assert [step["id"] for step in result["steps"]] == [
        "read_core_workflow_readiness",
        "plan_recommended_next_tool",
    ]
    plan = result["agentCoreNextToolPlan"]
    assert plan["component"] == "AgentCoreNextToolPlan"
    assert plan["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert plan["toolAvailable"] is False
    assert plan["manualActionRequired"] is True
    assert plan["safety"]["recommendedToolCalled"] is False
    assert plan["safety"]["autoExecuteAllowed"] is False
    assert plan["safety"]["autoApproveAllowed"] is False
    assert plan["safety"]["autoPublishAllowed"] is False
    assert result["toolResponses"]["coreWorkflowReadiness"]["data"]["mcpToolCallRecord"]["toolName"] == (
        "get_core_workflow_readiness"
    )


def test_real_demo_agent_core_next_tool_planner_surfaces_content_quality_revision_stop(tmp_path):
    store_path = tmp_path / "store.json"
    created = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={"input": str(ROOT / "examples/input/demo-source.md"), "reviewer": "teacher_1"},
    )
    task = next(item for item in created["data"]["createdTasks"] if item["taskType"] == "LAB_GENERATION")
    store = JsonTaskStore(store_path)
    artifact = next(
        item for item in store.list_artifacts(task_id=task["id"]) if item.kind == ArtifactKind.LAB_DSL
    )
    artifact.metadata["contentQualitySummary"].update(
        {
            "readyForImportPreview": False,
            "decisionStatus": "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW",
            "recommendedAction": "revise_blocked_dsl_before_import_preview",
            "requiresRevisionBeforeImportPreview": True,
            "blockingIssueTotal": 1,
            "warningIssueTotal": 0,
        }
    )
    artifact.metadata["workflowContentQualitySummary"].update(
        {
            "decisionStatus": "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW",
            "recommendedAction": "revise_blocked_dsl_before_import_preview",
            "requiresRevisionBeforeImportPreview": True,
            "blockingIssueTotal": 1,
            "warningIssueTotal": 0,
            "readyForImportPreviewKinds": [],
            "blockedForImportPreviewKinds": ["lab"],
        }
    )
    store.save_artifact(artifact)

    result = plan_core_next_tool_from_readiness(
        task_id=task["id"],
        reviewer="teacher_1",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_content_quality_revision",
    )

    plan = result["agentCoreNextToolPlan"]
    assert result["summary"]["reasonCode"] == "CONTENT_QUALITY_REVISION_REQUIRED"
    assert result["summary"]["manualActionRequired"] is True
    assert plan["manualActionKind"] == "content_quality_revision_request"
    assert plan["manualActionLabel"] == "内容质量需先记录修订请求"
    assert "review revision-request" in plan["manualActionCliCommand"]
    assert plan["contentQualityReadiness"]["readyForImportPreview"] is False
    assert plan["contentQualityReadiness"]["blockedForImportPreviewKinds"] == ["lab"]
    assert plan["canCallToolAfterHumanConfirmation"] is False
    assert plan["safety"]["recommendedToolCalled"] is False

    try:
        execute_core_next_tool_from_readiness(
            task_id=task["id"],
            reviewer="teacher_1",
            confirm_execute_recommended_tool=True,
            store_path=store_path,
            root=ROOT,
            trace_id="trace_agent_execute_content_quality_revision",
        )
    except RealDemoAgentRunnerError as exc:
        assert exc.code == "NEXT_TOOL_MANUAL_ACTION_REQUIRED"
    else:
        raise AssertionError("expected manual action error")

    revision = handle_request(
        "POST",
        f"/api/review-tasks/{task['id']}/revision-request",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "comment": "请先按内容质量摘要修订。",
            "priority": "HIGH",
        },
    )
    post_revision_plan = plan_core_next_tool_from_readiness(
        task_id=task["id"],
        reviewer="teacher_1",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_content_quality_regenerate",
    )["agentCoreNextToolPlan"]
    assert revision["success"] is True
    assert post_revision_plan["reasonCode"] == "CONTENT_QUALITY_REVISION_REGENERATION_PENDING"
    assert post_revision_plan["toolName"] == "regenerate_from_revision_mock"
    assert post_revision_plan["canCallToolAfterHumanConfirmation"] is True
    assert post_revision_plan["argumentsPreview"]["revisionRequestId"] == revision["data"]["revisionRequest"]["id"]

    execution = execute_core_next_tool_from_readiness(
        task_id=task["id"],
        reviewer="teacher_1",
        tool_arguments={"output": str(tmp_path / "agent-content-quality-revision.json")},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_content_quality_regenerate",
    )
    assert execution["summary"]["executedToolName"] == "regenerate_from_revision_mock"
    assert execution["summary"]["recommendedToolCalled"] is True
    assert execution["summary"]["postExecutionReasonCode"] == "CONTENT_QUALITY_REVISION_REVIEW_PENDING"
    assert execution["postExecutionCoreNextToolPlan"]["manualActionKind"] == "manual_review_action"
    assert execution["toolResponses"]["recommendedTool"]["data"]["mockRegeneration"]["newTask"]["status"] == (
        "WAITING_REVIEW"
    )

    revision_task_id = execution["toolResponses"]["recommendedTool"]["data"]["mockRegeneration"]["newTask"]["id"]
    revision_plan = plan_core_next_tool_from_readiness(
        task_id=revision_task_id,
        reviewer="teacher_1",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_content_quality_revision_task",
    )["agentCoreNextToolPlan"]
    assert revision_plan["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"
    assert revision_plan["contentQualityReadiness"]["readyForImportPreview"] is True
    assert revision_plan["contentQualityReadiness"]["requiresRevisionBeforeImportPreview"] is False


def test_real_demo_agent_core_next_tool_planner_suggests_import_preview_after_approval(tmp_path):
    store_path = tmp_path / "store.json"
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_approved_source",
    )
    task_id = created["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    assert approved["success"] is True

    result = plan_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_import_preview",
    )

    plan = result["agentCoreNextToolPlan"]
    assert result["summary"]["taskStatus"] == "APPROVED"
    assert result["summary"]["reasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"
    assert result["summary"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert result["summary"]["recommendedToolName"] == "create_lab_template_import_preview"
    assert result["summary"]["canCallToolAfterHumanConfirmation"] is True
    assert result["summary"]["recommendedToolCalled"] is False
    assert plan["toolName"] == "create_lab_template_import_preview"
    assert plan["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert plan["argumentsPreview"]["taskId"] == task_id
    assert plan["argumentsPreview"]["reviewer"] == "<reviewer>"
    assert plan["safety"]["recommendedToolCalled"] is False
    assert plan["safety"]["realAgentImport"] is False


def test_real_demo_agent_core_next_tool_executor_requires_confirmation(tmp_path):
    store_path = tmp_path / "store.json"
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_unconfirmed_source",
    )
    task_id = created["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    assert approved["success"] is True

    try:
        execute_core_next_tool_from_readiness(
            task_id=task_id,
            reviewer="teacher_1",
            store_path=store_path,
            root=ROOT,
            trace_id="trace_agent_execute_unconfirmed",
        )
    except RealDemoAgentRunnerError as exc:
        assert exc.code == "CONFIRM_RECOMMENDED_TOOL_REQUIRED"
    else:
        raise AssertionError("expected confirmation error")

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert [record.toolName for record in records] == []


def test_real_demo_agent_core_next_tool_executor_calls_one_confirmed_recommended_tool(tmp_path):
    store_path = tmp_path / "store.json"
    output = tmp_path / "lab-template-import-preview.json"
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_source",
    )
    task_id = created["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    assert approved["success"] is True

    result = execute_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_confirmed",
    )

    assert result["component"] == "RealDemoAgentCoreNextToolExecutor"
    assert result["mode"] == "MOCK_AGENT_RUNNER_SINGLE_CONFIRMED_TOOL_EXECUTION"
    assert result["summary"]["recommendedToolName"] == "create_lab_template_import_preview"
    assert result["summary"]["executedToolName"] == "create_lab_template_import_preview"
    assert result["summary"]["executedToolTotal"] == 1
    assert result["summary"]["confirmedByHuman"] is True
    assert result["summary"]["recommendedToolCalled"] is True
    assert result["summary"]["stepTotal"] == 3
    assert result["summary"]["postExecutionReasonCode"] == "PLATFORM_MOCK_IMPORT_PENDING"
    assert result["summary"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert result["summary"]["postExecutionFinalReviewState"] == "NOT_GRADING_REVIEW"
    assert result["summary"]["postExecutionRecommendedToolName"] == "create_lab_template_mock_import"
    assert result["summary"]["postExecutionCanCallToolAfterHumanConfirmation"] is True
    assert result["summary"]["canContinueWithSameCommand"] is True
    assert result["summary"]["requiresAdditionalArguments"] is False
    assert result["postExecutionCoreNextToolPlan"]["toolName"] == "create_lab_template_mock_import"
    assert result["postExecutionCoreNextToolPlan"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    guide = result["nextSingleStepActionGuide"]
    assert guide["component"] == "AgentCoreNextSingleStepActionGuide"
    assert guide["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert guide["nextToolName"] == "create_lab_template_mock_import"
    assert guide["canContinueWithSameCommand"] is True
    assert guide["currentStop"]["reasonCode"] == "CONFIRMABLE_TOOL_READY"
    assert guide["currentStop"]["nextOperatorAction"] == "copy_suggested_cli_command_after_manual_confirmation"
    assert guide["currentStop"]["autoExecuteAllowed"] is False
    assert "finalReviewState=NOT_GRADING_REVIEW" in guide["operatorSummary"]
    assert guide["requiresHumanManualAction"] is False
    assert guide["requiresAdditionalArguments"] is False
    assert guide["suggestedArguments"]["taskId"] == task_id
    assert guide["suggestedArguments"]["reviewer"] == "teacher_1"
    assert guide["suggestedCliCommand"].startswith("python lab_cli.py agent real-demo execute-core-next-tool")
    assert "--confirm-execute-recommended-tool" in guide["suggestedCliCommand"]
    assert result["executedTool"]["arguments"]["reviewer"] == "teacher_1"
    assert result["executedTool"]["arguments"]["output"] == str(output)
    assert result["toolResponses"]["postExecutionCoreWorkflowReadiness"]["data"]["mcpToolCallRecord"]["toolName"] == (
        "get_core_workflow_readiness"
    )
    assert result["safety"]["singleToolExecution"] is True
    assert result["safety"]["autoApproveAllowed"] is False
    assert result["safety"]["autoPublishAllowed"] is False
    assert output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert sorted(record.toolName for record in records) == [
        "create_lab_template_import_preview",
        "get_core_workflow_readiness",
        "get_core_workflow_readiness",
    ]


def test_real_demo_agent_executes_import_preview_for_reviewed_revision_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    lab_created = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": str(source)},
    )
    lab_revision_task_id = _create_reviewed_revision_task(
        tmp_path,
        store_path=store_path,
        source_task_id=lab_created["data"]["task"]["id"],
    )
    lab_output = tmp_path / "lab-revision-import-preview.json"
    lab_result = execute_core_next_tool_from_readiness(
        task_id=lab_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(lab_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_lab_revision_import_preview",
    )
    assert lab_result["summary"]["executedToolName"] == "create_lab_template_import_preview"
    assert lab_result["summary"]["postExecutionRecommendedToolName"] == "create_lab_template_mock_import"
    assert lab_result["summary"]["postExecutionReasonCode"] == "PLATFORM_MOCK_IMPORT_PENDING"
    assert lab_output.exists()
    lab_mock_output = tmp_path / "lab-revision-mock-import.json"
    lab_mock_result = execute_core_next_tool_from_readiness(
        task_id=lab_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(lab_mock_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_lab_revision_mock_import",
    )
    assert lab_mock_result["summary"]["executedToolName"] == "create_lab_template_mock_import"
    assert lab_mock_result["summary"]["postExecutionRecommendedToolName"] == "create_agent_entity_import_dry_run"
    assert lab_mock_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_DRY_RUN_PENDING"
    assert lab_mock_output.exists()
    lab_entities = JsonTaskStore(store_path).list_agent_entities(source_task_id=lab_revision_task_id)
    assert len(lab_entities) == 1
    assert lab_entities[0].entityType.value == "lab_template"
    lab_dry_run_output = tmp_path / "lab-revision-platform-dry-run.json"
    lab_dry_run_result = execute_core_next_tool_from_readiness(
        task_id=lab_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(lab_dry_run_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_lab_revision_platform_dry_run",
    )
    assert lab_dry_run_result["summary"]["executedToolName"] == "create_agent_entity_import_dry_run"
    assert lab_dry_run_result["summary"]["postExecutionRecommendedToolName"] == "agent_internal_publish_request"
    assert lab_dry_run_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_REQUEST_PENDING"
    assert lab_dry_run_result["nextSingleStepActionGuide"]["requiresAdditionalArguments"] is True
    assert lab_dry_run_result["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == "ADDITIONAL_ARGUMENTS_REQUIRED"
    assert lab_dry_run_result["toolResponses"]["recommendedTool"]["data"]["agentEntityImportDryRun"]["entityType"] == (
        "lab_template"
    )
    assert lab_dry_run_output.exists()
    lab_dry_run = json.loads(lab_dry_run_output.read_text(encoding="utf-8"))
    assert lab_dry_run["entityType"] == "lab_template"
    assert lab_dry_run["safety"]["dryRunOnly"] is True
    assert lab_dry_run["safety"]["requestSent"] is False
    lab_send_output = tmp_path / "lab-revision-platform-send.json"
    server, thread, base_url = start_recording_platform_server()
    try:
        lab_send_result = execute_core_next_tool_from_readiness(
            task_id=lab_revision_task_id,
            reviewer="teacher_1",
            tool_arguments={
                "dryRun": str(lab_dry_run_output),
                "baseUrl": base_url,
                "output": str(lab_send_output),
                "explicitPlatformCallOptIn": True,
                "confirmDryRunReviewed": True,
                "confirmManualPlatformReview": True,
                "confirmNoAutoPublish": True,
            },
            confirm_execute_recommended_tool=True,
            store_path=store_path,
            root=ROOT,
            trace_id="trace_agent_execute_lab_revision_platform_send",
        )
    finally:
        stop_recording_platform_server(server, thread)
    assert lab_send_result["summary"]["executedToolName"] == "agent_internal_publish_request"
    assert lab_send_result["summary"]["postExecutionRecommendedToolName"] == "query_agent_publish_status"
    assert lab_send_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_STATUS_QUERY_PENDING"
    assert lab_send_output.exists()
    assert RecordingPlatformImportHandler.requests[0]["authorization"] == "Bearer platform-secret-token"
    assert "platform-secret-token" not in json.dumps(lab_send_result, ensure_ascii=False)

    lab_status_output = tmp_path / "lab-revision-platform-status.json"
    server, thread, base_url = start_recording_platform_server()
    try:
        lab_status_result = execute_core_next_tool_from_readiness(
            task_id=lab_revision_task_id,
            reviewer="teacher_1",
            tool_arguments={
                "sendResult": str(lab_send_output),
                "baseUrl": base_url,
                "output": str(lab_status_output),
                "explicitPlatformQueryOptIn": True,
            },
            confirm_execute_recommended_tool=True,
            store_path=store_path,
            root=ROOT,
            trace_id="trace_agent_execute_lab_revision_platform_status",
        )
    finally:
        stop_recording_platform_server(server, thread)
    assert lab_status_result["summary"]["executedToolName"] == "query_agent_publish_status"
    assert lab_status_result["summary"]["postExecutionRecommendedToolName"] == "record_agent_entity_publish_result"
    assert lab_status_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_RESULT_RECORD_PENDING"
    assert lab_status_output.exists()
    assert RecordingPlatformImportHandler.requests[0]["authorization"] == "Bearer platform-secret-token"
    assert "platform-secret-token" not in json.dumps(lab_status_result, ensure_ascii=False)

    lab_result_output = tmp_path / "lab-revision-platform-result.json"
    lab_result_record = execute_core_next_tool_from_readiness(
        task_id=lab_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={
            "sendResult": str(lab_send_output),
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": str(lab_result_output),
        },
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_lab_revision_platform_result",
    )
    assert lab_result_record["summary"]["executedToolName"] == "record_agent_entity_publish_result"
    assert lab_result_record["summary"]["postExecutionRecommendedToolName"] == "record_agent_entity_signoff"
    assert lab_result_record["summary"]["postExecutionReasonCode"] == "PLATFORM_ENTITY_SIGNOFF_REQUIRED"
    assert lab_result_output.exists()

    lab_signoff_output = tmp_path / "lab-revision-platform-signoff.json"
    lab_signoff_result = execute_core_next_tool_from_readiness(
        task_id=lab_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(lab_signoff_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_lab_revision_platform_signoff",
    )
    assert lab_signoff_result["summary"]["executedToolName"] == "record_agent_entity_signoff"
    assert lab_signoff_result["summary"]["postExecutionRecommendedToolName"] == "record_final_publish_review_decision"
    assert lab_signoff_result["summary"]["postExecutionReasonCode"] == "FINAL_HUMAN_REVIEW_DECISION_REQUIRED"
    assert lab_signoff_output.exists()

    lab_final_output = tmp_path / "lab-revision-platform-final-review.json"
    lab_final_result = execute_core_next_tool_from_readiness(
        task_id=lab_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(lab_final_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_lab_revision_platform_final_review",
    )
    assert lab_final_result["summary"]["executedToolName"] == "record_final_publish_review_decision"
    assert lab_final_result["summary"]["postExecutionReasonCode"] == "CORE_WORKFLOW_READY"
    assert lab_final_result["summary"]["canContinueWithSameCommand"] is False
    assert lab_final_result["safety"]["realPublishAllowed"] is False
    assert lab_final_output.exists()
    lab_final_core = lab_final_result["toolResponses"]["postExecutionCoreWorkflowReadiness"]["data"][
        "coreWorkflowReadinessReport"
    ]
    assert lab_final_core["ready"] is True
    assert lab_final_core["summary"]["platformPreviewCreatedTotal"] == 1
    assert lab_final_core["summary"]["platformMockImportCreatedTotal"] == 1
    assert lab_final_core["summary"]["platformSignoffRecordedTotal"] == 1
    assert lab_final_core["summary"]["finalPublishReviewDecisionRecordedTotal"] == 1
    assert lab_final_core["safety"]["realPublish"] is False

    exam_created = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    exam_revision_task_id = _create_reviewed_revision_task(
        tmp_path,
        store_path=store_path,
        source_task_id=exam_created["data"]["task"]["id"],
    )
    exam_output = tmp_path / "exam-revision-import-preview.json"
    exam_result = execute_core_next_tool_from_readiness(
        task_id=exam_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(exam_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_exam_revision_import_preview",
    )
    assert exam_result["summary"]["executedToolName"] == "create_exam_question_import_preview"
    assert exam_result["summary"]["postExecutionRecommendedToolName"] == "create_exam_question_mock_import"
    assert exam_result["summary"]["postExecutionReasonCode"] == "PLATFORM_MOCK_IMPORT_PENDING"
    assert exam_output.exists()
    exam_mock_output = tmp_path / "exam-revision-mock-import.json"
    exam_mock_result = execute_core_next_tool_from_readiness(
        task_id=exam_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(exam_mock_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_exam_revision_mock_import",
    )
    assert exam_mock_result["summary"]["executedToolName"] == "create_exam_question_mock_import"
    assert exam_mock_result["summary"]["postExecutionRecommendedToolName"] == "create_agent_entity_import_dry_run"
    assert exam_mock_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_DRY_RUN_PENDING"
    assert exam_mock_output.exists()
    exam_entities = JsonTaskStore(store_path).list_agent_entities(source_task_id=exam_revision_task_id)
    assert len(exam_entities) == 1
    assert exam_entities[0].entityType.value == "exam_question"
    exam_dry_run_output = tmp_path / "exam-revision-platform-dry-run.json"
    exam_dry_run_result = execute_core_next_tool_from_readiness(
        task_id=exam_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(exam_dry_run_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_exam_revision_platform_dry_run",
    )
    assert exam_dry_run_result["summary"]["executedToolName"] == "create_agent_entity_import_dry_run"
    assert exam_dry_run_result["summary"]["postExecutionRecommendedToolName"] == "agent_internal_publish_request"
    assert exam_dry_run_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_REQUEST_PENDING"
    assert exam_dry_run_result["nextSingleStepActionGuide"]["requiresAdditionalArguments"] is True
    assert exam_dry_run_result["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == "ADDITIONAL_ARGUMENTS_REQUIRED"
    assert exam_dry_run_result["toolResponses"]["recommendedTool"]["data"]["agentEntityImportDryRun"]["entityType"] == (
        "exam_question"
    )
    assert exam_dry_run_output.exists()
    exam_dry_run = json.loads(exam_dry_run_output.read_text(encoding="utf-8"))
    assert exam_dry_run["entityType"] == "exam_question"
    assert exam_dry_run["safety"]["dryRunOnly"] is True
    assert exam_dry_run["safety"]["requestSent"] is False

    grading_task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Agent Grading revision source",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_agent_grading_revision_source",
    )
    store = JsonTaskStore(store_path)
    store.save(grading_task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path="templates/grading/examples/mixed-checks.yaml",
            title="Agent Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_agent_grading_revision_source",
            task_id=grading_task.id,
            source_ref="templates/grading/examples/mixed-checks.yaml",
            metadata={"dslKind": "Grading", "reviewRequired": True},
        )
    )
    grading_revision_task_id = _create_reviewed_revision_task(
        tmp_path,
        store_path=store_path,
        source_task_id=grading_task.id,
    )
    _attach_ready_grading_evidence(store_path, tmp_path, task_id=grading_revision_task_id)
    note_output = tmp_path / "agent-grading-revision-decision-note.json"
    note_plan = plan_core_next_tool_from_readiness(
        task_id=grading_revision_task_id,
        reviewer="teacher_1",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_plan_grading_revision_decision_note",
    )
    assert note_plan["summary"]["recommendedToolName"] == "record_review_decision_note"
    assert note_plan["summary"]["reasonCode"] == "GRADING_DECISION_NOTE_REQUIRED"
    assert note_plan["summary"]["finalReviewState"] == "WAITING_DECISION_NOTE"
    assert note_plan["agentCoreNextToolPlan"]["argumentsPreview"]["decision"] == "approve-ready"
    note = execute_core_next_tool_from_readiness(
        task_id=grading_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(note_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_grading_revision_decision_note",
    )
    assert note["summary"]["executedToolName"] == "record_review_decision_note"
    assert note["summary"]["postExecutionRecommendedToolName"] == "create_grading_rule_import_preview"
    assert note["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"
    assert note["summary"]["postExecutionFinalReviewState"] == "READY_FOR_HUMAN_APPROVE"
    assert note["toolResponses"]["recommendedTool"]["data"]["decisionNote"]["decision"] == "approve-ready"
    assert note_output.exists()
    grading_output = tmp_path / "grading-revision-import-preview.json"
    grading_result = execute_core_next_tool_from_readiness(
        task_id=grading_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(grading_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_grading_revision_import_preview",
    )
    assert grading_result["summary"]["executedToolName"] == "create_grading_rule_import_preview"
    assert grading_result["summary"]["postExecutionRecommendedToolName"] == "create_grading_rule_mock_import"
    assert grading_result["summary"]["postExecutionReasonCode"] == "PLATFORM_MOCK_IMPORT_PENDING"
    assert grading_result["summary"]["finalReviewState"] == "READY_FOR_HUMAN_APPROVE"
    assert grading_output.exists()
    grading_mock_output = tmp_path / "grading-revision-mock-import.json"
    grading_mock_result = execute_core_next_tool_from_readiness(
        task_id=grading_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(grading_mock_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_grading_revision_mock_import",
    )
    assert grading_mock_result["summary"]["executedToolName"] == "create_grading_rule_mock_import"
    assert grading_mock_result["summary"]["postExecutionRecommendedToolName"] == "create_agent_entity_import_dry_run"
    assert grading_mock_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_DRY_RUN_PENDING"
    assert grading_mock_result["summary"]["finalReviewState"] == "READY_FOR_HUMAN_APPROVE"
    assert grading_mock_output.exists()
    grading_entities = JsonTaskStore(store_path).list_agent_entities(source_task_id=grading_revision_task_id)
    assert len(grading_entities) == 1
    assert grading_entities[0].entityType.value == "grading_rule"
    grading_dry_run_output = tmp_path / "grading-revision-platform-dry-run.json"
    grading_dry_run_result = execute_core_next_tool_from_readiness(
        task_id=grading_revision_task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(grading_dry_run_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_execute_grading_revision_platform_dry_run",
    )
    assert grading_dry_run_result["summary"]["executedToolName"] == "create_agent_entity_import_dry_run"
    assert grading_dry_run_result["summary"]["postExecutionRecommendedToolName"] == "agent_internal_publish_request"
    assert grading_dry_run_result["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_REQUEST_PENDING"
    assert grading_dry_run_result["summary"]["finalReviewState"] == "READY_FOR_HUMAN_APPROVE"
    assert grading_dry_run_result["nextSingleStepActionGuide"]["requiresAdditionalArguments"] is True
    assert grading_dry_run_result["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == "ADDITIONAL_ARGUMENTS_REQUIRED"
    assert grading_dry_run_result["toolResponses"]["recommendedTool"]["data"]["agentEntityImportDryRun"]["entityType"] == (
        "grading_rule"
    )
    assert grading_dry_run_output.exists()
    grading_dry_run = json.loads(grading_dry_run_output.read_text(encoding="utf-8"))
    assert grading_dry_run["entityType"] == "grading_rule"
    assert grading_dry_run["safety"]["dryRunOnly"] is True
    assert grading_dry_run["safety"]["requestSent"] is False

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert sum(1 for record in records if record.toolName == "create_lab_template_import_preview") == 1
    assert sum(1 for record in records if record.toolName == "create_exam_question_import_preview") == 1
    assert sum(1 for record in records if record.toolName == "create_grading_rule_import_preview") == 1
    assert sum(1 for record in records if record.toolName == "create_lab_template_mock_import") == 1
    assert sum(1 for record in records if record.toolName == "create_exam_question_mock_import") == 1
    assert sum(1 for record in records if record.toolName == "create_grading_rule_mock_import") == 1
    assert sum(1 for record in records if record.toolName == "create_agent_entity_import_dry_run") == 3
    assert sum(1 for record in records if record.toolName == "agent_internal_publish_request") == 1
    assert sum(1 for record in records if record.toolName == "query_agent_publish_status") == 1
    assert sum(1 for record in records if record.toolName == "record_agent_entity_publish_result") == 1
    assert sum(1 for record in records if record.toolName == "record_agent_entity_signoff") == 1
    assert sum(1 for record in records if record.toolName == "record_final_publish_review_decision") == 1


def test_real_demo_agent_core_next_tool_executor_advances_lab_to_final_review(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    store_path = tmp_path / "store.json"
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_full_chain_source",
    )
    task_id = created["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    assert approved["success"] is True

    preview_output = tmp_path / "lab-preview.json"
    preview_result = execute_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(preview_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_full_chain_preview",
    )
    assert preview_result["summary"]["executedToolName"] == "create_lab_template_import_preview"
    assert preview_result["summary"]["postExecutionRecommendedToolName"] == "create_lab_template_mock_import"
    assert preview_result["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == "CONFIRMABLE_TOOL_READY"

    mock_import_output = tmp_path / "lab-mock-import.json"
    mock_import_result = execute_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(mock_import_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_full_chain_mock_import",
    )
    assert mock_import_result["summary"]["executedToolName"] == "create_lab_template_mock_import"
    assert mock_import_result["summary"]["postExecutionRecommendedToolName"] == "create_agent_entity_import_dry_run"
    entity_id = mock_import_result["executedTool"]["arguments"].get("id")
    if not entity_id:
        entities = JsonTaskStore(store_path).list_agent_entities(source_task_id=task_id)
        entity_id = entities[0].id

    dry_run_output = tmp_path / "platform-dry-run.json"
    dry_run_result = execute_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(dry_run_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_full_chain_dry_run",
    )
    assert dry_run_result["summary"]["executedToolName"] == "create_agent_entity_import_dry_run"
    assert dry_run_result["summary"]["postExecutionRecommendedToolName"] == "agent_internal_publish_request"
    assert dry_run_result["nextSingleStepActionGuide"]["requiresAdditionalArguments"] is True
    assert dry_run_result["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == "ADDITIONAL_ARGUMENTS_REQUIRED"
    assert dry_run_output.exists()

    send_output = tmp_path / "platform-send.json"
    server, thread, base_url = start_recording_platform_server()
    try:
        send_result = execute_core_next_tool_from_readiness(
            task_id=task_id,
            reviewer="teacher_1",
            tool_arguments={
                "dryRun": str(dry_run_output),
                "baseUrl": base_url,
                "output": str(send_output),
                "explicitPlatformCallOptIn": True,
                "confirmDryRunReviewed": True,
                "confirmManualPlatformReview": True,
                "confirmNoAutoPublish": True,
            },
            confirm_execute_recommended_tool=True,
            store_path=store_path,
            root=ROOT,
            trace_id="trace_agent_full_chain_send",
        )
    finally:
        stop_recording_platform_server(server, thread)
    assert send_result["summary"]["executedToolName"] == "agent_internal_publish_request"
    assert send_result["summary"]["postExecutionRecommendedToolName"] == "query_agent_publish_status"
    assert send_output.exists()
    assert RecordingPlatformImportHandler.requests[0]["authorization"] == "Bearer platform-secret-token"
    assert "platform-secret-token" not in json.dumps(send_result, ensure_ascii=False)

    status_output = tmp_path / "platform-status.json"
    server, thread, base_url = start_recording_platform_server()
    try:
        status_result = execute_core_next_tool_from_readiness(
            task_id=task_id,
            reviewer="teacher_1",
            tool_arguments={
                "sendResult": str(send_output),
                "baseUrl": base_url,
                "output": str(status_output),
                "explicitPlatformQueryOptIn": True,
            },
            confirm_execute_recommended_tool=True,
            store_path=store_path,
            root=ROOT,
            trace_id="trace_agent_full_chain_status",
        )
    finally:
        stop_recording_platform_server(server, thread)
    assert status_result["summary"]["executedToolName"] == "query_agent_publish_status"
    assert status_result["summary"]["postExecutionRecommendedToolName"] == "record_agent_entity_publish_result"
    assert status_output.exists()

    result_output = tmp_path / "platform-result.json"
    result_record = execute_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        tool_arguments={
            "sendResult": str(send_output),
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": str(result_output),
        },
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_full_chain_result_record",
    )
    assert result_record["summary"]["executedToolName"] == "record_agent_entity_publish_result"
    assert result_record["summary"]["postExecutionRecommendedToolName"] == "record_agent_entity_signoff"

    signoff_output = tmp_path / "platform-signoff.json"
    signoff_result = execute_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(signoff_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_full_chain_signoff",
    )
    assert signoff_result["summary"]["executedToolName"] == "record_agent_entity_signoff"
    assert signoff_result["summary"]["postExecutionRecommendedToolName"] == "record_final_publish_review_decision"
    assert signoff_result["nextSingleStepActionGuide"]["canContinueWithSameCommand"] is True

    final_output = tmp_path / "platform-final-review.json"
    final_result = execute_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer="teacher_1",
        tool_arguments={"output": str(final_output)},
        confirm_execute_recommended_tool=True,
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_full_chain_final_review",
    )
    assert final_result["summary"]["executedToolName"] == "record_final_publish_review_decision"
    assert final_result["summary"]["postExecutionReasonCode"] == "CORE_WORKFLOW_READY"
    assert final_result["summary"]["canContinueWithSameCommand"] is False
    assert final_result["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == "HUMAN_MANUAL_ACTION_REQUIRED"
    assert final_output.exists()

    final_core = final_result["toolResponses"]["postExecutionCoreWorkflowReadiness"]["data"][
        "coreWorkflowReadinessReport"
    ]
    assert final_core["ready"] is True
    assert final_core["summary"]["platformPreviewCreatedTotal"] == 1
    assert final_core["summary"]["platformMockImportCreatedTotal"] == 1
    assert final_core["summary"]["platformSignoffRecordedTotal"] == 1
    assert final_core["summary"]["finalPublishReviewDecisionRecordedTotal"] == 1
    assert final_core["nextToolRecommendation"]["reasonCode"] == "CORE_WORKFLOW_READY"
    assert final_core["safety"]["realPublish"] is False

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert [record.toolName for record in records].count("get_core_workflow_readiness") >= 10
    assert "agent_internal_publish_request" in [record.toolName for record in records]
    assert "record_final_publish_review_decision" in [record.toolName for record in records]


def test_real_demo_agent_readiness_guidance_distinguishes_signed_entities():
    guidance = _build_agent_entity_readiness_guidance(
        {
            "data": {
                "agentEntityReadinessReport": {
                    "summary": {
                        "requiredTotal": 3,
                        "previewCreatedTotal": 3,
                        "mockImportCreatedTotal": 3,
                        "readyForManualAgentReviewTotal": 3,
                        "missingPreviewTotal": 0,
                        "missingMockImportTotal": 0,
                        "agentEntitySignoffReadyTotal": 0,
                        "agentEntitySignoffRecordedTotal": 3,
                        "postSignoffPrePublishReadyTotal": 3,
                        "allReadyForManualPlatformReview": True,
                        "allPlatformEntitiesReadyForSignoff": False,
                        "allPlatformEntitiesSignoffRecorded": True,
                        "allPostSignoffPrePublishReady": True,
                    },
                    "items": [
                        {
                            "agentEntity": "lab_template",
                            "previewCreated": True,
                            "mockImportCreated": True,
                            "readyForManualAgentReview": True,
                            "readyForAgentEntitySignoff": False,
                            "signoffRecorded": True,
                        },
                        {
                            "agentEntity": "exam_question",
                            "previewCreated": True,
                            "mockImportCreated": True,
                            "readyForManualAgentReview": True,
                            "readyForAgentEntitySignoff": False,
                            "signoffRecorded": True,
                        },
                        {
                            "agentEntity": "grading_rule",
                            "previewCreated": True,
                            "mockImportCreated": True,
                            "readyForManualAgentReview": True,
                            "readyForAgentEntitySignoff": False,
                            "signoffRecorded": True,
                        },
                    ],
                    "safety": {
                        "readOnly": True,
                        "databaseWritten": False,
                        "realAgentImport": False,
                        "realPublish": False,
                    },
                }
            }
        }
    )

    assert guidance["enabled"] is True
    assert guidance["agentEntitySignoffReadyTotal"] == 0
    assert guidance["agentEntitySignoffRecordedTotal"] == 3
    assert guidance["postSignoffPrePublishReadyTotal"] == 3
    assert guidance["allPlatformEntitiesSignoffRecorded"] is True
    assert guidance["allPostSignoffPrePublishReady"] is True
    assert guidance["signoffReadyEntities"] == []
    assert set(guidance["signedEntities"]) == {"lab_template", "exam_question", "grading_rule"}
    assert guidance["signoffPendingEntities"] == []
    assert guidance["nextRecommendedAction"] == "review_signed_agent_entities_before_publish_planning"
    assert guidance["realAgentImport"] is False
    assert guidance["realPublishAllowed"] is False


def test_real_demo_agent_runner_calls_mcp_tools_and_keeps_review_boundaries(tmp_path):
    store_path = tmp_path / "store.json"
    revision_output = tmp_path / "agent-lab-revision.json"

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_comment="补充步骤截图验收标准。",
        revision_priority="HIGH",
        revision_output=str(revision_output),
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_runner_test",
    )

    assert result["component"] == "RealDemoAgentMockRunner"
    assert result["mode"] == "MOCK_AGENT_RUNNER"
    assert result["contractId"] == "real_demo_agent_workflow_design"
    assert [step["id"] for step in result["steps"]] == [
        "open_static_demo",
        "summarize_review_queue",
        "create_local_lab_task",
        "triage_provider_quality",
        "inspect_review_detail",
        "request_revision",
        "create_mock_revision",
        "inspect_audit",
    ]
    assert result["summary"]["stepTotal"] == 8
    assert result["summary"]["completedTotal"] == 8
    assert result["summary"]["humanReviewStopTotal"] == 6
    assert result["summary"]["mutatingStepTotal"] == 3
    assert result["summary"]["sourceTaskStatus"] == "WAITING_REVIEW"
    assert result["summary"]["newTaskStatus"] == "WAITING_REVIEW"
    assert result["summary"]["newArtifactId"].startswith("artifact_")
    assert result["summary"]["primaryRecommendedAction"] == "open_review_detail_and_collect_quality_evidence"
    assert result["summary"]["reviewDetailPrimaryRecommendedAction"] == "request_review_revision_before_any_publish"
    assert result["summary"]["providerQualityAvailableTotal"] == 0
    assert result["summary"]["readyForReviewTotal"] == 0
    assert result["summary"]["importPreviewEligibleNow"] is False
    assert result["summary"]["platformImportPreviewEnabledTotal"] == 0
    assert result["summary"]["approvedLabTaskId"] is None
    assert result["summary"]["labImportPreviewCreated"] is False
    assert result["summary"]["labImportPreviewOutput"] is None
    assert result["summary"]["labImportPreviewDraftId"] is None
    triage = result["agentReviewTriage"]
    assert triage["component"] == "AgentQualityAwareReviewTriage"
    assert triage["source"] == "get_review_task_summary.data.reviewTaskSummary.providerQualityTaskSignal"
    assert triage["queueSource"] == "get_review_task_summary.data.reviewTaskSummary.reviewPriorityQueue"
    assert triage["reasonCode"] == "PROVIDER_QUALITY_NOT_READY_OR_NOT_AVAILABLE"
    assert triage["manualReviewRequired"] is True
    assert triage["importPreviewAllowedAfterApproval"] is False
    assert triage["nextReviewTaskIds"] == [result["summary"]["sourceTaskId"]]
    assert triage["autoApproveAllowed"] is False
    assert triage["batchStateChangeAllowed"] is False
    assert triage["autoPublishAllowed"] is False
    assert triage["realPublishAllowed"] is False
    assert result["toolResponses"]["qualityReviewSummary"]["data"]["reviewTaskSummary"]["providerQualityTaskSignal"]["availableTotal"] == 0
    detail_guidance = result["agentReviewDetailGuidance"]
    assert detail_guidance["component"] == "AgentReviewDetailGuidance"
    assert detail_guidance["source"] == "get_review_detail.data.reviewDetail.reviewPage"
    assert detail_guidance["taskId"] == result["summary"]["sourceTaskId"]
    assert detail_guidance["artifactKind"] == "LAB_DSL"
    assert detail_guidance["requestRevisionVisible"] is True
    assert detail_guidance["requestRevisionChangesTaskStatus"] is False
    assert detail_guidance["mockPublishEnabled"] is False
    assert detail_guidance["platformImportPreviewEnabledTotal"] == 0
    assert detail_guidance["platformImportPreviewAllowedAfterApproval"] is True
    assert detail_guidance["primaryRecommendedAction"] == "request_review_revision_before_any_publish"
    assert detail_guidance["autoApproveAllowed"] is False
    assert detail_guidance["realPublishAllowed"] is False
    assert result["approvedLabReviewDetailGuidance"] is None
    assert result["agentLabImportPreviewGuidance"]["enabled"] is False
    assert result["agentAgentEntityReadinessGuidance"]["enabled"] is False
    assert result["agentLabImportPreviewGuidance"]["autoPublishAllowed"] is False
    assert result["toolResponses"]["reviewDetail"]["data"]["reviewDetail"]["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert result["toolResponses"]["revisionRequest"]["data"]["revisionRequest"]["taskStatusChanged"] is False
    assert result["toolResponses"]["mockRegeneration"]["data"]["mockRegeneration"]["safety"]["newLlmRequestSent"] is False
    assert result["toolResponses"]["audit"]["data"]["total"] == 1
    assert result["safety"]["realAgentStarted"] is False
    assert result["safety"]["realLlmCalled"] is False
    assert result["safety"]["realMcpServerStarted"] is False
    assert result["safety"]["autoPublishAllowed"] is False
    assert result["safety"]["realPublish"] is False
    assert revision_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert {record.toolName for record in records} >= {
        "get_review_task_summary",
        "generate_lab_from_source",
        "request_review_revision",
        "regenerate_from_revision_mock",
        "list_mcp_tool_call_records",
        "get_review_detail",
    }
    assert sum(1 for record in records if record.toolName == "get_review_task_summary") == 2
    assert sum(1 for record in records if record.toolName == "get_review_detail") == 1


def test_real_demo_agent_runner_creates_local_lab_import_preview_for_approved_lab_task(tmp_path):
    store_path = tmp_path / "store.json"
    approved_lab_output = tmp_path / "approved-lab-output.json"
    revision_output = tmp_path / "agent-lab-revision.json"
    import_output = tmp_path / "agent-lab-import-preview.json"

    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        actor="test-setup",
        trace_id="trace_agent_import_setup",
    )
    assert approved_lab_output.name == "approved-lab-output.json"
    approved_task_id = created["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{approved_task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert approved["success"] is True

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_comment="补充步骤截图验收标准。",
        revision_priority="HIGH",
        revision_output=str(revision_output),
        approved_lab_task_id=approved_task_id,
        lab_import_output=str(import_output),
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_import_test",
    )

    assert [step["id"] for step in result["steps"]][-4:] == [
        "inspect_approved_lab_detail",
        "create_lab_import_preview",
        "inspect_lab_import_preview_signoff",
        "summarize_agent_entity_readiness",
    ]
    assert result["summary"]["stepTotal"] == 12
    assert result["summary"]["completedTotal"] == 12
    assert result["summary"]["humanReviewStopTotal"] == 9
    assert result["summary"]["mutatingStepTotal"] == 4
    assert result["summary"]["approvedLabTaskId"] == approved_task_id
    assert result["summary"]["labImportPreviewCreated"] is True
    assert result["summary"]["labImportPreviewOutput"] == str(import_output)
    assert result["summary"]["labImportPreviewDraftId"]
    assert result["summary"]["agentEntityReadinessReported"] is True
    assert result["summary"]["agentEntityReadyTotal"] == 0
    assert result["summary"]["agentEntityRequiredTotal"] == 4
    assert result["summary"]["agentEntityMissingPreviewTotal"] == 3
    assert result["summary"]["agentEntityMissingMockImportTotal"] == 4
    assert result["summary"]["agentEntityReadinessNextAction"] == "create_missing_import_previews_before_platform_review"
    assert result["approvedLabReviewDetailGuidance"]["taskStatus"] == "APPROVED"
    assert result["approvedLabReviewDetailGuidance"]["artifactKind"] == "LAB_DSL"
    assert result["approvedLabReviewDetailGuidance"]["platformImportPreviewEnabledTotal"] == 1
    import_guidance = result["agentLabImportPreviewGuidance"]
    assert import_guidance["enabled"] is True
    assert import_guidance["taskId"] == approved_task_id
    assert import_guidance["sourceTaskStatus"] == "APPROVED"
    assert import_guidance["draftStatus"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert import_guidance["databaseWritten"] is False
    assert import_guidance["realAgentImport"] is False
    assert import_guidance["autoPublishAllowed"] is False
    assert import_guidance["batchStateChangeAllowed"] is False
    assert import_guidance["realPublishAllowed"] is False
    preview = result["toolResponses"]["labImportPreview"]["data"]["labTemplateImportPreview"]
    assert preview["sourceTaskId"] == approved_task_id
    assert preview["safety"]["databaseWritten"] is False
    assert preview["safety"]["realAgentImport"] is False
    post_detail = result["toolResponses"]["postImportReviewDetail"]["data"]["reviewDetail"]
    assert post_detail["platformImportPreview"]["visible"] is True
    assert post_detail["platformImportPreview"]["total"] == 1
    assert post_detail["platformImportPreviewSignoff"]["readyForHumanSignoff"] is True
    assert result["safety"]["databaseWritten"] is False
    assert result["safety"]["realAgentImport"] is False
    assert result["safety"]["realPublish"] is False
    readiness_guidance = result["agentAgentEntityReadinessGuidance"]
    assert readiness_guidance["enabled"] is True
    assert readiness_guidance["readOnly"] is True
    assert readiness_guidance["databaseWritten"] is False
    assert readiness_guidance["realAgentImport"] is False
    assert readiness_guidance["readyForManualAgentReviewTotal"] == 0
    assert readiness_guidance["missingPreviewEntities"] == ["exam_question", "grading_rule", "ppt_deck"]
    assert readiness_guidance["missingMockImportEntities"] == ["lab_template", "exam_question", "grading_rule", "ppt_deck"]
    readiness_report = result["toolResponses"]["agentEntityReadiness"]["data"]["agentEntityReadinessReport"]
    assert readiness_report["summary"]["previewCreatedTotal"] == 1
    assert readiness_report["safety"]["readOnly"] is True
    assert import_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert len(records) == 11
    assert sum(1 for record in records if record.toolName == "get_review_detail") == 3
    assert sum(1 for record in records if record.toolName == "create_lab_template_import_preview") == 1
    assert sum(1 for record in records if record.toolName == "get_agent_entity_readiness_report") == 1


def test_real_demo_agent_runner_creates_exam_and_grading_import_previews(tmp_path):
    store_path = tmp_path / "store.json"
    revision_output = tmp_path / "agent-lab-revision.json"
    exam_output = tmp_path / "agent-exam-import-preview.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"

    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    approved_task_id = generated["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{approved_task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert approved["success"] is True

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_output=str(revision_output),
        approved_exam_task_id=approved_task_id,
        exam_import_output=str(exam_output),
        approved_grading_task_id=approved_task_id,
        grading_import_output=str(grading_output),
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_exam_grading_import_test",
    )

    assert [step["id"] for step in result["steps"]][-7:] == [
        "inspect_approved_exam_detail",
        "create_exam_import_preview",
        "inspect_exam_import_preview_signoff",
        "inspect_approved_grading_detail",
        "create_grading_import_preview",
        "inspect_grading_import_preview_signoff",
        "summarize_agent_entity_readiness",
    ]
    assert result["summary"]["stepTotal"] == 15
    assert result["summary"]["completedTotal"] == 15
    assert result["summary"]["humanReviewStopTotal"] == 11
    assert result["summary"]["mutatingStepTotal"] == 5
    assert result["summary"]["approvedExamTaskId"] == approved_task_id
    assert result["summary"]["approvedGradingTaskId"] == approved_task_id
    assert result["summary"]["examImportPreviewCreated"] is True
    assert result["summary"]["gradingImportPreviewCreated"] is True
    assert result["summary"]["agentEntityReadinessReported"] is True
    assert result["summary"]["agentEntityReadyTotal"] == 0
    assert result["summary"]["agentEntityMissingPreviewTotal"] == 2
    assert result["summary"]["agentEntityMissingMockImportTotal"] == 4
    assert result["summary"]["examImportPreviewOutput"] == str(exam_output)
    assert result["summary"]["gradingImportPreviewOutput"] == str(grading_output)
    exam_guidance = result["agentExamImportPreviewGuidance"]
    assert exam_guidance["enabled"] is True
    assert exam_guidance["taskId"] == approved_task_id
    assert exam_guidance["sourceArtifactKind"] == "EXAM_DSL"
    assert exam_guidance["agentEntity"] == "exam_question"
    assert exam_guidance["answerVisibleToCandidate"] is False
    assert exam_guidance["databaseWritten"] is False
    assert exam_guidance["realAgentImport"] is False
    assert exam_guidance["realPublishAllowed"] is False
    grading_guidance = result["agentGradingImportPreviewGuidance"]
    assert grading_guidance["enabled"] is True
    assert grading_guidance["taskId"] == approved_task_id
    assert grading_guidance["sourceArtifactKind"] == "GRADING_DSL"
    assert grading_guidance["agentEntity"] == "grading_rule"
    assert grading_guidance["sandboxExecuted"] is False
    assert grading_guidance["contestantCodeExecuted"] is False
    assert grading_guidance["databaseWritten"] is False
    assert grading_guidance["realAgentImport"] is False
    exam_preview = result["toolResponses"]["examImportPreview"]["data"]["examQuestionImportPreview"]
    assert exam_preview["examQuestionDraft"]["candidateAnswerVisible"] is False
    assert exam_preview["safety"]["answerVisibleToCandidate"] is False
    grading_preview = result["toolResponses"]["gradingImportPreview"]["data"]["gradingRuleImportPreview"]
    assert grading_preview["gradingRuleDraft"]["sandboxRequiredBeforeRealExecution"] is True
    assert grading_preview["safety"]["sandboxExecuted"] is False
    post_detail = result["toolResponses"]["postGradingImportReviewDetail"]["data"]["reviewDetail"]
    assert post_detail["platformImportPreview"]["total"] == 2
    assert set(post_detail["platformImportPreview"]["agentEntities"]) == {"exam_question", "grading_rule"}
    assert post_detail["platformImportPreviewSignoff"]["readyForHumanSignoff"] is True
    assert result["safety"]["databaseWritten"] is False
    assert result["safety"]["realAgentImport"] is False
    assert result["safety"]["realPublish"] is False
    readiness_guidance = result["agentAgentEntityReadinessGuidance"]
    assert readiness_guidance["enabled"] is True
    assert readiness_guidance["missingPreviewEntities"] == ["lab_template", "ppt_deck"]
    assert readiness_guidance["missingMockImportEntities"] == ["lab_template", "exam_question", "grading_rule", "ppt_deck"]
    assert readiness_guidance["autoPublishAllowed"] is False
    assert exam_output.exists()
    assert grading_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert len(records) == 14
    assert sum(1 for record in records if record.toolName == "get_review_detail") == 5
    assert sum(1 for record in records if record.toolName == "create_exam_question_import_preview") == 1
    assert sum(1 for record in records if record.toolName == "create_grading_rule_import_preview") == 1
    assert sum(1 for record in records if record.toolName == "get_agent_entity_readiness_report") == 1


def test_real_demo_agent_runner_creates_explicit_mock_imports_and_readiness(tmp_path):
    store_path = tmp_path / "store.json"
    revision_output = tmp_path / "agent-lab-revision.json"
    lab_import_output = tmp_path / "agent-lab-import-preview.json"
    exam_import_output = tmp_path / "agent-exam-import-preview.json"
    grading_import_output = tmp_path / "agent-grading-import-preview.json"
    lab_mock_output = tmp_path / "agent-lab-mock-import.json"
    exam_mock_output = tmp_path / "agent-exam-mock-import.json"
    grading_mock_output = tmp_path / "agent-grading-mock-import.json"

    lab_created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        actor="test-setup",
        trace_id="trace_agent_mock_import_lab_setup",
    )
    approved_lab_task_id = lab_created["data"]["task"]["id"]
    lab_approved = handle_request(
        "POST",
        f"/api/ai-tasks/{approved_lab_task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert lab_approved["success"] is True

    exam_grading_generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    approved_conversion_task_id = exam_grading_generated["data"]["task"]["id"]
    conversion_approved = handle_request(
        "POST",
        f"/api/ai-tasks/{approved_conversion_task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert conversion_approved["success"] is True

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_output=str(revision_output),
        approved_lab_task_id=approved_lab_task_id,
        lab_import_output=str(lab_import_output),
        create_lab_mock_import=True,
        lab_mock_import_output=str(lab_mock_output),
        approved_exam_task_id=approved_conversion_task_id,
        exam_import_output=str(exam_import_output),
        create_exam_mock_import=True,
        exam_mock_import_output=str(exam_mock_output),
        approved_grading_task_id=approved_conversion_task_id,
        grading_import_output=str(grading_import_output),
        create_grading_mock_import=True,
        grading_mock_import_output=str(grading_mock_output),
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_mock_import_full_chain_test",
    )

    assert result["steps"][-1]["id"] == "summarize_agent_entity_readiness"
    assert [step["id"] for step in result["steps"] if step["id"].endswith("_mock_import")] == [
        "create_lab_mock_import",
        "create_exam_mock_import",
        "create_grading_mock_import",
    ]
    assert result["summary"]["stepTotal"] == 21
    assert result["summary"]["mutatingStepTotal"] == 9
    assert result["summary"]["agentEntityMockImportCreatedTotal"] == 3
    assert result["summary"]["labMockImportCreated"] is True
    assert result["summary"]["examMockImportCreated"] is True
    assert result["summary"]["gradingMockImportCreated"] is True
    assert result["summary"]["labMockImportOutput"] == str(lab_mock_output)
    assert result["summary"]["examMockImportOutput"] == str(exam_mock_output)
    assert result["summary"]["gradingMockImportOutput"] == str(grading_mock_output)
    assert result["summary"]["labMockImportEntityId"].startswith("agent_entity_")
    assert result["summary"]["examMockImportEntityId"].startswith("agent_entity_")
    assert result["summary"]["gradingMockImportEntityId"].startswith("agent_entity_")
    assert result["summary"]["agentEntityReadyTotal"] == 3
    assert result["summary"]["agentEntityRequiredTotal"] == 4
    assert result["summary"]["agentEntityMissingPreviewTotal"] == 1
    assert result["summary"]["agentEntityMissingMockImportTotal"] == 1
    assert result["summary"]["agentEntitySignoffReadyTotal"] == 0
    assert result["summary"]["agentEntitySignoffRecordedTotal"] == 0
    assert result["summary"]["postSignoffPrePublishReadyTotal"] == 0
    assert result["summary"]["agentEntityReadinessNextAction"] == "create_missing_import_previews_before_platform_review"

    lab_guidance = result["agentLabMockImportGuidance"]
    assert lab_guidance["enabled"] is True
    assert lab_guidance["agentEntity"] == "lab_template"
    assert lab_guidance["mockStoreWritten"] is True
    assert lab_guidance["databaseWritten"] is False
    assert lab_guidance["realAgentImport"] is False
    exam_guidance = result["agentExamMockImportGuidance"]
    assert exam_guidance["enabled"] is True
    assert exam_guidance["agentEntity"] == "exam_question"
    assert exam_guidance["answerVisibleToCandidate"] is False
    assert exam_guidance["realAgentImport"] is False
    grading_guidance = result["agentGradingMockImportGuidance"]
    assert grading_guidance["enabled"] is True
    assert grading_guidance["agentEntity"] == "grading_rule"
    assert grading_guidance["sandboxExecuted"] is False
    assert grading_guidance["contestantCodeExecuted"] is False
    assert grading_guidance["realAgentImport"] is False

    readiness_guidance = result["agentAgentEntityReadinessGuidance"]
    assert readiness_guidance["allReadyForManualPlatformReview"] is False
    assert readiness_guidance["agentEntitySignoffReadyTotal"] == 0
    assert readiness_guidance["agentEntitySignoffRecordedTotal"] == 0
    assert readiness_guidance["postSignoffPrePublishReadyTotal"] == 0
    assert readiness_guidance["signoffReadyEntities"] == []
    assert readiness_guidance["signedEntities"] == []
    assert set(readiness_guidance["signoffPendingEntities"]) == {"lab_template", "exam_question", "grading_rule"}
    assert set(readiness_guidance["readyEntities"]) == {"lab_template", "exam_question", "grading_rule"}
    assert readiness_guidance["missingPreviewEntities"] == ["ppt_deck"]
    assert readiness_guidance["missingMockImportEntities"] == ["ppt_deck"]
    readiness_report = result["toolResponses"]["agentEntityReadiness"]["data"]["agentEntityReadinessReport"]
    assert readiness_report["summary"]["allReadyForManualPlatformReview"] is False
    assert readiness_report["summary"]["mockImportCreatedTotal"] == 3
    assert readiness_report["safety"]["realAgentImport"] is False
    assert result["safety"]["databaseWritten"] is False
    assert result["safety"]["realAgentImport"] is False
    assert result["safety"]["realPublish"] is False
    assert lab_mock_output.exists()
    assert exam_mock_output.exists()
    assert grading_mock_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert sum(1 for record in records if record.toolName == "create_lab_template_mock_import") == 1
    assert sum(1 for record in records if record.toolName == "create_exam_question_mock_import") == 1
    assert sum(1 for record in records if record.toolName == "create_grading_rule_mock_import") == 1
    assert sum(1 for record in records if record.toolName == "get_agent_entity_readiness_report") == 1


def test_real_demo_agent_runner_collects_readonly_grading_evidence(tmp_path):
    store_path = tmp_path / "store.json"
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-readonly-grading-evidence.json"

    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    approved_task_id = generated["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{approved_task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert approved["success"] is True

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_output=str(revision_output),
        approved_grading_task_id=approved_task_id,
        grading_import_output=str(grading_output),
        readonly_grading_submission=str(ROOT / "examples/submissions/readonly-demo"),
        readonly_grading_output=str(evidence_output),
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_readonly_grading_evidence_test",
    )

    assert result["steps"][-2]["id"] == "collect_readonly_grading_evidence"
    assert result["steps"][-2]["tool"] == "run_readonly_grading_evidence"
    assert result["steps"][-2]["humanReviewStop"] is True
    assert result["steps"][-1]["id"] == "summarize_agent_entity_readiness"
    assert result["summary"]["stepTotal"] == 13
    assert result["summary"]["readonlyGradingEvidenceCreated"] is True
    assert result["summary"]["agentEntityReadinessReported"] is True
    assert result["summary"]["readonlyGradingEvidenceOutput"] == str(evidence_output)
    assert result["summary"]["readonlyGradingEvidenceExecutedTotal"] >= 0
    assert result["summary"]["readonlyGradingEvidenceDeferredTotal"] >= 1
    guidance = result["agentReadonlyGradingEvidenceGuidance"]
    assert guidance["enabled"] is True
    assert guidance["readonlyOnly"] is True
    assert guidance["commandExecuted"] is False
    assert guidance["pytestExecuted"] is False
    assert guidance["notebookExecuted"] is False
    assert guidance["contestantCodeExecuted"] is False
    assert guidance["networkEnabled"] is False
    evidence = result["toolResponses"]["readonlyGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert evidence["safety"]["readonlyOnly"] is True
    assert evidence["safety"]["contestantCodeExecuted"] is False
    assert evidence["safety"]["commandExecuted"] is False
    assert evidence["executionSummary"]["executed"] >= 0
    assert evidence["executionSummary"]["deferred"] >= 1
    assert result["safety"]["realPublish"] is False
    assert result["agentAgentEntityReadinessGuidance"]["enabled"] is True
    assert result["agentAgentEntityReadinessGuidance"]["realAgentImport"] is False
    assert grading_output.exists()
    assert evidence_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert len(records) == 12
    assert sum(1 for record in records if record.toolName == "run_readonly_grading_evidence") == 1


def test_real_demo_agent_runner_collects_controlled_grading_evidence(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-controlled-grading-evidence.json"
    grading_path = ROOT / "templates/grading/examples/controlled-command-sandbox.yaml"
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Controlled Docker grading plan",
        input_type="grading-dsl",
        input_ref=str(grading_path),
        final_result_path=str(grading_path),
        trace_id="trace_agent_controlled_setup",
    )
    store.save(task)
    artifact = create_artifact_record(
        kind=ArtifactKind.GRADING_DSL,
        path=str(grading_path),
        title="Controlled Docker Grading DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        trace_id="trace_agent_controlled_setup",
        task_id=task.id,
        source_ref=str(grading_path),
    )
    store.save_artifact(artifact)
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert approved["success"] is True
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_output=str(revision_output),
        approved_grading_task_id=task.id,
        grading_import_output=str(grading_output),
        controlled_grading_submission=str(ROOT / "examples/submissions/controlled-command-demo"),
        controlled_grading_output=str(evidence_output),
        controlled_grading_image="local-python:demo",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_controlled_grading_evidence_test",
    )

    assert result["steps"][-2]["id"] == "collect_controlled_grading_evidence"
    assert result["steps"][-2]["tool"] == "run_controlled_grading_evidence"
    assert result["steps"][-2]["humanReviewStop"] is True
    assert result["steps"][-1]["id"] == "summarize_agent_entity_readiness"
    assert result["summary"]["stepTotal"] == 13
    assert result["summary"]["gradingImportPreviewCreated"] is True
    assert result["summary"]["controlledGradingEvidenceCreated"] is True
    assert result["summary"]["agentEntityReadinessReported"] is True
    assert result["summary"]["controlledGradingEvidenceOutput"] == str(evidence_output)
    assert result["summary"]["controlledGradingEvidenceExecutedTotal"] == 2
    assert result["summary"]["controlledGradingEvidenceDeferredTotal"] == 0
    assert result["summary"]["controlledGradingEvidenceEarnedScore"] == 100
    guidance = result["agentControlledGradingEvidenceGuidance"]
    assert guidance["enabled"] is True
    assert guidance["runtime"] == "docker"
    assert guidance["image"] == "local-python:demo"
    assert guidance["readonlyOnly"] is False
    assert guidance["sandboxExecuted"] is True
    assert guidance["commandExecuted"] is True
    assert guidance["pytestExecuted"] is True
    assert guidance["notebookExecuted"] is False
    assert guidance["contestantCodeExecuted"] is True
    assert guidance["unknownShellExecuted"] is False
    assert guidance["networkEnabled"] is False
    assert guidance["hostExecutionAllowed"] is False
    evidence = result["toolResponses"]["controlledGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert evidence["safety"]["contestantCodeExecuted"] is True
    assert evidence["safety"]["commandExecuted"] is True
    assert evidence["safety"]["networkEnabled"] is False
    assert result["safety"]["controlledSandboxExecuted"] is True
    assert result["safety"]["controlledContestantCodeExecuted"] is True
    assert result["safety"]["controlledNetworkEnabled"] is False
    assert result["safety"]["realPublish"] is False
    assert result["agentAgentEntityReadinessGuidance"]["enabled"] is True
    assert result["agentAgentEntityReadinessGuidance"]["databaseWritten"] is False
    assert grading_output.exists()
    assert evidence_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert len(records) == 12
    assert sum(1 for record in records if record.toolName == "run_controlled_grading_evidence") == 1
    assert sum(1 for record in records if record.toolName == "get_agent_entity_readiness_report") == 1


def test_real_demo_agent_runner_collects_auto_grading_evidence(tmp_path):
    store_path = tmp_path / "store.json"
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-auto-grading-evidence.json"

    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    approved_task_id = generated["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{approved_task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert approved["success"] is True

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_output=str(revision_output),
        approved_grading_task_id=approved_task_id,
        grading_import_output=str(grading_output),
        auto_grading_submission=str(ROOT / "examples/submissions/readonly-demo"),
        auto_grading_output=str(evidence_output),
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_auto_grading_evidence_test",
    )

    assert result["steps"][-2]["id"] == "collect_auto_grading_evidence"
    assert result["steps"][-2]["tool"] == "run_grading_evidence_auto"
    assert result["steps"][-2]["humanReviewStop"] is True
    assert result["steps"][-1]["id"] == "summarize_agent_entity_readiness"
    assert result["summary"]["stepTotal"] == 13
    assert result["summary"]["autoGradingEvidenceCreated"] is True
    assert result["summary"]["autoGradingEvidenceOutput"] == str(evidence_output)
    assert result["summary"]["autoGradingEvidenceSourceReportTotal"] == 1
    assert result["summary"]["autoGradingEvidenceControlledIncluded"] is False
    guidance = result["agentAutoGradingEvidenceGuidance"]
    assert guidance["enabled"] is True
    assert guidance["sourceMode"] == "EVIDENCE_AUTO"
    assert guidance["readonlyAlwaysRunsFirst"] is True
    assert guidance["controlledCommandIncluded"] is False
    assert guidance["commandExecuted"] is False
    assert guidance["contestantCodeExecuted"] is False
    assert guidance["gradingDslCoverageStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert guidance["gradingDslCheckTotal"] == 1
    assert guidance["gradingDslEvidenceReadyTotal"] == 0
    assert guidance["gradingDslMissingEvidenceTotal"] == 1
    assert guidance["gradingDslMissingCheckIds"] == ["check_pytest"]
    assert guidance["gradingDslDecisionNoteRecommendation"] == "needs-evidence"
    assert guidance["gradingDslNextCoreActionId"] == "run_evidence_auto_with_controlled_command"
    evidence = result["toolResponses"]["autoGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert evidence["gradingDslCoverageSummary"]["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert evidence["gradingDslCoverageSummary"]["missingCheckIds"] == ["check_pytest"]
    assert evidence["steps"][0]["id"] == "readonly_static_evidence"
    assert evidence["steps"][1]["id"] == "controlled_command_evidence"
    assert evidence["steps"][1]["status"] == "SKIPPED"
    assert result["safety"]["autoGradingEvidenceCreated"] is True
    assert result["safety"]["autoGradingControlledCommandIncluded"] is False
    assert result["safety"]["autoGradingContestantCodeExecuted"] is False
    assert result["safety"]["realPublish"] is False
    detail = handle_request("GET", f"/api/review-tasks/{approved_task_id}", store_path=store_path)
    assert detail["success"] is True
    merged = detail["data"]["reviewDetail"]["mergedGradingEvidence"]
    assert merged["visible"] is True
    assert merged["latestReportType"] == "GRADING_EVIDENCE_AUTO"
    assert merged["latestReportMode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert merged["summary"]["autoEvidenceReport"] is True
    assert merged["summary"]["latestReportPath"] == str(evidence_output)
    assert detail["data"]["reviewDetail"]["reviewPage"]["mergedGradingEvidence"] == merged
    report_payload = handle_request(
        "GET",
        f"/api/grading/report?file={evidence_output}&taskId={approved_task_id}",
        store_path=store_path,
    )
    assert report_payload["success"] is True
    assert report_payload["data"]["mergedGradingEvidence"]["latestReportType"] == "GRADING_EVIDENCE_AUTO"
    assert report_payload["data"]["autoGradingEvidenceSummary"]["autoEvidenceReport"] is True
    assert grading_output.exists()
    assert evidence_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert len(records) == 12
    assert sum(1 for record in records if record.toolName == "run_grading_evidence_auto") == 1


def test_real_demo_agent_runner_collects_auto_grading_evidence_with_controlled_command(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-auto-controlled-grading-evidence.json"
    grading_path = ROOT / "templates/grading/examples/controlled-command-sandbox.yaml"
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Auto controlled grading plan",
        input_type="grading-dsl",
        input_ref=str(grading_path),
        final_result_path=str(grading_path),
        trace_id="trace_agent_auto_controlled_setup",
    )
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path=str(grading_path),
            title="Auto Controlled Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_agent_auto_controlled_setup",
            task_id=task.id,
            source_ref=str(grading_path),
        )
    )
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_approve"},
    )
    assert approved["success"] is True
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)

    result = run_real_demo_agent_workflow(
        demo_source_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        revision_output=str(revision_output),
        approved_grading_task_id=task.id,
        grading_import_output=str(grading_output),
        auto_grading_submission=str(ROOT / "examples/submissions/controlled-command-demo"),
        auto_grading_output=str(evidence_output),
        auto_grading_include_controlled=True,
        auto_grading_image="local-python:demo",
        store_path=store_path,
        root=ROOT,
        trace_id="trace_agent_auto_controlled_grading_evidence_test",
    )

    assert result["steps"][-2]["id"] == "collect_auto_grading_evidence"
    assert result["steps"][-2]["tool"] == "run_grading_evidence_auto"
    assert result["summary"]["stepTotal"] == 13
    assert result["summary"]["autoGradingEvidenceCreated"] is True
    assert result["summary"]["autoGradingEvidenceControlledIncluded"] is True
    assert result["summary"]["autoGradingEvidenceEarnedScore"] == 100
    assert result["summary"]["autoGradingEvidenceTotalScore"] == 100
    guidance = result["agentAutoGradingEvidenceGuidance"]
    assert guidance["enabled"] is True
    assert guidance["controlledCommandRequested"] is True
    assert guidance["controlledCommandIncluded"] is True
    assert guidance["commandExecuted"] is True
    assert guidance["contestantCodeExecuted"] is True
    assert guidance["networkEnabled"] is False
    assert guidance["gradingDslCoverageStatus"] == "FULLY_COVERED_READY_FOR_HUMAN_DECISION"
    assert guidance["gradingDslCheckTotal"] == 2
    assert guidance["gradingDslEvidenceReadyTotal"] == 2
    assert guidance["gradingDslMissingEvidenceTotal"] == 0
    assert guidance["gradingDslMissingCheckIds"] == []
    assert guidance["gradingDslDecisionNoteRecommendation"] == "approve-ready"
    assert guidance["gradingDslNextCoreActionId"] == "review_score_and_record_decision_note"
    evidence = result["toolResponses"]["autoGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert evidence["summary"]["scorePreviewStatus"] == "READY_FOR_HUMAN_SCORE_REVIEW"
    assert evidence["summary"]["decisionNoteRecommendation"] == "approve-ready"
    assert evidence["scorePreview"]["readyForDecisionNote"] is True
    assert evidence["gradingDslCoverageSummary"]["status"] == "FULLY_COVERED_READY_FOR_HUMAN_DECISION"
    assert evidence["gradingDslCoverageSummary"]["missingCheckIds"] == []
    assert evidence["safety"]["controlledCommandIncluded"] is True
    assert evidence["safety"]["contestantCodeExecuted"] is True
    assert evidence["safety"]["networkEnabled"] is False
    assert result["safety"]["autoGradingControlledCommandIncluded"] is True
    assert result["safety"]["autoGradingContestantCodeExecuted"] is True
    assert result["safety"]["realPublish"] is False
    assert grading_output.exists()
    assert evidence_output.exists()

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="real-demo-agent-mock")
    assert len(records) == 12
    assert sum(1 for record in records if record.toolName == "run_grading_evidence_auto") == 1


def test_real_demo_agent_runner_rejects_unapproved_lab_import_preview_task(tmp_path):
    store_path = tmp_path / "store.json"
    created = invoke_mcp_tool(
        "generate_lab_from_source",
        {"input": str(ROOT / "examples/input/demo-source.md")},
        store_path=store_path,
        root=ROOT,
        actor="test-setup",
        trace_id="trace_agent_import_unapproved_setup",
    )
    task_id = created["data"]["task"]["id"]

    try:
        run_real_demo_agent_workflow(
            demo_source_path=str(ROOT / "examples/input/demo-source.md"),
            reviewer="teacher_1",
            approved_lab_task_id=task_id,
            lab_import_output=str(tmp_path / "agent-lab-import-preview.json"),
            store_path=store_path,
            root=ROOT,
        )
    except RealDemoAgentRunnerError as exc:
        assert exc.code == "APPROVED_LAB_TASK_REQUIRED"
        assert exc.errors[0]["field"] == "approvedLabTaskId"
    else:
        raise AssertionError("expected RealDemoAgentRunnerError")


def test_real_demo_agent_quality_triage_recommends_manual_review_for_ready_real_llm_outputs():
    triage = _build_quality_aware_review_triage(
        {
            "data": {
                "reviewTaskSummary": {
                    "providerQualityTaskSignal": {
                        "taskTotal": 2,
                        "availableTotal": 2,
                        "realLlmCalledTotal": 2,
                        "readyForReviewTotal": 2,
                        "normalizationPatchTotal": 1,
                        "schemaRepairAppliedTotal": 1,
                        "items": [
                            {"taskId": "task_lab", "available": True, "readyForReview": True, "realLlmCalled": True},
                            {"taskId": "task_exam", "available": True, "readyForReview": True, "realLlmCalled": True},
                        ],
                    },
                    "reviewPriorityQueue": {
                        "items": [
                            {
                                "taskId": "task_lab",
                                "recommendedAction": "review_generation_profile_and_material_coverage",
                            },
                            {
                                "taskId": "task_exam",
                                "recommendedAction": "verify_candidate_preview_and_grading_refs",
                            },
                        ]
                    },
                }
            }
        }
    )

    assert triage["primaryRecommendedAction"] == "manual_review_real_llm_outputs_before_import_preview"
    assert triage["reasonCode"] == "REAL_LLM_PROVIDER_QUALITY_READY_FOR_MANUAL_REVIEW"
    assert triage["realLlmCalledTotal"] == 2
    assert triage["readyForReviewTotal"] == 2
    assert triage["importPreviewAllowedAfterApproval"] is True
    assert triage["nextReviewTaskIds"] == ["task_lab", "task_exam"]
    assert triage["autoApproveAllowed"] is False
    assert triage["realPublishAllowed"] is False


def test_real_demo_agent_runner_rejects_bad_revision_priority(tmp_path):
    try:
        run_real_demo_agent_workflow(
            demo_source_path=str(ROOT / "examples/input/demo-source.md"),
            reviewer="teacher_1",
            revision_priority="URGENT",
            store_path=tmp_path / "store.json",
            root=ROOT,
        )
    except RealDemoAgentRunnerError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "revisionPriority"
    else:
        raise AssertionError("expected RealDemoAgentRunnerError")
