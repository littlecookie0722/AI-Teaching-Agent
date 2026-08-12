import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealProviderShellRequest,
    build_real_provider_shell_error_context,
    build_real_provider_shell_registry,
    invoke_real_provider_shell,
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


def test_real_provider_shell_contract_is_mock_only_and_local():
    contract = load_json("providers/real-provider-shell.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["requiredContext"]["defaultProvider"] == "mock"
    assert contract["requiredContext"]["enabled"] is False
    assert contract["requiredContext"]["shellImplementationStatus"] == "disabled_shell"
    assert contract["requiredContext"]["sdkImported"] is False
    assert contract["requiredContext"]["clientCreated"] is False
    assert contract["requiredContext"]["generationOperationsEnabled"] is False
    assert contract["requiredContext"]["realProviderRoutingAllowed"] is False
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert contract["requiredContext"]["secretsRead"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert contract["requiredContext"]["secretValueReturned"] is False
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_provider_shell" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_provider_shell_registry_declares_disabled_classes_without_sdk_or_secret_reads():
    registry = build_real_provider_shell_registry(root=ROOT)
    providers = {provider["providerId"]: provider for provider in registry["providers"]}

    assert registry["mode"] == "MOCK_ONLY"
    assert registry["defaultProvider"] == "mock"
    assert registry["realProviderRoutingAllowed"] is False
    assert registry["realLlmCalled"] is False
    assert registry["secretsRead"] is False
    assert registry["networkAccess"] is False
    assert set(providers) == {"openai", "anthropic", "local"}
    assert providers["openai"]["className"] == "OpenAIProvider"
    assert providers["anthropic"]["className"] == "AnthropicProvider"
    assert providers["local"]["className"] == "LocalModelProvider"
    assert providers["openai"]["secretEnv"] == "OPENAI_API_KEY"
    assert providers["anthropic"]["secretEnv"] == "ANTHROPIC_API_KEY"
    assert providers["local"]["endpointEnv"] == "LOCAL_MODEL_ENDPOINT"
    for provider in providers.values():
        assert provider["enabled"] is False
        assert provider["shellImplementationStatus"] == "disabled_shell"
        assert provider["sdkImported"] is False
        assert provider["clientCreated"] is False
        assert provider["secretValueReturned"] is False
        assert provider["realLlmCalled"] is False
        assert provider["secretsRead"] is False
        assert provider["networkAccess"] is False
        assert provider["generatedContentCreated"] is False
        assert provider["taskCreated"] is False


def test_real_provider_shell_health_returns_disabled_descriptor():
    request = RealProviderShellRequest(provider_id="openai", operation="health", trace_id="trace_shell")
    health = invoke_real_provider_shell(request, root=ROOT)

    assert health["providerId"] == "openai"
    assert health["operation"] == "health"
    assert health["status"] == "DISABLED"
    assert health["readyForRealProvider"] is False
    assert health["sdkImported"] is False
    assert health["clientCreated"] is False
    assert health["realLlmCalled"] is False
    assert health["secretsRead"] is False
    assert health["networkAccess"] is False


def test_real_provider_shell_generate_json_reuses_gate_and_remains_safe(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-appear")
    request = RealProviderShellRequest(provider_id="openai", operation="generateJson")

    try:
        invoke_real_provider_shell(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_OPT_IN_REQUIRED"
        context = build_real_provider_shell_error_context(exc, request=request, root=ROOT)
        assert context["providerId"] == "openai"
        assert context["operation"] == "generateJson"
        assert context["readyForRealProvider"] is False
        assert context["generatedContentCreated"] is False
        assert context["taskCreated"] is False
        assert context["reviewBypassed"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
        assert context["secretValueReturned"] is False
        assert "sk-should-not-appear" not in json.dumps(context)
    else:
        raise AssertionError("expected ProviderError")


def test_real_provider_shell_generate_json_opt_in_still_disabled(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-still-hidden")
    request = RealProviderShellRequest(provider_id="openai", operation="generateJson", explicit_opt_in=True)

    try:
        invoke_real_provider_shell(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_DISABLED"
        context = build_real_provider_shell_error_context(exc, request=request, root=ROOT)
        assert context["explicitOptIn"] is True
        assert context["enabled"] is False
        assert context["realProviderRoutingAllowed"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
        assert "sk-still-hidden" not in json.dumps(context)
    else:
        raise AssertionError("expected ProviderError")


def test_real_provider_shell_generate_text_and_stream_are_disabled():
    text_request = RealProviderShellRequest(provider_id="anthropic", operation="generateText")
    stream_request = RealProviderShellRequest(provider_id="local", operation="streamGenerate")

    try:
        invoke_real_provider_shell(text_request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_SHELL_DISABLED"
        context = build_real_provider_shell_error_context(exc, request=text_request, root=ROOT)
        assert context["providerId"] == "anthropic"
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
    else:
        raise AssertionError("expected ProviderError")

    try:
        invoke_real_provider_shell(stream_request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "UNSUPPORTED_OPERATION"
        assert exc.errors[0]["field"] == "operation"
    else:
        raise AssertionError("expected ProviderError")


def test_real_provider_shell_cli_list_and_health_return_unified_json(capsys):
    exit_code, payload = run_cli(["provider", "real-shell", "list"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["realLlmCalled"] is False
    assert {provider["providerId"] for provider in payload["data"]["providers"]} == {"openai", "anthropic", "local"}

    exit_code, payload = run_cli(["provider", "real-shell", "health", "--provider", "openai"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["status"] == "DISABLED"
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["secretsRead"] is False
    assert payload["data"]["networkAccess"] is False


def test_real_provider_shell_cli_generate_json_fails_safely_without_secret_values(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-cli-hidden")
    exit_code, payload = run_cli(["provider", "real-shell", "generate-json", "--provider", "openai"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "REAL_PROVIDER_OPT_IN_REQUIRED"
    assert payload["providerShellContext"]["providerId"] == "openai"
    assert payload["providerShellContext"]["readyForRealProvider"] is False
    assert payload["providerShellContext"]["realLlmCalled"] is False
    assert payload["providerShellContext"]["secretsRead"] is False
    assert payload["providerShellContext"]["networkAccess"] is False
    assert payload["providerShellContext"]["secretValueReturned"] is False
    assert "sk-cli-hidden" not in json.dumps(payload)

    exit_code, payload = run_cli(
        ["provider", "real-shell", "generate-json", "--provider", "openai", "--explicit-opt-in"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_PROVIDER_DISABLED"
    assert payload["providerShellContext"]["explicitOptIn"] is True
    assert payload["providerShellContext"]["realLlmCalled"] is False
    assert payload["providerShellContext"]["secretsRead"] is False
    assert payload["providerShellContext"]["networkAccess"] is False
    assert "sk-cli-hidden" not in json.dumps(payload)
