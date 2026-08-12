import json
from importlib import metadata
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmSdkBoundaryRequest,
    build_real_llm_sdk_boundary_error_context,
    check_real_llm_sdk_boundary,
    describe_real_llm_sdk_boundary,
)


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def run_cli(args, capsys):
    exit_code = main(args)
    output = capsys.readouterr().out
    payload = json.loads(output)
    return exit_code, payload


def openai_installed():
    try:
        metadata.version("openai")
        return True
    except metadata.PackageNotFoundError:
        return False


def assert_no_real_call(context):
    for key in [
        "sdkImportAttempted",
        "sdkImported",
        "clientCreated",
        "secretValueRead",
        "secretValueReturned",
        "networkAccess",
        "realLlmCalled",
        "generatedContentCreated",
        "taskCreated",
        "autoPublishAllowed",
        "realPublish",
        "dependencyInstallExecutedByBoundary",
        "realCallAuthorized",
    ]:
        assert context[key] is False


def test_contract_declares_sdk_boundary_only():
    contract = load_json("providers/real-llm-sdk-boundary.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_SDK_BOUNDARY_ONLY"
    assert contract["supportedProvider"] == "openai"
    assert contract["targetPackage"] == "openai"
    assert contract["secretEnv"] == "OPENAI_API_KEY"
    assert contract["rules"]["requiresExplicitSdkBoundaryOptIn"] is True
    for value in contract["assertions"].values():
        assert value is False


def test_describe_is_safe_and_does_not_probe_runtime_state():
    descriptor = describe_real_llm_sdk_boundary(root=ROOT)

    assert descriptor["boundaryId"] == "real_llm_sdk_boundary"
    assert descriptor["sdkBoundaryChecked"] is False
    assert descriptor["sdkDependencyInstalled"] is False
    assert descriptor["secretPresenceChecked"] is False
    assert descriptor["requiresExplicitSdkBoundaryOptIn"] is True
    assert_no_real_call(descriptor)


def test_check_requires_explicit_opt_in():
    request = RealLlmSdkBoundaryRequest(provider_id="openai")

    with pytest.raises(ProviderError) as exc_info:
        check_real_llm_sdk_boundary(request, root=ROOT)

    exc = exc_info.value
    assert exc.code == "REAL_LLM_SDK_BOUNDARY_OPT_IN_REQUIRED"
    context = build_real_llm_sdk_boundary_error_context(exc, request=request, root=ROOT)
    assert context["sdkBoundaryChecked"] is False
    assert context["errorCode"] == "REAL_LLM_SDK_BOUNDARY_OPT_IN_REQUIRED"
    assert_no_real_call(context)


def test_explicit_check_reads_dependency_and_package_metadata_without_secret_check(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = check_real_llm_sdk_boundary(
        RealLlmSdkBoundaryRequest(
            provider_id="openai",
            explicit_sdk_boundary_opt_in=True,
        ),
        root=ROOT,
    )

    assert result["sdkBoundaryChecked"] is True
    assert result["dependencyManifestRead"] is True
    assert result["sdkDependencyDeclared"] is True
    assert result["sdkDependencySpecifier"].startswith("openai")
    assert result["sdkDependencyInstalled"] is openai_installed()
    assert result["secretPresenceChecked"] is False
    assert result["secretPresent"] is False
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert_no_real_call(result)


def test_secret_presence_check_does_not_return_secret_value(monkeypatch):
    secret = "hidden-value-that-must-not-leak"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    result = check_real_llm_sdk_boundary(
        RealLlmSdkBoundaryRequest(
            provider_id="openai",
            explicit_sdk_boundary_opt_in=True,
            check_secret_presence=True,
        ),
        root=ROOT,
    )

    assert result["secretPresenceChecked"] is True
    assert result["secretPresent"] is True
    assert result["secretValueRead"] is False
    assert result["secretValueReturned"] is False
    assert secret not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = RealLlmSdkBoundaryRequest(
        provider_id="anthropic",
        explicit_sdk_boundary_opt_in=True,
    )

    with pytest.raises(ProviderError) as exc_info:
        check_real_llm_sdk_boundary(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_sdk_boundary_error_context(exc_info.value, request=request, root=ROOT)
    assert context["providerId"] == "anthropic"
    assert_no_real_call(context)


def test_cli_describe_returns_json_envelope(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-sdk-boundary", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["sdkBoundaryChecked"] is False
    assert_no_real_call(payload["data"])


def test_cli_check_returns_json_envelope(capsys, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-sdk-boundary",
            "check",
            "--provider",
            "openai",
            "--explicit-sdk-boundary-opt-in",
            "--check-secret-presence",
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["sdkBoundaryChecked"] is True
    assert payload["data"]["secretPresenceChecked"] is True
    assert payload["data"]["secretPresent"] is False
    assert_no_real_call(payload["data"])


def test_cli_check_without_opt_in_returns_safe_error_context(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-sdk-boundary", "check", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_SDK_BOUNDARY_OPT_IN_REQUIRED"
    context = payload["realLlmSdkBoundaryContext"]
    assert context["sdkBoundaryChecked"] is False
    assert_no_real_call(context)
