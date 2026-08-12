from pathlib import Path

import pytest

from cli.ai_task import TaskStatus
from cli.store import JsonTaskStore
from mcp_server.stdio_client_smoke import (
    McpStdioClientSmokeError,
    run_mcp_stdio_client_smoke,
    run_mcp_stdio_local_core_client,
)


ROOT = Path(__file__).resolve().parents[1]


def test_mcp_stdio_client_smoke_runs_jsonrpc_sequence(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    report = run_mcp_stdio_client_smoke(input_path=source, work_dir=tmp_path / "smoke", root=ROOT)

    assert report["success"] is True
    assert report["mode"] == "LOCAL_MCP_STDIO_CLIENT_SMOKE"
    assert report["transport"] == "stdio_jsonrpc"
    assert report["exitCode"] == 0
    assert report["initialize"]["passed"] is True
    assert report["toolsList"]["passed"] is True
    assert report["toolsList"]["containsAnalyzeMaterial"] is True
    assert report["toolCall"]["passed"] is True
    assert report["toolCall"]["analysisMode"] == "MOCK_ONLY"
    assert report["toolCall"]["auditActor"] == "lab-cli-mcp-stdio-client-smoke"
    assert report["safety"]["networkListenerStarted"] is False
    assert report["safety"]["realAgentStarted"] is False
    assert report["safety"]["realLlmCalled"] is False
    assert report["safety"]["autoPublishAllowed"] is False

    records = JsonTaskStore(Path(report["storePath"])).list_mcp_tool_call_records(actor=report["actor"])
    assert len(records) == 1
    assert records[0].toolName == "analyze_material"
    assert records[0].status.value == "SUCCESS"


def test_mcp_stdio_client_smoke_requires_existing_input(tmp_path):
    with pytest.raises(McpStdioClientSmokeError) as exc_info:
        run_mcp_stdio_client_smoke(input_path=tmp_path / "missing.md", work_dir=tmp_path / "smoke", root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.errors[0]["field"] == "input"


def test_mcp_stdio_local_core_client_uses_review_gated_two_step_flow(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Local MCP Client Demo", encoding="utf-8")
    work_dir = tmp_path / "local-core-client"

    draft = run_mcp_stdio_local_core_client(
        input_path=source,
        work_dir=work_dir,
        reviewer="teacher_1",
        root=ROOT,
    )

    assert draft["success"] is True
    assert draft["mode"] == "LOCAL_CORE_DRAFT_WAITING_REVIEW"
    assert draft["generatedTask"]["status"] == "WAITING_REVIEW"
    assert draft["stopReason"]["code"] == "WAITING_REVIEW_REQUIRED"
    assert draft["toolsList"]["toolProfile"] == "local-core-mvp"
    assert draft["pausedToolCheck"]["code"] == "MCP_TOOL_NOT_IN_PROFILE"
    assert draft["safety"]["manualReviewApprovalPerformedByClient"] is False

    task_id = draft["generatedTask"]["id"]
    store = JsonTaskStore(work_dir / "mcp-local-core-client-store.json")
    task = store.get(task_id)
    assert task is not None
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1", reason="explicit test human approval")
    store.save(task)

    continuation = run_mcp_stdio_local_core_client(
        input_path=source,
        work_dir=work_dir,
        reviewer="teacher_1",
        approved_lab_task_id=task_id,
        root=ROOT,
    )

    expected_tools = {
        "get_review_detail",
        "create_lab_template_import_preview",
        "create_lab_template_mock_import",
        "create_agent_entity_import_dry_run",
        "get_core_workflow_readiness",
        "create_grading_job",
        "run_grading_job",
        "list_grading_records",
        "list_mcp_tool_call_records",
    }
    assert continuation["success"] is True
    assert continuation["mode"] == "LOCAL_CORE_APPROVED_CONTINUATION"
    assert continuation["localImport"]["dryRunOnly"] is True
    assert continuation["stopReason"]["code"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert continuation["grading"]["recordTotal"] >= 1
    assert expected_tools.issubset({item["tool"] for item in continuation["toolCalls"]})
    assert (expected_tools - {"list_mcp_tool_call_records"}).issubset(set(continuation["audit"]["toolNames"]))
    assert continuation["audit"]["secretValueReturned"] is False
    assert continuation["safety"]["autoPublishAllowed"] is False


def test_mcp_stdio_local_core_client_rejects_unapproved_continuation(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Local MCP Client Demo", encoding="utf-8")
    work_dir = tmp_path / "local-core-client"
    draft = run_mcp_stdio_local_core_client(
        input_path=source,
        work_dir=work_dir,
        reviewer="teacher_1",
        root=ROOT,
    )

    with pytest.raises(McpStdioClientSmokeError) as exc_info:
        run_mcp_stdio_local_core_client(
            input_path=source,
            work_dir=work_dir,
            reviewer="teacher_1",
            approved_lab_task_id=draft["generatedTask"]["id"],
            root=ROOT,
        )

    assert exc_info.value.code == "MCP_LOCAL_CORE_CLIENT_TASK_NOT_APPROVED"
