# 10_OPERATIONS_GUIDE

运营交付阶段编写，包含实验生成、审核、Skills 复用和独立智能体交付说明。

> 当前状态：运营交付内容已完成阶段性收尾并暂停扩展。本文件仅作为现有本地演示、Mock 交付和历史验收资料索引。后续默认不新增运营页面、运营手册、运营验收清单、运营交付包或运营向 Skills / Prompt 文档；开发重心转向真实 LLM 内容生成、DSL 归一化、评分沙箱、审核导入和 MCP 核心工具。

## 当前收尾结论

- 现有 `frontend/operations-*`、`delivery/*` 运营资料保留为归档参考。
- 现有验收命令和白名单命令只用于复现历史 Mock / Demo 状态。
- 后续不再把运营交付作为默认开发入口。
- 如需恢复运营交付，必须由用户明确提出新的运营任务和验收范围。

## Phase 1 Mock 交付预览

当前只支持 Mock 交付包导出，不发布真实实验、考试或环境。

`delivery/phase1-delivery-index.json` 是 Phase 1 运营交付入口索引，汇总本地静态页面、Runbook、交付包契约、验收报告命令和测试命令。它只引用本地文件和 `scripts/manifest.json` 白名单命令，不新增真实执行能力。

推荐先阅读本地验收步骤：

```powershell
notepad .\delivery\README.md
notepad .\delivery\HANDOFF.md
notepad .\delivery\PHASE2_READINESS.md
notepad .\delivery\FAQ.md
notepad .\scripts\phase1-demo.runbook.md
```

```powershell
start .\frontend\console.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
start .\frontend\delivery.html
```

交付包包含：

- Delivery contract 信息
- Delivery manifest
- DSL manifest
- Mock Workflow 报告
- Phase 1 自检结果
- 验收清单和验收摘要
- 安全断言
- 安全限制
- 推荐验证命令

`phase1 report` 会把本地交付包渲染为 `examples/output/phase1-acceptance-report.md`，方便人工验收阅读。该报告是可再生成的本地输出，不调用真实 Provider、不发布真实内容。

`scripts/phase1-demo.runbook.json` 是机器可校验的演示契约，`scripts/phase1-demo.runbook.md` 是人工演示说明。Runbook 只引用 `scripts/manifest.json` 中的白名单验证命令；本地页面预览是人工动作，不作为自动脚本执行。

`delivery/FAQ.md` 是 Phase 1 常见问题和故障排查入口；`delivery/phase1-faq.json` 是对应机器契约。遇到 `VALIDATION_ERROR`、Schema 校验失败、未审核发布阻断、Provider 禁用、未知 Shell 风险或本地输出被清理时，先按 FAQ 使用白名单命令复现，不要启用真实 Provider、上传交付包或执行输入脚本。

`delivery/HANDOFF.md` 是运营交接检查清单；`delivery/phase1-handoff.json` 是对应机器契约。交接时先按清单阅读 README、交付 README、FAQ 和 Runbook，再打开本地静态页面，最后运行白名单验证命令生成交付包与验收报告。

`delivery/HIGH_RISK_MCP_HANDOFF.md` 是高风险 MCP Tool 运营交接清单；`delivery/high-risk-mcp-handoff.json` 是对应机器契约。交接时必须确认 `mcp-server/high-risk-tool-safety.contract.json` 覆盖 `publish_lab`、`publish_exam`、`destroy_environment` 和 `get_second_confirmation_status`：发布/销毁类工具只能创建审核意图，二次确认状态工具只能只读查询；真实 MCP Server、真实 Agent、真实发布、真实销毁、二次确认通过动作和绕过人工审核全部禁用。

`delivery/PHASE2_READINESS.md` 是 Phase 2 准入门禁说明；`delivery/phase2-readiness-gate.json` 是对应机器契约。通过该门禁只表示可以进入 Phase 2 规划和 Mock Workflow 设计，不表示可以直接启用真实 LLM、真实云资源、真实智能体、真实沙箱或真实发布。

`frontend/console.html` 是推荐的 Phase 1 前端 2.0 本地入口页，只做静态导航和安全状态展示，不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不创建真实云资源、不执行真实沙箱、不自动发布或真实发布。

`frontend/audit.html` 是 Phase 1 审计可观测只读页，聚合 Provider 调用审计、MCP Tool 调用记录、Workflow Run、操作审计和审核审计；页面不启动真实 MCP Server、不启动真实 Agent、不启用真实 Provider、不读取密钥、不调用真实大模型、不导出真实审计包。

`frontend/audit-detail.html` 是 Phase 1 审计详情钻取页，展示单条 Provider / MCP 审计记录的 Trace 关联、脱敏参数、错误上下文和关联 Workflow Step；页面不重试真实调用、不读取密钥、不执行真实沙箱、不执行选手代码、不自动发布或真实发布。

`frontend/audit-incidents.html` 是 Phase 1 审计异常复盘页，将失败 Provider / MCP 审计记录按本地规则归类为运营排查建议；页面不自动修复、不导出真实事故报告、不重试真实调用、不启用真实 Provider、不读取密钥。

`frontend/operations-launchpad.html` 是 Phase 1 运营演示首页，集中提供 Console、Demo Map、Runbook、Acceptance、Delivery、Audit 和 Review Center 的本地入口；页面不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型。

`frontend/operations-presenter.html` 是 Phase 1 运营讲解台，只读展示 12 个演示步骤、12 条 speakerCue、6 个验收信号、8 个禁止动作、175/175 交付状态和白名单命令；页面不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不运行真实沙箱、不执行选手代码、不自动发布或真实发布。

`frontend/operations-signoff.html` 是 Phase 1 运营签收总览，只读展示 6/6 门禁、175/175 交付、20/20 自检、14/14 验收、6/6 安全断言、本地证据和白名单命令；页面不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不运行真实沙箱、不执行选手代码、不自动发布或真实发布。

`frontend/access.html` 是 Phase 5 IP + 端口访问入口页，只读展示本地静态页面入口和未来规划端口；当前不启动真实 HTTP 服务、不监听端口、不绑定局域网或公网 IP、不配置反向代理或 TLS。访问说明和机器契约分别是 `delivery/ACCESS_ENTRYPOINTS.md` 与 `delivery/access-entrypoints.json`。

`delivery/PHASE5_MOCK_BASELINE.md` 是真实 LLM PoC 前的 Mock 基线冻结说明，确认当前交付为 175/175、默认 Provider 仍为 `mock`、所有生成结果仍走 `WAITING_REVIEW`。对应机器契约为 `delivery/phase5-mock-baseline.json`，只用于准入判断，不启用真实 Provider。

`delivery/OPERATIONS_MANUAL.md` 是 Phase 5 运营手册，面向运营人员说明本地入口、内容生成、审核门禁、交付导出、高风险 MCP 限制和最终签收顺序；对应机器契约为 `delivery/operations-manual.json`，只允许人工预览和白名单命令，不启用真实 Provider、真实 MCP Server 或真实 Agent。

`delivery/STANDALONE_AGENT_DELIVERY.md` 是 Phase 5 独立智能体 Mock 交付说明，描述未来独立智能体的目标、输入输出、工具白名单、禁止工具、状态、错误处理、审计证据和验收规则；对应机器契约为 `delivery/standalone-agent-delivery.json`，不连接真实外部平台、不启动真实 Agent、不调用真实 LLM、不启动真实 MCP Server。

`delivery/FINAL_SIGNOFF.md` 是 Phase 5 最终运营签收包，汇总本地文档、静态预览、交付导出、验收报告、高风险 MCP 交接和最终测试顺序；对应机器契约为 `delivery/final-signoff.json`，只允许人工确认和白名单命令验证，不启动真实 Provider、真实 MCP Server 或真实 Agent。

`delivery/DEMO_SCRIPT_CHECKLIST.md` 是运营演示脚本检查清单，建议演示时按 Launchpad、Demo Map、Runbook、`phase1 check/export/report`、Acceptance、Delivery、Audit Incidents、审核门禁和安全边界的顺序讲解；对应机器契约为 `delivery/phase1-demo-script-checklist.json`。

`frontend/operations-demo-script.html` 是 Phase 1 运营演示脚本只读页，把 `delivery/DEMO_SCRIPT_CHECKLIST.md` 的 12 步顺序、验收信号、白名单命令和禁止动作页面化；页面不执行命令、不上传交付包、不批量状态变更、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不自动发布或真实发布。

`frontend/operations-runbook.html` 是 Phase 1 运营 Runbook 只读工作台，汇总入口阅读、静态页面预览、白名单验证命令、审计复盘入口和安全红线；页面不执行命令、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不上传交付包、不自动发布或真实发布。

`frontend/operations-acceptance.html` 是 Phase 1 运营验收只读工作台，汇总交付状态、Runbook、FAQ、Handoff、Phase 2 准入门禁和白名单验证命令；页面不执行命令、不上传交付包、不启动真实 Agent、不启用真实 Provider、不调用真实大模型、不自动发布或真实发布。

`frontend/operations-demo-map.html` 是 Phase 1 运营演示路径页面地图，按运营、审核员、教师和研发视角串联所有静态 Mock 页面；页面不执行命令、不批量状态变更、不上传交付包、不启动真实 Agent、不启用真实 Provider、不调用真实大模型。

交付包验收重点：

- `acceptanceSummary.passed` 必须为 `true`。
- `deliveryManifest.summary.missingRequired` 必须为 `0`。
- `safetyAssertions[*].passed` 必须全部为 `true`。
- `workflowReport.reviewRequired` 必须为 `true`。
- `workflowReport.publishBlockedUntilApproved` 必须为 `true`。
- FAQ 中引用的验证命令必须都来自 `scripts/manifest.json` 白名单。
- Handoff 中引用的验证命令必须都来自 `scripts/manifest.json` 白名单，静态页面预览必须保持人工动作。
- Readiness gate 中的阻断项必须保持生效，真实能力接入需要新的明确任务和人工确认。

`frontend/delivery.html` 只用于本地可视化预览交付状态，不上传交付包、不启用真实 Provider、不调用真实大模型、不执行真实沙箱、不发布真实平台实体。

## 审核要求

- AI 生成内容默认 `WAITING_REVIEW`。
- 审核通过前不得发布。
- Phase 1 `review publish` 仅执行 Mock 状态流转，不发布真实平台实体。

## 素材预检

生成 Lab DSL 前建议先做素材静态分析：

```powershell
python lab_cli.py material analyze --input examples/input/demo-source.md
```

Backend Mock：

```text
POST /api/materials/analyze body={"input":"examples/input/demo-source.md"}
```

输出中的 `risks`、`riskCount` 和 `requiresHumanReview` 仅供人工审核参考。Phase 1 不执行输入素材中的 Shell，不抓取远程内容，不调用真实大模型。

## 审核队列

```powershell
python lab_cli.py review list
python lab_cli.py review list --task-type LAB_GENERATION
python lab_cli.py review batch-summary
python lab_cli.py review batch-summary --task-type LAB_GENERATION --limit 10
python lab_cli.py review batch-summary --output examples/output/review-batch-summary.json
python lab_cli.py review approve --task-id <task_id> --reviewer teacher_1
python lab_cli.py review reject --task-id <task_id> --reviewer teacher_1 --reason "不符合要求"
python lab_cli.py review detail --task-id <task_id>
python lab_cli.py review detail --task-id <task_id> --output examples/output/review-detail.json
python lab_cli.py review audit --task-id <task_id>
python lab_cli.py audit list --resource-type AI_TASK --resource-id <task_id>
```

`review list` 默认只显示 `WAITING_REVIEW` 任务。
`review batch-summary` 只用于批量查看和导出摘要，批量 approve/reject/publish 固定禁用。
`review detail` 会聚合任务、产物、Workflow 步骤、审计事件、发布阻断策略和页面模型，适合运营审核前确认来源与影响范围。可提交示例见 `examples/review-detail/lab-review-detail.json`。

Backend Mock 只读接口：

```text
GET /api/review-tasks
GET /api/review-tasks?taskType=LAB_GENERATION
GET /api/review-task-summary?status=WAITING_REVIEW
GET /api/review-tasks/{id}
GET /api/review-audit-events?taskId=<task_id>
GET /api/audit-events?resourceType=AI_TASK&resourceId=<task_id>
```

环境和评分操作也会写入统一操作审计：

```powershell
python lab_cli.py audit list --resource-type ENVIRONMENT
python lab_cli.py audit list --action MOCK_GRADING_RUN
```

## Workflow Run 日志

每次执行主链路都会写入本地 Workflow Run：

```powershell
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/demo-report.json
python lab_cli.py workflow list --workflow-id phase1_main_demo
python lab_cli.py workflow get --id <workflow_run_id>
```

Backend Mock 查询：

```text
GET /api/workflow-runs?workflowId=phase1_main_demo
GET /api/workflow-runs/{id}
```

日志仅用于 Phase 1 本地审计，固定不调用真实大模型、不执行真实沙箱、不真实发布。

## Artifact 清单

主链路和单步生成会记录本地产物清单：

```powershell
python lab_cli.py artifact list
python lab_cli.py artifact list --workflow-run-id <workflow_run_id>
python lab_cli.py artifact get --id <artifact_id>
```

Backend Mock：

```text
GET /api/artifacts?kind=LAB_DSL
GET /api/artifacts?workflowRunId=<workflow_run_id>
GET /api/artifacts/{id}
```

Artifact 仅用于运营预览和审核定位，记录本地路径、状态和安全标记，不上传真实文件、不发布平台实体。

## Provider Mock 检查

Phase 1 只允许使用 Mock Provider，运营预览时可用以下命令确认：

```powershell
python lab_cli.py provider list
python lab_cli.py provider health
python lab_cli.py provider mock-generate --prompt-id lab_generation_v0
python lab_cli.py provider audit --operation generateJson
```

Provider Mock 只返回本地 DSL 示例引用，生成状态仍为 `WAITING_REVIEW`，不会调用真实大模型、不会读取密钥、不会访问网络。

Phase 2 Provider 接入规划只作为下一阶段设计输入，不能视为真实 Provider 启用授权：

```powershell
notepad providers\PHASE2_PROVIDER_PLAN.md
python -m pytest tests/test_phase2_provider_plan.py
```

`providers/PHASE2_PROVIDER_PLAN.md` 记录 `LLMProvider`、`generateText`、`generateJson`、`streamGenerate` 的接口形状，以及 OpenAI / Anthropic / Local Model 的禁用占位。当前仍不读取 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 或 `LOCAL_MODEL_ENDPOINT` 的真实值。

Provider Adapter 只用于统一调用边界，当前仍只路由到 MockProvider：

```powershell
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
```

`providers/adapter.py` 会为返回结果补充 `adapterId=mock_provider_adapter`、`interfaceName=LLMProvider` 和 `operation=generateJson` 等字段，便于后续 Workflow 统一接入。
Provider Adapter 错误路径会返回 `providerErrorContext`，用于确认失败时仍不调用真实 LLM、不读取密钥、不访问网络、不创建任务、不生成内容。
Provider Adapter 调用审计会记录 registry、health、generateJson 的成功和失败路径，可通过 `provider audit` 或 `/api/provider-audit-events` 查询，事件仍固定为 `MOCK_ONLY`。
Workflow Mock 的 Lab / Exam / Grading / PPT 生成步骤也会写入 Provider 调用审计；运营排查主链路时可按 `traceId` 查询四条 `generateJson` 审计事件。
`ai_workflows/provider_adapter_workflow.py` 会把 Lab / Exam / Grading / PPT 四类 Mock 生成统一收口到 Adapter，并继续返回 `WAITING_REVIEW`。

## MCP Tool Mock 检查

Phase 1 只允许本地 MCP Tool Mock 调用，不启动真实 MCP Server：

```powershell
python lab_cli.py mcp list
python lab_cli.py mcp call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp audit --tool analyze_material
python -m pytest tests/test_mcp_manifest.py tests/test_mcp_mock_tools.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py tests/test_high_risk_mcp_handoff.py tests/test_final_signoff.py
```

`mcp call` 会读取 `mcp-server/tools.manifest.json` 并映射到 Backend Mock，成功响应中必须保持 `realMcpServerStarted=false`、`realAgentStarted=false`。调用记录会进入本地 `mcpToolCallRecords`，便于运营复盘失败原因；参数只保存 key 和脱敏预览。

高风险 MCP 交接时只允许打开 `frontend/review-center.html` 和 `frontend/audit.html` 做人工查看，不允许将 `publish_lab`、`publish_exam` 或 `destroy_environment` 解释为真实执行授权；`get_second_confirmation_status` 也只能说明 Mock 二次确认状态，不提供真实确认入口。

## 限制说明

- 不接入真实大模型。
- 不创建真实 VM 或 Notebook。
- 不导入生产数据库。
- 不执行未知 Shell 脚本。
- 不无沙箱执行选手代码。
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
