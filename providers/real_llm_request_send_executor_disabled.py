"""Disabled executor model for the real LLM request-send path.

This module accepts a completed disabled execution-request model and turns it
into a local disabled executor review model. It never grants approval,
authorizes a real call, creates or starts executors, creates executor runs,
dispatches executors, sends requests, reads secrets, accesses network, creates
generated content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_send_execution_request_disabled import (
    RealLlmRequestSendExecutionRequestDisabledRequest,
    build_real_llm_request_send_execution_request_disabled,
    describe_real_llm_request_send_execution_request_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_SEND_EXECUTOR_DISABLED_ID = "real_llm_request_send_executor_disabled"


@dataclass(frozen=True)
class RealLlmRequestSendExecutorDisabledRequest(
    RealLlmRequestSendExecutionRequestDisabledRequest
):
    explicit_request_send_executor_disabled_opt_in: bool = False
    request_send_execution_request_confirmed: bool = False
    executor_scope_confirmed: bool = False
    executor_record_confirmed: bool = False
    executor_disabled_boundary_confirmed: bool = False
    executor_dispatch_block_confirmed: bool = False
    send_runtime_disabled_confirmed: bool = False
    single_request_executor_confirmed: bool = False
    lab_only_executor_confirmed: bool = False
    runtime_kill_switch_confirmed_for_executor: bool = False
    audit_event_confirmed_for_executor: bool = False
    rollback_confirmed_for_executor: bool = False
    no_executor_start_in_request_send_executor_confirmed: bool = False
    no_executor_run_creation_in_request_send_executor_confirmed: bool = False
    no_executor_dispatch_in_request_send_executor_confirmed: bool = False
    no_request_send_in_request_send_executor_confirmed: bool = False
    no_secret_read_in_request_send_executor_confirmed: bool = False
    no_network_access_in_request_send_executor_confirmed: bool = False
    no_generated_content_creation_in_request_send_executor_confirmed: bool = False
    no_task_creation_in_request_send_executor_confirmed: bool = False
    no_publish_in_request_send_executor_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestSendExecutorDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    execution_request_descriptor = describe_real_llm_request_send_execution_request_disabled(
        root=root
    )
    return {
        **execution_request_descriptor,
        "requestSendExecutorDisabledId": REAL_LLM_REQUEST_SEND_EXECUTOR_DISABLED_ID,
        "upstreamGateId": "real_llm_request_send_execution_request_disabled",
        "mode": "REAL_LLM_REQUEST_SEND_EXECUTOR_DISABLED_ONLY",
        "executorMode": "DISABLED_REAL_REQUEST_SEND_EXECUTOR_MODEL_ONLY",
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
        "explicitRequestSendExecutorDisabledOptIn": (
            request.explicit_request_send_executor_disabled_opt_in
        ),
        "requestSendExecutionRequestConfirmed": (
            request.request_send_execution_request_confirmed
        ),
        "executorScopeConfirmed": request.executor_scope_confirmed,
        "executorRecordConfirmed": request.executor_record_confirmed,
        "executorDisabledBoundaryConfirmed": request.executor_disabled_boundary_confirmed,
        "executorDispatchBlockConfirmed": request.executor_dispatch_block_confirmed,
        "sendRuntimeDisabledConfirmed": request.send_runtime_disabled_confirmed,
        "singleRequestExecutorConfirmed": request.single_request_executor_confirmed,
        "labOnlyExecutorConfirmed": request.lab_only_executor_confirmed,
        "runtimeKillSwitchConfirmedForExecutor": (
            request.runtime_kill_switch_confirmed_for_executor
        ),
        "auditEventConfirmedForExecutor": request.audit_event_confirmed_for_executor,
        "rollbackConfirmedForExecutor": request.rollback_confirmed_for_executor,
        "noExecutorStartInRequestSendExecutorConfirmed": (
            request.no_executor_start_in_request_send_executor_confirmed
        ),
        "noExecutorRunCreationInRequestSendExecutorConfirmed": (
            request.no_executor_run_creation_in_request_send_executor_confirmed
        ),
        "noExecutorDispatchInRequestSendExecutorConfirmed": (
            request.no_executor_dispatch_in_request_send_executor_confirmed
        ),
        "noRequestSendInRequestSendExecutorConfirmed": (
            request.no_request_send_in_request_send_executor_confirmed
        ),
        "noSecretReadInRequestSendExecutorConfirmed": (
            request.no_secret_read_in_request_send_executor_confirmed
        ),
        "noNetworkAccessInRequestSendExecutorConfirmed": (
            request.no_network_access_in_request_send_executor_confirmed
        ),
        "noGeneratedContentCreationInRequestSendExecutorConfirmed": (
            request.no_generated_content_creation_in_request_send_executor_confirmed
        ),
        "noTaskCreationInRequestSendExecutorConfirmed": (
            request.no_task_creation_in_request_send_executor_confirmed
        ),
        "noPublishInRequestSendExecutorConfirmed": (
            request.no_publish_in_request_send_executor_confirmed
        ),
        "allowedOperations": [
            "disabled_execution_request_validation",
            "disabled_send_executor_model_generation",
            "future_final_manual_send_review_design",
        ],
        "blockedOperations": [
            "manual_approval_grant",
            "real_call_authorization",
            "executor_creation",
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
        "requestSendExecutionRequestDisabledReady": False,
        "requestSendExecutorChecklistReady": False,
        "requestSendExecutorDisabledReady": False,
        "readyForFinalRealRequestSendApprovalReview": False,
        "readyForRealRequestSend": False,
        "requestSendExecutorPlanBuilt": False,
        "requestSendExecutorDisabledModelBuilt": False,
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
        "sendExecutorMaterialized": False,
        "sendExecutorPersisted": False,
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


def describe_real_llm_request_send_executor_disabled(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmRequestSendExecutorDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestSendExecutionRequestDisabledReady": True,
        "requiresExplicitRequestSendExecutorDisabledOptIn": True,
        "requiresRequestSendExecutionRequestConfirmation": True,
        "requiresExecutorScopeConfirmation": True,
        "requiresExecutorRecordConfirmation": True,
        "requiresExecutorDisabledBoundaryConfirmation": True,
        "requiresExecutorDispatchBlockConfirmation": True,
        "requiresSendRuntimeDisabledConfirmation": True,
        "requiresSingleRequestExecutorConfirmation": True,
        "requiresLabOnlyExecutorConfirmation": True,
        "requiresRuntimeKillSwitchForExecutorConfirmation": True,
        "requiresAuditEventForExecutorConfirmation": True,
        "requiresRollbackForExecutorConfirmation": True,
        "requiresNoExecutorStartInRequestSendExecutorConfirmation": True,
        "requiresNoExecutorRunCreationInRequestSendExecutorConfirmation": True,
        "requiresNoExecutorDispatchInRequestSendExecutorConfirmation": True,
        "requiresNoRequestSendInRequestSendExecutorConfirmation": True,
        "requiresNoSecretReadInRequestSendExecutorConfirmation": True,
        "requiresNoNetworkAccessInRequestSendExecutorConfirmation": True,
        "requiresNoGeneratedContentCreationInRequestSendExecutorConfirmation": True,
        "requiresNoTaskCreationInRequestSendExecutorConfirmation": True,
        "requiresNoPublishInRequestSendExecutorConfirmation": True,
        "realCallAuthorizationPath": "future_final_manual_real_request_send_approval_review",
    }


def _validate_provider_scope(request: RealLlmRequestSendExecutorDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request send executor currently only supports openai",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed for the disabled request send executor",
                }
            ],
        )


def _executor_checklist(
    request: RealLlmRequestSendExecutorDisabledRequest,
    *,
    execution_request_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "request_send_execution_request_disabled_ready", "passed": execution_request_ready, "required": True},
        {
            "id": "explicit_request_send_executor_disabled_opt_in",
            "passed": request.explicit_request_send_executor_disabled_opt_in,
            "required": True,
        },
        {
            "id": "request_send_execution_request_confirmed",
            "passed": request.request_send_execution_request_confirmed,
            "required": True,
        },
        {"id": "executor_scope_confirmed", "passed": request.executor_scope_confirmed, "required": True},
        {"id": "executor_record_confirmed", "passed": request.executor_record_confirmed, "required": True},
        {
            "id": "executor_disabled_boundary_confirmed",
            "passed": request.executor_disabled_boundary_confirmed,
            "required": True,
        },
        {
            "id": "executor_dispatch_block_confirmed",
            "passed": request.executor_dispatch_block_confirmed,
            "required": True,
        },
        {
            "id": "send_runtime_disabled_confirmed",
            "passed": request.send_runtime_disabled_confirmed,
            "required": True,
        },
        {
            "id": "single_request_executor_confirmed",
            "passed": request.single_request_executor_confirmed,
            "required": True,
        },
        {
            "id": "lab_only_executor_confirmed",
            "passed": request.lab_only_executor_confirmed,
            "required": True,
        },
        {
            "id": "runtime_kill_switch_confirmed_for_executor",
            "passed": request.runtime_kill_switch_confirmed_for_executor,
            "required": True,
        },
        {
            "id": "audit_event_confirmed_for_executor",
            "passed": request.audit_event_confirmed_for_executor,
            "required": True,
        },
        {
            "id": "rollback_confirmed_for_executor",
            "passed": request.rollback_confirmed_for_executor,
            "required": True,
        },
        {
            "id": "no_executor_start_in_request_send_executor_confirmed",
            "passed": request.no_executor_start_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_run_creation_in_request_send_executor_confirmed",
            "passed": request.no_executor_run_creation_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_in_request_send_executor_confirmed",
            "passed": request.no_executor_dispatch_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_request_send_executor_confirmed",
            "passed": request.no_request_send_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_request_send_executor_confirmed",
            "passed": request.no_secret_read_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_request_send_executor_confirmed",
            "passed": request.no_network_access_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_generated_content_creation_in_request_send_executor_confirmed",
            "passed": request.no_generated_content_creation_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_request_send_executor_confirmed",
            "passed": request.no_task_creation_in_request_send_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_request_send_executor_confirmed",
            "passed": request.no_publish_in_request_send_executor_confirmed,
            "required": True,
        },
    ]


def _execution_request_summary(execution_request: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestSendExecutionRequestDisabledId": execution_request[
            "requestSendExecutionRequestDisabledId"
        ],
        "requestSendAuthorizationPackageReady": execution_request[
            "requestSendAuthorizationPackageReady"
        ],
        "requestSendExecutionRequestDisabledReady": execution_request[
            "requestSendExecutionRequestDisabledReady"
        ],
        "readyForDisabledRealRequestSendExecutor": execution_request[
            "readyForDisabledRealRequestSendExecutor"
        ],
        "readyForRealRequestSend": execution_request["readyForRealRequestSend"],
        "executionRequestPersisted": execution_request["executionRequestPersisted"],
        "executionRequestQueued": execution_request["executionRequestQueued"],
        "executionRequestDispatched": execution_request["executionRequestDispatched"],
        "manualApprovalGranted": execution_request["manualApprovalGranted"],
        "realCallAuthorized": execution_request["realCallAuthorized"],
        "requestSent": execution_request["requestSent"],
        "networkAccess": execution_request["networkAccess"],
        "realLlmCalled": execution_request["realLlmCalled"],
        "secretValueRead": execution_request["secretValueRead"],
        "generatedContentCreated": execution_request["generatedContentCreated"],
        "taskCreated": execution_request["taskCreated"],
    }


def _executor_model(
    request: RealLlmRequestSendExecutorDisabledRequest,
    *,
    built: bool,
) -> dict[str, Any]:
    return {
        "executorId": REAL_LLM_REQUEST_SEND_EXECUTOR_DISABLED_ID,
        "built": built,
        "executorScope": "single_lab_generate_json_request",
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
        "createdNow": False,
        "materializedNow": False,
        "persistedNow": False,
        "startedNow": False,
        "runCreatedNow": False,
        "dispatchedNow": False,
        "manualApprovalGrantedNow": False,
        "realCallAuthorizedNow": False,
        "sendAllowedNow": False,
        "futureFinalHumanApprovalRequired": True,
    }


def _executor_policy() -> dict[str, Any]:
    return {
        "executorPolicyId": "minimal_real_llm_request_send_executor_disabled_policy",
        "createExecutorNow": False,
        "materializeExecutorNow": False,
        "persistExecutorNow": False,
        "startExecutorNow": False,
        "createExecutorRunNow": False,
        "dispatchExecutorNow": False,
        "requiredFutureFields": [
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
            "timeoutSeconds",
            "retryCount",
        ],
    }


def _send_execution_boundary() -> dict[str, Any]:
    return {
        "sendExecutionBoundaryId": "minimal_real_llm_request_send_executor_disabled_boundary",
        "sendExecutorCreated": False,
        "sendExecutorMaterialized": False,
        "sendExecutorPersisted": False,
        "sendExecutorStarted": False,
        "sendExecutorRunCreated": False,
        "sendExecutorDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "readyForRealRequestSend": False,
        "nextStage": "final_real_request_send_approval_review",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "manualApprovalGranted", "reason": "disabled_executor_does_not_grant_approval"},
            {"field": "realCallAuthorized", "reason": "requires_future_final_human_approval"},
            {"field": "sendExecutorStarted", "reason": "disabled_executor_model_is_not_started"},
            {"field": "sendExecutorRunCreated", "reason": "disabled_executor_model_creates_no_runs"},
            {"field": "sendExecutorDispatched", "reason": "disabled_executor_model_is_not_dispatched"},
            {"field": "requestSent", "reason": "disabled_executor_model_does_not_send_requests"},
            {"field": "networkAccess", "reason": "disabled_executor_model_does_not_access_network"},
            {"field": "secretValueRead", "reason": "disabled_executor_model_does_not_read_secret_values"},
            {"field": "taskCreated", "reason": "disabled_executor_model_must_not_create_ai_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_request_send_executor_disabled(
    request: RealLlmRequestSendExecutorDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    execution_request = build_real_llm_request_send_execution_request_disabled(request, root=root)
    execution_request_ready = (
        execution_request.get("requestSendExecutionRequestDisabledReady") is True
    )
    checklist = _executor_checklist(request, execution_request_ready=execution_request_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestSendExecutionRequestDisabledReady": execution_request_ready,
        "executionRequestSummary": _execution_request_summary(execution_request),
        "requestSendExecutorChecklist": checklist,
        "requestSendExecutorChecklistReady": checklist_passed,
        "requestSendExecutorDisabledReady": checklist_passed,
        "readyForFinalRealRequestSendApprovalReview": checklist_passed,
        "readyForRealRequestSend": False,
        "requestSendExecutor": _executor_model(request, built=checklist_passed),
        "requestSendExecutorPolicy": _executor_policy(),
        "sendExecutionBoundary": _send_execution_boundary(),
        "requestSendExecutorPlanBuilt": checklist_passed,
        "requestSendExecutorDisabledModelBuilt": checklist_passed,
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
        "sendExecutorMaterialized": False,
        "sendExecutorPersisted": False,
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
            "真实 LLM 请求发送执行器禁用模型已生成；当前不会授予人工批准、授权真实调用、"
            "创建或启动执行器、创建运行记录、派发执行器、发送请求、联网、读取密钥、创建任务或发布。"
        ),
    }


def build_real_llm_request_send_executor_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestSendExecutorDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestSendExecutorDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            execution_request = build_real_llm_request_send_execution_request_disabled(
                request,
                root=root,
            )
        else:
            execution_request = None
    except ProviderError:
        execution_request = None
    if execution_request is not None:
        context["requestSendExecutionRequestDisabledReady"] = bool(
            execution_request.get("requestSendExecutionRequestDisabledReady", False)
        )
        context["executionRequestSummary"] = _execution_request_summary(execution_request)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
