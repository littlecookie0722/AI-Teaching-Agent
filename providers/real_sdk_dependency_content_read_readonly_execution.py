"""Readonly real SDK dependency content read with redacted preview.

This module performs the first reviewed local dependency manifest/lockfile
content read. It only reads allowlisted files under the project root and returns
redacted summaries. It does not persist content, write artifacts, generate
patches, materialize or execute commands, install SDKs, import SDKs, check
secrets, use network access, call real LLMs, or publish content.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .provider_runtime_guard import redact_provider_payload
from .real_sdk_dependency_content_read_final_confirmation import (
    RealSdkDependencyContentReadFinalConfirmationRequest,
    build_real_sdk_dependency_content_read_final_confirmation,
    describe_real_sdk_dependency_content_read_final_confirmation,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SDK_DEPENDENCY_CONTENT_READ_READONLY_EXECUTION_ID = (
    "real_sdk_dependency_content_read_readonly_execution"
)
SUPPORTED_PROVIDER = "openai"
MANIFEST_CANDIDATES = ("pyproject.toml", "requirements.txt")
LOCKFILE_CANDIDATES = ("uv.lock", "poetry.lock", "requirements.lock")
MAX_READ_BYTES = 128 * 1024
MAX_PREVIEW_LINES = 20


@dataclass(frozen=True)
class RealSdkDependencyContentReadReadonlyExecutionRequest(
    RealSdkDependencyContentReadFinalConfirmationRequest
):
    content_read_execution_scope_confirmed: bool = False
    content_read_execution_approver_confirmed: bool = False
    content_read_execution_ticket_confirmed: bool = False
    readonly_dependency_content_read_confirmed: bool = False
    manifest_content_read_confirmed: bool = False
    lockfile_content_read_confirmed: bool = False
    redaction_before_return_confirmed: bool = False
    no_raw_content_return_execution_confirmed: bool = False
    no_content_persistence_execution_confirmed: bool = False
    no_content_artifact_write_execution_confirmed: bool = False
    no_patch_generation_after_content_read_execution_confirmed: bool = False
    no_command_execution_after_content_read_execution_confirmed: bool = False
    no_dependency_install_after_content_read_execution_confirmed: bool = False
    no_secret_presence_check_after_content_read_execution_confirmed: bool = False
    no_network_after_content_read_execution_confirmed: bool = False
    no_real_call_after_content_read_execution_confirmed: bool = False


def _base_context(
    request: RealSdkDependencyContentReadReadonlyExecutionRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    descriptor = describe_real_sdk_dependency_content_read_final_confirmation(root=ROOT)
    return {
        **descriptor,
        "contentReadReadonlyExecutionId": REAL_SDK_DEPENDENCY_CONTENT_READ_READONLY_EXECUTION_ID,
        "gateId": REAL_SDK_DEPENDENCY_CONTENT_READ_READONLY_EXECUTION_ID,
        "upstreamGateId": "real_sdk_dependency_content_read_final_confirmation",
        "gateMode": "DEPENDENCY_CONTENT_READ_READONLY_EXECUTION_REDACTED_ONLY",
        "executionMode": "LOCAL_READONLY_CONTENT_READ_REDACTED_PREVIEW_ONLY",
        "providerId": request.provider_id,
        "operation": request.operation,
        "promptId": request.prompt_id,
        "outputKind": request.output_kind,
        "inputRef": request.input_ref,
        "approvalRef": request.approval_ref.strip() if request.approval_ref else None,
        "reviewer": request.reviewer.strip() if request.reviewer else None,
        "redactionApplied": True,
        "redactedPayloadPreview": redact_provider_payload(dict(request.payload or {})),
        "contentReadFinalConfirmationRequired": True,
        "contentReadFinalConfirmationModelReady": False,
        "contentReadReadonlyExecutionOnly": True,
        "contentReadReadonlyExecutionModelReady": False,
        "dependencyContentReadAuthorized": False,
        "dependencyContentReadExecuted": False,
        "dependencyManifestContentRead": False,
        "dependencyLockfileContentRead": False,
        "dependencyContentReturned": False,
        "rawDependencyContentReturned": False,
        "redactedDependencyContentPreviewReturned": False,
        "dependencyContentPersisted": False,
        "contentReadReadonlyExecutionRecordPersisted": False,
        "contentReadReadonlyExecutionArtifactWritten": False,
        "contentReadReadonlyExecutionExecuted": False,
        "dependencyFileRead": False,
        "liveDependencyFileRead": False,
        "dependencySnapshotReadFromFile": False,
        "dependencySnapshotContentCaptured": False,
        "snapshotFileWritten": False,
        "targetPathResolutionExecuted": False,
        "targetFileWritten": False,
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
        "realCallAfterContentReadReadonlyExecutionAuthorized": False,
        "realLlmCalled": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "traceId": request.trace_id,
    }


def describe_real_sdk_dependency_content_read_readonly_execution(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealSdkDependencyContentReadReadonlyExecutionRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresContentReadFinalConfirmationModelReady": True,
        "requiresReadonlyReadScope": True,
        "requiresRedactionBeforeReturn": True,
        "requiresNoRawContentReturnPolicy": True,
        "allowlistedManifestCandidates": list(MANIFEST_CANDIDATES),
        "allowlistedLockfileCandidates": list(LOCKFILE_CANDIDATES),
        "maxReadBytes": MAX_READ_BYTES,
    }


def _final_confirmation_summary(confirmation: dict[str, Any]) -> dict[str, Any]:
    return {
        "contentReadFinalConfirmationId": confirmation["contentReadFinalConfirmationId"],
        "contentReadPlanModelReady": confirmation["contentReadPlanModelReady"],
        "contentReadFinalConfirmationModelReady": confirmation["contentReadFinalConfirmationModelReady"],
        "readyForRealDependencyContentReadonlyReadTask": (
            confirmation["readyForRealDependencyContentReadonlyReadTask"]
        ),
        "dependencyContentReadAuthorized": confirmation["dependencyContentReadAuthorized"],
        "dependencyContentReadExecuted": confirmation["dependencyContentReadExecuted"],
        "dependencyContentReturned": confirmation["dependencyContentReturned"],
        "contentReadFinalConfirmationArtifactWritten": (
            confirmation["contentReadFinalConfirmationArtifactWritten"]
        ),
        "contentReadExecutionTaskCreated": confirmation["contentReadExecutionTaskCreated"],
        "contentReadExecutionApprovalGranted": confirmation["contentReadExecutionApprovalGranted"],
        "patchGenerated": confirmation["patchGenerated"],
        "commandExecuted": confirmation["commandExecuted"],
        "dependencyInstallExecuted": confirmation["dependencyInstallExecuted"],
        "secretPresenceChecked": confirmation["secretPresenceChecked"],
        "networkAccess": confirmation["networkAccess"],
        "realLlmCalled": confirmation["realLlmCalled"],
    }


def _content_read_execution_checklist(
    request: RealSdkDependencyContentReadReadonlyExecutionRequest,
    *,
    final_confirmation_ready: bool,
) -> list[dict[str, Any]]:
    return [
        {"id": "content_read_final_confirmation_model_ready", "passed": final_confirmation_ready, "required": True},
        {
            "id": "content_read_execution_scope_confirmed",
            "passed": request.content_read_execution_scope_confirmed,
            "required": True,
        },
        {
            "id": "content_read_execution_approver_confirmed",
            "passed": request.content_read_execution_approver_confirmed,
            "required": True,
        },
        {
            "id": "content_read_execution_ticket_confirmed",
            "passed": request.content_read_execution_ticket_confirmed,
            "required": True,
        },
        {
            "id": "readonly_dependency_content_read_confirmed",
            "passed": request.readonly_dependency_content_read_confirmed,
            "required": True,
        },
        {
            "id": "manifest_content_read_confirmed",
            "passed": request.manifest_content_read_confirmed,
            "required": True,
        },
        {
            "id": "lockfile_content_read_confirmed",
            "passed": request.lockfile_content_read_confirmed,
            "required": True,
        },
        {
            "id": "redaction_before_return_confirmed",
            "passed": request.redaction_before_return_confirmed,
            "required": True,
        },
        {
            "id": "no_raw_content_return_execution_confirmed",
            "passed": request.no_raw_content_return_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_content_persistence_execution_confirmed",
            "passed": request.no_content_persistence_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_content_artifact_write_execution_confirmed",
            "passed": request.no_content_artifact_write_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_patch_generation_after_content_read_execution_confirmed",
            "passed": request.no_patch_generation_after_content_read_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_command_execution_after_content_read_execution_confirmed",
            "passed": request.no_command_execution_after_content_read_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_dependency_install_after_content_read_execution_confirmed",
            "passed": request.no_dependency_install_after_content_read_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_secret_presence_check_after_content_read_execution_confirmed",
            "passed": request.no_secret_presence_check_after_content_read_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_network_after_content_read_execution_confirmed",
            "passed": request.no_network_after_content_read_execution_confirmed,
            "required": True,
        },
        {
            "id": "no_real_call_after_content_read_execution_confirmed",
            "passed": request.no_real_call_after_content_read_execution_confirmed,
            "required": True,
        },
    ]


def _validate_provider_scope(request: RealSdkDependencyContentReadReadonlyExecutionRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "真实 SDK 依赖 content read readonly execution 当前只允许 OpenAI 单 Provider 范围",
            [
                {
                    "field": "provider",
                    "reason": "only openai is allowed in dependency content read readonly execution",
                }
            ],
        )


def _safe_candidate_paths(root: Path) -> list[dict[str, Any]]:
    candidates = []
    for kind, names in [("manifest", MANIFEST_CANDIDATES), ("lockfile", LOCKFILE_CANDIDATES)]:
        for name in names:
            path = (root / name).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError:
                continue
            candidates.append(
                {
                    "kind": kind,
                    "path": path,
                    "relativePath": name,
                    "exists": path.exists() and path.is_file(),
                }
            )
    return candidates


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[=:]\s*)[^\s#]+"),
    re.compile(r"(?i)(://[^:/\s]+:)[^@\s]+(@)"),
]


def _redact_dependency_content(content: str) -> tuple[str, int]:
    redacted = content
    replacements = 0
    for pattern in SECRET_PATTERNS:
        redacted, count = pattern.subn(lambda match: match.group(1) + "[REDACTED]" if match.groups() else "[REDACTED]", redacted)
        replacements += count
    return redacted, replacements


def _package_mentions(redacted_content: str) -> list[str]:
    mentions: list[str] = []
    for line in redacted_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("["):
            continue
        match = re.match(r"([A-Za-z0-9_.\-]+)", stripped)
        if match:
            value = match.group(1)
            if value not in mentions:
                mentions.append(value)
        if len(mentions) >= 20:
            break
    return mentions


def _read_dependency_file(entry: dict[str, Any]) -> dict[str, Any]:
    path: Path = entry["path"]
    raw_bytes = path.read_bytes()
    truncated = len(raw_bytes) > MAX_READ_BYTES
    content = raw_bytes[:MAX_READ_BYTES].decode("utf-8", errors="replace")
    redacted, redaction_count = _redact_dependency_content(content)
    preview_lines = redacted.splitlines()[:MAX_PREVIEW_LINES]
    return {
        "kind": entry["kind"],
        "relativePath": entry["relativePath"],
        "exists": True,
        "readBytes": min(len(raw_bytes), MAX_READ_BYTES),
        "truncated": truncated,
        "lineCount": len(content.splitlines()),
        "redactionCount": redaction_count,
        "redactedPreviewLines": preview_lines,
        "redactedSha256": hashlib.sha256(redacted.encode("utf-8")).hexdigest(),
        "packageMentions": _package_mentions(redacted),
        "rawContentReturned": False,
        "contentPersisted": False,
    }


def _readonly_content_read_model(files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "executionId": REAL_SDK_DEPENDENCY_CONTENT_READ_READONLY_EXECUTION_ID,
        "readonlyRead": True,
        "materializedNow": False,
        "writeNow": False,
        "persistNow": False,
        "executeCommandNow": False,
        "installNow": False,
        "secretCheckNow": False,
        "networkNow": False,
        "realCallNow": False,
        "allowlistedManifestCandidates": list(MANIFEST_CANDIDATES),
        "allowlistedLockfileCandidates": list(LOCKFILE_CANDIDATES),
        "files": files,
        "summary": {
            "filesRead": len(files),
            "manifestFilesRead": sum(1 for item in files if item["kind"] == "manifest"),
            "lockfileFilesRead": sum(1 for item in files if item["kind"] == "lockfile"),
            "rawContentReturned": False,
            "contentPersisted": False,
        },
        "blockedActions": [
            {"id": "return_raw_dependency_content", "allowedNow": False},
            {"id": "persist_dependency_content", "allowedNow": False},
            {"id": "write_content_read_artifact", "allowedNow": False},
            {"id": "generate_dependency_patch", "allowedNow": False},
            {"id": "materialize_command", "allowedNow": False},
            {"id": "execute_command", "allowedNow": False},
            {"id": "install_sdk_dependency", "allowedNow": False},
            {"id": "check_secret_presence", "allowedNow": False},
            {"id": "network_call", "allowedNow": False},
            {"id": "real_llm_call", "allowedNow": False},
        ],
    }


def _future_change_envelope() -> dict[str, bool]:
    return {
        "dependencyContentReturned": False,
        "rawDependencyContentReturned": False,
        "dependencyContentPersisted": False,
        "contentReadReadonlyExecutionRecordPersisted": False,
        "contentReadReadonlyExecutionArtifactWritten": False,
        "targetFileWritten": False,
        "commandExecutionAuthorized": False,
        "commandExecuted": False,
        "dependencyFileMutationAuthorized": False,
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
        "realCallAfterContentReadReadonlyExecutionAuthorized": False,
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
            {"field": "raw_dependency_content_return", "reason": "not_allowed_after_redacted_read"},
            {"field": "dependency_content_persistence", "reason": "not_allowed_after_redacted_read"},
            {"field": "content_read_artifact_write", "reason": "not_allowed_after_redacted_read"},
            {"field": "patch_generation", "reason": "not_allowed_after_redacted_read"},
            {"field": "command_execution", "reason": "not_allowed_after_redacted_read"},
            {"field": "dependency_install", "reason": "not_allowed_after_redacted_read"},
            {"field": "secret_presence_check", "reason": "not_allowed_after_redacted_read"},
            {"field": "network_call", "reason": "not_allowed_after_redacted_read"},
            {"field": "real_llm_call", "reason": "not_allowed_after_redacted_read"},
        ]
    )
    return reasons


def _test_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "test_real_sdk_dependency_content_read_readonly_execution",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_readonly_execution.py",
        },
        {
            "id": "test_real_sdk_dependency_content_read_final_confirmation",
            "status": "REQUIRED_NOW",
            "command": "python -m pytest tests/test_real_sdk_dependency_content_read_final_confirmation.py",
        },
        {"id": "test_all", "status": "REQUIRED_BEFORE_SDK_INSTALL", "command": "python -m pytest"},
    ]


def build_real_sdk_dependency_content_read_readonly_execution_error_context(
    exc: ProviderError,
    *,
    request: RealSdkDependencyContentReadReadonlyExecutionRequest,
    root: Path = ROOT,
) -> dict[str, Any]:
    context = _base_context(request, root=root)
    try:
        confirmation = build_real_sdk_dependency_content_read_final_confirmation(request, root=ROOT)
    except ProviderError:
        confirmation = None
    if confirmation is not None:
        context["contentReadFinalConfirmationModelReady"] = bool(
            confirmation.get("readyForRealDependencyContentReadonlyReadTask", False)
        )
        context["contentReadFinalConfirmationSummary"] = _final_confirmation_summary(confirmation)
    return {**context, "errorCode": exc.code}


def build_real_sdk_dependency_content_read_readonly_execution(
    request: RealSdkDependencyContentReadReadonlyExecutionRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_provider_scope(request)
    context = _base_context(request, root=root)
    confirmation = build_real_sdk_dependency_content_read_final_confirmation(request, root=ROOT)
    final_ready = confirmation.get("readyForRealDependencyContentReadonlyReadTask") is True
    checklist = _content_read_execution_checklist(request, final_confirmation_ready=final_ready)
    checklist_passed = all(item["passed"] is True for item in checklist if item["required"] is True)

    files: list[dict[str, Any]] = []
    if checklist_passed:
        for entry in _safe_candidate_paths(root):
            if entry["exists"]:
                files.append(_read_dependency_file(entry))

    files_read = len(files)
    manifest_read = any(item["kind"] == "manifest" for item in files)
    lockfile_read = any(item["kind"] == "lockfile" for item in files)

    return {
        **context,
        "contentReadFinalConfirmationModelReady": final_ready,
        "contentReadFinalConfirmationSummary": _final_confirmation_summary(confirmation),
        "contentReadExecutionChecklist": checklist,
        "contentReadReadonlyExecutionModelReady": checklist_passed,
        "dependencyContentReadAuthorized": checklist_passed,
        "dependencyContentReadExecuted": checklist_passed and files_read > 0,
        "dependencyManifestContentRead": manifest_read,
        "dependencyLockfileContentRead": lockfile_read,
        "dependencyFileRead": checklist_passed and files_read > 0,
        "liveDependencyFileRead": checklist_passed and files_read > 0,
        "redactedDependencyContentPreviewReturned": checklist_passed and files_read > 0,
        "dependencyContentReturned": False,
        "rawDependencyContentReturned": False,
        "dependencyContentPersisted": False,
        "contentReadReadonlyExecutionModel": _readonly_content_read_model(files),
        "futureChangeEnvelope": _future_change_envelope(),
        "testMatrix": _test_matrix(),
        "blockedUntil": _blocked_until(checklist),
        "message": "真实 SDK 依赖 content read readonly execution 已完成本地只读读取和脱敏预览；当前不会返回原文、持久化内容或记录、写产物、生成 patch、物化或执行命令、安装依赖、读取密钥、联网或真实调用。",
    }
