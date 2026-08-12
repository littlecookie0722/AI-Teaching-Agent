# 04_DSL_SPEC

详见 `AI_PLATFORM_CODEX_FULL_GUIDE.md` 第 11 章。本项目 Phase 1 已提供四类 DSL：

- Lab：`templates/lab/lab.schema.json`
- Exam：`templates/exam/exam.schema.json`
- Grading：`templates/grading/grading.schema.json`
- PPT：`templates/ppt/ppt.schema.json`

## 示例

- Lab：`templates/lab/examples/basic-lab.yaml`
- Exam：`templates/exam/examples/notebook-fill-blank.yaml`
- Grading：`templates/grading/examples/python-pytest.yaml`
- PPT：`templates/ppt/examples/course-ppt.yaml`

## CLI 校验

```powershell
python lab_cli.py dsl validate --kind lab --file templates/lab/examples/basic-lab.yaml
python lab_cli.py dsl validate --kind exam --file templates/exam/examples/notebook-fill-blank.yaml
python lab_cli.py dsl validate --kind grading --file templates/grading/examples/python-pytest.yaml
python lab_cli.py dsl validate --kind ppt --file templates/ppt/examples/course-ppt.yaml
```

所有 AI 生成类 DSL 示例默认状态为 `WAITING_REVIEW`，审核通过前不得发布。

## Schema 校验约定

- 四类 DSL 使用 JSON Schema Draft 2020-12，由 `jsonschema.Draft202012Validator` 执行完整标准关键字校验。
- Schema 在加载时会先通过 Draft 2020-12 metaschema 自检；非法 Schema 不会进入 DSL 文档校验。
- `validate_dsl(document, schema)` 保持无返回值的成功契约；失败时抛出 `DslValidationError`，其中 `errors` 固定为 `[{"field": "$.spec...", "reason": "..."}]`。
- 字段路径延续 `$` 风格：对象字段使用 `$.metadata.title`，数组元素使用 `$.spec.questions[0].score`；多条错误按字段路径稳定排序。

聚焦验证：

```powershell
python -m pytest tests/test_dsl_examples.py tests/test_dsl_validation.py -q
```
