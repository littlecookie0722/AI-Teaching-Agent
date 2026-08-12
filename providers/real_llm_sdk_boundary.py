"""Real LLM SDK installation and environment boundary.

This boundary checks local dependency declaration, installed package metadata,
and optional environment variable name presence. It does not import the SDK,
create a client, read secret values, access the network, call a real model,
create content, create tasks, or publish anything.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import metadata, util
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError


ROOT = Path(__file__).resolve().parents[1]
REAL_LLM_SDK_BOUNDARY_ID = "real_llm_sdk_boundary"
SUPPORTED_PROVIDER = "openai"
SDK_DISTRIBUTION = "openai"
SDK_IMPORT_NAME = "openai"
SECRET_ENV = "OPENAI_API_KEY"


@dataclass(frozen=True)
class RealLlmSdkBoundaryRequest:
    provider_id: str = SUPPORTED_PROVIDER
    explicit_sdk_boundary_opt_in: bool = False
    check_secret_presence: bool = False
    trace_id: str | None = None


def _dependency_manifest_context(*, root: Path) -> dict[str, Any]:
    requirements_path = root / "requirements.txt"
    declared = False
    specifier = None
    if requirements_path.exists():
        for line in requirements_path.read_text(encoding="utf-8").splitlines():
            clean = line.split("#", 1)[0].strip()
            if not clean:
                continue
            if clean.lower().startswith(SDK_DISTRIBUTION):
                declared = True
                specifier = clean
                break
    return {
        "dependencyManifestPath": "requirements.txt",
        "dependencyManifestRead": requirements_path.exists(),
        "sdkDependencyDeclared": declared,
        "sdkDependencySpecifier": specifier,
    }


def _sdk_metadata_context() -> dict[str, Any]:
    try:
        version = metadata.version(SDK_DISTRIBUTION)
        installed = True
    except metadata.PackageNotFoundError:
        version = None
        installed = False

    return {
        "sdkDistribution": SDK_DISTRIBUTION,
        "sdkImportName": SDK_IMPORT_NAME,
        "sdkMetadataResolved": installed,
        "sdkDependencyInstalled": installed,
        "sdkVersion": version,
        "sdkImportable": util.find_spec(SDK_IMPORT_NAME) is not None,
        "sdkImportMetadataChecked": True,
        "sdkImportAttempted": False,
        "sdkImported": False,
    }


def _secret_presence_context(*, check_secret_presence: bool) -> dict[str, Any]:
    return {
        "secretEnv": SECRET_ENV,
        "secretPresenceCheckRequested": check_secret_presence,
        "secretPresenceChecked": check_secret_presence,
        "secretPresent": SECRET_ENV in os.environ if check_secret_presence else False,
        "secretValueRead": False,
        "secretValueReturned": False,
    }


def _base_context(
    request: RealLlmSdkBoundaryRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    return {
        "boundaryId": REAL_LLM_SDK_BOUNDARY_ID,
        "providerId": request.provider_id,
        "supportedProvider": SUPPORTED_PROVIDER,
        "phase": "Phase 2",
        "mode": "REAL_SDK_BOUNDARY_ONLY",
        "envExamplePath": ".env.example",
        "explicitSdkBoundaryOptIn": request.explicit_sdk_boundary_opt_in,
        "allowedProvider": SUPPORTED_PROVIDER,
        "allowedChecks": [
            "dependency_manifest_declaration",
            "local_sdk_package_metadata",
            "secret_environment_variable_name_presence",
        ],
        "blockedOperations": [
            "sdk_import",
            "client_creation",
            "secret_value_read",
            "network_request",
            "real_llm_call",
            "content_creation",
            "task_creation",
            "publish",
        ],
        "dependencyManifestPath": "requirements.txt",
        "dependencyManifestRead": False,
        "sdkDependencyDeclared": False,
        "sdkDependencySpecifier": None,
        "sdkDistribution": SDK_DISTRIBUTION,
        "sdkImportName": SDK_IMPORT_NAME,
        "sdkMetadataResolved": False,
        "sdkDependencyInstalled": False,
        "sdkVersion": None,
        "sdkImportable": False,
        "sdkImportMetadataChecked": False,
        "sdkImportAttempted": False,
        "sdkImported": False,
        "clientCreated": False,
        "secretEnv": SECRET_ENV,
        "secretPresenceCheckRequested": request.check_secret_presence,
        "secretPresenceChecked": False,
        "secretPresent": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "autoPublishAllowed": False,
        "realPublish": False,
        "dependencyInstallExecutedByBoundary": False,
        "sdkBoundaryChecked": False,
        "sdkBoundaryReady": False,
        "readyForRealLlmSdkCallReview": False,
        "realCallAuthorized": False,
        "traceId": request.trace_id,
    }


def describe_real_llm_sdk_boundary(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmSdkBoundaryRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresExplicitSdkBoundaryOptIn": True,
        "checksPackageMetadataOnly": True,
        "checksSecretPresenceOnly": True,
        "secretValueMustNotBeReturned": True,
        "realCallAuthorizationPath": "not_implemented",
    }


def _validate_request(request: RealLlmSdkBoundaryRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM SDK boundary currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed in the real SDK boundary"}],
        )
    if not request.explicit_sdk_boundary_opt_in:
        raise ProviderError(
            "REAL_LLM_SDK_BOUNDARY_OPT_IN_REQUIRED",
            "Real LLM SDK boundary check requires explicit opt-in",
            [
                {
                    "field": "explicitSdkBoundaryOptIn",
                    "reason": "pass --explicit-sdk-boundary-opt-in to check installed SDK metadata",
                }
            ],
        )


def check_real_llm_sdk_boundary(
    request: RealLlmSdkBoundaryRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_request(request)

    dependency_context = _dependency_manifest_context(root=root)
    sdk_context = _sdk_metadata_context()
    secret_context = _secret_presence_context(check_secret_presence=request.check_secret_presence)
    sdk_ready = dependency_context["sdkDependencyDeclared"] and sdk_context["sdkDependencyInstalled"]
    env_ready = secret_context["secretPresent"] if request.check_secret_presence else True
    ready_for_review = sdk_ready and env_ready

    blockers: list[str] = []
    if not dependency_context["sdkDependencyDeclared"]:
        blockers.append("openai_dependency_not_declared")
    if not sdk_context["sdkDependencyInstalled"]:
        blockers.append("openai_sdk_not_installed")
    if request.check_secret_presence and not secret_context["secretPresent"]:
        blockers.append("openai_api_key_env_not_present")

    return {
        **_base_context(request, root=root),
        **dependency_context,
        **sdk_context,
        **secret_context,
        "sdkBoundaryChecked": True,
        "sdkBoundaryReady": sdk_ready,
        "readyForRealLlmSdkCallReview": ready_for_review,
        "realCallAuthorized": False,
        "blockers": blockers,
    }


def build_real_llm_sdk_boundary_error_context(
    exc: ProviderError,
    *,
    request: RealLlmSdkBoundaryRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmSdkBoundaryRequest()
    return {
        **_base_context(request, root=root),
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
