# 02_ROADMAP

详见 `AI_PLATFORM_CODEX_FULL_GUIDE.md` 第 15 章和第 22 章。

## 当前路线结论

项目已经完成 Mock 基线、Provider 抽象、SDK 边界和 request-send 安全建模。当前封口点是：

```text
real-llm-request-send-attempt-gate-disabled
```

后续默认不再新增同义安全壳，不再继续扩展 `*-disabled`、`*-gate`、`*-executor`、`*-review-only` 链条。

## 下一阶段路线

1. SDK 安装执行收口说明：已完成，见 `docs/13_REAL_SDK_INSTALL_EXECUTION.md`。
2. 真实 SDK 依赖安装或依赖文件变更：已通过 `requirements.txt` 和 `python -m pip install -r requirements.txt` 确认。
3. SDK import 验证：已验证 `import openai`。
4. 环境变量存在性边界验证，不输出密钥值：已完成，见 `docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md`。
5. SDK client 构造边界验证：已完成 smoke test，未发请求，见 `docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md`。
6. 最小真实 LLM 单请求 PoC：已实现，见 `docs/15_REAL_LLM_MINIMAL_POC.md`；当前环境缺少真实 `OPENAI_API_KEY`，未执行在线请求。
7. 将真实 LLM 能力接回 Lab DSL 生成 Workflow：已实现，见 `docs/16_REAL_LLM_WORKFLOW_RECONNECT.md`。
8. Lab 生成核心业务参数与审核质量信号第一版：已实现，见 `docs/17_LAB_GENERATION_CORE_SIGNALS.md`。
9. 核心业务开发：下一步，优先增强真实 Lab prompt 匹配、试题转换、评分脚本生成、评分沙箱、审核中心和运营复用。

## 核心业务优先级

1. AI 生成教学实验。
2. AI 将旧实验改造成考试 / 竞赛试题。
3. AI 生成自动评分 DSL / 脚本计划。
4. 沙箱内机器自动判分。
5. VM / Notebook 环境管理。
6. MCP Tool 与 Agent 编排。

## 智能模式建议

- 文档、Mock、普通业务代码、测试修复：GPT-5.5 高智能模式。
- SDK 安装、依赖解析、环境变量读取边界、SDK import、client 构造、最小真实请求 PoC：GPT-5.5 超高智能模式。
