import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manifest():
    with (ROOT / "prompts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_prompt_manifest_is_phase1_mock_registry():
    manifest = load_manifest()

    assert manifest["phase"] == "Phase 1"
    assert manifest["mode"] == "MOCK_ONLY"
    assert manifest["globalRules"]["promptStorage"] == "prompts/"
    assert manifest["globalRules"]["businessCodeMayEmbedPrompts"] is False
    assert manifest["globalRules"]["realLlmCalled"] is False
    assert manifest["globalRules"]["secretsAllowedInPrompt"] is False


def test_prompt_manifest_ids_are_unique():
    manifest = load_manifest()
    ids = [prompt["id"] for prompt in manifest["prompts"]]

    assert len(ids) == len(set(ids))


def test_prompt_manifest_paths_exist_and_stay_under_prompts():
    manifest = load_manifest()
    prompts_root = ROOT / "prompts"

    for prompt in manifest["prompts"]:
        path = ROOT / prompt["path"]
        assert path.exists(), prompt["path"]
        assert path.is_file()
        assert path.resolve().is_relative_to(prompts_root.resolve())


def test_prompt_manifest_dsl_prompts_reference_existing_schemas_and_review_gate():
    manifest = load_manifest()
    dsl_kinds = {"Lab", "Exam", "Grading", "PPT"}

    for prompt in manifest["prompts"]:
        if prompt["outputKind"] in dsl_kinds:
            assert (ROOT / prompt["outputSchema"]).exists()
            assert prompt["defaultStatus"] == "WAITING_REVIEW"
            assert prompt["reviewRequired"] is True
            assert prompt["mode"] == "MOCK_ONLY"


def test_prompt_templates_include_required_frontmatter_markers():
    manifest = load_manifest()

    for prompt in manifest["prompts"]:
        content = (ROOT / prompt["path"]).read_text(encoding="utf-8")
        assert prompt["id"] in content
        assert "version" in content
        assert "mode" in content
        assert prompt["mode"] in content


def test_prompt_templates_do_not_contain_secret_placeholders():
    manifest = load_manifest()
    forbidden = ["api_key", "apikey", "token=", "password=", "secret="]

    for prompt in manifest["prompts"]:
        content = (ROOT / prompt["path"]).read_text(encoding="utf-8").lower()
        assert not any(item in content for item in forbidden)


def test_lab_generation_prompt_declares_real_minimal_context_mapping():
    content = (ROOT / "prompts/workflows/lab_generation.md").read_text(encoding="utf-8")

    assert "real-llm-minimal-poc-v2" in content
    assert "realMode: REAL_LLM_MINIMAL_SINGLE_REQUEST" in content
    assert "Lab generation context JSON" in content
    assert "spec.targetUsers" in content
    assert "metadata.durationMinutes" in content
    assert "metadata.difficulty" in content
    assert "metadata.tags" in content
    assert "teachingStyle" in content
    assert "Return JSON only" in content
    assert "at least 2 distinct learning objectives" in content
