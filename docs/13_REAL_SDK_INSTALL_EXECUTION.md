# 13_REAL_SDK_INSTALL_EXECUTION

本文件记录真实 OpenAI SDK 安装执行收口结果。它是执行证据，不是新的安全门禁、禁用壳或评审壳。

## 1. 状态

状态：已执行。

当前封口点仍是：

```text
real-llm-request-send-attempt-gate-disabled
```

本步骤完成后，后续不得再新增安装前禁用壳、请求发送禁用壳、执行器禁用壳或同义门禁，除非用户明确指定新的风险、输入、输出、验收标准和停止条件。

## 2. 执行范围

允许范围：

- 使用项目现有 `requirements.txt`。
- 执行真实 SDK 依赖安装或确认命令。
- 验证 `import openai`。
- 记录 SDK 版本与 import 结果。

禁止范围：

- 不发起真实 LLM 请求。
- 不读取或打印 API Key 值。
- 不把真实 Provider 设为默认 Provider。
- 不创建 AI Task。
- 不生成或发布真实实验、考试、评分内容。
- 不访问真实云资源。

## 3. 依赖策略

当前依赖文件：

```text
requirements.txt
```

当前 SDK 声明：

```text
openai>=1.0.0,<2.0.0
```

版本策略：保持当前 1.x 兼容范围，避免在最小 PoC 前引入跨主版本 SDK 变更。

## 4. 已执行命令

执行日期：2026-06-06。

```powershell
python -m pip install -r requirements.txt
```

结果摘要：

```text
Requirement already satisfied: openai<2.0.0,>=1.0.0 ... (1.109.1)
```

import 验证命令：

```powershell
@'
import importlib
import importlib.metadata as metadata
module = importlib.import_module("openai")
print("openai_imported=true")
print("openai_version=" + metadata.version("openai"))
print("openai_has_client=" + str(hasattr(module, "OpenAI")).lower())
'@ | python -
```

结果摘要：

```text
openai_imported=true
openai_version=1.109.1
openai_has_client=true
```

## 5. 安全确认

- SDK 安装命令已执行。
- `import openai` 已验证通过。
- `OpenAI` client 类存在。
- 未发起真实 LLM 请求。
- 未读取或输出 `OPENAI_API_KEY` 值。
- 未访问真实云资源。
- 未自动发布任何 AI 生成内容。

## 6. 后续路线

下一步直接进入：

```text
环境变量存在性边界 → SDK client 构造边界 → 最小真实 LLM 单请求 PoC → Lab DSL Workflow 接回 → 核心业务开发
```

环境变量存在性与 SDK client 构造边界执行记录见：

```text
docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md
```

环境变量与 client 构造仍遵守：

- API Key 只能来自环境变量。
- 不输出密钥值。
- client 构造阶段不发起模型请求。
- 最小真实请求只允许单次 Lab DSL JSON 生成。
- 输出必须通过 `templates/lab/lab.schema.json`。
- 生成结果必须进入 `WAITING_REVIEW`。

## 7. 参考

- OpenAI 官方文档说明 SDK 可用于本地开发环境，并通过环境变量配置 API Key：`https://platform.openai.com/docs/libraries`
