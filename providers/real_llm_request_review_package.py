"""Real LLM request review package.

This module prepares a local, redacted request package for the first future
real LLM dry-run request review. It does not import SDKs, construct clients,
read secret values, send requests, create generated content, create tasks, or
publish artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_llm_sdk_boundary import ROOT, SECRET_ENV, SUPPORTED_PROVIDER
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS


REAL_LLM_REQUEST_REVIEW_PACKAGE_ID = "real_llm_request_review_package"


@dataclass(frozen=True)
class RealLlmRequestReviewPackageRequest:
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
    explicit_request_review_opt_in: bool = False
    client_boundary_confirmed: bool = False
    prompt_scope_confirmed: bool = False
    schema_validation_confirmed: bool = False
    audit_redaction_confirmed: bool = False
    human_review_policy_confirmed: bool = False
    no_request_send_confirmed: bool = False
    no_network_call_confirmed: bool = False
    no_real_llm_call_confirmed: bool = False
    reviewer: str | None = None
    approval_ref: str | None = None
    trace_id: str | None = None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(
    request: RealLlmRequestReviewPackageRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    return {
        "requestReviewPackageId": REAL_LLM_REQUEST_REVIEW_PACKAGE_ID,
        "phase": "Phase 2",
        "mode": "REAL_LLM_REQUEST_REVIEW_PACKAGE_ONLY",
        "providerId": request.provider_id,
        "supportedProvider": SUPPORTED_PROVIDER,
        "secretEnv": SECRET_ENV,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "secretValueLogged": False,
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
        "explicitRequestReviewOptIn": request.explicit_request_review_opt_in,
        "clientBoundaryConfirmed": request.client_boundary_confirmed,
        "promptScopeConfirmed": request.prompt_scope_confirmed,
        "schemaValidationConfirmed": request.schema_validation_confirmed,
        "auditRedactionConfirmed": request.audit_redaction_confirmed,
        "humanReviewPolicyConfirmed": request.human_review_policy_confirmed,
        "noRequestSendConfirmed": request.no_request_send_confirmed,
        "noNetworkCallConfirmed": request.no_network_call_confirmed,
        "noRealLlmCallConfirmed": request.no_real_llm_call_confirmed,
        "allowedOperations": [
            "request_shape_construction",
            "payload_redaction_preview",
            "review_checklist_generation",
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
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "requestShapeBuilt": False,
        "requestReviewPackageBuilt": False,
        "requestReviewPackageReady": False,
        "readyForManualRequestReview": False,
        "readyForFirstRealCallApproval": False,
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
        "rootPathUsedForExecution": False,
    }


def describe_real_llm_request_review_package(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmRequestReviewPackageRequest()
    return {
        **_base_context(request, root=root),
        "requiresExplicitRequestReviewOptIn": True,
        "requiresClientBoundaryConfirmation": True,
        "requiresPromptScopeConfirmation": True,
        "requiresSchemaValidationConfirmation": True,
        "requiresAuditRedactionConfirmation": True,
        "requiresHumanReviewPolicyConfirmation": True,
        "requiresNoRequestSendConfirmation": True,
        "requiresNoNetworkConfirmation": True,
        "requiresNoRealLlmCallConfirmation": True,
        "realCallAuthorizationPath": "future_manual_approval_after_request_review",
    }


def _missing_confirmations(request: RealLlmRequestReviewPackageRequest) -> list[dict[str, str]]:
    checks = [
        ("explicitRequestReviewOptIn", request.explicit_request_review_opt_in),
        ("clientBoundaryConfirmed", request.client_boundary_confirmed),
        ("promptScopeConfirmed", request.prompt_scope_confirmed),
        ("schemaValidationConfirmed", request.schema_validation_confirmed),
        ("auditRedactionConfirmed", request.audit_redaction_confirmed),
        ("humanReviewPolicyConfirmed", request.human_review_policy_confirmed),
        ("noRequestSendConfirmed", request.no_request_send_confirmed),
        ("noNetworkCallConfirmed", request.no_network_call_confirmed),
        ("noRealLlmCallConfirmed", request.no_real_llm_call_confirmed),
    ]
    return [
        {"field": field, "reason": "required for real LLM request review package"}
        for field, passed in checks
        if not passed
    ]


def _validate_request(request: RealLlmRequestReviewPackageRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request review package currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed for the first request review package"}],
        )
    if request.operation != "generateJson":
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request review package currently only supports generateJson",
            [{"field": "operation", "reason": "only generateJson is in scope for the first package"}],
        )
    if request.prompt_id != "lab_generation_v0":
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request review package currently only supports lab_generation_v0",
            [{"field": "promptId", "reason": "only lab_generation_v0 is in scope for the first package"}],
        )
    if request.output_kind != "Lab":
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM request review package currently only supports Lab output",
            [{"field": "outputKind", "reason": "only Lab DSL is in scope for the first package"}],
        )
    if request.timeout_seconds <= 0:
        raise ProviderError(
            "VALIDATION_ERROR",
            "timeoutSeconds must be positive",
            [{"field": "timeoutSeconds", "reason": "must be greater than 0"}],
        )
    if request.retry_count < 0:
        raise ProviderError(
            "VALIDATION_ERROR",
            "retryCount must be non-negative",
            [{"field": "retryCount", "reason": "must be greater than or equal to 0"}],
        )
    if request.concurrency_limit != 1:
        raise ProviderError(
            "VALIDATION_ERROR",
            "concurrencyLimit must remain 1 for the first real request review package",
            [{"field": "concurrencyLimit", "reason": "only single-request review is allowed"}],
        )
    missing = _missing_confirmations(request)
    if missing:
        raise ProviderError(
            "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED",
            "Real LLM request review package requires explicit opt-in and safety confirmations",
            missing,
        )


def _request_shape(request: RealLlmRequestReviewPackageRequest) -> dict[str, Any]:
    return {
        "provider": request.provider_id,
        "operation": request.operation,
        "modelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "promptId": request.prompt_id,
        "inputRef": request.input_ref,
        "responseFormat": {
            "type": "json_schema",
            "schemaRef": "templates/lab/lab.schema.json",
            "outputKind": request.output_kind,
        },
        "runtimeOptions": {
            "timeoutSeconds": request.timeout_seconds,
            "retryCount": request.retry_count,
            "concurrencyLimit": request.concurrency_limit,
        },
        "payloadPreview": redact_provider_payload(dict(request.payload or {})),
        "sendAllowed": False,
    }


def _review_checklist() -> list[dict[str, Any]]:
    return [
        {"id": "client_boundary_passed", "required": True, "owner": "operator"},
        {"id": "prompt_scope_reviewed", "required": True, "owner": "teacher_or_reviewer"},
        {"id": "lab_schema_selected", "required": True, "owner": "developer"},
        {"id": "payload_redaction_verified", "required": True, "owner": "security_reviewer"},
        {"id": "timeout_retry_concurrency_reviewed", "required": True, "owner": "developer"},
        {"id": "manual_review_policy_confirmed", "required": True, "owner": "teacher_or_reviewer"},
        {"id": "no_request_send_during_package_generation", "required": True, "owner": "operator"},
    ]


def _blockers() -> list[dict[str, str]]:
    return [
        {"field": "requestSent", "reason": "disabled_in_request_review_package"},
        {"field": "networkAccess", "reason": "disabled_until_final_real_call_approval"},
        {"field": "realCallAuthorized", "reason": "requires_future_manual_real_call_approval"},
        {"field": "taskCreated", "reason": "request review package must not create AI tasks"},
    ]


def build_real_llm_request_review_package(
    request: RealLlmRequestReviewPackageRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_request(request)
    return {
        **_base_context(request, root=root),
        "requestShapeBuilt": True,
        "requestShape": _request_shape(request),
        "reviewChecklist": _review_checklist(),
        "manualApprovalRequiredBeforeSend": True,
        "requestReviewPackageBuilt": True,
        "requestReviewPackageReady": True,
        "readyForManualRequestReview": True,
        "readyForFirstRealCallApproval": False,
        "requestSent": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "realCallAuthorized": False,
        "blockers": _blockers(),
    }


def build_real_llm_request_review_package_error_context(
    exc: ProviderError,
    *,
    request: RealLlmRequestReviewPackageRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmRequestReviewPackageRequest()
    return {
        **_base_context(request, root=root),
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
