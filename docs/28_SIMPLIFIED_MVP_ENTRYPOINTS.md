# 精简 MVP 入口与实施边界

> 状态：生成入口与 `teaching-core` profile 已完成，审核聚合与本地导出待实现。
> 日期：2026-08-23
> 上位约束：`AGENTS.md`、`docs/24_PROJECT_PROGRESS_MAP.md`

## 1. 目标

当前只优化一条教师工作流：

```text
打开生成入口
→ 提交一份 Markdown
→ 生成 Lab + Exam/Grading
→ 在审核入口逐项查看并记录人工决定
→ 全部通过后导出本地教学包
```

这里的“单一入口”表示用户不需要理解内部 CLI、MCP、平台实体或多个工作台；它不表示绕过逐项人工审核，也不引入批量自动通过。

## 2. 现有入口盘点

| 入口 | 当前能力 | 决策 | 主要差距 |
| --- | --- | --- | --- |
| `frontend/generation-workspace.html` | 一份素材、一次请求生成 Lab / Exam / Grading / PPT，创建 4 个 `WAITING_REVIEW` 任务。 | 选为唯一默认生成入口。 | 默认视图需收敛为 Lab + Exam/Grading，并停止创建 PPT 任务。 |
| `frontend/review-center.html` | 集中读取审核队列、DSL 摘要、质量信号和候选人安全信息。 | 选为唯一默认审核入口。 | 需按同一 `workflowRun.id` 聚合三类任务，并接入已有逐任务 approve/reject 动作。 |
| `frontend/lab-generate.html`、`frontend/exam-generate.html` | 分别覆盖 Lab 和 Exam/Grading 生成。 | 保留为兼容与诊断入口，退出当前主导航。 | 不再单独产品化。 |
| `frontend/lab-review.html`、`frontend/exam-review.html`、`frontend/grading-review.html` | 单任务详情和人工审核动作。 | 在审核中心达到功能等价前保留为深层详情入口。 | 不再作为教师必须依次访问的主流程。 |
| PPT、评分报告、评分工作台、平台实体、AI Task、MCP、Agent 页面 | 支撑此前更大范围本地 PoC。 | 冻结并退出当前主导航。 | 只修复兼容性、安全或阻断当前闭环的问题。 |

## 3. 后端复用决策

默认生成流程复用现有：

```text
POST /api/phase2/workflows/content-generation/run
```

该接口当前固定生成四类 DSL。实施时增加可选请求字段 `artifactProfile`：

| 值 | 行为 | 兼容策略 |
| --- | --- | --- |
| `legacy-all` | 保持现有 Lab / Exam / Grading / PPT 四类输出。 | 未传字段时继续使用，避免破坏既有 CLI、测试和演示调用。 |
| `teaching-core` | 只生成 Lab / Exam / Grading，并创建 3 个 `WAITING_REVIEW` 任务。 | 精简生成页面显式传入，作为当前产品默认。 |

不新增第二个同义生成 API。`teaching-core` 必须复用现有 Provider、归一化、Schema、Artifact、WorkflowRun 和审计逻辑，并满足：

- 任一核心 DSL 生成或校验失败时，不创建可审核任务。
- Mock 仍是默认 Provider；真实 LLM 仍需显式 opt-in 和确认项。
- 响应继续保留统一 JSON envelope、`createdTasks`、`generatedDsl`、`workflowRun`、`reviewSummary` 和 `safety`。
- `generatedDsl` 在 `teaching-core` 下只包含 `lab`、`exam`、`grading`；不得生成空 PPT 占位任务。
- Exam 候选人预览固定隐藏答案和内部 `gradingRef`。

## 4. 教学包聚合模型

当前不新增 `TeachingPackage` 数据库实体。使用已有 `workflowRun.id` 作为一次教学包生成批次的稳定关联键，并从已有任务和 Artifact 派生只读摘要。

目标摘要至少包含：

```text
workflowRunId
artifactProfile=teaching-core
sourceRef
Lab / Exam / Grading taskId、status、dslPath、schemaValidated
candidateSafeExamPreview
reviewProgress
exportReady
reviewEntry
```

状态按三个任务派生：

- 任一任务为 `REJECTED`：教学包为 `NEEDS_REVISION`。
- 否则任一任务仍为 `WAITING_REVIEW`：教学包为 `WAITING_REVIEW`。
- 三个任务均为 `APPROVED`：教学包为 `APPROVED`，允许本地导出。

不得新增批量 approve/reject 接口。审核中心可集中展示三个任务，但每次决定仍调用已有 `POST /api/ai-tasks/{id}/approve` 或 `POST /api/ai-tasks/{id}/reject`，并保留 reviewer、reject reason 和审计事件。

## 5. 本地导出边界

本地教学包导出只在三个任务全部 `APPROVED` 后启用，目标内容为：

```text
manifest.json
lab.json
exam.json
grading.json
exam-candidate-preview.json
review-summary.json
```

导出不依赖 platform entity、import-preview、mock-import 或 import-dry-run，不发送网络请求、不执行评分沙箱、不生成 PPT、不发布。具体 CLI/API 名称在实现导出切片时写入 `docs/05_API_SPEC.md` 和 `docs/06_CLI_SPEC.md`，本文件不预先声明尚未实现的公共接口。

## 6. 实施顺序

1. 已完成：为既有内容生成 API 增加 `artifactProfile=teaching-core`，补正常、非法 profile、失败不落任务和兼容路径测试。
2. 已完成：将 `generation-workspace.html` 默认切到 `teaching-core`，只展示三类产物和一个审核中心入口。
3. 让 `review-center.html` 按 `workflowRun.id` 展示教学包进度，并接入已有逐任务人工决定。
4. 增加仅对全部已批准任务开放的本地教学包导出。
5. 收敛主导航和 E2E，保留旧入口的直接 URL 与契约回归。

每一步单独完成、单独测试；不得把 PPT、受控评分、平台实体、MCP 或 Agent 顺带带回当前范围。

## 7. 验收证据

实施完成后至少提供：

- Mock：一份 Markdown 生成 3 个 `WAITING_REVIEW` 任务，无 PPT 任务。
- 错误：无效 `artifactProfile` 和 Schema 失败返回统一错误，且不创建审核任务。
- 兼容：未传 `artifactProfile` 的既有四类调用仍通过原回归。
- 审核：三个任务逐项 approve/reject，拒绝必须填写 reason，状态可由同一审核中心回读。
- 脱敏：候选人预览中不存在答案或 `gradingRef`。
- 导出：未全部批准时阻断；全部批准后产出六个本地文件且不触发外部行为。
