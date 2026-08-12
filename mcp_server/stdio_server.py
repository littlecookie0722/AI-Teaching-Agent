"""Line-delimited JSON-RPC stdio MCP server boundary.

This module starts no network listener and runs no agent. It exposes the
existing MCP tool manifest through a process stdin/stdout boundary so local MCP
clients can initialize, list tools, and call tools while preserving the same
Backend Mock, audit, and review boundaries.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from .mock_server import call_server_tool, list_server_tools
from .mock_tools import DEFAULT_MCP_TOOL_PROFILE, McpToolError, load_mcp_manifest, normalize_mcp_tool_profile


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ai-training-platform-mcp"


def handle_jsonrpc_request(
    request: dict[str, Any],
    *,
    root: Path = ROOT,
    store_path: Path | None = None,
    actor: str = "mcp-stdio-server",
) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}
    if request.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return _error(request_id, -32600, "Invalid JSON-RPC request")
    if method == "notifications/initialized":
        return None
    if not isinstance(params, dict):
        return _error(request_id, -32602, "params must be an object")
    if method == "initialize":
        return _result(request_id, _initialize_result(root, _profile_from_params(params)))
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, _tools_list_result(root, _profile_from_params(params)))
    if method == "tools/call":
        return _result(request_id, _tools_call_result(params, root=root, store_path=store_path, actor=actor))
    return _error(request_id, -32601, f"Unknown method: {method}")


def handle_jsonrpc_line(
    line: str,
    *,
    root: Path = ROOT,
    store_path: Path | None = None,
    actor: str = "mcp-stdio-server",
) -> str | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        return json.dumps(_error(None, -32700, "Parse error", {"detail": str(exc)}), ensure_ascii=False)
    if not isinstance(payload, dict):
        return json.dumps(_error(None, -32600, "JSON-RPC request must be an object"), ensure_ascii=False)
    response = handle_jsonrpc_request(payload, root=root, store_path=store_path, actor=actor)
    if response is None:
        return None
    return json.dumps(response, ensure_ascii=False, separators=(",", ":"))


def run_stdio(
    *,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    root: Path = ROOT,
    store_path: Path | None = None,
    actor: str = "mcp-stdio-server",
) -> int:
    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue
        response_line = handle_jsonrpc_line(line, root=root, store_path=store_path, actor=actor)
        if response_line is None:
            continue
        output_stream.write(response_line)
        output_stream.write("\n")
        output_stream.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AI Training Platform MCP stdio server.")
    parser.add_argument("--store", help="Optional local JSON store path for MCP tool audit records.")
    parser.add_argument("--actor", default="mcp-stdio-server", help="Actor label stored in MCP tool audit records.")
    args = parser.parse_args(argv)
    store_path = Path(args.store) if args.store else None
    return run_stdio(store_path=store_path, actor=args.actor)


def _initialize_result(root: Path, profile: str = DEFAULT_MCP_TOOL_PROFILE) -> dict[str, Any]:
    manifest = load_mcp_manifest(root)
    profile = normalize_mcp_tool_profile(profile)
    tools = list_server_tools(root, profile=profile)
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {},
            "prompts": {},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": manifest["version"],
        },
        "aiTrainingPlatform": {
            "mode": "LOCAL_STDIO_MCP",
            "manifest": "mcp-server/tools.manifest.json",
            "toolCount": tools["total"],
            "manifestToolCount": len(manifest["tools"]),
            "toolProfile": profile,
            "transport": "stdio_jsonrpc",
            "safety": _stdio_safety(),
        },
    }


def _tools_list_result(root: Path, profile: str = DEFAULT_MCP_TOOL_PROFILE) -> dict[str, Any]:
    profile = normalize_mcp_tool_profile(profile)
    payload = list_server_tools(root, profile=profile)
    tools = [
        {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["inputSchema"],
            "annotations": {
                "riskLevel": tool["riskLevel"],
                "reviewRequired": tool["reviewRequired"],
            },
        }
        for tool in payload["items"]
    ]
    return {
        "tools": tools,
        "aiTrainingPlatform": {
            "mode": "LOCAL_STDIO_MCP",
            "toolProfile": payload["toolProfile"],
            "toolPolicy": payload["toolPolicy"],
            "safety": _stdio_safety(),
        },
    }


def _tools_call_result(
    params: dict[str, Any],
    *,
    root: Path,
    store_path: Path | None,
    actor: str,
) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if not isinstance(name, str) or not name:
        raise JsonRpcInvalidParams("tools/call params.name must be a non-empty string")
    if not isinstance(arguments, dict):
        raise JsonRpcInvalidParams("tools/call params.arguments must be an object")
    profile = _profile_from_params(params)
    try:
        response = call_server_tool(name, arguments, root=root, store_path=store_path, actor=actor, profile=profile)
    except McpToolError as exc:
        response = {
            "success": False,
            "code": exc.code,
            "message": exc.message,
            "errors": exc.errors,
            "traceId": "trace_mcp_stdio_validation",
        }
    text = json.dumps(response, ensure_ascii=False)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": response,
        "isError": response.get("success") is not True,
    }


def _profile_from_params(params: dict[str, Any]) -> str:
    profile = params.get("profile", DEFAULT_MCP_TOOL_PROFILE)
    if profile is None:
        return DEFAULT_MCP_TOOL_PROFILE
    if not isinstance(profile, str):
        raise JsonRpcInvalidParams("params.profile must be a string")
    try:
        return normalize_mcp_tool_profile(profile)
    except McpToolError as exc:
        raise JsonRpcInvalidParams(exc.message) from exc


def _stdio_safety() -> dict[str, bool]:
    return {
        "stdioTransportStarted": True,
        "networkListenerStarted": False,
        "realAgentStarted": False,
        "realLlmCalledByServer": False,
        "realCloudResourceChangedByServer": False,
        "autoPublishAllowed": False,
        "realPublish": False,
    }


class JsonRpcInvalidParams(ValueError):
    pass


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _wrap_invalid_params(handler):
    def wrapper(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except JsonRpcInvalidParams as exc:
            request = args[0] if args else {}
            request_id = request.get("id") if isinstance(request, dict) else None
            return _error(request_id, -32602, str(exc))

    return wrapper


handle_jsonrpc_request = _wrap_invalid_params(handle_jsonrpc_request)


if __name__ == "__main__":
    raise SystemExit(main())
