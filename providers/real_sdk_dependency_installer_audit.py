"""Disabled real SDK dependency installer audit.

This module shapes the future dependency-install implementation task without
executing it. It never generates executable install commands, installs
packages, resolves package metadata, modifies dependency files, imports SDKs,
checks secrets, opens network connections, creates tasks, or publishes content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .mock_provider import ProviderError, load_provider_contract
from .provider_runtime_guard import redact_provider_payload
from .real_llm_sdk_task_blueprint import DEFAULT_MODEL_ALIAS
from .real_sdk_dependency_install_plan import (
    RealSdkDependencyInstallPlanRequest,
    build_real_sdk_dependency_install_plan,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_INSTALLER_AUDIT_ID = "real_sdk_dependency_installer_audit"
SUPPORTED_PROVIDER = "openai"
TARGET_PACKAGE = "openai"


@dataclass(frozen=True)
class RealSdkDependencyInstallerAuditRequest:
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
    sdk_dependency_review_confirmed: bool = False
    provider_contract_review_confirmed: bool = False
    runtime_contract_review_confirmed: bool = False
    secret_injection_review_confirmed: bool = False
    network_access_review_confirmed: bool = False
    rollback_plan_confirmed: bool = False
    minimal_impl_review_confirmed: bool = False
    sdk_package_review_confirmed: bool = False
    sdk_version_pin_review_confirmed: bool = False
    dependency_license_review_confirmed: bool = False
    dependency_hash_review_confirmed: bool = False
    env_var_name_review_confirmed: bool = False
    env_example_review_confirmed: bool = False
    secret_non_read_policy_confirmed: bool = False
    ci_install_policy_confirmed: bool = False
    package_manager_review_confirmed: bool = False
    lockfile_strategy_review_confirmed: bool = False
    version_pin_strategy_confirmed: bool = False
    hash_verification_strategy_confirmed: bool = False
    rollback_files_review_confirmed: bool = False
    ci_cache_policy_confirmed: bool = False
    no_install_execution_confirmed: bool = False
    no_network_policy_confirmed: bool = False
    no_secret_policy_confirmed: bool = False
    command_review_confirmed: bool = False
    dependency_file_review_confirmed: bool = False
    lockfile_diff_review_confirmed: bool = False
    offline_ci_review_confirmed: bool = False
    rollback_command_review_confirmed: bool = False
    execution_disabled_confirmed: bool = False
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


def _install_plan_request(request: RealSdkDependencyInstallerAuditRequest) -> RealSdkDependencyInstallPlanRequest:
    return RealSdkDependencyInstallPlanRequest(
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
        target_model_alias=request.target_model_alias,
        task_ref=request.task_ref,
        sdk_dependency_review_confirmed=request.sdk_dependency_review_confirmed,
        provider_contract_review_confirmed=request.provider_contract_review_confirmed,
        runtime_contract_review_confirmed=request.runtime_contract_review_confirmed,
        secret_injection_review_confirmed=request.secret_injection_review_confirmed,
        network_access_review_confirmed=request.network_access_review_confirmed,
        rollback_plan_confirmed=request.rollback_plan_confirmed,
        minimal_impl_review_confirmed=request.minimal_impl_review_confirmed,
        sdk_package_review_confirmed=request.sdk_package_review_confirmed,
        sdk_version_pin_review_confirmed=request.sdk_version_pin_review_confirmed,
        dependency_license_review_confirmed=request.dependency_license_review_confirmed,
        dependency_hash_review_confirmed=request.dependency_hash_review_confirmed,
        env_var_name_review_confirmed=request.env_var_name_review_confirmed,
        env_example_review_confirmed=request.env_example_review_confirmed,
        secret_non_read_policy_confirmed=request.secret_non_read_policy_confirmed,
        ci_install_policy_confirmed=request.ci_install_policy_confirmed,
        package_manager_review_confirmed=request.package_manager_review_confirmed,
        lockfile_strategy_review_confirmed=request.lockfile_strategy_review_confirmed,
        version_pin_strategy_confirmed=request.version_pin_strategy_confirmed,
        hash_verification_strategy_confirmed=request.hash_verification_strategy_confirmed,
        rollback_files_review_confirmed=request.rollback_files_review_confirmed,
        ci_cache_policy_confirmed=request.ci_cache_policy_confirmed,
        no_install_execution_confirmed=request.no_install_execution_confirmed,
        no_network_policy_confirmed=request.no_network_policy_confirmed,
        no_secret_policy_confirmed=request.no_secret_policy_confirmed,
        trace_id=request.trace_id,
    )


def _base_context(request: RealSdkDependencyInstallerAuditRequest, *, root: Path) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, request.provider_id)
    secret_env = provider.get("secretEnv") if provider else None
    return {
        "auditId": REAL_SDK_DEPENDENCY_INSTALLER_AUDIT_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "auditMode": "INSTALLER_AUDIT_DISABLED_ONLY",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "providerId": request.provider_id,
        "supportedProvider": SUPPORTED_PROVIDER,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "providerEnabled": bool(provider.get("enabled", False)) if provider else False,
        "targetPackage": TARGET_PACKAGE,
        "targetSecretEnv": secret_env,
        "secretNameOnly": True,
        "packageNameOnly": True,
        "targetModelAlias": _clean_text(request.target_model_alias) or DEFAULT_MODEL_ALIAS,
        "runtimeFlags": _safe_runtime_flags(runtime_contract),
        "approvalRef": _clean_text(request.approval_ref),
        "reviewer": _clean_text(request.reviewer),
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "installPlanRequired": True,
        "installPlanReady": False,
        "installerAuditChecklistPassed": False,
        "readyForInstallerImplementationTask": False,
        "installerExecutionEnabled": False,
        "installCommandMaterialized": False,
        "dependencyInstallAllowed": False,
        "dependencyInstallCommandGenerated": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstalled": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "dependencyLockfileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "dependencyFileChanged": False,
        "lockfileDiffGenerated": False,
        "rollbackCommandGenerated": False,
        "offlineCiExecuted": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "networkAccess": False,
        "networkAccessEnabledNow": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_installer_audit(*, root: Path = ROOT) -> dict[str, Any]:
    provider_contract = load_provider_contract(root)
    runtime_contract = _load_runtime_contract(root)
    provider = _find_provider(provider_contract, SUPPORTED_PROVIDER)
    return {
        "auditId": REAL_SDK_DEPENDENCY_INSTALLER_AUDIT_ID,
        "interfaceName": "LLMProvider",
        "phase": runtime_contract.get("phase", "Phase 1"),
        "targetPhase": "Phase 2",
        "mode": runtime_contract.get("mode", "MOCK_ONLY"),
        "auditMode": "INSTALLER_AUDIT_DISABLED_ONLY",
        "defaultProvider": provider_contract.get("activeProvider", "mock"),
        "supportedProvider": SUPPORTED_PROVIDER,
        "targetPackage": TARGET_PACKAGE,
        "targetSecretEnv": provider.get("secretEnv") if provider else None,
        "requiresInstallPlan": True,
        "requiresCommandReview": True,
        "requiresDependencyFileReview": True,
        "requiresLockfileDiffReview": True,
        "requiresOfflineCiReview": True,
        "requiresRollbackCommandReview": True,
        "generatedStatus": "WAITING_REVIEW",
        "installPlanReady": False,
        "readyForInstallerImplementationTask": False,
        "installerExecutionEnabled": False,
        "installCommandMaterialized": False,
        "dependencyInstallAllowed": False,
        "dependencyInstallCommandGenerated": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstallAllowed": False,
        "sdkDependencyInstalled": False,
        "packageVersionResolved": False,
        "packageHashResolved": False,
        "packageDownloaded": False,
        "dependencyLockfileChanged": False,
        "requirementsChanged": False,
        "pyprojectChanged": False,
        "dependencyFileChanged": False,
        "lockfileDiffGenerated": False,
        "rollbackCommandGenerated": False,
        "offlineCiExecuted": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "networkAccess": False,
        "networkAccessEnabledNow": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "reviewBypassed": False,
        "realCallAuthorized": False,
        "realLlmCalled": False,
        "secretsRead": False,
        "providerContractChangeApplied": False,
        "runtimeContractChangeApplied": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "pipeline": [
            "real_sdk_dependency_install_plan",
            "installer_command_review",
            "dependency_file_review",
            "lockfile_diff_review",
            "offline_ci_review",
            "future_disabled_installer_implementation_task",
        ],
    }


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "planId": plan["planId"],
        "installPlanChecklistPassed": plan["installPlanChecklistPassed"],
        "readyForDependencyInstallImplementationReview": plan["readyForDependencyInstallImplementationReview"],
        "dependencyInstallCommandGenerated": plan["dependencyInstallCommandGenerated"],
        "dependencyInstallExecuted": plan["dependencyInstallExecuted"],
        "dependencyLockfileChanged": plan["dependencyLockfileChanged"],
        "packageVersionResolved": plan["packageVersionResolved"],
        "packageHashResolved": plan["packageHashResolved"],
        "secretPresenceChecked": plan["secretPresenceChecked"],
        "networkAccess": plan["networkAccess"],
    }


def _installer_audit_checklist(
    request: RealSdkDependencyInstallerAuditRequest,
    *,
    plan_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "install_plan_ready", "passed": plan_ready, "required": True},
        {"id": "command_review_confirmed", "passed": request.command_review_confirmed, "required": True},
        {"id": "dependency_file_review_confirmed", "passed": request.dependency_file_review_confirmed, "required": True},
        {"id": "lockfile_diff_review_confirmed", "passed": request.lockfile_diff_review_confirmed, "required": True},
        {"id": "offline_ci_review_confirmed", "passed": request.offline_ci_review_confirmed, "required": True},
        {"id": "rollback_command_review_confirmed", "passed": request.rollback_command_review_confirmed, "required": True},
        {"id": "execution_disabled_confirmed", "passed": request.execution_disabled_confirmed, "required": True},
    ]


def _proposed_command_blueprint() -> dict[str, Any]:
    return {
        "id": "future_openai_sdk_install",
        "package": TARGET_PACKAGE,
        "commandTemplate": "python -m pip install openai==<reviewed-version> --require-hashes",
        "commandMaterialized": False,
        "executableNow": False,
        "containsExactVersion": False,
        "containsHashes": False,
        "requiresSeparateReviewedTask": True,
    }


def _file_audit_plan() -> list[dict[str, Any]]:
    return [
        {
            "id": "dependency_manifest",
            "path": "pyproject.toml_or_requirements.txt",
            "changeType": "future_reviewed_change",
            "changedNow": False,
            "requiresLockfilePairing": True,
        },
        {
            "id": "dependency_lockfile",
            "path": "future_lockfile",
            "changeType": "future_reviewed_lockfile_update",
            "changedNow": False,
            "requiresHashReview": True,
        },
        {
            "id": "rollback_doc",
            "path": "docs/decisions/future-real-sdk-dependency-rollback.md",
            "changeType": "future_reviewed_doc",
            "changedNow": False,
            "requiresRollbackReview": True,
        },
    ]


def _blocked_until(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    reasons = [
        {"field": item["id"], "reason": "required"}
        for item in checklist
        if item["required"] is True and item["passed"] is False
    ]
    reasons.extend(
        [
            {"field": "future_disabled_installer_implementation_task", "reason": "must_be_separate_reviewed_task"},
            {"field": "dependency_install_command", "reason": "not_materialized_by_audit"},
            {"field": "dependency_file_changes", "reason": "not_applied_by_audit"},
            {"field": "lockfile_diff", "reason": "not_generated_by_audit"},
            {"field": "package_resolution", "reason": "not_performed_by_audit"},
            {"field": "network_call", "reason": "not_allowed_by_audit"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_installer_audit",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_installer_audit.py",
        },
        {
            "id": "test_real_sdk_dependency_install_plan",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_install_plan.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyInstallerAuditRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖安装执行审计当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency installer audit"}],
        )


def build_real_sdk_dependency_installer_audit_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyInstallerAuditRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            plan = build_real_sdk_dependency_install_plan(_install_plan_request(request), root=root)
        else:
            plan = None
    except ProviderError:
        plan = None
    if plan is not None:
        context["installPlanReady"] = bool(plan.get("readyForDependencyInstallImplementationReview", False))
        context["installPlanSummary"] = _plan_summary(plan)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_installer_audit(
    request: RealSdkDependencyInstallerAuditRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    plan = build_real_sdk_dependency_install_plan(_install_plan_request(request), root=root)
    plan_ready = plan.get("readyForDependencyInstallImplementationReview") is True
    checklist = _installer_audit_checklist(request, plan_ready=plan_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "installPlanReady": plan_ready,
        "installPlanSummary": _plan_summary(plan),
        "installerAuditChecklist": checklist,
        "installerAuditChecklistPassed": checklist_passed,
        "readyForInstallerImplementationTask": checklist_passed,
        "proposedCommandBlueprint": _proposed_command_blueprint(),
        "fileAuditPlan": _file_audit_plan(),
        "rollbackAudit": {
            "rollbackCommandMaterialized": False,
            "rollbackExecuted": False,
            "requiresSeparateReview": True,
            "restoreLockfile": True,
            "removeDependencyManifestChange": True,
        },
        "ciAudit": {
            "offlineOnly": True,
            "ciExecuted": False,
            "networkDisabled": True,
            "requiresSeparateReviewedTask": True,
        },
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖安装执行审计已生成；当前不会生成命令、安装依赖、修改文件、解析包元数据或联网。",
    }
