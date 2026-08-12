# quality

核心回归测试矩阵目录。当前用于本地和 CI 前置验证：按固定 profile 运行项目内预定义 pytest 子集，并输出 JSON 证据报告。

## 输入说明

- `profile`: 预定义测试矩阵，当前支持 `quick`、`core`、`backend-core`、`real-llm-offline`、`mcp`。`quick` / `core` 已包含 `lab_generation_v1`、`exam_grading_generation_v1`、`grading_stable_v1` 和 `frontend_core_manifest`：前三项分别保护 Lab 生成、Exam/Grading 生成和 Grading 稳定闭环，`frontend_core_manifest` 保护核心前端页面契约、数据加载器和本地闭环深链。真实 LLM 生成路径用离线假适配验证显式 opt-in、模型/base URL/API surface 传参、Provider 审计和人工审核边界；`grading_stable_v1` 默认不联网、不读取密钥、不调用真实平台。
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

当前新增第三主功能后的 `quick` profile 已完成一次本地实跑；当前 quick profile 还会运行 `frontend_core_manifest`，用于保护 Review Center、Grading Report、AI Task 和 Platform Entities 等核心页契约：

- JSON 报告：`examples/output/regression-matrix-quick.json`
- 结果摘要：`commandTotal=9`、`executedTotal=9`、`passedTotal=9`、`failedTotal=0`
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
