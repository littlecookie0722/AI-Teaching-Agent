# 23_DEMO_USAGE_GUIDE

本说明面向演示人员，目标是把当前项目在本地部署、启动、演示能力和大模型配置讲清楚。当前项目以 CLI、静态页面、Backend Mock 和 MCP Mock 为主；默认不启动真实 Web 服务，不连接生产数据库，不创建真实云资源，不自动发布内容。

> 运营验收和 `operations-*` 页面当前仅作为既有演示资料归档参考，后续默认不再扩展运营交付内容。新开发优先围绕真实 LLM 生成、DSL 归一化、评分沙箱、审核导入和 MCP 核心工具。

> 当前没有真实实训平台后端接口。演示默认只做本地闭环：真实 LLM 产物、Schema 校验、审核中心、本地 import-preview / mock-import / import-dry-run DTO、受控评分 evidence 和本地评分记录复核；不需要平台 API base URL、`AGENT_API_TOKEN`、平台状态查询、平台侧签收或真实发布。

## 1. 当前演示形态

当前可以演示三类能力：

1. Phase 1 / Mock 平台底座：DSL、CLI、AI Task、人工审核、Mock 评分、Mock Backend、Mock MCP、静态前端页面。
2. Phase 2 / 真实 LLM 成果复放：复放已有真实 Lab / Exam / Grading / PPT DSL，展示候选人预览脱敏、审核队列、PPTX Artifact、评分 evidence 和一键验收清单。
3. Phase 2 / 真实 LLM 生成入口：在显式 opt-in、环境变量和模型名齐备时，可通过 OpenAI-compatible SDK 发送真实请求生成 Lab DSL，或运行正式真实 LLM Workflow 生成 Lab / Exam / Grading / PPT 四类 DSL。

默认推荐先演示第 1 和第 2 类。第 3 类会消耗真实模型额度，必须由操作者明确设置环境变量并确认命令参数。

### 1.1 最近真实回归证据

2026-07-12 已使用 DeepSeek v4 flash 对 Linux 日志分析、Python 数据清洗和 Web API 测试三份素材完成真实 Lab / Exam / Grading / PPT 回归。最终 12 份 DSL 均通过文件级 Schema 校验并停在 `WAITING_REVIEW`；Exam 候选人预览均移除了 `answer` 和 `gradingRef`。本次出现过一次 Lab objectives 数量不足的内容质量警告，已通过收紧 Prompt 的最小目标数并复跑同一素材验证修复。详细矩阵见 `docs/25_REAL_LLM_SCHEMA_DRIFT_MATRIX.md`。该证据不代表自动批准、真实平台导入或发布。

## 2. 本地部署

### 2.1 前置要求

- Windows PowerShell。
- Python 3.11+。
- Node.js 只在重新生成 PPTX Artifact 或运行相关脚本时需要；普通静态页面演示不需要启动 Node 服务。
- Docker 只在后续真实容器评分演示时需要；当前一键演示清单不会启动 Docker。

### 2.2 安装 Python 依赖

在项目根目录执行：

```powershell
$PROJECT_ROOT = Resolve-Path "."
Set-Location $PROJECT_ROOT
python -m pip install -r requirements.txt
```

验证 OpenAI SDK 已安装：

```powershell
python -c "import openai, importlib.metadata as m; print(m.version('openai'))"
```

### 2.3 本地状态文件

CLI 默认把本地 Mock 状态写入：

```text
cli/.lab_cli_store.json
```

如需隔离演示状态，可在当前 PowerShell 设置：

```powershell
$env:LAB_CLI_STORE="examples/output/demo-local-store.json"
```

该文件只用于本地演示，不代表真实数据库。

如果要让 Backend Mock 的评分任务 API 默认读写同一个本地 SQLite staging 文件，可设置：

```powershell
$env:LAB_BACKEND_GRADING_DB_PATH="examples/output/grading-local.sqlite3"
```

也可以在启动 HTTP server 时使用 `--grading-db`。该配置只影响 `/api/grading/jobs`、`/api/grading/jobs/{id}/run`、`/api/grading/jobs` 列表和查询，以及 `/api/grading/workers/run-once`、`/api/grading/workers/drain-once` 的本地 SQLite 默认路径；显式请求 `dbPath` 优先。它不是生产数据库。

## 3. 启动方式

### 3.1 静态页面演示

当前前端是静态 HTML 原型，不需要启动前端 dev server。直接打开页面：

```powershell
start .\frontend\real-demo.html
start .\frontend\review-center.html
start .\frontend\ppt-review.html
start .\frontend\grading-report.html
```

如需通过本地 HTTP 包装器访问页面和 API，并让评分任务默认使用本地 SQLite：

```powershell
python -m backend.mock_http_server --host 127.0.0.1 --port 8000 --grading-db examples/output/grading-local.sqlite3
```

本地评分 worker 如需一次处理有限数量的排队任务，可使用：

```powershell
python lab_cli.py grade worker-drain-once --db-path examples/output/grading-local.sqlite3 --limit 5 --lease-seconds 300 --max-attempts 3
```

`worker-drain-once` 是顺序、有限批次的本地 staging 命令，`--limit` 最大 20；返回中的 `workerDrain.quota` 会标记是否触顶和是否可能仍有可运行任务，`workerDrain.resourceCleanup` 会标记本地报告与评分记录保留情况。它不会启动常驻后台服务、真实生产队列或并发 worker。

归档的运营交付视角页面仍可打开查看，但不作为后续开发入口：

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\operations-demo-map.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
start .\frontend\delivery.html
```

### 3.2 CLI 演示

所有 CLI 返回统一 JSON。常用命令：

```powershell
python lab_cli.py phase1 check
python lab_cli.py review batch-summary
python lab_cli.py workflow registry list
python lab_cli.py mcp list
```

#### 3.2.1 无 Key 离线 Demo

从干净检出开始，先安装开发依赖，再运行一条不需要 API Key 的本地闭环：

```powershell
python -m pip install -e ".[dev]"
python lab_cli.py demo offline
```

`demo offline` 使用本地 deterministic fixture / MockProvider，依次校验
Lab、Exam、Grading、PPT 四类 DSL，生成不含 `answer` 和内部 `gradingRef`
的候选人预览，并确认四类产物保持 `WAITING_REVIEW`、未审核前发布被阻断。
默认会写入以下本地产物：

```text
examples/output/offline-demo-summary.json
examples/output/offline-demo-workflow-report.json
examples/output/offline-demo-candidate-preview.json
```

也可以把产物写入临时目录，避免混入仓库工作区：

```powershell
python lab_cli.py demo offline `
  --input examples/input/demo-source.md `
  --reviewer offline-demo `
  --output .\tmp\offline-demo-summary.json `
  --workflow-output .\tmp\offline-demo-workflow-report.json `
  --candidate-preview-output .\tmp\offline-demo-candidate-preview.json
```

成功摘要的关键字段是 `status=PASS`、四类 `*Validated=true`、
`candidatePreviewSafe=true`、`reviewStatus=WAITING_REVIEW`、
`blockingIssueTotal=0`。低级内容 warning 会保留给人工审核，不代表自动通过。
该命令不调用模型、不读取密钥、不联网、不执行选手代码、不发布；失败时仍返回
统一 JSON envelope，并且不会写出未通过校验的 summary 或候选人预览。

真实 LLM 成果复放的一键清单：

```powershell
python lab_cli.py phase2 demo-bundle checklist --bundle examples/output/real-llm-demo-bundle.json --acceptance-summary examples/output/real-llm-demo-acceptance-summary.json --output examples/output/real-llm-demo-checklist.json
python lab_cli.py review real-dsl-preview --output examples/output/real-llm-demo-real-dsl-review-preview.json
python lab_cli.py review real-dsl-revision --kind lab --source examples/output/real-llm-lab.json --reviewer teacher_1 --comment "补充实验验收说明，并保持人工审核。" --target-section steps --requested-change "补充验收标准" --output examples/output/real-llm-lab-revision.json --report-output examples/output/real-llm-lab-revision-report.json
python lab_cli.py review real-dsl-revision-batch --preview examples/output/real-llm-demo-real-dsl-review-preview.json --reviewer teacher_1 --output-dir examples/output --report-output examples/output/real-llm-demo-revision-batch-report.json
python lab_cli.py review real-dsl-revision-diff-preview --batch-report examples/output/real-llm-demo-revision-batch-report.json --output examples/output/real-llm-demo-revision-diff-preview.json
python lab_cli.py review real-dsl-revision-decision --diff-preview examples/output/real-llm-demo-revision-diff-preview.json --suggestion-id revise_lab_objective_depth --reviewer teacher_1 --decision approve --reason "人工确认该修订可进入后续手动合并，发布前仍需复核最终 DSL。" --output examples/output/real-llm-demo-revision-decision-report.json
python lab_cli.py review real-dsl-revision-promote --decision-report examples/output/real-llm-demo-revision-decision-report.json --reviewer teacher_2 --output examples/output/real-llm-demo-revision-promoted-candidate.json --report-output examples/output/real-llm-demo-revision-promotion-report.json
python lab_cli.py review real-dsl-revision-enqueue --promotion-report examples/output/real-llm-demo-revision-promotion-report.json --reviewer teacher_3
python lab_cli.py exam generate-from-lab --lab templates/lab/examples/basic-lab.yaml --provider-mode real-llm --model deepseek-v4-flash --base-url https://api.deepseek.com --api-surface chat.completions --repair-on-schema-failure --explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish
python lab_cli.py grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/controlled-command-demo --output examples/output/grading-stable-v1-evidence.json --submission-id submission_001 --candidate-id candidate_001 --reviewer teacher_1 --image ai-grading-python:0.1 --review-detail-output examples/output/grading-stable-v1-review-detail.json --result-preview-output examples/output/grading-stable-v1-result-preview.json
python lab_cli.py grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/controlled-command-demo --output examples/output/grading-stable-v1-docker-smoke-evidence.json --submission-id docker_smoke_submission_001 --candidate-id candidate_docker_smoke --reviewer teacher_1 --image ai-grading-python:0.1 --review-detail-output examples/output/grading-stable-v1-docker-smoke-review-detail.json --result-preview-output examples/output/grading-stable-v1-docker-smoke-result-preview.json --fail-on-controlled-unavailable
python lab_cli.py grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/mixed-checks-pass --output examples/output/grading-stable-v1-docker-full-pass-evidence.json --submission-id docker_full_pass_submission_001 --candidate-id candidate_docker_full_pass --reviewer teacher_1 --image ai-grading-python:0.1 --review-detail-output examples/output/grading-stable-v1-docker-full-pass-review-detail.json --result-preview-output examples/output/grading-stable-v1-docker-full-pass-result-preview.json --fail-on-controlled-unavailable
python lab_cli.py lab import-preview --task-id <approved_lab_task_id> --reviewer teacher_4 --output examples/output/lab-template-import-preview.json
python lab_cli.py exam import-preview --task-id <approved_exam_task_id> --reviewer teacher_5 --output examples/output/exam-question-import-preview.json
python lab_cli.py grade import-preview --task-id <approved_grading_task_id> --reviewer teacher_5 --output examples/output/grading-rule-import-preview.json
python lab_cli.py review real-dsl-revision --kind lab --source examples/output/real-llm-lab.json --reviewer teacher_1 --comment "请用真实 LLM 重新组织实验步骤说明。" --provider-mode real-llm --model <model> --base-url <openai-compatible-base-url> --explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish --output examples/output/real-llm-lab-revision.json --report-output examples/output/real-llm-lab-revision-report.json
```

`exam generate-from-lab --lab ... --provider-mode real-llm` 是第二个主功能稳定入口：输入必须是已通过 Schema 校验的 Lab DSL；输出为任务专属 Exam DSL、Grading DSL 和候选人安全预览，状态统一停在 `WAITING_REVIEW`。返回 JSON 中的 `examGradingFeatureReadiness.completeForStableV1=true` 表示题目 `gradingRef` 已被评分 `checks` / `assessmentPlan` 覆盖、总分已对齐、候选人预览不包含 `answer` 和内部 `gradingRef`。审核通过后再运行 `exam import-preview` 与 `grade import-preview`，仍然只做本地草稿预览，不调用真实平台、不发布。

`grade stable-v1` 是第三个主功能稳定入口：输入 Grading DSL 和本地 submission，默认请求受控 command evidence，输出评分 evidence 报告、本地 `GradingRecord`、评分结果预览和审核详情摘要。返回 JSON 中的 `gradingStableV1Readiness.completeForStableV1=true` 表示受控 evidence 已覆盖命令类检查、评分报告可读、`GradingRecord` 已进入人工复核队列、Review Detail 能看到 evidence 与 record。真实 Docker runtime smoke 建议加 `--fail-on-controlled-unavailable`，确保 Docker 或镜像不可用时直接失败；`examples/submissions/mixed-checks-pass` 是与 `templates/grading/examples/mixed-checks.yaml` 完全匹配的满分样例，用于验证六类检查 `6/6` 通过、总分 `100/100`。`examples/output/grading-stable-v1-docker-smoke-evidence.json`、`examples/output/grading-stable-v1-docker-full-pass-evidence.json` 和对应 result-preview 的 evidence item 会直接显示状态、得分、来源、exitCode、stdout/stderr 尾部、检查文件和错误码。该命令不会自动 `record-review`、不会自动审核 AI Task、不会发送真实平台请求；审核员下一步仍需人工运行 `grade record-review --decision approve-ready` 或记录补证据/需修订。

`lab/exam/grade import-preview` 需要先把对应 DSL 任务通过人工审核变为 `APPROVED`。审核通过后可先运行 `python lab_cli.py review detail --task-id <approved_task_id>` 查看 `platformImportPreviewActions`，其中会列出可用的 CLI、Backend API 和 MCP Tool 入口，以及是否已经生成过对应预览。执行入口后，`platformImportPreview` 会展示平台 `lab_template`、`exam_question`、`grading_rule` 草稿预览和审计记录；`platformImportPreviewSignoff` 会展示人工签收 checklist，确认源 DSL、Schema、候选答案隐藏、沙箱边界和不写库/不发布标记是否需要人工确认。整个过程不写真实数据库、不调用真实平台、不发布，也不执行评分沙箱。

### 3.3 Backend Mock

当前 Backend 是本地请求处理函数，不启动真实 HTTP 服务。通过测试验证：

```powershell
python -m pytest tests/test_backend_mock_api.py
```

如果需要演示 API 能力，可讲解 `backend/README.md` 中的 Mock API 路由；这些路由由测试直接调用，不监听端口。

### 3.4 MCP Mock

当前 MCP 是本地 Mock Tool 和本地 MCP Server Mock runtime，不启动真实 MCP Server，不监听端口。
默认工具 profile 是 `local-core-mvp`，只暴露本地核心闭环工具；revision-loop、真实平台 import-send / import-status、平台签收 / 最终发布复核、环境创建、发布 / 销毁意图等历史工具不在默认 profile 中。

```powershell
python lab_cli.py mcp list
python lab_cli.py mcp call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp call --tool get_review_task_summary --arguments "{}"
python lab_cli.py mcp call --tool get_real_dsl_review_preview --arguments "{}"
python lab_cli.py mcp call --tool create_lab_template_import_preview --arguments "{\"taskId\":\"<approved_lab_task_id>\",\"reviewer\":\"teacher_4\",\"output\":\"examples/output/lab-template-import-preview.json\"}"
python lab_cli.py mcp call --tool create_exam_question_import_preview --arguments "{\"taskId\":\"<approved_exam_task_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/exam-question-import-preview.json\"}"
python lab_cli.py mcp call --tool create_grading_rule_import_preview --arguments "{\"taskId\":\"<approved_grading_task_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/grading-rule-import-preview.json\"}"
python lab_cli.py mcp call --tool create_agent_entity_import_dry_run --arguments "{\"id\":\"<agent_entity_id>\",\"reviewer\":\"teacher_5\",\"output\":\"examples/output/platform-entity-import-dry-run.json\"}"
python lab_cli.py mcp server-info
python lab_cli.py mcp server-tools
python lab_cli.py mcp stdio-smoke --input examples/input/demo-source.md --output examples/output/mcp-stdio-client-smoke.json
```

审核退回修改和真实 DSL 修订能力当前保留 CLI / Backend 本地能力，但不属于默认 `local-core-mvp` MCP 工具集。演示时如需展示修订流程，优先使用 CLI，避免误把暂停工具作为当前 Agent 默认路线：

```powershell
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md
python lab_cli.py review revision-request --task-id <task_id> --reviewer teacher_1 --comment "补充步骤截图验收标准。" --priority HIGH --target-section steps
python lab_cli.py review regenerate-mock --task-id <task_id> --reviewer teacher_1
python lab_cli.py review real-dsl-revision-batch --preview examples/output/real-llm-demo-real-dsl-review-preview.json --reviewer teacher_1 --output-dir examples/output --report-output examples/output/real-llm-demo-revision-batch-report.json
```

上述修订链路只写入本地 Mock store 或本地修订报告：源任务仍是 `WAITING_REVIEW`，新修订任务也是 `WAITING_REVIEW`，`newLlmRequestSent=false`、`realLlmCalled=false`、`realPublish=false`。如需回归历史全量 MCP manifest，可显式运行 `python lab_cli.py mcp list --profile all`；该 profile 仅作历史契约参考，不作为当前本地核心 MVP 或 Agent 默认工具集。

## 4. 推荐演示路径

### 4.1 真实 LLM 成果复放演示

推荐从这条路径开始：

```text
frontend/real-demo.html
  -> frontend/review-center.html
  -> frontend/ppt-review.html
  -> frontend/grading-report.html
```

讲解顺序：

1. `real-demo.html`：看 `RealDemoOneClickChecklist`，确认 `readyForDemo=true`、`acceptance=7/7`、`sections=6/6`、`gradingEvidenceCoverage=100/100`。
2. `RealDslReviewPreview`：直接查看真实 Lab 步骤、候选人安全 Exam 题面、教师审核专用 `gradingRef`、Grading assessmentPlan/checks 和 PPT 大纲；同时查看 `qualitySignals`、`reviewIssues`、`revisionSuggestions`，把真实产物从“能展示”推进到“能审核、能退回修订”。
3. `generated_dsl`：Lab / Exam / Grading / PPT 四类 DSL 都是 `WAITING_REVIEW`。
4. `candidate_preview`：候选人预览安全，`answerVisibleToCandidate=false`，不包含 `answer` 或内部 `gradingRef`；教师审核面板可以看到 `teacherOnlyGradingRefVisibleInReview=true`。
5. `review-center.html`：真实 Demo 四类产物进入审核队列，不能批量通过、不能自动发布。
6. `ppt-review.html`：PPTX Artifact 可做页级审核，仍需人工确认。
7. `grading-report.html`：受控 Docker evidence 覆盖 `40/40`，Notebook 静态 evidence 覆盖 `60/60`，合计 `100/100`，但仍需人工审核。
8. 本地修订链路：通过默认 MCP 工具 `get_real_dsl_review_preview` 查看真实 DSL 审核摘要；如审核人需要退回或生成修订草稿，使用 CLI `review revision-request`、`review regenerate-mock`、`review real-dsl-revision-*` 系列命令完成本地修订和人工决策。revision-loop 历史 MCP 工具只在 `--profile all` 中保留作契约回归参考，当前 `local-core-mvp` 默认不暴露。上述路径都不能绕过人工审核，`approve` 和候选提升都不会自动发布。

对应脚本：

```text
delivery/REAL_DEMO_SCRIPT.md
delivery/real-demo-script.json
delivery/REAL_DEMO_QUICK_COMMANDS.md
delivery/real-demo-quick-commands.json
delivery/REAL_DEMO_AGENT_WORKFLOW.md
delivery/real-demo-agent-workflow.json
```

### 4.2 Phase 1 Mock 交付演示

入口：

```text
delivery/DEMO_SCRIPT_CHECKLIST.md
frontend/operations-demo-script.html
```

推荐命令：

```powershell
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
```

## 5. 当前能力清单

### 5.1 内容生成与 DSL

- Lab DSL、Exam DSL、Grading DSL、PPT DSL Schema。
- MockProvider 生成四类 DSL，默认进入 `WAITING_REVIEW`。
- 真实 LLM 最小 Lab DSL PoC。
- 真实 LLM Workflow，可生成 Lab / Exam / Grading / PPT 四类 DSL；历史 `real-llm-demo` 入口仅用于旧演示包回归。
- Exam 候选人预览脱敏导出，防止标准答案进入选手端。
- PPT DSL 到 PPTX Artifact 的本地构建 PoC。

### 5.2 审核与任务

- AI Task 本地状态模型。
- `WAITING_REVIEW`、审核通过、驳回、Mock publish 状态流转。
- Review Detail 聚合任务、产物、Workflow、审计、评分计划、候选人预览和平台导入预览摘要。
- Review Priority Queue 人工审核优先队列。
- 真实 Demo Review Queue，展示四类真实演示产物。
- 审核退回修改请求和 Mock 修订再生成，均可通过 CLI / Backend Mock / MCP Mock 调用。
- PPT 页级审核状态更新 Mock。

### 5.3 评分与 evidence

- Mock 评分报告。
- 真实沙箱前预检。
- 只读 evidence 演示层。
- 受控 Docker evidence 摘要。
- Notebook 静态 JSON 解析 evidence。
- `gradingEvidenceCoverage=100/100` 演示摘要。

### 5.4 平台工具化

- `lab_cli.py` 统一 JSON CLI。
- Backend Mock API 函数。
- MCP Mock Tools。
- MCP Server Mock runtime。
- Provider 调用审计、MCP 调用审计、审核审计、操作审计。

### 5.5 前端静态原型

- `frontend/real-demo.html`：真实成果演示首屏。
- `frontend/review-center.html`：审核中心。
- `frontend/ppt-review.html`：PPT 页级审核。
- `frontend/grading-report.html`：评分报告与 evidence。
- `frontend/workflows.html`：Workflow 能力目录。
- `frontend/audit.html`、`frontend/audit-detail.html`、`frontend/audit-incidents.html`：审计可观测。
- `frontend/operations-*.html`：运营演示、签收、Runbook、交付入口。

## 6. 大模型配置

### 6.1 配置位置

真实大模型相关变量只允许来自当前 shell 环境变量、配置中心或本地未提交文件。仓库中的 `.env.example` 只提供变量名示例，不允许写入真实密钥。

当前支持 OpenAI-compatible 配置：

```powershell
$env:OPENAI_API_KEY="<your-api-key>"
$env:OPENAI_MODEL="<model-name>"
$env:OPENAI_BASE_URL="<openai-compatible-base-url>"
```

说明：

- `OPENAI_API_KEY`：真实 API Key。不得写入 Git、Markdown、日志或前端。
- `OPENAI_MODEL`：模型名；也可以在 CLI 中用 `--model` 指定。
- `OPENAI_BASE_URL`：可选。用于 OpenAI-compatible endpoint；不设置时使用 SDK 默认 OpenAI endpoint。

设置后可先运行只读配置摘要命令：

```powershell
python lab_cli.py provider real-llm-runtime-config
```

如果模型名和 OpenAI-compatible base URL 准备用命令参数传入，也可以先这样检查：

```powershell
python lab_cli.py provider real-llm-runtime-config --model deepseek-v4-flash --base-url https://api.deepseek.com
```

该命令只显示变量是否存在、模型名/base URL 的来源和非密钥配置值，不输出 API Key，不导入 SDK，不创建 client，不发起请求。

返回 JSON 中的 `commandReadiness` 会说明当前 shell 还缺 `OPENAI_API_KEY`、模型名，还是已经可以运行显式确认的真实 LLM workflow。`safeCommandTemplates` 会给出无密钥命令模板：

- `secretEnvPowerShell`: 只包含 `$env:OPENAI_API_KEY="<your-api-key>"` 占位符。
- `runtimeConfigCheckArgs`: 只读检查命令参数数组。
- `workflowRunArgs`: 真实 LLM 演示 workflow 参数数组，包含 `--explicit-real-call-opt-in`、`--confirm-real-dsl`、`--confirm-waiting-review` 和 `--confirm-no-auto-publish`。

这些模板用于减少 PowerShell 手工拼接错误；模板不会返回、记录或猜测真实 API Key。

本项目代码不会自动加载 `.env` 文件。若使用本地 `.env`，需要操作者自行在 PowerShell 中加载，而且真实 `.env` 不得提交。

### 6.2 使用你自己的 OpenAI-compatible 模型

以 OpenAI-compatible 服务为例：

```powershell
$env:OPENAI_API_KEY="<your-api-key>"
$env:OPENAI_MODEL="mimo-v2.5-pro"
$env:OPENAI_BASE_URL="https://api.xiaomimimo.com/v1"
```

也可以不设置 `OPENAI_MODEL`，改为在命令中传：

```powershell
--model "mimo-v2.5-pro"
```

当 `OPENAI_MODEL` 和 `OPENAI_BASE_URL` 已设置时，真实二次修订等命令可以省略 `--model` 和 `--base-url`，由运行时配置读取。

不要把真实 key 写入 `.env.example`、README、docs 或测试文件。

### 6.3 检查 SDK client 边界

该命令只导入 SDK、读取环境变量用于构造 client，不发起模型请求：

```powershell
python lab_cli.py provider real-llm-sdk-client-boundary check --provider openai --explicit-sdk-boundary-opt-in --explicit-client-boundary-opt-in --confirm-sdk-import --confirm-client-construction --confirm-secret-value-handling --confirm-no-network-call --confirm-no-real-llm-call
```

### 6.4 最小真实 Lab DSL 请求

当前第一个主功能推荐优先使用 `lab generate-from-source --provider-mode real-llm`：它只发起 Lab DSL 生成请求，成功后会写入任务专属 `examples/output/<task_id>-lab.json`，创建 `WAITING_REVIEW` 任务，并返回 `labFeatureReadiness`。这条路径适合验证“真实大模型产出可审核 Lab 内容”，后续可直接接 `review approve`、`lab import-preview` 和 `lab mock-import`，不需要一次性生成 Exam / Grading / PPT。

```powershell
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md --provider-mode real-llm --model "deepseek-v4-flash" --base-url "https://api.deepseek.com" --api-surface chat.completions --repair-on-schema-failure --explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish
```

上面的命令不会在参数中接收 API Key；真实密钥仍必须提前设置在当前 PowerShell 的 `OPENAI_API_KEY` 中。若模型服务支持 Responses API，也可以省略 `--api-surface chat.completions` 使用默认 `auto`。

旧的最小 PoC 命令仍保留用于 SDK 边界验证，它也只发送一次真实请求，只生成 Lab DSL，输出仍为 `WAITING_REVIEW`：

```powershell
python lab_cli.py provider real-llm-minimal-poc run --provider openai --input examples/input/demo-source.md --output examples/output/real-llm-minimal-poc-lab.json --model "%OPENAI_MODEL%" --explicit-real-call-opt-in --confirm-single-request --confirm-lab-only --confirm-waiting-review --confirm-no-auto-publish
```

PowerShell 中也可以直接写模型名：

```powershell
python lab_cli.py provider real-llm-minimal-poc run --provider openai --input examples/input/demo-source.md --output examples/output/real-llm-minimal-poc-lab.json --model "mimo-v2.5-pro" --explicit-real-call-opt-in --confirm-single-request --confirm-lab-only --confirm-waiting-review --confirm-no-auto-publish
```

### 6.5 正式真实 LLM Workflow

该命令默认会发起 4 次真实请求，分别生成 Lab / Exam / Grading / PPT DSL。所有结果仍为 `WAITING_REVIEW`：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-real-llm-report.json --provider-mode real-llm --real-llm-lab-output examples/output/real-llm-lab.json --real-llm-exam-output examples/output/real-llm-exam.json --real-llm-grading-output examples/output/real-llm-grading.json --real-llm-ppt-output examples/output/real-llm-ppt.json --model "mimo-v2.5-pro" --base-url "https://api.xiaomimimo.com/v1" --api-surface chat.completions --max-output-tokens 2600 --repair-on-schema-failure --explicit-real-call-opt-in --confirm-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

正式 `real-llm` 报告的审核提示应显示“真实 LLM 已生成 Lab/Exam/Grading/PPT 四类 DSL，全部仍需人工审核”，不应再出现“真实 LLM 仅用于 Lab DSL，Exam/Grading/PPT 仍为 Mock”。如果读取的是旧报告文件，需重新运行上面的命令生成新报告。

OpenAI-compatible endpoint 如果不支持 Responses API，或 Responses 调用在该端点上表现为 `APIConnectionError`，系统会自动尝试降级到 Chat Completions。也可以显式传 `--api-surface chat.completions` 直接绕过 Responses API。报告中的 `apiSurface` 会记录实际使用了 `responses`、`chat.completions` 或 `chat.completions.json_object`；失败响应中的 `errors[0].attempts` 会记录每个尝试过的 API surface 和错误类型。

可选 `--repair-on-schema-failure` 用于真实模型偶发输出字段类型不符合 Schema 的情况。它只在某一类 DSL Schema 校验失败时最多追加一次真实修复请求；报告中可查看 `generatedDsl.<kind>.provider.requestCount`、`schemaRepairAttempted`、`schemaRepairApplied` 和 `schemaRepair`。修复后仍必须人工审核，不会自动发布。

每类 DSL 摘要还会包含 `generatedDsl.<kind>.qualitySummary`，用于快速查看 `readyForReview`、`normalizationPatchCount`、`schemaRepairApplied`、`requestCount`、`apiSurface` 和 `responseId`。创建审核任务后，`review detail` 也会在 `reviewPage.providerSummary.qualitySummary` 和 `calls[*].qualitySummary` 展示同一口径的质量摘要，审核人不需要回到 Workflow Report 翻找真实 LLM 的归一化和 Schema 修复记录。该摘要只汇总已有审计和归一化结果，不会改变人工审核要求。

注意：这会消耗真实模型额度；打开修复开关时，最多每类失败 DSL 多消耗一次请求。失败时不会创建 AI Task，不会发布内容，但会在 `--output` 指定位置写入 `PHASE2_WORKFLOW_FAILURE_REPORT`，用于复盘 Provider 错误、Schema 失败诊断和已存在的部分输出文件路径。

若失败码是 `REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED`，失败报告和终端 JSON 都会包含 `schemaFailureDiagnostic`。该诊断只包含字段路径、失败类别、结构摘要和建议动作，不包含真实 API Key、原始 DSL 正文、标准答案或 gradingRef 原值。

真实请求完成后，可先运行本地只读校验，不重新调用模型、不读取密钥、不创建任务：

```powershell
python lab_cli.py phase2 real-dsl-demo verify --workflow-report examples/output/phase2-real-llm-report.json --lab examples/output/real-llm-lab.json --exam examples/output/real-llm-exam.json --grading examples/output/real-llm-grading.json --ppt examples/output/real-llm-ppt.json --output examples/output/real-llm-demo-local-verification.json
```

该报告会汇总四类 DSL 的 Schema 校验、`WAITING_REVIEW` 状态、Lab 步骤数、Exam 题目数、Grading checks / assessmentPlan、PPT 页数、内容质量阻塞和下一步建议。它适合在进入 `review detail`、`close-loop` 或导入预览前做一次快速自检。

也可以直接运行一键本地闭环命令，把只读校验、Demo Bundle、验收摘要和一键清单串成一个统一 JSON：

```powershell
python lab_cli.py phase2 real-dsl-demo one-click --workflow-report examples/output/phase2-real-llm-report.json --input examples/input/demo-source.md --lab examples/output/real-llm-lab.json --exam examples/output/real-llm-exam.json --grading examples/output/real-llm-grading.json --ppt examples/output/real-llm-ppt.json --submission examples/submissions/readonly-demo --output examples/output/real-llm-demo-one-click.json
```

如果审核人已经人工确认 Lab / Exam / Grading 三类 DSL 可以进入导入预览，可追加 `--run-close-loop`、三个 `--confirm-*-review-approved` 和 `--create-mock-imports`，让同一个命令继续生成本地导入预览和 mock platform entity readiness。该命令不会再次请求大模型、不会读取密钥、不会访问网络、不会真实导入平台、不会发布。

### 6.6 历史真实 Demo Workflow

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-real-llm-demo-report.json --provider-mode real-llm-demo --real-demo-lab-output examples/output/demo-real-lab.json --real-demo-exam-output examples/output/demo-real-exam.json --real-demo-grading-output examples/output/demo-real-grading.json --real-demo-ppt-output examples/output/demo-real-ppt.json --model "mimo-v2.5-pro" --target-users "平台开发者" --duration-minutes 45 --tech-tags "LLM" --explicit-real-call-opt-in --confirm-demo-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

后续真实开发默认使用 `--provider-mode real-llm`。该入口主要用于旧演示包和回归测试，同样会消耗真实模型额度，且不会自动发布内容。

## 7. 常用验证命令

```powershell
python -m pytest tests/test_real_demo_script.py
python -m pytest tests/test_real_demo_agent_runner.py
python -m pytest tests/test_cli.py tests/test_frontend_manifest.py
python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py
python -m pytest
```

一键验收清单：

```powershell
python lab_cli.py phase2 real-dsl-demo one-click --workflow-report examples/output/phase2-real-llm-report.json --input examples/input/demo-source.md --lab examples/output/real-llm-lab.json --exam examples/output/real-llm-exam.json --grading examples/output/real-llm-grading.json --ppt examples/output/real-llm-ppt.json --submission examples/submissions/readonly-demo --output examples/output/real-llm-demo-one-click.json
python lab_cli.py phase2 demo-bundle checklist --bundle examples/output/real-llm-demo-bundle.json --acceptance-summary examples/output/real-llm-demo-acceptance-summary.json --output examples/output/real-llm-demo-checklist.json
python lab_cli.py phase2 real-dsl-demo close-loop --workflow-report examples/output/phase2-real-llm-report.json --input examples/input/demo-source.md --reviewer teacher_2 --lab-import-output examples/output/lab-template-import-preview.json --exam-import-output examples/output/exam-question-import-preview.json --grading-import-output examples/output/grading-rule-import-preview.json --create-mock-imports --lab-mock-import-output examples/output/lab-template-mock-import.json --exam-mock-import-output examples/output/exam-question-mock-import.json --grading-mock-import-output examples/output/grading-rule-mock-import.json --output examples/output/real-llm-demo-close-loop.json --confirm-lab-review-approved --confirm-exam-review-approved --confirm-grading-review-approved
python lab_cli.py phase2 real-dsl-demo close-loop --workflow-report examples/output/phase2-real-llm-report.json --input examples/input/demo-source.md --reviewer teacher_2 --lab-import-output examples/output/lab-template-import-preview.json --exam-import-output examples/output/exam-question-import-preview.json --grading-import-output examples/output/grading-rule-import-preview.json --controlled-submission examples/submissions/real-demo-controlled --controlled-plan-output examples/output/real-llm-demo-controlled-plan.json --controlled-report-output examples/output/real-llm-demo-controlled-sandbox-report.json --controlled-image ai-grading-python:0.1 --controlled-stdout-command "python main.py" --controlled-stdout-expected "Python 3.11" --controlled-pytest-path checks/check_main.py --output examples/output/real-llm-demo-close-loop.json --confirm-lab-review-approved --confirm-exam-review-approved --confirm-grading-review-approved
python lab_cli.py agent real-demo run --input examples/input/demo-source.md --reviewer teacher_1 --revision-output examples/output/demo-agent-lab-revision.json
```

`phase2 real-dsl-demo one-click` 是当前 P0 推荐入口，适合在真实 LLM Workflow 成功后快速验证整条演示闭环。它默认只复用已有真实 DSL 产物，不发送新请求；需要导入预览时再显式打开 `--run-close-loop`。

命令输出的 `oneClick.entryRoutes` 是演示导航索引，只包含本地只读页面和产物路径，不会触发真实请求或发布。常用字段包括：

- `reviewCenter`：打开本次 Lab 任务的审核中心入口。
- `reviewCenterAfterAgentEntityReturn`：从平台实体导入页返回审核中心时使用，带 `agentEntityRefresh=1` 刷新标记。
- `platformEntities`：本地平台实体导入预览 / mock import 复核入口。
- `labReview` / `examReview` / `gradingReview` / `pptReview`：四类审核页入口。
- `gradingReport`：评分报告页入口；未生成受控评分报告文件时只携带 `taskId`，传入 `--controlled-submission` 并生成报告后会同时携带 `file`。
- `outputFiles`：本次 verification、bundle、acceptance summary、checklist、close-loop 和受控评分报告的文件路径。

`phase2 real-dsl-demo close-loop` 用于把已有真实 LLM DSL 产物推进到“可演示审核闭环”：它读取 `phase2-real-llm-report.json`，创建或复用四类 `WAITING_REVIEW` 任务，并要求显式确认 Lab / Exam / Grading 已人工审核通过后，才会审批三类可导入任务、生成本地导入预览，并在输出中汇总 `platformImportPreviewSignoff`。传入 `--create-mock-imports` 后，还会把三类导入预览写入本地 mock platform entity store，并在 `agentEntityReadinessReport.scope.platformEntities=lab_template/exam_question/grading_rule` 的 close-loop 作用域内输出 `summary.allReadyForManualPlatformReview=true`。这只表示本地平台实体候选记录已准备好人工复核，不代表真实平台入库。该命令不会再次请求大模型；PPT 仍保持 `WAITING_REVIEW`，用于后续 PPT 页级审核演示，不计入 close-loop 的三类平台实体 readiness 统计。若传入 `--controlled-submission`，命令会额外从真实 Grading DSL 生成受控 Docker 可执行子集，并执行 `CONTROLLED_DOCKER_SANDBOX_POC` 评分证据；这一路径只允许 allowlist 的 Python / pytest 检查，提交目录只读挂载、网络关闭、不自动 pull 镜像、不发布。

## 8. 安全边界

演示时必须遵守：

- AI 生成内容默认 `WAITING_REVIEW`。
- 审核通过前不得发布实验、试题、评分规则或 PPT。
- 不把标准答案展示给选手端。
- 不在日志、文档、前端或 Git 中写入 API Key。
- 不执行未知 Shell。
- 不无沙箱执行选手代码。
- 不操作生产数据库。
- 不创建、修改或删除真实云资源。
- 不启动真实 Agent。
- 不把真实 LLM 设置为默认 Provider。

## 9. 排错

### 缺少依赖

```powershell
python -m pip install -r requirements.txt
```

### 找不到 API Key

确认当前 PowerShell 中存在变量：

```powershell
python -c "import os; print('OPENAI_API_KEY present=', bool(os.environ.get('OPENAI_API_KEY')))"
```

不要打印 key 值本身。

### 模型名缺失

设置：

```powershell
$env:OPENAI_MODEL="<model-name>"
```

或在 CLI 命令中传 `--model "<model-name>"`。

### OpenAI-compatible endpoint 不支持 Responses API

真实 Demo Workflow 已支持在 endpoint 返回不支持时降级到 Chat Completions，并继续执行本地 DSL Schema 校验。仍建议先用最小 Lab DSL 请求验证模型输出质量。

### 真实 LLM 返回字段类型漂移

真实模型可能把 DSL 中的对象或字符串字段生成成数组、数字或说明性文本，也可能把 Lab `difficulty/tags/targetUsers`、Exam `questionType/totalScore/questions[*].score`、Grading check type 或 PPT slide type 写成同义词和非标准格式。当前已对 Lab `metadata.difficulty/durationMinutes/tags`、Lab `spec.objectives/targetUsers/materials/environment.resources`、Lab resources 中的 `cpuCores/memory/ramGb` 等资源别名、Exam `questionType/totalScore/questions[*].score/answer/gradingRef`、Grading `requiredLimits`、Grading check type 同义词、PPT slide type/bullets/speaker notes/duration 做确定性归一化；PPT 中不属于 Schema 的讲稿和时长会先转为审核可见的 bullets，再移除原始额外字段。归一化后仍会执行 Schema 校验，失败时不会写 Workflow Report、不会创建 AI Task、不会自动发布。

### 静态页面打不开

确认在项目根目录执行 `start .\frontend\real-demo.html`。这些页面不需要 dev server，也不需要后端服务。

## 10. 建议演示口径

可以这样收束：

```text
这套平台现在已经把 AI 生成结果先标准化为 DSL，再进入 CLI、审核、MCP 和前端演示链路。
真实大模型可以接入，但默认不自动发布；所有实验、试题、评分规则和 PPT 都先进入 WAITING_REVIEW。
当前演示版已经能展示真实 LLM 产出的 Lab / Exam / Grading / PPT、PPTX Artifact、评分 evidence 和人工审核闭环。
```
