import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyInstallAuthorizationPackageRequest,
    build_real_sdk_dependency_install_authorization_package,
    build_real_sdk_dependency_install_authorization_package_error_context,
    describe_real_sdk_dependency_install_authorization_package,
)
from tests.test_real_sdk_dependency_content_read_readonly_execution import make_dependency_root
from tests.test_real_sdk_dependency_executor_disabled import assert_json_envelope
from tests.test_real_sdk_dependency_install_execution_gate import (
    assert_safe_install_execution_gate_context,
    confirmed_cli_args as confirmed_gate_cli_args,
    confirmed_request as confirmed_gate_request,
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


def assert_safe_install_authorization_package_context(context, *, gate_allowed=False):
    assert_safe_install_execution_gate_context(context, proposal_allowed=gate_allowed)
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
    if not gate_allowed:
        assert context["installAuthorizationPackageModelReady"] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_gate_request())
    payload.update(
        {
            "approval_ref": "INSTALL-AUTH-PACKAGE-001",
            "dependency_install_authorization_scope_confirmed": True,
            "final_install_approver_confirmed": True,
            "install_authorization_ticket_confirmed": True,
            "dependency_install_change_window_confirmed": True,
            "install_execution_gate_review_confirmed": True,
            "dependency_manifest_write_policy_confirmed": True,
            "dependency_lockfile_write_policy_confirmed": True,
            "package_manager_command_policy_confirmed": True,
            "rollback_checkpoint_confirmed": True,
            "post_install_validation_plan_confirmed": True,
            "no_execution_authorization_during_authorization_package_confirmed": True,
            "no_dependency_file_write_during_authorization_package_confirmed": True,
            "no_patch_file_write_during_authorization_package_confirmed": True,
            "no_patch_apply_during_authorization_package_confirmed": True,
            "no_command_materialization_during_authorization_package_confirmed": True,
            "no_command_execution_during_authorization_package_confirmed": True,
            "no_dependency_install_during_authorization_package_confirmed": True,
            "no_package_resolution_during_authorization_package_confirmed": True,
            "no_secret_presence_check_during_authorization_package_confirmed": True,
            "no_network_during_authorization_package_confirmed": True,
            "no_real_call_during_authorization_package_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyInstallAuthorizationPackageRequest(**payload)


def confirmed_cli_args():
    args = confirmed_gate_cli_args()
    args[1] = "real-sdk-dependency-install-authorization-package"
    args[2] = "evaluate"
    args[args.index("--approval-ref") + 1] = "INSTALL-AUTH-PACKAGE-001"
    flags = [
        "dependency-install-authorization-scope",
        "final-install-approver",
        "install-authorization-ticket",
        "dependency-install-change-window",
        "install-execution-gate-review",
        "dependency-manifest-write-policy",
        "dependency-lockfile-write-policy",
        "package-manager-command-policy",
        "rollback-checkpoint",
        "post-install-validation-plan",
        "no-execution-authorization-during-authorization-package",
        "no-dependency-file-write-during-authorization-package",
        "no-patch-file-write-during-authorization-package",
        "no-patch-apply-during-authorization-package",
        "no-command-materialization-during-authorization-package",
        "no-command-execution-during-authorization-package",
        "no-dependency-install-during-authorization-package",
        "no-package-resolution-during-authorization-package",
        "no-secret-presence-check-during-authorization-package",
        "no-network-during-authorization-package",
        "no-real-call-during-authorization-package",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_install_authorization_package_contract_is_disabled_and_local():
    contract = load_json("providers/real-sdk-dependency-install-authorization-package.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_install_authorization_package"
    assert contract["activeProvider"] == "mock"
    assert contract["safety"]["installAuthorizationPackageOnly"] is True
    assert contract["safety"]["executionAuthorizationGranted"] is False
    assert contract["requiredContext"]["executionAuthorized"] is False
    assert contract["requiredContext"]["dependencyFileWriteAuthorized"] is False
    assert contract["requiredContext"]["commandExecuted"] is False
    assert contract["requiredContext"]["dependencyInstallExecuted"] is False
    assert "grant_dependency_install_execution_authorization" in contract["blockedOperations"]
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_install_authorization_package" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_install_authorization_package_describe_is_safe():
    descriptor = describe_real_sdk_dependency_install_authorization_package(root=ROOT)

    assert descriptor["installAuthorizationPackageId"] == "real_sdk_dependency_install_authorization_package"
    assert descriptor["gateMode"] == "DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_DISABLED"
    assert descriptor["authorizationPackageMode"] == "LOCAL_DEPENDENCY_INSTALL_AUTHORIZATION_PACKAGE_MODEL_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["installAuthorizationPackageOnly"] is True
    assert descriptor["installAuthorizationPackageModelReady"] is False
    assert "future_explicit_dependency_install_execution" in descriptor["pipeline"]
    assert_safe_install_authorization_package_context(descriptor)


def test_real_sdk_dependency_install_authorization_package_default_does_not_prepare_execution(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_authorization_package(
        RealSdkDependencyInstallAuthorizationPackageRequest(provider_id="openai"),
        root=root,
    )

    assert result["installExecutionGateModelReady"] is False
    assert result["installAuthorizationPackageModelReady"] is False
    assert result["readyForExplicitDependencyInstallExecutionRequest"] is False
    assert result["installAuthorizationPackageModel"] is None
    assert_safe_install_authorization_package_context(result)


def test_real_sdk_dependency_install_authorization_package_ready_still_does_not_install(tmp_path):
    root = make_dependency_root(tmp_path)
    requirements = root / "requirements.txt"
    before = requirements.read_text(encoding="utf-8")
    result = build_real_sdk_dependency_install_authorization_package(confirmed_request(), root=root)
    after = requirements.read_text(encoding="utf-8")
    model = result["installAuthorizationPackageModel"]

    assert result["installExecutionGateModelReady"] is True
    assert result["installAuthorizationChecklistPassed"] is True
    assert result["installAuthorizationPackageModelReady"] is True
    assert result["readyForExplicitDependencyInstallExecutionRequest"] is True
    assert model["authorizationPackageOnly"] is True
    assert model["authorizationGrantedNow"] is False
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
    assert_safe_install_authorization_package_context(result, gate_allowed=True)


def test_real_sdk_dependency_install_authorization_package_missing_confirmations(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_authorization_package(
        confirmed_request(dependency_install_authorization_scope_confirmed=False),
        root=root,
    )
    checklist = {item["id"]: item for item in result["installAuthorizationChecklist"]}

    assert result["installExecutionGateModelReady"] is True
    assert result["installAuthorizationPackageModelReady"] is False
    assert result["installAuthorizationPackageModel"] is None
    assert checklist["install_execution_gate_model_ready"]["passed"] is True
    assert checklist["dependency_install_authorization_scope_confirmed"]["passed"] is False
    assert_safe_install_authorization_package_context(result, gate_allowed=True)


def test_real_sdk_dependency_install_authorization_package_invalid_scope_keeps_safe_error_context(tmp_path):
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_install_authorization_package(request, root=tmp_path)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_install_authorization_package_error_context(
            exc,
            request=request,
            root=tmp_path,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["installAuthorizationPackageModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_install_authorization_package_context(context)


def test_real_sdk_dependency_install_authorization_package_cli_describe_and_evaluate_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-authorization-package", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installAuthorizationPackageId"] == "real_sdk_dependency_install_authorization_package"
    assert payload["data"]["installAuthorizationPackageModelReady"] is False
    assert_safe_install_authorization_package_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-authorization-package", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installExecutionGateModelReady"] is False
    assert payload["data"]["installAuthorizationPackageModelReady"] is False
    assert_safe_install_authorization_package_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installExecutionGateModelReady"] is True
    assert payload["data"]["installAuthorizationPackageModelReady"] is True
    assert payload["data"]["executionAuthorized"] is False
    assert payload["data"]["commandExecuted"] is False
    assert payload["data"]["dependencyInstallExecuted"] is False
    assert_safe_install_authorization_package_context(payload["data"], gate_allowed=True)


def test_real_sdk_dependency_install_authorization_package_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-install-authorization-package",
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
            "real-sdk-dependency-install-authorization-package",
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
    context = payload["realSdkDependencyInstallAuthorizationPackageContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_install_authorization_package_context(context)
