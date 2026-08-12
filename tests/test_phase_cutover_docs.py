from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_agents_declares_cutover_stop_rule_and_next_mode_guidance():
    content = read("AGENTS.md")

    assert "阶段封口与防循环规则" in content
    assert "real-llm-request-send-attempt-gate-disabled" in content
    assert "不得继续创建新的 pre-install / request-send / executor / authorization / gate disabled 模块" in content
    assert "真实 SDK 安装执行" in content
    assert "建议智能模式" in content
    assert "超高智能模式" in content


def test_full_guide_declares_cutover_and_core_business_route():
    content = read("docs/AI_PLATFORM_CODEX_FULL_GUIDE.md")

    assert "# 22. 阶段封口与核心业务切换规则" in content
    assert "安全门禁不能无限拆分" in content
    assert "real-llm-request-send-attempt-gate-disabled" in content
    assert "不再新增同义或更细粒度" in content
    assert "SDK 安装执行收口说明" in content
    assert "最小真实 LLM 单请求 PoC" in content
    assert "当前默认下一步是第 8 步核心业务开发" in content
    assert "核心业务优先级" in content
    assert "AI 生成教学实验" in content
    assert "建议智能模式" in content


def test_cutover_guide_is_actionable_and_blocks_more_disabled_shells():
    content = read("docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md")

    for heading in [
        "## 1. 当前封口结论",
        "## 2. 下一阶段固定路线",
        "## 3. 真实 SDK 安装边界",
        "## 4. 最小真实 LLM PoC 边界",
        "## 5. 核心业务开发优先级",
        "## 6. 非目标",
        "## 7. Codex 下一步建议规则",
    ]:
        assert heading in content

    assert "real-llm-request-send-attempt-gate-disabled" in content
    assert "默认禁止继续新增同义或更细的安全壳" in content
    assert "任何新的 `*-gate-disabled`、`*-executor-disabled`、`*-review-only`" in content
    assert "运行明确的 SDK 安装命令" in content
    assert "不打印密钥值" in content
    assert "真实 LLM Workflow 回接边界" in content
    assert "phase2 workflow run --provider-mode real-llm-minimal" in content
    assert "Markdown / demo-source.md → Lab DSL JSON → Lab Schema 校验 → AI Task WAITING_REVIEW" in content
    assert "选手端预览，不含标准答案" in content
    assert "GPT-5.5 超高智能模式" in content


def test_start_here_and_roadmap_point_to_cutover_document():
    start = read("docs/00_START_HERE.md")
    roadmap = read("docs/02_ROADMAP.md")

    assert "docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md" in start
    assert "real-llm-request-send-attempt-gate-disabled" in start
    assert "不再新增同义安全壳" in roadmap
    assert "真实 SDK 依赖安装或依赖文件变更" in roadmap
    assert "docs/16_REAL_LLM_WORKFLOW_RECONNECT.md" in roadmap
    assert "核心业务优先级" in roadmap
    assert "GPT-5.5 超高智能模式" in roadmap
