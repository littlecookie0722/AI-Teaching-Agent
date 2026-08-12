import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyInstallPlanRequest,
    build_real_sdk_dependency_install_plan,
    build_real_sdk_dependency_install_plan_error_context,
    describe_real_sdk_dependency_install_plan,
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


def assert_safe_install_plan_context(context):
    for key in [
        "dependencyInstallAllowed",
        "dependencyInstallCommandGenerated",
        "dependencyInstallExecuted",
        "sdkDependencyInstallAllowed",
        "sdkDependencyInstalled",
        "packageVersionResolved",
        "packageHashResolved",
        "packageDownloaded",
        "dependencyLockfileChanged",
        "requirementsChanged",
        "pyprojectChanged",
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
    }
    payload.update(overrides)
    return RealSdkDependencyInstallPlanRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-sdk-dependency-install-plan",
        "plan",
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
    ]


def test_real_sdk_dependency_install_plan_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-install-plan.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["planId"] == "real_sdk_dependency_install_plan"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["targetPackage"] == "openai"
    assert contract["allowedScope"]["provider"] == "openai"
    assert contract["allowedScope"]["operation"] == "generateJson"
    assert contract["allowedScope"]["promptId"] == "lab_generation_v0"
    assert contract["allowedScope"]["outputKind"] == "Lab"
    assert contract["allowedScope"]["generatedStatus"] == "WAITING_REVIEW"
    assert contract["requiredContext"]["dependencyEnvGateRequired"] is True
    assert contract["requiredContext"]["dependencyEnvGateReady"] is False
    assert contract["requiredContext"]["installPlanChecklistPassed"] is False
    assert contract["requiredContext"]["readyForDependencyInstallImplementationReview"] is False
    assert contract["requiredContext"]["dependencyInstallCommandGenerated"] is False
    assert contract["requiredContext"]["dependencyInstallExecuted"] is False
    assert contract["requiredContext"]["dependencyLockfileChanged"] is False
    assert contract["requiredContext"]["secretPresenceChecked"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["sdkDependencyInstalled"] is False
    assert contract["safety"]["packageVersionResolved"] is False
    assert contract["safety"]["packageHashResolved"] is False
    assert contract["safety"]["packageDownloaded"] is False
    assert contract["safety"]["dependencyLockfileChanged"] is False
    assert contract["safety"]["secretPresenceChecked"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "generate_install_command" in contract["blockedOperations"]
    assert "modify_dependency_lockfile" in contract["blockedOperations"]
    assert "check_secret_presence" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_install_plan" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_install_plan_describe_is_draft_only_and_safe():
    descriptor = describe_real_sdk_dependency_install_plan(root=ROOT)

    assert descriptor["planId"] == "real_sdk_dependency_install_plan"
    assert descriptor["interfaceName"] == "LLMProvider"
    assert descriptor["mode"] == "MOCK_ONLY"
    assert descriptor["planMode"] == "DEPENDENCY_INSTALL_DRAFT_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["supportedProvider"] == "openai"
    assert descriptor["targetPackage"] == "openai"
    assert descriptor["requiresDependencyEnvGate"] is True
    assert descriptor["requiresPackageManagerReview"] is True
    assert descriptor["generatedStatus"] == "WAITING_REVIEW"
    assert "future_dependency_install_implementation_task" in descriptor["pipeline"]
    assert_safe_install_plan_context(descriptor)


def test_real_sdk_dependency_install_plan_default_plan_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "dependency-install-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_install_plan(
        RealSdkDependencyInstallPlanRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["installPlanChecklist"]}
    assert result["dependencyEnvGateReady"] is False
    assert result["dependencyEnvGateSummary"]["dependencyEnvChecklistPassed"] is False
    assert result["installPlanChecklistPassed"] is False
    assert result["readyForDependencyInstallImplementationReview"] is False
    assert checklist["dependency_env_gate_ready"]["passed"] is False
    assert checklist["package_manager_review_confirmed"]["passed"] is False
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["proposedDependencySpec"]["packageName"] == "openai"
    assert result["proposedDependencySpec"]["exactVersionKnown"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_install_plan_context(result)


def test_real_sdk_dependency_install_plan_gate_ready_but_missing_plan_confirmations():
    request = confirmed_request(
        package_manager_review_confirmed=False,
        lockfile_strategy_review_confirmed=False,
    )
    result = build_real_sdk_dependency_install_plan(request, root=ROOT)
    checklist = {item["id"]: item for item in result["installPlanChecklist"]}

    assert result["dependencyEnvGateReady"] is True
    assert result["dependencyEnvGateSummary"]["readyForDependencyImplementationTask"] is True
    assert result["installPlanChecklistPassed"] is False
    assert result["readyForDependencyInstallImplementationReview"] is False
    assert checklist["dependency_env_gate_ready"]["passed"] is True
    assert checklist["package_manager_review_confirmed"]["passed"] is False
    assert checklist["lockfile_strategy_review_confirmed"]["passed"] is False
    assert_safe_install_plan_context(result)


def test_real_sdk_dependency_install_plan_all_confirmations_ready_but_still_no_install_action():
    result = build_real_sdk_dependency_install_plan(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["installPlanChecklist"]}

    assert result["dependencyEnvGateReady"] is True
    assert result["dependencyEnvGateSummary"]["dependencyEnvChecklistPassed"] is True
    assert result["installPlanChecklistPassed"] is True
    assert result["readyForDependencyInstallImplementationReview"] is True
    assert checklist["hash_verification_strategy_confirmed"]["passed"] is True
    assert all(item["appliedNow"] is False for item in result["plannedFiles"])
    assert result["rollbackPlan"]["appliedNow"] is False
    assert result["proposedDependencySpec"]["packageNameOnly"] is True
    assert result["proposedDependencySpec"]["exactVersionKnown"] is False
    assert result["proposedDependencySpec"]["resolvedNow"] is False
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_install_plan_context(result)


def test_real_sdk_dependency_install_plan_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_install_plan(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_install_plan_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["dependencyEnvGateReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_install_plan_context(context)


def test_real_sdk_dependency_install_plan_cli_describe_and_plan_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-dependency-install-plan", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["planId"] == "real_sdk_dependency_install_plan"
    assert payload["data"]["readyForDependencyInstallImplementationReview"] is False
    assert_safe_install_plan_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-plan", "plan", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["dependencyEnvGateReady"] is False
    assert payload["data"]["installPlanChecklistPassed"] is False
    assert_safe_install_plan_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["dependencyEnvGateReady"] is True
    assert payload["data"]["installPlanChecklistPassed"] is True
    assert payload["data"]["readyForDependencyInstallImplementationReview"] is True
    assert_safe_install_plan_context(payload["data"])


def test_real_sdk_dependency_install_plan_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-plan", "plan", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-install-plan", "plan", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkDependencyInstallPlanContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_install_plan_context(context)
