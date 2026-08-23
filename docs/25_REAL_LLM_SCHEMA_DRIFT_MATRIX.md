# 真实 LLM Schema 漂移样本矩阵

> 状态：P0 真实输出稳定性回归索引  
> 测试入口：`tests/test_real_llm_demo_dsl.py::test_real_llm_demo_schema_drift_matrix_regression`

## 目标

真实模型输出 Lab / Exam / Grading / PPT DSL 时，常见失败不是业务逻辑错误，而是字段形状漂移：

- Schema 要求 object，模型输出 string / array。
- Schema 要求 string，模型输出 object / array / number。
- 字段名使用同义词，如 `cpuCores`、`memory`、`items`、`totalPoints`。
- 评分计划字段缺失或类型不稳定。

本矩阵用于把真实失败样本固定成离线回归测试。后续遇到新的 `REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED`，优先补这个矩阵和确定性归一化，不要回到新增门禁或运营展示页。

## 当前覆盖

| 样本 | 原始失败形态 | 归一化结果 |
| --- | --- | --- |
| `lab_materials_string_array` | `spec.materials[]` 是字符串 | 转为 `{type,path}` object |
| `lab_environment_resources_string` | `spec.environment.resources` 是说明文本 | 解析为 `{cpu,memoryGb}` |
| `lab_environment_resources_aliases` | resources 使用 `cpuCores/memory` 等别名 | 转为标准 `cpu/memoryGb` |
| `lab_grading_ref_shape_drift` | `spec.grading` 是字符串或带 `id/gradingRef` 的 object | 转为 `{ref}` object |
| `lab_materials_and_steps_object_map` | `spec.materials` / `spec.steps` 是以资源名或步骤 id 为 key 的 object map | 转为 materials / steps 数组，保留步骤 key 作为 step id |
| `lab_step_alias_fields` | `steps[]` 使用 `stepId/name/description/shellCommands/expected` 等常见别名 | 提升到 `id/title/instruction/commands/expectedResult`，避免步骤语义被默认文案覆盖 |
| `exam_answer_and_grading_ref_object_fields` | `answer/gradingRef` 是 object / array / number | 转为字符串，保留审核语义 |
| `exam_missing_questions_custom_total_score` | 模型给出 `totalScore` 但省略 `spec.questions` | 回填可审核默认题，并让题目分值与 `totalScore` 对齐 |
| `exam_top_level_questions` | 模型把 `questions` 放在 DSL 顶层而不是 `spec.questions` | 提升到 `spec.questions`，保留真实题目内容 |
| `exam_questions_object_map` | `spec.questions` 是以题号为 key 的 object map | 转为 questions 数组，保留 key 作为题目 id |
| `exam_question_alias_fields` | `questions[]` 使用 `question/prompt/name/correctAnswer/checkId` 等常见别名 | 提升到 `stem/title/answer/gradingRef`，避免题干被默认文案覆盖 |
| `grading_required_limits_non_string_values` | `requiredLimits.cpu/timeout` 非字符串 | 转为 schema 要求的字符串 |
| `grading_metadata_object_fields` | `metadata.id/title/sourceExamId` 是 object / array | 转为 schema 要求的字符串 |
| `grading_check_string_fields` | `checks[].id/path/command/jsonPath` 是 object / array / number | 转为 schema 要求的字符串 |
| `grading_check_alias_fields` | `checks[]` 使用 `checkId/checkType/cmd/filePath/fieldPath/expectedOutput` 等常见别名 | 提升到 `id/type/command/path/jsonPath/expected`，避免评分规则语义被默认值覆盖 |
| `grading_assessment_plan_input_summary` | `assessmentPlan[].inputSummary` 是 object 或空字符串 | 转为字符串，空值回填可审核计划摘要 |
| `grading_assessment_plan_alias_fields` | `assessmentPlan[]` 使用 `check_id/summary/execution/limits/evidence` 等常见别名，且顺序与 `checks[]` 不一致 | 提升到 `checkId/inputSummary/executionPlan/requiredLimits/mockEvidence`，按 check id 对齐评分计划并固定只读 evidence |
| `grading_assessment_plan_mock_evidence` | `assessmentPlan[].mockEvidence` 是字符串、错误状态或带真实证据字段 | 固定为 `{status: MOCK_EVIDENCE_NOT_COLLECTED}`，避免模型伪造执行证据 |
| `grading_checks_and_assessment_plan_object_map` | `spec.checks` / `spec.assessmentPlan` 是以 check id 为 key 的 object map | 转为 checks / assessmentPlan 数组，保留 key 作为 check id 并继续对齐评分计划 |
| `ppt_metadata_and_slide_named_fields` | `metadata.title/audience`、`slides[].title/subtitle` 是带同名字段的 object | 优先提取同名字段为 schema 要求的字符串 |
| `ppt_slide_alias_fields` | `slides[]` 使用 `slideId/layout/heading/points/items` 等常见别名，且旧 `layout` 值可能不在新版枚举中 | 提升到 `id/type/title/bullets`；合法 `layout` 保留，非枚举 alias 在推导 `type` 后移除，避免课件正文要点被裁剪或 Schema 回归 |
| `ppt_slides_object_map` | `spec.slides` 是以页面 id 为 key 的 object map | 转为 slides 数组，保留 key 作为 slide id |

## Schema 失败诊断

当真实 LLM 输出仍未通过 Schema 校验时，`ProviderError.details.schemaFailureDiagnostic` 和 CLI 返回的 `providerErrorContext.schemaFailureDiagnostic` 会给出可读诊断：

- `errors`：字段路径、失败原因、漂移类别和敏感字段值已脱敏标记。
- `reasonSummary` / `topLevelFieldSummary`：按原因和顶层字段聚合，方便判断是 Prompt 问题还是归一化缺口。
- `suspectedDriftTypes` / `recommendedActions`：给出下一步优先补 Prompt、归一化、枚举映射或保留失败样本。
- `documentShape`：只包含 DSL 的 key 和列表数量，不包含题干、答案、gradingRef、token 或 API Key 原值。

诊断只用于定位问题，不替代 Schema 校验、人工审核或一次性 repair。遇到新增真实失败样本时，仍按“先收录样本、再补确定性归一化、最后补测试”的顺序处理。

## 内容质量归一化样本

- `test_real_llm_demo_exam_moves_answer_like_grading_refs_to_answer`：2026-07-06 DeepSeek v4 flash 曾把 Exam `questions[].gradingRef` 写成中文说明、代码片段或带引号答案，导致四类 DSL 虽通过 Schema，但报告级内容质量出现 `grading_ref_uncovered`。归一化会把明显不像稳定 check id 的 `gradingRef` 改为题目 id / `check_qN`，并在 `answer` 缺失时把原文本迁移到 `answer`，使候选端继续脱敏答案，同时让 Grading `checks` / `assessmentPlan` 能覆盖题目引用。
- `test_real_llm_demo_exam_normalizes_generic_manual_grading_refs`：2026-07-06 DeepSeek v4 flash 真实样本曾把 Exam 四道题的 `gradingRef` 全部写成泛化值 `manual`，而 Grading check id 已按题目 id 生成，导致 `grading_ref_uncovered`。归一化把 `manual` / `review` / `human_review` 等泛化教师侧引用视为不稳定值，改为对应题目 id，不把 `manual` 当作标准答案。
- `test_real_llm_demo_grading_aligns_check_ids_to_exam_grading_refs`：真实模型可能把 Grading `checks[].id` 生成为题目 id，而 Exam `questions[].gradingRef` 是短教师侧评分引用；当 gradingRef 像稳定 ID 时，归一化会把 check id 和 assessmentPlan checkId 对齐到 gradingRef，避免 Schema 已通过但导入预览被 `grading_ref_uncovered` 阻塞。
- `test_real_llm_demo_grading_expands_single_check_to_cover_exam_refs`：真实模型可能只生成一个汇总 check，而 Exam 有多道题和多个 gradingRef；当 Grading checks 少于 Exam questions 且未覆盖 gradingRef 时，归一化会按题生成最小可审核 checks，并重新对齐 assessmentPlan。

## 新增样本规则

1. 只收录真实模型实际出现过，或与实际失败等价的字段漂移。
2. 样本必须先通过确定性归一化，再通过 DSL Schema 校验。
3. 输出仍必须是 `WAITING_REVIEW`，不得自动 approve / publish。
4. 不为了未知未来情况预先发明大量规则。
5. 如果归一化会改变业务语义，必须保留为 Schema 失败并让人工重新生成或修订。

## 验证命令

```powershell
python -m pytest tests/test_real_llm_demo_dsl.py::test_real_llm_demo_schema_drift_matrix_regression -q
python -m pytest tests/test_real_llm_demo_dsl.py -q
```

## 可选在线 Smoke

默认测试只使用 fake client 和离线漂移样本，不会请求真实模型。需要验证 OpenAI-compatible 真实模型链路时，必须显式开启在线 smoke：

```powershell
$env:LAB_REAL_LLM_ONLINE_SMOKE="1"
$env:OPENAI_API_KEY="<your-api-key>"
$env:LAB_REAL_LLM_ONLINE_SMOKE_MODEL="<model-name>"
$env:LAB_REAL_LLM_ONLINE_SMOKE_BASE_URL="<openai-compatible-base-url>"
python -m pytest tests/test_real_llm_demo_dsl.py::test_real_llm_demo_online_smoke_lab_schema_when_enabled -q -m real_llm_online
```

说明：

- 在线 smoke 只生成一次 Lab DSL，用于验证 SDK、模型配置、base URL、响应解析、Schema 校验和 `WAITING_REVIEW` 审核边界。
- 该测试会消耗真实模型额度，普通本地回归和 CI 不应开启 `LAB_REAL_LLM_ONLINE_SMOKE=1`。
- 不得把真实 API Key 写入 `.env.example`、README、docs、测试文件或日志。
- 四类 DSL 的完整真实生成仍使用 `phase2 workflow run --provider-mode real-llm` 或 `phase2 real-dsl-demo one-click` 手动链路；在线 smoke 不替代完整演示闭环。

## 2026-07-06 DeepSeek v4 flash 在线稳定性样本

本次使用环境变量中的 OpenAI-compatible API Key，并显式指定：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/p0-deepseek-v4-flash-workflow-report.json --provider-mode real-llm --real-llm-lab-output examples/output/p0-deepseek-v4-flash-lab.json --real-llm-exam-output examples/output/p0-deepseek-v4-flash-exam.json --real-llm-grading-output examples/output/p0-deepseek-v4-flash-grading.json --real-llm-ppt-output examples/output/p0-deepseek-v4-flash-ppt.json --model deepseek-v4-flash --base-url https://api.deepseek.com --api-surface chat.completions --repair-on-schema-failure --timeout-seconds 120 --max-output-tokens 4096 --explicit-real-call-opt-in --confirm-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

结果：

| Kind | Output | Schema | Status | Issues | Notes |
| --- | --- | --- | --- | ---: | --- |
| Lab | `examples/output/p0-deepseek-v4-flash-lab.json` | pass | `WAITING_REVIEW` | 0 | 2 objectives, 4 steps, material linked |
| Exam | `examples/output/p0-deepseek-v4-flash-exam.json` | pass | `WAITING_REVIEW` | 0 | 3 questions, total score 100 |
| Grading | `examples/output/p0-deepseek-v4-flash-grading.json` | pass | `WAITING_REVIEW` | 0 | 3 checks, assessment plan aligned, score 100 |
| PPT | `examples/output/p0-deepseek-v4-flash-ppt.json` | pass | `WAITING_REVIEW` | 0 | 7 slides, 5 content slides |

补充校验：

```powershell
python lab_cli.py dsl validate --kind lab --file examples/output/p0-deepseek-v4-flash-lab.json
python lab_cli.py dsl validate --kind exam --file examples/output/p0-deepseek-v4-flash-exam.json
python lab_cli.py dsl validate --kind grading --file examples/output/p0-deepseek-v4-flash-grading.json
python lab_cli.py dsl validate --kind ppt --file examples/output/p0-deepseek-v4-flash-ppt.json
```

四条独立校验均返回 `success=true`。本轮没有新增 `REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED`，因此未新增归一化规则；仅把该模型作为四类 DSL 在线成功样本记录。安全边界保持：`realLlmCalled=true`、`realLlmRequestCount=4`、`reviewBypassed=false`、`autoPublishAllowed=false`、`realPublish=false`、`realCloudResourceChanged=false`、`sandboxExecuted=false`、`contestantCodeExecuted=false`。密钥仅来自环境变量，未写入文档或输出摘要。

## 2026-07-06 DeepSeek v4 flash 多输入连续通过样本

为验证 P0 真实 LLM 输出稳定性，继续使用同一模型对 3 份不同输入素材分别生成 Lab / Exam / Grading / PPT 四类 DSL：

| Round | Input | Workflow report | DSL validation |
| --- | --- | --- | --- |
| Data cleaning | `examples/input/p0-source-python-data-cleaning.md` | `examples/output/p0-deepseek-v4-flash-data-cleaning-workflow-report.json` | 4/4 pass |
| Log analysis | `examples/input/p0-source-linux-log-analysis.md` | `examples/output/p0-deepseek-v4-flash-log-analysis-workflow-report.json` | 4/4 pass |
| API testing | `examples/input/p0-source-web-api-testing.md` | `examples/output/p0-deepseek-v4-flash-api-testing-workflow-report.json` | 4/4 pass |

汇总 evidence：

- `examples/output/p0-deepseek-v4-flash-multi-round-summary.json`
- `examples/output/p0-deepseek-v4-flash-multi-round-dsl-validation.json`

结果摘要：

```text
roundTotal=3
realLlmRequestTotal=12
dslValidationTotal=12
dslValidationPassed=12
dslValidationFailed=0
schemaFailureSampleFound=false
normalizationChanged=false
```

三轮均保持 `READY_FOR_MANUAL_REVIEW`，四类 DSL 均保持 `WAITING_REVIEW`。本轮没有新增真实 Schema 失败样本，因此不新增归一化规则、不新增门禁、不扩展运营内容。

连续多输入通过后，已做一层只读产品化验证：

- `GET /api/workflow/report?file=examples/output/p0-deepseek-v4-flash-data-cleaning-workflow-report.json` 可读取真实 workflow report。
- `review-center.html?agentReport=examples%2Foutput%2Fp0-deepseek-v4-flash-data-cleaning-workflow-report.json` 可作为 Review Center 的只读报告入口。
- `GET /api/review-task-summary?limit=8&detailMode=light` 仍偏向固定 demo artifact 路径，部分动态任务可用；自定义真实输出批次的 Lab / Exam / Grading / PPT 需要下一步做真实产物路径映射和前端 2.0 产品化接入。

因此 P0 真实 LLM 输出稳定性当前可收口；后续如无新增真实失败样本，默认转入 Review Center / 前端 2.0 核心页产品化，不再追加门禁、运营内容或真实平台后端对接。

## 2026-07-06 DeepSeek v4 flash gradingRef 内容质量漂移修复样本

本轮按 P0 要求使用环境变量中的 DeepSeek v4 flash 跑一轮 Lab / Exam / Grading / PPT：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/p0-deepseek-v4-flash-current-workflow-report.json --provider-mode real-llm --real-llm-lab-output examples/output/p0-deepseek-v4-flash-current-lab.json --real-llm-exam-output examples/output/p0-deepseek-v4-flash-current-exam.json --real-llm-grading-output examples/output/p0-deepseek-v4-flash-current-grading.json --real-llm-ppt-output examples/output/p0-deepseek-v4-flash-current-ppt.json --model deepseek-v4-flash --base-url https://api.deepseek.com --api-surface chat.completions --repair-on-schema-failure --timeout-seconds 120 --max-output-tokens 4096 --explicit-real-call-opt-in --confirm-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

结果：四类 DSL 均 `schemaValidated=true` 且保持 `WAITING_REVIEW`，但内容质量摘要出现：

```text
contentQualitySummary.status=NEEDS_REVISION_BEFORE_IMPORT_PREVIEW
blockingIssueTotal=1
blocker.id=grading_ref_uncovered
grading.coverage.gradingRefsCovered=false
```

真实失败样本：Exam 中部分 `gradingRef` 被模型写成答案/说明文本，Grading 中的 check id 无法覆盖这些引用。已按样本补确定性归一化：

```text
set.spec.questions[N].answer.fromUnstableGradingRef
set.spec.questions[N].gradingRef.fromUnstableValue
```

复跑命令：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/p0-deepseek-v4-flash-current-normalized-workflow-report.json --provider-mode real-llm --real-llm-lab-output examples/output/p0-deepseek-v4-flash-current-normalized-lab.json --real-llm-exam-output examples/output/p0-deepseek-v4-flash-current-normalized-exam.json --real-llm-grading-output examples/output/p0-deepseek-v4-flash-current-normalized-grading.json --real-llm-ppt-output examples/output/p0-deepseek-v4-flash-current-normalized-ppt.json --model deepseek-v4-flash --base-url https://api.deepseek.com --api-surface chat.completions --repair-on-schema-failure --timeout-seconds 120 --max-output-tokens 4096 --explicit-real-call-opt-in --confirm-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

修复后结果：

```text
schemaChecks.lab/exam/grading/ppt.schemaValidated=true
contentQualitySummary.status=READY_FOR_MANUAL_REVIEW
contentQualitySummary.blockingIssueTotal=0
contentQualitySummary.readyForImportPreviewKinds=lab,exam,grading
grading.coverage.gradingRefsCovered=true
grading.coverage.missingGradingRefs=[]
safety.reviewBypassed=false
safety.autoPublishAllowed=false
safety.realPublish=false
```

本次只补真实失败样本对应的归一化和回归测试，未新增门禁、运营内容或真实平台后端对接要求。

## 2026-07-06 DeepSeek v4 flash P0 stability manual gradingRef 复核

按 P0 要求再次使用环境变量中的 DeepSeek v4 flash 跑 Lab / Exam / Grading / PPT。首次输出成功落盘且四类 DSL 均通过 Schema，但内容质量摘要出现真实失败样本：

```text
workflowReport=examples/output/p0-deepseek-v4-flash-p0-stability-workflow-report.json
schemaChecks.lab/exam/grading/ppt.schemaValidated=true
contentQualitySummary.blockingIssueTotal=1
blocker.id=grading_ref_uncovered
grading.coverage.missingGradingRefs=manual
```

失败原因：Exam 四道题的 `gradingRef` 都是泛化值 `manual`，Grading checks / assessmentPlan 则按题目 id 生成，二者无法覆盖。已补确定性归一化样本：

```text
test_real_llm_demo_exam_normalizes_generic_manual_grading_refs
UNSTABLE_GENERIC_GRADING_REFS=manual, manual_review, review, teacher_review, human_review
```

复跑证据：

```text
workflowReport=examples/output/p0-deepseek-v4-flash-p0-stability-fixed-workflow-report.json
summary=examples/output/p0-deepseek-v4-flash-p0-stability-fixed-summary.json
schemaChecks.lab/exam/grading/ppt.schemaValidated=true
generatedDsl.lab/exam/grading/ppt.status=WAITING_REVIEW
schemaRepairAttempted.lab/exam/grading/ppt=false
contentQualitySummary.blockingIssueTotal=0
grading.coverage.gradingRefsCovered=true
grading.coverage.missingGradingRefs=[]
safety.reviewBypassed=false
safety.autoPublishAllowed=false
safety.realPublish=false
```

本次只按真实失败样本补归一化和诊断记录，未新增门禁、运营内容或真实平台后端对接要求。

## 2026-07-06 DeepSeek v4 flash live 稳定性复核

按 P0 要求再次使用环境变量中的 DeepSeek v4 flash 跑一轮 Lab / Exam / Grading / PPT：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/p0-deepseek-v4-flash-live-workflow-report.json --provider-mode real-llm --real-llm-lab-output examples/output/p0-deepseek-v4-flash-live-lab.json --real-llm-exam-output examples/output/p0-deepseek-v4-flash-live-exam.json --real-llm-grading-output examples/output/p0-deepseek-v4-flash-live-grading.json --real-llm-ppt-output examples/output/p0-deepseek-v4-flash-live-ppt.json --model deepseek-v4-flash --base-url https://api.deepseek.com --api-surface chat.completions --repair-on-schema-failure --timeout-seconds 120 --max-output-tokens 4096 --explicit-real-call-opt-in --confirm-real-dsl --confirm-waiting-review --confirm-no-auto-publish
```

结果证据：

- `examples/output/p0-deepseek-v4-flash-live-workflow-report.json`
- `examples/output/p0-deepseek-v4-flash-live-summary.json`
- `examples/output/p0-deepseek-v4-flash-live-lab.json`
- `examples/output/p0-deepseek-v4-flash-live-exam.json`
- `examples/output/p0-deepseek-v4-flash-live-grading.json`
- `examples/output/p0-deepseek-v4-flash-live-ppt.json`

结果摘要：

```text
realLlmRequestCount=4
realLlmGeneratedKinds=lab,exam,grading,ppt
schemaChecks.lab/exam/grading/ppt.schemaValidated=true
generatedDsl.lab/exam/grading/ppt.status=WAITING_REVIEW
schemaRepairAttempted=false
schemaRepairApplied=false
contentQualitySummary.blockingIssueTotal=0
safety.reviewBypassed=false
safety.autoPublishAllowed=false
safety.realPublish=false
```

四个落盘 DSL 已分别通过 `python lab_cli.py dsl validate --kind ... --file ...` 文件级校验；归一化矩阵和 CLI 失败诊断回归通过。本轮没有新增真实 Schema 失败样本，因此不修改归一化代码、不新增门禁、不扩展运营内容。

## 2026-07-12 DeepSeek v4 flash 三素材质量回归

使用环境变量中的 OpenAI-compatible 配置，对 Linux 日志分析、Python 数据清洗和 Web API 测试三份 Markdown 素材运行正式 `phase2 workflow run --provider-mode real-llm`。密钥仅由环境变量读取，运行产物保存在本机临时回归目录，未写入 Git。

最终用于验收的三轮结果如下：

| 素材 | Lab objectives / steps | Exam | Grading | PPT | 文件级 Schema 校验 |
| --- | --- | --- | --- | --- | --- |
| Linux 日志分析 | 4 / 5 | 5 题，100 分对齐 | gradingRef 全覆盖，100 分对齐 | 5 页 | 4/4 pass |
| Python 数据清洗 | 4 / 4 | 4 题，100 分对齐 | gradingRef 全覆盖，100 分对齐 | 7 页 | 4/4 pass |
| Web API 测试 | 3 / 4 | 3 题，100 分对齐 | gradingRef 全覆盖，100 分对齐 | 7 页 | 4/4 pass |

最终 12 份 DSL 都满足 `schemaValidated=true` 与 `status=WAITING_REVIEW`；三份 Candidate Preview 共导出 12 道题，均满足 `answersRemoved=true`、`answerVisibleToCandidate=false`，且不含 `answer` 或 `gradingRef` 字段。所有运行均保持 `reviewBypassed=false`、`autoPublishAllowed=false`、`realPublish=false`、`realCloudResourceChanged=false`。

本轮捕获到一个非 Schema 内容质量样本：Web API 测试首次生成的 Lab 只有 1 个 objective，触发 `lab_objective_depth` 警告。根因是 `prompts/workflows/lab_generation.md` 仅要求至少一个 objective，而质量标准要求至少两个。已将 Prompt 最小化收紧为“至少 2 个不同学习目标”，并补 `tests/test_prompt_manifest.py` 断言；复跑同一素材后得到 3 个 objectives、零质量问题。该修复不新增 Schema 归一化规则、自动审核、发布能力或平台对接。
