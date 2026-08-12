import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendExecutorDispatchGateDisabledRequest,
    build_real_llm_request_send_executor_dispatch_gate_disabled,
    build_real_llm_request_send_executor_dispatch_gate_disabled_error_context,
    describe_real_llm_request_send_executor_dispatch_gate_disabled,
)
from test_real_llm_request_send_executor_creation_gate_disabled import (
    assert_no_real_call as assert_creation_gate_no_real_call,
    confirmed_cli_args as confirmed_creation_gate_cli_args,
    confirmed_payload as confirmed_creation_gate_payload,
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
    payload = confirmed_creation_gate_payload(
        explicit_request_send_executor_dispatch_gate_disabled_opt_in=True,
        executor_creation_gate_confirmed=True,
        executor_dispatch_scope_confirmed=True,
        executor_dispatch_record_confirmed=True,
        executor_dispatch_policy_confirmed=True,
        executor_run_reference_confirmed=True,
        executor_identity_for_dispatch_confirmed=True,
        runtime_gate_reference_for_dispatch_confirmed=True,
        authorization_record_reference_for_dispatch_confirmed=True,
        dispatch_queue_boundary_confirmed=True,
        dispatch_audit_redaction_confirmed=True,
        dispatch_rollback_confirmed=True,
        dispatch_waiting_review_policy_confirmed=True,
        no_dispatch_queue_write_confirmed=True,
        no_dispatch_record_persistence_confirmed=True,
        no_executor_dispatch_in_dispatch_gate_confirmed=True,
        no_executor_start_in_dispatch_gate_confirmed=True,
        no_executor_run_creation_in_dispatch_gate_confirmed=True,
        no_request_send_in_dispatch_gate_confirmed=True,
        no_secret_read_in_dispatch_gate_confirmed=True,
        no_client_creation_in_dispatch_gate_confirmed=True,
        no_network_access_in_dispatch_gate_confirmed=True,
        no_real_call_authorization_in_dispatch_gate_confirmed=True,
        no_generated_content_creation_in_dispatch_gate_confirmed=True,
        no_task_creation_in_dispatch_gate_confirmed=True,
        no_publish_in_dispatch_gate_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendExecutorDispatchGateDisabledRequest(
        **confirmed_payload(**overrides)
    )


def confirmed_cli_args():
    args = confirmed_creation_gate_cli_args()
    args[1] = "real-llm-request-send-executor-dispatch-gate-disabled"
    args[2] = "evaluate"
    args.extend(
        [
            "--explicit-request-send-executor-dispatch-gate-disabled-opt-in",
            "--confirm-executor-creation-gate",
            "--confirm-executor-dispatch-scope",
            "--confirm-executor-dispatch-record",
            "--confirm-executor-dispatch-policy",
            "--confirm-executor-run-reference",
            "--confirm-executor-identity-for-dispatch",
            "--confirm-runtime-gate-reference-for-dispatch",
            "--confirm-authorization-record-reference-for-dispatch",
            "--confirm-dispatch-queue-boundary",
            "--confirm-dispatch-audit-redaction",
            "--confirm-dispatch-rollback",
            "--confirm-dispatch-waiting-review-policy",
            "--confirm-no-dispatch-queue-write",
            "--confirm-no-dispatch-record-persistence",
            "--confirm-no-executor-dispatch-in-dispatch-gate",
            "--confirm-no-executor-start-in-dispatch-gate",
            "--confirm-no-executor-run-creation-in-dispatch-gate",
            "--confirm-no-request-send-in-dispatch-gate",
            "--confirm-no-secret-read-in-dispatch-gate",
            "--confirm-no-client-creation-in-dispatch-gate",
            "--confirm-no-network-access-in-dispatch-gate",
            "--confirm-no-real-call-authorization-in-dispatch-gate",
            "--confirm-no-generated-content-creation-in-dispatch-gate",
            "--confirm-no-task-creation-in-dispatch-gate",
            "--confirm-no-publish-in-dispatch-gate",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_creation_gate_no_real_call(context)
    assert context["dispatchQueueWritten"] is False
    assert context["dispatchRecordPersisted"] is False
    assert context["sendExecutorDispatched"] is False
    assert context["executorDispatched"] is False
    assert context["requestSendAttempted"] is False


def test_contract_declares_executor_dispatch_gate_disabled_only():
    contract = load_json("providers/real-llm-request-send-executor-dispatch-gate-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_executor_creation_gate_disabled"
    assert contract["rules"]["requiresRequestSendExecutorCreationGateDisabledReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendExecutorDispatchGateDisabledReady"] is True
    assert contract["assertions"]["readyForRealRequestSendAttemptGate"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["dispatchQueueWritten"] is False
    assert contract["assertions"]["dispatchRecordPersisted"] is False
    assert contract["assertions"]["sendExecutorDispatched"] is False
    assert contract["assertions"]["executorDispatched"] is False
    assert contract["assertions"]["requestSendAttempted"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["executorDispatchBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_dispatch_executor():
    descriptor = describe_real_llm_request_send_executor_dispatch_gate_disabled(
        root=ROOT
    )

    assert descriptor["requestSendExecutorDispatchGateDisabledId"] == (
        "real_llm_request_send_executor_dispatch_gate_disabled"
    )
    assert descriptor["requestSendExecutorDispatchGateMode"] == (
        "REQUEST_SEND_EXECUTOR_DISPATCH_GATE_DISABLED_MODEL_ONLY"
    )
    assert descriptor["requestSendExecutorCreationGateDisabledReady"] is False
    assert descriptor["requestSendExecutorDispatchGateDisabledReady"] is False
    assert descriptor["readyForRealRequestSendAttemptGate"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_executor_dispatch_gate_requires_upstream_creation_gate():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_executor_dispatch_gate_disabled(
            RealLlmRequestSendExecutorDispatchGateDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_executor_dispatch_gate_disabled_error_context(
        exc,
        request=RealLlmRequestSendExecutorDispatchGateDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendExecutorCreationGateDisabledReady"] is False
    assert context["requestSendExecutorDispatchGateDisabledReady"] is False
    assert_no_real_call(context)


def test_executor_dispatch_gate_ready_still_does_not_dispatch_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_executor_dispatch_gate_disabled(
        confirmed_request(),
        root=ROOT,
    )

    assert result["requestSendExecutorCreationGateDisabledReady"] is True
    assert result["requestSendExecutorCreationGateDisabledSummary"]["requestSendExecutorCreationGateDisabledReady"] is True
    assert result["requestSendExecutorDispatchGateChecklistReady"] is True
    assert result["requestSendExecutorDispatchGateDisabledReady"] is True
    assert result["readyForRealRequestSendAttemptGate"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["executorDispatchGateModelBuilt"] is True
    assert result["executorDispatchGateModel"]["dispatchQueueWrittenNow"] is False
    assert result["executorDispatchGateModel"]["dispatchRecordPersistedNow"] is False
    assert result["executorDispatchGateModel"]["executorDispatchedNow"] is False
    assert result["executorDispatchGateModel"]["requestSendAttemptedNow"] is False
    assert result["executorDispatchGateModel"]["requestSentNow"] is False
    assert result["executorDispatchGateModel"]["clientCreationAllowedNow"] is False
    assert result["executorDispatchGateModel"]["realCallAuthorizedNow"] is False
    assert result["executorDispatchGateModel"]["sendAllowedNow"] is False
    assert result["executorDispatchGatePolicy"]["dispatchExecutorNow"] is False
    assert result["executorDispatchGatePolicy"]["sendRequestNow"] is False
    assert result["sendExecutionBoundary"]["sendExecutorDispatched"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_executor_dispatch_gate_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_executor_dispatch_gate_disabled(
        confirmed_request(
            executor_dispatch_scope_confirmed=False,
            no_executor_dispatch_in_dispatch_gate_confirmed=False,
            no_real_call_authorization_in_dispatch_gate_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {
        item["id"]: item
        for item in result["requestSendExecutorDispatchGateChecklist"]
    }

    assert result["requestSendExecutorCreationGateDisabledReady"] is True
    assert result["requestSendExecutorDispatchGateDisabledReady"] is False
    assert result["readyForRealRequestSendAttemptGate"] is False
    assert checklist["request_send_executor_creation_gate_disabled_ready"]["passed"] is True
    assert checklist["executor_dispatch_scope_confirmed"]["passed"] is False
    assert checklist["no_executor_dispatch_in_dispatch_gate_confirmed"]["passed"] is False
    assert checklist["no_real_call_authorization_in_dispatch_gate_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_executor_dispatch_gate_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_executor_dispatch_gate_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendExecutorDispatchGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_evaluate_return_json(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-executor-dispatch-gate-disabled",
            "describe",
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutorDispatchGateDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutorCreationGateDisabledReady"] is True
    assert payload["data"]["requestSendExecutorDispatchGateDisabledReady"] is True
    assert payload["data"]["readyForRealRequestSendAttemptGate"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_evaluate_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-executor-dispatch-gate-disabled",
            "evaluate",
            "--provider",
            "openai",
        ],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendExecutorDispatchGateDisabledContext"]
    assert context["requestSendExecutorCreationGateDisabledReady"] is False
    assert context["requestSendExecutorDispatchGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-executor-dispatch-gate-disabled",
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
