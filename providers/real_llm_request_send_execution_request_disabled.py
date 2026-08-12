"""Disabled execution request model for the real LLM request-send path.

This module accepts a completed request-send authorization package and turns it
into a local execution-request review model. It never grants approval,
authorizes a real call, persists or queues an execution request, dispatches an
executor, sends requests, reads secrets, accesses network, creates tasks, or
publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_authorization_package import (
    RealLlmRequestSendAuthorizationPackageRequest,
    build_real_llm_request_send_authorization_package,
    describe_real_llm_request_send_authorization_package,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_EXECUTION_REQUEST_DISABLED_ID = (
    "real_llm_request_send_execution_request_disabled"
)


@dataclass(frozen=True)
class RealLlmRequestSendExecutionRequestDisabledRequest(
    RealLlmRequestSendAuthorizationPackageRequest
):
    explicit_request_send_execution_request_disabled_opt_in: bool = False
    request_send_authorization_package_confirmed: bool = False
    execution_request_scope_confirmed: bool = False
    execution_request_record_confirmed: bool = False
    send_executor_disabled_boundary_confirmed: bool = False
    final_human_authorization_review_confirmed: bool = False
    single_request_execution_confirmed: bool = False
    lab_only_execution_confirmed: bool = False
    runtime_kill_switch_confirmed: bool = False
    audit_event_confirmed_for_execution_request: bool = False
    rollback_confirmed_for_execution_request: bool = False
    no_manual_approval_grant_in_execution_request_confirmed: bool = False
    no_real_call_authorization_in_execution_request_confirmed: bool = False
    no_executor_dispatch_in_execution_request_confirmed: bool = False
    no_request_send_in_execution_request_confirmed: bool = False
    no_secret_read_in_execution_request_confirmed: bool = False
    no_network_access_in_execution_request_confirmed: bool = False
    no_task_creation_in_execution_request_confirmed: bool = False
    no_publish_in_execution_request_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendExecutionRequestDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    authorization_descriptor = describe_real_llm_request_send_authorization_package(root=root)
    return {
        **authorization_descriptor,
        "requestSendExecutionRequestDisabledId": (
            REAL_LLM_REQUEST_SEND_EXECUTION_REQUEST_DISABLED_ID
        ),
        "upstreamGateId": "real_llm_request_send_authorization_package",
        "mode": "REAL_LLM_REQUEST_SEND_EXECUTION_REQUEST_DISABLED_ONLY",
        "executionRequestMode": "DISABLED_REAL_REQUEST_SEND_EXECUTION_REQUEST_MODEL_ONLY",
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
        "explicitRequestSendExecutionRequestDisabledOptIn": (
            request.explicit_request_send_execution_request_disabled_opt_in
        ),
        "requestSendAuthorizationPackageConfirmed": (
            request.request_send_authorization_package_confirmed
        ),
        "executionRequestScopeConfirmed": request.execution_request_scope_confirmed,
        "executionRequestRecordConfirmed": request.execution_request_record_confirmed,
        "sendExecutorDisabledBoundaryConfirmed": (
            request.send_executor_disabled_boundary_confirmed
        ),
        "finalHumanAuthorizationReviewConfirmed": (
            request.final_human_authorization_review_confirmed
        ),
        "singleRequestExecutionConfirmed": request.single_request_execution_confirmed,
        "labOnlyExecutionConfirmed": request.lab_only_execution_confirmed,
        "runtimeKillSwitchConfirmed": request.runtime_kill_switch_confirmed,
        "auditEventConfirmedForExecutionRequest": (
            request.audit_event_confirmed_for_execution_request
        ),
        "rollbackConfirmedForExecutionRequest": request.rollback_confirmed_for_execution_request,
        "noManualApprovalGrantInExecutionRequestConfirmed": (
            request.no_manual_approval_grant_in_execution_request_confirmed
        ),
        "noRealCallAuthorizationInExecutionRequestConfirmed": (
            request.no_real_call_authorization_in_execution_request_confirmed
        ),
        "noExecutorDispatchInExecutionRequestConfirmed": (
            request.no_executor_dispatch_in_execution_request_confirmed
        ),
        "noRequestSendInExecutionRequestConfirmed": (
            request.no_request_send_in_execution_request_confirmed
        ),
        "noSecretReadInExecutionRequestConfirmed": (
            request.no_secret_read_in_execution_request_confirmed
        ),
        "noNetworkAccessInExecutionRequestConfirmed": (
            request.no_network_access_in_execution_request_confirmed
        ),
        "noTaskCreationInExecutionRequestConfirmed": (
            request.no_task_creation_in_execution_request_confirmed
        ),
        "noPublishInExecutionRequestConfirmed": (
            request.no_publish_in_execution_request_confirmed
        ),
        "allowedOperations": [
            "request_send_authorization_package_validation",
            "disabled_execution_request_generation",
            "future_disabled_send_executor_review_design",
        ],
        "blockedOperations": [
            "manual_approval_grant",
            "real_call_authorization",
            "execution_request_persistence",
            "execution_request_queue",
            "execution_request_dispatch",
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
        "requestSendAuthorizationPackageReady": False,
        "requestSendExecutionRequestChecklistReady": False,
        "requestSendExecutionRequestDisabledReady": False,
        "readyForDisabledRealRequestSendExecutor": False,
        "readyForRealRequestSend": False,
        "executionRequestBuilt": False,
        "executionRequestMaterialized": False,
        "executionRequestPersisted": False,
        "executionRequestQueued": False,
        "executionRequestDispatched": False,
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


def describe_real_llm_request_send_execution_request_disabled(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendExecutionRequestDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendAuthorizationPackageReady": True,
        "requiresExplicitRequestSendExecutionRequestDisabledOptIn": True,
        "requiresRequestSendAuthorizationPackageConfirmation": True,
        "requiresExecutionRequestScopeConfirmation": True,
        "requiresExecutionRequestRecordConfirmation": True,
        "requiresSendExecutorDisabledBoundaryConfirmation": True,
        "requiresFinalHumanAuthorizationReviewConfirmation": True,
        "requiresSingleRequestExecutionConfirmation": True,
        "requiresLabOnlyExecutionConfirmation": True,
        "requiresRuntimeKillSwitchConfirmation": True,
        "requiresAuditEventForExecutionRequestConfirmation": True,
        "requiresRollbackForExecutionRequestConfirmation": True,
        "requiresNoManualApprovalGrantInExecutionRequestConfirmation": True,
        "requiresNoRealCallAuthorizationInExecutionRequestConfirmation": True,
        "requiresNoExecutorDispatchInExecutionRequestConfirmation": True,
        "requiresNoRequestSendInExecutionRequestConfirmation": True,
        "requiresNoSecretReadInExecutionRequestConfirmation": True,
        "requiresNoNetworkAccessInExecutionRequestConfirmation": True,
        "requiresNoTaskCreationInExecutionRequestConfirmation": True,
        "requiresNoPublishInExecutionRequestConfirmation": True,
        "realCallAuthorizationPath": "future_disabled_real_request_send_executor_after_review",
    }


def _validate_provider_scope(request: RealLlmRequestSendExecutionRequestDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send execution request currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the disabled execution request",
                }
            ],
        )


def _execution_request_checklist(
    request: RealLlmRequestSendExecutionRequestDisabledRequest,
    *,
    authorization_package_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "request_send_authorization_package_ready", "passed": authorization_package_ready, "required": True},
        {
            "id": "explicit_request_send_execution_request_disabled_opt_in",
            "passed": request.explicit_request_send_execution_request_disabled_opt_in,
            "required": True,
        },
        {
            "id": "request_send_authorization_package_confirmed",
            "passed": request.request_send_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "execution_request_scope_confirmed",
            "passed": request.execution_request_scope_confirmed,
            "required": True,
        },
        {
            "id": "execution_request_record_confirmed",
            "passed": request.execution_request_record_confirmed,
            "required": True,
        },
        {
            "id": "send_executor_disabled_boundary_confirmed",
            "passed": request.send_executor_disabled_boundary_confirmed,
            "required": True,
        },
        {
            "id": "final_human_authorization_review_confirmed",
            "passed": request.final_human_authorization_review_confirmed,
            "required": True,
        },
        {
            "id": "single_request_execution_confirmed",
            "passed": request.single_request_execution_confirmed,
            "required": True,
        },
        {
            "id": "lab_only_execution_confirmed",
            "passed": request.lab_only_execution_confirmed,
            "required": True,
        },
        {
            "id": "runtime_kill_switch_confirmed",
            "passed": request.runtime_kill_switch_confirmed,
            "required": True,
        },
        {
            "id": "audit_event_confirmed_for_execution_request",
            "passed": request.audit_event_confirmed_for_execution_request,
            "required": True,
        },
        {
            "id": "rollback_confirmed_for_execution_request",
            "passed": request.rollback_confirmed_for_execution_request,
            "required": True,
        },
        {
            "id": "no_manual_approval_grant_in_execution_request_confirmed",
            "passed": request.no_manual_approval_grant_in_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_authorization_in_execution_request_confirmed",
            "passed": request.no_real_call_authorization_in_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_in_execution_request_confirmed",
            "passed": request.no_executor_dispatch_in_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_execution_request_confirmed",
            "passed": request.no_request_send_in_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_execution_request_confirmed",
            "passed": request.no_secret_read_in_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_execution_request_confirmed",
            "passed": request.no_network_access_in_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_execution_request_confirmed",
            "passed": request.no_task_creation_in_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_execution_request_confirmed",
            "passed": request.no_publish_in_execution_request_confirmed,
            "required": True,
        },
    ]


def _authorization_package_summary(authorization_package: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendAuthorizationPackageId": authorization_package["requestSendAuthorizationPackageId"],
        "minimalCallSendExecutorDisabledReady": authorization_package[
            "minimalCallSendExecutorDisabledReady"
        ],
        "requestSendAuthorizationPackageReady": authorization_package[
            "requestSendAuthorizationPackageReady"
        ],
        "readyForFinalManualSendAuthorizationReview": authorization_package[
            "readyForFinalManualSendAuthorizationReview"
        ],
        "readyForRealRequestSend": authorization_package["readyForRealRequestSend"],
        "manualApprovalGranted": authorization_package["manualApprovalGranted"],
        "realCallAuthorized": authorization_package["realCallAuthorized"],
        "requestSent": authorization_package["requestSent"],
        "networkAccess": authorization_package["networkAccess"],
        "realLlmCalled": authorization_package["realLlmCalled"],
        "secretValueRead": authorization_package["secretValueRead"],
        "generatedContentCreated": authorization_package["generatedContentCreated"],
        "taskCreated": authorization_package["taskCreated"],
    }


def _execution_request_record(
    request: RealLlmRequestSendExecutionRequestDisabledRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "executionRequestId": REAL_LLM_REQUEST_SEND_EXECUTION_REQUEST_DISABLED_ID,
        "built": built,
        "executionScope": "single_lab_generate_json_request",
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
        "materializedNow": False,
        "persistedNow": False,
        "queuedNow": False,
        "dispatchedNow": False,
        "manualApprovalGrantedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureDisabledExecutorRequired": True,
        "futureHumanReviewRequired": True,
    }


def _execution_request_policy() -> dict[str, Any]:
    return {
        "executionRequestPolicyId": "minimal_real_llm_request_send_execution_request_policy",
        "materializeRecordNow": False,
        "persistRecordNow": False,
        "queueRecordNow": False,
        "dispatchExecutorNow": False,
        "requiredFutureFields": [
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
            "timeoutSeconds",
            "retryCount",
        ],
    }


def _send_execution_boundary() -> dict[str, Any]:
    return {
        "sendExecutionBoundaryId": "minimal_real_llm_request_send_execution_request_boundary",
        "executionRequestMaterialized": False,
        "executionRequestPersisted": False,
        "executionRequestQueued": False,
        "executionRequestDispatched": False,
        "sendImplementationCreated": False,
        "sendExecutorMaterialized": False,
        "sendExecutorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "readyForRealRequestSend": False,
        "nextStage": "real_request_send_executor_disabled",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "manualApprovalGranted", "reason": "execution_request_does_not_grant_approval"},
            {"field": "realCallAuthorized", "reason": "requires_future_explicit_human_approval"},
            {"field": "executionRequestPersisted", "reason": "execution_request_model_is_not_persisted"},
            {"field": "executionRequestDispatched", "reason": "execution_request_model_is_not_dispatched"},
            {"field": "requestSent", "reason": "execution_request_model_does_not_send_requests"},
            {"field": "networkAccess", "reason": "execution_request_model_does_not_access_network"},
            {"field": "secretValueRead", "reason": "execution_request_model_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "execution_request_model_must_not_create_ai_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_execution_request_disabled(
    request: RealLlmRequestSendExecutionRequestDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    authorization_package = build_real_llm_request_send_authorization_package(request, root=root)
    authorization_package_ready = (
        authorization_package.get("requestSendAuthorizationPackageReady") is True
    )
    checklist = _execution_request_checklist(
        request,
        authorization_package_ready=authorization_package_ready,
    )
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestSendAuthorizationPackageReady": authorization_package_ready,
        "authorizationPackageSummary": _authorization_package_summary(authorization_package),
        "requestSendExecutionRequestChecklist": checklist,
        "requestSendExecutionRequestChecklistReady": checklist_passed,
        "requestSendExecutionRequestDisabledReady": checklist_passed,
        "readyForDisabledRealRequestSendExecutor": checklist_passed,
        "readyForRealRequestSend": False,
        "executionRequest": _execution_request_record(request, built=checklist_passed),
        "executionRequestPolicy": _execution_request_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "executionRequestBuilt": checklist_passed,
        "executionRequestMaterialized": False,
        "executionRequestPersisted": False,
        "executionRequestQueued": False,
        "executionRequestDispatched": False,
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
            "真实 LLM 请求发送执行请求禁用模型已生成；当前不会授予人工批准、授权真实调用、"
            "持久化或派发执行请求、发送请求、联网、读取密钥、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_execution_request_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendExecutionRequestDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendExecutionRequestDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            authorization_package = build_real_llm_request_send_authorization_package(
                request,
                root=root,
            )
        else:
            authorization_package = None
    except ProviderError:
        authorization_package = None
    if authorization_package is not None:
        context["requestSendAuthorizationPackageReady"] = bool(
            authorization_package.get("requestSendAuthorizationPackageReady", False)
        )
        context["authorizationPackageSummary"] = _authorization_package_summary(authorization_package)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
