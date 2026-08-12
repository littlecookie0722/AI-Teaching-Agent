# review-detail

Phase 1 审核详情示例目录。这里放可提交的静态 Mock JSON，用于前端审核页、运营手册和 MCP Tool 契约对齐。

## 输入说明

- 示例来源：本地 Lab 生成任务和 `examples/input/demo-source.md`。
- 示例状态：`WAITING_REVIEW`。

## 输出说明

- `lab-review-detail.json`：单个 Lab 审核任务的聚合视图，包含 AI Task、Artifact、Workflow Step、审核策略、页面模型和安全标记。

## 命令示例

```powershell
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md
python lab_cli.py review detail --task-id <task_id> --output examples/output/review-detail.json
```

## 测试方式

```powershell
python -m pytest tests/test_review_detail_examples.py
```

## 限制说明

- 仅 Phase 1 Mock 示例。
- 不调用真实大模型。
- 不发布真实实验或考试。
- 不展示选手端标准答案。
