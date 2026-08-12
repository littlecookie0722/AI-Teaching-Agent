import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendExecutionRequestDisabledRequest,
    build_real_llm_request_send_execution_request_disabled,
    build_real_llm_request_send_execution_request_disabled_error_context,
    describe_real_llm_request_send_execution_request_disabled,
)
from test_real_llm_request_send_authorization_package import (
    assert_no_real_call as assert_authorization_no_real_call,
    confirmed_cli_args as confirmed_authorization_cli_args,
    confirmed_payload as confirmed_authorization_payload,
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
    payload = confirmed_authorization_payload(
        explicit_request_send_execution_request_disabled_opt_in=True,
        request_send_authorization_package_confirmed=True,
        execution_request_scope_confirmed=True,
        execution_request_record_confirmed=True,
        send_executor_disabled_boundary_confirmed=True,
        final_human_authorization_review_confirmed=True,
        single_request_execution_confirmed=True,
        lab_only_execution_confirmed=True,
        runtime_kill_switch_confirmed=True,
        audit_event_confirmed_for_execution_request=True,
        rollback_confirmed_for_execution_request=True,
        no_manual_approval_grant_in_execution_request_confirmed=True,
        no_real_call_authorization_in_execution_request_confirmed=True,
        no_executor_dispatch_in_execution_request_confirmed=True,
        no_request_send_in_execution_request_confirmed=True,
        no_secret_read_in_execution_request_confirmed=True,
        no_network_access_in_execution_request_confirmed=True,
        no_task_creation_in_execution_request_confirmed=True,
        no_publish_in_execution_request_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendExecutionRequestDisabledRequest(**confirmed_payload(**overrides))


def confirmed_cli_args():
    args = confirmed_authorization_cli_args()
    args[1] = "real-llm-request-send-execution-request-disabled"
    args[2] = "evaluate"
    args.extend(
        [
            "--explicit-request-send-execution-request-disabled-opt-in",
            "--confirm-request-send-authorization-package",
            "--confirm-execution-request-scope",
            "--confirm-execution-request-record",
            "--confirm-send-executor-disabled-boundary",
            "--confirm-final-human-authorization-review",
            "--confirm-single-request-execution",
            "--confirm-lab-only-execution",
            "--confirm-runtime-kill-switch",
            "--confirm-audit-event-for-execution-request",
            "--confirm-rollback-for-execution-request",
            "--confirm-no-manual-approval-grant-in-execution-request",
            "--confirm-no-real-call-authorization-in-execution-request",
            "--confirm-no-executor-dispatch-in-execution-request",
            "--confirm-no-request-send-in-execution-request",
            "--confirm-no-secret-read-in-execution-request",
            "--confirm-no-network-access-in-execution-request",
            "--confirm-no-task-creation-in-execution-request",
            "--confirm-no-publish-in-execution-request",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_authorization_no_real_call(context)
    assert context["executionRequestMaterialized"] is False
    assert context["executionRequestPersisted"] is False
    assert context["executionRequestQueued"] is False
    assert context["executionRequestDispatched"] is False


def test_contract_declares_disabled_execution_request_only():
    contract = load_json("providers/real-llm-request-send-execution-request-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_EXECUTION_REQUEST_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_authorization_package"
    assert contract["rules"]["requiresRequestSendAuthorizationPackageReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendExecutionRequestDisabledReady"] is True
    assert contract["assertions"]["readyForDisabledRealRequestSendExecutor"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["executionRequestPersisted"] is False
    assert contract["assertions"]["executionRequestDispatched"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["executionRequestBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_prepare_send():
    descriptor = describe_real_llm_request_send_execution_request_disabled(root=ROOT)

    assert descriptor["requestSendExecutionRequestDisabledId"] == (
        "real_llm_request_send_execution_request_disabled"
    )
    assert descriptor["executionRequestMode"] == "DISABLED_REAL_REQUEST_SEND_EXECUTION_REQUEST_MODEL_ONLY"
    assert descriptor["requestSendAuthorizationPackageReady"] is False
    assert descriptor["requestSendExecutionRequestDisabledReady"] is False
    assert descriptor["readyForDisabledRealRequestSendExecutor"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_execution_request_requires_upstream_authorization_package():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_execution_request_disabled(
            RealLlmRequestSendExecutionRequestDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_execution_request_disabled_error_context(
        exc,
        request=RealLlmRequestSendExecutionRequestDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendAuthorizationPackageReady"] is False
    assert context["requestSendExecutionRequestDisabledReady"] is False
    assert_no_real_call(context)


def test_execution_request_ready_still_does_not_persist_dispatch_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_execution_request_disabled(confirmed_request(), root=ROOT)

    assert result["requestSendAuthorizationPackageReady"] is True
    assert result["authorizationPackageSummary"]["requestSendAuthorizationPackageReady"] is True
    assert result["requestSendExecutionRequestChecklistReady"] is True
    assert result["requestSendExecutionRequestDisabledReady"] is True
    assert result["readyForDisabledRealRequestSendExecutor"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["executionRequestBuilt"] is True
    assert result["executionRequest"]["persistedNow"] is False
    assert result["executionRequest"]["queuedNow"] is False
    assert result["executionRequest"]["dispatchedNow"] is False
    assert result["executionRequest"]["manualApprovalGrantedNow"] is False
    assert result["executionRequest"]["realCallAuthorizedNow"] is False
    assert result["executionRequest"]["sendAllowedNow"] is False
    assert result["executionRequestPolicy"]["persistRecordNow"] is False
    assert result["sendExecutionBoundary"]["executionRequestDispatched"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_execution_request_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_execution_request_disabled(
        confirmed_request(
            execution_request_record_confirmed=False,
            no_executor_dispatch_in_execution_request_confirmed=False,
            no_request_send_in_execution_request_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {item["id"]: item for item in result["requestSendExecutionRequestChecklist"]}

    assert result["requestSendAuthorizationPackageReady"] is True
    assert result["requestSendExecutionRequestDisabledReady"] is False
    assert result["readyForDisabledRealRequestSendExecutor"] is False
    assert checklist["request_send_authorization_package_ready"]["passed"] is True
    assert checklist["execution_request_record_confirmed"]["passed"] is False
    assert checklist["no_executor_dispatch_in_execution_request_confirmed"]["passed"] is False
    assert checklist["no_request_send_in_execution_request_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_execution_request_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_execution_request_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendExecutionRequestDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_evaluate_return_json(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-execution-request-disabled", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutionRequestDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendAuthorizationPackageReady"] is True
    assert payload["data"]["requestSendExecutionRequestDisabledReady"] is True
    assert payload["data"]["readyForDisabledRealRequestSendExecutor"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_evaluate_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-llm-request-send-execution-request-disabled", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendExecutionRequestDisabledContext"]
    assert context["requestSendAuthorizationPackageReady"] is False
    assert context["requestSendExecutionRequestDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-execution-request-disabled",
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
