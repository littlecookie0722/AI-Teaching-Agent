import json
from pathlib import Path

from cli.provider_audit import ProviderCallStatus, create_provider_call_audit_event
from cli.store import JsonTaskStore
from providers import (
    ProviderAdapter,
    ProviderError,
    ProviderRequest,
    build_provider_error_context,
    invoke_provider,
)


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_provider_adapter_contract_is_mock_only_and_paths_exist():
    contract = load_json("providers/provider-adapter.contract.json")

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["interfaceName"] == "LLMProvider"
    assert contract["activeProvider"] == "mock"
    assert contract["rules"]["mockProviderOnly"] is True
    assert contract["rules"]["realProviderRoutingAllowed"] is False
    assert contract["rules"]["realProviderPreflightAllowed"] is True
    assert contract["rules"]["realProviderPreflightNetworkAccess"] is False
    assert contract["rules"]["realProviderPreflightSecretValueReturned"] is False
    assert contract["rules"]["realProviderPreflightDefaultReady"] is False
    assert contract["rules"]["realProviderShellAllowed"] is True
    assert contract["rules"]["realProviderShellGenerationEnabled"] is False
    assert contract["rules"]["providerRuntimeGuardAllowed"] is True
    assert contract["rules"]["providerRuntimeGuardNetworkAccess"] is False
    assert contract["rules"]["realLlmPocAdapterAllowed"] is True
    assert contract["rules"]["realLlmPocAdapterEnabled"] is False
    assert contract["rules"]["realLlmPocAdapterNetworkAccess"] is False
    assert contract["rules"]["realLlmPocAdapterSecretValueReturned"] is False
    assert contract["rules"]["streamGenerateEnabled"] is False
    assert contract["rules"]["schemaValidationRequiredForGenerateJson"] is True
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert "realProviderPreflight" in {operation["id"] for operation in contract["operations"]}
    assert "realProviderShell" in {operation["id"] for operation in contract["operations"]}
    assert "realProviderRuntimeGuard" in {operation["id"] for operation in contract["operations"]}
    assert "realLlmPocAdapter" in {operation["id"] for operation in contract["operations"]}
    assert "test_real_provider_gate" in contract["recommendedCommandIds"]
    assert "test_real_provider_shell" in contract["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_provider_adapter_error_matrix_is_mock_only_and_paths_exist():
    contract = load_json("providers/provider-adapter-errors.contract.json")

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["adapterId"] == "mock_provider_adapter"
    assert contract["interfaceName"] == "LLMProvider"
    assert contract["errorContextField"] == "providerErrorContext"
    assert {case["id"] for case in contract["errorCases"]} == {
        "disabled_provider",
        "missing_prompt_id",
        "unknown_prompt",
        "output_kind_mismatch",
        "stream_generate_deferred",
    }
    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()
    for value in contract["requiredErrorContext"].values():
        if isinstance(value, bool):
            assert value is False
    assert contract["requiredErrorContext"]["mode"] == "MOCK_ONLY"


def test_provider_call_audit_contract_is_mock_only_and_paths_exist():
    contract = load_json("providers/provider-audit.contract.json")

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["adapterId"] == "mock_provider_adapter"
    assert contract["interfaceName"] == "LLMProvider"
    assert contract["storeKey"] == "providerCallAuditEvents"
    assert set(contract["recordedOperations"]) == {"registry", "health", "generateJson"}
    assert set(contract["statuses"]) == {"SUCCESS", "FAILED"}
    assert {"providerId", "operation", "status", "promptId", "traceId", "actor"} <= set(contract["supportedFilters"])
    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()
    assert {entry["path"] for entry in contract["entrypoints"] if entry["type"] == "api"} == {
        "/api/provider-audit-events"
    }
    assert {entry["command"] for entry in contract["entrypoints"] if entry["type"] == "cli"} == {
        "python lab_cli.py provider audit"
    }
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert contract["safety"]["autoPublishAllowed"] is False


def test_provider_call_audit_event_records_mock_success_safety_flags():
    event = create_provider_call_audit_event(
        operation="generateJson",
        provider_id="mock",
        status=ProviderCallStatus.SUCCESS,
        actor="lab-cli",
        trace_id="trace_provider_audit",
        result={
            "promptId": "lab_generation_v0",
            "outputKind": "Lab",
            "inputRef": "examples/input/demo-source.md",
            "dslPath": "templates/lab/examples/basic-lab.yaml",
            "dslId": "lab_python_basic",
            "generatedStatus": "WAITING_REVIEW",
        },
    )
    payload = event.to_dict()

    assert payload["adapterId"] == "mock_provider_adapter"
    assert payload["interfaceName"] == "LLMProvider"
    assert payload["status"] == "SUCCESS"
    assert payload["promptId"] == "lab_generation_v0"
    assert payload["mockOutputCreated"] is True
    assert payload["generatedContentCreated"] is True
    assert payload["taskCreated"] is False
    assert payload["reviewBypassed"] is False
    assert payload["realLlmCalled"] is False
    assert payload["secretsRead"] is False
    assert payload["networkAccess"] is False


def test_provider_call_audit_store_filters_failed_events(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    store.save_provider_call_audit_event(
        create_provider_call_audit_event(
            operation="health",
            provider_id="mock",
            status=ProviderCallStatus.SUCCESS,
            actor="backend-mock",
            trace_id="trace_health",
        )
    )
    failed = create_provider_call_audit_event(
        operation="generateJson",
        provider_id="mock",
        status=ProviderCallStatus.FAILED,
        actor="backend-mock",
        trace_id="trace_generate",
        prompt_id="missing_prompt",
        error_code="NOT_FOUND",
        error_field="promptId",
        error_message="Prompt 不存在",
    )
    store.save_provider_call_audit_event(failed)

    events = store.list_provider_call_audit_events(
        operation="generateJson",
        status=ProviderCallStatus.FAILED.value,
        prompt_id="missing_prompt",
    )

    assert [event.id for event in events] == [failed.id]
    assert events[0].errorCode == "NOT_FOUND"
    assert events[0].generatedContentCreated is False
    assert events[0].taskCreated is False


def test_provider_adapter_invokes_mock_generate_json_with_schema_validation():
    result = invoke_provider(
        "generateJson",
        prompt_id="lab_generation_v0",
        input_ref="examples/input/demo-source.md",
        root=ROOT,
    )

    assert result["adapterId"] == "mock_provider_adapter"
    assert result["interfaceName"] == "LLMProvider"
    assert result["operation"] == "generateJson"
    assert result["providerId"] == "mock"
    assert result["mode"] == "MOCK_ONLY"
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["reviewRequired"] is True
    assert result["publishBlockedUntilApproved"] is True
    assert result["dsl"]["kind"] == "Lab"
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False


def test_provider_adapter_invokes_mock_generate_text():
    result = ProviderAdapter(ROOT).invoke(
        request=ProviderRequest(operation="generateText", prompt_id="self_check_v0")
    )

    assert result["adapterId"] == "mock_provider_adapter"
    assert result["operation"] == "generateText"
    assert result["providerId"] == "mock"
    assert result["mode"] == "MOCK_ONLY"
    assert result["generatedStatus"] == "DRAFT"
    assert result["realLlmCalled"] is False


def test_provider_adapter_health_does_not_read_secrets_or_network():
    result = invoke_provider("health", root=ROOT)

    assert result["adapterId"] == "mock_provider_adapter"
    assert result["operation"] == "health"
    assert result["providerId"] == "mock"
    assert result["status"] == "UP"
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False


def test_provider_adapter_rejects_disabled_real_provider():
    try:
        invoke_provider("generateJson", provider_id="openai", prompt_id="lab_generation_v0", root=ROOT)
    except ProviderError as exc:
        assert exc.code == "PROVIDER_DISABLED"
        assert exc.errors[0]["field"] == "provider"
        context = build_provider_error_context(exc, operation="generateJson", provider_id="openai")
        assert context["adapterId"] == "mock_provider_adapter"
        assert context["providerId"] == "openai"
        assert context["errorCode"] == "PROVIDER_DISABLED"
        assert context["generatedContentCreated"] is False
        assert context["taskCreated"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_provider_adapter_rejects_stream_generate():
    try:
        invoke_provider("streamGenerate", prompt_id="lab_generation_v0", root=ROOT)
    except ProviderError as exc:
        assert exc.code == "UNSUPPORTED_OPERATION"
        assert exc.errors[0]["field"] == "operation"
    else:
        raise AssertionError("expected ProviderError")


def test_provider_adapter_rejects_missing_prompt_id_with_safe_context():
    try:
        invoke_provider("generateJson", root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "promptId"
        context = build_provider_error_context(exc, operation="generateJson", provider_id="mock")
        assert context["generatedContentCreated"] is False
        assert context["taskCreated"] is False
        assert context["reviewBypassed"] is False
        assert context["autoPublishAllowed"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_provider_adapter_commands_are_allowlisted():
    contract = load_json("providers/provider-adapter.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_provider_gate" in contract["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in contract["recommendedCommandIds"]
    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
