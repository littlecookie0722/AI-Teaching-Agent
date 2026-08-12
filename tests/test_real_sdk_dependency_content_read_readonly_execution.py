import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyContentReadReadonlyExecutionRequest,
    build_real_sdk_dependency_content_read_readonly_execution,
    build_real_sdk_dependency_content_read_readonly_execution_error_context,
    describe_real_sdk_dependency_content_read_readonly_execution,
)
from tests.test_real_sdk_dependency_content_read_final_confirmation import (
    assert_safe_content_read_final_context,
    confirmed_cli_args as confirmed_final_cli_args,
    confirmed_request as confirmed_final_request,
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


def assert_safe_content_read_execution_context(context, *, read_allowed=False):
    if not read_allowed:
        assert_safe_content_read_final_context(context)
    else:
        for key in [
            "contentReadFinalConfirmationRecordPersisted",
            "contentReadFinalConfirmationArtifactWritten",
            "contentReadFinalConfirmationExecuted",
            "contentReadExecutionApprovalGranted",
            "contentReadExecutionTaskCreated",
            "contentReadPlanRecordPersisted",
            "contentReadPlanArtifactWritten",
            "contentReadPlanExecuted",
            "contentReadApprovalRecordPersisted",
            "contentReadApprovalArtifactWritten",
        ]:
            assert context[key] is False
    assert context["dependencyContentReturned"] is False
    assert context["rawDependencyContentReturned"] is False
    assert context["dependencyContentPersisted"] is False
    assert context["contentReadReadonlyExecutionRecordPersisted"] is False
    assert context["contentReadReadonlyExecutionArtifactWritten"] is False
    assert context["commandExecuted"] is False
    assert context["dependencyFileChanged"] is False
    assert context["patchGenerated"] is False
    assert context["dependencyInstallExecuted"] is False
    assert context["sdkDependencyInstalled"] is False
    assert context["sdkImported"] is False
    assert context["clientCreated"] is False
    assert context["secretPresenceChecked"] is False
    assert context["secretValueRead"] is False
    assert context["networkAccess"] is False
    assert context["realLlmCalled"] is False
    if not read_allowed:
        assert context["dependencyContentReadAuthorized"] is False
        assert context["dependencyContentReadExecuted"] is False
        assert context["dependencyFileRead"] is False
        assert context["liveDependencyFileRead"] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_final_request())
    payload.update(
        {
            "approval_ref": "CONTENT-READ-EXEC-001",
            "content_read_execution_scope_confirmed": True,
            "content_read_execution_approver_confirmed": True,
            "content_read_execution_ticket_confirmed": True,
            "readonly_dependency_content_read_confirmed": True,
            "manifest_content_read_confirmed": True,
            "lockfile_content_read_confirmed": True,
            "redaction_before_return_confirmed": True,
            "no_raw_content_return_execution_confirmed": True,
            "no_content_persistence_execution_confirmed": True,
            "no_content_artifact_write_execution_confirmed": True,
            "no_patch_generation_after_content_read_execution_confirmed": True,
            "no_command_execution_after_content_read_execution_confirmed": True,
            "no_dependency_install_after_content_read_execution_confirmed": True,
            "no_secret_presence_check_after_content_read_execution_confirmed": True,
            "no_network_after_content_read_execution_confirmed": True,
            "no_real_call_after_content_read_execution_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyContentReadReadonlyExecutionRequest(**payload)


def confirmed_cli_args():
    args = confirmed_final_cli_args()
    args[1] = "real-sdk-dependency-content-read-readonly-execution"
    args[2] = "read"
    args[args.index("--approval-ref") + 1] = "CONTENT-READ-EXEC-001"
    flags = [
        "content-read-execution-scope",
        "content-read-execution-approver",
        "content-read-execution-ticket",
        "readonly-dependency-content-read",
        "manifest-content-read",
        "lockfile-content-read",
        "redaction-before-return",
        "no-raw-content-return-execution",
        "no-content-persistence-execution",
        "no-content-artifact-write-execution",
        "no-patch-generation-after-content-read-execution",
        "no-command-execution-after-content-read-execution",
        "no-dependency-install-after-content-read-execution",
        "no-secret-presence-check-after-content-read-execution",
        "no-network-after-content-read-execution",
        "no-real-call-after-content-read-execution",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def make_dependency_root(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "openai==1.0.0\napi_key=sk-secret-value-123456\npytest>=8\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text(
        "[[package]]\nname = \"openai\"\ntoken = abcdefghijklmnop\n",
        encoding="utf-8",
    )
    return tmp_path


def test_real_sdk_dependency_content_read_readonly_execution_contract_is_local_and_redacted_only():
    contract = load_json("providers/real-sdk-dependency-content-read-readonly-execution.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_content_read_readonly_execution"
    assert contract["activeProvider"] == "mock"
    assert contract["safety"]["readonlyReadAllowedAfterConfirmation"] is True
    assert contract["safety"]["redactedPreviewOnly"] is True
    assert contract["requiredContext"]["dependencyContentReadExecuted"] is False
    assert contract["requiredContext"]["rawDependencyContentReturned"] is False
    assert contract["requiredContext"]["dependencyContentPersisted"] is False
    assert "return_raw_dependency_content" in contract["blockedOperations"]
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_content_read_readonly_execution" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_content_read_readonly_execution_describe_is_safe():
    descriptor = describe_real_sdk_dependency_content_read_readonly_execution(root=ROOT)

    assert descriptor["contentReadReadonlyExecutionId"] == "real_sdk_dependency_content_read_readonly_execution"
    assert descriptor["gateMode"] == "DEPENDENCY_CONTENT_READ_READONLY_EXECUTION_REDACTED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["contentReadReadonlyExecutionOnly"] is True
    assert descriptor["contentReadReadonlyExecutionModelReady"] is False
    assert descriptor["allowlistedManifestCandidates"] == ["pyproject.toml", "requirements.txt"]
    assert_safe_content_read_execution_context(descriptor)


def test_real_sdk_dependency_content_read_readonly_execution_default_does_not_read(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_content_read_readonly_execution(
        RealSdkDependencyContentReadReadonlyExecutionRequest(provider_id="openai"),
        root=root,
    )

    assert result["contentReadFinalConfirmationModelReady"] is False
    assert result["contentReadReadonlyExecutionModelReady"] is False
    assert result["dependencyContentReadExecuted"] is False
    assert result["redactedDependencyContentPreviewReturned"] is False
    assert result["contentReadReadonlyExecutionModel"]["summary"]["filesRead"] == 0
    assert_safe_content_read_execution_context(result)


def test_real_sdk_dependency_content_read_readonly_execution_reads_redacted_preview_only(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_content_read_readonly_execution(confirmed_request(), root=root)
    serialized = json.dumps(result, ensure_ascii=False)
    files = result["contentReadReadonlyExecutionModel"]["files"]

    assert result["contentReadFinalConfirmationModelReady"] is True
    assert result["contentReadReadonlyExecutionModelReady"] is True
    assert result["dependencyContentReadAuthorized"] is True
    assert result["dependencyContentReadExecuted"] is True
    assert result["dependencyManifestContentRead"] is True
    assert result["dependencyLockfileContentRead"] is True
    assert result["redactedDependencyContentPreviewReturned"] is True
    assert result["dependencyContentReturned"] is False
    assert result["rawDependencyContentReturned"] is False
    assert result["dependencyContentPersisted"] is False
    assert len(files) == 2
    assert {item["relativePath"] for item in files} == {"requirements.txt", "uv.lock"}
    assert "sk-secret-value-123456" not in serialized
    assert "abcdefghijklmnop" not in serialized
    assert "[REDACTED]" in serialized
    assert any("openai" in item["packageMentions"] for item in files)
    assert all(item["rawContentReturned"] is False for item in files)
    assert all(item["contentPersisted"] is False for item in files)
    assert all(item["allowedNow"] is False for item in result["contentReadReadonlyExecutionModel"]["blockedActions"])
    assert result["futureChangeEnvelope"]["dependencyInstallExecuted"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_content_read_execution_context(result, read_allowed=True)


def test_real_sdk_dependency_content_read_readonly_execution_invalid_scope_keeps_safe_error_context(tmp_path):
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_content_read_readonly_execution(request, root=tmp_path)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_content_read_readonly_execution_error_context(
            exc,
            request=request,
            root=tmp_path,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["contentReadReadonlyExecutionModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_content_read_execution_context(context)


def test_real_sdk_dependency_content_read_readonly_execution_cli_describe_and_read_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-content-read-readonly-execution", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadReadonlyExecutionId"] == "real_sdk_dependency_content_read_readonly_execution"
    assert_safe_content_read_execution_context(payload["data"])

    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-content-read-readonly-execution",
            "read",
            "--provider",
            "openai",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadReadonlyExecutionModelReady"] is False
    assert payload["data"]["dependencyContentReadExecuted"] is False
    assert_safe_content_read_execution_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadReadonlyExecutionModelReady"] is True
    assert payload["data"]["dependencyContentReadAuthorized"] is True
    assert payload["data"]["dependencyContentReadExecuted"] is True
    assert payload["data"]["dependencyContentReturned"] is False
    assert payload["data"]["rawDependencyContentReturned"] is False
    assert payload["data"]["dependencyContentPersisted"] is False
    assert payload["data"]["commandExecuted"] is False
    assert payload["data"]["dependencyInstallExecuted"] is False
    assert payload["data"]["secretPresenceChecked"] is False
    assert payload["data"]["networkAccess"] is False
    assert payload["data"]["realLlmCalled"] is False
    assert_safe_content_read_execution_context(payload["data"], read_allowed=True)


def test_real_sdk_dependency_content_read_readonly_execution_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-content-read-readonly-execution",
            "read",
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
            "real-sdk-dependency-content-read-readonly-execution",
            "read",
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
    context = payload["realSdkDependencyContentReadReadonlyExecutionContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_content_read_execution_context(context)
