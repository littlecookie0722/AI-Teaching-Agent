import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmMinimalCallSendExecutorDisabledRequest,
    build_real_llm_minimal_call_send_executor_disabled_error_context,
    describe_real_llm_minimal_call_send_executor_disabled,
    prepare_real_llm_minimal_call_send_executor_disabled,
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
        "approval_ref": "MINIMAL-CALL-SEND-EXECUTOR-001",
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
        "explicit_disabled_executor_opt_in": True,
        "first_call_approval_gate_confirmed": True,
        "client_boundary_ready_confirmed": True,
        "request_shape_confirmed": True,
        "no_executor_dispatch_confirmed": True,
        "no_request_send_in_executor_confirmed": True,
        "no_network_access_in_executor_confirmed": True,
        "no_real_llm_call_in_executor_confirmed": True,
        "no_secret_read_in_executor_confirmed": True,
        "no_task_creation_in_executor_confirmed": True,
        "no_publish_in_executor_confirmed": True,
        "explicit_pre_send_dry_run_record_opt_in": True,
        "disabled_executor_confirmed": True,
        "approval_gate_confirmed": True,
        "log_redaction_confirmed": True,
        "failure_rollback_confirmed": True,
        "response_schema_validation_confirmed": True,
        "post_call_review_confirmed": True,
        "no_request_send_in_dry_run_confirmed": True,
        "no_network_access_in_dry_run_confirmed": True,
        "no_secret_read_in_dry_run_confirmed": True,
        "no_task_creation_in_dry_run_confirmed": True,
        "no_publish_in_dry_run_confirmed": True,
        "explicit_minimal_call_poc_review_opt_in": True,
        "pre_send_dry_run_record_confirmed": True,
        "single_request_scope_confirmed": True,
        "lab_only_scope_confirmed": True,
        "env_secret_source_confirmed": True,
        "no_secret_logging_confirmed": True,
        "network_egress_confirmed": True,
        "cost_limit_enforced_confirmed": True,
        "timeout_retry_limit_confirmed": True,
        "response_schema_validation_confirmed_for_poc": True,
        "waiting_review_task_policy_confirmed": True,
        "failure_rollback_confirmed_for_poc": True,
        "audit_event_plan_confirmed": True,
        "no_auto_publish_confirmed": True,
        "no_batch_call_confirmed": True,
        "no_streaming_confirmed": True,
        "no_exam_grading_ppt_scope_confirmed": True,
        "no_real_request_send_in_review_confirmed": True,
        "explicit_send_executor_disabled_opt_in": True,
        "minimal_call_poc_review_confirmed": True,
        "send_executor_boundary_confirmed": True,
        "final_manual_authorization_record_confirmed": True,
        "secret_runtime_read_boundary_confirmed": True,
        "network_call_boundary_confirmed": True,
        "sdk_client_boundary_confirmed": True,
        "response_validation_boundary_confirmed": True,
        "waiting_review_task_creation_boundary_confirmed": True,
        "audit_logging_boundary_confirmed": True,
        "rollback_boundary_confirmed": True,
        "no_executor_dispatch_confirmed_for_send": True,
        "no_request_send_in_disabled_executor_confirmed": True,
        "no_secret_read_in_disabled_executor_confirmed": True,
        "no_network_access_in_disabled_executor_confirmed": True,
        "no_real_llm_call_in_disabled_executor_confirmed": True,
        "no_task_creation_in_disabled_executor_confirmed": True,
        "no_publish_in_disabled_executor_confirmed": True,
    }
    payload.update(overrides)
    return RealLlmMinimalCallSendExecutorDisabledRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-llm-minimal-call-send-executor-disabled",
        "prepare",
        "--provider",
        "openai",
        "--payload",
        '{"source":"examples/input/demo-source.md","api_key":"fake-secret-that-must-be-redacted"}',
        "--reviewer",
        "teacher_1",
        "--approval-ref",
        "MINIMAL-CALL-SEND-EXECUTOR-001",
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
        "--explicit-disabled-executor-opt-in",
        "--confirm-first-call-approval-gate",
        "--confirm-client-boundary-ready",
        "--confirm-request-shape",
        "--confirm-no-executor-dispatch",
        "--confirm-no-request-send-in-executor",
        "--confirm-no-network-access-in-executor",
        "--confirm-no-real-llm-call-in-executor",
        "--confirm-no-secret-read-in-executor",
        "--confirm-no-task-creation-in-executor",
        "--confirm-no-publish-in-executor",
        "--explicit-pre-send-dry-run-record-opt-in",
        "--confirm-disabled-executor",
        "--confirm-approval-gate",
        "--confirm-log-redaction",
        "--confirm-failure-rollback",
        "--confirm-response-schema-validation",
        "--confirm-post-call-review",
        "--confirm-no-request-send-in-dry-run",
        "--confirm-no-network-access-in-dry-run",
        "--confirm-no-secret-read-in-dry-run",
        "--confirm-no-task-creation-in-dry-run",
        "--confirm-no-publish-in-dry-run",
        "--explicit-minimal-call-poc-review-opt-in",
        "--confirm-pre-send-dry-run-record",
        "--confirm-single-request-scope",
        "--confirm-lab-only-scope",
        "--confirm-env-secret-source",
        "--confirm-no-secret-logging",
        "--confirm-network-egress",
        "--confirm-cost-limit-enforced",
        "--confirm-timeout-retry-limit",
        "--confirm-response-schema-validation-for-poc",
        "--confirm-waiting-review-task-policy",
        "--confirm-failure-rollback-for-poc",
        "--confirm-audit-event-plan",
        "--confirm-no-auto-publish",
        "--confirm-no-batch-call",
        "--confirm-no-streaming",
        "--confirm-no-exam-grading-ppt-scope",
        "--confirm-no-real-request-send-in-review",
        "--explicit-send-executor-disabled-opt-in",
        "--confirm-minimal-call-poc-review",
        "--confirm-send-executor-boundary",
        "--confirm-final-manual-authorization-record",
        "--confirm-secret-runtime-read-boundary",
        "--confirm-network-call-boundary",
        "--confirm-sdk-client-boundary",
        "--confirm-response-validation-boundary",
        "--confirm-waiting-review-task-creation-boundary",
        "--confirm-audit-logging-boundary",
        "--confirm-rollback-boundary",
        "--confirm-no-executor-dispatch-for-send",
        "--confirm-no-request-send-in-disabled-executor",
        "--confirm-no-secret-read-in-disabled-executor",
        "--confirm-no-network-access-in-disabled-executor",
        "--confirm-no-real-llm-call-in-disabled-executor",
        "--confirm-no-task-creation-in-disabled-executor",
        "--confirm-no-publish-in-disabled-executor",
    ]


def assert_no_real_call(context):
    assert context["sendImplementationCreated"] is False
    assert context["sendExecutorCreated"] is False
    assert context["sendExecutorMaterialized"] is False
    assert context["sendExecutorPersisted"] is False
    assert context["sendExecutorDispatched"] is False
    assert context["executorDispatched"] is False
    assert context["requestSendAttempted"] is False
    assert context["requestSent"] is False
    assert context["sdkImported"] is False
    assert context["clientCreated"] is False
    assert context["secretPresenceChecked"] is False
    assert context["secretValueRead"] is False
    assert context["secretValueReturned"] is False
    assert context["secretValueLogged"] is False
    assert context["networkAccess"] is False
    assert context["realLlmCalled"] is False
    assert context["generatedContentCreated"] is False
    assert context["taskCreated"] is False
    assert context["manualApprovalGranted"] is False
    assert context["autoPublishAllowed"] is False
    assert context["realPublish"] is False
    assert context["realCallAuthorized"] is False


def test_contract_declares_disabled_send_executor_only():
    contract = load_json("providers/real-llm-minimal-call-send-executor-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_MINIMAL_CALL_SEND_EXECUTOR_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_minimal_call_poc_review"
    assert contract["rules"]["requiresMinimalCallPocReviewReady"] is True
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["minimalCallSendExecutorDisabledReady"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["sendExecutorDispatched"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["assertions"]["networkAccess"] is False
    assert contract["assertions"]["realLlmCalled"] is False
    assert contract["futureSendExecutorBoundary"]["sendAllowedInThisStep"] is False


def test_describe_is_safe_and_does_not_prepare_send_executor():
    descriptor = describe_real_llm_minimal_call_send_executor_disabled(root=ROOT)

    assert descriptor["minimalCallSendExecutorDisabledId"] == "real_llm_minimal_call_send_executor_disabled"
    assert descriptor["executorMode"] == "DISABLED_MINIMAL_REAL_CALL_SEND_EXECUTOR_MODEL_ONLY"
    assert descriptor["minimalCallPocReviewReady"] is False
    assert descriptor["minimalCallSendExecutorDisabledReady"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_send_executor_requires_upstream_poc_review_before_prepare():
    with pytest.raises(ProviderError) as exc_info:
        prepare_real_llm_minimal_call_send_executor_disabled(
            RealLlmMinimalCallSendExecutorDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_minimal_call_send_executor_disabled_error_context(
        exc,
        request=RealLlmMinimalCallSendExecutorDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["minimalCallPocReviewReady"] is False
    assert context["minimalCallSendExecutorDisabledReady"] is False
    assert_no_real_call(context)


def test_send_executor_ready_still_does_not_send_or_read_secret():
    secret = "fake-secret-that-must-be-redacted"
    result = prepare_real_llm_minimal_call_send_executor_disabled(confirmed_request(), root=ROOT)

    assert result["minimalCallPocReviewReady"] is True
    assert result["minimalCallPocReviewSummary"]["readyForMinimalRealCallImplementation"] is True
    assert result["sendExecutorChecklistReady"] is True
    assert result["minimalCallSendExecutorDisabledReady"] is True
    assert result["readyForExplicitRealRequestSendAuthorization"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["sendExecutorPlanBuilt"] is True
    assert result["disabledSendExecutorModelBuilt"] is True
    assert result["sendExecutorPrepared"] is True
    assert result["sendExecutorPlan"]["dispatchAllowedNow"] is False
    assert result["sendExecutorPlan"]["requestSendAllowedNow"] is False
    assert result["sendExecutorPlan"]["networkAllowedNow"] is False
    assert result["sendExecutorPlan"]["secretReadAllowedNow"] is False
    assert result["authorizationBoundary"]["sendAllowedInThisStep"] is False
    assert result["authorizationBoundary"]["manualApprovalGranted"] is False
    assert result["secretBoundary"]["readAllowedNow"] is False
    assert result["networkBoundary"]["networkAllowedNow"] is False
    assert result["responseHandlingBoundary"]["validResponseDefaultStatus"] == "WAITING_REVIEW"
    assert result["rollbackBoundary"]["safeFailureLeavesGeneratedContent"] is False
    assert secret not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_send_executor_with_missing_send_flags_is_not_ready():
    result = prepare_real_llm_minimal_call_send_executor_disabled(
        confirmed_request(
            minimal_call_poc_review_confirmed=False,
            send_executor_boundary_confirmed=False,
            no_request_send_in_disabled_executor_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["sendExecutorChecklist"]}

    assert result["minimalCallPocReviewReady"] is True
    assert result["sendExecutorChecklistReady"] is False
    assert result["minimalCallSendExecutorDisabledReady"] is False
    assert result["readyForExplicitRealRequestSendAuthorization"] is False
    assert checklist["minimal_call_poc_review_ready"]["passed"] is True
    assert checklist["minimal_call_poc_review_confirmed"]["passed"] is False
    assert checklist["send_executor_boundary_confirmed"]["passed"] is False
    assert checklist["no_request_send_in_disabled_executor_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        prepare_real_llm_minimal_call_send_executor_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_minimal_call_send_executor_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["minimalCallSendExecutorDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_prepare_return_json(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-minimal-call-send-executor-disabled", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["minimalCallSendExecutorDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["minimalCallPocReviewReady"] is True
    assert payload["data"]["minimalCallSendExecutorDisabledReady"] is True
    assert payload["data"]["readyForExplicitRealRequestSendAuthorization"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_prepare_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-minimal-call-send-executor-disabled", "prepare", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmMinimalCallSendExecutorDisabledContext"]
    assert context["minimalCallPocReviewReady"] is False
    assert context["minimalCallSendExecutorDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-minimal-call-send-executor-disabled",
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
