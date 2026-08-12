# Phase Cutover And Core Business Guide

本文件用于防止项目继续陷入无限新增安全门禁、禁用壳或评审壳。后续 Codex / AI Coding Agent 必须优先遵守这里的封口规则，再进入真实 SDK 安装和核心业务开发。

## 1. 当前封口结论

安装前与真实请求发送前的安全建模已经收口。

最后一个允许的请求发送前禁用壳是：

```text
real-llm-request-send-attempt-gate-disabled
```

从该点之后，默认禁止继续新增同义或更细的安全壳，包括：

- `final-real-request-send-execution-disabled`
- `real-request-send-final-executor-disabled`
- `request-send-post-attempt-gate-disabled`
- `sdk-install-preflight-disabled`
- `dependency-install-final-executor-disabled`
- 任何新的 `*-gate-disabled`、`*-executor-disabled`、`*-review-only`，如果它只是再次证明“不执行真实动作”

例外条件：用户明确指定要新增某个安全壳，并给出具体风险、输入、输出、验收标准和停止条件。

## 2. 下一阶段固定路线

后续不再从安全壳继续拆分，直接进入以下路线：

1. SDK 安装执行收口说明：确认不再追加安装前禁用壳。
2. 真实 SDK 依赖安装或依赖文件变更：更新依赖文件或执行安装命令。
3. SDK import 验证：只验证 SDK 可导入，不发请求。
4. 环境变量边界：只检查变量存在性，不输出密钥值。
5. SDK client 构造边界：构造 client 但不发起模型请求。
6. 最小真实 LLM 单请求 PoC：仅限单次 Lab JSON 生成请求，输出必须过 Lab Schema，并进入 `WAITING_REVIEW`。
7. 接回核心 Workflow：已完成，真实 Provider 作为显式可选路径接入 Lab DSL 生成，见 `docs/16_REAL_LLM_WORKFLOW_RECONNECT.md`。
8. 进入核心业务开发：下一步默认做 Lab 生成业务增强、审核质量信号、Prompt / Provider 可观测和后续 Exam / Grading 真实能力分层接入。

这 8 步是上限，不得在其中再插入新的安全壳层级。

## 3. 真实 SDK 安装边界

SDK 安装阶段允许：

- 检查当前依赖管理方式。
- 更新 `requirements.txt` 或项目实际使用的依赖文件。
- 运行明确的 SDK 安装命令。
- 验证 `import openai` 或等价 SDK import。
- 记录版本、安装结果和回滚方式。

SDK 安装阶段禁止：

- 发起真实 LLM 请求。
- 输出或记录 API Key。
- 修改业务 Workflow 为默认真实 Provider。
- 自动创建 AI Task 或发布内容。
- 访问真实云资源。

## 4. 最小真实 LLM PoC 边界

最小真实 LLM PoC 只允许一个业务场景：

```text
Markdown / demo-source.md → Lab DSL JSON → Lab Schema 校验 → AI Task WAITING_REVIEW
```

要求：

- Provider 必须显式 opt-in。
- API Key 只能来自环境变量。
- 不打印密钥值。
- 只允许单请求，不允许 batch，不允许 streaming。
- 输出必须通过 `templates/lab/lab.schema.json`。
- 生成结果必须进入 `WAITING_REVIEW`。
- 不允许自动发布。

## 4.1 真实 LLM Workflow 回接边界

当前已完成：

```text
phase2 workflow run --provider-mode real-llm-minimal
```

该路径只把真实 LLM 最小 PoC 接回 Lab DSL 生成：

- 默认 `--provider-mode mock` 不变。
- 显式 `--provider-mode real-llm-minimal` 时，只有 Lab DSL 使用真实 LLM 单请求。
- Exam / Grading / PPT 仍使用 MockProvider。
- Lab DSL 必须通过 schema，状态必须为 `WAITING_REVIEW`。
- Workflow Report、AI Task、Artifact、WorkflowRun 和 Provider 审计都会记录真实 Lab 调用边界。
- 不允许自动发布，不创建云资源，不启动 Agent，不执行沙箱或选手代码。

## 5. 核心业务开发优先级

真实 SDK 最小 PoC 后，优先开发以下业务能力。

### 5.1 AI 生成教学实验

输入：

- Markdown / README / Shell 静态分析结果
- 目标人群、课时、难度
- 可选技术栈标签

输出：

- Lab DSL
- AI Task
- 审核材料

验收：

- Lab DSL 通过 schema。
- 状态为 `WAITING_REVIEW`。
- 来源素材、Prompt、Provider、traceId 可追溯。

### 5.2 旧实验改造成考试 / 竞赛试题

输入：

- 已审核 Lab DSL
- Notebook 或实验说明

输出：

- Exam DSL
- Grading DSL
- 选手端预览，不含标准答案

验收：

- Exam / Grading DSL 均通过 schema。
- 标准答案不进入选手端字段。
- 生成结果进入 `WAITING_REVIEW`。

### 5.3 AI 生成自动评分脚本

输入：

- Exam DSL
- 评分规则说明
- 可用评分类型

输出：

- Grading DSL
- 评分计划
- 风险提示

验收：

- 不直接执行未知代码。
- 评分计划可解释。
- 高风险检查需要人工审核。

### 5.4 机器自动判分

输入：

- 学生提交
- 已审核 Grading DSL

输出：

- 评分报告 JSON
- stdout / stderr 摘要
- check 明细

验收：

- 选手代码只在沙箱中运行。
- 限制 CPU、内存、时间、网络和文件系统。
- 报告可解释、可审计。

### 5.5 VM / Notebook 环境管理

输入：

- 环境模板
- 资源规格
- 用户或课程上下文

输出：

- Environment 记录
- 审核任务或操作审计

验收：

- 真实云资源创建、销毁必须二次确认。
- 默认仍可使用 Mock 环境。

### 5.6 MCP 与 Agent 编排

输入：

- 稳定 CLI / API 工具
- Tool schema
- 风险等级

输出：

- MCP Tool
- Agent Workflow
- 审计记录

验收：

- Agent 只编排工具，不承载隐藏业务规则。
- 高风险工具只创建待审核意图。

## 6. 非目标

后续默认不做：

- 新增同义安全壳。
- 继续扩大门禁链条。
- 把真实 Provider 设为默认 Provider。
- 绕过 `WAITING_REVIEW`。
- 自动发布真实实验或考试。
- 无沙箱执行选手代码。
- 在前端、日志、测试输出中展示标准答案或密钥。

## 7. Codex 下一步建议规则

每次最终输出必须包含：

```text
建议智能模式：GPT-5.5 高智能模式 / GPT-5.5 超高智能模式
```

建议标准：

- 文档、Mock、普通业务代码、测试修复：GPT-5.5 高智能模式。
- SDK 安装、依赖解析、环境变量边界、SDK import、client 构造、最小真实 LLM 请求：GPT-5.5 超高智能模式。

## 8. 下一步推荐

当前推荐下一步：

```text
进入核心业务开发：
1. 增强 Lab DSL 生成输入参数：目标人群、课时、难度、技术栈标签和教学风格。
2. 增强 Lab DSL 生成质量信号：schema 校验、材料覆盖率、风险提示、审核重点。
3. 将 Prompt / Provider / traceId / responseId / usage 等信息纳入审核详情。
4. 继续保持 Exam / Grading / PPT 默认 Mock，后续按业务优先级分层接入真实 LLM。
```

建议智能模式：GPT-5.5 超高智能模式。
