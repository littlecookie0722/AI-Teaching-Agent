"""Real SDK dependency install authorization package, disabled.

This module prepares a local authorization package model after the install
execution gate is ready. It does not grant execution authorization, write
dependency files, write patch files, apply patches, materialize or execute
commands, install packages, resolve package metadata, check secrets, use
network access, import SDKs, create clients, call real LLMs, create tasks, or
publish content.
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
)
from .real_sdk_dependency_install_execution_gate import (
    REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_GATE_ID,
    RealSdkDependencyInstallExecutionGateRequest,
    build_real_sdk_dependency_install_execution_gate,
    describe_real_sdk_dependency_install_execution_gate,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_ID = (
    "real_sdk_dependency_install_authorization_package"
)


@dataclass(frozen=True)
class RealSdkDependencyInstallAuthorizationPackageRequest(
    RealSdkDependencyInstallExecutionGateRequest
):
    dependency_install_authorization_scope_confirmed: bool = False
    final_install_approver_confirmed: bool = False
    install_authorization_ticket_confirmed: bool = False
    dependency_install_change_window_confirmed: bool = False
    install_execution_gate_review_confirmed: bool = False
    dependency_manifest_write_policy_confirmed: bool = False
    dependency_lockfile_write_policy_confirmed: bool = False
    package_manager_command_policy_confirmed: bool = False
    rollback_checkpoint_confirmed: bool = False
    post_install_validation_plan_confirmed: bool = False
    no_execution_authorization_during_authorization_package_confirmed: bool = False
    no_dependency_file_write_during_authorization_package_confirmed: bool = False
    no_patch_file_write_during_authorization_package_confirmed: bool = False
    no_patch_apply_during_authorization_package_confirmed: bool = False
    no_command_materialization_during_authorization_package_confirmed: bool = False
    no_command_execution_during_authorization_package_confirmed: bool = False
    no_dependency_install_during_authorization_package_confirmed: bool = False
    no_package_resolution_during_authorization_package_confirmed: bool = False
    no_secret_presence_check_during_authorization_package_confirmed: bool = False
    no_network_during_authorization_package_confirmed: bool = False
    no_real_call_during_authorization_package_confirmed: bool = False


def _base_context(
    request: RealSdkDependencyInstallAuthorizationPackageRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    descriptor = describe_real_sdk_dependency_install_execution_gate(root=root)
    return {
        **descriptor,
        "installAuthorizationPackageId": REAL_SDK_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_ID,
        "gateId": REAL_SDK_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_ID,
        "upstreamGateId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_GATE_ID,
        "gateMode": "DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_DISABLED",
        "authorizationPackageMode": "LOCAL_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_MODEL_ONLY",
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
        "installExecutionGateRequired": True,
        "installExecutionGateModelReady": False,
        "installAuthorizationPackageOnly": True,
        "installAuthorizationPackageModelReady": False,
        "readyForExplicitDependencyInstallExecutionRequest": False,
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


def describe_real_sdk_dependency_install_authorization_package(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealSdkDependencyInstallAuthorizationPackageRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresInstallExecutionGateModelReady": True,
        "requiresSeparateExecutionAuthorization": True,
        "requiresNoAuthorizationDuringPackage": True,
        "pipeline": [
            "real_sdk_dependency_install_execution_gate",
            "dependency_install_authorization_package",
            "future_explicit_dependency_install_execution",
        ],
    }


def _execution_gate_summary(gate: dict[str, Any]) -> dict[str, Any]:
    model = gate.get("installExecutionGateModel") or {}
    return {
        "installExecutionGateId": gate["installExecutionGateId"],
        "installExecutionGateModelReady": gate["installExecutionGateModelReady"],
        "readyForSeparateDependencyInstallExecutionApproval": gate[
            "readyForSeparateDependencyInstallExecutionApproval"
        ],
        "sourceSuggestedChangeCount": model.get("sourceSuggestedChangeCount", 0),
        "dependencyInstallExecutionAuthorized": gate["dependencyInstallExecutionAuthorized"],
        "executionAuthorized": gate["executionAuthorized"],
        "dependencyFileWriteAuthorized": gate["dependencyFileWriteAuthorized"],
        "commandMaterialized": gate["commandMaterialized"],
        "commandExecuted": gate["commandExecuted"],
        "dependencyInstallExecuted": gate["dependencyInstallExecuted"],
        "packageVersionResolved": gate["packageVersionResolved"],
        "secretPresenceChecked": gate["secretPresenceChecked"],
        "networkAccess": gate["networkAccess"],
        "realLlmCalled": gate["realLlmCalled"],
    }


def _authorization_checklist(
    request: RealSdkDependencyInstallAuthorizationPackageRequest,
    *,
    gate_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "install_execution_gate_model_ready", "passed": gate_ready, "required": True},
        {
            "id": "dependency_install_authorization_scope_confirmed",
            "passed": request.dependency_install_authorization_scope_confirmed,
            "required": True,
        },
        {
            "id": "final_install_approver_confirmed",
            "passed": request.final_install_approver_confirmed,
            "required": True,
        },
        {
            "id": "install_authorization_ticket_confirmed",
            "passed": request.install_authorization_ticket_confirmed,
            "required": True,
        },
        {
            "id": "dependency_install_change_window_confirmed",
            "passed": request.dependency_install_change_window_confirmed,
            "required": True,
        },
        {
            "id": "install_execution_gate_review_confirmed",
            "passed": request.install_execution_gate_review_confirmed,
            "required": True,
        },
        {
            "id": "dependency_manifest_write_policy_confirmed",
            "passed": request.dependency_manifest_write_policy_confirmed,
            "required": True,
        },
        {
            "id": "dependency_lockfile_write_policy_confirmed",
            "passed": request.dependency_lockfile_write_policy_confirmed,
            "required": True,
        },
        {
            "id": "package_manager_command_policy_confirmed",
            "passed": request.package_manager_command_policy_confirmed,
            "required": True,
        },
        {
            "id": "rollback_checkpoint_confirmed",
            "passed": request.rollback_checkpoint_confirmed,
            "required": True,
        },
        {
            "id": "post_install_validation_plan_confirmed",
            "passed": request.post_install_validation_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_execution_authorization_during_authorization_package_confirmed",
            "passed": request.no_execution_authorization_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_write_during_authorization_package_confirmed",
            "passed": request.no_dependency_file_write_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_file_write_during_authorization_package_confirmed",
            "passed": request.no_patch_file_write_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_apply_during_authorization_package_confirmed",
            "passed": request.no_patch_apply_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_command_materialization_during_authorization_package_confirmed",
            "passed": request.no_command_materialization_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_during_authorization_package_confirmed",
            "passed": request.no_command_execution_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_during_authorization_package_confirmed",
            "passed": request.no_dependency_install_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_package_resolution_during_authorization_package_confirmed",
            "passed": request.no_package_resolution_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_presence_check_during_authorization_package_confirmed",
            "passed": request.no_secret_presence_check_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_network_during_authorization_package_confirmed",
            "passed": request.no_network_during_authorization_package_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_during_authorization_package_confirmed",
            "passed": request.no_real_call_during_authorization_package_confirmed,
            "required": True,
        },
    ]


def _authorization_package_model(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "authorizationPackageId": REAL_SDK_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_ID,
        "authorizationPackageOnly": True,
        "targetPackage": TARGET_PACKAGE,
        "recommendedSpecifier": RECOMMENDED_SPECIFIER,
        "sourceGateId": gate["installExecutionGateId"],
        "sourceGateReady": gate["installExecutionGateModelReady"],
        "authorizationGrantedNow": False,
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
        "explicitFutureAuthorizationRequired": True,
        "authorizationEvidence": {
            "approverIdentityRequired": True,
            "changeTicketRequired": True,
            "changeWindowRequired": True,
            "rollbackCheckpointRequired": True,
            "postInstallValidationRequired": True,
            "secretPresenceCheckDeferred": True,
            "networkPackageInstallDeferred": True,
        },
        "blockedActions": [
            {"id": "grant_dependency_install_execution_authorization", "allowedNow": False},
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
            {"field": "execution_authorization", "reason": "not_granted_by_authorization_package"},
            {"field": "dependency_file_write", "reason": "not_written_by_authorization_package"},
            {"field": "patch_file_write", "reason": "not_written_by_authorization_package"},
            {"field": "patch_apply", "reason": "not_applied_by_authorization_package"},
            {"field": "command_materialization", "reason": "not_materialized_by_authorization_package"},
            {"field": "command_execution", "reason": "not_executed_by_authorization_package"},
            {"field": "dependency_install", "reason": "not_installed_by_authorization_package"},
            {"field": "package_resolution", "reason": "not_resolved_by_authorization_package"},
            {"field": "secret_presence_check", "reason": "not_checked_by_authorization_package"},
            {"field": "network_call", "reason": "not_allowed_by_authorization_package"},
            {"field": "real_llm_call", "reason": "not_allowed_by_authorization_package"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_install_authorization_package",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_authorization_package.py",
        },
        {
            "id": "test_real_sdk_dependency_install_execution_gate",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_SDK_INSTALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyInstallAuthorizationPackageRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 install authorization package 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency install authorization package"}],
        )


def build_real_sdk_dependency_install_authorization_package_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyInstallAuthorizationPackageRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        gate = build_real_sdk_dependency_install_execution_gate(request, root=root)
    except ProviderError:
        gate = None
    if gate is not None:
        context["installExecutionGateModelReady"] = bool(gate.get("installExecutionGateModelReady", False))
        context["installExecutionGateSummary"] = _execution_gate_summary(gate)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_install_authorization_package(
    request: RealSdkDependencyInstallAuthorizationPackageRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    gate = build_real_sdk_dependency_install_execution_gate(request, root=root)
    gate_ready = gate.get("installExecutionGateModelReady") is True
    checklist = _authorization_checklist(request, gate_ready=gate_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "installExecutionGateModelReady": gate_ready,
        "installExecutionGateSummary": _execution_gate_summary(gate),
        "installAuthorizationChecklist": checklist,
        "installAuthorizationChecklistPassed": checklist_passed,
        "installAuthorizationPackageModelReady": checklist_passed,
        "readyForExplicitDependencyInstallExecutionRequest": checklist_passed,
        "installAuthorizationPackageModel": _authorization_package_model(gate) if checklist_passed else None,
        "futureExecutionEnvelope": _future_execution_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 install authorization package 已生成授权包模型；当前不会授权执行、写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。",
    }
