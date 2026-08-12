# templates

Phase 1 DSL Schema 与示例目录。当前包含 Lab / Exam / Grading / PPT 四类基础校验字段。

## 输入说明

- Schema：`templates/<kind>/<kind>.schema.json`
- 示例 YAML：`templates/<kind>/examples/*.yaml`
- Phase 3 Mock 评分示例：`templates/grading/examples/mixed-checks.yaml` 覆盖 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类评分项，并在 `spec.assessmentPlan` 中声明评分前计划字段，但仍不执行命令、pytest、Notebook、真实 JSON/日志读取或选手代码。

## 输出说明

示例 YAML 均作为 AI 生成后的中间产物，默认需要人工审核。Lab / Exam / Grading / PPT 示例状态为 `WAITING_REVIEW`。

## 命令示例

```powershell
python lab_cli.py dsl validate --kind lab --file templates/lab/examples/basic-lab.yaml
python lab_cli.py dsl validate --kind exam --file templates/exam/examples/notebook-fill-blank.yaml
python lab_cli.py grade run --grading templates/grading/examples/python-pytest.yaml
python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml
python lab_cli.py dsl validate --kind ppt --file templates/ppt/examples/course-ppt.yaml
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- Schema 只覆盖 Phase 1 必要字段，后续可按 DSL 规范继续扩展。
- 不包含真实发布、真实评分沙箱或真实云资源字段。
