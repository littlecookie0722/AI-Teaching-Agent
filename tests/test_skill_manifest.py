import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_manifest():
    return load_json("skills/manifest.json")


def test_skill_manifest_is_phase1_mock_registry():
    manifest = load_manifest()

    assert manifest["phase"] == "Phase 1"
    assert manifest["mode"] == "MOCK_ONLY"
    assert manifest["globalRules"]["realLlmCalled"] is False
    assert manifest["globalRules"]["realCloudResourceCreated"] is False
    assert manifest["globalRules"]["contestantCodeExecuted"] is False
    assert manifest["globalRules"]["outputMustBeDsl"] is True


def test_skill_manifest_ids_are_unique_and_files_exist():
    manifest = load_manifest()
    ids = [skill["id"] for skill in manifest["skills"]]

    assert len(ids) == len(set(ids))
    for skill in manifest["skills"]:
        skill_path = ROOT / skill["path"]
        assert skill_path.exists(), skill["path"]
        assert skill_path.is_file()
        content = skill_path.read_text(encoding="utf-8")
        assert f"name: {skill['id']}" in content


def test_skill_manifest_references_existing_prompts_and_prompt_ids():
    manifest = load_manifest()
    prompts = load_json("prompts/manifest.json")
    prompt_ids = {prompt["id"] for prompt in prompts["prompts"]}

    for skill in manifest["skills"]:
        if "promptId" in skill:
            assert skill["promptId"] in prompt_ids
            assert (ROOT / skill["promptPath"]).exists()


def test_skill_manifest_references_existing_workflows():
    manifest = load_manifest()
    workflows = load_json("ai-workflows/workflow.manifest.json")
    workflow_ids = {workflow["id"] for workflow in workflows["workflows"]}

    for skill in manifest["skills"]:
        if "workflowId" in skill:
            assert skill["workflowId"] in workflow_ids


def test_skill_manifest_references_existing_schemas_and_examples():
    manifest = load_manifest()

    for skill in manifest["skills"]:
        if "outputSchema" in skill:
            assert (ROOT / skill["outputSchema"]).exists(), skill["outputSchema"]
            assert (ROOT / skill["exampleOutput"]).exists(), skill["exampleOutput"]
        assert skill["reviewRequired"] is True
        assert skill["mode"] == "MOCK_ONLY"


def test_skill_manifest_covers_all_generation_kinds():
    manifest = load_manifest()
    output_kinds = {skill["outputKind"] for skill in manifest["skills"] if skill["outputKind"] != "OperationSkillPack"}

    assert output_kinds == {"Lab", "Exam", "Grading", "PPT"}


def test_skill_manifest_registers_operations_skill_pack():
    manifest = load_manifest()
    skills = {skill["id"]: skill for skill in manifest["skills"]}

    skill_pack = skills["operations-skill-pack"]
    assert skill_pack["outputKind"] == "OperationSkillPack"
    assert skill_pack["contractPath"] == "skills/operations-skill-pack.contract.json"
    assert (ROOT / skill_pack["contractPath"]).exists()
    assert set(skill_pack["baseSkillIds"]) == {"lab-generation", "exam-generation", "grading-script-generation", "ppt-generation"}
    assert set(skill_pack["baseSkillIds"]).issubset(skills)
    assert skill_pack["realAgentStarted"] is False
    assert skill_pack["realLlmCalled"] is False
    assert skill_pack["publishBlockedUntilApproved"] is True
