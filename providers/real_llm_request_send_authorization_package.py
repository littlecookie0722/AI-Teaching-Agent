"""Final authorization package model for the minimal real LLM request send.

This module turns the disabled minimal-call send executor model into a local
authorization package for future human review. It never grants approval,
authorizes a real call, materializes a send executor, sends a request, reads
secret values, accesses network, creates generated content, creates tasks, or
publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_minimal_call_send_executor_disabled import (
    RealLlmMinimalCallSendExecutorDisabledRequest,
    prepare_real_llm_minimal_call_send_executor_disabled,
    describe_real_llm_minimal_call_send_executor_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_AUTHORIZATION_PACKAGE_ID = "real_llm_request_send_authorization_package"


@dataclass(frozen=True)
class RealLlmRequestSendAuthorizationPackageRequest(RealLlmMinimalCallSendExecutorDisabledRequest):
    explicit_request_send_authorization_package_opt_in: bool = False
    send_executor_disabled_confirmed_for_authorization: bool = False
    authorization_scope_confirmed: bool = False
    send_approver_identity_confirmed: bool = False
    approval_record_location_confirmed: bool = False
    single_request_authorization_confirmed: bool = False
    lab_only_authorization_confirmed: bool = False
    provider_prompt_input_confirmed: bool = False
    cost_timeout_retry_confirmed_for_send: bool = False
    secret_handling_confirmed_for_send: bool = False
    network_egress_confirmed_for_send: bool = False
    response_validation_confirmed_for_send: bool = False
    waiting_review_policy_confirmed_for_send: bool = False
    audit_redaction_confirmed_for_send: bool = False
    rollback_confirmed_for_send: bool = False
    no_manual_approval_grant_in_package_confirmed: bool = False
    no_real_call_authorization_in_package_confirmed: bool = False
    no_request_send_in_authorization_package_confirmed: bool = False
    no_secret_read_in_authorization_package_confirmed: bool = False
    no_network_access_in_authorization_package_confirmed: bool = False
    no_task_creation_in_authorization_package_confirmed: bool = False
    no_publish_in_authorization_package_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendAuthorizationPackageRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    send_executor_descriptor = describe_real_llm_minimal_call_send_executor_disabled(root=root)
    return {
        **send_executor_descriptor,
        "requestSendAuthorizationPackageId": REAL_LLM_REQUEST_SEND_AUTHORIZATION_PACKAGE_ID,
        "upstreamGateId": "real_llm_minimal_call_send_executor_disabled",
        "mode": "REAL_LLM_REQUEST_SEND_AUTHORIZATION_PACKAGE_ONLY",
        "authorizationMode": "FINAL_HUMAN_AUTHORIZATION_PACKAGE_MODEL_ONLY",
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
        "explicitRequestSendAuthorizationPackageOptIn": (
            request.explicit_request_send_authorization_package_opt_in
        ),
        "sendExecutorDisabledConfirmedForAuthorization": (
            request.send_executor_disabled_confirmed_for_authorization
        ),
        "authorizationScopeConfirmed": request.authorization_scope_confirmed,
        "sendApproverIdentityConfirmed": request.send_approver_identity_confirmed,
        "approvalRecordLocationConfirmed": request.approval_record_location_confirmed,
        "singleRequestAuthorizationConfirmed": request.single_request_authorization_confirmed,
        "labOnlyAuthorizationConfirmed": request.lab_only_authorization_confirmed,
        "providerPromptInputConfirmed": request.provider_prompt_input_confirmed,
        "costTimeoutRetryConfirmedForSend": request.cost_timeout_retry_confirmed_for_send,
        "secretHandlingConfirmedForSend": request.secret_handling_confirmed_for_send,
        "networkEgressConfirmedForSend": request.network_egress_confirmed_for_send,
        "responseValidationConfirmedForSend": request.response_validation_confirmed_for_send,
        "waitingReviewPolicyConfirmedForSend": request.waiting_review_policy_confirmed_for_send,
        "auditRedactionConfirmedForSend": request.audit_redaction_confirmed_for_send,
        "rollbackConfirmedForSend": request.rollback_confirmed_for_send,
        "noManualApprovalGrantInPackageConfirmed": (
            request.no_manual_approval_grant_in_package_confirmed
        ),
        "noRealCallAuthorizationInPackageConfirmed": (
            request.no_real_call_authorization_in_package_confirmed
        ),
        "noRequestSendInAuthorizationPackageConfirmed": (
            request.no_request_send_in_authorization_package_confirmed
        ),
        "noSecretReadInAuthorizationPackageConfirmed": (
            request.no_secret_read_in_authorization_package_confirmed
        ),
        "noNetworkAccessInAuthorizationPackageConfirmed": (
            request.no_network_access_in_authorization_package_confirmed
        ),
        "noTaskCreationInAuthorizationPackageConfirmed": (
            request.no_task_creation_in_authorization_package_confirmed
        ),
        "noPublishInAuthorizationPackageConfirmed": (
            request.no_publish_in_authorization_package_confirmed
        ),
        "allowedOperations": [
            "disabled_send_executor_validation",
            "request_send_authorization_package_generation",
            "future_single_request_send_approval_design",
        ],
        "blockedOperations": [
            "manual_approval_grant",
            "real_call_authorization",
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "send_executor_materialization",
            "send_executor_dispatch",
            "request_send",
            "network_request",
            "real_llm_call",
            "generated_content_creation",
            "task_creation",
            "publish",
            "batch_request",
            "streaming_request",
        ],
        "minimalCallSendExecutorDisabledReady": False,
        "requestSendAuthorizationChecklistReady": False,
        "requestSendAuthorizationPackageReady": False,
        "readyForFinalManualSendAuthorizationReview": False,
        "readyForRealRequestSend": False,
        "authorizationPackageBuilt": False,
        "authorizationPackageMaterialized": False,
        "authorizationPackagePersisted": False,
        "approvalRecordPersisted": False,
        "approvalRecordWritten": False,
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
        "sendExecutorMaterialized": False,
        "sendExecutorPersisted": False,
        "sendExecutorDispatched": False,
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


def describe_real_llm_request_send_authorization_package(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmRequestSendAuthorizationPackageRequest()
    return {
        **_base_context(request, root=root),
        "requiresMinimalCallSendExecutorDisabledReady": True,
        "requiresExplicitRequestSendAuthorizationPackageOptIn": True,
        "requiresSendExecutorDisabledConfirmation": True,
        "requiresAuthorizationScopeConfirmation": True,
        "requiresSendApproverIdentityConfirmation": True,
        "requiresApprovalRecordLocationConfirmation": True,
        "requiresSingleRequestAuthorizationConfirmation": True,
        "requiresLabOnlyAuthorizationConfirmation": True,
        "requiresProviderPromptInputConfirmation": True,
        "requiresCostTimeoutRetryConfirmation": True,
        "requiresSecretHandlingConfirmation": True,
        "requiresNetworkEgressConfirmation": True,
        "requiresResponseValidationConfirmation": True,
        "requiresWaitingReviewPolicyConfirmation": True,
        "requiresAuditRedactionConfirmation": True,
        "requiresRollbackConfirmation": True,
        "requiresNoManualApprovalGrantInPackageConfirmation": True,
        "requiresNoRealCallAuthorizationInPackageConfirmation": True,
        "requiresNoRequestSendInAuthorizationPackageConfirmation": True,
        "requiresNoSecretReadInAuthorizationPackageConfirmation": True,
        "requiresNoNetworkAccessInAuthorizationPackageConfirmation": True,
        "requiresNoTaskCreationInAuthorizationPackageConfirmation": True,
        "requiresNoPublishInAuthorizationPackageConfirmation": True,
        "realCallAuthorizationPath": "future_explicit_real_request_send_execution_request",
    }


def _validate_provider_scope(request: RealLlmRequestSendAuthorizationPackageRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send authorization package currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed for the send authorization package"}],
        )


def _authorization_checklist(
    request: RealLlmRequestSendAuthorizationPackageRequest,
    *,
    send_executor_disabled_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "minimal_call_send_executor_disabled_ready",
            "passed": send_executor_disabled_ready,
            "required": True,
        },
        {
            "id": "explicit_request_send_authorization_package_opt_in",
            "passed": request.explicit_request_send_authorization_package_opt_in,
            "required": True,
        },
        {
            "id": "send_executor_disabled_confirmed_for_authorization",
            "passed": request.send_executor_disabled_confirmed_for_authorization,
            "required": True,
        },
        {
            "id": "authorization_scope_confirmed",
            "passed": request.authorization_scope_confirmed,
            "required": True,
        },
        {
            "id": "send_approver_identity_confirmed",
            "passed": request.send_approver_identity_confirmed,
            "required": True,
        },
        {
            "id": "approval_record_location_confirmed",
            "passed": request.approval_record_location_confirmed,
            "required": True,
        },
        {
            "id": "single_request_authorization_confirmed",
            "passed": request.single_request_authorization_confirmed,
            "required": True,
        },
        {
            "id": "lab_only_authorization_confirmed",
            "passed": request.lab_only_authorization_confirmed,
            "required": True,
        },
        {
            "id": "provider_prompt_input_confirmed",
            "passed": request.provider_prompt_input_confirmed,
            "required": True,
        },
        {
            "id": "cost_timeout_retry_confirmed_for_send",
            "passed": request.cost_timeout_retry_confirmed_for_send,
            "required": True,
        },
        {
            "id": "secret_handling_confirmed_for_send",
            "passed": request.secret_handling_confirmed_for_send,
            "required": True,
        },
        {
            "id": "network_egress_confirmed_for_send",
            "passed": request.network_egress_confirmed_for_send,
            "required": True,
        },
        {
            "id": "response_validation_confirmed_for_send",
            "passed": request.response_validation_confirmed_for_send,
            "required": True,
        },
        {
            "id": "waiting_review_policy_confirmed_for_send",
            "passed": request.waiting_review_policy_confirmed_for_send,
            "required": True,
        },
        {
            "id": "audit_redaction_confirmed_for_send",
            "passed": request.audit_redaction_confirmed_for_send,
            "required": True,
        },
        {
            "id": "rollback_confirmed_for_send",
            "passed": request.rollback_confirmed_for_send,
            "required": True,
        },
        {
            "id": "no_manual_approval_grant_in_package_confirmed",
            "passed": request.no_manual_approval_grant_in_package_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_authorization_in_package_confirmed",
            "passed": request.no_real_call_authorization_in_package_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_authorization_package_confirmed",
            "passed": request.no_request_send_in_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_authorization_package_confirmed",
            "passed": request.no_secret_read_in_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_authorization_package_confirmed",
            "passed": request.no_network_access_in_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_authorization_package_confirmed",
            "passed": request.no_task_creation_in_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_authorization_package_confirmed",
            "passed": request.no_publish_in_authorization_package_confirmed,
            "required": True,
        },
    ]


def _send_executor_summary(send_executor: dict[str, Any]) -> dict[str, Any]:
    return {
        "minimalCallSendExecutorDisabledId": send_executor["minimalCallSendExecutorDisabledId"],
        "minimalCallPocReviewReady": send_executor["minimalCallPocReviewReady"],
        "minimalCallSendExecutorDisabledReady": send_executor["minimalCallSendExecutorDisabledReady"],
        "readyForExplicitRealRequestSendAuthorization": (
            send_executor["readyForExplicitRealRequestSendAuthorization"]
        ),
        "readyForRealRequestSend": send_executor["readyForRealRequestSend"],
        "sendExecutorPlanBuilt": send_executor["sendExecutorPlanBuilt"],
        "sendExecutorDispatched": send_executor["sendExecutorDispatched"],
        "requestSent": send_executor["requestSent"],
        "networkAccess": send_executor["networkAccess"],
        "realLlmCalled": send_executor["realLlmCalled"],
        "secretValueRead": send_executor["secretValueRead"],
        "generatedContentCreated": send_executor["generatedContentCreated"],
        "taskCreated": send_executor["taskCreated"],
        "manualApprovalGranted": send_executor["manualApprovalGranted"],
        "realCallAuthorized": send_executor["realCallAuthorized"],
    }


def _authorization_package(
    request: RealLlmRequestSendAuthorizationPackageRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "packageId": REAL_LLM_REQUEST_SEND_AUTHORIZATION_PACKAGE_ID,
        "built": built,
        "authorizationScope": "single_lab_generate_json_request",
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
        "batchAllowed": False,
        "streamingAllowed": False,
        "manualApprovalGrantedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureHumanApprovalRequired": True,
        "futureExecutionRequestRequired": True,
        "futureApprovalRecordMustNameProvider": True,
        "futureApprovalRecordMustNamePrompt": True,
        "futureApprovalRecordMustNameInputRef": True,
    }


def _authorization_record_policy() -> dict[str, Any]:
    return {
        "authorizationRecordPolicyId": "minimal_real_llm_send_authorization_record_policy",
        "materializeRecordNow": False,
        "persistRecordNow": False,
        "approvalRecordWritten": False,
        "requiredFutureFields": [
            "providerId",
            "operation",
            "promptId",
            "outputKind",
            "inputRef",
            "targetModelAlias",
            "approvalRef",
            "reviewer",
            "costLimit",
            "timeoutSeconds",
            "retryCount",
        ],
    }


def _send_execution_boundary() -> dict[str, Any]:
    return {
        "sendExecutionBoundaryId": "minimal_real_llm_request_send_execution_boundary",
        "sendImplementationCreated": False,
        "sendExecutorMaterialized": False,
        "sendExecutorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "readyForRealRequestSend": False,
        "nextStage": "explicit_real_request_send_execution_request_disabled",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "manualApprovalGranted", "reason": "authorization_package_does_not_grant_approval"},
            {"field": "realCallAuthorized", "reason": "requires_future_explicit_execution_request"},
            {"field": "requestSent", "reason": "authorization_package_does_not_send_requests"},
            {"field": "networkAccess", "reason": "authorization_package_does_not_access_network"},
            {"field": "secretValueRead", "reason": "authorization_package_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "authorization_package_must_not_create_ai_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_authorization_package(
    request: RealLlmRequestSendAuthorizationPackageRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    send_executor = prepare_real_llm_minimal_call_send_executor_disabled(request, root=root)
    send_executor_ready = send_executor.get("minimalCallSendExecutorDisabledReady") is True
    checklist = _authorization_checklist(request, send_executor_disabled_ready=send_executor_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "minimalCallPocReviewReady": send_executor["minimalCallPocReviewReady"],
        "minimalCallSendExecutorDisabledReady": send_executor_ready,
        "readyForExplicitRealRequestSendAuthorization": (
            send_executor["readyForExplicitRealRequestSendAuthorization"]
        ),
        "sendExecutorSummary": _send_executor_summary(send_executor),
        "requestSendAuthorizationChecklist": checklist,
        "requestSendAuthorizationChecklistReady": checklist_passed,
        "requestSendAuthorizationPackageReady": checklist_passed,
        "readyForFinalManualSendAuthorizationReview": checklist_passed,
        "readyForRealRequestSend": False,
        "authorizationPackage": _authorization_package(request, built=checklist_passed),
        "authorizationRecordPolicy": _authorization_record_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "authorizationPackageBuilt": checklist_passed,
        "authorizationPackageMaterialized": False,
        "authorizationPackagePersisted": False,
        "approvalRecordPersisted": False,
        "approvalRecordWritten": False,
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
        "sendExecutorMaterialized": False,
        "sendExecutorPersisted": False,
        "sendExecutorDispatched": False,
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
            "真实 LLM 请求发送最终授权包模型已生成；当前不会授予人工批准、授权真实调用、"
            "创建真实发送实现、发送请求、联网、读取密钥、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_authorization_package_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendAuthorizationPackageRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendAuthorizationPackageRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            send_executor = prepare_real_llm_minimal_call_send_executor_disabled(request, root=root)
        else:
            send_executor = None
    except ProviderError:
        send_executor = None
    if send_executor is not None:
        context["minimalCallSendExecutorDisabledReady"] = bool(
            send_executor.get("minimalCallSendExecutorDisabledReady", False)
        )
        context["sendExecutorSummary"] = _send_executor_summary(send_executor)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
