"""Real LLM SDK client construction boundary.

This boundary is the step after package installation checks. With explicit
operator opt-in it imports the installed OpenAI SDK and constructs a local
client object from environment configuration. It must not call any model API,
perform network requests, create generated content, create tasks, or publish.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from .mock_provider import ProviderError
from .real_llm_sdk_boundary import (
    ROOT,
    SECRET_ENV,
    SDK_DISTRIBUTION,
    SDK_IMPORT_NAME,
    SUPPORTED_PROVIDER,
    RealLlmSdkBoundaryRequest,
    check_real_llm_sdk_boundary,
)


REAL_LLM_SDK_CLIENT_BOUNDARY_ID = "real_llm_sdk_client_boundary"


@dataclass(frozen=True)
class RealLlmSdkClientBoundaryRequest:
    provider_id: str = SUPPORTED_PROVIDER
    explicit_sdk_boundary_opt_in: bool = False
    explicit_client_boundary_opt_in: bool = False
    confirm_sdk_import: bool = False
    confirm_client_construction: bool = False
    confirm_secret_value_handling: bool = False
    confirm_no_network_call: bool = False
    confirm_no_real_llm_call: bool = False
    trace_id: str | None = None


def _base_context(
    request: RealLlmSdkClientBoundaryRequest,
    *,
    root: Path,
) -> dict[str, Any]:
    return {
        "clientBoundaryId": REAL_LLM_SDK_CLIENT_BOUNDARY_ID,
        "providerId": request.provider_id,
        "supportedProvider": SUPPORTED_PROVIDER,
        "phase": "Phase 2",
        "mode": "REAL_SDK_CLIENT_BOUNDARY_ONLY",
        "envExamplePath": ".env.example",
        "dependencyManifestPath": "requirements.txt",
        "sdkDistribution": SDK_DISTRIBUTION,
        "sdkImportName": SDK_IMPORT_NAME,
        "secretEnv": SECRET_ENV,
        "baseUrlEnv": "OPENAI_BASE_URL",
        "modelEnv": "OPENAI_MODEL",
        "explicitSdkBoundaryOptIn": request.explicit_sdk_boundary_opt_in,
        "explicitClientBoundaryOptIn": request.explicit_client_boundary_opt_in,
        "confirmations": {
            "sdkImport": request.confirm_sdk_import,
            "clientConstruction": request.confirm_client_construction,
            "secretValueHandling": request.confirm_secret_value_handling,
            "noNetworkCall": request.confirm_no_network_call,
            "noRealLlmCall": request.confirm_no_real_llm_call,
        },
        "allowedOperations": [
            "sdk_import",
            "environment_secret_value_read_for_client_constructor_only",
            "client_object_construction",
        ],
        "blockedOperations": [
            "model_request",
            "network_request",
            "real_llm_call",
            "prompt_execution",
            "generated_content_creation",
            "task_creation",
            "publish",
        ],
        "dependencyManifestRead": False,
        "sdkDependencyDeclared": False,
        "sdkDependencyInstalled": False,
        "sdkVersion": None,
        "sdkBoundaryChecked": False,
        "sdkBoundaryReady": False,
        "sdkImportAttempted": False,
        "sdkImported": False,
        "sdkImportError": None,
        "clientConstructionAttempted": False,
        "clientCreated": False,
        "clientClassName": None,
        "clientModule": None,
        "secretPresenceChecked": False,
        "secretPresent": False,
        "secretValueRead": False,
        "secretValueReturned": False,
        "secretValueLogged": False,
        "baseUrlConfigured": False,
        "baseUrlValueReturned": False,
        "modelConfigured": False,
        "modelValueReturned": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "autoPublishAllowed": False,
        "realPublish": False,
        "clientBoundaryChecked": False,
        "clientBoundaryReady": False,
        "readyForFirstDryRunRequestReview": False,
        "realCallAuthorized": False,
        "traceId": request.trace_id,
    }


def describe_real_llm_sdk_client_boundary(*, root: Path = ROOT) -> dict[str, Any]:
    request = RealLlmSdkClientBoundaryRequest(provider_id=SUPPORTED_PROVIDER)
    return {
        **_base_context(request, root=root),
        "requiresExplicitSdkBoundaryOptIn": True,
        "requiresExplicitClientBoundaryOptIn": True,
        "requiresSdkImportConfirmation": True,
        "requiresClientConstructionConfirmation": True,
        "requiresSecretValueHandlingConfirmation": True,
        "requiresNoNetworkConfirmation": True,
        "requiresNoRealLlmCallConfirmation": True,
        "realCallAuthorizationPath": "not_implemented",
    }


def _missing_confirmations(request: RealLlmSdkClientBoundaryRequest) -> list[dict[str, str]]:
    checks = [
        ("explicitSdkBoundaryOptIn", request.explicit_sdk_boundary_opt_in),
        ("explicitClientBoundaryOptIn", request.explicit_client_boundary_opt_in),
        ("confirmSdkImport", request.confirm_sdk_import),
        ("confirmClientConstruction", request.confirm_client_construction),
        ("confirmSecretValueHandling", request.confirm_secret_value_handling),
        ("confirmNoNetworkCall", request.confirm_no_network_call),
        ("confirmNoRealLlmCall", request.confirm_no_real_llm_call),
    ]
    return [
        {"field": field, "reason": "required for real SDK client construction boundary"}
        for field, passed in checks
        if not passed
    ]


def _validate_request(request: RealLlmSdkClientBoundaryRequest) -> None:
    if request.provider_id != SUPPORTED_PROVIDER:
        raise ProviderError(
            "VALIDATION_ERROR",
            "Real LLM SDK client boundary currently only supports openai",
            [{"field": "provider", "reason": "only openai is allowed in the real SDK client boundary"}],
        )
    missing = _missing_confirmations(request)
    if missing:
        raise ProviderError(
            "REAL_LLM_SDK_CLIENT_BOUNDARY_CONFIRMATION_REQUIRED",
            "Real LLM SDK client boundary requires explicit opt-in and safety confirmations",
            missing,
        )


def _sdk_version() -> str | None:
    try:
        return metadata.version(SDK_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return None


def _construct_openai_client() -> dict[str, Any]:
    secret_value = os.environ.get(SECRET_ENV)
    if not secret_value:
        raise ProviderError(
            "REAL_LLM_SDK_CLIENT_SECRET_REQUIRED",
            "OPENAI_API_KEY must be present to construct the OpenAI client boundary",
            [{"field": SECRET_ENV, "reason": "set the environment variable outside git-tracked files"}],
        )

    module = importlib.import_module(SDK_IMPORT_NAME)
    client_class = getattr(module, "OpenAI")
    kwargs: dict[str, Any] = {"api_key": secret_value}
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    client = client_class(**kwargs)
    return {
        "clientClassName": client.__class__.__name__,
        "clientModule": client.__class__.__module__,
        "baseUrlConfigured": bool(base_url),
        "modelConfigured": "OPENAI_MODEL" in os.environ and bool(os.environ.get("OPENAI_MODEL")),
    }


def check_real_llm_sdk_client_boundary(
    request: RealLlmSdkClientBoundaryRequest,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_request(request)

    sdk_boundary = check_real_llm_sdk_boundary(
        RealLlmSdkBoundaryRequest(
            provider_id=request.provider_id,
            explicit_sdk_boundary_opt_in=True,
            check_secret_presence=True,
            trace_id=request.trace_id,
        ),
        root=root,
    )
    if not sdk_boundary["sdkBoundaryReady"]:
        raise ProviderError(
            "REAL_LLM_SDK_BOUNDARY_NOT_READY",
            "Real LLM SDK package boundary must be ready before client construction",
            [{"field": "sdkBoundaryReady", "reason": "install and declare the openai dependency first"}],
        )
    if not sdk_boundary["secretPresent"]:
        raise ProviderError(
            "REAL_LLM_SDK_CLIENT_SECRET_REQUIRED",
            "OPENAI_API_KEY must be present to construct the OpenAI client boundary",
            [{"field": SECRET_ENV, "reason": "set the environment variable outside git-tracked files"}],
        )

    context = {
        **_base_context(request, root=root),
        "dependencyManifestRead": sdk_boundary["dependencyManifestRead"],
        "sdkDependencyDeclared": sdk_boundary["sdkDependencyDeclared"],
        "sdkDependencyInstalled": sdk_boundary["sdkDependencyInstalled"],
        "sdkVersion": _sdk_version(),
        "sdkBoundaryChecked": True,
        "sdkBoundaryReady": True,
        "secretPresenceChecked": True,
        "secretPresent": True,
        "secretValueRead": True,
        "sdkImportAttempted": True,
        "clientConstructionAttempted": True,
    }

    try:
        client_context = _construct_openai_client()
    except ProviderError:
        raise
    except Exception as exc:  # pragma: no cover - defensive against SDK constructor changes.
        raise ProviderError(
            "REAL_LLM_SDK_CLIENT_CONSTRUCTION_FAILED",
            "OpenAI client construction failed inside the no-call boundary",
            [{"field": "client", "reason": exc.__class__.__name__}],
        ) from exc

    return {
        **context,
        **client_context,
        "sdkImported": True,
        "clientCreated": True,
        "secretValueReturned": False,
        "secretValueLogged": False,
        "baseUrlValueReturned": False,
        "modelValueReturned": False,
        "networkAccess": False,
        "realLlmCalled": False,
        "generatedContentCreated": False,
        "taskCreated": False,
        "clientBoundaryChecked": True,
        "clientBoundaryReady": True,
        "readyForFirstDryRunRequestReview": True,
        "realCallAuthorized": False,
        "blockers": [],
    }


def build_real_llm_sdk_client_boundary_error_context(
    exc: ProviderError,
    *,
    request: RealLlmSdkClientBoundaryRequest | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request = request or RealLlmSdkClientBoundaryRequest()
    return {
        **_base_context(request, root=root),
        "errorCode": exc.code,
        "errorMessage": exc.message,
        "errors": exc.errors,
    }
