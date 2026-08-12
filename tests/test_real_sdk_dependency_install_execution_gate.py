import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyInstallExecutionGateRequest,
    build_real_sdk_dependency_install_execution_gate,
    build_real_sdk_dependency_install_execution_gate_error_context,
    describe_real_sdk_dependency_install_execution_gate,
)
from tests.test_real_sdk_dependency_content_read_readonly_execution import make_dependency_root
from tests.test_real_sdk_dependency_executor_disabled import assert_json_envelope
from tests.test_real_sdk_dependency_install_change_proposal import (
    assert_safe_install_change_proposal_context,
    confirmed_cli_args as confirmed_proposal_cli_args,
    confirmed_request as confirmed_proposal_request,
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


def assert_safe_install_execution_gate_context(context, *, proposal_allowed=False):
    assert_safe_install_change_proposal_context(context, proposal_allowed=proposal_allowed)
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
    if not proposal_allowed:
        assert context["installExecutionGateModelReady"] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_proposal_request())
    payload.update(
        {
            "approval_ref": "INSTALL-EXEC-GATE-001",
            "dependency_install_execution_scope_confirmed": True,
            "install_execution_approver_confirmed": True,
            "install_execution_ticket_confirmed": True,
            "install_execution_change_window_confirmed": True,
            "install_change_proposal_review_confirmed": True,
            "dependency_manifest_target_confirmed": True,
            "lockfile_update_policy_confirmed": True,
            "package_manager_policy_confirmed": True,
            "install_execution_rollback_checkpoint_confirmed": True,
            "post_install_validation_plan_confirmed": True,
            "no_dependency_file_write_during_execution_gate_confirmed": True,
            "no_patch_file_write_during_execution_gate_confirmed": True,
            "no_patch_apply_during_execution_gate_confirmed": True,
            "no_command_materialization_during_execution_gate_confirmed": True,
            "no_command_execution_during_execution_gate_confirmed": True,
            "no_dependency_install_during_execution_gate_confirmed": True,
            "no_package_resolution_during_execution_gate_confirmed": True,
            "no_secret_presence_check_during_execution_gate_confirmed": True,
            "no_network_during_execution_gate_confirmed": True,
            "no_real_call_during_execution_gate_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyInstallExecutionGateRequest(**payload)


def confirmed_cli_args():
    args = confirmed_proposal_cli_args()
    args[1] = "real-sdk-dependency-install-execution-gate"
    args[2] = "evaluate"
    args[args.index("--approval-ref") + 1] = "INSTALL-EXEC-GATE-001"
    flags = [
        "dependency-install-execution-scope",
        "install-execution-approver",
        "install-execution-ticket",
        "install-execution-change-window",
        "install-change-proposal-review",
        "dependency-manifest-target",
        "lockfile-update-policy",
        "package-manager-policy",
        "install-execution-rollback-checkpoint",
        "post-install-validation-plan",
        "no-dependency-file-write-during-execution-gate",
        "no-patch-file-write-during-execution-gate",
        "no-patch-apply-during-execution-gate",
        "no-command-materialization-during-execution-gate",
        "no-command-execution-during-execution-gate",
        "no-dependency-install-during-execution-gate",
        "no-package-resolution-during-execution-gate",
        "no-secret-presence-check-during-execution-gate",
        "no-network-during-execution-gate",
        "no-real-call-during-execution-gate",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_install_execution_gate_contract_is_disabled_and_local():
    contract = load_json("providers/real-sdk-dependency-install-execution-gate.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_install_execution_gate"
    assert contract["activeProvider"] == "mock"
    assert contract["safety"]["installExecutionGateOnly"] is True
    assert contract["safety"]["executionAuthorizationGranted"] is False
    assert contract["requiredContext"]["executionAuthorized"] is False
    assert contract["requiredContext"]["commandExecuted"] is False
    assert contract["requiredContext"]["dependencyInstallExecuted"] is False
    assert "authorize_dependency_install_execution" in contract["blockedOperations"]
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_install_execution_gate" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_install_execution_gate_describe_is_safe():
    descriptor = describe_real_sdk_dependency_install_execution_gate(root=ROOT)

    assert descriptor["installExecutionGateId"] == "real_sdk_dependency_install_execution_gate"
    assert descriptor["gateMode"] == "DEPENDENCY_INSTALL_EXECUTION_GATE_DISABLED"
    assert descriptor["executionGateMode"] == "LOCAL_DEPENDENCY_INSTALL_EXECUTION_GATE_MODEL_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["installExecutionGateOnly"] is True
    assert descriptor["installExecutionGateModelReady"] is False
    assert "future_explicit_dependency_install_execution" in descriptor["pipeline"]
    assert_safe_install_execution_gate_context(descriptor)


def test_real_sdk_dependency_install_execution_gate_default_does_not_prepare_execution(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_execution_gate(
        RealSdkDependencyInstallExecutionGateRequest(provider_id="openai"),
        root=root,
    )

    assert result["installChangeProposalModelReady"] is False
    assert result["installExecutionGateModelReady"] is False
    assert result["readyForSeparateDependencyInstallExecutionApproval"] is False
    assert result["installExecutionGateModel"] is None
    assert_safe_install_execution_gate_context(result)


def test_real_sdk_dependency_install_execution_gate_ready_still_does_not_install(tmp_path):
    root = make_dependency_root(tmp_path)
    requirements = root / "requirements.txt"
    before = requirements.read_text(encoding="utf-8")
    result = build_real_sdk_dependency_install_execution_gate(confirmed_request(), root=root)
    after = requirements.read_text(encoding="utf-8")
    model = result["installExecutionGateModel"]

    assert result["installChangeProposalModelReady"] is True
    assert result["installExecutionGateChecklistPassed"] is True
    assert result["installExecutionGateModelReady"] is True
    assert result["readyForSeparateDependencyInstallExecutionApproval"] is True
    assert model["gateOnly"] is True
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
    assert_safe_install_execution_gate_context(result, proposal_allowed=True)


def test_real_sdk_dependency_install_execution_gate_missing_gate_confirmations(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_execution_gate(
        confirmed_request(dependency_install_execution_scope_confirmed=False),
        root=root,
    )
    checklist = {item["id"]: item for item in result["installExecutionGateChecklist"]}

    assert result["installChangeProposalModelReady"] is True
    assert result["installExecutionGateModelReady"] is False
    assert result["installExecutionGateModel"] is None
    assert checklist["install_change_proposal_model_ready"]["passed"] is True
    assert checklist["dependency_install_execution_scope_confirmed"]["passed"] is False
    assert_safe_install_execution_gate_context(result, proposal_allowed=True)


def test_real_sdk_dependency_install_execution_gate_invalid_scope_keeps_safe_error_context(tmp_path):
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_install_execution_gate(request, root=tmp_path)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_install_execution_gate_error_context(
            exc,
            request=request,
            root=tmp_path,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["installExecutionGateModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_install_execution_gate_context(context)


def test_real_sdk_dependency_install_execution_gate_cli_describe_and_evaluate_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-execution-gate", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installExecutionGateId"] == "real_sdk_dependency_install_execution_gate"
    assert payload["data"]["installExecutionGateModelReady"] is False
    assert_safe_install_execution_gate_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-execution-gate", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installChangeProposalModelReady"] is False
    assert payload["data"]["installExecutionGateModelReady"] is False
    assert_safe_install_execution_gate_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installChangeProposalModelReady"] is True
    assert payload["data"]["installExecutionGateModelReady"] is True
    assert payload["data"]["executionAuthorized"] is False
    assert payload["data"]["commandExecuted"] is False
    assert payload["data"]["dependencyInstallExecuted"] is False
    assert_safe_install_execution_gate_context(payload["data"], proposal_allowed=True)


def test_real_sdk_dependency_install_execution_gate_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-install-execution-gate",
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
            "real-sdk-dependency-install-execution-gate",
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
    context = payload["realSdkDependencyInstallExecutionGateContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_install_execution_gate_context(context)
