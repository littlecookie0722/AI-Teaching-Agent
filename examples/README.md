# examples

本地示例输入和可复现演示入口。

## 输入说明

- `examples/input/demo-source.md`：用于 Mock 生成 Lab DSL / PPT DSL 的 Markdown 输入。
- `examples/review-detail/lab-review-detail.json`：用于前端审核页和运营演示的静态审核详情 Mock 示例。

## 输出说明

Mock CLI 不会把 AI 结果直接发布，只返回示例 DSL 路径和 `WAITING_REVIEW` 状态的 AI Task。
素材分析命令只返回本地静态摘要和风险标记，不执行输入文件里的 Shell。

## 命令示例

```powershell
python lab_cli.py demo offline
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md
python lab_cli.py material analyze --input examples/input/demo-source.md
python lab_cli.py ppt generate --input examples/input/demo-source.md
python lab_cli.py review detail --task-id <task_id> --output examples/output/review-detail.json
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- `demo offline` 使用本地 deterministic fixture / MockProvider，不读取 API Key、不联网。
- 生成结果只进入 `WAITING_REVIEW`，不会自动发布；候选人预览不包含答案或内部 `gradingRef`。
- 示例命令不执行未知 Shell 脚本，也不执行选手代码。
