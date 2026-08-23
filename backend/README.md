# backend

Phase 1 Backend API Mock 适配层。核心实现仍是不连接数据库的本地请求处理函数；另提供框架无关的 `BackendApiApp` 边界和可选本地 HTTP 包装器，用于让静态前端页面通过浏览器读取 `/api/*`。

> 当前没有真实实训平台后端接口。Backend Mock 当前默认只支撑本地闭环：审核任务、导入预览、mock-import、import-dry-run DTO、受控评分 evidence、评分记录和本地审计；`/api/platform-entities/{id}/import-send`、`/import-status`、真实平台状态登记、平台侧签收和发布前复核只作为未来其他团队对接平台时的技术参考，不作为当前运行或开发目标。

## 输入说明

- `method`: 当前支持 `GET`，以及素材分析、Workflow Demo、Lab/Exam/PPT 生成、Lab/Exam/Grading/PPT 导入预览、Mock 评分、AI Task 审核动作、环境状态动作的 `POST`。
- `path`: 形如 `/api/materials/analyze`、`/api/workflow/demo`、`/api/labs/generate`、`/api/exams/generate-from-lab`、`/api/grading/evidence-merge`、`/api/ppt/generate`、`/api/ppt/import-preview`、`/api/ppt/mock-import`、`/api/providers`、`/api/provider-audit-events`、`/api/ai-tasks`、`/api/review-task-summary`、`/api/review-tasks/{id}`、`/api/review-tasks/{id}/revision-request`、`/api/review-audit-events`、`/api/audit-events`、`/api/environments`、`/api/ai-tasks/{id}/approve`、`/api/environments/{id}/start` 的 API 路径。
- `body`: `POST` 动作使用本地字典，例如 `{"reviewer": "teacher_1"}` 或环境创建参数。
- Mock store：默认与 CLI 一致，可通过测试传入本地 JSON store 路径。

## 输出说明

所有接口返回统一 JSON：

```json
{
  "success": true,
  "code": "OK",
  "message": "查询成功",
  "data": {},
  "traceId": "trace_xxx"
}
```

## 命令示例

```powershell
python -m pytest tests/test_backend_mock_api.py
```

本地浏览器演示可启动标准库 HTTP 包装器：

```powershell
python -m backend.mock_http_server --host 127.0.0.1 --port 8000
```

`backend/app.py` 提供 `BackendApiApp`、`BackendAppResponse` 和统一 HTTP 状态映射；`backend/mock_http_server.py` 只负责标准库 HTTP 读写、JSON body 解析和静态响应发送。后续迁移 FastAPI / ASGI / 真实后端框架时，应优先复用或替换 `BackendApiApp.handle()` 这一层，而不是继续把路由、鉴权、静态路径解析和状态码逻辑堆进 server handler。

同时提供无第三方依赖的 ASGI 适配层：

```text
backend.asgi_app:app
```

该入口实现 ASGI callable、lifespan、GET/POST、header 透传、JSON object body 校验和统一响应发送，内部仍复用 `BackendApiApp.handle()`。当前仓库不强制安装 `uvicorn` / `fastapi`；后续如果要试跑 ASGI 服务，可在本地开发环境额外安装 ASGI server 后挂载 `backend.asgi_app:app`。该入口仍是开发 / 迁移边界，不代表生产部署、生产数据库或生产鉴权完成。

如果希望评分任务 API 默认使用同一个本地 SQLite staging 文件，而不是每次请求都传 `dbPath`，可使用：

```powershell
python -m backend.mock_http_server --host 127.0.0.1 --port 8000 --grading-db examples/output/grading-local.sqlite3
```

等价地，也可以设置环境变量 `LAB_BACKEND_GRADING_DB_PATH`。该配置只影响 Backend Mock 的 Grading Job API、Grading Record 创建/复核写路径和 `/api/grading/workers/run-once`、`/api/grading/workers/drain-once` 默认持久化路径；显式请求体或 query 中的 `dbPath` 仍然优先。它仍是本地 SQLite staging，不是生产数据库。

真实后端 API MVP 的最小鉴权边界可通过环境变量开启：

```powershell
$env:LAB_BACKEND_API_TOKEN="<random-local-token>"
python -m backend.mock_http_server --host 127.0.0.1 --port 8000
```

开启后，除 `GET /api/health` 外，所有 `/api/*` 请求都必须带 `Authorization: Bearer <random-local-token>`。未配置 `LAB_BACKEND_API_TOKEN` 时，服务仅允许绑定 loopback 地址；如果指定非 loopback 地址，则必须配置 token，否则拒绝启动。配置后错误或缺失 token 会返回统一 JSON，错误码为 `AUTH_REQUIRED` 或 `AUTH_INVALID`，HTTP 包装器映射为 401。服务不会在响应中回显 token。

启动后可访问：

```text
http://127.0.0.1:8000/review-center.html
http://127.0.0.1:8000/platform-entities.html
http://127.0.0.1:8000/api/backend/core-readiness
http://127.0.0.1:8000/api/backend/core-db/summary?coreDbPath=examples/output/backend-core-local.sqlite3
http://127.0.0.1:8000/api/review-task-summary
http://127.0.0.1:8000/api/review-task-summary?limit=3&detailMode=light
```

该服务默认只绑定 `127.0.0.1`，复用本地 Mock store，静态文件只从 `frontend/` 目录读取；它不连接真实数据库、不调用真实 LLM、不执行沙箱、不创建云资源。POST API 仍沿用 `backend.mock_api.handle_request` 的人工审核和安全边界，审核中心页面的 `review-center-data.js` 只发 GET 请求。页面首屏使用 `detailMode=light` 轻量摘要，避免本地 store 变大时为每个待审核任务展开完整 `reviewDetail`；需要人工审核时再调用 `GET /api/review-tasks/{id}` 加载详情。`realDemoReviewQueue` 会优先检查 `examples/output/real-llm-lab.json`、`real-llm-exam.json`、`real-llm-grading.json`、`real-llm-ppt.json` 和 PPTX artifact 是否存在，并尝试把这些路径绑定到当前 Mock store 中最新 `WAITING_REVIEW` 任务；若找到动态任务，审核中心会默认优先打开该真实任务详情，若只有本地产物没有任务，则仅显示只读产物卡片并提示先运行真实 workflow / one-click 写入 store。`platform-entities.html` 使用 `GET /api/platform-entities`、`GET /api/platform-entities/{id}` 和 `GET /api/platform-entities/readiness-report` 查看本地 Lab / Exam / Grading 草稿与就绪状态；审核中心会用 `entityId`、`sourceTaskId` 和 `entityKind=lab|exam|grading` 深链到该页，自动定位实体并选择准备类型。页面提供本地平台契约校验入口 `POST /api/platform-entities/contract-validate`，默认读取 `examples/input/platform-contract.json` 并把同一份 `contractConfig` 用于 dry-run，用于检查四类实体 endpoint、状态别名和 `requestBodyMapping`；该校验只读本地 JSON，不读取 token、不发送真实平台请求、不写库。页面还提供 `AgentEntityDemoDataPrepareAction`，先通过 `GET /api/ai-tasks?status=APPROVED&taskType={taskType}` 只读加载已审核任务候选，再对已 `APPROVED` 的任务串联 `import-preview -> mock-import -> import-dry-run` 准备本地演示草稿。`readiness-report` 当前只作为本地草稿、dry-run、受控评分 evidence 和评分记录复核的只读汇总；send、status query、result record、signoff 和 final publish review decision 计数仅保留为未来真实平台对接参考，不作为当前演示闭环要求。审核中心卡片当前应关注本地 artifact、导入预览、dry-run DTO、评分 evidence 和评分记录复核摘要。页面不输入或展示 token，不自动审核，不发布实体，仍固定 `databaseWritten=false`、`realPublish=false`。

审核中心也支持自定义真实输出批次：给 `/api/review-task-summary` 和 `/api/review-tasks/{id}` 追加 `agentReport=<workflow-report-json>`，其中 report 必须是 `phase2 workflow run --provider-mode real-llm` 生成的 workflow report，且包含 `generatedDsl.lab/exam/grading/ppt.dslPath`。`GET /api/review-task-summary?detailMode=light&agentReport=examples/output/p0-deepseek-v4-flash-live-workflow-report.json` 会把该 report 中的 Lab / Exam / Grading / PPT 路径映射成 `realDemoReviewQueue.items[]`。`GET /api/review-tasks/{id}?agentReport=...` 会优先按该 report 生成只读 synthetic review detail，即使当前 Mock store 里已有同名 taskId，也会展示本批次 report 的 DSL 路径、`reviewPage.dslPreview`、DSL artifact 和 Workflow Report artifact；若轻量 report 只有 DSL 路径而没有 taskId，则使用 `real_demo_lab` / `real_demo_exam` / `real_demo_grading` / `real_demo_ppt` fallback。Exam 预览保持 `candidateSafety.answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false` 和 `answersRemovedFromSafePreview=true`。该路径只读本地文件，不再次请求 LLM、不读取密钥、不执行沙箱、不自动审核、不发布。

当平台实体已在 Backend Core SQLite staging 中，而评分记录在 Grading SQLite staging 中时，可用显式双路径查询把两套本地 staging 只读拼接起来：

```text
GET /api/platform-entities/readiness-report?sourceTaskId=<task_id>&coreDbPath=examples/output/backend-core-local.sqlite3&gradingDbPath=examples/output/grading-local.sqlite3
```

其中 `coreDbPath` 只用于读取 Backend Core 的 `platform_entities` / Artifact / 操作审计，`gradingDbPath` 只用于读取 Grading SQLite 的 `grading_records`。响应中的 `backendCoreAgentEntityReadiness.gradingRecordExternalSourceUsed=true` 和 `gradingRecordSource.mode=LOCAL_SQLITE_GRADING_RECORD_READINESS_BRIDGE` 表示已启用该桥接；若 `gradingDbPath` 文件不存在，会返回 `gradingRecordSource.available=false` 和原因，不会初始化或创建 SQLite 文件。该查询只读，不写任一 SQLite 文件，不启动 worker，不执行沙箱，不发送平台请求。

本地 HTTP 包装器也可用于验证“审核通过后生成本地导入预览”的核心闭环：先调用 `POST /api/ai-tasks/{id}/approve` 将 DSL 任务变为 `APPROVED`，再调用 `POST /api/labs/import-preview`、`POST /api/exams/import-preview`、`POST /api/grading/import-preview` 或 `POST /api/ppt/import-preview` 生成本地平台草稿预览。`POST /api/grading/import-preview` 会在 `GradingRuleImportPreview.controlledEvidenceNextAction` 中给出 `POST /api/grading/evidence-auto` 与 `grade evidence-auto --include-controlled-command` 的下一步证据生成入口，提示最终导入复核前先收集评分 evidence；`POST /api/ppt/import-preview` 会生成 `ppt_deck` 草稿，并标记 PPTX Artifact 仍需人工审核后再规划发布。该预览不执行沙箱、不执行选手代码。随后 `GET /api/review-tasks/{id}` 会在 `platformImportPreview`、`platformImportPreviewActions` 和 `platformImportPreviewSignoff` 中展示已生成预览、签收项和缺口状态；整个过程固定 `databaseWritten=false`、`realPlatformImport=false`、`realPublishAllowed=false`。

`GET /api/backend/core-readiness` 是真实后端 API MVP 前的只读 readiness 汇总接口，用于查看 AI Task、Artifact、Review、Platform Entity Import、Grading Job、Grading Record、Grading Worker 和 Audit 八类核心 API 是否已有本地 contract / staging 数据，以及迁移到真实后端还缺哪些生产能力。可选 query 参数：`taskId` 用于按任务过滤 Grading Job / Record 与平台实体，`dbPath` 用于只读查看本地 SQLite staging 摘要。该接口固定不创建 SQLite 文件、不初始化 schema、不启动 worker、不执行沙箱、不读取密钥、不访问网络、不写生产数据库、不发布；当 `dbPath` 不存在时只返回 `sqlite staging file does not exist`。

Backend Core 本地 SQLite 是真实后端 API MVP 的第一段持久化 staging，可显式执行：

```powershell
curl -X POST http://127.0.0.1:8000/api/backend/core-db/init -H "Content-Type: application/json" -d "{\"coreDbPath\":\"examples/output/backend-core-local.sqlite3\",\"actor\":\"teacher_1\"}"
curl -X POST http://127.0.0.1:8000/api/backend/core-db/sync-local -H "Content-Type: application/json" -d "{\"coreDbPath\":\"examples/output/backend-core-local.sqlite3\",\"actor\":\"teacher_1\"}"
```

它会初始化并同步 `ai_tasks`、`artifacts`、`review_audit_events`、`operation_audit_events`、`platform_entities` 五张核心表，每条记录保留 `raw_json`，用于验证从 JSON store 到数据库的 round-trip 迁移。`GET /api/backend/core-db/summary?coreDbPath=...` 只读返回任务、Artifact、审计和平台实体计数及状态 / 类型分布；文件不存在时不会创建数据库。

同步后，下列核心只读接口可追加 `coreDbPath` 从 Backend Core SQLite staging 读取数据：

```text
GET /api/ai-tasks?coreDbPath=examples/output/backend-core-local.sqlite3
GET /api/ai-tasks/{id}?coreDbPath=examples/output/backend-core-local.sqlite3
GET /api/artifacts?coreDbPath=examples/output/backend-core-local.sqlite3
GET /api/artifacts/{id}?coreDbPath=examples/output/backend-core-local.sqlite3
GET /api/review-audit-events?coreDbPath=examples/output/backend-core-local.sqlite3
GET /api/audit-events?coreDbPath=examples/output/backend-core-local.sqlite3
GET /api/platform-entities?coreDbPath=examples/output/backend-core-local.sqlite3
GET /api/platform-entities/{id}?coreDbPath=examples/output/backend-core-local.sqlite3
```

这些 GET 查询使用 SQLite 只读模式，响应标记 `mode=LOCAL_SQLITE_BACKEND_CORE_READONLY`、`localSqliteRead=true`，文件不存在时返回 `BACKEND_CORE_SQLITE_READONLY_ERROR` 且不会创建数据库。未传 `coreDbPath` 时仍沿用 JSON store。该能力仍只写本地开发 SQLite，不是生产数据库，不提供完整用户权限或生产队列。

Lab / Exam / PPT 生成和 AI Task 审核动作也支持显式 `coreDbPath` 写穿到 Backend Core SQLite staging：

```powershell
curl -X POST http://127.0.0.1:8000/api/labs/generate -H "Content-Type: application/json" -d "{\"input\":\"examples/input/demo-source.md\",\"coreDbPath\":\"examples/output/backend-core-local.sqlite3\"}"
curl -X POST http://127.0.0.1:8000/api/ai-tasks/{taskId}/approve -H "Content-Type: application/json" -d "{\"reviewer\":\"teacher_1\",\"coreDbPath\":\"examples/output/backend-core-local.sqlite3\"}"
```

写穿响应会包含 `backendCoreWriteThrough`，其中 `mode=LOCAL_SQLITE_BACKEND_CORE_WRITE_THROUGH`、`localSqliteWritten=true`，并分别标记 `taskWritten`、`artifactsWritten`、`reviewAuditEventWritten`、`operationAuditEventWritten`。未传 `coreDbPath` 时仍只写 JSON store；该能力用于验证真实后端 repository 写路径，不写生产数据库、不自动审核、不发布。

`backend/core_contract.py` 定义 `BackendCoreRepositoryContract`、`BackendCoreRepositoryConfig`、`BackendCoreRepositoryFactory` 与当前 SQLite adapter；`backend/core_service.py` 依赖 factory + contract，集中处理 `coreDbPath` 解析、SQLite staging 读写、语义化只读查询、只读摘要和写穿摘要；`backend/mock_api.py` 只负责路由和统一 JSON 响应，不直接拼接 Backend Core 表名。`BackendCoreRepositoryFactory` 已提供 adapter registry：默认注册 `sqlite-local`，能够识别 `postgresql` / `mysql` 数据库 URL 并生成脱敏摘要；如果未注册对应真实 adapter，会返回 `BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE`，不会尝试连接外部数据库。`backend/core_postgres_repository.py` 和 `backend/core_mysql_repository.py` 已分别提供 PostgreSQL / MySQL repository adapter 的最小真实 driver 边界，支持 lazy driver import、可注入 connector、schema 初始化、AI Task / Artifact / Review Audit / Operation Audit / Platform Entity round-trip、summary 统计和密钥脱敏错误；默认 HTTP mock 尚不自动注册外部 adapter，部署或测试环境需要显式注册到 factory 后才会连接外部数据库。后续接真实数据库或后端框架时应注册具体 adapter 并配置测试库，而不是继续在路由里追加同义 SQLite helper。

`backend/core_task_service.py` 是替换直接 `JsonTaskStore` 写入的第一条真实后端服务化入口。它只依赖 `BackendCoreRepositoryContract`，支持创建 `WAITING_REVIEW` AI Task、挂接 Artifact、人工 approve / reject、写入 Review Audit 与 Operation Audit；拒绝必须带原因，重复审核会被状态流转阻断。`POST /api/backend/core-tasks` 与 `POST /api/backend/core-tasks/{id}/approve|reject|review` 已接入该服务并返回 `data.backendCoreTaskService`，标记 repository contract、SQLite staging 写入、审核审计和禁止自动发布状态。`GET /api/backend/core-tasks?coreDbPath=...` 与 `GET /api/backend/core-tasks/{id}?coreDbPath=...` 已补齐同一路径下的 repository-backed 只读列表和详情，列表支持 `status`、`taskType` 过滤，并固定 `jsonStoreRead=false`、`productionDatabaseWritten=false`、`realPublish=false`。该服务不会写 JSON store、不自动审核、不发布，后续真实 HTTP/ASGI 路由应继续复用该服务，而不是把任务创建、读取和审核逻辑堆回 router 里。

可通过 `LAB_BACKEND_CORE_REPOSITORY_KIND` 显式声明 repository 类型；显式 `coreDbPath` 只允许 `sqlite-local`。`postgresql` / `mysql` 需要通过 `LAB_BACKEND_CORE_DATABASE_URL` 和已注册 adapter 使用；未注册 adapter 时会返回统一 JSON 错误，不会回退到 JSON store，也不会尝试连接真实数据库。PostgreSQL adapter 的真实运行需要安装 `psycopg[binary]`，MySQL adapter 的真实运行需要安装 `mysql-connector-python`，并且都只应指向测试 / staging 数据库；错误响应只返回 driver 缺失、连接异常类型或脱敏 URL 摘要，不回显账号、密码或完整连接串。

如果不希望每个 Backend Core 请求都显式传 `coreDbPath`，本地开发可设置 `LAB_BACKEND_CORE_DATABASE_URL`：

```powershell
$env:LAB_BACKEND_CORE_DATABASE_URL="sqlite:///./examples/output/backend-core-local.sqlite3"
python -m backend.mock_http_server --host 127.0.0.1 --port 8000
```

随后 `GET /api/backend/core-db/summary`、`POST /api/backend/core-db/init`、核心 GET 只读查询以及 Lab / Exam / PPT / AI Task 审核写穿，在未传 `coreDbPath` 时会默认使用该本地 SQLite staging 文件；请求体或 query 中显式传入 `coreDbPath` 仍然优先。该 URL 入口接受 `sqlite:///...` 作为本地开发默认路径；也能识别 `postgresql://...`、`postgres://...`、`mysql://...` 和 `mariadb://...` 并生成不含 host、账号或密码值的脱敏摘要，但只有注册真实 repository adapter 后才会连接。带 host 的 sqlite URL 仍会返回不支持；错误响应只返回 scheme、结构原因或 adapter 缺失原因，不回显完整 URL，避免泄露账号或密钥。

PostgreSQL 测试库迁移 CLI 用于显式注册 adapter、初始化 Backend Core schema 并读取摘要：

```powershell
$env:LAB_BACKEND_CORE_DATABASE_URL="postgresql://<db_user>:<db_password>@<test-host>:5432/lab_core_staging"
python lab_cli.py backend-core postgresql plan
python lab_cli.py backend-core postgresql init --confirm-test-database
python lab_cli.py backend-core postgresql summary
python lab_cli.py backend-core postgresql smoke --confirm-test-database --reviewer teacher_smoke
```

`plan` 只解析 URL 类型、driver 安装状态和 schema 表清单，固定不访问网络、不写 schema；`init` 必须显式传 `--confirm-test-database`，只用于测试 / staging 数据库 schema 初始化；`summary` 只读取仓储摘要；`smoke` 会在测试库中创建一条 `WAITING_REVIEW` 任务、Artifact、操作审计，再执行人工 approve round-trip，用于真实库 / CI 证据。四个命令都返回统一 JSON，连接串只以 `scheme`、账号/密码是否存在等脱敏摘要呈现，不返回完整 URL。真实执行需要 `requirements.txt` 中的 `psycopg[binary]`，且默认 HTTP mock 仍不会自动连接外部数据库。

MySQL 测试库迁移 CLI 与 PostgreSQL 入口保持一致：

```powershell
$env:LAB_BACKEND_CORE_DATABASE_URL="mysql://<db_user>:<db_password>@<test-host>:3306/lab_core_staging"
python lab_cli.py backend-core mysql plan
python lab_cli.py backend-core mysql init --confirm-test-database
python lab_cli.py backend-core mysql summary
python lab_cli.py backend-core mysql smoke --confirm-test-database --reviewer teacher_smoke
```

该入口只接受 MySQL / MariaDB 测试或 staging URL，`plan` 不联网、不写 schema；`init` 和 `smoke` 需要显式 `--confirm-test-database`。真实执行需要 `requirements.txt` 中的 `mysql-connector-python`，输出同样不回显完整连接串、账号或密码，默认 HTTP mock 仍不会自动注册 MySQL adapter。

真实 PostgreSQL 测试库可选 CI smoke：

```powershell
$env:LAB_BACKEND_CORE_POSTGRESQL_SMOKE="1"
$env:LAB_BACKEND_CORE_DATABASE_URL="postgresql://<db_user>:<db_password>@<test-host>:5432/lab_core_staging"
python -m pytest tests/test_backend_core_postgres_real_smoke.py -q
```

未设置 `LAB_BACKEND_CORE_POSTGRESQL_SMOKE=1` 时该测试会 skip；设置后会真实连接 `LAB_BACKEND_CORE_DATABASE_URL` 指向的测试 / staging 库并写入 smoke 记录。不要把该环境变量指向生产库。

真实 MySQL 测试库也提供可选 smoke：

```powershell
$env:LAB_BACKEND_CORE_MYSQL_SMOKE="1"
$env:LAB_BACKEND_CORE_DATABASE_URL="mysql://<db_user>:<db_password>@<test-host>:3306/lab_core_staging"
python -m pytest tests/test_backend_core_mysql_real_smoke.py -q
```

未设置 `LAB_BACKEND_CORE_MYSQL_SMOKE=1` 时该测试会 skip；设置后会真实连接 `LAB_BACKEND_CORE_DATABASE_URL` 指向的测试 / staging 库并写入 smoke 记录。不要把该环境变量指向生产库。

GitHub Actions 已提供同一 smoke 的临时数据库版本：

```text
.github/workflows/backend-core-postgresql-smoke.yml
```

该 workflow 通过 PostgreSQL 16 service 创建一次性 `lab_core_smoke` 测试库，设置 `LAB_BACKEND_CORE_POSTGRESQL_SMOKE=1` 和临时 `LAB_BACKEND_CORE_DATABASE_URL` 后运行 `tests/test_backend_core_postgres_real_smoke.py`。它不读取仓库 secret、不连接外部数据库、不写生产库；通过后只说明 Backend Core repository contract、PostgreSQL adapter、schema 初始化和审核 round-trip 在临时 CI 数据库中可用。

PR 前核心回归矩阵也已登记为 GitHub Actions：

```text
.github/workflows/core-regression-matrix.yml
```

该 workflow 只调用已有 CLI 入口：

```bash
python lab_cli.py quality regression-matrix --profile core --stop-on-failure --output examples/output/regression-matrix-core.json
```

它会上传 `core-regression-matrix-report` artifact，并在 CLI JSON 返回 `success=false` 时显式失败。该入口不读取仓库 secret、不调用真实 LLM、不连接生产数据库；它只是把本地固定矩阵接到 CI，远端实际运行结果仍需在 workflow 真正执行后记录。

后端最小部署注册清单位于：

```text
backend/deployment.manifest.json
```

该清单登记当前可用的三个后端入口：`python -m backend.mock_http_server --host 127.0.0.1 --port 8000` 本地 HTTP 包装器、`backend.app.BackendApiApp` 框架无关边界、`backend.asgi_app:app` ASGI 挂载点；同时列出 Backend Core / Grading staging 所需环境变量名称、CI smoke workflow、核心回归矩阵 workflow、API 分组和安全停止线。它不是生产 Kubernetes / Docker 部署文件，不开启生产数据库写入、生产队列、公开网络、真实云资源或自动发布。后续接测试环境时应复用 `backend.asgi_app:app` 或 `BackendApiApp`，不要再为相同入口新增同义部署壳。

ASGI 测试环境挂载 smoke：

```powershell
python -m pytest tests/test_backend_asgi_mount_smoke.py -q
python lab_cli.py backend-core asgi-smoke --output examples/output/backend-asgi-smoke-report.json
```

该 smoke 以 in-process ASGI 方式调用 `backend.asgi_app:app`，覆盖 `GET /api/health`、`POST /api/backend/core-db/init`、`GET /api/backend/core-db/summary`、`GET /api/backend/core-readiness`、`GET /api/mcp/server/info`、`POST /api/mcp/server/call` 和最小 Bearer token 鉴权边界。`backend-core asgi-smoke` 会把同一组检查落盘为 JSON evidence，便于本地验收、CI artifact 或测试环境挂载记录复用。它不会启动网络监听、不读取仓库 secret、不连接外部数据库、不写生产库、不调用真实 LLM，也不自动审核或发布。通过该测试只说明当前 ASGI target 已具备测试环境挂载前的核心 API smoke 证据；真实测试环境实际挂载后仍需要记录外部运行结果和平台网关配置。

## 支持接口

```text
GET /api/health
GET /api/backend/core-readiness
GET /api/backend/core-db/summary
POST /api/backend/core-tasks
GET /api/backend/core-tasks
GET /api/backend/core-tasks/{id}
POST /api/backend/core-tasks/{id}/approve
POST /api/backend/core-tasks/{id}/reject
POST /api/backend/core-tasks/{id}/review
GET /api/ai-tasks
GET /api/ai-tasks/{id}
GET /api/review-tasks
GET /api/review-task-summary
GET /api/review-tasks/{id}
GET /api/review-tasks/{id}/core-readiness
GET /api/platform-entities
GET /api/platform-entities/readiness-report
POST /api/platform-entities/contract-validate
GET /api/platform-entities/{id}
POST /api/platform-entities/{id}/import-dry-run
# 以下真实平台对接相关 API 当前暂停，仅作为未来团队技术参考：
# POST /api/platform-entities/{id}/import-send
# POST /api/platform-entities/{id}/import-status
# POST /api/platform-entities/{id}/import-result
# POST /api/platform-entities/{id}/signoff
# POST /api/platform-entities/{id}/final-publish-review-decision
GET /api/review-tasks/{id}/revision-requests
POST /api/review-tasks/{id}/revision-request
POST /api/review-tasks/{id}/regenerate-mock
POST /api/review-tasks/{id}/decision-note
GET /api/review-tasks/{id}/ppt-page-review-status
POST /api/review-tasks/{id}/ppt-page-review-status
GET /api/review-tasks/{id}/second-confirmation-status
GET /api/review-audit-events
GET /api/audit-events
GET /api/artifacts
GET /api/artifacts/{id}
GET /api/providers
GET /api/providers/mock/health
GET /api/provider-audit-events
GET /api/mcp/server/info
GET /api/mcp/server/tools
POST /api/mcp/server/call
POST /api/mcp/intents/publish-lab
POST /api/mcp/intents/publish-exam
POST /api/mcp/intents/destroy-environment
GET /api/workflow-runs
GET /api/workflow-runs/{id}
GET /api/environments
GET /api/environments/{id}
GET /api/workflow/report?file=examples/output/demo-report.json
GET /api/grading/report?file=examples/output/grading-report.json
GET /api/grading/report?file=examples/output/grading-report.json&taskId=task_grading_demo
GET /api/review/real-dsl-preview
POST /api/review/real-dsl-revision
POST /api/review/real-dsl-revision-batch
GET /api/review/real-dsl-revision-diff-preview
POST /api/backend/core-db/init
POST /api/backend/core-db/sync-local
POST /api/review/real-dsl-revision-decision
POST /api/review/real-dsl-revision-promote
POST /api/review/real-dsl-revision-enqueue
POST /api/materials/analyze
POST /api/workflow/demo
POST /api/labs/generate
POST /api/labs/import-preview
POST /api/exams/generate-from-lab
POST /api/exams/import-preview
POST /api/ppt/generate
POST /api/ppt/import-preview
POST /api/ppt/mock-import
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
POST /api/grading/workers/run-once
POST /api/grading/workers/drain-once
GET /api/grading/records
POST /api/grading/records
GET /api/grading/records/{id}
POST /api/grading/records/{id}/review
POST /api/grading/import-preview
POST /api/providers/mock/generate
POST /api/ai-tasks/{id}/approve
POST /api/ai-tasks/{id}/reject
POST /api/environments/vm
POST /api/environments/notebook
POST /api/environments/{id}/start
POST /api/environments/{id}/stop
POST /api/environments/{id}/reset
```

Workflow Demo 请求体：

```json
{
  "input": "examples/input/demo-source.md",
  "reviewer": "teacher_1"
}
```

Workflow Demo 输出会包含 `report`、`createdTasks`、`reviewRequired=true`、`publishBlockedUntilApproved=true`、`sandboxExecuted=false`。其中 Lab、Exam、Grading、PPT 四类生成任务都会写入本地 Mock store，状态为 `WAITING_REVIEW`。
同时会写入本地 Workflow Run 记录，可通过 `GET /api/workflow-runs` 或 `GET /api/workflow-runs/{id}` 查询步骤日志和 traceId。

素材分析请求体：

```json
{
  "input": "examples/input/demo-source.md"
}
```

素材分析只读取本地文本素材，输出 `analysis`，固定 `realLlmCalled=false`、`remoteContentFetched=false`、`unknownShellExecuted=false`、`sandboxExecuted=false`。

评分 evidence 合并请求体：

```json
{
  "reports": [
    "examples/output/readonly-sandbox-report.json",
    "examples/output/controlled-command-sandbox-report.json"
  ],
  "output": "examples/output/merged-evidence-report.json",
  "taskId": "<grading_task_id>"
}
```

`POST /api/grading/evidence-merge` 只读取已有本地 JSON 报告并写出 `GRADING_EVIDENCE_MERGE_REPORT`、操作审计和 `GRADING_REPORT` Artifact；它不读取 submission、不启动 Docker、不执行 pytest/Notebook/命令、不调用真实 LLM、不自动审核、不发布。若提供 `taskId`，合并报告会归属到该审核任务，并可在 `GET /api/review-tasks/{id}` 的 `mergedGradingEvidence` 中展示。

自动评分 evidence 请求体：

```json
{
  "grading": "templates/grading/examples/mixed-checks.yaml",
  "submission": "examples/submissions/readonly-demo",
  "output": "examples/output/grading-evidence-auto.json",
  "taskId": "<optional_grading_task_id>",
  "includeControlledCommand": false,
  "failOnControlledUnavailable": false,
  "image": "ai-grading-python:0.1"
}
```

`POST /api/grading/evidence-auto` 编排已有只读 evidence、可选受控 Docker evidence 和 evidence merge 能力，写出 `GRADING_EVIDENCE_AUTO_REPORT`、操作审计和 `GRADING_REPORT` Artifact；默认只运行只读证据收集，不执行选手命令。只有 `includeControlledCommand=true` 时才尝试受控 Docker 命令证据，Docker 不可用时默认降级为 warning 并保留只读报告；传 `failOnControlledUnavailable=true` 时才把该情况作为失败返回。报告会返回 `executionMatrix`，按 check 展示只读 evidence、受控命令 evidence、最终选用 evidence、缺口和建议下一步；同时返回 `scorePreview`，只基于 `executionMatrix.selectedEvidence` 计算 `earnedScore`、`totalScore`、`coveredScore`、`missingScore`、覆盖率、通过率和 `readyForDecisionNote`，用于人工评分复核，不会自动通过或发布；还会返回 `nextCoreAction`，在缺受控命令证据时指向带 `includeControlledCommand=true` 的重跑入口，证据齐全时指向记录人工审核 decision note。报告还会返回 `manualReviewChecklist`，把每个 check 的 `recommendedReviewAction`、`recommendedDecision`、`readyForDecision` 和总体 `decisionNoteRecommendation` 固定化，便于审核中心和评分报告页直接提示下一条人工结论；并返回 `gradingDslCoverageSummary`，汇总 Grading DSL checks 与 evidence 覆盖关系、缺失 check、受控命令缺口、下一步动作和人工 decision note 建议。报告新增只读 `reviewerSafetySummary`，把分数预览、证据覆盖、受控容器执行状态、阻断原因和下一条人工动作折成审核员可读摘要；该摘要会写入操作审计和 Artifact metadata，但不新增门禁、不自动审核、不改变 evidence 收集策略。该清单仍固定 `autoApproveAllowed=false`、`autoPublishAllowed=false`、`realPublishAllowed=false`。若提供 `taskId`，自动报告会归属到该审核任务，并可在 `GET /api/review-tasks/{id}` 的 `mergedGradingEvidence.latestReportType=GRADING_EVIDENCE_AUTO` 与 `GET /api/grading/report?file={file}&taskId={id}.autoGradingEvidenceSummary` 中展示。该接口不调用真实 LLM、不自动审核、不发布。

评分任务请求体与 `evidence-auto` 类似，另需 `submissionId`：

```json
{
  "grading": "templates/grading/examples/mixed-checks.yaml",
  "submission": "examples/submissions/readonly-demo",
  "output": "examples/output/grading-job-evidence-auto.json",
  "submissionId": "submission_001",
  "taskId": "<optional_grading_task_id>",
  "candidateId": "candidate_001",
  "reviewer": "teacher_1"
}
```

`POST /api/grading/jobs` 创建本地 `QUEUED` 评分任务；`POST /api/grading/jobs/{id}/run` 或 `POST /api/grading/jobs/run` 同步执行本地 job，复用 `evidence-auto` 生成报告并派生 `GradingRecord`，job 最终进入 `WAITING_REVIEW`。`backend/grading_job_service.py` 已承接创建、同步运行、JSON/SQLite staging 写入、报告 artifact 和操作审计，`backend/mock_api.py` 只保留 HTTP payload / response 适配。默认仍写本地 JSON store；当设置 `LAB_BACKEND_GRADING_DB_PATH` / HTTP `--grading-db` 或请求显式传 `dbPath` 时，会把 job 写入本地 SQLite，执行、查询和列表接口也从同一 SQLite 读取并写回 job / record，同时镜像到 JSON store 供审核详情聚合。显式 `dbPath` 优先于后端默认路径，响应会返回 `dbPathSource`。SQLite 执行请求可选 `leaseSeconds` 和 `maxAttempts`，用于设置单次领取租约时长和本地重试上限，非法值会返回统一 JSON 参数错误。`POST /api/grading/workers/drain-once` 会在同一 SQLite 上按 `limit` 顺序执行最多 20 个可运行 job，遇到空队列或单个 job 失败即停止并返回 `workerDrain` 摘要；`workerDrain.quota` 标记本次是否触顶、是否可能还有可运行 job，`workerDrain.resourceCleanup` 记录本地报告和评分记录保留情况，批次级 `operationAuditEvent.action=GRADING_WORKER_DRAIN` 可用于审计。它不启动常驻后台 worker 或并发 worker。该能力是未来真实任务队列和数据库入库的 staging 替身，当前固定 `databaseWritten=false`、`productionDatabaseWritten=false`、`queuePersistedToProduction=false`、`autoApproveAllowed=false`、`realPublish=false`。

评分记录请求体：

```json
{
  "report": "examples/output/grading-evidence-auto.json",
  "submissionId": "submission_001",
  "candidateId": "candidate_001",
  "taskId": "<optional_grading_task_id>",
  "reviewer": "teacher_1"
}
```

`POST /api/grading/records` 只从已有评分报告派生本地 `GradingRecord`，模拟未来 `grading_record` 表的最小记录，保存 submissionId、candidateId、reportPath、得分、覆盖率、evidence 摘要、人工复核状态和固定安全标记。`backend/grading_record_service.py` 已承接记录创建、人工复核、JSON/SQLite staging 写入和 `GRADING_RECORD_CREATE` / `GRADING_RECORD_REVIEW` 操作审计，`backend/mock_api.py` 只保留 HTTP payload / response 适配。它不重新评分、不启动 Docker、不执行选手代码、不改变 AI Task 状态、不自动通过、不发布。`GET /api/grading/records` 可按 `submissionId`、`candidateId`、`taskId`、`status` 查询，`GET /api/grading/records/{id}` 查询单条记录。`POST /api/grading/records/{id}/review` 只记录人工复核结论，`decision` 支持 `approve-ready`、`needs-evidence`、`needs-revision`，后两者必须提供 `reason`；该接口只更新本地评分记录和审计，不改变 AI Task 状态、不重新执行沙箱、不发布。审核详情会在 `gradingRecords.reviewIntegration` 中汇总最新记录是否已人工复核为 `approve-ready`，`core-readiness` 在已有评分记录时会把该结论作为平台复核前的只读步骤。默认仍写入本地 JSON store；当设置 `LAB_BACKEND_GRADING_DB_PATH` / HTTP `--grading-db` 或请求显式传 `dbPath` 时，创建和复核会写入本地 SQLite 并镜像回 JSON store 供审核详情聚合；响应固定 `databaseWritten=false`、`productionDatabaseWritten=false`。

`backend.grading_repository.GradingSQLiteRepository` 提供本地 SQLite 评分仓储草案，用于把当前 JSON store 中的 `GradingJob` / `GradingRecord` 同步到 `grading_jobs` / `grading_records` 表，验证未来真实后端数据库表字段、索引和 round-trip 读写。CLI 入口为 `grade db-init`、`grade db-sync-local`、`grade db-summary`、`grade worker-run-once`、`grade worker-drain-once`，以及显式 `--db-path` 的 `grade job-create/job-run/job-list/job-get`；HTTP mock API 入口为 `POST /api/grading/db/init`、`POST /api/grading/db/sync-local`、`POST /api/grading/workers/run-once`、`POST /api/grading/workers/drain-once`，以及 `LAB_BACKEND_GRADING_DB_PATH` / `--grading-db` / 显式 `dbPath` 的 `/api/grading/jobs` 创建、查询和运行。`worker-run-once` 会先回收本地 SQLite 中过期的 `RUNNING` claim：未达 `maxAttempts` 的任务回到 `QUEUED`，达到上限的任务转为 `FAILED` 并写入 `GRADING_JOB_RETRY_LIMIT_EXCEEDED`；随后再用 `claimOwner`、`claimedAt`、`claimExpiresAt`、`attemptCount` 字段领取一个 `QUEUED` / `FAILED` job 并标记为 `RUNNING`，同步执行一次，执行后把 job / record 镜像回 JSON store 供审核详情读取。`worker-drain-once` 只是对单次 worker 做有限循环，`limit` 默认 5、最大 20，顺序执行，返回 quota、资源保留计划和批次审计，不启动常驻后台 worker 或并发 worker。该仓储只写开发机本地 SQLite 文件，固定 `localSqliteOnly=true`、`claimLeaseEnabled=true`、`expiredClaimRecoveryEnabled=true`、`singleProcessSequentialDrain=true`、`quotaEnforced=true`、`resourceCleanupPlanned=true`、`persistentBackgroundWorker=false`、`productionDatabaseWritten=false`、`productionQueueUsed=false`、`autoApproveAllowed=false`、`realPublish=false`。

审核动作请求体：

```json
{
  "reviewer": "teacher_1",
  "reason": "驳回时必填"
}
```

审核动作会写入本地审计事件，可查询：

```text
GET /api/review-audit-events?taskId=<task_id>
GET /api/review-audit-events?action=APPROVE
GET /api/review-audit-events?actor=teacher_1
GET /api/review-task-summary?status=WAITING_REVIEW
GET /api/providers/real-llm-runtime-config
GET /api/review/real-dsl-preview
POST /api/review/real-dsl-revision
POST /api/review/real-dsl-revision-batch
GET /api/review/real-dsl-revision-diff-preview
POST /api/review/real-dsl-revision-decision
POST /api/review/real-dsl-revision-promote
POST /api/review/real-dsl-revision-enqueue
GET /api/review-tasks/<task_id>
```

审计事件固定为 `mode=MOCK_ONLY`，`realPublish=false`。
`POST /api/ai-tasks/{id}/approve` 对 Grading 任务会在返回体和 `operationAuditEvent.detail` 附带只读 `preApproveReviewCheck`，汇总 `mergedGradingEvidence`、`scorePreview` 和 `reviewDecisionNotes` 是否存在，并要求 latest decision note 为 `approve-ready` 才返回 `approveReadyDecision=true` / `READY_FOR_HUMAN_APPROVE`；当 `scorePreviewReadyForDecisionNote=false` 时会追加 `grading_score_preview_not_ready_for_decision_note` warning，`needs-revision` / `needs-evidence` 也会保留 warning。该检查只提示审核人，不阻断人工通过、不自动通过、不批量改状态、不发布。

`GET /api/review-tasks/{id}` 会返回 `reviewDetail`，聚合 AI Task、Artifact、Workflow Step、审核审计、统一操作审计、Provider 调用审计、`reviewPolicy` 和安全标记，用于人工审核详情页。真实 LLM 任务会在 `reviewDetail.reviewPage.providerSummary.qualitySummary` 与 `calls[*].qualitySummary` 展示 Provider / Schema 层质量摘要，包括 `readyForReview`、归一化 patch 数、Schema 修复状态、请求次数、API surface 和 response id；同时会在 `reviewDetail.contentQualitySummary` 与 `reviewDetail.reviewPage.contentQualitySummary` 展示内容层质量摘要，包括 Lab 目标/步骤、Exam 分值、Grading gradingRef 覆盖和 assessmentPlan 对齐、PPT 页数，以及 Lab / Exam / Grading 是否可进入导入预览。`reviewDetail.reviewPage.dslPreview` 会读取本地 DSL 文件并返回只读真实产物摘要：`contentLoaded`、`schemaKind`、`schemaValidated`、`documentKind`、`documentStatus`、`title`、`summary` 和 `safePreview`；Lab 展示步骤/目标/环境摘要，Exam 只展示候选安全题目摘要并标记 `answerVisibleToCandidate=false`、`gradingRefVisibleToCandidate=false`，Grading 展示 checks / assessmentPlan / 沙箱前置摘要，PPT 展示 slide 数和标题摘要。该预览只读本地文件，不读取密钥、不访问网络、不执行沙箱、不自动审核、不发布。内容质量摘要还会返回 `decisionStatus`、`recommendedAction`、`requiresRevisionBeforeImportPreview`、`requiresEvidenceBeforeFinalApproval`、`blockers` 和 `warnings`，用于明确区分可进入导入预览、带警告复核、需先修订、Grading 需先补 evidence 等人工下一步。这些字段只辅助人工审核，不改变 `WAITING_REVIEW` 和禁止自动发布边界。对包含 Lab / Exam / Grading DSL 的任务，`reviewDetail.platformImportPreviewActions` 与 `reviewDetail.reviewPage.platformImportPreviewActions` 会展示 `PlatformImportPreviewActionPanel`，列出可用的 CLI、Backend API 和 MCP Tool 导入预览入口，并透出 `contentQualityReadyForImportPreview`、`contentQualityRecommendedAction`、ready/blocked 统计和 blocking issue 数；这些质量字段是建议层，任务仍必须先 `APPROVED` 才能生成本地导入预览。任务未 `APPROVED` 时入口可见但禁用，审核通过后可用于生成本地导入预览。任务已生成 Lab / Exam / Grading 平台导入预览时，`reviewDetail.platformImportPreview` 与 `reviewDetail.reviewPage.platformImportPreview` 会统一展示 `PlatformImportPreviewSummary`，包含平台实体草稿、源 DSL、导入计划、操作审计引用和固定 `databaseWritten=false` / `realPublishAllowed=false` 标记；其中 Grading 规则预览会透出 `controlledEvidenceNextAction`，把最终导入复核前的评分 evidence 下一步指向 `POST /api/grading/evidence-auto`。`reviewDetail.platformImportPreviewSignoff` 与 `reviewDetail.reviewPage.platformImportPreviewSignoff` 会进一步展示 `PlatformImportPreviewSignoffChecklist`，用于人工确认已生成预览是否可签收，以及哪些实体仍缺导入预览；当签收项包含 Grading 规则时，它会附带只读 `preApproveReviewCheckSummary`、`gradingEvidenceReportSummary`、`controlledEvidenceNextAction`、`confirm_pre_approve_review_check_before_grading_rule_import`、`confirm_grading_evidence_report_before_grading_rule_import` 和 `confirm_controlled_grading_evidence_next_action_before_platform_import` 人工确认项，提示最新 `GRADING_EVIDENCE_AUTO` / merge 报告、evidence 与 latest `approve-ready` 决策是否满足，但不改变 `readyForHumanSignoff`、不触发真实平台导入、不写库、不发布。当 Grading 任务关联受控 Docker plan/report Artifact 时，`reviewDetail.controlledGradingEvidence` 与 `reviewDetail.reviewPage.controlledGradingEvidence` 会展示 `CONTROLLED_DOCKER_GRADING_PLAN`、`CONTROLLED_DOCKER_SANDBOX_RUN`、executed/passed、得分、reportDetail 摘要和 `networkEnabled=false` 等安全标记；当任务关联 `GRADING_EVIDENCE_MERGE` 或 `GRADING_EVIDENCE_AUTO` 报告时，`reviewDetail.mergedGradingEvidence` 与 `reviewPage.mergedGradingEvidence` 会展示最新证据报告路径、报告类型、check 级人工复核项、覆盖率和安全摘要。它们只作为人工审核证据，不自动通过、不发布。

`GET /api/review-tasks/{id}/core-readiness` 会返回只读 `CoreWorkflowReadinessReport`，把任务审核状态、内容质量摘要、平台实体 readiness、`platformImportPreviewActions` 和 Grading `preApproveReviewCheck` 汇总为单任务核心闭环步骤。Lab 任务只检查 `lab_template`，Exam 组合任务检查 `exam_question` 与 `grading_rule`，Exam 修订任务只检查本次修订的 `exam_question`，Grading / Grading 修订任务会先检查 evidence、decision note、`manualReviewChecklistStatus`、`decisionNoteRecommendation` 和 `approve-ready` 决策，再检查 `grading_rule` 导入步骤；若本地 `GradingRecord` 已存在，会额外检查最新记录是否经人工 `record-review approve-ready`，未通过时以 `toolAvailable=false` 和 `cliCommand=python lab_cli.py grade record-review ...` 推荐人工复核，没有评分记录时不阻断 Grading DSL 导入预览。平台实体 readiness 也会在 `grading_rule` item 下返回 `gradingRecordReviewEvidence`，把该评分记录复核状态作为平台复核前证据，并在 summary 中统计 ready / blocked 数；该 evidence 不自动签收、不自动发布。当 `contentQualitySummary` 判定 `NEEDS_REVISION_BEFORE_IMPORT_PREVIEW` 或存在 blocked import preview kind 时，`contentQualityReadiness.readyForImportPreview=false`，`recommendedNextAction=request_content_revision_before_import_preview`，`nextToolRecommendation.reasonCode=CONTENT_QUALITY_REVISION_REQUIRED`，优先建议审核人记录 `review revision-request`，不会先建议人工 approve 或导入预览。`summary.finalReviewState` 与 `nextToolRecommendation.finalReviewState` 会统一返回 `READY_FOR_HUMAN_APPROVE`、`NEEDS_MORE_EVIDENCE`、`NEEDS_REVISION`、`WAITING_DECISION_NOTE`、`WAITING_EVIDENCE` 或 `NOT_GRADING_REVIEW`。当任务已审核但还没有生成导入预览时，`platformImportPreviewActionSummary` 会列出 pending 的平台实体、预览组件、下一步动作和 CLI 命令，帮助审核员直接执行 `lab/exam/grade import-preview`。`nextToolRecommendation` 会基于第一个 blocked step 给出只读下一步建议，可能指向 `create_*_import_preview`、`run_grading_evidence_auto`、人工 `grade record-review`、平台导入 dry-run/status/result 工具，或人工审核/修订/签收动作，但固定 `autoExecuteAllowed=false`，不会由 readiness 接口自动调用后续工具。当最新 `GRADING_EVIDENCE_AUTO` 报告建议 `needs-evidence` 时，`recommendedNextAction` 会优先指向补 evidence / 记录对应 decision note，而不是继续推进平台草稿。该接口不执行导入、不发送请求、不启动沙箱、不自动 approve、不发布，固定 `readOnly=true`、`networkAccess=false`、`autoPublishAllowed=false`、`realPublish=false`。
`POST /api/phase2/workflows/content-generation/run` 默认仍以 `artifactProfile=legacy-all` 兼容创建 Lab / Exam / Grading / PPT 四类 `WAITING_REVIEW` 审核包；显式传 `artifactProfile=teaching-core` 时只生成 Lab / Exam / Grading，返回候选人安全 Exam 预览和 `TeachingPackageGenerationSummary`，不创建 PPT 任务或 Artifact。请求体可传 `providerMode=real-llm`、`model`、`baseUrl`、`maxOutputTokens`、对应 `realLlm*Output` 路径和显式确认项 `explicitRealCallOptIn=true`、`confirmRealDsl=true`、`confirmWaitingReview=true`、`confirmNoAutoPublish=true`；`teaching-core` 真实模式只发送三类请求。非法 profile、Provider/Schema 失败或候选预览脱敏失败均不创建可审核任务。可选 `repairOnSchemaFailure=true` 会在某一类 DSL Schema 校验失败时最多追加一次真实修复请求；结果仍为 `WAITING_REVIEW`，不会自动发布、不会执行沙箱、不会生成真实 PPTX。
`GET /api/providers/real-llm-runtime-config` 返回只读 `realLlmRuntimeConfig` 摘要，用于演示前确认当前 shell 是否设置 `OPENAI_API_KEY`、`OPENAI_MODEL` 和 `OPENAI_BASE_URL`；Base URL 只返回 scheme/path 形状，主机名和命令模板中的 endpoint 均使用脱敏占位符。该接口不返回 API Key 值、不导入 SDK、不创建 client、不发起网络请求、不创建任务或产物。
审核人可通过 `POST /api/review-tasks/{id}/revision-request` 记录修改/再生成意见，字段包括 `reviewer`、`comment`、可选 `priority`、`targetSections` 和 `requestedChanges`。该接口只写入 `REVIEW_REVISION_REQUEST` 操作审计，任务状态保持 `WAITING_REVIEW`，`reviewDetail.revisionRequests` 和 `reviewDetail.reviewPage.revisionRequests` 会聚合展示历史意见；`GET /api/review-tasks/{id}/revision-requests` 可单独查询列表。该能力不触发真实 LLM、不自动通过、不真实发布。
`POST /api/review-tasks/{id}/regenerate-mock` 会读取最近一条或指定 `revisionRequestId` 的修改意见，优先按源任务 `finalResultPath` 选择主 DSL Artifact 生成本地修订版 DSL，创建新的 `WAITING_REVIEW` 修订任务，并写入 Artifact、Workflow Run 和 `REVIEW_MOCK_REGENERATE` 操作审计；修订任务会写入独立的内容质量摘要，`core-readiness` 对新任务会优先停在人工审核，而不是继续继承源任务的旧内容质量阻塞；源任务状态不变，不新增真实 LLM 请求、不自动通过、不真实发布。
`POST /api/review-tasks/{id}/decision-note` 会记录审核人基于 `reviewDetail.mergedGradingEvidence.reviewDecisionHints` 的本地判断，请求体包含 `reviewer`、`decision=approve-ready|needs-revision|needs-evidence` 和可选 `reason`；`needs-revision` / `needs-evidence` 必填原因。接口写入 `REVIEW_DECISION_NOTE` Artifact 和 `REVIEW_DECISION_NOTE_RECORD` 操作审计，并在 `reviewDetail.reviewDecisionNotes` / `reviewDetail.reviewPage.reviewDecisionNotes` 中展示历史记录；它不会改变任务状态、不自动通过、不批量改状态、不发布。
当最新 `GRADING_EVIDENCE_AUTO` 报告包含 `scorePreview` 与 `manualReviewChecklist.decisionNoteRecommendation` 时，`reviewDetail.preApproveReviewCheck.summary` 和 `GET /api/review-tasks/{id}/core-readiness.summary` 会透出 `scorePreviewStatus`、预览得分、覆盖分、缺失分、`scorePreviewReadyForDecisionNote`、`decisionNoteRecommendation`、`decisionNoteRecommendationReason`、`manualReviewChecklistStatus` 和 `nextDecisionNoteAction`，供审核中心默认高亮建议按钮并填入 reason；该建议只减少人工选择成本，不会自动提交 decision note。
当任务关联 `PPTX_FILE` 时，`reviewDetail.pptPageReview` 和 `reviewDetail.reviewPage.pptPageReview` 会返回逐页审核模型，包含 `pageReviewSummary`、`slideReviews`、人工批注、QA 信号和 `operatorDecision.autoApproveAllowed=false`；`GET /api/review-tasks/{id}/ppt-page-review-status` 可单独只读查询该模型。`POST /api/review-tasks/{id}/ppt-page-review-status` 只写本地单页审核状态和 `PPT_PAGE_REVIEW_UPDATE` 操作审计，`REVISE_REQUIRED` 必须填写 `comment`，不改变 AI Task 总状态、不自动通过、不真实发布。
当任务关联 `GRADING_DSL` 时，`reviewDetail.assessmentPlan` 和 `reviewDetail.reviewPage.assessmentPlan` 会返回评分计划审核模型，包含 `summary.planTotal`、`checkIds`、`runnerTypes`、`executionStrategies`、`mockEvidenceStatuses`、`riskLevels`、`requiredLimits` 和完整 `items`。该模型优先来自 artifact metadata 中的 `workflowQualitySignals.grading.assessmentPlan`，缺失时兜底读取 Grading DSL 的 `spec.assessmentPlan`；同时 `reviewDetail.assessmentPlan.manualReviewChecklist` 和 `reviewDetail.reviewPage.assessmentPlanManualReviewChecklist` 会返回五项人工复核清单：确认评分计划与 checks 对齐、Mock 证据未采集、真实沙箱证据前置、执行限制完整、未执行也未发布。该清单只做人工审核提示，固定 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`、`realSandboxRunEnabled=false`、`realPublishAllowed=false`，不执行沙箱或选手代码。
`GET /api/review-task-summary` 会返回待审核队列摘要、`providerQualityTaskSignal` Provider 质量聚合、`reviewPriorityQueue` 审核优先队列、`realDemoReviewQueue` 真实演示产物审核摘要、`controlledDockerEvidenceReviewSignal` 受控容器证据覆盖信号、`gradingEvidenceReadinessSignal` 评分证据就绪度聚合、`notebookEvidenceReviewPlan` Notebook 缺口审核计划和批量动作策略；优先队列会按 `status`、`taskType`、`limit` 过滤后的审核详情派生 `priority`、`reasonCode`、`recommendedAction`、评分计划/候选预览/质量信号摘要，仍只用于人工审核排序。`providerQualityTaskSignal` 与队列项 `providerQualitySummary` 均来自 `reviewDetail.reviewPage.providerSummary.qualitySummary` 和 `calls[].qualitySummary`，用于展示真实 LLM 产物是否 `readyForReview`、归一化 patch 数、Schema 修复状态、请求数、token 数和 response id；Mock 任务会返回 `available=false` 的稳定结构。评分任务的队列项还会返回 `manualReviewChecklistSummary`，从 `reviewDetail.assessmentPlan.manualReviewChecklist` 折叠出 `checklistTotal`、`matchedTotal`、`needsHumanReviewTotal`、`nextReviewChecklistIds` 和人工决策边界；若评分任务已有关联受控 Docker evidence，队列项会追加 `controlledGradingEvidenceSummary`，并把 `reasonCode` 切换为 `CONTROLLED_DOCKER_EVIDENCE_REVIEW_REQUIRED`；若已有合并 evidence，队列项还会追加 `gradingEvidenceReadinessSummary`，从 `mergedGradingEvidence.checkEvidenceReviewItems` 派生 `evidenceReadyTotal`、`missingEvidenceTotal`、受控命令缺口、只读静态缺口、下一步证据动作和 `GradingEvidenceActionGuide`。Action Guide 只提示审核员使用既有 `POST /api/grading/evidence-auto` / `grade evidence-auto`、打开最新评分报告并记录 decision note，不自动审核、不自动发布。`realDemoReviewQueue` 优先从本地 `examples/output/real-llm-*.json` 和 PPTX artifact 派生 `localArtifactTotal` / `schemaValidatedTotal`，并用 `finalResultPath` 把产物绑定到最新 `WAITING_REVIEW` 任务，返回 `dynamicTaskAvailable`、`dynamicTaskId` 和 `fallbackTaskId`；找不到动态任务时仍展示 `real_demo_*` 只读占位产物，但前端不会尝试加载不存在的详情。`controlledDockerEvidenceReviewSignal` 会优先从 `reviewDetail.controlledGradingEvidence` 生成动态摘要，`sourceMode=DYNAMIC_CONTROLLED_DOCKER_EVIDENCE`，并包含真实 plan/report 路径、`planTotal`、`reportTotal`、covered check ids/types、executed/passed 和得分；若当前队列没有动态 evidence，则 `sourceMode=STATIC_DEMO_FALLBACK`，回退为固定演示摘要：`check_q1` / `check_q4` 已有 `stdout_contains` / `pytest` 覆盖并得到 `40/40`，`check_q2` / `check_q3` 仍是 `notebook_cell` 人工审核缺口。`notebookEvidenceReviewPlan` 则把这两个缺口展开成只读审核计划，列出 `verify_notebook_cell_targets`、`verify_expected_output_tokens`、`confirm_notebook_execution_requires_sandbox` 和 `confirm_no_notebook_kernel_started`。这些字段都只读展示，不创建任务、不运行容器、不启动 Notebook kernel、不执行 pytest、不自动通过、不发布。Phase 1/Mock 路径中批量 approve/reject/publish 均为禁用，`providerQualityTaskSignal.autoApproveAllowed=false`、`reviewPriorityQueue.summary.autoApproveAllowed=false`、`gradingEvidenceReadinessSignal.safety.sandboxExecutedByReadiness=false`、`batchStateChangeAllowed=false`，`realDemoReviewQueue.realPublishAllowed=false`，`controlledDockerEvidenceReviewSignal.realPublishAllowed=false`，`notebookEvidenceReviewPlan.safety.notebookExecuted=false`。
`GET /api/review/real-dsl-preview` 会读取本地真实 LLM 产物 `examples/output/real-llm-lab.json`、`real-llm-exam.json`、`real-llm-grading.json`、`real-llm-ppt.json` 和候选人安全预览，使用与 `lab_cli.py review real-dsl-preview` 相同的 builder 返回 `realDslReviewPreview`。该接口可通过 query 覆盖 `lab`、`exam`、`grading`、`ppt`、`candidatePreview` 路径；它只做本地 DSL Schema 校验、审核摘要聚合、确定性 `qualitySignals`、`reviewIssues` 和 `revisionSuggestions` 生成，不新增 LLM 请求、不读取密钥、不访问网络、不创建任务、不执行命令、不自动通过、不发布。
`POST /api/review/real-dsl-revision` 会基于本地真实 DSL 和人工修改意见生成 `WAITING_REVIEW` 修订草稿与 revision report。请求体包含 `kind`、`reviewer`、`comment`，可选 `source`、`targetSections`、`requestedChanges`、`output`、`reportOutput`；默认 `providerMode=local`，只做本地确定性修订草稿，不新增 LLM 请求、不读取密钥、不访问网络。传 `providerMode=real-llm` 并显式提供 `explicitRealCallOptIn=true`、`confirmWaitingReview=true`、`confirmNoAutoPublish=true` 后，会复用 OpenAI-compatible SDK 发起一次真实二次修订请求；`model` 可省略并从 `OPENAI_MODEL` 读取，`baseUrl` 可省略并从 `OPENAI_BASE_URL` 读取。输出仍为 `WAITING_REVIEW`，不创建正式审核通过状态、不自动发布。
`POST /api/review/real-dsl-revision-batch` 会读取 `RealDslReviewPreview.revisionSuggestions`，按建议的 `kind` 与 `targetSection` 生成多份本地 `WAITING_REVIEW` 修订草稿和 `realDslRevisionBatch` 报告。请求体包含 `reviewer`，可选 `preview`、`outputDir`、`reportOutput`；该接口只做本地确定性修订，不新增 LLM 请求、不读取密钥、不访问网络、不执行沙箱、不自动通过、不发布。
`GET /api/review/real-dsl-revision-diff-preview` 会读取 `RealDslRevisionBatch` 报告、源 DSL 和修订 DSL，返回 `realDslRevisionDiffPreview`，包含 `summary.diffTotal`、`draftDiffs[].fieldDiffs`、源值摘要、修订值摘要与审核建议。可通过 query 参数 `batchReport` 覆盖批量报告路径，可选 `output` 写入本地预览文件；该接口不新增 LLM 请求、不读取密钥、不访问网络、不执行沙箱、不自动通过、不发布。
`POST /api/review/real-dsl-revision-decision` 会读取 `RealDslRevisionDiffPreview`，按 `suggestionId` 记录审核人的 `approve`、`reject` 或 `request-change` 决策，并写入 `realDslRevisionDecision` 报告。请求体包含 `suggestionId`、`reviewer`、`decision`，可选 `diffPreview`、`reason`、`output`；`reject` 和 `request-change` 必须填写 `reason`。`approve` 只表示该修订可进入后续手动合并，接口不会修改源 DSL 或修订 DSL，不创建发布态，不新增 LLM 请求、不读取密钥、不访问网络、不执行沙箱、不自动通过、不发布。
`POST /api/review/real-dsl-revision-promote` 会读取 `RealDslRevisionDecision` 报告，仅允许 `decision=approve` 且 `decisionStatus=REVISION_APPROVED_FOR_MANUAL_MERGE` 的修订被复制为新的 `WAITING_REVIEW` 候选 DSL，并写入 `realDslRevisionPromotion` 报告。请求体包含 `reviewer`，可选 `decisionReport`、`output`、`reportOutput`；该接口不会修改源 DSL 或修订 DSL，不创建已通过状态，不新增 LLM 请求、不读取密钥、不访问网络、不执行沙箱、不自动通过、不发布。
`POST /api/review/real-dsl-revision-enqueue` 会读取 `RealDslRevisionPromotion` 报告，把已提升的 `WAITING_REVIEW` 候选 DSL 创建为本地 AI Task、DSL Artifact、Workflow Run 和操作审计事件，并返回 `promotionReviewQueueItem` 与 `reviewDetail`。请求体包含 `reviewer`，可选 `promotionReport`；入队后可通过 `GET /api/ai-tasks?status=WAITING_REVIEW`、`GET /api/review-tasks/{id}` 或 MCP `enqueue_real_dsl_revision_candidate_review` 继续人工审核。该接口不新增 LLM 请求、不读取密钥、不访问网络、不执行沙箱、不自动通过、不发布。
`POST /api/labs/import-preview` 会读取已 `APPROVED` 的 Lab DSL 任务和它关联的 `LAB_DSL` Artifact，重新执行 Lab Schema 校验后生成本地 `LabTemplateImportPreview`、`WORKFLOW_REPORT` Artifact 和 `LAB_TEMPLATE_IMPORT_PREVIEW` 操作审计。请求体包含 `taskId`、`reviewer`，可选 `output`；返回 `data.labTemplateImportPreview`、`artifact` 和 `operationAuditEvent`。该接口只生成平台 `lab_template` 草稿导入预览，固定 `databaseWritten=false`、`realPlatformImport=false`、`realPublishAllowed=false`，不会写真实数据库、调用真实平台导入 API 或发布实验。
`POST /api/exams/import-preview` 和 `POST /api/grading/import-preview` 读取已 `APPROVED` 的任务及其 `EXAM_DSL` / `GRADING_DSL` Artifact，重新执行 Schema 校验后分别生成本地 `ExamQuestionImportPreview` / `GradingRuleImportPreview`、`WORKFLOW_REPORT` Artifact 和操作审计。请求体包含 `taskId`、`reviewer`，可选 `output`；它们只生成平台 `exam_question`、`grading_rule` 草稿导入预览，固定 `databaseWritten=false`、`realPlatformImport=false`、`realPublishAllowed=false`。Exam 预览保持 `answerVisibleToCandidate=false`，Grading 预览保持真实沙箱执行前复核要求，不写库、不执行评分、不发布。
`POST /api/labs/mock-import`、`POST /api/exams/mock-import` 和 `POST /api/grading/mock-import` 要求对应任务已 `APPROVED` 且已经生成导入预览，然后把预览中的实体草稿写入本地 JSON store 的 `platformEntities`，返回 `data.platformEntityMockImport`、`platformEntityRecord`、`artifact` 和 `operationAuditEvent`。该步骤只表示本地 Mock 平台草稿入库，固定 `mockStoreWritten=true`、`databaseWritten=false`、`realPlatformImport=false`、`realPublish=false`；可通过 `GET /api/platform-entities?sourceTaskId=<task_id>` 或 `GET /api/platform-entities/{id}` 查询。`backend/platform_entity_service.py` 已承接平台实体列表、详情、`platformEntityImportActivity`、`readiness-report` 只读查询、`contract-validate` 和当前本地闭环使用的 `import-dry-run`；`import-send` / `import-status` / `import-result` 仅作为未来真实平台对接技术参考保留。HTTP 路由只做统一 JSON response 适配。`GET /api/review-tasks/{id}` 会在 `platformEntityMockImport` 和 `reviewPage.platformEntityMockImport` 中展示已 Mock 入库记录。
`POST /api/platform-entities/contract-validate` 只读取本地 `contractConfig` JSON，可选 `entityType`，返回 `platformApiContractValidation`、`mode=LOCAL_PLATFORM_API_CONTRACT_VALIDATION` 和安全标记；用于离线检查 draft import endpoint、状态字段别名、状态映射和 `requestBodyMapping`。仓库内的 `examples/input/platform-contract.json` 覆盖 Lab / Exam / Grading / PPT 四类本地 staging 映射，可直接作为 CLI/HTTP 校验样例；它不代表真实平台正式字段，后续其他团队拿到真实平台 API 文档后再替换 endpoint 和字段映射。该接口不读取 token、不发送请求、不写数据库、不真实导入、不发布。
`POST /api/platform-entities/{id}/import-dry-run` 读取本地 `mock-import` 产生的平台实体记录，把 Lab / Exam / Grading / PPT 草稿转换成未来真实平台 draft import API 的 DTO、目标 endpoint、`platformApiContract`、`contractValidation` 和 idempotency key 预览，并写入 `WORKFLOW_REPORT` Artifact 与 `PLATFORM_ENTITY_IMPORT_DRY_RUN` 操作审计。请求体包含 `reviewer`，可选 `output`、`contractConfig`、`coreDbPath`；当传入 `coreDbPath` 时，会从 Backend Core repository 的 `platform_entities` 读取实体，并把 dry-run Artifact 与操作审计写回同一 repository，响应返回 `backendCoreAgentEntityImportDryRun`，确认 `repositoryContractUsed=true`、`jsonStoreSourceRead=false`、`artifactWritten=true` 和 `operationAuditEventWritten=true`。`contractConfig` 是本地 JSON 文件路径，可覆盖 `entities.<entityType>.draftImportPath`、`statusPathTemplate`、`draftIdResponseKeys`、`statusResponseKeys`、`statusMapping` 和 `requestBodyMapping`，用于适配测试平台字段差异，不承载密钥。该接口只做 dry-run，固定 `dryRunOnly=true`、`requestSent=false`、`networkAccess=false`、`databaseWritten=false`、`realPlatformImport=false`、`realPublish=false`，不会调用真实平台 API。`cli/platform_api_contract.py` 集中维护四类实体的 draft-import endpoint、状态查询路径模板、draft id/status 响应字段别名和建议登记状态，供 contract-validate、dry-run、send/status 和后续真实平台 adapter 复用。

`POST /api/platform-entities/{id}/import-send`、`POST /api/platform-entities/{id}/import-status` 和 `POST /api/platform-entities/{id}/import-result` 当前不属于本地闭环默认 API。它们的既有实现和契约说明仅保留给未来真实平台对接团队参考；在没有真实平台后端接口、平台 API base URL、`AGENT_API_TOKEN` 和平台状态定义前，不要求运行、不作为 readiness 阻塞项，也不作为下一步开发目标。

统一操作审计事件可查询：

```text
GET /api/audit-events?resourceType=ENVIRONMENT
GET /api/audit-events?action=MOCK_GRADING_RUN
GET /api/audit-events?actor=backend-mock
```

`backend/audit_query_service.py` 已承接 `/api/audit-events`、`/api/review-audit-events` 和 `/api/provider-audit-events` 的过滤校验与只读查询分支。统一操作审计事件固定标记不调用真实 LLM、不改动真实云资源、不执行选手代码、不真实发布。`review-audit-events` / `audit-events` 可通过 `coreDbPath` 从 Backend Core 本地 SQLite staging 只读查询；未传 `coreDbPath` 时仍读 JSON store。Provider 调用审计当前仍只读 JSON store，不访问真实 Provider。

Artifact Mock 清单可查询：

```text
GET /api/artifacts?kind=LAB_DSL
GET /api/artifacts?workflowRunId=<workflow_run_id>
GET /api/artifacts/{id}
```

Artifact 只记录本地产物元数据和安全标记，不上传真实文件，不连接远程对象存储。

Provider 调用审计可查询：

```text
GET /api/provider-audit-events?operation=generateJson
GET /api/provider-audit-events?status=FAILED
GET /api/provider-audit-events?providerId=mock
```

Provider registry、health 和 generateJson 的成功/失败路径都会写入本地 `providerCallAuditEvents`，并通过同一个审计查询服务返回；事件固定 `mode=MOCK_ONLY`，不调用真实 LLM、不读取密钥、不访问网络、不创建任务、不自动发布。
`POST /api/labs/generate`、`POST /api/exams/generate-from-lab`、`POST /api/ppt/generate` 和 `POST /api/workflow/demo` 的 Provider Adapter 生成步骤也会写入同一套审计事件，并在返回体中暴露 `providerCallAuditEvent`。
`POST /api/labs/import-preview`、`POST /api/exams/import-preview`、`POST /api/grading/import-preview` 和 `POST /api/ppt/import-preview` 只接受已审核通过的 DSL 任务，返回本地平台实体草稿预览、Artifact 和操作审计事件；这些步骤不属于 Provider 生成，不发起新的 LLM 请求，也不会写真实平台数据库。

MCP Tool 调用记录可查询：

```text
GET /api/mcp-tool-call-records?toolName=analyze_material
GET /api/mcp-tool-call-records?status=FAILED
GET /api/mcp-tool-call-records?traceId=trace_xxx
```

`mcpToolCallRecords` 只记录本地 Mock Tool 调用边界，包含成功、参数校验失败和 Backend Mock 失败；参数只保存 key 和脱敏预览，不启动真实 MCP Server 或 Agent。

PPT 生成请求体：

```json
{
  "input": "examples/input/demo-source.md"
}
```

Mock 评分请求体：

```json
{
  "grading": "templates/grading/examples/python-pytest.yaml"
}
```

`POST /api/grading/run` 和 `GET /api/grading/report` 会返回 `reportDetail`，用于前端评分详情页直接展示 `sandboxPolicy`、`explainability`、`checkPlans[].mockEvidence`、安全摘要和审计摘要。`reportDetail` 由 `sandbox.grade_runner.build_grading_report_detail` 统一构造，Backend 只做透传和审计事件注入。`GET /api/grading/report` 可选传入 `taskId`；当该审核任务已关联 `GRADING_EVIDENCE_MERGE` 或 `GRADING_EVIDENCE_AUTO` Artifact 时，响应会追加 `mergedGradingEvidence`、`mergedGradingEvidenceSummary`、`mergedGradingEvidenceCheckItems` 和可选 `autoGradingEvidenceSummary`，复用 `GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence` 的只读摘要，便于评分报告页直接展示 check 级 evidence 与人工复核动作。该聚合只读取本地任务和 Artifact，不执行 Docker、pytest、Notebook、命令或发布。

Provider Mock 生成请求体：

```json
{
  "promptId": "lab_generation_v0",
  "outputKind": "Lab",
  "inputRef": "examples/input/demo-source.md"
}
```

Provider Mock 接口只返回本地 DSL 示例引用，固定 `mode=MOCK_ONLY`、`realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`。

Exam 生成请求体：

```json
{
  "labId": "lab_demo"
}
```

Lab 生成请求体：

```json
{
  "input": "examples/input/demo-source.md"
}
```

环境创建请求体：

```json
{
  "title": "Ubuntu VM",
  "image": "ubuntu-22.04",
  "resources": {
    "cpu": 2,
    "memoryGb": 4
  }
}
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- 只提供本地 Mock 查询、Workflow Demo、Lab/Exam/PPT 生成、Mock 评分、审核状态流转和环境记录创建，不提供真实发布/资源接口。
- 不启动 Web Server。
- 不连接生产数据库。
- 不创建真实 VM 或 Notebook。
- 不执行选手代码，评分报告接口只读取本地 Mock JSON。
- Workflow Demo 只串联本地素材分析、DSL 示例、Mock 评分报告和本地 AI Task，不调用真实模型，不保存真实发布物。Phase 2 content-generation API 在显式 `providerMode=real-llm` 和确认项齐全时可调用真实 OpenAI-compatible LLM 生成四类 DSL，但仍只保存待审核产物，不自动发布。
- 素材分析只做静态读取和风险标记，不执行输入文件中的 Shell，不抓取远程内容。
- Workflow Run 查询只读取本地 Mock store，不启动真实编排引擎。
- Artifact 查询只读取本地 Mock store，不连接对象存储、不发布产物。
- Provider 接口只启用 `mock` Provider；真实 Provider 健康检查或生成请求会被拒绝。
- Provider Mock 不读取 API Key、不访问网络、不调用真实 LLM。
- MCP Server Mock 接口只调用 `mcp_server/mock_server.py` 本地 runtime，返回 `networkListenerStarted=false`，不启动真实 MCP Server 或 Agent。
- 高风险 MCP 意图接口只创建 `WAITING_REVIEW` AI Task 和操作审计；发布意图固定 `realPublish=false`、`autoPublishAllowed=false`，销毁环境意图固定 `requiresSecondConfirmation=true`、`environmentDestroyed=false`。`GET /api/review-tasks/{id}` 会把这类意图聚合为 `highRiskIntent.postReviewDisposition`、`reviewPolicy.postReviewDispositionState` 和 `reviewPage.highRiskIntentPanel`，但不提供真实执行入口；审核通过发布意图后仍是 `APPROVED_EXECUTION_BLOCKED`，审核通过销毁环境意图后仍是 `APPROVED_PENDING_SECOND_CONFIRMATION`。`GET /api/review-tasks/{id}/second-confirmation-status` 只读返回二次确认 Mock 状态，固定 `confirmationActionAvailable=false`、`destroyRealEnvironmentEnabled=false`。
- Lab 生成只返回本地示例 DSL，并创建 `WAITING_REVIEW` AI Task，不调用真实大模型。
- Exam 生成只返回本地 Exam DSL 和 Grading DSL，并创建 `WAITING_REVIEW` AI Task；标准答案不得展示给选手端。
- Phase 2 Grading 生成接口 `/api/phase2/workflows/grading-generation/run` 只读取本地 Exam DSL，通过 MockProvider 生成 Grading DSL 审核包，并写入本地 AI Task、Artifact、WorkflowRun 和 Provider 审计；不执行真实沙箱或选手代码。
- PPT 生成只返回本地 PPT DSL，并创建 `WAITING_REVIEW` AI Task，`artifactGenerated=false`，不生成真实 PPT 文件。
- Mock 评分只读取 Grading DSL，并通过 `sandbox.GradingRunner` / `sandbox.MockSandboxExecutor` 生成报告，支持 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类评分项的 Mock 计划；`sandboxExecuted=false`、`commandExecuted=false`、`contestantCodeExecuted=false`，不执行选手代码、不执行 Notebook、不读取真实 JSON/日志文件，同时写入统一操作审计事件。`MOCK_GRADING_RUN.detail` 包含 runner、checkSummary、checkPlans 和真实沙箱/命令/pytest/Notebook/文件读取阻断动作；`reportDetail` 与审计计划字段共享 sandbox 构造逻辑，仍只展示 Mock 计划，不代表真实沙箱已执行。
- 审核通过/拒绝只更新本地 AI Task 并写入本地审计事件，不发布真实实验或考试。
- 环境 vm/notebook 创建只写入本地 Mock store 和统一操作审计事件，不调用云资源。
- 环境 start/stop/reset 只更新本地状态并写入统一操作审计事件，不调用云资源。
