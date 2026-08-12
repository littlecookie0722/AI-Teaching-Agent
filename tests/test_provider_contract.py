import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_provider_contract_is_phase1_mock_only():
    contract = load_json("providers/provider.contract.json")

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["activeProvider"] == "mock"
    assert contract["rules"]["onlyMockProviderEnabled"] is True
    assert contract["rules"]["realProviderInstantiationBlocked"] is True
    assert contract["rules"]["apiKeysNotReadInPhase1"] is True


def test_only_mock_provider_is_enabled():
    contract = load_json("providers/provider.contract.json")
    enabled = [provider for provider in contract["providers"] if provider["enabled"] is True]

    assert [provider["id"] for provider in enabled] == ["mock"]
    assert enabled[0]["requiresApiKey"] is False
    assert enabled[0]["realLlmCalled"] is False
    assert enabled[0]["networkAccess"] is False


def test_real_provider_placeholders_are_disabled_and_secret_env_only():
    contract = load_json("providers/provider.contract.json")

    for provider in contract["providers"]:
        if provider["id"] == "mock":
            continue
        assert provider["enabled"] is False
        assert provider["phase1Allowed"] is False
        assert provider["realLlmCalled"] is False
        assert provider["networkAccess"] is False
        assert provider["implementationStatus"] == "placeholder"


def test_supported_mock_outputs_reference_prompt_manifest_and_dsl_files():
    contract = load_json("providers/provider.contract.json")
    prompt_manifest = load_json("prompts/manifest.json")
    prompts = {prompt["id"]: prompt for prompt in prompt_manifest["prompts"]}

    for output in contract["supportedMockOutputs"]:
        prompt = prompts[output["promptId"]]
        assert prompt["outputKind"] == output["outputKind"]
        assert prompt["defaultStatus"] == "WAITING_REVIEW"
        assert prompt["reviewRequired"] is True
        assert prompt["path"].startswith("prompts/")
        assert (ROOT / prompt["path"]).exists()
        assert (ROOT / output["dslPath"]).exists()


def test_provider_interface_declares_required_methods():
    contract = load_json("providers/provider.contract.json")

    assert set(contract["providerInterface"]) == {"generateText", "generateJson", "health"}
