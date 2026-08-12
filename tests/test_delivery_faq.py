import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_faq():
    with (ROOT / "delivery/phase1-faq.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scripts_manifest():
    with (ROOT / "scripts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_delivery_faq_is_phase1_mock_only():
    faq = load_faq()

    assert faq["phase"] == "Phase 1"
    assert faq["mode"] == "MOCK_ONLY"
    assert faq["safety"]["realLlmCalled"] is False
    assert faq["safety"]["realAgentStarted"] is False
    assert faq["safety"]["realCloudResourceCreated"] is False
    assert faq["safety"]["sandboxExecuted"] is False
    assert faq["safety"]["contestantCodeExecuted"] is False
    assert faq["safety"]["unknownShellExecuted"] is False
    assert faq["safety"]["autoPublishAllowed"] is False
    assert faq["safety"]["realPublish"] is False
    assert faq["safety"]["remoteUploadAllowed"] is False
    assert faq["safety"]["secretVisibleInFrontend"] is False


def test_delivery_faq_items_are_unique_and_cover_common_failures():
    faq = load_faq()
    ids = [item["id"] for item in faq["faqItems"]]
    categories = set(faq["categories"])

    assert len(ids) == len(set(ids))
    assert {
        "missing_input",
        "schema_validation_failed",
        "review_reject_requires_reason",
        "unreviewed_publish_blocked",
        "phase1_report_missing_package",
        "phase1_report_rejects_non_mock",
        "operations_launchpad_entry",
        "demo_order_unclear",
        "real_provider_disabled",
        "unknown_shell_not_executed",
        "wrong_cli_entrypoint",
        "generated_outputs_ignored",
        "pytest_dependency_missing",
    } <= set(ids)

    for item in faq["faqItems"]:
        assert item["category"] in categories
        assert item["title"]
        assert item["symptom"]
        assert item["likelyCause"]
        assert item["safeResolution"]
        assert item["blockedActions"]
        assert isinstance(item["phase1Safety"], dict)


def test_delivery_faq_recommended_commands_are_allowlisted_and_safe():
    faq = load_faq()
    manifest = load_scripts_manifest()
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}
    blocked_patterns = [pattern.lower() for pattern in manifest["blockedPatterns"]]

    assert set(faq["recommendedCommandIds"]).issubset(allowed)
    for command_id in faq["recommendedCommandIds"]:
        command = allowed[command_id]
        command_text = command["command"].lower()
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert not any(pattern in command_text for pattern in blocked_patterns)

    for item in faq["faqItems"]:
        assert set(item["verifyCommandIds"]).issubset(allowed)


def test_delivery_faq_paths_exist_or_are_generated_outputs():
    faq = load_faq()

    for item in [*faq["inputs"], *faq["outputs"]]:
        if not item.get("generated", False):
            assert (ROOT / item["path"]).exists()
        assert item.get("localOnly", True) is True

    for item in faq["faqItems"]:
        for path in item.get("relatedPaths", []):
            assert (ROOT / path).exists()
            assert not path.startswith(("http://", "https://"))
        for path in item.get("generatedRelatedPaths", []):
            assert path.startswith("examples/output/")


def test_delivery_faq_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/FAQ.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 测试方式", "## 限制说明"]:
        assert heading in content
    assert "frontend/operations-launchpad.html" in content
    assert "start .\\frontend\\operations-launchpad.html" in content
    assert "python lab_cli.py phase1 check" in content
    assert "DEMO_SCRIPT_CHECKLIST.md" in content
    assert "python -m pytest tests/test_demo_script_checklist.py" in content
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in content
    assert "python -m pytest tests/test_delivery_faq.py" in content
    assert "WAITING_REVIEW" in content
    assert "MOCK_ONLY" in content
    assert "不接入真实大模型" in content
    assert "不执行未知 Shell" in content
