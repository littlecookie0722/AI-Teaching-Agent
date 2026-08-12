import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealProviderGateRequest,
    build_real_provider_gate_error_context,
    preflight_real_provider,
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


def test_real_provider_gate_contract_is_mock_only_and_local():
    contract = load_json("providers/real-provider-gate.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["requiredContext"]["defaultProvider"] == "mock"
    assert contract["requiredContext"]["readyForRealProvider"] is False
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert contract["requiredContext"]["secretsRead"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert contract["requiredContext"]["secretValueReturned"] is False
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_provider_gate" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_provider_gate_requires_explicit_opt_in_before_any_secret_or_network():
    request = RealProviderGateRequest(provider_id="openai")

    try:
        preflight_real_provider(request, root=ROOT, environ={})
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_OPT_IN_REQUIRED"
        context = build_real_provider_gate_error_context(exc, request=request)
        assert context["providerId"] == "openai"
        assert context["explicitOptIn"] is False
        assert context["readyForRealProvider"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
        assert context["secretValueReturned"] is False
        assert context["generatedContentCreated"] is False
        assert context["taskCreated"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_real_provider_gate_still_rejects_contract_disabled_provider_after_opt_in():
    request = RealProviderGateRequest(provider_id="openai", explicit_opt_in=True)

    try:
        preflight_real_provider(request, root=ROOT, environ={"OPENAI_API_KEY": "sk-test"})
    except ProviderError as exc:
        assert exc.code == "REAL_PROVIDER_DISABLED"
        context = build_real_provider_gate_error_context(exc, request=request)
        assert context["explicitOptIn"] is True
        assert context["defaultProvider"] == "mock"
        assert context["readyForRealProvider"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
        assert "sk-test" not in json.dumps(context)
    else:
        raise AssertionError("expected ProviderError")


def test_real_provider_gate_limits_first_scope_to_lab_json_generation():
    request = RealProviderGateRequest(
        provider_id="openai",
        operation="generateText",
        prompt_id="exam_generation_v0",
        output_kind="Exam",
        explicit_opt_in=True,
    )

    try:
        preflight_real_provider(request, root=ROOT, environ={})
    except ProviderError as exc:
        assert exc.code == "UNSUPPORTED_OPERATION"
        assert exc.errors[0]["field"] == "operation"
    else:
        raise AssertionError("expected ProviderError")

    request = RealProviderGateRequest(provider_id="openai", prompt_id="exam_generation_v0", output_kind="Exam")
    try:
        preflight_real_provider(request, root=ROOT, environ={})
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "promptId"
    else:
        raise AssertionError("expected ProviderError")


def test_real_provider_gate_cli_returns_unified_json_without_secret_values(capsys):
    exit_code, payload = run_cli(["provider", "real-preflight", "--provider", "openai"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "REAL_PROVIDER_OPT_IN_REQUIRED"
    assert payload["errors"][0]["field"] == "explicitOptIn"
    assert payload["providerGateContext"]["providerId"] == "openai"
    assert payload["providerGateContext"]["readyForRealProvider"] is False
    assert payload["providerGateContext"]["realLlmCalled"] is False
    assert payload["providerGateContext"]["secretsRead"] is False
    assert payload["providerGateContext"]["networkAccess"] is False
    assert payload["providerGateContext"]["secretValueReturned"] is False


def test_real_provider_gate_cli_explicit_opt_in_still_stays_disabled(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-appear")

    exit_code, payload = run_cli(
        ["provider", "real-preflight", "--provider", "openai", "--explicit-opt-in"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_PROVIDER_DISABLED"
    assert payload["providerGateContext"]["explicitOptIn"] is True
    assert payload["providerGateContext"]["realLlmCalled"] is False
    assert payload["providerGateContext"]["secretsRead"] is False
    assert payload["providerGateContext"]["networkAccess"] is False
    assert "sk-should-not-appear" not in json.dumps(payload)
