"""MCP Tool call record model for Phase 1 mock MCP boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class McpToolCallStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class McpToolCallRecord:
    toolName: str
    status: McpToolCallStatus
    actor: str
    backendMethod: str
    backendPath: str
    riskLevel: str
    reviewRequired: bool
    argumentKeys: list[str] = field(default_factory=list)
    argumentPreview: dict[str, Any] = field(default_factory=dict)
    backendCalled: bool = False
    responseCode: str | None = None
    responseMessage: str | None = None
    backendTraceId: str | None = None
    errorCode: str | None = None
    errorField: str | None = None
    errorMessage: str | None = None
    id: str = field(default_factory=lambda: f"mcp_call_{uuid4().hex[:12]}")
    occurredAt: str = field(default_factory=utc_now)
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    mode: str = "MOCK_ONLY"
    realMcpServerStarted: bool = False
    realAgentStarted: bool = False
    realLlmCalled: bool = False
    secretsRead: bool = False
    networkAccess: bool = False
    realCloudResourceChanged: bool = False
    sandboxExecuted: bool = False
    contestantCodeExecuted: bool = False
    autoPublishAllowed: bool = False
    realPublish: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpToolCallRecord":
        payload = dict(data)
        payload["status"] = McpToolCallStatus(payload["status"])
        return cls(**payload)


def create_mcp_tool_call_record(
    *,
    tool_name: str,
    status: McpToolCallStatus,
    actor: str,
    backend_method: str,
    backend_path: str,
    risk_level: str,
    review_required: bool,
    trace_id: str,
    argument_keys: list[str] | None = None,
    argument_preview: dict[str, Any] | None = None,
    backend_called: bool = False,
    response_code: str | None = None,
    response_message: str | None = None,
    backend_trace_id: str | None = None,
    error_code: str | None = None,
    error_field: str | None = None,
    error_message: str | None = None,
) -> McpToolCallRecord:
    return McpToolCallRecord(
        toolName=tool_name,
        status=status,
        actor=actor,
        backendMethod=backend_method,
        backendPath=backend_path,
        riskLevel=risk_level,
        reviewRequired=review_required,
        argumentKeys=argument_keys or [],
        argumentPreview=argument_preview or {},
        backendCalled=backend_called,
        responseCode=response_code,
        responseMessage=response_message,
        backendTraceId=backend_trace_id,
        errorCode=error_code,
        errorField=error_field,
        errorMessage=error_message,
        traceId=trace_id,
    )
