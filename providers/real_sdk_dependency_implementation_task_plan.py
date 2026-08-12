"""Disabled real SDK dependency implementation task plan.

This module prepares a reviewed future task plan for real SDK dependency file
changes. It does not create tasks, write dependency files, materialize patches,
apply patches, execute commands, install SDKs, import SDKs, check secrets, use
network access, call real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_apply_gate import (
    RealSdkDependencyApplyGateRequest,
    build_real_sdk_dependency_apply_gate,
    describe_real_sdk_dependency_apply_gate,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_IMPLEMENTATION_TASK_PLAN_ID = "real_sdk_dependency_implementation_task_plan"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyImplementationTaskPlanRequest(RealSdkDependencyApplyGateRequest):
    implementation_task_scope_confirmed: bool = False
    change_window_review_confirmed: bool = False
    dependency_manifest_target_confirmed: bool = False
    lockfile_update_strategy_confirmed: bool = False
    rollback_owner_confirmed: bool = False
    post_change_test_owner_confirmed: bool = False
    no_dependency_file_change_confirmed: bool = False
    no_patch_materialization_confirmed: bool = False
    no_task_creation_confirmed: bool = False
    no_real_call_after_plan_confirmed: bool = False


def _base_context(request: RealSdkDependencyImplementationTaskPlanRequest, *, root: Path) -> dict[str, Any]:
    apply_descriptor = describe_real_sdk_dependency_apply_gate(root=root)
    return {
        **apply_descriptor,
        "planId": REAL_SDK_DEPENDENCY_IMPLEMENTATION_TASK_PLAN_ID,
        "gateId": REAL_SDK_DEPENDENCY_IMPLEMENTATION_TASK_PLAN_ID,
        "upstreamGateId": "real_sdk_dependency_apply_gate",
        "gateMode": "DEPENDENCY_IMPLEMENTATION_TASK_PLAN_DISABLED_ONLY",
        "planningMode": "REVIEWED_TASK_PLAN_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "applyGateRequired": True,
        "applyGateReady": False,
        "implementationTaskPlanOnly": True,
        "implementationTaskPlanReady": False,
        "readyForReviewedDependencyImplementationTask": False,
        "dependencyImplementationTaskCreated": False,
        "implementationTicketMaterialized": False,
        "taskCreationAuthorized": False,
        "dependencyFileChangeAuthorized": False,
        "dependencyManifestWriteAuthorized": False,
        "dependencyLockfileWriteAuthorized": False,
        "patchMaterialized": False,
        "patchApplyAuthorized": False,
        "commandExecutionAuthorized": False,
        "realCallAfterPlanAuthorized": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_implementation_task_plan(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyImplementationTaskPlanRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresApplyGateReady": True,
        "requiresTaskScopeReview": True,
        "requiresChangeWindowReview": True,
        "requiresRollbackOwner": True,
        "requiresPostChangeTestOwner": True,
        "pipeline": [
            "real_sdk_dependency_patch_proposal",
            "real_sdk_dependency_apply_gate",
            "dependency_implementation_task_plan",
            "future_reviewed_dependency_file_change_task",
            "future_real_llm_dry_run_after_dependency_review",
        ],
    }


def _apply_gate_summary(apply_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "gateId": apply_gate["gateId"],
        "patchProposalReady": apply_gate["patchProposalReady"],
        "applyGateChecklistPassed": apply_gate["applyGateChecklistPassed"],
        "readyForFutureDependencyPatchApplyTask": apply_gate["readyForFutureDependencyPatchApplyTask"],
        "applyAuthorized": apply_gate["applyAuthorized"],
        "patchApplied": apply_gate["patchApplied"],
        "dependencyFileChanged": apply_gate["dependencyFileChanged"],
        "commandExecutionAuthorized": apply_gate.get("commandExecutionAuthorized", False),
        "secretPresenceChecked": apply_gate["secretPresenceChecked"],
        "networkAccess": apply_gate["networkAccess"],
    }


def _implementation_checklist(
    request: RealSdkDependencyImplementationTaskPlanRequest,
    *,
    apply_gate_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "apply_gate_ready", "passed": apply_gate_ready, "required": True},
        {
            "id": "implementation_task_scope_confirmed",
            "passed": request.implementation_task_scope_confirmed,
            "required": True,
        },
        {"id": "change_window_review_confirmed", "passed": request.change_window_review_confirmed, "required": True},
        {
            "id": "dependency_manifest_target_confirmed",
            "passed": request.dependency_manifest_target_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_update_strategy_confirmed",
            "passed": request.lockfile_update_strategy_confirmed,
            "required": True,
        },
        {"id": "rollback_owner_confirmed", "passed": request.rollback_owner_confirmed, "required": True},
        {
            "id": "post_change_test_owner_confirmed",
            "passed": request.post_change_test_owner_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_change_confirmed",
            "passed": request.no_dependency_file_change_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_materialization_confirmed",
            "passed": request.no_patch_materialization_confirmed,
            "required": True,
        },
        {"id": "no_task_creation_confirmed", "passed": request.no_task_creation_confirmed, "required": True},
        {
            "id": "no_real_call_after_plan_confirmed",
            "passed": request.no_real_call_after_plan_confirmed,
            "required": True,
        },
    ]


def _implementation_task_plan() -> list[dict[str, Any]]:
    return [
        {
            "id": "prepare_reviewed_branch",
            "status": "FUTURE_REVIEWED_TASK_ONLY",
            "executeNow": False,
            "writeNow": False,
            "createTaskNow": False,
            "description": "Prepare a reviewed branch or work item before dependency files are touched.",
        },
        {
            "id": "review_dependency_target_files",
            "status": "FUTURE_REVIEWED_TASK_ONLY",
            "executeNow": False,
            "writeNow": False,
            "createTaskNow": False,
            "description": "Confirm exact dependency manifest and lockfile targets with rollback owner.",
        },
        {
            "id": "future_edit_dependency_manifest",
            "status": "FUTURE_REVIEWED_TASK_ONLY",
            "executeNow": False,
            "writeNow": False,
            "createTaskNow": False,
            "description": "Edit dependency manifest only inside the future approved task.",
        },
        {
            "id": "future_lockfile_update_strategy",
            "status": "FUTURE_REVIEWED_TASK_ONLY",
            "executeNow": False,
            "writeNow": False,
            "createTaskNow": False,
            "description": "Choose whether lockfile update is manual, skipped, or generated in a later reviewed task.",
        },
        {
            "id": "future_post_change_test_matrix",
            "status": "FUTURE_REVIEWED_TASK_ONLY",
            "executeNow": False,
            "writeNow": False,
            "createTaskNow": False,
            "description": "Run provider, delivery, and full pytest suites after future dependency change.",
        },
        {
            "id": "future_rollback_review",
            "status": "FUTURE_REVIEWED_TASK_ONLY",
            "executeNow": False,
            "writeNow": False,
            "createTaskNow": False,
            "description": "Review rollback evidence before any real SDK dry run can be attempted.",
        },
    ]


def _future_change_envelope() -> dict[str, bool]:
    return {
        "taskCreated": False,
        "dependencyImplementationTaskCreated": False,
        "implementationTicketMaterialized": False,
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
            {"field": "future_reviewed_dependency_file_change_task", "reason": "must_be_separate_reviewed_task"},
            {"field": "implementation_task_creation", "reason": "not_created_by_disabled_plan"},
            {"field": "dependency_manifest_write", "reason": "not_written_by_plan"},
            {"field": "dependency_lockfile_write", "reason": "not_written_by_plan"},
            {"field": "patch_materialization", "reason": "not_materialized_by_plan"},
            {"field": "patch_apply", "reason": "not_executed_by_plan"},
            {"field": "command_execution", "reason": "not_allowed_by_plan"},
            {"field": "real_llm_call", "reason": "not_allowed_after_plan"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_plan"},
            {"field": "network_call", "reason": "not_allowed_by_plan"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_implementation_task_plan",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_implementation_task_plan.py",
        },
        {
            "id": "test_real_sdk_dependency_apply_gate",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_apply_gate.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyImplementationTaskPlanRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖实现任务计划当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency implementation task plan"}],
        )


def build_real_sdk_dependency_implementation_task_plan_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyImplementationTaskPlanRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            apply_gate = build_real_sdk_dependency_apply_gate(request, root=root)
        else:
            apply_gate = None
    except ProviderError:
        apply_gate = None
    if apply_gate is not None:
        context["applyGateReady"] = bool(apply_gate.get("readyForFutureDependencyPatchApplyTask", False))
        context["applyGateSummary"] = _apply_gate_summary(apply_gate)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_implementation_task_plan(
    request: RealSdkDependencyImplementationTaskPlanRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    apply_gate = build_real_sdk_dependency_apply_gate(request, root=root)
    apply_gate_ready = apply_gate.get("readyForFutureDependencyPatchApplyTask") is True
    checklist = _implementation_checklist(request, apply_gate_ready=apply_gate_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "applyGateReady": apply_gate_ready,
        "applyGateSummary": _apply_gate_summary(apply_gate),
        "implementationTaskPlanChecklist": checklist,
        "implementationTaskPlanReady": checklist_passed,
        "readyForReviewedDependencyImplementationTask": checklist_passed,
        "implementationTaskPlan": _implementation_task_plan(),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖实现任务计划已生成；当前不会创建任务、写依赖文件、生成 patch、执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
