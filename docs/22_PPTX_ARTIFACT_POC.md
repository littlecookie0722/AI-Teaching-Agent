# 22_PPTX_ARTIFACT_POC

状态：v0.1.10 已完成教学 PPT 产品闭环的真实样本版式质量回归。

当前实现包含两条兼容路径：

- `ppt artifact build`：读取已有 `WAITING_REVIEW` PPT DSL，生成本地 PPTX 与预览。
- `ppt generate-from-teaching-package`：从已批准的 `teaching-core` 教学包确定性生成 5-8 页教学 PPT，默认 6 页。

两条路径都使用项目内的 `python-pptx` + Pillow 构建器，不需要 Node.js、Codex presentations runtime、网络或密钥。历史 `scripts/build_pptx_from_ppt_dsl.mjs` 继续保留为直接调用兼容工具，但不再是 CLI 默认实现。

## 产品范围

教学 PPT 路径只接受 `exportReady=true` 的 `teaching-core` 父 WorkflowRun，并重新校验 Lab / Exam / Grading Schema、跨产物引用和候选人安全预览。可见内容只来自 Lab 与候选人安全 Exam 预览，不读取答案作为课件内容，也不显示内部 `gradingRef`。

默认 6 页依次为：

1. 封面
2. 学习目标
3. 核心概念
4. 实验流程
5. 候选人安全练习
6. 总结

`--slide-count` 支持 5-8。生成服务强制页数范围、首尾语义、必要教学段落、唯一页 ID、Schema、泄漏检查和质量预检；全局 PPT Schema 继续允许历史短 Deck，以保持旧接口兼容。

产品 DSL 会显式写入 `hero` / `objectives` / `concept` / `process` / `exercise` / `summary` 版式，并按实际画布容量生成 bullet：学习目标和总结最多 3 条，核心概念、实验流程和课堂练习最多 4 条。5/6 页课件的流程槽不足以逐条展示全部源 Lab 步骤时，最后一个可用流程槽会明确聚合剩余步骤的编号范围和数量，避免源步骤静默消失或总结夸大覆盖范围。标题、副标题和 bullet 也按版式安全长度收敛，超长显示文本保留明确省略号。旧 DSL 可继续省略 `layout`，预检和构建器会用同一规则推断版式。

成功生成后会创建独立 `teaching_presentation_generation` child WorkflowRun，不向父教学包追加 PPT Artifact。父教学包的三项审核摘要与六成员 ZIP 因而保持不变。

## 本地产物

默认目录：

```text
examples/output/teaching-presentations/<childWorkflowRunId>/
  presentation.json
  presentation.pptx
  manifest.json
  contact-sheet.png
  slides/slide-01.png ...
```

PPTX 为 16:9；逐页预览为 1280x720 PNG。Manifest 和 `PPTX_FILE` Artifact metadata 包含 SHA-256、文件大小、逐页审核状态、contact sheet 和 advisory `qualityReport`。预检中的 `renderedBulletLimit` / `renderedBulletTotal` 与实际版式一致；超容量或超长兼容 DSL 会进入 `NEEDS_REVIEW`，PPTX 与 PNG 使用相同的显示文本。

构建先在同一输出根目录的临时目录完成，PPTX、全部页面预览和 contact sheet 完整后才原子提升为最终目录。构建失败不会创建 child WorkflowRun、AI Task 或 Artifact，也不会留下最终半成品目录。

## 审核与下载

新课件只创建一个 `PPT_GENERATION` / `WAITING_REVIEW` 任务。每页支持：

- `APPROVED`
- `NEEDS_REVIEW`
- `REVISE_REQUIRED`

`REVISE_REQUIRED` 必须填写人工批注。只有全部页面为 `APPROVED` 时，整套课件才允许人工批准；整套任务为 `APPROVED` 后才允许下载 PPTX。预览和下载只使用 Artifact ID 路由：

```text
GET /api/ppt-artifacts/{artifactId}/previews/{slideIndex}
GET /api/ppt-artifacts/{artifactId}/contact-sheet
GET /api/ppt-artifacts/{artifactId}/download
```

这些路由复用可选的 `LAB_BACKEND_API_TOKEN` Bearer 校验，只读取 Artifact 已注册且位于本地工作区内的文件。产品 Deck 每次读取预览、contact sheet 或 PPTX 时还会核对 Artifact metadata 中登记的 SHA-256，缺失或不匹配均 fail closed；前端不接收或拼接本地文件路径。

## 命令示例

从已批准教学包生成默认 6 页课件：

```powershell
python lab_cli.py ppt generate-from-teaching-package --workflow-run-id <approvedWorkflowRunId> --reviewer teacher_1 --slide-count 6
```

兼容的已有 DSL 构建：

```powershell
python lab_cli.py ppt artifact build --dsl templates/ppt/examples/course-ppt.yaml --output examples/output/ppt-artifact-demo.pptx --manifest-output examples/output/ppt-artifact-demo-manifest.json --preview-output examples/output/ppt-artifact-demo-slide-01.png --preview-dir examples/output/ppt-artifact-demo-slides --contact-sheet-output examples/output/ppt-artifact-demo-contact-sheet.png
```

逐页审核：

```powershell
python lab_cli.py review ppt-page-update --task-id <presentationTaskId> --slide-index 4 --review-status APPROVED --reviewer teacher_1
python lab_cli.py review approve --task-id <presentationTaskId> --reviewer teacher_1
```

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_pptx_artifact.py tests/test_teaching_presentation.py tests/test_backend_ppt_artifact_routes.py tests/test_teaching_presentation_frontend.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_ppt_preflight.py tests/test_cli.py tests/test_backend_mock_api.py
```

## 限制与停止线

- 当前生成是本地确定性转换，不新增真实 LLM 请求。
- 质量预检是启发式报告，不能替代逐页人工视觉检查。
- 不提供在线编辑器、模板市场、云上传、平台导入、自动批准或发布。
- 自动评分、MCP/Agent 扩张和外部平台路线继续冻结。
- 5-8 页本地生成、预览、逐页审核、整套人工决定和批准后下载已达到本阶段停止线；后续只修复具体版式、兼容性或安全缺陷。
