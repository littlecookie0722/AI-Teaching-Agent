import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendExecutorDisabledRequest,
    build_real_llm_request_send_executor_disabled,
    build_real_llm_request_send_executor_disabled_error_context,
    describe_real_llm_request_send_executor_disabled,
)
from test_real_llm_request_send_execution_request_disabled import (
    assert_no_real_call as assert_execution_request_no_real_call,
    confirmed_cli_args as confirmed_execution_request_cli_args,
    confirmed_payload as confirmed_execution_request_payload,
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
    payload = confirmed_execution_request_payload(
        explicit_request_send_executor_disabled_opt_in=True,
        request_send_execution_request_confirmed=True,
        executor_scope_confirmed=True,
        executor_record_confirmed=True,
        executor_disabled_boundary_confirmed=True,
        executor_dispatch_block_confirmed=True,
        send_runtime_disabled_confirmed=True,
        single_request_executor_confirmed=True,
        lab_only_executor_confirmed=True,
        runtime_kill_switch_confirmed_for_executor=True,
        audit_event_confirmed_for_executor=True,
        rollback_confirmed_for_executor=True,
        no_executor_start_in_request_send_executor_confirmed=True,
        no_executor_run_creation_in_request_send_executor_confirmed=True,
        no_executor_dispatch_in_request_send_executor_confirmed=True,
        no_request_send_in_request_send_executor_confirmed=True,
        no_secret_read_in_request_send_executor_confirmed=True,
        no_network_access_in_request_send_executor_confirmed=True,
        no_generated_content_creation_in_request_send_executor_confirmed=True,
        no_task_creation_in_request_send_executor_confirmed=True,
        no_publish_in_request_send_executor_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendExecutorDisabledRequest(**confirmed_payload(**overrides))


def confirmed_cli_args():
    args = confirmed_execution_request_cli_args()
    args[1] = "real-llm-request-send-executor-disabled"
    args[2] = "prepare"
    args.extend(
        [
            "--explicit-request-send-executor-disabled-opt-in",
            "--confirm-request-send-execution-request",
            "--confirm-executor-scope",
            "--confirm-executor-record",
            "--confirm-executor-disabled-boundary",
            "--confirm-executor-dispatch-block",
            "--confirm-send-runtime-disabled",
            "--confirm-single-request-executor",
            "--confirm-lab-only-executor",
            "--confirm-runtime-kill-switch-for-executor",
            "--confirm-audit-event-for-executor",
            "--confirm-rollback-for-executor",
            "--confirm-no-executor-start-in-request-send-executor",
            "--confirm-no-executor-run-creation-in-request-send-executor",
            "--confirm-no-executor-dispatch-in-request-send-executor",
            "--confirm-no-request-send-in-request-send-executor",
            "--confirm-no-secret-read-in-request-send-executor",
            "--confirm-no-network-access-in-request-send-executor",
            "--confirm-no-generated-content-creation-in-request-send-executor",
            "--confirm-no-task-creation-in-request-send-executor",
            "--confirm-no-publish-in-request-send-executor",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_execution_request_no_real_call(context)
    assert context["sendExecutorStarted"] is False
    assert context["sendExecutorRunCreated"] is False
    assert context["executorStarted"] is False
    assert context["executorRunCreated"] is False


def test_contract_declares_disabled_executor_only():
    contract = load_json("providers/real-llm-request-send-executor-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_EXECUTOR_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_execution_request_disabled"
    assert contract["rules"]["requiresRequestSendExecutionRequestDisabledReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendExecutorDisabledReady"] is True
    assert contract["assertions"]["readyForFinalRealRequestSendApprovalReview"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["sendExecutorStarted"] is False
    assert contract["assertions"]["sendExecutorRunCreated"] is False
    assert contract["assertions"]["sendExecutorDispatched"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["executorBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_prepare_send():
    descriptor = describe_real_llm_request_send_executor_disabled(root=ROOT)

    assert descriptor["requestSendExecutorDisabledId"] == "real_llm_request_send_executor_disabled"
    assert descriptor["executorMode"] == "DISABLED_REAL_REQUEST_SEND_EXECUTOR_MODEL_ONLY"
    assert descriptor["requestSendExecutionRequestDisabledReady"] is False
    assert descriptor["requestSendExecutorDisabledReady"] is False
    assert descriptor["readyForFinalRealRequestSendApprovalReview"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_executor_requires_upstream_execution_request():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_executor_disabled(
            RealLlmRequestSendExecutorDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_executor_disabled_error_context(
        exc,
        request=RealLlmRequestSendExecutorDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendExecutionRequestDisabledReady"] is False
    assert context["requestSendExecutorDisabledReady"] is False
    assert_no_real_call(context)


def test_executor_ready_still_does_not_create_start_dispatch_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_executor_disabled(confirmed_request(), root=ROOT)

    assert result["requestSendExecutionRequestDisabledReady"] is True
    assert result["executionRequestSummary"]["requestSendExecutionRequestDisabledReady"] is True
    assert result["requestSendExecutorChecklistReady"] is True
    assert result["requestSendExecutorDisabledReady"] is True
    assert result["readyForFinalRealRequestSendApprovalReview"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["requestSendExecutorPlanBuilt"] is True
    assert result["requestSendExecutorDisabledModelBuilt"] is True
    assert result["requestSendExecutor"]["createdNow"] is False
    assert result["requestSendExecutor"]["startedNow"] is False
    assert result["requestSendExecutor"]["runCreatedNow"] is False
    assert result["requestSendExecutor"]["dispatchedNow"] is False
    assert result["requestSendExecutor"]["manualApprovalGrantedNow"] is False
    assert result["requestSendExecutor"]["realCallAuthorizedNow"] is False
    assert result["requestSendExecutor"]["sendAllowedNow"] is False
    assert result["requestSendExecutorPolicy"]["startExecutorNow"] is False
    assert result["sendExecutionBoundary"]["sendExecutorStarted"] is False
    assert result["sendExecutionBoundary"]["sendExecutorRunCreated"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_executor_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_executor_disabled(
        confirmed_request(
            executor_record_confirmed=False,
            no_executor_start_in_request_send_executor_confirmed=False,
            no_request_send_in_request_send_executor_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["requestSendExecutorChecklist"]}

    assert result["requestSendExecutionRequestDisabledReady"] is True
    assert result["requestSendExecutorDisabledReady"] is False
    assert result["readyForFinalRealRequestSendApprovalReview"] is False
    assert checklist["request_send_execution_request_disabled_ready"]["passed"] is True
    assert checklist["executor_record_confirmed"]["passed"] is False
    assert checklist["no_executor_start_in_request_send_executor_confirmed"]["passed"] is False
    assert checklist["no_request_send_in_request_send_executor_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_executor_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_executor_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendExecutorDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_prepare_return_json(capsys):
    exit_code, payload = run_cli(["provider", "real-llm-request-send-executor-disabled", "describe"], capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutorDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutionRequestDisabledReady"] is True
    assert payload["data"]["requestSendExecutorDisabledReady"] is True
    assert payload["data"]["readyForFinalRealRequestSendApprovalReview"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_prepare_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-executor-disabled", "prepare", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendExecutorDisabledContext"]
    assert context["requestSendExecutionRequestDisabledReady"] is False
    assert context["requestSendExecutorDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-executor-disabled",
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
