"""Provider call audit model for Phase 1 mock provider boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class ProviderCallStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class ProviderCallAuditEvent:
    operation: str
    providerId: str
    status: ProviderCallStatus
    actor: str
    promptId: str | None = None
    outputKind: str | None = None
    inputRef: str | None = None
    errorCode: str | None = None
    errorField: str | None = None
    errorMessage: str | None = None
    dslPath: str | None = None
    dslId: str | None = None
    generatedStatus: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"provider_audit_{uuid4().hex[:12]}")
    occurredAt: str = field(default_factory=utc_now)
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    adapterId: str = "mock_provider_adapter"
    interfaceName: str = "LLMProvider"
    mode: str = "MOCK_ONLY"
    mockOutputCreated: bool = False
    realLlmCalled: bool = False
    secretsRead: bool = False
    networkAccess: bool = False
    generatedContentCreated: bool = False
    taskCreated: bool = False
    reviewBypassed: bool = False
    autoPublishAllowed: bool = False
    realPublish: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderCallAuditEvent":
        payload = dict(data)
        payload["status"] = ProviderCallStatus(payload["status"])
        return cls(**payload)


def create_provider_call_audit_event(
    *,
    operation: str,
    provider_id: str,
    status: ProviderCallStatus,
    actor: str,
    trace_id: str,
    prompt_id: str | None = None,
    output_kind: str | None = None,
    input_ref: str | None = None,
    adapter_id: str = "mock_provider_adapter",
    interface_name: str = "LLMProvider",
    error_code: str | None = None,
    error_field: str | None = None,
    error_message: str | None = None,
    result: dict[str, Any] | None = None,
    detail: dict[str, Any] | None = None,
    mode: str = "MOCK_ONLY",
    mock_output_created: bool | None = None,
    real_llm_called: bool = False,
    secrets_read: bool = False,
    network_access: bool = False,
    generated_content_created: bool | None = None,
    task_created: bool = False,
    review_bypassed: bool = False,
    auto_publish_allowed: bool = False,
    real_publish: bool = False,
) -> ProviderCallAuditEvent:
    result = result or {}
    default_mock_output_created = status == ProviderCallStatus.SUCCESS and operation in {"generateJson", "generateText"}
    default_generated_content_created = status == ProviderCallStatus.SUCCESS and operation == "generateJson"
    return ProviderCallAuditEvent(
        operation=operation,
        providerId=provider_id,
        status=status,
        actor=actor,
        traceId=trace_id,
        promptId=prompt_id or result.get("promptId"),
        outputKind=output_kind or result.get("outputKind"),
        inputRef=input_ref or result.get("inputRef"),
        errorCode=error_code,
        errorField=error_field,
        errorMessage=error_message,
        dslPath=result.get("dslPath"),
        dslId=result.get("dslId"),
        generatedStatus=result.get("generatedStatus"),
        detail=detail or {},
        adapterId=adapter_id,
        interfaceName=interface_name,
        mode=mode,
        mockOutputCreated=default_mock_output_created if mock_output_created is None else mock_output_created,
        realLlmCalled=real_llm_called,
        secretsRead=secrets_read,
        networkAccess=network_access,
        generatedContentCreated=(
            default_generated_content_created
            if generated_content_created is None
            else generated_content_created
        ),
        taskCreated=task_created,
        reviewBypassed=review_bypassed,
        autoPublishAllowed=auto_publish_allowed,
        realPublish=real_publish,
    )
