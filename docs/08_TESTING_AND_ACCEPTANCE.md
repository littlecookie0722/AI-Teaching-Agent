# 08_TESTING_AND_ACCEPTANCE

# 验收主链路

```text
输入 demo-source.md
  ↓
生成 Lab DSL
  ↓
人工审核
  ↓
生成 Exam DSL
  ↓
生成 Grading DSL
  ↓
执行 Mock 评分
  ↓
输出评分报告
```

# 必测项

1. CLI 参数缺失
2. 输入文件不存在
3. DSL Schema 错误
4. AI Task 状态非法流转
5. review reject 无 reason
6. 未审核内容 publish
7. grade run 成功
8. grade run 失败
9. 输出 JSON 格式一致
10. 日志包含 traceId
11. review approve / reject 记录 reviewer 和 reviewTime
12. APPROVED 后 publish 仅执行 Mock 状态流转，不发布真实平台实体
13. `phase1 check` 自检通过
14. grade run 可保存 Mock 评分报告
15. grade report 可读取 Mock 评分报告
16. MCP Tool manifest 工具名唯一，输入 schema、Backend Mock 映射和安全限制完整
17. Workflow manifest 声明主链路、生成类输出、审核门禁和 Phase 1 安全限制
18. Sandbox Mock Executor 报告必须标记不执行沙箱、不执行选手代码
19. Prompt manifest 必须声明版本、路径、输出 Schema、审核要求和密钥限制
20. Skill manifest 必须覆盖 Lab / Exam / Grading / PPT，并引用存在的 Prompt、Workflow、Schema 和示例输出
21. Frontend manifest 必须声明页面、组件、Mock API 依赖和安全限制，Mock 数据不得允许自动发布或展示密钥
22. Scripts manifest 必须只允许本地验证/Mock 导出命令，并阻止破坏性、云资源、生产和未知 Shell 动作
23. Config contract 必须保持 Phase 1 Mock 默认值，`.env.example` 不得包含真实密钥
24. Local artifacts contract 必须保证 `.env.example` 和 `examples/output/README.md` 可跟踪，真实 `.env`、Mock Store、生成报告、缓存和交付包归档被忽略
25. Delivery package contract 必须声明交付物、验收清单、安全断言和本地推荐命令，`phase1 export` 输出的必需验收项必须通过
26. Review audit 必须记录 approve / reject / Mock publish 事件，并可通过 CLI 与 Backend Mock 查询；事件必须标记 `realPublish=false`
27. Operation audit 必须记录审核、环境 Mock 操作和 Mock 评分事件，并可通过 CLI 与 Backend Mock 查询；事件必须禁止真实 LLM、真实云资源、选手代码执行和真实发布
28. Provider contract 必须保持 Phase 1 仅启用 `mock` Provider，真实 Provider 禁用，Mock 生成结果默认 `WAITING_REVIEW`
29. Provider Mock CLI 和 Backend API 必须统一返回 JSON，并固定 `realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`
30. Workflow Run 日志必须记录 Mock 主链路步骤、traceId 和安全标记，并可通过 CLI 与 Backend Mock 查询
31. 素材分析 Mock 必须只做静态本地分析，CLI 与 Backend API 返回统一 JSON，并固定 `realLlmCalled=false`、`remoteContentFetched=false`、`unknownShellExecuted=false`、`sandboxExecuted=false`
32. Artifact Mock 清单必须记录素材分析、DSL、Mock 报告产物元数据，并可通过 CLI 与 Backend Mock 查询；记录必须禁止真实 LLM、真实云资源、真实沙箱、选手代码执行和真实发布
33. Review Detail Mock 必须聚合 AI Task、Artifact、Workflow Step、审核审计、统一操作审计、发布策略和 `reviewPage` 页面模型，并固定 `autoPublishAllowed=false`、`realPublish=false`
34. Review Detail 示例必须可提交、可测试，且 CLI 支持 `review detail --output` 导出本地 JSON
35. Review Batch Summary Mock 必须只做待审核队列摘要和导出，批量 approve/reject/publish 必须固定禁用
36. Review Center 静态原型必须保持 `MOCK_ONLY`，只展示审核队列和任务详情，批量状态变更、真实发布、真实后端依赖、密钥展示必须固定禁用
37. Lab Generation 静态原型必须保持 `MOCK_ONLY`，只展示本地素材分析、MockProvider、Lab DSL 预览和 `WAITING_REVIEW` 审核门禁，真实 LLM、远程素材抓取、未知 Shell 执行和自动发布必须固定禁用
38. Grading Report 静态原型必须保持 `MOCK_ONLY`，只展示 Mock 分数、check 明细和审计入口，真实沙箱、选手代码执行、未知 Shell 执行、真实云资源变更和真实发布必须固定禁用
39. AI Task Center 静态原型必须保持 `MOCK_ONLY`，只展示任务列表、待审核摘要、Workflow 日志入口和审核详情入口，自动发布、批量状态变更、真实 Agent 运行、真实 LLM 调用和密钥展示必须固定禁用
40. Dashboard 静态原型必须保持 `MOCK_ONLY`，只展示健康状态、待审核压力、Workflow Run、Artifact 和安全总览，自动发布、批量状态变更、真实 LLM、真实云资源、真实沙箱和密钥展示必须固定禁用
41. Exam Generation 静态原型必须保持 `MOCK_ONLY`，只展示 Lab ID、Exam DSL / Grading DSL 预览和审核门禁，标准答案不得展示给选手端，真实 LLM、真实沙箱、自动发布和真实发布必须固定禁用
42. Environment Management 静态原型必须保持 `MOCK_ONLY`，只展示 VM / Notebook Mock 记录、状态流转和操作审计，真实云资源创建/变更/销毁、真实沙箱、选手代码执行和密钥展示必须固定禁用
43. Skills Management 静态原型必须保持 `MOCK_ONLY`，只展示 Skill、Prompt、Workflow、DSL Schema、示例输出和 CLI Mock 关联关系，真实智能体、真实 LLM、Prompt 散落业务代码、自动发布和密钥展示必须固定禁用
44. Provider Settings 静态原型必须保持 `MOCK_ONLY`，只展示 MockProvider 启用态、真实 Provider 禁用态和运行配置，真实 Provider、真实 LLM、网络访问、密钥读取/展示和 Prompt 散落业务代码必须固定禁用
45. Lab Review 静态原型必须保持 `MOCK_ONLY`，只展示单个 Lab DSL 审核详情、Artifact、Timeline 和操作栏，批量状态变更、自动发布、真实发布和选手端答案泄露必须固定禁用
46. Labs Management 静态原型必须保持 `MOCK_ONLY`，只展示 Lab 列表、状态筛选、生成入口和审核入口，批量状态变更、自动发布、真实发布、真实 LLM 和密钥展示必须固定禁用
47. Exams Management 静态原型必须保持 `MOCK_ONLY`，只展示 Exam 列表、Grading DSL 关联、生成入口和脱敏候选人预览，标准答案选手端隐藏，真实沙箱、自动发布、真实发布和真实 LLM 必须固定禁用
48. Grading Management 静态原型必须保持 `MOCK_ONLY`，只展示 Grading DSL 清单、Mock 评分入口、报告入口和审计入口，真实沙箱、选手代码执行、未知 Shell、真实重评和真实发布必须固定禁用
49. Exam Review 静态原型必须保持 `MOCK_ONLY`，只展示单个 Exam DSL、Grading DSL、Timeline 和操作栏，标准答案选手端隐藏，真实沙箱、自动发布、真实发布和批量状态变更必须固定禁用
50. Grading Review 静态原型必须保持 `MOCK_ONLY`，只展示单个 Grading DSL、Mock 报告预览、Timeline 和操作栏，真实沙箱、选手代码执行、未知 Shell、真实重评、自动发布、真实发布和批量状态变更必须固定禁用
51. PPT Management 静态原型必须保持 `MOCK_ONLY`，只展示 PPT DSL 清单、生成入口、审核入口和 Slide Plan 摘要，真实大模型、真实 PPT 文件生成、自动发布、真实发布和密钥展示必须固定禁用
52. PPT Review 静态原型必须保持 `MOCK_ONLY`，只展示单个 PPT DSL、Slide Plan、Timeline 和操作栏，真实大模型、真实 PPT 文件生成、自动发布、真实发布、批量状态变更和密钥展示必须固定禁用
53. Delivery Acceptance 静态原型必须保持 `MOCK_ONLY`，只展示本地交付清单、验收摘要、Phase 1 自检、推荐命令和安全断言，真实大模型、真实云资源、真实沙箱、上传交付包、自动发布、真实发布和密钥展示必须固定禁用
54. Mock Console 静态原型必须保持 `MOCK_ONLY`，只展示本地静态导航、推荐验证命令和安全断言，真实 Agent、真实 Provider、真实 LLM、真实云资源、真实沙箱、选手代码执行、自动发布、真实发布、批量状态变更和密钥展示必须固定禁用
55. Phase 1 Demo Runbook 必须只作为人工验收说明和机器可测契约，验证命令必须引用 `scripts/manifest.json` 的白名单命令，预览动作不得写工作区，未知 Shell、真实 LLM、真实智能体、真实云资源、真实沙箱、选手代码执行、自动发布和真实发布必须固定禁用
56. Phase 1 Acceptance Report 必须由本地交付包确定性生成 Markdown，只用于人工验收阅读，不重新生成内容、不调用真实 Provider、不发布真实内容，并作为可再生成本地输出忽略
57. Phase 1 Demo Script Checklist 必须保持 `MOCK_ONLY`，只描述人工演示顺序、白名单验证命令、验收信号和禁用动作，不得变成自动执行脚本，也不得触发真实 Provider、真实 Agent、真实云资源、真实沙箱、远程上传、自动发布或真实发布
58. Phase 1 Delivery Index 必须保持 `MOCK_ONLY`，只汇总本地入口、Runbook、交付包契约、验收报告和白名单验证命令，不新增真实执行能力，不上传交付包，不发布真实内容
59. Phase 1 FAQ 必须保持 `MOCK_ONLY`，只记录本地故障排查、白名单验证命令和安全恢复步骤，不接入真实大模型、不创建真实云资源、不执行未知 Shell、不绕过人工审核、不上传交付包
60. Phase 1 Handoff Checklist 必须保持 `MOCK_ONLY`，只聚合本地交接阅读顺序、静态预览、验收证据、白名单命令和安全确认项，不新增真实执行能力，不上传交付包，不发布真实内容
61. Phase 2 Readiness Gate 必须保持 `MOCK_ONLY`，只定义进入下一阶段规划/Mock 设计前的准入信号、允许下一步和阻断项，不授权真实 LLM、真实 Agent、真实云资源、真实沙箱、未知 Shell、自动发布或真实发布
62. Operations Runbook 静态原型必须保持 `MOCK_ONLY`，只展示本地入口、白名单命令、审计复盘入口和安全红线，执行命令、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、上传交付包、自动发布和真实发布必须固定禁用
63. Operations Acceptance 静态原型必须保持 `MOCK_ONLY`，只展示运营验收项、交付状态、Runbook、FAQ、Handoff、Phase 2 准入门禁和白名单命令，执行命令、上传交付包、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布必须固定禁用
64. Operations Demo Map 静态原型必须保持 `MOCK_ONLY`，只展示角色视角、演示路径、静态页面入口和白名单命令，执行命令、批量状态变更、上传交付包、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布必须固定禁用
65. Operations Demo Script 静态原型必须保持 `MOCK_ONLY`，只展示 12 步演示顺序、验收信号、白名单命令和禁止动作，执行命令、批量状态变更、上传交付包、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布必须固定禁用
66. Operations Presenter View 静态原型必须保持 `MOCK_ONLY`，只展示 12 个步骤、12 条 speakerCue、6 个验收信号、8 个禁止动作、交付 175/175 和 Phase 1 Check 20/20；执行命令、批量状态变更、上传交付包、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布必须固定禁用
67. Operations Signoff Dashboard 静态原型必须保持 `MOCK_ONLY`，只展示 6/6 门禁、175/175 交付、20/20 自检、14/14 验收、6/6 安全断言、本地证据和禁用动作；执行命令、批量状态变更、上传交付包、启动真实 Agent、启用真实 Provider、调用真实大模型、创建真实云资源、运行真实沙箱、执行选手代码、自动发布和真实发布必须固定禁用
68. Phase 2 Content Generation Workflow 必须保持 `MOCK_ONLY`，通过 MockProvider 编排 Lab / Exam / Grading / PPT DSL 审核包，CLI 和 Backend Mock 均返回统一 JSON，写入 AI Task、Provider 审计、Artifact 和 Workflow Run；真实 LLM、真实 Agent、真实云资源、真实沙箱、选手代码执行、自动发布和真实发布必须固定禁用
69. Phase 2 Exam Conversion Workflow 必须保持 `MOCK_ONLY`，只静态读取 Lab DSL 和 Notebook JSON，生成 Exam / Grading DSL 审核包；候选人预览必须移除标准答案，Notebook cell、真实沙箱、选手代码、真实 LLM、真实 Agent、真实云资源、自动发布和真实发布必须固定禁用
70. Phase 2 PPT Generation Workflow 必须保持 `MOCK_ONLY`，只读取本地 Markdown，先生成 slide plan JSON，再生成 PPT DSL 审核包；CLI 和 Backend Mock 均返回统一 JSON，写入 AI Task、Provider 审计、Artifact 和 Workflow Run；真实 PPT 文件生成、PDF / Word 直接转 PPT、真实 LLM、真实 Agent、真实云资源、自动发布和真实发布必须固定禁用
71. Phase 2 Workflow Registry 必须保持 `MOCK_ONLY`，只提供本地 Workflow 能力目录查询；CLI 和 Backend Mock 均返回统一 JSON，引用的 contract 路径必须存在；不得执行 Workflow、创建 AI Task、写 Artifact、调用真实 LLM、启动真实 Agent、创建真实云资源、自动发布或真实发布
72. Phase 2 Workflow Registry MCP Mock Tools 必须保持 `MOCK_ONLY`，`list_workflows` / `get_workflow` 只能通过 Backend Mock 读取能力目录并写入本地 MCP 调用审计；不得启动真实 MCP Server、真实 Agent，不得执行 Workflow、创建 AI Task、写 Artifact、调用真实 LLM、创建真实云资源、自动发布或真实发布
73. Phase 2 Workflow Registry 前端 Mock 必须保持 `MOCK_ONLY`，`frontend/workflows.html` 只读展示 Workflow 能力目录、MCP Mock 工具、CLI/Backend 入口和安全断言；不得运行 Workflow、创建 AI Task、写 Artifact、启动真实 MCP Server、真实 Agent、调用真实 LLM、自动发布或真实发布
74. Phase 3 Mock 评分器接口必须保持 `MOCK_ONLY`，`sandbox/grade_runner.py` 只能根据 Grading DSL 生成 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类 check 的计划化报告；不得执行命令、不得运行 pytest、不得执行 Notebook、不得读取真实 JSON/日志文件、不得执行选手代码、不得访问真实沙箱或宿主机敏感路径
75. Phase 3 评分报告前端 Mock 必须保持 `MOCK_ONLY`，`frontend/grading-report.html` 只读展示 `mock_grading_runner`、`checkSummary.executed=0` 和六类 check 的 `MOCK_PLAN_ONLY` 执行计划；不得执行命令、运行 pytest、执行 Notebook、读取真实 JSON/日志文件、启动真实沙箱、执行选手代码或真实发布
76. Phase 3 评分运行审计必须保持 `MOCK_ONLY`，`MOCK_GRADING_RUN.detail` 必须记录 `mock_grading_runner`、`checkSummary.executed=0`、六类 `checkPlans` 和 `runRealPytestEnabled=false`；不得执行命令、运行 pytest、执行 Notebook、读取真实 JSON/日志文件、启动真实沙箱、执行选手代码或真实发布
77. Phase 4 MCP Server Mock 必须保持 `MOCK_ONLY`，`mcp_server/mock_server.py` 只提供本地 initialize/listTools/callTool 形态；不得监听端口、启动真实 MCP Server、启动 Agent、调用真实 LLM、创建真实云资源、运行真实沙箱、执行选手代码、自动发布或真实发布
78. Phase 4 高风险 MCP Tool 必须保持 review-intent-only，`publish_lab`、`publish_exam` 和 `destroy_environment` 只能创建 `WAITING_REVIEW` AI Task 和操作审计；不得真实发布、不得销毁环境、不得改动真实云资源，`destroy_environment` 必须要求二次确认
79. Phase 4 高风险 MCP 意图前端 Mock 必须保持 `MOCK_ONLY`，审核中心只展示 `HighRiskMcpIntentPanel`，审计页只展示对应 MCP 调用记录、`postReviewDisposition` 和统一操作审计；前端必须覆盖 `WAITING_HUMAN_REVIEW`、`APPROVED_EXECUTION_BLOCKED`、`APPROVED_PENDING_SECOND_CONFIRMATION` 三种 Mock 处置态，`publish_lab` / `publish_exam` 固定 `realPublish=false`，`destroy_environment` 固定 `requiresSecondConfirmation=true`、`secondConfirmationSatisfied=false`、`environmentDestroyed=false`，不得执行真实发布、真实销毁或绕过人工审核
80. Phase 4 高风险 MCP 意图审核详情必须返回 `postReviewDisposition`：待审核为 `WAITING_HUMAN_REVIEW`，发布意图审核通过后为 `APPROVED_EXECUTION_BLOCKED`，销毁环境意图审核通过后为 `APPROVED_PENDING_SECOND_CONFIRMATION` 且 `secondConfirmationSatisfied=false`；所有状态均不得开启真实执行、真实发布、真实云资源变更或真实环境销毁
81. Phase 4 高风险 MCP 二次确认状态查询必须保持只读，CLI `review second-confirmation-status` 和 Backend `/api/review-tasks/{id}/second-confirmation-status` 只能返回 Mock 状态；非二次确认意图必须返回校验错误，销毁环境意图必须固定 `confirmationActionAvailable=false`、`destroyRealEnvironmentEnabled=false`、`environmentDestroyed=false`
82. Phase 4 MCP 二次确认状态查询工具必须保持只读，`get_second_confirmation_status` 只能通过 MCP Mock 调用 Backend 查询接口并写入 `mcpToolCallRecords`；必须固定 `readOnly=true`、`confirmationEndpointEnabled=false`、`destroyRealEnvironmentEnabled=false`、`environmentDestroyed=false`，不得提供确认执行工具或真实销毁入口
83. Phase 4 二次确认状态前端可视化必须保持只读，`frontend/review-center.html` 只能展示 `SecondConfirmationStatusPanel`，`frontend/audit.html` 只能展示 `get_second_confirmation_status` 查询记录；页面与 Mock 数据必须固定 `readOnly=true`、`confirmationActionAvailable=false`、`confirmationEndpointEnabled=false`、`destroyRealEnvironmentEnabled=false`、`environmentDestroyed=false`，不得提供二次确认通过、真实执行或真实销毁按钮
84. Phase 4 高风险 MCP Tool 安全矩阵契约必须覆盖 `publish_lab`、`publish_exam`、`destroy_environment` 和 `get_second_confirmation_status`；矩阵必须与 MCP manifest、前端 Mock 数据和脚本白名单一致，发布/销毁类工具只允许创建审核意图，二次确认状态工具只允许只读查询，真实 MCP Server、真实 Agent、真实大模型、真实发布、真实销毁和绕过人工审核必须固定禁用
85. Phase 5 高风险 MCP 运营交接必须保持 `MOCK_ONLY`，`delivery/HIGH_RISK_MCP_HANDOFF.md` 和 `delivery/high-risk-mcp-handoff.json` 只允许人工确认安全矩阵、审核意图、二次确认只读状态和前端可视化证据；不得把 `publish_lab`、`publish_exam`、`destroy_environment` 或 `get_second_confirmation_status` 解释为真实执行授权
86. Phase 5 最终运营签收包必须保持 `MOCK_ONLY`，`delivery/FINAL_SIGNOFF.md` 和 `delivery/final-signoff.json` 只允许人工确认本地文档、静态预览、导出包、验收报告和白名单测试；不得启动真实 Provider、真实 MCP Server、真实 Agent、真实云资源、真实沙箱、未知 Shell、选手代码执行、自动发布或真实发布
87. Phase 5 运营手册包必须保持 `MOCK_ONLY`，`delivery/OPERATIONS_MANUAL.md` 和 `delivery/operations-manual.json` 只允许运营人员打开本地静态页面、运行白名单命令、收集本地生成证据和提交人工审核；不得启用真实 Provider、真实 MCP Server、真实 Agent、真实云资源、真实沙箱、未知 Shell、选手代码执行、自动发布或真实发布
88. Phase 5 运营 Skill 包必须保持 `MOCK_ONLY`，`skills/operations-skill-pack/SKILL.md` 和 `skills/operations-skill-pack.contract.json` 只允许组合现有 Lab / Exam / Grading / PPT Skill、Prompt、Workflow、Schema、CLI Mock 和交付文档；不得启动真实 Agent、真实 Provider、真实 MCP Server、真实云资源、真实沙箱、未知 Shell、选手代码执行、自动发布或真实发布
89. Phase 5 独立智能体交付包必须保持 `MOCK_ONLY`，`delivery/STANDALONE_AGENT_DELIVERY.md` 和 `delivery/standalone-agent-delivery.json` 只允许描述未来独立智能体的本地 Mock Tool / Mock Workflow 编排、状态、错误、审计和验收规则；不得连接真实外部平台、启动真实 Agent、调用真实 LLM、启动真实 MCP Server、创建真实云资源、执行真实沙箱、执行选手代码、绕过人工审核、自动发布或真实发布
90. Phase 5 IP + 端口访问入口必须保持 `MOCK_ONLY`，`delivery/ACCESS_ENTRYPOINTS.md`、`delivery/access-entrypoints.json` 和 `frontend/access.html` 只允许展示本地静态页面入口和禁用的未来规划端口；不得启动真实 HTTP 服务、监听端口、绑定局域网/公网 IP、配置反向代理或 TLS、启动真实 MCP Server、启动真实 Agent、调用真实 LLM、远程上传、自动发布或真实发布
91. Phase 5 Mock 基线冻结必须保持 `MOCK_ONLY`，`delivery/PHASE5_MOCK_BASELINE.md` 和 `delivery/phase5-mock-baseline.json` 只允许记录 175/175 本地 Mock 交付状态和真实 LLM PoC 准入门禁；不得启用真实 Provider、读取或输出真实密钥、调用真实 LLM、启动真实 MCP Server、启动真实 Agent、创建真实云资源、执行真实沙箱、执行选手代码、绕过 `WAITING_REVIEW`、自动发布或真实发布

# 核心回归测试矩阵

`quality regression-matrix` 是当前 PR 前本地回归入口，用于把 P0/P1 核心能力拆成固定 pytest profile，并输出 JSON evidence。

```powershell
python lab_cli.py quality regression-profiles
python lab_cli.py quality regression-matrix --profile quick --output examples/output/regression-matrix-quick.json
python lab_cli.py quality regression-matrix --profile core --stop-on-failure --output examples/output/regression-matrix-core.json
```

矩阵只运行预定义 profile，不接受任意命令字符串，不使用 shell；默认 marker 过滤为 `not integration and not real_llm_online`，因此不会触发真实在线 LLM 测试或外部数据库集成测试。若需要真实 PostgreSQL / MySQL / LLM smoke，必须单独使用对应显式 opt-in 命令和测试环境。

GitHub Actions 已提供 `.github/workflows/core-regression-matrix.yml`，用于在 PR 或手动触发时运行 `core` profile，并上传 `examples/output/regression-matrix-core.json` 与 CLI JSON 输出。该 workflow 只是调用现有 `lab_cli.py quality regression-matrix`，如果 CLI 返回 `success=false` 会显式失败；真实远端运行结果、失败截图或外部 CI artifact 仍需在后续实际执行后记录。

# 快速自检

如果本地 Python 尚未安装依赖，先执行：

```powershell
python -m pip install -r requirements.txt
```

```powershell
python lab_cli.py phase1 check
python -m pytest
```

`phase1 check` 会检查：

- Lab / Exam / Grading / PPT DSL 示例
- AI Task 默认 `WAITING_REVIEW`
- 未审核 publish 被阻止
- 审核动作审计事件可查询
- 统一操作审计事件可查询
- Review Detail Mock 可查询，`phase1 check` 包含 `review_detail_mock`，并验证 `reviewPage` 中 DSL 预览和 Mock 发布阻断
- Review Batch Summary Mock 可查询，`phase1 check` 包含 `review_batch_summary_mock`，并验证批量审核/发布禁用
- Artifact Mock 清单可查询，`phase1 check` 包含 `artifact_manifest_mock`
- 环境管理仅为 Mock
- 素材分析仅为本地静态 Mock，不执行未知 Shell
- Provider 仅启用 Mock，不读取密钥，不调用真实 LLM
- Workflow Run 记录可写入和查询
- Workflow 报告可写入和读取
- Backend Mock health / ai-tasks / environments / workflow report

MCP 契约校验：

```powershell
python -m pytest tests/test_mcp_manifest.py
```

Workflow 契约校验：

```powershell
python -m pytest tests/test_workflow_manifest.py
```

Sandbox Mock 校验：

```powershell
python -m pytest tests/test_sandbox_mock_executor.py
```

Prompt 契约校验：

```powershell
python -m pytest tests/test_prompt_manifest.py
```

Skill 契约校验：

```powershell
python -m pytest tests/test_skill_manifest.py
```

Provider 契约与 Mock 校验：

```powershell
python -m pytest tests/test_provider_contract.py tests/test_provider_mock.py
```

素材分析 Mock 校验：

```powershell
python -m pytest tests/test_material_analyzer.py
```

Frontend 契约校验：

```powershell
python -m pytest tests/test_frontend_manifest.py
```

Frontend 统一 Mock 控制台预览：

```powershell
start .\frontend\console.html
```

审核中心静态原型预览：

```powershell
start .\frontend\review-center.html
```

Lab 生成静态原型预览：

```powershell
start .\frontend\labs.html
start .\frontend\lab-generate.html
```

Lab 审核详情静态原型预览：

```powershell
start .\frontend\lab-review.html
```

PPT 管理静态原型预览：

```powershell
start .\frontend\ppt.html
start .\frontend\ppt-review.html
```

评分报告静态原型预览：

```powershell
start .\frontend\grading.html
start .\frontend\grading-review.html
start .\frontend\grading-report.html
```

AI 任务中心静态原型预览：

```powershell
start .\frontend\ai-tasks.html
```

Dashboard 静态原型预览：

```powershell
start .\frontend\dashboard.html
```

Delivery 交付验收静态原型预览：

```powershell
start .\frontend\delivery.html
```

Exam 生成静态原型预览：

```powershell
start .\frontend\exams.html
start .\frontend\exam-review.html
start .\frontend\exam-generate.html
```

环境管理静态原型预览：

```powershell
start .\frontend\environments.html
```

Skills 管理静态原型预览：

```powershell
start .\frontend\skills.html
```

Provider 设置静态原型预览：

```powershell
start .\frontend\provider-settings.html
```

审计可观测静态原型预览：

```powershell
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
```

Scripts 契约校验：

```powershell
python -m pytest tests/test_scripts_manifest.py
```

Phase 1 本地演示验收 Runbook：

```powershell
start .\frontend\console.html
start .\frontend\audit.html
start .\frontend\audit-detail.html
start .\frontend\audit-incidents.html
start .\frontend\operations-launchpad.html
start .\frontend\operations-presenter.html
start .\frontend\operations-demo-script.html
start .\frontend\operations-runbook.html
start .\frontend\operations-acceptance.html
start .\frontend\operations-demo-map.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_delivery_index.py
```

配置契约校验：

```powershell
python -m pytest tests/test_config_contract.py
```

本地产物忽略契约校验：

```powershell
python -m pytest tests/test_local_artifacts_contract.py
```

交付包契约校验：

```powershell
python -m pytest tests/test_delivery_package_contract.py
```

Phase 1 FAQ / 故障排查契约校验：

```powershell
python -m pytest tests/test_delivery_faq.py
```

Phase 1 运营交接清单契约校验：

```powershell
python -m pytest tests/test_delivery_handoff.py
```

Phase 2 准入门禁契约校验：

```powershell
python -m pytest tests/test_phase2_readiness_gate.py
```

Phase 2 Provider 接入规划契约校验：

```powershell
python -m pytest tests/test_phase2_provider_plan.py
```

Provider Adapter Mock 契约校验：

```powershell
python -m pytest tests/test_provider_adapter.py
```

Provider Adapter 错误矩阵校验：

```powershell
python lab_cli.py provider mock-generate --prompt-id missing_prompt
python -m pytest tests/test_provider_adapter.py tests/test_cli.py tests/test_backend_mock_api.py
```

Provider Adapter 调用审计校验：

```powershell
python lab_cli.py provider health
python lab_cli.py provider mock-generate --prompt-id missing_prompt
python lab_cli.py provider audit --status FAILED
python -m pytest tests/test_provider_adapter.py tests/test_cli.py tests/test_backend_mock_api.py
```

Workflow Provider 调用审计校验：

```powershell
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1
python lab_cli.py provider audit --operation generateJson
python -m pytest tests/test_provider_adapter_workflow.py tests/test_cli.py tests/test_backend_mock_api.py
```

MCP Tool Mock 调用层和调用审计校验：

```powershell
python lab_cli.py mcp list
python lab_cli.py mcp call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp call --tool list_workflows --arguments "{\"category\":\"ppt_generation\"}"
python lab_cli.py mcp call --tool get_workflow --arguments "{\"workflowId\":\"phase2_content_generation\"}"
python lab_cli.py mcp server-info
python lab_cli.py mcp server-tools
python lab_cli.py mcp server-call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp call --tool publish_lab --arguments "{\"labId\":\"lab_demo\",\"reason\":\"运营申请发布\"}"
python lab_cli.py mcp server-call --tool destroy_environment --arguments "{\"environmentId\":\"env_demo\",\"reason\":\"清理申请\"}"
python lab_cli.py mcp audit --tool analyze_material
python -m pytest tests/test_mcp_manifest.py tests/test_mcp_mock_tools.py tests/test_mcp_server_mock.py tests/test_cli.py
```

Provider Adapter Workflow helper 校验：

```powershell
python -m pytest tests/test_provider_adapter_workflow.py
```

Phase 2 Mock Workflow 编排校验：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json
python lab_cli.py phase2 workflow report --file examples/output/phase2-content-generation-report.json
python -m pytest tests/test_phase2_workflow_orchestrator.py
```

Phase 2 试题改造 Mock Workflow 校验：

```powershell
python lab_cli.py phase2 exam-convert run --lab templates/lab/examples/basic-lab.yaml --notebook examples/notebooks/demo-lab.ipynb --reviewer teacher_1 --output examples/output/phase2-exam-conversion-report.json
python lab_cli.py phase2 exam-convert report --file examples/output/phase2-exam-conversion-report.json
python -m pytest tests/test_phase2_exam_conversion_workflow.py
```

Phase 2 PPT 生成 Mock Workflow 校验：

```powershell
python lab_cli.py phase2 ppt-generate run --input examples/input/demo-source.md --reviewer teacher_1 --slide-plan-output examples/output/phase2-ppt-slide-plan.json --output examples/output/phase2-ppt-generation-report.json
python lab_cli.py phase2 ppt-generate report --file examples/output/phase2-ppt-generation-report.json
python -m pytest tests/test_phase2_ppt_generation_workflow.py
```

Phase 2 Workflow Registry 校验：

```powershell
python lab_cli.py workflow registry list
python lab_cli.py workflow registry get --workflow-id phase2_content_generation
python lab_cli.py mcp call --tool list_workflows --arguments "{\"category\":\"ppt_generation\"}"
python lab_cli.py mcp call --tool get_workflow --arguments "{\"workflowId\":\"phase2_content_generation\"}"
start .\frontend\workflows.html
python -m pytest tests/test_phase2_workflow_registry.py
```

Phase 3 Mock 评分器接口校验：

```powershell
python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-grading-report.json
python lab_cli.py grade report --file examples/output/phase3-grading-report.json
start .\frontend\grading-report.html
python -m pytest tests/test_sandbox_mock_executor.py tests/test_cli.py tests/test_backend_mock_api.py
python -m pytest tests/test_frontend_manifest.py
```
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
