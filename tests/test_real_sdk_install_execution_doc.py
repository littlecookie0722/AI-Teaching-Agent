from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_real_sdk_install_execution_doc_records_actual_execution_without_new_gate():
    content = read("docs/13_REAL_SDK_INSTALL_EXECUTION.md")

    assert "# 13_REAL_SDK_INSTALL_EXECUTION" in content
    assert "状态：已执行" in content
    assert "执行证据，不是新的安全门禁、禁用壳或评审壳" in content
    assert "real-llm-request-send-attempt-gate-disabled" in content
    assert "python -m pip install -r requirements.txt" in content
    assert "openai>=1.0.0,<2.0.0" in content
    assert "openai_version=1.109.1" in content
    assert "import openai" in content
    assert "未发起真实 LLM 请求" in content
    assert "未读取或输出 `OPENAI_API_KEY` 值" in content
    assert "最小真实 LLM 单请求 PoC" in content


def test_entry_docs_point_to_real_sdk_install_execution_record():
    readme = read("README.md")
    start = read("docs/00_START_HERE.md")
    roadmap = read("docs/02_ROADMAP.md")

    assert "docs/13_REAL_SDK_INSTALL_EXECUTION.md" in readme
    assert "真实 SDK 安装执行收口已完成" in readme
    assert "python -c \"import openai" in readme
    assert "docs/13_REAL_SDK_INSTALL_EXECUTION.md" in start
    assert "尚未发起真实 LLM 请求" in start
    assert "SDK 安装执行收口说明：已完成" in roadmap
    assert "SDK import 验证：已验证 `import openai`" in roadmap
