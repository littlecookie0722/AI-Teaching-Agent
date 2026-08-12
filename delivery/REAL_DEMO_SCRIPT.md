# Real LLM Demo Script

本脚本用于演示“真实大模型产出成果”的第一版闭环。它只复放已有真实 DSL、验收摘要、评分 evidence 和静态页面，不重新请求大模型，不读取密钥，不访问网络，不运行 Docker / pytest / Notebook，不执行选手代码，不自动发布或真实发布。

## 输入说明

- `docs/21_REAL_LLM_DEMO_BUNDLE.md`: 真实 Demo Bundle 的范围、命令和限制。
- `examples/output/real-llm-demo-bundle.json`: 已有真实 LLM Demo Bundle。
- `examples/output/real-llm-demo-acceptance-summary.json`: 7/7 演示闭环验收摘要。
- `examples/output/real-llm-demo-checklist.json`: 一键演示清单。
- `frontend/real-demo.html`: 演示首屏。
- `frontend/review-center.html`: 人工审核队列。
- `frontend/ppt-review.html`: PPT 页级审核入口。
- `frontend/grading-report.html`: 评分 evidence 解释页。
- `frontend/mock-data.json`: 前端静态数据。
- `mcp-server/tools.manifest.json`: MCP `get_review_task_summary` 输出合同。
- `mcp-server/tools.manifest.json`: MCP `request_review_revision` / `regenerate_from_revision_mock` 审核循环工具合同。

## 输出说明

本脚本不生成真实平台内容。唯一可再生成的本地证据是：

```text
examples/output/real-llm-demo-checklist.json
```

## 命令示例

```powershell
start .\frontend\real-demo.html
start .\frontend\review-center.html
start .\frontend\ppt-review.html
start .\frontend\grading-report.html
python lab_cli.py phase2 demo-bundle checklist --bundle examples/output/real-llm-demo-bundle.json --acceptance-summary examples/output/real-llm-demo-acceptance-summary.json --output examples/output/real-llm-demo-checklist.json
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md
python lab_cli.py mcp call --tool request_review_revision --arguments "{\"taskId\":\"<task_id>\",\"reviewer\":\"teacher_1\",\"comment\":\"补充步骤截图验收标准。\",\"priority\":\"HIGH\",\"targetSections\":[\"steps\"]}"
python lab_cli.py mcp call --tool regenerate_from_revision_mock --arguments "{\"taskId\":\"<task_id>\",\"reviewer\":\"teacher_1\"}"
python -m pytest tests/test_cli.py tests/test_frontend_manifest.py
```

`start .\frontend\*.html` 只是人工本地预览。`phase2 demo-bundle checklist` 只读取已有 JSON 并生成清单，不调用真实模型、不运行评分、不发布。
MCP 审核循环命令只写入本地 Mock store：源任务不变，新修订任务仍为 `WAITING_REVIEW`，`newLlmRequestSent=false`、`realLlmCalled=false`。

## 演示顺序

1. 说明边界：这是“真实输出复放演示”，源 Bundle 来自真实 LLM 产物，但本次演示不发送新请求、不读取密钥、不发布。
2. 打开 `frontend/real-demo.html`，先看 `RealDemoOneClickChecklist`：`readyForDemo=true`、`acceptance=7/7`、`sections=6/6`、`gradingEvidenceCoverage=100/100`。
3. 指出 `generated_dsl` section：Lab / Exam / Grading / PPT 四类 DSL 都是 `WAITING_REVIEW`，AI 输出先进入人工审核。
4. 指出候选人预览：`candidate_preview` 通过，`answerVisibleToCandidate=false`，标准答案不出现在选手端。
5. 打开 `frontend/review-center.html`，展示 `RealDemoReviewQueue`：四个真实演示产物进入审核队列，`autoApproveAllowed=false`、`batchStateChangeAllowed=false`。
6. 打开 `frontend/ppt-review.html`，展示 PPTX Artifact 可做页级审核，但仍是 `WAITING_REVIEW`，不会自动发布。
7. 打开 `frontend/grading-report.html`，解释 Grading evidence：受控 Docker 覆盖 `40/40`，Notebook 静态解析覆盖 `60/60`，合计 `100/100`，但仍需人工审核。
8. 演示 MCP 审核循环：先创建一个本地 `WAITING_REVIEW` Lab 任务，再调用 `request_review_revision` 记录退回意见，最后调用 `regenerate_from_revision_mock` 创建新的待审核修订稿；强调这是 Agent 可调用工具入口，不是自动通过或真实发布。
9. 收尾确认安全边界：`newLlmRequestSent=false`、`secretsRead=false`、`networkAccess=false`、`sandboxExecutedByChecklist=false`、`commandExecutedByChecklist=false`、`realPublishAllowed=false`。

## 验证方式

```powershell
python -m pytest tests/test_real_demo_script.py
python -m pytest tests/test_cli.py tests/test_frontend_manifest.py
python -m pytest
```

## 限制说明

- 不发送新的真实 LLM 请求。
- 不读取或展示 API Key、Token、密码。
- 不访问网络。
- 不运行 Docker、pytest、Notebook kernel 或选手代码。
- 不展示选手端应隐藏的标准答案。
- 不批量通过、不自动通过、不自动发布、不真实发布。
- MCP 审核循环只创建本地修改意见和待审核修订稿，不发送新的真实 LLM 请求，不改变源任务状态。
- `gradingEvidenceCoverage=100/100` 只说明演示 evidence 已覆盖，不代表真实业务已完成审批。
