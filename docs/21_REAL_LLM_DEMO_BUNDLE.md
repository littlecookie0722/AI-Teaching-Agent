# 21_REAL_LLM_DEMO_BUNDLE

状态：已实现第一版。

本文件记录“真实 LLM 产出成果演示包”收口流程。它复放已有真实 LLM DSL 产物，不再次调用大模型，不读取密钥，不访问网络。

## 范围

已实现：

- `phase2 demo-bundle build`
- `phase2 demo-bundle report`
- `phase2 demo-bundle acceptance`
- `phase2 demo-bundle checklist`
- 读取已有真实 Workflow Report 和 Lab / Exam / Grading / PPT DSL。
- 对四类 DSL 做本地 Schema 校验，并确认状态仍为 `WAITING_REVIEW`。
- 为真实 Exam DSL 生成候选人预览摘要，固定 `answerVisibleToCandidate=false`。
- 对真实 Grading DSL 做确定性归一化。
- 生成真实沙箱前预检报告。
- 执行只读沙箱 PoC，支持 `file_exists` / `json_field`，其它检查延期。
- 额外生成独立的只读 evidence 演示 Grading DSL，用 `result.csv` 和 `metrics.json` 产出可展示评分证据；该演示层不修改原始真实 LLM Grading DSL。
- 从真实 PPT DSL 生成本地 PPTX Artifact 附件，状态仍为 `WAITING_REVIEW`，审核通过前不得发布。
- 前端 `real-demo.html` 已补充 `CoreBusinessDemoPath`，把真实 Lab、Exam、Grading、只读 evidence、PPTX Artifact 和 PPT 页级审核动作串成一条运营演示主线。
- 前端 `real-demo.html` 已补充 `RealDemoAcceptanceSummary`，展示 `phase2 demo-bundle acceptance` 生成的闭环验收摘要、7/7 通过信号、Grading evidence coverage `100/100`、MCP 合同可见性和安全边界。
- 前端 `real-demo.html` 已补充 `RealDemoOneClickChecklist`，展示 `phase2 demo-bundle checklist` 生成的一键演示清单，把四类 DSL、候选人预览、Grading evidence coverage、PPTX Artifact、Review/MCP 合同和安全边界折叠成 `6/6` section。
- 前端 `operations-presenter.html` 与 `operations-signoff.html` 已补充 `RealDemoAcceptanceSummary`，让运营讲解和签收视角也能引用同一份闭环摘要。
- 前端 `real-demo.html` 与 `grading-report.html` 已同源展示 `readonlyEvidenceDemo.reportDetail`，用于解释只读 evidence 的 checkSummary、checkPlans、readonlyEvidence 状态和安全边界。
- 前端 `real-demo.html` 与 `grading-report.html` 已补充 `controlledDockerEvidenceDemo` 摘要，展示真实 demo Grading DSL 子集 `check_q1` / `check_q4` 的受控 Docker `stdout_contains` / `pytest` 评分证据、`40/40` 得分、固定镜像校验结果和宿主机执行禁用边界。
- 前端 `review-center.html` 已补充 `RealDemoReviewQueue`，把真实演示 Lab / Exam / Grading / PPT 四个 `WAITING_REVIEW` 产物接入人工审核视图。
- 前端 `review-center.html` 已补充 `ControlledDockerEvidenceReviewSignal`，把受控 Docker evidence 的覆盖点和缺口接入审核中心：`check_q1` / `check_q4` 已有容器证据，`check_q2` / `check_q3` 仍为 Notebook 人工审核缺口。
- 前端 `review-center.html` 已补充 `NotebookEvidenceReviewPlan`，把 `check_q2` / `check_q3` 的 Notebook 缺口展开为只读审核计划，不启动 Notebook kernel。
- CLI `phase2 demo-bundle acceptance` 已补充演示闭环验收摘要，把真实 Demo Bundle、前端审核入口、MCP 输出合同和只读评分报告明细串成一个本地 JSON 证据索引。
- CLI `phase2 demo-bundle checklist` 已补充一键验收清单，只读取 Demo Bundle 和验收摘要，输出 `examples/output/real-llm-demo-checklist.json`，用于演示前快速确认 `readyForDemo=true`。
- 输出统一 JSON 演示包、WorkflowRun 和 Artifact 记录。

未实现：

- 不新增真实 LLM 请求。
- 不读取或输出 API Key。
- 不执行命令、pytest、Notebook 或选手代码。
- 不启动容器、VM、Notebook kernel 或真实 Agent。
- 不自动发布实验、试题、评分规则或 PPT。

## 输入说明

- `--workflow-report`: 已有真实 LLM Demo Workflow Report，默认 `examples/output/mimo-real-demo-report.json`。
- `--lab`: 已有真实 Lab DSL。
- `--exam`: 已有真实 Exam DSL。
- `--grading`: 已有真实 Grading DSL。
- `--ppt`: 已有真实 PPT DSL。
- `--submission`: 本地提交目录，仅供只读沙箱检查。
- `--normalized-grading-output`: 归一化 Grading DSL 输出。
- `--precheck-output`: 真实沙箱前预检报告输出。
- `--readonly-report-output`: 只读沙箱报告输出。
- `--readonly-evidence-grading-output`: 只读 evidence 演示 Grading DSL 输出。
- `--readonly-evidence-report-output`: 只读 evidence 演示评分报告输出。
- `--candidate-preview-output`: 候选人预览输出。
- `--pptx-output`: PPTX Artifact 输出，默认 `examples/output/real-llm-demo-ppt-artifact.pptx`。
- `--pptx-manifest-output`: PPTX Artifact 构建摘要输出，默认 `examples/output/real-llm-demo-ppt-artifact-manifest.json`。
- `--pptx-preview-output`: PPTX Artifact 首页 PNG 预览输出，默认 `examples/output/real-llm-demo-ppt-artifact-slide-01.png`。
- `--output`: 演示包输出。

验收摘要命令输入：

- `--bundle`: 已生成的真实 Demo Bundle，默认 `examples/output/real-llm-demo-bundle.json`。
- `--output`: 演示闭环验收摘要输出，默认 `examples/output/real-llm-demo-acceptance-summary.json`。

一键验收清单命令输入：

- `--bundle`: 已生成的真实 Demo Bundle，默认 `examples/output/real-llm-demo-bundle.json`。
- `--acceptance-summary`: 已生成的演示闭环验收摘要，默认 `examples/output/real-llm-demo-acceptance-summary.json`。
- `--output`: 一键验收清单输出，默认 `examples/output/real-llm-demo-checklist.json`。

## 命令示例

```powershell
python lab_cli.py phase2 demo-bundle build --workflow-report examples/output/mimo-real-demo-report.json --lab examples/output/real-llm-lab.json --exam examples/output/real-llm-exam.json --grading examples/output/real-llm-grading.json --ppt examples/output/real-llm-ppt.json --submission examples/submissions/readonly-demo --readonly-evidence-grading-output examples/output/real-llm-demo-readonly-evidence-grading.json --readonly-evidence-report-output examples/output/real-llm-demo-readonly-evidence-report.json --pptx-output examples/output/real-llm-demo-ppt-artifact.pptx --pptx-manifest-output examples/output/real-llm-demo-ppt-artifact-manifest.json --pptx-preview-output examples/output/real-llm-demo-ppt-artifact-slide-01.png --output examples/output/real-llm-demo-bundle.json
```

读取演示包：

```powershell
python lab_cli.py phase2 demo-bundle report --file examples/output/real-llm-demo-bundle.json
```

生成演示闭环验收摘要：

```powershell
python lab_cli.py phase2 demo-bundle acceptance --bundle examples/output/real-llm-demo-bundle.json --output examples/output/real-llm-demo-acceptance-summary.json
```

生成一键验收清单：

```powershell
python lab_cli.py phase2 demo-bundle checklist --bundle examples/output/real-llm-demo-bundle.json --acceptance-summary examples/output/real-llm-demo-acceptance-summary.json --output examples/output/real-llm-demo-checklist.json
```

## 输出说明

关键字段：

```json
{
  "mode": "REAL_LLM_DEMO_REPLAY_AND_READONLY_SANDBOX_BUNDLE",
  "generatedDsl": {
    "lab": {"status": "WAITING_REVIEW", "schemaValidated": true},
    "exam": {"status": "WAITING_REVIEW", "schemaValidated": true},
    "grading": {"status": "WAITING_REVIEW", "schemaValidated": true},
    "ppt": {"status": "WAITING_REVIEW", "schemaValidated": true, "artifactGenerated": true}
  },
  "pptArtifact": {
    "kind": "PPTX_FILE",
    "status": "WAITING_REVIEW",
    "path": "examples/output/real-llm-demo-ppt-artifact.pptx",
    "previewPath": "examples/output/real-llm-demo-ppt-artifact-slide-01.png",
    "previewAvailable": true,
    "autoPublishAllowed": false,
    "realPublish": false
  },
  "candidatePreview": {
    "answersRemoved": true,
    "answerVisibleToCandidate": false
  },
  "readonlyEvidenceDemo": {
    "doesNotModifySourceGrading": true,
    "executionSummary": {"executed": 2, "deferred": 0},
    "score": {"earnedScore": 70},
    "reportDetail": {
      "source": "sandbox.grade_runner.build_grading_report_detail",
      "mode": "READONLY_REAL_SANDBOX_POC",
      "checkSummary": {"executed": 2, "deferred": 0},
      "readonlyEvidence": {"status": "COLLECTED", "collectedTotal": 2},
      "checkPlans[].readonlyEvidence.status": "COLLECTED",
      "sandboxExecutionRequest.mode": "REAL_SANDBOX_REQUIRED"
    },
    "safety": {"readonlyOnly": true, "contestantCodeExecuted": false}
  },
  "controlledDockerEvidenceDemo": {
    "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
    "planMode": "CONTROLLED_DOCKER_GRADING_PLAN",
    "sourceGradingPath": "examples/output/real-llm-grading.json",
    "gradingPath": "examples/output/mimo-real-demo-controlled-plan.json",
    "submissionPath": "examples/submissions/real-demo-controlled",
    "reportPath": "examples/output/mimo-real-demo-controlled-sandbox-report.json",
    "imageVerifyPath": "examples/output/grading-sandbox-image-verify.json",
    "image": {
      "tag": "ai-grading-python:0.1",
      "pytestAvailable": true,
      "networkEnabledForGrading": false
    },
    "checkSummary": {
      "total": 2,
      "executed": 2,
      "passed": 2,
      "byType": {"stdout_contains": 1, "pytest": 1}
    },
    "score": {"earnedScore": 40, "totalScore": 40},
    "safety": {
      "hostExecutionAllowed": false,
      "networkEnabled": false,
      "unknownShellExecuted": false,
      "autoApproveAllowed": false,
      "realPublish": false
    }
  },
  "coreBusinessDemoPath": {
    "component": "CoreBusinessDemoPath",
    "stepTotal": 6,
    "route": "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report",
    "manualReviewRequired": true,
    "pptPageReviewActionVisible": true,
    "autoPublishAllowed": false,
    "realPublish": false
  },
  "realDemoReviewQueue": {
    "component": "RealDemoReviewQueue",
    "taskTotal": 4,
    "waitingReviewTotal": 4,
    "schemaValidatedTotal": 4,
    "readonlyEvidenceCollectedTotal": 2,
    "answerVisibleToCandidate": false,
    "manualReviewRequired": true,
    "autoApproveAllowed": false,
    "realPublishAllowed": false
  },
  "realDemoAcceptanceSummary": {
    "mode": "REAL_LLM_DEMO_ACCEPTANCE_STATIC",
    "route": "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report",
    "signals": {
      "dslValidatedTotal": 4,
      "waitingReviewDslTotal": 4,
      "realDemoReviewQueueTaskTotal": 4,
      "mcpOutputContractIncludesRealDemoReviewQueue": true,
      "readonlyEvidenceCollectedTotal": 2,
      "readonlyEvidenceDemoEarnedScore": 70,
      "pptPageReviewActionVisible": true,
      "candidatePreviewAnswerSafe": true
    },
    "safety": {
      "newLlmRequestSent": false,
      "secretsRead": false,
      "networkAccess": false,
      "autoApproveAllowed": false,
      "batchStateChangeAllowed": false,
      "realPublishAllowed": false,
      "contestantCodeExecuted": false
    },
    "acceptance": {"passed": true, "passedCount": 6, "total": 6}
  },
  "safety": {
    "realLlmCalled": true,
    "newLlmRequestSent": false,
    "secretsRead": false,
    "contestantCodeExecuted": false,
    "realPublish": false,
    "pptxArtifactGenerated": true,
    "pptxArtifactAutoPublishAllowed": false
  }
}
```

注意：如果真实 Grading DSL 只有 `stdout_contains` 或 `pytest`，只读沙箱会如实返回 `deferred`，不会伪造成已经自动判分完成。`notebook_cell` 当前只支持静态 `.ipynb` JSON 解析 evidence，不启动 kernel、不执行 cell。

为便于第一版演示直接看到可执行评分证据，演示包会另外生成 `readonlyEvidenceDemo`。它是独立的只读 evidence Grading DSL，只检查演示提交目录里的 `result.csv` 和 `metrics.json`，不会覆盖、编辑或替换真实 LLM 生成的 Grading DSL。

`readonlyEvidenceDemo.reportDetail` 是演示闭环的评分报告解释层，来源为 `sandbox.grade_runner.build_grading_report_detail`。`real-demo.html` 用它说明 evidence 已采集，`grading-report.html` 用它承接 `/real-demo -> /grading/:id/report` 的报告入口。该层只展示 `file_exists` / `json_field` 的只读 evidence，不执行 Grading DSL 命令、不运行 pytest、不执行 Notebook、不执行选手代码，也不表示真实 Grading DSL 已被自动批准。

Phase 3 后续已增加 `grade sandbox-run --execution-mode controlled-command` 的最小 Docker 命令评分 PoC，可用于把真实 LLM 生成的 Grading DSL 中 `stdout_contains` / `pytest` 检查推进到受控容器执行。该路径不会新增 LLM 请求、不会读取密钥、不会自动发布，且 Docker 镜像必须本地存在；当前演示包默认仍使用只读 evidence demo。

当前静态演示页已把 `examples/output/mimo-real-demo-controlled-plan.json`、`examples/output/mimo-real-demo-controlled-sandbox-report.json` 和 `examples/output/grading-sandbox-image-verify.json` 作为 `controlledDockerEvidenceDemo` 展示出来。它只复放已经通过 CLI 生成的本地证据，用于说明真实 demo Grading DSL 的 `check_q1` / `check_q4` 子集可以在 `ai-grading-python:0.1` 受控镜像中执行，得分为 `40/40`；页面本身不启动 Docker、不运行命令、不发送新的 LLM 请求，也不改变 `CoreBusinessDemoPath.stepTotal=6` 的主闭环口径。

真实 demo Grading DSL 可通过 `grade controlled-plan` 生成受控 Docker 可执行子集：

```powershell
python lab_cli.py grade controlled-plan --grading examples/output/real-llm-grading.json --stdout-command "python main.py" --stdout-expected "Python 3.11" --pytest-path checks/check_main.py --output examples/output/mimo-real-demo-controlled-plan.json
python lab_cli.py grade sandbox-run --execution-mode controlled-command --grading examples/output/mimo-real-demo-controlled-plan.json --submission examples/submissions/real-demo-controlled --image ai-grading-python:0.1 --output examples/output/mimo-real-demo-controlled-sandbox-report.json
```

第一条命令只生成 `WAITING_REVIEW` Grading DSL，不执行容器；第二条命令才显式进入受控 Docker PoC。

`review-center.html` 的 `RealDemoReviewQueue` 是人工审核视图的演示入口，读取 `realDemoPrototype.generatedDsl`、`realDemoPrototype.coreBusinessDemoPath` 和 `realDemoPrototype.readonlyEvidenceDemo.reportDetail`。它只展示四类真实演示产物仍处于 `WAITING_REVIEW`，并提示 Grading 可查看只读 evidence，不能批量通过、自动通过或发布。

`review-center.html` 的 `ControlledDockerEvidenceReviewSignal` 读取 `realDemoPrototype.controlledDockerEvidenceDemo`，把受控 Docker PoC 证据直接展示在审核中心：`controlledPlanPath=examples/output/mimo-real-demo-controlled-plan.json`、`controlledReportPath=examples/output/mimo-real-demo-controlled-sandbox-report.json`、`coveredCheckIds=check_q1/check_q4`、`coveredCheckTypes=stdout_contains/pytest`、`executed=2`、`passed=2`、`earnedScore=40/40`。同一面板会明确显示 `remainingCheckIds=check_q2/check_q3`、`remainingCheckTypes=notebook_cell`、`remainingScore=60`、`remainingStatus=NEEDS_MANUAL_NOTEBOOK_REVIEW`，因此该证据只表示受控命令子集已通过，不代表整份 Grading DSL 可以自动批准。

`review-center.html` 的 `NotebookEvidenceReviewPlan` 读取 `realDemoPrototype.generatedDsl.grading.spec.assessmentPlan + reviewTaskSummary.controlledDockerEvidenceReviewSignal`，把 `check_q2` / `check_q3` 展开为 `STATIC_NOTEBOOK_PLAN_REVIEW_ONLY`：审核员需要确认 Notebook cell 目标、期望输出 token、Notebook 执行必须进入沙箱，以及当前没有启动 Notebook kernel。该计划固定 `notebookKernelStarted=false`、`notebookExecuted=false`、`contestantCodeExecuted=false`、`realPublishAllowed=false`。

当前已补充 Notebook 静态 evidence 演示计划与报告：

```powershell
python lab_cli.py grade sandbox-run --grading examples/output/mimo-real-demo-notebook-static-plan.json --submission examples/submissions/real-demo-notebook --output examples/output/mimo-real-demo-notebook-static-report.json
```

该报告覆盖 `check_q2/check_q3`，`executionSummary.executed=2`、`score.earnedScore=60/60`，`readonlyEvidence.method=STATIC_NOTEBOOK_JSON_PARSE`，并固定 `notebookKernelStarted=false`、`notebookExecuted=false`、`contestantCodeExecuted=false`。

`phase2 demo-bundle acceptance` 是本地验收摘要命令。它会读取演示包、`frontend/mock-data.json` 和 `mcp-server/tools.manifest.json`，核对真实演示页、审核中心、MCP `get_review_task_summary` 合同、评分报告明细和 PPT 页级审核动作是否形成闭环。该命令不会重新生成内容、不会发送新的 LLM 请求、不会读取密钥、不会访问网络，也不会执行命令、pytest、Notebook 或选手代码。

`phase2 demo-bundle checklist` 是本地一键验收清单命令。它只读取指定的 demo bundle 和 acceptance summary，输出 `RealDemoOneClickChecklist`，包含 `readyForDemo=true`、`acceptance=7/7`、`sections=6/6`、`gradingEvidenceCoverage=100/100` 和只读安全边界；清单内的 `safeCommands` 会使用本次命令实际传入的 `--bundle` / `--acceptance-summary` / `--output` 路径，避免自定义演示文件名时回退到默认 `mimo-real-demo-*`。它不是新增门禁，不重新发送 LLM 请求，不读取密钥，不运行 Docker/pytest/Notebook，也不执行选手代码。

`real-demo.html` 的 `RealDemoAcceptanceSummary` 面板读取 `realDemoPrototype.realDemoAcceptanceSummary`，用于把 `examples/output/real-llm-demo-acceptance-summary.json` 可视化到演示首屏流程中。它显示 `acceptance.passed=true`、`passedCount=7`、`failedStepIds=[]`、`mcpOutputContractIncludesRealDemoReviewQueue=true`、`readonlyEvidenceCollectedTotal=2`、`gradingEvidenceCoverage=100/100` 和 `batchStateChangeAllowed=false`，只作为演示证据索引，不触发命令执行。

`real-demo.html` 的 `RealDemoOneClickChecklist` 面板读取 `realDemoPrototype.oneClickDemoChecklist`，用于演示前一屏确认：四类 DSL 均 `WAITING_REVIEW`、候选人预览安全、Grading evidence coverage `100/100`、PPTX Artifact 仍需审核、Review/MCP 合同可见、安全边界关闭。该面板只展示 `examples/output/real-llm-demo-checklist.json` 的静态摘要。

`review real-dsl-preview` 是本地真实 DSL 审核预览命令。它读取 `real-llm-lab.json`、`real-llm-exam.json`、`real-llm-grading.json`、`real-llm-ppt.json` 和 `real-llm-demo-candidate-preview.json`，确定性生成 `examples/output/real-llm-demo-real-dsl-review-preview.json`；它不新增 LLM 请求、不读取密钥、不执行命令、不创建任务、不发布。

```powershell
python lab_cli.py review real-dsl-preview --output examples/output/real-llm-demo-real-dsl-review-preview.json
```

`real-demo.html` 和 `review-center.html` 的 `RealDslReviewPreview` 面板读取 `realDemoPrototype.realDslReviewPreview` 和 `examples/output/real-llm-demo-real-dsl-review-preview.json`，用于把真实 DSL 从“路径可见”提升到“内容可审”：展示 `real-llm-lab.json` 的 4 个实验步骤、`real-llm-demo-candidate-preview.json` 的 4 道候选人安全题面、`real-llm-exam.json` 中仅教师审核可见的 `gradingRef`、`real-llm-grading.json` 的 4 条 assessmentPlan/checks，以及 `real-llm-ppt.json` 的 5 页 PPT 大纲。该面板固定 `gradingRefVisibleToCandidate=false`、`teacherOnlyGradingRefVisibleInReview=true`、`commandExecutedFromPage=false`、`realSandboxRunEnabled=false`、`autoApproveAllowed=false`。

`operations-presenter.html` 的 `RealDemoAcceptanceSummary` 面板读取 `operationsPresenterPrototype.realDemoAcceptanceSummarySignal`，用于讲解闭环摘要。`operations-signoff.html` 的 `RealDemoAcceptanceSummary 签收` 面板读取 `operationsSignoffPrototype.realDemoAcceptanceSummarySignoff`，用于签收闭环摘要。二者都显示 `passedCount=7`、`failedStepIds=[]`、`mcpOutputContractIncludesRealDemoReviewQueue=true`、`readonlyEvidenceCollectedTotal=2`、`gradingEvidenceCoverage=100/100`、`newLlmRequestSent=false`、`batchStateChangeAllowed=false` 和 `realPublishAllowed=false`，不执行命令、不上传、不触发发布。

`gradingEvidenceCoverage` 是演示证据覆盖摘要，不是自动审批结果：受控 Docker 覆盖 `check_q1/check_q4` 的 `40/40`，Notebook 静态解析覆盖 `check_q2/check_q3` 的 `60/60`，合计 `100/100`。该摘要固定 `manualReviewRequired=true`、`autoApproveAllowed=false`、`realPublishAllowed=false`。

## 测试方式

```powershell
python -m pytest tests/test_cli.py
python -m pytest
```

## 限制说明

- 该命令用于演示收口，不替代真实 LLM 生成命令。
- 该命令只复放已有真实产物；如果要重新生成 Lab / Exam / Grading / PPT，需要运行 `phase2 workflow run --provider-mode real-llm-demo`。
- 只读沙箱不是完整自动评分沙箱；完整评分仍需后续容器执行器支持命令、pytest 和 Notebook。
- `readonlyEvidenceDemo` 只服务第一版演示证据展示，不能替代完整评分规则验收。
- `controlledDockerEvidenceDemo` 只展示本地受控 Docker PoC 证据，不代表真实业务 Grading DSL 已自动批准；审核通过前不得发布。
- `ControlledDockerEvidenceReviewSignal` 只在审核中心展示 evidence 覆盖情况，不运行 Docker、不执行 pytest、不发送新的 LLM 请求；Notebook 缺口仍需人工复核。
- `NotebookEvidenceReviewPlan` 只展示 Notebook 缺口的审核计划，不启动 Notebook kernel、不执行 cell、不执行选手代码。
- `phase2 demo-bundle acceptance` 只证明演示闭环证据可见、可追溯、未绕过人工审核；它不代表真实业务已完成发布验收，也不替代后续容器沙箱和运营签收。
- `phase2 demo-bundle checklist` 只把已有演示证据折叠成一屏清单，不新增审批门禁，不触发真实 SDK、真实 LLM、真实沙箱或发布动作。
- PPTX Artifact 是本地课件附件 PoC，当前验证可打开和可审核；尚未做逐页渲染预览和高质量模板 QA。
- `CoreBusinessDemoPath` 已接入 `real-demo.html`、`review-center.html`、`operations-presenter.html` 和 `operations-signoff.html`，用于让演示入口、审核中心、运营讲解和签收提示同源；`readonlyEvidenceDemo.reportDetail` 已接入 `real-demo.html`、`review-center.html` 和 `grading-report.html`，用于让只读评分 evidence 可解释、可追溯；它们不代表自动审批流，每一步仍需人工审核后才能进入真实发布。
- 演示包内的真实 LLM 内容仍必须人工审核，审核通过前不得发布。

## 下一步

- 将受控 Docker evidence 从演示摘要推进到真实 Grading DSL 的可选评分路径：保持人工审核前不发布，优先支持 `stdout_contains` / `pytest` 的最小业务闭环。

建议智能模式：GPT-5.5 高智能模式。
