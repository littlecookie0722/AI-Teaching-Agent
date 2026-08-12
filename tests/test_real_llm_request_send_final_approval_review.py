import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendFinalApprovalReviewRequest,
    build_real_llm_request_send_final_approval_review,
    build_real_llm_request_send_final_approval_review_error_context,
    describe_real_llm_request_send_final_approval_review,
)
from test_real_llm_request_send_executor_disabled import (
    assert_no_real_call as assert_executor_no_real_call,
    confirmed_cli_args as confirmed_executor_cli_args,
    confirmed_payload as confirmed_executor_payload,
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
    payload = confirmed_executor_payload(
        explicit_request_send_final_approval_review_opt_in=True,
        request_send_executor_disabled_confirmed=True,
        final_approver_identity_confirmed=True,
        final_approval_scope_confirmed=True,
        final_approval_record_location_confirmed=True,
        single_request_final_approval_confirmed=True,
        lab_only_final_approval_confirmed=True,
        provider_prompt_input_final_review_confirmed=True,
        cost_timeout_retry_final_review_confirmed=True,
        runtime_kill_switch_final_review_confirmed=True,
        secret_handling_final_review_confirmed=True,
        network_egress_final_review_confirmed=True,
        response_validation_final_review_confirmed=True,
        waiting_review_policy_final_review_confirmed=True,
        audit_redaction_final_review_confirmed=True,
        rollback_final_review_confirmed=True,
        no_manual_approval_grant_in_final_review_confirmed=True,
        no_real_call_authorization_in_final_review_confirmed=True,
        no_executor_dispatch_in_final_review_confirmed=True,
        no_request_send_in_final_review_confirmed=True,
        no_secret_read_in_final_review_confirmed=True,
        no_network_access_in_final_review_confirmed=True,
        no_generated_content_creation_in_final_review_confirmed=True,
        no_task_creation_in_final_review_confirmed=True,
        no_publish_in_final_review_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendFinalApprovalReviewRequest(**confirmed_payload(**overrides))


def confirmed_cli_args():
    args = confirmed_executor_cli_args()
    args[1] = "real-llm-request-send-final-approval-review"
    args[2] = "review"
    args.extend(
        [
            "--explicit-request-send-final-approval-review-opt-in",
            "--confirm-request-send-executor-disabled",
            "--confirm-final-approver-identity",
            "--confirm-final-approval-scope",
            "--confirm-final-approval-record-location",
            "--confirm-single-request-final-approval",
            "--confirm-lab-only-final-approval",
            "--confirm-provider-prompt-input-final-review",
            "--confirm-cost-timeout-retry-final-review",
            "--confirm-runtime-kill-switch-final-review",
            "--confirm-secret-handling-final-review",
            "--confirm-network-egress-final-review",
            "--confirm-response-validation-final-review",
            "--confirm-waiting-review-policy-final-review",
            "--confirm-audit-redaction-final-review",
            "--confirm-rollback-final-review",
            "--confirm-no-manual-approval-grant-in-final-review",
            "--confirm-no-real-call-authorization-in-final-review",
            "--confirm-no-executor-dispatch-in-final-review",
            "--confirm-no-request-send-in-final-review",
            "--confirm-no-secret-read-in-final-review",
            "--confirm-no-network-access-in-final-review",
            "--confirm-no-generated-content-creation-in-final-review",
            "--confirm-no-task-creation-in-final-review",
            "--confirm-no-publish-in-final-review",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_executor_no_real_call(context)
    assert context["finalApprovalReviewPackageMaterialized"] is False
    assert context["finalApprovalReviewPackagePersisted"] is False
    assert context["approvalRecordPersisted"] is False
    assert context["approvalRecordWritten"] is False


def test_contract_declares_final_approval_review_only():
    contract = load_json("providers/real-llm-request-send-final-approval-review.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_FINAL_APPROVAL_REVIEW_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_executor_disabled"
    assert contract["rules"]["requiresRequestSendExecutorDisabledReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendFinalApprovalReviewReady"] is True
    assert contract["assertions"]["readyForExplicitRealRequestSendAuthorizationTask"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["approvalRecordWritten"] is False
    assert contract["assertions"]["manualApprovalGranted"] is False
    assert contract["assertions"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["finalApprovalBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_grant_approval():
    descriptor = describe_real_llm_request_send_final_approval_review(root=ROOT)

    assert descriptor["requestSendFinalApprovalReviewId"] == "real_llm_request_send_final_approval_review"
    assert descriptor["approvalReviewMode"] == "FINAL_HUMAN_APPROVAL_REVIEW_MODEL_ONLY"
    assert descriptor["requestSendExecutorDisabledReady"] is False
    assert descriptor["requestSendFinalApprovalReviewReady"] is False
    assert descriptor["readyForExplicitRealRequestSendAuthorizationTask"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_final_approval_review_requires_upstream_executor():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_final_approval_review(
            RealLlmRequestSendFinalApprovalReviewRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_final_approval_review_error_context(
        exc,
        request=RealLlmRequestSendFinalApprovalReviewRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendExecutorDisabledReady"] is False
    assert context["requestSendFinalApprovalReviewReady"] is False
    assert_no_real_call(context)


def test_final_approval_review_ready_still_does_not_grant_authorize_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_final_approval_review(confirmed_request(), root=ROOT)

    assert result["requestSendExecutorDisabledReady"] is True
    assert result["requestSendExecutorSummary"]["requestSendExecutorDisabledReady"] is True
    assert result["requestSendFinalApprovalChecklistReady"] is True
    assert result["requestSendFinalApprovalReviewReady"] is True
    assert result["readyForExplicitRealRequestSendAuthorizationTask"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["finalApprovalReviewPackageBuilt"] is True
    assert result["finalApprovalReviewPackage"]["manualApprovalGrantedNow"] is False
    assert result["finalApprovalReviewPackage"]["realCallAuthorizedNow"] is False
    assert result["finalApprovalReviewPackage"]["sendAllowedNow"] is False
    assert result["finalApprovalPolicy"]["grantManualApprovalNow"] is False
    assert result["finalApprovalPolicy"]["authorizeRealCallNow"] is False
    assert result["sendExecutionBoundary"]["manualApprovalGranted"] is False
    assert result["sendExecutionBoundary"]["realCallAuthorized"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_final_approval_review_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_final_approval_review(
        confirmed_request(
            final_approval_scope_confirmed=False,
            no_manual_approval_grant_in_final_review_confirmed=False,
            no_real_call_authorization_in_final_review_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["requestSendFinalApprovalChecklist"]}

    assert result["requestSendExecutorDisabledReady"] is True
    assert result["requestSendFinalApprovalReviewReady"] is False
    assert result["readyForExplicitRealRequestSendAuthorizationTask"] is False
    assert checklist["request_send_executor_disabled_ready"]["passed"] is True
    assert checklist["final_approval_scope_confirmed"]["passed"] is False
    assert checklist["no_manual_approval_grant_in_final_review_confirmed"]["passed"] is False
    assert checklist["no_real_call_authorization_in_final_review_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_final_approval_review(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_final_approval_review_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendFinalApprovalReviewReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_review_return_json(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-request-send-final-approval-review", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendFinalApprovalReviewReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutorDisabledReady"] is True
    assert payload["data"]["requestSendFinalApprovalReviewReady"] is True
    assert payload["data"]["readyForExplicitRealRequestSendAuthorizationTask"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_review_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-final-approval-review", "review", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendFinalApprovalReviewContext"]
    assert context["requestSendExecutorDisabledReady"] is False
    assert context["requestSendFinalApprovalReviewReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-final-approval-review",
            "review",
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
