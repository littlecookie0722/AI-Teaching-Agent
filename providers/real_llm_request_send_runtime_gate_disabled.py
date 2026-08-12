"""Disabled runtime gate for the real LLM request-send path.

This module accepts a completed disabled authorization record write gate model
and prepares a local runtime gate model. It never opens or persists a runtime
gate, disables kill switches, reserves budgets, opens network egress, writes
authorization records, creates or dispatches executors, sends requests, reads
secrets, creates generated content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_authorization_record_write_gate import (
    REAL_LLM_REQUEST_SEND_AUTHORIZATION_RECORD_WRITE_GATE_ID,
    RealLlmRequestSendAuthorizationRecordWriteGateRequest,
    build_real_llm_request_send_authorization_record_write_gate,
    describe_real_llm_request_send_authorization_record_write_gate,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ID = (
    "real_llm_request_send_runtime_gate_disabled"
)


@dataclass(frozen=True)
class RealLlmRequestSendRuntimeGateDisabledRequest(
    RealLlmRequestSendAuthorizationRecordWriteGateRequest
):
    explicit_request_send_runtime_gate_disabled_opt_in: bool = False
    authorization_record_write_gate_confirmed: bool = False
    runtime_gate_scope_confirmed: bool = False
    runtime_gate_record_confirmed: bool = False
    runtime_kill_switch_boundary_confirmed: bool = False
    runtime_budget_boundary_confirmed: bool = False
    runtime_timeout_retry_boundary_confirmed: bool = False
    runtime_concurrency_boundary_confirmed: bool = False
    runtime_network_egress_boundary_confirmed: bool = False
    runtime_secret_read_boundary_confirmed: bool = False
    runtime_client_boundary_confirmed: bool = False
    runtime_response_validation_confirmed: bool = False
    runtime_audit_redaction_confirmed: bool = False
    runtime_rollback_confirmed: bool = False
    runtime_waiting_review_policy_confirmed: bool = False
    no_runtime_gate_open_confirmed: bool = False
    no_runtime_gate_persistence_confirmed: bool = False
    no_kill_switch_disable_confirmed: bool = False
    no_budget_reservation_confirmed: bool = False
    no_network_egress_open_confirmed: bool = False
    no_secret_read_in_runtime_gate_confirmed: bool = False
    no_client_creation_in_runtime_gate_confirmed: bool = False
    no_executor_creation_in_runtime_gate_confirmed: bool = False
    no_executor_dispatch_in_runtime_gate_confirmed: bool = False
    no_request_send_in_runtime_gate_confirmed: bool = False
    no_real_call_authorization_in_runtime_gate_confirmed: bool = False
    no_generated_content_creation_in_runtime_gate_confirmed: bool = False
    no_task_creation_in_runtime_gate_confirmed: bool = False
    no_publish_in_runtime_gate_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendRuntimeGateDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    record_gate_descriptor = describe_real_llm_request_send_authorization_record_write_gate(
        root=root
    )
    return {
        **record_gate_descriptor,
        "requestSendRuntimeGateDisabledId": REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ID,
        "upstreamGateId": REAL_LLM_REQUEST_SEND_AUTHORIZATION_RECORD_WRITE_GATE_ID,
        "mode": "REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ONLY",
        "requestSendRuntimeGateMode": "REQUEST_SEND_RUNTIME_GATE_DISABLED_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "timeoutSeconds": request.timeout_seconds,
        "retryCount": request.retry_count,
        "concurrencyLimit": request.concurrency_limit,
        "reviewer": _clean_text(request.reviewer),
        "approvalRef": _clean_text(request.approval_ref),
        "secretEnv": SECRET_ENV,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "explicitRequestSendRuntimeGateDisabledOptIn": (
            request.explicit_request_send_runtime_gate_disabled_opt_in
        ),
        "authorizationRecordWriteGateConfirmed": (
            request.authorization_record_write_gate_confirmed
        ),
        "runtimeGateScopeConfirmed": request.runtime_gate_scope_confirmed,
        "runtimeGateRecordConfirmed": request.runtime_gate_record_confirmed,
        "runtimeKillSwitchBoundaryConfirmed": (
            request.runtime_kill_switch_boundary_confirmed
        ),
        "runtimeBudgetBoundaryConfirmed": request.runtime_budget_boundary_confirmed,
        "runtimeTimeoutRetryBoundaryConfirmed": (
            request.runtime_timeout_retry_boundary_confirmed
        ),
        "runtimeConcurrencyBoundaryConfirmed": (
            request.runtime_concurrency_boundary_confirmed
        ),
        "runtimeNetworkEgressBoundaryConfirmed": (
            request.runtime_network_egress_boundary_confirmed
        ),
        "runtimeSecretReadBoundaryConfirmed": (
            request.runtime_secret_read_boundary_confirmed
        ),
        "runtimeClientBoundaryConfirmed": request.runtime_client_boundary_confirmed,
        "runtimeResponseValidationConfirmed": (
            request.runtime_response_validation_confirmed
        ),
        "runtimeAuditRedactionConfirmed": request.runtime_audit_redaction_confirmed,
        "runtimeRollbackConfirmed": request.runtime_rollback_confirmed,
        "runtimeWaitingReviewPolicyConfirmed": (
            request.runtime_waiting_review_policy_confirmed
        ),
        "noRuntimeGateOpenConfirmed": request.no_runtime_gate_open_confirmed,
        "noRuntimeGatePersistenceConfirmed": (
            request.no_runtime_gate_persistence_confirmed
        ),
        "noKillSwitchDisableConfirmed": request.no_kill_switch_disable_confirmed,
        "noBudgetReservationConfirmed": request.no_budget_reservation_confirmed,
        "noNetworkEgressOpenConfirmed": request.no_network_egress_open_confirmed,
        "noSecretReadInRuntimeGateConfirmed": (
            request.no_secret_read_in_runtime_gate_confirmed
        ),
        "noClientCreationInRuntimeGateConfirmed": (
            request.no_client_creation_in_runtime_gate_confirmed
        ),
        "noExecutorCreationInRuntimeGateConfirmed": (
            request.no_executor_creation_in_runtime_gate_confirmed
        ),
        "noExecutorDispatchInRuntimeGateConfirmed": (
            request.no_executor_dispatch_in_runtime_gate_confirmed
        ),
        "noRequestSendInRuntimeGateConfirmed": (
            request.no_request_send_in_runtime_gate_confirmed
        ),
        "noRealCallAuthorizationInRuntimeGateConfirmed": (
            request.no_real_call_authorization_in_runtime_gate_confirmed
        ),
        "noGeneratedContentCreationInRuntimeGateConfirmed": (
            request.no_generated_content_creation_in_runtime_gate_confirmed
        ),
        "noTaskCreationInRuntimeGateConfirmed": (
            request.no_task_creation_in_runtime_gate_confirmed
        ),
        "noPublishInRuntimeGateConfirmed": request.no_publish_in_runtime_gate_confirmed,
        "allowedOperations": [
            "authorization_record_write_gate_validation",
            "disabled_runtime_gate_model_generation",
            "future_send_executor_creation_gate_design",
        ],
        "blockedOperations": [
            "runtime_gate_open",
            "runtime_gate_persistence",
            "runtime_kill_switch_disable",
            "runtime_budget_reservation",
            "network_egress_open",
            "authorization_record_write",
            "manual_approval_grant",
            "real_call_authorization",
            "executor_creation",
            "executor_dispatch",
            "request_send",
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "network_request",
            "real_llm_call",
            "generated_content_creation",
            "task_creation",
            "publish",
            "batch_request",
            "streaming_request",
        ],
        "requestSendAuthorizationRecordWriteGateReady": False,
        "requestSendRuntimeGateChecklistReady": False,
        "requestSendRuntimeGateDisabledReady": False,
        "readyForRealRequestSendExecutorCreationGate": False,
        "readyForRealRequestSend": False,
        "runtimeGateModelBuilt": False,
        "runtimeGateMaterialized": False,
        "runtimeGatePersisted": False,
        "runtimeGateOpened": False,
        "runtimeKillSwitchDisabled": False,
        "runtimeBudgetReserved": False,
        "runtimeNetworkEgressOpened": False,
        "authorizationRecordWritten": False,
        "approvalRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendExecutorCreated": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_llm_request_send_runtime_gate_disabled(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendRuntimeGateDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendAuthorizationRecordWriteGateReady": True,
        "requiresExplicitRequestSendRuntimeGateDisabledOptIn": True,
        "requiresAuthorizationRecordWriteGateConfirmation": True,
        "requiresRuntimeGateScopeConfirmation": True,
        "requiresRuntimeGateRecordConfirmation": True,
        "requiresRuntimeKillSwitchBoundaryConfirmation": True,
        "requiresRuntimeBudgetBoundaryConfirmation": True,
        "requiresRuntimeTimeoutRetryBoundaryConfirmation": True,
        "requiresRuntimeConcurrencyBoundaryConfirmation": True,
        "requiresRuntimeNetworkEgressBoundaryConfirmation": True,
        "requiresRuntimeSecretReadBoundaryConfirmation": True,
        "requiresRuntimeClientBoundaryConfirmation": True,
        "requiresRuntimeResponseValidationConfirmation": True,
        "requiresRuntimeAuditRedactionConfirmation": True,
        "requiresRuntimeRollbackConfirmation": True,
        "requiresRuntimeWaitingReviewPolicyConfirmation": True,
        "requiresNoRuntimeGateOpenConfirmation": True,
        "requiresNoRuntimeGatePersistenceConfirmation": True,
        "requiresNoKillSwitchDisableConfirmation": True,
        "requiresNoBudgetReservationConfirmation": True,
        "requiresNoNetworkEgressOpenConfirmation": True,
        "requiresNoSecretReadInRuntimeGateConfirmation": True,
        "requiresNoClientCreationInRuntimeGateConfirmation": True,
        "requiresNoExecutorCreationInRuntimeGateConfirmation": True,
        "requiresNoExecutorDispatchInRuntimeGateConfirmation": True,
        "requiresNoRequestSendInRuntimeGateConfirmation": True,
        "requiresNoRealCallAuthorizationInRuntimeGateConfirmation": True,
        "requiresNoGeneratedContentCreationInRuntimeGateConfirmation": True,
        "requiresNoTaskCreationInRuntimeGateConfirmation": True,
        "requiresNoPublishInRuntimeGateConfirmation": True,
        "realRequestSendPath": "future_real_request_send_executor_creation_gate",
    }


def _validate_provider_scope(request: RealLlmRequestSendRuntimeGateDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send runtime gate currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the request send runtime gate",
                }
            ],
        )


def _runtime_gate_checklist(
    request: RealLlmRequestSendRuntimeGateDisabledRequest,
    *,
    record_gate_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "request_send_authorization_record_write_gate_ready",
            "passed": record_gate_ready,
            "required": True,
        },
        {
            "id": "explicit_request_send_runtime_gate_disabled_opt_in",
            "passed": request.explicit_request_send_runtime_gate_disabled_opt_in,
            "required": True,
        },
        {
            "id": "authorization_record_write_gate_confirmed",
            "passed": request.authorization_record_write_gate_confirmed,
            "required": True,
        },
        {
            "id": "runtime_gate_scope_confirmed",
            "passed": request.runtime_gate_scope_confirmed,
            "required": True,
        },
        {
            "id": "runtime_gate_record_confirmed",
            "passed": request.runtime_gate_record_confirmed,
            "required": True,
        },
        {
            "id": "runtime_kill_switch_boundary_confirmed",
            "passed": request.runtime_kill_switch_boundary_confirmed,
            "required": True,
        },
        {
            "id": "runtime_budget_boundary_confirmed",
            "passed": request.runtime_budget_boundary_confirmed,
            "required": True,
        },
        {
            "id": "runtime_timeout_retry_boundary_confirmed",
            "passed": request.runtime_timeout_retry_boundary_confirmed,
            "required": True,
        },
        {
            "id": "runtime_concurrency_boundary_confirmed",
            "passed": request.runtime_concurrency_boundary_confirmed,
            "required": True,
        },
        {
            "id": "runtime_network_egress_boundary_confirmed",
            "passed": request.runtime_network_egress_boundary_confirmed,
            "required": True,
        },
        {
            "id": "runtime_secret_read_boundary_confirmed",
            "passed": request.runtime_secret_read_boundary_confirmed,
            "required": True,
        },
        {
            "id": "runtime_client_boundary_confirmed",
            "passed": request.runtime_client_boundary_confirmed,
            "required": True,
        },
        {
            "id": "runtime_response_validation_confirmed",
            "passed": request.runtime_response_validation_confirmed,
            "required": True,
        },
        {
            "id": "runtime_audit_redaction_confirmed",
            "passed": request.runtime_audit_redaction_confirmed,
            "required": True,
        },
        {
            "id": "runtime_rollback_confirmed",
            "passed": request.runtime_rollback_confirmed,
            "required": True,
        },
        {
            "id": "runtime_waiting_review_policy_confirmed",
            "passed": request.runtime_waiting_review_policy_confirmed,
            "required": True,
        },
        {
            "id": "no_runtime_gate_open_confirmed",
            "passed": request.no_runtime_gate_open_confirmed,
            "required": True,
        },
        {
            "id": "no_runtime_gate_persistence_confirmed",
            "passed": request.no_runtime_gate_persistence_confirmed,
            "required": True,
        },
        {
            "id": "no_kill_switch_disable_confirmed",
            "passed": request.no_kill_switch_disable_confirmed,
            "required": True,
        },
        {
            "id": "no_budget_reservation_confirmed",
            "passed": request.no_budget_reservation_confirmed,
            "required": True,
        },
        {
            "id": "no_network_egress_open_confirmed",
            "passed": request.no_network_egress_open_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_runtime_gate_confirmed",
            "passed": request.no_secret_read_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_client_creation_in_runtime_gate_confirmed",
            "passed": request.no_client_creation_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_creation_in_runtime_gate_confirmed",
            "passed": request.no_executor_creation_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_in_runtime_gate_confirmed",
            "passed": request.no_executor_dispatch_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_runtime_gate_confirmed",
            "passed": request.no_request_send_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_authorization_in_runtime_gate_confirmed",
            "passed": request.no_real_call_authorization_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_generated_content_creation_in_runtime_gate_confirmed",
            "passed": request.no_generated_content_creation_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_runtime_gate_confirmed",
            "passed": request.no_task_creation_in_runtime_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_runtime_gate_confirmed",
            "passed": request.no_publish_in_runtime_gate_confirmed,
            "required": True,
        },
    ]


def _authorization_record_write_gate_summary(record_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendAuthorizationRecordWriteGateId": record_gate[
            "requestSendAuthorizationRecordWriteGateId"
        ],
        "requestSendAuthorizationTaskDisabledReady": record_gate[
            "requestSendAuthorizationTaskDisabledReady"
        ],
        "authorizationRecordWriteGateReady": record_gate[
            "authorizationRecordWriteGateReady"
        ],
        "readyForRequestSendRuntimeGate": record_gate[
            "readyForRequestSendRuntimeGate"
        ],
        "readyForRealRequestSend": record_gate["readyForRealRequestSend"],
        "authorizationRecordWritten": record_gate["authorizationRecordWritten"],
        "approvalRecordWritten": record_gate["approvalRecordWritten"],
        "manualApprovalGranted": record_gate["manualApprovalGranted"],
        "realCallAuthorized": record_gate["realCallAuthorized"],
        "requestSent": record_gate["requestSent"],
        "networkAccess": record_gate["networkAccess"],
        "realLlmCalled": record_gate["realLlmCalled"],
        "secretValueRead": record_gate["secretValueRead"],
        "generatedContentCreated": record_gate["generatedContentCreated"],
        "taskCreated": record_gate["taskCreated"],
    }


def _runtime_gate_model(
    request: RealLlmRequestSendRuntimeGateDisabledRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "runtimeGateId": REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ID,
        "built": built,
        "runtimeScope": "single_lab_generate_json_request",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "singleRequestOnly": True,
        "labOnly": True,
        "runtimeGateOpenedNow": False,
        "runtimeGatePersistedNow": False,
        "runtimeKillSwitchDisabledNow": False,
        "runtimeBudgetReservedNow": False,
        "networkEgressOpenedNow": False,
        "secretReadAllowedNow": False,
        "clientCreationAllowedNow": False,
        "executorCreationAllowedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureSendExecutorCreationGateRequired": True,
    }


def _runtime_gate_policy() -> dict[str, Any]:
    return {
        "runtimeGatePolicyId": "minimal_real_llm_request_send_runtime_gate_disabled_policy",
        "openRuntimeGateNow": False,
        "persistRuntimeGateNow": False,
        "disableRuntimeKillSwitchNow": False,
        "reserveRuntimeBudgetNow": False,
        "openNetworkEgressNow": False,
        "allowSecretReadNow": False,
        "allowClientCreationNow": False,
        "allowExecutorCreationNow": False,
        "authorizeRealCallNow": False,
        "requiredFutureFields": [
            "authorizationRecordGateId",
            "runtimeGateId",
            "runtimeKillSwitch",
            "budget",
            "timeoutSeconds",
            "retryCount",
            "concurrencyLimit",
            "networkEgressPolicy",
            "secretEnv",
            "providerId",
            "operation",
            "promptId",
            "outputKind",
            "inputRef",
            "targetModelAlias",
        ],
    }


def _send_execution_boundary() -> dict[str, Any]:
    return {
        "sendExecutionBoundaryId": "minimal_real_llm_request_send_runtime_gate_disabled_boundary",
        "runtimeGateMaterialized": False,
        "runtimeGatePersisted": False,
        "runtimeGateOpened": False,
        "runtimeKillSwitchDisabled": False,
        "runtimeBudgetReserved": False,
        "runtimeNetworkEgressOpened": False,
        "authorizationRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendExecutorCreated": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "readyForRealRequestSend": False,
        "nextStage": "real_request_send_executor_creation_gate",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "runtimeGateOpened", "reason": "runtime_gate_disabled_shell_does_not_open_runtime_gate"},
            {"field": "runtimeGatePersisted", "reason": "runtime_gate_disabled_shell_does_not_persist_runtime_gate"},
            {"field": "runtimeKillSwitchDisabled", "reason": "runtime_gate_disabled_shell_keeps_kill_switch_enabled"},
            {"field": "runtimeBudgetReserved", "reason": "runtime_gate_disabled_shell_does_not_reserve_budget"},
            {"field": "runtimeNetworkEgressOpened", "reason": "runtime_gate_disabled_shell_does_not_open_network_egress"},
            {"field": "authorizationRecordWritten", "reason": "runtime_gate_disabled_shell_does_not_write_authorization_records"},
            {"field": "manualApprovalGranted", "reason": "runtime_gate_disabled_shell_does_not_grant_approval"},
            {"field": "realCallAuthorized", "reason": "requires_future_real_request_send_executor_creation_gate"},
            {"field": "requestSent", "reason": "runtime_gate_disabled_shell_does_not_send_requests"},
            {"field": "networkAccess", "reason": "runtime_gate_disabled_shell_does_not_access_network"},
            {"field": "secretValueRead", "reason": "runtime_gate_disabled_shell_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "runtime_gate_disabled_shell_must_not_create_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_runtime_gate_disabled(
    request: RealLlmRequestSendRuntimeGateDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    record_gate = build_real_llm_request_send_authorization_record_write_gate(
        request,
        root=root,
    )
    record_gate_ready = record_gate.get("authorizationRecordWriteGateReady") is True
    checklist = _runtime_gate_checklist(
        request,
        record_gate_ready=record_gate_ready,
    )
    checklist_passed = all(
        item["passed"] is True for item in checklist if item["required"] is True
    )

    return {
        **context,
        "requestSendAuthorizationRecordWriteGateReady": record_gate_ready,
        "requestSendAuthorizationRecordWriteGateSummary": (
            _authorization_record_write_gate_summary(record_gate)
        ),
        "requestSendRuntimeGateChecklist": checklist,
        "requestSendRuntimeGateChecklistReady": checklist_passed,
        "requestSendRuntimeGateDisabledReady": checklist_passed,
        "readyForRealRequestSendExecutorCreationGate": checklist_passed,
        "readyForRealRequestSend": False,
        "runtimeGateModel": _runtime_gate_model(request, built=checklist_passed),
        "runtimeGatePolicy": _runtime_gate_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "runtimeGateModelBuilt": checklist_passed,
        "runtimeGateMaterialized": False,
        "runtimeGatePersisted": False,
        "runtimeGateOpened": False,
        "runtimeKillSwitchDisabled": False,
        "runtimeBudgetReserved": False,
        "runtimeNetworkEgressOpened": False,
        "authorizationRecordWritten": False,
        "approvalRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendExecutorCreated": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "blockedUntil": _blocked_until(checklist),
        "message": (
            "真实 LLM 请求发送运行时门禁禁用模型已生成；当前不会打开运行时门禁、"
            "关闭 kill switch、预留预算、打开网络出口、读取密钥、创建执行器、"
            "授权真实调用、发送请求、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_runtime_gate_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendRuntimeGateDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendRuntimeGateDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            record_gate = build_real_llm_request_send_authorization_record_write_gate(
                request,
                root=root,
            )
        else:
            record_gate = None
    except ProviderError:
        record_gate = None
    if record_gate is not None:
        context["requestSendAuthorizationRecordWriteGateReady"] = bool(
            record_gate.get("authorizationRecordWriteGateReady", False)
        )
        context["requestSendAuthorizationRecordWriteGateSummary"] = (
            _authorization_record_write_gate_summary(record_gate)
        )
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
