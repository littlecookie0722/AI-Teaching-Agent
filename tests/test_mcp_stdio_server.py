import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path

from cli.store import JsonTaskStore
from mcp_server.stdio_server import handle_jsonrpc_line, handle_jsonrpc_request, run_stdio


ROOT = Path(__file__).resolve().parents[1]


def jsonrpc(method, params=None, request_id=1):
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def test_mcp_stdio_initialize_and_list_tools():
    initialized = handle_jsonrpc_request(jsonrpc("initialize"), root=ROOT)
    listed = handle_jsonrpc_request(jsonrpc("tools/list", request_id=2), root=ROOT)

    assert initialized["result"]["protocolVersion"]
    assert initialized["result"]["serverInfo"]["name"] == "ai-training-platform-mcp"
    assert initialized["result"]["aiTrainingPlatform"]["transport"] == "stdio_jsonrpc"
    assert initialized["result"]["aiTrainingPlatform"]["toolProfile"] == "local-core-mvp"
    assert initialized["result"]["aiTrainingPlatform"]["manifestToolCount"] > initialized["result"]["aiTrainingPlatform"]["toolCount"]
    assert initialized["result"]["aiTrainingPlatform"]["safety"]["networkListenerStarted"] is False
    tools = listed["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert "analyze_material" in names
    assert "run_grading_evidence_auto" in names
    assert "create_grading_job" in names
    assert "run_grading_job" in names
    assert "review_grading_record" in names
    assert "list_agent_entities" in names
    assert "get_agent_entity" in names
    assert "validate_agent_entity_contract" in names
    assert "agent_internal_publish_request" not in names
    assert "query_agent_publish_status" not in names
    assert "publish_lab" not in names
    assert "destroy_environment" not in names
    analyze = next(tool for tool in tools if tool["name"] == "analyze_material")
    assert analyze["inputSchema"]["type"] == "object"
    assert analyze["annotations"]["reviewRequired"] is False
    assert listed["result"]["aiTrainingPlatform"]["toolProfile"]["profile"] == "local-core-mvp"
    assert listed["result"]["aiTrainingPlatform"]["toolPolicy"]["realPlatformBackendToolsEnabledByDefault"] is False
    assert listed["result"]["aiTrainingPlatform"]["safety"]["realAgentStarted"] is False


def test_mcp_stdio_call_tool_records_audit(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo", encoding="utf-8")

    payload = handle_jsonrpc_request(
        jsonrpc(
            "tools/call",
            {"name": "analyze_material", "arguments": {"input": str(source)}},
            request_id=3,
        ),
        root=ROOT,
        store_path=store_path,
        actor="stdio-test",
    )

    result = payload["result"]
    structured = result["structuredContent"]
    assert result["isError"] is False
    assert structured["success"] is True
    assert structured["data"]["analysis"]["mode"] == "MOCK_ONLY"
    assert structured["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert structured["data"]["mcpToolCallRecord"]["actor"] == "stdio-test"
    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="stdio-test")
    assert len(records) == 1
    assert records[0].toolName == "analyze_material"


def test_mcp_stdio_returns_tool_validation_error_as_call_result(tmp_path):
    payload = handle_jsonrpc_request(
        jsonrpc("tools/call", {"name": "analyze_material", "arguments": {}}, request_id=4),
        root=ROOT,
        store_path=tmp_path / "store.json",
    )

    result = payload["result"]
    structured = result["structuredContent"]
    assert result["isError"] is True
    assert structured["success"] is False
    assert structured["code"] == "VALIDATION_ERROR"
    assert structured["errors"][0]["field"] == "input"


def test_mcp_stdio_rejects_invalid_jsonrpc():
    payload = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 5, "method": "missing"}, root=ROOT)
    parsed = json.loads(handle_jsonrpc_line("{not-json", root=ROOT))

    assert payload["error"]["code"] == -32601
    assert parsed["error"]["code"] == -32700


def test_mcp_stdio_run_stdio_processes_line_delimited_requests(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo", encoding="utf-8")
    input_stream = StringIO(
        json.dumps(jsonrpc("initialize"), ensure_ascii=False)
        + "\n"
        + json.dumps(
            jsonrpc("tools/call", {"name": "analyze_material", "arguments": {"input": str(source)}}, request_id=2),
            ensure_ascii=False,
        )
        + "\n"
    )
    output_stream = StringIO()

    exit_code = run_stdio(input_stream=input_stream, output_stream=output_stream, root=ROOT, store_path=store_path)
    lines = [json.loads(line) for line in output_stream.getvalue().splitlines()]

    assert exit_code == 0
    assert lines[0]["result"]["serverInfo"]["name"] == "ai-training-platform-mcp"
    assert lines[1]["result"]["structuredContent"]["success"] is True


def test_mcp_stdio_module_runs_as_subprocess(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo", encoding="utf-8")
    request = json.dumps(
        jsonrpc("tools/call", {"name": "analyze_material", "arguments": {"input": str(source)}}),
        ensure_ascii=False,
    )

    completed = subprocess.run(
        [sys.executable, "-m", "mcp_server.stdio_server", "--store", str(store_path), "--actor", "stdio-subprocess"],
        input=request + "\n",
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=True,
    )

    response = json.loads(completed.stdout.strip())
    structured = response["result"]["structuredContent"]
    assert structured["success"] is True
    assert structured["data"]["mcpToolCallRecord"]["actor"] == "stdio-subprocess"
    assert completed.stderr == ""
