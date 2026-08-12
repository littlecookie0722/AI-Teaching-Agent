"""Disabled authorization record write gate for the real LLM request-send path.

This module accepts a completed disabled authorization task model and prepares
a local authorization record write gate model. It never writes authorization or
approval records, grants approval, authorizes real calls, creates or dispatches
executors, sends requests, reads secrets, accesses network, creates generated
content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_authorization_task_disabled import (
    REAL_LLM_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_ID,
    RealLlmRequestSendAuthorizationTaskDisabledRequest,
    build_real_llm_request_send_authorization_task_disabled,
    describe_real_llm_request_send_authorization_task_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_AUTHORIZATION_RECORD_WRITE_GATE_ID = (
    "real_llm_request_send_authorization_record_write_gate"
)


@dataclass(frozen=True)
class RealLlmRequestSendAuthorizationRecordWriteGateRequest(
    RealLlmRequestSendAuthorizationTaskDisabledRequest
):
    explicit_authorization_record_write_gate_opt_in: bool = False
    authorization_task_disabled_confirmed: bool = False
    authorization_record_scope_confirmed: bool = False
    authorization_record_storage_boundary_confirmed: bool = False
    authorization_record_schema_confirmed: bool = False
    approval_record_reference_confirmed: bool = False
    final_approver_identity_for_record_confirmed: bool = False
    single_request_authorization_record_confirmed: bool = False
    lab_only_authorization_record_confirmed: bool = False
    provider_prompt_input_authorization_record_confirmed: bool = False
    cost_timeout_retry_authorization_record_confirmed: bool = False
    runtime_kill_switch_authorization_record_confirmed: bool = False
    secret_runtime_boundary_authorization_record_confirmed: bool = False
    network_egress_authorization_record_confirmed: bool = False
    response_validation_authorization_record_confirmed: bool = False
    waiting_review_policy_authorization_record_confirmed: bool = False
    audit_redaction_authorization_record_confirmed: bool = False
    rollback_authorization_record_confirmed: bool = False
    no_authorization_record_write_confirmed: bool = False
    no_approval_record_write_confirmed: bool = False
    no_manual_approval_grant_in_record_gate_confirmed: bool = False
    no_real_call_authorization_in_record_gate_confirmed: bool = False
    no_executor_dispatch_in_record_gate_confirmed: bool = False
    no_request_send_in_record_gate_confirmed: bool = False
    no_secret_read_in_record_gate_confirmed: bool = False
    no_network_access_in_record_gate_confirmed: bool = False
    no_generated_content_creation_in_record_gate_confirmed: bool = False
    no_task_creation_in_record_gate_confirmed: bool = False
    no_publish_in_record_gate_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendAuthorizationRecordWriteGateRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    authorization_task_descriptor = (
        describe_real_llm_request_send_authorization_task_disabled(root=root)
    )
    return {
        **authorization_task_descriptor,
        "requestSendAuthorizationRecordWriteGateId": (
            REAL_LLM_REQUEST_SEND_AUTHORIZATION_RECORD_WRITE_GATE_ID
        ),
        "upstreamGateId": REAL_LLM_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_ID,
        "mode": "REAL_LLM_REQUEST_SEND_AUTHORIZATION_RECORD_WRITE_GATE_ONLY",
        "authorizationRecordWriteGateMode": (
            "AUTHORIZATION_RECORD_WRITE_GATE_DISABLED_MODEL_ONLY"
        ),
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
        "explicitAuthorizationRecordWriteGateOptIn": (
            request.explicit_authorization_record_write_gate_opt_in
        ),
        "authorizationTaskDisabledConfirmed": (
            request.authorization_task_disabled_confirmed
        ),
        "authorizationRecordScopeConfirmed": (
            request.authorization_record_scope_confirmed
        ),
        "authorizationRecordStorageBoundaryConfirmed": (
            request.authorization_record_storage_boundary_confirmed
        ),
        "authorizationRecordSchemaConfirmed": (
            request.authorization_record_schema_confirmed
        ),
        "approvalRecordReferenceConfirmed": request.approval_record_reference_confirmed,
        "finalApproverIdentityForRecordConfirmed": (
            request.final_approver_identity_for_record_confirmed
        ),
        "singleRequestAuthorizationRecordConfirmed": (
            request.single_request_authorization_record_confirmed
        ),
        "labOnlyAuthorizationRecordConfirmed": (
            request.lab_only_authorization_record_confirmed
        ),
        "providerPromptInputAuthorizationRecordConfirmed": (
            request.provider_prompt_input_authorization_record_confirmed
        ),
        "costTimeoutRetryAuthorizationRecordConfirmed": (
            request.cost_timeout_retry_authorization_record_confirmed
        ),
        "runtimeKillSwitchAuthorizationRecordConfirmed": (
            request.runtime_kill_switch_authorization_record_confirmed
        ),
        "secretRuntimeBoundaryAuthorizationRecordConfirmed": (
            request.secret_runtime_boundary_authorization_record_confirmed
        ),
        "networkEgressAuthorizationRecordConfirmed": (
            request.network_egress_authorization_record_confirmed
        ),
        "responseValidationAuthorizationRecordConfirmed": (
            request.response_validation_authorization_record_confirmed
        ),
        "waitingReviewPolicyAuthorizationRecordConfirmed": (
            request.waiting_review_policy_authorization_record_confirmed
        ),
        "auditRedactionAuthorizationRecordConfirmed": (
            request.audit_redaction_authorization_record_confirmed
        ),
        "rollbackAuthorizationRecordConfirmed": (
            request.rollback_authorization_record_confirmed
        ),
        "noAuthorizationRecordWriteConfirmed": (
            request.no_authorization_record_write_confirmed
        ),
        "noApprovalRecordWriteConfirmed": request.no_approval_record_write_confirmed,
        "noManualApprovalGrantInRecordGateConfirmed": (
            request.no_manual_approval_grant_in_record_gate_confirmed
        ),
        "noRealCallAuthorizationInRecordGateConfirmed": (
            request.no_real_call_authorization_in_record_gate_confirmed
        ),
        "noExecutorDispatchInRecordGateConfirmed": (
            request.no_executor_dispatch_in_record_gate_confirmed
        ),
        "noRequestSendInRecordGateConfirmed": (
            request.no_request_send_in_record_gate_confirmed
        ),
        "noSecretReadInRecordGateConfirmed": (
            request.no_secret_read_in_record_gate_confirmed
        ),
        "noNetworkAccessInRecordGateConfirmed": (
            request.no_network_access_in_record_gate_confirmed
        ),
        "noGeneratedContentCreationInRecordGateConfirmed": (
            request.no_generated_content_creation_in_record_gate_confirmed
        ),
        "noTaskCreationInRecordGateConfirmed": (
            request.no_task_creation_in_record_gate_confirmed
        ),
        "noPublishInRecordGateConfirmed": request.no_publish_in_record_gate_confirmed,
        "allowedOperations": [
            "disabled_authorization_task_validation",
            "authorization_record_write_gate_model_generation",
            "future_request_send_runtime_gate_design",
        ],
        "blockedOperations": [
            "authorization_record_persistence",
            "authorization_record_write",
            "approval_record_persistence",
            "approval_record_write",
            "manual_approval_grant",
            "real_call_authorization",
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
        "requestSendAuthorizationTaskDisabledReady": False,
        "authorizationRecordWriteGateChecklistReady": False,
        "authorizationRecordWriteGateReady": False,
        "readyForRequestSendRuntimeGate": False,
        "readyForRealRequestSend": False,
        "authorizationRecordWriteGateModelBuilt": False,
        "authorizationRecordMaterialized": False,
        "authorizationRecordPersisted": False,
        "authorizationRecordWritten": False,
        "approvalRecordPersisted": False,
        "approvalRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "secretValueLogged": False,
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


def describe_real_llm_request_send_authorization_record_write_gate(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendAuthorizationRecordWriteGateRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendAuthorizationTaskDisabledReady": True,
        "requiresExplicitAuthorizationRecordWriteGateOptIn": True,
        "requiresAuthorizationTaskDisabledConfirmation": True,
        "requiresAuthorizationRecordScopeConfirmation": True,
        "requiresAuthorizationRecordStorageBoundaryConfirmation": True,
        "requiresAuthorizationRecordSchemaConfirmation": True,
        "requiresApprovalRecordReferenceConfirmation": True,
        "requiresFinalApproverIdentityForRecordConfirmation": True,
        "requiresSingleRequestAuthorizationRecordConfirmation": True,
        "requiresLabOnlyAuthorizationRecordConfirmation": True,
        "requiresProviderPromptInputAuthorizationRecordConfirmation": True,
        "requiresCostTimeoutRetryAuthorizationRecordConfirmation": True,
        "requiresRuntimeKillSwitchAuthorizationRecordConfirmation": True,
        "requiresSecretRuntimeBoundaryAuthorizationRecordConfirmation": True,
        "requiresNetworkEgressAuthorizationRecordConfirmation": True,
        "requiresResponseValidationAuthorizationRecordConfirmation": True,
        "requiresWaitingReviewPolicyAuthorizationRecordConfirmation": True,
        "requiresAuditRedactionAuthorizationRecordConfirmation": True,
        "requiresRollbackAuthorizationRecordConfirmation": True,
        "requiresNoAuthorizationRecordWriteConfirmation": True,
        "requiresNoApprovalRecordWriteConfirmation": True,
        "requiresNoManualApprovalGrantInRecordGateConfirmation": True,
        "requiresNoRealCallAuthorizationInRecordGateConfirmation": True,
        "requiresNoExecutorDispatchInRecordGateConfirmation": True,
        "requiresNoRequestSendInRecordGateConfirmation": True,
        "requiresNoSecretReadInRecordGateConfirmation": True,
        "requiresNoNetworkAccessInRecordGateConfirmation": True,
        "requiresNoGeneratedContentCreationInRecordGateConfirmation": True,
        "requiresNoTaskCreationInRecordGateConfirmation": True,
        "requiresNoPublishInRecordGateConfirmation": True,
        "realCallAuthorizationPath": "future_request_send_runtime_gate",
    }


def _validate_provider_scope(
    request: RealLlmRequestSendAuthorizationRecordWriteGateRequest,
) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send authorization record write gate currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the authorization record write gate",
                }
            ],
        )


def _record_gate_checklist(
    request: RealLlmRequestSendAuthorizationRecordWriteGateRequest,
    *,
    authorization_task_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "request_send_authorization_task_disabled_ready", "passed": authorization_task_ready, "required": True},
        {
            "id": "explicit_authorization_record_write_gate_opt_in",
            "passed": request.explicit_authorization_record_write_gate_opt_in,
            "required": True,
        },
        {
            "id": "authorization_task_disabled_confirmed",
            "passed": request.authorization_task_disabled_confirmed,
            "required": True,
        },
        {
            "id": "authorization_record_scope_confirmed",
            "passed": request.authorization_record_scope_confirmed,
            "required": True,
        },
        {
            "id": "authorization_record_storage_boundary_confirmed",
            "passed": request.authorization_record_storage_boundary_confirmed,
            "required": True,
        },
        {
            "id": "authorization_record_schema_confirmed",
            "passed": request.authorization_record_schema_confirmed,
            "required": True,
        },
        {
            "id": "approval_record_reference_confirmed",
            "passed": request.approval_record_reference_confirmed,
            "required": True,
        },
        {
            "id": "final_approver_identity_for_record_confirmed",
            "passed": request.final_approver_identity_for_record_confirmed,
            "required": True,
        },
        {
            "id": "single_request_authorization_record_confirmed",
            "passed": request.single_request_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "lab_only_authorization_record_confirmed",
            "passed": request.lab_only_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "provider_prompt_input_authorization_record_confirmed",
            "passed": request.provider_prompt_input_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "cost_timeout_retry_authorization_record_confirmed",
            "passed": request.cost_timeout_retry_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "runtime_kill_switch_authorization_record_confirmed",
            "passed": request.runtime_kill_switch_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "secret_runtime_boundary_authorization_record_confirmed",
            "passed": request.secret_runtime_boundary_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "network_egress_authorization_record_confirmed",
            "passed": request.network_egress_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "response_validation_authorization_record_confirmed",
            "passed": request.response_validation_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "waiting_review_policy_authorization_record_confirmed",
            "passed": request.waiting_review_policy_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "audit_redaction_authorization_record_confirmed",
            "passed": request.audit_redaction_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "rollback_authorization_record_confirmed",
            "passed": request.rollback_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "no_authorization_record_write_confirmed",
            "passed": request.no_authorization_record_write_confirmed,
            "required": True,
        },
        {
            "id": "no_approval_record_write_confirmed",
            "passed": request.no_approval_record_write_confirmed,
            "required": True,
        },
        {
            "id": "no_manual_approval_grant_in_record_gate_confirmed",
            "passed": request.no_manual_approval_grant_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_authorization_in_record_gate_confirmed",
            "passed": request.no_real_call_authorization_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_in_record_gate_confirmed",
            "passed": request.no_executor_dispatch_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_record_gate_confirmed",
            "passed": request.no_request_send_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_record_gate_confirmed",
            "passed": request.no_secret_read_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_record_gate_confirmed",
            "passed": request.no_network_access_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_generated_content_creation_in_record_gate_confirmed",
            "passed": request.no_generated_content_creation_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_record_gate_confirmed",
            "passed": request.no_task_creation_in_record_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_record_gate_confirmed",
            "passed": request.no_publish_in_record_gate_confirmed,
            "required": True,
        },
    ]


def _authorization_task_summary(authorization_task: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendAuthorizationTaskDisabledId": authorization_task[
            "requestSendAuthorizationTaskDisabledId"
        ],
        "requestSendFinalApprovalReviewReady": authorization_task[
            "requestSendFinalApprovalReviewReady"
        ],
        "requestSendAuthorizationTaskDisabledReady": authorization_task[
            "requestSendAuthorizationTaskDisabledReady"
        ],
        "readyForAuthorizationRecordWriteGate": authorization_task[
            "readyForAuthorizationRecordWriteGate"
        ],
        "readyForRealRequestSend": authorization_task["readyForRealRequestSend"],
        "authorizationTaskCreated": authorization_task["authorizationTaskCreated"],
        "authorizationTaskPersisted": authorization_task["authorizationTaskPersisted"],
        "authorizationTaskQueued": authorization_task["authorizationTaskQueued"],
        "authorizationTaskDispatched": authorization_task["authorizationTaskDispatched"],
        "authorizationRecordWritten": authorization_task["authorizationRecordWritten"],
        "manualApprovalGranted": authorization_task["manualApprovalGranted"],
        "realCallAuthorized": authorization_task["realCallAuthorized"],
        "requestSent": authorization_task["requestSent"],
        "networkAccess": authorization_task["networkAccess"],
        "realLlmCalled": authorization_task["realLlmCalled"],
        "secretValueRead": authorization_task["secretValueRead"],
        "generatedContentCreated": authorization_task["generatedContentCreated"],
        "taskCreated": authorization_task["taskCreated"],
    }


def _record_write_gate_model(
    request: RealLlmRequestSendAuthorizationRecordWriteGateRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "recordWriteGateId": REAL_LLM_REQUEST_SEND_AUTHORIZATION_RECORD_WRITE_GATE_ID,
        "built": built,
        "recordScope": "single_lab_generate_json_request",
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
        "authorizationRecordWrittenNow": False,
        "authorizationRecordPersistedNow": False,
        "approvalRecordWrittenNow": False,
        "manualApprovalGrantedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureRequestSendRuntimeGateRequired": True,
    }


def _record_write_policy() -> dict[str, Any]:
    return {
        "authorizationRecordWritePolicyId": "minimal_real_llm_request_send_authorization_record_write_gate_policy",
        "materializeRecordNow": False,
        "persistAuthorizationRecordNow": False,
        "writeAuthorizationRecordNow": False,
        "writeApprovalRecordNow": False,
        "grantManualApprovalNow": False,
        "authorizeRealCallNow": False,
        "requiredFutureFields": [
            "authorizationTaskId",
            "authorizationRecordId",
            "approvalRecordRef",
            "providerId",
            "operation",
            "promptId",
            "outputKind",
            "inputRef",
            "targetModelAlias",
            "reviewer",
            "runtimeKillSwitch",
            "costLimit",
            "timeoutSeconds",
            "retryCount",
        ],
    }


def _send_execution_boundary() -> dict[str, Any]:
    return {
        "sendExecutionBoundaryId": "minimal_real_llm_request_send_authorization_record_write_gate_boundary",
        "authorizationRecordMaterialized": False,
        "authorizationRecordPersisted": False,
        "authorizationRecordWritten": False,
        "approvalRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "readyForRealRequestSend": False,
        "nextStage": "request_send_runtime_gate",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "authorizationRecordWritten", "reason": "record_gate_does_not_write_authorization_records"},
            {"field": "authorizationRecordPersisted", "reason": "record_gate_does_not_persist_authorization_records"},
            {"field": "approvalRecordWritten", "reason": "record_gate_does_not_write_approval_records"},
            {"field": "manualApprovalGranted", "reason": "record_gate_does_not_grant_approval"},
            {"field": "realCallAuthorized", "reason": "requires_future_request_send_runtime_gate"},
            {"field": "requestSent", "reason": "record_gate_does_not_send_requests"},
            {"field": "networkAccess", "reason": "record_gate_does_not_access_network"},
            {"field": "secretValueRead", "reason": "record_gate_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "record_gate_must_not_create_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_authorization_record_write_gate(
    request: RealLlmRequestSendAuthorizationRecordWriteGateRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    authorization_task = build_real_llm_request_send_authorization_task_disabled(
        request,
        root=root,
    )
    authorization_task_ready = (
        authorization_task.get("requestSendAuthorizationTaskDisabledReady") is True
    )
    checklist = _record_gate_checklist(
        request,
        authorization_task_ready=authorization_task_ready,
    )
    checklist_passed = all(
        item["passed"] is True for item in checklist if item["required"] is True
    )

    return {
        **context,
        "requestSendAuthorizationTaskDisabledReady": authorization_task_ready,
        "requestSendAuthorizationTaskSummary": _authorization_task_summary(
            authorization_task
        ),
        "authorizationRecordWriteGateChecklist": checklist,
        "authorizationRecordWriteGateChecklistReady": checklist_passed,
        "authorizationRecordWriteGateReady": checklist_passed,
        "readyForRequestSendRuntimeGate": checklist_passed,
        "readyForRealRequestSend": False,
        "authorizationRecordWriteGateModel": _record_write_gate_model(
            request,
            built=checklist_passed,
        ),
        "authorizationRecordWritePolicy": _record_write_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "authorizationRecordWriteGateModelBuilt": checklist_passed,
        "authorizationRecordMaterialized": False,
        "authorizationRecordPersisted": False,
        "authorizationRecordWritten": False,
        "approvalRecordPersisted": False,
        "approvalRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "secretValueLogged": False,
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
            "真实 LLM 请求发送授权记录写入门禁模型已生成；当前不会写授权记录或批准记录，"
            "不会授予人工批准、授权真实调用、发送请求、联网、读取密钥、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_authorization_record_write_gate_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendAuthorizationRecordWriteGateRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendAuthorizationRecordWriteGateRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            authorization_task = build_real_llm_request_send_authorization_task_disabled(
                request,
                root=root,
            )
        else:
            authorization_task = None
    except ProviderError:
        authorization_task = None
    if authorization_task is not None:
        context["requestSendAuthorizationTaskDisabledReady"] = bool(
            authorization_task.get("requestSendAuthorizationTaskDisabledReady", False)
        )
        context["requestSendAuthorizationTaskSummary"] = _authorization_task_summary(
            authorization_task
        )
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
