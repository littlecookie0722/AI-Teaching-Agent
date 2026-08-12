import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    ProviderRuntimeGuardRequest,
    build_provider_runtime_guard_error_context,
    evaluate_provider_runtime_guard,
    redact_provider_payload,
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


def test_provider_runtime_guard_contract_is_mock_only_and_local():
    contract = load_json("providers/provider-runtime-guard.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["activeProvider"] == "mock"
    assert contract["runtimeLimits"]["timeoutSeconds"]["default"] == 30
    assert contract["runtimeLimits"]["retryCount"]["max"] == 3
    assert contract["runtimeLimits"]["concurrencyLimit"]["max"] == 4
    assert contract["requiredContext"]["guardPassed"] is True
    assert contract["requiredContext"]["redactionApplied"] is True
    assert contract["requiredContext"]["schemaValidationRequired"] is True
    assert contract["requiredContext"]["generatedStatus"] == "WAITING_REVIEW"
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert contract["requiredContext"]["secretsRead"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_provider_runtime_guard" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_provider_runtime_guard_evaluates_limits_without_real_execution():
    fake_key = "sk-" + "should-redact"
    result = evaluate_provider_runtime_guard(
        ProviderRuntimeGuardRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "nested": {"token": "abc", "note": "Bearer live-token"}},
            trace_id="trace_guard",
        ),
        root=ROOT,
    )

    assert result["guardId"] == "provider_runtime_guard"
    assert result["providerId"] == "openai"
    assert result["guardPassed"] is True
    assert result["timeoutSeconds"] == 30
    assert result["retryCount"] == 1
    assert result["concurrencyLimit"] == 1
    assert result["timeoutConfigured"] is True
    assert result["retryConfigured"] is True
    assert result["concurrencyLimitConfigured"] is True
    assert result["logRedactionRequired"] is True
    assert result["redactionApplied"] is True
    assert result["schemaValidationRequired"] is True
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["readyForRealProvider"] is False
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False
    assert result["secretValueReturned"] is False
    assert result["sdkImported"] is False
    assert result["clientCreated"] is False
    assert result["generatedContentCreated"] is False
    assert result["taskCreated"] is False
    dumped = json.dumps(result)
    assert fake_key not in dumped
    assert "live-token" not in dumped
    assert result["redactedPayloadPreview"]["apiKey"] == "[REDACTED]"
    assert result["redactedPayloadPreview"]["nested"]["token"] == "[REDACTED]"
    assert result["redactedPayloadPreview"]["nested"]["note"] == "Bearer [REDACTED]"


def test_provider_runtime_guard_redacts_nested_secret_shapes():
    payload = {
        "password": "plain",
        "headers": {"Authorization": "Bearer hidden-token"},
        "text": "token=abc123 secret=qwerty",
        "items": [{"value": "sk-list-secret"}],
    }

    redacted = redact_provider_payload(payload)
    dumped = json.dumps(redacted)

    assert redacted["password"] == "[REDACTED]"
    assert redacted["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["text"] == "token=[REDACTED] secret=[REDACTED]"
    assert redacted["items"][0]["value"] == "[REDACTED]"
    assert "hidden-token" not in dumped
    assert "abc123" not in dumped
    assert "qwerty" not in dumped
    assert "sk-list-secret" not in dumped


def test_provider_runtime_guard_rejects_invalid_scope_with_safe_context():
    request = ProviderRuntimeGuardRequest(provider_id="openai", output_kind="Exam")

    try:
        evaluate_provider_runtime_guard(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_provider_runtime_guard_error_context(exc, request=request, root=ROOT)
        assert context["guardPassed"] is False
        assert context["providerId"] == "openai"
        assert context["outputKind"] == "Exam"
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
        assert context["generatedContentCreated"] is False
        assert context["taskCreated"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_provider_runtime_guard_rejects_limit_ranges():
    cases = [
        ("timeoutSeconds", ProviderRuntimeGuardRequest(provider_id="openai", timeout_seconds=0)),
        ("retryCount", ProviderRuntimeGuardRequest(provider_id="openai", retry_count=4)),
        ("concurrencyLimit", ProviderRuntimeGuardRequest(provider_id="openai", concurrency_limit=0)),
    ]

    for field, request in cases:
        try:
            evaluate_provider_runtime_guard(request, root=ROOT)
        except ProviderError as exc:
            assert exc.code == "VALIDATION_ERROR"
            assert exc.errors[0]["field"] == field
            context = build_provider_runtime_guard_error_context(exc, request=request, root=ROOT)
            assert context["guardPassed"] is False
            assert context["realLlmCalled"] is False
            assert context["secretsRead"] is False
            assert context["networkAccess"] is False
        else:
            raise AssertionError("expected ProviderError")


def test_provider_runtime_guard_rejects_mock_and_stream_scope():
    for request, code in [
        (ProviderRuntimeGuardRequest(provider_id="mock"), "VALIDATION_ERROR"),
        (ProviderRuntimeGuardRequest(provider_id="openai", operation="streamGenerate"), "UNSUPPORTED_OPERATION"),
    ]:
        try:
            evaluate_provider_runtime_guard(request, root=ROOT)
        except ProviderError as exc:
            assert exc.code == code
            context = build_provider_runtime_guard_error_context(exc, request=request, root=ROOT)
            assert context["readyForRealProvider"] is False
            assert context["realLlmCalled"] is False
            assert context["secretValueReturned"] is False
        else:
            raise AssertionError("expected ProviderError")


def test_provider_runtime_guard_cli_returns_unified_json_and_redacts(capsys):
    fake_key = "sk-" + "cli-redact"
    fake_token = "cli" + "-token"
    exit_code, payload = run_cli(
        [
            "provider",
            "runtime-guard",
            "--provider",
            "openai",
            "--payload",
            json.dumps({"apiKey": fake_key, "headers": {"Authorization": f"Bearer {fake_token}"}}),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    data = payload["data"]
    assert data["guardPassed"] is True
    assert data["providerId"] == "openai"
    assert data["realLlmCalled"] is False
    assert data["secretsRead"] is False
    assert data["networkAccess"] is False
    assert fake_key not in json.dumps(payload)
    assert fake_token not in json.dumps(payload)
    assert data["redactedPayloadPreview"]["apiKey"] == "[REDACTED]"

    exit_code, payload = run_cli(
        ["provider", "runtime-guard", "--provider", "openai", "--timeout-seconds", "0"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["providerRuntimeGuardContext"]["guardPassed"] is False
    assert payload["providerRuntimeGuardContext"]["realLlmCalled"] is False
    assert payload["providerRuntimeGuardContext"]["secretsRead"] is False
    assert payload["providerRuntimeGuardContext"]["networkAccess"] is False


def test_provider_runtime_guard_cli_rejects_bad_payload_json(capsys):
    exit_code, payload = run_cli(
        ["provider", "runtime-guard", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"
