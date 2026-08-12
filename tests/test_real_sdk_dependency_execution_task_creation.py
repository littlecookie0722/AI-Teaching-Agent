import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyExecutionTaskCreationRequest,
    build_real_sdk_dependency_execution_task_creation,
    build_real_sdk_dependency_execution_task_creation_error_context,
    describe_real_sdk_dependency_execution_task_creation,
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


def assert_safe_task_creation_context(context):
    for key in [
        "executionApprovalGranted",
        "executionTaskCreated",
        "taskPersisted",
        "taskQueued",
        "executionDispatched",
        "dependencyFileMutationAuthorized",
        "dependencyFileChangeAuthorized",
        "dependencyManifestWriteAuthorized",
        "dependencyLockfileWriteAuthorized",
        "dependencyManifestMutated",
        "dependencyLockfileMutated",
        "dependencyFileChanged",
        "requirementsChanged",
        "pyprojectChanged",
        "lockfileChanged",
        "dependencyLockfileChanged",
        "patchGenerated",
        "patchMaterialized",
        "patchFileWritten",
        "patchApplied",
        "commandExecutionAuthorized",
        "commandExecuted",
        "dependencyInstallExecuted",
        "sdkDependencyInstalled",
        "sdkImported",
        "clientCreated",
        "secretPresenceChecked",
        "secretValueRead",
        "networkAccess",
        "realCallAfterTaskCreationAuthorized",
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
        "approval_ref": "TASK-CREATE-001",
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
        "readonly_diff_scope_confirmed": True,
        "dependency_snapshot_review_confirmed": True,
        "candidate_dependency_delta_confirmed": True,
        "rollback_delta_review_confirmed": True,
        "test_impact_review_confirmed": True,
        "reviewer_signoff_confirmed": True,
        "no_diff_review_artifact_write_confirmed": True,
        "no_patch_generation_confirmed": True,
        "no_install_or_lock_resolution_confirmed": True,
        "no_real_call_after_diff_review_confirmed": True,
        "readonly_diff_review_confirmed": True,
        "final_approver_identity_confirmed": True,
        "change_ticket_confirmed": True,
        "maintenance_window_reconfirmed": True,
        "rollback_checkpoint_confirmed": True,
        "post_change_validation_confirmed": True,
        "dependency_file_target_reconfirmed": True,
        "no_execution_authorization_confirmed": True,
        "no_dependency_file_mutation_confirmed": True,
        "no_real_call_after_final_confirmation_confirmed": True,
        "execution_task_scope_confirmed": True,
        "task_owner_confirmed": True,
        "task_queue_policy_confirmed": True,
        "dependency_execution_runbook_confirmed": True,
        "no_task_persistence_confirmed": True,
        "no_execution_dispatch_confirmed": True,
        "no_dependency_file_mutation_after_task_confirmed": True,
        "no_command_execution_after_task_confirmed": True,
        "no_dependency_install_after_task_confirmed": True,
        "no_real_call_after_task_creation_confirmed": True,
    }
    payload.update(overrides)
    return RealSdkDependencyExecutionTaskCreationRequest(**payload)


def confirmed_cli_args():
    args = [
        "provider",
        "real-sdk-dependency-execution-task-creation",
        "create",
        "--provider",
        "openai",
        "--approval-ref",
        "TASK-CREATE-001",
        "--reviewer",
        "teacher_1",
    ]
    flags = [
        "dry-run-plan",
        "runtime-guard",
        "schema-review",
        "human-review-policy",
        "audit-redaction",
        "sdk-dependency-review",
        "provider-contract-review",
        "runtime-contract-review",
        "secret-injection-review",
        "network-access-review",
        "rollback-plan",
        "minimal-impl-review",
        "sdk-package-review",
        "sdk-version-pin-review",
        "dependency-license-review",
        "dependency-hash-review",
        "env-var-name-review",
        "env-example-review",
        "secret-non-read-policy",
        "ci-install-policy",
        "package-manager-review",
        "lockfile-strategy-review",
        "version-pin-strategy",
        "hash-verification-strategy",
        "rollback-files-review",
        "ci-cache-policy",
        "no-install-execution",
        "no-network-policy",
        "no-secret-policy",
        "command-review",
        "dependency-file-review",
        "lockfile-diff-review",
        "offline-ci-review",
        "rollback-command-review",
        "execution-disabled",
        "preview-scope",
        "manifest-preview",
        "lockfile-preview",
        "rollback-preview",
        "no-diff-generation",
        "no-file-write",
        "patch-scope",
        "patch-plan-review",
        "no-patch-file-write",
        "no-patch-apply",
        "no-diff-artifact",
        "apply-scope",
        "final-manual-approval",
        "dependency-patch-proposal-review",
        "dependency-file-backup-review",
        "rollback-rehearsal-review",
        "no-apply-execution",
        "no-dependency-file-write",
        "no-command-execution",
        "implementation-task-scope",
        "change-window-review",
        "dependency-manifest-target",
        "lockfile-update-strategy",
        "rollback-owner",
        "post-change-test-owner",
        "no-dependency-file-change",
        "no-patch-materialization",
        "no-task-creation",
        "no-real-call-after-plan",
        "approver",
        "approval-record-location",
        "dependency-change-summary",
        "rollback-evidence",
        "test-evidence-plan",
        "security-owner",
        "maintenance-window",
        "no-approval-artifact-write",
        "no-dependency-change-execution",
        "no-real-call-before-approval",
        "readonly-diff-scope",
        "dependency-snapshot-review",
        "candidate-dependency-delta",
        "rollback-delta-review",
        "test-impact-review",
        "reviewer-signoff",
        "no-diff-review-artifact-write",
        "no-patch-generation",
        "no-install-or-lock-resolution",
        "no-real-call-after-diff-review",
        "readonly-diff-review",
        "final-approver-identity",
        "change-ticket",
        "maintenance-window-reconfirmed",
        "rollback-checkpoint",
        "post-change-validation",
        "dependency-file-target",
        "no-execution-authorization",
        "no-dependency-file-mutation",
        "no-real-call-after-final-confirmation",
        "execution-task-scope",
        "task-owner",
        "task-queue-policy",
        "dependency-execution-runbook",
        "no-task-persistence",
        "no-execution-dispatch",
        "no-dependency-file-mutation-after-task",
        "no-command-execution-after-task",
        "no-dependency-install-after-task",
        "no-real-call-after-task-creation",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_execution_task_creation_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-execution-task-creation.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_execution_task_creation"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["executionTaskCreationOnly"] is True
    assert contract["requiredContext"]["executionTaskCreationModelReady"] is False
    assert contract["requiredContext"]["executionTaskCreated"] is False
    assert contract["requiredContext"]["taskPersisted"] is False
    assert contract["requiredContext"]["executionDispatched"] is False
    assert "persist_dependency_execution_task" in contract["blockedOperations"]
    assert "dispatch_dependency_execution" in contract["blockedOperations"]
    assert "write_dependency_manifest" in contract["blockedOperations"]
    assert "execute_install_command" in contract["blockedOperations"]
    assert "check_secret_presence" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_execution_task_creation" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_execution_task_creation_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_execution_task_creation(root=ROOT)

    assert descriptor["executionTaskCreationId"] == "real_sdk_dependency_execution_task_creation"
    assert descriptor["gateMode"] == "DEPENDENCY_EXECUTION_TASK_CREATION_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresFinalExecutionConfirmationReady"] is True
    assert descriptor["executionTaskCreationOnly"] is True
    assert "future_real_dependency_file_change_executor" in descriptor["pipeline"]
    assert_safe_task_creation_context(descriptor)


def test_real_sdk_dependency_execution_task_creation_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "task-create-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_execution_task_creation(
        RealSdkDependencyExecutionTaskCreationRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["executionTaskCreationChecklist"]}
    assert result["finalExecutionConfirmationReady"] is False
    assert result["executionTaskCreationModelReady"] is False
    assert result["readyForDisabledDependencyExecutionTaskRecord"] is False
    assert checklist["final_execution_confirmation_ready"]["passed"] is False
    assert checklist["task_owner_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_task_creation_context(result)


def test_real_sdk_dependency_execution_task_creation_final_ready_but_missing_task_confirmations():
    request = confirmed_request(task_owner_confirmed=False, no_task_persistence_confirmed=False)
    result = build_real_sdk_dependency_execution_task_creation(request, root=ROOT)
    checklist = {item["id"]: item for item in result["executionTaskCreationChecklist"]}

    assert result["finalExecutionConfirmationReady"] is True
    assert result["finalExecutionConfirmationSummary"]["readyForReviewedDependencyExecutionTask"] is True
    assert result["executionTaskCreationModelReady"] is False
    assert result["readyForDisabledDependencyExecutionTaskRecord"] is False
    assert checklist["final_execution_confirmation_ready"]["passed"] is True
    assert checklist["task_owner_confirmed"]["passed"] is False
    assert checklist["no_task_persistence_confirmed"]["passed"] is False
    assert_safe_task_creation_context(result)


def test_real_sdk_dependency_execution_task_creation_ready_but_no_task_persistence_or_dispatch():
    result = build_real_sdk_dependency_execution_task_creation(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["executionTaskCreationChecklist"]}

    assert result["finalExecutionConfirmationReady"] is True
    assert result["executionTaskCreationModelReady"] is True
    assert result["readyForDisabledDependencyExecutionTaskRecord"] is True
    assert result["executionTaskCreated"] is False
    assert result["taskPersisted"] is False
    assert result["taskQueued"] is False
    assert result["executionDispatched"] is False
    assert checklist["no_task_persistence_confirmed"]["passed"] is True
    assert checklist["no_execution_dispatch_confirmed"]["passed"] is True
    assert result["taskCreationModel"]["materializedNow"] is False
    assert result["taskCreationModel"]["persistNow"] is False
    assert result["taskCreationModel"]["dispatchNow"] is False
    assert result["taskCreationModel"]["taskRecord"]["status"] == "NOT_CREATED"
    assert all(item["allowedNow"] is False for item in result["taskCreationModel"]["blockedActions"])
    assert result["futureChangeEnvelope"]["executionTaskCreated"] is False
    assert result["futureChangeEnvelope"]["taskPersisted"] is False
    assert result["futureChangeEnvelope"]["executionDispatched"] is False
    assert result["futureChangeEnvelope"]["commandExecuted"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_task_creation_context(result)


def test_real_sdk_dependency_execution_task_creation_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_execution_task_creation(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_execution_task_creation_error_context(
            exc,
            request=request,
            root=ROOT,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["executionTaskCreationModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_task_creation_context(context)


def test_real_sdk_dependency_execution_task_creation_cli_describe_and_create_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-execution-task-creation", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["executionTaskCreationId"] == "real_sdk_dependency_execution_task_creation"
    assert payload["data"]["executionTaskCreationModelReady"] is False
    assert_safe_task_creation_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-execution-task-creation", "create", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["finalExecutionConfirmationReady"] is False
    assert payload["data"]["executionTaskCreationModelReady"] is False
    assert_safe_task_creation_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["finalExecutionConfirmationReady"] is True
    assert payload["data"]["executionTaskCreationModelReady"] is True
    assert payload["data"]["readyForDisabledDependencyExecutionTaskRecord"] is True
    assert payload["data"]["executionTaskCreated"] is False
    assert payload["data"]["taskPersisted"] is False
    assert payload["data"]["executionDispatched"] is False
    assert_safe_task_creation_context(payload["data"])


def test_real_sdk_dependency_execution_task_creation_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-execution-task-creation",
            "create",
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
            "real-sdk-dependency-execution-task-creation",
            "create",
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
    context = payload["realSdkDependencyExecutionTaskCreationContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_task_creation_context(context)
