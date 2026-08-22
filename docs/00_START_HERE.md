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

这是一个 AI 实训平台智能化升级项目，目标不是单点功能，而是一套 AI 原生实训基础设施。

## 当前开发重点

Phase 1 底座已经完成，当前默认推进真实演示稳定性和核心业务产品化：

```text
真实 LLM 输出与 DSL 归一化
审核详情与导入预览
Grading DSL / 受控评分
本地实体、状态和版本管理
核心前端、CLI、API、MCP
```

## 不要现在做什么

除非用户明确恢复，不要默认做：

```text
外部平台 API 对接
平台 import-send / import-status / 签收发布
新增同义安全壳
运营交付页和新运营材料
```

## 给 Codex 的第一条命令

```text
请阅读 AGENTS.md 和 docs/24_PROJECT_PROGRESS_MAP.md，
根据当前路线实现一个最小、可验证的核心业务增量。
```
