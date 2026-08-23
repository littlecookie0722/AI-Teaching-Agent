# quality

核心回归测试矩阵目录。当前用于本地和 CI 前置验证：按固定 profile 运行项目内预定义 pytest 子集，并输出 JSON 证据报告。

## DSL 离线质量基线

`quality dsl-eval` 读取 `evals/dsl_quality/v1/manifest.json`，把 20 个已脱敏
case 渲染为实际 Lab / Exam / Grading / PPT DSL 和候选人预览，再调用项目正式
Draft 2020-12 校验器与跨产物质量规则。语料覆盖 5 个教学领域、中文/英文和
normal/boundary 两类输入；每个 case 都会报告产物 id、逐项指标和失败原因。

检查项包括：

- 四类 DSL Schema 与 `WAITING_REVIEW` 状态。
- Lab → Exam → Grading 的实体引用、题目到评分项/执行计划的引用覆盖。
- Exam、题目、Grading check 和 assessment plan 的总分一致性。
- 候选人预览中的 `answer` / `gradingRef` 字段和值泄漏。
- Lab 学习目标/步骤完整性与 PPT 最小页数。

```powershell
ai-teaching-agent quality dsl-eval
ai-teaching-agent quality dsl-eval --output examples/output/dsl-quality-eval.json
python -m pytest tests/test_dsl_quality_eval.py -q
```

报告不含运行时间戳，同一 manifest 会生成字节稳定的 JSON 内容。该入口只读取
本地脱敏 fixture，不联网、不调用真实 LLM、不执行选手代码，也不替代后续真实模型
失败样本回归；新增真实失败样本时应先脱敏，再作为新 corpus 版本或明确 case 加入。

## PPT 产物质量预检

`ppt artifact build` 和真实 Demo Bundle 会调用 `quality.ppt_preflight`，对
已通过 Schema 校验的 PPT DSL 做本地、确定性的审核前检查。报告包含逐页标题、
正文密度、长文本、估算溢出，以及显式或推断版式的实际 0/3/4 条 bullet 容量；
`renderedBulletLimit` / `renderedBulletTotal` 与构建器一致，并写入构建 JSON、
manifest、PPTX Artifact metadata 和页级 `qaSignals`。该检查是
`advisoryOnly=true`：不会修改 DSL、改变 `WAITING_REVIEW`、自动批准或发布。

```powershell
python -m pytest tests/test_ppt_preflight.py -q
python lab_cli.py quality regression-matrix --profile quick --dry-run
```

## 输入说明

- `profile`: 预定义测试矩阵，当前支持 `quick`、`core`、`backend-core`、`real-llm-offline`、`mcp`。`quick` / `core` 已包含 `lab_generation_v1`、`exam_grading_generation_v1`、`offline_demo`、`ppt_quality_preflight`、`grading_stable_v1` 和 `frontend_core_manifest`：`offline_demo` 保护无 API Key 的四类 DSL、候选人预览和审核状态闭环；`ppt_quality_preflight` 保护 PPT 版式容量、可见文本、预检与真实 Artifact 完整性；其余核心命令分别保护 Lab 生成、Exam/Grading 生成、Grading 稳定闭环和核心前端页面契约。真实 LLM 生成路径用离线假适配验证显式 opt-in、模型/base URL/API surface 传参、Provider 审计和人工审核边界；`grading_stable_v1` 默认不联网、不读取密钥、不调用真实平台。
- `output`: 可选 JSON 报告路径，建议写入 `examples/output/` 或临时目录。
- `timeoutSeconds`: 单条 pytest 命令超时时间。
- `dryRun`: 只列出将执行的固定命令，不运行测试。

## 输出说明

报告统一为 JSON：

```json
{
  "mode": "LOCAL_REGRESSION_TEST_MATRIX",
  "profile": "quick",
  "success": true,
  "commands": [
    {
      "id": "dsl_contract",
      "status": "PASSED",
      "exitCode": 0
    }
  ],
  "safety": {
    "predefinedProfilesOnly": true,
    "arbitraryCommandAllowed": false,
    "shellExecutionAllowed": false
  }
}
```

## 命令示例

```powershell
python lab_cli.py quality regression-matrix --profile quick --output examples/output/regression-matrix-quick.json
python lab_cli.py quality regression-matrix --profile core --stop-on-failure --output examples/output/regression-matrix-core.json
python lab_cli.py quality regression-matrix --profile backend-core --dry-run
python lab_cli.py quality regression-profiles
```

## 测试方式

```powershell
python -m pytest tests/test_quality_regression_matrix.py
python -m pytest tests/test_cli.py::test_quality_regression_matrix_cli_writes_json_report
```

## CI 入口

`.github/workflows/core-regression-matrix.yml` 会在 PR 或手动触发时运行同一个固定矩阵：

```bash
python lab_cli.py quality regression-matrix --profile core --stop-on-failure --output examples/output/regression-matrix-core.json
```

Workflow 会上传 `regression-matrix-core` JSON 报告；如果 CLI 返回 `success=false`，CI 会显式失败。该 workflow 仍只调用已有 CLI 矩阵，不引入新的任意命令执行入口。

## 本地实跑证据

当前本地 `core` profile 已完成过一次历史实跑记录：

- 证据文档：`docs/26_CORE_REGRESSION_RUN_EVIDENCE.md`
- JSON 报告：`examples/output/regression-matrix-core.json`
- 结果摘要：`commandTotal=9`、`executedTotal=9`、`passedTotal=9`、`failedTotal=0`
- `grading_core` 覆盖受控 Docker evidence、evidence merge、评分 job/record 和 SQLite staging。
- 说明：加入 `exam_grading_generation_v1` 后，新的 quick/core 矩阵命令数会增加；需要重新生成证据时继续使用同一个 `quality regression-matrix` 入口，不新增同义 runner。

当前新增第三主功能后的 `quick` profile 已完成一次本地实跑；当前 quick profile 还会运行 `offline_demo` 和 `frontend_core_manifest`，分别保护无 key Demo 与 Review Center、Grading Report、AI Task 和 Platform Entities 等核心页契约：

- JSON 报告：`examples/output/regression-matrix-quick.json`
- 结果摘要：`commandTotal=10`、`executedTotal=10`、`passedTotal=10`、`failedTotal=0`
- `offline_demo` 覆盖 `python lab_cli.py demo offline` 的四类 DSL Schema 校验、候选人安全预览、`WAITING_REVIEW`、发布阻断和本地安全标记。
- `exam_grading_generation_v1` 覆盖 Lab DSL 输入、真实 LLM 离线 fake 双请求、任务专属 Exam/Grading 输出、候选人安全预览、`WAITING_REVIEW` 和审核后本地 import-preview。
- `grading_stable_v1` 覆盖单命令生成受控 evidence、创建 `GradingRecord`、输出 `reviewDetail` 与 `gradingResultPreview`，仍不自动复核、不发布。
- `frontend_core_manifest` 覆盖核心静态页和渐进增强数据加载器，不启动真实平台、不执行发布。

后续如果继续补回归证据，只记录 GitHub Actions / 外部 CI 的实际 artifact，或在新增核心功能后向现有 profile 增补必要测试文件；不要新增同义 regression runner、CI shell 或任意命令执行入口。

## 限制说明

- 不接收任意命令字符串。
- 不使用 shell 执行命令。
- 默认排除 `integration` 和 `real_llm_online` pytest marker。
- 不读取密钥、不调用真实 LLM、不连接生产数据库。
- 不创建或删除真实云资源。
- 不自动发布。
