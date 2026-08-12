import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyInstallChangeProposalRequest,
    build_real_sdk_dependency_install_change_proposal,
    build_real_sdk_dependency_install_change_proposal_error_context,
    describe_real_sdk_dependency_install_change_proposal,
)
from tests.test_real_sdk_dependency_content_read_readonly_execution import (
    assert_safe_content_read_execution_context,
    confirmed_cli_args as confirmed_readonly_cli_args,
    confirmed_request as confirmed_readonly_request,
    make_dependency_root,
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


def assert_safe_install_change_proposal_context(context, *, proposal_allowed=False):
    assert_safe_content_read_execution_context(context, read_allowed=proposal_allowed)
    for key in [
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
    assert context["dependencyInstallPatchPlanGenerated"] is False
    if not proposal_allowed:
        assert context["nonExecutablePatchPreviewGenerated"] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_readonly_request())
    payload.update(
        {
            "approval_ref": "INSTALL-CHANGE-001",
            "install_change_proposal_scope_confirmed": True,
            "install_change_approver_confirmed": True,
            "install_change_ticket_confirmed": True,
            "readonly_content_review_confirmed": True,
            "target_manifest_change_confirmed": True,
            "target_lockfile_policy_confirmed": True,
            "openai_package_requirement_confirmed": True,
            "version_pin_policy_confirmed": True,
            "rollback_plan_confirmed": True,
            "no_dependency_file_write_during_proposal_confirmed": True,
            "no_patch_file_write_during_proposal_confirmed": True,
            "no_patch_apply_during_proposal_confirmed": True,
            "no_command_materialization_during_proposal_confirmed": True,
            "no_command_execution_during_proposal_confirmed": True,
            "no_dependency_install_during_proposal_confirmed": True,
            "no_package_resolution_during_proposal_confirmed": True,
            "no_secret_presence_check_during_proposal_confirmed": True,
            "no_network_during_proposal_confirmed": True,
            "no_real_call_during_proposal_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyInstallChangeProposalRequest(**payload)


def confirmed_cli_args():
    args = confirmed_readonly_cli_args()
    args[1] = "real-sdk-dependency-install-change-proposal"
    args[2] = "propose"
    args[args.index("--approval-ref") + 1] = "INSTALL-CHANGE-001"
    flags = [
        "install-change-proposal-scope",
        "install-change-approver",
        "install-change-ticket",
        "readonly-content-review",
        "target-manifest-change",
        "target-lockfile-policy",
        "openai-package-requirement",
        "version-pin-policy",
        "rollback-plan",
        "no-dependency-file-write-during-proposal",
        "no-patch-file-write-during-proposal",
        "no-patch-apply-during-proposal",
        "no-command-materialization-during-proposal",
        "no-command-execution-during-proposal",
        "no-dependency-install-during-proposal",
        "no-package-resolution-during-proposal",
        "no-secret-presence-check-during-proposal",
        "no-network-during-proposal",
        "no-real-call-during-proposal",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_install_change_proposal_contract_is_plan_only_and_local():
    contract = load_json("providers/real-sdk-dependency-install-change-proposal.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_install_change_proposal"
    assert contract["activeProvider"] == "mock"
    assert contract["safety"]["installChangeProposalOnly"] is True
    assert contract["safety"]["nonExecutablePatchPreviewAllowedAfterConfirmation"] is True
    assert contract["requiredContext"]["dependencyInstallPatchPlanGenerated"] is False
    assert contract["requiredContext"]["patchGenerated"] is False
    assert contract["requiredContext"]["dependencyFileChanged"] is False
    assert contract["requiredContext"]["dependencyInstallExecuted"] is False
    assert "write_dependency_manifest" in contract["blockedOperations"]
    assert "write_patch_file" in contract["blockedOperations"]
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_install_change_proposal" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_install_change_proposal_describe_is_safe():
    descriptor = describe_real_sdk_dependency_install_change_proposal(root=ROOT)

    assert descriptor["installChangeProposalId"] == "real_sdk_dependency_install_change_proposal"
    assert descriptor["gateMode"] == "DEPENDENCY_INSTALL_CHANGE_PROPOSAL_PLAN_ONLY"
    assert descriptor["proposalMode"] == "LOCAL_INSTALL_CHANGE_PROPOSAL_MODEL_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["installChangeProposalOnly"] is True
    assert descriptor["installChangeProposalModelReady"] is False
    assert "future_reviewed_dependency_install_execution" in descriptor["pipeline"]
    assert_safe_install_change_proposal_context(descriptor)


def test_real_sdk_dependency_install_change_proposal_default_does_not_read_or_propose(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_change_proposal(
        RealSdkDependencyInstallChangeProposalRequest(provider_id="openai"),
        root=root,
    )

    assert result["contentReadReadonlyExecutionModelReady"] is False
    assert result["installChangeProposalModelReady"] is False
    assert result["readyForDependencyInstallPatchReview"] is False
    assert result["installChangeProposalModel"] is None
    assert_safe_install_change_proposal_context(result)


def test_real_sdk_dependency_install_change_proposal_read_ready_but_missing_install_confirmations(tmp_path):
    root = make_dependency_root(tmp_path)
    result = build_real_sdk_dependency_install_change_proposal(
        confirmed_request(install_change_proposal_scope_confirmed=False),
        root=root,
    )
    checklist = {item["id"]: item for item in result["installChangeChecklist"]}

    assert result["contentReadReadonlyExecutionModelReady"] is True
    assert result["readonlyExecutionSummary"]["dependencyContentReadExecuted"] is True
    assert result["installChangeProposalModelReady"] is False
    assert result["installChangeProposalModel"] is None
    assert checklist["content_read_readonly_execution_model_ready"]["passed"] is True
    assert checklist["install_change_proposal_scope_confirmed"]["passed"] is False
    assert_safe_install_change_proposal_context(result, proposal_allowed=True)


def test_real_sdk_dependency_install_change_proposal_ready_generates_non_executable_preview_only(tmp_path):
    root = make_dependency_root(tmp_path)
    requirements = root / "requirements.txt"
    before = requirements.read_text(encoding="utf-8")
    result = build_real_sdk_dependency_install_change_proposal(confirmed_request(), root=root)
    after = requirements.read_text(encoding="utf-8")
    model = result["installChangeProposalModel"]

    assert result["contentReadReadonlyExecutionModelReady"] is True
    assert result["installChangeChecklistPassed"] is True
    assert result["installChangeProposalModelReady"] is True
    assert result["readyForDependencyInstallPatchReview"] is True
    assert result["dependencyInstallPatchPlanGenerated"] is False
    assert result["nonExecutablePatchPreviewGenerated"] is True
    assert model["proposalOnly"] is True
    assert model["dependencyFileWriteNow"] is False
    assert model["patchFileWriteNow"] is False
    assert model["patchApplyNow"] is False
    assert model["commandMaterializeNow"] is False
    assert model["installNow"] is False
    assert model["packageResolveNow"] is False
    assert model["secretCheckNow"] is False
    assert model["networkNow"] is False
    assert model["nonExecutablePatchPreview"]["generated"] is True
    assert model["nonExecutablePatchPreview"]["materialized"] is False
    assert "openai>=1.0.0,<2.0.0" in "\n".join(model["nonExecutablePatchPreview"]["lines"])
    assert before == after
    assert all(item["allowedNow"] is False for item in model["blockedActions"])
    assert_safe_install_change_proposal_context(result, proposal_allowed=True)


def test_real_sdk_dependency_install_change_proposal_invalid_scope_keeps_safe_error_context(tmp_path):
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_install_change_proposal(request, root=tmp_path)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_install_change_proposal_error_context(
            exc,
            request=request,
            root=tmp_path,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["installChangeProposalModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_install_change_proposal_context(context)


def test_real_sdk_dependency_install_change_proposal_cli_describe_and_propose_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-change-proposal", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installChangeProposalId"] == "real_sdk_dependency_install_change_proposal"
    assert payload["data"]["installChangeProposalModelReady"] is False
    assert_safe_install_change_proposal_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-change-proposal", "propose", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadReadonlyExecutionModelReady"] is False
    assert payload["data"]["installChangeProposalModelReady"] is False
    assert_safe_install_change_proposal_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadReadonlyExecutionModelReady"] is True
    assert payload["data"]["installChangeProposalModelReady"] is True
    assert payload["data"]["nonExecutablePatchPreviewGenerated"] is True
    assert payload["data"]["patchGenerated"] is False
    assert payload["data"]["patchFileWritten"] is False
    assert payload["data"]["dependencyInstallExecuted"] is False
    assert_safe_install_change_proposal_context(payload["data"], proposal_allowed=True)


def test_real_sdk_dependency_install_change_proposal_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-install-change-proposal",
            "propose",
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
            "real-sdk-dependency-install-change-proposal",
            "propose",
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
    context = payload["realSdkDependencyInstallChangeProposalContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_install_change_proposal_context(context)
