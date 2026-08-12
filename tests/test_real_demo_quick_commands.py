import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_quick_commands():
    with (ROOT / "delivery/real-demo-quick-commands.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_real_demo_quick_commands_are_local_replay_only():
    quick = load_quick_commands()

    assert quick["phase"] == "Phase 2 Demo"
    assert quick["mode"] == "REAL_LLM_DEMO_REPLAY_STATIC"
    assert quick["safety"]["newLlmRequestSent"] is False
    assert quick["safety"]["secretsRead"] is False
    assert quick["safety"]["networkAccess"] is False
    assert quick["safety"]["realMcpServerStarted"] is False
    assert quick["safety"]["realAgentStarted"] is False
    assert quick["safety"]["sandboxExecutedByCommands"] is False
    assert quick["safety"]["contestantCodeExecutedByCommands"] is False
    assert quick["safety"]["autoApproveAllowed"] is False
    assert quick["safety"]["batchStateChangeAllowed"] is False
    assert quick["safety"]["realPublish"] is False
    assert quick["safety"]["sourceTaskStatusUnchanged"] is True
    assert quick["safety"]["newTaskWaitingReview"] is True


def test_real_demo_quick_commands_inputs_outputs_and_order():
    quick = load_quick_commands()

    for item in quick["inputs"]:
        assert (ROOT / item["path"]).exists()
        assert item["required"] is True
    for item in quick["outputs"]:
        if not item.get("generated", False):
            assert (ROOT / item["path"]).exists()
        assert item["localOnly"] is True

    commands = quick["commands"]
    assert [command["order"] for command in commands] == list(range(1, 8))
    assert [command["id"] for command in commands] == [
        "set_isolated_store",
        "open_real_demo_page",
        "rebuild_checklist",
        "create_waiting_review_lab_task",
        "request_review_revision",
        "regenerate_from_revision_mock",
        "inspect_mcp_revision_audit",
    ]
    assert commands[3]["capture"] == {"field": "data.task.id", "as": "TASK_ID"}
    assert commands[4]["capture"] == {
        "field": "data.response.data.revisionRequest.id",
        "as": "REVISION_REQUEST_ID",
    }


def test_real_demo_quick_commands_are_copyable_and_do_not_contain_secret_values():
    quick = load_quick_commands()
    blocked_fragments = quick["blockedCommandFragments"]

    for command in quick["commands"]:
        text = command["command"]
        assert text.startswith(("$env:LAB_CLI_STORE=", "start .\\frontend\\", "python lab_cli.py "))
        assert "sk-" not in text
        assert "<your-api-key>" not in text
        for fragment in blocked_fragments:
            assert fragment not in text

    command_text = "\n".join(command["command"] for command in quick["commands"])
    assert "request_review_revision" in command_text
    assert "regenerate_from_revision_mock" in command_text
    assert "phase2 demo-bundle checklist" in command_text
    assert "review publish" not in command_text


def test_real_demo_quick_commands_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/REAL_DEMO_QUICK_COMMANDS.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 命令示例", "## 演示顺序", "## 验证方式", "## 限制说明"]:
        assert heading in content
    assert "frontend/real-demo.html" in content
    assert "real-llm-demo-bundle.json" in content
    assert "real-llm-demo-checklist.json" in content
    assert "request_review_revision" in content
    assert "regenerate_from_revision_mock" in content
    assert "data.task.id" in content
    assert "data.response.data.revisionRequest.id" in content
    assert "WAITING_REVIEW" in content
    assert "python -m pytest tests/test_real_demo_quick_commands.py" in content
    assert "不发送新的真实 LLM 请求" in content
    assert "不读取或展示 API Key" in content
    assert "不自动通过、不批量变更、不自动发布、不真实发布" in content
    assert "sk-" not in content
