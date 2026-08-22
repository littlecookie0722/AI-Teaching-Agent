# 00_START_HERE

请从这里开始。

演示人员如果只想部署、启动并讲解当前演示版，请先看：

```text
docs/23_DEMO_USAGE_GUIDE.md
```

该文档包含本地依赖安装、静态页面入口、CLI / Backend Mock / MCP Mock 启动方式、当前能力清单，以及 `OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL` 的大模型配置说明。

## 继续开发时先看什么

当前执行约束只有两处：

```text
AGENTS.md
docs/24_PROJECT_PROGRESS_MAP.md
```

`AGENTS.md` 负责全局工作方式和安全边界；`docs/24_PROJECT_PROGRESS_MAP.md` 负责当前路线、优先级和功能停止线。`docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md`、`docs/02_ROADMAP.md` 和完整指南保留为阶段背景或技术参考，不再作为独立的逐回合规则源。

当前精简 MVP 的入口盘点、复用决策和实施顺序见：

```text
docs/28_SIMPLIFIED_MVP_ENTRYPOINTS.md
```

该文档是当前 P0 的实施说明，不新增上位约束；发生冲突时仍以 `AGENTS.md` 和进度地图为准。

真实 SDK 安装执行记录见：

```text
docs/13_REAL_SDK_INSTALL_EXECUTION.md
```

当前已执行 `python -m pip install -r requirements.txt` 并验证 `import openai`，但尚未发起真实 LLM 请求。

真实 SDK client 构造边界记录见：

```text
docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md
```

最小真实 LLM 单请求 PoC 实现记录见：

```text
docs/15_REAL_LLM_MINIMAL_POC.md
```

真实 LLM Lab Workflow 回接记录见：

```text
docs/16_REAL_LLM_WORKFLOW_RECONNECT.md
```

真实 SDK、真实 LLM 请求和相关环境变量仍然必须显式 opt-in，密钥不得写入代码或日志；当前具体开发路线以进度地图为准，不要回到新增同义门禁或禁用壳。

## 当前项目要做什么

这是一个独立运行的 AI 教学智能体。当前目标不是建设完整实训平台，而是让教师从一份 Markdown 教学材料得到一套可人工审核、可本地导出的 Lab + Exam 教学包；Grading 作为 Exam 的内部配套规则。

```text
Markdown 教学材料
→ Lab + Exam/Grading
→ Schema 校验
→ WAITING_REVIEW
→ 人工批准或退回
→ 本地导出
```

## 当前开发重点

Phase 1 底座和更大范围的本地 PoC 已经完成。当前只推进上述单一 MVP 闭环：

```text
Markdown 输入与真实 LLM 生成质量
Lab / Exam / Grading DSL 及跨产物校验
候选人安全预览
单一生成入口与单一审核入口
人工审核状态与本地教学包导出
```

## 不要现在做什么

除非用户明确恢复，不要默认做：

```text
PPT / PPTX 产品化
自动评分与受控沙箱生产化
本地实体和 import-preview / mock-import / import-dry-run 扩张
MCP / Agent 新能力和多页面工作台扩张
外部平台 API 对接
平台 import-send / import-status / 签收发布
VM / Notebook 和生产部署
新增同义安全壳
运营交付页和新运营材料
```

上述已有实现保留并进行必要的兼容性或安全修复，但不再同时作为当前 MVP 的交付目标。当前 MVP 验收后，PPT 产品化和自动评分产品化只能选择一项进入下一阶段。

## 给 Codex 的第一条命令

```text
请阅读 AGENTS.md 和 docs/24_PROJECT_PROGRESS_MAP.md，
根据当前路线实现一个最小、可验证的核心业务增量。
```
