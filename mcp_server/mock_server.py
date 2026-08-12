"""Phase 4 local MCP server mock runtime.

The runtime exposes MCP-shaped initialize, list_tools, and call_tool helpers
without opening a socket, spawning an agent, or starting a real MCP server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .mock_tools import (
    DEFAULT_MCP_TOOL_PROFILE,
    McpToolError,
    invoke_mcp_tool,
    list_mcp_tools,
    load_mcp_manifest,
    mcp_tool_profile_metadata,
    normalize_mcp_tool_profile,
)


ROOT = Path(__file__).resolve().parents[1]


def build_mcp_server_info(root: Path = ROOT, *, profile: str | None = DEFAULT_MCP_TOOL_PROFILE) -> dict[str, Any]:
    normalized_profile = normalize_mcp_tool_profile(profile)
    manifest = load_mcp_manifest(root)
    tools = list_mcp_tools(root, profile=normalized_profile)
    tool_profile = mcp_tool_profile_metadata(normalized_profile, root)
    return {
        "server": {
            "id": "ai_training_platform_mcp_mock",
            "name": "AI Training Platform MCP Mock Server",
            "version": manifest["version"],
            "phase": "Phase 4",
            "mode": manifest["mode"],
            "protocol": "mcp-server-mock",
            "transport": "local_function_only",
            "toolCount": len(tools),
            "manifestToolCount": tool_profile["manifestToolTotal"],
            "toolProfile": normalized_profile,
        },
        "capabilities": {
            "initialize": True,
            "listTools": True,
            "callTool": True,
            "streaming": False,
            "resources": False,
            "prompts": False,
        },
        "safety": {
            "realMcpServerStarted": False,
            "realAgentStarted": False,
            "realLlmCalled": False,
            "networkListenerStarted": False,
            "networkAccess": False,
            "realCloudResourceChanged": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
        "toolPolicy": {
            "source": "mcp-server/tools.manifest.json",
            "defaultToolProfile": DEFAULT_MCP_TOOL_PROFILE,
            "directInvocationDefaultProfile": DEFAULT_MCP_TOOL_PROFILE,
            "activeToolProfile": normalized_profile,
            "pausedToolTotal": tool_profile["pausedToolTotal"],
            "toolsCallBackendMockOnly": True,
            "returnsUnifiedJson": True,
            "auditRequired": True,
            "argumentPreviewRedactsSecrets": True,
            "highRiskRequiresReview": True,
            "realPlatformBackendToolsEnabledByDefault": False,
        },
        "toolProfile": tool_profile,
    }


def initialize_mcp_server(root: Path = ROOT, *, profile: str | None = DEFAULT_MCP_TOOL_PROFILE) -> dict[str, Any]:
    info = build_mcp_server_info(root, profile=profile)
    return {
        **info,
        "message": "MCP Mock Server initialized locally; no listener or agent was started.",
    }


def list_server_tools(root: Path = ROOT, *, profile: str | None = DEFAULT_MCP_TOOL_PROFILE) -> dict[str, Any]:
    normalized_profile = normalize_mcp_tool_profile(profile)
    tools = list_mcp_tools(root, profile=normalized_profile)
    return {
        "items": tools,
        "total": len(tools),
        **build_mcp_server_info(root, profile=normalized_profile),
    }


def call_server_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    store_path: Path | None = None,
    root: Path = ROOT,
    actor: str = "mcp-server-mock",
    trace_id: str | None = None,
    profile: str | None = DEFAULT_MCP_TOOL_PROFILE,
) -> dict[str, Any]:
    normalized_profile = normalize_mcp_tool_profile(profile)
    response = invoke_mcp_tool(
        name,
        arguments or {},
        store_path=store_path,
        root=root,
        actor=actor,
        trace_id=trace_id,
        profile=normalized_profile,
    )
    server_info = build_mcp_server_info(root, profile=normalized_profile)
    data = response.setdefault("data", {}) if response.get("success") else None
    if isinstance(data, dict):
        data["mcpServer"] = server_info["server"]
        data["mcpServerSafety"] = server_info["safety"]
        data["mcpServerToolPolicy"] = server_info["toolPolicy"]
    else:
        response["mcpServer"] = server_info["server"]
        response["mcpServerSafety"] = server_info["safety"]
    return response


__all__ = [
    "build_mcp_server_info",
    "call_server_tool",
    "initialize_mcp_server",
    "list_server_tools",
    "McpToolError",
]
