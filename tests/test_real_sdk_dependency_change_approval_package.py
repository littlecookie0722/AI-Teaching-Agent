import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyChangeApprovalPackageRequest,
    build_real_sdk_dependency_change_approval_package,
    build_real_sdk_dependency_change_approval_package_error_context,
    describe_real_sdk_dependency_change_approval_package,
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


def assert_safe_approval_package_context(context):
    for key in [
        "manualApprovalGranted",
        "approvalPackageWritten",
        "approvalRecordMaterialized",
        "approvalTicketCreated",
        "dependencyChangeApproved",
        "dependencyChangeExecutionAuthorized",
        "dependencyFileChangeAuthorized",
        "dependencyManifestWriteAuthorized",
        "dependencyLockfileWriteAuthorized",
        "patchMaterialized",
        "patchFileWritten",
        "patchApplied",
        "patchApplyAuthorized",
        "commandExecutionAuthorized",
        "dependencyImplementationTaskCreated",
        "dependencyPatchGenerated",
        "dependencyFileChanged",
        "requirementsChanged",
        "pyprojectChanged",
        "lockfileChanged",
        "dependencyLockfileChanged",
        "dependencyInstallExecuted",
        "sdkDependencyInstalled",
        "sdkImported",
        "clientCreated",
        "secretPresenceChecked",
        "secretValueRead",
        "networkAccess",
        "realCallBeforeApprovalAuthorized",
        "realLlmCalled",
        "generatedContentCreated",
        "taskCreated",
        "reviewBypassed",
        "realCallAuthorized",
        "autoPublishAllowed",
        "realPublish",
    ]:
        assert context[key] is False


def confirmed_request(**overrides):
    payload = {
        "provider_id": "openai",
        "approval_ref": "APPROVAL-PACKAGE-001",
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
        "implementation_task_scope_confirmed": True,
        "change_window_review_confirmed": True,
        "dependency_manifest_target_confirmed": True,
        "lockfile_update_strategy_confirmed": True,
        "rollback_owner_confirmed": True,
        "post_change_test_owner_confirmed": True,
        "no_dependency_file_change_confirmed": True,
        "no_patch_materialization_confirmed": True,
        "no_task_creation_confirmed": True,
        "no_real_call_after_plan_confirmed": True,
        "approver_confirmed": True,
        "approval_record_location_confirmed": True,
        "dependency_change_summary_confirmed": True,
        "rollback_evidence_confirmed": True,
        "test_evidence_plan_confirmed": True,
        "security_owner_confirmed": True,
        "maintenance_window_confirmed": True,
        "no_approval_artifact_write_confirmed": True,
        "no_dependency_change_execution_confirmed": True,
        "no_real_call_before_approval_confirmed": True,
    }
    payload.update(overrides)
    return RealSdkDependencyChangeApprovalPackageRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-sdk-dependency-change-approval-package",
        "package",
        "--provider",
        "openai",
        "--approval-ref",
        "APPROVAL-PACKAGE-001",
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
        "--confirm-implementation-task-scope",
        "--confirm-change-window-review",
        "--confirm-dependency-manifest-target",
        "--confirm-lockfile-update-strategy",
        "--confirm-rollback-owner",
        "--confirm-post-change-test-owner",
        "--confirm-no-dependency-file-change",
        "--confirm-no-patch-materialization",
        "--confirm-no-task-creation",
        "--confirm-no-real-call-after-plan",
        "--confirm-approver",
        "--confirm-approval-record-location",
        "--confirm-dependency-change-summary",
        "--confirm-rollback-evidence",
        "--confirm-test-evidence-plan",
        "--confirm-security-owner",
        "--confirm-maintenance-window",
        "--confirm-no-approval-artifact-write",
        "--confirm-no-dependency-change-execution",
        "--confirm-no-real-call-before-approval",
    ]


def test_real_sdk_dependency_change_approval_package_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-change-approval-package.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_change_approval_package"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["approvalPackageOnly"] is True
    assert contract["requiredContext"]["approvalPackageWritten"] is False
    assert contract["requiredContext"]["manualApprovalGranted"] is False
    assert contract["requiredContext"]["dependencyFileChanged"] is False
    assert "write_approval_artifact" in contract["blockedOperations"]
    assert "write_dependency_manifest" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_change_approval_package" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_change_approval_package_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_change_approval_package(root=ROOT)

    assert descriptor["approvalPackageId"] == "real_sdk_dependency_change_approval_package"
    assert descriptor["gateMode"] == "DEPENDENCY_CHANGE_APPROVAL_PACKAGE_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresImplementationTaskPlanReady"] is True
    assert descriptor["approvalPackageOnly"] is True
    assert "future_reviewed_dependency_file_change_task" in descriptor["pipeline"]
    assert_safe_approval_package_context(descriptor)


def test_real_sdk_dependency_change_approval_package_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "approval-package-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_change_approval_package(
        RealSdkDependencyChangeApprovalPackageRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["approvalPackageChecklist"]}
    assert result["implementationTaskPlanReady"] is False
    assert result["approvalPackageReady"] is False
    assert result["readyForManualDependencyChangeApproval"] is False
    assert checklist["implementation_task_plan_ready"]["passed"] is False
    assert checklist["approver_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_approval_package_context(result)


def test_real_sdk_dependency_change_approval_package_task_plan_ready_but_missing_approval_confirmations():
    request = confirmed_request(approver_confirmed=False, rollback_evidence_confirmed=False)
    result = build_real_sdk_dependency_change_approval_package(request, root=ROOT)
    checklist = {item["id"]: item for item in result["approvalPackageChecklist"]}

    assert result["implementationTaskPlanReady"] is True
    assert result["implementationTaskPlanSummary"]["readyForReviewedDependencyImplementationTask"] is True
    assert result["approvalPackageReady"] is False
    assert result["readyForManualDependencyChangeApproval"] is False
    assert checklist["implementation_task_plan_ready"]["passed"] is True
    assert checklist["approver_confirmed"]["passed"] is False
    assert checklist["rollback_evidence_confirmed"]["passed"] is False
    assert_safe_approval_package_context(result)


def test_real_sdk_dependency_change_approval_package_all_confirmations_ready_but_no_approval_or_file_change():
    result = build_real_sdk_dependency_change_approval_package(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["approvalPackageChecklist"]}

    assert result["implementationTaskPlanReady"] is True
    assert result["approvalPackageReady"] is True
    assert result["readyForManualDependencyChangeApproval"] is True
    assert checklist["no_approval_artifact_write_confirmed"]["passed"] is True
    assert checklist["no_dependency_change_execution_confirmed"]["passed"] is True
    assert result["approvalPackageModel"]["materializedNow"] is False
    assert result["approvalPackageModel"]["writeNow"] is False
    assert all(item["materializedNow"] is False for item in result["approvalPackageModel"]["requiredEvidence"])
    assert result["futureChangeEnvelope"]["approvalPackageWritten"] is False
    assert result["futureChangeEnvelope"]["manualApprovalGranted"] is False
    assert result["futureChangeEnvelope"]["dependencyFileChanged"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_approval_package_context(result)


def test_real_sdk_dependency_change_approval_package_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_change_approval_package(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_change_approval_package_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["implementationTaskPlanReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_approval_package_context(context)


def test_real_sdk_dependency_change_approval_package_cli_describe_and_package_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-dependency-change-approval-package", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["approvalPackageId"] == "real_sdk_dependency_change_approval_package"
    assert payload["data"]["readyForManualDependencyChangeApproval"] is False
    assert_safe_approval_package_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-change-approval-package", "package", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["implementationTaskPlanReady"] is False
    assert payload["data"]["approvalPackageReady"] is False
    assert_safe_approval_package_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["implementationTaskPlanReady"] is True
    assert payload["data"]["approvalPackageReady"] is True
    assert payload["data"]["readyForManualDependencyChangeApproval"] is True
    assert payload["data"]["approvalPackageWritten"] is False
    assert_safe_approval_package_context(payload["data"])


def test_real_sdk_dependency_change_approval_package_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-change-approval-package",
            "package",
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
            "real-sdk-dependency-change-approval-package",
            "package",
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
    context = payload["realSdkDependencyChangeApprovalPackageContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_approval_package_context(context)
