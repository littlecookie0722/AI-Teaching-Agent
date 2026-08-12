import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyInstallExecutorDisabledRequest,
    build_real_sdk_dependency_install_executor_disabled,
    build_real_sdk_dependency_install_executor_disabled_error_context,
    describe_real_sdk_dependency_install_executor_disabled,
)
from tests.test_real_sdk_dependency_content_read_readonly_execution import make_dependency_root
from tests.test_real_sdk_dependency_executor_disabled import assert_json_envelope
from tests.test_real_sdk_dependency_install_execution_request import (
    assert_safe_install_execution_request_context,
    confirmed_cli_args as confirmed_execution_request_cli_args,
    confirmed_request as confirmed_execution_request,
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


def assert_safe_install_executor_disabled_context(context, *, request_allowed=False):
    assert_safe_install_execution_request_context(
        context,
        authorization_allowed=request_allowed,
    )
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
        "executorDispatched",
        "executorStarted",
        "executorRunCreated",
        "commandTemplateMaterialized",
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
    assert context["executorDryRunOnly"] is True
    if not request_allowed:
        assert context["installExecutorDisabledModelReady"] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_execution_request())
    payload.update(
        {
            "approval_ref": "INSTALL-EXECUTOR-DISABLED-001",
            "dependency_install_executor_disabled_scope_confirmed": True,
            "executor_disabled_owner_confirmed": True,
            "executor_disabled_runtime_guard_confirmed": True,
            "executor_disabled_dry_run_mode_confirmed": True,
            "install_execution_request_review_confirmed": True,
            "executor_no_dispatch_policy_confirmed": True,
            "executor_no_command_template_materialization_confirmed": True,
            "executor_no_dependency_file_write_policy_confirmed": True,
            "executor_no_package_resolution_policy_confirmed": True,
            "executor_no_secret_presence_check_policy_confirmed": True,
            "executor_no_network_policy_confirmed": True,
            "executor_rollback_checkpoint_confirmed": True,
            "executor_post_install_validation_plan_confirmed": True,
            "no_execution_authorization_during_executor_disabled_confirmed": True,
            "no_executor_dispatch_during_executor_disabled_confirmed": True,
            "no_executor_start_during_executor_disabled_confirmed": True,
            "no_executor_run_creation_during_executor_disabled_confirmed": True,
            "no_dependency_file_write_during_executor_disabled_confirmed": True,
            "no_patch_file_write_during_executor_disabled_confirmed": True,
            "no_patch_apply_during_executor_disabled_confirmed": True,
            "no_command_materialization_during_executor_disabled_confirmed": True,
            "no_command_execution_during_executor_disabled_confirmed": True,
            "no_dependency_install_during_executor_disabled_confirmed": True,
            "no_package_resolution_during_executor_disabled_confirmed": True,
            "no_secret_presence_check_during_executor_disabled_confirmed": True,
            "no_network_during_executor_disabled_confirmed": True,
            "no_real_call_during_executor_disabled_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyInstallExecutorDisabledRequest(**payload)


def confirmed_cli_args():
    args = confirmed_execution_request_cli_args()
    args[1] = "real-sdk-dependency-install-executor-disabled"
    args[2] = "evaluate"
    args[args.index("--approval-ref") + 1] = "INSTALL-EXECUTOR-DISABLED-001"
    flags = [
        "dependency-install-executor-disabled-scope",
        "executor-disabled-owner",
        "executor-disabled-runtime-guard",
        "executor-disabled-dry-run-mode",
        "install-execution-request-review",
        "executor-no-dispatch-policy",
        "executor-no-command-template-materialization",
        "executor-no-dependency-file-write-policy",
        "executor-no-package-resolution-policy",
        "executor-no-secret-presence-check-policy",
        "executor-no-network-policy",
        "executor-rollback-checkpoint",
        "executor-post-install-validation-plan",
        "no-execution-authorization-during-executor-disabled",
        "no-executor-dispatch-during-executor-disabled",
        "no-executor-start-during-executor-disabled",
        "no-executor-run-creation-during-executor-disabled",
        "no-dependency-file-write-during-executor-disabled",
        "no-patch-file-write-during-executor-disabled",
        "no-patch-apply-during-executor-disabled",
        "no-command-materialization-during-executor-disabled",
        "no-command-execution-during-executor-disabled",
        "no-dependency-install-during-executor-disabled",
        "no-package-resolution-during-executor-disabled",
        "no-secret-presence-check-during-executor-disabled",
        "no-network-during-executor-disabled",
        "no-real-call-during-executor-disabled",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_install_executor_disabled_contract_is_disabled_and_local():
    contract = load_json("providers/real-sdk-dependency-install-executor-disabled.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_install_executor_disabled"
    assert contract["activeProvider"] == "mock"
    assert contract["safety"]["installExecutorDisabledOnly"] is True
    assert contract["safety"]["executorDispatched"] is False
    assert contract["safety"]["executorStarted"] is False
    assert contract["safety"]["executorRunCreated"] is False
    assert contract["requiredContext"]["executionAuthorized"] is False
    assert contract["requiredContext"]["dependencyFileWriteAuthorized"] is False
    assert contract["requiredContext"]["commandExecuted"] is False
    assert contract["requiredContext"]["dependencyInstallExecuted"] is False
    assert "start_dependency_install_executor" in contract["blockedOperations"]
    assert "create_executor_run" in contract["blockedOperations"]
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_install_executor_disabled" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_install_executor_disabled_describe_is_safe():
    descriptor = describe_real_sdk_dependency_install_executor_disabled(root=ROOT)

    assert descriptor["installExecutorDisabledId"] == "real_sdk_dependency_install_executor_disabled"
    assert descriptor["gateMode"] == "DEPENDENCY_INSTALL_EXECUTOR_DISABLED"
    assert descriptor["executorDisabledMode"] == "LOCAL_DEPENDENCY_INSTALL_EXECUTOR_DISABLED_MODEL_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["installExecutorDisabledOnly"] is True
    assert descriptor["installExecutorDisabledModelReady"] is False
    assert "future_explicit_dependency_install_dry_run_command_review" in descriptor["pipeline"]
    assert_safe_install_executor_disabled_context(descriptor)


def test_real_sdk_dependency_install_executor_disabled_default_does_not_dispatch(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_executor_disabled(
        RealSdkDependencyInstallExecutorDisabledRequest(provider_id="openai"),
        root=root,
    )

    assert result["installExecutionRequestModelReady"] is False
    assert result["installExecutorDisabledModelReady"] is False
    assert result["readyForFutureDependencyInstallDryRunCommandReview"] is False
    assert result["installExecutorDisabledModel"] is None
    assert_safe_install_executor_disabled_context(result)


def test_real_sdk_dependency_install_executor_disabled_ready_still_does_not_install(tmp_path):
    root = make_dependency_root(tmp_path)
    requirements = root / "requirements.txt"
    before = requirements.read_text(encoding="utf-8")
    result = build_real_sdk_dependency_install_executor_disabled(confirmed_request(), root=root)
    after = requirements.read_text(encoding="utf-8")
    model = result["installExecutorDisabledModel"]

    assert result["installExecutionRequestModelReady"] is True
    assert result["installExecutorDisabledChecklistPassed"] is True
    assert result["installExecutorDisabledModelReady"] is True
    assert result["readyForFutureDependencyInstallDryRunCommandReview"] is True
    assert model["executorDisabledOnly"] is True
    assert model["executionAuthorizationNow"] is False
    assert model["executorDispatchNow"] is False
    assert model["executorStartNow"] is False
    assert model["executorRunCreateNow"] is False
    assert model["dependencyFileWriteNow"] is False
    assert model["patchFileWriteNow"] is False
    assert model["patchApplyNow"] is False
    assert model["commandTemplateMaterializeNow"] is False
    assert model["commandMaterializeNow"] is False
    assert model["commandExecuteNow"] is False
    assert model["installNow"] is False
    assert model["packageResolveNow"] is False
    assert model["secretCheckNow"] is False
    assert model["networkNow"] is False
    assert before == after
    assert all(item["allowedNow"] is False for item in model["blockedActions"])
    assert_safe_install_executor_disabled_context(result, request_allowed=True)


def test_real_sdk_dependency_install_executor_disabled_missing_confirmations(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_executor_disabled(
        confirmed_request(dependency_install_executor_disabled_scope_confirmed=False),
        root=root,
    )
    checklist = {item["id"]: item for item in result["installExecutorDisabledChecklist"]}

    assert result["installExecutionRequestModelReady"] is True
    assert result["installExecutorDisabledModelReady"] is False
    assert result["installExecutorDisabledModel"] is None
    assert checklist["install_execution_request_model_ready"]["passed"] is True
    assert checklist["dependency_install_executor_disabled_scope_confirmed"]["passed"] is False
    assert_safe_install_executor_disabled_context(result, request_allowed=True)


def test_real_sdk_dependency_install_executor_disabled_invalid_scope_keeps_safe_error_context(tmp_path):
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_install_executor_disabled(request, root=tmp_path)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_install_executor_disabled_error_context(
            exc,
            request=request,
            root=tmp_path,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["installExecutorDisabledModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_install_executor_disabled_context(context)


def test_real_sdk_dependency_install_executor_disabled_cli_describe_and_evaluate_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-executor-disabled", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installExecutorDisabledId"] == "real_sdk_dependency_install_executor_disabled"
    assert payload["data"]["installExecutorDisabledModelReady"] is False
    assert_safe_install_executor_disabled_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-executor-disabled", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installExecutionRequestModelReady"] is False
    assert payload["data"]["installExecutorDisabledModelReady"] is False
    assert_safe_install_executor_disabled_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installExecutionRequestModelReady"] is True
    assert payload["data"]["installExecutorDisabledModelReady"] is True
    assert payload["data"]["executorDispatched"] is False
    assert payload["data"]["executorStarted"] is False
    assert payload["data"]["executorRunCreated"] is False
    assert payload["data"]["commandExecuted"] is False
    assert payload["data"]["dependencyInstallExecuted"] is False
    assert_safe_install_executor_disabled_context(payload["data"], request_allowed=True)


def test_real_sdk_dependency_install_executor_disabled_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-install-executor-disabled",
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
            "real-sdk-dependency-install-executor-disabled",
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
    context = payload["realSdkDependencyInstallExecutorDisabledContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_install_executor_disabled_context(context)
