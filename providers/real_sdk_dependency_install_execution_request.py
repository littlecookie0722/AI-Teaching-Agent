"""Real SDK dependency install execution request, disabled.

This module prepares a local execution request model after the install
authorization package is ready. It does not grant execution authorization,
write dependency files, write patch files, apply patches, materialize or
execute commands, install packages, resolve package metadata, check secrets,
use network access, import SDKs, create clients, call real LLMs, create tasks,
or publish content.
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
from .real_sdk_dependency_install_authorization_package import (
    REAL_SDK_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_ID,
    RealSdkDependencyInstallAuthorizationPackageRequest,
    build_real_sdk_dependency_install_authorization_package,
    describe_real_sdk_dependency_install_authorization_package,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_REQUEST_ID = (
    "real_sdk_dependency_install_execution_request"
)


@dataclass(frozen=True)
class RealSdkDependencyInstallExecutionRequestRequest(
    RealSdkDependencyInstallAuthorizationPackageRequest
):
    dependency_install_execution_request_scope_confirmed: bool = False
    execution_request_approver_confirmed: bool = False
    execution_request_ticket_confirmed: bool = False
    execution_request_change_window_confirmed: bool = False
    install_authorization_package_review_confirmed: bool = False
    dependency_manifest_write_target_confirmed: bool = False
    dependency_lockfile_write_target_confirmed: bool = False
    package_manager_execution_policy_confirmed: bool = False
    execution_request_rollback_checkpoint_confirmed: bool = False
    execution_request_post_install_validation_confirmed: bool = False
    no_execution_authorization_during_execution_request_confirmed: bool = False
    no_dependency_file_write_during_execution_request_confirmed: bool = False
    no_patch_file_write_during_execution_request_confirmed: bool = False
    no_patch_apply_during_execution_request_confirmed: bool = False
    no_command_materialization_during_execution_request_confirmed: bool = False
    no_command_execution_during_execution_request_confirmed: bool = False
    no_dependency_install_during_execution_request_confirmed: bool = False
    no_package_resolution_during_execution_request_confirmed: bool = False
    no_secret_presence_check_during_execution_request_confirmed: bool = False
    no_network_during_execution_request_confirmed: bool = False
    no_real_call_during_execution_request_confirmed: bool = False


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


def _base_context(
    request: RealSdkDependencyInstallExecutionRequestRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    descriptor = describe_real_sdk_dependency_install_authorization_package(root=root)
    return {
        **descriptor,
        "installExecutionRequestId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_REQUEST_ID,
        "gateId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_REQUEST_ID,
        "upstreamGateId": REAL_SDK_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_ID,
        "gateMode": "DEPENDENCY_INSTALL_EXECUTION_REQUEST_DISABLED",
        "executionRequestMode": "LOCAL_DEPENDENCY_INSTALL_EXECUTION_REQUEST_MODEL_ONLY",
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
        "installAuthorizationPackageRequired": True,
        "installAuthorizationPackageModelReady": False,
        "installExecutionRequestOnly": True,
        "installExecutionRequestModelReady": False,
        "readyForExplicitDependencyInstallExecutorImplementation": False,
        "requiresInstallAuthorizationPackageModelReady": True,
        "requiresSeparateExecutorImplementation": True,
        "requiresNoExecutionDuringRequest": True,
        **_future_execution_envelope(),
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_install_execution_request(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealSdkDependencyInstallExecutionRequestRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "pipeline": [
            "real_sdk_dependency_install_execution_gate",
            "dependency_install_authorization_package",
            "dependency_install_execution_request",
            "future_explicit_dependency_install_executor",
        ],
    }


def _authorization_package_summary(package: dict[str, Any]) -> dict[str, Any]:
    model = package.get("installAuthorizationPackageModel") or {}
    return {
        "installAuthorizationPackageId": package["installAuthorizationPackageId"],
        "installAuthorizationPackageModelReady": package["installAuthorizationPackageModelReady"],
        "readyForExplicitDependencyInstallExecutionRequest": package[
            "readyForExplicitDependencyInstallExecutionRequest"
        ],
        "sourceGateReady": model.get("sourceGateReady", False),
        "dependencyInstallExecutionAuthorized": package["dependencyInstallExecutionAuthorized"],
        "executionAuthorized": package["executionAuthorized"],
        "dependencyFileWriteAuthorized": package["dependencyFileWriteAuthorized"],
        "commandMaterialized": package["commandMaterialized"],
        "commandExecuted": package["commandExecuted"],
        "dependencyInstallExecuted": package["dependencyInstallExecuted"],
        "packageVersionResolved": package["packageVersionResolved"],
        "secretPresenceChecked": package["secretPresenceChecked"],
        "networkAccess": package["networkAccess"],
        "realLlmCalled": package["realLlmCalled"],
    }


def _execution_request_checklist(
    request: RealSdkDependencyInstallExecutionRequestRequest,
    *,
    authorization_package_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "install_authorization_package_model_ready",
            "passed": authorization_package_ready,
            "required": True,
        },
        {
            "id": "dependency_install_execution_request_scope_confirmed",
            "passed": request.dependency_install_execution_request_scope_confirmed,
            "required": True,
        },
        {
            "id": "execution_request_approver_confirmed",
            "passed": request.execution_request_approver_confirmed,
            "required": True,
        },
        {
            "id": "execution_request_ticket_confirmed",
            "passed": request.execution_request_ticket_confirmed,
            "required": True,
        },
        {
            "id": "execution_request_change_window_confirmed",
            "passed": request.execution_request_change_window_confirmed,
            "required": True,
        },
        {
            "id": "install_authorization_package_review_confirmed",
            "passed": request.install_authorization_package_review_confirmed,
            "required": True,
        },
        {
            "id": "dependency_manifest_write_target_confirmed",
            "passed": request.dependency_manifest_write_target_confirmed,
            "required": True,
        },
        {
            "id": "dependency_lockfile_write_target_confirmed",
            "passed": request.dependency_lockfile_write_target_confirmed,
            "required": True,
        },
        {
            "id": "package_manager_execution_policy_confirmed",
            "passed": request.package_manager_execution_policy_confirmed,
            "required": True,
        },
        {
            "id": "execution_request_rollback_checkpoint_confirmed",
            "passed": request.execution_request_rollback_checkpoint_confirmed,
            "required": True,
        },
        {
            "id": "execution_request_post_install_validation_confirmed",
            "passed": request.execution_request_post_install_validation_confirmed,
            "required": True,
        },
        {
            "id": "no_execution_authorization_during_execution_request_confirmed",
            "passed": request.no_execution_authorization_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_write_during_execution_request_confirmed",
            "passed": request.no_dependency_file_write_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_file_write_during_execution_request_confirmed",
            "passed": request.no_patch_file_write_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_apply_during_execution_request_confirmed",
            "passed": request.no_patch_apply_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_command_materialization_during_execution_request_confirmed",
            "passed": request.no_command_materialization_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_during_execution_request_confirmed",
            "passed": request.no_command_execution_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_during_execution_request_confirmed",
            "passed": request.no_dependency_install_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_package_resolution_during_execution_request_confirmed",
            "passed": request.no_package_resolution_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_presence_check_during_execution_request_confirmed",
            "passed": request.no_secret_presence_check_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_network_during_execution_request_confirmed",
            "passed": request.no_network_during_execution_request_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_during_execution_request_confirmed",
            "passed": request.no_real_call_during_execution_request_confirmed,
            "required": True,
        },
    ]


def _execution_request_model(authorization_package: dict[str, Any]) -> dict[str, Any]:
    return {
        "executionRequestId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_REQUEST_ID,
        "executionRequestOnly": True,
        "targetPackage": TARGET_PACKAGE,
        "recommendedSpecifier": RECOMMENDED_SPECIFIER,
        "sourceAuthorizationPackageId": authorization_package["installAuthorizationPackageId"],
        "sourceAuthorizationPackageReady": authorization_package[
            "installAuthorizationPackageModelReady"
        ],
        "authorizationGrantedNow": False,
        "executionDispatchNow": False,
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
        "explicitExecutorImplementationRequired": True,
        "executorImplementationDeferred": True,
        "executionEvidence": {
            "executionRequestRecorded": True,
            "executorOwnerRequired": True,
            "dependencyFileTargetRequired": True,
            "lockfileTargetRequired": True,
            "packageManagerPolicyRequired": True,
            "rollbackCheckpointRequired": True,
            "postInstallValidationRequired": True,
            "secretPresenceCheckDeferred": True,
            "networkPackageInstallDeferred": True,
        },
        "blockedActions": [
            {"id": "grant_dependency_install_execution_authorization", "allowedNow": False},
            {"id": "dispatch_dependency_install_executor", "allowedNow": False},
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


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "future_dependency_install_executor", "reason": "must_be_separate_explicit_step"},
            {"field": "execution_authorization", "reason": "not_granted_by_execution_request"},
            {"field": "dependency_file_write", "reason": "not_written_by_execution_request"},
            {"field": "patch_file_write", "reason": "not_written_by_execution_request"},
            {"field": "patch_apply", "reason": "not_applied_by_execution_request"},
            {"field": "command_materialization", "reason": "not_materialized_by_execution_request"},
            {"field": "command_execution", "reason": "not_executed_by_execution_request"},
            {"field": "dependency_install", "reason": "not_installed_by_execution_request"},
            {"field": "package_resolution", "reason": "not_resolved_by_execution_request"},
            {"field": "secret_presence_check", "reason": "not_checked_by_execution_request"},
            {"field": "network_call", "reason": "not_allowed_by_execution_request"},
            {"field": "real_llm_call", "reason": "not_allowed_by_execution_request"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_install_execution_request",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_execution_request.py",
        },
        {
            "id": "test_real_sdk_dependency_install_authorization_package",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_authorization_package.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_SDK_INSTALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyInstallExecutionRequestRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 install execution request 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency install execution request"}],
        )


def build_real_sdk_dependency_install_execution_request_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyInstallExecutionRequestRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        authorization_package = build_real_sdk_dependency_install_authorization_package(
            request,
            root=root,
        )
    except ProviderError:
        authorization_package = None
    if authorization_package is not None:
        context["installAuthorizationPackageModelReady"] = bool(
            authorization_package.get("installAuthorizationPackageModelReady", False)
        )
        context["installAuthorizationPackageSummary"] = _authorization_package_summary(
            authorization_package
        )
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_install_execution_request(
    request: RealSdkDependencyInstallExecutionRequestRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    authorization_package = build_real_sdk_dependency_install_authorization_package(
        request,
        root=root,
    )
    authorization_package_ready = (
        authorization_package.get("installAuthorizationPackageModelReady") is True
    )
    checklist = _execution_request_checklist(
        request,
        authorization_package_ready=authorization_package_ready,
    )
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "installAuthorizationPackageModelReady": authorization_package_ready,
        "installAuthorizationPackageSummary": _authorization_package_summary(authorization_package),
        "installExecutionRequestChecklist": checklist,
        "installExecutionRequestChecklistPassed": checklist_passed,
        "installExecutionRequestModelReady": checklist_passed,
        "readyForExplicitDependencyInstallExecutorImplementation": checklist_passed,
        "installExecutionRequestModel": (
            _execution_request_model(authorization_package) if checklist_passed else None
        ),
        "futureExecutionEnvelope": _future_execution_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 install execution request 已生成执行请求模型；当前不会授权执行、写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。",
    }
