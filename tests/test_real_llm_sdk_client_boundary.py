import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmSdkClientBoundaryRequest,
    build_real_llm_sdk_client_boundary_error_context,
    check_real_llm_sdk_client_boundary,
    describe_real_llm_sdk_client_boundary,
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


def confirmed_request(**overrides):
    payload = {
        "provider_id": "openai",
        "explicit_sdk_boundary_opt_in": True,
        "explicit_client_boundary_opt_in": True,
        "confirm_sdk_import": True,
        "confirm_client_construction": True,
        "confirm_secret_value_handling": True,
        "confirm_no_network_call": True,
        "confirm_no_real_llm_call": True,
    }
    payload.update(overrides)
    return RealLlmSdkClientBoundaryRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-llm-sdk-client-boundary",
        "check",
        "--provider",
        "openai",
        "--explicit-sdk-boundary-opt-in",
        "--explicit-client-boundary-opt-in",
        "--confirm-sdk-import",
        "--confirm-client-construction",
        "--confirm-secret-value-handling",
        "--confirm-no-network-call",
        "--confirm-no-real-llm-call",
    ]


def assert_no_real_call(context):
    assert context["networkAccess"] is False
    assert context["realLlmCalled"] is False
    assert context["generatedContentCreated"] is False
    assert context["taskCreated"] is False
    assert context["autoPublishAllowed"] is False
    assert context["realPublish"] is False
    assert context["realCallAuthorized"] is False
    assert context["secretValueReturned"] is False
    assert context["secretValueLogged"] is False


def test_contract_declares_client_boundary_only():
    contract = load_json("providers/real-llm-sdk-client-boundary.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_SDK_CLIENT_BOUNDARY_ONLY"
    assert contract["supportedProvider"] == "openai"
    assert contract["rules"]["requiresExplicitClientBoundaryOptIn"] is True
    assert contract["assertions"]["sdkImported"] is True
    assert contract["assertions"]["clientCreated"] is True
    assert contract["assertions"]["networkAccess"] is False
    assert contract["assertions"]["realLlmCalled"] is False


def test_describe_is_safe_and_does_not_construct_client():
    descriptor = describe_real_llm_sdk_client_boundary(root=ROOT)

    assert descriptor["clientBoundaryId"] == "real_llm_sdk_client_boundary"
    assert descriptor["sdkImportAttempted"] is False
    assert descriptor["sdkImported"] is False
    assert descriptor["clientConstructionAttempted"] is False
    assert descriptor["clientCreated"] is False
    assert descriptor["secretValueRead"] is False
    assert descriptor["clientBoundaryChecked"] is False
    assert_no_real_call(descriptor)


def test_client_boundary_requires_confirmations():
    request = RealLlmSdkClientBoundaryRequest(provider_id="openai")

    with pytest.raises(ProviderError) as exc_info:
        check_real_llm_sdk_client_boundary(request, root=ROOT)

    exc = exc_info.value
    assert exc.code == "REAL_LLM_SDK_CLIENT_BOUNDARY_CONFIRMATION_REQUIRED"
    context = build_real_llm_sdk_client_boundary_error_context(exc, request=request, root=ROOT)
    assert context["clientBoundaryChecked"] is False
    assert context["sdkImported"] is False
    assert context["clientCreated"] is False
    assert_no_real_call(context)


def test_client_boundary_requires_secret(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ProviderError) as exc_info:
        check_real_llm_sdk_client_boundary(confirmed_request(), root=ROOT)

    exc = exc_info.value
    assert exc.code == "REAL_LLM_SDK_CLIENT_SECRET_REQUIRED"
    context = build_real_llm_sdk_client_boundary_error_context(exc, request=confirmed_request(), root=ROOT)
    assert context["clientBoundaryChecked"] is False
    assert context["clientCreated"] is False
    assert_no_real_call(context)


def test_client_boundary_constructs_client_without_leaking_secret(monkeypatch):
    secret = "test-client-boundary-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    result = check_real_llm_sdk_client_boundary(confirmed_request(), root=ROOT)

    assert result["sdkBoundaryChecked"] is True
    assert result["sdkBoundaryReady"] is True
    assert result["sdkImportAttempted"] is True
    assert result["sdkImported"] is True
    assert result["clientConstructionAttempted"] is True
    assert result["clientCreated"] is True
    assert result["clientClassName"] == "OpenAI"
    assert result["secretPresenceChecked"] is True
    assert result["secretPresent"] is True
    assert result["secretValueRead"] is True
    assert result["clientBoundaryReady"] is True
    assert result["readyForFirstDryRunRequestReview"] is True
    assert secret not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        check_real_llm_sdk_client_boundary(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_sdk_client_boundary_error_context(exc_info.value, request=request, root=ROOT)
    assert context["providerId"] == "anthropic"
    assert context["sdkImported"] is False
    assert context["clientCreated"] is False
    assert_no_real_call(context)


def test_cli_describe_returns_json_envelope(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-sdk-client-boundary", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["clientBoundaryChecked"] is False
    assert payload["data"]["clientCreated"] is False
    assert_no_real_call(payload["data"])


def test_cli_check_requires_secret_and_returns_safe_error(capsys, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_SDK_CLIENT_SECRET_REQUIRED"
    context = payload["realLlmSdkClientBoundaryContext"]
    assert context["clientBoundaryChecked"] is False
    assert context["clientCreated"] is False
    assert_no_real_call(context)


def test_cli_check_constructs_client_without_leaking_secret(capsys, monkeypatch):
    secret = "test-cli-client-boundary-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["clientCreated"] is True
    assert payload["data"]["clientBoundaryReady"] is True
    assert secret not in json.dumps(payload, ensure_ascii=False)
    assert_no_real_call(payload["data"])
