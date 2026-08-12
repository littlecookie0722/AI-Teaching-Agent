"""Local MCP stdio client smoke runner.

The runner starts the project stdio server as a subprocess, sends a minimal
JSON-RPC sequence, and verifies that a client can initialize, list tools, and
call a safe read-only tool through stdin/stdout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTOR = "lab-cli-mcp-stdio-client-smoke"
DEFAULT_TIMEOUT_SECONDS = 15
LOCAL_CORE_CLIENT_ACTOR = "lab-cli-mcp-local-core-client"
PAUSED_DEFAULT_TOOL = "agent_internal_publish_request"


class McpStdioClientSmokeError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        errors: list[dict[str, str]] | None = None,
        report: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []
        self.report = report or {}


def run_mcp_stdio_client_smoke(
    *,
    input_path: Path,
    work_dir: Path,
    root: Path = ROOT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    actor: str = DEFAULT_ACTOR,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise McpStdioClientSmokeError(
            "VALIDATION_ERROR",
            "MCP stdio client smoke timeout must be positive.",
            [{"field": "timeoutSeconds", "reason": "must be positive"}],
        )
    if not input_path.exists() or not input_path.is_file():
        raise McpStdioClientSmokeError(
            "VALIDATION_ERROR",
            "MCP stdio client smoke input file does not exist.",
            [{"field": "input", "reason": str(input_path)}],
        )

    work_dir.mkdir(parents=True, exist_ok=True)
    store_path = work_dir / "mcp-stdio-client-smoke-store.json"
    command = [
        sys.executable,
        "-m",
        "mcp_server.stdio_server",
        "--store",
        str(store_path),
        "--actor",
        actor,
    ]
    requests = [
        _jsonrpc("initialize", request_id=1),
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        _jsonrpc("tools/list", request_id=2),
        _jsonrpc(
            "tools/call",
            {"name": "analyze_material", "arguments": {"input": str(input_path)}},
            request_id=3,
        ),
    ]
    raw_input = "".join(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n" for request in requests)

    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            command,
            input=raw_input,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=root,
            env=env,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        report = _base_report(
            input_path=input_path,
            work_dir=work_dir,
            store_path=store_path,
            command=command,
            actor=actor,
            timeout_seconds=timeout_seconds,
        )
        report.update(
            {
                "exitCode": None,
                "timedOut": True,
                "stderrTail": _tail(exc.stderr),
                "stdoutLineCount": 0,
                "success": False,
            }
        )
        raise McpStdioClientSmokeError(
            "MCP_STDIO_CLIENT_SMOKE_TIMEOUT",
            "MCP stdio client smoke timed out.",
            [{"field": "timeoutSeconds", "reason": str(timeout_seconds)}],
            report,
        ) from exc

    responses = _parse_stdout_lines(completed.stdout or "")
    report = _base_report(
        input_path=input_path,
        work_dir=work_dir,
        store_path=store_path,
        command=command,
        actor=actor,
        timeout_seconds=timeout_seconds,
    )
    report.update(
        {
            "exitCode": completed.returncode,
            "timedOut": False,
            "stdoutLineCount": len([line for line in (completed.stdout or "").splitlines() if line.strip()]),
            "stderrTail": _tail(completed.stderr),
            "requestsSent": [
                {"id": request.get("id"), "method": request.get("method")}
                for request in requests
                if request.get("method") != "notifications/initialized"
            ],
            "responses": [_summarize_response(response) for response in responses],
            "initialize": _extract_initialize_summary(responses),
            "toolsList": _extract_tools_list_summary(responses),
            "toolCall": _extract_tool_call_summary(responses),
        }
    )
    report["success"] = _report_passed(report)

    if completed.returncode != 0:
        raise McpStdioClientSmokeError(
            "MCP_STDIO_CLIENT_SMOKE_PROCESS_FAILED",
            "MCP stdio server subprocess exited with a non-zero code.",
            [{"field": "exitCode", "reason": str(completed.returncode)}],
            report,
        )
    if not report["success"]:
        raise McpStdioClientSmokeError(
            "MCP_STDIO_CLIENT_SMOKE_FAILED",
            "MCP stdio client smoke response validation failed.",
            [{"field": "responses", "reason": "initialize/tools-list/tools-call did not all pass"}],
            report,
        )
    return report


def run_mcp_stdio_local_core_client(
    *,
    input_path: Path,
    work_dir: Path,
    reviewer: str,
    approved_lab_task_id: str | None = None,
    root: Path = ROOT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    actor: str = LOCAL_CORE_CLIENT_ACTOR,
) -> dict[str, Any]:
    """Run a real local stdio client in an explicitly review-gated two-step flow."""

    if timeout_seconds <= 0:
        raise McpStdioClientSmokeError(
            "VALIDATION_ERROR",
            "MCP local core client timeout must be positive.",
            [{"field": "timeoutSeconds", "reason": "must be positive"}],
        )
    if not input_path.exists() or not input_path.is_file():
        raise McpStdioClientSmokeError(
            "VALIDATION_ERROR",
            "MCP local core client input file does not exist.",
            [{"field": "input", "reason": str(input_path)}],
        )
    if not reviewer.strip():
        raise McpStdioClientSmokeError(
            "VALIDATION_ERROR",
            "MCP local core client reviewer is required.",
            [{"field": "reviewer", "reason": "must not be blank"}],
        )

    work_dir.mkdir(parents=True, exist_ok=True)
    store_path = work_dir / "mcp-local-core-client-store.json"
    report = _local_core_client_base_report(
        input_path=input_path,
        work_dir=work_dir,
        store_path=store_path,
        reviewer=reviewer,
        actor=actor,
        timeout_seconds=timeout_seconds,
        approved_lab_task_id=approved_lab_task_id,
    )
    client = _LocalMcpStdioClient(
        root=root,
        store_path=store_path,
        actor=actor,
        timeout_seconds=timeout_seconds,
    )
    try:
        initialize = client.request("initialize", {})
        client.notify("notifications/initialized", {})
        tools_list = client.request("tools/list", {})
        tool_names = _tool_names_from_response(tools_list)
        _validate_default_profile(initialize, tool_names)
        report["initialize"] = _initialize_summary(initialize)
        report["toolsList"] = {
            "toolCount": len(tool_names),
            "toolProfile": _tool_profile_from_response(tools_list),
            "pausedToolVisible": PAUSED_DEFAULT_TOOL in tool_names,
            "passed": PAUSED_DEFAULT_TOOL not in tool_names,
        }

        paused = _call_tool(client, PAUSED_DEFAULT_TOOL, {})
        report["pausedToolCheck"] = _tool_response_summary(PAUSED_DEFAULT_TOOL, paused)
        if paused.get("success") is not False or paused.get("code") != "MCP_TOOL_NOT_IN_PROFILE":
            raise McpStdioClientSmokeError(
                "MCP_LOCAL_CORE_CLIENT_PAUSED_TOOL_POLICY_FAILED",
                "Default MCP profile exposed a paused platform tool.",
                [{"field": "pausedTool", "reason": str(paused.get("code"))}],
                report,
            )

        if approved_lab_task_id:
            _run_local_core_continuation(
                client,
                report=report,
                approved_lab_task_id=approved_lab_task_id,
                reviewer=reviewer,
                work_dir=work_dir,
                actor=actor,
            )
        else:
            _run_local_core_draft(
                client,
                report=report,
                input_path=input_path,
                actor=actor,
            )
    except McpStdioClientSmokeError:
        raise
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_FAILED",
            "Local MCP stdio client execution failed.",
            [{"field": "stdio", "reason": str(exc)}],
            report,
        ) from exc
    finally:
        client.close()
        report["process"] = client.summary()

    report["success"] = _local_core_client_report_passed(report)
    if not report["success"]:
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_VALIDATION_FAILED",
            "Local MCP stdio client response validation failed.",
            [{"field": "report", "reason": "required local core evidence missing"}],
            report,
        )
    return report


def _run_local_core_draft(
    client: "_LocalMcpStdioClient",
    *,
    report: dict[str, Any],
    input_path: Path,
    actor: str,
) -> None:
    analysis = _call_tool(client, "analyze_material", {"input": str(input_path)})
    generated = _call_tool(client, "generate_lab_from_source", {"input": str(input_path)})
    task = generated.get("data", {}).get("task", {}) if isinstance(generated.get("data"), dict) else {}
    task_id = str(task.get("id") or "")
    if not task_id or task.get("status") != "WAITING_REVIEW":
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_DRAFT_NOT_REVIEW_GATED",
            "Lab generation did not return a WAITING_REVIEW task.",
            [{"field": "generate_lab_from_source", "reason": str(task.get("status"))}],
            report,
        )
    review = _call_tool(client, "get_review_detail", {"taskId": task_id})
    audit = _call_tool(client, "list_mcp_tool_call_records", {"actor": actor})
    report.update(
        {
            "mode": "LOCAL_CORE_DRAFT_WAITING_REVIEW",
            "generatedTask": {"id": task_id, "status": task.get("status")},
            "toolCalls": [
                _tool_response_summary("analyze_material", analysis),
                _tool_response_summary("generate_lab_from_source", generated),
                _tool_response_summary("get_review_detail", review),
                _tool_response_summary("list_mcp_tool_call_records", audit),
            ],
            "audit": _audit_summary(audit, actor=actor),
            "stopReason": {"code": "WAITING_REVIEW_REQUIRED", "taskId": task_id},
        }
    )


def _run_local_core_continuation(
    client: "_LocalMcpStdioClient",
    *,
    report: dict[str, Any],
    approved_lab_task_id: str,
    reviewer: str,
    work_dir: Path,
    actor: str,
) -> None:
    review = _call_tool(client, "get_review_detail", {"taskId": approved_lab_task_id})
    task = review.get("data", {}).get("reviewDetail", {}).get("task", {})
    if not isinstance(task, dict) or task.get("status") != "APPROVED":
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_TASK_NOT_APPROVED",
            "Local import continuation requires a manually approved Lab task.",
            [{"field": "approvedLabTaskId", "reason": str(task.get("status") if isinstance(task, dict) else None)}],
            report,
        )
    preview = _call_tool(
        client,
        "create_lab_template_import_preview",
        {"taskId": approved_lab_task_id, "reviewer": reviewer, "output": str(work_dir / "lab-import-preview.json")},
    )
    mock_import = _call_tool(
        client,
        "create_lab_template_mock_import",
        {"taskId": approved_lab_task_id, "reviewer": reviewer, "output": str(work_dir / "lab-mock-import.json")},
    )
    entity = mock_import.get("data", {}).get("agentEntityRecord", {})
    entity_id = str(entity.get("id") or "") if isinstance(entity, dict) else ""
    if not entity_id:
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_ENTITY_MISSING",
            "MCP mock-import did not return a local platform entity id.",
            [{"field": "create_lab_template_mock_import", "reason": "agentEntityRecord.id missing"}],
            report,
        )
    dry_run = _call_tool(
        client,
        "create_agent_entity_import_dry_run",
        {
            "id": entity_id,
            "reviewer": reviewer,
            "output": str(work_dir / "lab-import-dry-run.json"),
            "contractConfig": "examples/input/platform-contract.json",
        },
    )
    readiness = _call_tool(client, "get_core_workflow_readiness", {"taskId": approved_lab_task_id})
    readiness_report = readiness.get("data", {}).get("coreWorkflowReadinessReport", {})
    if readiness_report.get("recommendedNextAction") != "LOCAL_CORE_MVP_STOP_LINE_REACHED":
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_STOP_LINE_NOT_REACHED",
            "Local import continuation did not stop at the local core MVP boundary.",
            [{"field": "recommendedNextAction", "reason": str(readiness_report.get("recommendedNextAction"))}],
            report,
        )

    grading_output = work_dir / "grading-evidence.json"
    grading_job = _call_tool(
        client,
        "create_grading_job",
        {
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(grading_output),
            "submissionId": "submission_mcp_local_core_client",
            "taskId": approved_lab_task_id,
            "candidateId": "candidate_mcp_local_core_client",
            "reviewer": reviewer,
        },
    )
    job_id = str(grading_job.get("data", {}).get("gradingJob", {}).get("id") or "")
    grading_run = _call_tool(client, "run_grading_job", {"id": job_id, "reviewer": reviewer})
    grading_records = _call_tool(client, "list_grading_records", {"taskId": approved_lab_task_id})
    audit = _call_tool(client, "list_mcp_tool_call_records", {"actor": actor})
    if int(grading_records.get("data", {}).get("total") or 0) < 1:
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_GRADING_RECORD_MISSING",
            "MCP grading flow did not expose a local GradingRecord.",
            [{"field": "list_grading_records", "reason": "expected at least one record"}],
            report,
        )
    report.update(
        {
            "mode": "LOCAL_CORE_APPROVED_CONTINUATION",
            "approvedTask": {"id": approved_lab_task_id, "status": task.get("status")},
            "localImport": {
                "agentEntityId": entity_id,
                "dryRunOnly": dry_run.get("data", {}).get("agentEntityImportDryRun", {}).get("safety", {}).get("dryRunOnly"),
                "stopReason": readiness_report.get("recommendedNextAction"),
            },
            "grading": {
                "jobId": job_id,
                "jobStatus": grading_run.get("data", {}).get("gradingJob", {}).get("status"),
                "recordTotal": grading_records.get("data", {}).get("total"),
            },
            "toolCalls": [
                _tool_response_summary("get_review_detail", review),
                _tool_response_summary("create_lab_template_import_preview", preview),
                _tool_response_summary("create_lab_template_mock_import", mock_import),
                _tool_response_summary("create_agent_entity_import_dry_run", dry_run),
                _tool_response_summary("get_core_workflow_readiness", readiness),
                _tool_response_summary("create_grading_job", grading_job),
                _tool_response_summary("run_grading_job", grading_run),
                _tool_response_summary("list_grading_records", grading_records),
                _tool_response_summary("list_mcp_tool_call_records", audit),
            ],
            "audit": _audit_summary(audit, actor=actor),
            "stopReason": {"code": "LOCAL_CORE_MVP_STOP_LINE_REACHED", "taskId": approved_lab_task_id},
        }
    )


class _LocalMcpStdioClient:
    def __init__(self, *, root: Path, store_path: Path, actor: str, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.request_id = 0
        self.process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.stdio_server", "--store", str(store_path), "--actor", actor],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=root,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.stderr_tail = ""

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.request_id += 1
        self._send({"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params})
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            raise OSError("MCP stdio server closed stdout before responding")
        response = json.loads(line)
        if not isinstance(response, dict):
            raise ValueError("MCP stdio response must be an object")
        if response.get("id") != self.request_id:
            raise ValueError("MCP stdio response id did not match request")
        if "error" in response:
            raise ValueError(f"MCP JSON-RPC error: {response['error']}")
        return response

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _send(self, request: dict[str, Any]) -> None:
        if self.process.stdin is None:
            raise OSError("MCP stdio server stdin is unavailable")
        self.process.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        if self.process.stderr is not None:
            self.stderr_tail = _tail(self.process.stderr.read())

    def summary(self) -> dict[str, Any]:
        return {"exitCode": self.process.returncode, "stderrTail": self.stderr_tail}


def _call_tool(client: _LocalMcpStdioClient, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = client.request("tools/call", {"name": name, "arguments": arguments})
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    structured = result.get("structuredContent") if isinstance(result, dict) else None
    if not isinstance(structured, dict):
        raise ValueError(f"MCP tool {name} did not return structuredContent")
    if structured.get("success") is not True and name != PAUSED_DEFAULT_TOOL:
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_TOOL_FAILED",
            "Local MCP tool call failed.",
            [{"field": name, "reason": str(structured.get("code"))}],
        )
    return structured


def _tool_names_from_response(response: dict[str, Any]) -> set[str]:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    tools = result.get("tools") if isinstance(result.get("tools"), list) else []
    return {str(tool.get("name")) for tool in tools if isinstance(tool, dict) and tool.get("name")}


def _tool_profile_from_response(response: dict[str, Any]) -> str | None:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    profile = result.get("aiTrainingPlatform", {}).get("toolProfile") if isinstance(result, dict) else None
    return profile.get("profile") if isinstance(profile, dict) else None


def _validate_default_profile(initialize: dict[str, Any], tool_names: set[str]) -> None:
    result = initialize.get("result") if isinstance(initialize.get("result"), dict) else {}
    profile = result.get("aiTrainingPlatform", {}).get("toolProfile") if isinstance(result, dict) else None
    if profile != "local-core-mvp" or PAUSED_DEFAULT_TOOL in tool_names:
        raise McpStdioClientSmokeError(
            "MCP_LOCAL_CORE_CLIENT_PROFILE_INVALID",
            "Local MCP client did not receive the local-core-mvp tool profile.",
            [{"field": "toolProfile", "reason": str(profile)}],
        )


def _initialize_summary(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    safety = result.get("aiTrainingPlatform", {}).get("safety", {}) if isinstance(result, dict) else {}
    return {
        "serverName": result.get("serverInfo", {}).get("name") if isinstance(result, dict) else None,
        "toolProfile": result.get("aiTrainingPlatform", {}).get("toolProfile") if isinstance(result, dict) else None,
        "networkListenerStarted": safety.get("networkListenerStarted") if isinstance(safety, dict) else None,
    }


def _tool_response_summary(name: str, response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    record = data.get("mcpToolCallRecord") if isinstance(data, dict) else {}
    return {
        "tool": name,
        "success": response.get("success"),
        "code": response.get("code"),
        "traceId": response.get("traceId"),
        "auditRecordId": record.get("id") if isinstance(record, dict) else None,
    }


def _audit_summary(response: dict[str, Any], *, actor: str) -> dict[str, Any]:
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return {
        "actor": actor,
        "recordTotal": data.get("total"),
        "toolNames": sorted({str(item.get("toolName")) for item in items if isinstance(item, dict)}),
        "secretValueReturned": False,
    }


def _local_core_client_base_report(
    *,
    input_path: Path,
    work_dir: Path,
    store_path: Path,
    reviewer: str,
    actor: str,
    timeout_seconds: int,
    approved_lab_task_id: str | None,
) -> dict[str, Any]:
    return {
        "component": "LocalMcpStdioClientAcceptance",
        "transport": "stdio_jsonrpc",
        "serverModule": "mcp_server.stdio_server",
        "input": str(input_path),
        "workDir": str(work_dir),
        "storePath": str(store_path),
        "reviewer": reviewer,
        "actor": actor,
        "approvedLabTaskId": approved_lab_task_id,
        "timeoutSeconds": timeout_seconds,
        "safety": {
            "stdioTransportStarted": True,
            "networkListenerStarted": False,
            "realMcpNetworkServerStarted": False,
            "realAgentStarted": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "manualReviewApprovalPerformedByClient": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }


def _local_core_client_report_passed(report: dict[str, Any]) -> bool:
    tool_calls = report.get("toolCalls") if isinstance(report.get("toolCalls"), list) else []
    succeeded = {item.get("tool") for item in tool_calls if isinstance(item, dict) and item.get("success") is True}
    expected = (
        {"analyze_material", "generate_lab_from_source", "get_review_detail", "list_mcp_tool_call_records"}
        if report.get("mode") == "LOCAL_CORE_DRAFT_WAITING_REVIEW"
        else {
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
    )
    audited_expected = expected - {"list_mcp_tool_call_records"}
    audited_names = set(report.get("audit", {}).get("toolNames", []))
    return (
        report.get("toolsList", {}).get("passed") is True
        and report.get("pausedToolCheck", {}).get("code") == "MCP_TOOL_NOT_IN_PROFILE"
        and expected.issubset(succeeded)
        and audited_expected.issubset(audited_names)
        and report.get("audit", {}).get("recordTotal", 0) >= len(audited_expected)
        and report.get("process", {}).get("exitCode") == 0
        and report.get("safety", {}).get("autoPublishAllowed") is False
    )


def _base_report(
    *,
    input_path: Path,
    work_dir: Path,
    store_path: Path,
    command: list[str],
    actor: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    return {
        "mode": "LOCAL_MCP_STDIO_CLIENT_SMOKE",
        "transport": "stdio_jsonrpc",
        "serverModule": "mcp_server.stdio_server",
        "serverCommand": command,
        "actor": actor,
        "input": str(input_path),
        "workDir": str(work_dir),
        "storePath": str(store_path),
        "timeoutSeconds": timeout_seconds,
        "safety": {
            "serverProcessStarted": True,
            "stdioTransportStarted": True,
            "networkListenerStarted": False,
            "networkAccess": False,
            "realMcpNetworkServerStarted": False,
            "realAgentStarted": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "realCloudResourceChanged": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }


def _jsonrpc(method: str, params: dict[str, Any] | None = None, *, request_id: int) -> dict[str, Any]:
    request: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        request["params"] = params
    return request


def _parse_stdout_lines(stdout: str) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise McpStdioClientSmokeError(
                "MCP_STDIO_CLIENT_SMOKE_INVALID_JSON",
                "MCP stdio server returned invalid JSON.",
                [{"field": f"stdout[{line_number}]", "reason": str(exc)}],
            ) from exc
        if not isinstance(payload, dict):
            raise McpStdioClientSmokeError(
                "MCP_STDIO_CLIENT_SMOKE_INVALID_JSON",
                "MCP stdio server returned a non-object JSON payload.",
                [{"field": f"stdout[{line_number}]", "reason": "expected object"}],
            )
        responses.append(payload)
    return responses


def _summarize_response(response: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"id": response.get("id"), "hasError": "error" in response}
    result = response.get("result")
    if isinstance(result, dict):
        if "serverInfo" in result:
            summary["serverInfo"] = result["serverInfo"]
        if "tools" in result and isinstance(result["tools"], list):
            summary["toolCount"] = len(result["tools"])
        if "structuredContent" in result:
            structured = result["structuredContent"]
            summary["toolCallSuccess"] = isinstance(structured, dict) and structured.get("success") is True
            summary["toolCallCode"] = structured.get("code") if isinstance(structured, dict) else None
            summary["isError"] = result.get("isError")
    if "error" in response:
        summary["error"] = response["error"]
    return summary


def _extract_initialize_summary(responses: list[dict[str, Any]]) -> dict[str, Any]:
    response = _response_by_id(responses, 1)
    result = response.get("result") if isinstance(response, dict) else None
    if not isinstance(result, dict):
        return {"passed": False, "reason": "missing initialize result"}
    safety = result.get("aiTrainingPlatform", {}).get("safety", {})
    return {
        "passed": result.get("protocolVersion") is not None
        and result.get("serverInfo", {}).get("name") == "ai-training-platform-mcp"
        and safety.get("networkListenerStarted") is False,
        "protocolVersion": result.get("protocolVersion"),
        "serverInfo": result.get("serverInfo"),
        "transport": result.get("aiTrainingPlatform", {}).get("transport"),
        "networkListenerStarted": safety.get("networkListenerStarted"),
    }


def _extract_tools_list_summary(responses: list[dict[str, Any]]) -> dict[str, Any]:
    response = _response_by_id(responses, 2)
    result = response.get("result") if isinstance(response, dict) else None
    if not isinstance(result, dict):
        return {"passed": False, "reason": "missing tools/list result", "toolCount": 0}
    tools = result.get("tools") if isinstance(result.get("tools"), list) else []
    names = [tool.get("name") for tool in tools if isinstance(tool, dict)]
    safety = result.get("aiTrainingPlatform", {}).get("safety", {})
    return {
        "passed": "analyze_material" in names and safety.get("networkListenerStarted") is False,
        "toolCount": len(tools),
        "containsAnalyzeMaterial": "analyze_material" in names,
        "networkListenerStarted": safety.get("networkListenerStarted"),
    }


def _extract_tool_call_summary(responses: list[dict[str, Any]]) -> dict[str, Any]:
    response = _response_by_id(responses, 3)
    result = response.get("result") if isinstance(response, dict) else None
    if not isinstance(result, dict):
        return {"passed": False, "reason": "missing tools/call result"}
    structured = result.get("structuredContent")
    data = structured.get("data", {}) if isinstance(structured, dict) else {}
    mcp_server_safety = data.get("mcpServerSafety", {}) if isinstance(data, dict) else {}
    record = data.get("mcpToolCallRecord", {}) if isinstance(data, dict) else {}
    return {
        "passed": isinstance(structured, dict)
        and structured.get("success") is True
        and result.get("isError") is False
        and mcp_server_safety.get("networkListenerStarted") is False,
        "tool": "analyze_material",
        "success": structured.get("success") if isinstance(structured, dict) else False,
        "code": structured.get("code") if isinstance(structured, dict) else None,
        "isError": result.get("isError"),
        "analysisMode": data.get("analysis", {}).get("mode") if isinstance(data.get("analysis"), dict) else None,
        "auditActor": record.get("actor") if isinstance(record, dict) else None,
        "networkListenerStarted": mcp_server_safety.get("networkListenerStarted"),
        "realAgentStarted": mcp_server_safety.get("realAgentStarted"),
    }


def _response_by_id(responses: list[dict[str, Any]], request_id: int) -> dict[str, Any]:
    for response in responses:
        if response.get("id") == request_id:
            return response
    return {}


def _report_passed(report: dict[str, Any]) -> bool:
    return (
        report.get("exitCode") == 0
        and report.get("initialize", {}).get("passed") is True
        and report.get("toolsList", {}).get("passed") is True
        and report.get("toolCall", {}).get("passed") is True
        and report.get("safety", {}).get("networkListenerStarted") is False
        and report.get("safety", {}).get("realAgentStarted") is False
        and report.get("safety", {}).get("realLlmCalled") is False
        and report.get("safety", {}).get("autoPublishAllowed") is False
    )


def _tail(value: str | bytes | None, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-limit:]
