from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_agents_declares_cutover_stop_rule_and_route_guidance():
    content = read("AGENTS.md")

    assert "## 0. 规则优先级与文档分工" in content
    assert "## 3. 当前范围与停止线" in content
    assert "real-llm-request-send-attempt-gate-disabled" in content
    assert "不得新增同义的 `*-disabled`、`*-gate`、`*-executor`、`*-authorization`、`*-review-only`、`pre-install` 或 `request-send` 模块" in content
    assert "真实 SDK、环境变量、client 构造或真实 LLM 请求必须显式 opt-in" in content


def test_full_guide_declares_cutover_and_core_business_route():
    content = read("docs/AI_PLATFORM_CODEX_FULL_GUIDE.md")

    assert "# 22. 阶段封口与核心业务切换规则（历史归档）" in content
    assert "当前封口、核心范围和路线停止线以 `AGENTS.md` 第 3 节及 `docs/24_PROJECT_PROGRESS_MAP.md` 为准" in content
    assert "安全门禁不能无限拆分" in content
    assert "real-llm-request-send-attempt-gate-disabled" in content
    assert "不再新增同义或更细粒度" in content
    assert "SDK 安装执行收口说明" in content
    assert "最小真实 LLM 单请求 PoC" in content
    assert "当前默认下一步是第 8 步核心业务开发" in content
    assert "核心业务优先级" in content
    assert "AI 生成教学实验" in content


def test_cutover_guide_is_actionable_and_blocks_more_disabled_shells():
    content = read("docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md")

    for heading in [
        "## 1. 当前封口结论",
        "## 2. 下一阶段固定路线",
        "## 3. 真实 SDK 安装边界",
        "## 4. 最小真实 LLM PoC 边界",
        "## 5. 核心业务开发优先级",
        "## 6. 非目标",
        "## 7. 下一步建议",
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


def test_start_here_and_roadmap_point_to_cutover_document():
    start = read("docs/00_START_HERE.md")
    roadmap = read("docs/02_ROADMAP.md")

    assert "docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md" in start
    assert "当前执行约束只有两处" in start
    assert "docs/24_PROJECT_PROGRESS_MAP.md" in start
    assert "当前执行路线以 [`24_PROJECT_PROGRESS_MAP.md`](24_PROJECT_PROGRESS_MAP.md) 为唯一状态源" in roadmap
    assert "真实 LLM 输出质量与归一化" in roadmap
    assert "历史阶段参考" in roadmap
