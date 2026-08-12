"""Real LLM SDK implementation task blueprint.

This module turns the local dry-run plan and approval gate into a
machine-readable blueprint for a future real SDK implementation task. It does
not install SDKs, import SDKs, read secret values, check secret presence, open
network connections, create AI tasks, or publish artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_approval_gate import RealLlmApprovalGateRequest, evaluate_real_llm_approval_gate


ROOT = Path(__file__).resolve().parents[1]
REAL_LLM_SDK_TASK_BLUEPRINT_ID = "real_llm_sdk_task_blueprint"
DEFAULT_MODEL_ALIAS = "provider-default-lab-json-model"


@dataclass(frozen=True)
class RealLlmSdkTaskBlueprintRequest:
    provider_id: str
    operation: str = "generateJson"
    prompt_id: str = "lab_generation_v0"
    output_kind: str = "Lab"
    input_ref: str = "examples/input/demo-source.md"
    timeout_seconds: int = 30
    retry_count: int = 1
    concurrency_limit: int = 1
    payload: Mapping[str, Any] | None = None
    approval_ref: str | None = None
    reviewer: str | None = None
    dry_run_plan_confirmed: bool = False
    runtime_guard_confirmed: bool = False
    schema_review_confirmed: bool = False
    human_review_policy_confirmed: bool = False
    audit_redaction_confirmed: bool = False
    target_model_alias: str = DEFAULT_MODEL_ALIAS
    task_ref: str | None = None
    trace_id: str | None = None


def _load_runtime_contract(root: Path) -> dict[str, Any]:
    with (root / "config/runtime.contract.json").open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ProviderError(
            "PROVIDER_CONTRACT_ERROR",
            "Runtime contract root must be object",
            [{"field": "config/runtime.contract.json", "reason": "root must be object"}],
        )
    return payload


def _find_provider(contract: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    for provider in contract.get("providers", []):
        if provider.get("id") == provider_id:
            return provider
    return None


def _safe_runtime_flags(runtime_contract: dict[str, Any]) -> dict[str, str]:
    return {
        key: value
        for key, value in runtime_contract.get("defaults", {}).items()
        if key.startswith("ENABLE_") or key in {"APP_PHASE", "APP_MODE"}
    }


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _base_context(request: RealLlmSdkTaskBlueprintRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    return {
        "blueprintId": REAL_LLM_SDK_TASK_BLUEPRINT_ID,
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "blueprintMode": "PRE_IMPLEMENTATION_BLUEPRINT",
        "targetTaskType": "REAL_LLM_SDK_MINIMAL_POC",
        "taskRef": _clean_text(request.task_ref),
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "providerContractEnabled": bool(provider.get("enabled", False)) if provider else False,
        "secretEnv": provider.get("secretEnv") if provider else None,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "timeoutSeconds": request.timeout_seconds,
        "retryCount": request.retry_count,
        "concurrencyLimit": request.concurrency_limit,
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "dryRunPlanConfirmed": request.dry_run_plan_confirmed,
        "runtimeGuardConfirmed": request.runtime_guard_confirmed,
        "schemaReviewConfirmed": request.schema_review_confirmed,
        "humanReviewPolicyConfirmed": request.human_review_policy_confirmed,
        "auditRedactionConfirmed": request.audit_redaction_confirmed,
        "runtimeFlags": _safe_runtime_flags(runtime_contract),
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "networkAccessEnabledNow": False,
        "implementationAllowed": False,
        "realCallAuthorized": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def _approval_request(request: RealLlmSdkTaskBlueprintRequest) -> RealLlmApprovalGateRequest:
    return RealLlmApprovalGateRequest(
        provider_id=request.provider_id,
        operation=request.operation,
        prompt_id=request.prompt_id,
        output_kind=request.output_kind,
        input_ref=request.input_ref,
        timeout_seconds=request.timeout_seconds,
        retry_count=request.retry_count,
        concurrency_limit=request.concurrency_limit,
        payload=request.payload,
        approval_ref=request.approval_ref,
        reviewer=request.reviewer,
        dry_run_plan_confirmed=request.dry_run_plan_confirmed,
        runtime_guard_confirmed=request.runtime_guard_confirmed,
        schema_review_confirmed=request.schema_review_confirmed,
        human_review_policy_confirmed=request.human_review_policy_confirmed,
        audit_redaction_confirmed=request.audit_redaction_confirmed,
        trace_id=request.trace_id,
    )


def _target_scope(request: RealLlmSdkTaskBlueprintRequest) -> dict[str, Any]:
    return {
        "scopeId": "lab_generate_from_source_minimal_poc",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "generatedStatus": "WAITING_REVIEW",
        "publishAllowed": False,
    }


def _proposed_change_set() -> list[dict[str, Any]]:
    return [
        {
            "path": "providers/real_llm_poc_adapter.py",
            "purpose": "Add the smallest disabled-by-default real SDK invocation path behind explicit gates.",
            "currentTurnChanged": False,
            "requiresReview": True,
        },
        {
            "path": "providers/provider.contract.json",
            "purpose": "Review provider enablement and model alias config without changing defaults silently.",
            "currentTurnChanged": False,
            "requiresReview": True,
        },
        {
            "path": "config/runtime.contract.json",
            "purpose": "Review runtime feature flags, timeout, retry, concurrency, redaction, and network gating.",
            "currentTurnChanged": False,
            "requiresReview": True,
        },
        {
            "path": ".env.example",
            "purpose": "Document environment variable names only; never commit secret values.",
            "currentTurnChanged": False,
            "requiresReview": True,
        },
        {
            "path": "tests/test_real_provider_sdk_poc.py",
            "purpose": "Add regression coverage for disabled defaults, missing secrets, redaction, schema, and review gates.",
            "currentTurnChanged": False,
            "requiresReview": True,
        },
        {
            "path": "providers/README.md",
            "purpose": "Document the future SDK path, safety limits, CLI examples, and verification commands.",
            "currentTurnChanged": False,
            "requiresReview": True,
        },
        {
            "path": "providers/PHASE2_PROVIDER_PLAN.md",
            "purpose": "Update the provider plan after a future implementation task is explicitly approved.",
            "currentTurnChanged": False,
            "requiresReview": True,
        },
    ]


def _implementation_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "create_feature_branch_or_task_record",
            "status": "PLANNED",
            "description": "Track the future SDK task separately from the mock baseline.",
        },
        {
            "id": "review_sdk_dependency",
            "status": "BLOCKED",
            "description": "Choose and pin provider SDK dependency only after explicit task approval.",
        },
        {
            "id": "add_disabled_sdk_adapter_path",
            "status": "BLOCKED",
            "description": "Add code behind runtime/provider gates while preserving mock default behavior.",
        },
        {
            "id": "inject_secret_name_only",
            "status": "BLOCKED",
            "description": "Use configured environment variable names; do not read or log values in planning.",
        },
        {
            "id": "enable_network_under_guard",
            "status": "BLOCKED",
            "description": "Future real calls require explicit network review and runtime flag changes.",
        },
        {
            "id": "validate_lab_schema_before_task",
            "status": "REQUIRED",
            "description": "Future real JSON output must pass Lab DSL schema validation before task creation.",
        },
        {
            "id": "create_waiting_review_task",
            "status": "REQUIRED_AFTER_SCHEMA",
            "description": "Future real output must create a WAITING_REVIEW task, never an auto-published artifact.",
        },
        {
            "id": "write_redacted_audit_event",
            "status": "REQUIRED",
            "description": "All future success and failure paths must write redacted provider audit records.",
        },
    ]


def _dependency_plan() -> dict[str, Any]:
    return {
        "sdkDependencyInstalled": False,
        "dependencyChangeAllowedNow": False,
        "futureReviewRequired": True,
        "notes": [
            "Do not install provider SDKs in this blueprint step.",
            "Pin and review any future SDK dependency in a separate implementation task.",
        ],
    }


def _environment_plan(secret_env: str | None) -> dict[str, Any]:
    return {
        "secretEnv": secret_env,
        "secretNameOnly": True,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "envExampleUpdateAllowedNow": False,
    }


def _network_plan() -> dict[str, Any]:
    return {
        "networkAccessRequiredForFuture": True,
        "networkAccessEnabledNow": False,
        "networkAccess": False,
        "requiresExplicitRuntimeFlagReview": True,
    }


def _test_matrix() -> list[dict[str, Any]]:
    return [
        {
            "id": "test_real_llm_sdk_task_blueprint",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_llm_sdk_task_blueprint.py",
        },
        {
            "id": "test_real_llm_approval_gate",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_llm_approval_gate.py",
        },
        {
            "id": "test_real_llm_dry_run_plan",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_llm_dry_run_plan.py",
        },
        {
            "id": "test_provider_runtime_guard",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_provider_runtime_guard.py",
        },
        {
            "id": "test_real_provider_sdk_poc",
            "status": "PLANNED_FOR_FUTURE_TASK",
            "command": "python -m pytest tests/test_real_provider_sdk_poc.py",
        },
        {
            "id": "test_all",
            "status": "REQUIRED_BEFORE_MERGE",
            "command": "python -m pytest",
        },
    ]


def _rollback_plan() -> list[dict[str, str]]:
    return [
        {
            "id": "restore_mock_default",
            "action": "Keep activeProvider=mock and disable future real-provider flags.",
        },
        {
            "id": "disable_network",
            "action": "Return network flags to disabled state if a future SDK task fails review.",
        },
        {
            "id": "remove_sdk_dependency",
            "action": "Remove any future SDK dependency via reviewed dependency-change rollback.",
        },
        {
            "id": "keep_review_gate",
            "action": "Keep generated content in WAITING_REVIEW until humans approve.",
        },
    ]


def _human_review_plan() -> dict[str, Any]:
    return {
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "publishBeforeApprovalAllowed": False,
        "reviewArtifacts": [
            "Lab DSL JSON/YAML",
            "Schema validation result",
            "Redacted provider audit event",
            "Prompt and model alias metadata",
        ],
    }


def _blocked_until() -> list[dict[str, str]]:
    return [
        {"field": "explicit_user_task", "reason": "real_sdk_implementation_must_be_requested_separately"},
        {"field": "approval_gate", "reason": "must_pass_before_implementation_task"},
        {"field": "provider_contract_change", "reason": "requires_review"},
        {"field": "runtime_contract_change", "reason": "requires_review"},
        {"field": "sdk_dependency", "reason": "requires_review"},
        {"field": "secret_injection", "reason": "requires_review"},
        {"field": "network_access", "reason": "requires_review"},
        {"field": "realCallAuthorized", "reason": "false_in_blueprint"},
    ]


def _approval_summary(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "gateId": gate["gateId"],
        "approvalGateEvaluated": gate["approvalGateEvaluated"],
        "approvalChecklistPassed": gate["approvalChecklistPassed"],
        "readyForImplementationTask": gate["readyForImplementationTask"],
        "realCallAuthorized": gate["realCallAuthorized"],
        "secretPresenceChecked": gate["secretPresenceChecked"],
        "secretValueRead": gate["secretValueRead"],
        "realLlmCalled": gate["realLlmCalled"],
        "networkAccess": gate["networkAccess"],
    }


def build_real_llm_sdk_task_blueprint_error_context(
    exc: ProviderError,
    *,
    request: RealLlmSdkTaskBlueprintRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    return {
        **_base_context(request, root=root),
        "blueprintGenerated": False,
        "blueprintReady": False,
        "readyForImplementationTask": False,
        "errorCode": exc.code,
    }


def build_real_llm_sdk_task_blueprint(
    request: RealLlmSdkTaskBlueprintRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    approval_gate = evaluate_real_llm_approval_gate(_approval_request(request), root=root)
    blueprint_ready = approval_gate.get("readyForImplementationTask") is True

    return {
        **context,
        "blueprintGenerated": True,
        "blueprintReady": blueprint_ready,
        "readyForImplementationTask": blueprint_ready,
        "implementationAllowed": False,
        "realCallAuthorized": False,
        "approvalGateSummary": _approval_summary(approval_gate),
        "targetScope": _target_scope(request),
        "proposedChangeSet": _proposed_change_set(),
        "implementationSteps": _implementation_steps(),
        "dependencyPlan": _dependency_plan(),
        "environmentPlan": _environment_plan(context["secretEnv"]),
        "networkPlan": _network_plan(),
        "testMatrix": _test_matrix(),
        "rollbackPlan": _rollback_plan(),
        "humanReviewPlan": _human_review_plan(),
        "blockedUntil": _blocked_until(),
        "message": "真实 LLM SDK 最小接入任务蓝图已生成；当前不会实施或授权真实调用。",
    }
