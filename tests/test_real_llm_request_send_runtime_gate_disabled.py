import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendRuntimeGateDisabledRequest,
    build_real_llm_request_send_runtime_gate_disabled,
    build_real_llm_request_send_runtime_gate_disabled_error_context,
    describe_real_llm_request_send_runtime_gate_disabled,
)
from test_real_llm_request_send_authorization_record_write_gate import (
    assert_no_real_call as assert_record_gate_no_real_call,
    confirmed_cli_args as confirmed_record_gate_cli_args,
    confirmed_payload as confirmed_record_gate_payload,
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
    payload = confirmed_record_gate_payload(
        explicit_request_send_runtime_gate_disabled_opt_in=True,
        authorization_record_write_gate_confirmed=True,
        runtime_gate_scope_confirmed=True,
        runtime_gate_record_confirmed=True,
        runtime_kill_switch_boundary_confirmed=True,
        runtime_budget_boundary_confirmed=True,
        runtime_timeout_retry_boundary_confirmed=True,
        runtime_concurrency_boundary_confirmed=True,
        runtime_network_egress_boundary_confirmed=True,
        runtime_secret_read_boundary_confirmed=True,
        runtime_client_boundary_confirmed=True,
        runtime_response_validation_confirmed=True,
        runtime_audit_redaction_confirmed=True,
        runtime_rollback_confirmed=True,
        runtime_waiting_review_policy_confirmed=True,
        no_runtime_gate_open_confirmed=True,
        no_runtime_gate_persistence_confirmed=True,
        no_kill_switch_disable_confirmed=True,
        no_budget_reservation_confirmed=True,
        no_network_egress_open_confirmed=True,
        no_secret_read_in_runtime_gate_confirmed=True,
        no_client_creation_in_runtime_gate_confirmed=True,
        no_executor_creation_in_runtime_gate_confirmed=True,
        no_executor_dispatch_in_runtime_gate_confirmed=True,
        no_request_send_in_runtime_gate_confirmed=True,
        no_real_call_authorization_in_runtime_gate_confirmed=True,
        no_generated_content_creation_in_runtime_gate_confirmed=True,
        no_task_creation_in_runtime_gate_confirmed=True,
        no_publish_in_runtime_gate_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendRuntimeGateDisabledRequest(
        **confirmed_payload(**overrides)
    )


def confirmed_cli_args():
    args = confirmed_record_gate_cli_args()
    args[1] = "real-llm-request-send-runtime-gate-disabled"
    args[2] = "evaluate"
    args.extend(
        [
            "--explicit-request-send-runtime-gate-disabled-opt-in",
            "--confirm-authorization-record-write-gate",
            "--confirm-runtime-gate-scope",
            "--confirm-runtime-gate-record",
            "--confirm-runtime-kill-switch-boundary",
            "--confirm-runtime-budget-boundary",
            "--confirm-runtime-timeout-retry-boundary",
            "--confirm-runtime-concurrency-boundary",
            "--confirm-runtime-network-egress-boundary",
            "--confirm-runtime-secret-read-boundary",
            "--confirm-runtime-client-boundary",
            "--confirm-runtime-response-validation",
            "--confirm-runtime-audit-redaction",
            "--confirm-runtime-rollback",
            "--confirm-runtime-waiting-review-policy",
            "--confirm-no-runtime-gate-open",
            "--confirm-no-runtime-gate-persistence",
            "--confirm-no-kill-switch-disable",
            "--confirm-no-budget-reservation",
            "--confirm-no-network-egress-open",
            "--confirm-no-secret-read-in-runtime-gate",
            "--confirm-no-client-creation-in-runtime-gate",
            "--confirm-no-executor-creation-in-runtime-gate",
            "--confirm-no-executor-dispatch-in-runtime-gate",
            "--confirm-no-request-send-in-runtime-gate",
            "--confirm-no-real-call-authorization-in-runtime-gate",
            "--confirm-no-generated-content-creation-in-runtime-gate",
            "--confirm-no-task-creation-in-runtime-gate",
            "--confirm-no-publish-in-runtime-gate",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_record_gate_no_real_call(context)
    assert context["runtimeGateMaterialized"] is False
    assert context["runtimeGatePersisted"] is False
    assert context["runtimeGateOpened"] is False
    assert context["runtimeKillSwitchDisabled"] is False
    assert context["runtimeBudgetReserved"] is False
    assert context["runtimeNetworkEgressOpened"] is False
    assert context["sendExecutorCreated"] is False


def test_contract_declares_runtime_gate_disabled_only():
    contract = load_json("providers/real-llm-request-send-runtime-gate-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_RUNTIME_GATE_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_authorization_record_write_gate"
    assert contract["rules"]["requiresRequestSendAuthorizationRecordWriteGateReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendRuntimeGateDisabledReady"] is True
    assert contract["assertions"]["readyForRealRequestSendExecutorCreationGate"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["runtimeGateOpened"] is False
    assert contract["assertions"]["runtimeKillSwitchDisabled"] is False
    assert contract["assertions"]["runtimeBudgetReserved"] is False
    assert contract["assertions"]["runtimeNetworkEgressOpened"] is False
    assert contract["assertions"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["runtimeGateBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_open_runtime_gate():
    descriptor = describe_real_llm_request_send_runtime_gate_disabled(root=ROOT)

    assert descriptor["requestSendRuntimeGateDisabledId"] == (
        "real_llm_request_send_runtime_gate_disabled"
    )
    assert descriptor["requestSendRuntimeGateMode"] == (
        "REQUEST_SEND_RUNTIME_GATE_DISABLED_MODEL_ONLY"
    )
    assert descriptor["requestSendAuthorizationRecordWriteGateReady"] is False
    assert descriptor["requestSendRuntimeGateDisabledReady"] is False
    assert descriptor["readyForRealRequestSendExecutorCreationGate"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_runtime_gate_requires_upstream_record_write_gate():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_runtime_gate_disabled(
            RealLlmRequestSendRuntimeGateDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_runtime_gate_disabled_error_context(
        exc,
        request=RealLlmRequestSendRuntimeGateDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendAuthorizationRecordWriteGateReady"] is False
    assert context["requestSendRuntimeGateDisabledReady"] is False
    assert_no_real_call(context)


def test_runtime_gate_ready_still_does_not_open_authorize_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_runtime_gate_disabled(
        confirmed_request(),
        root=ROOT,
    )

    assert result["requestSendAuthorizationRecordWriteGateReady"] is True
    assert result["requestSendAuthorizationRecordWriteGateSummary"]["authorizationRecordWriteGateReady"] is True
    assert result["requestSendRuntimeGateChecklistReady"] is True
    assert result["requestSendRuntimeGateDisabledReady"] is True
    assert result["readyForRealRequestSendExecutorCreationGate"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["runtimeGateModelBuilt"] is True
    assert result["runtimeGateModel"]["runtimeGateOpenedNow"] is False
    assert result["runtimeGateModel"]["runtimeKillSwitchDisabledNow"] is False
    assert result["runtimeGateModel"]["runtimeBudgetReservedNow"] is False
    assert result["runtimeGateModel"]["networkEgressOpenedNow"] is False
    assert result["runtimeGateModel"]["secretReadAllowedNow"] is False
    assert result["runtimeGateModel"]["clientCreationAllowedNow"] is False
    assert result["runtimeGateModel"]["executorCreationAllowedNow"] is False
    assert result["runtimeGateModel"]["realCallAuthorizedNow"] is False
    assert result["runtimeGateModel"]["sendAllowedNow"] is False
    assert result["runtimeGatePolicy"]["openRuntimeGateNow"] is False
    assert result["runtimeGatePolicy"]["authorizeRealCallNow"] is False
    assert result["sendExecutionBoundary"]["runtimeGateOpened"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_runtime_gate_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_runtime_gate_disabled(
        confirmed_request(
            runtime_gate_scope_confirmed=False,
            no_runtime_gate_open_confirmed=False,
            no_real_call_authorization_in_runtime_gate_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["requestSendRuntimeGateChecklist"]}

    assert result["requestSendAuthorizationRecordWriteGateReady"] is True
    assert result["requestSendRuntimeGateDisabledReady"] is False
    assert result["readyForRealRequestSendExecutorCreationGate"] is False
    assert checklist["request_send_authorization_record_write_gate_ready"]["passed"] is True
    assert checklist["runtime_gate_scope_confirmed"]["passed"] is False
    assert checklist["no_runtime_gate_open_confirmed"]["passed"] is False
    assert checklist["no_real_call_authorization_in_runtime_gate_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_runtime_gate_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_runtime_gate_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendRuntimeGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_evaluate_return_json(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-runtime-gate-disabled", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendRuntimeGateDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendAuthorizationRecordWriteGateReady"] is True
    assert payload["data"]["requestSendRuntimeGateDisabledReady"] is True
    assert payload["data"]["readyForRealRequestSendExecutorCreationGate"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_evaluate_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-runtime-gate-disabled", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendRuntimeGateDisabledContext"]
    assert context["requestSendAuthorizationRecordWriteGateReady"] is False
    assert context["requestSendRuntimeGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-runtime-gate-disabled",
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
