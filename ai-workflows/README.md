# ai-workflows

AI Workflow 契约目录。当前 Phase 2 默认仍为 MockProvider-first 工作流编排；真实 LLM 只允许通过显式 `real-llm-minimal` 或 `real-llm-demo` 模式接入，不启动真实智能体，不创建真实云资源，不执行选手代码。

## 输入说明

- `workflow.manifest.json`: Phase 1 Mock Workflow 契约。
- `phase2-content-generation.contract.json`: Phase 2 内容生成工作流契约，默认 Mock 编排 Lab / Exam / Grading / PPT DSL；显式 `real-llm-minimal` 模式只让 Lab DSL 使用真实 LLM 单请求；显式 `real-llm-demo` 模式让 Lab / Exam / Grading / PPT 四类 DSL 各用一次真实 LLM 请求生成。
- `phase2-exam-conversion.contract.json`: Phase 2 Mock 试题改造工作流契约，读取 Lab DSL 和 Notebook JSON，生成 Exam / Grading DSL 审核包。
- `phase2-grading-generation.contract.json`: Phase 2 Mock 评分脚本生成工作流契约，读取 Exam DSL，生成 Grading DSL 审核包和 `assessmentPlan` 质量信号。
- `phase2-ppt-generation.contract.json`: Phase 2 Mock PPT / 文档生成工作流契约，读取 Markdown，先生成 slide plan JSON，再生成 PPT DSL 审核包。
- `phase2-workflow-registry.contract.json`: Phase 2 Mock Workflow 能力目录，集中声明可查询的 Workflow、契约路径、CLI / Backend 入口和安全标记。
- `ai_workflows/provider_adapter_workflow.py`: Workflow 侧 Provider Adapter helper，统一生成 Lab / Exam / Grading / PPT DSL；默认 Mock，显式 real 模式支持 Lab 最小 PoC 或四类 DSL Demo。
- `ai_workflows/workflow_registry.py`: Workflow Registry 查询 helper，用于 CLI 和 Backend 的只读能力发现。
- `provider-audit-workflow.contract.json`: Workflow 级 Provider 调用审计契约，要求入口层写入本地 `providerCallAuditEvents`。
- 每个 workflow 需要声明：
  - `id`
  - `entrypoint.cli`
  - `entrypoint.backend`
  - `inputs`
  - `outputs`
  - `steps`
  - `runLog`
  - `reviewGate`
  - `safety`

## 输出说明

生成类 Workflow 的输出必须是 DSL 或 Mock 报告：

```text
Material Analysis -> COMPLETED
Lab DSL      -> WAITING_REVIEW
Exam DSL     -> WAITING_REVIEW
Grading DSL  -> WAITING_REVIEW
PPT DSL      -> WAITING_REVIEW
Mock Report  -> COMPLETED
```

Phase 2 `phase2_content_generation` 同时写入本地 AI Task、Provider 审计、Workflow Run、Artifact 清单和 Workflow Report JSON，生成类 DSL 继续保持 `WAITING_REVIEW`。该工作流支持 Lab 生成业务参数，并在报告、Lab Artifact metadata 和审核详情中输出 `labGenerationContext`、`qualitySignals`、`reviewHighlights` 和 `providerSummary`。显式真实 Lab 模式会把 Lab provider 标记为 `openai` / `realLlmCalled=true`，Exam / Grading / PPT 仍为 Mock。显式真实 Demo 模式会把 Lab / Exam / Grading / PPT 四类 provider 都标记为真实调用，并记录 `realLlmRequestCount=4`。

Phase 2 `phase2_exam_conversion` 额外读取 `examples/notebooks/demo-lab.ipynb`，只解析 Notebook JSON，不执行 cell；候选人预览会复用 `ai_workflows/exam_candidate_preview.py` 移除标准答案，并检测答案文本是否意外进入候选人字段。报告会输出 `qualitySignals`，覆盖标准答案隐藏、题目 gradingRef 与评分 check 对齐、Exam / Grading 分值一致性、评分计划可解释性，并同步写入 Exam / Grading Artifact metadata。`qualitySignals.grading.assessmentPlan` 会从 Grading DSL checks 派生评分前计划，包含 `inputSummary`、`executionPlan.requiredLimits`、`mockEvidence.status`、`riskLevel` 和 `sandboxRequiredBeforeRealExecution`，用于和 Phase 3 `reportDetail.checkPlans` 保持字段语义一致。

Phase 2 `phase2_grading_generation` 可独立从 Exam DSL 生成 Grading DSL 审核包。报告会输出 `qualitySignals.coverage.gradingRefCoverage`、`scoreCoverage` 和 `explainability`，并把 `qualitySignals.grading.assessmentPlan` 写入 Grading Artifact metadata，供审核详情页展示；当前不执行真实沙箱、不运行选手代码。

Phase 2 `phase2_ppt_generation` 额外输出 slide plan JSON 作为中间结果，PPT DSL 保持 `WAITING_REVIEW`；当前不生成真实 PPT 文件或 Markdown 课件文件。

Phase 2 `phase2_workflow_registry` 是只读能力目录，输出四条 Workflow 的摘要或单条 Workflow 详情及其 contract，不创建任务、不生成内容、不写运行记录。

任何生成内容在审核通过前不得发布。

## 命令示例

当前不启动真实 Workflow 引擎，只通过 manifest 和既有 CLI / Backend Mock 验证：

```powershell
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1
python lab_cli.py material analyze --input examples/input/demo-source.md
python lab_cli.py workflow list --workflow-id phase1_main_demo
python lab_cli.py workflow get --id workflow_run_demo
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json --target-users "高职学生,教师" --duration-minutes 90 --difficulty intermediate --tech-tags "Python,Notebook" --teaching-style project_based
python lab_cli.py phase2 workflow report --file examples/output/phase2-content-generation-report.json
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-real-llm-workflow-report.json --provider-mode real-llm-minimal --real-lab-output examples/output/phase2-real-llm-lab.json --model <model> --explicit-real-call-opt-in --confirm-single-request --confirm-lab-only --confirm-waiting-review --confirm-no-auto-publish
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-real-llm-demo-report.json --provider-mode real-llm-demo --real-demo-lab-output examples/output/demo-real-lab.json --real-demo-exam-output examples/output/demo-real-exam.json --real-demo-grading-output examples/output/demo-real-grading.json --real-demo-ppt-output examples/output/demo-real-ppt.json --model <model> --explicit-real-call-opt-in --confirm-demo-real-dsl --confirm-waiting-review --confirm-no-auto-publish
python lab_cli.py phase2 exam-convert run --lab templates/lab/examples/basic-lab.yaml --notebook examples/notebooks/demo-lab.ipynb --reviewer teacher_1 --output examples/output/phase2-exam-conversion-report.json
python lab_cli.py phase2 exam-convert report --file examples/output/phase2-exam-conversion-report.json
python lab_cli.py exam candidate-preview --exam templates/exam/examples/notebook-fill-blank.yaml --output examples/output/exam-candidate-preview.json
python lab_cli.py exam candidate-preview --exam examples/output/demo-real-exam.json --output examples/output/demo-real-exam-candidate-preview.json
python lab_cli.py phase2 grading-generate run --exam templates/exam/examples/notebook-fill-blank.yaml --reviewer teacher_1 --output examples/output/phase2-grading-generation-report.json
python lab_cli.py phase2 grading-generate report --file examples/output/phase2-grading-generation-report.json
python lab_cli.py phase2 ppt-generate run --input examples/input/demo-source.md --reviewer teacher_1 --slide-plan-output examples/output/phase2-ppt-slide-plan.json --output examples/output/phase2-ppt-generation-report.json
python lab_cli.py phase2 ppt-generate report --file examples/output/phase2-ppt-generation-report.json
python lab_cli.py workflow registry list
python lab_cli.py workflow registry get --workflow-id phase2_content_generation
python lab_cli.py provider audit --operation generateJson
python -m pytest tests/test_workflow_manifest.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_phase2_workflow_orchestrator.py
python -m pytest tests/test_real_llm_demo_dsl.py
python -m pytest tests/test_phase2_exam_conversion_workflow.py
python -m pytest tests/test_phase2_ppt_generation_workflow.py
python -m pytest tests/test_phase2_workflow_registry.py
```

## 已声明 Workflow

```text
phase1_main_demo
lab_generation_mock
exam_generation_mock
ppt_generation_mock
phase2_content_generation
phase2_exam_conversion
phase2_grading_generation
phase2_ppt_generation
phase2_workflow_registry
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- 默认 `realLlmCalled=false`；只有 `phase2 workflow run --provider-mode real-llm-minimal` 会让 Lab DSL 发起一次真实 LLM 请求，或 `--provider-mode real-llm-demo` 会让 Lab / Exam / Grading / PPT 四类 DSL 各发起一次真实 LLM 请求。
- `realCloudResourceCreated=false`，不创建真实云资源。
- `unknownShellExecuted=false`，素材分析只做静态风险标记。
- `contestantCodeExecuted=false`，不执行选手代码。
- `autoPublishAllowed=false`，不允许自动发布。
- 生成类输出默认 `WAITING_REVIEW`。
- Workflow Run 只记录本地步骤日志和 traceId，不启动真实智能体编排。
- Lab / Exam / Grading / PPT 生成统一通过 Provider Adapter；真实模式支持 Lab 最小 PoC 和四类 DSL Demo，两者都必须显式 opt-in。
- Lab 生成业务参数只影响生成上下文与审核质量信号，不授权自动发布；默认仍需要人工审核。
- Workflow Provider 调用审计只写本地 Mock Store，可按 traceId 查询；真实 Lab 模式会记录 `realLlmCalled=true`、`secretsRead=true`、`networkAccess=true`。
- Phase 2 当前已完成 Mock 工作流、真实 Lab 显式回接和真实 LLM Demo 四类 DSL 生成；仍不做真实 Agent planning、不生成真实 PPT 文件、不执行真实沙箱。
- Phase 2 试题改造只静态解析 Notebook JSON，不执行 Notebook cell，不运行选手代码；标准答案只留在 DSL，不出现在候选人预览。
- `exam candidate-preview` 可独立把 Mock 或真实 Demo 生成的 Exam DSL 导出为候选人 JSON；如果答案文本泄漏到候选人可见字段，命令会失败并返回 `CANDIDATE_PREVIEW_ANSWER_LEAK_DETECTED`。
- Phase 2 试题改造质量信号只辅助人工审核，不自动发布、不自动驳回；真实评分执行仍需后续沙箱。
- Phase 2 评分脚本生成只读取本地 Exam DSL，输出 Grading DSL 审核包和评分计划质量信号；不执行评分、不运行沙箱。
- Phase 2 PPT 生成只支持本地 Markdown 输入，必须先输出 slide plan；真实 PPT 文件生成和 PDF / Word 直接转 PPT 暂不启用。
- Phase 2 Workflow Registry 只做本地 contract 发现，不执行 Workflow、不创建 AI Task、不写 Artifact、不绕过审核。
- 标准答案不得展示给选手端。
