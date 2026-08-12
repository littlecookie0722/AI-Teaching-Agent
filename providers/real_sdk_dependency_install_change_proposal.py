"""Real SDK dependency install change proposal, plan-only.

This module turns the reviewed readonly dependency content preview into a
reviewable install change proposal. It does not write dependency files, write
patch files, apply patches, materialize or execute commands, install packages,
resolve package metadata, import SDKs, check secrets, use network access, call
real LLMs, create tasks, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_content_read_readonly_execution import (
    RealSdkDependencyContentReadReadonlyExecutionRequest,
    build_real_sdk_dependency_content_read_readonly_execution,
    describe_real_sdk_dependency_content_read_readonly_execution,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_INSTALL_CHANGE_PROPOSAL_ID = "real_sdk_dependency_install_change_proposal"
SUPPORTED_PROVIDER = "openai"
TARGET_PACKAGE = "openai"
RECOMMENDED_SPECIFIER = "openai>=1.0.0,<2.0.0"


@dataclass(frozen=True)
class RealSdkDependencyInstallChangeProposalRequest(
    RealSdkDependencyContentReadReadonlyExecutionRequest
):
    install_change_proposal_scope_confirmed: bool = False
    install_change_approver_confirmed: bool = False
    install_change_ticket_confirmed: bool = False
    readonly_content_review_confirmed: bool = False
    target_manifest_change_confirmed: bool = False
    target_lockfile_policy_confirmed: bool = False
    openai_package_requirement_confirmed: bool = False
    version_pin_policy_confirmed: bool = False
    rollback_plan_confirmed: bool = False
    no_dependency_file_write_during_proposal_confirmed: bool = False
    no_patch_file_write_during_proposal_confirmed: bool = False
    no_patch_apply_during_proposal_confirmed: bool = False
    no_command_materialization_during_proposal_confirmed: bool = False
    no_command_execution_during_proposal_confirmed: bool = False
    no_dependency_install_during_proposal_confirmed: bool = False
    no_package_resolution_during_proposal_confirmed: bool = False
    no_secret_presence_check_during_proposal_confirmed: bool = False
    no_network_during_proposal_confirmed: bool = False
    no_real_call_during_proposal_confirmed: bool = False


def _base_context(
    request: RealSdkDependencyInstallChangeProposalRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    descriptor = describe_real_sdk_dependency_content_read_readonly_execution(root=ROOT)
    return {
        **descriptor,
        "installChangeProposalId": REAL_SDK_DEPENDENCY_INSTALL_CHANGE_PROPOSAL_ID,
        "gateId": REAL_SDK_DEPENDENCY_INSTALL_CHANGE_PROPOSAL_ID,
        "upstreamGateId": "real_sdk_dependency_content_read_readonly_execution",
        "gateMode": "DEPENDENCY_INSTALL_CHANGE_PROPOSAL_PLAN_ONLY",
        "proposalMode": "LOCAL_INSTALL_CHANGE_PROPOSAL_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetPackage": TARGET_PACKAGE,
        "recommendedSpecifier": RECOMMENDED_SPECIFIER,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "contentReadReadonlyExecutionRequired": True,
        "contentReadReadonlyExecutionModelReady": False,
        "installChangeProposalOnly": True,
        "installChangeProposalModelReady": False,
        "readyForDependencyInstallPatchReview": False,
        "dependencyInstallPatchPlanGenerated": False,
        "nonExecutablePatchPreviewGenerated": False,
        "dependencyFileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "lockfileChanged": False,
        "dependencyLockfileChanged": False,
        "dependencyPatchGenerated": False,
        "patchGenerated": False,
        "patchMaterialized": False,
        "patchFileWritten": False,
        "patchApplied": False,
        "commandMaterialized": False,
        "installCommandMaterialized": False,
        "commandExecuted": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_install_change_proposal(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyInstallChangeProposalRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresContentReadReadonlyExecutionModelReady": True,
        "requiresReadonlyContentReview": True,
        "requiresDependencyInstallPatchPlanReview": True,
        "requiresNoDependencyFileWrite": True,
        "requiresNoPatchFileWrite": True,
        "requiresNoCommandMaterialization": True,
        "pipeline": [
            "real_sdk_dependency_content_read_readonly_execution",
            "dependency_install_change_proposal",
            "future_reviewed_dependency_install_execution",
        ],
    }


def _readonly_execution_summary(execution: dict[str, Any]) -> dict[str, Any]:
    model = execution.get("contentReadReadonlyExecutionModel", {})
    summary = model.get("summary", {})
    return {
        "contentReadReadonlyExecutionId": execution["contentReadReadonlyExecutionId"],
        "contentReadReadonlyExecutionModelReady": execution["contentReadReadonlyExecutionModelReady"],
        "dependencyContentReadExecuted": execution["dependencyContentReadExecuted"],
        "dependencyManifestContentRead": execution["dependencyManifestContentRead"],
        "dependencyLockfileContentRead": execution["dependencyLockfileContentRead"],
        "redactedDependencyContentPreviewReturned": execution["redactedDependencyContentPreviewReturned"],
        "filesRead": summary.get("filesRead", 0),
        "dependencyContentReturned": execution["dependencyContentReturned"],
        "rawDependencyContentReturned": execution["rawDependencyContentReturned"],
        "dependencyContentPersisted": execution["dependencyContentPersisted"],
        "patchGenerated": execution["patchGenerated"],
        "commandExecuted": execution["commandExecuted"],
        "dependencyInstallExecuted": execution["dependencyInstallExecuted"],
        "secretPresenceChecked": execution["secretPresenceChecked"],
        "networkAccess": execution["networkAccess"],
        "realLlmCalled": execution["realLlmCalled"],
    }


def _install_change_checklist(
    request: RealSdkDependencyInstallChangeProposalRequest,
    *,
    readonly_execution_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "content_read_readonly_execution_model_ready", "passed": readonly_execution_ready, "required": True},
        {
            "id": "install_change_proposal_scope_confirmed",
            "passed": request.install_change_proposal_scope_confirmed,
            "required": True,
        },
        {
            "id": "install_change_approver_confirmed",
            "passed": request.install_change_approver_confirmed,
            "required": True,
        },
        {
            "id": "install_change_ticket_confirmed",
            "passed": request.install_change_ticket_confirmed,
            "required": True,
        },
        {
            "id": "readonly_content_review_confirmed",
            "passed": request.readonly_content_review_confirmed,
            "required": True,
        },
        {
            "id": "target_manifest_change_confirmed",
            "passed": request.target_manifest_change_confirmed,
            "required": True,
        },
        {
            "id": "target_lockfile_policy_confirmed",
            "passed": request.target_lockfile_policy_confirmed,
            "required": True,
        },
        {
            "id": "openai_package_requirement_confirmed",
            "passed": request.openai_package_requirement_confirmed,
            "required": True,
        },
        {
            "id": "version_pin_policy_confirmed",
            "passed": request.version_pin_policy_confirmed,
            "required": True,
        },
        {"id": "rollback_plan_confirmed", "passed": request.rollback_plan_confirmed, "required": True},
        {
            "id": "no_dependency_file_write_during_proposal_confirmed",
            "passed": request.no_dependency_file_write_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_file_write_during_proposal_confirmed",
            "passed": request.no_patch_file_write_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_apply_during_proposal_confirmed",
            "passed": request.no_patch_apply_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_command_materialization_during_proposal_confirmed",
            "passed": request.no_command_materialization_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_during_proposal_confirmed",
            "passed": request.no_command_execution_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_during_proposal_confirmed",
            "passed": request.no_dependency_install_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_package_resolution_during_proposal_confirmed",
            "passed": request.no_package_resolution_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_presence_check_during_proposal_confirmed",
            "passed": request.no_secret_presence_check_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_network_during_proposal_confirmed",
            "passed": request.no_network_during_proposal_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_during_proposal_confirmed",
            "passed": request.no_real_call_during_proposal_confirmed,
            "required": True,
        },
    ]


def _validate_provider_scope(request: RealSdkDependencyInstallChangeProposalRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 install change proposal 当前只允许 OpenAI 单 Provider 范围",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed in dependency install change proposal",
                }
            ],
        )


def _files_from_readonly_execution(execution: dict[str, Any]) -> list[dict[str, Any]]:
    model = execution.get("contentReadReadonlyExecutionModel", {})
    files = model.get("files", [])
    if not isinstance(files, list):
        return []
    return [item for item in files if isinstance(item, dict)]


def _package_mentioned(file_model: dict[str, Any]) -> bool:
    return TARGET_PACKAGE in file_model.get("packageMentions", [])


def _manifest_suggested_changes(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for file_model in files:
        if file_model.get("kind") != "manifest":
            continue
        path = file_model.get("relativePath")
        if path == "requirements.txt":
            changes.append(
                {
                    "id": "requirements_txt_openai_requirement",
                    "targetPath": path,
                    "action": "review_requirement_entry"
                    if _package_mentioned(file_model)
                    else "add_requirement_entry",
                    "package": TARGET_PACKAGE,
                    "recommendedSpecifier": RECOMMENDED_SPECIFIER,
                    "packageAlreadyMentionedInRedactedPreview": _package_mentioned(file_model),
                    "writeNow": False,
                    "reason": "Future reviewed install execution should ensure a reviewed OpenAI SDK requirement.",
                }
            )
        elif path == "pyproject.toml":
            changes.append(
                {
                    "id": "pyproject_openai_dependency",
                    "targetPath": path,
                    "action": "review_project_dependency_entry",
                    "package": TARGET_PACKAGE,
                    "recommendedSpecifier": RECOMMENDED_SPECIFIER,
                    "packageAlreadyMentionedInRedactedPreview": _package_mentioned(file_model),
                    "writeNow": False,
                    "reason": "Future reviewed install execution may update project dependency metadata.",
                }
            )
    if not changes:
        changes.append(
            {
                "id": "manual_manifest_selection_required",
                "targetPath": None,
                "action": "manual_review_required",
                "package": TARGET_PACKAGE,
                "recommendedSpecifier": RECOMMENDED_SPECIFIER,
                "writeNow": False,
                "reason": "No allowlisted dependency manifest was read; select a manifest in a separate review.",
            }
        )
    return changes


def _non_executable_patch_preview(files: list[dict[str, Any]]) -> list[str]:
    requirement_seen = any(file_model.get("relativePath") == "requirements.txt" for file_model in files)
    if requirement_seen:
        return [
            "--- requirements.txt",
            "+++ requirements.txt",
            "@@ future reviewed change preview only @@",
            f"+{RECOMMENDED_SPECIFIER}",
        ]
    return [
        "--- <reviewed dependency manifest>",
        "+++ <reviewed dependency manifest>",
        "@@ future reviewed change preview only @@",
        f"+{RECOMMENDED_SPECIFIER}",
    ]


def _install_change_proposal_model(files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "proposalId": REAL_SDK_DEPENDENCY_INSTALL_CHANGE_PROPOSAL_ID,
        "proposalOnly": True,
        "targetPackage": TARGET_PACKAGE,
        "recommendedSpecifier": RECOMMENDED_SPECIFIER,
        "dependencyFileWriteNow": False,
        "patchFileWriteNow": False,
        "patchApplyNow": False,
        "commandMaterializeNow": False,
        "commandExecuteNow": False,
        "installNow": False,
        "packageResolveNow": False,
        "secretCheckNow": False,
        "networkNow": False,
        "realCallNow": False,
        "suggestedChanges": _manifest_suggested_changes(files),
        "nonExecutablePatchPreview": {
            "generated": True,
            "materialized": False,
            "writeNow": False,
            "applyNow": False,
            "lines": _non_executable_patch_preview(files),
        },
        "installValidationPlan": [
            "Review dependency manifest target and version policy.",
            "Review lockfile regeneration policy in a separate task.",
            "Only after explicit approval, execute installation in a separate controlled step.",
        ],
        "blockedActions": [
            {"id": "write_dependency_manifest", "allowedNow": False},
            {"id": "write_dependency_lockfile", "allowedNow": False},
            {"id": "write_patch_file", "allowedNow": False},
            {"id": "apply_patch", "allowedNow": False},
            {"id": "materialize_install_command", "allowedNow": False},
            {"id": "execute_command", "allowedNow": False},
            {"id": "install_sdk_dependency", "allowedNow": False},
            {"id": "resolve_package_version", "allowedNow": False},
            {"id": "download_package", "allowedNow": False},
            {"id": "import_real_sdk", "allowedNow": False},
            {"id": "create_real_client", "allowedNow": False},
            {"id": "check_secret_presence", "allowedNow": False},
            {"id": "network_call", "allowedNow": False},
            {"id": "real_llm_call", "allowedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "dependencyInstallPatchPlanGenerated": False,
        "dependencyFileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "lockfileChanged": False,
        "dependencyLockfileChanged": False,
        "dependencyPatchGenerated": False,
        "patchGenerated": False,
        "patchMaterialized": False,
        "patchFileWritten": False,
        "patchApplied": False,
        "commandMaterialized": False,
        "installCommandMaterialized": False,
        "commandExecuted": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
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
            {"field": "future_dependency_install_execution", "reason": "must_be_separate_reviewed_step"},
            {"field": "dependency_file_write", "reason": "not_written_by_proposal"},
            {"field": "patch_file_write", "reason": "not_written_by_proposal"},
            {"field": "patch_apply", "reason": "not_applied_by_proposal"},
            {"field": "command_materialization", "reason": "not_materialized_by_proposal"},
            {"field": "command_execution", "reason": "not_executed_by_proposal"},
            {"field": "dependency_install", "reason": "not_installed_by_proposal"},
            {"field": "package_resolution", "reason": "not_resolved_by_proposal"},
            {"field": "secret_presence_check", "reason": "not_checked_by_proposal"},
            {"field": "network_call", "reason": "not_allowed_by_proposal"},
            {"field": "real_llm_call", "reason": "not_allowed_by_proposal"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_install_change_proposal",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py",
        },
        {
            "id": "test_real_sdk_dependency_content_read_readonly_execution",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_readonly_execution.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_SDK_INSTALL", "command": "python -m pytest"},
    ]


def build_real_sdk_dependency_install_change_proposal_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyInstallChangeProposalRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        readonly_execution = build_real_sdk_dependency_content_read_readonly_execution(request, root=root)
    except ProviderError:
        readonly_execution = None
    if readonly_execution is not None:
        context["contentReadReadonlyExecutionModelReady"] = bool(
            readonly_execution.get("contentReadReadonlyExecutionModelReady", False)
        )
        context["readonlyExecutionSummary"] = _readonly_execution_summary(readonly_execution)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_install_change_proposal(
    request: RealSdkDependencyInstallChangeProposalRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    readonly_execution = build_real_sdk_dependency_content_read_readonly_execution(request, root=root)
    readonly_execution_ready = readonly_execution.get("contentReadReadonlyExecutionModelReady") is True
    files = _files_from_readonly_execution(readonly_execution) if readonly_execution_ready else []
    checklist = _install_change_checklist(request, readonly_execution_ready=readonly_execution_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "contentReadReadonlyExecutionModelReady": readonly_execution_ready,
        "readonlyExecutionSummary": _readonly_execution_summary(readonly_execution),
        "installChangeChecklist": checklist,
        "installChangeChecklistPassed": checklist_passed,
        "installChangeProposalModelReady": checklist_passed,
        "readyForDependencyInstallPatchReview": checklist_passed,
        "dependencyInstallPatchPlanGenerated": False,
        "nonExecutablePatchPreviewGenerated": checklist_passed,
        "installChangeProposalModel": _install_change_proposal_model(files) if checklist_passed else None,
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 install change proposal 已生成计划模型；当前不会写依赖文件、写 patch 文件、应用 patch、物化或执行命令、安装依赖、解析包、读取密钥、联网或真实调用。",
    }
