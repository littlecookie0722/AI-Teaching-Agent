"""Disabled executor for the first real LLM call.

This module wires the client-boundary confirmation, request review package, and
first-call approval gate into a local disabled executor model. It never
dispatches an executor, sends a request, reads secret values, accesses network,
creates generated content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_first_call_approval_gate import (
    RealLlmFirstCallApprovalGateRequest,
    describe_real_llm_first_call_approval_gate,
    evaluate_real_llm_first_call_approval_gate,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_FIRST_CALL_EXECUTOR_DISABLED_ID = "real_llm_first_call_executor_disabled"


@dataclass(frozen=True)
class RealLlmFirstCallExecutorDisabledRequest(RealLlmFirstCallApprovalGateRequest):
    explicit_disabled_executor_opt_in: bool = False
    first_call_approval_gate_confirmed: bool = False
    client_boundary_ready_confirmed: bool = False
    request_shape_confirmed: bool = False
    no_executor_dispatch_confirmed: bool = False
    no_request_send_in_executor_confirmed: bool = False
    no_network_access_in_executor_confirmed: bool = False
    no_real_llm_call_in_executor_confirmed: bool = False
    no_secret_read_in_executor_confirmed: bool = False
    no_task_creation_in_executor_confirmed: bool = False
    no_publish_in_executor_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _approval_request(request: RealLlmFirstCallExecutorDisabledRequest) -> RealLlmFirstCallApprovalGateRequest:
    return RealLlmFirstCallApprovalGateRequest(
        provider_id=request.provider_id,
        operation=request.operation,
        prompt_id=request.prompt_id,
        output_kind=request.output_kind,
        input_ref=request.input_ref,
        timeout_seconds=request.timeout_seconds,
        retry_count=request.retry_count,
        concurrency_limit=request.concurrency_limit,
        target_model_alias=request.target_model_alias,
        payload=request.payload,
        reviewer=request.reviewer,
        approval_ref=request.approval_ref,
        explicit_request_review_opt_in=request.explicit_request_review_opt_in,
        client_boundary_confirmed=request.client_boundary_confirmed,
        prompt_scope_confirmed=request.prompt_scope_confirmed,
        schema_validation_confirmed=request.schema_validation_confirmed,
        audit_redaction_confirmed=request.audit_redaction_confirmed,
        human_review_policy_confirmed=request.human_review_policy_confirmed,
        no_request_send_confirmed=request.no_request_send_confirmed,
        no_network_call_confirmed=request.no_network_call_confirmed,
        no_real_llm_call_confirmed=request.no_real_llm_call_confirmed,
        explicit_first_call_approval_opt_in=request.explicit_first_call_approval_opt_in,
        request_review_package_confirmed=request.request_review_package_confirmed,
        approver_identity_confirmed=request.approver_identity_confirmed,
        approval_record_confirmed=request.approval_record_confirmed,
        secret_injection_runtime_confirmed=request.secret_injection_runtime_confirmed,
        network_egress_window_confirmed=request.network_egress_window_confirmed,
        cost_limit_confirmed=request.cost_limit_confirmed,
        model_alias_confirmed=request.model_alias_confirmed,
        timeout_retry_confirmed=request.timeout_retry_confirmed,
        schema_enforcement_confirmed=request.schema_enforcement_confirmed,
        audit_log_redaction_confirmed=request.audit_log_redaction_confirmed,
        rollback_plan_confirmed=request.rollback_plan_confirmed,
        post_call_validation_confirmed=request.post_call_validation_confirmed,
        no_send_in_gate_confirmed=request.no_send_in_gate_confirmed,
        no_task_creation_in_gate_confirmed=request.no_task_creation_in_gate_confirmed,
        no_publish_in_gate_confirmed=request.no_publish_in_gate_confirmed,
        trace_id=request.trace_id,
    )


def _base_context(
    request: RealLlmFirstCallExecutorDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    approval_descriptor = describe_real_llm_first_call_approval_gate(root=root)
    return {
        **approval_descriptor,
        "firstCallExecutorDisabledId": REAL_LLM_FIRST_CALL_EXECUTOR_DISABLED_ID,
        "upstreamGateId": "real_llm_first_call_approval_gate",
        "mode": "REAL_LLM_FIRST_CALL_EXECUTOR_DISABLED_ONLY",
        "executorMode": "DISABLED_EXECUTOR_MODEL_ONLY",
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
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "secretValueLogged": False,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "explicitDisabledExecutorOptIn": request.explicit_disabled_executor_opt_in,
        "firstCallApprovalGateConfirmed": request.first_call_approval_gate_confirmed,
        "clientBoundaryReadyConfirmed": request.client_boundary_ready_confirmed,
        "requestShapeConfirmed": request.request_shape_confirmed,
        "noExecutorDispatchConfirmed": request.no_executor_dispatch_confirmed,
        "noRequestSendInExecutorConfirmed": request.no_request_send_in_executor_confirmed,
        "noNetworkAccessInExecutorConfirmed": request.no_network_access_in_executor_confirmed,
        "noRealLlmCallInExecutorConfirmed": request.no_real_llm_call_in_executor_confirmed,
        "noSecretReadInExecutorConfirmed": request.no_secret_read_in_executor_confirmed,
        "noTaskCreationInExecutorConfirmed": request.no_task_creation_in_executor_confirmed,
        "noPublishInExecutorConfirmed": request.no_publish_in_executor_confirmed,
        "allowedOperations": [
            "client_boundary_confirmation_check",
            "first_call_approval_gate_evaluation",
            "disabled_executor_plan_generation",
        ],
        "blockedOperations": [
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "executor_dispatch",
            "request_send",
            "network_request",
            "real_llm_call",
            "generated_content_creation",
            "task_creation",
            "publish",
        ],
        "approvalGateReady": False,
        "disabledExecutorChecklistReady": False,
        "disabledFirstCallExecutorReady": False,
        "readyForMinimalRealCallPocReview": False,
        "readyForRealRequestSend": False,
        "executorPrepared": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "requestSendAttempted": False,
        "requestSent": False,
        "sdkImported": False,
        "clientCreated": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "realCallAuthorized": False,
        "traceId": request.trace_id,
    }


def describe_real_llm_first_call_executor_disabled(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmFirstCallExecutorDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresApprovalGateReady": True,
        "requiresExplicitDisabledExecutorOptIn": True,
        "requiresClientBoundaryReadyConfirmation": True,
        "requiresRequestShapeConfirmation": True,
        "requiresNoExecutorDispatchConfirmation": True,
        "requiresNoRequestSendConfirmation": True,
        "requiresNoNetworkAccessConfirmation": True,
        "requiresNoSecretReadConfirmation": True,
        "realCallAuthorizationPath": "future_minimal_real_call_poc_after_disabled_executor_review",
    }


def _validate_provider_scope(request: RealLlmFirstCallExecutorDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM first-call disabled executor currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed for the first-call disabled executor"}],
        )


def _executor_checklist(
    request: RealLlmFirstCallExecutorDisabledRequest,
    *,
    approval_gate_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "approval_gate_ready", "passed": approval_gate_ready, "required": True},
        {
            "id": "explicit_disabled_executor_opt_in",
            "passed": request.explicit_disabled_executor_opt_in,
            "required": True,
        },
        {
            "id": "first_call_approval_gate_confirmed",
            "passed": request.first_call_approval_gate_confirmed,
            "required": True,
        },
        {
            "id": "client_boundary_ready_confirmed",
            "passed": request.client_boundary_ready_confirmed,
            "required": True,
        },
        {"id": "request_shape_confirmed", "passed": request.request_shape_confirmed, "required": True},
        {
            "id": "no_executor_dispatch_confirmed",
            "passed": request.no_executor_dispatch_confirmed,
            "required": True,
        },
        {
            "id": "no_request_send_in_executor_confirmed",
            "passed": request.no_request_send_in_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_executor_confirmed",
            "passed": request.no_network_access_in_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_real_llm_call_in_executor_confirmed",
            "passed": request.no_real_llm_call_in_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_executor_confirmed",
            "passed": request.no_secret_read_in_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_executor_confirmed",
            "passed": request.no_task_creation_in_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_executor_confirmed",
            "passed": request.no_publish_in_executor_confirmed,
            "required": True,
        },
    ]


def _approval_summary(approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "firstCallApprovalGateId": approval["firstCallApprovalGateId"],
        "requestReviewPackageReady": approval["requestReviewPackageReady"],
        "firstCallApprovalGateReady": approval["firstCallApprovalGateReady"],
        "readyForDisabledFirstCallExecutor": approval["readyForDisabledFirstCallExecutor"],
        "readyForFirstRealCallApproval": approval["readyForFirstRealCallApproval"],
        "manualApprovalGranted": approval["manualApprovalGranted"],
        "requestSent": approval["requestSent"],
        "networkAccess": approval["networkAccess"],
        "realLlmCalled": approval["realLlmCalled"],
        "secretValueRead": approval["secretValueRead"],
        "generatedContentCreated": approval["generatedContentCreated"],
        "taskCreated": approval["taskCreated"],
    }


def _executor_plan(request: RealLlmFirstCallExecutorDisabledRequest) -> dict[str, Any]:
    return {
        "executorId": REAL_LLM_FIRST_CALL_EXECUTOR_DISABLED_ID,
        "materializedNow": False,
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "clientBoundaryRequired": True,
        "requestShapeRequired": True,
        "approvalGateRequired": True,
        "executorDispatchAllowedNow": False,
        "requestSendAllowedNow": False,
        "networkAllowedNow": False,
        "secretReadAllowedNow": False,
        "taskCreationAllowedNow": False,
        "publishAllowedNow": False,
        "nextStage": "minimal_real_call_poc_review",
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "executorDispatch", "reason": "disabled_executor_does_not_dispatch"},
            {"field": "requestSent", "reason": "disabled_executor_does_not_send_requests"},
            {"field": "networkAccess", "reason": "disabled_until_minimal_real_call_poc"},
            {"field": "secretValueRead", "reason": "disabled_executor_does_not_read_secret_values"},
            {"field": "realCallAuthorized", "reason": "requires_future_minimal_real_call_poc"},
            {"field": "taskCreated", "reason": "disabled_executor_must_not_create_ai_tasks"},
        ]
    )
    return reasons


def prepare_real_llm_first_call_executor_disabled(
    request: RealLlmFirstCallExecutorDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    approval = evaluate_real_llm_first_call_approval_gate(_approval_request(request), root=root)
    approval_gate_ready = approval.get("readyForDisabledFirstCallExecutor") is True
    checklist = _executor_checklist(request, approval_gate_ready=approval_gate_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestReviewPackageReady": approval["requestReviewPackageReady"],
        "requestShapeBuilt": approval["requestShapeBuilt"],
        "requestReviewPackageBuilt": approval["requestReviewPackageBuilt"],
        "readyForManualRequestReview": approval["readyForManualRequestReview"],
        "explicitRequestReviewOptIn": request.explicit_request_review_opt_in,
        "clientBoundaryConfirmed": request.client_boundary_confirmed,
        "promptScopeConfirmed": request.prompt_scope_confirmed,
        "schemaValidationConfirmed": request.schema_validation_confirmed,
        "auditRedactionConfirmed": request.audit_redaction_confirmed,
        "humanReviewPolicyConfirmed": request.human_review_policy_confirmed,
        "noRequestSendConfirmed": request.no_request_send_confirmed,
        "noNetworkCallConfirmed": request.no_network_call_confirmed,
        "noRealLlmCallConfirmed": request.no_real_llm_call_confirmed,
        "explicitFirstCallApprovalOptIn": request.explicit_first_call_approval_opt_in,
        "requestReviewPackageConfirmed": request.request_review_package_confirmed,
        "approverIdentityConfirmed": request.approver_identity_confirmed,
        "approvalRecordConfirmed": request.approval_record_confirmed,
        "secretInjectionRuntimeConfirmed": request.secret_injection_runtime_confirmed,
        "networkEgressWindowConfirmed": request.network_egress_window_confirmed,
        "costLimitConfirmed": request.cost_limit_confirmed,
        "modelAliasConfirmed": request.model_alias_confirmed,
        "timeoutRetryConfirmed": request.timeout_retry_confirmed,
        "schemaEnforcementConfirmed": request.schema_enforcement_confirmed,
        "auditLogRedactionConfirmed": request.audit_log_redaction_confirmed,
        "rollbackPlanConfirmed": request.rollback_plan_confirmed,
        "postCallValidationConfirmed": request.post_call_validation_confirmed,
        "noSendInGateConfirmed": request.no_send_in_gate_confirmed,
        "noTaskCreationInGateConfirmed": request.no_task_creation_in_gate_confirmed,
        "noPublishInGateConfirmed": request.no_publish_in_gate_confirmed,
        "firstCallApprovalGateReady": approval["firstCallApprovalGateReady"],
        "firstCallApprovalChecklistReady": approval["firstCallApprovalChecklistReady"],
        "readyForDisabledFirstCallExecutor": approval["readyForDisabledFirstCallExecutor"],
        "approvalGateReady": approval_gate_ready,
        "approvalGateSummary": _approval_summary(approval),
        "disabledExecutorChecklist": checklist,
        "disabledExecutorChecklistReady": checklist_passed,
        "disabledFirstCallExecutorReady": checklist_passed,
        "readyForMinimalRealCallPocReview": checklist_passed,
        "readyForRealRequestSend": False,
        "executorPlan": _executor_plan(request),
        "executorPrepared": checklist_passed,
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
        "realCallAuthorized": False,
        "blockedUntil": _blocked_until(checklist),
        "message": (
            "真实 LLM 首次调用禁用执行器已准备；当前不会派发执行器、发送请求、"
            "联网、读取密钥、真实调用、生成内容、创建任务或发布。"
        ),
    }


def build_real_llm_first_call_executor_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmFirstCallExecutorDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmFirstCallExecutorDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            approval = evaluate_real_llm_first_call_approval_gate(_approval_request(request), root=root)
        else:
            approval = None
    except ProviderError:
        approval = None
    if approval is not None:
        context["approvalGateReady"] = bool(approval.get("readyForDisabledFirstCallExecutor", False))
        context["approvalGateSummary"] = _approval_summary(approval)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
