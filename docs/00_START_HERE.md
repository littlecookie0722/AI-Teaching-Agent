# 00_START_HERE

请从这里开始。

演示人员如果只想部署、启动并讲解当前演示版，请先看：

```text
docs/23_DEMO_USAGE_GUIDE.md
```

该文档包含本地依赖安装、静态页面入口、CLI / Backend Mock / MCP Mock 启动方式、当前能力清单，以及 `OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL` 的大模型配置说明。

## 当前必须先看的封口规则

继续开发前必须阅读：

```text
docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md
```

该文档明确：`real-llm-request-send-attempt-gate-disabled` 是安装前与真实请求发送前的封口点。后续默认不再新增同义安全壳，下一阶段进入真实 SDK 安装、环境变量边界、SDK import/client 边界、最小真实 LLM 单请求 PoC 和核心业务开发。

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

当前已实现一次真实请求代码路径和 Phase 2 Lab Workflow 显式回接；由于当前 shell 未检测到真实 `OPENAI_API_KEY`，尚未执行在线请求。下一步默认进入核心业务开发，不要回到新增同义门禁或禁用壳。

## 当前项目要做什么

这是一个 AI 实训平台智能化升级项目，目标不是单点功能，而是一套 AI 原生实训基础设施。

## 第一个里程碑

先完成 Phase 1：

```text
目录结构
DSL Schema
CLI Mock
AI Task 状态模型
人工审核流
基础测试
```

## 不要现在做什么

不要现在做：

```text
真实大模型
真实云资源
真实 Agent
真实发布
真实判卷
复杂 UI
```

## 给 Codex 的第一条命令

```text
请阅读 AGENTS.md 和 docs/AI_PLATFORM_CODEX_FULL_GUIDE.md。
只完成 Phase 1 的项目底座搭建。
```
