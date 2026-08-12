import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manifest():
    with (ROOT / "scripts/manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_runbook():
    with (ROOT / "scripts/phase1-demo.runbook.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_scripts_manifest_is_phase1_mock_contract():
    manifest = load_manifest()

    assert manifest["phase"] == "Phase 1"
    assert manifest["mode"] == "MOCK_ONLY"
    assert manifest["executionPolicy"]["unknownShellScriptsAllowed"] is False
    assert manifest["executionPolicy"]["destructiveCommandsAllowed"] is False
    assert manifest["executionPolicy"]["productionAccessAllowed"] is False
    assert manifest["executionPolicy"]["cloudAccessAllowed"] is False
    assert manifest["executionPolicy"]["contestantCodeExecutionAllowed"] is False
    assert manifest["executionPolicy"]["secretLoggingAllowed"] is False


def test_scripts_manifest_command_ids_are_unique():
    manifest = load_manifest()
    ids = [command["id"] for command in manifest["allowedCommands"]]

    assert len(ids) == len(set(ids))


def test_scripts_manifest_allowed_commands_are_local_validation_only():
    manifest = load_manifest()

    for command in manifest["allowedCommands"]:
        assert command["category"] in {"validation", "mock_export"}
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert "|" not in command["command"]


def test_scripts_manifest_blocks_dangerous_patterns():
    manifest = load_manifest()
    blocked = set(manifest["blockedPatterns"])

    for pattern in ["rm -rf", "Remove-Item -Recurse -Force", "terraform destroy", "kubectl delete", "docker run"]:
        assert pattern in blocked


def test_scripts_manifest_allowed_commands_do_not_match_blocked_patterns():
    manifest = load_manifest()
    blocked_patterns = [pattern.lower() for pattern in manifest["blockedPatterns"]]

    for command in manifest["allowedCommands"]:
        command_text = command["command"].lower()
        assert not any(pattern.lower() in command_text for pattern in blocked_patterns)


def test_scripts_manifest_write_paths_are_scoped_to_examples_output():
    manifest = load_manifest()

    for command in manifest["allowedCommands"]:
        if command["writesToWorkspace"]:
            allowed_paths = command.get("allowedWritePaths", [])
            assert allowed_paths
            assert all(path.startswith("examples/output/") for path in allowed_paths)


def test_scripts_manifest_demo_runbooks_are_manual_and_safe():
    manifest = load_manifest()
    allowed_ids = {command["id"] for command in manifest["allowedCommands"]}

    assert manifest["demoRunbooks"]
    for runbook in manifest["demoRunbooks"]:
        assert runbook["manualOnly"] is True
        assert runbook["requiresHumanInitiatedRun"] is True
        assert runbook["requiresNetwork"] is False
        assert runbook["unknownShellScriptsAllowed"] is False
        assert runbook["contestantCodeExecutionAllowed"] is False
        assert runbook["autoPublishAllowed"] is False
        assert runbook["realPublish"] is False
        assert set(runbook["allowedCommandIds"]).issubset(allowed_ids)
        assert (ROOT / runbook["contractPath"]).exists()
        assert (ROOT / runbook["readmePath"]).exists()
        assert "test_demo_script_checklist" in runbook["allowedCommandIds"]
        assert "test_final_signoff" in runbook["allowedCommandIds"]
        assert "test_operations_manual" in runbook["allowedCommandIds"]
        assert "test_operations_skill_pack" in runbook["allowedCommandIds"]
        assert "test_standalone_agent_delivery" in runbook["allowedCommandIds"]
        assert "test_access_entrypoints" in runbook["allowedCommandIds"]
        assert "test_phase5_mock_baseline" in runbook["allowedCommandIds"]
        assert "test_real_sdk_minimal_impl" in runbook["allowedCommandIds"]
        assert "test_real_sdk_dependency_env_gate" in runbook["allowedCommandIds"]
        assert "frontend/operations-launchpad.html" in runbook["previewTargets"]
        assert "frontend/access.html" in runbook["previewTargets"]
        assert "frontend/operations-presenter.html" in runbook["previewTargets"]
        assert "frontend/operations-demo-script.html" in runbook["previewTargets"]
        assert all((ROOT / path).exists() for path in runbook["previewTargets"])
        assert all(path.startswith("examples/output/") for path in runbook.get("allowedWritePaths", []))


def test_phase1_demo_runbook_uses_allowlisted_commands_only():
    manifest = load_manifest()
    runbook = load_runbook()
    commands_by_id = {command["id"]: command for command in manifest["allowedCommands"]}
    blocked_patterns = [pattern.lower() for pattern in manifest["blockedPatterns"]]

    assert runbook["phase"] == "Phase 1"
    assert runbook["mode"] == "MOCK_ONLY"
    assert runbook["executionPolicy"]["manualOnly"] is True
    assert runbook["executionPolicy"]["allowedCommandIdsOnly"] is True
    assert runbook["executionPolicy"]["unknownShellScriptsAllowed"] is False
    assert runbook["executionPolicy"]["realLlmCalled"] is False
    assert runbook["executionPolicy"]["realAgentStarted"] is False
    assert runbook["executionPolicy"]["realCloudResourceCreated"] is False
    assert runbook["executionPolicy"]["sandboxExecuted"] is False
    assert runbook["executionPolicy"]["autoPublishAllowed"] is False
    assert runbook["executionPolicy"]["realPublish"] is False

    for item in [*runbook["inputs"], *runbook["outputs"]]:
        if not item.get("generated", False):
            assert (ROOT / item["path"]).exists()

    output_paths = {item["path"] for item in runbook["outputs"]}
    step_ids = {step["id"] for step in runbook["steps"]}
    assert "frontend/operations-launchpad.html" in output_paths
    assert "frontend/access.html" in output_paths
    assert "frontend/operations-presenter.html" in output_paths
    assert "frontend/operations-demo-script.html" in output_paths
    assert "read_demo_script_checklist" in step_ids
    assert "read_final_signoff" in step_ids
    assert "read_operations_manual" in step_ids
    assert "read_operations_skill_pack" in step_ids
    assert "test_standalone_agent_delivery" in step_ids
    assert "test_access_entrypoints" in step_ids
    assert "read_access_entrypoints" in step_ids
    assert "read_phase5_mock_baseline" in step_ids
    assert "test_phase5_mock_baseline" in step_ids
    assert "test_real_sdk_minimal_impl" in step_ids
    assert "test_real_sdk_dependency_env_gate" in step_ids
    assert "test_backend_mock_api" in step_ids
    assert "open_access_preview" in step_ids
    assert "open_operations_launchpad" in step_ids
    assert "open_operations_presenter" in step_ids
    assert "open_operations_demo_script" in step_ids
    assert "test_demo_script_checklist" in step_ids
    assert "test_final_signoff" in step_ids
    assert "test_operations_manual" in step_ids
    assert "test_operations_skill_pack" in step_ids

    for step in runbook["steps"]:
        assert step["manualOnly"] is True
        assert step["requiresNetwork"] is False
        command = step.get("command")
        if command:
            assert not any(pattern in command.lower() for pattern in blocked_patterns)

        if step["type"] == "allowed_command":
            allowed_command = commands_by_id[step["allowedCommandId"]]
            assert step["command"] == allowed_command["command"]
            assert step["writesToWorkspace"] == allowed_command["writesToWorkspace"]
        elif step["type"] == "manual_preview":
            assert step["allowedCommandId"] is None
            assert command.startswith("start .\\frontend\\")
            assert step["writesToWorkspace"] is False
        elif step["type"] == "manual_review":
            assert step["allowedCommandId"] is None
            assert command is None


def test_phase1_demo_runbook_markdown_documents_inputs_outputs_and_limits():
    content = (ROOT / "scripts/phase1-demo.runbook.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 测试方式", "## 限制说明"]:
        assert heading in content
    assert "frontend/operations-launchpad.html" in content
    assert "frontend/operations-presenter.html" in content
    assert "frontend/operations-demo-script.html" in content
    assert "DEMO_SCRIPT_CHECKLIST.md" in content
    assert "python -m pytest tests/test_demo_script_checklist.py" in content
    assert "start .\\frontend\\operations-launchpad.html" in content
    assert "start .\\frontend\\operations-presenter.html" in content
    assert "start .\\frontend\\operations-demo-script.html" in content
    assert "python lab_cli.py phase1 check" in content
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in content
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in content
    assert "python -m pytest tests/test_phase2_provider_plan.py" in content
    assert "python -m pytest tests/test_cli.py" in content
    assert "python -m pytest tests/test_backend_mock_api.py" in content
    assert "python -m pytest tests/test_provider_adapter.py" in content
    assert "python -m pytest tests/test_provider_adapter_workflow.py" in content
    assert "python -m pytest tests/test_mcp_mock_tools.py" in content
    assert "python -m pytest tests/test_high_risk_mcp_safety_contract.py" in content
    assert "python -m pytest tests/test_high_risk_mcp_handoff.py" in content
    assert "FINAL_SIGNOFF.md" in content
    assert "python -m pytest tests/test_final_signoff.py" in content
    assert "OPERATIONS_MANUAL.md" in content
    assert "python -m pytest tests/test_operations_manual.py" in content
    assert "operations-skill-pack" in content
    assert "python -m pytest tests/test_operations_skill_pack.py" in content
    assert "STANDALONE_AGENT_DELIVERY.md" in content
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in content
    assert "ACCESS_ENTRYPOINTS.md" in content
    assert "frontend/access.html" in content
    assert "python -m pytest tests/test_access_entrypoints.py" in content
    assert "PHASE5_MOCK_BASELINE.md" in content
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in content
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in content
    assert "reviewPriorityQueue" in content
    assert "MCP `get_review_task_summary`" in content
    assert "不执行未知 Shell 脚本" in content


def test_mcp_tool_call_audit_contract_references_allowlisted_commands():
    manifest = load_manifest()
    with (ROOT / "mcp-server/tool-call-audit.contract.json").open("r", encoding="utf-8") as file:
        contract = json.load(file)

    allowed_ids = {command["id"] for command in manifest["allowedCommands"]}
    assert set(contract["recommendedCommandIds"]) <= allowed_ids
