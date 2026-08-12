"""Real LLM SDK approval gate.

This module evaluates the local approval checklist required before a future
task may implement a real LLM SDK path. It does not authorize a real call and
does not import SDKs, read secret values, check secret presence, open network
connections, create AI tasks, or publish artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_dry_run_plan import RealLlmDryRunPlanRequest, build_real_llm_dry_run_plan


ROOT = Path(__file__).resolve().parents[1]
REAL_LLM_APPROVAL_GATE_ID = "real_llm_approval_gate"


@dataclass(frozen=True)
class RealLlmApprovalGateRequest:
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


def _base_context(request: RealLlmApprovalGateRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    return {
        "gateId": REAL_LLM_APPROVAL_GATE_ID,
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "approvalMode": "PRE_IMPLEMENTATION_REVIEW",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "providerContractEnabled": bool(provider.get("enabled", False)) if provider else False,
        "secretEnv": provider.get("secretEnv") if provider else None,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
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
        "readyForRealProvider": False,
        "realCallAuthorized": False,
        "sdkImported": False,
        "clientCreated": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "traceId": request.trace_id,
    }


def _approval_checklist(request: RealLlmApprovalGateRequest, dry_run_plan_passed: bool) -> list[dict[str, Any]]:
    return [
        {
            "id": "approval_ref_provided",
            "passed": _clean_text(request.approval_ref) is not None,
            "required": True,
        },
        {
            "id": "reviewer_provided",
            "passed": _clean_text(request.reviewer) is not None,
            "required": True,
        },
        {
            "id": "dry_run_plan_passed",
            "passed": dry_run_plan_passed,
            "required": True,
        },
        {
            "id": "dry_run_plan_confirmed",
            "passed": request.dry_run_plan_confirmed,
            "required": True,
        },
        {
            "id": "runtime_guard_confirmed",
            "passed": request.runtime_guard_confirmed,
            "required": True,
        },
        {
            "id": "schema_review_confirmed",
            "passed": request.schema_review_confirmed,
            "required": True,
        },
        {
            "id": "human_review_policy_confirmed",
            "passed": request.human_review_policy_confirmed,
            "required": True,
        },
        {
            "id": "audit_redaction_confirmed",
            "passed": request.audit_redaction_confirmed,
            "required": True,
        },
    ]


def _blocking_reasons(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.append({"field": "realCallAuthorized", "reason": "false_until_future_explicit_real_provider_task"})
    return reasons


def build_real_llm_approval_gate_error_context(
    exc: ProviderError,
    *,
    request: RealLlmApprovalGateRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    return {
        **_base_context(request, root=root),
        "approvalGateEvaluated": False,
        "approvalChecklistPassed": False,
        "readyForImplementationTask": False,
        "errorCode": exc.code,
    }


def evaluate_real_llm_approval_gate(request: RealLlmApprovalGateRequest, *, root: Path = ROOT) -> dict[str, Any]:
    context = _base_context(request, root=root)
    dry_run_plan = build_real_llm_dry_run_plan(
        RealLlmDryRunPlanRequest(
            provider_id=request.provider_id,
            operation=request.operation,
            prompt_id=request.prompt_id,
            output_kind=request.output_kind,
            input_ref=request.input_ref,
            timeout_seconds=request.timeout_seconds,
            retry_count=request.retry_count,
            concurrency_limit=request.concurrency_limit,
            payload=request.payload,
            trace_id=request.trace_id,
        ),
        root=root,
    )
    dry_run_plan_passed = dry_run_plan.get("planPassed") is True and dry_run_plan.get("runtimeGuardPassed") is True
    checklist = _approval_checklist(request, dry_run_plan_passed)
    approval_checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)
    return {
        **context,
        "approvalGateEvaluated": True,
        "dryRunPlanPassed": dry_run_plan_passed,
        "approvalChecklist": checklist,
        "approvalChecklistPassed": approval_checklist_passed,
        "readyForImplementationTask": approval_checklist_passed,
        "realCallAuthorized": False,
        "dryRunPlanSummary": {
            "planId": dry_run_plan["planId"],
            "planPassed": dry_run_plan["planPassed"],
            "runtimeGuardPassed": dry_run_plan["runtimeGuardPassed"],
            "providerContractEnabled": dry_run_plan["providerContractEnabled"],
            "dryRunOnly": dry_run_plan["dryRunOnly"],
            "readyForRealProvider": dry_run_plan["readyForRealProvider"],
            "realLlmCalled": dry_run_plan["realLlmCalled"],
            "secretValueRead": dry_run_plan["secretValueRead"],
            "secretPresenceChecked": dry_run_plan["secretPresenceChecked"],
            "taskCreated": dry_run_plan["taskCreated"],
        },
        "requiredFutureChanges": [
            "separate_explicit_real_provider_task",
            "runtime_contract_change_review",
            "provider_contract_change_review",
            "sdk_dependency_review",
            "secret_injection_review",
            "network_access_review",
            "schema_validation_regression_tests",
            "human_review_flow_regression_tests",
        ],
        "blockedReasons": _blocking_reasons(checklist),
        "message": "真实 LLM SDK 批准门禁已评估；当前不会授权真实调用。",
    }
