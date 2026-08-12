"""Disabled executor dispatch gate for the real LLM request-send path.

This module accepts a completed disabled executor creation gate model and
prepares a local executor dispatch gate model. It never writes dispatch queues,
persists dispatch records, dispatches executors, sends requests, reads secrets,
creates clients, accesses network, creates generated content, creates tasks, or
publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_executor_creation_gate_disabled import (
    REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ID,
    RealLlmRequestSendExecutorCreationGateDisabledRequest,
    build_real_llm_request_send_executor_creation_gate_disabled,
    describe_real_llm_request_send_executor_creation_gate_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ID = (
    "real_llm_request_send_executor_dispatch_gate_disabled"
)


@dataclass(frozen=True)
class RealLlmRequestSendExecutorDispatchGateDisabledRequest(
    RealLlmRequestSendExecutorCreationGateDisabledRequest
):
    explicit_request_send_executor_dispatch_gate_disabled_opt_in: bool = False
    executor_creation_gate_confirmed: bool = False
    executor_dispatch_scope_confirmed: bool = False
    executor_dispatch_record_confirmed: bool = False
    executor_dispatch_policy_confirmed: bool = False
    executor_run_reference_confirmed: bool = False
    executor_identity_for_dispatch_confirmed: bool = False
    runtime_gate_reference_for_dispatch_confirmed: bool = False
    authorization_record_reference_for_dispatch_confirmed: bool = False
    dispatch_queue_boundary_confirmed: bool = False
    dispatch_audit_redaction_confirmed: bool = False
    dispatch_rollback_confirmed: bool = False
    dispatch_waiting_review_policy_confirmed: bool = False
    no_dispatch_queue_write_confirmed: bool = False
    no_dispatch_record_persistence_confirmed: bool = False
    no_executor_dispatch_in_dispatch_gate_confirmed: bool = False
    no_executor_start_in_dispatch_gate_confirmed: bool = False
    no_executor_run_creation_in_dispatch_gate_confirmed: bool = False
    no_request_send_in_dispatch_gate_confirmed: bool = False
    no_secret_read_in_dispatch_gate_confirmed: bool = False
    no_client_creation_in_dispatch_gate_confirmed: bool = False
    no_network_access_in_dispatch_gate_confirmed: bool = False
    no_real_call_authorization_in_dispatch_gate_confirmed: bool = False
    no_generated_content_creation_in_dispatch_gate_confirmed: bool = False
    no_task_creation_in_dispatch_gate_confirmed: bool = False
    no_publish_in_dispatch_gate_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendExecutorDispatchGateDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    creation_gate_descriptor = describe_real_llm_request_send_executor_creation_gate_disabled(
        root=root
    )
    return {
        **creation_gate_descriptor,
        "requestSendExecutorDispatchGateDisabledId": (
            REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ID
        ),
        "upstreamGateId": REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ID,
        "mode": "REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ONLY",
        "requestSendExecutorDispatchGateMode": (
            "REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_MODEL_ONLY"
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
        "explicitRequestSendExecutorDispatchGateDisabledOptIn": (
            request.explicit_request_send_executor_dispatch_gate_disabled_opt_in
        ),
        "executorCreationGateConfirmed": request.executor_creation_gate_confirmed,
        "executorDispatchScopeConfirmed": request.executor_dispatch_scope_confirmed,
        "executorDispatchRecordConfirmed": request.executor_dispatch_record_confirmed,
        "executorDispatchPolicyConfirmed": request.executor_dispatch_policy_confirmed,
        "executorRunReferenceConfirmed": request.executor_run_reference_confirmed,
        "executorIdentityForDispatchConfirmed": (
            request.executor_identity_for_dispatch_confirmed
        ),
        "runtimeGateReferenceForDispatchConfirmed": (
            request.runtime_gate_reference_for_dispatch_confirmed
        ),
        "authorizationRecordReferenceForDispatchConfirmed": (
            request.authorization_record_reference_for_dispatch_confirmed
        ),
        "dispatchQueueBoundaryConfirmed": request.dispatch_queue_boundary_confirmed,
        "dispatchAuditRedactionConfirmed": request.dispatch_audit_redaction_confirmed,
        "dispatchRollbackConfirmed": request.dispatch_rollback_confirmed,
        "dispatchWaitingReviewPolicyConfirmed": (
            request.dispatch_waiting_review_policy_confirmed
        ),
        "noDispatchQueueWriteConfirmed": request.no_dispatch_queue_write_confirmed,
        "noDispatchRecordPersistenceConfirmed": (
            request.no_dispatch_record_persistence_confirmed
        ),
        "noExecutorDispatchInDispatchGateConfirmed": (
            request.no_executor_dispatch_in_dispatch_gate_confirmed
        ),
        "noExecutorStartInDispatchGateConfirmed": (
            request.no_executor_start_in_dispatch_gate_confirmed
        ),
        "noExecutorRunCreationInDispatchGateConfirmed": (
            request.no_executor_run_creation_in_dispatch_gate_confirmed
        ),
        "noRequestSendInDispatchGateConfirmed": (
            request.no_request_send_in_dispatch_gate_confirmed
        ),
        "noSecretReadInDispatchGateConfirmed": (
            request.no_secret_read_in_dispatch_gate_confirmed
        ),
        "noClientCreationInDispatchGateConfirmed": (
            request.no_client_creation_in_dispatch_gate_confirmed
        ),
        "noNetworkAccessInDispatchGateConfirmed": (
            request.no_network_access_in_dispatch_gate_confirmed
        ),
        "noRealCallAuthorizationInDispatchGateConfirmed": (
            request.no_real_call_authorization_in_dispatch_gate_confirmed
        ),
        "noGeneratedContentCreationInDispatchGateConfirmed": (
            request.no_generated_content_creation_in_dispatch_gate_confirmed
        ),
        "noTaskCreationInDispatchGateConfirmed": (
            request.no_task_creation_in_dispatch_gate_confirmed
        ),
        "noPublishInDispatchGateConfirmed": request.no_publish_in_dispatch_gate_confirmed,
        "allowedOperations": [
            "executor_creation_gate_validation",
            "disabled_executor_dispatch_gate_model_generation",
            "future_request_send_attempt_gate_design",
        ],
        "blockedOperations": [
            "dispatch_queue_write",
            "dispatch_record_persistence",
            "executor_dispatch",
            "executor_start",
            "executor_run_creation",
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
        "requestSendExecutorCreationGateDisabledReady": False,
        "requestSendExecutorDispatchGateChecklistReady": False,
        "requestSendExecutorDispatchGateDisabledReady": False,
        "readyForRealRequestSendAttemptGate": False,
        "readyForRealRequestSend": False,
        "executorDispatchGateModelBuilt": False,
        "dispatchQueueWritten": False,
        "dispatchRecordPersisted": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "requestSendAttempted": False,
        "requestSent": False,
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


def describe_real_llm_request_send_executor_dispatch_gate_disabled(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendExecutorDispatchGateDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendExecutorCreationGateDisabledReady": True,
        "requiresExplicitRequestSendExecutorDispatchGateDisabledOptIn": True,
        "requiresExecutorCreationGateConfirmation": True,
        "requiresExecutorDispatchScopeConfirmation": True,
        "requiresExecutorDispatchRecordConfirmation": True,
        "requiresExecutorDispatchPolicyConfirmation": True,
        "requiresExecutorRunReferenceConfirmation": True,
        "requiresExecutorIdentityForDispatchConfirmation": True,
        "requiresRuntimeGateReferenceForDispatchConfirmation": True,
        "requiresAuthorizationRecordReferenceForDispatchConfirmation": True,
        "requiresDispatchQueueBoundaryConfirmation": True,
        "requiresDispatchAuditRedactionConfirmation": True,
        "requiresDispatchRollbackConfirmation": True,
        "requiresDispatchWaitingReviewPolicyConfirmation": True,
        "requiresNoDispatchQueueWriteConfirmation": True,
        "requiresNoDispatchRecordPersistenceConfirmation": True,
        "requiresNoExecutorDispatchInDispatchGateConfirmation": True,
        "requiresNoExecutorStartInDispatchGateConfirmation": True,
        "requiresNoExecutorRunCreationInDispatchGateConfirmation": True,
        "requiresNoRequestSendInDispatchGateConfirmation": True,
        "requiresNoSecretReadInDispatchGateConfirmation": True,
        "requiresNoClientCreationInDispatchGateConfirmation": True,
        "requiresNoNetworkAccessInDispatchGateConfirmation": True,
        "requiresNoRealCallAuthorizationInDispatchGateConfirmation": True,
        "requiresNoGeneratedContentCreationInDispatchGateConfirmation": True,
        "requiresNoTaskCreationInDispatchGateConfirmation": True,
        "requiresNoPublishInDispatchGateConfirmation": True,
        "realRequestSendPath": "future_real_request_send_attempt_gate",
    }


def _validate_provider_scope(
    request: RealLlmRequestSendExecutorDispatchGateDisabledRequest,
) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send executor dispatch gate currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the executor dispatch gate",
                }
            ],
        )


def _executor_dispatch_gate_checklist(
    request: RealLlmRequestSendExecutorDispatchGateDisabledRequest,
    *,
    creation_gate_ready: bool,
) -> list[dict[str, Any]]:
    checks = [
        ("request_send_executor_creation_gate_disabled_ready", creation_gate_ready),
        (
            "explicit_request_send_executor_dispatch_gate_disabled_opt_in",
            request.explicit_request_send_executor_dispatch_gate_disabled_opt_in,
        ),
        ("executor_creation_gate_confirmed", request.executor_creation_gate_confirmed),
        ("executor_dispatch_scope_confirmed", request.executor_dispatch_scope_confirmed),
        ("executor_dispatch_record_confirmed", request.executor_dispatch_record_confirmed),
        ("executor_dispatch_policy_confirmed", request.executor_dispatch_policy_confirmed),
        ("executor_run_reference_confirmed", request.executor_run_reference_confirmed),
        (
            "executor_identity_for_dispatch_confirmed",
            request.executor_identity_for_dispatch_confirmed,
        ),
        (
            "runtime_gate_reference_for_dispatch_confirmed",
            request.runtime_gate_reference_for_dispatch_confirmed,
        ),
        (
            "authorization_record_reference_for_dispatch_confirmed",
            request.authorization_record_reference_for_dispatch_confirmed,
        ),
        ("dispatch_queue_boundary_confirmed", request.dispatch_queue_boundary_confirmed),
        ("dispatch_audit_redaction_confirmed", request.dispatch_audit_redaction_confirmed),
        ("dispatch_rollback_confirmed", request.dispatch_rollback_confirmed),
        (
            "dispatch_waiting_review_policy_confirmed",
            request.dispatch_waiting_review_policy_confirmed,
        ),
        ("no_dispatch_queue_write_confirmed", request.no_dispatch_queue_write_confirmed),
        (
            "no_dispatch_record_persistence_confirmed",
            request.no_dispatch_record_persistence_confirmed,
        ),
        (
            "no_executor_dispatch_in_dispatch_gate_confirmed",
            request.no_executor_dispatch_in_dispatch_gate_confirmed,
        ),
        (
            "no_executor_start_in_dispatch_gate_confirmed",
            request.no_executor_start_in_dispatch_gate_confirmed,
        ),
        (
            "no_executor_run_creation_in_dispatch_gate_confirmed",
            request.no_executor_run_creation_in_dispatch_gate_confirmed,
        ),
        (
            "no_request_send_in_dispatch_gate_confirmed",
            request.no_request_send_in_dispatch_gate_confirmed,
        ),
        (
            "no_secret_read_in_dispatch_gate_confirmed",
            request.no_secret_read_in_dispatch_gate_confirmed,
        ),
        (
            "no_client_creation_in_dispatch_gate_confirmed",
            request.no_client_creation_in_dispatch_gate_confirmed,
        ),
        (
            "no_network_access_in_dispatch_gate_confirmed",
            request.no_network_access_in_dispatch_gate_confirmed,
        ),
        (
            "no_real_call_authorization_in_dispatch_gate_confirmed",
            request.no_real_call_authorization_in_dispatch_gate_confirmed,
        ),
        (
            "no_generated_content_creation_in_dispatch_gate_confirmed",
            request.no_generated_content_creation_in_dispatch_gate_confirmed,
        ),
        ("no_task_creation_in_dispatch_gate_confirmed", request.no_task_creation_in_dispatch_gate_confirmed),
        ("no_publish_in_dispatch_gate_confirmed", request.no_publish_in_dispatch_gate_confirmed),
    ]
    return [{"id": item_id, "passed": passed, "required": True} for item_id, passed in checks]


def _executor_creation_gate_summary(creation_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendExecutorCreationGateDisabledId": creation_gate[
            "requestSendExecutorCreationGateDisabledId"
        ],
        "requestSendRuntimeGateDisabledReady": creation_gate[
            "requestSendRuntimeGateDisabledReady"
        ],
        "requestSendExecutorCreationGateDisabledReady": creation_gate[
            "requestSendExecutorCreationGateDisabledReady"
        ],
        "readyForRealRequestSendExecutorDispatchGate": creation_gate[
            "readyForRealRequestSendExecutorDispatchGate"
        ],
        "readyForRealRequestSend": creation_gate["readyForRealRequestSend"],
        "executorFactoryMaterialized": creation_gate["executorFactoryMaterialized"],
        "sendExecutorCreated": creation_gate["sendExecutorCreated"],
        "sendExecutorDispatched": creation_gate["sendExecutorDispatched"],
        "executorDispatched": creation_gate["executorDispatched"],
        "realCallAuthorized": creation_gate["realCallAuthorized"],
        "requestSent": creation_gate["requestSent"],
        "networkAccess": creation_gate["networkAccess"],
        "realLlmCalled": creation_gate["realLlmCalled"],
        "secretValueRead": creation_gate["secretValueRead"],
        "generatedContentCreated": creation_gate["generatedContentCreated"],
        "taskCreated": creation_gate["taskCreated"],
    }


def _executor_dispatch_gate_model(
    request: RealLlmRequestSendExecutorDispatchGateDisabledRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "executorDispatchGateId": REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ID,
        "built": built,
        "dispatchScope": "single_lab_generate_json_request",
        "executorCreationGateId": REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ID,
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
        "dispatchQueueWrittenNow": False,
        "dispatchRecordPersistedNow": False,
        "executorDispatchedNow": False,
        "executorStartedNow": False,
        "executorRunCreatedNow": False,
        "requestSendAttemptedNow": False,
        "requestSentNow": False,
        "secretReadAllowedNow": False,
        "clientCreationAllowedNow": False,
        "networkAccessAllowedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureRequestSendAttemptGateRequired": True,
    }


def _executor_dispatch_gate_policy() -> dict[str, Any]:
    return {
        "executorDispatchGatePolicyId": (
            "minimal_real_llm_request_send_executor_dispatch_gate_disabled_policy"
        ),
        "writeDispatchQueueNow": False,
        "persistDispatchRecordNow": False,
        "dispatchExecutorNow": False,
        "startExecutorNow": False,
        "createExecutorRunNow": False,
        "attemptRequestSendNow": False,
        "sendRequestNow": False,
        "allowSecretReadNow": False,
        "allowClientCreationNow": False,
        "allowNetworkAccessNow": False,
        "authorizeRealCallNow": False,
        "requiredFutureFields": [
            "executorCreationGateId",
            "executorDispatchGateId",
            "dispatchRecordId",
            "executorId",
            "executorRunId",
            "dispatchPolicy",
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
        "sendExecutionBoundaryId": (
            "minimal_real_llm_request_send_executor_dispatch_gate_disabled_boundary"
        ),
        "dispatchQueueWritten": False,
        "dispatchRecordPersisted": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "readyForRealRequestSend": False,
        "nextStage": "real_request_send_attempt_gate",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "dispatchQueueWritten", "reason": "dispatch_gate_does_not_write_queues"},
            {"field": "dispatchRecordPersisted", "reason": "dispatch_gate_does_not_persist_dispatch_records"},
            {"field": "sendExecutorDispatched", "reason": "dispatch_gate_does_not_dispatch_executors"},
            {"field": "requestSendAttempted", "reason": "requires_future_request_send_attempt_gate"},
            {"field": "requestSent", "reason": "dispatch_gate_does_not_send_requests"},
            {"field": "networkAccess", "reason": "dispatch_gate_does_not_access_network"},
            {"field": "secretValueRead", "reason": "dispatch_gate_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "dispatch_gate_must_not_create_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_executor_dispatch_gate_disabled(
    request: RealLlmRequestSendExecutorDispatchGateDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    creation_gate = build_real_llm_request_send_executor_creation_gate_disabled(
        request,
        root=root,
    )
    creation_gate_ready = (
        creation_gate.get("requestSendExecutorCreationGateDisabledReady") is True
    )
    checklist = _executor_dispatch_gate_checklist(
        request,
        creation_gate_ready=creation_gate_ready,
    )
    checklist_passed = all(
        item["passed"] is True for item in checklist if item["required"] is True
    )

    return {
        **context,
        "requestSendExecutorCreationGateDisabledReady": creation_gate_ready,
        "requestSendExecutorCreationGateDisabledSummary": (
            _executor_creation_gate_summary(creation_gate)
        ),
        "requestSendExecutorDispatchGateChecklist": checklist,
        "requestSendExecutorDispatchGateChecklistReady": checklist_passed,
        "requestSendExecutorDispatchGateDisabledReady": checklist_passed,
        "readyForRealRequestSendAttemptGate": checklist_passed,
        "readyForRealRequestSend": False,
        "executorDispatchGateModel": _executor_dispatch_gate_model(
            request,
            built=checklist_passed,
        ),
        "executorDispatchGatePolicy": _executor_dispatch_gate_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "executorDispatchGateModelBuilt": checklist_passed,
        "dispatchQueueWritten": False,
        "dispatchRecordPersisted": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "requestSendAttempted": False,
        "requestSent": False,
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
            "真实 LLM 请求发送执行器派发门禁禁用模型已生成；当前不会写派发队列、"
            "持久化派发记录、派发执行器、启动执行器、创建运行记录、读取密钥、"
            "创建 client、联网、授权真实调用、发送请求、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_executor_dispatch_gate_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendExecutorDispatchGateDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendExecutorDispatchGateDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            creation_gate = build_real_llm_request_send_executor_creation_gate_disabled(
                request,
                root=root,
            )
        else:
            creation_gate = None
    except ProviderError:
        creation_gate = None
    if creation_gate is not None:
        context["requestSendExecutorCreationGateDisabledReady"] = bool(
            creation_gate.get("requestSendExecutorCreationGateDisabledReady", False)
        )
        context["requestSendExecutorCreationGateDisabledSummary"] = (
            _executor_creation_gate_summary(creation_gate)
        )
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
