import json
from pathlib import Path

import pytest

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmRequestSendExecutorCreationGateDisabledRequest,
    build_real_llm_request_send_executor_creation_gate_disabled,
    build_real_llm_request_send_executor_creation_gate_disabled_error_context,
    describe_real_llm_request_send_executor_creation_gate_disabled,
)
from test_real_llm_request_send_runtime_gate_disabled import (
    assert_no_real_call as assert_runtime_gate_no_real_call,
    confirmed_cli_args as confirmed_runtime_gate_cli_args,
    confirmed_payload as confirmed_runtime_gate_payload,
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
    payload = confirmed_runtime_gate_payload(
        explicit_request_send_executor_creation_gate_disabled_opt_in=True,
        runtime_gate_disabled_confirmed=True,
        executor_creation_scope_confirmed=True,
        executor_creation_record_confirmed=True,
        executor_factory_boundary_confirmed=True,
        executor_identity_boundary_confirmed=True,
        executor_runtime_gate_reference_confirmed=True,
        executor_secret_boundary_confirmed=True,
        executor_client_boundary_confirmed=True,
        executor_dispatch_boundary_confirmed=True,
        executor_audit_redaction_confirmed=True,
        executor_rollback_confirmed=True,
        executor_waiting_review_policy_confirmed=True,
        no_executor_factory_materialization_confirmed=True,
        no_executor_creation_confirmed=True,
        no_executor_persistence_confirmed=True,
        no_executor_start_confirmed=True,
        no_executor_run_creation_confirmed=True,
        no_executor_dispatch_confirmed=True,
        no_request_send_in_executor_creation_gate_confirmed=True,
        no_secret_read_in_executor_creation_gate_confirmed=True,
        no_client_creation_in_executor_creation_gate_confirmed=True,
        no_network_access_in_executor_creation_gate_confirmed=True,
        no_real_call_authorization_in_executor_creation_gate_confirmed=True,
        no_generated_content_creation_in_executor_creation_gate_confirmed=True,
        no_task_creation_in_executor_creation_gate_confirmed=True,
        no_publish_in_executor_creation_gate_confirmed=True,
    )
    payload.update(overrides)
    return payload


def confirmed_request(**overrides):
    return RealLlmRequestSendExecutorCreationGateDisabledRequest(
        **confirmed_payload(**overrides)
    )


def confirmed_cli_args():
    args = confirmed_runtime_gate_cli_args()
    args[1] = "real-llm-request-send-executor-creation-gate-disabled"
    args[2] = "evaluate"
    args.extend(
        [
            "--explicit-request-send-executor-creation-gate-disabled-opt-in",
            "--confirm-runtime-gate-disabled",
            "--confirm-executor-creation-scope",
            "--confirm-executor-creation-record",
            "--confirm-executor-factory-boundary",
            "--confirm-executor-identity-boundary",
            "--confirm-executor-runtime-gate-reference",
            "--confirm-executor-secret-boundary",
            "--confirm-executor-client-boundary",
            "--confirm-executor-dispatch-boundary",
            "--confirm-executor-audit-redaction",
            "--confirm-executor-rollback",
            "--confirm-executor-waiting-review-policy",
            "--confirm-no-executor-factory-materialization",
            "--confirm-no-executor-creation",
            "--confirm-no-executor-persistence",
            "--confirm-no-executor-start",
            "--confirm-no-executor-run-creation",
            "--confirm-no-dispatch-in-executor-creation-gate",
            "--confirm-no-request-send-in-executor-creation-gate",
            "--confirm-no-secret-read-in-executor-creation-gate",
            "--confirm-no-client-creation-in-executor-creation-gate",
            "--confirm-no-network-access-in-executor-creation-gate",
            "--confirm-no-real-call-authorization-in-executor-creation-gate",
            "--confirm-no-generated-content-creation-in-executor-creation-gate",
            "--confirm-no-task-creation-in-executor-creation-gate",
            "--confirm-no-publish-in-executor-creation-gate",
        ]
    )
    return args


def assert_no_real_call(context):
    assert_runtime_gate_no_real_call(context)
    assert context["executorFactoryMaterialized"] is False
    assert context["sendExecutorCreated"] is False
    assert context["sendExecutorPersisted"] is False
    assert context["sendExecutorStarted"] is False
    assert context["sendExecutorRunCreated"] is False
    assert context["sendExecutorDispatched"] is False


def test_contract_declares_executor_creation_gate_disabled_only():
    contract = load_json("providers/real-llm-request-send-executor-creation-gate-disabled.contract.json")

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "REAL_LLM_REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_ONLY"
    assert contract["upstreamGateId"] == "real_llm_request_send_runtime_gate_disabled"
    assert contract["rules"]["requiresRequestSendRuntimeGateDisabledReady"] is True
    assert contract["rules"]["manualApprovalGranted"] is False
    assert contract["rules"]["realCallAuthorized"] is False
    assert contract["assertions"]["requestSendExecutorCreationGateDisabledReady"] is True
    assert contract["assertions"]["readyForRealRequestSendExecutorDispatchGate"] is True
    assert contract["assertions"]["readyForRealRequestSend"] is False
    assert contract["assertions"]["executorFactoryMaterialized"] is False
    assert contract["assertions"]["sendExecutorCreated"] is False
    assert contract["assertions"]["sendExecutorPersisted"] is False
    assert contract["assertions"]["sendExecutorStarted"] is False
    assert contract["assertions"]["sendExecutorRunCreated"] is False
    assert contract["assertions"]["sendExecutorDispatched"] is False
    assert contract["assertions"]["requestSent"] is False
    assert contract["executorCreationBoundary"]["sendAllowedNow"] is False


def test_describe_is_safe_and_does_not_create_executor():
    descriptor = describe_real_llm_request_send_executor_creation_gate_disabled(
        root=ROOT
    )

    assert descriptor["requestSendExecutorCreationGateDisabledId"] == (
        "real_llm_request_send_executor_creation_gate_disabled"
    )
    assert descriptor["requestSendExecutorCreationGateMode"] == (
        "REQUEST_SEND_EXECUTOR_CREATION_GATE_DISABLED_MODEL_ONLY"
    )
    assert descriptor["requestSendRuntimeGateDisabledReady"] is False
    assert descriptor["requestSendExecutorCreationGateDisabledReady"] is False
    assert descriptor["readyForRealRequestSendExecutorDispatchGate"] is False
    assert descriptor["readyForRealRequestSend"] is False
    assert_no_real_call(descriptor)


def test_executor_creation_gate_requires_upstream_runtime_gate():
    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_executor_creation_gate_disabled(
            RealLlmRequestSendExecutorCreationGateDisabledRequest(provider_id="openai"),
            root=ROOT,
        )

    exc = exc_info.value
    assert exc.code == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = build_real_llm_request_send_executor_creation_gate_disabled_error_context(
        exc,
        request=RealLlmRequestSendExecutorCreationGateDisabledRequest(provider_id="openai"),
        root=ROOT,
    )
    assert context["requestSendRuntimeGateDisabledReady"] is False
    assert context["requestSendExecutorCreationGateDisabledReady"] is False
    assert_no_real_call(context)


def test_executor_creation_gate_ready_still_does_not_create_dispatch_or_send():
    sensitive_value = "fake-secret-that-must-be-redacted"
    result = build_real_llm_request_send_executor_creation_gate_disabled(
        confirmed_request(),
        root=ROOT,
    )

    assert result["requestSendRuntimeGateDisabledReady"] is True
    assert result["requestSendRuntimeGateDisabledSummary"]["requestSendRuntimeGateDisabledReady"] is True
    assert result["requestSendExecutorCreationGateChecklistReady"] is True
    assert result["requestSendExecutorCreationGateDisabledReady"] is True
    assert result["readyForRealRequestSendExecutorDispatchGate"] is True
    assert result["readyForRealRequestSend"] is False
    assert result["executorCreationGateModelBuilt"] is True
    assert result["executorCreationGateModel"]["executorFactoryMaterializedNow"] is False
    assert result["executorCreationGateModel"]["executorCreatedNow"] is False
    assert result["executorCreationGateModel"]["executorPersistedNow"] is False
    assert result["executorCreationGateModel"]["executorStartedNow"] is False
    assert result["executorCreationGateModel"]["executorRunCreatedNow"] is False
    assert result["executorCreationGateModel"]["executorDispatchedNow"] is False
    assert result["executorCreationGateModel"]["clientCreationAllowedNow"] is False
    assert result["executorCreationGateModel"]["realCallAuthorizedNow"] is False
    assert result["executorCreationGateModel"]["sendAllowedNow"] is False
    assert result["executorCreationGatePolicy"]["createExecutorNow"] is False
    assert result["executorCreationGatePolicy"]["dispatchExecutorNow"] is False
    assert result["sendExecutionBoundary"]["sendExecutorCreated"] is False
    assert result["sendExecutionBoundary"]["requestSent"] is False
    assert sensitive_value not in json.dumps(result, ensure_ascii=False)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in json.dumps(result, ensure_ascii=False)
    assert_no_real_call(result)


def test_executor_creation_gate_with_missing_flags_is_not_ready():
    result = build_real_llm_request_send_executor_creation_gate_disabled(
        confirmed_request(
            executor_creation_scope_confirmed=False,
            no_executor_creation_confirmed=False,
            no_real_call_authorization_in_executor_creation_gate_confirmed=False,
        ),
        root=ROOT,
    )
    checklist = {
        item["id"]: item
        for item in result["requestSendExecutorCreationGateChecklist"]
    }

    assert result["requestSendRuntimeGateDisabledReady"] is True
    assert result["requestSendExecutorCreationGateDisabledReady"] is False
    assert result["readyForRealRequestSendExecutorDispatchGate"] is False
    assert checklist["request_send_runtime_gate_disabled_ready"]["passed"] is True
    assert checklist["executor_creation_scope_confirmed"]["passed"] is False
    assert checklist["no_executor_creation_confirmed"]["passed"] is False
    assert checklist["no_real_call_authorization_in_executor_creation_gate_confirmed"]["passed"] is False
    assert_no_real_call(result)


def test_invalid_provider_is_rejected_safely():
    request = confirmed_request(provider_id="anthropic")

    with pytest.raises(ProviderError) as exc_info:
        build_real_llm_request_send_executor_creation_gate_disabled(request, root=ROOT)

    assert exc_info.value.code == "VALIDATION_ERROR"
    context = build_real_llm_request_send_executor_creation_gate_disabled_error_context(
        exc_info.value,
        request=request,
        root=ROOT,
    )
    assert context["providerId"] == "anthropic"
    assert context["requestSendExecutorCreationGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_describe_and_evaluate_return_json(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-executor-creation-gate-disabled",
            "describe",
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendExecutorCreationGateDisabledReady"] is False
    assert_no_real_call(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["requestSendRuntimeGateDisabledReady"] is True
    assert payload["data"]["requestSendExecutorCreationGateDisabledReady"] is True
    assert payload["data"]["readyForRealRequestSendExecutorDispatchGate"] is True
    assert payload["data"]["readyForRealRequestSend"] is False
    assert_no_real_call(payload["data"])


def test_cli_evaluate_missing_upstream_confirmations_returns_safe_error(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-executor-creation-gate-disabled",
            "evaluate",
            "--provider",
            "openai",
        ],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_REQUEST_REVIEW_CONFIRMATION_REQUIRED"
    context = payload["realLlmRequestSendExecutorCreationGateDisabledContext"]
    assert context["requestSendRuntimeGateDisabledReady"] is False
    assert context["requestSendExecutorCreationGateDisabledReady"] is False
    assert_no_real_call(context)


def test_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-request-send-executor-creation-gate-disabled",
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
