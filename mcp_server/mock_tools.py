"""Phase 1 local MCP Tool mock invocation layer.

This module does not start an MCP server. It maps tool calls from the local
manifest to the existing Backend Mock request handler and returns the same JSON
envelope shape as CLI and Backend APIs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.mock_api import handle_request
from cli.mcp_audit import McpToolCallStatus, create_mcp_tool_call_record
from cli.store import JsonTaskStore


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "mcp-server/tools.manifest.json"
DEFAULT_MCP_TOOL_PROFILE = "local-core-mvp"
ALL_MCP_TOOL_PROFILE = "all"

LOCAL_CORE_MVP_TOOL_NAMES = {
    "get_real_llm_runtime_config",
    "analyze_material",
    "workflow_demo",
    "generate_lab_from_source",
    "generate_exam_from_lab",
    "generate_ppt",
    "run_grading",
    "run_readonly_grading_evidence",
    "run_controlled_grading_evidence",
    "merge_grading_evidence_reports",
    "run_grading_evidence_auto",
    "create_grading_job",
    "list_grading_jobs",
    "get_grading_job",
    "run_grading_job",
    "create_grading_record",
    "list_grading_records",
    "get_grading_record",
    "review_grading_record",
    "record_review_decision_note",
    "list_ai_tasks",
    "get_ai_task",
    "list_review_tasks",
    "get_grading_result_preview",
    "get_grading_evidence_readiness",
    "get_review_task_summary",
    "get_real_dsl_review_preview",
    "create_lab_template_import_preview",
    "create_exam_question_import_preview",
    "create_grading_rule_import_preview",
    "create_lab_template_mock_import",
    "create_exam_question_mock_import",
    "create_grading_rule_mock_import",
    "list_agent_entities",
    "get_agent_entity",
    "validate_agent_entity_contract",
    "get_review_detail",
    "get_agent_entity_readiness_report",
    "get_core_workflow_readiness",
    "create_agent_entity_import_dry_run",
    "list_review_audit_events",
    "list_operation_audit_events",
    "list_workflow_runs",
    "list_artifacts",
    "get_artifact",
    "get_workflow_run",
    "list_workflows",
    "get_workflow",
    "list_providers",
    "get_provider_health",
    "mock_provider_generate",
    "list_provider_audit_events",
    "list_mcp_tool_call_records",
}


PAUSED_MCP_TOOL_NAMES = {
    "create_real_dsl_revision_draft",
    "create_real_dsl_revision_batch_from_preview",
    "get_real_dsl_revision_diff_preview",
    "create_real_dsl_revision_decision",
    "promote_real_dsl_revision_candidate",
    "enqueue_real_dsl_revision_candidate_review",
    "agent_internal_publish_request",
    "record_agent_entity_publish_result",
    "query_agent_publish_status",
    "record_agent_entity_signoff",
    "record_final_publish_review_decision",
    "request_review_revision",
    "regenerate_from_revision_mock",
    "get_second_confirmation_status",
    "create_vm_environment",
    "create_notebook_environment",
    "publish_lab",
    "publish_exam",
    "destroy_environment",
}


class McpToolError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def load_mcp_manifest(root: Path = ROOT) -> dict[str, Any]:
    with (root / "mcp-server/tools.manifest.json").open("r", encoding="utf-8") as file:
        manifest = json.load(file)
    if not isinstance(manifest, dict):
        raise McpToolError("MCP_MANIFEST_ERROR", "MCP manifest root must be object", [{"field": "manifest", "reason": "root must be object"}])
    return manifest


def normalize_mcp_tool_profile(profile: str | None) -> str:
    normalized = (profile or DEFAULT_MCP_TOOL_PROFILE).strip().lower().replace("_", "-")
    if normalized in {"core", "local-core", "local-mvp"}:
        return DEFAULT_MCP_TOOL_PROFILE
    if normalized in {DEFAULT_MCP_TOOL_PROFILE, ALL_MCP_TOOL_PROFILE}:
        return normalized
    raise McpToolError(
        "VALIDATION_ERROR",
        "MCP Tool profile 不支持",
        [{"field": "profile", "reason": profile or ""}],
    )


def mcp_tool_profile_metadata(profile: str | None = DEFAULT_MCP_TOOL_PROFILE, root: Path = ROOT) -> dict[str, Any]:
    normalized = normalize_mcp_tool_profile(profile)
    all_tools = load_mcp_manifest(root)["tools"]
    paused_names = [tool["name"] for tool in all_tools if tool["name"] in PAUSED_MCP_TOOL_NAMES]
    core_names = [tool["name"] for tool in all_tools if tool["name"] in LOCAL_CORE_MVP_TOOL_NAMES]
    return {
        "profile": normalized,
        "defaultProfile": DEFAULT_MCP_TOOL_PROFILE,
        "allToolsProfile": ALL_MCP_TOOL_PROFILE,
        "scope": "local_core_mvp" if normalized == DEFAULT_MCP_TOOL_PROFILE else "full_manifest_reference",
        "manifestToolTotal": len(all_tools),
        "activeToolTotal": len(core_names) if normalized == DEFAULT_MCP_TOOL_PROFILE else len(all_tools),
        "pausedToolTotal": len(paused_names),
        "pausedToolNames": paused_names,
        "pausedReason": (
            "real platform backend, operations, revision-loop, environment, and publish/destroy tools are not part of the current local core MVP default profile"
        ),
    }


def _tool_in_profile(tool_name: str, profile: str) -> bool:
    if profile == ALL_MCP_TOOL_PROFILE:
        return True
    return tool_name in LOCAL_CORE_MVP_TOOL_NAMES


def list_mcp_tools(root: Path = ROOT, *, profile: str | None = DEFAULT_MCP_TOOL_PROFILE) -> list[dict[str, Any]]:
    manifest = load_mcp_manifest(root)
    normalized_profile = normalize_mcp_tool_profile(profile)
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "riskLevel": tool["riskLevel"],
            "reviewRequired": tool["reviewRequired"],
            "backend": tool["backend"],
            "inputSchema": tool["inputSchema"],
            "outputContract": tool.get("outputContract"),
            "safety": tool["safety"],
        }
        for tool in manifest["tools"]
        if _tool_in_profile(tool["name"], normalized_profile)
    ]


def _find_tool(name: str, root: Path, profile: str) -> dict[str, Any]:
    for tool in load_mcp_manifest(root)["tools"]:
        if tool["name"] == name:
            if not _tool_in_profile(tool["name"], profile):
                raise McpToolError(
                    "MCP_TOOL_NOT_IN_PROFILE",
                    "MCP Tool 不在当前工具 profile 中",
                    [
                        {"field": "tool", "reason": name},
                        {"field": "profile", "reason": profile},
                    ],
                )
            return tool
    raise McpToolError("NOT_FOUND", "MCP Tool 不存在", [{"field": "tool", "reason": name}])


def _validate_arguments(tool: dict[str, Any], arguments: dict[str, Any]) -> None:
    schema = tool["inputSchema"]
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    missing = [name for name in required if name not in arguments]
    if missing:
        raise McpToolError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": name, "reason": "缺少参数"} for name in missing],
        )
    if schema.get("additionalProperties") is False:
        unknown = [name for name in arguments if name not in properties]
        if unknown:
            raise McpToolError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": name, "reason": "未知参数"} for name in unknown],
            )
    for name, value in arguments.items():
        expected = properties.get(name, {}).get("type")
        if expected == "string" and not isinstance(value, str):
            raise McpToolError("VALIDATION_ERROR", "参数错误", [{"field": name, "reason": "必须是字符串"}])
        if expected == "integer" and not isinstance(value, int):
            raise McpToolError("VALIDATION_ERROR", "参数错误", [{"field": name, "reason": "必须是整数"}])
        if expected == "boolean" and not isinstance(value, bool):
            raise McpToolError("VALIDATION_ERROR", "参数错误", [{"field": name, "reason": "必须是布尔值"}])
        if expected == "object" and value is not None and not isinstance(value, dict):
            raise McpToolError("VALIDATION_ERROR", "参数错误", [{"field": name, "reason": "必须是对象"}])
        if expected == "array" and not isinstance(value, list):
            raise McpToolError("VALIDATION_ERROR", "参数错误", [{"field": name, "reason": "必须是数组"}])
        allowed_values = properties.get(name, {}).get("enum")
        if allowed_values is not None and value not in allowed_values:
            raise McpToolError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": name, "reason": f"必须是以下值之一: {', '.join(str(item) for item in allowed_values)}"}],
            )


def _build_path(path_template: str, arguments: dict[str, Any]) -> str:
    path = path_template
    for name, value in arguments.items():
        path = path.replace(f"{{{name}}}", str(value))
    return path


def _query_arguments(tool: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    path = tool["backend"]["path"]
    return {key: value for key, value in arguments.items() if f"{{{key}}}" not in path}


def _append_query(path: str, query: dict[str, Any]) -> str:
    if not query:
        return path
    parts: list[str] = []
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, list):
            parts.extend(f"{key}={item}" for item in value if item is not None)
        else:
            parts.append(f"{key}={value}")
    if not parts:
        return path
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}{'&'.join(parts)}"


def _first_error_field(errors: list[dict[str, str]] | None) -> str | None:
    if not errors:
        return None
    return errors[0].get("field")


def _safe_argument_preview(arguments: dict[str, Any]) -> dict[str, Any]:
    redacted_fragments = ("secret", "token", "password", "apikey", "api_key", "key")
    preview: dict[str, Any] = {}
    for name, value in sorted(arguments.items()):
        lowered = name.lower()
        if any(fragment in lowered for fragment in redacted_fragments):
            preview[name] = "<redacted>"
        elif isinstance(value, str):
            preview[name] = value if len(value) <= 120 else f"{value[:117]}..."
        elif isinstance(value, (int, bool)) or value is None:
            preview[name] = value
        elif isinstance(value, dict):
            preview[name] = {"type": "object", "keys": sorted(value)}
        elif isinstance(value, list):
            preview[name] = {"type": "array", "length": len(value)}
        else:
            preview[name] = {"type": type(value).__name__}
    return preview


def _save_mcp_tool_call_record(
    *,
    tool: dict[str, Any],
    arguments: dict[str, Any],
    status: McpToolCallStatus,
    actor: str,
    trace_id: str,
    backend_method: str,
    backend_path: str,
    store_path: Path | None,
    backend_called: bool,
    response: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_field: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    response = response or {}
    record = create_mcp_tool_call_record(
        tool_name=tool["name"],
        status=status,
        actor=actor,
        backend_method=backend_method,
        backend_path=backend_path,
        risk_level=tool["riskLevel"],
        review_required=tool["reviewRequired"],
        trace_id=trace_id,
        argument_keys=sorted(arguments),
        argument_preview=_safe_argument_preview(arguments),
        backend_called=backend_called,
        response_code=response.get("code"),
        response_message=response.get("message"),
        backend_trace_id=response.get("traceId"),
        error_code=error_code or (response.get("code") if status == McpToolCallStatus.FAILED else None),
        error_field=error_field or (_first_error_field(response.get("errors")) if status == McpToolCallStatus.FAILED else None),
        error_message=error_message or (response.get("message") if status == McpToolCallStatus.FAILED else None),
    )
    JsonTaskStore(store_path).save_mcp_tool_call_record(record)
    return record.to_dict()


def invoke_mcp_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    store_path: Path | None = None,
    root: Path = ROOT,
    actor: str = "mcp-mock",
    trace_id: str | None = None,
    profile: str | None = DEFAULT_MCP_TOOL_PROFILE,
) -> dict[str, Any]:
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise McpToolError("VALIDATION_ERROR", "参数错误", [{"field": "arguments", "reason": "必须是对象"}])
    normalized_profile = normalize_mcp_tool_profile(profile)
    tool = _find_tool(name, root, normalized_profile)
    backend = tool["backend"]
    method = backend["method"]
    path = _build_path(backend["path"], arguments)
    call_trace_id = trace_id or response_trace_id_placeholder()
    try:
        _validate_arguments(tool, arguments)
    except McpToolError as exc:
        _save_mcp_tool_call_record(
            tool=tool,
            arguments=arguments,
            status=McpToolCallStatus.FAILED,
            actor=actor,
            trace_id=call_trace_id,
            backend_method=method,
            backend_path=path,
            store_path=store_path,
            backend_called=False,
            error_code=exc.code,
            error_field=_first_error_field(exc.errors),
            error_message=exc.message,
        )
        raise

    if method == "GET":
        query_arguments = _query_arguments(tool, arguments)
        if name == "get_core_workflow_readiness" and normalized_profile == ALL_MCP_TOOL_PROFILE:
            query_arguments["includeFuturePlatformFlow"] = True
        response = handle_request(method, _append_query(path, query_arguments), store_path=store_path)
    else:
        response = handle_request(method, path, store_path=store_path, body=_query_arguments(tool, arguments))

    status = McpToolCallStatus.SUCCESS if response.get("success") else McpToolCallStatus.FAILED
    call_record = _save_mcp_tool_call_record(
        tool=tool,
        arguments=arguments,
        status=status,
        actor=actor,
        trace_id=call_trace_id,
        backend_method=method,
        backend_path=path,
        store_path=store_path,
        backend_called=True,
        response=response,
    )
    data = response.setdefault("data", {}) if response.get("success") else None
    if isinstance(data, dict):
        data["mcpTool"] = {
            "name": name,
            "mode": "MOCK_ONLY",
            "riskLevel": tool["riskLevel"],
            "reviewRequired": tool["reviewRequired"],
            "realMcpServerStarted": False,
            "realAgentStarted": False,
        }
        data["mcpToolCallRecord"] = call_record
    else:
        response["mcpToolCallRecord"] = call_record
    return response


def response_trace_id_placeholder() -> str:
    from uuid import uuid4

    return f"trace_{uuid4().hex[:12]}"
