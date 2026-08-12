import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyApplyGateRequest,
    build_real_sdk_dependency_apply_gate,
    build_real_sdk_dependency_apply_gate_error_context,
    describe_real_sdk_dependency_apply_gate,
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


def assert_json_envelope(payload):
    assert set(payload) >= {"success", "code", "message", "traceId"}
    assert payload["traceId"].startswith("trace_")


def assert_safe_apply_gate_context(context):
    for key in [
        "applyAuthorized",
        "applyApprovalMaterialized",
        "patchProposalMaterialized",
        "patchFileWritten",
        "patchApplied",
        "dependencyPatchGenerated",
        "dependencyFileWritePlannedNow",
        "dependencyFileChanged",
        "requirementsChanged",
        "pyprojectChanged",
        "lockfileChanged",
        "dependencyLockfileChanged",
        "lockfileDiffGenerated",
        "dependencyDiffGenerated",
        "diffArtifactWritten",
        "rollbackDiffGenerated",
        "rollbackCommandGenerated",
        "offlineCiExecuted",
        "installerExecutionEnabled",
        "installCommandMaterialized",
        "dependencyInstallAllowed",
        "dependencyInstallCommandGenerated",
        "dependencyInstallExecuted",
        "sdkDependencyInstallAllowed",
        "sdkDependencyInstalled",
        "packageVersionResolved",
        "packageHashResolved",
        "packageDownloaded",
        "sdkImported",
        "clientCreated",
        "secretPresenceChecked",
        "secretValueRead",
        "secretValueReturned",
        "networkAccess",
        "networkAccessEnabledNow",
        "generatedContentCreated",
        "taskCreated",
        "reviewBypassed",
        "realCallAuthorized",
        "realLlmCalled",
        "secretsRead",
        "providerContractChangeApplied",
        "runtimeContractChangeApplied",
        "autoPublishAllowed",
        "realPublish",
    ]:
        assert context[key] is False


def confirmed_request(**overrides):
    payload = {
        "provider_id": "openai",
        "approval_ref": "APPROVAL-APPLY-001",
        "reviewer": "teacher_1",
        "dry_run_plan_confirmed": True,
        "runtime_guard_confirmed": True,
        "schema_review_confirmed": True,
        "human_review_policy_confirmed": True,
        "audit_redaction_confirmed": True,
        "sdk_dependency_review_confirmed": True,
        "provider_contract_review_confirmed": True,
        "runtime_contract_review_confirmed": True,
        "secret_injection_review_confirmed": True,
        "network_access_review_confirmed": True,
        "rollback_plan_confirmed": True,
        "minimal_impl_review_confirmed": True,
        "sdk_package_review_confirmed": True,
        "sdk_version_pin_review_confirmed": True,
        "dependency_license_review_confirmed": True,
        "dependency_hash_review_confirmed": True,
        "env_var_name_review_confirmed": True,
        "env_example_review_confirmed": True,
        "secret_non_read_policy_confirmed": True,
        "ci_install_policy_confirmed": True,
        "package_manager_review_confirmed": True,
        "lockfile_strategy_review_confirmed": True,
        "version_pin_strategy_confirmed": True,
        "hash_verification_strategy_confirmed": True,
        "rollback_files_review_confirmed": True,
        "ci_cache_policy_confirmed": True,
        "no_install_execution_confirmed": True,
        "no_network_policy_confirmed": True,
        "no_secret_policy_confirmed": True,
        "command_review_confirmed": True,
        "dependency_file_review_confirmed": True,
        "lockfile_diff_review_confirmed": True,
        "offline_ci_review_confirmed": True,
        "rollback_command_review_confirmed": True,
        "execution_disabled_confirmed": True,
        "preview_scope_confirmed": True,
        "manifest_preview_confirmed": True,
        "lockfile_preview_confirmed": True,
        "rollback_preview_confirmed": True,
        "no_diff_generation_confirmed": True,
        "no_file_write_confirmed": True,
        "patch_scope_confirmed": True,
        "patch_plan_review_confirmed": True,
        "no_patch_file_write_confirmed": True,
        "no_patch_apply_confirmed": True,
        "no_diff_artifact_confirmed": True,
        "apply_scope_confirmed": True,
        "final_manual_approval_confirmed": True,
        "dependency_patch_proposal_review_confirmed": True,
        "dependency_file_backup_review_confirmed": True,
        "rollback_rehearsal_review_confirmed": True,
        "no_apply_execution_confirmed": True,
        "no_dependency_file_write_confirmed": True,
        "no_command_execution_confirmed": True,
    }
    payload.update(overrides)
    return RealSdkDependencyApplyGateRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-sdk-dependency-apply-gate",
        "evaluate",
        "--provider",
        "openai",
        "--approval-ref",
        "APPROVAL-APPLY-001",
        "--reviewer",
        "teacher_1",
        "--confirm-dry-run-plan",
        "--confirm-runtime-guard",
        "--confirm-schema-review",
        "--confirm-human-review-policy",
        "--confirm-audit-redaction",
        "--confirm-sdk-dependency-review",
        "--confirm-provider-contract-review",
        "--confirm-runtime-contract-review",
        "--confirm-secret-injection-review",
        "--confirm-network-access-review",
        "--confirm-rollback-plan",
        "--confirm-minimal-impl-review",
        "--confirm-sdk-package-review",
        "--confirm-sdk-version-pin-review",
        "--confirm-dependency-license-review",
        "--confirm-dependency-hash-review",
        "--confirm-env-var-name-review",
        "--confirm-env-example-review",
        "--confirm-secret-non-read-policy",
        "--confirm-ci-install-policy",
        "--confirm-package-manager-review",
        "--confirm-lockfile-strategy-review",
        "--confirm-version-pin-strategy",
        "--confirm-hash-verification-strategy",
        "--confirm-rollback-files-review",
        "--confirm-ci-cache-policy",
        "--confirm-no-install-execution",
        "--confirm-no-network-policy",
        "--confirm-no-secret-policy",
        "--confirm-command-review",
        "--confirm-dependency-file-review",
        "--confirm-lockfile-diff-review",
        "--confirm-offline-ci-review",
        "--confirm-rollback-command-review",
        "--confirm-execution-disabled",
        "--confirm-preview-scope",
        "--confirm-manifest-preview",
        "--confirm-lockfile-preview",
        "--confirm-rollback-preview",
        "--confirm-no-diff-generation",
        "--confirm-no-file-write",
        "--confirm-patch-scope",
        "--confirm-patch-plan-review",
        "--confirm-no-patch-file-write",
        "--confirm-no-patch-apply",
        "--confirm-no-diff-artifact",
        "--confirm-apply-scope",
        "--confirm-final-manual-approval",
        "--confirm-dependency-patch-proposal-review",
        "--confirm-dependency-file-backup-review",
        "--confirm-rollback-rehearsal-review",
        "--confirm-no-apply-execution",
        "--confirm-no-dependency-file-write",
        "--confirm-no-command-execution",
    ]


def test_real_sdk_dependency_apply_gate_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-apply-gate.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_apply_gate"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["patchProposalRequired"] is True
    assert contract["requiredContext"]["patchProposalReady"] is False
    assert contract["requiredContext"]["dependencyApplyGateOnly"] is True
    assert contract["requiredContext"]["applyAuthorized"] is False
    assert contract["requiredContext"]["patchApplied"] is False
    assert "authorize_patch_apply" in contract["blockedOperations"]
    assert "apply_patch" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_apply_gate" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_apply_gate_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_apply_gate(root=ROOT)

    assert descriptor["gateId"] == "real_sdk_dependency_apply_gate"
    assert descriptor["gateMode"] == "DEPENDENCY_APPLY_GATE_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresPatchProposal"] is True
    assert descriptor["dependencyApplyGateOnly"] is True
    assert "future_dependency_patch_apply_task" in descriptor["pipeline"]
    assert_safe_apply_gate_context(descriptor)


def test_real_sdk_dependency_apply_gate_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "apply-gate-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_apply_gate(
        RealSdkDependencyApplyGateRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["applyGateChecklist"]}
    assert result["patchProposalReady"] is False
    assert result["applyGateChecklistPassed"] is False
    assert result["readyForFutureDependencyPatchApplyTask"] is False
    assert checklist["patch_proposal_ready"]["passed"] is False
    assert checklist["final_manual_approval_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_apply_gate_context(result)


def test_real_sdk_dependency_apply_gate_proposal_ready_but_missing_apply_confirmations():
    request = confirmed_request(apply_scope_confirmed=False, final_manual_approval_confirmed=False)
    result = build_real_sdk_dependency_apply_gate(request, root=ROOT)
    checklist = {item["id"]: item for item in result["applyGateChecklist"]}

    assert result["patchProposalReady"] is True
    assert result["patchProposalSummary"]["readyForDependencyPatchImplementationTask"] is True
    assert result["applyGateChecklistPassed"] is False
    assert result["readyForFutureDependencyPatchApplyTask"] is False
    assert checklist["patch_proposal_ready"]["passed"] is True
    assert checklist["apply_scope_confirmed"]["passed"] is False
    assert checklist["final_manual_approval_confirmed"]["passed"] is False
    assert_safe_apply_gate_context(result)


def test_real_sdk_dependency_apply_gate_all_confirmations_ready_but_apply_still_unauthorized():
    result = build_real_sdk_dependency_apply_gate(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["applyGateChecklist"]}

    assert result["patchProposalReady"] is True
    assert result["applyGateChecklistPassed"] is True
    assert result["readyForFutureDependencyPatchApplyTask"] is True
    assert result["dependencyApplyGateReady"] is True
    assert checklist["no_apply_execution_confirmed"]["passed"] is True
    assert all(item["materializedNow"] is False for item in result["applyEvidencePlan"])
    assert result["applyPolicy"]["applyAuthorized"] is False
    assert result["applyPolicy"]["patchApplied"] is False
    assert result["applyPolicy"]["dependencyFileChanged"] is False
    assert result["applyPolicy"]["commandExecuted"] is False
    assert_safe_apply_gate_context(result)


def test_real_sdk_dependency_apply_gate_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_apply_gate(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_apply_gate_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["patchProposalReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_apply_gate_context(context)


def test_real_sdk_dependency_apply_gate_cli_describe_and_evaluate_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-dependency-apply-gate", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["gateId"] == "real_sdk_dependency_apply_gate"
    assert payload["data"]["readyForFutureDependencyPatchApplyTask"] is False
    assert_safe_apply_gate_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-apply-gate", "evaluate", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["patchProposalReady"] is False
    assert payload["data"]["applyGateChecklistPassed"] is False
    assert_safe_apply_gate_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["patchProposalReady"] is True
    assert payload["data"]["applyGateChecklistPassed"] is True
    assert payload["data"]["readyForFutureDependencyPatchApplyTask"] is True
    assert payload["data"]["applyAuthorized"] is False
    assert_safe_apply_gate_context(payload["data"])


def test_real_sdk_dependency_apply_gate_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-apply-gate", "evaluate", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-apply-gate", "evaluate", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkDependencyApplyGateContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_apply_gate_context(context)
