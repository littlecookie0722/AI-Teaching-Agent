# frontend

前端页面契约目录。当前只定义页面、组件、API 依赖和 Mock UI 数据，不启动真实 Web 应用。

> 当前产品主线只保留 `generation-workspace.html` 和 `review-center.html`：从一份 Markdown 生成 Lab + Exam/Grading，并完成逐项人工审核。其他页面保留为兼容、诊断或历史 PoC，不作为当前主导航。入口决策和待实现差距见 `docs/28_SIMPLIFIED_MVP_ENTRYPOINTS.md`。

## 当前默认入口

- `generation-workspace.html`：唯一默认生成入口。现有实现仍固定生成 Lab / Exam / Grading / PPT；下一实现切片将通过兼容的 `artifactProfile=teaching-core` 收敛为前三类。
- `review-center.html`：唯一默认审核入口。现有实现已集中读取队列和详情；下一实现切片将按 `workflowRun.id` 聚合教学包并接入已有逐任务 approve/reject 动作。
- `lab-generate.html`、`exam-generate.html` 和三个独立审核页：保留直接 URL，作为兼容、诊断和审核中心功能等价前的深层入口。
- PPT、评分、平台实体、AI Task、MCP、Agent 和运营页面：退出当前主导航，只做必要的兼容性、安全或阻断性缺陷修复。

## 输入说明

- `ui.manifest.json`: 前端页面契约，声明 route、组件、API Mock 依赖、优先级和安全限制。
- `mock-data.json`: 页面可用的本地 Mock 数据。
- `console.html`: Phase 1 前端 2.0 统一 Mock 控制台，串联所有静态原型、验证命令和安全断言。
- `dashboard.html`: Phase 1 Dashboard 静态原型，展示健康状态、待审核压力、Workflow、Artifact 和安全总览。
- `audit.html`: Phase 1 审计可观测静态原型，展示 Provider / MCP Tool / 高风险 MCP 意图 / Workflow / Operation / Review 本地审计记录，并在 `MOCK_GRADING_RUN` 中展示 `assessmentPlanSummary` 与 `checkPlans[].assessmentPlan*` 追溯字段。
- `audit-detail.html`: Phase 1 审计详情静态原型，展示单条 Provider / MCP 审计记录、Trace 关联、脱敏参数和错误上下文。
- `audit-incidents.html`: Phase 1 审计异常复盘静态原型，展示失败 Provider / MCP 审计记录的本地规则分类和运营排查建议。
- `operations-launchpad.html`: Phase 1 运营演示首页静态原型，集中提供本地静态页入口、验收命令、交接说明和安全边界。
- `operations-presenter.html`: Phase 1 运营讲解台静态原型，一页式展示 speakerCue、验收信号、Grading `AssessmentPlanAuditSignal`、白名单命令和禁止动作。
- `operations-signoff.html`: Phase 1 签收总览静态原型，一屏展示 7/7 门禁、175/175 交付、20/20 自检、14/14 验收、7/7 安全断言和审核优先队列签收提示。
- `operations-demo-script.html`: Phase 1 运营演示脚本静态原型，展示 12 步演示顺序、验收信号、`assessmentPlan` 审计追溯、白名单命令和禁止动作。
- `operations-runbook.html`: Phase 1 运营 Runbook 静态原型，汇总本地预览入口、白名单验证命令、审计复盘入口和安全红线。
- `operations-acceptance.html`: Phase 1 运营验收静态原型，汇总交付状态、Runbook、FAQ、Handoff、Phase 2 准入门禁、`AssessmentPlanAuditSignal` 和白名单验证命令。
- `operations-demo-map.html`: Phase 1 运营演示路径静态原型，按角色和演示顺序串联全部前端 Mock 页面。
- `real-demo.html`: Phase 2 真实 LLM Demo Evidence 静态原型，复放已有真实 LLM 演示包，展示 `CoreBusinessDemoPath`、`RealDemoAcceptanceSummary`、四类 DSL、候选人预览脱敏、独立 `readonlyEvidenceDemo` 评分证据、PPTX Artifact、PPT 页级审核入口和安全边界；不新增 LLM 请求、不读取密钥、不执行选手代码、不发布。
- `delivery.html`: Phase 1 交付验收静态原型，展示交付清单、验收摘要、Phase 1 自检和安全断言。
- `generation-workspace.html`: 本地核心一键生成工作台。页面通过单一 `POST /api/phase2/workflows/content-generation/run` 从一份本地教学素材生成 Lab / Exam / Grading / PPT 四类 DSL，展示批次进度、Schema/内容质量摘要、四个任务 ID 和对应审核入口；所有任务固定进入 `WAITING_REVIEW`。默认使用 Mock Provider；真实模式必须显式确认，模型密钥只由同源后端从环境变量读取。页面不直接调用模型 Provider、不接收 API Key、不自动审核、不发布、不执行选手代码，并固定 `answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false`、`autoPublishAllowed=false`。
- `review-center.html`: Phase 1/2 审核中心静态原型，展示本地 Mock 队列、只读 API 动态队列、任务详情、`reviewPage.dslPreview` 真实 DSL 文件摘要、`reviewPage.artifactGroups`、`reviewPage.qualitySignals`、`reviewDetail.contentQualitySummary` / `reviewPage.contentQualitySummary`、`reviewDetail.gradingRecords.reviewIntegration` 评分记录人工复核状态、`reviewPage.platformImportPreviewActions`、`reviewPage.platformImportPreview`、`reviewPage.platformImportPreviewSignoff`、`reviewPage.platformEntityMockImport`、高风险 MCP 意图和禁用的批量动作。页面支持 URL 参数 `coreDbPath` 和 `gradingDbPath`；审核详情与核心就绪报告都会转发两者，使 `reviewDetail.gradingRecords` 与评分报告读取同一 SQLite 或 JSON staging 来源，并明确展示 `LOCAL_SQLITE_GRADING_RECORDS` / JSON staging。`MvpReviewWorkspace.staticFallbackContextLinks` 会在页面初始化、详情 404 或静态兜底时把“打开当前审核页”和“打开评分报告”刷新为带 `coreDbPath`、`gradingDbPath`、`agentReport` 的本地深链；`MvpReviewWorkspace.noHorizontalOverflow` 通过长状态、路径和 `entryHref` 换行，避免 1280px 宽度下横向滚动。
- `platform-entities.html`: 平台实体草稿页面，当前默认展示本地 Lab / Exam / Grading / PPT mock-import 草稿、导入就绪报告、`platformEntityImportActivity`、本地 import-dry-run DTO、受控评分 evidence 和评分记录复核摘要。页面支持从审核中心通过 `entityId`、`sourceTaskId`、`entityKind=lab|exam|grading|ppt`、`coreDbPath`、`gradingDbPath`、`agentReport` 深链进入并自动选择准备类型；URL 带 `coreDbPath` 时，列表、详情、已审核任务候选查询和 `POST /api/platform-entities/{id}/import-dry-run body.coreDbPath` 都使用同一 Backend Core repository。审核详情页的人工 approve/reject 也会将该上下文写回本地任务仓储，确保候选查询不会误读默认 JSON store。URL 同时带 `gradingDbPath` 时，`GET /api/platform-entities/readiness-report?sourceTaskId=...&coreDbPath=...&gradingDbPath=...` 会只读拼接评分记录复核证据，返回审核中心时也保留这些本地上下文。页面提供 `PlatformApiContractValidateAction` 手动调用 `POST /api/platform-entities/contract-validate` 校验 `examples/input/platform-contract.json`，并把同一份 `contractConfig` 用于本地 dry-run；该动作只读取本地 JSON，不读取密钥、不发送平台请求、不写库。`AgentEntityDemoDataPrepareAction` 可通过 `GET /api/ai-tasks?status=APPROVED&taskType={taskType}&coreDbPath=...` 加载已审核任务候选，再串联 `import-preview -> mock-import -> import-dry-run`，快速准备四类本地演示草稿。`LocalAgentEntityList.noHorizontalOverflow` 会让实体列表里的长 `entityType/sourceTaskId/status` 标签在卡片内换行，避免 1280px 演示宽度下出现内部挤出。页面默认只保留本地四步：mock-import、dry-run、返回审核中心、未来平台对接暂停说明；`import-send`、`import-status`、`import-result`、平台侧 `signoff` 和最终发布不提供按钮、不绑定 POST、不要求平台 API base URL 或平台 token，只作为后续其他团队真实平台对接参考。页面不输入或展示密钥，不自动审核，不执行真实发布。
- `ai-tasks.html`: Phase 1/2 AI 任务中心静态原型，展示任务列表、状态过滤、待审核摘要、`TaskExecutionWorkspace` 本地闭环导航和 Workflow 入口；页面引入 `ai-tasks-data.js` 作为渐进增强适配器，在同源 Backend Mock 启动时只读调用 `GET /api/ai-tasks`、`GET /api/ai-tasks?status=WAITING_REVIEW`、`GET /api/ai-tasks/{id}`、`GET /api/review-task-summary` 和按当前任务查询的 `GET /api/grading/records`，也可通过 `coreDbPath` 只读调用 `GET /api/backend/core-tasks`。`TaskExecutionWorkspace` 会把 `LOADED_LOCAL_SQLITE` 或 `LOADED_JSON_STAGING` 显示为评分记录读取状态；Exam / Grading 任务一旦已有 `GradingRecord.reportPath`，会启用评分报告与评分工作台入口，并保留 `coreDbPath`、`gradingDbPath`、`agentReport` 上下文。页面展示候选答案保护、下一步人工动作和 `method=GET only` 边界；长状态、本地路径和 report 参数会在卡片内换行，避免演示时横向滚动。接口不可用时保持 `STATIC_HTML_FALLBACK`。该适配器不发送 POST、不 approve/reject、不批量变更、不自动发布、不读取密钥。
- `labs.html`: Phase 1 Labs 管理静态原型，展示 Lab 列表、状态筛选、审核入口和发布阻断策略。
- `lab-generate.html`: 本地核心 Lab 生成工作台，展示本地素材分析、Prompt 版本、Lab DSL 预览、`LocalCoreGenerationWorkspace`、`LabGenerationCloseLoopAction` 和审核门禁；页面引入 `lab-generate-data.js` 作为渐进增强适配器，在同源 Backend Mock 启动时调用 `POST /api/labs/generate`，从本地 Markdown 素材生成 `WAITING_REVIEW` Lab 任务、Lab DSL 摘要、素材分析和 Provider 审计摘要。默认 `providerMode=mock`；明确选择 `real-llm`、确认真实调用后，页面只向同源后端传递模型 / 可选 Base URL，后端从环境变量读取密钥并复用相同的 DSL、Task、Artifact 和审核链路。URL 带 `coreDbPath` 时，生成请求会把 `coreDbPath` 写入 body，让任务和 Artifact 写穿到同一个本地 Backend Core repository；页面初始化和生成成功后，`LabGenerationCloseLoopAction` 都会刷新审核中心、Lab 审核页和本地导入预览深链，并保留 `coreDbPath`、`gradingDbPath`、`agentReport` 上下文，固定 `requiresHumanReview=true`、`realPlatformImport=false`、`realPublishAllowed=false`；接口不可用时保持 `STATIC_HTML_FALLBACK`。页面自身不读取密钥、不直接调用模型 Provider、不抓取远程素材、不执行未知 Shell、不自动审核、不发布。
- `lab-review.html`: Phase 1/2 Lab 审核详情静态原型，展示单个 Lab DSL 审核任务、Timeline、风险摘要、`generationProfile`、`qualitySignals`、`providerSummary.qualitySummary`、Provider 调用质量卡片和操作栏。
- `ppt.html`: 本地 PPT DSL 清单，提供生成页和审核页入口；真实 PPT 文件生成、自动发布和真实发布均不可用。
- `ppt-generate.html`: 本地核心 PPT 生成工作台，使用同源 Backend Mock 的 `POST /api/ppt/generate` 从本地 Markdown 创建 `WAITING_REVIEW` PPT DSL 任务，展示安全摘要、产物路径、审核中心、PPT 审核页与 PPT Deck 本地导入预览深链；默认 Mock，显式确认后可经同源后端请求真实 LLM DSL，前端不读取、保存或传递模型 API Key。
- `grading-workspace.html`: 本地自动评分工作台。页面通过 `POST /api/grading/jobs` 创建本地评分任务、通过 `POST /api/grading/jobs/{id}/run` 同步运行已有的受控评分能力、通过 `GET /api/grading/records` 读取派生的 `GradingRecord`，并通过 `POST /api/grading/records/{id}/review` 记录 `approve-ready`、`needs-evidence` 或 `needs-revision` 人工复核。URL 支持 `taskId`、`coreDbPath`、`gradingDbPath`、`agentReport` 本地上下文；AI Task 与 Review Center 都会只读查询最新 `GradingRecord.reportPath` 后才启用对应评分报告链接，避免将 Grading DSL 文件误当作评分报告。页面不读取模型密钥，不自动审核、不发布、不调用真实平台，且默认将受控 Docker evidence 作为可选本地执行能力。
- `ppt-review.html`: Phase 1/2 PPT 审核详情静态原型，展示单个 PPT DSL、Slide Plan、Timeline、审核策略、真实 PPT 文件生成禁用策略、Demo Bundle 已生成的待审核 PPTX Artifact 摘要、逐页审核状态、人工批注、QA 信号摘要，以及 `PptPageReviewUpdateAction` 页级审核更新 Mock 入口。任务人工批准后可调用既有 `POST /api/ppt/import-preview` 和 `POST /api/ppt/mock-import`，并带本地仓储上下文进入 Platform Entities；不会发送真实平台请求或发布。
- `exams.html`: Phase 1 Exams 管理静态原型，展示 Exam 列表、Grading DSL 关联和标准答案隐藏策略。
- `exam-review.html`: Phase 1/2 Exam 审核详情静态原型，展示 Exam DSL、Grading DSL、Timeline、审核策略、标准答案隐藏策略、`questionGradingRefCoverage`、`scoreCoverage` 和评分计划可解释性。
- `exam-generate.html`: 本地核心 Exam / Grading 生成工作台，展示 Lab ID 输入、Lab DSL 路径、Exam DSL / Grading DSL 预览、`LocalCoreGenerationWorkspace`、`ExamGenerationCloseLoopAction` 和标准答案隐藏策略；页面引入 `exam-generate-data.js` 作为渐进增强适配器，在同源 Backend Mock 启动时调用 `POST /api/exams/generate-from-lab`，从 Lab ID 生成 `WAITING_REVIEW` Exam / Grading 任务摘要、候选安全题目摘要和 Provider 审计摘要。默认 Mock；明确选择 `real-llm` 后后端校验本地 Lab DSL 并从环境变量读取密钥。URL 带 `coreDbPath` 时，生成请求会把 `coreDbPath` 写入 body，让 Exam / Grading 任务和 Artifact 写穿到同一个本地 Backend Core repository；页面初始化和生成成功后，`ExamGenerationCloseLoopAction` 都会刷新审核中心、Exam 审核页、Grading 审核页、Exam 本地导入预览和 Grading 本地导入预览深链，并保留 `coreDbPath`、`gradingDbPath`、`agentReport` 上下文，固定 `answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false`、`sandboxExecuted=false`、`realPublishAllowed=false`；接口不可用时保持 `STATIC_HTML_FALLBACK`。页面自身不读取密钥、不直接调用模型 Provider、不执行真实沙箱、不展示标准答案或 `gradingRef` 给选手端、不自动审核、不发布。
- `grading.html`: Phase 1/2 Grading 管理静态原型，展示 Grading DSL 清单、Phase 2 `phase2_grading_generation` Mock 生成入口、Mock 评分入口、报告入口、`reportDetail` 摘要、`gradingRefCoverage` / `scoreCoverage` / `assessmentPlan` 质量信号和真实执行禁用策略。
- `grading-review.html`: Phase 1/2 Grading 审核详情静态原型，展示 Grading DSL、Mock 报告预览、`reportDetail` 审核关注项、`AssessmentPlanManualReviewChecklist`、`gradingRefCoverage`、`scoreCoverage`、`explainability`、Timeline、审核策略和真实执行禁用策略。
- `grading-report.html`: 本地核心评分报告页，读取已有本地评分 evidence，接口不可用时保留静态 fallback；展示 `ReviewerReportWorkspace` 首屏审核工作区、`ReviewerSafetySummary` 审核员安全摘要、`reportDetail`、`sandboxPolicy`、`explainability`、`assessmentPlanSummary`、`checkPlans[].assessmentPlan*`、`mockEvidence`、`file_exists` / `stdout_contains` / `pytest` / `notebook_cell` / `json_field` / `log_keyword` 六类 check 计划、`GradingRecordReviewSummary` 评分记录人工复核状态、审计入口和安全标记。`GradingRecordReviewSummary` 会明确标示本次读到的是 `LOCAL_SQLITE_GRADING_RECORD` 或 JSON staging，并展示 `approve-ready`、`needs-evidence`、`needs-revision` 结论及其阻断动作。`ReviewerReportWorkspace` 只读汇总得分、evidence readiness、decision note、GradingRecord 复核、候选答案保护和下一步人工审核入口，并在返回审核中心时保留 `coreDbPath`、`gradingDbPath`、`agentReport` 上下文；页面不执行评分、不自动审批、不调用真实平台。
- `environments.html`: Phase 1 环境管理静态原型，展示 VM / Notebook Mock 记录、状态流转和操作审计。
- `skills.html`: Phase 1 Skills 管理静态原型，展示 Skill、Prompt、Workflow、DSL Schema 和 CLI Mock 的关联关系。
- `provider-settings.html`: Phase 1 Provider 设置静态原型，展示 MockProvider 启用态、真实 Provider 禁用态和密钥不展示策略。
- `workflows.html`: Phase 2 Workflow Registry 静态原型，展示四条 Mock Workflow 能力、MCP Mock 工具、CLI/Backend 入口和禁用动作。
- Dashboard 和 AI Task Center 可使用 `GET /api/review-task-summary` 展示待审核队列摘要；批量状态变更在 Phase 1 固定禁用。
- 审核详情页使用 `GET /api/review-tasks/{id}` 的聚合 Mock 数据，减少前端分别拼接任务、产物、Workflow 和审计事件；当 URL 带 `agentReport` 或 `coreDbPath` 时，`lab-review.html`、`exam-review.html`、`grading-review.html` 和 `ppt-review.html` 会把查询参数继续传给详情 API，只读打开真实 workflow report 中的 synthetic review detail。
- `examples/review-detail/lab-review-detail.json` 提供审核详情页可参考的静态 Mock 示例。

## 输出说明

当前输出是前端信息架构、Mock UI 数据和可直接打开的静态原型，不是生产前端应用。

`console.html` 演示 Phase 1 前端 2.0 统一入口。页面串联 `/dashboard`、`/delivery`、`/ai-tasks`、`/review-center`、Lab、Exam、Grading、PPT、Environment、Skills 和 Provider Mock 原型，只做本地导航和安全状态展示，不启动真实前端工程。

Phase 1 本地演示验收步骤见 `scripts/phase1-demo.runbook.md`，机器可测契约见 `scripts/phase1-demo.runbook.json`。Runbook 只引用 `scripts/manifest.json` 中的白名单验证命令；本地页面预览是人工动作，不作为自动脚本执行。

`dashboard.html` 演示 Phase 1 运营首页，聚合健康状态、待审核压力、Workflow Run、Artifact 清单、安全总览和 Grading `AssessmentPlanDashboardSignal`。首页读取 `GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary` / `gradingReviewPrototype.assessmentPlanSummary`，把 `planTotal`、`alignedWithChecks`、`riskLevel`、`MOCK_EVIDENCE_NOT_COLLECTED`、`realSandboxEvidenceRequired` 和 `requiredLimits` 作为待审核压力提示展示；它不启动前端工程，也不请求真实服务。

`audit.html` 演示审计可观测只读页。页面串联 `GET /api/provider-audit-events`、`GET /api/mcp-tool-call-records`、`GET /api/workflow-runs`、`GET /api/audit-events` 和 `GET /api/review-audit-events`，展示 `providerCallAuditEvents`、`mcpToolCallRecords`、`highRiskMcpIntentPrototype`、`secondConfirmationStatusPrototype` 与 `MOCK_GRADING_RUN` 的 `mock_grading_runner/checkSummary/checkPlans` 摘要；评分审计同时展示 `AssessmentPlanAuditSignal`、`operationAuditEvents.detail.assessmentPlanSummary`、`assessmentPlanSummary.source=grading.spec.assessmentPlan`、`assessmentPlanAlignedWithChecks=true`、`checkPlans[].assessmentPlanSourceField`、`assessmentPlanExecutionPlan`、`assessmentPlanMockEvidence` 和 `checkPlans[].containerSandboxPlan`，确保报告页与审计页能追溯同一份 `spec.assessmentPlan` 与容器 dry-run 计划。`publish_lab`、`publish_exam`、`destroy_environment` 仅展示高风险审核意图、`postReviewDisposition`、二次确认只读状态和操作审计，不启动真实 MCP Server、真实 Agent、真实 Provider、真实沙箱或真实后端。

`audit-detail.html` 演示审计详情钻取页。页面串联 `GET /api/provider-audit-events`、`GET /api/mcp-tool-call-records`、`GET /api/workflow-runs/{id}` 和 `GET /api/audit-events`，展示 `auditDetailPrototype.selectedRecords`、Trace 关联、脱敏参数、错误上下文和关联 Workflow Step；新增 `AssessmentPlanManualReviewTrace` 只读追溯卡片，引用 `gradingReviewPrototype.assessmentPlanManualReviewChecklist` 与 `reviewCenterPrototype.nextManualReviewAction`，把 `task_grading_demo` 的 5 项人工复核清单追到 `operationAuditEvents[action=MOCK_GRADING_RUN].detail.assessmentPlanSummary`。页面不重试真实调用，不读取密钥，不运行真实沙箱，不执行选手代码。

`audit-incidents.html` 演示审计异常复盘页。页面串联 `GET /api/provider-audit-events`、`GET /api/mcp-tool-call-records`、`GET /api/workflow-runs` 和 `GET /api/audit-events`，展示 `auditIncidentReviewPrototype.incidents` 和本地 `incidentRules`，只给出安全 Mock 命令建议，不自动修复、不导出真实事故报告、不重试真实调用。

`operations-launchpad.html` 演示运营入口只读工作台。页面串联 `frontend/mock-data.json.operationsLaunchpadPrototype`、`frontend/mock-data.json.consolePrototype`、`frontend/mock-data.json.deliveryPrototype` 和 `frontend/ui.manifest.json`，集中打开 Console、Demo Map、Runbook、Acceptance、Delivery、Audit 和 Review Center，不运行命令，不上传交付包，不批量状态变更。

`operations-presenter.html` 演示运营 Presenter View 只读工作台。页面串联 `frontend/mock-data.json.operationsPresenterPrototype`、`frontend/mock-data.json.operationsDemoScriptPrototype`、`frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath`、`frontend/mock-data.json.realDemoPrototype.realDemoAcceptanceSummary`、`delivery/phase1-demo-script-checklist.json` 和 `delivery/DEMO_SCRIPT_CHECKLIST.md`，展示 14 个步骤、14 条 speakerCue、8 个验收信号、8 个禁止动作、175/175 交付状态、白名单命令、`CoreBusinessDemoPath` 演示主线和 `RealDemoAcceptanceSummary` 闭环摘要；其中 `review_priority_queue_visible` 展示 CLI `review batch-summary`、Backend Mock `GET /api/review-task-summary` 与 MCP Mock `get_review_task_summary` 的 `reviewPriorityQueue` 同源追溯，固定 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`；`CoreBusinessDemoPath` 固定展示 `/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report`、`stepTotal=6`、`dslValidatedTotal=4`、`waitingReviewDslTotal=4`、`readonlyEvidenceDemoEarnedScore=70`、`pptPageReviewActionVisible=true` 和 `reviewRequiredBeforePublish=true`；`RealDemoAcceptanceSummary` 固定展示 `acceptancePassed=true`、`passedCount=7`、`failedStepIds=[]`、`mcpOutputContractIncludesRealDemoReviewQueue=true`、`readonlyEvidenceCollectedTotal=2` 和 `realPublishAllowed=false`；`assessment_plan_audit_trace_visible` 展示 `AssessmentPlanAuditSignal`、`gradingReport.assessmentPlanSummary` 与 `operationAuditEvents.detail.assessmentPlanSummary` 的同源追溯，不运行命令，不上传交付包，不启动真实服务。

`operations-signoff.html` 演示签收总览只读工作台。页面串联 `frontend/mock-data.json.operationsSignoffPrototype`、`frontend/mock-data.json.deliveryPrototype`、`frontend/mock-data.json.operationsAcceptancePrototype`、`frontend/mock-data.json.reviewCenterPrototype.reviewPriorityQueue`、`frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath`、`frontend/mock-data.json.realDemoPrototype.realDemoAcceptanceSummary`、交付契约和 Runbook，展示 7/7 门禁、175/175 交付、20/20 自检、14/14 验收、7/7 安全断言、本地证据、`CoreBusinessDemoPath` 签收提示、`RealDemoAcceptanceSummary` 签收提示和审核优先队列签收提示；队列签收固定显示 `topPriorityTaskId=task_grading_demo`、`topPriorityReasonCode=HIGH_RISK_MOCK_EVIDENCE_REQUIRED`、`recommendedAction=review_grading_plan_before_publish`；核心业务演示签收固定显示 `core_business_demo_path_visible`、`stepTotal=6`、`readonlyEvidenceDemoEarnedScore=70`、`pptPageReviewActionVisible=true` 和 `reviewRequiredBeforePublish=true`；闭环摘要签收固定显示 `real_demo_acceptance_summary_passed`、`acceptancePassed=true`、`passedCount=7`、`mcpOutputContractIncludesRealDemoReviewQueue=true` 和 `failedStepIds=[]`，并保持 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`autoPublishAllowed=false`、`realPublishAllowed=false`，不运行命令，不上传交付包，不启动真实服务。

运营演示脚本检查清单位于 `delivery/DEMO_SCRIPT_CHECKLIST.md`，机器契约位于 `delivery/phase1-demo-script-checklist.json`。`operations-demo-script.html` 是该清单的静态页面版，串联 `frontend/mock-data.json.operationsDemoScriptPrototype`、验收信号、`reviewPriorityQueue`、`assessmentPlanSummary.source=grading.spec.assessmentPlan`、白名单命令和禁用动作；其中审核优先队列通过 CLI / Backend / MCP 三链路同源展示，只读展示，不执行检查清单中的命令。

`operations-runbook.html` 演示运营 Runbook 只读工作台。页面串联 `frontend/mock-data.json.operationsRunbookPrototype`、`scripts/phase1-demo.runbook.json` 和 `scripts/manifest.json`，展示入口阅读、静态页面预览、白名单验证命令、审计复盘和安全红线，不运行命令，不启动真实服务。

`operations-acceptance.html` 演示运营验收只读工作台。页面串联 `frontend/mock-data.json.operationsAcceptancePrototype`、`config/delivery-package.contract.json`、`delivery/FAQ.md`、`delivery/HANDOFF.md` 和 `delivery/PHASE2_READINESS.md`，展示验收项、关联静态页面、白名单命令和安全断言；新增 `assessment_plan_audit_trace_visible` 验收项，确认 `gradingReport.assessmentPlanSummary`、`operationAuditEvents.detail.assessmentPlanSummary`、`checkPlans[].assessmentPlanSourceField` 与 `AssessmentPlanAuditSignal` 对齐，不上传交付包，不运行命令，不发布真实内容。

`operations-demo-map.html` 演示运营页面地图只读工作台。页面串联 `frontend/mock-data.json.operationsDemoMapPrototype`、`frontend/ui.manifest.json` 和 `frontend/mock-data.json`，按运营、审核员、教师和研发视角组织 6 段演示路径，不运行命令，不批量变更状态，不上传交付包。

`delivery.html` 演示 Phase 1 交付验收总览。页面串联 `config/delivery-package.contract.json`、`phase1 check`、`phase1 export`、验收清单和安全断言，只展示本地 Mock 交付状态，不上传交付包，不发布真实内容。

`review-center.html` 演示审核队列摘要、单任务详情、DSL 预览、Timeline、`CoreWorkflowReadiness`、`RealDemoReviewQueue`、`ControlledDockerEvidenceReviewSignal`、`NotebookEvidenceReviewPlan`、`ReviewPriorityQueue`、`NextManualReviewAction`、Grading `assessmentPlan` 队列信号、`RealDslContentQualityDecision` 内容质量决策、`PlatformImportPreviewActionPanel` 平台导入预览入口、`PlatformImportPreviewSummary` 平台导入预览摘要、PPT `PptPageReviewUpdateAction` 页级审核入口、Exam / Grading `QualitySignalQueueSummary`、高风险 MCP 意图面板、二次确认只读状态面板和操作栏安全策略。页面引入 `review-center-data.js` 作为渐进增强适配器：若通过 `python -m backend.mock_http_server --host 127.0.0.1 --port 8000` 启动同源 Backend Mock API，它先通过 `GET /api/review-task-summary?limit=3&detailMode=light` 更新首屏队列数量、优先级摘要和受控评分证据信号，渲染只读“API 动态队列”；该队列会追加 `realDemoReviewQueue` 里的本地真实产物卡片，优先展示 `examples/output/real-llm-lab.json`、`real-llm-exam.json`、`real-llm-grading.json`、`real-llm-ppt.json` 和 PPTX artifact，并在 Mock store 中存在匹配 `finalResultPath` 的 `WAITING_REVIEW` 任务时优先打开真实任务详情。点击动态任务只会更新 `taskId` 查询参数并调用 `GET /api/review-tasks/{id}` 和 `GET /api/review-tasks/{id}/core-readiness` 加载详情与核心闭环下一步；如果只有本地产物没有对应任务，卡片保持只读禁用并提示先运行真实 workflow / one-click 写入 store。右侧详情摘要会同步展示任务标题、任务类型、状态、artifact 数、workflow step 数、`rejectRequiresReason`、`autoPublishAllowed=false`、`realPublishAllowed=false` 和 `sandboxExecuted=false`，`RealDslContentQualityDecision` 会读取 `reviewDetail.contentQualitySummary` / `reviewPage.contentQualitySummary`，展示 `decisionStatus`、`recommendedAction`、`requiresRevisionBeforeImportPreview`、`requiresEvidenceBeforeFinalApproval`、ready/blocked kinds、blockers 和 warnings，用于区分“可进入导入预览”“需先修订”“Grading 最终通过前需补 evidence”；`CoreWorkflowReadiness` 会展示 `recommendedNextAction`、ready/blocked step 数、`gradingManualReviewChecklistStatus`、`gradingDecisionNoteRecommendation`、`gradingNextDecisionNoteAction`、平台实体与 Grading evidence 缺口；对 Grading 任务，core readiness 会先展示 evidence / decision note 缺口，再展示平台导入步骤，固定 `readOnly=true`、`autoApproveAllowed=false`、`autoPublishAllowed=false`、`realPublish=false`；页面也会把 `reviewPage.dslPreview` 的 kind、artifactKind、artifactId、status、path、`contentLoaded`、`schemaValidated`、真实 DSL 标题、summary、safePreview、candidateSafety 和 reviewSafety 渲染到 DSL Preview 区块：Lab 展示步骤/目标/环境摘要，Exam 只展示候选安全题目摘要并保持答案和 gradingRef 不展开，Grading 展示 checks / assessmentPlan / 沙箱前置摘要，PPT 展示 slide 数和标题摘要；若详情接口失败，状态条会保持 `API_READONLY_LOADED` 并显示 `DETAIL_LOAD_FAILED`，只有摘要接口不可用时才保持 `STATIC_HTML_FALLBACK` 静态演示。该适配器只允许发送 `POST /api/grading/evidence-auto` 生成本地评分证据报告，以及 PPT 页级审核元数据更新；不 approve/reject/publish、不绕过人工审核、不读取密钥。`RealDemoReviewQueue` 的 API 数据源为 `reviewTaskSummary.realDemoReviewQueue + local examples/output real LLM artifacts`，返回 `sourceMode`、`localArtifactTotal`、`schemaValidatedTotal`、`dynamicTaskTotal`、`dynamicTaskAvailable`、`dynamicTaskId` 和 `fallbackTaskId`，仍保持 `answerVisibleToCandidate=false`、`autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`realPublishAllowed=false`；`PlatformImportPreviewActionPanel` 读取 `GET /api/review-tasks/{id}.reviewDetail.platformImportPreviewActions` 和 `reviewPage.platformImportPreviewActions`，在生成预览前列出 `lab import-preview`、`exam import-preview`、`grade import-preview` 的 CLI、Backend API 和 MCP Tool 入口，并显示 `previewAlreadyCreated` 状态；`PlatformImportPreviewSummary` 读取 `GET /api/review-tasks/{id}.reviewDetail.platformImportPreview` 和 `reviewPage.platformImportPreview`，展示 `lab_template`、`exam_question`、`grading_rule` 三类本地平台草稿导入预览，固定 `databaseWritten=false`、`realPlatformImport=false`、`realPublishAllowed=false`；`ControlledDockerEvidenceReviewSignal` 优先读取 `reviewDetail.controlledGradingEvidence`，没有动态 evidence 时回退 `realDemoPrototype.controlledDockerEvidenceDemo`，把 `examples/output/mimo-real-demo-controlled-plan.json` 与 `examples/output/mimo-real-demo-controlled-sandbox-report.json` 的受控 Docker 证据展示到审核中心：`check_q1` / `check_q4` 已通过 `stdout_contains` / `pytest` 覆盖，`executed=2`、`passed=2`、`earnedScore=40/40`，而 `check_q2` / `check_q3` 仍是 `notebook_cell` 缺口，`remainingScore=60`、`remainingStatus=STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW`；`NotebookEvidenceReviewPlan` 读取 `realDemoPrototype.generatedDsl.grading.spec.assessmentPlan + reviewTaskSummary.controlledDockerEvidenceReviewSignal`，把 `check_q2` / `check_q3` 展开为 `STATIC_NOTEBOOK_JSON_PARSE_REVIEW`，列出 `verify_notebook_cell_targets`、`verify_expected_output_tokens`、`review_static_notebook_evidence_matches_expected_tokens` 和 `confirm_no_notebook_kernel_started`，并固定 `notebookKernelStarted=false`、`notebookExecuted=false`、`contestantCodeExecuted=false`；`ReviewPriorityQueue` 读取 `reviewTaskSummary.items + reviewDetail.qualitySignals + reviewDetail.assessmentPlan + reviewDetail.assessmentPlan.manualReviewChecklist`，按 `riskLevel=high`、`mockEvidenceStatus=MOCK_EVIDENCE_NOT_COLLECTED`、`manualReviewChecklist.status=NEEDS_HUMAN_REVIEW`、`candidateSafeExamPreview.answersRemoved=true`、`qualitySignalStatus=NEEDS_REVIEW` 排序；质量信号只辅助人工审核，不自动通过或发布；`publish_lab`、`publish_exam`、`destroy_environment` 仅作为 `reviewIntentOnly=true` 的高风险意图展示，真实发布、真实环境销毁、二次确认通过和绕过审核固定禁用。

`CoreWorkflowReadiness` 的 `next single-step action guide` 会把可继续执行的 `execute-core-next-tool` CLI 建议命令展示在审核中心，并提供“复制建议命令”按钮。页面会根据同一条建议自动生成 `review-center.html?taskId={taskId}&agentReport={outputPath}` 回看链接，并提供“复制执行后回看链接”按钮。两个按钮都只写入剪贴板，状态固定记录 `commandExecuted=false` 与 `stateChanged=false`，不会在浏览器中执行命令、不会调用审核通过/发布接口，也不会改变任务状态。

审核中心支持把任意真实 LLM workflow report 作为自定义真实输出批次打开，例如 `review-center.html?agentReport=examples/output/p0-deepseek-v4-flash-live-workflow-report.json`。同源 Backend Mock 启动后，页面会把该参数传给 `GET /api/review-task-summary?detailMode=light&agentReport={workflowReport}`，并把 report 内的 `generatedDsl.lab/exam/grading/ppt.dslPath` 映射为 `RealDemoReviewQueue` 四个队列项。点击队列项会继续调用 `GET /api/review-tasks/{id}?agentReport={workflowReport}`；页面上的“打开 Lab / Exam / Grading / PPT 审核”入口也会保留当前 `agentReport` 和 `coreDbPath`，跳到独立的 `lab-review.html?taskId=...&agentReport=...`、`exam-review.html?taskId=...&agentReport=...`、`grading-review.html?taskId=...&agentReport=...` 和 `ppt-review.html?taskId=...&agentReport=...` 时继续沿用同一份 report。当 taskId 不在当前 Mock store 时，后端会生成只读 synthetic review detail；如果轻量 report 只有 DSL 路径而没有 taskId，队列和详情会使用 `real_demo_lab` / `real_demo_exam` / `real_demo_grading` / `real_demo_ppt` fallback。页面仍能展示 `reviewPage.dslPreview`、`reviewPage.artifactGroups`、DSL Preview 链接、Workflow Report 链接和候选安全预览。Exam 的候选预览固定不展开 `answer` 和内部 `gradingRef`，页面显示 `candidateSafety.answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false`、`answersRemovedFromSafePreview=true`。该路径只读本地 report 和 DSL 文件，不再次请求真实 LLM、不读取密钥、不 approve/reject、不发布。

审核中心支持通过 URL 参数 `agentReport=examples/output/demo-agent-core-next-tool-execution-{taskId}.json` 只读加载 Agent 单步执行报告。页面调用 `GET /api/workflow/report?file={agentReport}` 读取既有 JSON，展示 `agentCoreNextToolExecution`、`postExecutionCoreNextToolPlan` 和 `nextSingleStepActionGuide`，用于人工回看“刚刚执行了哪个推荐工具、执行后下一步是什么”。当报告中的 `nextSingleStepActionGuide.canContinueWithSameCommand=true` 时，页面会启用“复制报告下一步命令”，只把报告里的下一条 CLI 建议复制到剪贴板。该面板不运行 Agent、不执行 CLI、不调用真实 LLM、不自动审核、不发布。

`MVP Review Workspace` 是 `review-center.html` 的首屏汇总工作区，复用已有 `GET /api/review-task-summary`、`GET /api/review-tasks/{id}` 和 `GET /api/review-tasks/{id}/core-readiness` 数据，集中显示四类真实 DSL 批次校验数、当前任务、评分证据状态、本地导入预览状态、当前审核入口、评分报告入口和下一步人工动作。该工作区不新增后端接口，不执行 CLI，不调用 approve/reject/publish，只把页面下方已有详情面板的关键信号提前到首屏，避免演示时在队列、证据、导入预览和报告入口之间来回查找。

`review-center.html` 还会读取 `reviewDetail.reviewPage.providerSummary.qualitySummary` 与 `calls[].qualitySummary`，在真实演示审核队列中展示 `ProviderQualitySummary`：`readyForReview=true`、`normalizationPatchCount=1`、`schemaRepairApplied=false`、`apiSurface=chat.completions`、`responseId=resp_demo_lab_quality` 和 `providerAdapter=openai_responses_sdk_adapter`。当 `reviewDetail.mergedGradingEvidence.checkEvidenceReviewItems` 可用时，页面会在 `MergedGradingEvidenceReviewSignal` 面板中展开 check 级证据，显示每个 check 的 id/type、状态、得分、只读或受控 Docker 来源、建议人工动作和 `manualReviewRequired`，固定 `autoApproveAllowed=false`、`realPublishAllowed=false`，只辅助审核员复核，不自动通过。页面也会把 `reviewTaskSummary.gradingEvidenceReadinessSignal` 与队列项 `gradingEvidenceReadinessSummary` 展示为 `GradingEvidenceReadiness`，汇总 `evidenceReadyTotal`、`missingEvidenceTotal`、受控命令缺口、只读静态缺口和下一步证据动作；其 `GradingEvidenceActionGuide` 会给出 `POST /api/grading/evidence-auto`、`python lab_cli.py grade evidence-auto --task-id <taskId>`、打开最新评分报告和记录审核 decision note 的人工步骤；`GET /api/review-tasks/{id}` 会同时返回 `reviewDetail.preApproveReviewCheck` 与 `reviewDetail.reviewPage.preApproveReviewCheck`，页面据此刷新 `DecisionNoteNextStep`、`scorePreviewStatus`、预览得分、缺失分、`scorePreviewReadyForDecisionNote` 和最终人工通过 readiness。审核中心会从 URL 参数、`core-readiness.summary.gradingDecisionNoteRecommendation` 或 `mergedGradingEvidence.summary.decisionNoteRecommendation` 读取推荐 `approve-ready` / `needs-evidence` / `needs-revision`，高亮对应按钮并把 `decisionNoteRecommendationReason` 作为提交 reason，但仍要求人工点击确认；`POST /api/grading/evidence-auto` 成功后，页面会先用响应报告即时刷新评分报告入口、`MergedGradingEvidenceReviewSignal`、`GradingEvidenceReadiness` 和 `PreApproveReviewCheck` 文案，再调用 `GET /api/review-tasks/{id}` 做最终回填；`POST /api/review-tasks/{id}/decision-note` 成功后会即时刷新 `DecisionNoteNextStep` 和 `PreApproveReviewCheck`，只有 latest decision 为 `approve-ready` 时才把 `FinalHumanApproveReadiness` 推到 `READY_FOR_HUMAN_APPROVE`，`needs-revision` 会提示修订评分 DSL 或 evidence，`needs-evidence` 会提示补充/复核 evidence；`FinalHumanApproveReadiness` 会展示 `finalReviewState=READY_FOR_HUMAN_APPROVE|NEEDS_MORE_EVIDENCE|NEEDS_REVISION|WAITING_DECISION_NOTE|WAITING_EVIDENCE`、`humanApproveReady`、`approveReadyDecision`、`scorePreviewStatus`、`scorePreviewReadyForDecisionNote`、`singleTaskManualApproveOnly` 与 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`autoPublishAllowed=false`、`realPublishAllowed=false`，但不会调用 approve API。该摘要只读取已有 `mergedGradingEvidence.checkEvidenceReviewItems` 与 `scorePreview`，Action Guide 只调用既有 evidence-auto 能力，不自动审核、不发布、不读取密钥。平台实体 readiness 卡片会直接展开 `platformEntityImportActivity` 的最新 dry-run、send、status query、result record 摘要，包括 `latestDryRunArtifact`、`latestSendStatusCode`、`latestStatusQuery`、`latestResultStatus` 和 `platformDraftId`，方便审核员不跳页也能确认人工导入进度。审核中心的 `API Platform Entity Mock Import` 卡片也会按 entityId 合并 `platformEntityReadinessReport.items[]`，在每个本地草稿旁展示 `activitySummary`、`signoffState`、`readyForSignoff`、`postSignoffPrePublishChecklist`、`finalPublishReviewDecision`，并只给出 `打开实体详情` 与 `平台签收暂停` 本地查看入口。当平台结果为 `ACCEPTED_FOR_DRAFT` 且五项人工清单均满足时，卡片会展示 `READY_FOR_PLATFORM_ENTITY_SIGNOFF`、`readyForAgentEntitySignoff=true` 和 `manualSignoffChecklist`，只表示未来平台对接团队可参考的 readiness 证据，不自动通过、不自动发布；点击暂停入口只打开 `platform-entities.html` 本地详情和暂停说明，不携带平台签收 action 参数，返回审核中心时保留 `taskId`、`coreDbPath`、`gradingDbPath` 和 `agentReport`。

`ai-tasks.html` 演示 AI 任务中心的 Mock 展示。页面串联任务列表、待审核摘要、Workflow Timeline、审核详情入口、`ReviewPrioritySignal`、`NextManualReviewAction`、Lab `ProviderQualityTaskSignal`、Exam / Grading `QualitySignalTaskSignal` 和 Grading `AssessmentPlanTaskSignal`；`ReviewPrioritySignal` 读取 `reviewCenterPrototype.reviewPriorityQueue`，展示 `topPriorityTaskId=task_grading_demo`、`topPriorityReasonCode=HIGH_RISK_MOCK_EVIDENCE_REQUIRED`、`urgentTotal=1`、`highTotal=1`、`normalTotal=1` 和 `manualReviewChecklistNeedsHumanReviewTotal=5`，仅用于排序提示，不允许自动通过或批量状态变更；`ProviderQualityTaskSignal` 读取 `reviewDetail.reviewPage.providerSummary.qualitySummary` 和 `calls[].qualitySummary`，展示 `task_lab_demo` 的 `readyForReview=true`、`normalizationPatchCount=1`、`schemaRepairApplied=false`、`responseId=resp_demo_lab_quality` 和 `providerAdapter=openai_responses_sdk_adapter`，只辅助人工审核，不自动通过或发布；`NextManualReviewAction` 读取 `reviewCenterPrototype.nextManualReviewAction`，把下一步人工入口指向 `/review-center?taskId=task_grading_demo`，并通过 `reviewPriorityQueue.items[0].manualReviewChecklistSummary` 显示 5 项待人工核查清单，仍固定 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`realPublishAllowed=false`；质量信号读取 `examReviewPrototype.qualitySignals` / `gradingReviewPrototype.qualitySignals`，展示 `matchedCoverageTotal=4`、`explainablePlanTotal=2`、`candidateSafeExamPreviewTotal=1`、`questionGradingRefCoverage.status=MATCHED`、`gradingRefCoverage.status=MATCHED`、`scoreCoverage.status=MATCHED` 和 `assessmentPlanAlignedWithChecks=true`；Grading 任务行读取 `GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary` / `gradingReviewPrototype.assessmentPlanSummary`，展示 `planTotal`、`alignedWithChecks`、`riskLevel`、`MOCK_EVIDENCE_NOT_COLLECTED`、`realSandboxEvidenceRequired` 和 `requiredLimits`，禁止自动发布、批量状态变更、真实沙箱和真实 Agent 运行。

`labs.html` 演示 Lab 管理入口的 Mock 展示。页面串联 `GET /api/labs`、`GET /api/review-task-summary`、`/labs/generate` 和 `/labs/:id/review`，禁止批量状态变更、自动发布和真实发布。

`lab-generate.html` 演示从本地 Markdown 素材到 Lab DSL 的本地核心生成路径。页面强调 `Local Backend API`、`lab_generation_v0`、`WAITING_REVIEW` 和发布阻断；启动 `python -m backend.mock_http_server --host 127.0.0.1 --port 8000` 后，可在页面输入本地 Markdown 路径并通过 `POST /api/labs/generate` 创建待审核 Lab 任务。若页面 URL 带 `coreDbPath`，该路径会随 POST body 写入本地 Backend Core repository；生成后的审核中心、Lab 审核页和导入预览入口会继续保留 `coreDbPath`、`gradingDbPath`、`agentReport`。生成结果会展示 `labFeatureReadiness`，确认任务专属 Lab DSL、素材绑定、最小教学质量、人工审核和本地导入预览路径是否满足稳定 v1。页面只显示安全摘要，前端不直接调用真实 LLM、不读取密钥、不抓取远程素材、不执行未知 Shell、不发布。

`lab-review.html` 演示单个 Lab DSL 审核详情。页面强调 `GET /api/review-tasks/{id}`、`reviewPage.generationProfile.context`、`reviewPage.qualitySignals`、`reviewPage.providerSummary`、`reviewPage.providerSummary.qualitySummary`、`reviewPage.providerSummary.calls[].qualitySummary`、`materialCoverage.status=LINKED`、`qualitySignals.lab.matching.status=NEEDS_REVIEW`、`providerSummary.realLlmCalled=true`、`providerSummary.qualitySummary.readyForReview=true`、`POST /api/ai-tasks/{id}/approve`、`POST /api/ai-tasks/{id}/reject`、`rejectRequiresReason=true` 和 `realPublishAllowed=false`；Provider 质量摘要只辅助人工审核，不自动驳回或发布，不执行批量状态变更或真实发布。

`ppt.html` 是 PPT DSL 清单与入口。`ppt-generate.html` 通过同源 `POST /api/ppt/generate` 生成本地 Mock PPT DSL，并显示 `taskId`、`pptDslPath`、审核入口和 `WAITING_REVIEW` 停止状态；接口不可用时保留静态 fallback。两页都禁止生成真实 PPT 文件、自动发布和真实发布，且不读取或展示模型密钥。

`ppt-review.html` 演示单个 PPT DSL 的审核详情。页面强调 `GET /api/review-tasks/{id}`、`POST /api/ai-tasks/{id}/approve`、`POST /api/ai-tasks/{id}/reject`、`POST /api/review-tasks/{id}/ppt-page-review-status`、`python lab_cli.py review ppt-page-update`、`PptDslPreview`、`Slide Plan`、`realPptFileGenerated=false`、`generateRealPptFileEnabled=false`、`PPTX_FILE`、`pptxArtifactGenerated=true` 和 `autoPublishAllowed=false`。页面只读展示已有 PPTX Artifact，并展示 `PageReviewStatus`、`PptPageReviewUpdateAction`、`manualCommentRequired=true`、`qaSignalStatus=NEEDS_REVIEW`、`APPROVED` / `NEEDS_REVIEW` / `REVISE_REQUIRED` 三类逐页状态；页级更新要求 `reviewerRequired=true`，`REVISE_REQUIRED` 要求 `reviseRequiresComment=true`，写入 `PPT_PAGE_REVIEW_UPDATE` 操作审计并返回更新后的 `pageReviewSummary`，但保持 `taskStatusChanged=false`、`artifactStatusChanged=false`、`autoApproveAllowed=false`、`realPublishAllowed=false`。这些信号只辅助人工审核，不自动通过、不在前端生成真实 PPT 文件、不自动发布或真实发布。

`exams.html` 演示 Exam 管理入口的 Mock 展示。页面串联 `GET /api/exams`、`POST /api/exams/generate-from-lab`、`/exams/generate` 和 Grading DSL 预览，标准答案在候选人视角固定脱敏，禁止真实沙箱、自动发布和真实发布。

`exam-review.html` 演示单个 Exam DSL 与 Grading DSL 的审核详情。页面强调 `GET /api/review-tasks/{id}`、`candidateSafeExamPreview.answersRemoved=true`、`qualitySignals.coverage.questionGradingRefCoverage.status=MATCHED`、`qualitySignals.coverage.scoreCoverage.status=MATCHED`、`qualitySignals.coverage.explainability.assessmentPlanAlignedWithChecks=true`、`POST /api/ai-tasks/{id}/approve`、`POST /api/ai-tasks/{id}/reject`、`answerVisibleToCandidate=false` 和 `standardAnswerRevealToCandidate=false`，不执行真实沙箱、自动发布或真实发布。

`exam-generate.html` 演示从 Lab ID 到 Exam DSL / Grading DSL 的本地核心生成路径。页面强调 `Local Backend API`、`exam_generation_v0`、`grading_generation_v0`、`WAITING_REVIEW`、标准答案选手端隐藏和发布阻断；启动 `python -m backend.mock_http_server --host 127.0.0.1 --port 8000` 后，可在页面输入 Lab ID 并通过 `POST /api/exams/generate-from-lab` 创建待审核 Exam / Grading 任务摘要。若页面 URL 带 `coreDbPath`，该路径会随 POST body 写入本地 Backend Core repository；生成后的审核中心、Exam 审核页、Grading 审核页和两类导入预览入口会继续保留 `coreDbPath`、`gradingDbPath`、`agentReport`。页面只展示候选安全摘要，固定 `answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false`，前端不直接调用真实 LLM、不读取密钥、不执行真实沙箱、不发布。

`grading.html` 演示 Grading 管理入口的 Mock 展示。页面串联 `GET /api/grading`、`POST /api/grading/run`、`GET /api/grading/report`、`POST /api/phase2/workflows/grading-generation/run` 和 `/grading/:id/report`，展示 `phase2_grading_generation`、`gradingRefCoverage.matched=true`、`scoreCoverage.matched=true`、`assessmentPlanAlignedWithChecks=true`、`reportDetail.checkPlans`、`sandboxPolicy.executorBoundary`、`containerSandboxPlan.mode=CONTAINER_PLAN_ONLY`、`containerSandboxPlan.containerPlan.image`、`containerSandboxPlan.containerPlan.mounts[0].mode`、`containerSandboxPlan.resultPlaceholder.status=NOT_EXECUTED`、`EXPLAINABLE_MOCK_PLAN`、`MOCK_EVIDENCE_NOT_COLLECTED` 和 `requiredLimits` 摘要；只允许 Grading DSL Mock 生成和 Mock 评分入口，禁止真实沙箱、选手代码执行、未知 Shell、真实重评和真实发布。

`grading-review.html` 演示单个 Grading DSL 的审核详情。页面强调 `GET /api/review-tasks/{id}`、`reviewDetail.assessmentPlan`、`reviewPage.assessmentPlan`、`qualitySignals.coverage.gradingRefCoverage.status=MATCHED`、`qualitySignals.coverage.scoreCoverage.status=MATCHED`、`qualitySignals.coverage.explainability.assessmentPlanAlignedWithChecks=true`、`POST /api/ai-tasks/{id}/approve`、`POST /api/ai-tasks/{id}/reject`、`reportDetail` 审核关注项、`containerSandboxPlan.mode=CONTAINER_PLAN_ONLY`、`sandboxExecuted=false` 和 `contestantCodeExecuted=false`；`spec.assessmentPlan` 只作为后端聚合缺失时的兜底来源。页面新增 `AssessmentPlanManualReviewChecklist`，读取 `reviewCenterPrototype.nextManualReviewAction`，要求操作员逐项确认 `verify_assessment_plan_aligned_with_checks`、`confirm_mock_evidence_not_collected`、`confirm_real_sandbox_evidence_required_before_real_execution`、`verify_required_limits_present` 和 `confirm_no_execution_or_publish`，并固定 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`realSandboxRunEnabled=false`、`realPublishAllowed=false`。页面展示评分计划的 `inputSummary`、`executionPlan.requiredLimits`、`containerSandboxPlan`、`resultPlaceholder.status=NOT_EXECUTED`、`mockEvidence.status`、`riskLevel` 与沙箱限制，不执行真实沙箱、真实重评、自动发布或真实发布。

`grading-report.html` 演示自动评分报告页的 Mock 展示。页面强调 `mock_grading_runner`、`MOCK_PLAN_ONLY`、`CONTAINER_PLAN_ONLY`、`checkSummary.executed=0`、`sandboxExecuted=false`、`commandExecuted=false` 和 `contestantCodeExecuted=false`，展示 `reportDetail.sandboxPolicy`、`EXPLAINABLE_MOCK_PLAN`、`assessmentPlanSummary.source=grading.spec.assessmentPlan`、`assessmentPlanAlignedWithChecks=true`、`checkPlans[].assessmentPlanSourceField`、`checkPlans[].containerSandboxPlan`、`resultPlaceholder.status=NOT_EXECUTED`、`MOCK_EVIDENCE_NOT_COLLECTED`、`inputSummary`、`riskLevel` 和 `executionPlan.requiredLimits`，并可从审计页查看 `MOCK_GRADING_RUN` 的评分计划审计，不执行真实沙箱。

`environments.html` 演示环境管理页的 Mock 展示。页面强调 `provider=mock`、`realCloudResourceCreated=false`、`realCloudResourceChanged=false` 和操作审计，不创建、启动、停止、重置或销毁真实 VM / Notebook。

`skills.html` 演示运营复用 Skills 的 Mock 展示。页面强调 `businessCodeMayEmbedPrompts=false`、`outputMustBeDsl=true`、`WAITING_REVIEW` 和发布阻断，不启动真实智能体，不调用真实大模型。

`provider-settings.html` 演示 Provider 设置页的 Mock 展示。页面强调 `MockProvider` 是唯一启用 Provider，`OpenAI`、`Anthropic`、`Local Model` 均为禁用占位，API Key 只允许来自环境变量且不展示到前端。

`workflows.html` 演示 Phase 2 Workflow Registry 只读能力目录。页面串联 `GET /api/workflow-registry`、`GET /api/workflow-registry/{workflowId}`、`list_workflows` 和 `get_workflow` MCP Mock 工具，展示内容生成、试题改造、PPT 生成、Grading 生成四条 Mock Workflow；页面不运行 Workflow、不创建 AI Task、不写 Artifact、不启动真实 MCP Server 或 Agent。

`real-demo.html` 演示真实大模型产出成果的第一版可视化收口。页面读取 `frontend/mock-data.json.realDemoPrototype` 的静态摘要，对应 `examples/output/real-llm-demo-bundle.json`，展示 `CoreBusinessDemoPath` 主线：真实 Lab DSL、候选人安全 Exam DSL、保留原始 Grading DSL、只读 evidence 评分、真实 demo 受控 Docker evidence、PPTX Artifact 和 `PptPageReviewUpdateAction` 页级审核入口。页面新增 `RealDemoAcceptanceSummary` 面板，读取 `realDemoPrototype.realDemoAcceptanceSummary`，展示 `phase2 demo-bundle acceptance` 生成的 `examples/output/real-llm-demo-acceptance-summary.json`、`acceptance.passed=true`、`passedCount=7`、`mcpOutputContractIncludesRealDemoReviewQueue=true`、`readonlyEvidenceCollectedTotal=2`、`gradingEvidenceCoverage=100/100` 和 `failedStepIds=[]`。页面也新增 `RealDemoOneClickChecklist` 面板，读取 `realDemoPrototype.oneClickDemoChecklist` 和 `examples/output/real-llm-demo-checklist.json`，展示 `readyForDemo=true`、`acceptance=7/7`、`sections=6/6`、`generated_dsl/candidate_preview/grading_evidence_coverage/pptx_artifact/review_and_mcp/safety_boundaries`、`gradingEvidenceCoverage=100/100` 和只读安全边界。页面新增 `RealDslReviewPreview` 面板，读取 `realDemoPrototype.realDslReviewPreview`，直接展示真实 Lab 步骤、候选人安全 Exam 题面、教师审核专用 `gradingRef`、Grading assessmentPlan/checks 和 5 页 PPT 大纲；其中 `gradingRefVisibleToCandidate=false`、`teacherOnlyGradingRefVisibleInReview=true`。该主线固定 `stepTotal=6`、`reviewCenterLinked=true`、`pptPageReviewActionVisible=true`、`reviewRequiredBeforePublish=true`，并展示 Lab / Exam / Grading / PPT DSL 均为 `WAITING_REVIEW`、候选人预览 `answerVisibleToCandidate=false`、`readonlyEvidenceDemo.doesNotModifySourceGrading=true`、`readonlyEvidenceDemo.executionSummary.executed=2`、`readonlyEvidenceDemo.score.earnedScore=70`、`readonlyEvidenceDemo.reportDetail.mode=READONLY_REAL_SANDBOX_POC`、`controlledDockerEvidenceDemo.mode=CONTROLLED_DOCKER_SANDBOX_POC`、`controlledDockerEvidenceDemo.gradingPath=examples/output/mimo-real-demo-controlled-plan.json`、`controlledDockerEvidenceDemo.reportPath=examples/output/mimo-real-demo-controlled-sandbox-report.json`、`controlledDockerEvidenceDemo.score.earnedScore=40`、`notebookStaticEvidenceEarnedScore=60` 和 `controlledDockerEvidenceDemo.image.tag=ai-grading-python:0.1`；页面只读，不新增 LLM 请求、不读取密钥、不访问网络、不触发 Docker/pytest/Notebook/选手代码执行、不自动发布或真实发布。`review-center.html` 中的 `ControlledDockerEvidenceReviewSignal` 现在以 `reviewDetail.controlledGradingEvidence` 为优先数据源；当本地任务没有受控评分 artifact 时，`sourceMode=STATIC_DEMO_FALLBACK` 并回退展示 `realDemoPrototype.controlledDockerEvidenceDemo` 的静态演示证据；当 Backend summary 聚合到真实任务 evidence 时，`sourceMode=DYNAMIC_CONTROLLED_DOCKER_EVIDENCE`。

`review-center.html` 的 `CoreWorkflowReadiness` 面板会读取 `contentQualityReadiness` 与 `nextToolRecommendation.contentQualityReadiness`。当核心 readiness 返回 `CONTENT_QUALITY_REVISION_REQUIRED` 时，页面会展示 `contentQualityReadyForImportPreview=false`、阻塞 kind、`review revision-request` 建议命令和 `autoExecuteAllowed=false`，并把复制下一步命令停在人工修订请求，不会触发自动 approve、导入预览或真实发布。

`grading-report.html` 是 `LOCAL_CORE_MVP` 评分报告页：它加载已有演示闭环只读 evidence、受控 Docker evidence、Notebook 静态 evidence、总覆盖摘要、`GradingResultPreview` 候选人安全预览、`GradingEvidenceReadiness` 评分证据就绪摘要、`EvidenceAutoExecutionMatrix` 自动 evidence 执行矩阵、`EvidenceAutoScorePreview` 自动 evidence 分数预览、`ReviewerSafetySummary` 审核员安全摘要、`ReviewDecisionOutcome` 人工结论回流、`GradingRecordReviewSummary` 评分记录人工复核状态、`MergedEvidenceSourceChain` 检查项级证据来源链和 `ManualReviewActionChecklist` 人工复核动作面板；接口不可用时才使用静态 fallback。页面显示 `ReadonlyReportDetail.source=realDemoPrototype.readonlyEvidenceDemo.reportDetail`、`checkSummary.executed=2`、`readonlyEvidenceCollectedTotal=2`、`checkPlans[].readonlyEvidence.status=COLLECTED`、`sandboxExecutionRequest.mode=REAL_SANDBOX_REQUIRED`、`sourceGradingModified=false`，以及 `ControlledDockerEvidenceDemo.source=grade sandbox-run --execution-mode controlled-command`、`CONTROLLED_DOCKER_SANDBOX_POC`、`ai-grading-python:0.1`、`planPath=examples/output/mimo-real-demo-controlled-plan.json`、`reportPath=examples/output/mimo-real-demo-controlled-sandbox-report.json`、`check_q1 stdout_contains=1`、`check_q4 pytest=1`、`earnedScore=40/40`、`notebookStaticReportPath=examples/output/mimo-real-demo-notebook-static-report.json`、`check_q2/check_q3 earnedScore=60/60` 和 `gradingEvidenceCoverage=100/100`，用于从 `/real-demo` 或 `/review-center` 跳到 `/grading/:id/report` 时解释真实演示 evidence 的来源；`review-center.html` 的 `Grading Report Entry` 会从 `reviewDetail.mergedGradingEvidence.summary.latestReportPath` 生成 `grading-report.html?file={file}&taskId={id}`，静态演示项也提供 `entryHref=grading-report.html?file=examples/output/merged-evidence-report.json&taskId=real_demo_grading`，便于从审核中心直接打开带参数的报告页；页面引入 `grading-report-data.js` 作为渐进增强适配器：通过 `python -m backend.mock_http_server --host 127.0.0.1 --port 8000` 打开页面时，会按 URL 中的 `file` / `reportFile` 与 `taskId` / `id` 优先调用 `GET /api/grading/report?file={file}&taskId={id}` 并刷新首屏总分、得分、评分项、真实执行数、`reportDetail.sandboxPolicy`、`explainability`、报告路径和安全边界，再调用 `GET /api/grading/result-preview?report={file}&maxItems=6`、`GET /api/grading/evidence-readiness?report={file}` 与 `GET /api/grading/records?taskId={id}`；只有当 `taskId` 形如 `task_*` 或 `real_demo_*` 时，预览/evidence 辅助接口才携带 `taskId`，避免把提交 id 误当 AI Task id 导致非关键 404；评分记录面板只读显示 record total、最新记录状态、`approve-ready` / `needs-evidence` / `needs-revision` 人工结论、review command 和 `platformApiRequired=false`；若响应中的 `report.mode=GRADING_EVIDENCE_AUTO_REPORT`，页面会渲染 `EvidenceAutoSummary`、`EvidenceAutoExecutionMatrix`、`EvidenceAutoScorePreview`、`ReviewerSafetySummary`、`readonly_static_evidence`、可选 `controlled_command_evidence`、warning、覆盖摘要和 `manualReviewChecklist` 人工复核入口；若响应包含 `mergedGradingEvidence.visible=true`，则替换证据来源链表格和人工复核动作面板并显示 `API_READONLY_LOADED`；若该接口没有合并 evidence、请求失败或 URL 没有报告文件参数，则回退 `GET /api/review-tasks/{id}`，并可用 `reviewDetail.gradingRecords.reviewIntegration` 作为评分记录复核 fallback；接口不可用或任务暂无合并 evidence 时保持 `STATIC_HTML_FALLBACK`。页面不发送 POST、不触发命令、不运行 pytest、不启动 Notebook、不替换真实 Grading DSL、不自动通过或发布。

`ai-tasks.html?agentReport=<workflow-report-json>` 复用 Review Center 的
`realDemoReviewQueue`。摘要返回 `AGENT_REPORT_REAL_LLM_ARTIFACTS` 且本地任务列表为空
时，四类真实 DSL 产物会显示为 synthetic `WAITING_REVIEW` task cards；点击卡片会
携带 `agentReport`、`coreDbPath` 和 `gradingDbPath` 调用
`GET /api/review-tasks/{id}` 加载同一批次的只读审核详情。该路径不创建任务、不把
synthetic card 当成可批准记录，也不改变答案脱敏和自动发布阻断。

### 本地任务与评分报告回退

`ai-tasks.html` 会在 URL 指定的 `taskId` 不存在时显示 `API_READONLY_LOADED_WITH_TASK_NOT_FOUND`，并明确标出当前安全回退选中的任务，不会静默把第一条任务伪装成请求目标。对 Exam / Grading 任务，评分记录接口失败会显示“评分记录加载失败”，评分报告入口保持禁用。

`grading-report.html` 允许只传 `taskId`。页面先只读查询 `GET /api/grading/records?taskId={id}`，若最新 `GradingRecord` 带有 `reportPath`，就补齐 URL 的 `file` 参数并加载该报告、评分 evidence 与人工复核状态；无记录或加载失败才回退审核详情。该过程不执行评分、不读取密钥、不调用真实平台 API。

### 审核中心真实演示深链

`review-center.html` 的 `RealDemoReviewQueue` 保留 `/labs/:id/review`、`/exams/:id/review`、`/grading/:id/report`、`/ppt/:id/review` 原型路由，同时为本地演示补充 `entryHref`：`lab-review.html?taskId=real_demo_lab`、`exam-review.html?taskId=real_demo_exam`、`grading-report.html?file=examples/output/merged-evidence-report.json&taskId=real_demo_grading`、`ppt-review.html?taskId=real_demo_ppt`。这些链接只打开只读审核页，不发送 POST、不 approve/reject/publish、不执行沙箱、不读取密钥。

`review-center.html?agentReport=<workflow-report-json>` 已支持自定义真实输出批次产品化读取。页面会把 `GET /api/review-task-summary?agentReport=...` 返回的 Lab / Exam / Grading / PPT 四类 DSL 路径渲染到 Review Queue；点击队列项后，`GET /api/review-tasks/{id}?agentReport=...` 会优先按该 workflow report 返回只读审核详情，即使本地 Mock store 已存在同名 taskId，也会展示本批次的 DSL preview、DSL artifact link 和 Workflow Report artifact link。轻量 report 只有 `generatedDsl.*.dslPath` 而没有 `taskId` 时，页面使用 `real_demo_lab` / `real_demo_exam` / `real_demo_grading` / `real_demo_ppt` fallback 任务入口。页面首屏标识为 `LOCAL_CORE_MVP`，明确“真实 LLM 产物：只读加载”和“真实 LLM 请求：本页不发起”，避免将已加载的真实产物误标为 Mock；评分报告入口只会在 `mergedGradingEvidence.latestReportPath` 存在时启用，不能把 Lab / Exam / PPT DSL 误当作评分报告。Exam DSL preview 仍固定 `candidateSafety.answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false` 和 `answersRemovedFromSafePreview=true`。

`lab-review.html`、`exam-review.html` 和 `ppt-review.html` 引入 `review-detail-data.js` 作为渐进增强适配器。通过 `python -m backend.mock_http_server --host 127.0.0.1 --port 8000` 打开页面时，页面会读取 URL 中的 `taskId` 或 `id`，调用 `GET /api/review-tasks/{id}` 更新任务标题、状态、DSL 摘要和 Timeline；接口不可用或任务不存在时保持 `STATIC_HTML_FALLBACK` 静态内容。该适配器只发送 GET，不发送 approve/reject/publish，不执行沙箱，不读取密钥，固定展示 `autoPublishAllowed=false` 和 `realPublishAllowed=false`。

上述三类审核详情页也引入 `review-action-data.js`，用于人工点击“通过 / 驳回”时调用 `POST /api/ai-tasks/{id}/approve` 或 `POST /api/ai-tasks/{id}/reject`。页面要求填写 reviewer；驳回要求填写 reason；成功后刷新只读详情并展示 `ACTION_APPROVED_RECORDED` 或 `ACTION_REJECTED_RECORDED`。该动作只写本地 Mock store 的审核状态和审计事件，不发布、不批量变更、不执行真实沙箱、不调用真实 LLM。

`lab-review.html`、`exam-review.html` 和 `grading-review.html` 引入 `review-import-preview-data.js`，在人工审核通过后可点击生成平台导入预览：Lab 调用 `POST /api/labs/import-preview`，Exam 调用 `POST /api/exams/import-preview`，Grading 调用 `POST /api/grading/import-preview`。这些动作要求任务已 `APPROVED`，只生成本地 `LabTemplateImportPreview`、`ExamQuestionImportPreview` 或 `GradingRuleImportPreview` artifact，不写真实数据库、不调用真实平台导入、不发布；PPT 审核页不提供平台实体导入预览。预览生成后，同一面板会启用 `AgentEntityMockImportAction`，继续调用 `POST /api/labs/mock-import`、`POST /api/exams/mock-import` 或 `POST /api/grading/mock-import`，把草稿写入本地 Mock store，并生成 `platform-entities.html?entityId={id}&sourceTaskId={taskId}&entityKind={kind}` 深链，方便直接跳到平台实体页查看 readiness、dry-run 和后续人工签收。该动作固定 `mockStoreWritten=true`、`databaseWritten=false`、`realPlatformImport=false`、`realPublish=false`。

`ai-tasks.html` 在同源 Backend Mock 启动时会只读加载任务列表、待审核任务、任务详情和审核优先级摘要；默认使用 `GET /api/ai-tasks`，当 URL 带 `coreDbPath` 时切换到 `GET /api/backend/core-tasks?coreDbPath=...` 和 `GET /api/backend/core-tasks/{id}?coreDbPath=...`，用于查看 Backend Core repository-backed 任务。页面跳转到审核中心、评分报告和导入预览时会保留 `coreDbPath`、`gradingDbPath`、`agentReport`，该增强只读，不创建任务、不审核、不批量改状态、不自动发布。

`platform-entities.html` 接收 `sourceTaskId`、`entityKind`、`coreDbPath`、`gradingDbPath` 和 `agentReport` 深链参数时，会优先保持本次任务上下文。若本地列表中没有匹配 `sourceTaskId + entityKind` 的实体草稿，页面显示 `LOCAL_ENTITY_NOT_PREPARED` / `RequestedEntityPlaceholder` 占位详情并提示先准备本地 mock-import / dry-run 草稿，不再自动选中第一条历史实体；若实体列表来自 `mock-data.json` 静态 fallback，选择实体时直接渲染已有本地摘要，不再拿静态 id 探测 Backend Core 详情，避免真实演示深链出现非关键 404。此时导入动作区也会显示 `nextLocalAction=prepare_demo_draft_or_run_mock_import`，并阻止把占位实体当成可 dry-run 实体。返回审核中心链接仍指向 URL 中的本次任务并保留本地上下文。“准备演示草稿”会把同一个 `coreDbPath` 写入 import-preview、mock-import 和 import-dry-run 请求体，并把页面上的 `contractConfig` 传给 dry-run，避免 Backend Core/SQLite 演示链路写入默认 JSON store。长状态标签会在卡片内换行，避免导入预览页在 1280px 宽度下出现横向滚动。该页面仍只做本地导入预览、mock-import 和 import-dry-run，不调用真实平台发送、状态查询、平台侧签收或真实发布。

第一批页面：

```text
/console
/review-center
/dashboard
/audit
/audit/:id
/audit/incidents
/operations/launchpad
/operations/presenter
/operations/demo-script
/operations/runbook
/operations/acceptance
/operations/demo-map
/delivery
/ai-tasks
/labs
/workflows
/labs/generate
/labs/:id/review
/ppt
/ppt/:id/review
/grading
/grading/:id/review
/grading/:id/report
/exams/:id/review
```

第二批页面：

```text
/exams
/exams/:id/review
/exams/generate
/environments
/skills
/settings/providers
```

## 命令示例

```powershell
start .\frontend\console.html
start .\frontend\dashboard.html
start .\frontend\audit.html
start .\frontend\audit-detail.html
start .\frontend\audit-incidents.html
start .\frontend\operations-launchpad.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
start .\frontend\operations-runbook.html
start .\frontend\operations-acceptance.html
start .\frontend\operations-demo-map.html
start .\frontend\delivery.html
start .\frontend\review-center.html
start .\frontend\review-center.html?taskId=<taskId>&coreDbPath=examples/output/backend-core-local.sqlite3
start .\frontend\platform-entities.html
start .\frontend\ai-tasks.html
start .\frontend\ai-tasks.html?coreDbPath=examples/output/backend-core-local.sqlite3
start .\frontend\workflows.html
start .\frontend\labs.html
start .\frontend\lab-generate.html
start .\frontend\lab-review.html
start .\frontend\ppt.html
start .\frontend\ppt-generate.html
start .\frontend\ppt-review.html
start .\frontend\exams.html
start .\frontend\exam-review.html
start .\frontend\exam-generate.html
start .\frontend\grading.html
start .\frontend\grading-review.html
start .\frontend\grading-report.html
start .\frontend\environments.html
start .\frontend\skills.html
start .\frontend\provider-settings.html
python -m pytest tests/test_frontend_manifest.py
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- Phase 1 不启动真实前端项目。
- 不接入真实后端，只引用 Backend Mock API 契约。
- `audit.html` 只读展示本地 Mock 审计记录，不导出真实审计包，不读取或展示密钥。
- `audit.html` 中高风险 MCP 意图仅展示本地审核意图、`postReviewDisposition`、`get_second_confirmation_status` 只读查询记录和统一审计记录，不执行真实发布、不销毁真实环境、不满足真实二次确认、不绕过人工审核。
- `audit-detail.html` 只读展示本地 Mock 审计详情，不重试真实 Provider / MCP 调用，不读取或展示密钥。
- `audit-incidents.html` 只读展示本地 Mock 异常复盘，不自动修复、不导出真实事故报告、不重试真实调用。
- `operations-launchpad.html` 只读展示运营演示入口、验收命令和交接说明，不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型。
- `operations-presenter.html` 只读展示运营讲解台、speakerCue、验收信号和禁用动作，不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不运行真实沙箱、不执行选手代码。
- `operations-signoff.html` 只读展示签收总览、交付证据、验收门禁和安全断言，不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不运行真实沙箱、不执行选手代码。
- `operations-demo-script.html` 只读展示 12 步运营演示脚本、验收信号和禁用动作，不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型。
- `operations-runbook.html` 只读展示本地演示步骤和白名单命令，不执行命令、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不上传交付包。
- `operations-acceptance.html` 只读展示运营验收项和交付状态，不执行命令、不上传交付包、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不自动发布或真实发布。
- `operations-demo-map.html` 只读展示运营演示路径和角色视角，不执行命令、不批量状态变更、不上传交付包、不启动真实 Agent、不启用真实 Provider、不调用真实大模型。
- `console.html` 不发起网络请求，不启动真实 Agent，不启用真实 Provider，不调用真实大模型，不创建真实云资源，不自动发布或真实发布。
- `dashboard.html` 不发起网络请求，不执行自动发布，不创建真实资源，不展示密钥。
- `delivery.html` 不发起网络请求，不上传交付包，不启用真实 Provider，不调用真实大模型，不执行真实沙箱，不自动发布或真实发布。
- `review-center.html` 可只读加载由 CLI / 后端既有链路生成的真实 LLM workflow report；页面自身不读取密钥、不直接调用真实 LLM。同源 Backend Mock 启动时可调用 `POST /api/grading/evidence-auto` 生成本地评分证据报告；不执行真实审核、不自动发布、不执行高风险 MCP 意图、不确认二次因子、不销毁真实环境。
- `generation-workspace.html` 只向同源后端发送一次生成请求；前端不接收或持久化 API Key，不自动审核，不发布，四类生成任务均停在 `WAITING_REVIEW`。
- `ai-tasks.html` 仅在同源 Backend Mock 启动时发起只读 GET；默认读取 `/api/ai-tasks`，带 `coreDbPath` 时读取 `/api/backend/core-tasks`。它不启动真实 Agent，不执行审核动作，不自动发布，不执行批量状态变更。
- `labs.html` 不发起网络请求，不批量变更状态，不自动发布，不发布真实实验。
- `lab-generate.html` 默认只向同源 Backend Mock 发起 Mock 请求；用户明确选择 `real-llm` 后同源后端才可读取环境变量密钥并发送请求。前端不直接调用模型 Provider、不读取密钥、不抓取远程素材、不执行未知 Shell。
- `lab-review.html` 不发起网络请求，不执行真实审核，不批量变更状态，不发布真实实验。
- `ppt.html` 只提供本地 PPT 清单与页面导航；`ppt-generate.html` 默认向同源 Backend Mock 发起本地请求，显式 `real-llm` 时由同源后端处理环境变量密钥；不生成真实 PPT 文件、不自动发布或真实发布课件。
- `ppt-review.html` 不发起网络请求，不执行真实审核，不调用真实大模型，不生成真实 PPT 文件，不批量变更状态，不自动发布或真实发布课件。
- `exams.html` 不发起网络请求，不调用真实大模型，不展示选手端标准答案，不执行真实沙箱，不自动发布或真实发布考试。
- `exam-review.html` 不发起网络请求，不执行真实审核，不展示选手端标准答案，不执行真实沙箱，不自动发布或真实发布考试。
- `exam-generate.html` 默认向同源 Backend Mock 发起本地 API 请求；显式 `real-llm` 时由同源后端处理环境变量密钥。前端不直接调用模型 Provider、不读取密钥、不展示选手端标准答案或 `gradingRef`，不执行真实沙箱，不自动发布考试。
- `grading.html` 不发起网络请求，不执行真实沙箱，不执行选手代码，不执行未知 Shell，不真实重评或真实发布。
- `grading-review.html` 不发起网络请求，不执行真实审核，不执行真实沙箱，不执行选手代码，不执行未知 Shell，不真实重评或真实发布。
- `grading-report.html` 仅在同源 Backend Mock 启动时发起只读 GET；`GradingResultPreview` 和 `GradingEvidenceReadiness` 只读取既有评分报告，不执行真实沙箱，不执行选手代码，不执行 Grading DSL 命令，不运行 pytest，不展示标准答案或 `gradingRef` 给候选人；`mockEvidence` 仅表示 Mock 阶段未采集真实执行证据，真实证据必须来自后续 SandboxExecutor。
- `environments.html` 不发起网络请求，不创建真实云资源，不操作真实 VM / Notebook，不展示密钥。
- `skills.html` 不发起网络请求，不启动真实智能体，不调用真实大模型，不允许 Prompt 散落到业务代码，不自动发布。
- `provider-settings.html` 不发起网络请求，不启用真实 Provider，不调用真实大模型，不读取或展示 API Key。
- `workflows.html` 不发起网络请求，不运行 Workflow，不创建 AI Task，不写 Artifact，不启动真实 MCP Server，不启动真实 Agent，不调用真实大模型，不自动发布或真实发布。
- 不展示密钥。
- `/settings/providers` 只展示 Mock Provider 和禁用的真实 Provider 占位，不展示任何 API Key。
- `WorkflowLogViewer` 只展示本地 Workflow Run Mock 日志，不代表真实智能体编排。
- `/labs/:id/review` 只展示聚合审核详情，不自动发布。
- 不展示选手端标准答案。
- 不允许自动发布。
- 不允许批量 approve / reject / publish。
- 环境页面只展示 Mock 资源，不创建真实 VM / Notebook。
- 评分报告只读展示已有本地 evidence；静态 fallback 仍会标记 `sandboxExecuted=false`。
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
