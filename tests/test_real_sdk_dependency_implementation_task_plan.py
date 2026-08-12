import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyImplementationTaskPlanRequest,
    build_real_sdk_dependency_implementation_task_plan,
    build_real_sdk_dependency_implementation_task_plan_error_context,
    describe_real_sdk_dependency_implementation_task_plan,
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


def assert_safe_task_plan_context(context):
    for key in [
        "dependencyImplementationTaskCreated",
        "implementationTicketMaterialized",
        "taskCreationAuthorized",
        "dependencyFileChangeAuthorized",
        "dependencyManifestWriteAuthorized",
        "dependencyLockfileWriteAuthorized",
        "patchMaterialized",
        "patchFileWritten",
        "patchApplied",
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
        "realCallAfterPlanAuthorized",
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
        "approval_ref": "APPROVAL-IMPLEMENT-001",
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
    }
    payload.update(overrides)
    return RealSdkDependencyImplementationTaskPlanRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-sdk-dependency-implementation-task-plan",
        "plan",
        "--provider",
        "openai",
        "--approval-ref",
        "APPROVAL-IMPLEMENT-001",
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
    ]


def test_real_sdk_dependency_implementation_task_plan_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-implementation-task-plan.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_implementation_task_plan"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["implementationTaskPlanOnly"] is True
    assert contract["requiredContext"]["dependencyImplementationTaskCreated"] is False
    assert contract["requiredContext"]["dependencyFileChanged"] is False
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert "create_dependency_implementation_task" in contract["blockedOperations"]
    assert "write_dependency_manifest" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_implementation_task_plan" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_implementation_task_plan_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_implementation_task_plan(root=ROOT)

    assert descriptor["planId"] == "real_sdk_dependency_implementation_task_plan"
    assert descriptor["gateMode"] == "DEPENDENCY_IMPLEMENTATION_TASK_PLAN_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresApplyGateReady"] is True
    assert descriptor["implementationTaskPlanOnly"] is True
    assert "future_reviewed_dependency_file_change_task" in descriptor["pipeline"]
    assert_safe_task_plan_context(descriptor)


def test_real_sdk_dependency_implementation_task_plan_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "implementation-plan-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_implementation_task_plan(
        RealSdkDependencyImplementationTaskPlanRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["implementationTaskPlanChecklist"]}
    assert result["applyGateReady"] is False
    assert result["implementationTaskPlanReady"] is False
    assert result["readyForReviewedDependencyImplementationTask"] is False
    assert checklist["apply_gate_ready"]["passed"] is False
    assert checklist["implementation_task_scope_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_task_plan_context(result)


def test_real_sdk_dependency_implementation_task_plan_apply_gate_ready_but_missing_plan_confirmations():
    request = confirmed_request(
        implementation_task_scope_confirmed=False,
        change_window_review_confirmed=False,
    )
    result = build_real_sdk_dependency_implementation_task_plan(request, root=ROOT)
    checklist = {item["id"]: item for item in result["implementationTaskPlanChecklist"]}

    assert result["applyGateReady"] is True
    assert result["applyGateSummary"]["readyForFutureDependencyPatchApplyTask"] is True
    assert result["implementationTaskPlanReady"] is False
    assert result["readyForReviewedDependencyImplementationTask"] is False
    assert checklist["apply_gate_ready"]["passed"] is True
    assert checklist["implementation_task_scope_confirmed"]["passed"] is False
    assert checklist["change_window_review_confirmed"]["passed"] is False
    assert_safe_task_plan_context(result)


def test_real_sdk_dependency_implementation_task_plan_all_confirmations_ready_but_no_task_or_file_change():
    result = build_real_sdk_dependency_implementation_task_plan(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["implementationTaskPlanChecklist"]}

    assert result["applyGateReady"] is True
    assert result["implementationTaskPlanReady"] is True
    assert result["readyForReviewedDependencyImplementationTask"] is True
    assert checklist["no_task_creation_confirmed"]["passed"] is True
    assert checklist["no_dependency_file_change_confirmed"]["passed"] is True
    assert all(step["executeNow"] is False for step in result["implementationTaskPlan"])
    assert all(step["writeNow"] is False for step in result["implementationTaskPlan"])
    assert all(step["createTaskNow"] is False for step in result["implementationTaskPlan"])
    assert result["futureChangeEnvelope"]["taskCreated"] is False
    assert result["futureChangeEnvelope"]["dependencyFileChanged"] is False
    assert result["futureChangeEnvelope"]["patchMaterialized"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_task_plan_context(result)


def test_real_sdk_dependency_implementation_task_plan_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_implementation_task_plan(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_implementation_task_plan_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["applyGateReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_task_plan_context(context)


def test_real_sdk_dependency_implementation_task_plan_cli_describe_and_plan_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-dependency-implementation-task-plan", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["planId"] == "real_sdk_dependency_implementation_task_plan"
    assert payload["data"]["readyForReviewedDependencyImplementationTask"] is False
    assert_safe_task_plan_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-implementation-task-plan", "plan", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["applyGateReady"] is False
    assert payload["data"]["implementationTaskPlanReady"] is False
    assert_safe_task_plan_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["applyGateReady"] is True
    assert payload["data"]["implementationTaskPlanReady"] is True
    assert payload["data"]["readyForReviewedDependencyImplementationTask"] is True
    assert payload["data"]["dependencyImplementationTaskCreated"] is False
    assert_safe_task_plan_context(payload["data"])


def test_real_sdk_dependency_implementation_task_plan_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-implementation-task-plan",
            "plan",
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
            "real-sdk-dependency-implementation-task-plan",
            "plan",
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
    context = payload["realSdkDependencyImplementationTaskPlanContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_task_plan_context(context)
