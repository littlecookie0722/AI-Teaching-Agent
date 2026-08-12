"""Real SDK dependency install execution gate, disabled.

This module evaluates whether the reviewed install change proposal is ready for
a future, separately authorized SDK dependency installation step. It does not
write dependency files, write patch files, apply patches, materialize or execute
commands, install packages, resolve package metadata, check secrets, use network
access, import SDKs, create clients, call real LLMs, create tasks, or publish
content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_install_change_proposal import (
    RECOMMENDED_SPECIFIER,
    SUPPORTED_PROVIDER,
    TARGET_PACKAGE,
    RealSdkDependencyInstallChangeProposalRequest,
    build_real_sdk_dependency_install_change_proposal,
    describe_real_sdk_dependency_install_change_proposal,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_GATE_ID = "real_sdk_dependency_install_execution_gate"


@dataclass(frozen=True)
class RealSdkDependencyInstallExecutionGateRequest(
    RealSdkDependencyInstallChangeProposalRequest
):
    dependency_install_execution_scope_confirmed: bool = False
    install_execution_approver_confirmed: bool = False
    install_execution_ticket_confirmed: bool = False
    install_execution_change_window_confirmed: bool = False
    install_change_proposal_review_confirmed: bool = False
    dependency_manifest_target_confirmed: bool = False
    lockfile_update_policy_confirmed: bool = False
    package_manager_policy_confirmed: bool = False
    install_execution_rollback_checkpoint_confirmed: bool = False
    post_install_validation_plan_confirmed: bool = False
    no_dependency_file_write_during_execution_gate_confirmed: bool = False
    no_patch_file_write_during_execution_gate_confirmed: bool = False
    no_patch_apply_during_execution_gate_confirmed: bool = False
    no_command_materialization_during_execution_gate_confirmed: bool = False
    no_command_execution_during_execution_gate_confirmed: bool = False
    no_dependency_install_during_execution_gate_confirmed: bool = False
    no_package_resolution_during_execution_gate_confirmed: bool = False
    no_secret_presence_check_during_execution_gate_confirmed: bool = False
    no_network_during_execution_gate_confirmed: bool = False
    no_real_call_during_execution_gate_confirmed: bool = False


def _base_context(
    request: RealSdkDependencyInstallExecutionGateRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    descriptor = describe_real_sdk_dependency_install_change_proposal(root=root)
    return {
        **descriptor,
        "installExecutionGateId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_GATE_ID,
        "gateId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_GATE_ID,
        "upstreamGateId": "real_sdk_dependency_install_change_proposal",
        "gateMode": "DEPENDENCY_INSTALL_EXECUTION_GATE_DISABLED",
        "executionGateMode": "LOCAL_DEPENDENCY_INSTALL_EXECUTION_GATE_MODEL_ONLY",
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
        "installChangeProposalRequired": True,
        "installChangeProposalModelReady": False,
        "installExecutionGateOnly": True,
        "installExecutionGateModelReady": False,
        "readyForSeparateDependencyInstallExecutionApproval": False,
        "dependencyInstallExecutionAuthorized": False,
        "executionAuthorized": False,
        "dependencyFileWriteAuthorized": False,
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
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_install_execution_gate(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyInstallExecutionGateRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresInstallChangeProposalModelReady": True,
        "requiresSeparateExecutionAuthorization": True,
        "requiresNoExecutionDuringGate": True,
        "pipeline": [
            "real_sdk_dependency_install_change_proposal",
            "dependency_install_execution_gate",
            "future_explicit_dependency_install_execution",
        ],
    }


def _proposal_summary(proposal: dict[str, Any]) -> dict[str, Any]:
    model = proposal.get("installChangeProposalModel") or {}
    preview = model.get("nonExecutablePatchPreview") or {}
    return {
        "installChangeProposalId": proposal["installChangeProposalId"],
        "installChangeProposalModelReady": proposal["installChangeProposalModelReady"],
        "readyForDependencyInstallPatchReview": proposal["readyForDependencyInstallPatchReview"],
        "nonExecutablePatchPreviewGenerated": proposal["nonExecutablePatchPreviewGenerated"],
        "suggestedChangeCount": len(model.get("suggestedChanges") or []),
        "nonExecutablePatchPreviewLineCount": len(preview.get("lines") or []),
        "dependencyFileChanged": proposal["dependencyFileChanged"],
        "patchGenerated": proposal["patchGenerated"],
        "patchFileWritten": proposal["patchFileWritten"],
        "patchApplied": proposal["patchApplied"],
        "commandMaterialized": proposal["commandMaterialized"],
        "commandExecuted": proposal["commandExecuted"],
        "dependencyInstallExecuted": proposal["dependencyInstallExecuted"],
        "packageVersionResolved": proposal["packageVersionResolved"],
        "secretPresenceChecked": proposal["secretPresenceChecked"],
        "networkAccess": proposal["networkAccess"],
        "realLlmCalled": proposal["realLlmCalled"],
    }


def _execution_gate_checklist(
    request: RealSdkDependencyInstallExecutionGateRequest,
    *,
    proposal_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "install_change_proposal_model_ready", "passed": proposal_ready, "required": True},
        {
            "id": "dependency_install_execution_scope_confirmed",
            "passed": request.dependency_install_execution_scope_confirmed,
            "required": True,
        },
        {
            "id": "install_execution_approver_confirmed",
            "passed": request.install_execution_approver_confirmed,
            "required": True,
        },
        {
            "id": "install_execution_ticket_confirmed",
            "passed": request.install_execution_ticket_confirmed,
            "required": True,
        },
        {
            "id": "install_execution_change_window_confirmed",
            "passed": request.install_execution_change_window_confirmed,
            "required": True,
        },
        {
            "id": "install_change_proposal_review_confirmed",
            "passed": request.install_change_proposal_review_confirmed,
            "required": True,
        },
        {
            "id": "dependency_manifest_target_confirmed",
            "passed": request.dependency_manifest_target_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_update_policy_confirmed",
            "passed": request.lockfile_update_policy_confirmed,
            "required": True,
        },
        {
            "id": "package_manager_policy_confirmed",
            "passed": request.package_manager_policy_confirmed,
            "required": True,
        },
        {
            "id": "install_execution_rollback_checkpoint_confirmed",
            "passed": request.install_execution_rollback_checkpoint_confirmed,
            "required": True,
        },
        {
            "id": "post_install_validation_plan_confirmed",
            "passed": request.post_install_validation_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_write_during_execution_gate_confirmed",
            "passed": request.no_dependency_file_write_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_file_write_during_execution_gate_confirmed",
            "passed": request.no_patch_file_write_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_apply_during_execution_gate_confirmed",
            "passed": request.no_patch_apply_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_command_materialization_during_execution_gate_confirmed",
            "passed": request.no_command_materialization_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_during_execution_gate_confirmed",
            "passed": request.no_command_execution_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_during_execution_gate_confirmed",
            "passed": request.no_dependency_install_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_package_resolution_during_execution_gate_confirmed",
            "passed": request.no_package_resolution_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_presence_check_during_execution_gate_confirmed",
            "passed": request.no_secret_presence_check_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_network_during_execution_gate_confirmed",
            "passed": request.no_network_during_execution_gate_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_during_execution_gate_confirmed",
            "passed": request.no_real_call_during_execution_gate_confirmed,
            "required": True,
        },
    ]


def _install_execution_gate_model(proposal: dict[str, Any]) -> dict[str, Any]:
    proposal_model = proposal.get("installChangeProposalModel") or {}
    suggested_changes = proposal_model.get("suggestedChanges") or []
    return {
        "gateModelId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_GATE_ID,
        "gateOnly": True,
        "targetPackage": TARGET_PACKAGE,
        "recommendedSpecifier": RECOMMENDED_SPECIFIER,
        "sourceProposalId": proposal_model.get("proposalId"),
        "sourceSuggestedChangeCount": len(suggested_changes),
        "executionAuthorizationNow": False,
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
        "separateExecutionRequirements": [
            "User must explicitly authorize dependency file mutation in a later step.",
            "User must explicitly authorize command materialization in a later step.",
            "User must explicitly authorize network package installation in a later step.",
            "Post-install tests must run after any future dependency mutation.",
        ],
        "nonExecutableExecutionPlan": [
            {
                "id": "review_target_manifest",
                "writeNow": False,
                "executeNow": False,
                "description": "Review the selected dependency manifest and lockfile policy.",
            },
            {
                "id": "future_dependency_update",
                "writeNow": False,
                "executeNow": False,
                "description": "In a separate approved step, update the dependency manifest if authorized.",
            },
            {
                "id": "future_install_validation",
                "writeNow": False,
                "executeNow": False,
                "description": "In a separate approved step, run install and validation commands if authorized.",
            },
        ],
        "blockedActions": [
            {"id": "authorize_execution_now", "allowedNow": False},
            {"id": "write_dependency_manifest", "allowedNow": False},
            {"id": "write_dependency_lockfile", "allowedNow": False},
            {"id": "write_patch_file", "allowedNow": False},
            {"id": "apply_patch", "allowedNow": False},
            {"id": "materialize_install_command", "allowedNow": False},
            {"id": "execute_command", "allowedNow": False},
            {"id": "install_sdk_dependency", "allowedNow": False},
            {"id": "resolve_package_version", "allowedNow": False},
            {"id": "download_package", "allowedNow": False},
            {"id": "check_secret_presence", "allowedNow": False},
            {"id": "network_call", "allowedNow": False},
            {"id": "real_llm_call", "allowedNow": False},
        ],
    }


def _future_execution_envelope() -> dict[str, bool]:
    return {
        "dependencyInstallExecutionAuthorized": False,
        "executionAuthorized": False,
        "dependencyFileWriteAuthorized": False,
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
            {"field": "future_dependency_install_execution", "reason": "must_be_separate_explicit_step"},
            {"field": "execution_authorization", "reason": "not_granted_by_execution_gate"},
            {"field": "dependency_file_write", "reason": "not_written_by_execution_gate"},
            {"field": "patch_file_write", "reason": "not_written_by_execution_gate"},
            {"field": "patch_apply", "reason": "not_applied_by_execution_gate"},
            {"field": "command_materialization", "reason": "not_materialized_by_execution_gate"},
            {"field": "command_execution", "reason": "not_executed_by_execution_gate"},
            {"field": "dependency_install", "reason": "not_installed_by_execution_gate"},
            {"field": "package_resolution", "reason": "not_resolved_by_execution_gate"},
            {"field": "secret_presence_check", "reason": "not_checked_by_execution_gate"},
            {"field": "network_call", "reason": "not_allowed_by_execution_gate"},
            {"field": "real_llm_call", "reason": "not_allowed_by_execution_gate"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_install_execution_gate",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py",
        },
        {
            "id": "test_real_sdk_dependency_install_change_proposal",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_SDK_INSTALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyInstallExecutionGateRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 install execution gate 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency install execution gate"}],
        )


def build_real_sdk_dependency_install_execution_gate_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyInstallExecutionGateRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        proposal = build_real_sdk_dependency_install_change_proposal(request, root=root)
    except ProviderError:
        proposal = None
    if proposal is not None:
        context["installChangeProposalModelReady"] = bool(proposal.get("installChangeProposalModelReady", False))
        context["installChangeProposalSummary"] = _proposal_summary(proposal)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_install_execution_gate(
    request: RealSdkDependencyInstallExecutionGateRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    proposal = build_real_sdk_dependency_install_change_proposal(request, root=root)
    proposal_ready = proposal.get("installChangeProposalModelReady") is True
    checklist = _execution_gate_checklist(request, proposal_ready=proposal_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "installChangeProposalModelReady": proposal_ready,
        "installChangeProposalSummary": _proposal_summary(proposal),
        "installExecutionGateChecklist": checklist,
        "installExecutionGateChecklistPassed": checklist_passed,
        "installExecutionGateModelReady": checklist_passed,
        "readyForSeparateDependencyInstallExecutionApproval": checklist_passed,
        "installExecutionGateModel": _install_execution_gate_model(proposal) if checklist_passed else None,
        "futureExecutionEnvelope": _future_execution_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 install execution gate 已生成门禁模型；当前不会授权执行、写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。",
    }
