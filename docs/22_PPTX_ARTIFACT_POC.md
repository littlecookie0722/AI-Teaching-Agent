# 22_PPTX_ARTIFACT_POC

状态：已实现第一版，并在 v0.1.3 增加构建前质量预检。

本文件记录 PPT DSL 到本地 PPTX Artifact 的最小可用 PoC。该能力只读取本地 PPT DSL，使用 bundled `@oai/artifact-tool/presentation-jsx` 导出可打开的 `.pptx` 文件，不新增 LLM 请求，不读取密钥，不访问网络，不自动发布。

## 范围

已实现：

- `ppt artifact build`
- `phase2 demo-bundle build` 已复用该能力，为真实 LLM Demo PPT DSL 生成本地 PPTX Artifact 附件。
- 输入本地 PPT DSL YAML。
- 先执行 `templates/ppt/ppt.schema.json` 校验。
- 仅接受 `WAITING_REVIEW` 状态的 PPT DSL。
- 生成本地 PPTX 文件。
- 写入 `PPT_ARTIFACT_GENERATION` AI Task，状态仍为 `WAITING_REVIEW`。
- 写入 `PPTX_FILE` Artifact 记录。
- Manifest、CLI 返回和审核页均包含 `preview` / `firstSlidePreview` / `slidePreviews` / `contactSheet` 字段；提供 preview 输出路径时会用 artifact-tool 渲染首页 PNG，提供 preview dir/contact sheet 路径时会渲染每页 PNG 和总览图。
- PPT 审核页已补充 `pageReviewSummary`、逐页 `reviewStatus`、人工批注和 `qaSignals` 静态契约，覆盖 `APPROVED` / `NEEDS_REVIEW` / `REVISE_REQUIRED` 三类状态。
- `ppt artifact build` 会生成 `qualityReport`：按页检查标题、正文密度、长文本、估算溢出和 renderer 的 6-bullet 截断风险；报告同时写入构建 JSON、manifest、`PPTX_FILE` Artifact metadata 和页级 `qaSignals`。
- `qualityReport` 只读且 `advisoryOnly=true`，质量 warning/blocking 不会绕过人工审核，也不会改变 `WAITING_REVIEW` 或触发发布。
- PPT 页级审核更新已接入 Backend Mock、CLI 和前端静态演示：`POST /api/review-tasks/{id}/ppt-page-review-status`、`python lab_cli.py review ppt-page-update`、`PptPageReviewUpdateAction`。
- 页级审核更新只修改 PPTX Artifact 的页级审核元数据，写入 `PPT_PAGE_REVIEW_UPDATE` 操作审计，返回更新后的 `pageReviewSummary`，不改变 AI Task 状态，不自动通过，不自动发布。
- 返回统一 JSON。

未实现：

- 不调用真实 LLM。
- 不重新生成 PPT DSL 内容。
- 不读取或输出 API Key。
- 不上传对象存储。
- 不发布到真实平台。
- 不替代人工审核。

## 输入说明

- 运行环境需要可执行的 Node.js，以及 Codex presentations runtime。默认从 `PATH` 查找 `node`，也可通过 `CODEX_NODE_EXE` 指定可执行文件；可通过 `PRESENTATIONS_SKILL_DIR` 指定 presentations Skill 目录。
- `--dsl`: 本地 PPT DSL 文件，必须通过 Schema 校验，且状态必须是 `WAITING_REVIEW`。
- `--output`: 本地 PPTX 输出路径，默认 `examples/output/ppt-artifact.pptx`。
- `--manifest-output`: 可选，本地构建摘要 JSON 输出路径。
- `--preview-output`: 可选，首页 PNG 预览输出路径；未提供时默认写到 PPTX 同目录同名 `-slide-01.png`。
- `--preview-dir`: 可选，每页 PNG 缩略图输出目录；未提供时默认写到 PPTX 同目录同名 `-slides/`。
- `--contact-sheet-output`: 可选，缩略图总览图输出路径；未提供时默认写到 PPTX 同目录同名 `-contact-sheet.png`。
- `--reviewer`: 记录本地操作审计 actor，默认 `teacher_1`。

## 命令示例

```powershell
python lab_cli.py ppt artifact build --dsl templates/ppt/examples/course-ppt.yaml --output examples/output/ppt-artifact-demo.pptx --manifest-output examples/output/ppt-artifact-demo-manifest.json --preview-output examples/output/ppt-artifact-demo-slide-01.png --preview-dir examples/output/ppt-artifact-demo-slides --contact-sheet-output examples/output/ppt-artifact-demo-contact-sheet.png
```

页级审核更新 Mock：

```powershell
python lab_cli.py review ppt-page-update --task-id task_ppt_demo --slide-index 4 --review-status REVISE_REQUIRED --reviewer teacher_1 --comment "需要补充操作截图"
```

## 输出说明

关键字段：

```json
{
  "mode": "LOCAL_PPTX_ARTIFACT_POC",
  "task": {
    "taskType": "PPT_ARTIFACT_GENERATION",
    "status": "WAITING_REVIEW"
  },
  "artifact": {
    "kind": "PPTX_FILE",
    "status": "WAITING_REVIEW",
    "metadata": {
      "qualityReport": {
        "status": "PASS",
        "advisoryOnly": true,
        "issueTotal": 0
      },
      "previewAvailable": true,
      "firstSlidePreview": {
        "title": "AI 工具应用课程",
        "imagePath": "examples/output/ppt-artifact-demo-slide-01.png"
      },
      "slidePreviews": [
        {"index": 1, "imagePath": "examples/output/ppt-artifact-demo-slides/slide-01.png"}
      ],
      "contactSheet": {
        "path": "examples/output/ppt-artifact-demo-contact-sheet.png"
      }
    },
    "realLlmCalled": false,
    "realPublish": false
  },
  "safety": {
    "newLlmRequestSent": false,
    "secretsRead": false,
    "networkAccess": false,
    "autoPublishAllowed": false,
    "realPublish": false
  }
}
```

## 测试方式

```powershell
python -m pytest tests/test_ppt_preflight.py -q
python -m pytest tests/test_cli.py -q
python -m pytest
```

缺少 Node.js 或 Codex presentations runtime 时，仅跳过 7 个实际生成 PPTX 的端到端测试；其余核心回归测试继续执行。跳过不代表 PPTX 能力已验证，发布前仍需在具备该运行时的环境执行上述完整测试。

## 限制说明

- 当前是 Artifact PoC，版式只保证可打开、可编辑和可审核，不承诺高端商业演示稿质量。
- 质量预检是基于 PPT DSL 的启发式 advisory report，不等同于像素级渲染验证；warning/blocking 仍需人工判断和修改源 DSL。
- 当前已渲染每页 PNG 和 contact sheet；逐页审核状态、人工批注、QA 信号和页级状态更新仍是本地审核辅助，不代表自动通过。
- 输入必须是 PPT DSL；该命令不直接从 Markdown 或 Prompt 生成内容。
- 生成的 PPTX 仍需人工审核，审核通过前不得发布。
- 后续若要生产级课件，应在此命令之上增加渲染预览、版式 QA、模板体系和前端审核预览。

## 下一步

- PPT 审核页和审核中心已展示 PPTX Artifact 摘要、路径、manifest、slideCount、bytes、审核状态、首页 PNG、contact sheet、逐页审核状态、人工批注、版式 QA 信号和 `PptPageReviewUpdateAction`。
- v0.1.3 已把 PPT DSL 质量预检接入本地 PPTX Artifact 和 Demo Bundle；下一步回到 P1 核心业务缺口，优先处理具体的评分隔离/报告问题或真实前端交互缺陷。
