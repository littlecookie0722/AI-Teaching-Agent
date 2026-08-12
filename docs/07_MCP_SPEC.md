# 07_MCP_SPEC

详见 `AI_PLATFORM_CODEX_FULL_GUIDE.md` 第 7 章。

## Phase 1 MCP Tool 契约草案

当前维护 `mcp-server/tools.manifest.json` 和本地调用层 `mcp_server/mock_tools.py`，并提供本地 stdio JSON-RPC 服务入口；不监听网络端口，不接入真实智能体。默认工具 profile 是 `local-core-mvp`，包括底层 `invoke_mcp_tool()` 直接调用；历史全量工具只能显式使用 `--profile all` 或 `profile="all"`。

MCP 客户端配置、默认 profile、推荐工具顺序和停止线见 `docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md`。

## Phase 4 MCP Server Mock

当前维护 `mcp-server/server.contract.json`、`mcp_server/mock_server.py` 和 `mcp_server/stdio_server.py`，提供 MCP Server 形态的本地初始化、工具列表、工具调用和 line-delimited JSON-RPC stdio 传输能力。

同时维护 `mcp_server/stdio_client_smoke.py`，用于从客户端视角启动本地 stdio server 子进程，发送 `initialize`、`tools/list` 和 `tools/call`，并输出本地 JSON evidence。该 smoke 不新增真实 Agent、不监听网络端口、不调用真实 LLM。

当前也维护 `mcp-server/high-risk-tool-safety.contract.json`，把 `publish_lab`、`publish_exam`、`destroy_environment` 和 `get_second_confirmation_status` 的安全矩阵单独固化为可测试契约。该文件只声明安全边界，不新增真实 MCP Server、真实 Agent、确认执行工具、真实发布或真实销毁能力。

Phase 4 Mock Server 只做：

- `initialize_mcp_server`
- `list_server_tools`
- `call_server_tool`
- CLI：`python lab_cli.py mcp server-info`
- CLI：`python lab_cli.py mcp server-tools`
- CLI：`python lab_cli.py mcp server-call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"`
- CLI：`python lab_cli.py mcp stdio-smoke --input examples/input/demo-source.md --output examples/output/mcp-stdio-client-smoke.json`
- stdio：`python -m mcp_server.stdio_server`
- Backend Mock：`GET /api/mcp/server/info`
- Backend Mock：`GET /api/mcp/server/tools`
- Backend Mock：`POST /api/mcp/server/call`

它不监听端口，不启动 Agent，不接入真实 LLM。`server-call` 和 stdio `tools/call` 仍复用 MCP Tool manifest 和 Backend Mock，并写入 `mcpToolCallRecords`。

## 工具边界

```text
MCP Tool Contract
  ↓
MCP Server Mock
  ↓
Backend Mock / CLI
  ↓
统一 JSON
  ↓
AI Task / DSL / Mock Report
```

Phase 1 允许声明但不真实执行：

- `workflow_demo`
- `analyze_material`
- `generate_lab_from_source`
- `generate_exam_from_lab`
- `generate_ppt`
- `run_grading`
- `list_ai_tasks`
- `get_ai_task`
- `list_review_tasks`
- `get_review_task_summary`
- `get_review_detail`
- `get_second_confirmation_status`
- `list_review_audit_events`
- `list_operation_audit_events`
- `list_artifacts`
- `get_artifact`
- `list_workflow_runs`
- `get_workflow_run`
- `list_providers`
- `get_provider_health`
- `mock_provider_generate`
- `list_provider_audit_events`
- `list_mcp_tool_call_records`
- `create_lab_template_import_preview`
- `create_exam_question_import_preview`
- `create_grading_rule_import_preview`
- `create_lab_template_mock_import`
- `create_exam_question_mock_import`
- `create_grading_rule_mock_import`
- `list_platform_entities`
- `get_agent_entity`
- `validate_agent_entity_contract`
- `get_agent_entity_readiness_report`
- `get_core_workflow_readiness`
- `merge_grading_evidence_reports`
- `run_grading_evidence_auto`
- `create_agent_entity_import_dry_run`
- `agent_internal_publish_request`
- `query_agent_publish_status`
- `record_agent_entity_publish_result`
- `create_vm_environment`
- `create_notebook_environment`
- `publish_lab`
- `publish_exam`
- `destroy_environment`

## 本地 Mock 调用

```powershell
python lab_cli.py mcp list
python lab_cli.py mcp call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp server-info
python lab_cli.py mcp server-tools
python lab_cli.py mcp server-call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python -m mcp_server.stdio_server
python lab_cli.py mcp stdio-smoke --input examples/input/demo-source.md --output examples/output/mcp-stdio-client-smoke.json
python lab_cli.py mcp call --tool create_lab_template_import_preview --arguments "{\"taskId\":\"<approved_lab_task_id>\",\"reviewer\":\"teacher_1\",\"output\":\"examples/output/lab-template-import-preview.json\"}"
python lab_cli.py mcp call --tool create_lab_template_mock_import --arguments "{\"taskId\":\"<approved_lab_task_id>\",\"reviewer\":\"teacher_1\",\"output\":\"examples/output/lab-template-mock-import.json\"}"
python lab_cli.py mcp call --tool create_exam_question_import_preview --arguments "{\"taskId\":\"<approved_exam_task_id>\",\"reviewer\":\"teacher_1\",\"output\":\"examples/output/exam-question-import-preview.json\"}"
python lab_cli.py mcp call --tool create_exam_question_mock_import --arguments "{\"taskId\":\"<approved_exam_task_id>\",\"reviewer\":\"teacher_1\",\"output\":\"examples/output/exam-question-mock-import.json\"}"
python lab_cli.py mcp call --tool create_grading_rule_import_preview --arguments "{\"taskId\":\"<approved_grading_task_id>\",\"reviewer\":\"teacher_1\",\"output\":\"examples/output/grading-rule-import-preview.json\"}"
python lab_cli.py mcp call --tool create_grading_rule_mock_import --arguments "{\"taskId\":\"<approved_grading_task_id>\",\"reviewer\":\"teacher_1\",\"output\":\"examples/output/grading-rule-mock-import.json\"}"
python lab_cli.py mcp call --tool list_platform_entities --arguments "{\"sourceTaskId\":\"<approved_task_id>\",\"entityType\":\"lab_template\"}"
python lab_cli.py mcp call --tool get_agent_entity --arguments "{\"id\":\"<agent_entity_id>\"}"
python lab_cli.py mcp call --tool validate_agent_entity_contract --arguments "{\"contractConfig\":\"examples/input/platform-contract.json\",\"entityType\":\"lab_template\"}"
python lab_cli.py mcp call --tool get_agent_entity_readiness_report --arguments "{\"sourceTaskId\":\"<approved_task_id>\"}"
python lab_cli.py mcp call --tool get_core_workflow_readiness --arguments "{\"taskId\":\"<task_id>\"}"
python lab_cli.py mcp call --tool merge_grading_evidence_reports --arguments "{\"reports\":[\"examples/output/readonly-sandbox-report.json\",\"examples/output/controlled-command-sandbox-report.json\"],\"output\":\"examples/output/merged-evidence-report.json\",\"taskId\":\"<grading_task_id>\"}"
python lab_cli.py mcp call --tool run_grading_evidence_auto --arguments "{\"grading\":\"templates/grading/examples/mixed-checks.yaml\",\"submission\":\"examples/submissions/readonly-demo\",\"output\":\"examples/output/grading-evidence-auto.json\"}"
python lab_cli.py mcp call --tool create_grading_job --arguments "{\"grading\":\"templates/grading/examples/mixed-checks.yaml\",\"submission\":\"examples/submissions/readonly-demo\",\"output\":\"examples/output/mcp-grading-job-evidence-auto.json\",\"submissionId\":\"submission_001\",\"reviewer\":\"teacher_1\"}"
python lab_cli.py mcp call --tool run_grading_job --arguments "{\"id\":\"<grading_job_id>\",\"reviewer\":\"teacher_1\"}"
python lab_cli.py mcp call --tool list_grading_records --arguments "{\"submissionId\":\"submission_001\"}"
python lab_cli.py mcp call --tool review_grading_record --arguments "{\"id\":\"<grading_record_id>\",\"reviewer\":\"teacher_1\",\"decision\":\"approve-ready\"}"
python lab_cli.py mcp call --tool create_agent_entity_import_dry_run --arguments "{\"id\":\"<agent_entity_id>\",\"reviewer\":\"teacher_1\",\"output\":\"examples/output/platform-entity-import-dry-run.json\"}"
python lab_cli.py mcp audit --tool analyze_material
Get-Content docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md
```

`mcp call` 只把工具调用映射到 Backend Mock 的 `handle_request`，不会监听端口，不启动真实 MCP Server，也不启动 Agent。调用边界会写入本地 `mcpToolCallRecords`，可通过 `mcp audit`、`GET /api/mcp-tool-call-records` 或 MCP Tool `list_mcp_tool_call_records` 查询。默认 profile 会拒绝 `agent_internal_publish_request`、`query_agent_publish_status`、`record_agent_entity_signoff`、`record_final_publish_review_decision`、环境创建、发布 / 销毁意图和 revision-loop 暂停工具；只有显式 `all` profile 才能用于历史契约回归。

`python -m mcp_server.stdio_server` 作为本地 stdio JSON-RPC 服务运行，每行读取一个 JSON-RPC request 并返回一行 response。支持 `initialize`、`tools/list`、`tools/call`、`ping` 和 `notifications/initialized`。其中 `tools/call` 的 `structuredContent` 是项目统一 JSON 响应；失败工具调用也作为 MCP `tools/call` 结果返回并设置 `isError=true`，便于调用方读取 `code`、`message`、`errors` 和 `traceId`。

`python lab_cli.py mcp stdio-smoke` 会作为本地客户端启动 `mcp_server.stdio_server` 子进程，发送最小 JSON-RPC 序列并调用 `analyze_material`。报告字段包括 `initialize`、`toolsList`、`toolCall`、`responses` 和 `safety`；`safety.networkListenerStarted=false`、`realAgentStarted=false`、`realLlmCalled=false`、`autoPublishAllowed=false`。该命令只验证客户端挂接和 stdio 协议，不创建业务任务、不发布、不执行评分沙箱、不读取密钥。

`get_review_task_summary` 的输出契约包含 `data.reviewTaskSummary.reviewPriorityQueue`，用于 MCP 调用方读取审核优先队列。该队列只服务人工分拣，字段包括 `priority`、`reasonCode`、`recommendedAction`、`manualReviewChecklistSummary`、`summary.autoApproveAllowed=false` 和 `summary.batchStateChangeAllowed=false`；其中 `manualReviewChecklistSummary` 来自 `reviewDetail.assessmentPlan.manualReviewChecklist`，用于展示评分任务下一步应人工核查的清单项，不得据此自动 approve、reject、publish 或执行真实沙箱。

`get_review_task_summary` 的输出契约同时包含 `data.reviewTaskSummary.realDemoReviewQueue`，用于 MCP 调用方读取真实演示产物的人工审核入口。该字段固定展示 Lab / Exam / Grading / PPT 四个 `WAITING_REVIEW` 产物、`schemaValidatedTotal=4`、`readonlyEvidenceCollectedTotal=2`、候选人答案不可见和 PPT 页级审核入口；它只服务演示审核分拣，不创建任务、不自动通过、不批量变更状态、不真实发布。

`merge_grading_evidence_reports` 的输出契约包含 `data.report`、`data.operationAuditEvent` 和 `data.artifact`，用于把已有只读评分 evidence 与受控 Docker evidence 合并成一个人工审核覆盖率报告。该工具只读取本地 JSON 报告并写出合并结果，不读取 submission、不启动 Docker、不执行 pytest/Notebook/命令、不调用真实 LLM、不自动通过、不发布；来源报告的 `safety` 可以反映历史受控容器执行，但工具自身必须保持 `sandboxExecutedByTool=false`、`contestantCodeExecutedByTool=false`、`networkAccess=false`。

`run_grading_evidence_auto` 的输出契约包含 `data.report`、`data.operationAuditEvent` 和 `data.artifact`，用于把只读 evidence、可选受控 Docker evidence 和合并报告串成一个可审核的 `GRADING_EVIDENCE_AUTO_REPORT`。`data.report.executionMatrix` 会按 check 展示只读 evidence、受控命令 evidence、最终选用 evidence 和缺口，`data.report.nextCoreAction` 会给出下一步核心动作。该工具默认只执行只读 evidence 和合并，不执行选手命令；只有显式传入 `includeControlledCommand=true` 才会调用受控 Docker evidence，且仍必须保持 `networkEnabled=false`、`hostExecutionAllowed=false`、`autoApproveAllowed=false`、`realPublish=false`。

`create_grading_job` / `list_grading_jobs` / `get_grading_job` / `run_grading_job` 的输出契约用于暴露已稳定的本地评分任务流。`create_grading_job` 只创建 `QUEUED` staging job，不执行选手代码；`run_grading_job` 复用 evidence-auto 路径生成评分报告并派生 `GradingRecord`，记录状态可能是 `WAITING_REVIEW` 或因证据缺口进入 `NEEDS_EVIDENCE`。这组工具固定 `queuePersistedToProduction=false`、`productionDatabaseWritten=false`、`autoApproveAllowed=false`、`realPublish=false`，不启动真实平台队列、不写生产数据库、不自动审核。

`create_grading_record` / `list_grading_records` / `get_grading_record` / `review_grading_record` 的输出契约用于暴露已稳定的本地评分记录复核流。记录创建只读取已有评分报告，不重新评分、不启动 Docker、不执行选手代码；复核工具只记录人工 `approve-ready`、`needs-evidence` 或 `needs-revision`，并保持 `taskStatusChanged=false`、`recordCreatesNewExecution=false`、`autoApproveAllowed=false`、`realPublish=false`。该复核结果可被审核详情、评分报告和平台实体 readiness 读取，作为本地核心闭环证据。

`get_review_task_summary.reviewPriorityQueue.items[].mergedGradingEvidenceSummary` 和 `mergedGradingEvidenceReviewSignal` 会暴露合并 evidence 的 check 级审核摘要：`checkEvidenceReviewItemTotal`、`manualCheckReviewTotal` 与最多 6 条 `checkEvidenceReviewItems` 预览。每条 item 只展示 check id/type、状态、得分、evidence 来源和建议人工动作，固定 `autoApproveAllowed=false`、`realPublishAllowed=false`，不得作为自动通过依据。

## 统一输出

所有工具必须返回：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {},
  "traceId": "trace_xxx"
}
```

失败时必须返回：

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "参数错误",
  "errors": [
    {"field": "input", "reason": "文件不存在"}
  ],
  "traceId": "trace_xxx"
}
```

## 安全要求

- 生成类工具必须创建或返回 `WAITING_REVIEW` 任务。
- 未审核内容不得发布。
- `run_grading` 在 Phase 1 中必须 `sandboxExecuted=false`。
- 环境工具在 Phase 1 中必须 `realCloudResourceCreated=false`。
- 高风险工具必须 `reviewRequired=true`。
- `publish_lab` / `publish_exam` 只能创建 `WAITING_REVIEW` 发布意图，必须 `realPublish=false`、`autoPublishAllowed=false`。
- `destroy_environment` 只能创建 `WAITING_REVIEW` 销毁意图，必须 `requiresSecondConfirmation=true`、`realCloudResourceChanged=false`、`environmentDestroyed=false`。
- 素材分析工具只允许静态读取本地文本素材，必须 `remoteContentFetched=false`、`unknownShellExecuted=false`、`realLlmCalled=false`。
- 审核审计工具只读本地事件，必须 `realPublish=false`。
- 审核队列摘要工具只读本地待审核队列，必须禁用批量 approve/reject/publish。
- 审核队列摘要工具的 `realDemoReviewQueue` 只能展示真实演示产物人工审核入口，必须保持 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`realPublishAllowed=false`。
- 审核详情工具只读本地聚合视图，必须 `autoPublishAllowed=false`、`realPublish=false`、`rejectRequiresReason=true`，并包含 `reviewPage` 页面模型；当任务是高风险 MCP 意图时，必须返回 `highRiskIntent.postReviewDisposition` 和 `reviewPage.highRiskIntentPanel`，用 `WAITING_HUMAN_REVIEW`、`APPROVED_EXECUTION_BLOCKED`、`APPROVED_PENDING_SECOND_CONFIRMATION` 等 Mock 状态表达处置结果，并保持 `executeRealActionAllowed=false`、`environmentDestroyed=false`。
- `get_second_confirmation_status` 二次确认状态查询工具只能读取 `destroy_environment` 等 `secondConfirmationRequired=true` 意图的 Mock 状态，必须保持 `readOnly=true`、`secondConfirmationSatisfied=false`、`confirmationActionAvailable=false`、`confirmationEndpointEnabled=false`、`destroyRealEnvironmentEnabled=false`，不得提供确认执行工具或真实销毁入口。
- 高风险 MCP 安全矩阵必须覆盖 `publish_lab`、`publish_exam`、`destroy_environment` 和 `get_second_confirmation_status`；发布/销毁类工具必须保持 review-intent-only，二次确认状态查询必须保持 read-only，所有矩阵项必须固定 `realMcpServerStarted=false`、`realAgentStarted=false`、`realActionExecuted=false`、`realPublish=false`、`environmentDestroyed=false`。
- 导入预览工具 `create_lab_template_import_preview`、`create_exam_question_import_preview` 和 `create_grading_rule_import_preview` 只能读取已 `APPROVED` 的 DSL 任务和本地 Artifact，输出平台实体草稿预览，必须保持 `databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`。
- Mock 导入工具 `create_lab_template_mock_import`、`create_exam_question_mock_import` 和 `create_grading_rule_mock_import` 必须要求源任务已 `APPROVED` 且已有对应导入预览，只允许写入本地 JSON store 的 `platformEntities`，必须保持 `mockStoreWritten=true`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。
- 平台实体只读工具 `list_platform_entities` 和 `get_agent_entity` 只能读取本地 JSON store 或显式 `coreDbPath` 指向的 Backend Core SQLite staging，输出实体草稿和本地导入活动摘要；必须保持 `readOnly=true`、`networkAccess=false`、`databaseWritten=false`、`productionDatabaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不得要求平台 API base URL 或 `AGENT_API_TOKEN`。
- 平台契约校验工具 `validate_agent_entity_contract` 只能读取本地 `contractConfig` JSON 并校验 endpoint、状态别名、状态映射和 `requestBodyMapping`；必须保持 `localConfigOnly=true`、`requestSent=false`、`networkAccess=false`、`secretsRead=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不得发送真实平台请求。
- 平台实体就绪报告工具 `get_agent_entity_readiness_report` 只能读取本地导入预览 Artifact 与 Mock 平台实体草稿，输出 `AgentEntityReadinessReport`，可按 `sourceTaskId` 过滤；`agentEntitySignoffReadyTotal` 只表示尚未签收但可执行人工签收动作，`agentEntitySignoffRecordedTotal` 表示已经存在本地 `AgentEntitySignoffRecord`，`postSignoffPrePublishChecklist` 只表示真实发布前人工最终复核清单；必须保持 `readOnly=true`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不得执行真实平台导入或发布。
- 核心闭环就绪报告工具 `get_core_workflow_readiness` 只能读取单个任务的审核状态、内容质量摘要、平台实体就绪、`platformImportPreviewActions`、评分 evidence 就绪和人工 pre-approve decision note 信号，输出 `data.coreWorkflowReadinessReport`；其中 `platformImportPreviewActionSummary` 会列出 pending 导入预览实体、预览组件、下一步动作和 CLI 命令，`nextToolRecommendation` 会基于第一个 blocked step 给出只读工具选择建议，例如 `create_*_import_preview`、`run_grading_evidence_auto`、`record_review_decision_note`、`review revision-request` 或人工审核/签收动作。当内容质量要求先修订时，`nextToolRecommendation.reasonCode=CONTENT_QUALITY_REVISION_REQUIRED`，并携带 `contentQualityReadiness` 与手工修订 CLI 建议；当 Grading evidence 齐全但还没有人工结论时，`reasonCode=GRADING_DECISION_NOTE_REQUIRED` 并推荐 `record_review_decision_note`，记录 `approve-ready` 后才进入 Grading 导入预览。该建议只用于调用方决策，固定 `autoExecuteAllowed=false`，不会由 readiness 工具自动调用后续工具。该工具用于判断下一步核心动作，必须保持 `readOnly=true`、`autoApproveAllowed=false`、`autoPublishAllowed=false`、`realPublish=false`，不得自动通过、真实导入、真实发布、调用真实 LLM、读取密钥或执行沙箱。
- 平台实体真实导入 dry-run 工具 `create_agent_entity_import_dry_run` 只能读取本地 `mock-import` 产生的 `platformEntities` 记录，输出未来真实平台 draft import API 的 DTO、目标 endpoint 和 idempotency key 预览；必须保持 `dryRunOnly=true`、`requestSent=false`、`networkAccess=false`、`secretsRead=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不得发送真实平台请求。

以下真实平台发送 / 状态 / 结果登记工具仅保留在全量 manifest 中作为未来其他团队对接参考，当前默认 `local-core-mvp` profile 不暴露，不作为本地 MVP 下一步任务：

- 平台实体真实导入发送工具 `agent_internal_publish_request` 只能读取已人工复核的 `AgentEntityImportDryRun` 报告，在显式确认后向配置的 draft import endpoint 发送一次 POST JSON；必须保持 `requestSent=true`、`networkAccess=true`、`secretsRead=true`、`secretValueReturned=false`、`databaseWrittenByLocalSystem=false`、`manualPlatformReviewRequired=true`、`autoPublishAllowed=false`、`realPublish=false`，不得返回 token、不得直接写真实数据库、不得绕过平台侧人工复核。
- 平台实体导入状态查询工具 `query_agent_publish_status` 只能读取已发送的 `AgentEntityImportSendResult` 报告，并在显式确认后向平台侧 draft import 状态 endpoint 发送只读 GET；必须保持 `readOnlyToPlatform=true`、`mockStoreUpdated=false`、`databaseWrittenByLocalSystem=false`、`secretValueReturned=false`、`autoPublishAllowed=false`、`realPublish=false`，查询结果不得自动登记为通过或发布。
- 平台实体导入结果登记工具 `record_agent_entity_publish_result` 只能读取已发送的 `AgentEntityImportSendResult` 报告，并由人工登记平台侧 draft import 状态；必须保持 `requestSent=false`、`networkAccess=false`、`secretsRead=false`、`secretValueReturned=false`、`databaseWrittenByLocalSystem=false`、`autoPublishAllowed=false`、`realPublish=false`，不得自动查询平台、自动通过或发布。
- 审核决策备注工具 `record_review_decision_note` 只能记录本地人工评分审核结论，写入 `REVIEW_DECISION_NOTE` Artifact 和审计；必须保持 `taskStatusChanged=false`、`autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`sandboxExecutedByDecisionNote=false`、`contestantCodeExecuted=false`、`realAgentImport=false`、`realPublish=false`，不得自动通过、自动导入、执行评分或发布。
- 评分 evidence 合并工具 `merge_grading_evidence_reports` 只能读取已有本地评分报告 JSON 并生成 `GRADING_EVIDENCE_MERGE_REPORT`；必须保持 `readExistingReportsOnly=true`、`mergeExecutedOnlyExistingReports=true`、`sandboxExecutedByTool=false`、`contestantCodeExecutedByTool=false`、`commandExecutedByTool=false`、`notebookExecutedByTool=false`、`networkAccess=false`、`autoApproveAllowed=false`、`realPublish=false`。
- 评分 evidence 自动编排工具 `run_grading_evidence_auto` 必须先执行只读 evidence，再按显式 `includeControlledCommand=true` 决定是否执行受控 Docker evidence，并生成 `GRADING_EVIDENCE_AUTO_REPORT`；默认必须保持 `controlledCommandDefaultEnabled=false`、`defaultContestantCodeExecuted=false`、`defaultCommandExecuted=false`、`networkEnabled=false`、`hostExecutionAllowed=false`、`autoApproveAllowed=false`、`realPublish=false`。
- 评分任务流工具 `create_grading_job`、`list_grading_jobs`、`get_grading_job`、`run_grading_job` 只能封装本地 `GradingJob` staging API；创建只进入 `QUEUED`，运行只同步执行已有本地 job 并派生评分报告 / `GradingRecord`，必须保持 `queuePersistedToProduction=false`、`productionDatabaseWritten=false`、`autoApproveAllowed=false`、`realPublish=false`。若 job 显式配置受控 Docker evidence，运行工具可复用既有受控 evidence 边界，但不得绕过 `networkEnabled=false`、`hostExecutionAllowed=false` 和人工复核。
- 评分记录复核工具 `create_grading_record`、`list_grading_records`、`get_grading_record`、`review_grading_record` 只能封装本地 `GradingRecord` API；创建只读取已有报告，复核只记录人工结论，必须保持 `recordCreatesNewExecution=false`、`taskStatusChanged=false`、`autoApproveAllowed=false`、`realPublish=false`，不得重新执行评分、自动通过、导入或发布。
- 统一操作审计工具只读本地事件，必须禁止真实 LLM、真实云资源、选手代码执行和真实发布。
- Artifact 工具只读本地 Mock 产物元数据，必须禁止真实 LLM、真实云资源、真实沙箱、选手代码执行和真实发布。
- Workflow Run 工具只读本地运行日志，必须保留 traceId 和步骤顺序，且禁止真实 LLM、真实沙箱和真实发布。
- Provider 工具只允许读取 Mock Provider 状态或生成本地 DSL 示例引用，必须 `realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`。
- MCP Mock 调用层必须返回 `realMcpServerStarted=false`、`realAgentStarted=false`。
- MCP Mock 调用层默认 profile 必须是 `local-core-mvp`；暂停工具在默认 profile 下必须返回 `MCP_TOOL_NOT_IN_PROFILE`，不得通过直接函数调用绕过当前 Agent 工具集。
- MCP Server Mock 必须返回 `networkListenerStarted=false`，且只通过本地函数调用 Backend Mock。
- MCP stdio 服务必须返回 `networkListenerStarted=false`，只使用 stdin/stdout，不监听端口，不启动 Agent；`tools/call` 必须继续走 Backend Mock、统一 JSON 和本地审计记录。
- MCP Tool 调用记录必须保持 `MOCK_ONLY`，参数只保存 key 和脱敏预览，不启动真实 MCP Server 或 Agent。
- 标准答案不得展示给选手端。

## 校验方式

```powershell
python -m pytest tests/test_mcp_manifest.py
python -m pytest tests/test_mcp_mock_tools.py
python -m pytest tests/test_mcp_server_mock.py
python -m pytest tests/test_mcp_stdio_server.py
python -m pytest tests/test_mcp_stdio_client_smoke.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py
```
