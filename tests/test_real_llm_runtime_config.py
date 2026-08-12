import json

from providers.real_llm_runtime_config import build_real_llm_runtime_config_summary


def test_real_llm_runtime_config_summary_is_readonly_and_redacted():
    payload = build_real_llm_runtime_config_summary(
        environ={
            "OPENAI_API_KEY": "sk-test-never-return",
            "OPENAI_MODEL": "mimo-v2.5-pro",
            "OPENAI_BASE_URL": "https://api.example.test/v1",
        }
    )

    assert payload["component"] == "RealLlmRuntimeConfigSummary"
    assert payload["mode"] == "REAL_LLM_RUNTIME_CONFIG_SUMMARY"
    assert payload["env"]["OPENAI_API_KEY"]["present"] is True
    assert payload["env"]["OPENAI_API_KEY"]["valueReturned"] is False
    assert "value" not in payload["env"]["OPENAI_API_KEY"]
    assert payload["env"]["OPENAI_MODEL"]["value"] == "mimo-v2.5-pro"
    assert payload["env"]["OPENAI_BASE_URL"]["value"] == "https://api.example.test/v1"
    assert payload["readyForRealLlmCommand"] is True
    assert payload["missingRequiredEnv"] == []
    assert payload["commandReadiness"]["canRunWithCurrentEnvironment"] is True
    assert payload["commandReadiness"]["nextAction"] == "run_real_llm_workflow_with_explicit_confirmations"
    assert payload["safeCommandTemplates"]["secretEnvPowerShell"] == '$env:OPENAI_API_KEY="<your-api-key>"'
    assert "sk-test-never-return" not in json.dumps(payload)
    assert payload["safety"]["requestSent"] is False
    assert payload["safety"]["realLlmCalled"] is False
    assert payload["safety"]["networkAccess"] is False


def test_real_llm_runtime_config_summary_reports_missing_required_env():
    payload = build_real_llm_runtime_config_summary(environ={})

    assert payload["readyForRealLlmCommand"] is False
    assert payload["missingRequiredEnv"] == ["OPENAI_API_KEY", "OPENAI_MODEL"]
    assert payload["commandReadiness"]["canRunWithCurrentEnvironment"] is False
    assert payload["commandReadiness"]["nextAction"] == "set_api_key_env"
    assert payload["commandReadiness"]["missingBeforeRun"] == ["OPENAI_API_KEY", "OPENAI_MODEL"]
    assert "<model-name>" in payload["safeCommandTemplates"]["workflowRunArgs"]
    assert payload["env"]["OPENAI_API_KEY"]["present"] is False
    assert payload["env"]["OPENAI_MODEL"]["present"] is False


def test_real_llm_runtime_config_summary_uses_argument_model_without_secret_value():
    payload = build_real_llm_runtime_config_summary(
        environ={"OPENAI_API_KEY": "sk-test-never-return"},
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
    )

    assert payload["readyForRealLlmCommand"] is True
    assert payload["missingRequiredEnv"] == []
    assert payload["env"]["OPENAI_API_KEY"]["present"] is True
    assert "value" not in payload["env"]["OPENAI_API_KEY"]
    assert payload["env"]["OPENAI_MODEL"]["value"] == "deepseek-v4-flash"
    assert payload["env"]["OPENAI_MODEL"]["source"] == "argument"
    assert payload["env"]["OPENAI_MODEL"]["envPresent"] is False
    assert payload["env"]["OPENAI_MODEL"]["argumentProvided"] is True
    assert payload["env"]["OPENAI_BASE_URL"]["value"] == "https://api.deepseek.com"
    assert payload["env"]["OPENAI_BASE_URL"]["source"] == "argument"
    readiness = payload["commandReadiness"]
    assert readiness["canRunWithCurrentEnvironment"] is True
    assert readiness["model"]["source"] == "argument"
    assert readiness["baseUrl"]["source"] == "argument"
    templates = payload["safeCommandTemplates"]
    assert templates["placeholders"]["model"] is None
    assert templates["placeholders"]["baseUrl"] is None
    assert "deepseek-v4-flash" in templates["runtimeConfigCheckArgs"]
    assert "https://api.deepseek.com" in templates["runtimeConfigCheckArgs"]
    assert "deepseek-v4-flash" in templates["workflowRunArgs"]
    assert "https://api.deepseek.com" in templates["workflowRunArgs"]
    assert "--confirm-real-dsl" in templates["workflowRunArgs"]
    assert "sk-test-never-return" not in json.dumps(payload)
