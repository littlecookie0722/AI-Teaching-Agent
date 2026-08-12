"""Disabled real SDK dependency dry-run evidence model.

This module prepares a local evidence model for future dependency install
dry-run review. It does not write evidence files, persist review records,
materialize or execute commands, write dependency files, install SDKs, import
SDKs, check secrets, use network access, call real LLMs, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_executor_disabled import (
    RealSdkDependencyExecutorDisabledRequest,
    build_real_sdk_dependency_executor_disabled,
    describe_real_sdk_dependency_executor_disabled,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_DRY_RUN_EVIDENCE_ID = "real_sdk_dependency_dry_run_evidence"
SUPPORTED_PROVIDER = "openai"


@dataclass(frozen=True)
class RealSdkDependencyDryRunEvidenceRequest(RealSdkDependencyExecutorDisabledRequest):
    dry_run_evidence_scope_confirmed: bool = False
    command_review_record_confirmed: bool = False
    evidence_owner_confirmed: bool = False
    evidence_retention_policy_confirmed: bool = False
    no_evidence_file_write_confirmed: bool = False
    no_command_materialization_after_evidence_confirmed: bool = False
    no_command_execution_after_evidence_confirmed: bool = False
    no_dependency_file_mutation_after_evidence_confirmed: bool = False
    no_dependency_install_after_evidence_confirmed: bool = False
    no_real_call_after_evidence_confirmed: bool = False


def _base_context(request: RealSdkDependencyDryRunEvidenceRequest, *, root: Path) -> dict[str, Any]:
    executor_descriptor = describe_real_sdk_dependency_executor_disabled(root=root)
    return {
        **executor_descriptor,
        "dryRunEvidenceId": REAL_SDK_DEPENDENCY_DRY_RUN_EVIDENCE_ID,
        "gateId": REAL_SDK_DEPENDENCY_DRY_RUN_EVIDENCE_ID,
        "upstreamGateId": "real_sdk_dependency_executor_disabled",
        "gateMode": "DEPENDENCY_DRY_RUN_EVIDENCE_DISABLED_ONLY",
        "evidenceMode": "LOCAL_EVIDENCE_MODEL_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "executorModelRequired": True,
        "executorModelReady": False,
        "dryRunEvidenceOnly": True,
        "dryRunEvidenceModelReady": False,
        "readyForCommandReviewEvidence": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "taskPersisted": False,
        "taskQueued": False,
        "executionDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "dryRunExecuted": False,
        "installDryRunExecuted": False,
        "evidenceFileWritten": False,
        "commandReviewRecordPersisted": False,
        "commandMaterialized": False,
        "installCommandMaterialized": False,
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyFileMutationAuthorized": False,
        "dependencyFileChangeAuthorized": False,
        "dependencyManifestWriteAuthorized": False,
        "dependencyLockfileWriteAuthorized": False,
        "dependencyManifestMutated": False,
        "dependencyLockfileMutated": False,
        "dependencyFileChanged": False,
        "patchGenerated": False,
        "patchMaterialized": False,
        "patchFileWritten": False,
        "patchApplied": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAfterEvidenceAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_dry_run_evidence(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyDryRunEvidenceRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresExecutorModelReady": True,
        "requiresEvidenceOwner": True,
        "requiresNoEvidenceFileWritePolicy": True,
        "pipeline": [
            "real_sdk_dependency_execution_task_creation",
            "real_sdk_dependency_executor_disabled",
            "dependency_dry_run_evidence_model",
            "future_install_command_review",
            "future_real_dependency_file_change_after_review",
        ],
    }


def _executor_summary(executor: dict[str, Any]) -> dict[str, Any]:
    return {
        "executorDisabledId": executor["executorDisabledId"],
        "executionTaskCreationModelReady": executor["executionTaskCreationModelReady"],
        "executorModelReady": executor["executorModelReady"],
        "readyForDisabledDependencyExecutor": executor["readyForDisabledDependencyExecutor"],
        "executorStarted": executor["executorStarted"],
        "executorRunCreated": executor["executorRunCreated"],
        "commandMaterialized": executor["commandMaterialized"],
        "commandExecuted": executor["commandExecuted"],
        "dependencyInstallExecuted": executor["dependencyInstallExecuted"],
        "secretPresenceChecked": executor["secretPresenceChecked"],
        "networkAccess": executor["networkAccess"],
        "realLlmCalled": executor["realLlmCalled"],
    }


def _evidence_checklist(
    request: RealSdkDependencyDryRunEvidenceRequest,
    *,
    executor_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "executor_model_ready", "passed": executor_ready, "required": True},
        {
            "id": "dry_run_evidence_scope_confirmed",
            "passed": request.dry_run_evidence_scope_confirmed,
            "required": True,
        },
        {
            "id": "command_review_record_confirmed",
            "passed": request.command_review_record_confirmed,
            "required": True,
        },
        {"id": "evidence_owner_confirmed", "passed": request.evidence_owner_confirmed, "required": True},
        {
            "id": "evidence_retention_policy_confirmed",
            "passed": request.evidence_retention_policy_confirmed,
            "required": True,
        },
        {
            "id": "no_evidence_file_write_confirmed",
            "passed": request.no_evidence_file_write_confirmed,
            "required": True,
        },
        {
            "id": "no_command_materialization_after_evidence_confirmed",
            "passed": request.no_command_materialization_after_evidence_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_evidence_confirmed",
            "passed": request.no_command_execution_after_evidence_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_file_mutation_after_evidence_confirmed",
            "passed": request.no_dependency_file_mutation_after_evidence_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_evidence_confirmed",
            "passed": request.no_dependency_install_after_evidence_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_evidence_confirmed",
            "passed": request.no_real_call_after_evidence_confirmed,
            "required": True,
        },
    ]


def _evidence_model(request: RealSdkDependencyDryRunEvidenceRequest) -> dict[str, Any]:
    return {
        "evidenceId": REAL_SDK_DEPENDENCY_DRY_RUN_EVIDENCE_ID,
        "materializedNow": False,
        "writeNow": False,
        "persistNow": False,
        "dryRunNow": False,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "targetProvider": request.provider_id,
        "targetPackage": "openai",
        "commandReview": {
            "recordPersisted": False,
            "commandMaterialized": False,
            "commandExecutable": False,
            "allowedCommands": [],
        },
        "evidenceRecord": {
            "status": "NOT_WRITTEN",
            "fileWritten": False,
            "dryRunExecuted": False,
            "installDryRunExecuted": False,
            "networkAllowed": False,
        },
        "blockedActions": [
            {"id": "write_evidence_file", "allowedNow": False},
            {"id": "persist_command_review_record", "allowedNow": False},
            {"id": "materialize_command", "allowedNow": False},
            {"id": "execute_dry_run", "allowedNow": False},
            {"id": "execute_install_command", "allowedNow": False},
            {"id": "write_dependency_file", "allowedNow": False},
            {"id": "check_secret_presence", "allowedNow": False},
            {"id": "network_call", "allowedNow": False},
            {"id": "real_llm_call", "allowedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "dryRunEvidenceModelReady": False,
        "readyForCommandReviewEvidence": False,
        "executionApprovalGranted": False,
        "executionTaskCreated": False,
        "taskPersisted": False,
        "taskQueued": False,
        "executionDispatched": False,
        "executorStarted": False,
        "executorRunCreated": False,
        "dryRunExecuted": False,
        "installDryRunExecuted": False,
        "evidenceFileWritten": False,
        "commandReviewRecordPersisted": False,
        "commandMaterialized": False,
        "installCommandMaterialized": False,
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyFileMutationAuthorized": False,
        "dependencyFileChanged": False,
        "dependencyInstallExecuted": False,
        "sdkDependencyInstalled": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretPresenceChecked": False,
        "secretValueRead": False,
        "networkAccess": False,
        "realCallAfterEvidenceAuthorized": False,
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
            {"field": "evidence_file_write", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "command_review_record_persistence", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "command_materialization", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "dry_run_execution", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "command_execution", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "dependency_file_mutation", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "dependency_install", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "secret_presence_check", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "network_call", "reason": "not_allowed_by_dry_run_evidence_shell"},
            {"field": "real_llm_call", "reason": "not_allowed_after_dry_run_evidence_shell"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_dry_run_evidence",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_dry_run_evidence.py",
        },
        {
            "id": "test_real_sdk_dependency_executor_disabled",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_executor_disabled.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_REAL_CALL", "command": "python -m pytest"},
    ]


def _validate_provider_scope(request: RealSdkDependencyDryRunEvidenceRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 dry-run evidence 当前只允许 OpenAI 单 Provider 范围",
            [{"field": "provider", "reason": "only openai is allowed in dependency dry-run evidence shell"}],
        )


def build_real_sdk_dependency_dry_run_evidence_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyDryRunEvidenceRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        if request.provider_id == SUPPORTED_PROVIDER:
            executor = build_real_sdk_dependency_executor_disabled(request, root=root)
        else:
            executor = None
    except ProviderError:
        executor = None
    if executor is not None:
        context["executorModelReady"] = bool(executor.get("readyForDisabledDependencyExecutor", False))
        context["executorSummary"] = _executor_summary(executor)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_dry_run_evidence(
    request: RealSdkDependencyDryRunEvidenceRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    executor = build_real_sdk_dependency_executor_disabled(request, root=root)
    executor_ready = executor.get("readyForDisabledDependencyExecutor") is True
    checklist = _evidence_checklist(request, executor_ready=executor_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    return {
        **context,
        "executorModelReady": executor_ready,
        "executorSummary": _executor_summary(executor),
        "dryRunEvidenceChecklist": checklist,
        "dryRunEvidenceModelReady": checklist_passed,
        "readyForCommandReviewEvidence": checklist_passed,
        "dryRunEvidenceModel": _evidence_model(request),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 dry-run evidence 模型已生成；当前不会写 evidence 文件、持久化命令审阅记录、物化命令、执行 dry-run、执行命令、写依赖文件、安装依赖、读取密钥、联网或真实调用。",
    }
