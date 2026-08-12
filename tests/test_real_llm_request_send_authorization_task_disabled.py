import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendAuthorizationTaskDisabledRequest,
    build_real_llm_request_send_authorization_task_disabled,
    build_real_llm_request_send_authorization_task_disabled_error_context,
    describe_real_llm_request_send_authorization_task_disabled,
)
from test_real_llm_request_send_final_approval_review import (
    assert_no_real_call as assert_final_review_no_real_call,
    confirmed_cli_args as confirmed_final_review_cli_args,
    confirmed_payload as confirmed_final_review_payload,
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
    payload = confirmed_final_review_payload(
        explicit_request_send_authorization_task_disabled_opt_in=True,
        request_send_final_approval_review_confirmed=True,
        authorization_task_scope_confirmed=True,
        authorization_task_record_confirmed=True,
        manual_approval_record_reference_confirmed=True,
        final_approver_identity_for_task_confirmed=True,
        single_request_authorization_task_confirmed=True,
        lab_only_authorization_task_confirmed=True,
        provider_prompt_input_authorization_task_confirmed=True,
        cost_timeout_retry_authorization_task_confirmed=True,
        runtime_kill_switch_authorization_task_confirmed=True,
        secret_runtime_boundary_authorization_task_confirmed=True,
        network_egress_authorization_task_confirmed=True,
        response_validation_authorization_task_confirmed=True,
        waiting_review_policy_authorization_task_confirmed=True,
        audit_redaction_authorization_task_confirmed=True,
        rollback_authorization_task_confirmed=True,
        no_task_persistence_in_authorization_task_confirmed=True,
        no_queue_in_authorization_task_confirmed=True,
        no_executor_dispatch_in_authorization_task_confirmed=True,
        no_request_send_in_authorization_task_confirmed=True,
        no_secret_read_in_authorization_task_confirmed=True,
        no_network_access_in_authorization_task_confirmed=True,
        no_generated_content_creation_in_authorization_task_confirmed=True,
        no_publish_in_authorization_task_confirmed=True,
        no_manual_approval_grant_in_authorization_task_confirmed=True,
        no_real_call_authorization_in_authorization_task_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendAuthorizationTaskDisabledRequest(
        **confirmed_payload(**overrides)
    )


def confirmed_cli_args():
    args = confirmed_final_review_cli_args()
    args[1] = "real-llm-request-send-authorization-task-disabled"
    args[2] = "prepare"
    args.extend(
        [
            "--explicit-request-send-authorization-task-disabled-opt-in",
            "--confirm-request-send-final-approval-review",
            "--confirm-authorization-task-scope",
            "--confirm-authorization-task-record",
            "--confirm-manual-approval-record-reference",
            "--confirm-final-approver-identity-for-task",
            "--confirm-single-request-authorization-task",
            "--confirm-lab-only-authorization-task",
            "--confirm-provider-prompt-input-authorization-task",
            "--confirm-cost-timeout-retry-authorization-task",
            "--confirm-runtime-kill-switch-authorization-task",
            "--confirm-secret-runtime-boundary-authorization-task",
            "--confirm-network-egress-authorization-task",
            "--confirm-response-validation-authorization-task",
            "--confirm-waiting-review-policy-authorization-task",
            "--confirm-audit-redaction-authorization-task",
            "--confirm-rollback-authorization-task",
            "--confirm-no-task-persistence-in-authorization-task",
            "--confirm-no-queue-in-authorization-task",
            "--confirm-no-executor-dispatch-in-authorization-task",
            "--confirm-no-request-send-in-authorization-task",
            "--confirm-no-secret-read-in-authorization-task",
            "--confirm-no-network-access-in-authorization-task",
            "--confirm-no-generated-content-creation-in-authorization-task",
            "--confirm-no-publish-in-authorization-task",
            "--confirm-no-manual-approval-grant-in-authorization-task",
            "--confirm-no-real-call-authorization-in-authorization-task",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_final_review_no_real_call(context)
    assert context["authorizationTaskMaterialized"] is False
    assert context["authorizationTaskPersisted"] is False
    assert context["authorizationTaskQueued"] is False
    assert context["authorizationTaskDispatched"] is False
    assert context["authorizationTaskCreated"] is False
    assert context["authorizationRecordPersisted"] is False
    assert context["authorizationRecordWritten"] is False


def test_contract_declares_authorization_task_disabled_only():
    contract = load_json("providers/real-llm-request-send-authorization-task-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_final_approval_review"
    assert contract["rules"]["requiresRequestSendFinalApprovalReviewReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendAuthorizationTaskDisabledReady"] is True
    assert contract["assertions"]["readyForAuthorizationRecordWriteGate"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["authorizationTaskCreated"] is False
    assert contract["assertions"]["authorizationTaskPersisted"] is False
    assert contract["assertions"]["authorizationRecordWritten"] is False
    assert contract["assertions"]["manualApprovalGranted"] is False
    assert contract["assertions"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["authorizationTaskBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_create_task():
    descriptor = describe_real_llm_request_send_authorization_task_disabled(root=ROOT)

    assert descriptor["requestSendAuthorizationTaskDisabledId"] == (
        "real_llm_request_send_authorization_task_disabled"
    )
    assert descriptor["authorizationTaskMode"] == (
        "EXPLICIT_REAL_REQUEST_SEND_AUTHORIZATION_TASK_DISABLED_MODEL_ONLY"
    )
    assert descriptor["requestSendFinalApprovalReviewReady"] is False
    assert descriptor["requestSendAuthorizationTaskDisabledReady"] is False
    assert descriptor["readyForAuthorizationRecordWriteGate"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_authorization_task_requires_upstream_final_review():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_authorization_task_disabled(
            RealLlmRequestSendAuthorizationTaskDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_authorization_task_disabled_error_context(
        exc,
        request=RealLlmRequestSendAuthorizationTaskDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendFinalApprovalReviewReady"] is False
    assert context["requestSendAuthorizationTaskDisabledReady"] is False
    assert_no_real_call(context)


def test_authorization_task_ready_still_does_not_create_authorize_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_authorization_task_disabled(
        confirmed_request(),
        root=ROOT,
    )

    assert result["requestSendFinalApprovalReviewReady"] is True
    assert result["requestSendFinalApprovalReviewSummary"]["requestSendFinalApprovalReviewReady"] is True
    assert result["requestSendAuthorizationTaskChecklistReady"] is True
    assert result["requestSendAuthorizationTaskDisabledReady"] is True
    assert result["readyForAuthorizationRecordWriteGate"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["authorizationTaskModelBuilt"] is True
    assert result["authorizationTaskModel"]["taskCreatedNow"] is False
    assert result["authorizationTaskModel"]["taskQueuedNow"] is False
    assert result["authorizationTaskModel"]["taskDispatchedNow"] is False
    assert result["authorizationTaskModel"]["authorizationRecordWrittenNow"] is False
    assert result["authorizationTaskModel"]["manualApprovalGrantedNow"] is False
    assert result["authorizationTaskModel"]["realCallAuthorizedNow"] is False
    assert result["authorizationTaskModel"]["sendAllowedNow"] is False
    assert result["authorizationTaskPolicy"]["persistTaskNow"] is False
    assert result["authorizationTaskPolicy"]["authorizeRealCallNow"] is False
    assert result["sendExecutionBoundary"]["authorizationTaskCreated"] is False
    assert result["sendExecutionBoundary"]["authorizationRecordWritten"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_authorization_task_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_authorization_task_disabled(
        confirmed_request(
            authorization_task_scope_confirmed=False,
            no_task_persistence_in_authorization_task_confirmed=False,
            no_real_call_authorization_in_authorization_task_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["requestSendAuthorizationTaskChecklist"]}

    assert result["requestSendFinalApprovalReviewReady"] is True
    assert result["requestSendAuthorizationTaskDisabledReady"] is False
    assert result["readyForAuthorizationRecordWriteGate"] is False
    assert checklist["request_send_final_approval_review_ready"]["passed"] is True
    assert checklist["authorization_task_scope_confirmed"]["passed"] is False
    assert checklist["no_task_persistence_in_authorization_task_confirmed"]["passed"] is False
    assert checklist["no_real_call_authorization_in_authorization_task_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_authorization_task_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_authorization_task_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendAuthorizationTaskDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_prepare_return_json(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-authorization-task-disabled", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendAuthorizationTaskDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendFinalApprovalReviewReady"] is True
    assert payload["data"]["requestSendAuthorizationTaskDisabledReady"] is True
    assert payload["data"]["readyForAuthorizationRecordWriteGate"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_prepare_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-authorization-task-disabled", "prepare", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendAuthorizationTaskDisabledContext"]
    assert context["requestSendFinalApprovalReviewReady"] is False
    assert context["requestSendAuthorizationTaskDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-authorization-task-disabled",
            "prepare",
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
