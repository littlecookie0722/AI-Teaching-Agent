# 14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION

本文件记录真实 SDK 环境变量存在性边界与 SDK client 构造边界的执行结果。它是执行证据，不是新的安全门禁、禁用壳或评审壳。

## 1. 状态

状态：已执行。

已完成前置步骤：

- `docs/13_REAL_SDK_INSTALL_EXECUTION.md`：SDK 安装与 `import openai` 验证。
- `python lab_cli.py provider real-llm-sdk-client-boundary check ...`：client 构造边界 smoke test。

当前封口点仍是：

```text
real-llm-request-send-attempt-gate-disabled
```

本步骤完成后，后续不得再新增环境变量检查禁用壳、client 构造禁用壳、请求发送前禁用壳或同义门禁，除非用户明确指定新的风险、输入、输出、验收标准和停止条件。

## 2. 执行范围

允许范围：

- 检查当前运行环境是否存在 `OPENAI_API_KEY`，只返回布尔值。
- 使用临时测试 key 构造 `OpenAI` client。
- 验证 SDK import、client class、secret redaction、no-call 标记。
- 记录 CLI JSON 摘要。

禁止范围：

- 不输出真实 API Key 值。
- 不发起真实 LLM 请求。
- 不执行 prompt。
- 不生成 Lab / Exam / Grading / PPT 内容。
- 不创建 AI Task。
- 不访问真实云资源。
- 不发布任何内容。

## 3. 环境变量存在性验证

执行日期：2026-06-06。

```powershell
@'
import os
print("openai_api_key_present=" + str("OPENAI_API_KEY" in os.environ).lower())
print("openai_api_key_value_returned=false")
'@ | python -
```

结果摘要：

```text
openai_api_key_present=false
openai_api_key_value_returned=false
```

说明：

- 当前 shell 未检测到真实 `OPENAI_API_KEY`。
- 验证只返回存在性布尔值，没有读取、打印或记录密钥值。

## 4. Client 构造 smoke test

使用临时测试 key 在当前命令进程内构造 client。该 key 只用于 SDK constructor smoke test，不是真实密钥，不会写入文件或 Git。

```powershell
$env:OPENAI_API_KEY='test-client-boundary-smoke-key'
python lab_cli.py provider real-llm-sdk-client-boundary check --provider openai --explicit-sdk-boundary-opt-in --explicit-client-boundary-opt-in --confirm-sdk-import --confirm-client-construction --confirm-secret-value-handling --confirm-no-network-call --confirm-no-real-llm-call
Remove-Item Env:\OPENAI_API_KEY
```

结果摘要：

```text
success=true
code=OK
sdkVersion=1.109.1
sdkImported=true
clientCreated=true
clientClassName=OpenAI
secretValueRead=true
secretValueReturned=false
secretValueLogged=false
networkAccess=false
realLlmCalled=false
generatedContentCreated=false
taskCreated=false
readyForFirstDryRunRequestReview=true
realCallAuthorized=false
```

## 5. 安全确认

- 当前真实环境变量存在性已检查，未输出密钥值。
- SDK client 构造已通过 smoke test。
- 临时测试 key 未进入文档外的持久化配置，也未写入代码。
- CLI 返回统一 JSON。
- JSON 中没有返回或记录测试 key。
- 未发起网络请求。
- 未调用真实 LLM。
- 未创建 AI Task。
- 未生成或发布任何 AI 内容。

## 6. 后续路线

下一步直接进入最小真实 LLM 单请求 PoC：

```text
Markdown / demo-source.md → Lab DSL JSON → Lab Schema 校验 → AI Task WAITING_REVIEW
```

PoC 执行前置条件：

- 用户在本机环境变量中设置真实 `OPENAI_API_KEY`。
- 必须通过 `--model` 或 `OPENAI_MODEL` 显式指定模型，不使用隐式默认模型名。
- 请求必须显式 opt-in。
- 只允许单次请求，不 batch、不 streaming。
- 请求结果必须通过 `templates/lab/lab.schema.json`。
- 生成结果必须进入 `WAITING_REVIEW`。
- 不允许自动发布。
