# 18_REAL_LLM_DEMO_WORKFLOW

状态：已实现第一版。

本文件记录“演示真实大模型产出成果”的 Phase 2 工作流。它不是新的安全门禁、禁用壳或评审壳；它是在已有 SDK、client、最小 Lab PoC 和 Workflow 回接基础上，直接进入核心业务演示的一版实现。

## 范围

已实现：

- `phase2 workflow run --provider-mode real-llm-demo`
- 真实 LLM 生成四类 DSL：Lab、Exam、Grading、PPT。
- 每类 DSL 各发起一次真实 LLM 请求，总计 4 次请求；默认使用 OpenAI Responses API，OpenAI-compatible endpoint 不支持时可降级到 Chat Completions。
- 每次请求都使用对应 JSON Schema response format，并在本地再次执行 DSL Schema 校验。
- 生成结果写入 `examples/output/demo-real-*.json` 或 CLI 指定路径。
- Workflow Report、AI Task、Artifact、WorkflowRun、Provider 审计统一记录真实调用边界。
- 真实调用失败时会在 `--output` 指定位置写入 `PHASE2_WORKFLOW_FAILURE_REPORT`，保留 Provider 错误上下文、Schema 失败诊断、素材摘要和部分输出路径存在性，不创建 AI Task、不发布内容。
- 所有生成 DSL 仍为 `WAITING_REVIEW`，审核通过前不得发布。
- 可用 `exam candidate-preview` 将真实生成的 Exam DSL 导出为候选人预览 JSON，标准答案字段和答案文本不得出现在输出中。
- `review detail` 已聚合真实 Demo 的 `responseId`、token `usage`、Prompt / Model、Provider 审计摘要和 Exam 候选人预览摘要，供审核页直接展示。

未实现：

- 不把真实 LLM 设为默认 Provider。
- 不自动发布实验、试题、评分规则或课件。
- 不创建真实 VM / Notebook / 云资源。
- 不启动真实 Agent。
- 不执行评分沙箱或选手代码。
- 不生成真实 PPTX 文件。

## 输入说明

- `--input`: 本地 Markdown 素材路径，默认 `examples/input/demo-source.md`。
- `--model`: 模型名；也可通过 `OPENAI_MODEL` 提供。
- `OPENAI_API_KEY`: 必须从环境变量读取，不会返回或写入日志。
- `OPENAI_BASE_URL`: 可选，用于 OpenAI-compatible endpoint；默认先调用 Responses API，如果 endpoint 返回 404 / NotFound，会降级到 Chat Completions，并继续做本地 DSL Schema 校验。
- `--target-users`、`--duration-minutes`、`--difficulty`、`--tech-tags`、`--teaching-style`: Lab 生成上下文，会传给真实 LLM 并写入审核质量信号。
- `--real-demo-*-output`: 四类真实 DSL 输出路径。

## 命令

调用真实模型前可先做只读配置检查；该命令不会接收或输出 API Key，不创建 client，也不发送请求：

```powershell
python lab_cli.py provider real-llm-runtime-config --model deepseek-v4-flash --base-url https://api.deepseek.com
```

`readyForRealLlmCommand=true` 只表示当前 `OPENAI_API_KEY` 环境变量存在且模型名已通过环境变量或 `--model` 提供；它不代表已经发起真实调用，也不代表审核、发布或平台导入已获授权。

该只读摘要还会返回：

- `commandReadiness`: 结构化说明当前 shell 是否可以直接运行真实 LLM 命令、缺少哪些必备项，以及下一步应设置 API Key、补模型名还是运行带显式确认的 workflow。
- `safeCommandTemplates`: 无密钥命令模板，包含 PowerShell API Key 环境变量占位符、`real-llm-runtime-config` 参数数组和 `phase2 workflow run --provider-mode real-llm` 参数数组；模板不会包含真实 API Key 值。

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-real-llm-demo-report.json --provider-mode real-llm-demo --real-demo-lab-output examples/output/demo-real-lab.json --real-demo-exam-output examples/output/demo-real-exam.json --real-demo-grading-output examples/output/demo-real-grading.json --real-demo-ppt-output examples/output/demo-real-ppt.json --model <model> --target-users "平台开发者" --duration-minutes 45 --tech-tags "LLM" --explicit-real-call-opt-in --confirm-demo-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

读取报告：

```powershell
python lab_cli.py phase2 workflow report --file examples/output/phase2-real-llm-demo-report.json
```

如果 Workflow 失败，`--output` 位置会保存失败报告。Schema 校验失败时重点查看：

- `providerErrorContext.schemaFailureDiagnostic`
- `schemaFailureDiagnostic.suspectedDriftTypes`
- `schemaFailureDiagnostic.recommendedActions`

失败报告不包含 API Key、原始 DSL 正文、标准答案或 gradingRef 原值。

导出真实 Demo 试题的候选人预览：

```powershell
python lab_cli.py exam candidate-preview --exam examples/output/demo-real-exam.json --output examples/output/demo-real-exam-candidate-preview.json
```

读取已有真实 LLM Workflow Report 和四类 DSL 做本地只读校验：

```powershell
python lab_cli.py phase2 real-dsl-demo verify --workflow-report examples/output/phase2-real-llm-report.json --lab examples/output/real-llm-lab.json --exam examples/output/real-llm-exam.json --grading examples/output/real-llm-grading.json --ppt examples/output/real-llm-ppt.json --output examples/output/real-llm-demo-local-verification.json
```

`phase2 real-dsl-demo verify` 不重新调用真实 LLM、不读取密钥、不创建 AI Task、不自动审核和不发布；它只读取已有报告与 DSL，输出 Schema / 状态 / 内容数量 / Grading assessmentPlan / 内容质量阻塞 / 下一步建议。

基于已有真实 Demo 产物生成演示包：

```powershell
python lab_cli.py phase2 demo-bundle build --workflow-report examples/output/phase2-real-llm-report.json --lab examples/output/real-llm-lab.json --exam examples/output/real-llm-exam.json --grading examples/output/real-llm-grading.json --ppt examples/output/real-llm-ppt.json --submission examples/submissions/readonly-demo --readonly-evidence-grading-output examples/output/real-llm-demo-readonly-evidence-grading.json --readonly-evidence-report-output examples/output/real-llm-demo-readonly-evidence-report.json --output examples/output/real-llm-demo-bundle.json
```

`phase2 demo-bundle build` 只复放已有真实产物，执行本地 Schema 校验、候选人预览脱敏、Grading 归一化、真实沙箱前预检和只读沙箱报告收口；它还会生成独立只读 evidence 演示层，用演示提交目录里的 `result.csv` / `metrics.json` 产出可展示评分证据，不修改原始真实 LLM Grading。它不新增 LLM 请求、不读取密钥、不访问网络。

## 输出说明

报告关键字段：

```json
{
  "mode": "REAL_LLM_DEMO_WORKFLOW",
  "providerMode": "real-llm-demo",
  "providerAdapter": "openai_responses_sdk_demo_adapter",
  "generatedDsl": {
    "lab": {"status": "WAITING_REVIEW"},
    "exam": {"status": "WAITING_REVIEW"},
    "grading": {"status": "WAITING_REVIEW"},
    "ppt": {"status": "WAITING_REVIEW"}
  },
  "safety": {
    "realLlmCalled": true,
    "realLlmGeneratedKinds": ["lab", "exam", "grading", "ppt"],
    "realLlmRequestCount": 4,
    "realPublish": false,
    "sandboxExecuted": false,
    "contestantCodeExecuted": false
  }
}
```

本地状态：

- 创建 4 个 `WAITING_REVIEW` AI Task。
- 写入 4 条真实 Provider 调用审计。
- Provider 调用摘要会记录实际使用的 `apiSurface`，例如 `responses`、`chat.completions` 或 `chat.completions.json_object`。
- 写入 Material Analysis、4 个 DSL Artifact 和 1 个 Workflow Report Artifact。
- `contentQualitySummary` 和每个 `generatedDsl.<kind>.contentQualitySummary` 会返回 `decisionStatus`、`recommendedAction`、`requiresRevisionBeforeImportPreview`、`requiresEvidenceBeforeFinalApproval`、`blockers` 和 `warnings`，用于把真实 LLM 输出分为可进入导入预览、带警告复核、需先修订、Grading 需先补 evidence 等状态。
- Grading DSL 只生成评分计划，不执行评分。
- PPT DSL 只生成结构化课件计划，不生成真实 PPTX。
- Exam 候选人预览输出 `ExamCandidatePreview`，固定 `answerVisibleToCandidate=false`，不包含 `questions[].answer`；如果题干、挖空代码或其它候选人字段包含答案文本，命令会返回 `CANDIDATE_PREVIEW_ANSWER_LEAK_DETECTED`。
- 审核详情输出 `reviewPage.providerSummary`，包含 `responseIds`、`usage.totalTokens`、`providerCallAuditEventIds`、`auditSummary` 和每次调用的非敏感摘要；同时输出 `candidatePreview`，只包含题目数量、分值、脱敏状态和泄漏检测结果，不返回候选人题目正文数组。

## 失败策略

- 缺少显式确认：返回 `REAL_LLM_DEMO_DSL_CONFIRMATION_REQUIRED`。
- 缺少 `OPENAI_API_KEY`：返回 `REAL_LLM_DEMO_DSL_SECRET_REQUIRED`。
- 缺少模型名：返回 `REAL_LLM_DEMO_DSL_MODEL_REQUIRED`。
- SDK 未安装：返回 `REAL_LLM_DEMO_DSL_SDK_IMPORT_FAILED`。
- 模型输出不是合法 JSON 或不符合 Schema：返回 `REAL_LLM_DEMO_DSL_INVALID_JSON` 或 `REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED`。
- Provider 会先尝试拆掉常见可恢复包装：Markdown `json` code fence、单元素数组根节点，以及 `dsl` / `data` / `result` / `labDsl` / `examDsl` / `gradingDsl` / `pptDsl` 等 envelope；拆包后仍执行本地归一化和 Schema 校验。
- Provider 会在 canonical 字段为空时提升常见别名字段，减少 OpenAI-compatible 模型因字段命名习惯不同导致的误失败：例如 Lab 的 `learningObjectives/tasks/runtimeEnvironment`，Exam 的 `items/totalPoints/type`，Grading 的 `gradingRules/timeout/totalPoints`，PPT 的 `pages/style/targetAudience`。
- 失败时不写 Workflow Report，不创建 AI Task，不发布内容。

## 测试方式

```powershell
python -m pytest tests/test_exam_candidate_preview.py
python -m pytest tests/test_real_llm_demo_dsl.py tests/test_provider_adapter_workflow.py tests/test_phase2_workflow_orchestrator.py
```

测试默认使用 fake client / monkeypatch，不需要真实 key，不发送在线请求。

## 限制说明

- 该模式是演示路径，不是默认生产路径。
- 四次真实请求的成本取决于模型和输入长度。
- LLM 生成内容质量必须由人工审核确认，质量信号只辅助审核，不自动批准。
- 内容质量决策字段只作为人工审核和 Agent 单步推进的建议层；即使 `decisionStatus=READY_FOR_IMPORT_PREVIEW`，任务仍必须先人工审核通过，且 Grading 的最终通过仍需要 evidence / decision note 等后续复核。
- 如果 OpenAI-compatible 模型输出包含额外字段、遗漏平台 DSL 必填骨架、把 DSL 放进常见响应 envelope，或把字符串/对象/数组/数字混用，Provider 会先做确定性的 DSL 形状归一化，再执行本地 Schema 校验；归一化摘要会进入 Provider 审计和审核详情，供人工复核。
- Lab DSL 归一化会收敛 `metadata.difficulty/durationMinutes/tags`、`spec.objectives/targetUsers`、`spec.materials` 字符串或别名对象、`spec.environment.resources` 文本或非整数值，以及 `steps` 中的字符串字段和命令列表。
- Exam DSL 归一化会收敛 `metadata.difficulty/sourceLabId`、`questionType` 同义词、`totalScore` 字符串、`questions` 别名数组和题目分值漂移，并保持题目分值合计等于总分。
- Grading DSL 归一化会收敛 `totalScore/timeoutSeconds/checks` 的常见别名，补齐 runner 计划所需字段，例如 `stdout_contains.command/expected`、`notebook_cell.cellIndex/expected`、`json_field.jsonPath/expectedValue` 和 `pytest.path`；`expected` 内的对象、数字和数组会转成字符串 token，确保 Schema 通过后也能进入 `GradingRunner` 计划与 `grade sandbox-precheck` 预检。
- PPT DSL 归一化会收敛 `audience/durationMinutes/theme/slides` 的常见别名，规范 slide type、bullets、speaker notes 和时长字段，把可审核信息保留在 slide bullets 中。
- 标准答案不得进入候选人预览；候选人导出会做字段移除和答案文本泄漏检测，但仍需要人工审核试题表述质量。
- 真实评分执行仍需后续沙箱能力。
- 真实 PPTX 生成仍需后续 PPT Artifact 工作流。

## 下一步

- 最近一次真实 Demo 已使用 `mimo-v2.5-pro` 和 `OPENAI_BASE_URL=https://api.xiaomimimo.com/v1` 跑通，输出文件为 `examples/output/mimo-real-demo-*.json` 和 `examples/output/phase2-real-llm-report.json`；该 endpoint 不支持 Responses API，已自动降级到 Chat Completions。
- 人工检查四类 DSL 的课程可用性，并在审核详情中复核 usage、responseId、候选人预览摘要和 DSL 归一化摘要。
- Grading DSL 到真实沙箱前预检已进入 `docs/19_REAL_SANDBOX_PRECHECK.md`；可执行 `grade sandbox-precheck` 生成演示评分预检报告。
- 演示包收口已进入 `docs/21_REAL_LLM_DEMO_BUNDLE.md`；可执行 `phase2 demo-bundle build/report` 复放已有真实成果。

建议智能模式：GPT-5.5 超高智能模式。
