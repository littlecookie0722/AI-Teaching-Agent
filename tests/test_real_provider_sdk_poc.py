import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealProviderSdkPocRequest,
    build_real_provider_sdk_poc_error_context,
    describe_real_provider_sdk_poc,
    invoke_real_provider_sdk_poc,
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


def assert_safe_poc_context(context):
    for key in [
        "sdkPocEnabled",
        "sdkPocPassed",
        "sdkDependencyInstalled",
        "sdkImported",
        "clientCreated",
        "providerContractChangeApplied",
        "runtimeContractChangeApplied",
        "secretPresenceChecked",
        "secretValueRead",
        "secretValueReturned",
        "generatedContentCreated",
        "taskCreated",
        "reviewBypassed",
        "realCallAuthorized",
        "realLlmCalled",
        "secretsRead",
        "networkAccess",
        "networkAccessEnabledNow",
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
    }
    payload.update(overrides)
    return RealProviderSdkPocRequest(**payload)


def test_real_provider_sdk_poc_contract_is_mock_only_and_local():
    contract = load_json("providers/real-provider-sdk-poc.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["pocId"] == "real_provider_sdk_poc"
    assert contract["activeProvider"] == "mock"
    assert contract["allowedScope"]["operation"] == "generateJson"
    assert contract["allowedScope"]["promptId"] == "lab_generation_v0"
    assert contract["allowedScope"]["outputKind"] == "Lab"
    assert contract["allowedScope"]["generatedStatus"] == "WAITING_REVIEW"
    assert contract["requiredContext"]["blueprintRequired"] is True
    assert contract["requiredContext"]["sdkPocEnabled"] is False
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
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "import_real_sdk" in contract["blockedOperations"]
    assert "check_secret_presence" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_provider_sdk_poc" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_provider_sdk_poc_describe_is_disabled_and_safe():
    descriptor = describe_real_provider_sdk_poc(root=ROOT)

    assert descriptor["pocId"] == "real_provider_sdk_poc"
    assert descriptor["interfaceName"] == "LLMProvider"
    assert descriptor["mode"] == "MOCK_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["sdkPocEnabled"] is False
    assert descriptor["requiresBlueprint"] is True
    assert descriptor["requiresApprovalGate"] is True
    assert descriptor["requiresRuntimeGuard"] is True
    assert descriptor["requiresHumanReview"] is True
    assert descriptor["generatedStatus"] == "WAITING_REVIEW"
    assert descriptor["supportedOperation"] == "generateJson"
    assert descriptor["llmPocScope"] == "lab_generate_from_source_only"
    assert "real_llm_sdk_task_blueprint" in descriptor["pipeline"]
    assert "sdk_call_disabled" in descriptor["pipeline"]

    for key in [
        "sdkDependencyInstalled",
        "sdkImported",
        "clientCreated",
        "secretPresenceChecked",
        "secretValueRead",
        "secretValueReturned",
        "realCallAuthorized",
        "realLlmCalled",
        "secretsRead",
        "networkAccess",
        "generatedContentCreated",
        "taskCreated",
        "reviewBypassed",
        "autoPublishAllowed",
        "realPublish",
    ]:
        assert descriptor[key] is False


def test_real_provider_sdk_poc_requires_blueprint_before_adapter_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "sdk-poc-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    request = RealProviderSdkPocRequest(
        provider_id="openai",
        payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
    )

    try:
        invoke_real_provider_sdk_poc(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_LLM_SDK_BLUEPRINT_REQUIRED"
        context = build_real_provider_sdk_poc_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    serialized = json.dumps(context, ensure_ascii=False)
    assert context["errorCode"] == "REAL_LLM_SDK_BLUEPRINT_REQUIRED"
    assert context["blueprintRequired"] is True
    assert context["blueprintReady"] is False
    assert context["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_poc_context(context)
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized


def test_real_provider_sdk_poc_confirmed_blueprint_still_requires_explicit_opt_in():
    request = confirmed_request()

    try:
        invoke_real_provider_sdk_poc(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_OPT_IN_REQUIRED"
        context = build_real_provider_sdk_poc_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "REAL_PROVIDER_OPT_IN_REQUIRED"
    assert context["blueprintReady"] is True
    assert context["blueprintSummary"]["blueprintReady"] is True
    assert context["blueprintSummary"]["implementationAllowed"] is False
    assert context["blueprintSummary"]["realCallAuthorized"] is False
    assert context["explicitOptIn"] is False
    assert context["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_poc_context(context)


def test_real_provider_sdk_poc_confirmed_and_opt_in_still_blocked_by_provider_contract():
    request = confirmed_request(explicit_opt_in=True)

    try:
        invoke_real_provider_sdk_poc(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_DISABLED"
        context = build_real_provider_sdk_poc_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "REAL_PROVIDER_DISABLED"
    assert context["blueprintReady"] is True
    assert context["blueprintSummary"]["blueprintReady"] is True
    assert context["explicitOptIn"] is True
    assert context["providerEnabled"] is False
    assert context["providerContractEnabled"] is False
    assert context["generatedStatus"] == "WAITING_REVIEW"
    assert_safe_poc_context(context)


def test_real_provider_sdk_poc_invalid_scope_keeps_safe_context():
    request = confirmed_request(output_kind="Exam")

    try:
        invoke_real_provider_sdk_poc(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_provider_sdk_poc_error_context(exc, request=request, root=ROOT)
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["blueprintReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_poc_context(context)


def test_real_provider_sdk_poc_cli_describe_and_generate_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-poc", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["pocId"] == "real_provider_sdk_poc"
    assert payload["data"]["sdkPocEnabled"] is False

    exit_code, payload = run_cli(["provider", "real-sdk-poc", "generate-json", "--provider", "openai"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_LLM_SDK_BLUEPRINT_REQUIRED"
    context = payload["realProviderSdkPocContext"]
    assert context["blueprintReady"] is False
    assert_safe_poc_context(context)

    confirmed_args = [
        "provider",
        "real-sdk-poc",
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
    ]
    exit_code, payload = run_cli(confirmed_args, capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_PROVIDER_OPT_IN_REQUIRED"
    assert payload["realProviderSdkPocContext"]["blueprintReady"] is True
    assert_safe_poc_context(payload["realProviderSdkPocContext"])

    exit_code, payload = run_cli([*confirmed_args, "--explicit-opt-in"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_PROVIDER_DISABLED"
    assert payload["realProviderSdkPocContext"]["blueprintReady"] is True
    assert payload["realProviderSdkPocContext"]["explicitOptIn"] is True
    assert_safe_poc_context(payload["realProviderSdkPocContext"])


def test_real_provider_sdk_poc_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-poc", "generate-json", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-poc", "generate-json", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realProviderSdkPocContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_poc_context(context)
