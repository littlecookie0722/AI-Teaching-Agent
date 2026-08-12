import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script():
    with (ROOT / "delivery/real-demo-script.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_checklist():
    with (ROOT / "examples/output/real-llm-demo-checklist.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scripts_manifest():
    with (ROOT / "scripts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_real_demo_script_replays_existing_real_outputs_only():
    script = load_script()

    assert script["phase"] == "Phase 2 Demo"
    assert script["mode"] == "REAL_LLM_DEMO_REPLAY_STATIC"
    assert script["safety"]["manualOnly"] is True
    assert script["safety"]["sourceBundleRealLlmCalled"] is True
    assert script["safety"]["newLlmRequestSent"] is False
    assert script["safety"]["secretsRead"] is False
    assert script["safety"]["networkAccess"] is False
    assert script["safety"]["realMcpServerStarted"] is False
    assert script["safety"]["realAgentStarted"] is False
    assert script["safety"]["realCloudResourceCreated"] is False
    assert script["safety"]["sandboxExecutedByScript"] is False
    assert script["safety"]["commandExecutedByScript"] is False
    assert script["safety"]["pytestExecutedByScript"] is False
    assert script["safety"]["notebookExecutedByScript"] is False
    assert script["safety"]["contestantCodeExecutedByScript"] is False
    assert script["safety"]["autoApproveAllowed"] is False
    assert script["safety"]["autoPublishAllowed"] is False
    assert script["safety"]["realPublish"] is False
    assert script["safety"]["secretVisibleInFrontend"] is False
    assert script["safety"]["answerVisibleToCandidate"] is False


def test_real_demo_script_inputs_outputs_exist():
    script = load_script()

    for item in [*script["inputs"], *script["outputs"]]:
        if not item.get("generated", False):
            assert (ROOT / item["path"]).exists()
        assert not item["path"].startswith(("http://", "https://"))


def test_real_demo_script_flow_is_short_ordered_and_manual():
    script = load_script()
    flow = script["demoFlow"]
    orders = [step["order"] for step in flow]
    ids = [step["id"] for step in flow]

    assert orders == list(range(1, 10))
    assert len(ids) == len(set(ids))
    assert ids == [
        "read_real_demo_boundary",
        "open_real_demo",
        "confirm_generated_dsl_waiting_review",
        "open_review_center",
        "open_ppt_review",
        "open_grading_report",
        "demo_mcp_review_revision_loop",
        "validate_one_click_checklist",
        "confirm_blocked_actions",
    ]
    assert all(step["manualOnly"] is True for step in flow)
    assert all(step["expectedSignal"] for step in flow)
    assert all(step["speakerCue"] for step in flow)
    for step in flow:
        action = step.get("operatorAction")
        if action:
            assert action.startswith(("start .\\frontend\\", "python lab_cli.py "))
        if step.get("evidencePath"):
            assert (ROOT / step["evidencePath"]).exists()
        if step.get("generatedEvidencePath"):
            assert step["generatedEvidencePath"] == "examples/output/real-llm-demo-checklist.json"


def test_real_demo_script_matches_one_click_checklist_summary():
    script = load_script()
    checklist = load_checklist()
    signal_ids = {signal["id"] for signal in script["acceptanceSignals"]}
    section_ids = [section["id"] for section in checklist["sections"]]

    assert checklist["component"] == "RealDemoOneClickChecklist"
    assert checklist["summary"]["readyForDemo"] is True
    assert checklist["summary"]["acceptancePassed"] is True
    assert checklist["summary"]["acceptancePassedCount"] == 7
    assert checklist["summary"]["sectionPassedCount"] == checklist["summary"]["sectionTotal"] == 6
    assert checklist["summary"]["gradingEvidenceCoverageEarnedScore"] == 100
    assert checklist["summary"]["gradingEvidenceCoverageTotalScore"] == 100
    assert {
        "generated_dsl",
        "candidate_preview",
        "grading_evidence_coverage",
        "pptx_artifact",
        "review_and_mcp",
        "safety_boundaries",
    } == set(section_ids)
    assert {
        "real_demo_ready_for_demo",
        "acceptance_7_of_7",
        "sections_6_of_6",
        "generated_dsl_waiting_review",
        "candidate_preview_safe",
        "grading_coverage_complete",
        "review_mcp_visible",
        "mcp_revision_loop_mock_only",
        "real_actions_disabled",
    } <= signal_ids


def test_real_demo_script_references_allowlisted_validation_commands():
    script = load_script()
    manifest = load_scripts_manifest()
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(script["recommendedCommandIds"]).issubset(allowed)
    command_steps = [step for step in script["demoFlow"] if step.get("commandId")]
    assert {step["commandId"] for step in command_steps} == {"test_cli"}
    assert command_steps[0]["secondaryCommandId"] == "test_frontend_contract"
    assert allowed["test_cli"]["requiresNetwork"] is False
    assert allowed["test_frontend_contract"]["requiresNetwork"] is False


def test_real_demo_script_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/REAL_DEMO_SCRIPT.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 演示顺序", "## 验证方式", "## 限制说明"]:
        assert heading in content
    assert "frontend/real-demo.html" in content
    assert "frontend/review-center.html" in content
    assert "frontend/ppt-review.html" in content
    assert "frontend/grading-report.html" in content
    assert "RealDemoOneClickChecklist" in content
    assert "readyForDemo=true" in content
    assert "acceptance=7/7" in content
    assert "sections=6/6" in content
    assert "gradingEvidenceCoverage=100/100" in content
    assert "WAITING_REVIEW" in content
    assert "request_review_revision" in content
    assert "regenerate_from_revision_mock" in content
    assert "newLlmRequestSent=false" in content
    assert "answerVisibleToCandidate=false" in content
    assert "autoApproveAllowed=false" in content
    assert "realPublishAllowed=false" in content
    assert "python lab_cli.py phase2 demo-bundle checklist" in content
    assert "python -m pytest tests/test_real_demo_script.py" in content
    assert "不发送新的真实 LLM 请求" in content
    assert "不读取或展示 API Key" in content
    assert "不运行 Docker、pytest、Notebook kernel 或选手代码" in content
