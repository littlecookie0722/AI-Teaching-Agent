# Real Demo Quick Commands

这份清单用于现场快速演示“真实大模型产出成果复放 + MCP 审核退回修改 + Mock 修订稿生成”。所有命令都是本地命令；不发送新的真实 LLM 请求，不读取密钥，不访问网络，不启动真实 MCP Server，不发布内容。

## 输入说明

- `examples/input/demo-source.md`: 用于创建本地 `WAITING_REVIEW` Lab 任务。
- `examples/output/real-llm-demo-bundle.json`: 已有真实 LLM Demo Bundle。
- `examples/output/real-llm-demo-acceptance-summary.json`: 已有演示验收摘要。
- `frontend/real-demo.html`: 只读真实成果演示页。
- `mcp-server/tools.manifest.json`: MCP 工具契约。

## 输出说明

- `examples/output/real-llm-demo-checklist.json`: 从已有 Bundle 和验收摘要重建的一键演示清单。
- `examples/output/demo-quick-lab-revision.json`: MCP Mock 修订再生成输出的本地 Lab DSL 草稿。
- 本地 `LAB_CLI_STORE` 指向的 JSON store：保存 AI Task、MCP 调用审计和修订请求记录。

## 命令示例

```powershell
$env:LAB_CLI_STORE="examples/output/real-demo-quick-store.json"
start .\frontend\real-demo.html
python lab_cli.py phase2 demo-bundle checklist --bundle examples/output/real-llm-demo-bundle.json --acceptance-summary examples/output/real-llm-demo-acceptance-summary.json --output examples/output/real-llm-demo-checklist.json
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md
python lab_cli.py mcp call --tool request_review_revision --arguments "{\"taskId\":\"<TASK_ID>\",\"reviewer\":\"teacher_1\",\"comment\":\"补充步骤截图验收标准。\",\"priority\":\"HIGH\",\"targetSections\":[\"steps\"]}"
python lab_cli.py mcp call --tool regenerate_from_revision_mock --arguments "{\"taskId\":\"<TASK_ID>\",\"reviewer\":\"teacher_1\",\"revisionRequestId\":\"<REVISION_REQUEST_ID>\",\"output\":\"examples/output/demo-quick-lab-revision.json\"}"
python lab_cli.py mcp audit --tool regenerate_from_revision_mock
```

`<TASK_ID>` 来自第 4 条命令返回的 `data.task.id`。`<REVISION_REQUEST_ID>` 来自第 5 条命令返回的 `data.response.data.revisionRequest.id`。

## 演示顺序

1. 打开 `frontend/real-demo.html`，说明这是已有真实输出复放，不是新请求。
2. 重建一键演示清单，确认 `readyForDemo=true`。
3. 创建一个本地 `WAITING_REVIEW` Lab 任务，作为 MCP 审核循环样例。
4. 调用 `request_review_revision` 写入审核退回意见。
5. 调用 `regenerate_from_revision_mock` 生成新的 `WAITING_REVIEW` 修订稿。
6. 用 `mcp audit` 展示工具调用审计。

## 验证方式

```powershell
python -m pytest tests/test_real_demo_quick_commands.py
```

## 限制说明

- 不发送新的真实 LLM 请求。
- 不读取或展示 API Key、Token、密码。
- 不访问网络，不启动真实 MCP Server 或 Agent。
- 不运行 Docker、pytest、Notebook kernel 或选手代码。
- 不自动通过、不批量变更、不自动发布、不真实发布。
- MCP 修订再生成只创建本地 Mock 修订稿，源任务仍保持 `WAITING_REVIEW`。
