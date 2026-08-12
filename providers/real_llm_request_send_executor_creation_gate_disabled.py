"""Disabled executor creation gate for the real LLM request-send path.

This module accepts a completed disabled runtime gate model and prepares a local
executor creation gate model. It never materializes executor factories, creates
or persists executors, starts executors, creates executor runs, dispatches
executors, sends requests, reads secrets, creates clients, accesses network,
creates generated content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_runtime_gate_disabled import (
    REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ID,
    RealLlmRequestSendRuntimeGateDisabledRequest,
    build_real_llm_request_send_runtime_gate_disabled,
    describe_real_llm_request_send_runtime_gate_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ID = (
    "real_llm_request_send_executor_creation_gate_disabled"
)


@dataclass(frozen=True)
class RealLlmRequestSendExecutorCreationGateDisabledRequest(
    RealLlmRequestSendRuntimeGateDisabledRequest
):
    explicit_request_send_executor_creation_gate_disabled_opt_in: bool = False
    runtime_gate_disabled_confirmed: bool = False
    executor_creation_scope_confirmed: bool = False
    executor_creation_record_confirmed: bool = False
    executor_factory_boundary_confirmed: bool = False
    executor_identity_boundary_confirmed: bool = False
    executor_runtime_gate_reference_confirmed: bool = False
    executor_secret_boundary_confirmed: bool = False
    executor_client_boundary_confirmed: bool = False
    executor_dispatch_boundary_confirmed: bool = False
    executor_audit_redaction_confirmed: bool = False
    executor_rollback_confirmed: bool = False
    executor_waiting_review_policy_confirmed: bool = False
    no_executor_factory_materialization_confirmed: bool = False
    no_executor_creation_confirmed: bool = False
    no_executor_persistence_confirmed: bool = False
    no_executor_start_confirmed: bool = False
    no_executor_run_creation_confirmed: bool = False
    no_executor_dispatch_confirmed: bool = False
    no_request_send_in_executor_creation_gate_confirmed: bool = False
    no_secret_read_in_executor_creation_gate_confirmed: bool = False
    no_client_creation_in_executor_creation_gate_confirmed: bool = False
    no_network_access_in_executor_creation_gate_confirmed: bool = False
    no_real_call_authorization_in_executor_creation_gate_confirmed: bool = False
    no_generated_content_creation_in_executor_creation_gate_confirmed: bool = False
    no_task_creation_in_executor_creation_gate_confirmed: bool = False
    no_publish_in_executor_creation_gate_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendExecutorCreationGateDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    runtime_gate_descriptor = describe_real_llm_request_send_runtime_gate_disabled(
        root=root
    )
    return {
        **runtime_gate_descriptor,
        "requestSendExecutorCreationGateDisabledId": (
            REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ID
        ),
        "upstreamGateId": REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ID,
        "mode": "REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ONLY",
        "requestSendExecutorCreationGateMode": (
            "REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_MODEL_ONLY"
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
        "explicitRequestSendExecutorCreationGateDisabledOptIn": (
            request.explicit_request_send_executor_creation_gate_disabled_opt_in
        ),
        "runtimeGateDisabledConfirmed": request.runtime_gate_disabled_confirmed,
        "executorCreationScopeConfirmed": request.executor_creation_scope_confirmed,
        "executorCreationRecordConfirmed": request.executor_creation_record_confirmed,
        "executorFactoryBoundaryConfirmed": request.executor_factory_boundary_confirmed,
        "executorIdentityBoundaryConfirmed": (
            request.executor_identity_boundary_confirmed
        ),
        "executorRuntimeGateReferenceConfirmed": (
            request.executor_runtime_gate_reference_confirmed
        ),
        "executorSecretBoundaryConfirmed": request.executor_secret_boundary_confirmed,
        "executorClientBoundaryConfirmed": request.executor_client_boundary_confirmed,
        "executorDispatchBoundaryConfirmed": (
            request.executor_dispatch_boundary_confirmed
        ),
        "executorAuditRedactionConfirmed": request.executor_audit_redaction_confirmed,
        "executorRollbackConfirmed": request.executor_rollback_confirmed,
        "executorWaitingReviewPolicyConfirmed": (
            request.executor_waiting_review_policy_confirmed
        ),
        "noExecutorFactoryMaterializationConfirmed": (
            request.no_executor_factory_materialization_confirmed
        ),
        "noExecutorCreationConfirmed": request.no_executor_creation_confirmed,
        "noExecutorPersistenceConfirmed": request.no_executor_persistence_confirmed,
        "noExecutorStartConfirmed": request.no_executor_start_confirmed,
        "noExecutorRunCreationConfirmed": request.no_executor_run_creation_confirmed,
        "noExecutorDispatchConfirmed": request.no_executor_dispatch_confirmed,
        "noRequestSendInExecutorCreationGateConfirmed": (
            request.no_request_send_in_executor_creation_gate_confirmed
        ),
        "noSecretReadInExecutorCreationGateConfirmed": (
            request.no_secret_read_in_executor_creation_gate_confirmed
        ),
        "noClientCreationInExecutorCreationGateConfirmed": (
            request.no_client_creation_in_executor_creation_gate_confirmed
        ),
        "noNetworkAccessInExecutorCreationGateConfirmed": (
            request.no_network_access_in_executor_creation_gate_confirmed
        ),
        "noRealCallAuthorizationInExecutorCreationGateConfirmed": (
            request.no_real_call_authorization_in_executor_creation_gate_confirmed
        ),
        "noGeneratedContentCreationInExecutorCreationGateConfirmed": (
            request.no_generated_content_creation_in_executor_creation_gate_confirmed
        ),
        "noTaskCreationInExecutorCreationGateConfirmed": (
            request.no_task_creation_in_executor_creation_gate_confirmed
        ),
        "noPublishInExecutorCreationGateConfirmed": (
            request.no_publish_in_executor_creation_gate_confirmed
        ),
        "allowedOperations": [
            "runtime_gate_disabled_validation",
            "disabled_executor_creation_gate_model_generation",
            "future_send_executor_dispatch_gate_design",
        ],
        "blockedOperations": [
            "executor_factory_materialization",
            "executor_creation",
            "executor_persistence",
            "executor_start",
            "executor_run_creation",
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
        "requestSendRuntimeGateDisabledReady": False,
        "requestSendExecutorCreationGateChecklistReady": False,
        "requestSendExecutorCreationGateDisabledReady": False,
        "readyForRealRequestSendExecutorDispatchGate": False,
        "readyForRealRequestSend": False,
        "executorCreationGateModelBuilt": False,
        "executorFactoryMaterialized": False,
        "sendExecutorCreated": False,
        "sendExecutorPersisted": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
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


def describe_real_llm_request_send_executor_creation_gate_disabled(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealLlmRequestSendExecutorCreationGateDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendRuntimeGateDisabledReady": True,
        "requiresExplicitRequestSendExecutorCreationGateDisabledOptIn": True,
        "requiresRuntimeGateDisabledConfirmation": True,
        "requiresExecutorCreationScopeConfirmation": True,
        "requiresExecutorCreationRecordConfirmation": True,
        "requiresExecutorFactoryBoundaryConfirmation": True,
        "requiresExecutorIdentityBoundaryConfirmation": True,
        "requiresExecutorRuntimeGateReferenceConfirmation": True,
        "requiresExecutorSecretBoundaryConfirmation": True,
        "requiresExecutorClientBoundaryConfirmation": True,
        "requiresExecutorDispatchBoundaryConfirmation": True,
        "requiresExecutorAuditRedactionConfirmation": True,
        "requiresExecutorRollbackConfirmation": True,
        "requiresExecutorWaitingReviewPolicyConfirmation": True,
        "requiresNoExecutorFactoryMaterializationConfirmation": True,
        "requiresNoExecutorCreationConfirmation": True,
        "requiresNoExecutorPersistenceConfirmation": True,
        "requiresNoExecutorStartConfirmation": True,
        "requiresNoExecutorRunCreationConfirmation": True,
        "requiresNoExecutorDispatchConfirmation": True,
        "requiresNoRequestSendInExecutorCreationGateConfirmation": True,
        "requiresNoSecretReadInExecutorCreationGateConfirmation": True,
        "requiresNoClientCreationInExecutorCreationGateConfirmation": True,
        "requiresNoNetworkAccessInExecutorCreationGateConfirmation": True,
        "requiresNoRealCallAuthorizationInExecutorCreationGateConfirmation": True,
        "requiresNoGeneratedContentCreationInExecutorCreationGateConfirmation": True,
        "requiresNoTaskCreationInExecutorCreationGateConfirmation": True,
        "requiresNoPublishInExecutorCreationGateConfirmation": True,
        "realRequestSendPath": "future_real_request_send_executor_dispatch_gate",
    }


def _validate_provider_scope(
    request: RealLlmRequestSendExecutorCreationGateDisabledRequest,
) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send executor creation gate currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the executor creation gate",
                }
            ],
        )


def _executor_creation_gate_checklist(
    request: RealLlmRequestSendExecutorCreationGateDisabledRequest,
    *,
    runtime_gate_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "request_send_runtime_gate_disabled_ready",
            "passed": runtime_gate_ready,
            "required": True,
        },
        {
            "id": "explicit_request_send_executor_creation_gate_disabled_opt_in",
            "passed": request.explicit_request_send_executor_creation_gate_disabled_opt_in,
            "required": True,
        },
        {
            "id": "runtime_gate_disabled_confirmed",
            "passed": request.runtime_gate_disabled_confirmed,
            "required": True,
        },
        {
            "id": "executor_creation_scope_confirmed",
            "passed": request.executor_creation_scope_confirmed,
            "required": True,
        },
        {
            "id": "executor_creation_record_confirmed",
            "passed": request.executor_creation_record_confirmed,
            "required": True,
        },
        {
            "id": "executor_factory_boundary_confirmed",
            "passed": request.executor_factory_boundary_confirmed,
            "required": True,
        },
        {
            "id": "executor_identity_boundary_confirmed",
            "passed": request.executor_identity_boundary_confirmed,
            "required": True,
        },
        {
            "id": "executor_runtime_gate_reference_confirmed",
            "passed": request.executor_runtime_gate_reference_confirmed,
            "required": True,
        },
        {
            "id": "executor_secret_boundary_confirmed",
            "passed": request.executor_secret_boundary_confirmed,
            "required": True,
        },
        {
            "id": "executor_client_boundary_confirmed",
            "passed": request.executor_client_boundary_confirmed,
            "required": True,
        },
        {
            "id": "executor_dispatch_boundary_confirmed",
            "passed": request.executor_dispatch_boundary_confirmed,
            "required": True,
        },
        {
            "id": "executor_audit_redaction_confirmed",
            "passed": request.executor_audit_redaction_confirmed,
            "required": True,
        },
        {
            "id": "executor_rollback_confirmed",
            "passed": request.executor_rollback_confirmed,
            "required": True,
        },
        {
            "id": "executor_waiting_review_policy_confirmed",
            "passed": request.executor_waiting_review_policy_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_factory_materialization_confirmed",
            "passed": request.no_executor_factory_materialization_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_creation_confirmed",
            "passed": request.no_executor_creation_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_persistence_confirmed",
            "passed": request.no_executor_persistence_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_start_confirmed",
            "passed": request.no_executor_start_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_run_creation_confirmed",
            "passed": request.no_executor_run_creation_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_confirmed",
            "passed": request.no_executor_dispatch_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_executor_creation_gate_confirmed",
            "passed": request.no_request_send_in_executor_creation_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_executor_creation_gate_confirmed",
            "passed": request.no_secret_read_in_executor_creation_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_client_creation_in_executor_creation_gate_confirmed",
            "passed": request.no_client_creation_in_executor_creation_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_executor_creation_gate_confirmed",
            "passed": request.no_network_access_in_executor_creation_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_authorization_in_executor_creation_gate_confirmed",
            "passed": request.no_real_call_authorization_in_executor_creation_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_generated_content_creation_in_executor_creation_gate_confirmed",
            "passed": request.no_generated_content_creation_in_executor_creation_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_executor_creation_gate_confirmed",
            "passed": request.no_task_creation_in_executor_creation_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_executor_creation_gate_confirmed",
            "passed": request.no_publish_in_executor_creation_gate_confirmed,
            "required": True,
        },
    ]


def _runtime_gate_summary(runtime_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendRuntimeGateDisabledId": runtime_gate[
            "requestSendRuntimeGateDisabledId"
        ],
        "requestSendAuthorizationRecordWriteGateReady": runtime_gate[
            "requestSendAuthorizationRecordWriteGateReady"
        ],
        "requestSendRuntimeGateDisabledReady": runtime_gate[
            "requestSendRuntimeGateDisabledReady"
        ],
        "readyForRealRequestSendExecutorCreationGate": runtime_gate[
            "readyForRealRequestSendExecutorCreationGate"
        ],
        "readyForRealRequestSend": runtime_gate["readyForRealRequestSend"],
        "runtimeGateOpened": runtime_gate["runtimeGateOpened"],
        "runtimeKillSwitchDisabled": runtime_gate["runtimeKillSwitchDisabled"],
        "runtimeBudgetReserved": runtime_gate["runtimeBudgetReserved"],
        "runtimeNetworkEgressOpened": runtime_gate["runtimeNetworkEgressOpened"],
        "sendExecutorCreated": runtime_gate["sendExecutorCreated"],
        "sendExecutorDispatched": runtime_gate["sendExecutorDispatched"],
        "realCallAuthorized": runtime_gate["realCallAuthorized"],
        "requestSent": runtime_gate["requestSent"],
        "networkAccess": runtime_gate["networkAccess"],
        "realLlmCalled": runtime_gate["realLlmCalled"],
        "secretValueRead": runtime_gate["secretValueRead"],
        "generatedContentCreated": runtime_gate["generatedContentCreated"],
        "taskCreated": runtime_gate["taskCreated"],
    }


def _executor_creation_gate_model(
    request: RealLlmRequestSendExecutorCreationGateDisabledRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "executorCreationGateId": (
            REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ID
        ),
        "built": built,
        "executorScope": "single_lab_generate_json_request",
        "runtimeGateId": REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ID,
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
        "executorFactoryMaterializedNow": False,
        "executorCreatedNow": False,
        "executorPersistedNow": False,
        "executorStartedNow": False,
        "executorRunCreatedNow": False,
        "executorDispatchedNow": False,
        "secretReadAllowedNow": False,
        "clientCreationAllowedNow": False,
        "networkAccessAllowedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureSendExecutorDispatchGateRequired": True,
    }


def _executor_creation_gate_policy() -> dict[str, Any]:
    return {
        "executorCreationGatePolicyId": (
            "minimal_real_llm_request_send_executor_creation_gate_disabled_policy"
        ),
        "materializeExecutorFactoryNow": False,
        "createExecutorNow": False,
        "persistExecutorNow": False,
        "startExecutorNow": False,
        "createExecutorRunNow": False,
        "dispatchExecutorNow": False,
        "allowSecretReadNow": False,
        "allowClientCreationNow": False,
        "allowNetworkAccessNow": False,
        "authorizeRealCallNow": False,
        "requiredFutureFields": [
            "runtimeGateId",
            "executorCreationGateId",
            "executorId",
            "executorFactory",
            "executorIdentity",
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
            "minimal_real_llm_request_send_executor_creation_gate_disabled_boundary"
        ),
        "executorFactoryMaterialized": False,
        "sendExecutorCreated": False,
        "sendExecutorPersisted": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "readyForRealRequestSend": False,
        "nextStage": "real_request_send_executor_dispatch_gate",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "executorFactoryMaterialized", "reason": "executor_creation_gate_does_not_materialize_factories"},
            {"field": "sendExecutorCreated", "reason": "executor_creation_gate_does_not_create_executors"},
            {"field": "sendExecutorPersisted", "reason": "executor_creation_gate_does_not_persist_executors"},
            {"field": "sendExecutorStarted", "reason": "executor_creation_gate_does_not_start_executors"},
            {"field": "sendExecutorRunCreated", "reason": "executor_creation_gate_does_not_create_runs"},
            {"field": "sendExecutorDispatched", "reason": "requires_future_executor_dispatch_gate"},
            {"field": "realCallAuthorized", "reason": "requires_future_real_request_send_executor_dispatch_gate"},
            {"field": "requestSent", "reason": "executor_creation_gate_does_not_send_requests"},
            {"field": "networkAccess", "reason": "executor_creation_gate_does_not_access_network"},
            {"field": "secretValueRead", "reason": "executor_creation_gate_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "executor_creation_gate_must_not_create_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_executor_creation_gate_disabled(
    request: RealLlmRequestSendExecutorCreationGateDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    runtime_gate = build_real_llm_request_send_runtime_gate_disabled(
        request,
        root=root,
    )
    runtime_gate_ready = runtime_gate.get("requestSendRuntimeGateDisabledReady") is True
    checklist = _executor_creation_gate_checklist(
        request,
        runtime_gate_ready=runtime_gate_ready,
    )
    checklist_passed = all(
        item["passed"] is True for item in checklist if item["required"] is True
    )

    return {
        **context,
        "requestSendRuntimeGateDisabledReady": runtime_gate_ready,
        "requestSendRuntimeGateDisabledSummary": _runtime_gate_summary(runtime_gate),
        "requestSendExecutorCreationGateChecklist": checklist,
        "requestSendExecutorCreationGateChecklistReady": checklist_passed,
        "requestSendExecutorCreationGateDisabledReady": checklist_passed,
        "readyForRealRequestSendExecutorDispatchGate": checklist_passed,
        "readyForRealRequestSend": False,
        "executorCreationGateModel": _executor_creation_gate_model(
            request,
            built=checklist_passed,
        ),
        "executorCreationGatePolicy": _executor_creation_gate_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "executorCreationGateModelBuilt": checklist_passed,
        "executorFactoryMaterialized": False,
        "sendExecutorCreated": False,
        "sendExecutorPersisted": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
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
            "真实 LLM 请求发送执行器创建门禁禁用模型已生成；当前不会物化 factory、"
            "创建/持久化/启动执行器、创建运行记录、派发执行器、读取密钥、创建 client、"
            "联网、授权真实调用、发送请求、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_executor_creation_gate_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendExecutorCreationGateDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendExecutorCreationGateDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            runtime_gate = build_real_llm_request_send_runtime_gate_disabled(
                request,
                root=root,
            )
        else:
            runtime_gate = None
    except ProviderError:
        runtime_gate = None
    if runtime_gate is not None:
        context["requestSendRuntimeGateDisabledReady"] = bool(
            runtime_gate.get("requestSendRuntimeGateDisabledReady", False)
        )
        context["requestSendRuntimeGateDisabledSummary"] = _runtime_gate_summary(
            runtime_gate
        )
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
