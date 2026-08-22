from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_real_llm_minimal_poc_doc_records_implemented_boundary_and_command():
    content = read("docs/15_REAL_LLM_MINIMAL_POC.md")

    assert "# 15_REAL_LLM_MINIMAL_POC" in content
    assert "状态：已实现，未在当前环境执行真实在线请求。" in content
    assert "不是新的安全门禁、禁用壳或评审壳" in content
    assert "provider real-llm-minimal-poc describe" in content
    assert "provider real-llm-minimal-poc run" in content
    assert "--explicit-real-call-opt-in" in content
    assert "--confirm-single-request" in content
    assert "--confirm-lab-only" in content
    assert "--confirm-waiting-review" in content
    assert "--confirm-no-auto-publish" in content
    assert "`--model` 或 `OPENAI_MODEL` 必须明确提供" in content
    assert "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED" in content
    assert "\"realLlmCalled\": true" in content
    assert "\"taskCreated\": true" in content
    assert "将真实 LLM 能力接回 Lab DSL 生成 Workflow" in content
    assert "docs/16_REAL_LLM_WORKFLOW_RECONNECT.md" in content
    assert "下一步进入核心业务开发" in content


def test_real_llm_minimal_poc_is_linked_from_entry_docs():
    readme = read("README.md")
    start_here = read("docs/00_START_HERE.md")
    roadmap = read("docs/02_ROADMAP.md")
    full_guide = read("docs/AI_PLATFORM_CODEX_FULL_GUIDE.md")
    cli_readme = read("cli/README.md")
    providers_readme = read("providers/README.md")

    assert "docs/15_REAL_LLM_MINIMAL_POC.md" in readme
    assert "docs/16_REAL_LLM_WORKFLOW_RECONNECT.md" in readme
    assert "最小真实 LLM 单请求 PoC 已实现" in readme
    assert "真实 LLM Lab Workflow 回接已实现" in readme
    assert "provider real-llm-minimal-poc run" in readme
    assert "phase2 workflow run --provider-mode real-llm-minimal" in readme
    assert "docs/15_REAL_LLM_MINIMAL_POC.md" in start_here
    assert "docs/16_REAL_LLM_WORKFLOW_RECONNECT.md" in start_here
    assert "不要回到新增同义门禁或禁用壳" in start_here
    assert "当前路线摘要" in roadmap
    assert "真实 LLM 输出质量与归一化" in roadmap
    assert "24_PROJECT_PROGRESS_MAP.md" in roadmap
    assert "最小真实 LLM 单请求 PoC：已实现" in full_guide
    assert "当前默认下一步是第 8 步核心业务开发" in full_guide
    assert "real-llm-minimal-poc run" in cli_readme
    assert "phase2 workflow run --provider-mode real-llm-minimal" in cli_readme
    assert "providers/real_llm_minimal_poc.py" in providers_readme


def test_real_llm_workflow_reconnect_doc_records_cli_and_limits():
    content = read("docs/16_REAL_LLM_WORKFLOW_RECONNECT.md")

    assert "# 16_REAL_LLM_WORKFLOW_RECONNECT" in content
    assert "状态：已实现，默认仍为 Mock。" in content
    assert "不是新的安全门禁、禁用壳或评审壳" in content
    assert "phase2 workflow run --provider-mode real-llm-minimal" in content
    assert "Exam / Grading / PPT 仍使用 MockProvider" in content
    assert "REAL_LLM_MINIMAL_LAB_WORKFLOW" in content
    assert "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED" in content
    assert "python -m pytest tests/test_provider_adapter_workflow.py tests/test_phase2_workflow_orchestrator.py tests/test_real_llm_minimal_poc.py" in content
