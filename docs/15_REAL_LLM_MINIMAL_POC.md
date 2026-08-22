# 15_REAL_LLM_MINIMAL_POC

本文件记录最小真实 LLM 单请求 PoC 的实现状态。它是核心业务路径的一部分，不是新的安全门禁、禁用壳或评审壳。

## 1. 状态

状态：已实现，未在当前环境执行真实在线请求。

原因：

- 当前 shell 未检测到真实 `OPENAI_API_KEY`。
- 真实运行还需要显式指定 `--model` 或设置 `OPENAI_MODEL`。

本步骤对应 `docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md` 的第 6 步：

```text
最小真实 LLM 单请求 PoC
```

## 2. 输入说明

默认输入：

```text
examples/input/demo-source.md
```

可通过 `--input` 指定其他本地 Markdown / 文本材料。

运行前置条件：

- `openai` SDK 已安装并可导入。
- `OPENAI_API_KEY` 通过当前 shell 环境变量提供。
- `--model` 或 `OPENAI_MODEL` 必须明确提供，不使用隐式默认模型名。
- 必须显式传入真实调用确认项。
- Prompt 从 `prompts/workflows/lab_generation.md` 读取，当前真实最小请求版本为 `real-llm-minimal-poc-v2`。

## 3. 输出说明

默认输出：

```text
examples/output/real-llm-minimal-poc-lab.json
```

成功后会创建：

- Lab DSL JSON 文件。
- `LAB_GENERATION` AI Task。
- `LAB_DSL` Artifact 记录。
- Provider 调用审计记录。

强制输出边界：

- 只允许 Lab DSL。
- 结果必须通过 `templates/lab/lab.schema.json`。
- 生成内容状态必须是 `WAITING_REVIEW`。
- AI Task 状态必须是 `WAITING_REVIEW`。
- `autoPublishAllowed=false`。
- `realPublish=false`。
- 如果通过 Phase 2 Workflow 传入 `labGenerationContext`，真实请求会要求模型把目标用户、课时、难度、技术标签和教学风格映射到 Lab DSL 对应字段。

## 4. 命令示例

查看能力摘要：

```powershell
python lab_cli.py provider real-llm-minimal-poc describe
```

真实运行示例：

```powershell
$env:OPENAI_API_KEY="<real-api-key>"
python lab_cli.py provider real-llm-minimal-poc run --provider openai --input examples/input/demo-source.md --output examples/output/real-llm-minimal-poc-lab.json --model "<model-name>" --explicit-real-call-opt-in --confirm-single-request --confirm-lab-only --confirm-waiting-review --confirm-no-auto-publish
```

如果不想在命令行传模型，也可以设置：

```powershell
$env:OPENAI_MODEL="<model-name>"
```

## 5. CLI JSON 返回

缺少真实密钥时，命令安全失败并返回统一 JSON：

```json
{
  "success": false,
  "code": "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED",
  "message": "真实 LLM 最小 PoC 需要通过环境变量提供 OPENAI_API_KEY",
  "errors": [
    {
      "field": "OPENAI_API_KEY",
      "reason": "missing or empty"
    }
  ],
  "realLlmMinimalPocContext": {
    "requestSent": false,
    "networkAccess": false,
    "realLlmCalled": false,
    "taskCreated": false,
    "secretValueReturned": false
  }
}
```

成功时，CLI 返回产物路径、AI Task、Artifact 和 Provider Audit，不在 JSON envelope 中内嵌完整 DSL 内容：

```json
{
  "success": true,
  "code": "OK",
  "data": {
    "mode": "REAL_LLM_MINIMAL_SINGLE_REQUEST",
    "requestCount": 1,
    "singleRequestOnly": true,
    "realLlmCalled": true,
    "networkAccess": true,
    "schemaValidated": true,
    "generatedStatus": "WAITING_REVIEW",
    "promptVersion": "real-llm-minimal-poc-v2",
    "taskCreated": true,
    "dslPath": "examples/output/real-llm-minimal-poc-lab.json"
  }
}
```

## 6. 测试方式

本地无密钥测试：

```powershell
python lab_cli.py provider real-llm-minimal-poc run --provider openai --model test-model --explicit-real-call-opt-in --confirm-single-request --confirm-lab-only --confirm-waiting-review --confirm-no-auto-publish
```

专项测试：

```powershell
python -m pytest tests/test_real_llm_minimal_poc.py -q
```

回归测试：

```powershell
python -m pytest
```

专项测试使用 fake client 覆盖真实 SDK 调用路径，不消耗真实 API，不访问网络。

## 7. 限制说明

当前 PoC 不做：

- 不接入 Exam / Grading / PPT 生成。
- 不 batch。
- 不 streaming。
- 不自动重试。
- 不自动发布。
- 不真实创建云资源。
- 不执行选手代码。
- 不把真实 Provider 设为默认 Provider。

## 8. 下一步

第 7 步已经完成：

```text
将真实 LLM 能力接回 Lab DSL 生成 Workflow
```

实现记录见 `docs/16_REAL_LLM_WORKFLOW_RECONNECT.md`。当前已新增显式 provider 选择参数 `--provider-mode mock|real-llm-minimal`，默认仍为 `mock`。真实路径继续保持：

- 显式 opt-in。
- 单请求。
- Lab DSL schema 校验。
- `WAITING_REVIEW`。
- 可追溯的 task / artifact / provider audit。

下一步进入核心业务开发，优先增强 Lab 生成输入参数、质量信号和审核详情。
