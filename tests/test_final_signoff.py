import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_final_signoff_is_phase5_mock_only():
    contract = load_json("delivery/final-signoff.json")

    assert contract["phase"] == "Phase 5"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["id"] == "phase5_final_signoff_package"
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["readOnly"] is True
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["realMcpServerStarted"] is False
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["realCloudResourceChanged"] is False
    assert contract["safety"]["realCloudResourceCreated"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["unknownShellExecuted"] is False
    assert contract["safety"]["autoPublishAllowed"] is False
    assert contract["safety"]["realPublish"] is False
    assert contract["safety"]["remoteUploadAllowed"] is False
    assert contract["safety"]["secretVisibleInFrontend"] is False
    assert contract["safety"]["answerVisibleToCandidate"] is False


def test_final_signoff_inputs_outputs_and_sequence_exist():
    contract = load_json("delivery/final-signoff.json")
    sequence_ids = {item["id"] for item in contract["signoffSequence"]}

    for entry in [*contract["inputs"], *contract["outputs"]]:
        assert entry.get("required") is True or entry.get("requiredForSignoff") is True
        assert (ROOT / entry["path"]).exists()
        assert not entry["path"].startswith(("http://", "https://"))

    assert {
        "read_project_readme",
        "read_delivery_readme",
        "read_handoff",
        "read_operations_manual",
        "read_operations_skill_pack",
        "read_standalone_agent_delivery",
        "read_access_entrypoints",
        "read_phase5_mock_baseline",
        "read_high_risk_mcp_handoff",
        "open_launchpad",
        "open_access_preview",
        "open_signoff",
        "open_delivery",
        "run_phase1_check",
        "export_delivery_package",
        "render_acceptance_report",
        "run_operations_skill_pack_tests",
        "run_standalone_agent_delivery_tests",
        "run_access_entrypoints_tests",
        "run_phase5_mock_baseline_tests",
        "run_real_llm_poc_adapter_tests",
        "run_real_sdk_enablement_tests",
        "run_real_sdk_minimal_impl_tests",
        "run_real_sdk_dependency_env_gate_tests",
        "run_operations_manual_tests",
        "run_final_signoff_tests",
        "confirm_review_gate",
        "confirm_no_real_execution",
    } <= sequence_ids

    for output in contract["generatedOutputs"]:
        assert output["path"].startswith("examples/output/")
        assert output["trackedInGit"] is False
        assert output["requiredForSignoff"] is True


def test_final_signoff_commands_are_allowlisted_and_safe():
    contract = load_json("delivery/final-signoff.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_final_signoff" in contract["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in contract["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in contract["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in contract["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in contract["recommendedCommandIds"]

    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert "|" not in command["command"]
        assert "docker run" not in command["command"]
        assert "kubectl " not in command["command"]

    for item in contract["signoffSequence"]:
        command_id = item.get("commandId")
        if command_id:
            assert command_id in allowed


def test_final_signoff_is_registered_in_delivery_contract_and_index():
    delivery_contract = load_json("config/delivery-package.contract.json")
    delivery_index = load_json("delivery/phase1-delivery-index.json")

    deliverable_ids = {item["id"] for item in delivery_contract["deliverables"]}
    entry_ids = {item["id"] for item in delivery_index["entryPoints"]}

    assert "final_signoff_md" in deliverable_ids
    assert "final_signoff_contract" in deliverable_ids
    assert "operations_manual_md" in deliverable_ids
    assert "operations_manual_contract" in deliverable_ids
    assert "operations_skill_pack_md" in deliverable_ids
    assert "operations_skill_pack_contract" in deliverable_ids
    assert "standalone_agent_delivery_md" in deliverable_ids
    assert "standalone_agent_delivery_contract" in deliverable_ids
    assert "access_entrypoints_md" in deliverable_ids
    assert "access_entrypoints_contract" in deliverable_ids
    assert "frontend_access_entrypoints_prototype" in deliverable_ids
    assert "phase5_mock_baseline_md" in deliverable_ids
    assert "phase5_mock_baseline_contract" in deliverable_ids
    assert "real_sdk_enablement" in deliverable_ids
    assert "real_sdk_enablement_contract" in deliverable_ids
    assert "real_sdk_minimal_impl" in deliverable_ids
    assert "real_sdk_minimal_impl_contract" in deliverable_ids
    assert "real_sdk_dependency_env_gate" in deliverable_ids
    assert "real_sdk_dependency_env_gate_contract" in deliverable_ids
    assert "final_signoff" in entry_ids
    assert "final_signoff_contract" in entry_ids
    assert "operations_manual" in entry_ids
    assert "operations_manual_contract" in entry_ids
    assert "standalone_agent_delivery" in entry_ids
    assert "standalone_agent_delivery_contract" in entry_ids
    assert "access_entrypoints" in entry_ids
    assert "access_entrypoints_contract" in entry_ids
    assert "phase5_mock_baseline" in entry_ids
    assert "phase5_mock_baseline_contract" in entry_ids
    assert "real_sdk_minimal_impl" in entry_ids
    assert "real_sdk_minimal_impl_contract" in entry_ids
    assert "real_sdk_dependency_env_gate" in entry_ids
    assert "real_sdk_dependency_env_gate_contract" in entry_ids
    assert "access_preview" in entry_ids
    assert "test_operations_manual" in delivery_index["recommendedCommandIds"]
    assert "test_standalone_agent_delivery" in delivery_index["recommendedCommandIds"]
    assert "test_access_entrypoints" in delivery_index["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in delivery_index["recommendedCommandIds"]
    assert "test_final_signoff" in delivery_index["recommendedCommandIds"]

    core = next(item for item in delivery_contract["acceptanceChecklist"] if item["id"] == "core_deliverables_present")
    assert "final_signoff_md" in core["source"]["ids"]
    assert "final_signoff_contract" in core["source"]["ids"]
    assert "operations_manual_md" in core["source"]["ids"]
    assert "operations_manual_contract" in core["source"]["ids"]
    assert "operations_skill_pack_md" in core["source"]["ids"]
    assert "operations_skill_pack_contract" in core["source"]["ids"]
    assert "standalone_agent_delivery_md" in core["source"]["ids"]
    assert "standalone_agent_delivery_contract" in core["source"]["ids"]
    assert "access_entrypoints_md" in core["source"]["ids"]
    assert "access_entrypoints_contract" in core["source"]["ids"]
    assert "frontend_access_entrypoints_prototype" in core["source"]["ids"]
    assert "phase5_mock_baseline_md" in core["source"]["ids"]
    assert "phase5_mock_baseline_contract" in core["source"]["ids"]
    assert "real_sdk_enablement" in core["source"]["ids"]
    assert "real_sdk_enablement_contract" in core["source"]["ids"]
    assert "real_sdk_minimal_impl" in core["source"]["ids"]
    assert "real_sdk_minimal_impl_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate_contract" in core["source"]["ids"]
    assert "python -m pytest tests/test_operations_manual.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_operations_skill_pack.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_access_entrypoints.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_final_signoff.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_enablement.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in delivery_contract["recommendedCommands"]


def test_final_signoff_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/FINAL_SIGNOFF.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 签收顺序", "## 测试方式", "## 限制说明"]:
        assert heading in content

    assert "frontend/operations-launchpad.html" in content
    assert "frontend/operations-signoff.html" in content
    assert "frontend/delivery.html" in content
    assert "delivery/OPERATIONS_MANUAL.md" in content
    assert "skills/operations-skill-pack/SKILL.md" in content
    assert "delivery/STANDALONE_AGENT_DELIVERY.md" in content
    assert "delivery/ACCESS_ENTRYPOINTS.md" in content
    assert "delivery/PHASE5_MOCK_BASELINE.md" in content
    assert "frontend/access.html" in content
    assert "delivery/HIGH_RISK_MCP_HANDOFF.md" in content
    assert "python lab_cli.py phase1 check" in content
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert (
        "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json "
        "--output examples/output/phase1-acceptance-report.md"
    ) in content
    assert "python -m pytest tests/test_final_signoff.py" in content
    assert "python -m pytest tests/test_operations_manual.py" in content
    assert "python -m pytest tests/test_operations_skill_pack.py" in content
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in content
    assert "python -m pytest tests/test_access_entrypoints.py" in content
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in content
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in content
    assert "WAITING_REVIEW" in content
    assert "不接入真实大模型" in content
    assert "不启动真实智能体或真实 MCP Server" in content
    assert "不启动真实 HTTP 服务" in content


def test_final_signoff_ready_and_not_ready_rules_cover_safety():
    contract = load_json("delivery/final-signoff.json")
    ready_text = " ".join(contract["signoffDecision"]["readyWhen"])
    not_ready_text = " ".join(contract["signoffDecision"]["notReadyWhen"])

    assert "missingRequired=0" in ready_text
    assert "deliveryReady=175" in ready_text
    assert "deliveryRequired=175" in ready_text
    assert "Real LLM PoC adapter remains disabled" in ready_text
    assert "Real SDK minimal implementation shell remains default-disabled" in ready_text
    assert "Real SDK dependency and environment gate remains design-only" in ready_text
    assert "Real SDK dependency apply gate remains disabled" in ready_text
    assert "WAITING_REVIEW" in ready_text
    assert "real MCP Server" in ready_text
    assert "real publish flags remain false" in ready_text
    assert "not allowlisted" in not_ready_text
    assert "real LLM PoC gate" in not_ready_text
    assert "skips WAITING_REVIEW" in not_ready_text
