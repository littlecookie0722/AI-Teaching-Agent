from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_real_sdk_client_boundary_execution_doc_records_actual_boundary_smoke_test():
    content = read("docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md")

    assert "# 14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION" in content
    assert "状态：已执行" in content
    assert "执行证据，不是新的安全门禁、禁用壳或评审壳" in content
    assert "openai_api_key_present=false" in content
    assert "openai_api_key_value_returned=false" in content
    assert "test-client-boundary-smoke-key" in content
    assert "sdkImported=true" in content
    assert "clientCreated=true" in content
    assert "clientClassName=OpenAI" in content
    assert "secretValueReturned=false" in content
    assert "secretValueLogged=false" in content
    assert "networkAccess=false" in content
    assert "realLlmCalled=false" in content
    assert "readyForFirstDryRunRequestReview=true" in content
    assert "realCallAuthorized=false" in content
    assert "最小真实 LLM 单请求 PoC" in content


def test_real_sdk_client_boundary_execution_is_linked_from_entry_docs():
    readme = read("README.md")
    roadmap = read("docs/02_ROADMAP.md")
    install_doc = read("docs/13_REAL_SDK_INSTALL_EXECUTION.md")

    assert "docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md" in readme
    assert "真实 SDK 环境变量与 client 构造边界已完成" in readme
    assert "clientCreated=true" in readme
    assert "历史阶段参考" in roadmap
    assert "12_PHASE_CUTOVER_AND_CORE_BUSINESS.md" in roadmap
    assert "docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md" in install_doc
