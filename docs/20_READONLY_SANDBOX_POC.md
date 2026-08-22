# 20_READONLY_SANDBOX_POC

状态：已实现第一版。

本文件记录最小真实沙箱 PoC：只读文件型评分。它不是完整容器执行器，不运行命令、不运行 pytest、不启动 Notebook kernel、不执行 Notebook cell、不执行选手代码。

## 范围

已实现：

- `grade sandbox-run`
- `READONLY_REAL_SANDBOX_POC` 报告。
- 支持 `file_exists`、`json_field`、`notebook_cell` 静态 `.ipynb` JSON 解析和 `log_keyword` UTF-8 文本静态扫描。
- 只读取 `--submission` 指定目录内的相对路径文件。
- 对 `stdout_contains`、`pytest` 返回 `DEFERRED`。
- 输出 evidence、score、executionSummary、safety 和本地审计记录。

未实现：

- 不启动 Docker、Podman、Kubernetes、VM 或 Notebook kernel。
- 不执行命令、pytest、Notebook cell 或选手代码。
- 不打开网络。
- 不写入提交目录。
- 不自动发布评分结果。

## 输入说明

- `--grading`: 本地 Grading DSL，示例 `templates/grading/examples/readonly-sandbox.yaml`。
- `--submission`: 本地提交目录，示例 `examples/submissions/readonly-demo`。
- `--output`: 可选 JSON 报告输出路径。

## 输出说明

关键字段：

```json
{
  "mode": "READONLY_REAL_SANDBOX_POC",
  "executionSummary": {
    "executed": 4,
    "deferred": 1
  },
  "score": {
    "executableScore": 120,
    "earnedScore": 120,
    "deferredScore": 30
  },
  "safety": {
    "sandboxExecuted": true,
    "readonlyOnly": true,
    "contestantCodeExecuted": false,
    "commandExecuted": false,
    "networkEnabled": false
  }
}
```

## 命令示例

```powershell
python lab_cli.py grade sandbox-run --grading templates/grading/examples/readonly-sandbox.yaml --submission examples/submissions/readonly-demo --output examples/output/readonly-sandbox-report.json
python lab_cli.py grade sandbox-run --grading examples/output/mimo-real-demo-notebook-static-plan.json --submission examples/submissions/real-demo-notebook --output examples/output/mimo-real-demo-notebook-static-report.json
```

## 测试方式

```powershell
python -m pytest tests/test_readonly_sandbox_executor.py tests/test_cli.py tests/test_dsl_examples.py
```

## 限制说明

- `file_exists` / `json_field` / `log_keyword` 会执行只读文件检查；`notebook_cell` 只静态读取 `.ipynb` JSON，拼接指定 cell 的 `source` 和已有 `outputs` 文本后匹配 `expected` token。
- 所有路径必须是相对路径，且解析后必须仍在 `--submission` 目录内。
- JSON 文件大小限制为 1MB。
- Log 文件大小限制为 1MB，且必须是 UTF-8 文本。
- Notebook 文件大小限制为 5MB。
- JSONPath 当前只支持 `$.field` 和数字数组索引，如 `$.items[0].score`。
- 完整自动评分还需要后续容器执行器支持命令、pytest，以及真正的 Notebook kernel 执行。

## 下一步

- 将 `log_keyword` 静态 evidence 合并到审核页评分报告展示。
- 保持真实 Notebook kernel 执行延后，直到容器、资源限制和审计日志稳定。
- 在演示版中用受控 Docker 证据覆盖 `stdout_contains/pytest`，用静态 Notebook evidence 覆盖 `notebook_cell`。
