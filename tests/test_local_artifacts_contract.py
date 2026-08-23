import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_contract():
    with (ROOT / "config/local-artifacts.contract.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def gitignore_lines():
    return [
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_local_artifacts_contract_is_phase1_mock_only():
    contract = load_contract()

    assert contract["version"] == "0.1.1"
    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gitignorePath"] == ".gitignore"


def test_gitignore_contains_declared_ignored_artifacts():
    contract = load_contract()
    lines = set(gitignore_lines())

    for artifact in contract["ignoredArtifacts"]:
        assert artifact["pattern"] in lines


def test_allowlisted_files_are_not_ignored_by_final_exception():
    contract = load_contract()
    lines = gitignore_lines()

    for allowlisted in contract["trackedAllowList"]:
        allow_pattern = f"!{allowlisted}"
        assert (ROOT / allowlisted).exists()
        assert allow_pattern in lines

        conflicting_patterns = [
            artifact["pattern"]
            for artifact in contract["ignoredArtifacts"]
            if allowlisted != artifact["pattern"]
            and allowlisted.startswith(artifact["pattern"].rstrip("*"))
        ]
        if conflicting_patterns:
            assert lines.index(allow_pattern) > max(lines.index(pattern) for pattern in conflicting_patterns)


def test_secret_env_files_are_ignored_but_example_is_allowed():
    lines = gitignore_lines()

    assert ".env" in lines
    assert ".env.*" in lines
    assert "!.env.example" in lines
    assert lines.index("!.env.example") > lines.index(".env.*")


def test_generated_output_json_is_ignored_but_readme_is_allowed():
    lines = gitignore_lines()

    assert "examples/output/*.json" in lines
    assert "examples/output/*.md" in lines
    assert "!examples/output/README.md" in lines
    assert lines.index("!examples/output/README.md") > lines.index("examples/output/*.json")
    assert lines.index("!examples/output/README.md") > lines.index("examples/output/*.md")


def test_teaching_package_zip_exports_are_ignored():
    contract = load_contract()
    lines = gitignore_lines()

    assert "examples/output/teaching-packages/" in lines
    assert any(
        artifact["pattern"] == "examples/output/teaching-packages/"
        and artifact["category"] == "generated_output"
        for artifact in contract["ignoredArtifacts"]
    )


def test_contract_rules_cover_phase1_safety_boundary():
    rules = load_contract()["rules"]

    assert rules["realSecretsMustBeIgnored"] is True
    assert rules["envExampleMustRemainTracked"] is True
    assert rules["mockStoresMustBeIgnored"] is True
    assert rules["generatedReportsMustBeIgnored"] is True
    assert rules["teachingPackageExportsMustBeIgnored"] is True
    assert rules["cacheArtifactsMustBeIgnored"] is True
    assert rules["ignoreContractMustBeTested"] is True
