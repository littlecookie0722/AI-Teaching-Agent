# Real Demo Agent Workflow

本说明用于“演示型智能体”的最小 Mock 编排：让 Agent Runner 能复放真实 LLM Demo evidence、读取审核队列、基于 Provider 质量摘要和审核详情动作栏给出人工复核分流建议、通过 MCP 记录退回修改意见，生成一个 Mock 修订稿，并在用户提供已审核任务时创建本地导入预览和读取平台实体就绪报告。当前实现为本地 Mock Runner，不启动真实 Agent，不连接外部平台，不发送新的真实 LLM 请求。

## 输入说明

- `mcp-server/tools.manifest.json`: MCP Mock Tool 能力清单。
- `delivery/real-demo-quick-commands.json`: 可复制快速命令清单。
- `delivery/real-demo-script.json`: 演示脚本机器契约。
- `frontend/real-demo.html`: 真实成果只读演示页。
- `frontend/mock-data.json`: 前端静态证据数据。
- 可选 `approvedLabTaskId`: 已人工审核通过的 Lab DSL 任务 id。
- 可选 `labImportOutput`: 本地 Lab 导入预览 JSON 输出路径。
- 可选 `createLabMockImport` / `labMockImportOutput`: 显式要求将 Lab 导入预览写入本地 Mock 平台实体 store。
- 可选 `approvedExamTaskId` / `approvedGradingTaskId`: 已人工审核通过、包含 `EXAM_DSL` / `GRADING_DSL` Artifact 的任务 id；一个试题转换任务可同时提供两类 Artifact。
- 可选 `examImportOutput` / `gradingImportOutput`: 本地 Exam / Grading 导入预览 JSON 输出路径。
- 可选 `createExamMockImport` / `examMockImportOutput`: 显式要求将 Exam 导入预览写入本地 Mock 平台实体 store。
- 可选 `createGradingMockImport` / `gradingMockImportOutput`: 显式要求将 Grading 导入预览写入本地 Mock 平台实体 store。
- 可选 `readonlyGradingSubmission` / `readonlyGradingOutput`: 本地提交目录和只读评分证据报告输出路径，要求同时提供 `approvedGradingTaskId`。
- 可选 `controlledGradingSubmission` / `controlledGradingOutput` / `controlledGradingImage`: 本地提交目录、受控 Docker 评分证据报告输出路径和本地镜像名，要求同时提供 `approvedGradingTaskId`；只执行 allowlist 的 `stdout_contains` / `pytest` 检查，网络关闭。
- 可选 `taskId`: 用于 `plan-core-next-tool` 只读规划模式，或 `execute-core-next-tool` 单步确认执行模式，读取该任务的 `CoreWorkflowReadinessReport.nextToolRecommendation`。
- 可选 `toolArguments`: 用于 `execute-core-next-tool` 覆盖推荐工具参数，例如输出路径或平台实体 id。

## 输出说明

- `delivery/REAL_DEMO_AGENT_WORKFLOW.md`: 当前设计说明。
- `delivery/real-demo-agent-workflow.json`: 机器可测试的 Agent Workflow 设计契约。
- `agents/real_demo_runner.py`: 本地 Mock Agent Runner。
- `agentLabImportPreviewGuidance`: 可选输出，仅在传入 `approvedLabTaskId` 后出现可用状态，用于展示本地导入预览草稿和安全断言。
- `agentLabMockImportGuidance`: 可选输出，仅在显式传入 `createLabMockImport` 后出现可用状态，用于展示本地 Lab 平台实体候选记录，并固定 `mockStoreWritten=true`、`databaseWritten=false`、`realAgentImport=false`。
- `agentExamImportPreviewGuidance`: 可选输出，展示 ExamQuestionImportPreview 草稿，并固定 `answerVisibleToCandidate=false`。
- `agentExamMockImportGuidance`: 可选输出，仅在显式传入 `createExamMockImport` 后出现可用状态，用于展示本地 Exam 平台实体候选记录，并固定 `answerVisibleToCandidate=false`、`databaseWritten=false`、`realAgentImport=false`。
- `agentGradingImportPreviewGuidance`: 可选输出，展示 GradingRuleImportPreview 草稿，并固定 `sandboxExecuted=false`、`contestantCodeExecuted=false`。
- `agentGradingMockImportGuidance`: 可选输出，仅在显式传入 `createGradingMockImport` 后出现可用状态，用于展示本地 Grading 平台实体候选记录，并固定 `sandboxExecuted=false`、`contestantCodeExecuted=false`、`databaseWritten=false`、`realAgentImport=false`。
- `agentAgentEntityReadinessGuidance`: 可选输出，展示 Lab / Exam / Grading 三类平台实体是否已有导入预览、是否已 Mock 入库、`signoffReadyEntities`、`signedEntities`、`signoffPendingEntities` 和 `postSignoffPrePublishReadyTotal`，以及下一步应补导入预览、补 Mock 导入、记录人工签收还是复核已签收实体；固定 `readOnly=true`、`databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`。
- `agentReadonlyGradingEvidenceGuidance`: 可选输出，展示只读评分 evidence 摘要，并固定 `commandExecuted=false`、`pytestExecuted=false`、`notebookExecuted=false`、`contestantCodeExecuted=false`。
- `agentControlledGradingEvidenceGuidance`: 可选输出，展示受控 Docker 评分 evidence 摘要；该路径会在容器中执行选手代码，必须固定 `networkEnabled=false`、`hostExecutionAllowed=false`、`unknownShellExecuted=false`、`realPublishAllowed=false`。
- `agentCoreNextToolPlan`: 只读规划输出，来自 `get_core_workflow_readiness` 的 `nextToolRecommendation`，会标出推荐工具、参数预览、`finalReviewState`、是否需要人工动作和 `recommendedToolCalled=false`。
- `agentCoreNextToolExecution`: 显式人工确认后的单步执行输出，先读取同一份 readiness，再只调用一个推荐 MCP 工具，并返回 `executedToolTotal=1`。
- `postExecutionCoreNextToolPlan`: 单步执行后再次只读读取 readiness 得到的下一步提示，用于决定下一次人工确认工具或停在人工动作，并继续携带 `finalReviewState`。
- `nextSingleStepActionGuide`: 基于 `postExecutionCoreNextToolPlan` 生成的操作提示；当 `canContinueWithSameCommand=true` 时可复制 `suggestedCliCommand` 继续下一次单步确认执行；当 `finalReviewState=NEEDS_MORE_EVIDENCE|NEEDS_REVISION|WAITING_DECISION_NOTE|WAITING_EVIDENCE` 时优先停在对应人工复核或 evidence 动作。

输出不包含真实 Agent 配置、不包含密钥、不包含外部平台 URL。

## Agent 目标

帮助演示人员完成一条可审核闭环：

```text
打开真实成果复放
读取审核队列
创建本地 WAITING_REVIEW Lab 任务
基于 providerQualityTaskSignal 生成只读人工复核建议
读取 review detail 动作栏与导入预览入口
记录审核退回意见
生成新的 WAITING_REVIEW Mock 修订稿
展示 MCP 调用审计
可选：对已审核 Lab 创建本地导入预览
```

## 允许工具

- `get_review_task_summary`
- `generate_lab_from_source`
- `request_review_revision`
- `regenerate_from_revision_mock`
- `list_mcp_tool_call_records`
- `get_review_detail`
- `create_lab_template_import_preview`
- `create_lab_template_mock_import`
- `create_exam_question_import_preview`
- `create_exam_question_mock_import`
- `create_grading_rule_import_preview`
- `create_grading_rule_mock_import`
- `get_agent_entity_readiness_report`
- `run_readonly_grading_evidence`
- `run_controlled_grading_evidence`
- `get_core_workflow_readiness`
- `run_grading_evidence_auto`
- `create_agent_entity_import_dry_run`
- `record_agent_entity_publish_result`
- `record_agent_entity_signoff`
- `record_final_publish_review_decision`

## 禁止工具

- `publish_lab`
- `publish_exam`
- `destroy_environment`

这些高风险工具不能被演示 Agent 直接调用，也不能被解释为真实发布或真实销毁授权。

## 状态模型

- 请求状态：`demoSourcePath`、`reviewer`、`revisionComment`、`TASK_ID`、`PROVIDER_QUALITY_TASK_SIGNAL`、`AGENT_REVIEW_TRIAGE`、`AGENT_REVIEW_DETAIL_GUIDANCE`、`REVISION_REQUEST_ID`、`APPROVED_LAB_TASK_ID`、`LAB_IMPORT_PREVIEW_ID`、`LAB_MOCK_IMPORT_ID`、`APPROVED_EXAM_TASK_ID`、`EXAM_IMPORT_PREVIEW_ID`、`EXAM_MOCK_IMPORT_ID`、`APPROVED_GRADING_TASK_ID`、`GRADING_IMPORT_PREVIEW_ID`、`GRADING_MOCK_IMPORT_ID`、`PLATFORM_ENTITY_READINESS_REPORT`、`READONLY_GRADING_SUBMISSION`、`READONLY_GRADING_EVIDENCE_ID`、`CONTROLLED_GRADING_SUBMISSION`、`CONTROLLED_GRADING_IMAGE`、`CONTROLLED_GRADING_EVIDENCE_ID`。
- 持久化状态：`JsonTaskStore.aiTasks`、`JsonTaskStore.artifacts`、`JsonTaskStore.mcpToolCallRecords`、`JsonTaskStore.operationAuditEvents`。
- 审计状态：`mcpToolCallRecord`、`operationAuditEvent`、`workflowRun`、`artifact`。

Agent 不能只依赖对话记忆保存关键状态。

## 编排步骤

1. 打开 `frontend/real-demo.html`，确认 `RealDemoMcpRevisionLoop` 可见。
2. 调用 `get_review_task_summary`，确认真实演示队列仍是人工审核。
3. 调用 `generate_lab_from_source`，创建本地 `WAITING_REVIEW` Lab 任务。
4. 再次调用 `get_review_task_summary`，读取 `providerQualityTaskSignal` 和 `reviewPriorityQueue.items[].providerQualitySummary`，生成 `agentReviewTriage`。该建议只用于提示人工复核下一步，不能自动 approve、批量变更或发布。
5. 调用 `get_review_detail`，读取 `reviewPage.actionBar` 和 `platformImportPreviewActions`，生成 `agentReviewDetailGuidance`。该建议只指出是否可请求修订、是否可在审核后进入导入预览，不能替代人工审核。
6. 调用 `request_review_revision`，记录审核退回意见；源任务状态不得改变。
7. 调用 `regenerate_from_revision_mock`，创建新的 `WAITING_REVIEW` 修订稿。
8. 调用 `list_mcp_tool_call_records`，展示 MCP 审计记录。
9. 可选：如果传入 `approvedLabTaskId`，调用 `get_review_detail`，确认任务状态为 `APPROVED`、artifact 为 `LAB_DSL`，且 `platformImportPreviewActions.enabledTotal > 0`。
10. 可选：调用 `create_lab_template_import_preview`，生成本地 `LabTemplateImportPreview` JSON；必须保持 `databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`。
11. 可选：再次调用 `get_review_detail`，确认 `platformImportPreview` 和 `platformImportPreviewSignoff` 已在审核详情中可见，等待人工签收。
12. 可选且显式：如果传入 `createLabMockImport`，调用 `create_lab_template_mock_import`，将 Lab 导入预览写入本地 mock platform entity store；必须保持 `databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`。
13. 可选：如果传入 `approvedExamTaskId`，调用 `get_review_detail`，确认 `create_exam_question_import_preview` 动作可用。
14. 可选：调用 `create_exam_question_import_preview`，生成本地 `ExamQuestionImportPreview` JSON；必须保持 `answerVisibleToCandidate=false`、`databaseWritten=false`、`realAgentImport=false`。
15. 可选：再次调用 `get_review_detail`，确认 `exam_question` 草稿预览进入人工签收。
16. 可选且显式：如果传入 `createExamMockImport`，调用 `create_exam_question_mock_import`，将 Exam 导入预览写入本地 mock platform entity store；必须保持 `answerVisibleToCandidate=false`、`databaseWritten=false`、`realAgentImport=false`。
17. 可选：如果传入 `approvedGradingTaskId`，调用 `get_review_detail`，确认 `create_grading_rule_import_preview` 动作可用。
18. 可选：调用 `create_grading_rule_import_preview`，生成本地 `GradingRuleImportPreview` JSON；必须保持 `sandboxExecuted=false`、`contestantCodeExecuted=false`、`databaseWritten=false`。
19. 可选：再次调用 `get_review_detail`，确认 `grading_rule` 草稿预览进入人工签收。
20. 可选且显式：如果传入 `createGradingMockImport`，调用 `create_grading_rule_mock_import`，将 Grading 导入预览写入本地 mock platform entity store；必须保持 `sandboxExecuted=false`、`contestantCodeExecuted=false`、`databaseWritten=false`、`realAgentImport=false`。
21. 可选：如果传入 `readonlyGradingSubmission`，调用 `run_readonly_grading_evidence`，使用已审核 Grading 任务关联的 `GRADING_DSL` Artifact 生成只读评分 evidence；必须保持 `commandExecuted=false`、`pytestExecuted=false`、`notebookExecuted=false`、`contestantCodeExecuted=false`。
22. 可选：如果传入 `controlledGradingSubmission`，调用 `run_controlled_grading_evidence`，使用已审核 Grading 任务关联的 `GRADING_DSL` Artifact 生成受控 Docker 评分 evidence；允许在容器内执行 allowlist Python / pytest 检查，但必须保持 `networkEnabled=false`、`hostExecutionAllowed=false`、`unknownShellExecuted=false`、`realPublish=false`，且 evidence 仍需人工审核。
23. 可选：如果本轮创建过任一导入预览，调用 `get_agent_entity_readiness_report`，汇总 `lab_template`、`exam_question`、`grading_rule` 的导入预览、Mock 入库缺口、待签收实体和已签收实体；必须保持 `readOnly=true`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。
24. 可选只读规划：调用 `get_core_workflow_readiness`，读取 `nextToolRecommendation` 并生成 `AgentCoreNextToolPlan`；该步骤只规划，不调用推荐工具，必须保持 `recommendedToolCalled=false`、`autoExecuteAllowed=false`，并保留 `finalReviewState` 供 Agent 判断是否应停在 evidence、decision note 或人工审核。
25. 可选且显式：如果传入 `execute-core-next-tool --confirm-execute-recommended-tool`，Runner 先执行第 24 步，再只调用一个 `nextToolRecommendation.toolName`，最后再次只读读取 readiness 并返回 `postExecutionCoreNextToolPlan` 和 `nextSingleStepActionGuide`。若下一步是人工审核、人工签收、补 evidence、记录 decision note 或参数未补齐，必须返回错误或提示人工动作；该步骤不能自动 approve、不能自动发布、不能新增 LLM 请求。

每个会写状态的步骤后都必须停在人工审核语义上，不允许自动通过或发布。

## 错误处理

- `MISSING_TASK_ID`: 先运行 `generate_lab_from_source` 并捕获 `data.task.id`。
- `REVISION_REQUEST_NOT_FOUND`: 先运行 `request_review_revision`。
- `TASK_NOT_WAITING_REVIEW`: 停止流程，要求重新选择待审核任务。
- `BLOCKED_TOOL_REQUESTED`: 拒绝调用发布、销毁类高风险工具。
- `APPROVED_LAB_TASK_REQUIRED`: 未提供已人工审核通过的 Lab DSL 任务，或任务状态不是 `APPROVED`。
- `APPROVED_EXAM_TASK_REQUIRED`: 未提供已人工审核通过且含 Exam DSL 的任务，或任务状态不是 `APPROVED`。
- `APPROVED_GRADING_TASK_REQUIRED`: 未提供已人工审核通过且含 Grading DSL 的任务，或任务状态不是 `APPROVED`。
- `IMPORT_PREVIEW_ACTION_NOT_AVAILABLE`: 审核详情未开放 Lab 导入预览入口。
- `CONFIRM_RECOMMENDED_TOOL_REQUIRED`: `execute-core-next-tool` 缺少 `--confirm-execute-recommended-tool`。
- `NEXT_TOOL_MANUAL_ACTION_REQUIRED`: readiness 推荐的是人工审核、签收或复核动作，没有可执行 MCP 工具。
- `RECOMMENDED_TOOL_ARGUMENTS_INCOMPLETE`: 推荐工具参数中仍有 `<...>` 占位符，需要通过 `--arguments` 或 `--arguments-file` 补齐。

## 验证方式

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-lab-task-id <approved_lab_task_id> --lab-import-output examples/output/demo-agent-lab-import-preview.json
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-exam-task-id <approved_exam_task_id> --exam-import-output examples/output/demo-agent-exam-import-preview.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-lab-task-id <approved_lab_task_id> --lab-import-output examples/output/demo-agent-lab-import-preview.json --create-lab-mock-import --lab-mock-import-output examples/output/demo-agent-lab-mock-import.json --approved-exam-task-id <approved_exam_task_id> --exam-import-output examples/output/demo-agent-exam-import-preview.json --create-exam-mock-import --exam-mock-import-output examples/output/demo-agent-exam-mock-import.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --create-grading-mock-import --grading-mock-import-output examples/output/demo-agent-grading-mock-import.json
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --readonly-grading-submission examples/submissions/readonly-demo --readonly-grading-output examples/output/demo-agent-readonly-grading-evidence.json
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --controlled-grading-submission examples/submissions/controlled-command-demo --controlled-grading-output examples/output/demo-agent-controlled-grading-evidence.json --controlled-grading-image ai-grading-python:0.1
python lab_cli.py agent real-demo plan-core-next-tool --task-id <task_id> --reviewer teacher_1 --output examples/output/demo-agent-core-next-tool-plan.json
python lab_cli.py agent real-demo execute-core-next-tool --task-id <approved_task_id> --reviewer teacher_1 --arguments "{\"output\":\"examples/output/demo-agent-core-next-tool-execution-target.json\"}" --output examples/output/demo-agent-core-next-tool-execution.json --confirm-execute-recommended-tool
python -m pytest tests/test_real_demo_agent_runner.py
python -m pytest tests/test_real_demo_agent_workflow.py
python -m pytest tests/test_mcp_manifest.py tests/test_mcp_mock_tools.py
```

## 限制说明

- 不创建或启动真实 Agent。
- 不连接任何外部平台。
- 不发送新的真实 LLM 请求。
- 不读取或展示 API Key、Token、密码。
- 不启动真实 MCP Server。
- 默认不运行 Docker、Notebook kernel、未知 Shell 或选手代码；仅当显式传入 `controlledGradingSubmission` 时，使用本地 Docker 镜像执行 allowlist Python / pytest 检查，网络关闭、提交目录只读挂载、不自动拉取镜像、不执行 Notebook。
- 不自动通过、不批量变更、不自动发布、不真实发布。
- `plan-core-next-tool` 只读生成下一步工具计划，不调用推荐工具、不改变任务状态。
- `execute-core-next-tool` 每次只执行一个推荐 MCP 工具；执行后会返回 `postExecutionCoreNextToolPlan` 和 `nextSingleStepActionGuide`，但仍然要求人工审核/签收停点，不会替代审核结论。
- 生成的修订稿仍必须保持 `WAITING_REVIEW`。
- Lab 导入预览只允许基于已审核 Lab DSL 任务创建，输出仍是本地预览，不写平台数据库、不真实导入。
- Exam / Grading 导入预览只允许基于已审核 DSL 任务创建；Exam 不向选手侧暴露标准答案，Grading 不执行沙箱或选手代码。
- Mock 平台实体导入必须显式传入 `--create-*-mock-import`，只写本地 JSON store 的 `platformEntities`，不会写真实数据库、调用真实平台导入 API 或发布。
- 平台实体就绪报告只读读取本地导入预览 Artifact、Mock 平台实体草稿和本地签收记录，用于提示下一步缺口；`agentEntitySignoffReadyTotal` 表示尚未签收但可签收，`agentEntitySignoffRecordedTotal` 表示已存在 `AgentEntitySignoffRecord`；不写真实数据库、不调用真实平台导入 API、不发布。
- 只读评分 evidence 只检查本地提交目录内低风险文件，不运行命令、pytest、Notebook kernel 或选手代码；它不能替代后续完整受控沙箱。
