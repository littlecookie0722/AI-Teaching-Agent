import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmFirstCallExecutorDisabledRequest,
    build_real_llm_first_call_executor_disabled_error_context,
    describe_real_llm_first_call_executor_disabled,
    prepare_real_llm_first_call_executor_disabled,
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
        "approval_ref": "FIRST-CALL-EXECUTOR-001",
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
    }
    payload.update(overrides)
    return RealLlmFirstCallExecutorDisabledRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-llm-first-call-executor-disabled",
        "prepare",
        "--provider",
        "openai",
        "--payload",
        '{"source":"examples/input/demo-source.md","api_key":"fake-secret-that-must-be-redacted"}',
        "--reviewer",
        "teacher_1",
        "--approval-ref",
        "FIRST-CALL-EXECUTOR-001",
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
    ]


def assert_no_real_call(context):
    assert context["executorStarted"] is False
    assert context["executorRunCreated"] is False
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
    assert context["autoPublishAllowed"] is False
    assert context["realPublish"] is False
    assert context["realCallAuthorized"] is False


def test_contract_declares_disabled_executor_only():
    contract = load_json("providers/real-llm-first-call-executor-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_FIRST_CALL_EXECUTOR_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_first_call_approval_gate"
    assert contract["rules"]["requiresApprovalGateReady"] is True
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["disabledFirstCallExecutorReady"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["executorDispatched"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["assertions"]["realLlmCalled"] is False


def test_describe_is_safe_and_does_not_prepare_executor():
    descriptor = describe_real_llm_first_call_executor_disabled(root=ROOT)

    assert descriptor["firstCallExecutorDisabledId"] == "real_llm_first_call_executor_disabled"
    assert descriptor["executorMode"] == "DISABLED_EXECUTOR_MODEL_ONLY"
    assert descriptor["approvalGateReady"] is False
    assert descriptor["disabledFirstCallExecutorReady"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_executor_requires_upstream_approval_gate_before_prepare():
    with pytest.raises(ProviderError) as exc_info:
        prepare_real_llm_first_call_executor_disabled(
            RealLlmFirstCallExecutorDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_first_call_executor_disabled_error_context(
        exc,
        request=RealLlmFirstCallExecutorDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["approvalGateReady"] is False
    assert context["disabledFirstCallExecutorReady"] is False
    assert_no_real_call(context)


def test_executor_ready_still_does_not_dispatch_or_send():
    secret = "fake-secret-that-must-be-redacted"
    result = prepare_real_llm_first_call_executor_disabled(confirmed_request(), root=ROOT)

    assert result["approvalGateReady"] is True
    assert result["approvalGateSummary"]["readyForDisabledFirstCallExecutor"] is True
    assert result["disabledExecutorChecklistReady"] is True
    assert result["disabledFirstCallExecutorReady"] is True
    assert result["readyForMinimalRealCallPocReview"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["executorPrepared"] is True
    assert result["executorPlan"]["executorDispatchAllowedNow"] is False
    assert result["executorPlan"]["requestSendAllowedNow"] is False
    assert result["executorPlan"]["networkAllowedNow"] is False
    assert result["executorPlan"]["secretReadAllowedNow"] is False
    assert secret not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_executor_with_missing_executor_flags_is_not_ready():
    result = prepare_real_llm_first_call_executor_disabled(
        confirmed_request(
            first_call_approval_gate_confirmed=False,
            no_executor_dispatch_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["disabledExecutorChecklist"]}

    assert result["approvalGateReady"] is True
    assert result["disabledFirstCallExecutorReady"] is False
    assert result["readyForMinimalRealCallPocReview"] is False
    assert checklist["approval_gate_ready"]["passed"] is True
    assert checklist["first_call_approval_gate_confirmed"]["passed"] is False
    assert checklist["no_executor_dispatch_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        prepare_real_llm_first_call_executor_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_first_call_executor_disabled_error_context(exc_info.value, request=request, root=ROOT)
    assert context["providerId"] == "anthropic"
    assert context["disabledFirstCallExecutorReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_prepare_return_json(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-first-call-executor-disabled", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["disabledFirstCallExecutorReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["approvalGateReady"] is True
    assert payload["data"]["disabledFirstCallExecutorReady"] is True
    assert payload["data"]["readyForMinimalRealCallPocReview"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_prepare_missing_approval_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-first-call-executor-disabled", "prepare", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmFirstCallExecutorDisabledContext"]
    assert context["approvalGateReady"] is False
    assert context["disabledFirstCallExecutorReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-first-call-executor-disabled",
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
