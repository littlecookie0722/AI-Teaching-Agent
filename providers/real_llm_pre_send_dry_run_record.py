"""Pre-send dry-run record for the first real LLM call.

This module is the last local record before a future minimal real-call PoC.
It depends on the disabled first-call executor, but it never executes a dry
run, dispatches an executor, sends a request, reads secret values, accesses
network, creates generated content, creates tasks, or publishes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_first_call_executor_disabled import (
    RealLlmFirstCallExecutorDisabledRequest,
    describe_real_llm_first_call_executor_disabled,
    prepare_real_llm_first_call_executor_disabled,
)
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_PRE_SEND_DRY_RUN_RECORD_ID = "real_llm_pre_send_dry_run_record"


@dataclass(frozen=True)
class RealLlmPreSendDryRunRecordRequest(RealLlmFirstCallExecutorDisabledRequest):
    explicit_pre_send_dry_run_record_opt_in: bool = False
    disabled_executor_confirmed: bool = False
    approval_gate_confirmed: bool = False
    log_redaction_confirmed: bool = False
    failure_rollback_confirmed: bool = False
    response_schema_validation_confirmed: bool = False
    post_call_review_confirmed: bool = False
    no_request_send_in_dry_run_confirmed: bool = False
    no_network_access_in_dry_run_confirmed: bool = False
    no_secret_read_in_dry_run_confirmed: bool = False
    no_task_creation_in_dry_run_confirmed: bool = False
    no_publish_in_dry_run_confirmed: bool = False


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmPreSendDryRunRecordRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    disabled_descriptor = describe_real_llm_first_call_executor_disabled(root=root)
    return {
        **disabled_descriptor,
        "preSendDryRunRecordId": REAL_LLM_PRE_SEND_DRY_RUN_RECORD_ID,
        "upstreamGateId": "real_llm_first_call_executor_disabled",
        "mode": "REAL_LLM_PRE_SEND_DRY_RUN_RECORD_ONLY",
        "recordMode": "PRE_SEND_DRY_RUN_RECORD_MODEL_ONLY",
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
        "explicitPreSendDryRunRecordOptIn": request.explicit_pre_send_dry_run_record_opt_in,
        "disabledExecutorConfirmed": request.disabled_executor_confirmed,
        "approvalGateConfirmed": request.approval_gate_confirmed,
        "requestShapeConfirmed": request.request_shape_confirmed,
        "logRedactionConfirmed": request.log_redaction_confirmed,
        "failureRollbackConfirmed": request.failure_rollback_confirmed,
        "responseSchemaValidationConfirmed": request.response_schema_validation_confirmed,
        "postCallReviewConfirmed": request.post_call_review_confirmed,
        "noRequestSendInDryRunConfirmed": request.no_request_send_in_dry_run_confirmed,
        "noNetworkAccessInDryRunConfirmed": request.no_network_access_in_dry_run_confirmed,
        "noSecretReadInDryRunConfirmed": request.no_secret_read_in_dry_run_confirmed,
        "noTaskCreationInDryRunConfirmed": request.no_task_creation_in_dry_run_confirmed,
        "noPublishInDryRunConfirmed": request.no_publish_in_dry_run_confirmed,
        "allowedOperations": [
            "client_boundary_confirmation_check",
            "first_call_approval_gate_evaluation",
            "disabled_executor_plan_generation",
            "pre_send_dry_run_record_generation",
        ],
        "blockedOperations": [
            "sdk_import",
            "client_construction",
            "secret_presence_check",
            "secret_value_read",
            "executor_dispatch",
            "dry_run_execution",
            "dry_run_record_write",
            "request_send",
            "network_request",
            "real_llm_call",
            "generated_content_creation",
            "task_creation",
            "publish",
        ],
        "disabledFirstCallExecutorReady": False,
        "preSendDryRunChecklistReady": False,
        "preSendDryRunRecordReady": False,
        "readyForMinimalRealCallPoc": False,
        "readyForRealRequestSend": False,
        "executorPrepared": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "dryRunRecordBuilt": False,
        "dryRunRecordMaterialized": False,
        "dryRunRecordPersisted": False,
        "dryRunRecordWritten": False,
        "dryRunExecuted": False,
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
        "realCallAuthorizationPath": "future_minimal_real_call_poc_after_pre_send_dry_run_record_review",
        "traceId": request.trace_id,
    }


def describe_real_llm_pre_send_dry_run_record(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmPreSendDryRunRecordRequest()
    return {
        **_base_context(request, root=root),
        "requiresDisabledFirstCallExecutorReady": True,
        "requiresExplicitPreSendDryRunRecordOptIn": True,
        "requiresLogRedactionConfirmation": True,
        "requiresRollbackConfirmation": True,
        "requiresResponseSchemaValidationConfirmation": True,
        "requiresPostCallReviewConfirmation": True,
        "requiresNoRequestSendConfirmation": True,
        "requiresNoNetworkAccessConfirmation": True,
        "requiresNoSecretReadConfirmation": True,
        "requiresNoTaskCreationConfirmation": True,
        "requiresNoPublishConfirmation": True,
        "realCallAuthorizationPath": "future_minimal_real_call_poc_after_pre_send_dry_run_record_review",
    }


def _validate_provider_scope(request: RealLlmPreSendDryRunRecordRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM pre-send dry-run record currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed for the pre-send dry-run record"}],
        )


def _pre_send_checklist(
    request: RealLlmPreSendDryRunRecordRequest,
    *,
    disabled_executor_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "disabled_executor_ready", "passed": disabled_executor_ready, "required": True},
        {
            "id": "explicit_pre_send_dry_run_record_opt_in",
            "passed": request.explicit_pre_send_dry_run_record_opt_in,
            "required": True,
        },
        {
            "id": "disabled_executor_confirmed",
            "passed": request.disabled_executor_confirmed,
            "required": True,
        },
        {"id": "approval_gate_confirmed", "passed": request.approval_gate_confirmed, "required": True},
        {"id": "request_shape_confirmed", "passed": request.request_shape_confirmed, "required": True},
        {"id": "log_redaction_confirmed", "passed": request.log_redaction_confirmed, "required": True},
        {"id": "failure_rollback_confirmed", "passed": request.failure_rollback_confirmed, "required": True},
        {
            "id": "response_schema_validation_confirmed",
            "passed": request.response_schema_validation_confirmed,
            "required": True,
        },
        {"id": "post_call_review_confirmed", "passed": request.post_call_review_confirmed, "required": True},
        {
            "id": "no_request_send_in_dry_run_confirmed",
            "passed": request.no_request_send_in_dry_run_confirmed,
            "required": True,
        },
        {
            "id": "no_network_access_in_dry_run_confirmed",
            "passed": request.no_network_access_in_dry_run_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_read_in_dry_run_confirmed",
            "passed": request.no_secret_read_in_dry_run_confirmed,
            "required": True,
        },
        {
            "id": "no_task_creation_in_dry_run_confirmed",
            "passed": request.no_task_creation_in_dry_run_confirmed,
            "required": True,
        },
        {
            "id": "no_publish_in_dry_run_confirmed",
            "passed": request.no_publish_in_dry_run_confirmed,
            "required": True,
        },
    ]


def _disabled_executor_summary(disabled_executor: dict[str, Any]) -> dict[str, Any]:
    return {
        "firstCallExecutorDisabledId": disabled_executor["firstCallExecutorDisabledId"],
        "approvalGateReady": disabled_executor["approvalGateReady"],
        "disabledFirstCallExecutorReady": disabled_executor["disabledFirstCallExecutorReady"],
        "readyForMinimalRealCallPocReview": disabled_executor["readyForMinimalRealCallPocReview"],
        "readyForRealRequestSend": disabled_executor["readyForRealRequestSend"],
        "executorPrepared": disabled_executor["executorPrepared"],
        "executorDispatched": disabled_executor["executorDispatched"],
        "requestSent": disabled_executor["requestSent"],
        "networkAccess": disabled_executor["networkAccess"],
        "realLlmCalled": disabled_executor["realLlmCalled"],
        "secretValueRead": disabled_executor["secretValueRead"],
        "generatedContentCreated": disabled_executor["generatedContentCreated"],
        "taskCreated": disabled_executor["taskCreated"],
    }


def _audit_log_plan(request: RealLlmPreSendDryRunRecordRequest) -> dict[str, Any]:
    return {
        "logPlanId": "real_llm_first_call_pre_send_audit_log_plan",
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "redactionRequired": True,
        "logSecretValue": False,
        "logPromptRawPayload": False,
        "logResponseRawBeforeRedaction": False,
        "logOnlyDecisionFields": [
            "providerId",
            "operation",
            "promptId",
            "outputKind",
            "inputRef",
            "targetModelAlias",
            "approvalRef",
            "reviewer",
            "readyForMinimalRealCallPoc",
        ],
    }


def _rollback_plan() -> dict[str, Any]:
    return {
        "rollbackPlanId": "real_llm_first_call_pre_send_rollback_plan",
        "persistentMutationPlanned": False,
        "taskCreationPlanned": False,
        "publishPlanned": False,
        "remoteStateChanged": False,
        "rollbackActions": [
            "discard_local_dry_run_record_json",
            "keep_ai_task_creation_disabled",
            "keep_publish_disabled",
        ],
    }


def _validation_plan() -> dict[str, Any]:
    return {
        "validationPlanId": "real_llm_first_call_pre_send_response_validation_plan",
        "schemaRef": "templates/lab/lab.schema.json",
        "outputKind": "Lab",
        "generatedContentDefaultStatus": "WAITING_REVIEW",
        "validateBeforeTaskCreation": True,
        "taskCreationAllowedNow": False,
        "publishAllowedNow": False,
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "dryRunExecuted", "reason": "pre_send_record_only_does_not_execute_dry_run"},
            {"field": "dryRunRecordWritten", "reason": "pre_send_record_only_does_not_write_records"},
            {"field": "requestSent", "reason": "requires_future_minimal_real_call_poc"},
            {"field": "networkAccess", "reason": "requires_future_minimal_real_call_poc"},
            {"field": "secretValueRead", "reason": "pre_send_record_only_does_not_read_secret_values"},
            {"field": "realCallAuthorized", "reason": "requires_future_minimal_real_call_poc"},
            {"field": "taskCreated", "reason": "pre_send_record_must_not_create_ai_tasks"},
        ]
    )
    return reasons


def build_real_llm_pre_send_dry_run_record(
    request: RealLlmPreSendDryRunRecordRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    disabled_executor = prepare_real_llm_first_call_executor_disabled(request, root=root)
    disabled_executor_ready = disabled_executor.get("disabledFirstCallExecutorReady") is True
    checklist = _pre_send_checklist(request, disabled_executor_ready=disabled_executor_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "requestReviewPackageReady": disabled_executor["requestReviewPackageReady"],
        "requestShapeBuilt": disabled_executor["requestShapeBuilt"],
        "requestReviewPackageBuilt": disabled_executor["requestReviewPackageBuilt"],
        "readyForManualRequestReview": disabled_executor["readyForManualRequestReview"],
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
        "approvalGateReady": disabled_executor["approvalGateReady"],
        "firstCallApprovalGateReady": disabled_executor["firstCallApprovalGateReady"],
        "firstCallApprovalChecklistReady": disabled_executor["firstCallApprovalChecklistReady"],
        "readyForDisabledFirstCallExecutor": disabled_executor["readyForDisabledFirstCallExecutor"],
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
        "disabledExecutorChecklistReady": disabled_executor["disabledExecutorChecklistReady"],
        "disabledFirstCallExecutorReady": disabled_executor_ready,
        "readyForMinimalRealCallPocReview": disabled_executor["readyForMinimalRealCallPocReview"],
        "disabledExecutorSummary": _disabled_executor_summary(disabled_executor),
        "preSendDryRunChecklist": checklist,
        "preSendDryRunChecklistReady": checklist_passed,
        "preSendDryRunRecordReady": checklist_passed,
        "readyForMinimalRealCallPoc": checklist_passed,
        "readyForRealRequestSend": False,
        "dryRunRecord": {
            "recordId": REAL_LLM_PRE_SEND_DRY_RUN_RECORD_ID,
            "mode": "PRE_SEND_DRY_RUN_RECORD_MODEL_ONLY",
            "providerId": request.provider_id,
            "operation": request.operation,
            "promptId": request.prompt_id,
            "outputKind": request.output_kind,
            "inputRef": request.input_ref,
            "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
            "approvalRef": _clean_text(request.approval_ref),
            "reviewer": _clean_text(request.reviewer),
            "built": checklist_passed,
            "materialized": False,
            "persisted": False,
            "written": False,
            "executed": False,
            "requestSendAllowedNow": False,
            "networkAllowedNow": False,
            "secretReadAllowedNow": False,
            "taskCreationAllowedNow": False,
            "publishAllowedNow": False,
            "nextStage": "minimal_real_call_poc_implementation_review",
        },
        "auditLogPlan": _audit_log_plan(request),
        "rollbackPlan": _rollback_plan(),
        "validationPlan": _validation_plan(),
        "executorPrepared": disabled_executor["executorPrepared"],
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDispatched": False,
        "dryRunRecordBuilt": checklist_passed,
        "dryRunRecordMaterialized": False,
        "dryRunRecordPersisted": False,
        "dryRunRecordWritten": False,
        "dryRunExecuted": False,
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
            "真实 LLM 发送前 dry-run 记录已生成；当前不会执行 dry-run、写记录、"
            "派发执行器、发送请求、联网、读取密钥、真实调用、生成内容、创建任务或发布。"
        ),
    }


def build_real_llm_pre_send_dry_run_record_error_context(
    exc: ProviderError,
    *,
    request: RealLlmPreSendDryRunRecordRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmPreSendDryRunRecordRequest()
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            disabled_executor = prepare_real_llm_first_call_executor_disabled(request, root=root)
        else:
            disabled_executor = None
    except ProviderError:
        disabled_executor = None
    if disabled_executor is not None:
        context["disabledFirstCallExecutorReady"] = bool(
            disabled_executor.get("disabledFirstCallExecutorReady", False)
        )
        context["disabledExecutorSummary"] = _disabled_executor_summary(disabled_executor)
    return {
        **context,
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
