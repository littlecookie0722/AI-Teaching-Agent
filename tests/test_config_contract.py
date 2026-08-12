import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_contract():
    with (ROOT / "config/runtime.contract.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_env_example():
    values = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        values[key] = value
    return values


def test_config_contract_is_phase1_mock_only():
    contract = load_contract()

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["defaults"]["ENABLE_REAL_LLM"] == "false"
    assert contract["defaults"]["ENABLE_REAL_CLOUD"] == "false"
    assert contract["defaults"]["ENABLE_REAL_SANDBOX"] == "false"
    assert contract["defaults"]["ENABLE_AUTO_PUBLISH"] == "false"


def test_env_example_exists_and_contains_declared_variables():
    contract = load_contract()
    env_values = parse_env_example()
    declared = {variable["name"] for variable in contract["variables"]}

    assert (ROOT / contract["envExamplePath"]).exists()
    assert set(env_values) == declared


def test_env_example_uses_safe_phase1_defaults():
    env_values = parse_env_example()

    assert env_values["APP_PHASE"] == "Phase 1"
    assert env_values["APP_MODE"] == "MOCK_ONLY"
    assert env_values["ENABLE_REAL_LLM"] == "false"
    assert env_values["ENABLE_REAL_CLOUD"] == "false"
    assert env_values["ENABLE_REAL_SANDBOX"] == "false"
    assert env_values["ENABLE_AUTO_PUBLISH"] == "false"


def test_secret_variables_are_empty_in_env_example():
    contract = load_contract()
    env_values = parse_env_example()

    for variable in contract["variables"]:
        if variable["secret"]:
            assert env_values[variable["name"]] == ""
            assert variable["phase1Allowed"] is False
            assert variable["source"] == "environment_only"


def test_env_example_does_not_contain_blocked_secret_values():
    contract = load_contract()
    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")

    for blocked in contract["blockedConfigValues"]:
        assert blocked not in env_text


def test_no_real_env_files_are_present_in_repo():
    env_files = [path.name for path in ROOT.glob(".env*")]

    assert env_files == [".env.example"]


def test_config_contract_blocks_secret_exposure_rules():
    contract = load_contract()
    rules = contract["rules"]

    assert rules["realSecretsMustNotBeCommitted"] is True
    assert rules["envFilesOtherThanExampleMustNotBeCommitted"] is True
    assert rules["frontendMustNotExposeSecrets"] is True
    assert rules["logsMustNotPrintSecrets"] is True
