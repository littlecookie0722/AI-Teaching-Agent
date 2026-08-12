import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkMinimalImplRequest,
    build_real_sdk_minimal_impl_error_context,
    describe_real_sdk_minimal_impl,
    invoke_real_sdk_minimal_impl,
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


def assert_safe_impl_context(context):
    for key in [
        "implementationAllowed",
        "sdkImplementationEnabled",
        "sdkImplementationPassed",
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
    }
    payload.update(overrides)
    return RealSdkMinimalImplRequest(**payload)


def test_real_sdk_minimal_impl_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-minimal-impl.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["implementationId"] == "real_sdk_minimal_impl"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["allowedScope"]["provider"] == "openai"
    assert contract["allowedScope"]["operation"] == "generateJson"
    assert contract["allowedScope"]["promptId"] == "lab_generation_v0"
    assert contract["allowedScope"]["outputKind"] == "Lab"
    assert contract["allowedScope"]["generatedStatus"] == "WAITING_REVIEW"
    assert contract["requiredContext"]["enablementRequired"] is True
    assert contract["requiredContext"]["sdkImplementationEnabled"] is False
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
    assert "import_real_sdk" in contract["blockedOperations"]
    assert "check_secret_presence" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert "bypass_enablement" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_minimal_impl" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_minimal_impl_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_minimal_impl(root=ROOT)

    assert descriptor["implementationId"] == "real_sdk_minimal_impl"
    assert descriptor["interfaceName"] == "LLMProvider"
    assert descriptor["mode"] == "MOCK_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["supportedProvider"] == "openai"
    assert descriptor["requiresEnablement"] is True
    assert descriptor["requiresExplicitImplementationOptIn"] is True
    assert descriptor["requiresProviderContractChange"] is True
    assert descriptor["requiresRuntimeContractChange"] is True
    assert descriptor["generatedStatus"] == "WAITING_REVIEW"
    assert descriptor["supportedOperation"] == "generateJson"
    assert descriptor["allowedScope"] == "lab_generate_from_source_only"
    assert "real_sdk_enablement_checklist" in descriptor["pipeline"]
    assert "network_call_disabled" in descriptor["pipeline"]
    assert_safe_impl_context(descriptor)


def test_real_sdk_minimal_impl_requires_enablement_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "minimal-impl-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    request = RealSdkMinimalImplRequest(
        provider_id="openai",
        payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
    )

    try:
        invoke_real_sdk_minimal_impl(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_SDK_ENABLEMENT_REQUIRED"
        context = build_real_sdk_minimal_impl_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    serialized = json.dumps(context, ensure_ascii=False)
    assert context["errorCode"] == "REAL_SDK_ENABLEMENT_REQUIRED"
    assert context["enablementRequired"] is True
    assert context["enablementReady"] is False
    assert context["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_impl_context(context)
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized


def test_real_sdk_minimal_impl_confirmed_enablement_requires_explicit_implementation_opt_in():
    request = confirmed_request()

    try:
        invoke_real_sdk_minimal_impl(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_SDK_IMPLEMENTATION_OPT_IN_REQUIRED"
        context = build_real_sdk_minimal_impl_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "REAL_SDK_IMPLEMENTATION_OPT_IN_REQUIRED"
    assert context["enablementReady"] is True
    assert context["switchDesignReady"] is True
    assert context["readyForRealSdkImplementationTask"] is True
    assert context["enablementSummary"]["switchDesignReady"] is True
    assert context["enablementSummary"]["implementationAllowed"] is False
    assert context["enablementSummary"]["realCallAuthorized"] is False
    assert context["explicitImplementationOptIn"] is False
    assert context["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_impl_context(context)


def test_real_sdk_minimal_impl_confirmed_and_opt_in_still_disabled():
    request = confirmed_request(explicit_implementation_opt_in=True)

    try:
        invoke_real_sdk_minimal_impl(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_SDK_IMPLEMENTATION_DISABLED"
        context = build_real_sdk_minimal_impl_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "REAL_SDK_IMPLEMENTATION_DISABLED"
    assert context["enablementReady"] is True
    assert context["enablementSummary"]["switchDesignReady"] is True
    assert context["explicitImplementationOptIn"] is True
    assert context["providerEnabled"] is False
    assert context["providerContractEnabled"] is False
    assert context["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_impl_context(context)


def test_real_sdk_minimal_impl_invalid_scope_keeps_safe_context():
    request = confirmed_request(output_kind="Exam")

    try:
        invoke_real_sdk_minimal_impl(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_minimal_impl_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["enablementReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_impl_context(context)


def test_real_sdk_minimal_impl_cli_describe_and_generate_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-impl", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["implementationId"] == "real_sdk_minimal_impl"
    assert payload["data"]["sdkImplementationEnabled"] is False
    assert_safe_impl_context(payload["data"])

    exit_code, payload = run_cli(["provider", "real-sdk-impl", "generate-json", "--provider", "openai"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_SDK_ENABLEMENT_REQUIRED"
    context = payload["realSdkMinimalImplContext"]
    assert context["enablementReady"] is False
    assert_safe_impl_context(context)

    confirmed_args = [
        "provider",
        "real-sdk-impl",
        "generate-json",
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
    ]
    exit_code, payload = run_cli(confirmed_args, capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_SDK_IMPLEMENTATION_OPT_IN_REQUIRED"
    assert payload["realSdkMinimalImplContext"]["enablementReady"] is True
    assert_safe_impl_context(payload["realSdkMinimalImplContext"])

    exit_code, payload = run_cli([*confirmed_args, "--explicit-implementation-opt-in"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_SDK_IMPLEMENTATION_DISABLED"
    assert payload["realSdkMinimalImplContext"]["enablementReady"] is True
    assert payload["realSdkMinimalImplContext"]["explicitImplementationOptIn"] is True
    assert_safe_impl_context(payload["realSdkMinimalImplContext"])


def test_real_sdk_minimal_impl_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-impl", "generate-json", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-impl", "generate-json", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkMinimalImplContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_impl_context(context)
