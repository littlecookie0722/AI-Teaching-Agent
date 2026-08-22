# 19_REAL_SANDBOX_PRECHECK

状态：已实现第一版。

本文件记录 Grading DSL 到真实沙箱实现前的预检流程。它不是新的安全门禁、禁用壳或执行授权；它只把已有 GradingRunner 计划报告聚合成“是否可以进入真实沙箱实现评审”的结构化 JSON。

## 范围

已实现：

- `grade sandbox-precheck`
- 输入本地 Grading DSL，并先执行 Grading Schema 校验。
- 复用 `sandbox.GradingRunner` 生成 Mock 评分计划。
- 检查 `spec.assessmentPlan` 是否与 `spec.checks` 对齐。
- 检查每个 check 是否具备 `sandboxExecutionRequest`、`containerSandboxPlan`、资源限制和证据采集字段。
- 输出 `REAL_SANDBOX_PRECHECK_ONLY` JSON 报告。
- 写入本地 Operation Audit 和 Artifact 记录，统一标记 `reportType=REAL_SANDBOX_PRECHECK`。

未实现：

- 不启动 Docker、Podman、Kubernetes、VM 或 Notebook kernel。
- 不执行选手代码、评分命令、pytest 或 Notebook cell。
- 不读取选手文件、JSON 文件或日志文件。
- 不把预检通过解释为真实评分执行授权。
- 不自动发布评分结果。

## 输入说明

- `--grading`: 本地 Grading DSL 路径，示例为 `templates/grading/examples/mixed-checks.yaml`。
- `--output`: 可选 JSON 输出路径，建议写入 `examples/output/`。
- 输入 DSL 必须满足 `templates/grading/grading.schema.json`。

## 输出说明

核心字段：

```json
{
  "mode": "REAL_SANDBOX_PRECHECK_ONLY",
  "readiness": {
    "status": "READY_FOR_MANUAL_SANDBOX_REVIEW",
    "readyForRealSandboxImplementation": true,
    "readyForRealSandboxExecution": false,
    "manualReviewRequired": true,
    "blockers": [],
    "warnings": []
  },
  "summary": {
    "checkTotal": 6,
    "plannedOnly": 6,
    "executed": 0
  },
  "safety": {
    "sandboxExecuted": false,
    "contestantCodeExecuted": false,
    "commandExecuted": false,
    "realPublish": false
  }
}
```

`readyForRealSandboxImplementation=true` 表示计划可进入真实沙箱实现评审；`readyForRealSandboxExecution=false` 固定为 false，表示当前命令没有执行真实沙箱，也没有授权执行真实评分。

如果真实 LLM 生成的 Grading DSL 通过了 Schema，但缺少评分 runner 需要的字段，命令仍会返回成功的预检 JSON，并把状态标为 `BLOCKED_BEFORE_REAL_SANDBOX`。例如 `stdout_contains` 缺少 `command` 或 `expected` 时，`readiness.blockers[]` 会给出具体字段路径，供人工审核或后续 DSL 修复流程处理。

## 命令示例

```powershell
python lab_cli.py grade sandbox-precheck --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-real-sandbox-precheck.json
```

对真实 LLM 生成的 Grading DSL 执行预检：

```powershell
python lab_cli.py grade sandbox-precheck --grading examples/output/real-llm-grading.json --output examples/output/real-llm-demo-grading-precheck.json
```

如果真实 LLM 已生成的 Grading DSL 缺少 runner 计划字段，可先执行本地归一化：

```powershell
python lab_cli.py grade normalize --grading examples/output/real-llm-grading.json --exam examples/output/real-llm-exam.json --output examples/output/real-llm-demo-grading-normalized.json
python lab_cli.py grade sandbox-precheck --grading examples/output/real-llm-demo-grading-normalized.json --output examples/output/real-llm-demo-grading-precheck.json
```

## 测试方式

```powershell
python -m pytest tests/test_sandbox_mock_executor.py tests/test_cli.py
```

## 限制说明

- 预检只检查计划，不执行计划。
- `grade normalize` 只做本地确定性 DSL 字段补齐，不重新调用真实 LLM，不自动审核通过，不执行评分。
- 预检通过后，下一步应实现真实 `SandboxExecutor` 的最小容器执行 PoC，而不是继续新增同义禁用壳。
- 真实执行必须继续保留人工审核、隔离工作目录、资源限制、网络关闭、stdout/stderr/exitCode/durationMs 证据采集和审计日志引用。
- 真实评分结果仍不得绕过人工审核或自动发布。

## 下一步

- 基于 `sandbox.execution_contract.build_sandbox_execution_request` 和 `sandbox.container_executor.ContainerSandboxExecutor.plan` 实现最小真实容器执行 PoC。
- 先支持单个 `file_exists` 或 `json_field` 低风险 check，再扩展到 `pytest` 和 `notebook_cell`。
- 将真实执行结果回填到现有 `gradingReport.checks[]` 的 evidence 字段，保持 CLI JSON 契约不变。
