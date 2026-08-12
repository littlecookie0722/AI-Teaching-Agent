import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestReviewPackageRequest,
    build_real_llm_request_review_package,
    build_real_llm_request_review_package_error_context,
    describe_real_llm_request_review_package,
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
        "explicit_request_review_opt_in": True,
        "client_boundary_confirmed": True,
        "prompt_scope_confirmed": True,
        "schema_validation_confirmed": True,
        "audit_redaction_confirmed": True,
        "human_review_policy_confirmed": True,
        "no_request_send_confirmed": True,
        "no_network_call_confirmed": True,
        "no_real_llm_call_confirmed": True,
        "payload": {
            "source": "examples/input/demo-source.md",
            "api_key": "fake-secret-that-must-be-redacted",
            "note": "Bearer abcdefghijklmnopqrstuvwxyz",
        },
    }
    payload.update(overrides)
    return RealLlmRequestReviewPackageRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-llm-request-review",
        "package",
        "--provider",
        "openai",
        "--payload",
        '{"source":"examples/input/demo-source.md","api_key":"fake-secret-that-must-be-redacted"}',
        "--reviewer",
        "teacher_1",
        "--approval-ref",
        "REQ-REVIEW-001",
        "--explicit-request-review-opt-in",
        "--confirm-client-boundary",
        "--confirm-prompt-scope",
        "--confirm-schema-validation",
        "--confirm-audit-redaction",
        "--confirm-human-review-policy",
        "--confirm-no-request-send",
        "--confirm-no-network-call",
        "--confirm-no-real-llm-call",
    ]


def assert_no_real_call(context):
    assert context["sdkImported"] is False
    assert context["clientCreated"] is False
    assert context["secretPresenceChecked"] is False
    assert context["secretValueRead"] is False
    assert context["secretValueReturned"] is False
    assert context["secretValueLogged"] is False
    assert context["requestSent"] is False
    assert context["networkAccess"] is False
    assert context["realLlmCalled"] is False
    assert context["generatedContentCreated"] is False
    assert context["taskCreated"] is False
    assert context["autoPublishAllowed"] is False
    assert context["realPublish"] is False
    assert context["realCallAuthorized"] is False


def test_contract_declares_request_review_package_only():
    contract = load_json("providers/real-llm-request-review-package.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_REVIEW_PACKAGE_ONLY"
    assert contract["supportedProvider"] == "openai"
    assert contract["rules"]["requiresExplicitRequestReviewOptIn"] is True
    assert contract["assertions"]["requestShapeBuilt"] is True
    assert contract["assertions"]["requestSent"] is False
    assert contract["assertions"]["networkAccess"] is False
    assert contract["assertions"]["realLlmCalled"] is False


def test_describe_is_safe_and_does_not_build_request_shape():
    descriptor = describe_real_llm_request_review_package(root=ROOT)

    assert descriptor["requestReviewPackageId"] == "real_llm_request_review_package"
    assert descriptor["requestShapeBuilt"] is False
    assert descriptor["requestReviewPackageBuilt"] is False
    assert descriptor["readyForManualRequestReview"] is False
    assert_no_real_call(descriptor)


def test_package_requires_confirmations():
    request = RealLlmRequestReviewPackageRequest(provider_id="openai")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_review_package(request, root=ROOT)

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_review_package_error_context(exc, request=request, root=ROOT)
    assert context["requestReviewPackageBuilt"] is False
    assert_no_real_call(context)


def test_package_rejects_out_of_scope_prompt():
    request = confirmed_request(prompt_id="exam_generation_v0")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_review_package(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_review_package_error_context(exc_info.value, request=request, root=ROOT)
    assert context["promptId"] == "exam_generation_v0"
    assert_no_real_call(context)


def test_package_builds_redacted_request_shape_without_sending():
    secret = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_review_package(confirmed_request(), root=ROOT)

    assert result["requestShapeBuilt"] is True
    assert result["requestReviewPackageReady"] is True
    assert result["readyForManualRequestReview"] is True
    assert result["readyForFirstRealCallApproval"] is False
    assert result["requestShape"]["responseFormat"]["schemaRef"] == "templates/lab/lab.schema.json"
    assert result["requestShape"]["sendAllowed"] is False
    assert result["redactedPayloadPreview"]["api_key"] == "[REDACTED]"
    assert result["requestShape"]["payloadPreview"]["api_key"] == "[REDACTED]"
    assert secret not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_cli_describe_returns_json_envelope(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-request-review", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestReviewPackageBuilt"] is False
    assert_no_real_call(payload["data"])


def test_cli_package_missing_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-review", "package", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestReviewPackageContext"]
    assert context["requestReviewPackageBuilt"] is False
    assert_no_real_call(context)


def test_cli_package_builds_review_package_without_leaking_payload_secret(capsys):
    secret = "fake-secret-that-must-be-redacted"
    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestReviewPackageReady"] is True
    assert payload["data"]["requestShape"]["sendAllowed"] is False
    assert secret not in json.dumps(payload, ensure_ascii=False)
    assert_no_real_call(payload["data"])
