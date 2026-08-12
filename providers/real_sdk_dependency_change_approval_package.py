"""Disabled real SDK dependency change approval package.

This module prepares a local approval-package model for a future real SDK
dependency file change. It does not write approval artifacts, create tasks,
write dependency files, materialize patches, apply patches, execute commands,
install SDKs, import SDKs, check secrets, use network access, call real LLMs,
or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_implementation_task_plan import (
    RealSdkDependencyImplementationTaskPlanRequest,
    build_real_sdk_dependency_implementation_task_plan,
    describe_real_sdk_dependency_implementation_task_plan,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_CHANGE_APPROVAL_PACKAGE_ID = "real_sdk_dependency_change_approval_package"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyChangeApprovalPackageRequest(RealSdkDependencyImplementationTaskPlanRequest):
    approver_confirmed: bool = False
    approval_record_location_confirmed: bool = False
    dependency_change_summary_confirmed: bool = False
    rollback_evidence_confirmed: bool = False
    test_evidence_plan_confirmed: bool = False
    security_owner_confirmed: bool = False
    maintenance_window_confirmed: bool = False
    no_approval_artifact_write_confirmed: bool = False
    no_dependency_change_execution_confirmed: bool = False
    no_real_call_before_approval_confirmed: bool = False


def _base_context(request: RealSdkDependencyChangeApprovalPackageRequest, *, root: Path) -> dict[str, Any]:
    task_plan_descriptor = describe_real_sdk_dependency_implementation_task_plan(root=root)
    return {
        **task_plan_descriptor,
        "approvalPackageId": REAL_SDK_DEPENDENCY_CHANGE_APPROVAL_PACKAGE_ID,
        "gateId": REAL_SDK_DEPENDENCY_CHANGE_APPROVAL_PACKAGE_ID,
        "upstreamGateId": "real_sdk_dependency_implementation_task_plan",
        "gateMode": "DEPENDENCY_CHANGE_APPROVAL_PACKAGE_DISABLED_ONLY",
        "approvalPackageMode": "LOCAL_APPROVAL_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "implementationTaskPlanRequired": True,
        "implementationTaskPlanReady": False,
        "approvalPackageOnly": True,
        "approvalPackageReady": False,
        "readyForManualDependencyChangeApproval": False,
        "manualApprovalGranted": False,
        "approvalPackageWritten": False,
        "approvalRecordMaterialized": False,
        "approvalTicketCreated": False,
        "dependencyChangeApproved": False,
        "dependencyChangeExecutionAuthorized": False,
        "dependencyFileChangeAuthorized": False,
        "dependencyManifestWriteAuthorized": False,
        "dependencyLockfileWriteAuthorized": False,
        "patchMaterialized": False,
        "patchApplyAuthorized": False,
        "commandExecutionAuthorized": False,
        "realCallBeforeApprovalAuthorized": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_change_approval_package(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyChangeApprovalPackageRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresImplementationTaskPlanReady": True,
        "requiresApprover": True,
        "requiresApprovalRecordLocation": True,
        "requiresRollbackEvidence": True,
        "requiresTestEvidencePlan": True,
        "pipeline": [
            "real_sdk_dependency_patch_proposal",
            "real_sdk_dependency_apply_gate",
            "real_sdk_dependency_implementation_task_plan",
            "dependency_change_approval_package",
            "future_reviewed_dependency_file_change_task",
            "future_real_llm_dry_run_after_dependency_review",
        ],
    }


def _task_plan_summary(task_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "planId": task_plan["planId"],
        "applyGateReady": task_plan["applyGateReady"],
        "implementationTaskPlanReady": task_plan["implementationTaskPlanReady"],
        "readyForReviewedDependencyImplementationTask": task_plan["readyForReviewedDependencyImplementationTask"],
        "dependencyImplementationTaskCreated": task_plan["dependencyImplementationTaskCreated"],
        "dependencyFileChanged": task_plan["dependencyFileChanged"],
        "patchMaterialized": task_plan["patchMaterialized"],
        "secretPresenceChecked": task_plan["secretPresenceChecked"],
        "networkAccess": task_plan["networkAccess"],
        "realLlmCalled": task_plan["realLlmCalled"],
    }


def _approval_checklist(
    request: RealSdkDependencyChangeApprovalPackageRequest,
    *,
    task_plan_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "implementation_task_plan_ready", "passed": task_plan_ready, "required": True},
        {"id": "approver_confirmed", "passed": request.approver_confirmed, "required": True},
        {
            "id": "approval_record_location_confirmed",
            "passed": request.approval_record_location_confirmed,
            "required": True,
        },
        {
            "id": "dependency_change_summary_confirmed",
            "passed": request.dependency_change_summary_confirmed,
            "required": True,
        },
        {"id": "rollback_evidence_confirmed", "passed": request.rollback_evidence_confirmed, "required": True},
        {"id": "test_evidence_plan_confirmed", "passed": request.test_evidence_plan_confirmed, "required": True},
        {"id": "security_owner_confirmed", "passed": request.security_owner_confirmed, "required": True},
        {"id": "maintenance_window_confirmed", "passed": request.maintenance_window_confirmed, "required": True},
        {
            "id": "no_approval_artifact_write_confirmed",
            "passed": request.no_approval_artifact_write_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_change_execution_confirmed",
            "passed": request.no_dependency_change_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_before_approval_confirmed",
            "passed": request.no_real_call_before_approval_confirmed,
            "required": True,
        },
    ]


def _approval_package_model(request: RealSdkDependencyChangeApprovalPackageRequest) -> dict[str, Any]:
    return {
        "packageId": REAL_SDK_DEPENDENCY_CHANGE_APPROVAL_PACKAGE_ID,
        "materializedNow": False,
        "writeNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "targetFiles": [
            {"path": "requirements*.txt", "writeNow": False, "requiredForFutureTask": False},
            {"path": "pyproject.toml", "writeNow": False, "requiredForFutureTask": False},
            {"path": "lockfile", "writeNow": False, "requiredForFutureTask": False},
        ],
        "requiredEvidence": [
            {"id": "manual_approval_record", "materializedNow": False},
            {"id": "dependency_change_summary", "materializedNow": False},
            {"id": "rollback_evidence", "materializedNow": False},
            {"id": "post_change_test_evidence_plan", "materializedNow": False},
            {"id": "security_owner_acknowledgement", "materializedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "approvalPackageWritten": False,
        "approvalRecordMaterialized": False,
        "approvalTicketCreated": False,
        "manualApprovalGranted": False,
        "dependencyChangeApproved": False,
        "dependencyChangeExecutionAuthorized": False,
        "taskCreated": False,
        "dependencyImplementationTaskCreated": False,
        "dependencyFileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "lockfileChanged": False,
        "dependencyLockfileChanged": False,
        "patchFileWritten": False,
        "patchMaterialized": False,
        "patchApplied": False,
        "dependencyPatchGenerated": False,
        "applyAuthorized": False,
        "patchApplyAuthorized": False,
        "commandExecutionAuthorized": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "autoPublishAllowed": False,
        "realPublish": False,
    }


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "manual_dependency_change_approval", "reason": "not_granted_by_disabled_package"},
            {"field": "approval_artifact_write", "reason": "not_written_by_package"},
            {"field": "future_reviewed_dependency_file_change_task", "reason": "must_be_separate_reviewed_task"},
            {"field": "dependency_manifest_write", "reason": "not_written_by_package"},
            {"field": "dependency_lockfile_write", "reason": "not_written_by_package"},
            {"field": "patch_materialization", "reason": "not_materialized_by_package"},
            {"field": "command_execution", "reason": "not_allowed_by_package"},
            {"field": "real_llm_call", "reason": "not_allowed_before_manual_dependency_change_approval"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_package"},
            {"field": "network_call", "reason": "not_allowed_by_package"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_change_approval_package",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_change_approval_package.py",
        },
        {
            "id": "test_real_sdk_dependency_implementation_task_plan",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_implementation_task_plan.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyChangeApprovalPackageRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖变更人工批准包当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency change approval package"}],
        )


def build_real_sdk_dependency_change_approval_package_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyChangeApprovalPackageRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            task_plan = build_real_sdk_dependency_implementation_task_plan(request, root=root)
        else:
            task_plan = None
    except ProviderError:
        task_plan = None
    if task_plan is not None:
        context["implementationTaskPlanReady"] = bool(
            task_plan.get("readyForReviewedDependencyImplementationTask", False)
        )
        context["implementationTaskPlanSummary"] = _task_plan_summary(task_plan)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_change_approval_package(
    request: RealSdkDependencyChangeApprovalPackageRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    task_plan = build_real_sdk_dependency_implementation_task_plan(request, root=root)
    task_plan_ready = task_plan.get("readyForReviewedDependencyImplementationTask") is True
    checklist = _approval_checklist(request, task_plan_ready=task_plan_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "implementationTaskPlanReady": task_plan_ready,
        "implementationTaskPlanSummary": _task_plan_summary(task_plan),
        "approvalPackageChecklist": checklist,
        "approvalPackageReady": checklist_passed,
        "readyForManualDependencyChangeApproval": checklist_passed,
        "approvalPackageModel": _approval_package_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖变更人工批准包已生成；当前不会写批准文件、创建任务、写依赖文件、执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
