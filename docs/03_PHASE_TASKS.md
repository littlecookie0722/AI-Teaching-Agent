# 03_PHASE_TASKS

# Phase 1：底座

## P1-01 创建目录结构
- 目标：搭建项目骨架
- 验收：关键目录存在且有 README

## P1-02 创建 DSL Schema
- 目标：定义 Lab / Exam / Grading / PPT Schema
- 验收：Schema 合法，有示例，有校验测试

## P1-03 创建 CLI Mock
- 目标：lab-cli 支持核心命令
- 验收：所有命令返回统一 JSON

## P1-04 创建 AI Task 状态模型
- 目标：统一 AI 任务状态
- 验收：状态流转测试通过

## P1-05 创建人工审核流
- 目标：AI 生成结果默认 WAITING_REVIEW
- 验收：未审核不可发布

## P1-06 创建 Mock Workflow 契约
- 目标：把 Phase 1 主链路和生成子流程沉淀为可复用 manifest
- 验收：`ai-workflows/workflow.manifest.json` 存在，生成类输出默认 `WAITING_REVIEW`，安全限制可测试

## P1-07 创建 Prompt 契约
- 目标：集中管理 Prompt 模板、版本、输出 Schema 和审核要求
- 验收：`prompts/manifest.json` 存在，Prompt 路径均在 `prompts/` 下，生成类 Prompt 绑定 DSL Schema

## P1-08 创建 Skill 契约
- 目标：沉淀运营可复用 Skill，并关联 Prompt、Workflow、DSL Schema 和 CLI Mock
- 验收：`skills/manifest.json` 覆盖 Lab / Exam / Grading / PPT 四类生成能力，引用路径均存在

## P1-09 创建 Frontend 页面契约
- 目标：为前端 2.0 明确页面、组件、Mock API 依赖和安全边界
- 验收：`frontend/ui.manifest.json` 和 `frontend/mock-data.json` 存在，自动发布/密钥/标准答案/真实资源动作均被禁用

## P1-10 创建 Scripts 安全契约
- 目标：定义 Phase 1 允许的本地验证命令和禁止的高风险脚本模式
- 验收：`scripts/manifest.json` 存在，禁止未知 Shell、破坏性命令、云资源命令、生产访问和选手代码执行

## P1-11 创建配置与密钥安全契约
- 目标：定义 Phase 1 Mock 默认配置、`.env.example` 示例和密钥来源规则
- 验收：`config/runtime.contract.json` 和 `.env.example` 存在，真实 Provider 默认禁用，示例文件不包含真实密钥

## P1-12 创建本地产物忽略契约
- 目标：定义 Phase 1 本地密钥、Mock Store、生成报告、缓存和交付包归档的忽略规则
- 验收：`.gitignore` 和 `config/local-artifacts.contract.json` 存在，`.env.example` 与 `examples/output/README.md` 保持可跟踪，生成 JSON 和本地状态文件被忽略

## P1-13 创建 Phase 1 交付包契约
- 目标：定义本地 Mock 交付包内容、验收清单、安全断言和推荐验证命令
- 验收：`config/delivery-package.contract.json` 存在，`phase1 export` 输出 `deliveryManifest`、`acceptanceChecklist`、`acceptanceSummary` 和 `safetyAssertions`

## P1-14 创建审核审计事件
- 目标：记录 approve / reject / Mock publish 的本地审计事件，支持 CLI 和 Backend Mock 查询
- 验收：`review audit` 和 `GET /api/review-audit-events` 可按任务、动作、人员过滤，事件保持 `mode=MOCK_ONLY`、`realPublish=false`

## P1-15 创建统一操作审计事件
- 目标：记录审核、环境 Mock 操作和 Mock 评分的本地统一审计事件
- 验收：`audit list` 和 `GET /api/audit-events` 可按资源类型、资源 ID、动作、人员过滤，事件保持不调用真实 LLM、不改动真实云资源、不执行选手代码、不真实发布

## P1-16 创建 Provider Mock 抽象
- 目标：预留统一 Provider 接口，Phase 1 只实现确定性 MockProvider
- 验收：`provider list`、`provider health`、`provider mock-generate` 和 `/api/providers` 可用，只有 `mock` Provider 启用，真实 Provider 禁用且不读取密钥、不访问网络、不调用真实 LLM

## P1-17 创建 Workflow Run 日志
- 目标：记录 Mock 主链路每次运行的步骤、traceId 和安全标记
- 验收：`workflow list/get` 和 `GET /api/workflow-runs` 可查询本地运行记录，事件保持 `MOCK_ONLY`，不调用真实 LLM、不执行真实沙箱、不真实发布

## P1-18 创建素材分析 Mock
- 目标：在 DSL 生成前对本地 Markdown / 文本 / Shell 素材做静态摘要和风险标记
- 验收：`material analyze`、`POST /api/materials/analyze`、Lab 生成和 Workflow Demo 均返回 `materialAnalysis`，并保持 `realLlmCalled=false`、`remoteContentFetched=false`、`unknownShellExecuted=false`、`sandboxExecuted=false`

## P1-19 创建 Artifact Mock 清单
- 目标：统一记录素材分析、DSL 示例、Mock 评分报告和 Workflow 报告的本地产物元数据
- 验收：`artifact list/get` 和 `GET /api/artifacts` 可按类型、任务、Workflow Run、traceId 查询，记录保持 `MOCK_ONLY`，不上传真实文件、不连接远程对象存储、不发布产物

## P1-20 创建审核详情 Mock
- 目标：聚合单个审核任务的 AI Task、Artifact、Workflow Step、审核审计、统一操作审计和发布阻断策略
- 验收：`review detail` 和 `GET /api/review-tasks/{id}` 可返回统一审核详情和 `reviewPage` 页面模型，仍保持 `MOCK_ONLY`，审核通过前禁止发布

## P1-21 创建审核详情示例输出
- 目标：提供可提交的静态审核详情 JSON，并支持 CLI 导出本地审核详情
- 验收：`examples/review-detail/lab-review-detail.json` 可被测试校验，`review detail --output` 可写入本地 JSON，安全标记保持禁用真实执行

## P1-22 创建审核队列批量摘要 Mock
- 目标：支持运营批量查看待审核任务摘要，但不允许批量审核或批量发布
- 验收：`review batch-summary` 和 `GET /api/review-task-summary` 可返回队列卡片、状态统计和批量动作禁用策略，可导出本地 JSON

## P1-23 创建审核中心静态 Mock 原型
- 目标：提供前端 2.0 审核中心的一版可视化静态原型，展示审核队列、单任务详情、DSL 预览、Timeline 和操作栏
- 验收：`frontend/review-center.html` 可直接打开，页面契约声明 `/review-center`，批量 approve / reject / publish 和真实发布固定禁用

## P1-24 创建 Lab 生成静态 Mock 原型
- 目标：提供前端 2.0 Lab 生成页的一版可视化静态原型，展示本地素材分析、Prompt 选择、Lab DSL 预览和审核门禁
- 验收：`frontend/lab-generate.html` 可直接打开，页面契约声明 `/labs/generate` 原型，生成结果固定 `WAITING_REVIEW`，真实 LLM、远程素材抓取、未知 Shell 执行和自动发布固定禁用

## P1-25 创建评分报告静态 Mock 原型
- 目标：提供前端 2.0 自动评分报告页的一版可视化静态原型，展示 Mock 分数、check 明细、审计入口和安全标记
- 验收：`frontend/grading-report.html` 可直接打开，页面契约声明 `/grading/:id/report` 原型，真实沙箱、选手代码执行、未知 Shell 执行和真实发布固定禁用

## P1-26 创建 AI 任务中心静态 Mock 原型
- 目标：提供前端 2.0 AI 任务中心的一版可视化静态原型，展示任务列表、状态过滤、待审核摘要、Workflow 日志入口和审核详情入口
- 验收：`frontend/ai-tasks.html` 可直接打开，页面契约声明 `/ai-tasks` 原型，自动发布、批量状态变更、真实 Agent 运行、真实 LLM 调用和密钥展示固定禁用

## P1-27 创建 Dashboard 静态 Mock 原型
- 目标：提供前端 2.0 Dashboard 的一版可视化静态原型，聚合健康状态、待审核压力、Workflow Run、Artifact 和安全总览
- 验收：`frontend/dashboard.html` 可直接打开，页面契约声明 `/dashboard` 原型，自动发布、批量状态变更、真实 LLM、真实云资源、真实沙箱和密钥展示固定禁用

## P1-28 创建 Exam 生成静态 Mock 原型
- 目标：提供前端 2.0 Exam 生成页的一版可视化静态原型，展示 Lab ID 输入、Exam DSL / Grading DSL 预览、审核门禁和标准答案隐藏策略
- 验收：`frontend/exam-generate.html` 可直接打开，页面契约声明 `/exams/generate` 原型，生成结果固定 `WAITING_REVIEW`，标准答案不得展示给选手端，真实 LLM、真实沙箱、自动发布和真实发布固定禁用

## P1-29 创建环境管理静态 Mock 原型
- 目标：提供前端 2.0 环境管理页的一版可视化静态原型，展示 VM / Notebook Mock 记录、状态流转、资源参数和操作审计
- 验收：`frontend/environments.html` 可直接打开，页面契约声明 `/environments` 原型，真实云资源创建/变更/销毁、真实沙箱、选手代码执行和密钥展示固定禁用

## P1-30 创建 Skills 管理静态 Mock 原型
- 目标：提供前端 2.0 Skills 管理页的一版可视化静态原型，展示 Skill、Prompt、Workflow、DSL Schema、示例输出和 CLI Mock 的关联关系
- 验收：`frontend/skills.html` 可直接打开，页面契约声明 `/skills` 原型，真实智能体、真实 LLM、Prompt 散落业务代码、自动发布和密钥展示固定禁用

## P1-31 创建 Provider 设置静态 Mock 原型
- 目标：提供前端 2.0 Provider 设置页的一版可视化静态原型，展示 MockProvider 启用态、真实 Provider 禁用态、运行配置和密钥不展示策略
- 验收：`frontend/provider-settings.html` 可直接打开，页面契约声明 `/settings/providers` 原型，真实 Provider、真实 LLM、网络访问、密钥展示和 Prompt 散落业务代码固定禁用

## P1-32 创建 Lab 审核详情静态 Mock 原型
- 目标：提供前端 2.0 Lab 审核详情页的一版可视化静态原型，展示单个 Lab DSL 审核任务、来源素材、Artifact、Timeline、风险摘要和操作栏
- 验收：`frontend/lab-review.html` 可直接打开，页面契约声明 `/labs/:id/review` 原型，审核通过/驳回只保持单任务 Mock 操作，批量状态变更、自动发布、真实发布和标准答案泄露固定禁用

## P1-33 创建 Labs 管理静态 Mock 原型
- 目标：提供前端 2.0 Labs 管理页的一版可视化静态原型，展示 Lab 列表、状态筛选、待审核入口、生成入口和 DSL 预览入口
- 验收：`frontend/labs.html` 可直接打开，页面契约声明 `/labs` 原型，批量状态变更、自动发布、真实发布、真实 LLM 和密钥展示固定禁用

## P1-34 创建 Exams 管理静态 Mock 原型
- 目标：提供前端 2.0 Exams 管理页的一版可视化静态原型，展示 Exam 列表、Grading DSL 关联、生成入口和标准答案隐藏策略
- 验收：`frontend/exams.html` 可直接打开，页面契约声明 `/exams` 原型，标准答案选手端隐藏，批量状态变更、自动发布、真实发布、真实 LLM 和真实沙箱固定禁用

## P1-35 创建 Grading 管理静态 Mock 原型
- 目标：提供前端 2.0 Grading 管理页的一版可视化静态原型，展示 Grading DSL 清单、Mock 评分入口、评分报告入口和审计入口
- 验收：`frontend/grading.html` 可直接打开，页面契约声明 `/grading` 原型，真实沙箱、选手代码执行、未知 Shell、真实重评和真实发布固定禁用

## P1-36 创建 Exam 审核详情静态 Mock 原型
- 目标：提供前端 2.0 Exam 审核详情页的一版可视化静态原型，展示单个 Exam DSL、Grading DSL、Timeline、审核策略和标准答案隐藏策略
- 验收：`frontend/exam-review.html` 可直接打开，页面契约声明 `/exams/:id/review` 原型，审核通过/驳回只保持单任务 Mock 操作，标准答案选手端隐藏，真实沙箱、自动发布、真实发布和批量状态变更固定禁用

## P1-37 创建 Grading 审核详情静态 Mock 原型
- 目标：提供前端 2.0 Grading 审核详情页的一版可视化静态原型，展示单个 Grading DSL、Mock 报告预览、Timeline、审核策略和真实执行禁用策略
- 验收：`frontend/grading-review.html` 可直接打开，页面契约声明 `/grading/:id/review` 原型，审核通过/驳回只保持单任务 Mock 操作，真实沙箱、选手代码执行、未知 Shell、真实重评、自动发布和真实发布固定禁用

## P1-38 创建 PPT 管理静态 Mock 原型
- 目标：提供前端 2.0 PPT 管理页的一版可视化静态原型，展示 PPT DSL 清单、生成入口、审核入口和真实 PPT 文件生成禁用策略
- 验收：`frontend/ppt.html` 可直接打开，页面契约声明 `/ppt` 原型，只展示本地 PPT DSL 元数据，真实大模型、真实 PPT 文件生成、自动发布、真实发布和密钥展示固定禁用

## P1-39 创建 PPT 审核详情静态 Mock 原型
- 目标：提供前端 2.0 PPT 审核详情页的一版可视化静态原型，展示单个 PPT DSL、Slide Plan、Timeline、审核策略和真实 PPT 文件生成禁用策略
- 验收：`frontend/ppt-review.html` 可直接打开，页面契约声明 `/ppt/:id/review` 原型，审核通过/驳回只保持单任务 Mock 操作，真实大模型、真实 PPT 文件生成、自动发布、真实发布、批量状态变更和密钥展示固定禁用

## P1-40 创建 Delivery 交付验收静态 Mock 原型
- 目标：提供前端 2.0 交付验收页的一版可视化静态原型，展示交付清单、验收摘要、Phase 1 自检、推荐命令和安全断言
- 验收：`frontend/delivery.html` 可直接打开，页面契约声明 `/delivery` 原型，只展示本地 Mock 交付状态，真实大模型、真实云资源、真实沙箱、上传交付包、自动发布、真实发布和密钥展示固定禁用

## P1-41 创建 Frontend 2.0 统一 Mock 控制台
- 目标：提供前端 2.0 统一入口页，把 Dashboard、Delivery、Review、Labs、Exams、Grading、PPT、Environment、Skills 和 Provider 静态 Mock 原型串联起来
- 验收：`frontend/console.html` 可直接打开，页面契约声明 `/console` 原型，只做本地静态导航和安全状态展示，真实 Agent、真实 Provider、真实大模型、真实云资源、真实沙箱、自动发布、真实发布、批量状态变更和密钥展示固定禁用

## P1-42 创建 Phase 1 本地演示验收 Runbook
- 目标：沉淀可人工复现、可审计、可测试的 Phase 1 本地演示验收步骤
- 验收：`scripts/phase1-demo.runbook.json` 和 `scripts/phase1-demo.runbook.md` 存在，Runbook 只引用 `scripts/manifest.json` 中的白名单验证命令，未知 Shell、真实 LLM、真实云资源、真实沙箱、自动发布和真实发布固定禁用

## P1-43 创建 Phase 1 验收报告 Mock
- 目标：把本地 Mock 交付包确定性渲染为人工可读 Markdown 验收报告
- 验收：`phase1 report` 可读取 `examples/output/phase1-delivery-package.json` 并输出 `examples/output/phase1-acceptance-report.md`，CLI 仍返回统一 JSON，报告不重新生成内容、不调用真实 Provider、不发布真实内容

## P1-44 创建 Phase 1 运营交付入口索引
- 目标：汇总本地静态页面、Runbook、交付包契约、验收报告命令和测试命令，形成运营可交接入口清单
- 验收：`delivery/phase1-delivery-index.json` 和 `delivery/README.md` 存在，索引只引用本地文件和 `scripts/manifest.json` 白名单命令，真实 LLM、真实 Agent、真实云资源、真实沙箱、未知 Shell、自动发布和真实发布固定禁用

## P1-45 创建 Phase 1 运营 FAQ / 故障排查 Mock
- 目标：沉淀 Phase 1 本地验收常见失败场景、恢复步骤、白名单验证命令和安全红线，便于运营交接时定位问题
- 验收：`delivery/FAQ.md` 和 `delivery/phase1-faq.json` 存在，FAQ 只引用本地文件和 `scripts/manifest.json` 白名单命令，不接入真实大模型、不创建真实云资源、不执行未知 Shell、不绕过人工审核、不上传交付包

## P1-46 创建 Phase 1 运营交接清单 Mock
- 目标：把 README、交付索引、FAQ、Runbook、静态预览、验收证据和安全断言聚合为运营交接检查清单
- 验收：`delivery/HANDOFF.md` 和 `delivery/phase1-handoff.json` 存在，清单只引用本地文件、人工预览和 `scripts/manifest.json` 白名单命令，真实 LLM、真实 Agent、真实云资源、真实沙箱、未知 Shell、自动发布和真实发布固定禁用

## P1-47 创建 Phase 2 准入门禁 Mock
- 目标：定义 Phase 1 本地 Mock 交付进入 Phase 2 规划和 Mock Workflow 设计前必须满足的验收信号、允许下一步和阻断项
- 验收：`delivery/PHASE2_READINESS.md` 和 `delivery/phase2-readiness-gate.json` 存在，门禁只允许进入 Phase 2 规划/Mock 设计，不授权真实 LLM、真实 Agent、真实云资源、真实沙箱、未知 Shell、自动发布或真实发布

## P1-48 创建 Phase 2 Provider 接入规划 Mock
- 目标：定义 Phase 2 `LLMProvider` 接口、MockProvider-first 策略、真实 Provider 占位、密钥来源、Schema 校验、日志脱敏和审核门禁
- 验收：`providers/PHASE2_PROVIDER_PLAN.md` 和 `providers/phase2-provider-plan.contract.json` 存在，规划仍保持 `MOCK_ONLY`，不启用真实 Provider，不读取真实密钥，不访问网络，不允许绕过 `WAITING_REVIEW`

## P1-49 创建 Mock-only Provider Adapter
- 目标：为后续 Workflow 提供统一 `LLMProvider` 调用边界，让 CLI 和 Backend Mock 不再直接绑定 `MockProvider.generate_json`
- 验收：`providers/adapter.py` 和 `providers/provider-adapter.contract.json` 存在，adapter 只允许 `mock` Provider，`generateJson` 仍执行 Schema 校验，`streamGenerate` 固定暂缓，真实 Provider、真实密钥和网络访问固定禁用

## P1-50 将 Mock Workflow 接入 Provider Adapter
- 目标：让 Lab / Exam / Grading / PPT 的 Mock Workflow 生成步骤统一通过 `ai_workflows/provider_adapter_workflow.py` 调用 Provider Adapter，避免 Workflow 层直接读取生成模板
- 验收：CLI 与 Backend Mock 的单步生成和主链路报告均包含 `provider.adapterId=mock_provider_adapter`，真实 LLM、密钥读取、网络访问和自动发布仍固定禁用

## P1-51 创建 Provider Adapter 错误矩阵 Mock
- 目标：把禁用 Provider、缺少 Prompt、未知 Prompt、outputKind 不匹配和 streamGenerate 暂缓等失败路径沉淀为 `providers/provider-adapter-errors.contract.json`
- 验收：CLI 与 Backend Mock 的 Provider 失败响应均保持统一 JSON，并对 Provider 错误额外返回 `providerErrorContext`，确认不调用真实 LLM、不读取密钥、不访问网络、不创建 AI Task、不生成内容、不绕过审核

## P1-52 创建 Provider Adapter 调用审计 Mock
- 目标：记录 `provider list/health/mock-generate` 与 `/api/providers*` 的成功和失败调用，沉淀为本地 `providerCallAuditEvents`
- 验收：`python lab_cli.py provider audit` 和 `GET /api/provider-audit-events` 可按 Provider、操作、状态、Prompt、Trace、人员过滤；审计事件仍保持 `MOCK_ONLY`，不调用真实 LLM、不读取密钥、不访问网络、不创建任务、不自动发布

## P1-53 将 Workflow Mock 接入 Provider 调用审计
- 目标：Lab / Exam / Grading / PPT 单步生成与 `phase1_main_demo` 主链路的 Provider Adapter 调用都写入本地 `providerCallAuditEvents`
- 验收：`workflow demo` 的四个生成步骤返回 `providerCallAuditEvent`，并可通过 `provider audit --trace-id <traceId>` 或 `GET /api/provider-audit-events?traceId=<traceId>` 查询；审计仍保持 `MOCK_ONLY`，不启用真实 Provider、不读取密钥、不访问网络、不自动发布

## P1-54 创建 MCP Tool Mock 调用层
- 目标：在不启动真实 MCP Server 的前提下，提供 `mcp_server/mock_tools.py` 和 `lab-cli mcp list/call`，把 MCP manifest 工具映射到 Backend Mock
- 验收：`python lab_cli.py mcp list` 和 `python lab_cli.py mcp call --tool analyze_material --arguments ...` 返回统一 JSON；成功响应标记 `realMcpServerStarted=false`、`realAgentStarted=false`，工具调用不得访问真实 Provider、真实云资源或真实沙箱

## P1-55 创建 MCP Tool 调用审计与运行记录
- 目标：记录 `mcp call` 成功、参数校验失败和 Backend Mock 失败路径，沉淀为本地 `mcpToolCallRecords`
- 验收：`python lab_cli.py mcp audit`、`GET /api/mcp-tool-call-records` 和 MCP Tool `list_mcp_tool_call_records` 可按 Tool、状态、Trace、Actor、Backend Path 过滤；记录必须保持 `MOCK_ONLY`，不启动真实 MCP Server、不启动 Agent、不调用真实 LLM、不读取密钥、不访问网络、不操作云资源

## P1-56 创建审计可观测静态 Mock 原型
- 目标：新增 `/audit` 静态页面，聚合 Provider 调用审计、MCP Tool 调用记录、Workflow Run、统一操作审计和审核审计
- 验收：`frontend/audit.html` 可直接打开，页面契约声明 `/audit` 原型，只读展示本地 Mock 审计记录；真实 Provider、真实 MCP Server、真实 Agent、真实大模型、真实云资源、真实沙箱、自动发布、真实发布和密钥展示固定禁用

## P1-57 创建审计详情钻取静态 Mock 原型
- 目标：新增 `/audit/:id` 静态页面，展示单条 Provider / MCP 审计记录的 Trace 关联、脱敏参数、错误上下文和关联 Workflow Step
- 验收：`frontend/audit-detail.html` 可直接打开，页面契约声明 `/audit/:id` 原型，只读展示本地 Mock 审计详情；重试真实调用、启动真实 Agent、启用真实 Provider、读取密钥、真实沙箱、选手代码执行、自动发布和真实发布固定禁用

## P1-58 创建审计异常复盘静态 Mock 原型
- 目标：新增 `/audit/incidents` 静态页面，将失败 Provider / MCP 审计记录按本地规则归类为运营排查建议
- 验收：`frontend/audit-incidents.html` 可直接打开，页面契约声明 `/audit/incidents` 原型，只读展示异常分类、根因提示和安全 Mock 命令；自动修复、导出真实事故报告、重试真实调用、启动真实 Agent、启用真实 Provider、读取密钥、真实沙箱、选手代码执行、自动发布和真实发布固定禁用

## P1-59 创建运营 Runbook 页面化静态 Mock 原型
- 目标：新增 `/operations/runbook` 静态页面，把运营本地入口、白名单验证命令、审计复盘入口和安全红线聚合成只读工作台
- 验收：`frontend/operations-runbook.html` 可直接打开，页面契约声明 `/operations/runbook` 原型，只读展示 `scripts/phase1-demo.runbook.json`、`scripts/manifest.json` 和本地 Mock 命令；执行命令、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、上传交付包、自动发布和真实发布固定禁用

## P1-60 创建运营验收总览静态 Mock 原型
- 目标：新增 `/operations/acceptance` 静态页面，把交付状态、Runbook、FAQ、Handoff、Phase 2 准入门禁和白名单验证命令聚合成运营验收面板
- 验收：`frontend/operations-acceptance.html` 可直接打开，页面契约声明 `/operations/acceptance` 原型，只读展示验收项、关联静态页面、白名单命令和安全断言；执行命令、上传交付包、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布固定禁用

## P1-61 创建运营演示路径页面地图静态 Mock 原型
- 目标：新增 `/operations/demo-map` 静态页面，按角色和演示顺序串联全部 Phase 1 前端 Mock 页面
- 验收：`frontend/operations-demo-map.html` 可直接打开，页面契约声明 `/operations/demo-map` 原型，只读展示 6 段演示路径、角色视角、白名单命令和安全断言；执行命令、批量状态变更、上传交付包、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布固定禁用

## P1-62 创建运营演示首页 Launchpad 静态 Mock 原型
- 目标：新增 `/operations/launchpad` 静态页面，把 Console、Demo Map、Presenter、Demo Script、Runbook、Acceptance、Delivery、Audit 和 Review Center 聚合成运营演示入口
- 验收：`frontend/operations-launchpad.html` 可直接打开，页面契约声明 `/operations/launchpad` 原型，只读展示 9 个入口卡片、7 条验收命令、交付 175/175、交接说明和安全断言；执行命令、上传交付包、批量状态变更、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布固定禁用

## P1-63 创建运营演示脚本检查清单 Mock
- 目标：新增 `delivery/DEMO_SCRIPT_CHECKLIST.md` 和 `delivery/phase1-demo-script-checklist.json`，把运营演示顺序、口径、验收信号和禁用动作沉淀为可读、可测的清单
- 验收：清单必须从 Launchpad 开始，依次覆盖 Demo Map、Runbook、`phase1 check/export/report`、Acceptance、Delivery、Audit Incidents、审核门禁和安全边界；只引用本地静态页面和白名单验证命令，不得变成自动执行脚本，真实 LLM、真实 Agent、真实云资源、真实沙箱、未知 Shell、选手代码执行、远程上传、自动发布、真实发布、密钥展示和选手端标准答案展示固定禁用

## P1-64 创建运营演示脚本静态 Mock 原型
- 目标：新增 `/operations/demo-script` 静态页面，把 `delivery/DEMO_SCRIPT_CHECKLIST.md` 和 `delivery/phase1-demo-script-checklist.json` 页面化，供运营按固定顺序演示
- 验收：`frontend/operations-demo-script.html` 可直接打开，页面契约声明 `/operations/demo-script` 原型，只读展示 12 步演示顺序、6 个验收信号、8 个禁止动作、交付 175/175 和白名单命令文本；执行命令、上传交付包、批量状态变更、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布固定禁用

## P1-65 创建运营 Presenter View 静态 Mock 原型
- 目标：新增 `/operations/presenter` 静态页面，把运营演示脚本收束成一页式讲解台，展示 speakerCue、验收信号、白名单命令和禁用动作
- 验收：`frontend/operations-presenter.html` 可直接打开，页面契约声明 `/operations/presenter` 原型，只读展示 12 个步骤、12 条 speakerCue、6 个验收信号、8 个禁止动作、交付 175/175 和 Phase 1 Check 20/20；执行命令、上传交付包、批量状态变更、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布固定禁用

### P1-66：Phase 1 运营签收总览静态页

- 模块：frontend / delivery / operation
- 目标：提供 `frontend/operations-signoff.html`，把 6/6 门禁、175/175 交付、20/20 自检、14/14 验收、6/6 安全断言、本地证据、人工预览入口和禁用动作汇总成一屏签收视图。
- 验收：`frontend/operations-signoff.html` 可直接打开，页面契约声明 `/operations/signoff` 原型，只读展示签收门禁、交付证据、白名单命令文本和 Phase 1 禁用项；执行命令、上传交付包、批量状态变更、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布固定禁用

# Phase 2：AI Workflow

## P2-01 LLM Provider 抽象
- 目标：在保持 MockProvider-first 的前提下，为后续真实 Provider 接入预留统一边界。
- 验收：`providers/adapter.py` 仍只路由到 MockProvider，`realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`，失败响应包含 `providerErrorContext`。

## P2-02 内容生成 Mock Workflow 编排
- 目标：创建 Phase 2 `phase2_content_generation` 工作流，用 MockProvider 编排 Lab / Exam / Grading / PPT DSL 生成，并组装待审核包。
- 验收：`python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json` 返回统一 JSON，生成 4 个 `WAITING_REVIEW` AI Task，写入 Provider 调用审计、Artifact 清单和 Workflow Run；不调用真实 LLM、不启动真实 Agent、不创建真实云资源、不执行真实沙箱、不自动发布。

## P2-03 试题生成 Workflow
- 目标：创建 Phase 2 `phase2_exam_conversion` 工作流，读取 Lab DSL 和 Notebook JSON，将旧实验改造成 Exam / Grading DSL 审核包。
- 验收：`python lab_cli.py phase2 exam-convert run --lab templates/lab/examples/basic-lab.yaml --notebook examples/notebooks/demo-lab.ipynb --reviewer teacher_1 --output examples/output/phase2-exam-conversion-report.json` 返回统一 JSON，生成 2 个 `WAITING_REVIEW` AI Task，写入 Provider 调用审计、Artifact 清单和 Workflow Run；Notebook 只做 JSON 静态解析，不执行 cell，不执行选手代码，候选人预览不展示标准答案。

## P2-04 PPT 生成 Workflow
- 目标：创建 Phase 2 `phase2_ppt_generation` 工作流，从 Markdown 素材生成章节树、知识点和 slide plan JSON，再通过 MockProvider 生成 PPT DSL 审核包。
- 验收：`python lab_cli.py phase2 ppt-generate run --input examples/input/demo-source.md --reviewer teacher_1 --slide-plan-output examples/output/phase2-ppt-slide-plan.json --output examples/output/phase2-ppt-generation-report.json` 返回统一 JSON，生成 1 个 `WAITING_REVIEW` PPT AI Task，写入 Provider 调用审计、Artifact 清单和 Workflow Run；必须先保存 slide plan，中间结果标记 `pptFileGenerated=false`，不调用真实 LLM、不生成真实 PPT 文件、不启动真实 Agent、不创建真实云资源、不自动发布。

## P2-05 Workflow Registry 能力目录
- 目标：创建 Phase 2 `phase2_workflow_registry` 只读能力目录，统一登记内容生成、试题改造、PPT 生成三条 Mock Workflow 的 contract、CLI 入口、Backend 入口、输入输出和安全标记。
- 验收：`python lab_cli.py workflow registry list` 和 `python lab_cli.py workflow registry get --workflow-id phase2_content_generation` 返回统一 JSON；Backend Mock `GET /api/workflow-registry` 和 `GET /api/workflow-registry/{workflowId}` 可查询同一目录；Registry 不执行 Workflow、不创建 AI Task、不写 Artifact、不调用真实 LLM、不自动发布。

## P2-06 Workflow Registry MCP Mock Tools
- 目标：把 Phase 2 Workflow Registry 以 MCP Mock Tool 形式暴露给本地工具发现层，提供 `list_workflows` 和 `get_workflow` 两个只读能力。
- 验收：`python lab_cli.py mcp call --tool list_workflows --arguments "{\"category\":\"ppt_generation\"}"` 和 `python lab_cli.py mcp call --tool get_workflow --arguments "{\"workflowId\":\"phase2_content_generation\"}"` 返回统一 JSON，并写入本地 `mcpToolCallRecords`；不得启动真实 MCP Server、真实 Agent，不得执行 Workflow、创建 AI Task、写 Artifact、调用真实 LLM 或自动发布。

## P2-07 Workflow Registry 前端 Mock 能力目录
- 目标：新增 `frontend/workflows.html`，把 Phase 2 Workflow Registry、MCP Mock Tools、CLI 入口和 Backend Mock 入口展示成只读能力目录。
- 验收：`frontend/workflows.html` 可直接打开，页面契约声明 `/workflows` 原型；页面只读展示三条 Phase 2 Mock Workflow 和 `list_workflows` / `get_workflow`，不得运行 Workflow、创建 AI Task、写 Artifact、启动真实 MCP Server、启动真实 Agent、调用真实 LLM、自动发布或真实发布。

# Phase 3：自动评分

## P3-01 评分器接口 Mock
- 目标：新增 `sandbox/grade_runner.py` 和 `sandbox/grade-runner.contract.json`，把 Grading DSL 转成统一评分报告结构，并抽象 `SandboxExecutor` 执行边界。
- 验收：`python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-grading-report.json` 返回统一 JSON，报告包含 `runner`、`checkSummary`、`checks.executionPlan`；`sandboxExecuted=false`、`commandExecuted=false`、`contestantCodeExecuted=false`。

## P3-02 file_exists / stdout_contains / pytest Mock 评分项
- 目标：在不执行真实命令、不运行 pytest、不执行 Notebook、不读取选手代码的前提下，支持六类评分项的计划化报告和校验。
- 验收：`templates/grading/examples/mixed-checks.yaml` 覆盖 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类 check；`tests/test_sandbox_mock_executor.py` 校验六类 check 均为 `MOCK_PLAN_ONLY`，且真实沙箱和宿主机执行固定禁用。

## P3-03 Phase 3 评分报告前端 Mock
- 目标：更新 `frontend/grading-report.html`，把 `mock_grading_runner`、`checkSummary` 和六类评分项的 `MOCK_PLAN_ONLY` 执行计划展示给运营与教师审核视角。
- 验收：`frontend/grading-report.html` 可直接打开，页面契约声明 `/grading/:id/report` 原型；页面展示 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类 check，`checkSummary.executed=0`、`sandboxExecuted=false`、`commandExecuted=false`、`contestantCodeExecuted=false`，不得运行真实沙箱、命令、pytest 或 Notebook。

## P3-04 Phase 3 评分运行审计 Mock
- 目标：让 CLI、Backend Mock 和前端审计页展示 `MOCK_GRADING_RUN` 的 runner、checkSummary、checkPlans 和真实执行阻断动作。
- 验收：`grade run` 和 `/api/grading/run` 返回的 `operationAuditEvent.detail` 包含 `mock_grading_runner`、`checkSummary.executed=0`、六类 `MOCK_PLAN_ONLY` check plan、`runRealPytestEnabled=false` 和 `hostExecutionAllowed=false`；`frontend/audit.html` 展示同样的安全摘要。

## P3-05 沙箱执行
## P3-06 评分报告

# Phase 4：MCP

## P4-01 MCP Server
- 目标：新增 Phase 4 MCP Server Mock runtime，提供本地 initialize / listTools / callTool 形态。
- 验收：`python lab_cli.py mcp server-info`、`python lab_cli.py mcp server-tools`、`python lab_cli.py mcp server-call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"` 和 Backend Mock `/api/mcp/server/*` 均返回统一 JSON；固定 `realMcpServerStarted=false`、`realAgentStarted=false`、`networkListenerStarted=false`，并写入 MCP Tool 调用审计。

## P4-02 MCP Tool Schema
## P4-03 CLI 对接 MCP
## P4-04 高风险工具审核
- 目标：将 `publish_lab`、`publish_exam`、`destroy_environment` 纳入 MCP Tool manifest，但只允许创建本地待审核意图。
- 验收：三个工具通过 `lab-cli mcp call` / `server-call` 只返回 `WAITING_REVIEW` AI Task、操作审计和安全断言；`publish_*` 固定 `realPublish=false`、`autoPublishAllowed=false`，`destroy_environment` 固定 `requiresSecondConfirmation=true`、`realCloudResourceChanged=false`、`environmentDestroyed=false`。

## P4-05 高风险 MCP 意图前端可视化
- 目标：在审核中心和审计可观测页展示 `publish_lab`、`publish_exam`、`destroy_environment` 的高风险意图、审核后 Mock 处置态、MCP 调用记录和统一操作审计。
- 验收：`frontend/review-center.html` 展示 `HighRiskMcpIntentPanel`，`frontend/audit.html` 展示对应 `mcpToolCallRecords`、`postReviewDisposition` 与 `PUBLISH_LAB_INTENT` / `PUBLISH_EXAM_INTENT` / `DESTROY_ENVIRONMENT_INTENT`；页面和 Mock 数据均固定 `reviewIntentOnly=true`、`realPublish=false`、`secondConfirmationSatisfied=false`、`environmentDestroyed=false`，真实发布、真实销毁和绕过审核按钮禁用。

## P4-06 高风险 MCP 意图审核后 Mock 处置状态
- 目标：在 CLI / Backend / MCP 审核详情中为高风险 MCP 意图返回 `postReviewDisposition`，统一表达审核后仍处于 Mock 阻断态。
- 验收：`WAITING_REVIEW` 意图返回 `WAITING_HUMAN_REVIEW`；`publish_lab` / `publish_exam` 审核通过后返回 `APPROVED_EXECUTION_BLOCKED`；`destroy_environment` 审核通过后返回 `APPROVED_PENDING_SECOND_CONFIRMATION` 且 `secondConfirmationSatisfied=false`；所有处置态均保持 `executeRealActionAllowed=false`、`realPublish=false`、`environmentDestroyed=false`。

## P4-07 高风险 MCP 二次确认只读状态
- 目标：为 `destroy_environment` 这类 `secondConfirmationRequired=true` 的意图提供 CLI / Backend 只读二次确认状态查询。
- 验收：`review second-confirmation-status --task-id <task_id>` 和 `GET /api/review-tasks/{id}/second-confirmation-status` 返回统一 JSON，固定 `secondConfirmationSatisfied=false`、`confirmationActionAvailable=false`、`destroyRealEnvironmentEnabled=false`、`environmentDestroyed=false`；非二次确认意图返回校验错误，不提供确认执行入口。

## P4-08 MCP 二次确认状态查询工具
- 目标：将二次确认只读状态查询暴露为 MCP Tool `get_second_confirmation_status`，复用 Backend Mock 查询接口。
- 验收：`lab-cli mcp call --tool get_second_confirmation_status --arguments "{\"taskId\":\"<task_id>\"}"` 和 `server-call` 均返回统一 JSON 与 `mcpToolCallRecords`；工具固定 `readOnly=true`、`confirmationActionAvailable=false`、`confirmationEndpointEnabled=false`、`destroyRealEnvironmentEnabled=false`、`environmentDestroyed=false`，非二次确认意图返回 Backend Mock 校验错误。

## P4-09 二次确认状态前端可视化
- 目标：在 `frontend/review-center.html` 与 `frontend/audit.html` 中展示 `get_second_confirmation_status` 的只读查询状态和 MCP 调用记录。
- 验收：前端 Mock 数据包含 `secondConfirmationStatusPrototype`，审核中心展示 `SecondConfirmationStatusPanel`，审计页展示 `mcp_call_get_second_confirmation_status_demo`；所有页面固定 `readOnly=true`、`confirmationActionAvailable=false`、`confirmationEndpointEnabled=false`、`destroyRealEnvironmentEnabled=false`、`environmentDestroyed=false`，不得提供二次确认通过或真实销毁按钮。

## P4-10 高风险 MCP Tool 安全矩阵契约
- 目标：新增 `mcp-server/high-risk-tool-safety.contract.json`，把 `publish_lab`、`publish_exam`、`destroy_environment` 和 `get_second_confirmation_status` 的 review-intent-only / read-only / blocked action 规则固化为可测试矩阵。
- 验收：`python -m pytest tests/test_high_risk_mcp_safety_contract.py` 校验矩阵与 MCP manifest、前端 Mock 数据、MCP 调用记录和脚本白名单一致；所有矩阵项固定 `MOCK_ONLY`，不得启动真实 MCP Server、真实 Agent、真实大模型、真实发布、真实销毁或绕过人工审核。

# Phase 5：运营交付

## P5-01 运营手册
- 目标：新增 `delivery/OPERATIONS_MANUAL.md` 和 `delivery/operations-manual.json`，把运营入口、白名单命令、审核门禁、本地证据、高风险 MCP 限制和最终签收流程沉淀为可测试手册包。
- 验收：`python -m pytest tests/test_operations_manual.py` 校验运营手册与脚本白名单、交付索引、最终签收包和交付合同一致；交付清单展示 175/175，运营手册文档和契约进入导出包，且真实 Provider、真实 MCP Server、真实 Agent、真实云资源、真实沙箱、未知 Shell、选手代码执行、自动发布和真实发布固定禁用。
## P5-02 Skills 沉淀
- 目标：新增 `skills/operations-skill-pack/SKILL.md` 和 `skills/operations-skill-pack.contract.json`，把 Lab / Exam / Grading / PPT 四类基础 Skill、Prompt、Workflow、DSL Schema、CLI Mock、运营手册和最终签收流程组合为运营可复用 Skill 包。
- 验收：`python -m pytest tests/test_operations_skill_pack.py` 校验运营 Skill 包与 `skills/manifest.json`、Prompt manifest、Workflow manifest、脚本白名单、运营手册、最终签收包和交付合同一致；交付清单展示 175/175，Skill 包文档和契约进入导出包，且真实 Agent、真实 Provider、真实 MCP Server、真实云资源、真实沙箱、未知 Shell、选手代码执行、自动发布和真实发布固定禁用。
## P5-03 独立智能体交付
- 目标：新增 `delivery/STANDALONE_AGENT_DELIVERY.md` 和 `delivery/standalone-agent-delivery.json`，把未来独立智能体的目标、输入输出、允许工具、禁止工具、状态、错误处理、审计证据和验收规则沉淀为 Mock 交付包。
- 验收：`python -m pytest tests/test_standalone_agent_delivery.py` 校验独立智能体交付包与 MCP Tool manifest、Workflow manifest、脚本白名单、运营手册、最终签收包和交付合同一致；交付清单展示 175/175，独立智能体交付文档和契约进入导出包，且不连接真实外部平台、不启动真实 Agent、不调用真实 LLM、不启动真实 MCP Server、不创建真实云资源、不执行真实沙箱或选手代码、不自动发布或真实发布。
## P5-04 IP + 端口可视化网页交付
- 目标：新增 `delivery/ACCESS_ENTRYPOINTS.md`、`delivery/access-entrypoints.json` 和 `frontend/access.html`，把本地静态入口、未来规划端口、禁用动作和安全边界沉淀为可读、可测、可交付的访问说明。
- 验收：`python -m pytest tests/test_access_entrypoints.py` 校验访问入口文档、机器契约、静态页面、交付索引、Runbook、运营手册、交接清单和最终签收包一致；交付清单展示 175/175，访问入口只允许打开本地静态 HTML，真实 HTTP 服务、端口监听、局域网/公网 IP 绑定、反向代理、TLS、真实 MCP Server、真实 Agent、真实 LLM、远程上传、自动发布和真实发布固定禁用。

## P5-05 最终运营签收包
- 目标：新增 `delivery/FINAL_SIGNOFF.md` 和 `delivery/final-signoff.json`，把本地文档、静态预览、交付导出、验收报告、高风险 MCP 交接、白名单命令和全量测试收口为可测试的最终签收顺序。
- 验收：`python -m pytest tests/test_final_signoff.py` 校验最终签收包与 `scripts/manifest.json`、`delivery/phase1-delivery-index.json` 和 `config/delivery-package.contract.json` 一致；交付清单展示 175/175，最终签收文档和契约进入导出包，且真实 Provider、真实 MCP Server、真实 Agent、真实云资源、真实沙箱、未知 Shell、选手代码执行、自动发布和真实发布固定禁用。

## P5-06 真实 LLM 接入前 Mock 基线冻结
- 目标：新增 `delivery/PHASE5_MOCK_BASELINE.md` 和 `delivery/phase5-mock-baseline.json`，在进入真实 LLM PoC 前冻结 Mock 交付基线、默认 Provider、审核门禁和允许下一步范围。
- 验收：`python -m pytest tests/test_phase5_mock_baseline.py` 校验 Mock 基线冻结与交付合同、交付索引、最终签收包、运营手册、交接清单、运营 Skill 包和脚本白名单一致；交付清单展示 175/175，真实 LLM PoC 只能默认关闭、显式 opt-in、先限定 `lab generate-from-source`，且 API Key 只能来自环境变量，生成结果仍为 `WAITING_REVIEW`。
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
