"""Real LLM first-call final approval gate.

This module evaluates a local final-approval checklist for the first future
real LLM dry-run request. It can mark the approval package ready for manual
review, but it must not send requests, import SDKs, construct clients, read
secret values, create generated content, create tasks, or publish artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_request_review_package import (
    RealLlmRequestReviewPackageRequest,
    build_real_llm_request_review_package,
    describe_real_llm_request_review_package,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_FIRST_CALL_APPROVAL_GATE_ID = "real_llm_first_call_approval_gate"


@dataclass(frozen=True)
class RealLlmFirstCallApprovalGateRequest:
    provider_id: str = SUPPORTED_PROVIDER
    operation: str = "generateJson"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    timeout_seconds: int = 30
    retry_count: int = 1
    concurrency_limit: int = 1
    target_model_alias: str = DEFAULT_MODEL_ALIAS
    payload: Mapping[str, Any] | None = None
    reviewer: str | None = None
    approval_ref: str | None = None
    explicit_request_review_opt_in: bool = False
    client_boundary_confirmed: bool = False
    prompt_scope_confirmed: bool = False
    schema_validation_confirmed: bool = False
    audit_redaction_confirmed: bool = False
    human_review_policy_confirmed: bool = False
    no_request_send_confirmed: bool = False
    no_network_call_confirmed: bool = False
    no_real_llm_call_confirmed: bool = False
    explicit_first_call_approval_opt_in: bool = False
    request_review_package_confirmed: bool = False
    approver_identity_confirmed: bool = False
    approval_record_confirmed: bool = False
    secret_injection_runtime_confirmed: bool = False
    network_egress_window_confirmed: bool = False
    cost_limit_confirmed: bool = False
    model_alias_confirmed: bool = False
    timeout_retry_confirmed: bool = False
    schema_enforcement_confirmed: bool = False
    audit_log_redaction_confirmed: bool = False
    rollback_plan_confirmed: bool = False
    post_call_validation_confirmed: bool = False
    no_send_in_gate_confirmed: bool = False
    no_task_creation_in_gate_confirmed: bool = False
    no_publish_in_gate_confirmed: bool = False
    trace_id: str | None = None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _request_review_request(request: RealLlmFirstCallApprovalGateRequest) -> RealLlmRequestReviewPackageRequest:
    return RealLlmRequestReviewPackageRequest(
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
        explicit_request_review_opt_in=request.explicit_request_review_opt_in,
        client_boundary_confirmed=request.client_boundary_confirmed,
        prompt_scope_confirmed=request.prompt_scope_confirmed,
        schema_validation_confirmed=request.schema_validation_confirmed,
        audit_redaction_confirmed=request.audit_redaction_confirmed,
        human_review_policy_confirmed=request.human_review_policy_confirmed,
        no_request_send_confirmed=request.no_request_send_confirmed,
        no_network_call_confirmed=request.no_network_call_confirmed,
        no_real_llm_call_confirmed=request.no_real_llm_call_confirmed,
        reviewer=request.reviewer,
        approval_ref=request.approval_ref,
        trace_id=request.trace_id,
    )


def _base_context(
    request: RealLlmFirstCallApprovalGateRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    request_review_descriptor = describe_real_llm_request_review_package(root=root)
    return {
        **request_review_descriptor,
        "firstCallApprovalGateId": REAL_LLM_FIRST_CALL_APPROVAL_GATE_ID,
        "upstreamGateId": "real_llm_request_review_package",
        "mode": "REAL_LLM_FIRST_CALL_APPROVAL_GATE_ONLY",
        "approvalGateOnly": True,
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
        "allowedOperations": [
            "request_review_package_evaluation",
            "approval_checklist_generation",
            "manual_approval_package_model",
        ],
        "blockedOperations": [
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "request_send",
            "network_request",
            "real_llm_call",
            "generated_content_creation",
            "task_creation",
            "publish",
        ],
        "requestReviewPackageReady": False,
        "firstCallApprovalChecklistReady": False,
        "firstCallApprovalGateReady": False,
        "readyForDisabledFirstCallExecutor": False,
        "readyForFirstRealCallApproval": False,
        "manualApprovalPackageMaterialized": False,
        "manualApprovalGranted": False,
        "sdkImported": False,
        "clientCreated": False,
        "requestSent": False,
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


def describe_real_llm_first_call_approval_gate(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmFirstCallApprovalGateRequest()
    return {
        **_base_context(request, root=root),
        "requiresRequestReviewPackageReady": True,
        "requiresExplicitFirstCallApprovalOptIn": True,
        "requiresApproverIdentity": True,
        "requiresApprovalRecord": True,
        "requiresSecretInjectionRuntimeReview": True,
        "requiresNetworkEgressWindowReview": True,
        "requiresCostLimitReview": True,
        "requiresRollbackPlan": True,
        "realCallAuthorizationPath": "future_disabled_first_call_executor_after_manual_review",
    }


def _validate_provider_scope(request: RealLlmFirstCallApprovalGateRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM first-call approval gate currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed for the first-call approval gate"}],
        )


def _approval_checklist(
    request: RealLlmFirstCallApprovalGateRequest,
    *,
    request_review_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "request_review_package_ready", "passed": request_review_ready, "required": True},
        {
            "id": "explicit_first_call_approval_opt_in",
            "passed": request.explicit_first_call_approval_opt_in,
            "required": True,
        },
        {
            "id": "request_review_package_confirmed",
            "passed": request.request_review_package_confirmed,
            "required": True,
        },
        {"id": "approver_identity_confirmed", "passed": request.approver_identity_confirmed, "required": True},
        {"id": "approval_record_confirmed", "passed": request.approval_record_confirmed, "required": True},
        {
            "id": "secret_injection_runtime_confirmed",
            "passed": request.secret_injection_runtime_confirmed,
            "required": True,
        },
        {
            "id": "network_egress_window_confirmed",
            "passed": request.network_egress_window_confirmed,
            "required": True,
        },
        {"id": "cost_limit_confirmed", "passed": request.cost_limit_confirmed, "required": True},
        {"id": "model_alias_confirmed", "passed": request.model_alias_confirmed, "required": True},
        {"id": "timeout_retry_confirmed", "passed": request.timeout_retry_confirmed, "required": True},
        {
            "id": "schema_enforcement_confirmed",
            "passed": request.schema_enforcement_confirmed,
            "required": True,
        },
        {
            "id": "audit_log_redaction_confirmed",
            "passed": request.audit_log_redaction_confirmed,
            "required": True,
        },
        {"id": "rollback_plan_confirmed", "passed": request.rollback_plan_confirmed, "required": True},
        {
            "id": "post_call_validation_confirmed",
            "passed": request.post_call_validation_confirmed,
            "required": True,
        },
        {"id": "no_send_in_gate_confirmed", "passed": request.no_send_in_gate_confirmed, "required": True},
        {
            "id": "no_task_creation_in_gate_confirmed",
            "passed": request.no_task_creation_in_gate_confirmed,
            "required": True,
        },
        {"id": "no_publish_in_gate_confirmed", "passed": request.no_publish_in_gate_confirmed, "required": True},
    ]


def _request_review_summary(request_review: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestReviewPackageId": request_review["requestReviewPackageId"],
        "requestShapeBuilt": request_review["requestShapeBuilt"],
        "requestReviewPackageReady": request_review["requestReviewPackageReady"],
        "readyForManualRequestReview": request_review["readyForManualRequestReview"],
        "requestSent": request_review["requestSent"],
        "networkAccess": request_review["networkAccess"],
        "realLlmCalled": request_review["realLlmCalled"],
        "secretValueRead": request_review["secretValueRead"],
        "generatedContentCreated": request_review["generatedContentCreated"],
        "taskCreated": request_review["taskCreated"],
    }


def _approval_model(request: RealLlmFirstCallApprovalGateRequest) -> dict[str, Any]:
    return {
        "approvalGateId": REAL_LLM_FIRST_CALL_APPROVAL_GATE_ID,
        "materializedNow": False,
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "executorDispatchAllowedNow": False,
        "requestSendAllowedNow": False,
        "requiredEvidence": [
            {"id": "request_review_package", "materializedNow": False},
            {"id": "approver_identity", "materializedNow": False},
            {"id": "secret_injection_runtime", "materializedNow": False},
            {"id": "network_egress_window", "materializedNow": False},
            {"id": "cost_limit", "materializedNow": False},
            {"id": "rollback_plan", "materializedNow": False},
            {"id": "post_call_validation", "materializedNow": False},
        ],
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "manualApprovalGranted", "reason": "approval_gate_does_not_grant_send_authorization"},
            {"field": "requestSent", "reason": "disabled_in_first_call_approval_gate"},
            {"field": "networkAccess", "reason": "disabled_until_first_call_executor"},
            {"field": "realCallAuthorized", "reason": "requires_future_disabled_executor_review"},
            {"field": "taskCreated", "reason": "approval_gate_must_not_create_ai_tasks"},
        ]
    )
    return reasons


def evaluate_real_llm_first_call_approval_gate(
    request: RealLlmFirstCallApprovalGateRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    request_review = build_real_llm_request_review_package(_request_review_request(request), root=root)
    request_review_ready = request_review.get("requestReviewPackageReady") is True
    checklist = _approval_checklist(request, request_review_ready=request_review_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestReviewPackageReady": request_review_ready,
        "requestShapeBuilt": request_review["requestShapeBuilt"],
        "requestReviewPackageBuilt": request_review["requestReviewPackageBuilt"],
        "readyForManualRequestReview": request_review["readyForManualRequestReview"],
        "requestReviewPackageSummary": _request_review_summary(request_review),
        "firstCallApprovalChecklist": checklist,
        "firstCallApprovalChecklistReady": checklist_passed,
        "firstCallApprovalGateReady": checklist_passed,
        "readyForDisabledFirstCallExecutor": checklist_passed,
        "readyForFirstRealCallApproval": False,
        "manualApprovalPackage": _approval_model(request),
        "manualApprovalPackageMaterialized": False,
        "manualApprovalGranted": False,
        "sdkImported": False,
        "clientCreated": False,
        "requestSent": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "realCallAuthorized": False,
        "blockedUntil": _blocked_until(checklist),
        "message": (
            "真实 LLM 首次调用最终批准门禁已评估；当前只生成批准门禁模型，"
            "不会发送请求、联网、真实调用、读取密钥、生成内容、创建任务或发布。"
        ),
    }


def build_real_llm_first_call_approval_gate_error_context(
    exc: ProviderError,
    *,
    request: RealLlmFirstCallApprovalGateRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmFirstCallApprovalGateRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            request_review = build_real_llm_request_review_package(_request_review_request(request), root=root)
        else:
            request_review = None
    except ProviderError:
        request_review = None
    if request_review is not None:
        context["requestReviewPackageReady"] = bool(request_review.get("requestReviewPackageReady", False))
        context["requestReviewPackageSummary"] = _request_review_summary(request_review)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
