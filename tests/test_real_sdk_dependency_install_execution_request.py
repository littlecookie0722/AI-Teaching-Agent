import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyInstallExecutionRequestRequest,
    build_real_sdk_dependency_install_execution_request,
    build_real_sdk_dependency_install_execution_request_error_context,
    describe_real_sdk_dependency_install_execution_request,
)
from tests.test_real_sdk_dependency_content_read_readonly_execution import make_dependency_root
from tests.test_real_sdk_dependency_executor_disabled import assert_json_envelope
from tests.test_real_sdk_dependency_install_authorization_package import (
    assert_safe_install_authorization_package_context,
    confirmed_cli_args as confirmed_authorization_cli_args,
    confirmed_request as confirmed_authorization_request,
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


def assert_safe_install_execution_request_context(context, *, authorization_allowed=False):
    assert_safe_install_authorization_package_context(context, gate_allowed=authorization_allowed)
    for key in [
        "dependencyInstallExecutionAuthorized",
        "executionAuthorized",
        "dependencyFileWriteAuthorized",
        "dependencyFileChanged",
        "requirementsChanged",
        "pyprojectChanged",
        "lockfileChanged",
        "dependencyLockfileChanged",
        "dependencyPatchGenerated",
        "patchGenerated",
        "patchMaterialized",
        "patchFileWritten",
        "patchApplied",
        "commandMaterialized",
        "installCommandMaterialized",
        "commandExecuted",
        "dependencyInstallExecuted",
        "sdkDependencyInstalled",
        "packageVersionResolved",
        "packageHashResolved",
        "packageDownloaded",
        "sdkImported",
        "clientCreated",
        "secretPresenceChecked",
        "secretValueRead",
        "networkAccess",
        "realLlmCalled",
        "autoPublishAllowed",
        "realPublish",
    ]:
        assert context[key] is False
    if not authorization_allowed:
        assert context["installExecutionRequestModelReady"] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_authorization_request())
    payload.update(
        {
            "approval_ref": "INSTALL-EXEC-REQUEST-001",
            "dependency_install_execution_request_scope_confirmed": True,
            "execution_request_approver_confirmed": True,
            "execution_request_ticket_confirmed": True,
            "execution_request_change_window_confirmed": True,
            "install_authorization_package_review_confirmed": True,
            "dependency_manifest_write_target_confirmed": True,
            "dependency_lockfile_write_target_confirmed": True,
            "package_manager_execution_policy_confirmed": True,
            "execution_request_rollback_checkpoint_confirmed": True,
            "execution_request_post_install_validation_confirmed": True,
            "no_execution_authorization_during_execution_request_confirmed": True,
            "no_dependency_file_write_during_execution_request_confirmed": True,
            "no_patch_file_write_during_execution_request_confirmed": True,
            "no_patch_apply_during_execution_request_confirmed": True,
            "no_command_materialization_during_execution_request_confirmed": True,
            "no_command_execution_during_execution_request_confirmed": True,
            "no_dependency_install_during_execution_request_confirmed": True,
            "no_package_resolution_during_execution_request_confirmed": True,
            "no_secret_presence_check_during_execution_request_confirmed": True,
            "no_network_during_execution_request_confirmed": True,
            "no_real_call_during_execution_request_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyInstallExecutionRequestRequest(**payload)


def confirmed_cli_args():
    args = confirmed_authorization_cli_args()
    args[1] = "real-sdk-dependency-install-execution-request"
    args[2] = "evaluate"
    args[args.index("--approval-ref") + 1] = "INSTALL-EXEC-REQUEST-001"
    flags = [
        "dependency-install-execution-request-scope",
        "execution-request-approver",
        "execution-request-ticket",
        "execution-request-change-window",
        "install-authorization-package-review",
        "dependency-manifest-write-target",
        "dependency-lockfile-write-target",
        "package-manager-execution-policy",
        "execution-request-rollback-checkpoint",
        "execution-request-post-install-validation",
        "no-execution-authorization-during-execution-request",
        "no-dependency-file-write-during-execution-request",
        "no-patch-file-write-during-execution-request",
        "no-patch-apply-during-execution-request",
        "no-command-materialization-during-execution-request",
        "no-command-execution-during-execution-request",
        "no-dependency-install-during-execution-request",
        "no-package-resolution-during-execution-request",
        "no-secret-presence-check-during-execution-request",
        "no-network-during-execution-request",
        "no-real-call-during-execution-request",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_install_execution_request_contract_is_disabled_and_local():
    contract = load_json("providers/real-sdk-dependency-install-execution-request.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_install_execution_request"
    assert contract["activeProvider"] == "mock"
    assert contract["safety"]["installExecutionRequestOnly"] is True
    assert contract["safety"]["executionAuthorizationGranted"] is False
    assert contract["requiredContext"]["executionAuthorized"] is False
    assert contract["requiredContext"]["dependencyFileWriteAuthorized"] is False
    assert contract["requiredContext"]["commandExecuted"] is False
    assert contract["requiredContext"]["dependencyInstallExecuted"] is False
    assert "dispatch_dependency_install_executor" in contract["blockedOperations"]
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_install_execution_request" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_install_execution_request_describe_is_safe():
    descriptor = describe_real_sdk_dependency_install_execution_request(root=ROOT)

    assert descriptor["installExecutionRequestId"] == "real_sdk_dependency_install_execution_request"
    assert descriptor["gateMode"] == "DEPENDENCY_INSTALL_EXECUTION_REQUEST_DISABLED"
    assert descriptor["executionRequestMode"] == "LOCAL_DEPENDENCY_INSTALL_EXECUTION_REQUEST_MODEL_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["installExecutionRequestOnly"] is True
    assert descriptor["installExecutionRequestModelReady"] is False
    assert "future_explicit_dependency_install_executor" in descriptor["pipeline"]
    assert_safe_install_execution_request_context(descriptor)


def test_real_sdk_dependency_install_execution_request_default_does_not_prepare_executor(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_execution_request(
        RealSdkDependencyInstallExecutionRequestRequest(provider_id="openai"),
        root=root,
    )

    assert result["installAuthorizationPackageModelReady"] is False
    assert result["installExecutionRequestModelReady"] is False
    assert result["readyForExplicitDependencyInstallExecutorImplementation"] is False
    assert result["installExecutionRequestModel"] is None
    assert_safe_install_execution_request_context(result)


def test_real_sdk_dependency_install_execution_request_ready_still_does_not_install(tmp_path):
    root = make_dependency_root(tmp_path)
    requirements = root / "requirements.txt"
    before = requirements.read_text(encoding="utf-8")
    result = build_real_sdk_dependency_install_execution_request(confirmed_request(), root=root)
    after = requirements.read_text(encoding="utf-8")
    model = result["installExecutionRequestModel"]

    assert result["installAuthorizationPackageModelReady"] is True
    assert result["installExecutionRequestChecklistPassed"] is True
    assert result["installExecutionRequestModelReady"] is True
    assert result["readyForExplicitDependencyInstallExecutorImplementation"] is True
    assert model["executionRequestOnly"] is True
    assert model["authorizationGrantedNow"] is False
    assert model["executionDispatchNow"] is False
    assert model["executionAuthorizationNow"] is False
    assert model["dependencyFileWriteNow"] is False
    assert model["patchFileWriteNow"] is False
    assert model["patchApplyNow"] is False
    assert model["commandMaterializeNow"] is False
    assert model["commandExecuteNow"] is False
    assert model["installNow"] is False
    assert model["packageResolveNow"] is False
    assert model["secretCheckNow"] is False
    assert model["networkNow"] is False
    assert before == after
    assert all(item["allowedNow"] is False for item in model["blockedActions"])
    assert_safe_install_execution_request_context(result, authorization_allowed=True)


def test_real_sdk_dependency_install_execution_request_missing_confirmations(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_execution_request(
        confirmed_request(dependency_install_execution_request_scope_confirmed=False),
        root=root,
    )
    checklist = {item["id"]: item for item in result["installExecutionRequestChecklist"]}

    assert result["installAuthorizationPackageModelReady"] is True
    assert result["installExecutionRequestModelReady"] is False
    assert result["installExecutionRequestModel"] is None
    assert checklist["install_authorization_package_model_ready"]["passed"] is True
    assert checklist["dependency_install_execution_request_scope_confirmed"]["passed"] is False
    assert_safe_install_execution_request_context(result, authorization_allowed=True)


def test_real_sdk_dependency_install_execution_request_invalid_scope_keeps_safe_error_context(tmp_path):
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_install_execution_request(request, root=tmp_path)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_install_execution_request_error_context(
            exc,
            request=request,
            root=tmp_path,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["installExecutionRequestModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_install_execution_request_context(context)


def test_real_sdk_dependency_install_execution_request_cli_describe_and_evaluate_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-execution-request", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installExecutionRequestId"] == "real_sdk_dependency_install_execution_request"
    assert payload["data"]["installExecutionRequestModelReady"] is False
    assert_safe_install_execution_request_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-execution-request", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installAuthorizationPackageModelReady"] is False
    assert payload["data"]["installExecutionRequestModelReady"] is False
    assert_safe_install_execution_request_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installAuthorizationPackageModelReady"] is True
    assert payload["data"]["installExecutionRequestModelReady"] is True
    assert payload["data"]["executionAuthorized"] is False
    assert payload["data"]["commandExecuted"] is False
    assert payload["data"]["dependencyInstallExecuted"] is False
    assert_safe_install_execution_request_context(payload["data"], authorization_allowed=True)


def test_real_sdk_dependency_install_execution_request_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-install-execution-request",
            "evaluate",
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
            "real-sdk-dependency-install-execution-request",
            "evaluate",
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
    context = payload["realSdkDependencyInstallExecutionRequestContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_install_execution_request_context(context)
