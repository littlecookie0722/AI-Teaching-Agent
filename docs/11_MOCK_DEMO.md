# 11_MOCK_DEMO

Phase 1 一版效果演示。该演示只使用本地 Mock，不接入真实大模型、真实云资源、真实智能体，也不发布真实实验或考试。

## 一键主链路

```powershell
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1
```

输出为统一 JSON，核心字段包括：

- `mode`: 固定为 `MOCK_ONLY`
- `materialAnalysis`: 本地素材静态摘要和风险标记
- `steps`: Lab DSL、Exam DSL、Grading DSL、PPT DSL、Mock 评分报告
- `reviewRequired`: 固定为 `true`
- `publishBlockedUntilApproved`: 固定为 `true`
- `reportPath`: Mock 报告 JSON 保存路径

也可以指定输出路径：

```powershell
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/demo-report.json
python lab_cli.py workflow report --file examples/output/demo-report.json
```

Backend Mock 也可以直接跑同一条本地主链路：

```text
POST /api/workflow/demo body={"input":"examples/input/demo-source.md","reviewer":"teacher_1"}
```

该接口会创建 Lab、Exam、Grading、PPT 四个 `WAITING_REVIEW` 任务，并返回内嵌 Mock 评分报告；`sandboxExecuted=false`，不会执行选手代码。

## 素材静态分析

```powershell
python lab_cli.py material analyze --input examples/input/demo-source.md
```

Backend Mock：

```text
POST /api/materials/analyze body={"input":"examples/input/demo-source.md"}
```

素材分析只读取本地 UTF-8 文本，支持 Markdown / 文本 / Shell 后缀。输出固定 `realLlmCalled=false`、`remoteContentFetched=false`、`unknownShellExecuted=false`、`sandboxExecuted=false`。

## Workflow Run 日志

主链路执行后可查询本地运行日志：

```powershell
python lab_cli.py workflow list --workflow-id phase1_main_demo
python lab_cli.py workflow get --id <workflow_run_id>
```

Backend Mock：

```text
GET /api/workflow-runs?workflowId=phase1_main_demo
GET /api/workflow-runs/{id}
```

Workflow Run 会记录步骤顺序、traceId、报告路径和 Phase 1 安全标记。

## Artifact 清单

主链路执行后可查询本地产物元数据：

```powershell
python lab_cli.py artifact list --workflow-run-id <workflow_run_id>
python lab_cli.py artifact list --kind LAB_DSL
python lab_cli.py artifact get --id <artifact_id>
```

Backend Mock：

```text
GET /api/artifacts?workflowRunId=<workflow_run_id>
GET /api/artifacts/{id}
```

Artifact 记录素材分析、DSL 示例、Mock 评分报告和 Workflow 报告的本地路径与安全标记，不上传真实文件。

## DSL 校验

```powershell
python lab_cli.py dsl validate --kind lab --file templates/lab/examples/basic-lab.yaml
python lab_cli.py dsl validate --kind exam --file templates/exam/examples/notebook-fill-blank.yaml
python lab_cli.py dsl validate --kind grading --file templates/grading/examples/python-pytest.yaml
python lab_cli.py dsl validate --kind ppt --file templates/ppt/examples/course-ppt.yaml
```

## 审核与 Mock 发布

```powershell
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md
python lab_cli.py review batch-summary
python lab_cli.py review batch-summary --output examples/output/review-batch-summary.json
python lab_cli.py review detail --task-id <task_id>
python lab_cli.py review detail --task-id <task_id> --output examples/output/review-detail.json
python lab_cli.py review approve --task-id <task_id> --reviewer teacher_1
python lab_cli.py review publish --task-id <task_id>
python lab_cli.py review audit --task-id <task_id>
python lab_cli.py audit list --resource-type AI_TASK --resource-id <task_id>
```

Backend Mock 也可以发起本地 Lab DSL 生成：

```text
POST /api/labs/generate body={"input":"examples/input/demo-source.md"}
POST /api/exams/generate-from-lab body={"labId":"lab_demo"}
POST /api/ppt/generate body={"input":"examples/input/demo-source.md"}
```

Exam 生成返回本地 Exam DSL 和 Grading DSL，任务仍为 `WAITING_REVIEW`；标准答案不得展示给选手端。
PPT 生成返回本地 PPT DSL，任务仍为 `WAITING_REVIEW`，不会生成真实 PPT 文件。

`review publish` 只允许 `APPROVED` 任务进入 `COMPLETED`，并返回 `MOCK_ONLY` 发布结果。

Backend Mock 也提供本地审核状态流转：

```text
POST /api/ai-tasks/{id}/approve body={"reviewer":"teacher_1"}
POST /api/ai-tasks/{id}/reject body={"reviewer":"teacher_1","reason":"内容不符合要求"}
GET /api/review-task-summary
GET /api/review-tasks/{id}
GET /api/review-audit-events?taskId={id}
GET /api/audit-events?resourceType=AI_TASK&resourceId={id}
```

这些接口只更新本地 Mock store 并记录本地审计事件，不发布真实实验或考试。
`review batch-summary` 和 `GET /api/review-task-summary` 只做队列摘要，批量 approve/reject/publish 固定禁用。
`review detail` 和 `GET /api/review-tasks/{id}` 会把待审核任务、产物、Workflow 步骤、审计事件、发布阻断策略和 `reviewPage` 页面模型合并成一个审核详情。静态示例见 `examples/review-detail/lab-review-detail.json`。

## 审核中心静态原型

```powershell
start .\frontend\console.html
start .\frontend\dashboard.html
start .\frontend\audit.html
start .\frontend\audit-detail.html
start .\frontend\audit-incidents.html
start .\frontend\delivery.html
start .\frontend\review-center.html
start .\frontend\ai-tasks.html
```

`frontend/console.html` 是 Phase 1 前端 2.0 统一 Mock 控制台，串联 Dashboard、Audit、Delivery、Review、Labs、Exams、Grading、PPT、Environment、Skills 和 Provider 页面；页面不请求真实服务，不启动真实 Agent，不启用真实 Provider，不调用真实大模型，不创建真实云资源，不自动发布或真实发布。
`frontend/dashboard.html` 展示健康状态、待审核压力、Workflow Run、Artifact 清单和安全总览；页面不请求真实服务，不执行自动发布，不创建真实资源。
`frontend/audit.html` 展示 Provider / MCP Tool / Workflow / Operation / Review 本地 Mock 审计记录；页面不请求真实服务，不启动真实 MCP Server、真实 Agent 或真实 Provider，不读取密钥，不导出真实审计包。
`frontend/audit-detail.html` 展示单条 Provider / MCP 审计详情、Trace 关联、脱敏参数和错误上下文；页面不请求真实服务，不重试真实调用，不读取密钥，不执行真实沙箱或选手代码。
`frontend/audit-incidents.html` 展示失败审计记录的本地规则复盘、根因提示和安全 Mock 命令建议；页面不请求真实服务，不自动修复，不导出真实事故报告，不重试真实调用。
`frontend/operations-launchpad.html` 展示运营演示首页，集中打开 Console、Demo Map、Runbook、Acceptance、Delivery、Audit 和 Review Center；页面不请求真实服务，不执行命令，不上传交付包，不批量状态变更。

`delivery/DEMO_SCRIPT_CHECKLIST.md` 提供运营演示脚本检查清单，推荐按 Launchpad、Demo Map、Runbook、`phase1 check/export/report`、Acceptance、Delivery、Audit Incidents、审核门禁和安全边界顺序完成一次本地 Mock 讲解。
`frontend/operations-presenter.html` 展示运营 Presenter View，包含 12 个演示步骤、12 条 speakerCue、6 个验收信号、8 个禁止动作、175/175 交付状态和本地命令文本；页面不请求真实服务，不执行命令，不上传交付包，不批量状态变更，不启动真实 Agent。

`frontend/operations-signoff.html` 展示运营签收总览，包含 6/6 门禁、175/175 交付、20/20 自检、14/14 验收、6/6 安全断言、本地证据和禁用动作；页面不请求真实服务，不执行命令，不上传交付包，不批量状态变更，不启动真实 Agent。
`frontend/operations-demo-script.html` 展示运营演示脚本页面版，包含 12 步演示顺序、6 个验收信号、8 个禁止动作和本地命令文本；页面不请求真实服务，不执行命令，不上传交付包，不批量状态变更，不启动真实 Agent。
`frontend/operations-runbook.html` 展示运营本地入口、白名单验证命令、审计复盘入口和安全红线；页面不请求真实服务，不执行命令，不启动真实 Agent，不启用真实 Provider，不调用真实大模型，不上传交付包。
`frontend/operations-acceptance.html` 展示运营验收项、交付状态、Runbook、FAQ、Handoff、Phase 2 准入门禁和白名单命令；页面不请求真实服务，不执行命令，不上传交付包，不自动发布或真实发布。
`frontend/operations-demo-map.html` 展示运营演示路径和角色视角，按顺序串联总览、审计、审核、内容生成、评分环境和运营配置页面；页面不请求真实服务，不执行命令，不批量状态变更，不上传交付包。
`frontend/delivery.html` 展示本地 Phase 1 交付清单、验收摘要、`phase1 check`、`phase1 export` 和安全断言；页面不请求真实服务，不上传交付包，不启用真实 Provider，不自动发布或真实发布。
该页面是 Phase 1 Mock 原型，展示待审核队列、单任务详情、DSL 预览、Timeline 和审核操作栏。页面不请求真实服务，不执行真实审核，不执行真实发布；批量通过、批量驳回、批量发布按钮固定禁用。
`frontend/ai-tasks.html` 展示任务列表、状态过滤、待审核摘要、Workflow 日志入口和审核详情入口；页面不请求真实服务，不启动真实 Agent，不自动发布，不执行批量状态变更。

## Phase 1 本地演示验收 Runbook

```powershell
notepad .\delivery\README.md
notepad .\delivery\HANDOFF.md
notepad .\delivery\PHASE2_READINESS.md
notepad .\delivery\FAQ.md
notepad .\scripts\phase1-demo.runbook.md
start .\frontend\console.html
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
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_faq.py
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest tests/test_scripts_manifest.py
```

`delivery/phase1-delivery-index.json` 是运营交付入口索引，汇总本地静态页面、Runbook、交付包契约、验收报告和白名单验证命令。索引保持 `MOCK_ONLY`，不上传交付包，不新增真实执行能力。

`delivery/FAQ.md` 和 `delivery/phase1-faq.json` 汇总 Phase 1 常见失败场景和安全恢复步骤，覆盖缺少输入、Schema 校验失败、审核驳回缺少原因、未审核发布阻断、Provider 禁用、未知 Shell 风险、交付包缺失和测试依赖缺失等问题。FAQ 只引用本地白名单命令，不启用真实 Provider、不执行未知 Shell、不绕过人工审核。

`delivery/HANDOFF.md` 和 `delivery/phase1-handoff.json` 是运营交接检查清单，聚合 README、交付说明、FAQ、Runbook、静态预览、交付包、验收报告和安全确认项。清单只引用本地文件和白名单命令，不上传交付包，不新增真实执行能力。

`delivery/PHASE2_READINESS.md` 和 `delivery/phase2-readiness-gate.json` 是 Phase 2 准入门禁，定义通过哪些 Phase 1 验收信号后才可进入下一阶段规划和 Mock 设计。它不授权真实大模型、真实云资源、真实智能体、真实沙箱或真实发布。

`scripts/phase1-demo.runbook.json` 是机器可测试契约，`scripts/phase1-demo.runbook.md` 是人工演示说明。Runbook 只引用 `scripts/manifest.json` 中的白名单验证命令；本地页面预览只打开静态 HTML，不执行未知 Shell、不调用真实大模型、不启动真实智能体、不创建真实云资源、不执行真实沙箱、不自动发布或真实发布。

## Lab 生成静态原型

```powershell
start .\frontend\labs.html
start .\frontend\lab-generate.html
```

`frontend/labs.html` 展示 Lab 列表、状态筛选、待审核入口、生成入口和 DSL 预览入口；页面不请求真实服务，不批量变更状态，不自动发布，不发布真实实验。

该页面是 Phase 1 Lab 生成 Mock 原型，展示本地 Markdown 素材、`lab_generation_v0` Prompt 选择、素材静态分析、MockProvider 生成路径、Lab DSL 预览和 `WAITING_REVIEW` 审核门禁。页面不请求真实服务，不调用真实大模型，不抓取远程素材，不执行未知 Shell，不自动发布。

## Lab 审核详情静态原型

```powershell
start .\frontend\lab-review.html
```

该页面是 Phase 1 Lab 审核详情 Mock 原型，展示 `task_lab_demo`、Lab DSL 预览、来源素材、Artifact、Timeline、风险摘要和审核操作栏。页面不请求真实服务，不执行真实审核，不执行批量状态变更，不自动发布，不发布真实实验。

## PPT 管理静态原型

```powershell
start .\frontend\ppt.html
start .\frontend\ppt-review.html
```

`frontend/ppt.html` 展示 PPT DSL 清单、生成入口、审核入口、Slide Plan 摘要和真实 PPT 文件生成禁用策略。页面不请求真实服务，不调用真实大模型，不生成真实 PPT 文件，不自动发布或真实发布课件。
`frontend/ppt-review.html` 展示单个 PPT DSL 审核详情、Slide Plan、Timeline 和操作栏；页面不请求真实服务，不调用真实大模型，不生成真实 PPT 文件，不执行批量状态变更，不自动发布或真实发布课件。

## Exam 生成静态原型

```powershell
start .\frontend\exams.html
start .\frontend\exam-review.html
start .\frontend\exam-generate.html
```

`frontend/exams.html` 展示 Exam 列表、Grading DSL 关联、生成入口和候选人预览脱敏字段；页面不请求真实服务，不展示选手端标准答案，不执行真实沙箱，不自动发布或真实发布考试。
`frontend/exam-review.html` 展示单个 Exam DSL 与 Grading DSL 审核详情、Timeline 和操作栏；页面不请求真实服务，不展示选手端标准答案，不执行真实沙箱，不自动发布或真实发布考试。

该页面是 Phase 1 Exam 生成 Mock 原型，展示 `lab_demo` 输入、`exam_generation_v0` / `grading_generation_v0` Prompt 选择、Exam DSL / Grading DSL 预览和 `WAITING_REVIEW` 审核门禁。页面不请求真实服务，不调用真实大模型，不执行真实沙箱，不展示选手端标准答案，不自动发布考试。

## Provider Mock

```powershell
python lab_cli.py provider list
python lab_cli.py provider health
python lab_cli.py provider mock-generate --prompt-id lab_generation_v0 --input-ref examples/input/demo-source.md
python lab_cli.py provider mock-generate --prompt-id missing_prompt
python lab_cli.py provider audit --operation generateJson
```

Backend Mock 也提供相同能力：

```text
GET /api/providers
GET /api/providers/mock/health
POST /api/providers/mock/generate body={"promptId":"lab_generation_v0","inputRef":"examples/input/demo-source.md"}
GET /api/provider-audit-events?operation=generateJson
```

Provider Mock 只返回本地 DSL 示例引用，固定 `realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`，生成状态为 `WAITING_REVIEW`。
Provider 失败响应会带 `providerErrorContext`，用于确认失败路径没有创建任务、没有生成内容、没有读取密钥或访问网络。
Lab / Exam / Grading / PPT 的 Workflow Mock 生成已统一通过 `ai_workflows/provider_adapter_workflow.py` 调用 Provider Adapter，当前仍只路由到 MockProvider。
Provider Adapter 调用审计会记录 CLI 和 Backend Provider 成功/失败路径；Workflow Demo 的四个生成步骤也会写入同一套本地 Mock Store，可按 traceId 查询。

### MCP Tool Mock

```powershell
python lab_cli.py mcp list
python lab_cli.py mcp call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp audit --tool analyze_material
```

MCP Tool Mock 只读取 manifest 并调用 Backend Mock，不启动真实 MCP Server，不启动 Agent。`mcp call` 会写入本地 `mcpToolCallRecords`，可用 `mcp audit` 查看成功和失败路径。

## 环境状态 Mock

```powershell
python lab_cli.py env create --type vm --title "Ubuntu VM" --image ubuntu-22.04
python lab_cli.py env start --id <env_id>
python lab_cli.py env stop --id <env_id>
python lab_cli.py env reset --id <env_id>
```

Backend Mock 提供同样的本地状态流转：

```text
POST /api/environments/vm body={"title":"Ubuntu VM","image":"ubuntu-22.04","resources":{"cpu":2,"memoryGb":4}}
POST /api/environments/notebook body={"title":"Notebook","image":"python-3.11"}
POST /api/environments/{id}/start
POST /api/environments/{id}/stop
POST /api/environments/{id}/reset
```

这些接口只创建或更新本地 Mock store，不创建或操作真实 VM / Notebook。

环境管理静态原型：

```powershell
start .\frontend\environments.html
```

`frontend/environments.html` 展示 VM / Notebook Mock 记录、状态流转、资源参数和操作审计；页面不请求真实服务，不创建真实云资源，不操作真实 VM / Notebook，不销毁真实资源。

## Skills 管理静态原型

```powershell
start .\frontend\skills.html
```

`frontend/skills.html` 展示 Lab / Exam / Grading / PPT 四类运营复用 Skill，以及它们关联的 Prompt、Workflow、DSL Schema、示例输出和 CLI Mock。页面不请求真实服务，不启动真实智能体，不调用真实大模型，不允许 Prompt 散落到业务代码，不自动发布。

## Provider 设置静态原型

```powershell
start .\frontend\provider-settings.html
```

`frontend/provider-settings.html` 展示 MockProvider 启用态、OpenAI / Anthropic / Local Model 真实 Provider 禁用态、运行配置和 Mock 调用入口。页面不请求真实服务，不启用真实 Provider，不调用真实大模型，不读取或展示 API Key。

## 测试

```powershell
python lab_cli.py phase1 check
python -m pytest
```

## Mock 评分报告

```powershell
python lab_cli.py grade run --grading templates/grading/examples/python-pytest.yaml --output examples/output/grading-report.json
python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-grading-report.json
python lab_cli.py grade report --file examples/output/grading-report.json
start .\frontend\grading.html
start .\frontend\grading-review.html
start .\frontend\grading-report.html
```

评分报告为 `MOCK_ONLY`，不会执行选手代码。`templates/grading/examples/mixed-checks.yaml` 覆盖 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类评分项；报告会包含 `runner.id=mock_grading_runner`、`checkSummary.executed=0` 和每个 check 的 `executionPlan.strategy=MOCK_PLAN_ONLY`。
`frontend/grading.html` 展示 Grading DSL 清单、Mock 评分入口、评分报告入口和审计入口；页面不请求真实服务，不执行真实沙箱，不执行选手代码，不真实重评。
`frontend/grading-review.html` 展示单个 Grading DSL 审核详情、Mock 报告预览、Timeline 和操作栏；页面不请求真实服务，不执行真实沙箱，不执行选手代码，不真实重评，不自动发布或真实发布。
`frontend/grading-report.html` 展示 Mock 分数、`mock_grading_runner`、六类 check 明细、`MOCK_PLAN_ONLY` 执行计划、报告 JSON 和审计入口；页面不请求真实服务，不执行真实沙箱，不执行 Grading DSL 命令，不运行 pytest，不执行 Notebook，不读取真实 JSON/日志文件，不执行选手代码。

Backend Mock 也可以读取同一个本地报告文件：

```text
POST /api/grading/run body={"grading":"templates/grading/examples/python-pytest.yaml"}
POST /api/grading/run body={"grading":"templates/grading/examples/mixed-checks.yaml"}
GET /api/grading/report?file=examples/output/grading-report.json
```

`POST /api/grading/run` 只生成 Mock 报告，`sandboxExecuted=false`、`commandExecuted=false`，不会执行选手代码，也不会运行 pytest。

## 导出 Phase 1 Mock 交付包

```powershell
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
```

交付包包含 Delivery manifest、DSL manifest、Mock Workflow 报告、自检摘要、验收清单、验收摘要、安全断言、安全限制和推荐验证命令。Markdown 验收报告由交付包确定性渲染，仅用于 Phase 1 演示和运营预览，不代表真实发布内容。

关键验收字段：

- `acceptanceSummary.passed`: 是否通过 Phase 1 Mock 验收。
- `deliveryManifest.summary.missingRequired`: 必需交付物缺失数量。
- `safetyAssertions`: 真实大模型、真实云资源、真实沙箱执行、自动发布、选手代码执行均必须保持禁用。

## Phase 2 Provider 接入规划

```powershell
notepad providers\PHASE2_PROVIDER_PLAN.md
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
```

该规划只定义 MockProvider-first 的 `LLMProvider` 接口和真实 Provider 占位，不启用 OpenAI / Anthropic / Local Model，不读取真实密钥，不访问网络。
`providers/adapter.py` 提供统一 Provider Adapter 调用边界，但当前仍只路由到 MockProvider。
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
