"""Minimal real LLM call PoC implementation review.

This module turns the pre-send dry-run record into an implementation review
package for a future single real LLM request. It never sends a request, reads
secret values, accesses network, creates generated content, creates tasks, or
publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_pre_send_dry_run_record import (
    RealLlmPreSendDryRunRecordRequest,
    build_real_llm_pre_send_dry_run_record,
    describe_real_llm_pre_send_dry_run_record,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_MINIMAL_CALL_POC_REVIEW_ID = "real_llm_minimal_call_poc_review"


@dataclass(frozen=True)
class RealLlmMinimalCallPocReviewRequest(RealLlmPreSendDryRunRecordRequest):
    explicit_minimal_call_poc_review_opt_in: bool = False
    pre_send_dry_run_record_confirmed: bool = False
    single_request_scope_confirmed: bool = False
    lab_only_scope_confirmed: bool = False
    env_secret_source_confirmed: bool = False
    no_secret_logging_confirmed: bool = False
    network_egress_confirmed: bool = False
    cost_limit_enforced_confirmed: bool = False
    timeout_retry_limit_confirmed: bool = False
    response_schema_validation_confirmed_for_poc: bool = False
    waiting_review_task_policy_confirmed: bool = False
    failure_rollback_confirmed_for_poc: bool = False
    audit_event_plan_confirmed: bool = False
    no_auto_publish_confirmed: bool = False
    no_batch_call_confirmed: bool = False
    no_streaming_confirmed: bool = False
    no_exam_grading_ppt_scope_confirmed: bool = False
    no_real_request_send_in_review_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmMinimalCallPocReviewRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    pre_send_descriptor = describe_real_llm_pre_send_dry_run_record(root=root)
    return {
        **pre_send_descriptor,
        "minimalCallPocReviewId": REAL_LLM_MINIMAL_CALL_POC_REVIEW_ID,
        "upstreamGateId": "real_llm_pre_send_dry_run_record",
        "mode": "REAL_LLM_MINIMAL_CALL_POC_REVIEW_ONLY",
        "reviewMode": "MINIMAL_REAL_CALL_IMPLEMENTATION_REVIEW_ONLY",
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
        "explicitMinimalCallPocReviewOptIn": request.explicit_minimal_call_poc_review_opt_in,
        "preSendDryRunRecordConfirmed": request.pre_send_dry_run_record_confirmed,
        "singleRequestScopeConfirmed": request.single_request_scope_confirmed,
        "labOnlyScopeConfirmed": request.lab_only_scope_confirmed,
        "envSecretSourceConfirmed": request.env_secret_source_confirmed,
        "noSecretLoggingConfirmed": request.no_secret_logging_confirmed,
        "networkEgressConfirmed": request.network_egress_confirmed,
        "costLimitEnforcedConfirmed": request.cost_limit_enforced_confirmed,
        "timeoutRetryLimitConfirmed": request.timeout_retry_limit_confirmed,
        "responseSchemaValidationConfirmedForPoc": request.response_schema_validation_confirmed_for_poc,
        "waitingReviewTaskPolicyConfirmed": request.waiting_review_task_policy_confirmed,
        "failureRollbackConfirmedForPoc": request.failure_rollback_confirmed_for_poc,
        "auditEventPlanConfirmed": request.audit_event_plan_confirmed,
        "noAutoPublishConfirmed": request.no_auto_publish_confirmed,
        "noBatchCallConfirmed": request.no_batch_call_confirmed,
        "noStreamingConfirmed": request.no_streaming_confirmed,
        "noExamGradingPptScopeConfirmed": request.no_exam_grading_ppt_scope_confirmed,
        "noRealRequestSendInReviewConfirmed": request.no_real_request_send_in_review_confirmed,
        "allowedOperations": [
            "pre_send_dry_run_record_validation",
            "minimal_real_call_poc_review_package_generation",
            "future_single_lab_json_request_design",
        ],
        "blockedOperations": [
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "executor_dispatch",
            "dry_run_execution",
            "request_send",
            "network_request",
            "real_llm_call",
            "generated_content_creation",
            "task_creation",
            "publish",
            "batch_request",
            "streaming_request",
            "exam_generation",
            "grading_generation",
            "ppt_generation",
        ],
        "preSendDryRunRecordReady": False,
        "minimalCallPocChecklistReady": False,
        "minimalCallPocReviewReady": False,
        "readyForMinimalRealCallImplementation": False,
        "readyForRealRequestSend": False,
        "realCallAuthorized": False,
        "manualApprovalGranted": False,
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
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
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_llm_minimal_call_poc_review(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmMinimalCallPocReviewRequest()
    return {
        **_base_context(request, root=root),
        "requiresPreSendDryRunRecordReady": True,
        "requiresExplicitMinimalCallPocReviewOptIn": True,
        "requiresSingleRequestScopeConfirmation": True,
        "requiresLabOnlyScopeConfirmation": True,
        "requiresEnvSecretSourceConfirmation": True,
        "requiresNoSecretLoggingConfirmation": True,
        "requiresNetworkEgressConfirmation": True,
        "requiresCostLimitConfirmation": True,
        "requiresTimeoutRetryConfirmation": True,
        "requiresResponseSchemaValidationConfirmation": True,
        "requiresWaitingReviewTaskPolicyConfirmation": True,
        "requiresFailureRollbackConfirmation": True,
        "requiresAuditEventPlanConfirmation": True,
        "requiresNoAutoPublishConfirmation": True,
        "requiresNoBatchCallConfirmation": True,
        "requiresNoStreamingConfirmation": True,
        "requiresNoExamGradingPptScopeConfirmation": True,
        "requiresNoRealRequestSendInReviewConfirmation": True,
        "realCallAuthorizationPath": "future_explicit_minimal_real_call_send_executor_after_review",
    }


def _validate_provider_scope(request: RealLlmMinimalCallPocReviewRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM minimal call PoC review currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed for the minimal call PoC review"}],
        )


def _minimal_call_checklist(
    request: RealLlmMinimalCallPocReviewRequest,
    *,
    pre_send_record_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "pre_send_dry_run_record_ready", "passed": pre_send_record_ready, "required": True},
        {
            "id": "explicit_minimal_call_poc_review_opt_in",
            "passed": request.explicit_minimal_call_poc_review_opt_in,
            "required": True,
        },
        {
            "id": "pre_send_dry_run_record_confirmed",
            "passed": request.pre_send_dry_run_record_confirmed,
            "required": True,
        },
        {"id": "single_request_scope_confirmed", "passed": request.single_request_scope_confirmed, "required": True},
        {"id": "lab_only_scope_confirmed", "passed": request.lab_only_scope_confirmed, "required": True},
        {"id": "env_secret_source_confirmed", "passed": request.env_secret_source_confirmed, "required": True},
        {"id": "no_secret_logging_confirmed", "passed": request.no_secret_logging_confirmed, "required": True},
        {"id": "network_egress_confirmed", "passed": request.network_egress_confirmed, "required": True},
        {
            "id": "cost_limit_enforced_confirmed",
            "passed": request.cost_limit_enforced_confirmed,
            "required": True,
        },
        {"id": "timeout_retry_limit_confirmed", "passed": request.timeout_retry_limit_confirmed, "required": True},
        {
            "id": "response_schema_validation_confirmed_for_poc",
            "passed": request.response_schema_validation_confirmed_for_poc,
            "required": True,
        },
        {
            "id": "waiting_review_task_policy_confirmed",
            "passed": request.waiting_review_task_policy_confirmed,
            "required": True,
        },
        {
            "id": "failure_rollback_confirmed_for_poc",
            "passed": request.failure_rollback_confirmed_for_poc,
            "required": True,
        },
        {"id": "audit_event_plan_confirmed", "passed": request.audit_event_plan_confirmed, "required": True},
        {"id": "no_auto_publish_confirmed", "passed": request.no_auto_publish_confirmed, "required": True},
        {"id": "no_batch_call_confirmed", "passed": request.no_batch_call_confirmed, "required": True},
        {"id": "no_streaming_confirmed", "passed": request.no_streaming_confirmed, "required": True},
        {
            "id": "no_exam_grading_ppt_scope_confirmed",
            "passed": request.no_exam_grading_ppt_scope_confirmed,
            "required": True,
        },
        {
            "id": "no_real_request_send_in_review_confirmed",
            "passed": request.no_real_request_send_in_review_confirmed,
            "required": True,
        },
    ]


def _pre_send_summary(pre_send: dict[str, Any]) -> dict[str, Any]:
    return {
        "preSendDryRunRecordId": pre_send["preSendDryRunRecordId"],
        "disabledFirstCallExecutorReady": pre_send["disabledFirstCallExecutorReady"],
        "preSendDryRunRecordReady": pre_send["preSendDryRunRecordReady"],
        "readyForMinimalRealCallPoc": pre_send["readyForMinimalRealCallPoc"],
        "readyForRealRequestSend": pre_send["readyForRealRequestSend"],
        "dryRunExecuted": pre_send["dryRunExecuted"],
        "dryRunRecordWritten": pre_send["dryRunRecordWritten"],
        "requestSent": pre_send["requestSent"],
        "networkAccess": pre_send["networkAccess"],
        "realLlmCalled": pre_send["realLlmCalled"],
        "secretValueRead": pre_send["secretValueRead"],
        "generatedContentCreated": pre_send["generatedContentCreated"],
        "taskCreated": pre_send["taskCreated"],
    }


def _request_send_boundary(request: RealLlmMinimalCallPocReviewRequest) -> dict[str, Any]:
    return {
        "boundaryId": "minimal_real_llm_lab_json_request_boundary",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "secretEnv": SECRET_ENV,
        "singleRequestOnly": True,
        "labOnly": True,
        "batchAllowed": False,
        "streamingAllowed": False,
        "examGenerationAllowed": False,
        "gradingGenerationAllowed": False,
        "pptGenerationAllowed": False,
        "sendAllowedInThisReview": False,
        "futureSendRequiresSeparateExecutor": True,
    }


def _secret_policy() -> dict[str, Any]:
    return {
        "secretPolicyId": "minimal_real_llm_secret_policy",
        "secretEnv": SECRET_ENV,
        "source": "environment_only",
        "readAllowedInThisReview": False,
        "returnSecretValue": False,
        "logSecretValue": False,
        "persistSecretValue": False,
        "frontendExposureAllowed": False,
    }


def _response_validation_policy() -> dict[str, Any]:
    return {
        "responseValidationPolicyId": "minimal_real_llm_response_validation_policy",
        "schemaRef": "templates/lab/lab.schema.json",
        "outputKind": "Lab",
        "mustValidateBeforeTaskCreation": True,
        "invalidResponseCreatesTask": False,
        "validResponseDefaultStatus": "WAITING_REVIEW",
        "publishAllowedAfterValidation": False,
    }


def _failure_rollback_policy() -> dict[str, Any]:
    return {
        "rollbackPolicyId": "minimal_real_llm_failure_rollback_policy",
        "remoteRollbackRequired": False,
        "persistentMutationBeforeValidation": False,
        "taskCreationOnFailure": False,
        "publishOnFailure": False,
        "safeFailureCode": "REAL_LLM_MINIMAL_CALL_FAILED",
        "safeFailureLeavesGeneratedContent": False,
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "requestSent", "reason": "review_package_does_not_send_requests"},
            {"field": "networkAccess", "reason": "review_package_does_not_access_network"},
            {"field": "secretValueRead", "reason": "review_package_does_not_read_secret_values"},
            {"field": "realCallAuthorized", "reason": "requires_future_explicit_send_executor"},
            {"field": "taskCreated", "reason": "review_package_must_not_create_ai_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def build_real_llm_minimal_call_poc_review(
    request: RealLlmMinimalCallPocReviewRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    pre_send = build_real_llm_pre_send_dry_run_record(request, root=root)
    pre_send_record_ready = pre_send.get("preSendDryRunRecordReady") is True
    checklist = _minimal_call_checklist(request, pre_send_record_ready=pre_send_record_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestReviewPackageReady": pre_send["requestReviewPackageReady"],
        "requestShapeBuilt": pre_send["requestShapeBuilt"],
        "requestReviewPackageBuilt": pre_send["requestReviewPackageBuilt"],
        "readyForManualRequestReview": pre_send["readyForManualRequestReview"],
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
        "approvalGateReady": pre_send["approvalGateReady"],
        "firstCallApprovalGateReady": pre_send["firstCallApprovalGateReady"],
        "firstCallApprovalChecklistReady": pre_send["firstCallApprovalChecklistReady"],
        "readyForDisabledFirstCallExecutor": pre_send["readyForDisabledFirstCallExecutor"],
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
        "disabledExecutorChecklistReady": pre_send["disabledExecutorChecklistReady"],
        "disabledFirstCallExecutorReady": pre_send["disabledFirstCallExecutorReady"],
        "readyForMinimalRealCallPocReview": pre_send["readyForMinimalRealCallPocReview"],
        "executorPrepared": pre_send["executorPrepared"],
        "explicitPreSendDryRunRecordOptIn": request.explicit_pre_send_dry_run_record_opt_in,
        "disabledExecutorConfirmed": request.disabled_executor_confirmed,
        "approvalGateConfirmed": request.approval_gate_confirmed,
        "logRedactionConfirmed": request.log_redaction_confirmed,
        "failureRollbackConfirmed": request.failure_rollback_confirmed,
        "responseSchemaValidationConfirmed": request.response_schema_validation_confirmed,
        "postCallReviewConfirmed": request.post_call_review_confirmed,
        "noRequestSendInDryRunConfirmed": request.no_request_send_in_dry_run_confirmed,
        "noNetworkAccessInDryRunConfirmed": request.no_network_access_in_dry_run_confirmed,
        "noSecretReadInDryRunConfirmed": request.no_secret_read_in_dry_run_confirmed,
        "noTaskCreationInDryRunConfirmed": request.no_task_creation_in_dry_run_confirmed,
        "noPublishInDryRunConfirmed": request.no_publish_in_dry_run_confirmed,
        "preSendDryRunChecklistReady": pre_send["preSendDryRunChecklistReady"],
        "preSendDryRunRecordReady": pre_send_record_ready,
        "readyForMinimalRealCallPoc": pre_send["readyForMinimalRealCallPoc"],
        "dryRunRecordBuilt": pre_send["dryRunRecordBuilt"],
        "preSendSummary": _pre_send_summary(pre_send),
        "minimalCallPocChecklist": checklist,
        "minimalCallPocChecklistReady": checklist_passed,
        "minimalCallPocReviewReady": checklist_passed,
        "readyForMinimalRealCallImplementation": checklist_passed,
        "readyForRealRequestSend": False,
        "realCallAuthorized": False,
        "manualApprovalGranted": False,
        "requestSendBoundary": _request_send_boundary(request),
        "secretPolicy": _secret_policy(),
        "responseValidationPolicy": _response_validation_policy(),
        "failureRollbackPolicy": _failure_rollback_policy(),
        "auditEventPlan": {
            "auditEventPlanId": "minimal_real_llm_call_poc_audit_event_plan",
            "recordProvider": True,
            "recordModelAlias": True,
            "recordPromptId": True,
            "recordSchemaValidation": True,
            "recordTokenUsageIfReturned": True,
            "recordSecretValue": False,
            "recordRawResponseBeforeRedaction": False,
        },
        "implementationReviewPackage": {
            "packageId": REAL_LLM_MINIMAL_CALL_POC_REVIEW_ID,
            "built": checklist_passed,
            "sendImplementationCreated": False,
            "sendExecutorCreated": False,
            "requestSendAllowedNow": False,
            "networkAllowedNow": False,
            "secretReadAllowedNow": False,
            "taskCreationAllowedNow": False,
            "publishAllowedNow": False,
            "nextStage": "minimal_real_call_send_executor_explicit_implementation",
        },
        "sendImplementationCreated": False,
        "sendExecutorCreated": False,
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
        "autoPublishAllowed": False,
        "realPublish": False,
        "blockedUntil": _blocked_until(checklist),
        "message": (
            "真实 LLM 最小调用 PoC 实现评审包已生成；当前不会发送请求、联网、"
            "读取密钥、真实调用、生成内容、创建任务或发布。"
        ),
    }


def build_real_llm_minimal_call_poc_review_error_context(
    exc: ProviderError,
    *,
    request: RealLlmMinimalCallPocReviewRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmMinimalCallPocReviewRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            pre_send = build_real_llm_pre_send_dry_run_record(request, root=root)
        else:
            pre_send = None
    except ProviderError:
        pre_send = None
    if pre_send is not None:
        context["preSendDryRunRecordReady"] = bool(pre_send.get("preSendDryRunRecordReady", False))
        context["preSendSummary"] = _pre_send_summary(pre_send)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
