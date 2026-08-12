import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_contract():
    return load_json("providers/phase2-provider-plan.contract.json")


def test_phase2_provider_plan_is_phase1_mock_only():
    contract = load_contract()

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert contract["safety"]["autoPublishAllowed"] is False


def test_phase2_provider_plan_inputs_outputs_exist_and_define_interface():
    contract = load_contract()
    principle_ids = {item["id"] for item in contract["providerPrinciples"]}
    method_names = {item["name"] for item in contract["interfaceDesign"]["methods"]}

    assert {
        "mock_provider_first",
        "real_provider_requires_explicit_task",
        "schema_validation_required",
        "safe_error_matrix_required",
        "provider_call_audit_required",
        "prompt_manifest_only",
        "secrets_from_env_only",
        "logs_redact_secrets",
        "timeouts_retries_configured",
        "network_disabled_until_enabled",
        "review_gate_required",
        "real_provider_preflight_gate",
        "real_provider_shell_disabled",
        "provider_runtime_guard_required",
        "real_llm_poc_adapter_disabled",
        "real_llm_dry_run_plan_required",
        "real_llm_approval_gate_required",
        "real_llm_sdk_task_blueprint_required",
        "real_provider_sdk_poc_disabled",
        "real_sdk_enablement_switch_required",
        "real_sdk_minimal_impl_disabled",
        "real_sdk_dependency_env_gate_required",
    } <= principle_ids
    assert all(item["required"] is True for item in contract["providerPrinciples"])
    assert contract["interfaceDesign"]["interfaceName"] == "LLMProvider"
    assert method_names == {"generateText", "generateJson", "streamGenerate"}

    generate_json = next(
        item for item in contract["interfaceDesign"]["methods"] if item["name"] == "generateJson"
    )
    stream_generate = next(
        item for item in contract["interfaceDesign"]["methods"] if item["name"] == "streamGenerate"
    )
    assert generate_json["requiresSchemaValidation"] is True
    assert stream_generate["deferred"] is True

    for entry in [*contract["inputs"], *contract["outputs"]]:
        if not entry.get("generated", False):
            assert (ROOT / entry["path"]).exists()
        assert entry.get("localOnly", True) is True
    assert "providers/provider-adapter-errors.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/provider-audit.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_provider_gate.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-provider-gate.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_provider_shell.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-provider-shell.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/provider_runtime_guard.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/provider-runtime-guard.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_llm_poc_adapter.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-llm-poc-adapter.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_llm_dry_run_plan.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-llm-dry-run-plan.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_llm_approval_gate.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-llm-approval-gate.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_llm_sdk_task_blueprint.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-llm-sdk-task-blueprint.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_provider_sdk_poc.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-provider-sdk-poc.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_sdk_enablement.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-sdk-enablement.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_sdk_minimal_impl.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-sdk-minimal-impl.contract.json" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real_sdk_dependency_env_gate.py" in {entry["path"] for entry in contract["inputs"]}
    assert "providers/real-sdk-dependency-env-gate.contract.json" in {entry["path"] for entry in contract["inputs"]}


def test_phase2_provider_plan_commands_are_allowlisted():
    contract = load_contract()
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}
    blocked_patterns = [pattern.lower() for pattern in manifest["blockedPatterns"]]

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_provider_gate" in contract["recommendedCommandIds"]
    assert "test_real_provider_shell" in contract["recommendedCommandIds"]
    assert "test_provider_runtime_guard" in contract["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in contract["recommendedCommandIds"]
    assert "test_real_llm_dry_run_plan" in contract["recommendedCommandIds"]
    assert "test_real_llm_approval_gate" in contract["recommendedCommandIds"]
    assert "test_real_llm_sdk_task_blueprint" in contract["recommendedCommandIds"]
    assert "test_real_provider_sdk_poc" in contract["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in contract["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in contract["recommendedCommandIds"]
    assert "test_provider_adapter_workflow" in contract["recommendedCommandIds"]
    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        command_text = command["command"].lower()
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert not any(pattern in command_text for pattern in blocked_patterns)


def test_phase2_provider_plan_real_provider_placeholders_are_disabled():
    contract = load_contract()
    placeholders = {provider["id"]: provider for provider in contract["realProviderPlaceholders"]}

    assert set(placeholders) == {"openai", "anthropic", "local"}
    assert placeholders["openai"]["apiKeyEnv"] == "OPENAI_API_KEY"
    assert placeholders["anthropic"]["apiKeyEnv"] == "ANTHROPIC_API_KEY"
    assert placeholders["local"]["apiKeyEnv"] == "LOCAL_MODEL_ENDPOINT"
    for provider in placeholders.values():
        assert provider["enabled"] is False
        assert provider["realLlmCalled"] is False
        assert provider["networkAccess"] is False
        assert "sk-" not in provider["apiKeyEnv"].lower()
        assert "secret" not in provider["apiKeyEnv"].lower()


def test_phase2_provider_plan_blocks_real_execution():
    contract = load_contract()

    assert {
        "enable_real_llm",
        "read_real_secret",
        "network_call",
        "bypass_schema",
        "bypass_review",
        "log_secret",
        "auto_publish",
        "runtime_guard_bypass",
        "missing_timeout_retry_concurrency_guard",
        "unredacted_provider_payload",
        "real_llm_poc_adapter_bypass",
        "real_llm_dry_run_plan_bypass",
        "real_llm_approval_gate_bypass",
        "real_llm_sdk_task_blueprint_bypass",
        "real_provider_sdk_poc_bypass",
        "real_sdk_enablement_bypass",
        "real_sdk_minimal_impl_bypass",
        "real_sdk_dependency_env_gate_bypass",
        "install_sdk_dependency_without_gate",
        "secret_presence_check_without_gate",
    } <= set(contract["blockedWork"])
    assert all(item["allowed"] is True for item in contract["phase2AllowedWork"])
    assert "test_provider_adapter_workflow" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_provider_adapter" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_provider_gate" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_provider_shell" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_provider_runtime_guard" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_llm_poc_adapter" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_llm_dry_run_plan" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_llm_approval_gate" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_llm_sdk_task_blueprint" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_provider_sdk_poc" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_sdk_enablement" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_sdk_minimal_impl" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }
    assert "test_real_sdk_dependency_env_gate" in {
        signal["commandId"] for signal in contract["acceptanceSignals"]
    }


def test_phase2_provider_plan_markdown_documents_usage_and_limits():
    content = (ROOT / "providers/PHASE2_PROVIDER_PLAN.md").read_text(encoding="utf-8")

    for heading in [
        "## 输入说明",
        "## 输出说明",
        "## 接口设计",
        "## MockProvider 优先策略",
        "## 真实 Provider 预留",
        "## 安全与配置",
        "## 命令示例",
        "## 测试方式",
        "## 限制说明",
    ]:
        assert heading in content

    for text in [
        "MOCK_ONLY",
        "MockProvider",
        "LLMProvider",
        "generateText",
        "generateJson",
        "streamGenerate",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "LOCAL_MODEL_ENDPOINT",
        "WAITING_REVIEW",
        "providers/provider-adapter-errors.contract.json",
        "providers/provider-audit.contract.json",
        "providers/real-provider-gate.contract.json",
        "providers/real-provider-shell.contract.json",
        "providers/provider-runtime-guard.contract.json",
        "providers/real-llm-poc-adapter.contract.json",
        "providers/real-llm-dry-run-plan.contract.json",
        "providers/real-llm-approval-gate.contract.json",
        "providers/real-llm-sdk-task-blueprint.contract.json",
        "providers/real-provider-sdk-poc.contract.json",
        "providers/real-sdk-enablement.contract.json",
        "providers/real-sdk-minimal-impl.contract.json",
        "providers/real-sdk-dependency-env-gate.contract.json",
        "错误矩阵",
        "ai_workflows/provider_adapter_workflow.py",
        "providers/real_provider_shell.py",
        "providers/provider_runtime_guard.py",
        "providers/real_llm_poc_adapter.py",
        "providers/real_llm_dry_run_plan.py",
        "providers/real_llm_approval_gate.py",
        "providers/real_llm_sdk_task_blueprint.py",
        "providers/real_provider_sdk_poc.py",
        "providers/real_sdk_enablement.py",
        "providers/real_sdk_minimal_impl.py",
        "providers/real_sdk_dependency_env_gate.py",
        "不接入真实大模型",
        "不读取真实密钥",
        "不访问网络",
        "python -m pytest tests/test_phase2_provider_plan.py",
        "python -m pytest tests/test_provider_adapter_workflow.py",
        "python -m pytest tests/test_real_provider_gate.py",
        "python -m pytest tests/test_real_provider_shell.py",
        "python -m pytest tests/test_provider_runtime_guard.py",
        "python -m pytest tests/test_real_llm_poc_adapter.py",
        "python -m pytest tests/test_real_llm_dry_run_plan.py",
        "python -m pytest tests/test_real_llm_approval_gate.py",
        "python -m pytest tests/test_real_llm_sdk_task_blueprint.py",
        "python -m pytest tests/test_real_provider_sdk_poc.py",
        "python -m pytest tests/test_real_sdk_enablement.py",
        "python -m pytest tests/test_real_sdk_minimal_impl.py",
        "python -m pytest tests/test_real_sdk_dependency_env_gate.py",
        "python lab_cli.py provider real-sdk-enablement describe",
        "python lab_cli.py provider real-sdk-enablement check --provider openai",
        "python lab_cli.py provider real-sdk-impl describe",
        "python lab_cli.py provider real-sdk-impl generate-json --provider openai",
        "python lab_cli.py provider real-sdk-dependency-env describe",
        "python lab_cli.py provider real-sdk-dependency-env check --provider openai",
        "python lab_cli.py provider list",
        "python lab_cli.py provider health",
        "python lab_cli.py provider real-preflight --provider openai",
        "python lab_cli.py provider real-shell list",
        "python lab_cli.py provider runtime-guard --provider openai",
        "python lab_cli.py provider real-poc-adapter describe",
        "python lab_cli.py provider real-poc-adapter generate-json --provider openai",
        "python lab_cli.py provider real-dry-run plan --provider openai",
        "python lab_cli.py provider real-approval-gate check --provider openai",
        "python lab_cli.py provider real-sdk-blueprint plan --provider openai",
        "python lab_cli.py provider real-sdk-poc describe",
        "python lab_cli.py provider real-sdk-poc generate-json --provider openai",
        "python lab_cli.py provider mock-generate --prompt-id lab_generation_v0",
    ]:
        assert text in content
