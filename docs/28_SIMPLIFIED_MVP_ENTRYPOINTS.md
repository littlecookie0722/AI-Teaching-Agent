# 精简 MVP 入口与实施边界

> 状态：精简教学包 MVP 已完成；用户已选择 PPT 产品化，现已追加 5-8 页本地教学 PPT child workflow，并达到该阶段停止线。
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
→ 生成 5-8 页教学 PPT
→ 逐页审核、整套人工决定并在批准后本地下载
```

这里的“单一入口”表示用户不需要理解内部 CLI、MCP、平台实体或多个工作台；它不表示绕过逐项人工审核，也不引入批量自动通过。

## 2. 现有入口盘点

| 入口 | 当前能力 | 决策 | 主要差距 |
| --- | --- | --- | --- |
| `frontend/generation-workspace.html` | 一份素材、一次请求以 `teaching-core` 生成 Lab / Exam / Grading，创建 3 个 `WAITING_REVIEW` 任务。 | 唯一默认生成入口，已完成。 | 下一步不再扩张生成页。 |
| `frontend/review-center.html` | 按同一 `workflowRun.id` 聚合三类任务、教学包导出与教学 PPT child workflow；支持 PPT 预览、逐页审核、整套人工决定及批准后下载。 | 唯一默认审核、导出与 PPT 审核入口，已完成。 | 不新增批量审核、第二个课件页、在线编辑器或发布能力。 |
| `frontend/lab-generate.html`、`frontend/exam-generate.html` | 分别覆盖 Lab 和 Exam/Grading 生成。 | 保留为兼容与诊断入口，退出当前主导航。 | 不再单独产品化。 |
| `frontend/lab-review.html`、`frontend/exam-review.html`、`frontend/grading-review.html` | 单任务详情和人工审核动作。 | 在审核中心达到功能等价前保留为深层详情入口。 | 不再作为教师必须依次访问的主流程。 |
| 旧 PPT 页面、评分报告、评分工作台、平台实体、AI Task、MCP、Agent 页面 | 支撑此前更大范围本地 PoC。 | 冻结并退出当前主导航。教学 PPT 只在默认审核中心产品化。 | 只修复兼容性、安全或阻断当前闭环的问题。 |

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

当前实现通过 `GET /api/review-task-summary?detailMode=light&workflowRunId=<id>` 返回 `TeachingPackageReviewSummary`。摘要从 WorkflowRun、Artifact 和当前 AI Task 派生，不新增 `TeachingPackage` 持久化实体；未知运行返回 `NOT_FOUND`，历史 `legacy-all` 运行继续按批次返回原四类任务，但教学包摘要标记为不可用。默认生成入口把 `taskId` 和 `workflowRunId` 一并传给审核中心，动作完成后回读同一批次。页面不显示 Exam 答案或内部 `gradingRef`，也不提供批量状态变更。

## 5. 本地导出边界

本地教学包导出只在三个任务全部 `APPROVED` 后启用。公共入口为：

```text
lab-cli teaching-package export --workflow-run-id <id> --reviewer <name> [--output <zip>]
POST /api/teaching-packages/export
```

API 请求体只接受 `workflowRunId` 与 `reviewer`，固定写入 `examples/output/teaching-packages/<workflowRunId>.zip`；传入 `output` 会返回 `VALIDATION_ERROR`，只有 CLI 可用 `--output` 指定其他本地 ZIP。ZIP 固定且仅包含：

```text
manifest.json
lab.json
exam.json
grading.json
exam-candidate-preview.json
review-summary.json
```

导出会从 WorkflowRun、Artifact 与当前 AI Task 重新确认 `teaching-core` 身份和三项 `APPROVED` 状态，重新执行 Lab / Exam / Grading Schema 校验并重新生成候选人安全预览。为保持确定性 ZIP，`manifest.json` 不包含 `reviewer`、`exportedAt` 或其他易变导出元数据；导出人和导出时间只记录在 operation audit。任一条件不满足时不保留部分 ZIP。导出不依赖 platform entity、import-preview、mock-import 或 import-dry-run，不发送网络请求、不执行评分沙箱、不改变任务状态、不发布。后续教学 PPT 生成使用独立 child WorkflowRun，因此该 ZIP 始终保持六成员。

## 5.1 教学 PPT 扩展

公共入口为 `ppt generate-from-teaching-package` 和 `POST /api/teaching-presentations/generate`。两者只接受已批准、`exportReady=true` 的父批次，默认生成 6 页并支持 5-8 页。生成服务创建独立 child WorkflowRun 和单个 `PPT_GENERATION` / `WAITING_REVIEW` 任务，输出 PPT DSL、16:9 PPTX、逐页 PNG、contact sheet 与 manifest。

审核中心只通过 Artifact ID 路由读取预览。每页人工审核后，只有全部页面为 `APPROVED` 才允许批准整套课件，且只有整套任务批准后才允许下载 PPTX。课件可见内容不含答案或内部 `gradingRef`。该扩展不引入 LLM 请求、在线编辑器、云上传、平台导入、自动批准或发布。

## 6. 实施顺序

1. 已完成：为既有内容生成 API 增加 `artifactProfile=teaching-core`，补正常、非法 profile、失败不落任务和兼容路径测试。
2. 已完成：将 `generation-workspace.html` 默认切到 `teaching-core`，只展示三类产物和一个审核中心入口。
3. 已完成：`review-center.html` 按 `workflowRun.id` 展示教学包进度，并接入已有逐任务人工决定。
4. 已完成：增加仅对全部已批准任务开放的本地六文件 ZIP 教学包导出，并接回默认审核入口。
5. 已完成：保持单一生成/审核入口，保留旧入口的直接 URL 与契约回归，并完成 Mock 正常、错误、状态、脱敏和端到端验收。
6. 已完成：从已批准教学包生成 5-8 页本地教学 PPT，并在同一审核中心完成逐页审核、整套决定和批准后下载。

每一步单独完成、单独测试；PPT 只实现上述 child workflow，不得把受控评分、平台实体、MCP 或 Agent 顺带带回当前范围。

## 7. 验收证据

当前已提供并验证：

- Mock：一份 Markdown 生成 3 个 `WAITING_REVIEW` 任务，无 PPT 任务。
- 错误：无效 `artifactProfile` 和 Schema 失败返回统一错误，且不创建审核任务。
- 兼容：未传 `artifactProfile` 的既有四类调用仍通过原回归。
- 审核：三个任务逐项 approve/reject，拒绝必须填写 reason，状态可由同一审核中心回读。
- 脱敏：候选人预览中不存在答案或 `gradingRef`。
- 导出：未全部批准时阻断且无部分文件；全部批准后 ZIP 恰好包含六个约定成员且不触发外部行为。
- PPT：已批准父批次可生成 5-8 页、至少三种版式的 16:9 PPTX；逐页 PNG、contact sheet、页级审核门槛、批准后下载和候选人脱敏均有专项回归。
- 全量：项目测试、安装后 smoke、契约校验、安全扫描和桌面/移动端浏览器验收均通过。

以上证据已满足精简 MVP 与教学 PPT 产品化停止线。后续只修复具体版式、兼容性或安全缺陷，不自动转入自动评分或恢复其他冻结路线。
