import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmPocAdapterRequest,
    build_real_llm_poc_adapter_error_context,
    describe_real_llm_poc_adapter,
    invoke_real_llm_poc_adapter,
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


def test_real_llm_poc_adapter_contract_is_mock_only_and_local():
    contract = load_json("providers/real-llm-poc-adapter.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["adapterId"] == "real_llm_poc_adapter"
    assert contract["activeProvider"] == "mock"
    assert contract["requiredContext"]["adapterEnabled"] is False
    assert contract["requiredContext"]["readyForRealProvider"] is False
    assert contract["requiredContext"]["sdkImported"] is False
    assert contract["requiredContext"]["clientCreated"] is False
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert contract["requiredContext"]["secretsRead"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert "provider_runtime_guard" in {step["id"] for step in contract["pipeline"]}
    assert "real_provider_preflight" in {step["id"] for step in contract["pipeline"]}
    assert "sdk_call_disabled" in {step["id"] for step in contract["pipeline"]}
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_llm_poc_adapter" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_llm_poc_adapter_describe_is_disabled_and_safe():
    descriptor = describe_real_llm_poc_adapter(root=ROOT)

    assert descriptor["adapterId"] == "real_llm_poc_adapter"
    assert descriptor["mode"] == "MOCK_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["adapterEnabled"] is False
    assert descriptor["supportedOperation"] == "generateJson"
    assert descriptor["sdkImported"] is False
    assert descriptor["clientCreated"] is False
    assert descriptor["secretValueReturned"] is False
    assert descriptor["realLlmCalled"] is False
    assert descriptor["secretsRead"] is False
    assert descriptor["networkAccess"] is False
    assert {provider["providerId"] for provider in descriptor["providers"]} == {"openai", "anthropic", "local"}
    assert all(provider["enabled"] is False for provider in descriptor["providers"])


def test_real_llm_poc_adapter_requires_explicit_opt_in_after_runtime_guard():
    fake_key = "sk-" + "poc-hidden"
    request = RealLlmPocAdapterRequest(provider_id="openai", payload={"apiKey": fake_key})

    try:
        invoke_real_llm_poc_adapter(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_OPT_IN_REQUIRED"
        context = build_real_llm_poc_adapter_error_context(exc, request=request, root=ROOT)
        assert context["adapterId"] == "real_llm_poc_adapter"
        assert context["providerId"] == "openai"
        assert context["adapterPassed"] is False
        assert context["readyForRealProvider"] is False
        assert context["sdkImported"] is False
        assert context["clientCreated"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
        assert context["generatedContentCreated"] is False
        assert context["taskCreated"] is False
        assert fake_key not in json.dumps(context)
    else:
        raise AssertionError("expected ProviderError")


def test_real_llm_poc_adapter_opt_in_still_blocked_by_provider_contract():
    request = RealLlmPocAdapterRequest(provider_id="openai", explicit_opt_in=True)

    try:
        invoke_real_llm_poc_adapter(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_DISABLED"
        context = build_real_llm_poc_adapter_error_context(exc, request=request, root=ROOT)
        assert context["explicitOptIn"] is True
        assert context["providerEnabled"] is False
        assert context["adapterEnabled"] is False
        assert context["readyForRealProvider"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
        assert context["secretValueReturned"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_real_llm_poc_adapter_runtime_guard_fails_before_preflight_scope():
    request = RealLlmPocAdapterRequest(provider_id="openai", explicit_opt_in=True, timeout_seconds=0)

    try:
        invoke_real_llm_poc_adapter(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "timeoutSeconds"
        context = build_real_llm_poc_adapter_error_context(exc, request=request, root=ROOT)
        assert context["adapterPassed"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_real_llm_poc_adapter_cli_describe_and_generate_fail_safely(capsys):
    exit_code, payload = run_cli(["provider", "real-poc-adapter", "describe"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["adapterId"] == "real_llm_poc_adapter"
    assert payload["data"]["adapterEnabled"] is False
    assert payload["data"]["realLlmCalled"] is False

    exit_code, payload = run_cli(["provider", "real-poc-adapter", "generate-json", "--provider", "openai"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "REAL_PROVIDER_OPT_IN_REQUIRED"
    assert payload["realLlmPocAdapterContext"]["adapterPassed"] is False
    assert payload["realLlmPocAdapterContext"]["realLlmCalled"] is False
    assert payload["realLlmPocAdapterContext"]["secretsRead"] is False
    assert payload["realLlmPocAdapterContext"]["networkAccess"] is False

    exit_code, payload = run_cli(
        ["provider", "real-poc-adapter", "generate-json", "--provider", "openai", "--explicit-opt-in"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_PROVIDER_DISABLED"
    assert payload["realLlmPocAdapterContext"]["explicitOptIn"] is True
    assert payload["realLlmPocAdapterContext"]["providerEnabled"] is False
    assert payload["realLlmPocAdapterContext"]["realLlmCalled"] is False


def test_real_llm_poc_adapter_cli_rejects_bad_payload(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-poc-adapter", "generate-json", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"
