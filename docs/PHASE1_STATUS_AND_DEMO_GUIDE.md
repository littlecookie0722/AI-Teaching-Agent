# Phase 1 项目进度与演示校验说明

> 当前日期：2026-06-02  
> 项目：AI 实训平台智能化升级项目  
> 当前阶段：Phase 1 底座 / Mock 主链路收尾  
> 当前模式：`MOCK_ONLY`

## 1. 当前结论

当前项目已经完成 Phase 1 的主要底座建设，可以进行阶段性汇报和签收演示。

当前已具备：

- DSL 标准：Lab / Exam / Grading / PPT 四类 DSL Schema 和示例。
- CLI 工具：`lab_cli.py` 支持平台核心 Mock 能力调用，统一返回 JSON。
- AI Task 状态模型：AI 生成内容默认进入 `WAITING_REVIEW`。
- 人工审核门禁：未审核内容不能发布，驳回必须填写原因。
- Mock Workflow：可从本地 Markdown 素材跑通 Lab / Exam / Grading / PPT Mock 生成链路。
- Mock Provider：当前只启用 `mock` Provider，不读取密钥，不访问网络，不调用真实大模型。
- Mock Sandbox：当前只生成 Mock 评分报告，不执行选手代码。
- Backend API Mock：已实现本地请求处理函数，但不启动真实 HTTP Server。
- MCP Mock：已实现 MCP Tool manifest、Mock 调用层和调用审计，但不启动真实 MCP Server。
- 前端 2.0 静态原型：已覆盖 Dashboard、AI Task、Lab、Exam、Grading、PPT、Environment、Skills、Provider、Audit、Review、Delivery 等页面。
- 运营交付材料：已包含 Runbook、FAQ、Handoff、Demo Script、Phase 2 Readiness Gate 和交付验收页。

当前没有做：

- 不接入真实大模型。
- 不创建真实 VM / Notebook / 云资源。
- 不启动真实评分沙箱。
- 不执行选手代码。
- 不启动真实 MCP Server。
- 不启动真实 Agent。
- 不发布真实实验、考试、评分规则或 PPT。
- 不启动真正的前后端联动 Web 应用。

## 2. 当前进度判断

按项目规则推荐路线：

```text
DSL -> CLI -> Mock -> Workflow -> Sandbox -> MCP -> Agent -> Operation
```

当前已经完成到：

```text
DSL -> CLI -> Mock -> Workflow Mock -> Provider Mock -> Sandbox Mock -> MCP Mock -> Operation Mock
```

也就是说，Phase 1 的核心目标已经基本完成。现在剩余的 Phase 1 工作主要是签收、汇报、演示和少量文档收口，不是继续开发大功能。

## 3. 当前接口进度

### 3.1 CLI 命令进度

当前 CLI 入口为：

```powershell
python lab_cli.py ...
```

已覆盖的命令组：

- `phase1`: Phase 1 自检、交付包导出、验收报告生成。
- `material`: 本地素材静态分析。
- `lab`: 从本地素材生成 Lab DSL Mock。
- `exam`: 从 Lab ID 生成 Exam DSL / Grading DSL Mock。
- `ppt`: 生成 PPT DSL Mock。
- `grade`: 读取 Grading DSL 并生成 Mock 评分报告。
- `dsl`: 校验 DSL 示例文件。
- `ai-task`: 查询本地 AI Task。
- `review`: 查询待审核队列、查看详情、审核通过、驳回、Mock publish。
- `artifact`: 查询本地产物清单。
- `env`: 创建和维护本地 Mock VM / Notebook 记录。
- `provider`: 查询 Mock Provider、健康检查、Mock 生成、调用审计。
- `workflow`: 运行 Mock 主链路、查询 Workflow Run 和报告。
- `audit`: 查询统一操作审计事件。
- `mcp`: 查询 MCP Mock 工具、调用工具、查询调用审计。

CLI 统一返回格式：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {},
  "traceId": "trace_xxx"
}
```

### 3.2 Backend API Mock 进度

当前 Backend 位于 `backend/mock_api.py`。

它是本地请求处理函数，不是 HTTP 服务。支持的 Mock API 包括：

```text
GET  /api/health
GET  /api/ai-tasks
GET  /api/ai-tasks/{id}
GET  /api/review-tasks
GET  /api/review-task-summary
GET  /api/review-tasks/{id}
GET  /api/review-audit-events
GET  /api/audit-events
GET  /api/providers
GET  /api/providers/mock/health
GET  /api/provider-audit-events
GET  /api/mcp-tool-call-records
GET  /api/artifacts
GET  /api/artifacts/{id}
GET  /api/workflow-runs
GET  /api/workflow-runs/{id}
GET  /api/environments
GET  /api/environments/{id}
GET  /api/workflow/report
GET  /api/grading/report
POST /api/materials/analyze
POST /api/workflow/demo
POST /api/labs/generate
POST /api/exams/generate-from-lab
POST /api/ppt/generate
POST /api/grading/run
POST /api/providers/mock/generate
POST /api/ai-tasks/{id}/approve
POST /api/ai-tasks/{id}/reject
POST /api/environments/vm
POST /api/environments/notebook
POST /api/environments/{id}/start
POST /api/environments/{id}/stop
POST /api/environments/{id}/reset
```

这些接口目前用于测试和契约验证。它们不连接真实数据库、不启动 Web Server、不调用真实云资源。

### 3.3 前端页面进度

当前前端是静态 HTML 原型，不是可启动的 React / Vue / Vite 工程。

可演示页面包括：

- `frontend/operations-launchpad.html`: 运营演示入口。
- `frontend/console.html`: 前端 2.0 Mock 控制台。
- `frontend/dashboard.html`: Dashboard 总览。
- `frontend/ai-tasks.html`: AI 任务中心。
- `frontend/review-center.html`: 审核中心。
- `frontend/lab-generate.html`: Lab 生成页。
- `frontend/lab-review.html`: Lab 审核详情。
- `frontend/exam-generate.html`: Exam 生成页。
- `frontend/exam-review.html`: Exam 审核详情。
- `frontend/grading.html`: Grading 管理。
- `frontend/grading-report.html`: Mock 评分报告。
- `frontend/ppt.html`: PPT 管理。
- `frontend/environments.html`: 环境管理 Mock。
- `frontend/skills.html`: Skills 管理。
- `frontend/provider-settings.html`: Provider 设置。
- `frontend/audit.html`: 审计可观测页面。
- `frontend/delivery.html`: Phase 1 交付验收页。
- `frontend/operations-acceptance.html`: 运营验收总览。

这些页面可以点击浏览和讲解流程，但不会真的提交表单、调用接口或保存状态。

## 4. 核心能力说明

### 4.1 DSL 能力

DSL 全称是 `Domain-Specific Language`，即领域特定语言。

本项目中 DSL 是 AI 生成内容进入平台前的标准化中间格式。当前已支持：

- Lab DSL：实验内容结构。
- Exam DSL：考试 / 竞赛题结构。
- Grading DSL：评分规则结构。
- PPT DSL：课件结构。

价值：

- AI 输出不直接变成平台正式内容。
- AI 输出必须先形成可校验的结构化 DSL。
- DSL 默认状态为 `WAITING_REVIEW`。
- 审核通过前不得发布。

### 4.2 CLI 能力

CLI 全称是 `Command-Line Interface`，即命令行接口。

本项目中 CLI 是平台能力的工具化入口，供研发、运营和后续 MCP / Agent 调用。

价值：

- 把平台能力变成稳定命令。
- 所有命令统一返回 JSON。
- 先用 Mock 跑通流程，再接真实能力。
- 后续 Agent 不直接操作业务，而是调用受控 CLI / API。

### 4.3 审核门禁能力

当前 AI 生成类内容默认进入：

```text
WAITING_REVIEW
```

规则：

- 未审核内容不能 publish。
- `review approve` 必须记录 reviewer。
- `review reject` 必须记录 reviewer 和 reason。
- Phase 1 的 publish 也只是 Mock 状态流转，不是真实发布。

### 4.4 Mock Workflow 能力

当前可跑通一条 Mock 主链路：

```text
输入本地 Markdown
  -> 素材静态分析
  -> 生成 Lab DSL Mock
  -> 生成 Exam DSL Mock
  -> 生成 Grading DSL Mock
  -> 生成 PPT DSL Mock
  -> 创建 AI Task
  -> 进入 WAITING_REVIEW
  -> 输出 Workflow 报告
```

### 4.5 Mock 评分能力

当前 `grade run` 可读取 Grading DSL 并生成 Mock 评分报告。

但当前不会：

- 启动真实沙箱。
- 执行选手代码。
- 执行未知 Shell。
- 调用真实环境。

真实评分沙箱属于后续 Phase 3。

## 5. 推荐演示命令与作用

### 5.1 Phase 1 总自检

```powershell
python lab_cli.py phase1 check
```

作用：

- 检查 Lab / Exam / Grading / PPT DSL 示例。
- 检查 AI Task 默认 `WAITING_REVIEW`。
- 检查未审核 publish 是否被阻止。
- 检查 Backend Mock health。
- 检查素材分析 Mock。
- 检查 Artifact Mock。
- 检查审核详情与审核队列。
- 检查 Workflow Run 日志。
- 检查 Provider 是否只启用 `mock`。

期望结果：

```text
success=true
data.passed=true
data.total=20
```

汇报口径：

```text
Phase 1 自检 20 项全部通过，说明当前 DSL、CLI、Mock Workflow、审核门禁、Provider Mock 和 Backend Mock 均可用。
```

### 5.2 运行 Mock 主链路

```powershell
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/demo-report.json
```

作用：

- 从本地 Markdown 素材开始。
- 做素材静态分析。
- 串联 Lab / Exam / Grading / PPT Mock 生成。
- 创建待审核 AI Task。
- 输出本地 Workflow 报告。

汇报口径：

```text
这条命令展示从教学素材到实验、试题、评分规则和 PPT DSL 的 Mock 主链路，生成内容默认进入待审核状态。
```

### 5.3 查看待审核任务

```powershell
python lab_cli.py review list
```

作用：

- 查看当前本地 Mock store 中 `WAITING_REVIEW` 的 AI Task。
- 展示人工审核门禁。

汇报口径：

```text
AI 生成结果不会直接上线，而是进入待审核队列。
```

### 5.4 运行 Mock 评分

```powershell
python lab_cli.py grade run --grading templates/grading/examples/python-pytest.yaml --output examples/output/grading-report.json
```

作用：

- 读取 Grading DSL。
- 输出 Mock 评分报告。
- 写入本地审计事件。

汇报口径：

```text
当前已具备评分接口形态和报告结构，但 Phase 1 不执行真实选手代码，真实沙箱放到 Phase 3。
```

### 5.5 导出 Phase 1 交付包

```powershell
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
```

作用：

- 汇总 Phase 1 交付物清单。
- 汇总验收清单。
- 汇总安全断言。
- 输出本地 JSON 交付包。

汇报口径：

```text
交付包用于证明 Phase 1 的文档、示例、Schema、CLI、Mock 页面和测试材料是否齐全。
```

### 5.6 生成 Phase 1 验收报告

```powershell
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
```

作用：

- 读取交付包。
- 生成 Markdown 验收报告。
- 用于阶段签收阅读。

汇报口径：

```text
验收报告是 Phase 1 的阶段性签收材料，不会重新生成内容、不调用真实 Provider、不发布真实内容。
```

### 5.7 全量测试

```powershell
python -m pytest -q
```

作用：

- 运行项目测试套件。
- 覆盖 CLI、DSL、AI Task、审核、Provider、Workflow、Sandbox Mock、MCP Mock、前端契约、交付契约等。

当前参考结果：

```text
333 passed
```

## 6. 可演示内容

当前可做“静态页面 + CLI 实链路”的演示。

推荐演示顺序：

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\console.html
start .\frontend\dashboard.html
start .\frontend\lab-generate.html
start .\frontend\review-center.html
start .\frontend\grading-report.html
start .\frontend\audit.html
start .\frontend\delivery.html
start .\frontend\operations-acceptance.html
```

演示重点：

- `operations-launchpad.html`: 运营入口和演示路径。
- `console.html`: 前端 2.0 模块总览。
- `lab-generate.html`: 从素材到 Lab DSL 的生成形态。
- `review-center.html`: AI 结果必须人工审核。
- `grading-report.html`: Mock 评分报告结构。
- `audit.html`: Provider / MCP / Workflow / Review 审计可观测。
- `delivery.html`: 交付物 `175/175`、验收和安全断言。
- `operations-acceptance.html`: 运营验收总览。

注意事项：

- 页面是静态 Mock 原型。
- 页面不发起真实请求。
- 页面按钮不会真实提交或变更状态。
- 真正链路通过 CLI 和 Backend Mock 测试验证。

## 7. 距离 Phase 1 收尾还有多久

如果不新增真实前后端联动能力，Phase 1 当前已经达到可签收状态。

预计剩余时间：

```text
0.5 - 1 个工作日
```

剩余工作主要是：

- 跑一遍 `phase1 check`、`phase1 export`、`phase1 report`。
- 跑一遍全量测试。
- 按 `delivery/HANDOFF.md` 做人工交接确认。
- 按 `delivery/DEMO_SCRIPT_CHECKLIST.md` 做会议演示彩排。
- 确认 Phase 1 边界：仍为 `MOCK_ONLY`，不接真实 AI、不接真实云、不真实发布。

如果希望额外做“真正可交互的本地前后端演示版”，则不属于当前 Phase 1 已有范围，建议作为新增小任务评估。

预计新增时间：

```text
2 - 4 个工作日
```

可能包括：

- 为 `backend/mock_api.py` 包一层 FastAPI / Flask HTTP 服务。
- 为静态页面接入 `fetch` 调用。
- 增加本地状态刷新和表单提交。
- 增加页面端错误提示。
- 补充前后端联动测试。

## 8. 后续步骤建议

### 8.1 Phase 1 收尾

1. 固化汇报口径：Phase 1 已完成底座和 Mock 主链路。
2. 生成交付包和验收报告。
3. 进行会议演示和人工签收。
4. 明确 Phase 1 不包含真实 AI、真实云、真实沙箱和真实发布。

推荐命令：

```powershell
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest -q
```

### 8.2 Phase 2：AI Workflow

目标：

- 完善 `LLMProvider` 抽象。
- 继续坚持 MockProvider-first。
- 接入真实 Provider 前先完成安全门禁。
- Prompt 继续集中放在 `prompts/`。
- 输出必须经过 DSL Schema 校验。
- AI 输出继续默认 `WAITING_REVIEW`。

优先任务：

- LLM Provider 抽象层。
- Markdown / Shell 到 Lab DSL 的 Workflow。
- Lab DSL 到 Exam / Grading DSL 的 Workflow。
- Markdown 到 PPT DSL / Slide Plan 的 Workflow。

### 8.3 Phase 3：自动评分沙箱

目标：

- 实现真实但受控的评分运行器。
- 抽象 `SandboxExecutor`。
- 支持 `file_exists`、`stdout_contains`、`pytest` 等确定性评分。
- 限制 CPU、内存、时间、网络和文件系统。
- 输出可解释评分报告。

### 8.4 Phase 4：MCP Server

目标：

- 启动真实 MCP Server。
- MCP 工具只调用 CLI 或 Backend Service。
- 高风险工具必须进入审核，不直接执行。
- 所有 MCP 调用写入审计。

### 8.5 Phase 5：运营交付

目标：

- 将静态原型升级为真实可访问页面。
- 输出运营手册。
- 沉淀 Skills、Prompt、Workflow。
- 支持运营人员批量复用。

## 9. 会议汇报建议

建议对外汇报为：

```text
目前项目处于 Phase 1 收尾阶段。我们按 DSL -> CLI -> Mock -> Workflow 的顺序，先完成平台能力工具化和可验收化，没有直接做复杂 Agent。

当前已完成 DSL 标准、CLI Mock、AI Task 状态流转、人工审核门禁、Mock Workflow、Mock Provider、Mock Sandbox、MCP Mock、前端静态 2.0 原型和运营交付材料。

自检结果为 Phase 1 20/20 通过，全量测试持续通过，交付验收页显示交付清单 175/175 ready，安全断言通过。

当前没有接真实大模型、真实云资源、真实沙箱和真实发布，这是 Phase 1 的安全边界。下一步建议签收 Phase 1，并进入 Phase 2 的 Provider 抽象和 AI Workflow 接入。
```

## 10. 当前风险与注意事项

- 当前前端是静态 Mock 页面，不能作为真实业务系统使用。
- 当前 Backend API Mock 不启动 HTTP Server。
- 当前 Provider 只支持 Mock，不调用真实大模型。
- 当前 Sandbox 只输出 Mock 报告，不执行选手代码。
- 当前 MCP 是 Mock 调用层，不是正式 MCP Server。
- 当前 publish 只是 Mock 状态流转，不是真实发布。
- 标准答案不得展示到选手端。
- Prompt 不得散落到业务代码。
- 密钥不得进入日志、前端、交付包或 Git。
