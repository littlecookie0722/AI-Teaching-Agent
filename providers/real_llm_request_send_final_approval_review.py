"""Final approval review model for the real LLM request-send path.

This module accepts a completed disabled executor model and prepares a local
final human approval review package. It never grants approval, authorizes a
real call, creates or starts executors, dispatches executors, sends requests,
reads secrets, accesses network, creates generated content, creates tasks, or
publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_executor_disabled import (
    RealLlmRequestSendExecutorDisabledRequest,
    build_real_llm_request_send_executor_disabled,
    describe_real_llm_request_send_executor_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_FINAL_APPROVAL_REVIEW_ID = (
    "real_llm_request_send_final_approval_review"
)


@dataclass(frozen=True)
class RealLlmRequestSendFinalApprovalReviewRequest(
    RealLlmRequestSendExecutorDisabledRequest
):
    explicit_request_send_final_approval_review_opt_in: bool = False
    request_send_executor_disabled_confirmed: bool = False
    final_approver_identity_confirmed: bool = False
    final_approval_scope_confirmed: bool = False
    final_approval_record_location_confirmed: bool = False
    single_request_final_approval_confirmed: bool = False
    lab_only_final_approval_confirmed: bool = False
    provider_prompt_input_final_review_confirmed: bool = False
    cost_timeout_retry_final_review_confirmed: bool = False
    runtime_kill_switch_final_review_confirmed: bool = False
    secret_handling_final_review_confirmed: bool = False
    network_egress_final_review_confirmed: bool = False
    response_validation_final_review_confirmed: bool = False
    waiting_review_policy_final_review_confirmed: bool = False
    audit_redaction_final_review_confirmed: bool = False
    rollback_final_review_confirmed: bool = False
    no_manual_approval_grant_in_final_review_confirmed: bool = False
    no_real_call_authorization_in_final_review_confirmed: bool = False
    no_executor_dispatch_in_final_review_confirmed: bool = False
    no_request_send_in_final_review_confirmed: bool = False
    no_secret_read_in_final_review_confirmed: bool = False
    no_network_access_in_final_review_confirmed: bool = False
    no_generated_content_creation_in_final_review_confirmed: bool = False
    no_task_creation_in_final_review_confirmed: bool = False
    no_publish_in_final_review_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendFinalApprovalReviewRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    executor_descriptor = describe_real_llm_request_send_executor_disabled(root=root)
    return {
        **executor_descriptor,
        "requestSendFinalApprovalReviewId": REAL_LLM_REQUEST_SEND_FINAL_APPROVAL_REVIEW_ID,
        "upstreamGateId": "real_llm_request_send_executor_disabled",
        "mode": "REAL_LLM_REQUEST_SEND_FINAL_APPROVAL_REVIEW_ONLY",
        "approvalReviewMode": "FINAL_HUMAN_APPROVAL_REVIEW_MODEL_ONLY",
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
        "explicitRequestSendFinalApprovalReviewOptIn": (
            request.explicit_request_send_final_approval_review_opt_in
        ),
        "requestSendExecutorDisabledConfirmed": (
            request.request_send_executor_disabled_confirmed
        ),
        "finalApproverIdentityConfirmed": request.final_approver_identity_confirmed,
        "finalApprovalScopeConfirmed": request.final_approval_scope_confirmed,
        "finalApprovalRecordLocationConfirmed": (
            request.final_approval_record_location_confirmed
        ),
        "singleRequestFinalApprovalConfirmed": request.single_request_final_approval_confirmed,
        "labOnlyFinalApprovalConfirmed": request.lab_only_final_approval_confirmed,
        "providerPromptInputFinalReviewConfirmed": (
            request.provider_prompt_input_final_review_confirmed
        ),
        "costTimeoutRetryFinalReviewConfirmed": (
            request.cost_timeout_retry_final_review_confirmed
        ),
        "runtimeKillSwitchFinalReviewConfirmed": (
            request.runtime_kill_switch_final_review_confirmed
        ),
        "secretHandlingFinalReviewConfirmed": request.secret_handling_final_review_confirmed,
        "networkEgressFinalReviewConfirmed": request.network_egress_final_review_confirmed,
        "responseValidationFinalReviewConfirmed": (
            request.response_validation_final_review_confirmed
        ),
        "waitingReviewPolicyFinalReviewConfirmed": (
            request.waiting_review_policy_final_review_confirmed
        ),
        "auditRedactionFinalReviewConfirmed": request.audit_redaction_final_review_confirmed,
        "rollbackFinalReviewConfirmed": request.rollback_final_review_confirmed,
        "noManualApprovalGrantInFinalReviewConfirmed": (
            request.no_manual_approval_grant_in_final_review_confirmed
        ),
        "noRealCallAuthorizationInFinalReviewConfirmed": (
            request.no_real_call_authorization_in_final_review_confirmed
        ),
        "noExecutorDispatchInFinalReviewConfirmed": (
            request.no_executor_dispatch_in_final_review_confirmed
        ),
        "noRequestSendInFinalReviewConfirmed": (
            request.no_request_send_in_final_review_confirmed
        ),
        "noSecretReadInFinalReviewConfirmed": (
            request.no_secret_read_in_final_review_confirmed
        ),
        "noNetworkAccessInFinalReviewConfirmed": (
            request.no_network_access_in_final_review_confirmed
        ),
        "noGeneratedContentCreationInFinalReviewConfirmed": (
            request.no_generated_content_creation_in_final_review_confirmed
        ),
        "noTaskCreationInFinalReviewConfirmed": (
            request.no_task_creation_in_final_review_confirmed
        ),
        "noPublishInFinalReviewConfirmed": request.no_publish_in_final_review_confirmed,
        "allowedOperations": [
            "disabled_send_executor_validation",
            "final_human_approval_review_generation",
            "future_explicit_send_authorization_design",
        ],
        "blockedOperations": [
            "manual_approval_grant",
            "real_call_authorization",
            "approval_record_persistence",
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
        "requestSendExecutorDisabledReady": False,
        "requestSendFinalApprovalChecklistReady": False,
        "requestSendFinalApprovalReviewReady": False,
        "readyForExplicitRealRequestSendAuthorizationTask": False,
        "readyForRealRequestSend": False,
        "finalApprovalReviewPackageBuilt": False,
        "finalApprovalReviewPackageMaterialized": False,
        "finalApprovalReviewPackagePersisted": False,
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


def describe_real_llm_request_send_final_approval_review(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendFinalApprovalReviewRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendExecutorDisabledReady": True,
        "requiresExplicitRequestSendFinalApprovalReviewOptIn": True,
        "requiresRequestSendExecutorDisabledConfirmation": True,
        "requiresFinalApproverIdentityConfirmation": True,
        "requiresFinalApprovalScopeConfirmation": True,
        "requiresFinalApprovalRecordLocationConfirmation": True,
        "requiresSingleRequestFinalApprovalConfirmation": True,
        "requiresLabOnlyFinalApprovalConfirmation": True,
        "requiresProviderPromptInputFinalReviewConfirmation": True,
        "requiresCostTimeoutRetryFinalReviewConfirmation": True,
        "requiresRuntimeKillSwitchFinalReviewConfirmation": True,
        "requiresSecretHandlingFinalReviewConfirmation": True,
        "requiresNetworkEgressFinalReviewConfirmation": True,
        "requiresResponseValidationFinalReviewConfirmation": True,
        "requiresWaitingReviewPolicyFinalReviewConfirmation": True,
        "requiresAuditRedactionFinalReviewConfirmation": True,
        "requiresRollbackFinalReviewConfirmation": True,
        "requiresNoManualApprovalGrantInFinalReviewConfirmation": True,
        "requiresNoRealCallAuthorizationInFinalReviewConfirmation": True,
        "requiresNoExecutorDispatchInFinalReviewConfirmation": True,
        "requiresNoRequestSendInFinalReviewConfirmation": True,
        "requiresNoSecretReadInFinalReviewConfirmation": True,
        "requiresNoNetworkAccessInFinalReviewConfirmation": True,
        "requiresNoGeneratedContentCreationInFinalReviewConfirmation": True,
        "requiresNoTaskCreationInFinalReviewConfirmation": True,
        "requiresNoPublishInFinalReviewConfirmation": True,
        "realCallAuthorizationPath": "future_explicit_real_request_send_authorization_task",
    }


def _validate_provider_scope(request: RealLlmRequestSendFinalApprovalReviewRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send final approval review currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the final approval review",
                }
            ],
        )


def _final_approval_checklist(
    request: RealLlmRequestSendFinalApprovalReviewRequest,
    *,
    executor_disabled_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "request_send_executor_disabled_ready", "passed": executor_disabled_ready, "required": True},
        {
            "id": "explicit_request_send_final_approval_review_opt_in",
            "passed": request.explicit_request_send_final_approval_review_opt_in,
            "required": True,
        },
        {
            "id": "request_send_executor_disabled_confirmed",
            "passed": request.request_send_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "final_approver_identity_confirmed",
            "passed": request.final_approver_identity_confirmed,
            "required": True,
        },
        {
            "id": "final_approval_scope_confirmed",
            "passed": request.final_approval_scope_confirmed,
            "required": True,
        },
        {
            "id": "final_approval_record_location_confirmed",
            "passed": request.final_approval_record_location_confirmed,
            "required": True,
        },
        {
            "id": "single_request_final_approval_confirmed",
            "passed": request.single_request_final_approval_confirmed,
            "required": True,
        },
        {
            "id": "lab_only_final_approval_confirmed",
            "passed": request.lab_only_final_approval_confirmed,
            "required": True,
        },
        {
            "id": "provider_prompt_input_final_review_confirmed",
            "passed": request.provider_prompt_input_final_review_confirmed,
            "required": True,
        },
        {
            "id": "cost_timeout_retry_final_review_confirmed",
            "passed": request.cost_timeout_retry_final_review_confirmed,
            "required": True,
        },
        {
            "id": "runtime_kill_switch_final_review_confirmed",
            "passed": request.runtime_kill_switch_final_review_confirmed,
            "required": True,
        },
        {
            "id": "secret_handling_final_review_confirmed",
            "passed": request.secret_handling_final_review_confirmed,
            "required": True,
        },
        {
            "id": "network_egress_final_review_confirmed",
            "passed": request.network_egress_final_review_confirmed,
            "required": True,
        },
        {
            "id": "response_validation_final_review_confirmed",
            "passed": request.response_validation_final_review_confirmed,
            "required": True,
        },
        {
            "id": "waiting_review_policy_final_review_confirmed",
            "passed": request.waiting_review_policy_final_review_confirmed,
            "required": True,
        },
        {
            "id": "audit_redaction_final_review_confirmed",
            "passed": request.audit_redaction_final_review_confirmed,
            "required": True,
        },
        {
            "id": "rollback_final_review_confirmed",
            "passed": request.rollback_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_manual_approval_grant_in_final_review_confirmed",
            "passed": request.no_manual_approval_grant_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_authorization_in_final_review_confirmed",
            "passed": request.no_real_call_authorization_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_in_final_review_confirmed",
            "passed": request.no_executor_dispatch_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_final_review_confirmed",
            "passed": request.no_request_send_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_final_review_confirmed",
            "passed": request.no_secret_read_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_final_review_confirmed",
            "passed": request.no_network_access_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_generated_content_creation_in_final_review_confirmed",
            "passed": request.no_generated_content_creation_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_final_review_confirmed",
            "passed": request.no_task_creation_in_final_review_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_final_review_confirmed",
            "passed": request.no_publish_in_final_review_confirmed,
            "required": True,
        },
    ]


def _executor_summary(executor: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendExecutorDisabledId": executor["requestSendExecutorDisabledId"],
        "requestSendExecutionRequestDisabledReady": executor[
            "requestSendExecutionRequestDisabledReady"
        ],
        "requestSendExecutorDisabledReady": executor["requestSendExecutorDisabledReady"],
        "readyForFinalRealRequestSendApprovalReview": executor[
            "readyForFinalRealRequestSendApprovalReview"
        ],
        "readyForRealRequestSend": executor["readyForRealRequestSend"],
        "sendExecutorStarted": executor["sendExecutorStarted"],
        "sendExecutorRunCreated": executor["sendExecutorRunCreated"],
        "sendExecutorDispatched": executor["sendExecutorDispatched"],
        "manualApprovalGranted": executor["manualApprovalGranted"],
        "realCallAuthorized": executor["realCallAuthorized"],
        "requestSent": executor["requestSent"],
        "networkAccess": executor["networkAccess"],
        "realLlmCalled": executor["realLlmCalled"],
        "secretValueRead": executor["secretValueRead"],
        "generatedContentCreated": executor["generatedContentCreated"],
        "taskCreated": executor["taskCreated"],
    }


def _final_approval_review_package(
    request: RealLlmRequestSendFinalApprovalReviewRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "reviewPackageId": REAL_LLM_REQUEST_SEND_FINAL_APPROVAL_REVIEW_ID,
        "built": built,
        "approvalScope": "single_lab_generate_json_request",
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
        "manualApprovalGrantedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureExplicitAuthorizationTaskRequired": True,
        "futureHumanApprovalRecordRequired": True,
    }


def _final_approval_policy() -> dict[str, Any]:
    return {
        "finalApprovalPolicyId": "minimal_real_llm_request_send_final_approval_review_policy",
        "materializeApprovalNow": False,
        "persistApprovalNow": False,
        "writeApprovalRecordNow": False,
        "grantManualApprovalNow": False,
        "authorizeRealCallNow": False,
        "requiredFutureFields": [
            "executorId",
            "executionRequestId",
            "authorizationPackageId",
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
        "sendExecutionBoundaryId": "minimal_real_llm_request_send_final_approval_review_boundary",
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "approvalRecordWritten": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "readyForRealRequestSend": False,
        "nextStage": "explicit_real_request_send_authorization_task",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "manualApprovalGranted", "reason": "final_review_does_not_grant_approval"},
            {"field": "realCallAuthorized", "reason": "requires_future_explicit_authorization_task"},
            {"field": "approvalRecordWritten", "reason": "final_review_does_not_write_approval_records"},
            {"field": "requestSent", "reason": "final_review_does_not_send_requests"},
            {"field": "networkAccess", "reason": "final_review_does_not_access_network"},
            {"field": "secretValueRead", "reason": "final_review_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "final_review_must_not_create_ai_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_final_approval_review(
    request: RealLlmRequestSendFinalApprovalReviewRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    executor = build_real_llm_request_send_executor_disabled(request, root=root)
    executor_ready = executor.get("requestSendExecutorDisabledReady") is True
    checklist = _final_approval_checklist(request, executor_disabled_ready=executor_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestSendExecutorDisabledReady": executor_ready,
        "requestSendExecutorSummary": _executor_summary(executor),
        "requestSendFinalApprovalChecklist": checklist,
        "requestSendFinalApprovalChecklistReady": checklist_passed,
        "requestSendFinalApprovalReviewReady": checklist_passed,
        "readyForExplicitRealRequestSendAuthorizationTask": checklist_passed,
        "readyForRealRequestSend": False,
        "finalApprovalReviewPackage": _final_approval_review_package(request, built=checklist_passed),
        "finalApprovalPolicy": _final_approval_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "finalApprovalReviewPackageBuilt": checklist_passed,
        "finalApprovalReviewPackageMaterialized": False,
        "finalApprovalReviewPackagePersisted": False,
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
            "真实 LLM 请求发送最终批准评审模型已生成；当前不会授予人工批准、授权真实调用、"
            "写批准记录、派发执行器、发送请求、联网、读取密钥、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_final_approval_review_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendFinalApprovalReviewRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendFinalApprovalReviewRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            executor = build_real_llm_request_send_executor_disabled(request, root=root)
        else:
            executor = None
    except ProviderError:
        executor = None
    if executor is not None:
        context["requestSendExecutorDisabledReady"] = bool(
            executor.get("requestSendExecutorDisabledReady", False)
        )
        context["requestSendExecutorSummary"] = _executor_summary(executor)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
