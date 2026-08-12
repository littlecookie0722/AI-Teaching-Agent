# 27_MCP_LOCAL_CORE_CLIENT_USAGE

> Last updated: 2026-07-12
> Scope: local core MVP MCP client usage. This document is not a new gate, not an operations handoff, and not a real platform backend integration guide.

## 1. Purpose

This document tells a local MCP client or Agent how to connect to the project MCP stdio server and how to use only the stable `local-core-mvp` tool profile.

The current MCP boundary is:

```text
MCP client
  -> python -m mcp_server.stdio_server
  -> local-core-mvp tools
  -> Backend Mock / local repositories
  -> unified JSON
  -> WAITING_REVIEW / manual review / local import-preview
```

The MCP client must not call real platform import APIs, must not ask for `AGENT_API_TOKEN`, and must not publish generated content.

## 2. Client Config

Use stdio transport from the repository root:

The same ready-to-use example is available at
`examples/mcp/local-core-mcp.json`.

```json
{
  "mcpServers": {
    "ai-training-platform-local-core": {
      "command": "python",
      "args": ["-m", "mcp_server.stdio_server"],
      "cwd": "<PROJECT_ROOT>"
    }
  }
}
```

Replace `<PROJECT_ROOT>` with the absolute path of your local checkout. Keep
that machine-specific value in your local MCP client configuration; do not
commit it to the repository.

Optional local-only environment variables:

```powershell
$env:LAB_CLI_STORE="examples/output/mcp-local-core-store.json"
$env:LAB_BACKEND_CORE_DATABASE_URL="sqlite:///examples/output/backend-core-demo.sqlite3"
$env:LAB_BACKEND_GRADING_DB_PATH="examples/output/grading-local.sqlite3"
```

Do not configure `AGENT_API_TOKEN` for the current local core MVP.

## 3. Smoke Checks

Run these before wiring a real MCP client:

```powershell
python lab_cli.py mcp server-info
python lab_cli.py mcp server-tools
python lab_cli.py mcp stdio-smoke --input examples/input/demo-source.md --output examples/output/mcp-stdio-client-smoke.json
```

Expected boundary:

```text
activeToolProfile=local-core-mvp
networkListenerStarted=false
realAgentStarted=false
realPublish=false
```

### 3.1 Actual Local Client Acceptance

`stdio-smoke` verifies transport only. Use the following two-step command to
run a real local stdio client against the default profile. The first command
creates a Lab task through MCP and stops at `WAITING_REVIEW`:

```powershell
python lab_cli.py mcp stdio-local-core-demo `
  --input examples/input/demo-source.md `
  --work-dir examples/output/mcp-local-core-client `
  --reviewer teacher_1 `
  --output examples/output/mcp-local-core-client-draft.json
```

Approve the returned `generatedTask.id` explicitly outside the MCP client:

```powershell
$env:LAB_CLI_STORE="examples/output/mcp-local-core-client/mcp-local-core-client-store.json"
python lab_cli.py review approve --task-id <generated_task_id> --reviewer teacher_1
```

Then resume the local client with that approved task id:

```powershell
python lab_cli.py mcp stdio-local-core-demo `
  --input examples/input/demo-source.md `
  --work-dir examples/output/mcp-local-core-client `
  --reviewer teacher_1 `
  --approved-lab-task-id <generated_task_id> `
  --output examples/output/mcp-local-core-client-continuation.json
```

The continuation proves `tools/list`, material analysis, Lab generation,
review detail, import-preview, mock-import, import-dry-run, GradingJob /
GradingRecord reads, and MCP audit queries through the same stdio client. It
also verifies that `agent_internal_publish_request` returns
`MCP_TOOL_NOT_IN_PROFILE` under the default profile. The client itself never
approves a task and stops at `LOCAL_CORE_MVP_STOP_LINE_REACHED`.

## 4. Default Tool Profile

The default profile is `local-core-mvp` for all local MCP entry points:

```text
lab-cli mcp call
lab-cli mcp server-call
stdio tools/call
mcp_server.mock_tools.invoke_mcp_tool()
```

The default profile contains only stable local core tools:

- Runtime/config read-only: `get_real_llm_runtime_config`
- Material analysis: `analyze_material`
- Local generation: `generate_lab_from_source`, `generate_exam_from_lab`, `generate_ppt`
- Review read paths: `list_ai_tasks`, `get_ai_task`, `list_review_tasks`, `get_review_detail`, `get_review_task_summary`
- Grading evidence and review: `run_grading_evidence_auto`, `get_grading_result_preview`, `get_grading_evidence_readiness`, `record_review_decision_note`
- Local GradingJob / GradingRecord: `create_grading_job`, `run_grading_job`, `create_grading_record`, `review_grading_record`
- Local platform entity loop: `create_*_import_preview`, `create_*_mock_import`, `list_platform_entities`, `get_agent_entity`, `validate_agent_entity_contract`, `get_agent_entity_readiness_report`, `create_agent_entity_import_dry_run`
- Local audit/read-only queries: review audit, operation audit, artifacts, workflows, provider audit, MCP call audit

`--profile all` is only for historical manifest regression or future teams restoring platform/environment/publish integration. It is not the Agent default.

## 5. Recommended Tool Sequence

### 5.1 Readiness And Material

```text
get_real_llm_runtime_config
analyze_material
```

Use this to confirm local runtime state and inspect the source file. This does not read API key values and does not send a model request.

### 5.2 Generate Local Drafts

```text
generate_lab_from_source
generate_exam_from_lab
generate_ppt
```

Generated content stays `WAITING_REVIEW`. Standard answers and grading references remain teacher-side only.

For real LLM generation, use the existing explicit CLI opt-in workflow first, then return to MCP for review and local import inspection:

```powershell
python lab_cli.py phase2 real-dsl-demo one-click --input examples/input/demo-source.md --reviewer teacher_1 --provider-mode real-llm --model <model> --base-url <openai-compatible-base-url> --explicit-real-call-opt-in --confirm-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

### 5.3 Review And Readiness

```text
get_review_task_summary
get_review_detail
get_core_workflow_readiness
```

Use these to decide the next local action. The readiness response may recommend import-preview, grading evidence, or decision note, but it must keep `autoExecuteAllowed=false`.

### 5.4 Grading Evidence And Human Decision Note

```text
run_grading_evidence_auto
get_grading_result_preview
get_grading_evidence_readiness
record_review_decision_note
```

Default grading evidence starts with read-only evidence. Controlled Docker evidence requires explicit arguments and still stays local, review-gated, network-disabled, and non-publishing.

### 5.5 Local Import Preview Loop

```text
create_lab_template_import_preview
create_lab_template_mock_import
create_exam_question_import_preview
create_exam_question_mock_import
create_grading_rule_import_preview
create_grading_rule_mock_import
list_platform_entities
get_agent_entity
validate_agent_entity_contract
get_agent_entity_readiness_report
create_agent_entity_import_dry_run
```

Stop at `create_agent_entity_import_dry_run`. The dry-run DTO is the current local MVP endpoint.

## 6. Stop Lines

The MCP client must stop at one of these states:

```text
WAITING_REVIEW
READY_FOR_HUMAN_APPROVE
NEEDS_EVIDENCE
NEEDS_REVISION
LOCAL_CORE_MVP_STOP_LINE_REACHED
REAL_PLATFORM_BACKEND_PAUSED
```

The client must not auto approve, auto reject, batch change state, publish, destroy resources, or call real platform APIs.

## 6.1 Local Core Agent MVP

项目提供一个基于上述 profile 的本地 Agent MVP，不需要另行安装 Agent SDK，也不读取模型密钥：

```powershell
python lab_cli.py agent local-core run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/local-core-agent-run.json
```

该命令会输出可审计工具计划、每一步 MCP call record、Lab / Exam / Grading / PPT 产物路径、评分 evidence、审核入口和停止原因。默认调用顺序是：

```text
analyze_material
-> generate_lab_from_source
-> generate_exam_from_lab
-> generate_ppt
-> run_grading_evidence_auto (只读 evidence)
-> get_review_detail
-> WAITING_REVIEW_REQUIRED
```

它不会自动通过审核。只有人工审核已完成后，才可以显式传入已批准的任务 ID，使 Agent 运行本地 `import-preview -> mock-import -> import-dry-run`；完成后固定返回 `LOCAL_CORE_MVP_STOP_LINE_REACHED`，不会改为 `import-send` 或 `import-status`。

run record 可复放：

```powershell
python lab_cli.py agent local-core replay --record examples/output/local-core-agent-run.json --output examples/output/local-core-agent-replay.json
```

运行记录同时包含 `operatorSummary` 和 `nextActions`：前者说明当前处于“等待人工审核”还是“本地 dry-run 已完成”，后者提供审核路由、逐项审核命令和批准后的本地继续命令模板。每个 `steps[]` 项都包含 `label`、`purpose` 和 MCP audit record id，便于页面或脚本直接展示。

常见本地失败会保持统一 JSON，并增加不含密钥的 `agentDiagnostic`：

| 错误码 | 操作者动作 |
| --- | --- |
| `VALIDATION_ERROR` | 修正输入、输出或提交目录。 |
| `AGENT_TASK_NOT_APPROVED` | 在人工审核后，确认任务为 `APPROVED` 再传入任务 ID。 |
| `AGENT_RUN_RECORD_INVALID` | 使用完整的 `agent local-core run` JSON 记录进行 replay。 |
| `AGENT_RESPONSE_SHAPE_INVALID` | 检查关联 DSL、评分 evidence 或本地导入产物。 |
| `MCP_TOOL_NOT_IN_PROFILE` | 保持在本地停止线，不改用真实平台工具。 |

## 7. Paused Tools

The following tool families are not in the default profile:

- Real platform import send/status/result registration.
- Platform signoff and final publish review.
- VM / Notebook environment creation.
- Publish / destroy intents.
- Revision-loop tools.

If a default MCP call tries to use a paused tool, it should fail with:

```json
{
  "success": false,
  "code": "MCP_TOOL_NOT_IN_PROFILE"
}
```

This is expected. Do not work around it by asking for platform API base URL or platform token.

## 8. Verification

```powershell
python -m pytest tests/test_mcp_manifest.py tests/test_mcp_mock_tools.py tests/test_mcp_server_mock.py tests/test_mcp_stdio_server.py tests/test_mcp_stdio_client_smoke.py tests/test_local_core_agent.py -q
python lab_cli.py mcp call --tool agent_internal_publish_request --arguments '{"id":"agent_entity_demo"}'
```

The first command should pass. The second command should return `MCP_TOOL_NOT_IN_PROFILE` under the default profile.
