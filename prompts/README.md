# prompts

Phase 1 Prompt 模板与索引目录。当前只沉淀 Prompt 契约和占位模板，不调用真实大模型。

## 输入说明

- `manifest.json`: Prompt 注册表，声明 Prompt id、版本、路径、输入类型、输出类型、Schema、审核要求和安全限制。
- `workflows/*.md`: Lab / Exam / Grading / PPT 生成类 Prompt 占位模板。
- `codex/*.md`: Codex 开发辅助 Prompt。

## 输出说明

生成类 Prompt 必须输出 DSL：

```text
Lab      -> templates/lab/lab.schema.json
Exam     -> templates/exam/exam.schema.json
Grading  -> templates/grading/grading.schema.json
PPT      -> templates/ppt/ppt.schema.json
```

生成结果默认 `WAITING_REVIEW`，审核通过前不得发布。

## 命令示例

```powershell
python -m pytest tests/test_prompt_manifest.py
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- Phase 1 不调用真实大模型。
- Prompt 不得散落在业务代码里，业务代码只能引用 `prompts/` 或 `skills/` 文件。
- Prompt 不得包含 API Key、Token、密码或其他密钥。
- Exam Prompt 不得把标准答案展示给选手端。
- Grading Prompt 不得让大模型直接给最终分数。
- 生成类 Prompt 必须绑定 DSL Schema，并要求人工审核。
