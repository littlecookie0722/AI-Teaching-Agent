# 05_API_SPEC

详见 `AI_PLATFORM_CODEX_FULL_GUIDE.md` 第 10 章。

> 当前边界：没有真实实训平台后端接口。`/api/agent-entities/{id}/import-send`、`/api/agent-entities/{id}/import-status` 和真实平台 draft import 相关 API 仅作为未来对接团队的技术参考，当前默认不执行、不要求平台 API base URL 或 `AGENT_API_TOKEN`。本地闭环停止在 import-preview、mock-import、import-dry-run DTO、受控评分 evidence 和人工审核记录。

## Phase 1 Backend API Mock

当前实现位于 `backend/mock_api.py`，只提供本地请求处理函数，不启动真实 HTTP 服务。

支持：

```text
GET /api/health
GET /api/backend/core-readiness
GET /api/backend/core-db/summary
GET /api/ai-tasks
GET /api/ai-tasks/{id}
GET /api/review-tasks
GET /api/review-task-summary
GET /api/review-tasks/{id}
GET /api/review-tasks/{id}/core-readiness
GET /api/review-tasks/{id}/ppt-page-review-status
POST /api/review-tasks/{id}/ppt-page-review-status
GET /api/review-tasks/{id}/second-confirmation-status
GET /api/review-audit-events
GET /api/audit-events
GET /api/providers
GET /api/providers/mock/health
GET /api/provider-audit-events
GET /api/mcp-tool-call-records
GET /api/agent-entities
GET /api/agent-entities/readiness-report
GET /api/agent-entities/{id}
POST /api/agent-entities/{id}/import-dry-run
# 以下真实平台对接相关 API 当前暂停，仅作为未来团队技术参考：
# POST /api/agent-entities/{id}/import-send
# POST /api/agent-entities/{id}/import-status
# POST /api/agent-entities/{id}/import-result
# POST /api/agent-entities/{id}/signoff
# POST /api/agent-entities/{id}/final-publish-review-decision
GET /api/artifacts
GET /api/artifacts/{id}
GET /api/workflow-runs
GET /api/workflow-runs/{id}
GET /api/environments
GET /api/environments/{id}
GET /api/workflow/report?file=examples/output/demo-report.json
GET /api/grading/report?file=examples/output/grading-report.json
GET /api/grading/report?file=examples/output/grading-report.json&taskId=task_grading_demo
GET /api/grading/result-preview?report=examples/output/grading-evidence-auto.json
GET /api/grading/evidence-readiness?report=examples/output/grading-evidence-auto.json
POST /api/materials/analyze
POST /api/backend/core-db/init
POST /api/backend/core-db/sync-local
POST /api/workflow/demo
POST /api/labs/generate
POST /api/labs/import-preview
POST /api/labs/mock-import
POST /api/exams/generate-from-lab
POST /api/exams/import-preview
POST /api/exams/mock-import
POST /api/ppt/generate
POST /api/grading/run
POST /api/grading/readonly-evidence
POST /api/grading/controlled-evidence
POST /api/grading/evidence-merge
POST /api/grading/evidence-auto
GET /api/grading/jobs
POST /api/grading/jobs
GET /api/grading/jobs/{id}
POST /api/grading/jobs/{id}/run
POST /api/grading/jobs/run
GET /api/grading/records
POST /api/grading/records
GET /api/grading/records/{id}
POST /api/grading/records/{id}/review
POST /api/grading/import-preview
POST /api/grading/mock-import
POST /api/providers/mock/generate
POST /api/ai-tasks/{id}/approve
POST /api/ai-tasks/{id}/reject
POST /api/environments/vm
POST /api/environments/notebook
POST /api/environments/{id}/start
POST /api/environments/{id}/stop
POST /api/environments/{id}/reset
```

统一返回：

```json
{
  "success": true,
  "code": "OK",
  "message": "查询成功",
  "data": {},
  "traceId": "trace_xxx"
}
```

限制：

- 仅 Phase 1 Mock。
- 不启动 Web Server。
- 不连接真实数据库。
- 不提供真实资源创建、发布或销毁接口。
- `LAB_BACKEND_API_TOKEN` 是真实后端 API MVP 的最小 Bearer token 鉴权边界。未配置时保持本地演示默认开放；配置后除 `GET /api/health` 外，所有 `/api/*` 请求都必须提供 `Authorization: Bearer <token>`，否则统一返回 JSON 错误 `AUTH_REQUIRED` / `AUTH_INVALID`，HTTP 包装器映射为 401；响应和审计不回显 token。该能力是最小鉴权入口，不代表完整用户、角色或权限系统。
- `backend/app.py` 提供框架无关的 `BackendApiApp`、`BackendAppResponse` 和统一 HTTP 状态映射，把 `/api/*` 请求转发、静态文件读取、JSON 错误响应和状态码映射从标准库 HTTP handler 中抽出。后续接 FastAPI / ASGI / 真实后端框架时，应以 `BackendApiApp.handle()` 为迁移边界，不继续在 `backend/mock_http_server.py` 里追加路由或业务逻辑。
- `backend/asgi_app.py` 提供无第三方依赖的 `backend.asgi_app:app` ASGI 入口，支持 lifespan、GET/POST、header 透传、JSON object body 校验和统一响应发送，内部复用 `BackendApiApp.handle()`。该入口用于真实后端框架迁移和可选 ASGI server 挂载；当前不强制安装 `uvicorn` / `fastapi`，也不代表生产部署完成。
- `GET /api/backend/core-readiness` 只读返回 `data.backendCoreReadiness`，汇总 AI Task、Artifact、Review、Platform Entity Import、Grading Job、Grading Record、Grading Worker 和 Audit 八类核心 API 的本地 contract / staging 数据、生产化缺口和迁移边界。可选 `taskId` 按任务过滤核心数据，可选 `dbPath` 只读查看本地 SQLite staging 摘要；该接口不创建 SQLite 文件、不初始化 schema、不启动 worker、不执行沙箱、不读取密钥、不访问网络、不写生产数据库、不发布，固定 `summary.nextStage=REAL_BACKEND_API_MVP`。
- `POST /api/backend/core-db/init` 与 `POST /api/backend/core-db/sync-local` 是真实后端 API MVP 的本地 SQLite 持久化起点，显式 `coreDbPath` 时初始化 / 同步 `ai_tasks`、`artifacts`、`review_audit_events`、`operation_audit_events`、`platform_entities` 五张核心表，保留原始 JSON 以支持迁移 round-trip；`GET /api/backend/core-db/summary` 只读查看计数、状态分布和平台实体类型分布，若文件不存在不会创建 SQLite。同步后，`GET /api/ai-tasks`、`GET /api/ai-tasks/{id}`、`GET /api/artifacts`、`GET /api/artifacts/{id}`、`GET /api/review-audit-events`、`GET /api/audit-events`、`GET /api/agent-entities`、`GET /api/agent-entities/{id}` 可追加 `coreDbPath` 从 Backend Core SQLite staging 只读查询，并返回 `mode=LOCAL_SQLITE_BACKEND_CORE_READONLY`；未传 `coreDbPath` 时仍读 JSON store。该能力只写开发机本地 SQLite staging，固定 `productionDatabaseWritten=false`、`productionQueueUsed=false`、`autoApproveAllowed=false`、`realPublish=false`。
- `POST /api/labs/generate`、`POST /api/exams/generate-from-lab`、`POST /api/ppt/generate` 和 `POST /api/ai-tasks/{id}/approve|reject` 可在请求体显式传入 `coreDbPath`，将新任务、产物、审核审计和操作审计写穿到 Backend Core SQLite staging；响应返回 `data.backendCoreWriteThrough`，标记 `mode=LOCAL_SQLITE_BACKEND_CORE_WRITE_THROUGH`、`localSqliteWritten`、`taskWritten`、`artifactsWritten`、`reviewAuditEventWritten`、`operationAuditEventWritten`。未传 `coreDbPath` 时仍只写 JSON store；写穿只用于真实后端 repository 写路径验证，不代表生产数据库入库。
- `backend/core_contract.py` 定义 Backend Core repository contract、config、factory 和当前 SQLite adapter；`backend/core_service.py` 依赖 factory + contract，集中处理 `coreDbPath` 解析、SQLite staging 语义化只读查询、摘要和写穿，`backend/mock_api.py` 不直接拼接 Backend Core 表名。`BackendCoreRepositoryFactory` 已提供 adapter registry，默认注册 `sqlite-local`；`LAB_BACKEND_CORE_DATABASE_URL` 能识别 `sqlite`、`postgresql` / `postgres`、`mysql` / `mariadb`，并对外部数据库 URL 只返回 scheme、hostPresent、usernamePresent、passwordPresent 等脱敏摘要，不回显 host、账号、密码或完整 URL。未注册真实 adapter 时返回 `BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE`，不会尝试连接真实数据库。`backend/core_postgres_repository.py` 和 `backend/core_mysql_repository.py` 已分别提供 PostgreSQL / MySQL repository adapter 最小真实 driver 边界，支持 lazy driver import、可注入 connector、schema 初始化、AI Task / Artifact / Review Audit / Operation Audit / Platform Entity round-trip、summary 统计和密钥脱敏错误；默认 HTTP mock 不自动注册外部 adapter，测试或部署环境需显式注册后才会连接外部数据库。后续真实数据库适配应优先注册 repository adapter 并配置测试库，避免继续在路由中追加同义持久化 helper。
- `backend/core_task_service.py` 是 Backend Core 任务服务化入口，直接基于 `BackendCoreRepositoryContract` 创建 `WAITING_REVIEW` AI Task、Artifact、Review Audit 和 Operation Audit，并执行人工 approve / reject 状态流转校验。`POST /api/backend/core-tasks` 创建 repository-backed 待审核任务，请求体需要 `taskType`、`title`、`inputType`、`inputRef`、`actor`，可选 `coreDbPath`、`finalResultPath` 和 `artifacts`；`GET /api/backend/core-tasks?coreDbPath=...` 与 `GET /api/backend/core-tasks/{id}?coreDbPath=...` 直接从 Backend Core repository 只读查询任务，列表支持 `status` 和 `taskType` 过滤；`POST /api/backend/core-tasks/{id}/approve|reject|review` 执行人工审核，`review` 形式从请求体读取 `decision`。响应返回 `data.backendCoreTaskService`，固定 `repositoryContractUsed=true`、`jsonStoreWritten=false` 或 `jsonStoreRead=false`、`autoApproveAllowed=false`、`realPublish=false`。它不会写 JSON store、不自动审核、不发布；真实后端路由后续应继续调用该服务，而不是在 router 中直接操作任务模型或本地 store。
- `LAB_BACKEND_CORE_DATABASE_URL` 是 Backend Core 数据库 URL 默认入口；当前 `sqlite:///...` 会解析为本地开发 staging 路径，例如 `sqlite:///./examples/output/backend-core-local.sqlite3`。未传 `coreDbPath` 时，Core DB summary/init/sync、核心只读查询和写穿动作会使用该本地 SQLite staging 路径；显式 `coreDbPath` 仍然优先。`postgresql://...` / `postgres://...` / `mysql://...` / `mariadb://...` 会解析为外部数据库 adapter 配置，但默认未注册真实 adapter，因此只返回 `BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE`，不连接外部库；注册 PostgreSQL adapter 后真实运行需要 `psycopg[binary]`，注册 MySQL adapter 后真实运行需要 `mysql-connector-python`，都必须指向测试 / staging 数据库 URL。错误信息和 policy 只包含脱敏摘要、driver 缺失或异常类型，不回显完整 URL。
- `python lab_cli.py backend-core postgresql plan|init|summary|smoke` 是 PostgreSQL 测试库迁移和实跑证据入口。`plan` 只返回脱敏计划、driver 安装状态和 schema 表清单，不访问网络、不写 schema；`init --confirm-test-database` 显式注册 PostgreSQL adapter 并初始化测试 / staging schema；`summary` 读取真实仓储摘要；`smoke --confirm-test-database` 会写入一条待审核任务、Artifact、操作审计并执行人工 approve round-trip，用于测试库 / CI 证据。该入口需要 `LAB_BACKEND_CORE_DATABASE_URL` 或自定义 `--database-url-env`，命令响应不回显完整连接串、账号、密码或 token，且仍不自动发布、不连接生产队列。
- `python lab_cli.py backend-core mysql plan|init|summary|smoke` 是 MySQL 测试库迁移和实跑证据入口。它与 PostgreSQL 入口一致：`plan` 只做 URL/driver/schema 计划和脱敏摘要，`init` 必须显式 `--confirm-test-database`，`summary` 只读仓储摘要，`smoke` 写入一条测试任务并完成人工 approve round-trip。该入口需要 `mysql://...` 或 `mariadb://...` 测试 / staging URL 和 `mysql-connector-python`，默认 HTTP mock 不自动注册 MySQL adapter。
- `POST /api/materials/analyze` 请求体需要 `input`，只对本地 Markdown / 文本 / Shell 素材做静态摘要和风险标记，固定 `realLlmCalled=false`、`remoteContentFetched=false`、`unknownShellExecuted=false`、`sandboxExecuted=false`。
- `POST /api/workflow/demo` 请求体需要 `input` 和 `reviewer`，先做本地素材分析，再串联本地 Lab/Exam/Grading/PPT DSL 示例、创建 `WAITING_REVIEW` AI Task、返回 Mock 评分报告；`sandboxExecuted=false`，不执行选手代码。
- `POST /api/labs/generate` 请求体需要 `input`，先做本地素材分析，再生成任务专属 `examples/output/<task_id>-lab.json` Lab DSL，同时创建 `WAITING_REVIEW` AI Task。响应包含 `labFeatureReadiness`，用于证明第一个主功能稳定 v1：Schema 已校验、DSL 指向本次输入素材、学习目标和实验步骤达到最小教学质量、人工审核前禁止发布；下一步只允许人工审核后进入本地 `LabTemplateImportPreview` / mock-import，不调用真实平台。
- `POST /api/labs/import-preview` 请求体需要 `taskId` 和 `reviewer`，任务必须已 `APPROVED` 且关联 `LAB_DSL` Artifact。接口重新校验 Lab Schema 后返回 `data.labTemplateImportPreview`、`artifact` 和 `operationAuditEvent`，用于平台 `lab_template` 草稿导入前人工复核；固定 `databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`。
- `POST /api/labs/mock-import` 请求体需要 `taskId` 和 `reviewer`，任务必须已 `APPROVED` 且已有 `LabTemplateImportPreview`。接口把预览中的 `labTemplateDraft` 写入本地 Mock store 的 `platformEntities`，返回 `data.agentEntityMockImport`、`agentEntityRecord`、`artifact` 和 `operationAuditEvent`；固定 `mockStoreWritten=true`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。
- `POST /api/exams/generate-from-lab` 请求体需要 `labId`，只返回本地 Exam DSL 和 Grading DSL 示例，同时创建 `WAITING_REVIEW` AI Task；标准答案不得展示给选手端。
- `POST /api/exams/import-preview` 请求体需要 `taskId` 和 `reviewer`，任务必须已 `APPROVED` 且关联 `EXAM_DSL` Artifact。接口返回 `data.examQuestionImportPreview`、`artifact` 和 `operationAuditEvent`，用于平台 `exam_question` 草稿导入前人工复核；固定 `answerVisibleToCandidate=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`。
- `POST /api/grading/import-preview` 请求体需要 `taskId` 和 `reviewer`，任务必须已 `APPROVED` 且关联 `GRADING_DSL` Artifact。接口返回 `data.gradingRuleImportPreview`、`artifact` 和 `operationAuditEvent`，用于平台 `grading_rule` 草稿导入前人工复核；固定 `sandboxRequiredBeforeRealExecution=true`、`databaseWritten=false`、`realAgentImport=false`、`realPublishAllowed=false`，不执行评分沙箱。
- `POST /api/exams/mock-import` 与 `POST /api/grading/mock-import` 分别要求已有 `ExamQuestionImportPreview` / `GradingRuleImportPreview`，把 `examQuestionDraft` / `gradingRuleDraft` 写入本地 `platformEntities`；标准答案仍保持教师侧语义，评分规则仍不执行沙箱，固定 `databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。
- `POST /api/phase2/workflows/content-generation/run` 请求体需要 `input` 和 `reviewer`，默认通过 MockProvider 生成 Lab / Exam / Grading / PPT DSL 审核包。可选 `providerMode=real-llm`、`model`、`baseUrl`、`maxOutputTokens`、四类 `realLlm*Output` 路径以及 `explicitRealCallOptIn=true`、`confirmRealDsl=true`、`confirmWaitingReview=true`、`confirmNoAutoPublish=true`，发起真实 OpenAI-compatible LLM 内容生成；`repairOnSchemaFailure=true` 只在某一类 DSL Schema 校验失败时最多追加一次修复请求。所有生成结果仍为 `WAITING_REVIEW`，不自动发布、不执行沙箱、不生成真实 PPTX。
- `POST /api/phase2/workflows/grading-generation/run` 请求体需要 `exam` 和 `reviewer`，读取本地 Exam DSL，通过 MockProvider 生成 Grading DSL 审核包，同时创建 `WAITING_REVIEW` AI Task、Artifact、WorkflowRun 和 Provider 审计；不执行真实沙箱或选手代码。
- `POST /api/ppt/generate` 请求体需要 `input`，只返回本地 PPT DSL 示例，同时创建 `WAITING_REVIEW` AI Task，`artifactGenerated=false`。
- `POST /api/grading/run` 请求体需要 `grading`，只读取本地 Grading DSL 并生成 Mock 报告，`sandboxExecuted=false`，不执行选手代码。
- `POST /api/grading/readonly-evidence` 请求体需要 `grading` 和 `submission`，在只读模式下收集文件/JSON/日志/Notebook 静态证据，不执行选手命令、不启动 Docker。
- `POST /api/grading/controlled-evidence` 请求体需要 `grading` 和 `submission`，只针对受控命令型 check 生成 Docker 沙箱 evidence；该接口仍固定不开放网络、不发布，宿主机不直接执行选手代码。响应中的 report、operationAuditEvent.detail、artifact.metadata 和 reportDetail 会包含 `imageSupplyChain`，记录本地 `docker image inspect` 的 imageId/digest、allowlist 匹配、禁止自动 pull、未使用 registry auth 和未访问生产 registry；同时包含 `isolationQuality`，汇总网络关闭、只读挂载、只读 rootfs、资源限制、输出捕获、本地镜像检查和 registry 网络未使用等本地质量信号。当前为本地 PoC 审计摘要，不等同生产镜像签名强校验或生产隔离认证。
- `POST /api/grading/evidence-merge` 请求体需要 `reports` 和 `output`，只合并已有本地 JSON evidence 报告并写出 `GRADING_EVIDENCE_MERGE_REPORT`、操作审计和 `GRADING_REPORT` Artifact；可选 `taskId` 会把合并报告归属到审核任务。
- `POST /api/grading/evidence-auto` 请求体需要 `grading`、`submission` 和 `output`，编排已有只读 evidence、可选受控 Docker evidence 和 evidence merge，写出 `GRADING_EVIDENCE_AUTO_REPORT`。默认 `includeControlledCommand=false`，只读证据总是先运行；`includeControlledCommand=true` 时才尝试受控 Docker，Docker 不可用默认降级为 warning，`failOnControlledUnavailable=true` 才返回失败。响应包含 `executionMatrix`、`nextCoreAction` 和 `manualReviewChecklist`，分别用于展示 check 级证据覆盖/缺口、下一步应重跑受控 evidence / 修复静态证据 / 准备 Docker runtime / 记录人工审核结论，以及面向审核员的 check 级复核动作和 `decisionNoteRecommendation`。该接口不调用真实 LLM、不自动审核、不发布。
- `POST /api/grading/jobs` 请求体需要 `grading`、`submission`、`output` 和 `submissionId`，可选 `taskId`、`candidateId`、`reviewer`、`includeControlledCommand`、`failOnControlledUnavailable`、`image`、`dbPath`。接口创建本地 `QUEUED` `GradingJob`；`POST /api/grading/jobs/{id}/run` 或 `POST /api/grading/jobs/run` 同步执行本地 job，复用 `evidence-auto` 生成报告并派生 `GradingRecord`，job 最终进入 `WAITING_REVIEW`。`backend/grading_job_service.py` 是该能力的服务层入口，负责创建、同步运行、JSON/SQLite staging 写入、报告 Artifact 和 `GRADING_JOB_CREATE` / `GRADING_JOB_RUN` 操作审计；HTTP 路由只做 payload 与统一 JSON response 适配。默认写本地 JSON store；设置 `LAB_BACKEND_GRADING_DB_PATH`、HTTP server `--grading-db` 或显式 `dbPath` 时，创建、查询、列表和运行都读写本地 SQLite，并把执行后的 job / record 镜像回 JSON store。显式 `dbPath` 优先于后端默认路径，响应返回 `dbPathSource`。SQLite 执行请求可选 `leaseSeconds` 和 `maxAttempts`，非法值返回 `VALIDATION_ERROR`。`POST /api/grading/workers/drain-once` 请求体可选 `dbPath`、`actor`、`limit`、`leaseSeconds`、`maxAttempts`，会按 `limit` 顺序执行有限批次，默认 5、最大 20，队列为空或单个 job 失败即停止；返回 `workerDrain`、`workerRuns`、SQLite `summary`、批次级 `operationAuditEvent` 和安全标记。`workerDrain.quota` 标记本次是否触顶和是否可能仍有可运行任务；`workerDrain.resourceCleanup` 标记本地报告和评分记录保留情况。当前它只是未来真实评分队列 / 数据库入库的 staging 替身，固定 `databaseWritten=false`、`productionDatabaseWritten=false`、`queuePersistedToProduction=false`、`persistentBackgroundWorker=false`、`autoApproveAllowed=false`、`realPublish=false`。
- `POST /api/grading/records` 请求体需要 `report` 和 `submissionId`，可选 `candidateId`、`taskId`、`reviewer`、`dbPath`。接口只从已有评分报告派生本地 `GradingRecord`，保存得分、覆盖率、evidence 摘要和人工复核状态；不重新评分、不启动 Docker、不执行选手代码、不改变 AI Task 状态、不自动通过、不发布。`backend/grading_record_service.py` 是该能力的服务层入口，负责创建、人工复核、JSON/SQLite staging 写入和 `GRADING_RECORD_CREATE` / `GRADING_RECORD_REVIEW` 操作审计；HTTP 路由只做 payload 与统一 JSON response 适配。`GET /api/grading/records` 可按 `submissionId`、`candidateId`、`taskId`、`status` 查询；`GET /api/grading/records/{id}` 查询单条记录；`POST /api/grading/records/{id}/review` 请求体需要 `reviewer` 和 `decision`，可选 `dbPath`，`decision` 支持 `approve-ready`、`needs-evidence`、`needs-revision`，后两者必须提供 `reason`。复核只更新本地 `GradingRecord` 和操作审计，不改变 AI Task 状态、不重新执行沙箱、不发布。默认写本地 JSON store；设置 `LAB_BACKEND_GRADING_DB_PATH`、HTTP server `--grading-db` 或显式 `dbPath` 时，创建和复核会写入本地 SQLite，并镜像回 JSON store 供审核详情聚合；列表和详情查询也会在同样条件下直接读取本地 SQLite，因此后端重启或 JSON store 不完整时仍可通过 `dbPath` 查询已入库的评分记录。`GET /api/review-tasks/{id}` 会在 `gradingRecords.reviewIntegration` 中汇总单条记录是否已人工复核为 `approve-ready`。
- `backend.grading_repository.GradingSQLiteRepository` 是评分 job / record 的本地 SQLite 持久化草案，当前通过 CLI `grade db-init`、`grade db-sync-local`、`grade db-summary`、`grade worker-run-once`、`grade worker-drain-once` 验证 schema 初始化、JSON store 同步、状态摘要、单次 worker 和有限批次 worker；`grade job-create/job-run/job-list/job-get --db-path` 与 HTTP mock API 中 `LAB_BACKEND_GRADING_DB_PATH` / `--grading-db` / 显式 `dbPath` 的 `/api/grading/jobs` 也可直接读写该 SQLite 文件。`workers/run-once` 会先回收过期 `RUNNING` claim：未达 `maxAttempts` 的任务回到 `QUEUED`，达到上限的任务转为 `FAILED` 并写入 `GRADING_JOB_RETRY_LIMIT_EXCEEDED`；随后用 `claimOwner`、`claimedAt`、`claimExpiresAt`、`attemptCount` 领取一个 `QUEUED` / `FAILED` job 并标记为 `RUNNING`，再同步执行一次，并把 job / record 镜像回 JSON store 供审核详情读取。`workers/drain-once` 只是在单次 worker 上增加有限循环、quota 摘要、资源保留计划和批次审计，不启动常驻 worker、不启动并发 worker。该仓储只写本地 SQLite 文件，不连接生产数据库，不启动真实队列或常驻 worker，固定 `localSqliteOnly=true`、`claimLeaseEnabled=true`、`expiredClaimRecoveryEnabled=true`、`singleProcessSequentialDrain=true`、`quotaEnforced=true`、`resourceCleanupPlanned=true`、`persistentBackgroundWorker=false`、`productionDatabaseWritten=false`、`productionQueueUsed=false`、`autoApproveAllowed=false`、`realPublish=false`。
- `GET /api/grading/result-preview` 请求参数需要 `report`，可选 `taskId`、`candidateId`、`maxItems`；只读取已有本地评分报告和 Artifact metadata，返回候选人安全的 `data.gradingResultPreview`，不重新评分、不启动 Docker、不执行选手代码、不调用真实 LLM、不自动审核、不发布。
- `GET /api/grading/evidence-readiness` 请求参数需要至少一个 `report`，可重复传入多份 report；可选 `taskId`。接口只读取已有 evidence 报告，返回 `data.gradingEvidenceReadiness`，包含 check 级 evidence 就绪状态、缺口、下一步只读/受控 evidence 或人工复核建议；不写 Artifact、不启动 Docker、不执行 pytest、不启动 Notebook、不执行选手代码、不自动审核、不发布。
- `/api/review-tasks` 只读本地 Mock 审核队列，默认返回 `WAITING_REVIEW`。
- `/api/review-task-summary` 只读本地 Mock 审核队列摘要，可按 `status`、`taskType`、`limit` 查询；返回 `reviewPriorityQueue` 和 `realDemoReviewQueue`，后者展示真实演示 Lab / Exam / Grading / PPT 四个 `WAITING_REVIEW` 产物、只读 evidence 摘要和 PPT 页级审核入口；批量 approve/reject/publish 固定禁用。
- `/api/review-tasks/{id}` 只读本地 Mock 审核详情，聚合 AI Task、Artifact、Workflow Step、审核审计、统一操作审计、发布阻断策略和 `reviewPage` 页面模型；包含 Lab / Exam / Grading DSL 的任务会在顶层和 `reviewPage.platformImportPreviewActions` 返回 `AgentImportPreviewActionPanel`，列出导入预览 CLI、Backend API、MCP Tool 入口，并按任务是否 `APPROVED` 标记启用状态；任务已生成 Lab / Exam / Grading 平台导入预览时，顶层和 `reviewPage.platformImportPreview` 会返回 `AgentImportPreviewSummary`，展示平台实体草稿、源 DSL、导入计划和不写库/不发布边界；顶层和 `reviewPage.platformImportPreviewSignoff` 会返回 `AgentImportPreviewSignoffChecklist`，展示人工签收检查项、缺失预览入口和 `readyForHumanSignoff` 状态，但不执行真实导入、不写库、不发布；高风险 MCP 意图会额外返回 `highRiskIntent.postReviewDisposition`、`reviewPolicy.postReviewDispositionState` 和 `reviewPage.highRiskIntentPanel`，固定 `autoPublishAllowed=false`、`realPublish=false`、`environmentDestroyed=false`；PPTX Artifact 审核任务会额外返回 `pptPageReview`，包含逐页审核状态、人工批注和 QA 信号摘要。
- `/api/review-tasks/{id}/core-readiness` 只读返回 `data.coreWorkflowReadinessReport`，聚合审核状态、内容质量摘要、平台实体 readiness、`platformImportPreviewActions` 和 Grading `preApproveReviewCheck`，用于判断单个任务离本地核心演示闭环还缺哪一步。Lab、Exam、Grading、PPT 会按任务类型只统计其实际派生的实体，避免 Exam 任务被无关的 Lab/PPT 草稿阻塞；传入 `coreDbPath` 时，平台实体 preview、mock-import 与 dry-run evidence 从同一 Backend Core SQLite staging 只读聚合。默认停止线为 `import-preview -> mock-import -> import-dry-run`：三步完成后返回 `recommendedNextAction=LOCAL_CORE_MVP_STOP_LINE_REACHED`，不建议真实平台发送、状态查询、签收或发布。该接口不执行导入、不发送请求、不启动沙箱、不自动 approve、不发布。
- `/api/review-tasks/{id}/ppt-page-review-status` 只读返回 PPT / PPTX 审核任务的页级审核状态模型；非 PPT 审核任务返回 `VALIDATION_ERROR`，该接口不写审核决定、不自动通过、不发布真实课件。
- `POST /api/review-tasks/{id}/ppt-page-review-status` 请求体需要 `slideIndex`、`reviewStatus`、`reviewer` 和可选 `comment`，只更新本地 `PPTX_FILE` Artifact metadata 中的单页审核状态，并写入 `PPT_PAGE_REVIEW_UPDATE` 操作审计；`REVISE_REQUIRED` 必须填写 `comment`，该接口不改变 AI Task 总状态、不自动通过、不发布真实课件。
- `/api/review-tasks/{id}/second-confirmation-status` 只读本地高风险 MCP 二次确认 Mock 状态；仅 `destroy_environment` 这类 `secondConfirmationRequired=true` 的意图返回成功，且固定 `secondConfirmationSatisfied=false`、`confirmationActionAvailable=false`、`destroyRealEnvironmentEnabled=false`，不提供确认执行或真实销毁入口。
- `/api/review-audit-events` 只读审核审计事件，可按 `taskId`、`action`、`actor` 过滤；`backend/audit_query_service.py` 负责过滤校验和 JSON/Core SQLite 只读分支，传 `coreDbPath` 时返回 `mode=LOCAL_SQLITE_BACKEND_CORE_READONLY`，否则返回 `mode=MOCK_ONLY`。
- `/api/audit-events` 只读统一操作审计事件，可按 `resourceType`、`resourceId`、`action`、`actor` 过滤；同样由 `backend/audit_query_service.py` 承接，传 `coreDbPath` 时读 Backend Core 本地 SQLite staging，否则读 JSON store。
- `/api/artifacts` 只读本地 Mock 产物清单，可按 `kind`、`taskId`、`workflowRunId`、`traceId` 过滤。
- `/api/artifacts/{id}` 只读单条本地 Mock 产物记录，记录素材分析、DSL 输出、Mock 报告的路径和安全标记。
- `/api/providers` 只读 Phase 1 Provider 契约，只有 `mock` Provider 启用。
- `/api/providers/mock/health` 只返回 MockProvider 状态，不访问真实 Provider。
- `POST /api/providers/mock/generate` 请求体需要 `promptId`，可选 `outputKind`、`inputRef`，只返回本地 DSL 示例引用和 `WAITING_REVIEW` 状态。
- `/api/provider-audit-events` 只读本地 Provider 调用审计，可按 `providerId`、`operation`、`status`、`promptId`、`traceId`、`actor` 过滤；由 `backend/audit_query_service.py` 统一校验 `status` 并读取 JSON store，不访问真实 Provider。
- `/api/mcp-tool-call-records` 只读本地 MCP Tool 调用记录，可按 `toolName`、`status`、`traceId`、`actor`、`backendPath` 过滤；成功、参数失败和 Backend Mock 失败均保持 `MOCK_ONLY`，参数预览必须脱敏。
- `/api/agent-entities` 只读本地 Mock 平台实体草稿，可按 `entityType`、`sourceTaskId`、`traceId` 过滤；`/api/agent-entities/{id}` 查询单条实体，并返回 `agentEntityImportActivity` 只读摘要，用于查看本地 import dry-run Artifact 与操作审计状态。`/api/agent-entities/readiness-report` 只读汇总 `lab_template`、`exam_question`、`grading_rule` 是否已生成导入预览、是否已 Mock 入库、是否已有本地 dry-run DTO，并可按 `sourceTaskId` 过滤；其中 `grading_rule` item 会额外返回 `gradingRecordReviewEvidence`，显示同源任务最新 `GradingRecord` 是否已人工复核为 `HUMAN_APPROVED + approve-ready`，并在汇总中返回 `gradingRecordReviewApplicableTotal`、`gradingRecordReviewReadyTotal` 和 `gradingRecordReviewBlockedTotal`。该 evidence 只作为本地评分记录复核证据，不改变原有导入预览 ready 语义、不自动签收、不发布。带 `coreDbPath` 时，readiness 会从 Backend Core 读取 `platform_entities`、Artifacts 与操作审计；如果同时传入 `gradingDbPath`，会额外只读本地 Grading SQLite 的 `grading_records`，并在 `backendCoreAgentEntityReadiness.gradingRecordSource` 中标记 `LOCAL_SQLITE_GRADING_RECORD_READINESS_BRIDGE`、`dbPath` 与 `recordTotal`。`coreDbPath` 与 `gradingDbPath` 分别代表两套本地 staging，不会混用。`backend/agent_entity_service.py` 当前本地闭环只要求只读查询、实体类型校验、activity/readiness 聚合和 `import-dry-run`；`import-send` / `import-status` / `import-result` / `signoff` / `final-publish-review-decision` 仅保留为未来真实平台对接技术参考。readiness 报告和活动摘要均固定不回显密钥、不发送平台请求、不真实发布。
- `POST /api/agent-entities/contract-validate` 请求体需要 `contractConfig`，可选 `entityType`，只读取本地平台 API 契约 JSON 并返回 `data.platformApiContractValidation`、`mode=LOCAL_PLATFORM_API_CONTRACT_VALIDATION` 和安全标记；它校验 draft import endpoint、状态字段别名、状态映射和 `requestBodyMapping` 结构，固定 `requestSent=false`、`networkAccess=false`、`secretsRead=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。该接口供前端或后端挂载前离线检查真实平台字段配置，不读取 token、不发送请求、不写库。
- `POST /api/agent-entities/{id}/import-dry-run` 请求体需要 `reviewer`，可选 `output`、`contractConfig`、`coreDbPath`，只把本地 `platformEntities` 记录转换成未来真实平台导入 DTO、目标 endpoint、`platformApiContract` 和 `contractValidation` 预览，返回 `data.agentEntityImportDryRun`、`artifact` 和 `operationAuditEvent`。传入 `coreDbPath` 时，该接口会从 Backend Core repository 读取 `platform_entities` 中的实体记录，并把 dry-run Artifact 与 `PLATFORM_ENTITY_IMPORT_DRY_RUN` 操作审计写回同一 repository，响应补充 `data.backendCoreAgentEntityImportDryRun`，标记 `repositoryContractUsed=true`、`jsonStoreSourceRead=false`、`artifactWritten`、`operationAuditEventWritten` 和 `localSqliteWritten`；未传 `coreDbPath` 时仍读写 JSON store。该接口固定 `dryRunOnly=true`、`requestSent=false`、`networkAccess=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不会调用真实平台 API；业务逻辑由 `BackendAgentEntityService.build_import_dry_run` / `build_import_dry_run_from_repository` 承接，平台 endpoint、状态查询路径模板、draft id/status 响应字段别名、建议登记状态和本地契约配置校验由 `cli/platform_api_contract.py` 集中维护。`contractConfig` 是本地 JSON 文件路径，可覆盖 `entities.<entityType>.draftImportPath`、`statusPathTemplate`、`draftIdResponseKeys`、`statusResponseKeys` 和 `statusMapping`，用于适配测试平台字段差异；`contractValidation` 会列出每类实体的 endpoint、request body 来源、字段映射统计、未知顶层字段 warning 和安全标记，不读取密钥、不发送请求。
- `POST /api/agent-entities/{id}/import-send` 和 `POST /api/agent-entities/{id}/import-status` 当前不属于本地闭环默认 API。既有实现和契约说明仅保留给未来真实平台对接团队参考；在没有真实平台后端接口、平台 API base URL、`AGENT_API_TOKEN` 和平台状态定义前，不要求运行、不作为 readiness 阻塞项，也不作为下一步开发目标。
- 仓库内提供本地 staging 示例 `examples/input/platform-contract.json`，覆盖 `lab_template`、`exam_question`、`grading_rule`、`ppt_deck` 四类实体的 draft import endpoint、状态查询路径和 `requestBodyMapping`。该文件仅用于本地契约校验、dry-run 和字段映射回归，不代表真实平台正式 API 字段；后续其他团队拿到真实平台 API 文档后，再替换其中 endpoint 与字段映射。
- `contractConfig` 最小结构示例：

```json
{
  "statusPathTemplate": "/open/imports/{draftImportId}/state",
  "draftIdResponseKeys": ["jobId"],
  "statusResponseKeys": ["reviewState"],
  "statusMapping": {
    "QUEUED": "PENDING_MANUAL_PLATFORM_REVIEW",
    "DONE": "ACCEPTED_FOR_DRAFT"
  },
  "entities": {
    "lab_template": {
      "draftImportPath": "/open/lab-imports",
      "statusPathTemplate": "/open/lab-imports/{platformDraftId}/state",
      "requestBodyMapping": {
        "lab.title": {
          "source": "payload.title",
          "required": true
        },
        "lab.durationMinutes": "payload.durationMinutes",
        "workflow.idempotencyKey": "idempotencyKey",
        "review.status": {
          "value": "PENDING_MANUAL_PLATFORM_REVIEW"
        }
      }
    }
  }
}
```

`requestBodyMapping` 用于把 dry-run 内部 DTO 映射成未来真实平台请求体候选。键是目标请求体的 dot path，值可以是源 dot path 字符串，也可以是 `{ "source": "...", "required": true }`、`{ "source": "...", "default": ... }` 或 `{ "value": ... }`。配置后，`AgentEntityImportDryRun` 会同时保留 `requestPreview`（内部 DTO）和 `requestBody`（未来平台候选 body），并在 `requestBodyMapping` 中列出映射统计；当前阶段只用于本地预览和字段回归，不发送平台请求。

该文件仅描述平台字段差异，不允许放入 API key、token 或生产数据库连接串。
- `POST /api/agent-entities/{id}/import-result` 请求体需要 `reviewer`、`sendResult` 和 `platformStatus`，可选 `platformDraftId`、`message`、`output`、`coreDbPath`；只把人工确认的平台侧 draft import 状态登记为本地 `AgentEntityImportResultRecord`，并更新平台实体状态。允许状态为 `PENDING_MANUAL_PLATFORM_REVIEW`、`ACCEPTED_FOR_DRAFT`、`REJECTED_BY_PLATFORM`、`FAILED`；传入 `coreDbPath` 时会从 Backend Core repository 的 `platform_entities` 读取实体，并把更新后的实体、Artifact 和 `PLATFORM_ENTITY_IMPORT_RESULT_RECORD` 操作审计写回同一 repository，响应返回 `backendCoreAgentEntityImportResult`，标记 `repositoryContractUsed=true`、`jsonStoreSourceRead=false`、`agentEntityWritten=true`、`artifactWritten=true` 和 `operationAuditEventWritten=true`。接口不查询真实平台、不读取密钥、不发送请求、不发布；业务逻辑由 `BackendAgentEntityService.record_import_result` / `record_import_result_from_repository` 承接。
- `POST /api/agent-entities/{id}/signoff` 请求体需要 `reviewer`，可选 `comment`、`output`；只有 readiness 已满足 `READY_FOR_PLATFORM_ENTITY_SIGNOFF` 才会写入 `AgentEntitySignoffRecord`、Artifact 和 `PLATFORM_ENTITY_SIGNOFF_RECORD` 操作审计。该接口只记录本地人工签收，不改变实体发布状态、不发送请求、不读取密钥、不写真实数据库、不发布。
- `POST /api/agent-entities/{id}/final-publish-review-decision` 请求体需要 `reviewer`、`decision`、`confirmNoAutoPublish=true`、`confirmNoRealPublish=true`、`confirmFinalHumanReview=true`，可选 `comment`、`output`；`decision` 只能是 `APPROVED_FOR_PUBLISH_PLANNING` 或 `NEEDS_REVISION`。只有 `postSignoffPrePublishChecklist.status=READY_FOR_FINAL_HUMAN_PUBLISH_REVIEW` 才会写入 `FinalPublishReviewDecision`、Artifact 和 `PLATFORM_ENTITY_FINAL_PUBLISH_REVIEW_DECISION` 操作审计。该接口只记录本地最终人工复核结论，不改变实体发布状态、不发送请求、不读取密钥、不写真实数据库、不执行真实发布。
- `/api/workflow-runs` 只读本地 Workflow Run 记录，可按 `workflowId`、`status`、`traceId` 过滤。
- `/api/workflow-runs/{id}` 只读单次 Workflow Run 步骤日志。
- `/api/grading/report` 只读取本地 Mock 评分报告 JSON，不执行选手代码。可选 `taskId` 会追加 `mergedGradingEvidence`、`mergedGradingEvidenceSummary` 和 `mergedGradingEvidenceCheckItems`，来源为对应审核任务的 `GRADING_EVIDENCE_MERGE` Artifact；该聚合只读本地任务与 Artifact，不运行沙箱、不自动审核、不发布。
- `POST /api/ai-tasks/{id}/approve` 请求体需要 `reviewer`，只把本地任务从 `WAITING_REVIEW` 流转到 `APPROVED`，并写入本地审计事件。
- `POST /api/ai-tasks/{id}/reject` 请求体需要 `reviewer` 和 `reason`，只把本地任务从 `WAITING_REVIEW` 流转到 `REJECTED`，并写入本地审计事件。
- `POST /api/environments/vm|notebook` 请求体需要 `title` 和 `image`，可选 `resources.cpu`、`resources.memoryGb`，只创建本地 Mock 环境记录。
- `POST /api/environments/{id}/start|stop|reset` 只更新本地 Mock 环境状态并写入统一操作审计事件，不创建或操作真实 VM / Notebook。
- Mock 评分和环境操作都会写入统一操作审计事件，标记不调用真实 LLM、不改动真实云资源、不执行选手代码、不真实发布。
- Provider Mock 固定标记 `realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`；真实 Provider 在 Phase 1 会返回禁用错误。
