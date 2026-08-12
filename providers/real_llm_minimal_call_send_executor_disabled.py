"""Disabled send executor model for the minimal real LLM call.

This module turns the minimal-call PoC review package into a disabled model of
the future request sender. It never materializes a send executor, dispatches an
executor, sends a request, reads secret values, accesses network, creates
generated content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_minimal_call_poc_review import (
    RealLlmMinimalCallPocReviewRequest,
    build_real_llm_minimal_call_poc_review,
    describe_real_llm_minimal_call_poc_review,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_MINIMAL_CALL_SEND_EXECUTOR_DISABLED_ID = "real_llm_minimal_call_send_executor_disabled"


@dataclass(frozen=True)
class RealLlmMinimalCallSendExecutorDisabledRequest(RealLlmMinimalCallPocReviewRequest):
    explicit_send_executor_disabled_opt_in: bool = False
    minimal_call_poc_review_confirmed: bool = False
    send_executor_boundary_confirmed: bool = False
    final_manual_authorization_record_confirmed: bool = False
    secret_runtime_read_boundary_confirmed: bool = False
    network_call_boundary_confirmed: bool = False
    sdk_client_boundary_confirmed: bool = False
    response_validation_boundary_confirmed: bool = False
    waiting_review_task_creation_boundary_confirmed: bool = False
    audit_logging_boundary_confirmed: bool = False
    rollback_boundary_confirmed: bool = False
    no_executor_dispatch_confirmed_for_send: bool = False
    no_request_send_in_disabled_executor_confirmed: bool = False
    no_secret_read_in_disabled_executor_confirmed: bool = False
    no_network_access_in_disabled_executor_confirmed: bool = False
    no_real_llm_call_in_disabled_executor_confirmed: bool = False
    no_task_creation_in_disabled_executor_confirmed: bool = False
    no_publish_in_disabled_executor_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmMinimalCallSendExecutorDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    review_descriptor = describe_real_llm_minimal_call_poc_review(root=root)
    return {
        **review_descriptor,
        "minimalCallSendExecutorDisabledId": REAL_LLM_MINIMAL_CALL_SEND_EXECUTOR_DISABLED_ID,
        "upstreamGateId": "real_llm_minimal_call_poc_review",
        "mode": "REAL_LLM_MINIMAL_CALL_SEND_EXECUTOR_DISABLED_ONLY",
        "executorMode": "DISABLED_MINIMAL_REAL_CALL_SEND_EXECUTOR_MODEL_ONLY",
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
        "explicitSendExecutorDisabledOptIn": request.explicit_send_executor_disabled_opt_in,
        "minimalCallPocReviewConfirmed": request.minimal_call_poc_review_confirmed,
        "sendExecutorBoundaryConfirmed": request.send_executor_boundary_confirmed,
        "finalManualAuthorizationRecordConfirmed": request.final_manual_authorization_record_confirmed,
        "secretRuntimeReadBoundaryConfirmed": request.secret_runtime_read_boundary_confirmed,
        "networkCallBoundaryConfirmed": request.network_call_boundary_confirmed,
        "sdkClientBoundaryConfirmed": request.sdk_client_boundary_confirmed,
        "responseValidationBoundaryConfirmed": request.response_validation_boundary_confirmed,
        "waitingReviewTaskCreationBoundaryConfirmed": request.waiting_review_task_creation_boundary_confirmed,
        "auditLoggingBoundaryConfirmed": request.audit_logging_boundary_confirmed,
        "rollbackBoundaryConfirmed": request.rollback_boundary_confirmed,
        "noExecutorDispatchConfirmedForSend": request.no_executor_dispatch_confirmed_for_send,
        "noRequestSendInDisabledExecutorConfirmed": request.no_request_send_in_disabled_executor_confirmed,
        "noSecretReadInDisabledExecutorConfirmed": request.no_secret_read_in_disabled_executor_confirmed,
        "noNetworkAccessInDisabledExecutorConfirmed": request.no_network_access_in_disabled_executor_confirmed,
        "noRealLlmCallInDisabledExecutorConfirmed": request.no_real_llm_call_in_disabled_executor_confirmed,
        "noTaskCreationInDisabledExecutorConfirmed": request.no_task_creation_in_disabled_executor_confirmed,
        "noPublishInDisabledExecutorConfirmed": request.no_publish_in_disabled_executor_confirmed,
        "allowedOperations": [
            "minimal_call_poc_review_validation",
            "disabled_send_executor_plan_generation",
            "future_real_request_send_executor_design",
        ],
        "blockedOperations": [
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "send_executor_materialization",
            "send_executor_persistence",
            "send_executor_dispatch",
            "request_send",
            "network_request",
            "real_llm_call",
            "response_persistence",
            "generated_content_creation",
            "task_creation",
            "publish",
            "batch_request",
            "streaming_request",
        ],
        "minimalCallPocReviewReady": False,
        "sendExecutorChecklistReady": False,
        "minimalCallSendExecutorDisabledReady": False,
        "readyForExplicitRealRequestSendAuthorization": False,
        "readyForRealRequestSend": False,
        "sendExecutorPlanBuilt": False,
        "disabledSendExecutorModelBuilt": False,
        "sendExecutorPrepared": False,
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


def describe_real_llm_minimal_call_send_executor_disabled(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmMinimalCallSendExecutorDisabledRequest()
    return {
        **_base_context(request, root=root),
        "requiresMinimalCallPocReviewReady": True,
        "requiresExplicitSendExecutorDisabledOptIn": True,
        "requiresSendExecutorBoundaryConfirmation": True,
        "requiresFinalManualAuthorizationRecordConfirmation": True,
        "requiresSecretRuntimeReadBoundaryConfirmation": True,
        "requiresNetworkCallBoundaryConfirmation": True,
        "requiresSdkClientBoundaryConfirmation": True,
        "requiresResponseValidationBoundaryConfirmation": True,
        "requiresWaitingReviewTaskCreationBoundaryConfirmation": True,
        "requiresAuditLoggingBoundaryConfirmation": True,
        "requiresRollbackBoundaryConfirmation": True,
        "requiresNoExecutorDispatchForSendConfirmation": True,
        "requiresNoRequestSendInDisabledExecutorConfirmation": True,
        "requiresNoSecretReadInDisabledExecutorConfirmation": True,
        "requiresNoNetworkAccessInDisabledExecutorConfirmation": True,
        "requiresNoRealLlmCallInDisabledExecutorConfirmation": True,
        "requiresNoTaskCreationInDisabledExecutorConfirmation": True,
        "requiresNoPublishInDisabledExecutorConfirmation": True,
        "realCallAuthorizationPath": "future_explicit_real_request_send_authorization_package",
    }


def _validate_provider_scope(request: RealLlmMinimalCallSendExecutorDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM minimal call disabled send executor currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed for the disabled send executor model"}],
        )


def _send_executor_checklist(
    request: RealLlmMinimalCallSendExecutorDisabledRequest,
    *,
    minimal_call_poc_review_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "minimal_call_poc_review_ready", "passed": minimal_call_poc_review_ready, "required": True},
        {
            "id": "explicit_send_executor_disabled_opt_in",
            "passed": request.explicit_send_executor_disabled_opt_in,
            "required": True,
        },
        {
            "id": "minimal_call_poc_review_confirmed",
            "passed": request.minimal_call_poc_review_confirmed,
            "required": True,
        },
        {
            "id": "send_executor_boundary_confirmed",
            "passed": request.send_executor_boundary_confirmed,
            "required": True,
        },
        {
            "id": "final_manual_authorization_record_confirmed",
            "passed": request.final_manual_authorization_record_confirmed,
            "required": True,
        },
        {
            "id": "secret_runtime_read_boundary_confirmed",
            "passed": request.secret_runtime_read_boundary_confirmed,
            "required": True,
        },
        {
            "id": "network_call_boundary_confirmed",
            "passed": request.network_call_boundary_confirmed,
            "required": True,
        },
        {
            "id": "sdk_client_boundary_confirmed",
            "passed": request.sdk_client_boundary_confirmed,
            "required": True,
        },
        {
            "id": "response_validation_boundary_confirmed",
            "passed": request.response_validation_boundary_confirmed,
            "required": True,
        },
        {
            "id": "waiting_review_task_creation_boundary_confirmed",
            "passed": request.waiting_review_task_creation_boundary_confirmed,
            "required": True,
        },
        {
            "id": "audit_logging_boundary_confirmed",
            "passed": request.audit_logging_boundary_confirmed,
            "required": True,
        },
        {"id": "rollback_boundary_confirmed", "passed": request.rollback_boundary_confirmed, "required": True},
        {
            "id": "no_executor_dispatch_confirmed_for_send",
            "passed": request.no_executor_dispatch_confirmed_for_send,
            "required": True,
        },
        {
            "id": "no_request_send_in_disabled_executor_confirmed",
            "passed": request.no_request_send_in_disabled_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_disabled_executor_confirmed",
            "passed": request.no_secret_read_in_disabled_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_disabled_executor_confirmed",
            "passed": request.no_network_access_in_disabled_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_real_llm_call_in_disabled_executor_confirmed",
            "passed": request.no_real_llm_call_in_disabled_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_disabled_executor_confirmed",
            "passed": request.no_task_creation_in_disabled_executor_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_disabled_executor_confirmed",
            "passed": request.no_publish_in_disabled_executor_confirmed,
            "required": True,
        },
    ]


def _minimal_call_review_summary(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "minimalCallPocReviewId": review["minimalCallPocReviewId"],
        "preSendDryRunRecordReady": review["preSendDryRunRecordReady"],
        "minimalCallPocReviewReady": review["minimalCallPocReviewReady"],
        "readyForMinimalRealCallImplementation": review["readyForMinimalRealCallImplementation"],
        "readyForRealRequestSend": review["readyForRealRequestSend"],
        "requestSent": review["requestSent"],
        "networkAccess": review["networkAccess"],
        "realLlmCalled": review["realLlmCalled"],
        "secretValueRead": review["secretValueRead"],
        "generatedContentCreated": review["generatedContentCreated"],
        "taskCreated": review["taskCreated"],
    }


def _send_executor_plan(request: RealLlmMinimalCallSendExecutorDisabledRequest) -> dict[str, Any]:
    return {
        "executorId": REAL_LLM_MINIMAL_CALL_SEND_EXECUTOR_DISABLED_ID,
        "mode": "DISABLED_MINIMAL_REAL_CALL_SEND_EXECUTOR_MODEL_ONLY",
        "materializedNow": False,
        "persistedNow": False,
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "futureEntryPoint": "providers.real_llm_minimal_call_send_executor.run_once",
        "futureSecretReadPoint": f"{SECRET_ENV} at runtime only",
        "futureNetworkCallPoint": "provider SDK response generation API",
        "futureResponseValidation": "validate response as Lab DSL before task creation",
        "futureGeneratedStatus": "WAITING_REVIEW",
        "futureAuditEvent": "record provider, prompt, model alias, validation outcome, and token usage without secrets",
        "dispatchAllowedNow": False,
        "requestSendAllowedNow": False,
        "networkAllowedNow": False,
        "secretReadAllowedNow": False,
        "taskCreationAllowedNow": False,
        "publishAllowedNow": False,
        "nextStage": "explicit_real_request_send_authorization_package",
    }


def _authorization_boundary(request: RealLlmMinimalCallSendExecutorDisabledRequest) -> dict[str, Any]:
    return {
        "authorizationBoundaryId": "minimal_real_llm_request_send_authorization_boundary",
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "finalManualAuthorizationRecordConfirmed": request.final_manual_authorization_record_confirmed,
        "manualApprovalGranted": False,
        "realCallAuthorized": False,
        "sendAllowedInThisStep": False,
        "futureExplicitAuthorizationRequired": True,
        "futureAuthorizationArtifactRequired": True,
        "futureAuthorizationMustNameProvider": True,
        "futureAuthorizationMustNamePrompt": True,
        "futureAuthorizationMustNameInputRef": True,
    }


def _secret_boundary() -> dict[str, Any]:
    return {
        "secretBoundaryId": "minimal_real_llm_send_secret_boundary",
        "secretEnv": SECRET_ENV,
        "source": "environment_only",
        "presenceCheckAllowedNow": False,
        "readAllowedNow": False,
        "returnSecretValue": False,
        "logSecretValue": False,
        "persistSecretValue": False,
        "frontendExposureAllowed": False,
    }


def _network_boundary() -> dict[str, Any]:
    return {
        "networkBoundaryId": "minimal_real_llm_send_network_boundary",
        "networkAllowedNow": False,
        "egressWindowRequiredInFuture": True,
        "singleRequestOnlyInFuture": True,
        "batchAllowed": False,
        "streamingAllowed": False,
    }


def _response_handling_boundary() -> dict[str, Any]:
    return {
        "responseHandlingBoundaryId": "minimal_real_llm_send_response_handling_boundary",
        "schemaRef": "templates/lab/lab.schema.json",
        "outputKind": "Lab",
        "validateBeforePersistence": True,
        "persistRawResponseAllowedNow": False,
        "generatedContentCreatedNow": False,
        "taskCreationAllowedNow": False,
        "validResponseDefaultStatus": "WAITING_REVIEW",
        "publishAllowedAfterValidation": False,
    }


def _audit_boundary() -> dict[str, Any]:
    return {
        "auditBoundaryId": "minimal_real_llm_send_audit_boundary",
        "recordProvider": True,
        "recordModelAlias": True,
        "recordPromptId": True,
        "recordInputRef": True,
        "recordSchemaValidation": True,
        "recordTokenUsageIfReturned": True,
        "recordSecretValue": False,
        "recordRawResponseBeforeRedaction": False,
    }


def _rollback_boundary() -> dict[str, Any]:
    return {
        "rollbackBoundaryId": "minimal_real_llm_send_rollback_boundary",
        "remoteRollbackRequired": False,
        "persistentMutationBeforeValidation": False,
        "taskCreationOnFailure": False,
        "publishOnFailure": False,
        "safeFailureCode": "REAL_LLM_MINIMAL_SEND_EXECUTOR_DISABLED",
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
            {"field": "sendExecutorMaterialized", "reason": "disabled_send_executor_model_only"},
            {"field": "sendExecutorDispatch", "reason": "disabled_send_executor_does_not_dispatch"},
            {"field": "requestSent", "reason": "disabled_send_executor_does_not_send_requests"},
            {"field": "networkAccess", "reason": "disabled_send_executor_does_not_access_network"},
            {"field": "secretValueRead", "reason": "disabled_send_executor_does_not_read_secret_values"},
            {"field": "realCallAuthorized", "reason": "requires_future_explicit_send_authorization"},
            {"field": "taskCreated", "reason": "disabled_send_executor_must_not_create_ai_tasks"},
            {"field": "autoPublishAllowed", "reason": "ai_generated_content_requires_review"},
        ]
    )
    return reasons


def prepare_real_llm_minimal_call_send_executor_disabled(
    request: RealLlmMinimalCallSendExecutorDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    review = build_real_llm_minimal_call_poc_review(request, root=root)
    minimal_call_poc_review_ready = review.get("minimalCallPocReviewReady") is True
    checklist = _send_executor_checklist(request, minimal_call_poc_review_ready=minimal_call_poc_review_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestReviewPackageReady": review["requestReviewPackageReady"],
        "requestShapeBuilt": review["requestShapeBuilt"],
        "requestReviewPackageBuilt": review["requestReviewPackageBuilt"],
        "readyForManualRequestReview": review["readyForManualRequestReview"],
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
        "approvalGateReady": review["approvalGateReady"],
        "firstCallApprovalGateReady": review["firstCallApprovalGateReady"],
        "firstCallApprovalChecklistReady": review["firstCallApprovalChecklistReady"],
        "readyForDisabledFirstCallExecutor": review["readyForDisabledFirstCallExecutor"],
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
        "disabledExecutorChecklistReady": review["disabledExecutorChecklistReady"],
        "disabledFirstCallExecutorReady": review["disabledFirstCallExecutorReady"],
        "readyForMinimalRealCallPocReview": review["readyForMinimalRealCallPocReview"],
        "executorPrepared": review["executorPrepared"],
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
        "preSendDryRunChecklistReady": review["preSendDryRunChecklistReady"],
        "preSendDryRunRecordReady": review["preSendDryRunRecordReady"],
        "readyForMinimalRealCallPoc": review["readyForMinimalRealCallPoc"],
        "dryRunRecordBuilt": review["dryRunRecordBuilt"],
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
        "minimalCallPocChecklistReady": review["minimalCallPocChecklistReady"],
        "minimalCallPocReviewReady": minimal_call_poc_review_ready,
        "readyForMinimalRealCallImplementation": review["readyForMinimalRealCallImplementation"],
        "minimalCallPocReviewSummary": _minimal_call_review_summary(review),
        "sendExecutorChecklist": checklist,
        "sendExecutorChecklistReady": checklist_passed,
        "minimalCallSendExecutorDisabledReady": checklist_passed,
        "readyForExplicitRealRequestSendAuthorization": checklist_passed,
        "readyForRealRequestSend": False,
        "sendExecutorPlan": _send_executor_plan(request),
        "authorizationBoundary": _authorization_boundary(request),
        "secretBoundary": _secret_boundary(),
        "networkBoundary": _network_boundary(),
        "responseHandlingBoundary": _response_handling_boundary(),
        "auditBoundary": _audit_boundary(),
        "rollbackBoundary": _rollback_boundary(),
        "sendExecutorPlanBuilt": checklist_passed,
        "disabledSendExecutorModelBuilt": checklist_passed,
        "sendExecutorPrepared": checklist_passed,
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
            "真实 LLM 最小调用发送执行器禁用壳已准备；当前不会创建真实发送实现、"
            "派发执行器、发送请求、联网、读取密钥、真实调用、创建任务或发布。"
        ),
    }


def build_real_llm_minimal_call_send_executor_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealLlmMinimalCallSendExecutorDisabledRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmMinimalCallSendExecutorDisabledRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            review = build_real_llm_minimal_call_poc_review(request, root=root)
        else:
            review = None
    except ProviderError:
        review = None
    if review is not None:
        context["minimalCallPocReviewReady"] = bool(review.get("minimalCallPocReviewReady", False))
        context["minimalCallPocReviewSummary"] = _minimal_call_review_summary(review)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
