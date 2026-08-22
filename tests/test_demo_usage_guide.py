import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_demo_usage_guide_covers_deploy_start_and_capabilities():
    content = read("docs/23_DEMO_USAGE_GUIDE.md")

    assert "# 23_DEMO_USAGE_GUIDE" in content
    for heading in [
        "## 2. 本地部署",
        "## 3. 启动方式",
        "## 4. 推荐演示路径",
        "## 5. 当前能力清单",
        "## 6. 大模型配置",
        "## 7. 常用验证命令",
        "## 8. 安全边界",
        "## 9. 排错",
    ]:
        assert heading in content
    assert "python -m pip install -r requirements.txt" in content
    assert "python -c \"import openai, importlib.metadata as m; print(m.version('openai'))\"" in content
    assert "$env:LAB_CLI_STORE" in content
    assert "start .\\frontend\\real-demo.html" in content
    assert "start .\\frontend\\review-center.html" in content
    assert "start .\\frontend\\ppt-review.html" in content
    assert "start .\\frontend\\grading-report.html" in content
    assert "python lab_cli.py phase1 check" in content
    assert "python lab_cli.py mcp list" in content
    assert "python lab_cli.py mcp server-info" in content
    assert "默认工具 profile 是 `local-core-mvp`" in content
    assert "python lab_cli.py mcp stdio-smoke" in content
    assert "python lab_cli.py review revision-request" in content
    assert "python lab_cli.py review regenerate-mock" in content
    assert "python lab_cli.py mcp call --tool request_review_revision" not in content
    assert "python lab_cli.py mcp call --tool regenerate_from_revision_mock" not in content
    assert "python lab_cli.py mcp list --profile all" in content
    assert "newLlmRequestSent=false" in content
    assert "python -m pytest tests/test_backend_mock_api.py" in content


def test_demo_usage_guide_documents_real_demo_and_model_config_without_secret_values():
    content = read("docs/23_DEMO_USAGE_GUIDE.md")

    assert "RealDemoOneClickChecklist" in content
    assert "readyForDemo=true" in content
    assert "acceptance=7/7" in content
    assert "sections=6/6" in content
    assert "gradingEvidenceCoverage=100/100" in content
    assert "WAITING_REVIEW" in content
    assert "answerVisibleToCandidate=false" in content
    assert "delivery/REAL_DEMO_SCRIPT.md" in content
    assert "delivery/real-demo-script.json" in content
    assert "$env:OPENAI_API_KEY=\"<your-api-key>\"" in content
    assert "$env:OPENAI_MODEL=\"<model-name>\"" in content
    assert "$env:OPENAI_BASE_URL=\"<openai-compatible-base-url>\"" in content
    assert "$env:OPENAI_MODEL=\"mimo-v2.5-pro\"" in content
    assert "$env:OPENAI_BASE_URL=\"https://api.xiaomimimo.com/v1\"" in content
    assert "OPENAI_API_KEY" in content
    assert "OPENAI_MODEL" in content
    assert "OPENAI_BASE_URL" in content
    assert "不会自动加载 `.env` 文件" in content
    assert "不要把真实 key 写入 `.env.example`" in content
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", content)


def test_demo_usage_guide_documents_real_llm_commands_and_safety_limits():
    content = read("docs/23_DEMO_USAGE_GUIDE.md")

    assert "provider real-llm-sdk-client-boundary check" in content
    assert "provider real-llm-minimal-poc run" in content
    assert "phase2 workflow run" in content
    assert "python lab_cli.py agent real-demo run" in content
    assert "python -m pytest tests/test_real_demo_agent_runner.py" in content
    assert "--provider-mode real-llm-demo" in content
    assert "--explicit-real-call-opt-in" in content
    assert "--confirm-single-request" in content
    assert "--confirm-demo-real-dsl" in content
    assert "--confirm-waiting-review" in content
    assert "--confirm-no-auto-publish" in content
    assert "这会消耗真实模型额度" in content
    assert "不把真实 LLM 设置为默认 Provider" in content
    assert "不在日志、文档、前端或 Git 中写入 API Key" in content
    assert "不无沙箱执行选手代码" in content
