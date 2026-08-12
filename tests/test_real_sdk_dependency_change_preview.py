import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyChangePreviewRequest,
    build_real_sdk_dependency_change_preview,
    build_real_sdk_dependency_change_preview_error_context,
    describe_real_sdk_dependency_change_preview,
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


def assert_safe_change_preview_context(context):
    for key in [
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
        "approval_ref": "APPROVAL-001",
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
    }
    payload.update(overrides)
    return RealSdkDependencyChangePreviewRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-sdk-dependency-change-preview",
        "preview",
        "--provider",
        "openai",
        "--approval-ref",
        "APPROVAL-001",
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
    ]


def test_real_sdk_dependency_change_preview_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-change-preview.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["previewId"] == "real_sdk_dependency_change_preview"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["targetPackage"] == "openai"
    assert contract["requiredContext"]["installerAuditRequired"] is True
    assert contract["requiredContext"]["installerAuditReady"] is False
    assert contract["requiredContext"]["dependencyChangePreviewOnly"] is True
    assert contract["requiredContext"]["dependencyFileChanged"] is False
    assert contract["requiredContext"]["lockfileDiffGenerated"] is False
    assert contract["requiredContext"]["dependencyDiffGenerated"] is False
    assert "write_dependency_manifest" in contract["blockedOperations"]
    assert "generate_dependency_diff" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_change_preview" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_change_preview_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_change_preview(root=ROOT)

    assert descriptor["previewId"] == "real_sdk_dependency_change_preview"
    assert descriptor["previewMode"] == "DEPENDENCY_CHANGE_PREVIEW_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresInstallerAudit"] is True
    assert descriptor["dependencyChangePreviewOnly"] is True
    assert "future_dependency_change_implementation_task" in descriptor["pipeline"]
    assert_safe_change_preview_context(descriptor)


def test_real_sdk_dependency_change_preview_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "change-preview-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_change_preview(
        RealSdkDependencyChangePreviewRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["changePreviewChecklist"]}
    assert result["installerAuditReady"] is False
    assert result["changePreviewChecklistPassed"] is False
    assert result["readyForDependencyChangeImplementationTask"] is False
    assert checklist["installer_audit_ready"]["passed"] is False
    assert checklist["manifest_preview_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_change_preview_context(result)


def test_real_sdk_dependency_change_preview_audit_ready_but_missing_preview_confirmations():
    request = confirmed_request(preview_scope_confirmed=False, manifest_preview_confirmed=False)
    result = build_real_sdk_dependency_change_preview(request, root=ROOT)
    checklist = {item["id"]: item for item in result["changePreviewChecklist"]}

    assert result["installerAuditReady"] is True
    assert result["installerAuditSummary"]["readyForInstallerImplementationTask"] is True
    assert result["changePreviewChecklistPassed"] is False
    assert result["readyForDependencyChangeImplementationTask"] is False
    assert checklist["installer_audit_ready"]["passed"] is True
    assert checklist["preview_scope_confirmed"]["passed"] is False
    assert checklist["manifest_preview_confirmed"]["passed"] is False
    assert_safe_change_preview_context(result)


def test_real_sdk_dependency_change_preview_all_confirmations_ready_but_still_no_file_or_diff():
    result = build_real_sdk_dependency_change_preview(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["changePreviewChecklist"]}

    assert result["installerAuditReady"] is True
    assert result["changePreviewChecklistPassed"] is True
    assert result["readyForDependencyChangeImplementationTask"] is True
    assert result["dependencyChangePreviewReady"] is True
    assert checklist["no_file_write_confirmed"]["passed"] is True
    assert all(item["writeNow"] is False for item in result["manifestPreview"])
    assert result["lockfilePreview"]["lockfileGeneratedNow"] is False
    assert result["lockfilePreview"]["lockfileDiffGeneratedNow"] is False
    assert result["diffPreviewPolicy"]["diffGeneratedNow"] is False
    assert result["diffPreviewPolicy"]["diffArtifactWritten"] is False
    assert result["rollbackPreview"]["rollbackDiffGenerated"] is False
    assert_safe_change_preview_context(result)


def test_real_sdk_dependency_change_preview_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_change_preview(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_change_preview_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["installerAuditReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_change_preview_context(context)


def test_real_sdk_dependency_change_preview_cli_describe_and_preview_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-dependency-change-preview", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["previewId"] == "real_sdk_dependency_change_preview"
    assert payload["data"]["readyForDependencyChangeImplementationTask"] is False
    assert_safe_change_preview_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-change-preview", "preview", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installerAuditReady"] is False
    assert payload["data"]["changePreviewChecklistPassed"] is False
    assert_safe_change_preview_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["installerAuditReady"] is True
    assert payload["data"]["changePreviewChecklistPassed"] is True
    assert payload["data"]["readyForDependencyChangeImplementationTask"] is True
    assert_safe_change_preview_context(payload["data"])


def test_real_sdk_dependency_change_preview_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-change-preview", "preview", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-change-preview", "preview", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkDependencyChangePreviewContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_change_preview_context(context)
