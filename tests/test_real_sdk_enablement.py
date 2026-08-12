import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkEnablementRequest,
    build_real_sdk_enablement_error_context,
    describe_real_sdk_enablement,
    evaluate_real_sdk_enablement,
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


def assert_safe_enablement_context(context):
    for key in [
        "implementationAllowed",
        "realCallAuthorized",
        "sdkDependencyInstalled",
        "sdkImported",
        "clientCreated",
        "providerContractChangeApplied",
        "runtimeContractChangeApplied",
        "secretInjectionApplied",
        "secretPresenceChecked",
        "secretValueRead",
        "secretValueReturned",
        "networkAccessEnabledNow",
        "generatedContentCreated",
        "taskCreated",
        "reviewBypassed",
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
    }
    payload.update(overrides)
    return RealSdkEnablementRequest(**payload)


def test_real_sdk_enablement_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-enablement.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["enablementId"] == "real_sdk_enablement"
    assert contract["activeProvider"] == "mock"
    assert contract["allowedScope"]["operation"] == "generateJson"
    assert contract["allowedScope"]["promptId"] == "lab_generation_v0"
    assert contract["allowedScope"]["outputKind"] == "Lab"
    assert contract["allowedScope"]["generatedStatus"] == "WAITING_REVIEW"
    assert contract["requiredContext"]["blueprintRequired"] is True
    assert contract["requiredContext"]["switchDesignReady"] is False
    assert contract["requiredContext"]["implementationAllowed"] is False
    assert contract["requiredContext"]["realCallAuthorized"] is False
    assert contract["requiredContext"]["secretPresenceChecked"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["sdkDependencyInstalled"] is False
    assert contract["safety"]["sdkImported"] is False
    assert contract["safety"]["clientCreated"] is False
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert "modify_runtime_contract_now" in contract["blockedOperations"]
    assert "enable_provider_contract_now" in contract["blockedOperations"]
    assert "inject_secret_now" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_enablement" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_enablement_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_enablement(root=ROOT)

    assert descriptor["enablementId"] == "real_sdk_enablement"
    assert descriptor["mode"] == "MOCK_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresBlueprint"] is True
    assert descriptor["requiresSdkDependencyReview"] is True
    assert descriptor["requiresProviderContractReview"] is True
    assert descriptor["requiresRuntimeContractReview"] is True
    assert descriptor["requiresSecretInjectionReview"] is True
    assert descriptor["requiresNetworkAccessReview"] is True
    assert descriptor["requiresRollbackPlan"] is True
    assert descriptor["generatedStatus"] == "WAITING_REVIEW"
    assert descriptor["switchDesignReady"] is False
    assert "future_real_sdk_implementation_task" in descriptor["pipeline"]
    assert_safe_enablement_context(descriptor)


def test_real_sdk_enablement_default_check_is_blocked_without_confirmations_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "enablement-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = evaluate_real_sdk_enablement(
        RealSdkEnablementRequest(provider_id="openai", payload={"apiKey": fake_key}),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["enablementChecklist"]}
    assert result["blueprintReady"] is False
    assert result["enablementChecklistPassed"] is False
    assert result["switchDesignReady"] is False
    assert checklist["blueprint_ready"]["passed"] is False
    assert checklist["sdk_dependency_review_confirmed"]["passed"] is False
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_enablement_context(result)


def test_real_sdk_enablement_all_confirmations_ready_but_still_does_not_authorize_real_call():
    result = evaluate_real_sdk_enablement(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["enablementChecklist"]}

    assert result["blueprintReady"] is True
    assert result["blueprintSummary"]["blueprintReady"] is True
    assert result["enablementChecklistPassed"] is True
    assert result["switchDesignReady"] is True
    assert result["readyForRuntimeChangeReview"] is True
    assert result["readyForRealSdkImplementationTask"] is True
    assert checklist["blueprint_ready"]["passed"] is True
    assert checklist["network_access_review_confirmed"]["passed"] is True
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["plannedSwitches"]
    assert all(item["appliedNow"] is False for item in result["plannedSwitches"])
    assert_safe_enablement_context(result)


def test_real_sdk_enablement_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        evaluate_real_sdk_enablement(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_enablement_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["blueprintReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_enablement_context(context)


def test_real_sdk_enablement_cli_describe_and_check_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-enablement", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["enablementId"] == "real_sdk_enablement"
    assert payload["data"]["switchDesignReady"] is False
    assert_safe_enablement_context(payload["data"])

    exit_code, payload = run_cli(["provider", "real-sdk-enablement", "check", "--provider", "openai"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["blueprintReady"] is False
    assert payload["data"]["switchDesignReady"] is False
    assert_safe_enablement_context(payload["data"])

    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-enablement",
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
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["blueprintReady"] is True
    assert payload["data"]["switchDesignReady"] is True
    assert payload["data"]["readyForRealSdkImplementationTask"] is True
    assert_safe_enablement_context(payload["data"])


def test_real_sdk_enablement_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-enablement", "check", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-enablement", "check", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkEnablementContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_enablement_context(context)
