"""Disabled real SDK dependency readonly diff review.

This module prepares a local, non-materialized review model for a future real
SDK dependency-file diff. It does not read live dependency files, write review
artifacts, generate patch files, write dependency files, resolve versions,
install SDKs, import SDKs, check secrets, use network access, call real LLMs,
or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_change_approval_package import (
    RealSdkDependencyChangeApprovalPackageRequest,
    build_real_sdk_dependency_change_approval_package,
    describe_real_sdk_dependency_change_approval_package,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_READONLY_DIFF_REVIEW_ID = "real_sdk_dependency_readonly_diff_review"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyReadonlyDiffReviewRequest(RealSdkDependencyChangeApprovalPackageRequest):
    readonly_diff_scope_confirmed: bool = False
    dependency_snapshot_review_confirmed: bool = False
    candidate_dependency_delta_confirmed: bool = False
    rollback_delta_review_confirmed: bool = False
    test_impact_review_confirmed: bool = False
    reviewer_signoff_confirmed: bool = False
    no_diff_review_artifact_write_confirmed: bool = False
    no_patch_generation_confirmed: bool = False
    no_install_or_lock_resolution_confirmed: bool = False
    no_real_call_after_diff_review_confirmed: bool = False


def _base_context(request: RealSdkDependencyReadonlyDiffReviewRequest, *, root: Path) -> dict[str, Any]:
    approval_package_descriptor = describe_real_sdk_dependency_change_approval_package(root=root)
    return {
        **approval_package_descriptor,
        "readonlyDiffReviewId": REAL_SDK_DEPENDENCY_READONLY_DIFF_REVIEW_ID,
        "gateId": REAL_SDK_DEPENDENCY_READONLY_DIFF_REVIEW_ID,
        "upstreamGateId": "real_sdk_dependency_change_approval_package",
        "gateMode": "DEPENDENCY_READONLY_DIFF_REVIEW_DISABLED_ONLY",
        "diffReviewMode": "LOCAL_READONLY_DIFF_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "approvalPackageRequired": True,
        "approvalPackageReady": False,
        "readonlyDiffReviewOnly": True,
        "readonlyDiffReviewReady": False,
        "readyForReadonlyDependencyDiffReview": False,
        "diffReviewArtifactWritten": False,
        "diffGenerated": False,
        "realDiffGenerated": False,
        "dependencyDiffGenerated": False,
        "candidateDiffMaterialized": False,
        "dependencySnapshotReadFromFile": False,
        "dependencySnapshotWritten": False,
        "dependencyFileChangeAuthorized": False,
        "dependencyManifestWriteAuthorized": False,
        "dependencyLockfileWriteAuthorized": False,
        "dependencyVersionResolved": False,
        "dependencyHashResolved": False,
        "patchMaterialized": False,
        "patchFileWritten": False,
        "patchGenerated": False,
        "patchApplyAuthorized": False,
        "commandExecutionAuthorized": False,
        "manualApprovalGranted": False,
        "approvalPackageWritten": False,
        "dependencyChangeApproved": False,
        "dependencyChangeExecutionAuthorized": False,
        "realCallAfterDiffReviewAuthorized": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_readonly_diff_review(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyReadonlyDiffReviewRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresApprovalPackageReady": True,
        "requiresReadonlyDiffScope": True,
        "requiresReviewerSignoff": True,
        "pipeline": [
            "real_sdk_dependency_apply_gate",
            "real_sdk_dependency_implementation_task_plan",
            "real_sdk_dependency_change_approval_package",
            "dependency_readonly_diff_review",
            "future_reviewed_dependency_file_change_task",
            "future_real_llm_dry_run_after_dependency_review",
        ],
    }


def _approval_package_summary(approval_package: dict[str, Any]) -> dict[str, Any]:
    return {
        "approvalPackageId": approval_package["approvalPackageId"],
        "implementationTaskPlanReady": approval_package["implementationTaskPlanReady"],
        "approvalPackageReady": approval_package["approvalPackageReady"],
        "readyForManualDependencyChangeApproval": approval_package["readyForManualDependencyChangeApproval"],
        "manualApprovalGranted": approval_package["manualApprovalGranted"],
        "approvalPackageWritten": approval_package["approvalPackageWritten"],
        "dependencyFileChanged": approval_package["dependencyFileChanged"],
        "secretPresenceChecked": approval_package["secretPresenceChecked"],
        "networkAccess": approval_package["networkAccess"],
        "realLlmCalled": approval_package["realLlmCalled"],
    }


def _readonly_diff_checklist(
    request: RealSdkDependencyReadonlyDiffReviewRequest,
    *,
    approval_package_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "approval_package_ready", "passed": approval_package_ready, "required": True},
        {"id": "readonly_diff_scope_confirmed", "passed": request.readonly_diff_scope_confirmed, "required": True},
        {
            "id": "dependency_snapshot_review_confirmed",
            "passed": request.dependency_snapshot_review_confirmed,
            "required": True,
        },
        {
            "id": "candidate_dependency_delta_confirmed",
            "passed": request.candidate_dependency_delta_confirmed,
            "required": True,
        },
        {
            "id": "rollback_delta_review_confirmed",
            "passed": request.rollback_delta_review_confirmed,
            "required": True,
        },
        {"id": "test_impact_review_confirmed", "passed": request.test_impact_review_confirmed, "required": True},
        {"id": "reviewer_signoff_confirmed", "passed": request.reviewer_signoff_confirmed, "required": True},
        {
            "id": "no_diff_review_artifact_write_confirmed",
            "passed": request.no_diff_review_artifact_write_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_generation_confirmed",
            "passed": request.no_patch_generation_confirmed,
            "required": True,
        },
        {
            "id": "no_install_or_lock_resolution_confirmed",
            "passed": request.no_install_or_lock_resolution_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_diff_review_confirmed",
            "passed": request.no_real_call_after_diff_review_confirmed,
            "required": True,
        },
    ]


def _readonly_diff_review_model(request: RealSdkDependencyReadonlyDiffReviewRequest) -> dict[str, Any]:
    return {
        "reviewId": REAL_SDK_DEPENDENCY_READONLY_DIFF_REVIEW_ID,
        "materializedNow": False,
        "writeNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "candidateDeltaModel": {
            "generatedFromLiveFiles": False,
            "dependencyFileReadNow": False,
            "versionResolvedNow": False,
            "hashResolvedNow": False,
            "packageName": "openai",
            "packageVersion": None,
            "dependencySpec": "future-reviewed-pin-only",
        },
        "targetFiles": [
            {"path": "requirements*.txt", "readNow": False, "writeNow": False, "diffGeneratedNow": False},
            {"path": "pyproject.toml", "readNow": False, "writeNow": False, "diffGeneratedNow": False},
            {"path": "lockfile", "readNow": False, "writeNow": False, "diffGeneratedNow": False},
        ],
        "requiredEvidence": [
            {"id": "approval_package_review", "materializedNow": False},
            {"id": "candidate_dependency_delta", "materializedNow": False},
            {"id": "rollback_delta_review", "materializedNow": False},
            {"id": "test_impact_review", "materializedNow": False},
            {"id": "reviewer_signoff", "materializedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "approvalPackageReady": False,
        "readonlyDiffReviewReady": False,
        "readyForReadonlyDependencyDiffReview": False,
        "diffReviewArtifactWritten": False,
        "diffGenerated": False,
        "realDiffGenerated": False,
        "dependencyDiffGenerated": False,
        "candidateDiffMaterialized": False,
        "dependencySnapshotReadFromFile": False,
        "dependencySnapshotWritten": False,
        "dependencyVersionResolved": False,
        "dependencyHashResolved": False,
        "manualApprovalGranted": False,
        "approvalPackageWritten": False,
        "approvalRecordMaterialized": False,
        "approvalTicketCreated": False,
        "dependencyChangeApproved": False,
        "dependencyChangeExecutionAuthorized": False,
        "taskCreated": False,
        "dependencyImplementationTaskCreated": False,
        "dependencyFileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "lockfileChanged": False,
        "dependencyLockfileChanged": False,
        "patchGenerated": False,
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
        "realCallAfterDiffReviewAuthorized": False,
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
            {"field": "live_dependency_snapshot_read", "reason": "not_read_by_readonly_review"},
            {"field": "diff_review_artifact_write", "reason": "not_written_by_readonly_review"},
            {"field": "candidate_diff_materialization", "reason": "not_materialized_by_readonly_review"},
            {"field": "dependency_manifest_write", "reason": "not_written_by_readonly_review"},
            {"field": "dependency_lockfile_write", "reason": "not_written_by_readonly_review"},
            {"field": "patch_generation", "reason": "not_generated_by_readonly_review"},
            {"field": "dependency_version_resolution", "reason": "not_resolved_by_readonly_review"},
            {"field": "dependency_install", "reason": "not_allowed_by_readonly_review"},
            {"field": "real_llm_call", "reason": "not_allowed_after_readonly_diff_review"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_readonly_review"},
            {"field": "network_call", "reason": "not_allowed_by_readonly_review"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_readonly_diff_review",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_readonly_diff_review.py",
        },
        {
            "id": "test_real_sdk_dependency_change_approval_package",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_change_approval_package.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyReadonlyDiffReviewRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖只读差异审查当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in readonly dependency diff review"}],
        )


def build_real_sdk_dependency_readonly_diff_review_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyReadonlyDiffReviewRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            approval_package = build_real_sdk_dependency_change_approval_package(request, root=root)
        else:
            approval_package = None
    except ProviderError:
        approval_package = None
    if approval_package is not None:
        context["approvalPackageReady"] = bool(approval_package.get("readyForManualDependencyChangeApproval", False))
        context["approvalPackageSummary"] = _approval_package_summary(approval_package)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_readonly_diff_review(
    request: RealSdkDependencyReadonlyDiffReviewRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    approval_package = build_real_sdk_dependency_change_approval_package(request, root=root)
    approval_package_ready = approval_package.get("readyForManualDependencyChangeApproval") is True
    checklist = _readonly_diff_checklist(request, approval_package_ready=approval_package_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "approvalPackageReady": approval_package_ready,
        "approvalPackageSummary": _approval_package_summary(approval_package),
        "readonlyDiffReviewChecklist": checklist,
        "readonlyDiffReviewReady": checklist_passed,
        "readyForReadonlyDependencyDiffReview": checklist_passed,
        "readonlyDiffReviewModel": _readonly_diff_review_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖只读差异审查包已生成；当前不会读取依赖文件、写审查文件、生成 patch、写依赖文件、执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
