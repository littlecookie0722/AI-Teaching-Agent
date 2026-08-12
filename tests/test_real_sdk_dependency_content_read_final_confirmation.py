import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyContentReadFinalConfirmationRequest,
    build_real_sdk_dependency_content_read_final_confirmation,
    build_real_sdk_dependency_content_read_final_confirmation_error_context,
    describe_real_sdk_dependency_content_read_final_confirmation,
)
from tests.test_real_sdk_dependency_content_read_plan import (
    assert_safe_content_read_plan_context,
    confirmed_cli_args as confirmed_plan_cli_args,
    confirmed_request as confirmed_plan_request,
)
from tests.test_real_sdk_dependency_executor_disabled import assert_json_envelope


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def run_cli(args, capsys):
    exit_code = main(args)
    output = capsys.readouterr().out
    payload = json.loads(output)
    return exit_code, payload


def assert_safe_content_read_final_context(context):
    assert_safe_content_read_plan_context(context)
    for key in [
        "contentReadFinalConfirmationRecordPersisted",
        "contentReadFinalConfirmationArtifactWritten",
        "contentReadFinalConfirmationExecuted",
        "contentReadExecutionApprovalGranted",
        "contentReadExecutionTaskCreated",
        "realCallAfterContentReadFinalConfirmationAuthorized",
    ]:
        assert context[key] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_plan_request())
    payload.update(
        {
            "approval_ref": "CONTENT-READ-FINAL-001",
            "content_read_final_scope_confirmed": True,
            "content_read_final_approver_confirmed": True,
            "content_read_ticket_confirmed": True,
            "content_read_targets_final_confirmed": True,
            "manifest_read_final_confirmed": True,
            "lockfile_read_final_confirmed": True,
            "redaction_policy_final_confirmed": True,
            "no_raw_content_return_final_confirmed": True,
            "no_content_persistence_final_confirmed": True,
            "no_content_artifact_write_final_confirmed": True,
            "no_patch_generation_after_content_read_final_confirmed": True,
            "no_command_execution_after_content_read_final_confirmed": True,
            "no_dependency_install_after_content_read_final_confirmed": True,
            "no_real_call_after_content_read_final_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyContentReadFinalConfirmationRequest(**payload)


def confirmed_cli_args():
    args = confirmed_plan_cli_args()
    args[1] = "real-sdk-dependency-content-read-final-confirmation"
    args[2] = "confirm-read"
    args[args.index("--approval-ref") + 1] = "CONTENT-READ-FINAL-001"
    flags = [
        "content-read-final-scope",
        "content-read-final-approver",
        "content-read-ticket",
        "content-read-targets-final",
        "manifest-read-final",
        "lockfile-read-final",
        "redaction-policy-final",
        "no-raw-content-return-final",
        "no-content-persistence-final",
        "no-content-artifact-write-final",
        "no-patch-generation-after-content-read-final",
        "no-command-execution-after-content-read-final",
        "no-dependency-install-after-content-read-final",
        "no-real-call-after-content-read-final",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_content_read_final_confirmation_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-content-read-final-confirmation.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_content_read_final_confirmation"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["contentReadFinalConfirmationOnly"] is True
    assert contract["requiredContext"]["contentReadFinalConfirmationModelReady"] is False
    assert contract["requiredContext"]["readyForRealDependencyContentReadonlyReadTask"] is False
    assert contract["requiredContext"]["dependencyContentReadAuthorized"] is False
    assert contract["requiredContext"]["dependencyContentReadExecuted"] is False
    assert contract["requiredContext"]["dependencyContentReturned"] is False
    assert "read_dependency_manifest_content" in contract["blockedOperations"]
    assert "write_content_read_final_confirmation_artifact" in contract["blockedOperations"]
    assert "create_content_read_execution_task" in contract["blockedOperations"]
    assert "authorize_content_read_execution" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_content_read_final_confirmation" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_content_read_final_confirmation_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_content_read_final_confirmation(root=ROOT)

    assert descriptor["contentReadFinalConfirmationId"] == "real_sdk_dependency_content_read_final_confirmation"
    assert descriptor["gateMode"] == "DEPENDENCY_CONTENT_READ_FINAL_CONFIRMATION_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresContentReadPlanModelReady"] is True
    assert descriptor["contentReadFinalConfirmationOnly"] is True
    assert "future_dependency_content_read_readonly_execution" in descriptor["pipeline"]
    assert_safe_content_read_final_context(descriptor)


def test_real_sdk_dependency_content_read_final_confirmation_default_is_not_ready_and_redacts_payload(
    monkeypatch,
):
    fake_key = "sk-" + "content-read-final-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_content_read_final_confirmation(
        RealSdkDependencyContentReadFinalConfirmationRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["contentReadFinalChecklist"]}
    assert result["contentReadPlanModelReady"] is False
    assert result["contentReadFinalConfirmationModelReady"] is False
    assert result["readyForRealDependencyContentReadonlyReadTask"] is False
    assert checklist["content_read_plan_model_ready"]["passed"] is False
    assert checklist["content_read_final_scope_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_content_read_final_context(result)


def test_real_sdk_dependency_content_read_final_confirmation_plan_ready_but_missing_final_confirmations():
    request = confirmed_request(
        redaction_policy_final_confirmed=False,
        no_content_artifact_write_final_confirmed=False,
    )
    result = build_real_sdk_dependency_content_read_final_confirmation(request, root=ROOT)
    checklist = {item["id"]: item for item in result["contentReadFinalChecklist"]}

    assert result["contentReadPlanModelReady"] is True
    assert result["contentReadPlanSummary"]["readyForFutureDependencyContentReadExecutionReview"] is True
    assert result["contentReadFinalConfirmationModelReady"] is False
    assert result["readyForRealDependencyContentReadonlyReadTask"] is False
    assert checklist["content_read_plan_model_ready"]["passed"] is True
    assert checklist["redaction_policy_final_confirmed"]["passed"] is False
    assert checklist["no_content_artifact_write_final_confirmed"]["passed"] is False
    assert_safe_content_read_final_context(result)


def test_real_sdk_dependency_content_read_final_confirmation_ready_but_no_read_task_patch_or_execution():
    result = build_real_sdk_dependency_content_read_final_confirmation(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["contentReadFinalChecklist"]}

    assert result["contentReadPlanModelReady"] is True
    assert result["contentReadFinalConfirmationModelReady"] is True
    assert result["readyForRealDependencyContentReadonlyReadTask"] is True
    assert result["dependencyContentReadAuthorized"] is False
    assert result["dependencyContentReadExecuted"] is False
    assert result["dependencyManifestContentRead"] is False
    assert result["dependencyLockfileContentRead"] is False
    assert result["dependencyContentPersisted"] is False
    assert result["dependencyContentReturned"] is False
    assert result["contentReadFinalConfirmationArtifactWritten"] is False
    assert result["contentReadExecutionTaskCreated"] is False
    assert result["contentReadExecutionApprovalGranted"] is False
    assert result["patchGenerated"] is False
    assert result["commandExecuted"] is False
    assert result["dependencyInstallExecuted"] is False
    assert checklist["no_raw_content_return_final_confirmed"]["passed"] is True
    assert result["contentReadFinalConfirmationModel"]["readNow"] is False
    assert result["contentReadFinalConfirmationModel"]["writeNow"] is False
    assert result["contentReadFinalConfirmationModel"]["persistNow"] is False
    assert result["contentReadFinalConfirmationModel"]["finalReadScope"]["contentIncludedNow"] is False
    assert result["contentReadFinalConfirmationModel"]["finalReadScope"]["rawContentReturnedNow"] is False
    assert all(item["allowedNow"] is False for item in result["contentReadFinalConfirmationModel"]["blockedActions"])
    assert result["futureChangeEnvelope"]["contentReadFinalConfirmationArtifactWritten"] is False
    assert result["futureChangeEnvelope"]["contentReadExecutionTaskCreated"] is False
    assert result["futureChangeEnvelope"]["dependencyContentReadAuthorized"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_content_read_final_context(result)


def test_real_sdk_dependency_content_read_final_confirmation_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_content_read_final_confirmation(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_content_read_final_confirmation_error_context(
            exc,
            request=request,
            root=ROOT,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["contentReadFinalConfirmationModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_content_read_final_context(context)


def test_real_sdk_dependency_content_read_final_confirmation_cli_describe_and_confirm_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-content-read-final-confirmation", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadFinalConfirmationId"] == "real_sdk_dependency_content_read_final_confirmation"
    assert payload["data"]["contentReadFinalConfirmationModelReady"] is False
    assert_safe_content_read_final_context(payload["data"])

    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-content-read-final-confirmation",
            "confirm-read",
            "--provider",
            "openai",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadPlanModelReady"] is False
    assert payload["data"]["contentReadFinalConfirmationModelReady"] is False
    assert_safe_content_read_final_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadPlanModelReady"] is True
    assert payload["data"]["contentReadFinalConfirmationModelReady"] is True
    assert payload["data"]["readyForRealDependencyContentReadonlyReadTask"] is True
    assert payload["data"]["dependencyContentReadAuthorized"] is False
    assert payload["data"]["dependencyContentReturned"] is False
    assert payload["data"]["contentReadFinalConfirmationArtifactWritten"] is False
    assert payload["data"]["contentReadExecutionTaskCreated"] is False
    assert payload["data"]["patchGenerated"] is False
    assert_safe_content_read_final_context(payload["data"])


def test_real_sdk_dependency_content_read_final_confirmation_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-content-read-final-confirmation",
            "confirm-read",
            "--provider",
            "openai",
            "--payload",
            "not-json",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-content-read-final-confirmation",
            "confirm-read",
            "--provider",
            "openai",
            "--output-kind",
            "Exam",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkDependencyContentReadFinalConfirmationContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_content_read_final_context(context)
