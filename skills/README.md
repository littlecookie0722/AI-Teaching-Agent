# skills

Phase 1 可复用 Skill 目录。当前只沉淀 Skill 说明和 manifest，不启动真实智能体，不调用真实大模型。

## 输入说明

- `manifest.json`: Skill 注册表，声明 Skill 文件、Prompt、Workflow、DSL Schema、示例输出和 CLI 映射。
- `*/SKILL.md`: 单个 Skill 的运营说明。
- `operations-skill-pack/SKILL.md`: Phase 5 运营复用 Skill 包，组合 Lab / Exam / Grading / PPT / 交付验收流程。
- `operations-skill-pack.contract.json`: Phase 5 运营 Skill 包机器契约。

## 输出说明

Skill 的生成结果必须先落到 DSL：

```text
lab-generation              -> Lab DSL
exam-generation             -> Exam DSL
grading-script-generation   -> Grading DSL
ppt-generation              -> PPT DSL
operations-skill-pack       -> 本地运营复用流程和验收证据
```

生成类输出默认 `WAITING_REVIEW`，审核通过前不得发布。

## 命令示例

```powershell
python -m pytest tests/test_skill_manifest.py
python -m pytest tests/test_operations_skill_pack.py
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- Phase 1 不调用真实大模型。
- 不启动真实 Agent。
- Skill 只引用 `prompts/`、`ai-workflows/`、`templates/` 和 CLI Mock。
- 不创建真实云资源。
- 不执行选手代码。
- 不绕过人工审核。
