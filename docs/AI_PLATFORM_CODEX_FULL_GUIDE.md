# AI 教学智能体（独立版）：Codex 超详细开发执行说明

> 适用对象：Codex / AI Coding Agent / 研发人员  
> 项目目标：构建一个独立运行的 AI 教学智能体，提供实验生成、智能组卷、自动评分和教学内容交付等核心能力，并通过 CLI 或 MCP 协议对外提供服务。项目不再以接入外部实训平台为目标。
> 使用方式：把本文件放到项目根目录的 `docs/AI_PLATFORM_CODEX_FULL_GUIDE.md`，同时在项目根目录放置 `AGENTS.md`，让 Codex 每次开发前读取规则。

---

# 0. 最重要的结论

这个项目不要从“单纯的对话智能体”开始做。

正确顺序是：

```text
DSL 标准化
  ↓
CLI 工具化
  ↓
Mock 主链路跑通
  ↓
AI 工作流接入
  ↓
自动评分沙箱
  ↓
MCP Tool 暴露
  ↓
智能体编排与对外服务
```

也就是说：

```text
先让智能体能力变成稳定工具
再让 AI 或外部系统调用这些工具
最后再把工具编排成高级智能体服务
```

否则很容易出现：

- AI 能说但不能稳定执行
- Prompt 很长但接口仍然报错
- Agent 自主规划失控
- 生成内容无法审核
- 自动评分不可解释
- 运营人员无法复用

---

# 1. 项目总体目标

## 1.1 业务目标

构建一个独立运行的 AI 教学智能体，覆盖：

1. 新实验生成
2. 旧实验改造成考试 / 竞赛试题
3. 自动评分脚本生成
4. 选手提交自动判分
5. VM / Notebook 实验环境维护
6. 智能体能力 CLI 化
7. MCP 工具化
8. 独立智能体前端交互页面
9. 智能体对外服务 API 接入
10. 试题判分智能体
11. 通用 AI 教学助手
12. Skills / Prompt / 工作流最佳实践沉淀
13. 智能体成品对外交付

## 1.2 技术目标

最终智能体应形成：

```text
AI 内容生成能力
AI 任务编排能力
AI 评分能力
AI 环境管理能力
AI 工具调用能力 (MCP)
AI 对外服务与交付能力
```

## 1.3 独立智能体内部闭环与对外服务模式

本项目定位为独立 AI 教学智能体，不再依赖外部实训平台的后端接口。

智能体内部核心闭环是：

```text
真实 LLM 生成 DSL
  ↓
Schema 校验与归一化
  ↓
人工审核任务与审核详情
  ↓
候选人安全预览
  ↓
受控 Docker 评分 evidence
  ↓
review decision note
  ↓
智能体内部实体持久化与版本管理
  ↓
MCP Tool / API 对外输出
```

智能体通过自身的工具链（CLI、MCP Server）对外提供服务，不再有外部平台 API base URL、平台 Token、字段映射等对接逻辑。

## 1.4 最小可行版本 MVP

MVP 不追求完整智能体，只跑通一条主链路：

```text
输入 Markdown / GitHub README / Shell 脚本
  ↓
AI 或 Mock 生成实验 DSL
  ↓
人工审核
  ↓
生成试题 DSL
  ↓
生成评分 DSL
  ↓
CLI 执行 Mock 评分
  ↓
输出评分报告
```

MVP 验收成功后，才进入真实模型、真实云资源、真实 Notebook、真实评分沙箱。

---

# 2. 项目分层架构

## 2.1 总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                        Web Frontend 2.0                     │
│ 实验生成页面 / 试题生成页面 / 评分报告 / AI任务中心 / 审核中心 │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│                         Backend API                         │
│ Lab API / Exam API / Grading API / Env API / AI Task API     │
└──────────────┬────────────────┬────────────────┬────────────┘
               │                │                │
┌──────────────▼───────┐ ┌──────▼────────┐ ┌─────▼────────────┐
│       AI Workflow     │ │     CLI       │ │    MCP Server    │
│ 实验生成/试题/评分/PPT │ │ lab-cli       │ │ 大模型工具入口     │
└──────────────┬───────┘ └──────┬────────┘ └─────┬────────────┘
               │                │                │
┌──────────────▼────────────────▼────────────────▼────────────┐
│                       Domain Services                       │
│ LabService / ExamService / GradingService / EnvironmentService│
└──────────────┬────────────────┬────────────────┬────────────┘
               │                │                │
┌──────────────▼───────┐ ┌──────▼────────┐ ┌─────▼────────────┐
│      DSL Layer        │ │ Sandbox Layer │ │ Provider Layer   │
│ Lab/Exam/Grading/PPT  │ │ 自动评分沙箱   │ │ VM/Notebook/LLM  │
└──────────────────────┘ └───────────────┘ └──────────────────┘
```

## 2.2 推荐目录结构

```text
ai-training-platform/
├── AGENTS.md
├── README.md
├── docs/
│   ├── AI_PLATFORM_CODEX_FULL_GUIDE.md
│   ├── 00_START_HERE.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_ROADMAP.md
│   ├── 03_PHASE_TASKS.md
│   ├── 04_DSL_SPEC.md
│   ├── 05_API_SPEC.md
│   ├── 06_CLI_SPEC.md
│   ├── 07_MCP_SPEC.md
│   ├── 08_TESTING_AND_ACCEPTANCE.md
│   ├── 09_SECURITY_AND_SANDBOX.md
│   ├── 10_OPERATIONS_GUIDE.md
│   └── decisions/
│       └── ADR-0001-use-dsl-cli-mcp-first.md
│
├── backend/
├── frontend/
├── cli/
├── mcp-server/
├── ai-workflows/
├── templates/
├── prompts/
├── skills/
├── sandbox/
├── examples/
└── scripts/
```

---

# 3. Codex 工作方式规范

## 3.1 每次开发前必须做什么

Codex 每次接到任务，必须先执行：

1. 阅读 `AGENTS.md`
2. 阅读当前任务相关文档
3. 确认当前任务属于哪个模块
4. 检查现有目录结构
5. 检查是否已有类似实现
6. 先生成小计划
7. 只改动必要文件
8. 开发后运行测试
9. 输出变更说明

## 3.2 Codex 每次输出必须包含

```text
本次完成：
- ...

修改文件：
- ...

如何验证：
- ...

风险与注意事项：
- ...

下一步建议：
- ...
```

## 3.3 禁止 Codex 做的事情

Codex 不得：

1. 未经要求一次性重构全项目
2. 未经要求接入真实云资源
3. 未经要求调用真实大模型
4. 把 API Key 写死进代码
5. 直接执行未知 Shell 脚本
6. 无沙箱运行选手提交代码
7. 让 AI 生成结果直接发布
8. 删除用户现有业务逻辑
9. 破坏已有接口兼容性
10. 把 Prompt 散落在业务代码中
11. 没有 Schema 就自由生成 JSON
12. 忽略错误处理和日志
13. 不写测试就声称完成

---

# 4. Phase 1：项目底座阶段

## 4.1 Phase 1 目标

Phase 1 只做基础设施，不做真实 AI，不做真实云资源。

目标是让下面链路用 Mock 数据跑通：

```text
CLI 命令
  ↓
调用 Mock Service
  ↓
生成 DSL
  ↓
写入 AI Task
  ↓
进入 WAITING_REVIEW
  ↓
审核通过
  ↓
执行 Mock 评分
  ↓
输出评分报告
```

## 4.2 Phase 1 任务清单

### Task 1：创建项目骨架

#### 目标

建立统一目录，为后续模块开发做准备。

#### 需要创建

```text
docs/
cli/
mcp-server/
ai-workflows/
templates/
prompts/
skills/
sandbox/
examples/
scripts/
```

#### 验收标准

- 所有目录存在
- 每个关键目录有 README.md
- README 说明该目录职责
- 不包含无关业务代码

#### Codex 提示词

```text
请阅读 AGENTS.md 和 docs/AI_PLATFORM_CODEX_FULL_GUIDE.md。
当前只做 Phase 1 Task 1：创建项目骨架。
要求：
1. 创建 docs、cli、mcp-server、ai-workflows、templates、prompts、skills、sandbox、examples、scripts 目录；
2. 每个目录添加 README.md；
3. README 说明目录用途、输入输出、后续扩展方向；
4. 不实现真实业务逻辑；
5. 完成后输出文件列表和下一步建议。
```

---

### Task 2：创建 DSL Schema

#### 目标

定义实验、试题、评分、PPT 的统一结构。

#### 文件

```text
templates/lab/lab.schema.json
templates/exam/exam.schema.json
templates/grading/grading.schema.json
templates/ppt/ppt.schema.json
```

#### 验收标准

- Schema 是合法 JSON Schema
- 必填字段明确
- 枚举值明确
- 支持版本号
- 支持扩展 metadata
- 有示例 YAML / JSON

#### Codex 提示词

```text
请实现 Phase 1 Task 2：创建 DSL Schema。
要求：
1. 创建 lab / exam / grading / ppt 四类 schema；
2. 每类 schema 都包含 version、metadata、content、status 字段；
3. 创建 examples 示例；
4. 添加 schema 校验脚本或测试；
5. 不接入真实 AI；
6. 输出如何校验这些 schema。
```

---

### Task 3：实现 CLI Mock 框架

#### 目标

创建统一 CLI，使未来大模型可以通过命令调用平台能力。

#### 推荐命令

```bash
lab-cli lab generate-from-source --input examples/input/demo-source.md
lab-cli exam generate-from-lab --lab-id lab_demo
lab-cli grade run --grading templates/grading/examples/python-pytest.yaml
lab-cli ppt generate --input examples/input/demo-source.md
lab-cli ai-task get --id task_demo
lab-cli review approve --task-id task_demo
lab-cli review reject --task-id task_demo --reason "内容不符合要求"
```

#### 统一返回格式

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {},
  "traceId": "trace_xxx"
}
```

#### 失败返回格式

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "errors": [
    {
      "field": "input",
      "reason": "文件不存在"
    }
  ],
  "traceId": "trace_xxx"
}
```

#### Codex 提示词

```text
请实现 Phase 1 Task 3：CLI Mock 框架。
要求：
1. 在 cli/ 下实现 lab-cli；
2. 支持 lab、exam、grade、ppt、ai-task、review 命令组；
3. 所有命令返回统一 JSON；
4. 对不存在的文件、缺少参数、非法参数返回明确错误；
5. 添加 README 和命令示例；
6. 添加基础测试；
7. 不调用真实后端、不调用真实 AI。
```

---

### Task 4：AI Task 状态模型

#### 目标

所有 AI 生成、审核、评分任务都进入统一任务系统。

#### 状态枚举

```text
PENDING
RUNNING
WAITING_REVIEW
APPROVED
REJECTED
FAILED
COMPLETED
CANCELLED
```

#### 字段建议

```text
id
taskType
title
inputType
inputRef
status
modelName
promptVersion
intermediateResultPath
finalResultPath
errorMessage
createdBy
createdAt
updatedAt
traceId
```

#### Codex 提示词

```text
请实现 Phase 1 Task 4：AI Task 状态模型。
要求：
1. 定义 AI Task 数据模型；
2. 实现状态流转校验；
3. 生成内容默认进入 WAITING_REVIEW；
4. 只有 APPROVED 后才能进入 publish 或 completed；
5. 添加测试覆盖合法和非法状态流转；
6. 暂时用本地 JSON 文件或内存存储 Mock。
```

---

### Task 5：人工审核流

#### 目标

防止 AI 生成结果直接上线。

#### 流程

```text
AI 生成内容
  ↓
WAITING_REVIEW
  ↓
人工查看
  ↓
approve / reject
  ↓
APPROVED / REJECTED
```

#### Codex 提示词

```text
请实现 Phase 1 Task 5：人工审核流。
要求：
1. CLI 支持 review approve / reject；
2. 审核动作必须记录 reviewer、reviewTime、reason；
3. reject 必须填写 reason；
4. 未审核内容不能 publish；
5. 添加状态流转测试；
6. 输出示例命令。
```

---

# 5. Phase 2：AI 工作流阶段

## 5.1 Phase 2 目标

在 Phase 1 的 Mock 链路稳定后，开始接入 AI 工作流。

但仍然不允许自动发布。

## 5.2 LLM Provider 抽象

### 目标

避免业务代码绑定某个模型厂商。

### 接口设计

```text
LLMProvider
  - generateText(prompt, options)
  - generateJson(prompt, schema, options)
  - streamGenerate(prompt, options)
```

### Provider 类型

```text
OpenAIProvider
ClaudeProvider
LocalModelProvider
MockProvider
```

### 配置要求

- API Key 只能来自环境变量
- 模型名称配置化
- 支持超时
- 支持重试
- 支持并发限制
- 支持日志脱敏

### Codex 提示词

```text
请实现 Phase 2 Task 1：LLM Provider 抽象层。
要求：
1. 定义统一 LLMProvider 接口；
2. 实现 MockProvider；
3. 预留 OpenAI / Claude / LocalModel Provider；
4. API Key 从环境变量读取，不能写死；
5. Prompt 从 prompts/ 目录读取；
6. 返回内容必须经过 schema 校验；
7. 添加单元测试。
```

---

## 5.3 新实验生成 Workflow

### 输入

```text
GitHub URL
Markdown
Shell 脚本
PDF / Word 预留
```

### 输出

```text
Lab DSL
```

### 流程

```text
资料读取
  ↓
资料清洗
  ↓
技术栈识别
  ↓
教学目标生成
  ↓
实验步骤生成
  ↓
环境配置生成
  ↓
评分点生成
  ↓
Lab DSL 校验
  ↓
创建 AI Task
  ↓
WAITING_REVIEW
```

### Codex 提示词

```text
请实现 Phase 2 Task 2：新实验生成 Workflow。
要求：
1. 支持从 Markdown 文件读取资料；
2. 支持 Shell 脚本解析；
3. 输出 Lab DSL；
4. 输出必须通过 lab.schema.json 校验；
5. 生成结果保存到 examples/output/；
6. 创建 AI Task，状态为 WAITING_REVIEW；
7. 暂时使用 MockProvider，不接入真实模型；
8. 添加测试。
```

---

## 5.4 旧实验改造成试题 Workflow

### 输入

```text
Notebook
已有 Lab DSL
云环境实验说明
```

### 输出

```text
Exam DSL
Grading DSL
```

### 挖空策略

1. 关键 API 挖空
2. 核心参数挖空
3. 关键逻辑挖空
4. 配置项挖空
5. 输出结果判断
6. 日志排错题

### Codex 提示词

```text
请实现 Phase 2 Task 3：旧实验改造成试题 Workflow。
要求：
1. 支持读取 Lab DSL；
2. 支持读取 Notebook 的 cell 内容；
3. 生成 Exam DSL；
4. 生成 Grading DSL；
5. 保留标准答案，不展示给选手；
6. 结果进入 WAITING_REVIEW；
7. 添加示例 Notebook 和测试。
```

---

## 5.5 PPT / 文档生成 Workflow

### 正确流程

```text
原始资料
  ↓
章节树
  ↓
知识点
  ↓
PPT 大纲
  ↓
Slide Plan
  ↓
PPT 文件
  ↓
人工审核
```

### 不要做

```text
PDF / 文档 → 直接让 AI 生成 PPT
```

这样效果不可控。

### Codex 提示词

```text
请实现 Phase 2 Task 4：PPT / 文档生成 Workflow。
要求：
1. 定义 PPT DSL；
2. 支持 Markdown 输入；
3. 先生成 slide plan JSON；
4. 再生成 PPT 或 Markdown 版课件；
5. 保存中间结果；
6. 进入 WAITING_REVIEW；
7. 添加示例和测试。
```

---

# 6. Phase 3：自动评分阶段

## 6.1 阶段目标

实现确定性、可解释、可审计的自动评分。

优先做：

```text
文件存在性检查
命令输出检查
pytest 单元测试
Notebook cell 执行检查
JSON 字段检查
日志关键字检查
```

暂缓：

```text
完全开放式主观题 LLM 打分
不可解释图片打分
无标准答案的自由评分
```

## 6.2 评分器架构

```text
GradingRunner
  ├── FileExistsGrader
  ├── StdoutContainsGrader
  ├── PytestGrader
  ├── NotebookGrader
  ├── JsonFieldGrader
  └── KeywordGrader
```

## 6.3 沙箱要求

所有选手代码必须：

- 在容器中执行
- 限制 CPU
- 限制内存
- 限制执行时间
- 限制网络
- 限制文件系统访问
- 记录 stdout / stderr
- 记录执行日志

## 6.4 Codex 提示词

```text
请实现 Phase 3 Task 1：自动评分沙箱 MVP。
要求：
1. 在 sandbox/grade-runner 中实现评分运行器；
2. 支持 file_exists、stdout_contains、pytest 三种评分；
3. 输入为 grading DSL；
4. 输出评分报告 JSON；
5. 每个 check 都要包含得分、是否通过、错误信息、日志；
6. 添加超时控制；
7. 添加测试；
8. 不允许直接在宿主机执行未知代码，至少要抽象出 SandboxExecutor。
```

---

# 7. Phase 4：MCP 与智能体阶段

## 7.1 阶段目标

让大模型可以通过 MCP 调用平台能力。

## 7.2 MCP Tool 列表

```text
generate_lab_from_source
generate_exam_from_lab
generate_grading_script
run_grading
create_vm_environment
create_notebook_environment
generate_ppt
generate_acceptance_doc
publish_lab
publish_exam
```

## 7.3 MCP Tool 安全等级

| 工具 | 风险等级 | 是否需要审核 |
|---|---:|---|
| generate_lab_from_source | 低 | 是 |
| generate_exam_from_lab | 中 | 是 |
| generate_grading_script | 中 | 是 |
| run_grading | 中 | 否 |
| create_vm_environment | 高 | 是 |
| publish_lab | 高 | 是 |
| publish_exam | 高 | 是 |
| destroy_environment | 极高 | 必须二次确认 |

## 7.4 Codex 提示词

当前项目已有 MCP Tool manifest、本地 MCP Server Mock、line-delimited JSON-RPC stdio server 和客户端视角 stdio smoke。后续不得从零重写 MCP Server 或追加同义 mock server 壳；默认只封装已稳定 CLI / Backend API，或推进工具权限、审计和真实客户端配置。

当前本地验证命令：

```powershell
python lab_cli.py mcp server-info
python lab_cli.py mcp server-tools
python lab_cli.py mcp server-call --tool analyze_material --arguments "{\"input\":\"examples/input/demo-source.md\"}"
python lab_cli.py mcp stdio-smoke --input examples/input/demo-source.md --output examples/output/mcp-stdio-client-smoke.json
```

```text
请实现 Phase 4 Task 1：MCP Server MVP。
要求：
1. 在 mcp-server/ 中实现 MCP 工具服务；
2. 每个工具只调用 CLI 或后端 Service；
3. 工具入参必须定义 schema；
4. 工具出参必须是统一 JSON；
5. 高风险工具只创建待审核任务，不直接执行；
6. 添加 README，说明如何启动和调试；
7. 添加 Mock 测试。
```

---

# 8. Phase 5：运营交付阶段（暂停扩展）

当前 Phase 5 运营交付内容只作为历史交付和本地演示参考，不再作为后续默认开发目标。后续不得继续新增运营页面、运营验收清单、运营交付包、运营手册、运营向 Skills / Prompt 文档或同类内容，除非用户明确恢复运营交付任务。

本阶段已有内容只允许：

1. 修正文档错误。
2. 补充归档状态说明。
3. 修复会阻塞核心演示的坏链接或明显错误。

本阶段不再新增需求。

## 8.1 目标

研发负责 0 到 1：

```text
能力建设
工具开发
模板建设
审核流程
部署说明
```

运营负责 1 到 N：

```text
批量生成实验
批量审核
复用 Skills
复用 Prompt
发布到平台
```

以上目标当前暂停执行。后续默认回到 Lab / Exam / Grading / PPT / Sandbox / Review / MCP 等核心能力建设。

## 8.2 交付内容

```text
可视化网页
IP + 端口访问
独立智能体
操作手册
运维手册
常见问题
示例素材
模板库
Skills 库
```

## 8.3 Codex 提示词

```text
请实现 Phase 5 Task 1：运营交付文档。
要求：
1. 创建 docs/10_OPERATIONS_GUIDE.md；
2. 写清楚运营如何发起实验生成；
3. 写清楚运营如何审核 AI 结果；
4. 写清楚运营如何复用 Skills；
5. 写清楚常见失败原因；
6. 写清楚如何导出交付材料；
7. 添加截图占位符和示例流程。
```

该提示词已暂停使用。除非用户明确恢复运营交付任务，否则 Codex 不得继续按该提示词开发。

---

# 9. 数据库设计

## 9.1 ai_task

```sql
CREATE TABLE ai_task (
  id VARCHAR(64) PRIMARY KEY,
  task_type VARCHAR(64) NOT NULL,
  title VARCHAR(255),
  input_type VARCHAR(64),
  input_ref TEXT,
  status VARCHAR(32) NOT NULL,
  model_name VARCHAR(128),
  prompt_version VARCHAR(64),
  intermediate_result_path TEXT,
  final_result_path TEXT,
  error_message TEXT,
  created_by VARCHAR(64),
  reviewed_by VARCHAR(64),
  review_reason TEXT,
  trace_id VARCHAR(128),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  reviewed_at TIMESTAMP
);
```

## 9.2 lab_template

```sql
CREATE TABLE lab_template (
  id VARCHAR(64) PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  category VARCHAR(128),
  difficulty VARCHAR(32),
  dsl_content TEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_by VARCHAR(64),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## 9.3 exam_question

```sql
CREATE TABLE exam_question (
  id VARCHAR(64) PRIMARY KEY,
  lab_id VARCHAR(64),
  question_type VARCHAR(64),
  question_content TEXT NOT NULL,
  answer_content TEXT,
  grading_dsl TEXT,
  status VARCHAR(32),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## 9.4 grading_record

```sql
CREATE TABLE grading_record (
  id VARCHAR(64) PRIMARY KEY,
  submission_id VARCHAR(64) NOT NULL,
  grading_dsl TEXT NOT NULL,
  score DECIMAL(5,2),
  detail_report TEXT,
  logs TEXT,
  status VARCHAR(32),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## 9.5 environment_instance

```sql
CREATE TABLE environment_instance (
  id VARCHAR(64) PRIMARY KEY,
  env_type VARCHAR(64) NOT NULL,
  provider VARCHAR(64),
  image VARCHAR(255),
  status VARCHAR(32),
  owner_id VARCHAR(64),
  resource_config TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

# 10. API 设计

## 10.1 AI Task API

```http
POST /api/ai-tasks
GET /api/ai-tasks/{id}
GET /api/ai-tasks
POST /api/ai-tasks/{id}/retry
POST /api/ai-tasks/{id}/approve
POST /api/ai-tasks/{id}/reject
```

## 10.2 实验 API

```http
POST /api/labs/generate
GET /api/labs/{id}
GET /api/labs
POST /api/labs/{id}/approve
POST /api/labs/{id}/reject
POST /api/labs/{id}/publish
```

## 10.3 试题 API

```http
POST /api/exams/generate-from-lab
GET /api/exams/{id}
POST /api/exams/{id}/approve
POST /api/exams/{id}/reject
POST /api/exams/{id}/publish
```

## 10.4 评分 API

```http
POST /api/grading/run
GET /api/grading/{id}
GET /api/grading/{id}/report
```

## 10.5 环境 API

```http
POST /api/environments/vm
POST /api/environments/notebook
GET /api/environments/{id}
POST /api/environments/{id}/start
POST /api/environments/{id}/stop
POST /api/environments/{id}/reset
POST /api/environments/{id}/snapshot
DELETE /api/environments/{id}
```

## 10.6 统一响应

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "traceId": "trace_xxx"
}
```

---

# 11. DSL 设计详解

## 11.1 Lab DSL

```yaml
version: "1.0"
kind: "Lab"
metadata:
  id: "lab_claude_code_intro"
  title: "Claude Code 入门实验"
  category: "AI 工具应用"
  difficulty: "beginner"
  durationMinutes: 60
  tags:
    - "AI"
    - "Claude Code"
status: "WAITING_REVIEW"
spec:
  objectives:
    - "理解 AI 编码助手的基本使用方式"
    - "掌握用 AI 修改代码的基本流程"
  targetUsers:
    - "高职学生"
    - "本科低年级"
  environment:
    type: "ubuntu-vm"
    image: "ubuntu-22.04"
    resources:
      cpu: 2
      memoryGb: 4
  materials:
    - type: "markdown"
      path: "examples/input/demo-source.md"
  steps:
    - id: "step_1"
      title: "环境检查"
      instruction: "检查 Node.js 和 Git 是否安装"
      commands:
        - "node -v"
        - "git --version"
      expectedResult: "能正常输出版本号"
  grading:
    ref: "grading_claude_code_intro"
```

## 11.2 Exam DSL

```yaml
version: "1.0"
kind: "Exam"
metadata:
  id: "exam_notebook_fill_blank"
  title: "Notebook 数据清洗挖空题"
  sourceLabId: "lab_data_cleaning"
  difficulty: "intermediate"
status: "WAITING_REVIEW"
spec:
  questionType: "notebook_fill_blank"
  totalScore: 100
  questions:
    - id: "q1"
      title: "补全缺失的数据读取代码"
      stem: "请补全 Pandas 读取 CSV 文件的代码"
      blankCode: "df = pd.____('data.csv')"
      answer: "read_csv"
      score: 20
      gradingRef: "check_q1"
```

## 11.3 Grading DSL

```yaml
version: "1.0"
kind: "Grading"
metadata:
  id: "grading_python_basic"
  title: "Python 基础评分"
status: "APPROVED"
spec:
  totalScore: 100
  timeoutSeconds: 30
  checks:
    - id: "check_file"
      type: "file_exists"
      path: "result.csv"
      score: 20
    - id: "check_stdout"
      type: "stdout_contains"
      command: "python main.py"
      expected:
        - "accuracy"
      score: 30
    - id: "check_pytest"
      type: "pytest"
      path: "tests/test_main.py"
      score: 50
```

## 11.4 PPT DSL

```yaml
version: "1.0"
kind: "PPT"
metadata:
  id: "ppt_ai_tools_course"
  title: "AI 工具应用课程"
  audience: "学生"
  durationMinutes: 45
status: "WAITING_REVIEW"
spec:
  theme:
    style: "modern"
    language: "zh-CN"
  slides:
    - id: "slide_1"
      type: "title"
      title: "AI 工具应用课程"
      subtitle: "Claude Code 与智能编程实践"
    - id: "slide_2"
      type: "content"
      title: "学习目标"
      bullets:
        - "理解 AI 编程助手的作用"
        - "掌握基础使用流程"
        - "完成一个代码修改任务"
```

---

# 12. 前端 2.0 页面规划

## 12.1 页面列表

```text
/dashboard
/ai-tasks
/labs
/labs/generate
/labs/:id/review
/exams
/exams/generate
/grading
/grading/:id/report
/environments
/skills
/settings/providers
```

## 12.2 核心组件

```text
AiTaskStatusBadge
AiTaskTimeline
LabDslPreview
ExamDslPreview
GradingReportPanel
EnvironmentStatusCard
ReviewActionBar
PromptVersionSelector
SkillCard
WorkflowLogViewer
```

## 12.3 页面优先级

第一批页面：

1. AI 任务中心
2. 实验生成页面
3. 实验审核页面
4. 自动评分报告页面

第二批页面：

1. 试题生成页面
2. 环境管理页面
3. Skills 管理页面
4. Provider 配置页面

---

# 13. 安全规范

## 13.1 API Key

必须：

- 从环境变量读取
- 不进入日志
- 不进入数据库
- 不进入前端
- 不进入 Git

## 13.2 Shell 脚本

未知 Shell 脚本不得直接执行。

必须：

```text
静态分析
  ↓
风险识别
  ↓
人工确认
  ↓
沙箱执行
```

## 13.3 选手代码

所有选手代码必须在沙箱执行。

禁止：

- 直接在宿主机执行
- 访问宿主机敏感路径
- 默认开放网络
- 无限运行
- 无限写磁盘

## 13.4 发布操作

以下操作必须人工审核：

- 发布实验
- 发布考试
- 创建真实云资源
- 销毁环境
- 修改生产配置
- 批量生成内容入库

---

# 14. 测试策略

## 14.1 单元测试

覆盖：

- DSL 校验
- 状态流转
- CLI 参数解析
- 评分器逻辑
- Provider Mock
- Workflow 输出

## 14.2 集成测试

覆盖：

```text
输入 demo-source.md
  ↓
生成 Lab DSL
  ↓
审核
  ↓
生成 Exam DSL
  ↓
生成 Grading DSL
  ↓
执行 Mock Grading
  ↓
输出 Report
```

## 14.3 安全测试

覆盖：

- 超时命令
- 非法路径
- 缺少文件
- Shell 注入
- 大文件输入
- JSON Schema 错误
- 状态非法流转

---

# 15. 研发推进节奏

## 第 1 周

完成：

- 目录结构
- AGENTS.md
- DSL Schema
- 示例 YAML
- CLI Mock

## 第 2 周

完成：

- AI Task 模型
- 审核流
- Mock Workflow
- 基础测试

## 第 3 周

完成：

- LLM Provider 抽象
- Prompt 管理
- 实验生成 Workflow Mock
- 试题生成 Workflow Mock

## 第 4 周

完成：

- 评分 DSL
- 评分器 MVP
- 评分报告
- 沙箱抽象

## 第 5 周

完成：

- MCP Server MVP
- MCP Tool Schema
- CLI 对接 MCP
- 高风险操作审核

## 第 6 周

完成：

- 前端 AI 任务中心
- 实验生成页面
- 审核页面
- 评分报告页面

---

# 16. 推荐给 Codex 的总控提示词

把下面这段作为第一次任务发给 Codex：

```text
请先完整阅读项目根目录的 AGENTS.md，以及 docs/AI_PLATFORM_CODEX_FULL_GUIDE.md。

当前项目是“AI 实训平台智能化升级项目”，目标包括：
1. AI 生成新实验；
2. 旧实验改造成考试 / 竞赛试题；
3. 自动生成评分脚本并机器判分；
4. 管理 VM / Notebook 实验环境；
5. 平台能力 CLI 化；
6. 后续封装 MCP Tools；
7. 最终形成可被运营复用的 Skills 和智能体。

当前只允许做 Phase 1：项目底座。
不要接入真实大模型。
不要接入真实云资源。
不要做真实发布。
不要无沙箱执行代码。

请完成：
1. 检查当前项目结构；
2. 如果缺少 docs、cli、mcp-server、ai-workflows、templates、prompts、skills、sandbox、examples、scripts 目录，请创建；
3. 创建 lab / exam / grading / ppt 四类 DSL schema；
4. 创建每类 DSL 的 examples；
5. 创建 lab-cli Mock 框架；
6. CLI 支持 lab、exam、grade、ppt、ai-task、review 命令组；
7. 所有 CLI 统一返回 JSON；
8. 创建 AI Task 状态模型；
9. 实现 WAITING_REVIEW、APPROVED、REJECTED 等状态流转；
10. 添加 README 和基础测试；
11. 输出本次完成内容、修改文件、验证方式、下一步建议。

请先给出执行计划，再开始修改文件。
```

---

# 17. 后续每轮给 Codex 的提示词模板

## 17.1 开发新模块

```text
请阅读 AGENTS.md 和 docs/AI_PLATFORM_CODEX_FULL_GUIDE.md。
当前任务属于【模块名】。
只实现该模块的最小可用版本，不要扩展无关功能。

任务目标：
- ...

涉及文件：
- ...

实现要求：
1. ...
2. ...
3. ...

验收标准：
1. ...
2. ...
3. ...

测试要求：
1. ...
2. ...

完成后请输出：
- 修改文件
- 实现说明
- 如何验证
- 风险点
- 下一步建议
```

## 17.2 修复问题

```text
请阅读 AGENTS.md。
现在修复以下问题：

问题现象：
- ...

期望结果：
- ...

限制：
1. 只做最小修复；
2. 不重构无关代码；
3. 不改变已有公共接口，除非说明原因；
4. 添加回归测试；
5. 输出根因分析。

请先定位问题，再修改代码。
```

## 17.3 让 Codex 做自检

```text
请基于当前代码进行一次自检。
重点检查：
1. 是否符合 AGENTS.md；
2. 是否符合 docs/AI_PLATFORM_CODEX_FULL_GUIDE.md；
3. 是否有硬编码密钥；
4. 是否有未测试的核心逻辑；
5. 是否有未处理异常；
6. 是否有 AI 结果绕过审核；
7. 是否有无沙箱执行代码；
8. CLI 返回格式是否统一；
9. DSL 是否经过 schema 校验；
10. README 是否更新。

请输出问题清单和修复建议，不要直接修改代码。
```

---

# 18. 当前最推荐的落地顺序

你现在应该这样推进：

```text
第一步：把 AGENTS.md 和本指南放进项目
第二步：让 Codex 创建 Phase 1 目录和 DSL
第三步：让 Codex 实现 CLI Mock
第四步：让 Codex 实现 AI Task 和审核流
第五步：跑通 MVP 主链路
第六步：接入 MockProvider 的 AI Workflow
第七步：接入真实 LLM Provider
第八步：实现评分沙箱
第九步：实现 MCP Server
第十步：开发前端 2.0 页面
第十一步：沉淀研发复用 Skills / Prompt / Workflow
第十二步：收口核心演示闭环；运营使用手册暂停扩展
```

---

# 19. 最终交付物清单

## 19.1 研发交付

```text
后端服务
前端页面
CLI 工具
MCP Server
AI Workflow
评分沙箱
DSL Schema
测试用例
部署脚本
```

## 19.2 文档交付

```text
架构设计文档
开发说明文档
DSL 规范
API 规范
CLI 规范
MCP Tool 规范
测试验收文档
安全规范
运营手册（已收尾，暂停扩展）
Skills 使用说明
```

## 19.3 运营交付（归档参考）

运营交付已完成阶段性收尾，以下内容只作为现有资料索引和本地演示参考。除非用户明确恢复运营任务，否则不再新增或扩展。

```text
可视化网页
IP + 端口访问方式
独立智能体
实验生成模板
试题生成模板
PPT 生成模板
验收材料生成模板
常见问题手册
```

---

# 20. 判断项目是否走对的标准

如果做到下面这些，方向就是对的：

1. 没有真实 AI 时，Mock 主链路也能跑通。
2. 每个 AI 输出都有 DSL。
3. 每个 DSL 都能校验。
4. 每个 CLI 都返回 JSON。
5. 每个高风险操作都需要审核。
6. 每个评分结果都可解释。
7. 每个 Workflow 都有日志。
8. 研发人员能复用模板；运营复用材料仅保留现有归档。
9. Codex 每次开发都有明确边界。
10. Agent 只是编排工具，不承载不稳定业务逻辑。

---

# 21. 一句话原则

不要先做“会聊天的智能体”。

要先做：

```text
可校验的 DSL
可调用的 CLI
可审计的 Workflow
可解释的评分器
可复用的 Skills
可控的 MCP Tools
```

这些稳定之后，智能体自然就能做起来。

---

# 22. 阶段封口与核心业务切换规则

## 22.1 为什么增加本章

本项目强调安全门禁，但安全门禁不能无限拆分。门禁的目标是让真实 SDK、真实请求、真实云资源和真实发布在可审计边界内发生，而不是让项目长期停留在“新增禁用壳”的循环里。

因此从当前版本开始，Codex 必须把“继续新增安全壳”视为例外，把“进入核心业务开发”视为默认方向。

## 22.2 已经完成的安装前封口点

安装前和真实请求发送前的封口点是：

```text
real-llm-request-send-attempt-gate-disabled
```

完成该点后，不再新增同义或更细粒度的：

- request send disabled shell
- executor disabled shell
- authorization disabled shell
- final execution disabled shell
- pre-install disabled shell
- gate disabled shell
- review-only shell

除非用户明确说明新增安全壳要解决的风险、输入、输出、验收标准和停止条件，否则 Codex 必须拒绝继续拆分，并转向下一阶段。

## 22.3 下一阶段固定路线

完成 `real-llm-request-send-attempt-gate-disabled` 后，后续固定路线为：

```text
1. SDK 安装执行收口说明：已完成，见 `docs/13_REAL_SDK_INSTALL_EXECUTION.md`
2. 真实 SDK 依赖安装或依赖文件变更：已完成，`requirements.txt` 已安装
3. SDK import 验证：已完成，`import openai` 通过
4. 环境变量存在性边界验证，不输出密钥值：已完成，见 `docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md`
5. SDK client 构造边界验证：已完成，见 `docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md`
6. 最小真实 LLM 单请求 PoC：已实现，见 `docs/15_REAL_LLM_MINIMAL_POC.md`
7. 将真实 LLM 能力接回 Lab DSL 生成 Workflow：已实现，见 `docs/16_REAL_LLM_WORKFLOW_RECONNECT.md`
8. 核心业务开发：下一步，优先做实验生成、审核质量信号、试题转换、评分脚本生成、评分沙箱、审核中心和 MCP 核心工具；运营复用暂停扩展
```

这 8 步是切换到核心业务的上限路线，不得在其中再插入新的禁用壳层级。

当前默认下一步是第 8 步核心业务开发。除非用户明确要求，否则不得再新增同义的请求发送门禁、执行器禁用壳或 review-only 模块。

## 22.4 核心业务优先级

真实 SDK 打通后，核心业务开发优先级如下：

1. AI 生成教学实验：输入 Markdown / README / Shell 静态分析结果，输出 Lab DSL，默认 `WAITING_REVIEW`。
2. 旧实验改造成考试 / 竞赛题：输入 Lab DSL / Notebook，输出 Exam DSL 与 Grading DSL，标准答案不得展示给选手端。
3. 自动评分脚本生成：输入 Exam DSL / Grading 需求，输出 Grading DSL 和可审计评分计划。
4. 自动评分沙箱：在受控环境中执行确定性评分，输出可解释评分报告。
5. 审核中心：服务 Lab / Exam / Grading / PPT 的人工审核、导入预览、签收和阻断发布，不扩展运营流程。
6. MCP 与 Agent 编排：只编排已经稳定的 CLI / API 工具，不把业务规则藏在 Agent prompt 中。

## 22.4.1 独立智能体数据管理与对外服务

本智能体的核心数据流转和服务输出均在内部闭环完成，不依赖外部实训平台接口。

智能体默认不得涉及以下内容：

- 要求用户提供外部平台 API base URL 或 `AGENT_API_TOKEN`。
- 执行针对外部平台的实体导入请求或状态查询。
- 进行外部平台字段映射或平台侧签收、发布等操作。

智能体内部应实现：
1.  **实体持久化**：Lab/Exam/Grading 等实体在智能体内部数据库的存储与版本管理。
2.  **状态管理**：审核、评分等状态在智能体内部的完整流转。
3.  **对外服务**：通过 MCP Tool 或 API 将智能体能力（如生成、评分、查询）对外暴露，供其他智能体或系统调用。

## 22.5 下一步建议格式

Codex 每次输出“下一步建议”必须包含一条智能模式建议：

```text
建议智能模式：GPT-5.5 高智能模式 / GPT-5.5 超高智能模式
```

选择规则：

- 文档、Mock、普通代码、测试修复：高智能模式。
- 真实 SDK 安装、真实依赖解析、环境变量读取边界、SDK import、client 构造、真实 LLM 单请求 PoC：超高智能模式。

## 22.6 判断是否偏离路线

出现以下情况时，Codex 必须停止继续实现，并先修正文档或计划：

- 下一步建议又出现新的 `*-disabled`、`*-gate`、`*-review-only` 模块，但没有明确用户要求。
- 已经到达 SDK 安装前封口点，却继续新增 request-send 链路模型。
- 新任务没有服务于 Lab / Exam / Grading / PPT / Sandbox / Review / MCP 任一核心业务。
- 测试只证明“仍然不会发生任何真实动作”，但没有推动 SDK 安装或核心业务能力。

## 22.6.1 当前进度地图强制索引

`docs/24_PROJECT_PROGRESS_MAP.md` 是当前项目的强制执行索引，用于回答“现在实现了什么、还有什么没做、每个功能复杂度、下一步做什么、做到哪里必须停”。

从该文档加入后，Codex / AI Coding Agent 后续继续开发时必须遵守：

1. 每次开发前读取 `AGENTS.md`、本指南和 `docs/24_PROJECT_PROGRESS_MAP.md`。
2. 若历史 README、旧 Phase 文档或旧对话计划与 `docs/24_PROJECT_PROGRESS_MAP.md` 冲突，以 `docs/24_PROJECT_PROGRESS_MAP.md` 的当前路线和停止线为准。
3. 优先推进该文档的 P0/P1 核心业务任务，尤其是真实 LLM 输出稳定性、演示闭环、审核详情真实化、导入预览和受控评分沙箱。
4. 功能达到该文档的“做到什么就停”后，必须转入下一项，不得继续围绕同一功能追加同义 planning、review、gate、disabled shell、operations page 或验收壳。
5. 如果用户只说“继续”，默认从 `docs/24_PROJECT_PROGRESS_MAP.md` 中尚未完成且优先级最高的任务继续。

## 22.7 运营内容暂停规则

运营内容当前已完成简单收尾并暂停扩展。Codex 后续默认不得继续新增：

- `frontend/operations-*` 页面。
- `delivery/` 下的运营交付包、签收包、演示脚本或运营手册。
- 面向运营验收的 checklist、signoff、acceptance、handoff、runbook。
- 以运营复用为目标的新 Skill、Prompt 或 Workflow 文档。
- 将下一步建议导向运营交付、运营验收或外部平台运营交付。

允许的例外只有三类：

1. 用户明确说“恢复运营交付”或指定具体运营材料。
2. 现有运营文档有错字、坏链接或和核心演示冲突，需要最小修复。
3. 核心功能必须引用已有运营材料时，只做链接说明，不扩展运营需求。

后续默认路线是核心业务开发：真实 LLM 输出质量、DSL 归一化、评分 DSL、受控评分沙箱、智能体内部审核与预览、MCP 核心工具和后端 API 服务。
