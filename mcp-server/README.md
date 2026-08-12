# mcp-server

Phase 1 / Phase 4 MCP 目录。当前定义工具 manifest、本地调用层、本地 MCP Server Mock runtime，以及第一版可启动的 stdio JSON-RPC MCP 服务；不监听端口，不接入真实智能体，也不让大模型直接调用生产能力。

## 输入说明

- `tools.manifest.json`: MCP Tool Mock 契约清单。
- `server.contract.json`: Phase 4 MCP Server Mock 契约，声明本地 transport、capabilities 和安全断言。
- `tool-call-audit.contract.json`: MCP Tool 调用审计契约，约束本地记录字段、安全断言和脱敏策略。
- `high-risk-tool-safety.contract.json`: Phase 4 高风险 MCP Tool 安全矩阵，约束 review-intent-only、只读二次确认查询和真实动作禁用。
- `docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md`: MCP 客户端本地核心 profile 配置、调用顺序和停止线说明。
- `mcp_server/mock_tools.py`: 本地 MCP Tool Mock 调用层，读取 manifest 并映射到 Backend Mock。
- `mcp_server/mock_server.py`: 本地 MCP Server Mock runtime，提供 initialize / list_tools / call_tool 形态，不启动网络监听。
- `mcp_server/stdio_server.py`: 本地 line-delimited JSON-RPC stdio 服务入口，支持 `initialize`、`tools/list`、`tools/call`，不监听端口、不启动 Agent。
- `mcp_server/stdio_client_smoke.py`: 本地 MCP stdio 客户端 smoke，启动项目 stdio server 子进程，发送 `initialize` / `tools/list` / `tools/call`，并输出统一 JSON 证据。
- 每个 tool 需要声明：
  - `name`
  - `inputSchema`
  - `backend.method`
  - `backend.path`
  - `cli`
  - `riskLevel`
  - `reviewRequired`
  - `safety`

## 输出说明

所有工具未来必须保持统一 JSON 输出：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {},
  "traceId": "trace_xxx"
}
```

失败输出必须包含 `errors`。

## 命令示例

当前 MCP 默认使用 `local-core-mvp` 工具 profile，只暴露本地核心闭环工具：真实 LLM 配置只读摘要、素材分析、Lab / Exam / PPT 生成、审核队列读取、评分 evidence、GradingJob / GradingRecord 本地任务流、人工 decision note、本地平台实体 list / get / contract-validate、本地 import-preview / mock-import / import-dry-run 和审计查询。`lab-cli mcp call`、`server-call`、stdio `tools/call` 和底层 `mcp_server.mock_tools.invoke_mcp_tool()` 的默认 profile 都是 `local-core-mvp`。真实平台请求发送、平台状态查询、环境创建、发布 / 销毁意图、revision-loop 等历史工具不在默认 profile 中。

```powershell
python lab_cli.py mcp list
python lab_cli.py mcp call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp call --tool generate_lab_from_source --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp call --tool generate_exam_from_lab --arguments "{\"labId\":\"lab_demo\"}"
python lab_cli.py mcp call --tool run_grading_evidence_auto --arguments "{\"grading\":\"templates/grading/examples/mixed-checks.yaml\",\"submission\":\"examples/submissions/readonly-demo\",\"output\":\"examples/output/grading-evidence-auto.json\"}"
python lab_cli.py mcp call --tool create_grading_job --arguments "{\"grading\":\"templates/grading/examples/mixed-checks.yaml\",\"submission\":\"examples/submissions/readonly-demo\",\"output\":\"examples/output/mcp-grading-job-evidence-auto.json\",\"submissionId\":\"submission_001\",\"reviewer\":\"teacher_1\"}"
python lab_cli.py mcp call --tool list_grading_jobs --arguments "{\"submissionId\":\"submission_001\"}"
python lab_cli.py mcp call --tool run_grading_job --arguments "{\"id\":\"<grading_job_id>\",\"reviewer\":\"teacher_1\"}"
python lab_cli.py mcp call --tool create_grading_record --arguments "{\"report\":\"examples/output/mcp-grading-job-evidence-auto.json\",\"submissionId\":\"submission_001\",\"reviewer\":\"teacher_1\"}"
python lab_cli.py mcp call --tool list_grading_records --arguments "{\"submissionId\":\"submission_001\"}"
python lab_cli.py mcp call --tool review_grading_record --arguments "{\"id\":\"<grading_record_id>\",\"reviewer\":\"teacher_1\",\"decision\":\"approve-ready\"}"
python lab_cli.py mcp call --tool get_grading_result_preview --arguments "{\"report\":\"examples/output/grading-evidence-auto.json\"}"
python lab_cli.py mcp call --tool get_review_task_summary --arguments "{}"
python lab_cli.py mcp call --tool get_core_workflow_readiness --arguments "{\"taskId\":\"<task_id>\"}"
python lab_cli.py mcp call --tool create_lab_template_import_preview --arguments "{\"taskId\":\"<approved_lab_task_id>\",\"reviewer\":\"teacher_4\",\"output\":\"examples/output/lab-template-import-preview.json\"}"
python lab_cli.py mcp call --tool create_exam_question_import_preview --arguments "{\"taskId\":\"<approved_exam_task_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/exam-question-import-preview.json\"}"
python lab_cli.py mcp call --tool create_grading_rule_import_preview --arguments "{\"taskId\":\"<approved_grading_task_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/grading-rule-import-preview.json\"}"
python lab_cli.py mcp call --tool create_lab_template_mock_import --arguments "{\"taskId\":\"<approved_lab_task_id>\",\"reviewer\":\"teacher_4\",\"output\":\"examples/output/lab-template-mock-import.json\"}"
python lab_cli.py mcp call --tool create_exam_question_mock_import --arguments "{\"taskId\":\"<approved_exam_task_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/exam-question-mock-import.json\"}"
python lab_cli.py mcp call --tool create_grading_rule_mock_import --arguments "{\"taskId\":\"<approved_grading_task_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/grading-rule-mock-import.json\"}"
python lab_cli.py mcp call --tool list_platform_entities --arguments "{\"sourceTaskId\":\"<approved_task_id>\",\"entityType\":\"lab_template\"}"
python lab_cli.py mcp call --tool get_agent_entity --arguments "{\"id\":\"<agent_entity_id>\"}"
python lab_cli.py mcp call --tool validate_agent_entity_contract --arguments "{\"contractConfig\":\"examples/input/platform-contract.json\",\"entityType\":\"lab_template\"}"
python lab_cli.py mcp call --tool get_agent_entity_readiness_report --arguments "{\"sourceTaskId\":\"<approved_task_id>\"}"
python lab_cli.py mcp call --tool create_agent_entity_import_dry_run --arguments "{\"id\":\"<agent_entity_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/platform-entity-import-dry-run.json\"}"
python lab_cli.py mcp server-info
python lab_cli.py mcp server-tools
python lab_cli.py mcp server-call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python -m mcp_server.stdio_server
python lab_cli.py mcp stdio-smoke --input examples/input/demo-source.md --output examples/output/mcp-stdio-client-smoke.json
python lab_cli.py mcp audit --tool analyze_material
Get-Content docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md
python -m pytest tests/test_mcp_manifest.py
python -m pytest tests/test_mcp_mock_tools.py
python -m pytest tests/test_mcp_server_mock.py
python -m pytest tests/test_mcp_stdio_server.py
python -m pytest tests/test_mcp_stdio_client_smoke.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py
```

如需检查历史全量 manifest，可显式使用 `--profile all`，或在测试代码里显式传入 `profile="all"`。该 profile 仅用于回归测试和未来其他团队恢复真实平台 / 环境 / 发布对接时参考，不作为当前 Agent 默认工具集：

```powershell
python lab_cli.py mcp list --profile all
python lab_cli.py mcp server-tools --profile all
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- 提供 MCP Tool 契约草案、MCP Server Mock runtime 和本地 stdio JSON-RPC 传输层；stdio 只读写当前进程 stdin/stdout，不监听端口。
- Tool 只能映射到本地 CLI 或 Backend Mock。
- `mcp_server/mock_tools.py` 只做本地函数调用，不监听端口，不启动真实 MCP Server。
- `mcp_server/mock_tools.invoke_mcp_tool()` 默认也使用 `local-core-mvp`；暂停工具若未显式传 `profile="all"` 会返回 `MCP_TOOL_NOT_IN_PROFILE`。
- `mcp_server/mock_server.py` 只做本地函数调用，`transport=local_function_only`，固定 `networkListenerStarted=false`。
- `mcp_server/stdio_server.py` 支持 `python -m mcp_server.stdio_server` 作为本地 MCP stdio 进程，方法包括 `initialize`、`tools/list`、`tools/call`；工具调用仍复用 Backend Mock 和 `mcpToolCallRecords`，固定 `networkListenerStarted=false`、`realAgentStarted=false`、`autoPublishAllowed=false`。
- Backend Mock 暴露 `/api/mcp/server/info`、`/api/mcp/server/tools`、`/api/mcp/server/call`，仍不启动 Web Server 或真实 MCP Server。
- `lab-cli mcp call` 返回统一 JSON，并在成功响应里标记 `realMcpServerStarted=false`、`realAgentStarted=false`。
- `lab-cli mcp call` 会写入本地 `mcpToolCallRecords`，参数只保存 key 和脱敏预览，不保存原始密钥值。
- Artifact 工具只读取本地 Mock 产物元数据，不上传文件、不连接对象存储。
- Review Detail 工具只读取本地聚合审核视图，并返回 `reviewPage` 页面模型；高风险 MCP 意图会额外返回 `highRiskIntent.postReviewDisposition`、`reviewPolicy.postReviewDispositionState` 和 `reviewPage.highRiskIntentPanel`，不允许自动发布、真实发布或真实销毁。
- `request_review_revision`、`regenerate_from_revision_mock`、`get_second_confirmation_status`、`publish_lab`、`publish_exam`、`destroy_environment` 等历史 revision-loop / 高风险意图工具不在默认 `local-core-mvp` profile 中；仅 `--profile all` 可用于回归旧契约，且仍不得真实发布或销毁资源。
- `high-risk-tool-safety.contract.json` 只做安全矩阵契约，不新增运行时入口；`publish_lab`、`publish_exam`、`destroy_environment` 必须保持 review-intent-only，`get_second_confirmation_status` 必须保持 read-only。
- Review Task Summary 工具只做审核队列摘要，不允许批量审核或批量发布；`get_review_task_summary.outputContract` 声明 `data.reviewTaskSummary.providerQualityTaskSignal` 和 `data.reviewTaskSummary.reviewPriorityQueue.items[].providerQualitySummary`，供 MCP 调用方读取来自 `reviewDetail.reviewPage.providerSummary.qualitySummary` / `calls[].qualitySummary` 的真实 LLM 质量摘要，包括 `readyForReview`、归一化 patch 数、Schema 修复状态、请求数、token 数和 response id；Mock 任务返回 `available=false`。该工具同时声明 `data.reviewTaskSummary.reviewPriorityQueue`，供 MCP 调用方按 `priority`、`reasonCode`、`recommendedAction` 做人工审核排序。评分任务队列项包含 `manualReviewChecklistSummary`、可选 `controlledGradingEvidenceSummary`、可选 `mergedGradingEvidenceSummary`、可选 `gradingEvidenceReadinessSummary` 和 `preApproveReviewCheck`，用于显示下一步人工复核项、受控 Docker evidence、合并 evidence 覆盖率、证据 ready/missing 缺口、人工决策边界、是否已有 merged evidence 和 latest `approve-ready` decision note，`autoApproveAllowed=false`、`batchStateChangeAllowed=false`。该输出契约也声明 `data.reviewTaskSummary.preApproveReviewCheckSignal`，汇总评分任务的 `APPROVE_ALLOWED_WITH_WARNINGS` / `READY_FOR_HUMAN_APPROVE`、`warningTotal`、`evidenceReadyTotal` 和 `reviewDecisionNoteRecordedTotal`；`preApproveReviewCheck.summary.approveReadyDecision` 只有在 latest decision note 为 `approve-ready` 时为 true，`needs-revision` / `needs-evidence` 仍保留 warning。该字段只提示人工审核，不阻断人工通过、不自动通过；声明 `data.reviewTaskSummary.gradingEvidenceReadinessSignal`，从队列项 `gradingEvidenceReadinessSummary` 汇总 `evidenceReadyTotal`、`missingEvidenceTotal`、受控命令缺口和只读静态缺口，并在 `items[].actionGuide` 中给出 `POST /api/grading/evidence-auto`、`grade evidence-auto`、打开评分报告和记录 decision note 的人工步骤。该信号只读取已有 evidence，不运行 Docker、pytest、Notebook 或选手代码，不自动审核、不发布；声明 `data.reviewTaskSummary.realDemoReviewQueue`，用于展示真实演示 Lab / Exam / Grading / PPT 四个 `WAITING_REVIEW` 产物、`readonlyEvidenceCollectedTotal=2` 和 PPT 页级审核入口；声明 `data.reviewTaskSummary.controlledDockerEvidenceReviewSignal`，优先从 `reviewDetail.controlledGradingEvidence` 返回动态受控 Docker evidence 摘要，没有动态 evidence 时回退为固定演示摘要；声明 `data.reviewTaskSummary.mergedGradingEvidenceReviewSignal`，从 `reviewDetail.mergedGradingEvidence` 返回只读/受控证据合并后的覆盖 check、得分、`coverageRatio` 和 `mergeExecutedOnlyExistingReports=true`，没有合并报告时返回 `NO_MERGED_EVIDENCE_REPORT` 并提示先运行 `grade evidence-merge --task-id <grading-task-id>`；声明 `data.reviewTaskSummary.notebookEvidenceReviewPlan`，用于展开 Notebook 缺口的只读审核计划和人工复核动作。上述字段只做人工审核入口，不允许自动通过、批量状态变更、真实容器执行、Notebook kernel 启动或真实发布。
- `get_real_llm_runtime_config` 返回只读 `data.realLlmRuntimeConfig`，用于在真实 LLM 演示前确认 `OPENAI_API_KEY` 是否存在、`OPENAI_MODEL` 和 `OPENAI_BASE_URL` 当前配置。工具不返回 API Key 值、不导入 SDK、不创建 client、不发起请求、不创建任务或产物。
- `get_real_dsl_review_preview` 读取本地真实 LLM 产物并返回 `data.realDslReviewPreview`，与 `python lab_cli.py review real-dsl-preview` 和 `GET /api/review/real-dsl-preview` 复用同一审核预览模型。该工具只做本地 DSL Schema 校验、审核摘要聚合、确定性 `qualitySignals`、`reviewIssues` 和 `revisionSuggestions` 生成，默认输入为 `examples/output/real-llm-lab.json`、`real-llm-exam.json`、`real-llm-grading.json`、`real-llm-ppt.json` 和候选人安全预览；可选参数 `lab`、`exam`、`grading`、`ppt`、`candidatePreview` 用于覆盖路径。固定 `newLlmRequestSent=false`、`secretsRead=false`、`networkAccess=false`、`answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false`、`autoApproveAllowed=false`、`realPublishAllowed=false`。
- `create_real_dsl_revision_draft` 基于本地真实 DSL 和人工修改意见创建 `WAITING_REVIEW` 修订草稿，输出 `data.realDslRevisionDraft`、修订 DSL 和 revision report。默认 `providerMode=local`，只做本地确定性修订；传 `providerMode=real-llm`、`model`、可选 `baseUrl`，并显式提供 `explicitRealCallOptIn=true`、`confirmWaitingReview=true`、`confirmNoAutoPublish=true` 后，会发起一次 OpenAI-compatible 真实二次修订请求。两种模式都不创建已通过任务、不执行沙箱或选手代码、不自动发布。
- `create_real_dsl_revision_batch_from_preview` 读取本地 `RealDslReviewPreview.revisionSuggestions` 并创建多份 `WAITING_REVIEW` 修订草稿，输出 `data.realDslRevisionBatch` 和各修订 DSL/report 路径。该工具只做本地确定性修订，不新增真实 LLM 请求、不读取密钥、不执行沙箱或选手代码、不自动发布。
- `get_real_dsl_revision_diff_preview` 读取本地 `RealDslRevisionBatch` 报告、源 DSL 和修订 DSL，输出 `data.realDslRevisionDiffPreview`，包含每个修订草稿的 changed fields、源值摘要、修订值摘要和审核建议。该工具为只读审核视图，不新增真实 LLM 请求、不读取密钥、不执行沙箱或选手代码、不自动发布。
- `create_real_dsl_revision_decision` 读取本地 `RealDslRevisionDiffPreview` 并记录单条人工审核决策，输出 `data.realDslRevisionDecision`。`decision` 只能是 `approve`、`reject` 或 `request-change`，后两者必须提供 `reason`；`approve` 只进入 `REVISION_APPROVED_FOR_MANUAL_MERGE`，需要后续人工合并，不会修改源 DSL 或修订 DSL、不新增真实 LLM 请求、不读取密钥、不执行沙箱或选手代码、不自动发布。
- `promote_real_dsl_revision_candidate` 读取本地 `RealDslRevisionDecision`，仅允许已 `approve` 的修订复制为新的 `WAITING_REVIEW` 候选 DSL，输出 `data.realDslRevisionPromotion`。该工具需要人工审核语义，且不会修改源 DSL 或修订 DSL、不创建已通过任务、不新增真实 LLM 请求、不读取密钥、不执行沙箱或选手代码、不自动发布。
- `enqueue_real_dsl_revision_candidate_review` 读取本地 `RealDslRevisionPromotion`，把候选 DSL 创建为 `WAITING_REVIEW` AI Task、DSL Artifact、Workflow Run 和操作审计事件，输出 `data.promotionReviewQueueItem` 与 `reviewDetail`。该工具只把候选版接入既有审核队列，不自动 approve、不批量改状态、不新增真实 LLM 请求、不读取密钥、不执行沙箱或选手代码、不发布。
- `create_lab_template_import_preview` 读取已 `APPROVED` 的 Lab DSL 任务和关联 `LAB_DSL` Artifact，重新校验 Lab Schema 后输出 `data.labTemplateImportPreview`、`WORKFLOW_REPORT` Artifact 和 `LAB_TEMPLATE_IMPORT_PREVIEW` 操作审计。该工具只创建本地平台 `lab_template` 草稿导入预览，固定 `databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`，不写真实数据库、不调用真实平台导入 API、不发布。
- `create_exam_question_import_preview` 和 `create_grading_rule_import_preview` 读取已 `APPROVED` 的 Exam / Grading DSL 任务和关联 Artifact，重新校验 Schema 后输出 `data.examQuestionImportPreview` / `data.gradingRuleImportPreview`、`WORKFLOW_REPORT` Artifact 和操作审计。它们只创建本地平台 `exam_question` / `grading_rule` 草稿导入预览，固定 `databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`；Exam 不向候选人暴露标准答案，Grading 不执行真实沙箱或选手代码。
- `create_lab_template_mock_import`、`create_exam_question_mock_import` 和 `create_grading_rule_mock_import` 要求任务已 `APPROVED` 且已有对应导入预览，然后把预览中的实体草稿写入本地 JSON store 的 `platformEntities`，输出 `data.agentEntityMockImport` 与 `agentEntityRecord`。它们只标记 `mockStoreWritten=true`，固定 `databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不会写真实数据库、调用真实平台导入 API、执行评分或发布。
- `list_platform_entities` 和 `get_agent_entity` 只读查询本地平台实体草稿与 `agentEntityImportActivity`，可在传入 `coreDbPath` 时只读 Backend Core SQLite staging。它们固定 `readOnly=true`、`networkAccess=false`、`databaseWritten=false`、`productionDatabaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不要求真实平台 API base URL 或 token。
- `validate_agent_entity_contract` 只读取本地 `contractConfig` JSON，校验 draft import endpoint、状态字段别名、状态映射和 `requestBodyMapping`。该工具固定 `requestSent=false`、`networkAccess=false`、`secretsRead=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不会发送真实平台请求。
- `get_agent_entity_readiness_report` 只读查询 `data.agentEntityReadinessReport`，汇总 Lab / Exam / Grading 三类平台实体是否已有导入预览、是否已 Mock 入库、是否可进入人工平台复核；可用 `sourceTaskId` 过滤。`agentEntitySignoffReadyTotal` 表示尚未签收但可执行人工签收动作，`agentEntitySignoffRecordedTotal` 表示已经存在本地 `AgentEntitySignoffRecord`，`postSignoffPrePublishChecklist` 表示真实发布前人工最终复核清单且不提供发布入口。该工具固定 `readOnly=true`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不会写真实数据库、调用真实平台导入 API 或发布。
- `get_core_workflow_readiness` 只读查询 `data.coreWorkflowReadinessReport`，汇总单个任务的审核状态、平台实体导入就绪、pending 导入预览动作、Grading evidence 缺口和 pre-approve decision note 信号，用于判断下一步核心动作。`summary.finalReviewState` 与 `nextToolRecommendation.finalReviewState` 会统一返回 `READY_FOR_HUMAN_APPROVE`、`NEEDS_MORE_EVIDENCE`、`NEEDS_REVISION`、`WAITING_DECISION_NOTE`、`WAITING_EVIDENCE` 或 `NOT_GRADING_REVIEW`，让 Agent 只推荐一个明确下一步。`platformImportPreviewActionSummary` 会列出 pending 平台实体、预览组件、下一步动作和 CLI 命令；`nextToolRecommendation` 会给出只读下一步工具选择建议，例如 `create_*_import_preview`、`run_grading_evidence_auto`、`record_review_decision_note` 或人工审核/签收动作，并固定 `autoExecuteAllowed=false`，调用方需要显式人工步骤后才可另行调用对应工具。该工具固定 `readOnly=true`、`autoApproveAllowed=false`、`autoPublishAllowed=false`、`realPublish=false`，不会自动审核、真实导入、真实发布、调用真实 LLM、读取密钥或执行沙箱。
- `create_agent_entity_import_dry_run` 读取本地 `mock-import` 产生的平台实体记录，输出 `data.agentEntityImportDryRun`，包含未来真实平台 draft import API 的目标 endpoint、idempotency key、request DTO 和 `platformApiContract` 预览。可选 `contractConfig` 指向本地 JSON 文件，覆盖 `entities.<entityType>.draftImportPath`、`statusPathTemplate`、`draftIdResponseKeys`、`statusResponseKeys` 和 `statusMapping`，用于适配测试平台字段差异。该工具只写本地 `WORKFLOW_REPORT` Artifact 与操作审计，固定 `dryRunOnly=true`、`requestSent=false`、`networkAccess=false`、`secretsRead=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不会发送真实平台请求。
- `agent_internal_publish_request`、`query_agent_publish_status` 和 `record_agent_entity_publish_result` 属于未来真实平台后端对接参考，不在默认 `local-core-mvp` profile 中；当前开发只做到本地 `create_agent_entity_import_dry_run`，不得要求平台 API base URL 或 `AGENT_API_TOKEN`。
- `record_review_decision_note` 在 Grading evidence 已人工复核后记录本地 `ReviewDecisionNote`，支持 `approve-ready`、`needs-revision`、`needs-evidence` 三类结论。它只写 `REVIEW_DECISION_NOTE` Artifact 和 `REVIEW_DECISION_NOTE_RECORD` 审计，不改变 AI Task 状态、不自动通过、不执行沙箱、不调用真实 LLM、不导入或发布。`get_core_workflow_readiness` 在 evidence 齐全且等待结论时会优先推荐该工具；记录 `approve-ready` 后，下一步才会推荐 `create_grading_rule_import_preview`。
- `create_grading_job`、`list_grading_jobs`、`get_grading_job` 和 `run_grading_job` 封装本地 `GradingJob` API。创建工具只生成本地 `QUEUED` staging job，不执行选手代码；运行工具复用既有 `evidence-auto` 路径并派生 `GradingRecord`，记录状态可能是 `WAITING_REVIEW` 或因 evidence 缺口进入 `NEEDS_EVIDENCE`。这组工具固定 `queuePersistedToProduction=false`、`productionDatabaseWritten=false`、`autoApproveAllowed=false`、`realPublish=false`，只用于一类题型/语言的本地任务流闭环。
- `create_grading_record`、`list_grading_records`、`get_grading_record` 和 `review_grading_record` 封装本地 `GradingRecord` API。记录创建只读取已有评分报告，不重新评分、不启动 Docker；复核工具只写人工 `approve-ready` / `needs-evidence` / `needs-revision` 结论，不改变 AI Task 状态、不导入、不发布。该记录复核结果会被审核详情、评分报告和平台实体 readiness 用作本地核心闭环证据。
- `record_agent_entity_signoff` 和 `record_final_publish_review_decision` 属于历史签收 / 发布前复核参考，不在默认 `local-core-mvp` profile 中；当前本地 MVP 停在 import-dry-run DTO。
- `run_readonly_grading_evidence` 读取本地 Grading DSL 和提交目录，输出 `data.report` 与 `data.reportDetail`，只做文件、JSON、Notebook 文本等静态 evidence 收集；固定 `commandExecuted=false`、`pytestExecuted=false`、`notebookExecuted=false`、`contestantCodeExecuted=false`、`realPublish=false`。
- `run_controlled_grading_evidence` 读取本地 Grading DSL 和提交目录，调用既有受控 Docker executor 执行 allowlist `stdout_contains` / `pytest` 检查，输出 `CONTROLLED_DOCKER_SANDBOX_POC` 报告和操作审计。该工具会在容器内执行选手代码，因此必须显式体现 `commandExecuted=true`、`contestantCodeExecuted=true`；同时固定 `networkEnabled=false`、`hostExecutionAllowed=false`、`unknownShellExecuted=false`、`notebookExecuted=false`、`realPublish=false`，不自动 pull 镜像、不自动审核、不发布。
- `merge_grading_evidence_reports` 读取一到多份已有本地评分 evidence JSON，输出 `data.report`、`operationAuditEvent` 和 `GRADING_REPORT` Artifact。该工具只合并既有报告中的 `reportDetail.checkPlans` / `checks`，用于人工审核覆盖率，不读取 submission、不启动 Docker、不执行 pytest/Notebook/命令、不调用真实 LLM、不自动通过、不发布；来源报告的安全摘要可能显示此前已有受控容器证据，但 merge 工具本身固定 `sandboxExecutedByTool=false`、`contestantCodeExecutedByTool=false`、`networkAccess=false`。
- `run_grading_evidence_auto` 读取本地 Grading DSL 和提交目录，先运行只读 evidence，再按显式 `includeControlledCommand=true` 决定是否运行受控 Docker evidence，最后输出 `GRADING_EVIDENCE_AUTO_REPORT`。报告包含 `executionMatrix` 和 `nextCoreAction`，供 MCP 调用方判断 check 级证据覆盖、受控命令缺口和下一步核心动作。默认不执行选手命令、不启动真实 LLM、不自动通过、不发布；受控 Docker 执行只在调用方显式请求时发生，并继续保持 `networkEnabled=false`、`hostExecutionAllowed=false`。
- `get_grading_evidence_readiness` 读取一到多份已有评分 evidence 报告，返回 `GRADING_EVIDENCE_READINESS`，用于智能体判断当前评分证据覆盖率、缺失 check 和下一步 evidence 收集/人工复核动作。该工具只发起只读 GET，不执行 Docker、pytest、Notebook、选手代码、真实 LLM、自动审核或发布。
- `get_grading_result_preview` 读取已有本地评分报告并返回 `data.gradingResultPreview`，用于给智能体和页面展示候选人安全的分数、执行摘要和有限 evidence 预览。该工具只读已有 JSON 和 Artifact metadata，不运行评分、不启动 Docker、不执行选手代码、不调用真实 LLM、不自动通过、不发布，并固定 `answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false`。
- `analyze_material` 只做本地静态素材分析，必须 `unknownShellExecuted=false`、`remoteContentFetched=false`。
- 生成类工具必须默认 `WAITING_REVIEW`。
- Workflow Run 工具只读取本地步骤日志，不启动真实编排引擎。
- Workflow Registry 工具只读取 Phase 2 Mock 能力目录，不执行 Workflow、不创建 AI Task、不写 Artifact。
- 高风险工具必须 `reviewRequired=true`。
- `publish_lab`、`publish_exam` 和 `destroy_environment` 只保留在全量 manifest 参考里；默认核心 profile 不暴露这些工具。
- 环境工具只创建本地 Mock 记录，不创建真实 VM / Notebook。
- Provider 工具只读取 Mock Provider 契约或生成本地 DSL 示例引用，不读取密钥，不调用真实 LLM。
- Mock 评分工具 `sandboxExecuted=false`，不执行选手代码；受控 Docker evidence 工具是显式例外，只在本地容器中执行 allowlist 检查并保留人工审核边界。
- 发布类工具已进入 manifest，但仅为 review-intent-only；后续真实发布设计必须在审核通过和二次确认策略完成后单独实现。
