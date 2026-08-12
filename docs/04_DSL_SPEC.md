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
