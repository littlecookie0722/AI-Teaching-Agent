import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyEnvGateRequest,
    build_real_sdk_dependency_env_gate_error_context,
    describe_real_sdk_dependency_env_gate,
    evaluate_real_sdk_dependency_env_gate,
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


def assert_safe_dependency_env_context(context):
    for key in [
        "dependencyInstallAllowed",
        "sdkDependencyInstallAllowed",
        "sdkDependencyInstallPlannedNow",
        "sdkDependencyInstalled",
        "sdkImported",
        "clientCreated",
        "packageVersionResolved",
        "packageHashResolved",
        "packageDownloaded",
        "dependencyLockfileChanged",
        "requirementsChanged",
        "pyprojectChanged",
        "envExampleChangeApplied",
        "providerContractChangeApplied",
        "runtimeContractChangeApplied",
        "secretInjectionApplied",
        "secretPresenceCheckDesigned",
        "secretPresenceChecked",
        "secretValueRead",
        "secretValueReturned",
        "networkAccessEnabledNow",
        "generatedContentCreated",
        "taskCreated",
        "reviewBypassed",
        "realCallAuthorized",
        "realLlmCalled",
        "secretsRead",
        "networkAccess",
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
    }
    payload.update(overrides)
    return RealSdkDependencyEnvGateRequest(**payload)


def confirmed_cli_args():
    return [
        "provider",
        "real-sdk-dependency-env",
        "check",
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
    ]


def test_real_sdk_dependency_env_gate_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-env-gate.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_env_gate"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["targetPackage"] == "openai"
    assert contract["allowedScope"]["provider"] == "openai"
    assert contract["allowedScope"]["operation"] == "generateJson"
    assert contract["allowedScope"]["promptId"] == "lab_generation_v0"
    assert contract["allowedScope"]["outputKind"] == "Lab"
    assert contract["allowedScope"]["generatedStatus"] == "WAITING_REVIEW"
    assert contract["requiredContext"]["enablementRequired"] is True
    assert contract["requiredContext"]["dependencyEnvChecklistPassed"] is False
    assert contract["requiredContext"]["readyForDependencyImplementationTask"] is False
    assert contract["requiredContext"]["dependencyInstallAllowed"] is False
    assert contract["requiredContext"]["secretPresenceChecked"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["sdkDependencyInstalled"] is False
    assert contract["safety"]["sdkImported"] is False
    assert contract["safety"]["packageDownloaded"] is False
    assert contract["safety"]["secretPresenceChecked"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "check_secret_presence" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_env_gate" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_env_gate_describe_is_design_only_and_safe():
    descriptor = describe_real_sdk_dependency_env_gate(root=ROOT)

    assert descriptor["gateId"] == "real_sdk_dependency_env_gate"
    assert descriptor["interfaceName"] == "LLMProvider"
    assert descriptor["mode"] == "MOCK_ONLY"
    assert descriptor["gateMode"] == "DEPENDENCY_ENV_DESIGN_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["supportedProvider"] == "openai"
    assert descriptor["targetPackage"] == "openai"
    assert descriptor["packageNameOnly"] is True
    assert descriptor["secretNameOnly"] is True
    assert descriptor["requiresEnablement"] is True
    assert descriptor["requiresMinimalImplementationShellReview"] is True
    assert descriptor["requiresSecretNonReadPolicy"] is True
    assert descriptor["generatedStatus"] == "WAITING_REVIEW"
    assert "future_dependency_implementation_task" in descriptor["pipeline"]
    assert_safe_dependency_env_context(descriptor)


def test_real_sdk_dependency_env_gate_default_check_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "dependency-env-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = evaluate_real_sdk_dependency_env_gate(
        RealSdkDependencyEnvGateRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["dependencyEnvChecklist"]}
    assert result["enablementReady"] is False
    assert result["dependencyEnvChecklistPassed"] is False
    assert result["readyForDependencyImplementationTask"] is False
    assert result["readyForEnvPresenceCheckDesign"] is False
    assert checklist["enablement_ready"]["passed"] is False
    assert checklist["sdk_package_review_confirmed"]["passed"] is False
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["plannedDependencyChanges"]
    assert result["plannedEnvChanges"]
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_dependency_env_context(result)


def test_real_sdk_dependency_env_gate_enablement_ready_but_missing_dependency_confirmations():
    request = confirmed_request(
        sdk_package_review_confirmed=False,
        sdk_version_pin_review_confirmed=False,
        dependency_hash_review_confirmed=False,
    )
    result = evaluate_real_sdk_dependency_env_gate(request, root=ROOT)
    checklist = {item["id"]: item for item in result["dependencyEnvChecklist"]}

    assert result["enablementReady"] is True
    assert result["enablementSummary"]["readyForRealSdkImplementationTask"] is True
    assert result["dependencyEnvChecklistPassed"] is False
    assert result["readyForDependencyImplementationTask"] is False
    assert checklist["enablement_ready"]["passed"] is True
    assert checklist["sdk_package_review_confirmed"]["passed"] is False
    assert checklist["sdk_version_pin_review_confirmed"]["passed"] is False
    assert checklist["dependency_hash_review_confirmed"]["passed"] is False
    assert_safe_dependency_env_context(result)


def test_real_sdk_dependency_env_gate_all_confirmations_ready_but_still_no_real_action():
    result = evaluate_real_sdk_dependency_env_gate(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["dependencyEnvChecklist"]}

    assert result["enablementReady"] is True
    assert result["enablementSummary"]["switchDesignReady"] is True
    assert result["dependencyEnvChecklistPassed"] is True
    assert result["readyForDependencyImplementationTask"] is True
    assert result["readyForEnvPresenceCheckDesign"] is True
    assert checklist["minimal_impl_review_confirmed"]["passed"] is True
    assert checklist["secret_non_read_policy_confirmed"]["passed"] is True
    assert all(item["appliedNow"] is False for item in result["plannedDependencyChanges"])
    assert all(item["appliedNow"] is False for item in result["plannedEnvChanges"])
    assert result["plannedDependencyChanges"][0]["packageNameOnly"] is True
    assert result["plannedEnvChanges"][0]["secretNameOnly"] is True
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_dependency_env_context(result)


def test_real_sdk_dependency_env_gate_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        evaluate_real_sdk_dependency_env_gate(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_env_gate_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["enablementReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_dependency_env_context(context)


def test_real_sdk_dependency_env_gate_cli_describe_and_check_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-dependency-env", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["gateId"] == "real_sdk_dependency_env_gate"
    assert payload["data"]["dependencyEnvChecklistPassed"] is False
    assert_safe_dependency_env_context(payload["data"])

    exit_code, payload = run_cli(["provider", "real-sdk-dependency-env", "check", "--provider", "openai"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["enablementReady"] is False
    assert payload["data"]["dependencyEnvChecklistPassed"] is False
    assert_safe_dependency_env_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["enablementReady"] is True
    assert payload["data"]["dependencyEnvChecklistPassed"] is True
    assert payload["data"]["readyForDependencyImplementationTask"] is True
    assert_safe_dependency_env_context(payload["data"])


def test_real_sdk_dependency_env_gate_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-env", "check", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-env", "check", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkDependencyEnvGateContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_dependency_env_context(context)
