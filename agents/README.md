# agents

本目录存放本地 Agent 编排实现。当前包含历史 `real-demo` Mock Runner，以及可执行的 `local-core` Agent MVP。后者只调用 `local-core-mvp` MCP profile 中已稳定的本地工具，不连接外部平台、不调用真实大模型、不启动网络 MCP Server。

## Local Core Agent MVP

`agents/local_core_agent.py` 是一条可复放的本地工具调用链：素材分析 -> Lab -> Exam/Grading -> PPT -> 只读评分 evidence -> 审核详情。它把计划、每步 MCP audit record、产物路径、审核入口和停止原因写入 run record。

```powershell
python lab_cli.py agent local-core run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/local-core-agent-run.json
python lab_cli.py agent local-core replay --record examples/output/local-core-agent-run.json --output examples/output/local-core-agent-replay.json
```

默认运行不会 approve 任何任务，生成内容固定停在 `WAITING_REVIEW`。人工审核通过后，可显式提供已批准任务 ID 来执行本地 `import-preview -> mock-import -> import-dry-run`，并固定停在 `LOCAL_CORE_MVP_STOP_LINE_REACHED`：

```powershell
python lab_cli.py agent local-core run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/local-core-agent-import-run.json --approved-lab-task-id <lab_task_id> --approved-exam-task-id <exam_task_id> --approved-grading-task-id <grading_task_id>
```

该实现不调用 `import-send`、`import-status`、发布、云资源或 revision-loop 工具。

### 操作者可读输出与失败诊断

`agent local-core run` 的 run record 除了完整 `steps` 与 MCP audit record，还提供以下面向本地演示操作者的字段：

- `operatorSummary`：当前阶段、已完成工具数、待审核任务数、本地导入完成数和必须人工执行的动作。
- `nextActions`：审核入口、逐项人工批准命令、批准后的本地导入命令模板，或已到达 dry-run 停止线时的人工复核要求。
- 每个 `steps[]` 项含 `label` 与 `purpose`，不需要通过 MCP 工具名推断实际业务动作。

失败仍使用 CLI 统一 JSON。`VALIDATION_ERROR`、`AGENT_TASK_NOT_APPROVED`、`AGENT_RUN_RECORD_INVALID`、`MCP_TOOL_NOT_IN_PROFILE` 与 `AGENT_RESPONSE_SHAPE_INVALID` 均附带 `agentDiagnostic`，说明本地修复动作。该字段不会要求平台 base URL、token 或密钥，也不会建议绕过审核。

## 输入说明

- `delivery/real-demo-agent-workflow.json`: Agent Workflow 设计契约。
- `mcp-server/tools.manifest.json`: MCP Mock Tool 清单。
- `examples/input/demo-source.md`: 默认演示素材。
- 本地 `LAB_CLI_STORE` 或测试传入的 store path。
- 可选 `approvedLabTaskId`: 已人工审核通过的 Lab DSL 任务 id，用于创建本地 Lab 导入预览。
- 可选 `labImportOutput`: Lab 导入预览 JSON 输出路径。
- 可选 `createLabMockImport` / `labMockImportOutput`: 显式要求将 Lab 导入预览写入本地 Mock 平台实体 store。
- 可选 `approvedExamTaskId` / `approvedGradingTaskId`: 已人工审核通过、分别包含 `EXAM_DSL` / `GRADING_DSL` Artifact 的任务 id；同一个试题转换任务可以同时作为两者输入。
- 可选 `examImportOutput` / `gradingImportOutput`: Exam / Grading 导入预览 JSON 输出路径。
- 可选 `createExamMockImport` / `examMockImportOutput`: 显式要求将 Exam 导入预览写入本地 Mock 平台实体 store。
- 可选 `createGradingMockImport` / `gradingMockImportOutput`: 显式要求将 Grading 导入预览写入本地 Mock 平台实体 store。
- 可选 `readonlyGradingSubmission` / `readonlyGradingOutput`: 使用已审核 Grading 任务关联的 `GRADING_DSL`，对本地提交目录生成只读评分证据报告。
- 可选 `controlledGradingSubmission` / `controlledGradingOutput` / `controlledGradingImage`: 使用已审核 Grading 任务关联的 `GRADING_DSL`，在本地受控 Docker 容器里执行 allowlist `stdout_contains` / `pytest` 评分证据收集。

## 输出说明

Runner 返回普通 Python `dict`，由 CLI 包装为统一 JSON：

```text
success / code / message / data / traceId
```

输出内容包括 Agent 步骤、MCP Tool 响应摘要、Provider 质量分流建议、审核详情动作建议、源任务、修订请求、新修订任务、MCP 审计记录和安全断言。

`agentReviewTriage` 来自 `get_review_task_summary.data.reviewTaskSummary.providerQualityTaskSignal` 与 `reviewPriorityQueue`，只用于给出人工复核下一步建议；不会自动 approve、不会批量变更状态、不会触发真实发布。

`agentReviewDetailGuidance` 来自 `get_review_detail.data.reviewDetail.reviewPage`，会提炼 `actionBar`、`platformImportPreviewActions` 和发布阻断状态，用于告诉调用方下一步应请求修订、人工审核，还是审核通过后再做导入预览。

`agentCoreNextToolPlan` 来自 `get_core_workflow_readiness.data.coreWorkflowReadinessReport.nextToolRecommendation`，用于把单个任务的下一步建议转成 Agent 可读计划。CLI 默认使用 `--profile local-core-mvp`，只允许本地核心 MCP 工具；当 readiness 推荐真实平台 import-send / import-status / 签收 / 最终发布复核或 revision-loop 暂停工具时，计划会输出 `blockedByToolProfile=true`、`recommendedToolInProfile=false` 和 `toolProfileStopGuidance`，明确停在本地 import-dry-run / 人工复核交接点，不要求平台 API base URL、`AGENT_API_TOKEN` 或真实平台状态查询。计划会透出 `finalReviewState`，让 Agent 区分 `READY_FOR_HUMAN_APPROVE`、`NEEDS_MORE_EVIDENCE`、`NEEDS_REVISION`、`WAITING_DECISION_NOTE`、`WAITING_EVIDENCE` 和 `NOT_GRADING_REVIEW`，避免只按工具名推进。当 readiness 返回 `CONTENT_QUALITY_REVISION_REQUIRED` 时，计划会输出 `manualActionKind=content_quality_revision_request`、`manualActionCliCommand=python lab_cli.py review revision-request ...` 和 `contentQualityReadiness` 摘要，明确停在内容修订请求，而不是继续执行导入预览或 approve。Grading evidence 已齐全但还没有人工结论时，计划会推荐 `record_review_decision_note`，并带上 `decisionNoteRecommendation` 形成的参数草稿；记录 `approve-ready` 后才会进入 `create_grading_rule_import_preview`。该计划只调用只读 readiness 工具，不会调用推荐的后续工具；`recommendedToolCalled=false`、`autoExecuteAllowed=false`，适合作为“人工确认后再执行”的前置检查。

`agentCoreNextToolExecution` 会在显式传入 `--confirm-execute-recommended-tool` 后，复用同一份计划并只调用一个当前 profile 允许的推荐 MCP 工具。执行完成后会再次只读读取 readiness，返回 `postExecutionCoreNextToolPlan` 和 `nextSingleStepActionGuide`，并继续携带 `postExecutionFinalReviewState`、`currentStop` 和 `operatorSummary`，让调用方知道下一步是复制命令继续、到达本地停止线，还是停在人工审核动作；内容质量阻塞会显示 `currentStop.reasonCode=CONTENT_QUALITY_REVISION_REQUIRED`。该路径用于导入预览、Mock 导入、dry-run、评分 evidence 和 `record_review_decision_note` 等核心闭环动作。默认 `local-core-mvp` 下，Lab / Exam / Grading 任务在生成 import-preview、mock-import、`create_platform_entity_import_dry_run` 后即以 `LOCAL_CORE_MVP_STOP_LINE_REACHED` 停止；真实平台请求发送、状态查询、平台实体签收和最终发布复核记录仅保留在 `--profile all` 的历史全量 manifest 参考路径中，不作为当前 Agent 默认路线。

当下一步是 `agent_internal_publish_request`、`query_agent_publish_status`、平台实体签收或最终发布复核记录时，默认 `local-core-mvp` 会把它们标记为 `toolProfileStopGuidance`，不会要求补 `baseUrl`、`sendResult` 或平台 token。只有显式 `--profile all` 的历史回归场景才会暴露这些工具的原始参数占位符。

当传入 `approvedLabTaskId` 时，Runner 会先通过 `get_review_detail` 确认任务状态为 `APPROVED` 且关联 `LAB_DSL`，再调用 `create_lab_template_import_preview` 生成本地 `LabTemplateImportPreview`。输出中的 `agentLabImportPreviewGuidance` 会给出草稿 id、草稿状态和安全断言；该动作只写本地预览 JSON，不写平台数据库、不真实导入、不发布。

当传入 `approvedExamTaskId` 或 `approvedGradingTaskId` 时，Runner 会复用审核详情里的 `platformImportPreviewActions`，分别调用 `create_exam_question_import_preview`、`create_grading_rule_import_preview`。输出中的 `agentExamImportPreviewGuidance` 会固定 `answerVisibleToCandidate=false`，`agentGradingImportPreviewGuidance` 会固定 `sandboxExecuted=false` 与 `contestantCodeExecuted=false`。

当同时显式传入 `createLabMockImport`、`createExamMockImport` 或 `createGradingMockImport` 时，Runner 会在对应导入预览之后调用 `create_lab_template_mock_import`、`create_exam_question_mock_import` 或 `create_grading_rule_mock_import`，把本地导入预览草稿写入本地 mock platform entity store。输出中的 `agentLabMockImportGuidance`、`agentExamMockImportGuidance` 和 `agentGradingMockImportGuidance` 会给出本地实体 id，并固定 `mockStoreWritten=true`、`databaseWritten=false`、`realPlatformImport=false`、`realPublishAllowed=false`。

只要本轮创建过任一 Lab / Exam / Grading 导入预览，Runner 会追加调用 `get_platform_entity_readiness_report`，输出 `agentAgentEntityReadinessGuidance`，汇总三类平台实体是否已有导入预览、是否已 Mock 入库、哪些实体尚未签收但可签收、哪些实体已经存在本地 `AgentEntitySignoffRecord`，以及 `postSignoffPrePublishChecklist` 发布前人工最终复核清单。该报告只读读取本地 store 和 Artifact，固定 `databaseWritten=false`、`realPlatformImport=false`、`realPublish=false`，不提供真实发布入口。

当同时传入 `approvedGradingTaskId` 和 `readonlyGradingSubmission` 时，Runner 会读取该任务的 `GRADING_DSL` Artifact 路径，并调用 `run_readonly_grading_evidence` 生成只读 evidence 报告。该路径只静态检查提交目录中的文件、JSON 字段和 Notebook 文本；不运行命令、不运行 pytest、不启动 Notebook kernel、不执行选手代码。

当同时传入 `approvedGradingTaskId` 和 `controlledGradingSubmission` 时，Runner 会读取该任务的 `GRADING_DSL` Artifact 路径，并调用 `run_controlled_grading_evidence` 生成受控 Docker evidence 报告。该路径会在容器内执行 allowlist Python / pytest 检查，因此输出会明确 `commandExecuted=true`、`contestantCodeExecuted=true`；同时必须保持 `networkEnabled=false`、`hostExecutionAllowed=false`、`unknownShellExecuted=false`、`realPublish=false`，报告仍停在人工审核语义。

当同时传入 `approvedGradingTaskId` 和 `autoGradingSubmission` 时，Runner 会读取该任务的 `GRADING_DSL` Artifact 路径，并调用 MCP Tool `run_grading_evidence_auto`。该工具先运行只读 evidence，再按显式 `autoGradingIncludeControlled=true` 决定是否运行受控 Docker evidence，最后输出 `GRADING_EVIDENCE_AUTO_REPORT`。默认不会执行选手命令，不自动通过，不发布。

## 命令示例

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json
```

只读下一步工具计划：

```powershell
python lab_cli.py agent real-demo plan-core-next-tool --task-id <task_id> --reviewer teacher_1 --output examples/output/demo-agent-core-next-tool-plan.json
```

人工确认后执行一个推荐工具：

```powershell
python lab_cli.py agent real-demo execute-core-next-tool --task-id <approved_task_id> --reviewer teacher_1 --arguments "{\"output\":\"examples/output/demo-agent-core-next-tool-execution-target.json\"}" --output examples/output/demo-agent-core-next-tool-execution.json --confirm-execute-recommended-tool
```

Grading 在 evidence、`approve-ready` decision note 和人工 approve 都完成后，可以用同一个单步命令连续推进本地导入闭环。每次只执行一个推荐 MCP 工具，第一步生成 `GradingRuleImportPreview`，第二步写入本地 mock platform entity，第三步生成真实平台 draft import dry-run DTO，并在默认 `local-core-mvp` 下停在本地交接点；真实平台 `baseUrl` / 状态查询 / 签收不属于当前默认路线：

```powershell
python lab_cli.py agent real-demo execute-core-next-tool --task-id <approved_grading_task_id> --reviewer teacher_1 --arguments "{\"output\":\"examples/output/agent-grading-import-preview.json\"}" --output examples/output/agent-grading-step-1-import-preview.json --confirm-execute-recommended-tool
python lab_cli.py agent real-demo execute-core-next-tool --task-id <approved_grading_task_id> --reviewer teacher_1 --arguments "{\"output\":\"examples/output/agent-grading-mock-import.json\"}" --output examples/output/agent-grading-step-2-mock-import.json --confirm-execute-recommended-tool
python lab_cli.py agent real-demo execute-core-next-tool --task-id <approved_grading_task_id> --reviewer teacher_1 --arguments "{\"output\":\"examples/output/agent-grading-platform-dry-run.json\"}" --output examples/output/agent-grading-step-3-platform-dry-run.json --confirm-execute-recommended-tool
```

已审核 Lab 的本地导入预览：

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-lab-task-id <approved_lab_task_id> --lab-import-output examples/output/demo-agent-lab-import-preview.json
```

已审核 Exam / Grading 的本地导入预览：

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-exam-task-id <approved_exam_task_id> --exam-import-output examples/output/demo-agent-exam-import-preview.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json
```

已审核 Lab / Exam / Grading 的本地 Mock 平台实体导入：

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-lab-task-id <approved_lab_task_id> --lab-import-output examples/output/demo-agent-lab-import-preview.json --create-lab-mock-import --lab-mock-import-output examples/output/demo-agent-lab-mock-import.json --approved-exam-task-id <approved_exam_task_id> --exam-import-output examples/output/demo-agent-exam-import-preview.json --create-exam-mock-import --exam-mock-import-output examples/output/demo-agent-exam-mock-import.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --create-grading-mock-import --grading-mock-import-output examples/output/demo-agent-grading-mock-import.json
```

只读评分证据：

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --readonly-grading-submission examples/submissions/readonly-demo --readonly-grading-output examples/output/demo-agent-readonly-grading-evidence.json
```

受控 Docker 评分证据：

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --controlled-grading-submission examples/submissions/controlled-command-demo --controlled-grading-output examples/output/demo-agent-controlled-grading-evidence.json --controlled-grading-image ai-grading-python:0.1
```

自动评分证据编排：

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --auto-grading-submission examples/submissions/readonly-demo --auto-grading-output examples/output/demo-agent-grading-evidence-auto.json
```

自动评分证据编排，包含受控 Docker 命令证据：

```powershell
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json --approved-grading-task-id <approved_grading_task_id> --grading-import-output examples/output/demo-agent-grading-import-preview.json --auto-grading-submission examples/submissions/controlled-command-demo --auto-grading-output examples/output/demo-agent-grading-evidence-auto-controlled.json --auto-grading-include-controlled --auto-grading-image ai-grading-python:0.1
```

## 测试方式

```powershell
python -m pytest tests/test_real_demo_agent_runner.py
python -m pytest tests/test_cli.py
```

## 限制说明

- 不启动真实 Agent。
- 不连接任何外部平台。
- 不发送新的真实 LLM 请求。
- 不读取或展示密钥。
- 不启动真实 MCP Server。
- 不自动通过、不批量变更、不自动发布、不真实发布。
- `plan-core-next-tool` 只读取 `CoreWorkflowReadinessReport` 并生成本地建议计划，不调用推荐工具，不改变任务状态。
- `execute-core-next-tool` 必须显式传入 `--confirm-execute-recommended-tool`，并且每次只调用一个 `nextToolRecommendation.toolName`；执行后只读返回 `postExecutionCoreNextToolPlan` 和 `nextSingleStepActionGuide` 作为下一步提示，并通过 `finalReviewState` / `postExecutionFinalReviewState` 标明审核状态。当下一步是人工审核/签收等无工具动作时会失败返回，不会替代人工决定。
- Lab 导入预览只允许使用已人工审核通过的 Lab DSL 任务，且 `databaseWritten=false`、`realPlatformImport=false`。
- Exam / Grading 导入预览只生成本地平台实体草稿；Exam 标准答案不进入选手侧，Grading 不执行沙箱或选手代码。
- Mock 平台实体导入必须显式传入 `--create-*-mock-import`，只写本地 JSON store 的 `platformEntities`，不会写真实数据库、调用真实平台导入 API 或发布。
- 自动评分证据编排默认只执行只读 evidence；只有显式传 `--auto-grading-include-controlled` 时才尝试受控 Docker evidence，且仍保持网络禁用、宿主机执行禁用、人工审核后置。
- 平台实体就绪报告只读汇总导入预览和 Mock 入库缺口，不写真实数据库、不调用真实平台导入 API、不发布。
- 只读评分证据不是完整真实沙箱；它只收集低风险静态 evidence，并固定 `commandExecuted=false`、`pytestExecuted=false`、`notebookExecuted=false`、`contestantCodeExecuted=false`。
- 受控 Docker 评分证据只支持 allowlist `stdout_contains` / `pytest`，需要本地 Docker daemon 和本地镜像；不会自动 pull 镜像，不执行 Notebook 或未知 Shell，网络关闭，提交目录只读挂载。
