import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendAttemptGateDisabledRequest,
    build_real_llm_request_send_attempt_gate_disabled,
    build_real_llm_request_send_attempt_gate_disabled_error_context,
    describe_real_llm_request_send_attempt_gate_disabled,
)
from test_real_llm_request_send_executor_dispatch_gate_disabled import (
    assert_no_real_call as assert_dispatch_gate_no_real_call,
    confirmed_cli_args as confirmed_dispatch_gate_cli_args,
    confirmed_payload as confirmed_dispatch_gate_payload,
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


def confirmed_payload(**overrides):
    payload = confirmed_dispatch_gate_payload(
        explicit_request_send_attempt_gate_disabled_opt_in=True,
        executor_dispatch_gate_confirmed=True,
        request_send_attempt_scope_confirmed=True,
        request_send_attempt_record_confirmed=True,
        send_attempt_policy_confirmed=True,
        send_executor_reference_confirmed=True,
        executor_run_reference_for_attempt_confirmed=True,
        runtime_gate_reference_for_attempt_confirmed=True,
        authorization_record_reference_for_attempt_confirmed=True,
        provider_client_boundary_for_attempt_confirmed=True,
        secret_runtime_boundary_for_attempt_confirmed=True,
        network_egress_boundary_for_attempt_confirmed=True,
        response_validation_boundary_for_attempt_confirmed=True,
        waiting_review_policy_for_attempt_confirmed=True,
        attempt_audit_redaction_confirmed=True,
        attempt_rollback_confirmed=True,
        no_attempt_record_persistence_confirmed=True,
        no_request_send_attempt_confirmed=True,
        no_request_send_in_attempt_gate_confirmed=True,
        no_secret_read_in_attempt_gate_confirmed=True,
        no_client_creation_in_attempt_gate_confirmed=True,
        no_network_access_in_attempt_gate_confirmed=True,
        no_real_llm_call_in_attempt_gate_confirmed=True,
        no_generated_content_creation_in_attempt_gate_confirmed=True,
        no_task_creation_in_attempt_gate_confirmed=True,
        no_publish_in_attempt_gate_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendAttemptGateDisabledRequest(
        **confirmed_payload(**overrides)
    )


def confirmed_cli_args():
    args = confirmed_dispatch_gate_cli_args()
    args[1] = "real-llm-request-send-attempt-gate-disabled"
    args[2] = "evaluate"
    args.extend(
        [
            "--explicit-request-send-attempt-gate-disabled-opt-in",
            "--confirm-executor-dispatch-gate",
            "--confirm-request-send-attempt-scope",
            "--confirm-request-send-attempt-record",
            "--confirm-send-attempt-policy",
            "--confirm-send-executor-reference",
            "--confirm-executor-run-reference-for-attempt",
            "--confirm-runtime-gate-reference-for-attempt",
            "--confirm-authorization-record-reference-for-attempt",
            "--confirm-provider-client-boundary-for-attempt",
            "--confirm-secret-runtime-boundary-for-attempt",
            "--confirm-network-egress-boundary-for-attempt",
            "--confirm-response-validation-boundary-for-attempt",
            "--confirm-waiting-review-policy-for-attempt",
            "--confirm-attempt-audit-redaction",
            "--confirm-attempt-rollback",
            "--confirm-no-attempt-record-persistence",
            "--confirm-no-request-send-attempt",
            "--confirm-no-request-send-in-attempt-gate",
            "--confirm-no-secret-read-in-attempt-gate",
            "--confirm-no-client-creation-in-attempt-gate",
            "--confirm-no-network-access-in-attempt-gate",
            "--confirm-no-real-llm-call-in-attempt-gate",
            "--confirm-no-generated-content-creation-in-attempt-gate",
            "--confirm-no-task-creation-in-attempt-gate",
            "--confirm-no-publish-in-attempt-gate",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_dispatch_gate_no_real_call(context)
    assert context["attemptRecordPersisted"] is False
    assert context["requestSendAttempted"] is False
    assert context["requestSent"] is False
    assert context["clientCreated"] is False
    assert context["secretValueRead"] is False
    assert context["networkAccess"] is False
    assert context["realLlmCalled"] is False


def test_contract_declares_request_send_attempt_gate_disabled_only():
    contract = load_json("providers/real-llm-request-send-attempt-gate-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_ATTEMPT_GATE_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_executor_dispatch_gate_disabled"
    assert contract["rules"]["requiresRequestSendExecutorDispatchGateDisabledReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendAttemptGateDisabledReady"] is True
    assert contract["assertions"]["readyForFinalRealRequestSendExecution"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["attemptRecordPersisted"] is False
    assert contract["assertions"]["requestSendAttempted"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["requestSendAttemptBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_attempt_send():
    descriptor = describe_real_llm_request_send_attempt_gate_disabled(root=ROOT)

    assert descriptor["requestSendAttemptGateDisabledId"] == (
        "real_llm_request_send_attempt_gate_disabled"
    )
    assert descriptor["requestSendAttemptGateMode"] == (
        "REQUEST_SEND_ATTEMPT_GATE_DISABLED_MODEL_ONLY"
    )
    assert descriptor["requestSendExecutorDispatchGateDisabledReady"] is False
    assert descriptor["requestSendAttemptGateDisabledReady"] is False
    assert descriptor["readyForFinalRealRequestSendExecution"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_request_send_attempt_gate_requires_upstream_dispatch_gate():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_attempt_gate_disabled(
            RealLlmRequestSendAttemptGateDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_attempt_gate_disabled_error_context(
        exc,
        request=RealLlmRequestSendAttemptGateDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendExecutorDispatchGateDisabledReady"] is False
    assert context["requestSendAttemptGateDisabledReady"] is False
    assert_no_real_call(context)


def test_request_send_attempt_gate_ready_still_does_not_attempt_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_attempt_gate_disabled(
        confirmed_request(),
        root=ROOT,
    )

    assert result["requestSendExecutorDispatchGateDisabledReady"] is True
    assert result["requestSendExecutorDispatchGateDisabledSummary"]["requestSendExecutorDispatchGateDisabledReady"] is True
    assert result["requestSendAttemptGateChecklistReady"] is True
    assert result["requestSendAttemptGateDisabledReady"] is True
    assert result["readyForFinalRealRequestSendExecution"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["requestSendAttemptGateModelBuilt"] is True
    assert result["requestSendAttemptGateModel"]["attemptRecordPersistedNow"] is False
    assert result["requestSendAttemptGateModel"]["requestSendAttemptedNow"] is False
    assert result["requestSendAttemptGateModel"]["requestSentNow"] is False
    assert result["requestSendAttemptGateModel"]["clientCreationAllowedNow"] is False
    assert result["requestSendAttemptGateModel"]["realLlmCallAllowedNow"] is False
    assert result["requestSendAttemptGateModel"]["sendAllowedNow"] is False
    assert result["requestSendAttemptPolicy"]["attemptRequestSendNow"] is False
    assert result["requestSendAttemptPolicy"]["sendRequestNow"] is False
    assert result["requestSendExecutionBoundary"]["requestSendAttempted"] is False
    assert result["requestSendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_request_send_attempt_gate_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_attempt_gate_disabled(
        confirmed_request(
            request_send_attempt_scope_confirmed=False,
            no_request_send_attempt_confirmed=False,
            no_real_llm_call_in_attempt_gate_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {
        item["id"]: item
        for item in result["requestSendAttemptGateChecklist"]
    }

    assert result["requestSendExecutorDispatchGateDisabledReady"] is True
    assert result["requestSendAttemptGateDisabledReady"] is False
    assert result["readyForFinalRealRequestSendExecution"] is False
    assert checklist["request_send_executor_dispatch_gate_disabled_ready"]["passed"] is True
    assert checklist["request_send_attempt_scope_confirmed"]["passed"] is False
    assert checklist["no_request_send_attempt_confirmed"]["passed"] is False
    assert checklist["no_real_llm_call_in_attempt_gate_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_attempt_gate_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_attempt_gate_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendAttemptGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_evaluate_return_json(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-attempt-gate-disabled",
            "describe",
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendAttemptGateDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutorDispatchGateDisabledReady"] is True
    assert payload["data"]["requestSendAttemptGateDisabledReady"] is True
    assert payload["data"]["readyForFinalRealRequestSendExecution"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_evaluate_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-attempt-gate-disabled",
            "evaluate",
            "--provider",
            "openai",
        ],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendAttemptGateDisabledContext"]
    assert context["requestSendExecutorDispatchGateDisabledReady"] is False
    assert context["requestSendAttemptGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-attempt-gate-disabled",
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
