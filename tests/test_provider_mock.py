from providers import MockProvider, ProviderAdapter, ProviderError, build_provider_registry, get_provider_health, invoke_provider


def test_provider_registry_only_enables_mock():
    registry = build_provider_registry()

    assert registry["mode"] == "MOCK_ONLY"
    assert registry["activeProvider"] == "mock"
    assert registry["realLlmCalled"] is False
    assert registry["secretsRead"] is False
    assert registry["networkAccess"] is False
    assert [provider["id"] for provider in registry["providers"] if provider["enabled"]] == ["mock"]


def test_mock_provider_health_is_safe():
    health = get_provider_health("mock")

    assert health["providerId"] == "mock"
    assert health["status"] == "UP"
    assert health["mode"] == "MOCK_ONLY"
    assert health["realLlmCalled"] is False
    assert health["secretsRead"] is False
    assert health["networkAccess"] is False
    assert health["capabilities"]["generateJson"] is True


def test_mock_provider_generate_json_returns_waiting_review_dsl():
    result = MockProvider().generate_json("lab_generation_v0", input_ref="examples/input/demo-source.md")

    assert result["providerId"] == "mock"
    assert result["promptId"] == "lab_generation_v0"
    assert result["outputKind"] == "Lab"
    assert result["dslPath"] == "templates/lab/examples/basic-lab.yaml"
    assert result["dsl"]["kind"] == "Lab"
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["reviewRequired"] is True
    assert result["publishBlockedUntilApproved"] is True
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False


def test_mock_provider_rejects_disabled_real_provider_health():
    try:
        get_provider_health("openai")
    except ProviderError as exc:
        assert exc.code == "PROVIDER_DISABLED"
        assert exc.errors[0]["field"] == "provider"
    else:
        raise AssertionError("expected ProviderError")


def test_mock_provider_rejects_unknown_prompt():
    try:
        MockProvider().generate_json("missing_prompt")
    except ProviderError as exc:
        assert exc.code == "NOT_FOUND"
        assert exc.errors[0]["field"] == "promptId"
    else:
        raise AssertionError("expected ProviderError")


def test_mock_provider_rejects_output_kind_mismatch():
    try:
        MockProvider().generate_json("lab_generation_v0", output_kind="Exam")
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "outputKind"
    else:
        raise AssertionError("expected ProviderError")


def test_mock_provider_generate_text_does_not_call_real_llm():
    result = MockProvider().generate_text("self_check_v0")

    assert result["mode"] == "MOCK_ONLY"
    assert result["outputKind"] == "ReviewReport"
    assert result["generatedStatus"] == "DRAFT"
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False


def test_invoke_provider_adapter_delegates_to_mock_provider():
    result = invoke_provider("generateJson", prompt_id="grading_generation_v0")

    assert result["adapterId"] == ProviderAdapter.adapter_id
    assert result["interfaceName"] == ProviderAdapter.interface_name
    assert result["operation"] == "generateJson"
    assert result["providerId"] == "mock"
    assert result["outputKind"] == "Grading"
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False
