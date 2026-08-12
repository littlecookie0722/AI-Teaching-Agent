"""Disabled authorization task model for the real LLM request-send path.

This module accepts a completed final approval review model and prepares a
local disabled authorization task model. It never creates or persists tasks,
queues work, writes approval or authorization records, dispatches executors,
sends requests, reads secrets, accesses network, creates generated content, or
publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_final_approval_review import (
    REAL_LLM_REQUEST_SEND_FINAL_APPROVAL_REVIEW_ID,
    RealLlmRequestSendFinalApprovalReviewRequest,
    build_real_llm_request_send_final_approval_review,
    describe_real_llm_request_send_final_approval_review,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_ID = (
    "real_llm_request_send_authorization_task_disabled"
)


@dataclass(frozen=True)
class RealLlmRequestSendAuthorizationTaskDisabledRequest(
    RealLlmRequestSendFinalApprovalReviewRequest
):
    explicit_request_send_authorization_task_disabled_opt_in: bool = False
    request_send_final_approval_review_confirmed: bool = False
    authorization_task_scope_confirmed: bool = False
    authorization_task_record_confirmed: bool = False
    manual_approval_record_reference_confirmed: bool = False
    final_approver_identity_for_task_confirmed: bool = False
    single_request_authorization_task_confirmed: bool = False
    lab_only_authorization_task_confirmed: bool = False
    provider_prompt_input_authorization_task_confirmed: bool = False
    cost_timeout_retry_authorization_task_confirmed: bool = False
    runtime_kill_switch_authorization_task_confirmed: bool = False
    secret_runtime_boundary_authorization_task_confirmed: bool = False
    network_egress_authorization_task_confirmed: bool = False
    response_validation_authorization_task_confirmed: bool = False
    waiting_review_policy_authorization_task_confirmed: bool = False
    audit_redaction_authorization_task_confirmed: bool = False
    rollback_authorization_task_confirmed: bool = False
    no_task_persistence_in_authorization_task_confirmed: bool = False
    no_queue_in_authorization_task_confirmed: bool = False
    no_executor_dispatch_in_authorization_task_confirmed: bool = False
    no_request_send_in_authorization_task_confirmed: bool = False
    no_secret_read_in_authorization_task_confirmed: bool = False
    no_network_access_in_authorization_task_confirmed: bool = False
    no_generated_content_creation_in_authorization_task_confirmed: bool = False
    no_publish_in_authorization_task_confirmed: bool = False
    no_manual_approval_grant_in_authorization_task_confirmed: bool = False
    no_real_call_authorization_in_authorization_task_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendAuthorizationTaskDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    final_review_descriptor = describe_real_llm_request_send_final_approval_review(
        root=root
    )
    return {
        **final_review_descriptor,
        "requestSendAuthorizationTaskDisabledId": (
            REAL_LLM_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_ID
        ),
        "upstreamGateId": REAL_LLM_REQUEST_SEND_FINAL_APPROVAL_REVIEW_ID,
        "mode": "REAL_LLM_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_ONLY",
        "authorizationTaskMode": (
            "EXPLICIT_REAL_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_MODEL_ONLY"
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
        "explicitRequestSendAuthorizationTaskDisabledOptIn": (
            request.explicit_request_send_authorization_task_disabled_opt_in
        ),
        "requestSendFinalApprovalReviewConfirmed": (
            request.request_send_final_approval_review_confirmed
        ),
        "authorizationTaskScopeConfirmed": request.authorization_task_scope_confirmed,
        "authorizationTaskRecordConfirmed": request.authorization_task_record_confirmed,
        "manualApprovalRecordReferenceConfirmed": (
            request.manual_approval_record_reference_confirmed
        ),
        "finalApproverIdentityForTaskConfirmed": (
            request.final_approver_identity_for_task_confirmed
        ),
        "singleRequestAuthorizationTaskConfirmed": (
            request.single_request_authorization_task_confirmed
        ),
        "labOnlyAuthorizationTaskConfirmed": request.lab_only_authorization_task_confirmed,
        "providerPromptInputAuthorizationTaskConfirmed": (
            request.provider_prompt_input_authorization_task_confirmed
        ),
        "costTimeoutRetryAuthorizationTaskConfirmed": (
            request.cost_timeout_retry_authorization_task_confirmed
        ),
        "runtimeKillSwitchAuthorizationTaskConfirmed": (
            request.runtime_kill_switch_authorization_task_confirmed
        ),
        "secretRuntimeBoundaryAuthorizationTaskConfirmed": (
            request.secret_runtime_boundary_authorization_task_confirmed
        ),
        "networkEgressAuthorizationTaskConfirmed": (
            request.network_egress_authorization_task_confirmed
        ),
        "responseValidationAuthorizationTaskConfirmed": (
            request.response_validation_authorization_task_confirmed
        ),
        "waitingReviewPolicyAuthorizationTaskConfirmed": (
            request.waiting_review_policy_authorization_task_confirmed
        ),
        "auditRedactionAuthorizationTaskConfirmed": (
            request.audit_redaction_authorization_task_confirmed
        ),
        "rollbackAuthorizationTaskConfirmed": request.rollback_authorization_task_confirmed,
        "noTaskPersistenceInAuthorizationTaskConfirmed": (
            request.no_task_persistence_in_authorization_task_confirmed
        ),
        "noQueueInAuthorizationTaskConfirmed": (
            request.no_queue_in_authorization_task_confirmed
        ),
        "noExecutorDispatchInAuthorizationTaskConfirmed": (
            request.no_executor_dispatch_in_authorization_task_confirmed
        ),
        "noRequestSendInAuthorizationTaskConfirmed": (
            request.no_request_send_in_authorization_task_confirmed
        ),
        "noSecretReadInAuthorizationTaskConfirmed": (
            request.no_secret_read_in_authorization_task_confirmed
        ),
        "noNetworkAccessInAuthorizationTaskConfirmed": (
            request.no_network_access_in_authorization_task_confirmed
        ),
        "noGeneratedContentCreationInAuthorizationTaskConfirmed": (
            request.no_generated_content_creation_in_authorization_task_confirmed
        ),
        "noPublishInAuthorizationTaskConfirmed": (
            request.no_publish_in_authorization_task_confirmed
        ),
        "noManualApprovalGrantInAuthorizationTaskConfirmed": (
            request.no_manual_approval_grant_in_authorization_task_confirmed
        ),
        "noRealCallAuthorizationInAuthorizationTaskConfirmed": (
            request.no_real_call_authorization_in_authorization_task_confirmed
        ),
        "allowedOperations": [
            "final_approval_review_validation",
            "disabled_authorization_task_model_generation",
            "future_authorization_record_write_gate_design",
        ],
        "blockedOperations": [
            "authorization_task_persistence",
            "authorization_task_queue",
            "authorization_task_dispatch",
            "manual_approval_grant",
            "real_call_authorization",
            "authorization_record_persistence",
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
        "requestSendFinalApprovalReviewReady": False,
        "requestSendAuthorizationTaskChecklistReady": False,
        "requestSendAuthorizationTaskDisabledReady": False,
        "readyForAuthorizationRecordWriteGate": False,
        "readyForRealRequestSend": False,
        "authorizationTaskModelBuilt": False,
        "authorizationTaskMaterialized": False,
        "authorizationTaskPersisted": False,
        "authorizationTaskQueued": False,
        "authorizationTaskDispatched": False,
        "authorizationTaskCreated": False,
        "authorizationRecordPersisted": False,
        "authorizationRecordWritten": False,
        "approvalRecordPersisted": False,
        "approvalRecordWritten": False,
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
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_llm_request_send_authorization_task_disabled(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendAuthorizationTaskDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendFinalApprovalReviewReady": True,
        "requiresExplicitRequestSendAuthorizationTaskDisabledOptIn": True,
        "requiresRequestSendFinalApprovalReviewConfirmation": True,
        "requiresAuthorizationTaskScopeConfirmation": True,
        "requiresAuthorizationTaskRecordConfirmation": True,
        "requiresManualApprovalRecordReferenceConfirmation": True,
        "requiresFinalApproverIdentityForTaskConfirmation": True,
        "requiresSingleRequestAuthorizationTaskConfirmation": True,
        "requiresLabOnlyAuthorizationTaskConfirmation": True,
        "requiresProviderPromptInputAuthorizationTaskConfirmation": True,
        "requiresCostTimeoutRetryAuthorizationTaskConfirmation": True,
        "requiresRuntimeKillSwitchAuthorizationTaskConfirmation": True,
        "requiresSecretRuntimeBoundaryAuthorizationTaskConfirmation": True,
        "requiresNetworkEgressAuthorizationTaskConfirmation": True,
        "requiresResponseValidationAuthorizationTaskConfirmation": True,
        "requiresWaitingReviewPolicyAuthorizationTaskConfirmation": True,
        "requiresAuditRedactionAuthorizationTaskConfirmation": True,
        "requiresRollbackAuthorizationTaskConfirmation": True,
        "requiresNoTaskPersistenceInAuthorizationTaskConfirmation": True,
        "requiresNoQueueInAuthorizationTaskConfirmation": True,
        "requiresNoExecutorDispatchInAuthorizationTaskConfirmation": True,
        "requiresNoRequestSendInAuthorizationTaskConfirmation": True,
        "requiresNoSecretReadInAuthorizationTaskConfirmation": True,
        "requiresNoNetworkAccessInAuthorizationTaskConfirmation": True,
        "requiresNoGeneratedContentCreationInAuthorizationTaskConfirmation": True,
        "requiresNoPublishInAuthorizationTaskConfirmation": True,
        "requiresNoManualApprovalGrantInAuthorizationTaskConfirmation": True,
        "requiresNoRealCallAuthorizationInAuthorizationTaskConfirmation": True,
        "realCallAuthorizationPath": "future_authorization_record_write_gate",
    }


def _validate_provider_scope(
    request: RealLlmRequestSendAuthorizationTaskDisabledRequest,
) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send authorization task disabled currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the disabled authorization task",
                }
            ],
        )


def _authorization_task_checklist(
    request: RealLlmRequestSendAuthorizationTaskDisabledRequest,
    *,
    final_review_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "request_send_final_approval_review_ready", "passed": final_review_ready, "required": True},
        {
            "id": "explicit_request_send_authorization_task_disabled_opt_in",
            "passed": request.explicit_request_send_authorization_task_disabled_opt_in,
            "required": True,
        },
        {
            "id": "request_send_final_approval_review_confirmed",
            "passed": request.request_send_final_approval_review_confirmed,
            "required": True,
        },
        {
            "id": "authorization_task_scope_confirmed",
            "passed": request.authorization_task_scope_confirmed,
            "required": True,
        },
        {
            "id": "authorization_task_record_confirmed",
            "passed": request.authorization_task_record_confirmed,
            "required": True,
        },
        {
            "id": "manual_approval_record_reference_confirmed",
            "passed": request.manual_approval_record_reference_confirmed,
            "required": True,
        },
        {
            "id": "final_approver_identity_for_task_confirmed",
            "passed": request.final_approver_identity_for_task_confirmed,
            "required": True,
        },
        {
            "id": "single_request_authorization_task_confirmed",
            "passed": request.single_request_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "lab_only_authorization_task_confirmed",
            "passed": request.lab_only_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "provider_prompt_input_authorization_task_confirmed",
            "passed": request.provider_prompt_input_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "cost_timeout_retry_authorization_task_confirmed",
            "passed": request.cost_timeout_retry_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "runtime_kill_switch_authorization_task_confirmed",
            "passed": request.runtime_kill_switch_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "secret_runtime_boundary_authorization_task_confirmed",
            "passed": request.secret_runtime_boundary_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "network_egress_authorization_task_confirmed",
            "passed": request.network_egress_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "response_validation_authorization_task_confirmed",
            "passed": request.response_validation_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "waiting_review_policy_authorization_task_confirmed",
            "passed": request.waiting_review_policy_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "audit_redaction_authorization_task_confirmed",
            "passed": request.audit_redaction_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "rollback_authorization_task_confirmed",
            "passed": request.rollback_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_task_persistence_in_authorization_task_confirmed",
            "passed": request.no_task_persistence_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_queue_in_authorization_task_confirmed",
            "passed": request.no_queue_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_in_authorization_task_confirmed",
            "passed": request.no_executor_dispatch_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_authorization_task_confirmed",
            "passed": request.no_request_send_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_authorization_task_confirmed",
            "passed": request.no_secret_read_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_authorization_task_confirmed",
            "passed": request.no_network_access_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_generated_content_creation_in_authorization_task_confirmed",
            "passed": request.no_generated_content_creation_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_authorization_task_confirmed",
            "passed": request.no_publish_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_manual_approval_grant_in_authorization_task_confirmed",
            "passed": request.no_manual_approval_grant_in_authorization_task_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_authorization_in_authorization_task_confirmed",
            "passed": request.no_real_call_authorization_in_authorization_task_confirmed,
            "required": True,
        },
    ]


def _final_approval_summary(final_review: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendFinalApprovalReviewId": final_review[
            "requestSendFinalApprovalReviewId"
        ],
        "requestSendExecutorDisabledReady": final_review[
            "requestSendExecutorDisabledReady"
        ],
        "requestSendFinalApprovalReviewReady": final_review[
            "requestSendFinalApprovalReviewReady"
        ],
        "readyForExplicitRealRequestSendAuthorizationTask": final_review[
            "readyForExplicitRealRequestSendAuthorizationTask"
        ],
        "readyForRealRequestSend": final_review["readyForRealRequestSend"],
        "manualApprovalGranted": final_review["manualApprovalGranted"],
        "realCallAuthorized": final_review["realCallAuthorized"],
        "approvalRecordWritten": final_review["approvalRecordWritten"],
        "requestSent": final_review["requestSent"],
        "networkAccess": final_review["networkAccess"],
        "realLlmCalled": final_review["realLlmCalled"],
        "secretValueRead": final_review["secretValueRead"],
        "generatedContentCreated": final_review["generatedContentCreated"],
        "taskCreated": final_review["taskCreated"],
    }


def _authorization_task_model(
    request: RealLlmRequestSendAuthorizationTaskDisabledRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "authorizationTaskId": REAL_LLM_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_ID,
        "built": built,
        "taskScope": "single_lab_generate_json_request",
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
        "taskCreatedNow": False,
        "taskQueuedNow": False,
        "taskDispatchedNow": False,
        "authorizationRecordWrittenNow": False,
        "manualApprovalGrantedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureAuthorizationRecordWriteGateRequired": True,
    }


def _authorization_task_policy() -> dict[str, Any]:
    return {
        "authorizationTaskPolicyId": "minimal_real_llm_request_send_authorization_task_disabled_policy",
        "materializeTaskNow": False,
        "persistTaskNow": False,
        "queueTaskNow": False,
        "dispatchTaskNow": False,
        "writeAuthorizationRecordNow": False,
        "grantManualApprovalNow": False,
        "authorizeRealCallNow": False,
        "requiredFutureFields": [
            "finalApprovalReviewId",
            "authorizationTaskId",
            "authorizationRecordId",
            "providerId",
            "operation",
            "promptId",
            "outputKind",
            "inputRef",
            "targetModelAlias",
            "approvalRef",
            "reviewer",
            "runtimeKillSwitch",
            "costLimit",
            "timeoutSeconds",
            "retryCount",
        ],
    }


def _send_execution_boundary() -> dict[str, Any]:
    return {
        "sendExecutionBoundaryId": "minimal_real_llm_request_send_authorization_task_disabled_boundary",
        "authorizationTaskCreated": False,
        "authorizationTaskPersisted": False,
        "authorizationTaskQueued": False,
        "authorizationTaskDispatched": False,
        "authorizationRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "readyForRealRequestSend": False,
        "nextStage": "authorization_record_write_gate",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "authorizationTaskCreated", "reason": "disabled_task_model_does_not_create_tasks"},
            {"field": "authorizationTaskPersisted", "reason": "disabled_task_model_does_not_persist_tasks"},
            {"field": "authorizationTaskQueued", "reason": "disabled_task_model_does_not_queue_tasks"},
            {"field": "authorizationTaskDispatched", "reason": "disabled_task_model_does_not_dispatch_tasks"},
            {"field": "authorizationRecordWritten", "reason": "requires_future_authorization_record_write_gate"},
            {"field": "manualApprovalGranted", "reason": "disabled_task_model_does_not_grant_approval"},
            {"field": "realCallAuthorized", "reason": "requires_future_authorization_record_write_gate"},
            {"field": "requestSent", "reason": "disabled_task_model_does_not_send_requests"},
            {"field": "networkAccess", "reason": "disabled_task_model_does_not_access_network"},
            {"field": "secretValueRead", "reason": "disabled_task_model_does_not_read_secret_values"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_authorization_task_disabled(
    request: RealLlmRequestSendAuthorizationTaskDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    final_review = build_real_llm_request_send_final_approval_review(request, root=root)
    final_review_ready = final_review.get("requestSendFinalApprovalReviewReady") is True
    checklist = _authorization_task_checklist(
        request,
        final_review_ready=final_review_ready,
    )
    checklist_passed = all(
        item["passed"] is True for item in checklist if item["required"] is True
    )

    return {
        **context,
        "requestSendFinalApprovalReviewReady": final_review_ready,
        "requestSendFinalApprovalReviewSummary": _final_approval_summary(final_review),
        "requestSendAuthorizationTaskChecklist": checklist,
        "requestSendAuthorizationTaskChecklistReady": checklist_passed,
        "requestSendAuthorizationTaskDisabledReady": checklist_passed,
        "readyForAuthorizationRecordWriteGate": checklist_passed,
        "readyForRealRequestSend": False,
        "authorizationTaskModel": _authorization_task_model(
            request,
            built=checklist_passed,
        ),
        "authorizationTaskPolicy": _authorization_task_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "authorizationTaskModelBuilt": checklist_passed,
        "authorizationTaskMaterialized": False,
        "authorizationTaskPersisted": False,
        "authorizationTaskQueued": False,
        "authorizationTaskDispatched": False,
        "authorizationTaskCreated": False,
        "authorizationRecordPersisted": False,
        "authorizationRecordWritten": False,
        "approvalRecordPersisted": False,
        "approvalRecordWritten": False,
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
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "blockedUntil": _blocked_until(checklist),
        "message": (
            "真实 LLM 请求发送授权任务禁用模型已生成；当前不会创建、持久化、入队或派发任务，"
            "不会写授权记录、授予人工批准、授权真实调用、发送请求、联网、读取密钥或发布。"
        ),
    }


def build_real_llm_request_send_authorization_task_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendAuthorizationTaskDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendAuthorizationTaskDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            final_review = build_real_llm_request_send_final_approval_review(
                request,
                root=root,
            )
        else:
            final_review = None
    except ProviderError:
        final_review = None
    if final_review is not None:
        context["requestSendFinalApprovalReviewReady"] = bool(
            final_review.get("requestSendFinalApprovalReviewReady", False)
        )
        context["requestSendFinalApprovalReviewSummary"] = _final_approval_summary(
            final_review
        )
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
