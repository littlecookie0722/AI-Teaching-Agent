"""Disabled request-send attempt gate for the real LLM path.

This module accepts a completed disabled executor dispatch gate model and
prepares a local request-send attempt gate model. It never attempts to send a
request, reads secrets, creates clients, accesses network, calls real LLMs,
creates generated content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_executor_dispatch_gate_disabled import (
    REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ID,
    RealLlmRequestSendExecutorDispatchGateDisabledRequest,
    build_real_llm_request_send_executor_dispatch_gate_disabled,
    describe_real_llm_request_send_executor_dispatch_gate_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_ATTEMPT_GATE_DISABLED_ID = (
    "real_llm_request_send_attempt_gate_disabled"
)


@dataclass(frozen=True)
class RealLlmRequestSendAttemptGateDisabledRequest(
    RealLlmRequestSendExecutorDispatchGateDisabledRequest
):
    explicit_request_send_attempt_gate_disabled_opt_in: bool = False
    executor_dispatch_gate_confirmed: bool = False
    request_send_attempt_scope_confirmed: bool = False
    request_send_attempt_record_confirmed: bool = False
    send_attempt_policy_confirmed: bool = False
    send_executor_reference_confirmed: bool = False
    executor_run_reference_for_attempt_confirmed: bool = False
    runtime_gate_reference_for_attempt_confirmed: bool = False
    authorization_record_reference_for_attempt_confirmed: bool = False
    provider_client_boundary_for_attempt_confirmed: bool = False
    secret_runtime_boundary_for_attempt_confirmed: bool = False
    network_egress_boundary_for_attempt_confirmed: bool = False
    response_validation_boundary_for_attempt_confirmed: bool = False
    waiting_review_policy_for_attempt_confirmed: bool = False
    attempt_audit_redaction_confirmed: bool = False
    attempt_rollback_confirmed: bool = False
    no_attempt_record_persistence_confirmed: bool = False
    no_request_send_attempt_confirmed: bool = False
    no_request_send_in_attempt_gate_confirmed: bool = False
    no_secret_read_in_attempt_gate_confirmed: bool = False
    no_client_creation_in_attempt_gate_confirmed: bool = False
    no_network_access_in_attempt_gate_confirmed: bool = False
    no_real_llm_call_in_attempt_gate_confirmed: bool = False
    no_generated_content_creation_in_attempt_gate_confirmed: bool = False
    no_task_creation_in_attempt_gate_confirmed: bool = False
    no_publish_in_attempt_gate_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendAttemptGateDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    dispatch_gate_descriptor = describe_real_llm_request_send_executor_dispatch_gate_disabled(
        root=root
    )
    return {
        **dispatch_gate_descriptor,
        "requestSendAttemptGateDisabledId": REAL_LLM_REQUEST_SEND_ATTEMPT_GATE_DISABLED_ID,
        "upstreamGateId": REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ID,
        "mode": "REAL_LLM_REQUEST_SEND_ATTEMPT_GATE_DISABLED_ONLY",
        "requestSendAttemptGateMode": "REQUEST_SEND_ATTEMPT_GATE_DISABLED_MODEL_ONLY",
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
        "explicitRequestSendAttemptGateDisabledOptIn": (
            request.explicit_request_send_attempt_gate_disabled_opt_in
        ),
        "executorDispatchGateConfirmed": request.executor_dispatch_gate_confirmed,
        "requestSendAttemptScopeConfirmed": request.request_send_attempt_scope_confirmed,
        "requestSendAttemptRecordConfirmed": request.request_send_attempt_record_confirmed,
        "sendAttemptPolicyConfirmed": request.send_attempt_policy_confirmed,
        "sendExecutorReferenceConfirmed": request.send_executor_reference_confirmed,
        "executorRunReferenceForAttemptConfirmed": (
            request.executor_run_reference_for_attempt_confirmed
        ),
        "runtimeGateReferenceForAttemptConfirmed": (
            request.runtime_gate_reference_for_attempt_confirmed
        ),
        "authorizationRecordReferenceForAttemptConfirmed": (
            request.authorization_record_reference_for_attempt_confirmed
        ),
        "providerClientBoundaryForAttemptConfirmed": (
            request.provider_client_boundary_for_attempt_confirmed
        ),
        "secretRuntimeBoundaryForAttemptConfirmed": (
            request.secret_runtime_boundary_for_attempt_confirmed
        ),
        "networkEgressBoundaryForAttemptConfirmed": (
            request.network_egress_boundary_for_attempt_confirmed
        ),
        "responseValidationBoundaryForAttemptConfirmed": (
            request.response_validation_boundary_for_attempt_confirmed
        ),
        "waitingReviewPolicyForAttemptConfirmed": (
            request.waiting_review_policy_for_attempt_confirmed
        ),
        "attemptAuditRedactionConfirmed": request.attempt_audit_redaction_confirmed,
        "attemptRollbackConfirmed": request.attempt_rollback_confirmed,
        "noAttemptRecordPersistenceConfirmed": (
            request.no_attempt_record_persistence_confirmed
        ),
        "noRequestSendAttemptConfirmed": request.no_request_send_attempt_confirmed,
        "noRequestSendInAttemptGateConfirmed": (
            request.no_request_send_in_attempt_gate_confirmed
        ),
        "noSecretReadInAttemptGateConfirmed": (
            request.no_secret_read_in_attempt_gate_confirmed
        ),
        "noClientCreationInAttemptGateConfirmed": (
            request.no_client_creation_in_attempt_gate_confirmed
        ),
        "noNetworkAccessInAttemptGateConfirmed": (
            request.no_network_access_in_attempt_gate_confirmed
        ),
        "noRealLlmCallInAttemptGateConfirmed": (
            request.no_real_llm_call_in_attempt_gate_confirmed
        ),
        "noGeneratedContentCreationInAttemptGateConfirmed": (
            request.no_generated_content_creation_in_attempt_gate_confirmed
        ),
        "noTaskCreationInAttemptGateConfirmed": (
            request.no_task_creation_in_attempt_gate_confirmed
        ),
        "noPublishInAttemptGateConfirmed": request.no_publish_in_attempt_gate_confirmed,
        "allowedOperations": [
            "executor_dispatch_gate_validation",
            "disabled_request_send_attempt_gate_model_generation",
            "future_request_send_final_execution_design",
        ],
        "blockedOperations": [
            "request_send_attempt",
            "request_send",
            "attempt_record_persistence",
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "network_request",
            "real_llm_call",
            "response_stream_open",
            "generated_content_creation",
            "task_creation",
            "publish",
            "batch_request",
            "streaming_request",
        ],
        "requestSendExecutorDispatchGateDisabledReady": False,
        "requestSendAttemptGateChecklistReady": False,
        "requestSendAttemptGateDisabledReady": False,
        "readyForFinalRealRequestSendExecution": False,
        "readyForRealRequestSend": False,
        "requestSendAttemptGateModelBuilt": False,
        "attemptRecordPersisted": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "dispatchQueueWritten": False,
        "dispatchRecordPersisted": False,
        "sendExecutorCreated": False,
        "sendExecutorPersisted": False,
        "runtimeGateOpened": False,
        "runtimeKillSwitchDisabled": False,
        "runtimeBudgetReserved": False,
        "runtimeNetworkEgressOpened": False,
        "authorizationRecordWritten": False,
        "approvalRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
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


def describe_real_llm_request_send_attempt_gate_disabled(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendAttemptGateDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendExecutorDispatchGateDisabledReady": True,
        "requiresExplicitRequestSendAttemptGateDisabledOptIn": True,
        "requiresExecutorDispatchGateConfirmation": True,
        "requiresRequestSendAttemptScopeConfirmation": True,
        "requiresRequestSendAttemptRecordConfirmation": True,
        "requiresSendAttemptPolicyConfirmation": True,
        "requiresSendExecutorReferenceConfirmation": True,
        "requiresExecutorRunReferenceForAttemptConfirmation": True,
        "requiresRuntimeGateReferenceForAttemptConfirmation": True,
        "requiresAuthorizationRecordReferenceForAttemptConfirmation": True,
        "requiresProviderClientBoundaryForAttemptConfirmation": True,
        "requiresSecretRuntimeBoundaryForAttemptConfirmation": True,
        "requiresNetworkEgressBoundaryForAttemptConfirmation": True,
        "requiresResponseValidationBoundaryForAttemptConfirmation": True,
        "requiresWaitingReviewPolicyForAttemptConfirmation": True,
        "requiresAttemptAuditRedactionConfirmation": True,
        "requiresAttemptRollbackConfirmation": True,
        "requiresNoAttemptRecordPersistenceConfirmation": True,
        "requiresNoRequestSendAttemptConfirmation": True,
        "requiresNoRequestSendInAttemptGateConfirmation": True,
        "requiresNoSecretReadInAttemptGateConfirmation": True,
        "requiresNoClientCreationInAttemptGateConfirmation": True,
        "requiresNoNetworkAccessInAttemptGateConfirmation": True,
        "requiresNoRealLlmCallInAttemptGateConfirmation": True,
        "requiresNoGeneratedContentCreationInAttemptGateConfirmation": True,
        "requiresNoTaskCreationInAttemptGateConfirmation": True,
        "requiresNoPublishInAttemptGateConfirmation": True,
        "realRequestSendPath": "future_final_real_request_send_execution",
    }


def _validate_provider_scope(request: RealLlmRequestSendAttemptGateDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send attempt gate currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the request send attempt gate",
                }
            ],
        )


def _request_send_attempt_gate_checklist(
    request: RealLlmRequestSendAttemptGateDisabledRequest,
    *,
    dispatch_gate_ready: bool,
) -> list[dict[str, Any]]:
    checks = [
        ("request_send_executor_dispatch_gate_disabled_ready", dispatch_gate_ready),
        (
            "explicit_request_send_attempt_gate_disabled_opt_in",
            request.explicit_request_send_attempt_gate_disabled_opt_in,
        ),
        ("executor_dispatch_gate_confirmed", request.executor_dispatch_gate_confirmed),
        (
            "request_send_attempt_scope_confirmed",
            request.request_send_attempt_scope_confirmed,
        ),
        (
            "request_send_attempt_record_confirmed",
            request.request_send_attempt_record_confirmed,
        ),
        ("send_attempt_policy_confirmed", request.send_attempt_policy_confirmed),
        ("send_executor_reference_confirmed", request.send_executor_reference_confirmed),
        (
            "executor_run_reference_for_attempt_confirmed",
            request.executor_run_reference_for_attempt_confirmed,
        ),
        (
            "runtime_gate_reference_for_attempt_confirmed",
            request.runtime_gate_reference_for_attempt_confirmed,
        ),
        (
            "authorization_record_reference_for_attempt_confirmed",
            request.authorization_record_reference_for_attempt_confirmed,
        ),
        (
            "provider_client_boundary_for_attempt_confirmed",
            request.provider_client_boundary_for_attempt_confirmed,
        ),
        (
            "secret_runtime_boundary_for_attempt_confirmed",
            request.secret_runtime_boundary_for_attempt_confirmed,
        ),
        (
            "network_egress_boundary_for_attempt_confirmed",
            request.network_egress_boundary_for_attempt_confirmed,
        ),
        (
            "response_validation_boundary_for_attempt_confirmed",
            request.response_validation_boundary_for_attempt_confirmed,
        ),
        (
            "waiting_review_policy_for_attempt_confirmed",
            request.waiting_review_policy_for_attempt_confirmed,
        ),
        ("attempt_audit_redaction_confirmed", request.attempt_audit_redaction_confirmed),
        ("attempt_rollback_confirmed", request.attempt_rollback_confirmed),
        (
            "no_attempt_record_persistence_confirmed",
            request.no_attempt_record_persistence_confirmed,
        ),
        ("no_request_send_attempt_confirmed", request.no_request_send_attempt_confirmed),
        (
            "no_request_send_in_attempt_gate_confirmed",
            request.no_request_send_in_attempt_gate_confirmed,
        ),
        (
            "no_secret_read_in_attempt_gate_confirmed",
            request.no_secret_read_in_attempt_gate_confirmed,
        ),
        (
            "no_client_creation_in_attempt_gate_confirmed",
            request.no_client_creation_in_attempt_gate_confirmed,
        ),
        (
            "no_network_access_in_attempt_gate_confirmed",
            request.no_network_access_in_attempt_gate_confirmed,
        ),
        (
            "no_real_llm_call_in_attempt_gate_confirmed",
            request.no_real_llm_call_in_attempt_gate_confirmed,
        ),
        (
            "no_generated_content_creation_in_attempt_gate_confirmed",
            request.no_generated_content_creation_in_attempt_gate_confirmed,
        ),
        (
            "no_task_creation_in_attempt_gate_confirmed",
            request.no_task_creation_in_attempt_gate_confirmed,
        ),
        ("no_publish_in_attempt_gate_confirmed", request.no_publish_in_attempt_gate_confirmed),
    ]
    return [{"id": item_id, "passed": passed, "required": True} for item_id, passed in checks]


def _executor_dispatch_gate_summary(dispatch_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendExecutorDispatchGateDisabledId": dispatch_gate[
            "requestSendExecutorDispatchGateDisabledId"
        ],
        "requestSendExecutorCreationGateDisabledReady": dispatch_gate[
            "requestSendExecutorCreationGateDisabledReady"
        ],
        "requestSendExecutorDispatchGateDisabledReady": dispatch_gate[
            "requestSendExecutorDispatchGateDisabledReady"
        ],
        "readyForRealRequestSendAttemptGate": dispatch_gate[
            "readyForRealRequestSendAttemptGate"
        ],
        "readyForRealRequestSend": dispatch_gate["readyForRealRequestSend"],
        "dispatchQueueWritten": dispatch_gate["dispatchQueueWritten"],
        "dispatchRecordPersisted": dispatch_gate["dispatchRecordPersisted"],
        "sendExecutorDispatched": dispatch_gate["sendExecutorDispatched"],
        "executorDispatched": dispatch_gate["executorDispatched"],
        "requestSendAttempted": dispatch_gate["requestSendAttempted"],
        "requestSent": dispatch_gate["requestSent"],
        "realCallAuthorized": dispatch_gate["realCallAuthorized"],
        "networkAccess": dispatch_gate["networkAccess"],
        "realLlmCalled": dispatch_gate["realLlmCalled"],
        "secretValueRead": dispatch_gate["secretValueRead"],
        "generatedContentCreated": dispatch_gate["generatedContentCreated"],
        "taskCreated": dispatch_gate["taskCreated"],
    }


def _request_send_attempt_gate_model(
    request: RealLlmRequestSendAttemptGateDisabledRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "requestSendAttemptGateId": REAL_LLM_REQUEST_SEND_ATTEMPT_GATE_DISABLED_ID,
        "built": built,
        "attemptScope": "single_lab_generate_json_request",
        "executorDispatchGateId": REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ID,
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
        "attemptRecordPersistedNow": False,
        "requestSendAttemptedNow": False,
        "requestSentNow": False,
        "secretReadAllowedNow": False,
        "clientCreationAllowedNow": False,
        "networkAccessAllowedNow": False,
        "realLlmCallAllowedNow": False,
        "responseStreamOpenedNow": False,
        "generatedContentCreatedNow": False,
        "taskCreatedNow": False,
        "sendAllowedNow": False,
        "futureFinalRealRequestSendExecutionRequired": True,
    }


def _request_send_attempt_policy() -> dict[str, Any]:
    return {
        "requestSendAttemptPolicyId": (
            "minimal_real_llm_request_send_attempt_gate_disabled_policy"
        ),
        "persistAttemptRecordNow": False,
        "attemptRequestSendNow": False,
        "sendRequestNow": False,
        "allowSecretReadNow": False,
        "allowClientCreationNow": False,
        "allowNetworkAccessNow": False,
        "allowRealLlmCallNow": False,
        "openResponseStreamNow": False,
        "createGeneratedContentNow": False,
        "createWaitingReviewTaskNow": False,
        "requiredFutureFields": [
            "requestSendAttemptGateId",
            "attemptRecordId",
            "executorDispatchGateId",
            "executorId",
            "executorRunId",
            "authorizationRecordId",
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
            "schemaRef",
        ],
    }


def _request_send_execution_boundary() -> dict[str, Any]:
    return {
        "requestSendExecutionBoundaryId": (
            "minimal_real_llm_request_send_attempt_gate_disabled_boundary"
        ),
        "attemptRecordPersisted": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "readyForRealRequestSend": False,
        "nextStage": "final_real_request_send_execution",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "attemptRecordPersisted", "reason": "attempt_gate_does_not_persist_attempt_records"},
            {"field": "requestSendAttempted", "reason": "requires_future_final_real_request_send_execution"},
            {"field": "requestSent", "reason": "attempt_gate_does_not_send_requests"},
            {"field": "clientCreated", "reason": "attempt_gate_does_not_create_clients"},
            {"field": "networkAccess", "reason": "attempt_gate_does_not_access_network"},
            {"field": "secretValueRead", "reason": "attempt_gate_does_not_read_secret_values"},
            {"field": "realLlmCalled", "reason": "attempt_gate_does_not_call_real_llms"},
            {"field": "taskCreated", "reason": "attempt_gate_must_not_create_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_attempt_gate_disabled(
    request: RealLlmRequestSendAttemptGateDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    dispatch_gate = build_real_llm_request_send_executor_dispatch_gate_disabled(
        request,
        root=root,
    )
    dispatch_gate_ready = (
        dispatch_gate.get("requestSendExecutorDispatchGateDisabledReady") is True
    )
    checklist = _request_send_attempt_gate_checklist(
        request,
        dispatch_gate_ready=dispatch_gate_ready,
    )
    checklist_passed = all(
        item["passed"] is True for item in checklist if item["required"] is True
    )

    return {
        **context,
        "requestSendExecutorDispatchGateDisabledReady": dispatch_gate_ready,
        "requestSendExecutorDispatchGateDisabledSummary": (
            _executor_dispatch_gate_summary(dispatch_gate)
        ),
        "requestSendAttemptGateChecklist": checklist,
        "requestSendAttemptGateChecklistReady": checklist_passed,
        "requestSendAttemptGateDisabledReady": checklist_passed,
        "readyForFinalRealRequestSendExecution": checklist_passed,
        "readyForRealRequestSend": False,
        "requestSendAttemptGateModel": _request_send_attempt_gate_model(
            request,
            built=checklist_passed,
        ),
        "requestSendAttemptPolicy": _request_send_attempt_policy(),
        "requestSendExecutionBoundary": _request_send_execution_boundary(),
        "requestSendAttemptGateModelBuilt": checklist_passed,
        "attemptRecordPersisted": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "dispatchQueueWritten": False,
        "dispatchRecordPersisted": False,
        "sendExecutorCreated": False,
        "sendExecutorPersisted": False,
        "runtimeGateOpened": False,
        "runtimeKillSwitchDisabled": False,
        "runtimeBudgetReserved": False,
        "runtimeNetworkEgressOpened": False,
        "authorizationRecordWritten": False,
        "approvalRecordWritten": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
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
            "真实 LLM 请求发送尝试门禁禁用模型已生成；当前不会持久化尝试记录、"
            "尝试发送请求、发送请求、读取密钥、创建 client、联网、调用真实 LLM、"
            "创建生成内容、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_attempt_gate_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendAttemptGateDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendAttemptGateDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            dispatch_gate = build_real_llm_request_send_executor_dispatch_gate_disabled(
                request,
                root=root,
            )
        else:
            dispatch_gate = None
    except ProviderError:
        dispatch_gate = None
    if dispatch_gate is not None:
        context["requestSendExecutorDispatchGateDisabledReady"] = bool(
            dispatch_gate.get("requestSendExecutorDispatchGateDisabledReady", False)
        )
        context["requestSendExecutorDispatchGateDisabledSummary"] = (
            _executor_dispatch_gate_summary(dispatch_gate)
        )
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
