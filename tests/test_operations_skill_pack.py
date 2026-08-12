import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_operations_skill_pack_is_phase5_mock_only():
    contract = load_json("skills/operations-skill-pack.contract.json")

    assert contract["phase"] == "Phase 5"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["id"] == "operations_skill_pack"
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["realProviderEnabled"] is False
    assert contract["safety"]["realMcpServerStarted"] is False
    assert contract["safety"]["realCloudResourceChanged"] is False
    assert contract["safety"]["realCloudResourceCreated"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["unknownShellExecuted"] is False
    assert contract["safety"]["autoPublishAllowed"] is False
    assert contract["safety"]["realPublish"] is False
    assert contract["safety"]["promptMayBeEmbeddedInBusinessCode"] is False
    assert contract["safety"]["secretVisibleInFrontend"] is False
    assert contract["safety"]["answerVisibleToCandidate"] is False


def test_operations_skill_pack_inputs_outputs_exist():
    contract = load_json("skills/operations-skill-pack.contract.json")

    for entry in [*contract["inputs"], *contract["outputs"]]:
        assert entry.get("required") is True or entry.get("requiredForOperation") is True
        assert (ROOT / entry["path"]).exists()
        assert not entry["path"].startswith(("http://", "https://"))


def test_operations_skill_pack_references_existing_base_skills_and_workflows():
    contract = load_json("skills/operations-skill-pack.contract.json")
    skill_manifest = load_json("skills/manifest.json")
    prompt_manifest = load_json("prompts/manifest.json")
    workflow_manifest = load_json("ai-workflows/workflow.manifest.json")

    skill_ids = {skill["id"] for skill in skill_manifest["skills"]}
    prompt_ids = {prompt["id"] for prompt in prompt_manifest["prompts"]}
    workflow_ids = {workflow["id"] for workflow in workflow_manifest["workflows"]}

    assert set(contract["baseSkillIds"]) == {"lab-generation", "exam-generation", "grading-script-generation", "ppt-generation"}
    assert set(contract["baseSkillIds"]).issubset(skill_ids)

    for step in contract["workflowSequence"]:
        assert step["skillId"] in skill_ids
        assert step["workflowId"] in workflow_ids
        assert step["promptId"] in prompt_ids
        assert (ROOT / step["outputSchema"]).exists()
        assert step["expectedStatus"] == "WAITING_REVIEW"


def test_operations_skill_pack_commands_are_allowlisted():
    contract = load_json("skills/operations-skill-pack.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_operations_skill_pack" in contract["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in contract["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in contract["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in contract["recommendedCommandIds"]

    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert "|" not in command["command"]


def test_operations_skill_pack_is_registered_for_delivery_and_operations():
    delivery_contract = load_json("config/delivery-package.contract.json")
    operations_manual = load_json("delivery/operations-manual.json")
    final_signoff = load_json("delivery/final-signoff.json")

    deliverable_ids = {item["id"] for item in delivery_contract["deliverables"]}
    operations_input_ids = {item["id"] for item in operations_manual["inputs"]}
    signoff_input_ids = {item["id"] for item in final_signoff["inputs"]}

    assert "operations_skill_pack_md" in deliverable_ids
    assert "operations_skill_pack_contract" in deliverable_ids
    assert "phase5_mock_baseline_md" in deliverable_ids
    assert "phase5_mock_baseline_contract" in deliverable_ids
    assert "real_sdk_enablement" in deliverable_ids
    assert "real_sdk_enablement_contract" in deliverable_ids
    assert "real_sdk_minimal_impl" in deliverable_ids
    assert "real_sdk_minimal_impl_contract" in deliverable_ids
    assert "real_sdk_dependency_env_gate" in deliverable_ids
    assert "real_sdk_dependency_env_gate_contract" in deliverable_ids
    assert "operations_skill_pack" in operations_input_ids
    assert "operations_skill_pack_contract" in operations_input_ids
    assert "phase5_mock_baseline" in operations_input_ids
    assert "phase5_mock_baseline_contract" in operations_input_ids
    assert "real_sdk_enablement" in operations_input_ids
    assert "real_sdk_enablement_contract" in operations_input_ids
    assert "real_sdk_minimal_impl" in operations_input_ids
    assert "real_sdk_minimal_impl_contract" in operations_input_ids
    assert "real_sdk_dependency_env_gate" in operations_input_ids
    assert "real_sdk_dependency_env_gate_contract" in operations_input_ids
    assert "operations_skill_pack" in signoff_input_ids
    assert "operations_skill_pack_contract" in signoff_input_ids
    assert "phase5_mock_baseline" in signoff_input_ids
    assert "phase5_mock_baseline_contract" in signoff_input_ids
    assert "real_sdk_enablement" in signoff_input_ids
    assert "real_sdk_enablement_contract" in signoff_input_ids
    assert "real_sdk_minimal_impl" in signoff_input_ids
    assert "real_sdk_minimal_impl_contract" in signoff_input_ids
    assert "real_sdk_dependency_env_gate" in signoff_input_ids
    assert "real_sdk_dependency_env_gate_contract" in signoff_input_ids

    core = next(item for item in delivery_contract["acceptanceChecklist"] if item["id"] == "core_deliverables_present")
    assert "operations_skill_pack_md" in core["source"]["ids"]
    assert "operations_skill_pack_contract" in core["source"]["ids"]
    assert "phase5_mock_baseline_md" in core["source"]["ids"]
    assert "phase5_mock_baseline_contract" in core["source"]["ids"]
    assert "real_sdk_enablement" in core["source"]["ids"]
    assert "real_sdk_enablement_contract" in core["source"]["ids"]
    assert "real_sdk_minimal_impl" in core["source"]["ids"]
    assert "real_sdk_minimal_impl_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate_contract" in core["source"]["ids"]
    assert "python -m pytest tests/test_operations_skill_pack.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_enablement.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in delivery_contract["recommendedCommands"]


def test_operations_skill_pack_markdown_documents_usage_and_limits():
    content = (ROOT / "skills/operations-skill-pack/SKILL.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 使用步骤", "## 命令示例", "## 测试方式", "## 限制说明"]:
        assert heading in content

    assert "delivery/OPERATIONS_MANUAL.md" in content
    assert "delivery/FINAL_SIGNOFF.md" in content
    assert "delivery/PHASE5_MOCK_BASELINE.md" in content
    assert "lab-generation" in content
    assert "exam-generation" in content
    assert "grading-script-generation" in content
    assert "ppt-generation" in content
    assert "WAITING_REVIEW" in content
    assert "python -m pytest tests/test_operations_skill_pack.py" in content
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in content
    assert "python -m pytest tests/test_real_sdk_enablement.py" in content
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in content
    assert "不启动真实 Agent" in content
    assert "不接入真实大模型或真实 Provider" in content
