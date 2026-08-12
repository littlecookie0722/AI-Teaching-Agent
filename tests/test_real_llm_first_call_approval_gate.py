import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmFirstCallApprovalGateRequest,
    build_real_llm_first_call_approval_gate_error_context,
    describe_real_llm_first_call_approval_gate,
    evaluate_real_llm_first_call_approval_gate,
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
        "payload": {
            "source": "examples/input/demo-source.md",
            "api_key": "fake-secret-that-must-be-redacted",
            "note": "Bearer abcdefghijklmnopqrstuvwxyz",
        },
        "reviewer": "teacher_1",
        "approval_ref": "FIRST-CALL-APPROVAL-001",
        "explicit_request_review_opt_in": True,
        "client_boundary_confirmed": True,
        "prompt_scope_confirmed": True,
        "schema_validation_confirmed": True,
        "audit_redaction_confirmed": True,
        "human_review_policy_confirmed": True,
        "no_request_send_confirmed": True,
        "no_network_call_confirmed": True,
        "no_real_llm_call_confirmed": True,
        "explicit_first_call_approval_opt_in": True,
        "request_review_package_confirmed": True,
        "approver_identity_confirmed": True,
        "approval_record_confirmed": True,
        "secret_injection_runtime_confirmed": True,
        "network_egress_window_confirmed": True,
        "cost_limit_confirmed": True,
        "model_alias_confirmed": True,
        "timeout_retry_confirmed": True,
        "schema_enforcement_confirmed": True,
        "audit_log_redaction_confirmed": True,
        "rollback_plan_confirmed": True,
        "post_call_validation_confirmed": True,
        "no_send_in_gate_confirmed": True,
        "no_task_creation_in_gate_confirmed": True,
        "no_publish_in_gate_confirmed": True,
    }
    payload.update(overrides)
    return RealLlmFirstCallApprovalGateRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-llm-first-call-approval",
        "evaluate",
        "--provider",
        "openai",
        "--payload",
        '{"source":"examples/input/demo-source.md","api_key":"fake-secret-that-must-be-redacted"}',
        "--reviewer",
        "teacher_1",
        "--approval-ref",
        "FIRST-CALL-APPROVAL-001",
        "--explicit-request-review-opt-in",
        "--confirm-client-boundary",
        "--confirm-prompt-scope",
        "--confirm-schema-validation",
        "--confirm-audit-redaction",
        "--confirm-human-review-policy",
        "--confirm-no-request-send",
        "--confirm-no-network-call",
        "--confirm-no-real-llm-call",
        "--explicit-first-call-approval-opt-in",
        "--confirm-request-review-package",
        "--confirm-approver-identity",
        "--confirm-approval-record",
        "--confirm-secret-injection-runtime",
        "--confirm-network-egress-window",
        "--confirm-cost-limit",
        "--confirm-model-alias",
        "--confirm-timeout-retry",
        "--confirm-schema-enforcement",
        "--confirm-audit-log-redaction",
        "--confirm-rollback-plan",
        "--confirm-post-call-validation",
        "--confirm-no-send-in-gate",
        "--confirm-no-task-creation-in-gate",
        "--confirm-no-publish-in-gate",
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


def test_contract_declares_first_call_approval_gate_only():
    contract = load_json("providers/real-llm-first-call-approval-gate.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_FIRST_CALL_APPROVAL_GATE_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_review_package"
    assert contract["rules"]["requiresRequestReviewPackageReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["assertions"]["firstCallApprovalGateReady"] is True
    assert contract["assertions"]["readyForFirstRealCallApproval"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["assertions"]["realLlmCalled"] is False


def test_describe_is_safe_and_does_not_evaluate_approval():
    descriptor = describe_real_llm_first_call_approval_gate(root=ROOT)

    assert descriptor["firstCallApprovalGateId"] == "real_llm_first_call_approval_gate"
    assert descriptor["approvalGateOnly"] is True
    assert descriptor["requestReviewPackageReady"] is False
    assert descriptor["firstCallApprovalGateReady"] is False
    assert descriptor["manualApprovalGranted"] is False
    assert_no_real_call(descriptor)


def test_gate_requires_request_review_package_before_final_approval():
    with pytest.raises(ProviderError) as exc_info:
        evaluate_real_llm_first_call_approval_gate(
            RealLlmFirstCallApprovalGateRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_first_call_approval_gate_error_context(
        exc,
        request=RealLlmFirstCallApprovalGateRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestReviewPackageReady"] is False
    assert context["firstCallApprovalGateReady"] is False
    assert_no_real_call(context)


def test_gate_ready_still_does_not_authorize_or_send():
    secret = "fake-secret-that-must-be-redacted"
    result = evaluate_real_llm_first_call_approval_gate(confirmed_request(), root=ROOT)

    assert result["requestReviewPackageReady"] is True
    assert result["requestReviewPackageSummary"]["requestReviewPackageReady"] is True
    assert result["firstCallApprovalChecklistReady"] is True
    assert result["firstCallApprovalGateReady"] is True
    assert result["readyForDisabledFirstCallExecutor"] is True
    assert result["readyForFirstRealCallApproval"] is False
    assert result["manualApprovalGranted"] is False
    assert result["manualApprovalPackageMaterialized"] is False
    assert result["manualApprovalPackage"]["executorDispatchAllowedNow"] is False
    assert result["manualApprovalPackage"]["requestSendAllowedNow"] is False
    assert secret not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_gate_with_missing_final_flags_is_not_ready():
    result = evaluate_real_llm_first_call_approval_gate(
        confirmed_request(
            request_review_package_confirmed=False,
            approver_identity_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["firstCallApprovalChecklist"]}

    assert result["requestReviewPackageReady"] is True
    assert result["firstCallApprovalGateReady"] is False
    assert result["readyForDisabledFirstCallExecutor"] is False
    assert checklist["request_review_package_ready"]["passed"] is True
    assert checklist["request_review_package_confirmed"]["passed"] is False
    assert checklist["approver_identity_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        evaluate_real_llm_first_call_approval_gate(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_first_call_approval_gate_error_context(exc_info.value, request=request, root=ROOT)
    assert context["providerId"] == "anthropic"
    assert context["firstCallApprovalGateReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_evaluate_return_json(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-first-call-approval", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["firstCallApprovalGateReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestReviewPackageReady"] is True
    assert payload["data"]["firstCallApprovalGateReady"] is True
    assert payload["data"]["readyForDisabledFirstCallExecutor"] is True
    assert payload["data"]["readyForFirstRealCallApproval"] is False
    assert_no_real_call(payload["data"])


def test_cli_evaluate_missing_review_package_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-first-call-approval", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmFirstCallApprovalGateContext"]
    assert context["requestReviewPackageReady"] is False
    assert context["firstCallApprovalGateReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-first-call-approval",
            "evaluate",
            "--provider",
            "openai",
            "--payload",
            "not-json",
        ],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"
