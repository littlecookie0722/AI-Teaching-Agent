"""Real SDK dependency install executor, disabled.

This module prepares a local disabled executor model after the install
execution request is ready. It does not dispatch executors, start executor
runs, grant execution authorization, write dependency files, write patch
files, apply patches, materialize or execute commands, install packages,
resolve package metadata, check secrets, use network access, import SDKs,
create clients, call real LLMs, create tasks, or publish content.
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
from .real_sdk_dependency_install_execution_request import (
    REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_REQUEST_ID,
    RealSdkDependencyInstallExecutionRequestRequest,
    build_real_sdk_dependency_install_execution_request,
    describe_real_sdk_dependency_install_execution_request,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_INSTALL_EXECUTOR_DISABLED_ID = (
    "real_sdk_dependency_install_executor_disabled"
)


@dataclass(frozen=True)
class RealSdkDependencyInstallExecutorDisabledRequest(
    RealSdkDependencyInstallExecutionRequestRequest
):
    dependency_install_executor_disabled_scope_confirmed: bool = False
    executor_disabled_owner_confirmed: bool = False
    executor_disabled_runtime_guard_confirmed: bool = False
    executor_disabled_dry_run_mode_confirmed: bool = False
    install_execution_request_review_confirmed: bool = False
    executor_no_dispatch_policy_confirmed: bool = False
    executor_no_command_template_materialization_confirmed: bool = False
    executor_no_dependency_file_write_policy_confirmed: bool = False
    executor_no_package_resolution_policy_confirmed: bool = False
    executor_no_secret_presence_check_policy_confirmed: bool = False
    executor_no_network_policy_confirmed: bool = False
    executor_rollback_checkpoint_confirmed: bool = False
    executor_post_install_validation_plan_confirmed: bool = False
    no_execution_authorization_during_executor_disabled_confirmed: bool = False
    no_executor_dispatch_during_executor_disabled_confirmed: bool = False
    no_executor_start_during_executor_disabled_confirmed: bool = False
    no_executor_run_creation_during_executor_disabled_confirmed: bool = False
    no_dependency_file_write_during_executor_disabled_confirmed: bool = False
    no_patch_file_write_during_executor_disabled_confirmed: bool = False
    no_patch_apply_during_executor_disabled_confirmed: bool = False
    no_command_materialization_during_executor_disabled_confirmed: bool = False
    no_command_execution_during_executor_disabled_confirmed: bool = False
    no_dependency_install_during_executor_disabled_confirmed: bool = False
    no_package_resolution_during_executor_disabled_confirmed: bool = False
    no_secret_presence_check_during_executor_disabled_confirmed: bool = False
    no_network_during_executor_disabled_confirmed: bool = False
    no_real_call_during_executor_disabled_confirmed: bool = False


def _disabled_execution_envelope() -> dict[str, bool]:
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
        "executorDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "executorDryRunOnly": True,
        "commandTemplateMaterialized": False,
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
    request: RealSdkDependencyInstallExecutorDisabledRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    descriptor = describe_real_sdk_dependency_install_execution_request(root=root)
    return {
        **descriptor,
        "installExecutorDisabledId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTOR_DISABLED_ID,
        "gateId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTOR_DISABLED_ID,
        "upstreamGateId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTION_REQUEST_ID,
        "gateMode": "DEPENDENCY_INSTALL_EXECUTOR_DISABLED",
        "executorDisabledMode": "LOCAL_DEPENDENCY_INSTALL_EXECUTOR_DISABLED_MODEL_ONLY",
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
        "installExecutionRequestRequired": True,
        "installExecutionRequestModelReady": False,
        "installExecutorDisabledOnly": True,
        "installExecutorDisabledModelReady": False,
        "readyForFutureDependencyInstallDryRunCommandReview": False,
        "requiresInstallExecutionRequestModelReady": True,
        "requiresDisabledExecutorImplementationReview": True,
        "requiresNoExecutionDuringExecutorDisabled": True,
        **_disabled_execution_envelope(),
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_install_executor_disabled(
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = RealSdkDependencyInstallExecutorDisabledRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "pipeline": [
            "real_sdk_dependency_install_execution_gate",
            "dependency_install_authorization_package",
            "dependency_install_execution_request",
            "dependency_install_executor_disabled",
            "future_explicit_dependency_install_dry_run_command_review",
        ],
    }


def _execution_request_summary(execution_request: dict[str, Any]) -> dict[str, Any]:
    model = execution_request.get("installExecutionRequestModel") or {}
    return {
        "installExecutionRequestId": execution_request["installExecutionRequestId"],
        "installExecutionRequestModelReady": execution_request["installExecutionRequestModelReady"],
        "readyForExplicitDependencyInstallExecutorImplementation": execution_request[
            "readyForExplicitDependencyInstallExecutorImplementation"
        ],
        "sourceAuthorizationPackageReady": model.get("sourceAuthorizationPackageReady", False),
        "dependencyInstallExecutionAuthorized": execution_request[
            "dependencyInstallExecutionAuthorized"
        ],
        "executionAuthorized": execution_request["executionAuthorized"],
        "dependencyFileWriteAuthorized": execution_request["dependencyFileWriteAuthorized"],
        "commandMaterialized": execution_request["commandMaterialized"],
        "commandExecuted": execution_request["commandExecuted"],
        "dependencyInstallExecuted": execution_request["dependencyInstallExecuted"],
        "packageVersionResolved": execution_request["packageVersionResolved"],
        "secretPresenceChecked": execution_request["secretPresenceChecked"],
        "networkAccess": execution_request["networkAccess"],
        "realLlmCalled": execution_request["realLlmCalled"],
    }


def _executor_disabled_checklist(
    request: RealSdkDependencyInstallExecutorDisabledRequest,
    *,
    execution_request_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "install_execution_request_model_ready",
            "passed": execution_request_ready,
            "required": True,
        },
        {
            "id": "dependency_install_executor_disabled_scope_confirmed",
            "passed": request.dependency_install_executor_disabled_scope_confirmed,
            "required": True,
        },
        {
            "id": "executor_disabled_owner_confirmed",
            "passed": request.executor_disabled_owner_confirmed,
            "required": True,
        },
        {
            "id": "executor_disabled_runtime_guard_confirmed",
            "passed": request.executor_disabled_runtime_guard_confirmed,
            "required": True,
        },
        {
            "id": "executor_disabled_dry_run_mode_confirmed",
            "passed": request.executor_disabled_dry_run_mode_confirmed,
            "required": True,
        },
        {
            "id": "install_execution_request_review_confirmed",
            "passed": request.install_execution_request_review_confirmed,
            "required": True,
        },
        {
            "id": "executor_no_dispatch_policy_confirmed",
            "passed": request.executor_no_dispatch_policy_confirmed,
            "required": True,
        },
        {
            "id": "executor_no_command_template_materialization_confirmed",
            "passed": request.executor_no_command_template_materialization_confirmed,
            "required": True,
        },
        {
            "id": "executor_no_dependency_file_write_policy_confirmed",
            "passed": request.executor_no_dependency_file_write_policy_confirmed,
            "required": True,
        },
        {
            "id": "executor_no_package_resolution_policy_confirmed",
            "passed": request.executor_no_package_resolution_policy_confirmed,
            "required": True,
        },
        {
            "id": "executor_no_secret_presence_check_policy_confirmed",
            "passed": request.executor_no_secret_presence_check_policy_confirmed,
            "required": True,
        },
        {
            "id": "executor_no_network_policy_confirmed",
            "passed": request.executor_no_network_policy_confirmed,
            "required": True,
        },
        {
            "id": "executor_rollback_checkpoint_confirmed",
            "passed": request.executor_rollback_checkpoint_confirmed,
            "required": True,
        },
        {
            "id": "executor_post_install_validation_plan_confirmed",
            "passed": request.executor_post_install_validation_plan_confirmed,
            "required": True,
        },
        {
            "id": "no_execution_authorization_during_executor_disabled_confirmed",
            "passed": request.no_execution_authorization_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_dispatch_during_executor_disabled_confirmed",
            "passed": request.no_executor_dispatch_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_start_during_executor_disabled_confirmed",
            "passed": request.no_executor_start_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_executor_run_creation_during_executor_disabled_confirmed",
            "passed": request.no_executor_run_creation_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_write_during_executor_disabled_confirmed",
            "passed": request.no_dependency_file_write_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_file_write_during_executor_disabled_confirmed",
            "passed": request.no_patch_file_write_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_apply_during_executor_disabled_confirmed",
            "passed": request.no_patch_apply_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_command_materialization_during_executor_disabled_confirmed",
            "passed": request.no_command_materialization_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_during_executor_disabled_confirmed",
            "passed": request.no_command_execution_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_during_executor_disabled_confirmed",
            "passed": request.no_dependency_install_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_package_resolution_during_executor_disabled_confirmed",
            "passed": request.no_package_resolution_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_presence_check_during_executor_disabled_confirmed",
            "passed": request.no_secret_presence_check_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_network_during_executor_disabled_confirmed",
            "passed": request.no_network_during_executor_disabled_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_during_executor_disabled_confirmed",
            "passed": request.no_real_call_during_executor_disabled_confirmed,
            "required": True,
        },
    ]


def _executor_disabled_model(execution_request: dict[str, Any]) -> dict[str, Any]:
    return {
        "executorDisabledId": REAL_SDK_DEPENDENCY_INSTALL_EXECUTOR_DISABLED_ID,
        "executorDisabledOnly": True,
        "targetPackage": TARGET_PACKAGE,
        "recommendedSpecifier": RECOMMENDED_SPECIFIER,
        "sourceExecutionRequestId": execution_request["installExecutionRequestId"],
        "sourceExecutionRequestReady": execution_request["installExecutionRequestModelReady"],
        "executorImplementationDeferred": True,
        "explicitDryRunCommandReviewRequired": True,
        "executionAuthorizationNow": False,
        "dependencyFileWriteNow": False,
        "patchFileWriteNow": False,
        "patchApplyNow": False,
        "executorDispatchNow": False,
        "executorStartNow": False,
        "executorRunCreateNow": False,
        "commandTemplateMaterializeNow": False,
        "commandMaterializeNow": False,
        "commandExecuteNow": False,
        "installNow": False,
        "packageResolveNow": False,
        "secretCheckNow": False,
        "networkNow": False,
        "realCallNow": False,
        "dryRunEvidence": {
            "dryRunCommandReviewRequired": True,
            "dryRunEvidencePersistenceDeferred": True,
            "commandTemplateReviewRequired": True,
            "executorDispatchDeferred": True,
            "executorRunCreationDeferred": True,
            "dependencyFileMutationDeferred": True,
            "packageResolutionDeferred": True,
            "secretPresenceCheckDeferred": True,
            "networkPackageInstallDeferred": True,
        },
        "blockedActions": [
            {"id": "grant_dependency_install_execution_authorization", "allowedNow": False},
            {"id": "dispatch_dependency_install_executor", "allowedNow": False},
            {"id": "start_dependency_install_executor", "allowedNow": False},
            {"id": "create_executor_run", "allowedNow": False},
            {"id": "write_dependency_manifest", "allowedNow": False},
            {"id": "write_dependency_lockfile", "allowedNow": False},
            {"id": "write_patch_file", "allowedNow": False},
            {"id": "apply_patch", "allowedNow": False},
            {"id": "materialize_install_command_template", "allowedNow": False},
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
            {"field": "future_dependency_install_dry_run_command_review", "reason": "must_be_separate_explicit_step"},
            {"field": "execution_authorization", "reason": "not_granted_by_disabled_executor"},
            {"field": "executor_dispatch", "reason": "not_dispatched_by_disabled_executor"},
            {"field": "executor_start", "reason": "not_started_by_disabled_executor"},
            {"field": "executor_run_creation", "reason": "not_created_by_disabled_executor"},
            {"field": "dependency_file_write", "reason": "not_written_by_disabled_executor"},
            {"field": "patch_file_write", "reason": "not_written_by_disabled_executor"},
            {"field": "patch_apply", "reason": "not_applied_by_disabled_executor"},
            {"field": "command_materialization", "reason": "not_materialized_by_disabled_executor"},
            {"field": "command_execution", "reason": "not_executed_by_disabled_executor"},
            {"field": "dependency_install", "reason": "not_installed_by_disabled_executor"},
            {"field": "package_resolution", "reason": "not_resolved_by_disabled_executor"},
            {"field": "secret_presence_check", "reason": "not_checked_by_disabled_executor"},
            {"field": "network_call", "reason": "not_allowed_by_disabled_executor"},
            {"field": "real_llm_call", "reason": "not_allowed_by_disabled_executor"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_install_executor_disabled",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_executor_disabled.py",
        },
        {
            "id": "test_real_sdk_dependency_install_execution_request",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_execution_request.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_SDK_INSTALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyInstallExecutorDisabledRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 install executor disabled 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency install executor disabled"}],
        )


def build_real_sdk_dependency_install_executor_disabled_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyInstallExecutorDisabledRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        execution_request = build_real_sdk_dependency_install_execution_request(
            request,
            root=root,
        )
    except ProviderError:
        execution_request = None
    if execution_request is not None:
        context["installExecutionRequestModelReady"] = bool(
            execution_request.get("installExecutionRequestModelReady", False)
        )
        context["installExecutionRequestSummary"] = _execution_request_summary(
            execution_request
        )
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_install_executor_disabled(
    request: RealSdkDependencyInstallExecutorDisabledRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    execution_request = build_real_sdk_dependency_install_execution_request(
        request,
        root=root,
    )
    execution_request_ready = (
        execution_request.get("installExecutionRequestModelReady") is True
    )
    checklist = _executor_disabled_checklist(
        request,
        execution_request_ready=execution_request_ready,
    )
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "installExecutionRequestModelReady": execution_request_ready,
        "installExecutionRequestSummary": _execution_request_summary(execution_request),
        "installExecutorDisabledChecklist": checklist,
        "installExecutorDisabledChecklistPassed": checklist_passed,
        "installExecutorDisabledModelReady": checklist_passed,
        "readyForFutureDependencyInstallDryRunCommandReview": checklist_passed,
        "installExecutorDisabledModel": (
            _executor_disabled_model(execution_request) if checklist_passed else None
        ),
        "disabledExecutionEnvelope": _disabled_execution_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 install executor disabled 已生成禁用执行器模型；当前不会派发执行器、启动执行器、创建执行 run、授权执行、写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。",
    }
