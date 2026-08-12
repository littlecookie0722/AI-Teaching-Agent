import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmPreSendDryRunRecordRequest,
    build_real_llm_pre_send_dry_run_record,
    build_real_llm_pre_send_dry_run_record_error_context,
    describe_real_llm_pre_send_dry_run_record,
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
        "approval_ref": "PRE-SEND-DRY-RUN-001",
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
    }
    payload.update(overrides)
    return RealLlmPreSendDryRunRecordRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-llm-pre-send-dry-run-record",
        "record",
        "--provider",
        "openai",
        "--payload",
        '{"source":"examples/input/demo-source.md","api_key":"fake-secret-that-must-be-redacted"}',
        "--reviewer",
        "teacher_1",
        "--approval-ref",
        "PRE-SEND-DRY-RUN-001",
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
    ]


def assert_no_real_call(context):
    assert context["executorStarted"] is False
    assert context["executorRunCreated"] is False
    assert context["executorDispatched"] is False
    assert context["dryRunRecordMaterialized"] is False
    assert context["dryRunRecordPersisted"] is False
    assert context["dryRunRecordWritten"] is False
    assert context["dryRunExecuted"] is False
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
    assert context["autoPublishAllowed"] is False
    assert context["realPublish"] is False
    assert context["realCallAuthorized"] is False


def test_contract_declares_pre_send_record_only():
    contract = load_json("providers/real-llm-pre-send-dry-run-record.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_PRE_SEND_DRY_RUN_RECORD_ONLY"
    assert contract["upstreamGateId"] == "real_llm_first_call_executor_disabled"
    assert contract["rules"]["requiresDisabledFirstCallExecutorReady"] is True
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["preSendDryRunRecordReady"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["dryRunExecuted"] is False
    assert contract["assertions"]["dryRunRecordWritten"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["assertions"]["realLlmCalled"] is False


def test_describe_is_safe_and_does_not_build_record():
    descriptor = describe_real_llm_pre_send_dry_run_record(root=ROOT)

    assert descriptor["preSendDryRunRecordId"] == "real_llm_pre_send_dry_run_record"
    assert descriptor["recordMode"] == "PRE_SEND_DRY_RUN_RECORD_MODEL_ONLY"
    assert descriptor["disabledFirstCallExecutorReady"] is False
    assert descriptor["preSendDryRunRecordReady"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_record_requires_upstream_disabled_executor_before_build():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_pre_send_dry_run_record(
            RealLlmPreSendDryRunRecordRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_pre_send_dry_run_record_error_context(
        exc,
        request=RealLlmPreSendDryRunRecordRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["disabledFirstCallExecutorReady"] is False
    assert context["preSendDryRunRecordReady"] is False
    assert_no_real_call(context)


def test_record_ready_still_does_not_execute_or_send():
    secret = "fake-secret-that-must-be-redacted"
    result = build_real_llm_pre_send_dry_run_record(confirmed_request(), root=ROOT)

    assert result["disabledFirstCallExecutorReady"] is True
    assert result["explicitRequestReviewOptIn"] is True
    assert result["explicitFirstCallApprovalOptIn"] is True
    assert result["explicitDisabledExecutorOptIn"] is True
    assert result["readyForMinimalRealCallPocReview"] is True
    assert result["preSendDryRunChecklistReady"] is True
    assert result["preSendDryRunRecordReady"] is True
    assert result["readyForMinimalRealCallPoc"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["dryRunRecordBuilt"] is True
    assert result["dryRunRecord"]["built"] is True
    assert result["dryRunRecord"]["requestSendAllowedNow"] is False
    assert result["auditLogPlan"]["logSecretValue"] is False
    assert result["rollbackPlan"]["persistentMutationPlanned"] is False
    assert result["validationPlan"]["generatedContentDefaultStatus"] == "WAITING_REVIEW"
    assert secret not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_record_with_missing_pre_send_flags_is_not_ready():
    result = build_real_llm_pre_send_dry_run_record(
        confirmed_request(
            disabled_executor_confirmed=False,
            log_redaction_confirmed=False,
            no_request_send_in_dry_run_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["preSendDryRunChecklist"]}

    assert result["disabledFirstCallExecutorReady"] is True
    assert result["preSendDryRunRecordReady"] is False
    assert result["readyForMinimalRealCallPoc"] is False
    assert checklist["disabled_executor_ready"]["passed"] is True
    assert checklist["disabled_executor_confirmed"]["passed"] is False
    assert checklist["log_redaction_confirmed"]["passed"] is False
    assert checklist["no_request_send_in_dry_run_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_pre_send_dry_run_record(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_pre_send_dry_run_record_error_context(exc_info.value, request=request, root=ROOT)
    assert context["providerId"] == "anthropic"
    assert context["preSendDryRunRecordReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_record_return_json(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-pre-send-dry-run-record", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["preSendDryRunRecordReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["disabledFirstCallExecutorReady"] is True
    assert payload["data"]["preSendDryRunRecordReady"] is True
    assert payload["data"]["readyForMinimalRealCallPoc"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_record_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-pre-send-dry-run-record", "record", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmPreSendDryRunRecordContext"]
    assert context["disabledFirstCallExecutorReady"] is False
    assert context["preSendDryRunRecordReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-pre-send-dry-run-record",
            "record",
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
