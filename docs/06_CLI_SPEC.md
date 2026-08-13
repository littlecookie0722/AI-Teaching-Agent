# 06_CLI_SPEC

> 当前边界：没有真实实训平台后端接口。`platform-entity import-send`、`platform-entity import-status` 和真实平台 draft import 相关命令只作为未来对接团队的技术参考；当前默认不执行，也不要求平台 API base URL 或 `AGENT_API_TOKEN`。本地闭环停止在 import-preview、mock-import、import-dry-run DTO、受控评分 evidence 和人工审核记录。

# CLI 命名

统一命令：

```bash
lab-cli
```

# 命令组

```bash
lab-cli lab ...
lab-cli exam ...
lab-cli grade ...
lab-cli dsl ...
lab-cli ppt ...
lab-cli ai-task ...
lab-cli review ...
lab-cli artifact ...
lab-cli env ...
lab-cli provider ...
lab-cli material ...
lab-cli workflow ...
lab-cli demo ...
lab-cli phase1 ...
lab-cli backend-core ...
lab-cli quality ...
```

# 示例命令

```bash
lab-cli phase1 check
lab-cli phase1 export --output examples/output/phase1-delivery-package.json
lab-cli phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
lab-cli material analyze --input examples/input/demo-source.md
lab-cli demo offline --output examples/output/offline-demo-summary.json
lab-cli lab generate-from-source --input examples/input/demo-source.md
lab-cli lab generate-from-source --input examples/input/demo-source.md --provider-mode real-llm --model deepseek-v4-flash --base-url https://api.deepseek.com --api-surface chat.completions --repair-on-schema-failure --explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish
lab-cli exam generate-from-lab --lab-id lab_demo
lab-cli exam generate-from-lab --lab templates/lab/examples/basic-lab.yaml --provider-mode real-llm --model deepseek-v4-flash --base-url https://api.deepseek.com --api-surface chat.completions --repair-on-schema-failure --explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish
lab-cli exam candidate-preview --exam templates/exam/examples/notebook-fill-blank.yaml --output examples/output/exam-candidate-preview.json
lab-cli grade run --grading templates/grading/examples/python-pytest.yaml
lab-cli grade run --grading templates/grading/examples/python-pytest.yaml --output examples/output/grading-report.json
lab-cli grade evidence-auto --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/readonly-demo --output examples/output/grading-evidence-auto.json
lab-cli grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/controlled-command-demo --output examples/output/grading-stable-v1-evidence.json --submission-id submission_001 --candidate-id candidate_001 --reviewer teacher_1 --image ai-grading-python:0.1 --review-detail-output examples/output/grading-stable-v1-review-detail.json --result-preview-output examples/output/grading-stable-v1-result-preview.json
lab-cli grade evidence-readiness --report examples/output/grading-evidence-auto.json --output examples/output/grading-evidence-readiness.json
lab-cli grade result-preview --report examples/output/grading-evidence-auto.json --candidate-id candidate_001 --output examples/output/grading-result-preview.json
lab-cli grade job-create --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/readonly-demo --output examples/output/grading-job-evidence-auto.json --submission-id submission_001 --reviewer teacher_1
lab-cli grade job-run --id grading_job_demo
lab-cli grade job-list --submission-id submission_001
lab-cli grade job-get --id grading_job_demo
lab-cli grade job-create --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/readonly-demo --output examples/output/grading-job-evidence-auto.json --submission-id submission_001 --reviewer teacher_1 --db-path examples/output/grading-local.sqlite3
lab-cli grade job-run --id grading_job_demo --db-path examples/output/grading-local.sqlite3
lab-cli grade record-create --report examples/output/grading-evidence-auto.json --submission-id submission_001 --candidate-id candidate_001 --reviewer teacher_1
lab-cli grade record-list --submission-id submission_001
lab-cli grade record-get --id grading_record_demo
lab-cli grade record-review --id grading_record_demo --reviewer teacher_1 --decision approve-ready
lab-cli grade db-init --db-path examples/output/grading-local.sqlite3
lab-cli grade db-sync-local --db-path examples/output/grading-local.sqlite3
lab-cli grade db-summary --db-path examples/output/grading-local.sqlite3
lab-cli grade worker-run-once --db-path examples/output/grading-local.sqlite3 --lease-seconds 300 --max-attempts 3
lab-cli grade worker-drain-once --db-path examples/output/grading-local.sqlite3 --limit 5 --lease-seconds 300 --max-attempts 3
$env:LAB_BACKEND_CORE_DATABASE_URL="postgresql://<db_user>:<db_password>@<test-host>:5432/lab_core_staging"
lab-cli backend-core postgresql plan
lab-cli backend-core postgresql init --confirm-test-database
lab-cli backend-core postgresql summary
lab-cli backend-core postgresql smoke --confirm-test-database --reviewer teacher_smoke
$env:LAB_BACKEND_CORE_DATABASE_URL="mysql://<db_user>:<db_password>@<test-host>:3306/lab_core_staging"
lab-cli backend-core mysql plan
lab-cli backend-core mysql init --confirm-test-database
lab-cli backend-core mysql summary
lab-cli backend-core mysql smoke --confirm-test-database --reviewer teacher_smoke
lab-cli quality regression-profiles
lab-cli quality regression-matrix --profile quick --output examples/output/regression-matrix-quick.json
lab-cli quality regression-matrix --profile core --stop-on-failure --output examples/output/regression-matrix-core.json
lab-cli grade report --file examples/output/grading-report.json
lab-cli audit list
lab-cli audit list --resource-type ENVIRONMENT --action ENV_CREATE
lab-cli artifact list
lab-cli artifact list --kind LAB_DSL
lab-cli artifact get --id artifact_demo
lab-cli lab import-preview --task-id <approved_lab_task_id> --reviewer teacher_4 --output examples/output/lab-template-import-preview.json
lab-cli lab mock-import --task-id <approved_lab_task_id> --reviewer teacher_4 --output examples/output/lab-template-mock-import.json
lab-cli exam import-preview --task-id <approved_exam_task_id> --reviewer teacher_5 --output examples/output/exam-question-import-preview.json
lab-cli exam mock-import --task-id <approved_exam_task_id> --reviewer teacher_5 --output examples/output/exam-question-mock-import.json
lab-cli grade import-preview --task-id <approved_grading_task_id> --reviewer teacher_5 --output examples/output/grading-rule-import-preview.json
lab-cli grade mock-import --task-id <approved_grading_task_id> --reviewer teacher_5 --output examples/output/grading-rule-mock-import.json
lab-cli platform-entity list --source-task-id <approved_task_id>
lab-cli platform-entity get --id <agent_entity_id>
lab-cli platform-entity readiness-report
lab-cli platform-entity readiness-report --source-task-id <approved_task_id>
lab-cli platform-entity contract-validate --contract-config examples/input/platform-contract.json
lab-cli platform-entity contract-validate --contract-config examples/input/platform-contract.json --entity-type lab_template
lab-cli platform-entity import-dry-run --id <agent_entity_id> --reviewer teacher_6 --output examples/output/platform-entity-import-dry-run.json --contract-config examples/input/platform-contract.json
# 真实平台 import-send / import-status / import-result / signoff 当前暂停，不作为本地闭环命令示例。
lab-cli dsl validate --kind ppt --file templates/ppt/examples/course-ppt.yaml
lab-cli ppt generate --input examples/input/demo-source.md
lab-cli ppt artifact build --dsl templates/ppt/examples/course-ppt.yaml --output examples/output/ppt-artifact-demo.pptx --manifest-output examples/output/ppt-artifact-demo-manifest.json
lab-cli ai-task list
lab-cli ai-task list --status WAITING_REVIEW --task-type LAB_GENERATION
lab-cli ai-task get --id task_demo
lab-cli review list
lab-cli review list --task-type LAB_GENERATION
lab-cli review batch-summary
lab-cli review batch-summary --task-type LAB_GENERATION --limit 10
lab-cli review batch-summary --output examples/output/review-batch-summary.json
lab-cli review approve --task-id task_demo --reviewer teacher_1
lab-cli review reject --task-id task_demo --reviewer teacher_1 --reason "不符合要求"
lab-cli review publish --task-id task_demo
lab-cli review detail --task-id task_demo
lab-cli review detail --task-id task_demo --output examples/output/review-detail.json
lab-cli review core-readiness --task-id task_demo
lab-cli review core-readiness --task-id task_demo --output examples/output/core-readiness.json
lab-cli review ppt-page-status --task-id task_demo
lab-cli review ppt-page-status --task-id task_demo --output examples/output/ppt-page-review-status.json
lab-cli review ppt-page-update --task-id task_demo --slide-index 1 --review-status APPROVED --reviewer teacher_1 --comment "封面通过"
lab-cli review second-confirmation-status --task-id task_demo
lab-cli review audit --task-id task_demo
lab-cli env list
lab-cli env create --type vm --title "Ubuntu VM" --image ubuntu-22.04
lab-cli env get --id env_demo
lab-cli env start --id env_demo
lab-cli env stop --id env_demo
lab-cli env reset --id env_demo
lab-cli provider list
lab-cli provider health
lab-cli provider real-llm-runtime-config --model deepseek-v4-flash --base-url https://api.deepseek.com
lab-cli provider mock-generate --prompt-id lab_generation_v0
lab-cli provider audit --operation generateJson
lab-cli mcp list
lab-cli mcp call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
lab-cli mcp audit --tool analyze_material
lab-cli workflow demo --input examples/input/demo-source.md --reviewer teacher_1
lab-cli workflow demo --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/demo-report.json
lab-cli workflow list
lab-cli workflow list --workflow-id phase1_main_demo --status COMPLETED
lab-cli workflow get --id workflow_run_demo
lab-cli workflow report --file examples/output/demo-report.json
```

# 返回格式

成功：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {},
  "traceId": "trace_xxx"
}
```

# Phase 1 审核约束

- AI 生成内容默认进入 `WAITING_REVIEW`。
- `review approve` 和 `review reject` 必须记录 `reviewer`。
- `review reject` 必须填写 `reason`。
- `review list` 默认返回 `WAITING_REVIEW` 待审核队列。
- `review batch-summary` 聚合待审核队列卡片、状态统计和批量动作策略；只允许查看和导出摘要，不允许批量 approve/reject/publish。
- `review detail` 聚合单个任务的产物、Workflow 步骤、审核审计、操作审计、发布阻断策略和 `reviewPage` 页面模型，供后续前端审核页使用；高风险 MCP 意图任务会额外返回 `highRiskIntent.postReviewDisposition`、`reviewPolicy.postReviewDispositionState` 与 `reviewPage.highRiskIntentPanel`，并保持 `executeRealActionAllowed=false`、`realPublish=false`、`environmentDestroyed=false`；PPTX Artifact 审核任务会返回 `pptPageReview`，包含 `pageReviewSummary`、`slideReviews`、人工批注和 QA 信号；可通过 `--output` 导出本地 JSON。
- `review core-readiness` 只读聚合 `review detail`、内容质量摘要、平台实体 readiness、`platformImportPreviewActions` 和 Grading `preApproveReviewCheck`，输出 `CoreWorkflowReadinessReport`，用于判断某个任务离核心演示闭环还缺哪一步。Lab 任务只检查 `lab_template`，Exam 任务检查 `exam_question` 与 `grading_rule`，Grading 任务会先检查 evidence、decision note、`manualReviewChecklistStatus`、`decisionNoteRecommendation` 与 `approve-ready` 决策，再检查平台实体导入步骤，避免在评分证据不足时先推进平台草稿；若已有本地 `GradingRecord`，还会把 `gradingRecords.reviewIntegration.readyForPlatformReview` 纳入步骤，要求单条评分记录经人工 `record-review approve-ready` 后再继续平台复核。没有评分记录时不阻断 Grading DSL 导入预览。`nextToolRecommendation` 会用 `toolAvailable=false` 和 `cliCommand=python lab_cli.py grade record-review ...` 表达评分记录复核是人工动作，不伪装成 MCP 工具；当内容质量判定需要先修订时，`recommendedNextAction` 优先返回 `request_content_revision_before_import_preview`，并建议 `review revision-request`；当任务已审核但还没有生成导入预览时，`platformImportPreviewActionSummary` 会列出 pending 平台实体、预览组件、下一步动作和 CLI 命令；该命令不执行导入、不发送请求、不启动沙箱、不自动 approve、不发布。
- `agent real-demo plan-core-next-tool` 只读调用 MCP Mock 工具 `get_core_workflow_readiness`，输出 `AgentCoreNextToolPlan`，把 `CoreWorkflowReadinessReport.nextToolRecommendation` 转成 Agent 可读步骤计划。默认 `--profile local-core-mvp`，只规划本地核心 MCP 工具；当 readiness 推荐真实平台 import-send / import-status / 签收 / 最终发布复核或 revision-loop 暂停工具时，返回 `blockedByToolProfile=true` 与 `toolProfileStopGuidance`，不会要求平台 API base URL 或 token。它只规划，不调用推荐工具，固定 `recommendedToolCalled=false`、`realAgentStarted=false`、`realMcpServerStarted=false`、`autoExecuteAllowed=false`、`autoApproveAllowed=false`、`autoPublishAllowed=false`。
- `agent real-demo execute-core-next-tool` 需要显式 `--confirm-execute-recommended-tool`，先读取 `get_core_workflow_readiness`，再执行且只执行一个当前 profile 允许的 `nextToolRecommendation.toolName`。执行完成后会再次只读读取 readiness，返回 `postExecutionCoreNextToolPlan` 与 `nextSingleStepActionGuide` 作为下一步提示；`canContinueWithSameCommand=true` 时可复制 `suggestedCliCommand` 继续下一次人工确认单步推进。支持 `--arguments` / `--arguments-file` 覆盖推荐参数中的输出路径；输出 `AgentCoreNextToolExecutor`，固定 `executedToolTotal=1`、`autoApproveAllowed=false`、`autoPublishAllowed=false`、`realPublish=false`。当 Grading 已完成 evidence、`approve-ready` decision note 和人工 approve 后，该命令会依次推荐 `create_grading_rule_import_preview`、`create_grading_rule_mock_import`、`create_agent_entity_import_dry_run`，第三步只生成平台 draft import DTO 预览，并在默认 `local-core-mvp` 下以 `LOCAL_CORE_MVP_STOP_LINE_REACHED` 停止。`--profile all` 仅作为历史全量 manifest 回归参考，不作为当前 Agent 默认路线。
- `review ppt-page-status` 只读查询 PPT / PPTX 审核任务的逐页审核状态模型，返回 `APPROVED` / `NEEDS_REVIEW` / `REVISE_REQUIRED` 汇总、每页人工批注和 QA 信号；不写审核决定、不自动通过、不发布真实课件。
- `review ppt-page-update` 只更新本地 `PPTX_FILE` Artifact metadata 中的单页审核状态和人工批注，并写入 `PPT_PAGE_REVIEW_UPDATE` 操作审计；不改变 AI Task 总状态、不自动通过、不真实发布。`REVISE_REQUIRED` 必须填写 `--comment`。
- `review second-confirmation-status` 只读查询高风险 MCP 意图的二次确认 Mock 状态；非二次确认意图返回 `VALIDATION_ERROR`，销毁环境意图固定 `secondConfirmationSatisfied=false`、`confirmationActionAvailable=false`、`destroyRealEnvironmentEnabled=false`。
- `review audit` 只读取本地审核审计事件，可按 `taskId`、`action`、`actor` 过滤。
- `review publish` 仅允许 `APPROVED` 任务进入 `COMPLETED`，并且只返回 Mock 发布结果，不发布真实平台实体。
- `ai-task list` 从本地 Mock store 读取任务列表，可按 `status` 和 `taskType` 过滤。
- `artifact list/get` 只读取本地 Mock 产物清单，可按 `kind`、`taskId`、`workflowRunId`、`traceId` 过滤，不读取真实远程存储。
- `lab/exam/grade import-preview` 只接受已 `APPROVED` 的 DSL 任务，生成本地平台实体草稿导入预览，不写真实数据库、不发布。
- `lab/exam/grade mock-import` 要求先存在对应导入预览，只把实体草稿写入本地 JSON store 的 `platformEntities`；返回 `mockStoreWritten=true`，同时固定 `databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。
- `grade db-init`、`grade db-sync-local`、`grade db-summary` 只操作开发机本地 SQLite 文件，用于验证 `grading_jobs` / `grading_records` 持久化草案和从 JSON store 同步的 round-trip；固定 `localSqliteOnly=true`、`productionDatabaseWritten=false`、`queuePersistedToProduction=false`、`autoApproveAllowed=false`、`realPublish=false`。`grade job-create/job-run/job-list/job-get --db-path <file>` 可直接读写该 SQLite 文件，并把执行后的 job / record 镜像回 JSON store，供现有审核详情读取；`grade worker-run-once` 会先回收过期 `RUNNING` claim：未达 `--max-attempts` 的任务回到 `QUEUED`，达到上限的任务转为 `FAILED`；随后用 `claimOwner`、`claimedAt`、`claimExpiresAt`、`attemptCount` 领取一个 `QUEUED` / `FAILED` job 并标记为 `RUNNING`，再单次同步执行。`grade worker-drain-once` 复用同一单次 worker，按 `--limit` 顺序执行有限批次，默认 5、最大 20，队列为空或单个 job 失败即停止；响应包含 `workerDrain.quota`、`workerDrain.resourceCleanup` 和 `GRADING_WORKER_DRAIN` 批次审计。`--lease-seconds` 默认 300，`--max-attempts` 默认 3。它不是常驻后台 worker，不使用生产队列，也不启动并发 worker。
- `backend-core postgresql plan/init/summary/smoke` 是 Backend Core PostgreSQL 测试库迁移和实跑证据入口。`plan` 只解析 `LAB_BACKEND_CORE_DATABASE_URL` 或 `--database-url-env` 指向的 PostgreSQL URL，返回脱敏计划、driver 安装状态和 schema 表清单，固定不访问网络、不写 schema；`init` 必须传 `--confirm-test-database`，显式注册 PostgreSQL adapter 并初始化测试 / staging schema；`summary` 只读取真实仓储摘要；`smoke` 会写入一条待审核 AI Task、Artifact、操作审计并执行人工 approve round-trip，验证真实库读写和审核状态流转。命令都返回统一 JSON，不回显完整连接串、host、账号、密码或 token，不自动发布、不连接生产队列。真实执行需要安装 `psycopg[binary]`。
- `backend-core mysql plan/init/summary/smoke` 是 Backend Core MySQL 测试库迁移和实跑证据入口。`plan` 只解析 `LAB_BACKEND_CORE_DATABASE_URL` 或 `--database-url-env` 指向的 MySQL / MariaDB URL，返回脱敏计划、driver 安装状态和 schema 表清单，固定不访问网络、不写 schema；`init` 必须传 `--confirm-test-database`，显式注册 MySQL adapter 并初始化测试 / staging schema；`summary` 只读取真实仓储摘要；`smoke` 会写入一条待审核 AI Task、Artifact、操作审计并执行人工 approve round-trip。真实执行需要安装 `mysql-connector-python`，默认 HTTP mock 不自动连接外部库。
- `quality regression-profiles` 只列出本地固定回归测试 profile；`quality regression-matrix` 只按 `quick`、`core`、`backend-core`、`real-llm-offline`、`mcp` 这些预定义 profile 运行白名单 pytest 子集并输出 JSON 报告。它不接收任意命令字符串，不使用 shell，默认排除 `integration` 和 `real_llm_online` marker，不读取密钥、不调用真实 LLM、不连接生产数据库、不发布。失败时仍返回统一 JSON，并在 `regressionMatrix` 中保留失败命令、exitCode、stdout/stderr 摘要和安全断言。
- `platform-entity list/get` 只读取本地 Mock 平台实体草稿，可按 `sourceTaskId`、`entityType` 或 `traceId` 查询，不连接真实平台数据库；`get` 会返回 `agentEntityImportActivity` 只读摘要，用于查看 import dry-run / send Artifact 与操作审计状态，不读取报告正文、不回显密钥。
- `platform-entity readiness-report` 只读汇总 `lab_template`、`exam_question`、`grading_rule` 的导入预览、Mock 入库和人工平台复核就绪状态；可用 `--source-task-id` 聚焦单个任务，固定 `databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。
- `platform-entity contract-validate` 只读取本地 `--contract-config` JSON，校验平台 draft import endpoint、状态字段别名、状态映射和 `requestBodyMapping` 结构，可用 `--entity-type` 只检查单类实体。仓库内的 `examples/input/platform-contract.json` 是四类实体本地 staging 样例，可直接用于 CLI/HTTP 校验和 dry-run 回归；它不是正式平台 API 字段契约。命令返回 `platformApiContractValidation`，包含每类实体的 endpoint、request body 来源、字段映射统计、未知顶层字段 warning 和安全标记；固定 `requestSent=false`、`networkAccess=false`、`secretsRead=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`。
- `platform-entity import-dry-run` 读取本地 `mock-import` 产生的 `platformEntities` 记录，转换成未来真实平台 draft import API 的 DTO 与目标 endpoint 预览，并写入 `WORKFLOW_REPORT` Artifact 和操作审计。可选 `--contract-config <json>` 读取本地 JSON 契约配置，覆盖 `entities.<entityType>.draftImportPath`、`statusPathTemplate`、`draftIdResponseKeys`、`statusResponseKeys`、`statusMapping` 和 `requestBodyMapping`；生效后的 `platformApiContract` 和 `contractValidation` 会写入 dry-run 报告。该命令只做本地 dry-run，固定 `dryRunOnly=true`、`requestSent=false`、`networkAccess=false`、`databaseWritten=false`、`realAgentImport=false`、`realPublish=false`，不会调用真实平台 API。
- `platform-entity import-send`、`platform-entity import-status`、`platform-entity import-result` 和 `platform-entity signoff` 当前只作为未来真实平台对接团队的技术参考保留；没有真实平台后端接口时，不要求平台 API base URL、`AGENT_API_TOKEN`、平台状态或平台侧签收，不作为本地闭环下一步。
- `env create/start/stop/reset` 仅更新本地 Mock 状态，不创建、启动、停止或重置真实资源。
- `material analyze` 仅对本地 Markdown / 文本 / Shell 素材做静态摘要和风险标记，不执行 Shell、不抓取远程内容、不调用真实 LLM。
- `lab generate-from-source` 会先复用素材分析结果，再生成任务专属 `examples/output/<task_id>-lab.json` Lab DSL、创建 `WAITING_REVIEW` 任务，并返回 `labFeatureReadiness`。默认 `--provider-mode mock` 不读取密钥、不联网；显式 `--provider-mode real-llm` 时会复用 OpenAI-compatible SDK 边界，用 `OPENAI_API_KEY`、`--model` / `OPENAI_MODEL` 和 `--base-url` / `OPENAI_BASE_URL` 发送一次真实 Lab DSL 请求。真实模式仍必须传 `--explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish`，生成后继续走同一条人工审核、`lab import-preview` 和 `lab mock-import` 路径，不执行真实平台发布。稳定 v1 判定要求：Schema 已校验、DSL 绑定本次输入素材、至少 2 个学习目标和 3 个实验步骤、审核前不可发布。
- `exam generate-from-lab` 保留旧 `--lab-id` Mock 兼容路径，同时新增稳定 v1 路径：传入 `--lab <Lab DSL>` 后会先校验 Lab DSL，再生成任务专属 `examples/output/<task_id>-exam.json`、`examples/output/<task_id>-grading.json` 和 `examples/output/<task_id>-exam-candidate-preview.json`，创建一个 `WAITING_REVIEW` 任务并返回 `examGradingFeatureReadiness`。显式 `--provider-mode real-llm` 时会用 OpenAI-compatible 模型分别生成 Exam DSL 与 Grading DSL，然后做跨产物归一化：题目 `gradingRef` 必须被 Grading `checks` 与 `assessmentPlan` 覆盖，总分对齐，候选人预览移除 `answer` 与 `gradingRef`。真实模式必须传 `--lab` 和三项确认参数；审核通过前不能导入预览，审核通过后继续走本地 `exam import-preview` 与 `grade import-preview`，不调用真实平台、不发布。
- `ppt artifact build` 只读取本地 `WAITING_REVIEW` PPT DSL，使用 bundled artifact-tool 导出本地 PPTX Artifact，写入 `PPTX_FILE` 产物清单；不新增 LLM 请求、不读取密钥、不上传、不自动发布。
- `exam candidate-preview` 读取本地 Exam DSL，先做 Schema 校验，再输出 `ExamCandidatePreview` JSON；选手端字段不包含 `answer`，并且会检测答案文本是否泄漏到候选人可见内容。
- `workflow demo` 只串联本地 Mock 主链路，仍然要求人工审核，不自动发布，并将报告保存为 JSON。
- `workflow demo` 会写入本地 Workflow Run 记录，记录步骤顺序、traceId、报告路径和 Phase 1 安全标记。
- `workflow list/get` 只读取本地 Workflow Run 记录，可按 `workflowId`、`status`、`traceId` 查询。
- `workflow report` 只读取本地 Mock 报告文件。
- `phase1 check` 使用临时本地文件执行 DSL、审核防线、Workflow 报告和 Backend Mock 自检。
- `phase1 export` 导出本地 Mock 交付包，不发布真实内容；输出包含交付物清单、验收清单、验收摘要和安全断言。
- `phase1 report` 只读取本地 Mock 交付包并渲染 Markdown 验收报告；报告用于人工验收，不重新生成内容、不调用真实 Provider、不发布真实内容。
- `grade run --output` 保存本地 Mock 评分报告，不执行选手代码。
- `grade report` 只读取本地 Mock 评分报告。
- `grade result-preview` 只读取已有本地评分报告并输出候选人安全的评分结果预览，不重新评分、不启动 Docker、不执行选手代码、不发布。
- `grade run` 会写入统一操作审计事件。
- `grade evidence-auto` 会先运行只读 evidence，再按显式参数选择是否运行受控 Docker command evidence，并输出统一合并报告；报告包含 `executionMatrix`、`nextCoreAction`、`manualReviewChecklist` 和 `decisionNoteRecommendation`，用于判断 check 级证据覆盖、受控命令缺口、下一步核心动作以及人工审核应记录 `approve-ready` / `needs-evidence` / `needs-revision` 哪类 decision note；`executionMatrix.items` 顶层会直接给出 `status`、`passed`、`earnedScore`、`evidenceSourceKind`、`exitCode`、`stdoutTail`、`stderrTail`、`filesInspected`、`errorCode`、`errorReason` 和 `reason`，供 CLI / 前端快速展示失败原因。默认不执行选手代码，不自动通过，不发布。受控 Docker report 会透出 `imageSupplyChain` 本地镜像供应链审计摘要，包含 imageId/digest、allowlist 匹配、禁止自动 pull 和未使用 registry auth；也会透出 `isolationQuality`，汇总网络关闭、只读挂载、只读 rootfs、资源限制、输出捕获、本地镜像检查和 registry 网络未使用等本地质量信号。
- `grade stable-v1` 是第三个主功能稳定入口：读取 Grading DSL 与本地 submission，默认请求受控 command evidence，复用已有本地 `GradingJob` 同步运行，生成 `GRADING_EVIDENCE_AUTO_REPORT`、本地 `GradingRecord`、`gradingResultPreview` 和 `reviewDetail`，并返回 `gradingStableV1Readiness.completeForStableV1`。该命令只写本地 JSON store 和本地产物，不自动 `record-review`、不改变 AI Task 审核状态、不发送真实平台请求、不发布；本地真实 Docker runtime smoke 可用 `--image ai-grading-python:0.1 --fail-on-controlled-unavailable` 强制验证 Docker 路径，不可用时直接失败；若 Docker runtime 不可用且未设置 `--fail-on-controlled-unavailable`，报告会保留只读 evidence 和 warning，readiness 会指出受控 evidence 未完成。
- `grade evidence-readiness` 只读取已有 evidence 报告并输出评分证据就绪摘要，列出已覆盖 check、缺失 evidence、建议下一步 evidence 收集或人工复核动作；不启动沙箱、不执行 pytest、不启动 Notebook、不执行选手代码。
- `audit list` 只读取本地统一操作审计事件，可按 `resourceType`、`resourceId`、`action`、`actor` 过滤。
- `provider list` 只读取 Phase 1 Provider 契约，只有 `mock` Provider 启用。
- `provider health` 默认读取 MockProvider 状态；真实 Provider 返回禁用错误。
- `provider real-llm-runtime-config` 只读汇总真实 LLM 命令所需运行时配置，支持用 `--model` 和 `--base-url` 预览 OpenAI-compatible 命令参数来源；返回 `commandReadiness` 和不含密钥的 `safeCommandTemplates`，帮助操作者复制运行时检查和真实 LLM workflow 参数；API Key 仍只能来自 `OPENAI_API_KEY` 环境变量，命令不接受 key 参数、不返回 key 值、不创建 client、不发送请求、不创建任务、不发布。
- `provider mock-generate` 只返回本地 DSL 示例引用，状态为 `WAITING_REVIEW`，不调用真实 LLM、不读取密钥、不访问网络。
- `provider audit` 只读取本地 Provider 调用审计，可按 `--provider`、`--operation`、`--status`、`--prompt-id`、`--trace-id`、`--actor` 过滤。
- `mcp audit` 只读取本地 MCP Tool 调用记录，可按 `--tool`、`--status`、`--trace-id`、`--actor`、`--backend-path` 过滤。

失败：

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "参数错误",
  "errors": [],
  "traceId": "trace_xxx"
}
```
