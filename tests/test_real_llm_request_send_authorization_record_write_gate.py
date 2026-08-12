import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendAuthorizationRecordWriteGateRequest,
    build_real_llm_request_send_authorization_record_write_gate,
    build_real_llm_request_send_authorization_record_write_gate_error_context,
    describe_real_llm_request_send_authorization_record_write_gate,
)
from test_real_llm_request_send_authorization_task_disabled import (
    assert_no_real_call as assert_authorization_task_no_real_call,
    confirmed_cli_args as confirmed_authorization_task_cli_args,
    confirmed_payload as confirmed_authorization_task_payload,
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
    payload = confirmed_authorization_task_payload(
        explicit_authorization_record_write_gate_opt_in=True,
        authorization_task_disabled_confirmed=True,
        authorization_record_scope_confirmed=True,
        authorization_record_storage_boundary_confirmed=True,
        authorization_record_schema_confirmed=True,
        approval_record_reference_confirmed=True,
        final_approver_identity_for_record_confirmed=True,
        single_request_authorization_record_confirmed=True,
        lab_only_authorization_record_confirmed=True,
        provider_prompt_input_authorization_record_confirmed=True,
        cost_timeout_retry_authorization_record_confirmed=True,
        runtime_kill_switch_authorization_record_confirmed=True,
        secret_runtime_boundary_authorization_record_confirmed=True,
        network_egress_authorization_record_confirmed=True,
        response_validation_authorization_record_confirmed=True,
        waiting_review_policy_authorization_record_confirmed=True,
        audit_redaction_authorization_record_confirmed=True,
        rollback_authorization_record_confirmed=True,
        no_authorization_record_write_confirmed=True,
        no_approval_record_write_confirmed=True,
        no_manual_approval_grant_in_record_gate_confirmed=True,
        no_real_call_authorization_in_record_gate_confirmed=True,
        no_executor_dispatch_in_record_gate_confirmed=True,
        no_request_send_in_record_gate_confirmed=True,
        no_secret_read_in_record_gate_confirmed=True,
        no_network_access_in_record_gate_confirmed=True,
        no_generated_content_creation_in_record_gate_confirmed=True,
        no_task_creation_in_record_gate_confirmed=True,
        no_publish_in_record_gate_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendAuthorizationRecordWriteGateRequest(
        **confirmed_payload(**overrides)
    )


def confirmed_cli_args():
    args = confirmed_authorization_task_cli_args()
    args[1] = "real-llm-request-send-authorization-record-write-gate"
    args[2] = "evaluate"
    args.extend(
        [
            "--explicit-authorization-record-write-gate-opt-in",
            "--confirm-authorization-task-disabled",
            "--confirm-authorization-record-scope",
            "--confirm-authorization-record-storage-boundary",
            "--confirm-authorization-record-schema",
            "--confirm-approval-record-reference",
            "--confirm-final-approver-identity-for-record",
            "--confirm-single-request-authorization-record",
            "--confirm-lab-only-authorization-record",
            "--confirm-provider-prompt-input-authorization-record",
            "--confirm-cost-timeout-retry-authorization-record",
            "--confirm-runtime-kill-switch-authorization-record",
            "--confirm-secret-runtime-boundary-authorization-record",
            "--confirm-network-egress-authorization-record",
            "--confirm-response-validation-authorization-record",
            "--confirm-waiting-review-policy-authorization-record",
            "--confirm-audit-redaction-authorization-record",
            "--confirm-rollback-authorization-record",
            "--confirm-no-authorization-record-write",
            "--confirm-no-approval-record-write",
            "--confirm-no-manual-approval-grant-in-record-gate",
            "--confirm-no-real-call-authorization-in-record-gate",
            "--confirm-no-executor-dispatch-in-record-gate",
            "--confirm-no-request-send-in-record-gate",
            "--confirm-no-secret-read-in-record-gate",
            "--confirm-no-network-access-in-record-gate",
            "--confirm-no-generated-content-creation-in-record-gate",
            "--confirm-no-task-creation-in-record-gate",
            "--confirm-no-publish-in-record-gate",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_authorization_task_no_real_call(context)
    assert context["authorizationRecordMaterialized"] is False
    assert context["authorizationRecordPersisted"] is False
    assert context["authorizationRecordWritten"] is False
    assert context["approvalRecordPersisted"] is False
    assert context["approvalRecordWritten"] is False


def test_contract_declares_authorization_record_write_gate_only():
    contract = load_json("providers/real-llm-request-send-authorization-record-write-gate.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_AUTHORIZATION_RECORD_WRITE_GATE_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_authorization_task_disabled"
    assert contract["rules"]["requiresRequestSendAuthorizationTaskDisabledReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["authorizationRecordWriteGateReady"] is True
    assert contract["assertions"]["readyForRequestSendRuntimeGate"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["authorizationRecordPersisted"] is False
    assert contract["assertions"]["authorizationRecordWritten"] is False
    assert contract["assertions"]["approvalRecordWritten"] is False
    assert contract["assertions"]["manualApprovalGranted"] is False
    assert contract["assertions"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["authorizationRecordWriteBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_write_record():
    descriptor = describe_real_llm_request_send_authorization_record_write_gate(root=ROOT)

    assert descriptor["requestSendAuthorizationRecordWriteGateId"] == (
        "real_llm_request_send_authorization_record_write_gate"
    )
    assert descriptor["authorizationRecordWriteGateMode"] == (
        "AUTHORIZATION_RECORD_WRITE_GATE_DISABLED_MODEL_ONLY"
    )
    assert descriptor["requestSendAuthorizationTaskDisabledReady"] is False
    assert descriptor["authorizationRecordWriteGateReady"] is False
    assert descriptor["readyForRequestSendRuntimeGate"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_record_write_gate_requires_upstream_authorization_task():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_authorization_record_write_gate(
            RealLlmRequestSendAuthorizationRecordWriteGateRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_authorization_record_write_gate_error_context(
        exc,
        request=RealLlmRequestSendAuthorizationRecordWriteGateRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendAuthorizationTaskDisabledReady"] is False
    assert context["authorizationRecordWriteGateReady"] is False
    assert_no_real_call(context)


def test_record_write_gate_ready_still_does_not_write_authorize_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_authorization_record_write_gate(
        confirmed_request(),
        root=ROOT,
    )

    assert result["requestSendAuthorizationTaskDisabledReady"] is True
    assert result["requestSendAuthorizationTaskSummary"]["requestSendAuthorizationTaskDisabledReady"] is True
    assert result["authorizationRecordWriteGateChecklistReady"] is True
    assert result["authorizationRecordWriteGateReady"] is True
    assert result["readyForRequestSendRuntimeGate"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["authorizationRecordWriteGateModelBuilt"] is True
    assert result["authorizationRecordWriteGateModel"]["authorizationRecordWrittenNow"] is False
    assert result["authorizationRecordWriteGateModel"]["authorizationRecordPersistedNow"] is False
    assert result["authorizationRecordWriteGateModel"]["approvalRecordWrittenNow"] is False
    assert result["authorizationRecordWriteGateModel"]["manualApprovalGrantedNow"] is False
    assert result["authorizationRecordWriteGateModel"]["realCallAuthorizedNow"] is False
    assert result["authorizationRecordWriteGateModel"]["sendAllowedNow"] is False
    assert result["authorizationRecordWritePolicy"]["writeAuthorizationRecordNow"] is False
    assert result["authorizationRecordWritePolicy"]["authorizeRealCallNow"] is False
    assert result["sendExecutionBoundary"]["authorizationRecordWritten"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_record_write_gate_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_authorization_record_write_gate(
        confirmed_request(
            authorization_record_scope_confirmed=False,
            no_authorization_record_write_confirmed=False,
            no_real_call_authorization_in_record_gate_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["authorizationRecordWriteGateChecklist"]}

    assert result["requestSendAuthorizationTaskDisabledReady"] is True
    assert result["authorizationRecordWriteGateReady"] is False
    assert result["readyForRequestSendRuntimeGate"] is False
    assert checklist["request_send_authorization_task_disabled_ready"]["passed"] is True
    assert checklist["authorization_record_scope_confirmed"]["passed"] is False
    assert checklist["no_authorization_record_write_confirmed"]["passed"] is False
    assert checklist["no_real_call_authorization_in_record_gate_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_authorization_record_write_gate(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_authorization_record_write_gate_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["authorizationRecordWriteGateReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_evaluate_return_json(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-authorization-record-write-gate", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["authorizationRecordWriteGateReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendAuthorizationTaskDisabledReady"] is True
    assert payload["data"]["authorizationRecordWriteGateReady"] is True
    assert payload["data"]["readyForRequestSendRuntimeGate"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_evaluate_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-authorization-record-write-gate", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendAuthorizationRecordWriteGateContext"]
    assert context["requestSendAuthorizationTaskDisabledReady"] is False
    assert context["authorizationRecordWriteGateReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-authorization-record-write-gate",
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
