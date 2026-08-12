# 01_ARCHITECTURE

详见 `AI_PLATFORM_CODEX_FULL_GUIDE.md` 第 2 章。

## Phase 1 模块关系

```text
Frontend Contract
  ↓
Backend API Mock
  ↓
CLI Mock / Workflow Mock
  ↓
Material Analysis Mock / DSL Schema / AI Task / Sandbox Mock
```

当前前端不启动真实应用，只维护：

- `frontend/ui.manifest.json`
- `frontend/mock-data.json`

页面必须遵守：

- 实验生成前先展示素材静态分析结果
- AI 生成内容默认 `WAITING_REVIEW`
- 审核拒绝必须填写 reason
- 审核通过前不得发布
- 不展示标准答案给选手端
- 不展示密钥
- 不创建真实 VM / Notebook
- 不执行选手代码

## Phase 1 首批页面

```text
/dashboard
/ai-tasks
/labs/generate
/labs/:id/review
/grading/:id/report
```

## Phase 1 第二批页面

```text
/exams/generate
/environments
/skills
/settings/providers
```
