# sandbox

Phase 1 / Phase 3 Sandbox 安全契约、Mock Executor 和只读沙箱 PoC 目录。默认不执行选手代码、不执行未知 Shell；Mock runner 只把已经通过 Schema 校验的 Grading DSL 转成确定性 Mock 评分报告。只读沙箱 PoC 仅检查显式提交目录内的低风险文件类评分项。

## 输入说明

- `sandbox.contract.json`: Phase 1 沙箱安全契约。
- `execution-contract.json`: 未来真实沙箱执行请求/结果契约，当前为 `CONTRACT_ONLY`，只定义边界，不启动容器。
- `execution_contract.py`: 从 Grading check 构造未来沙箱执行请求和未执行结果占位，不执行命令、Notebook 或选手代码。
- `container-executor.contract.json`: 容器沙箱 dry-run 适配器契约，声明 `CONTAINER_PLAN_ONLY` 输出字段和安全断言。
- `container_executor.py`: `ContainerSandboxExecutor`，把 `REAL_SANDBOX_REQUIRED` 请求转换成容器执行计划，不调用 Docker、Podman、Kubernetes、Shell 或 Notebook kernel。
- `readonly_sandbox_executor.py`: 只读沙箱 PoC，支持 `file_exists`、`json_field`、静态 `notebook_cell` 和 `log_keyword`，只读取 `--submission` 指定目录内文件；不执行命令、pytest、Notebook kernel 或选手代码，并复用 `grade_runner` 的 `reportDetail` / `checkPlans` 字段作为报告页统一输入。
- `controlled_command_executor.py`: 受控 Docker 命令沙箱 PoC，支持显式 `stdout_contains` 和 `pytest`，只运行 allowlist Python 命令；提交目录以只读方式挂载到容器，网络关闭，不自动 pull 镜像，不执行 Notebook、未知 Shell 或真实发布。
- `evidence_merge.py`: 评分 evidence 合并器，只读取已有只读沙箱 / 受控 Docker 评分报告，按 check id 合并 evidence 和分值，不启动沙箱、不执行命令、不读取 submission。
- `grade controlled-plan`: CLI 计划生成命令，从已有 Grading DSL 中提取受控 Docker 可执行的 `stdout_contains` / `pytest` 子集，并补齐执行参数；它只输出新的 `WAITING_REVIEW` Grading DSL，不启动 Docker。
- `images/python-pytest/Dockerfile`: 固定 Python + pytest 评分镜像基线，默认 tag 为 `ai-grading-python:0.1`。
- `grade-runner.contract.json`: Phase 3 评分器接口 Mock 契约，包含 `gradingReport` 与 `reportDetail` 的输出字段清单。
- `grade_runner.py`: `GradingRunner` 和 `MockCheckExecutor`，支持 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类评分项的只读计划。
- `real_sandbox_precheck.py`: 真实沙箱前评分计划预检，复用 `GradingRunner` 报告检查 assessmentPlan、sandboxExecutionRequest、containerSandboxPlan 和限制字段是否足够清楚；不执行真实沙箱。
- `mock_executor.py`: `MockSandboxExecutor`，用于生成 Mock 评分报告，并暴露评分审计 detail 与 `reportDetail` 构造函数。
- 输入 Grading DSL 必须先通过 `templates/grading/grading.schema.json` 校验。
- 输入 Grading DSL 的 `spec.assessmentPlan` 会作为评分计划来源写入报告的 `assessmentPlanSummary` 和每个 `checkPlan` 的 `assessmentPlan*` 追溯字段，便于把审核页看到的计划与沙箱报告对齐。
- 混合评分示例：`templates/grading/examples/mixed-checks.yaml`。

## 输出说明

Mock 评分报告会包含：

```json
{
  "mode": "MOCK_ONLY",
  "phase": "Phase 3",
  "passed": true,
  "runner": {
    "id": "mock_grading_runner"
  },
  "sandboxPolicy": {
    "executorBoundary": "SandboxExecutor",
    "hostExecutionAllowed": false,
    "realSandboxRunEnabled": false,
    "filesystemIsolationRequired": true
  },
  "checkSummary": {
    "executed": 0,
    "plannedOnly": 6
  },
  "assessmentPlanSummary": {
    "source": "grading.spec.assessmentPlan",
    "alignedWithChecks": true,
    "planTotal": 6
  },
  "explainability": {
    "status": "EXPLAINABLE_MOCK_PLAN",
    "assessmentPlanAlignedWithChecks": true,
    "realSandboxEvidenceRequired": true
  },
  "sandboxExecuted": false,
  "contestantCodeExecuted": false,
  "commandExecuted": false,
  "checks": []
}
```

每个 check 也会标记：

```json
{
  "sandboxExecuted": false,
  "contestantCodeExecuted": false,
  "commandExecuted": false,
  "executionPlan": {
    "strategy": "MOCK_PLAN_ONLY"
  },
  "sandboxExecutionRequest": {
    "mode": "REAL_SANDBOX_REQUIRED"
  },
  "containerSandboxPlan": {
    "mode": "CONTAINER_PLAN_ONLY",
    "status": "PLANNED"
  },
  "inputSummary": {},
  "mockEvidence": {
    "status": "MOCK_EVIDENCE_NOT_COLLECTED"
  },
  "riskLevel": "LOW",
  "assessmentPlanSource": "grading.spec.assessmentPlan",
  "assessmentPlanSourceField": "spec.assessmentPlan[checkId=check_result_file]",
  "assessmentPlanAlignedWithCheck": true,
  "logs": []
}
```

`MOCK_GRADING_RUN` 操作审计的 `detail` 会复用评分报告中的 runner、checkSummary 和 checkPlans，并固定记录：

```json
{
  "blockedActions": ["realSandboxRun", "executeGradingCommand", "runRealPytest"],
  "runRealPytestEnabled": false,
  "hostExecutionAllowed": false
}
```

Backend 和前端页面使用的 `reportDetail` 也应来自 `sandbox.grade_runner.build_grading_report_detail`。它是评分报告明细的单一来源，负责统一输出 `sandboxPolicy`、`explainability`、`checkPlans[].inputSummary`、`checkPlans[].mockEvidence`、`executionPlan.requiredLimits`、`sandboxExecutionRequest`、`containerSandboxPlan`、安全摘要和审计摘要，避免后端或前端重新手写一套同义字段。

真实沙箱前预检报告来自 `sandbox.real_sandbox_precheck.build_real_sandbox_precheck_report`，顶层固定包含：

```json
{
  "mode": "REAL_SANDBOX_PRECHECK_ONLY",
  "readiness": {
    "status": "READY_FOR_MANUAL_SANDBOX_REVIEW",
    "readyForRealSandboxImplementation": true,
    "readyForRealSandboxExecution": false
  },
  "safety": {
    "sandboxExecuted": false,
    "contestantCodeExecuted": false,
    "commandExecuted": false
  }
}
```

其中 `readyForRealSandboxImplementation=true` 只表示评分计划可进入真实沙箱实现评审；`readyForRealSandboxExecution=false` 固定为 false，不能解释为已经授权或执行真实评分。

`execution-contract.json` 与 `sandbox.execution_contract` 定义未来真实容器执行器的输入/输出边界：

- `build_sandbox_execution_request`: 为每个 check 生成 `REAL_SANDBOX_REQUIRED` 请求，包含 isolated workspace、CPU/内存/超时/进程/网络限制、action 和必须采集的 evidence。
- `build_sandbox_result_placeholder`: 生成 `RESULT_PLACEHOLDER`，固定 `sandboxExecuted=false`、`contestantCodeExecuted=false`、`commandExecuted=false`，错误码为 `REAL_SANDBOX_NOT_IMPLEMENTED`。
- 当前不会调用 Docker、Podman、Kubernetes、Shell、Notebook kernel 或任何真实评分命令。

`container-executor.contract.json` 与 `sandbox.container_executor` 定义容器执行器的 dry-run 计划适配层：

- `ContainerSandboxExecutor.plan`: 校验 `REAL_SANDBOX_REQUIRED` 请求，并返回 `CONTAINER_PLAN_ONLY` 计划。
- `build_container_sandbox_plan`: 函数式入口，便于 CLI、Backend 或未来 MCP 复用。
- 输出包含 `containerPlan.image`、`workingDirectory`、只读 submission mount、CPU/内存/超时/网络限制、`commandPreview`、`evidenceRequired` 和 `resultPlaceholder`。
- 安全摘要固定 `containerStarted=false`、`sandboxExecuted=false`、`contestantCodeExecuted=false`、`commandExecuted=false`。
- 当前只验证计划形状，不启动容器；后续真实容器实现应复用同一请求契约和 evidence 字段。
- `GradingRunner` 会把每个 check 的 `sandboxExecutionRequest` 与 `containerSandboxPlan` 写入 `report.checks[]`、`reportDetail.checkPlans[]` 和 `MOCK_GRADING_RUN.detail.checkPlans[]`，用于审核页和审计页展示未来真实沙箱执行边界。

`readonly_sandbox_executor.py` 是当前最小真实沙箱 PoC：

- 支持 `file_exists`：检查提交目录内相对路径文件是否存在。
- 支持 `json_field`：读取提交目录内 JSON 文件，并用 `$.field` / `$.items[0].field` 形式路径比较 `expectedValue`。
- 支持 `notebook_cell` 静态解析：只读取 `.ipynb` JSON，拼接指定 cell 的 `source` 和已有 `outputs` 文本后匹配 `expected` token；不启动 kernel、不执行 cell。
- 支持 `log_keyword` 静态扫描：只读取提交目录内 UTF-8 文本日志并匹配 `expected` token；不执行日志生成命令。
- 其它类型如 `stdout_contains`、`pytest` 返回 `DEFERRED`，不执行。
- 所有路径必须是相对路径，且解析后必须位于 `--submission` 目录内；绝对路径或 `..` 逃逸会返回失败 evidence，不读取外部文件。
- 输出 `READONLY_REAL_SANDBOX_POC` 报告，`sandboxExecuted=true` 表示只读文件检查已执行；`contestantCodeExecuted=false`、`commandExecuted=false`、`networkEnabled=false` 固定保持。
- 报告顶层包含 `checkSummary`、`assessmentPlanSummary`、`explainability` 和 `reportDetail`，其中 `reportDetail.source=sandbox.grade_runner.build_grading_report_detail`，`checkPlans[].readonlyEvidence` 保存实际只读证据，`checkPlans[].mockEvidence` 继续表示 Grading DSL 计划中的 Mock 证据占位。

`controlled_command_executor.py` 是命令类评分的最小 Docker PoC：

- `grade controlled-plan` 可先把真实 LLM 生成的 Grading DSL 转成受控 Docker 可执行子集。例如从 `examples/output/mimo-real-demo-grading.json` 提取 `check_q1` / `check_q4`，补齐 `python main.py`、期望输出和 pytest 路径，输出 `examples/output/mimo-real-demo-controlled-plan.json`。该输出仍为 `WAITING_REVIEW`，需要人工确认后再执行。命令返回的 `executionCoverage` 会同时标出 `controlledDocker`、`readonlyStatic` 和 `deferred` 三类评分项：`stdout_contains` / `pytest` 进入受控 Docker plan，`file_exists` / `json_field` / 静态 `notebook_cell` / `log_keyword` 继续走只读静态 evidence，剩余类型才进入 deferred。
- 支持 `stdout_contains`：在 Docker 容器中运行 `python ...` / `python3 ...` 命令并匹配 stdout token。
- 支持 `pytest`：在 Docker 容器中运行 `python -m pytest <path>`，根据退出码判定通过；stdout / stderr / exitCode / durationMs 写入 evidence。
- Docker 运行参数固定包含 `--network none`、只读 submission mount、`--read-only`、CPU/内存/PID 限制和临时 `/tmp`。
- 报告新增 `isolation` 摘要，机器可读地记录 submission 只读挂载、容器工作目录、网络关闭、只读 rootfs、`/tmp` tmpfs、CPU/内存/PID/超时限制和 stdout/stderr 输出捕获策略；同一摘要会进入 CLI / Backend 的 `operationAuditEvent.detail`、`artifact.metadata` 和 `reportDetail`。
- 报告新增 `isolationQuality` 派生摘要，汇总 `network_disabled`、`submission_mount_readonly`、`rootfs_readonly`、`resource_limits_present`、`output_captured_by_runner`、`local_image_inspected` 和 `registry_network_not_used` 等检查，输出 `qualityState`、`readyForLocalControlledEvidence`、`criticalIsolationReady` 和 `manualImageReviewRequired`；它只用于本地人工复核和 evidence 质量判断，不是新的执行授权门禁。
- 报告新增 `executionProfile`，固定记录 `local-python-pytest-controlled-v1` 的允许 check 类型、Python/pytest 入口、网络、只读挂载、tmpfs、CPU/内存/PID/超时、输出捕获和禁止的宿主机/镜像拉取/自动审核边界；每个已启动 check 的 `isolation` 也会带同一 profile ID 与资源限制。
- 报告新增 `imageSupplyChain` 摘要，记录 `docker image inspect` 得到的本地 `imageId` / digest、repo tags、创建时间、Dockerfile OCI/profile labels、`ai-grading-python:` / `local-python:` / `python:` allowlist 匹配结果、`automaticPullDisabled=true`、`registryAuthUsed=false`、`productionRegistryUsed=false` 和 `networkAccessForPull=false`；同一摘要会进入 CLI / Backend 的 `operationAuditEvent.detail`、`artifact.metadata`、`reportDetail`、`runner`、`sandboxPolicy` 和 `isolation`。
- 默认镜像是 `ai-grading-python:0.1`，但命令不会自动拉取镜像；Docker 不可用时返回 `DOCKER_RUNTIME_UNAVAILABLE`，本地镜像不存在时返回 `SANDBOX_IMAGE_MISSING`，两个错误都附带下一步本地修复提示且不会降级到宿主机。当前 allowlist 为本地 PoC 审计模式，未匹配镜像会标记为 `UNMATCHED_AUDIT_ONLY`，不会自动拉取、登录 registry 或访问生产镜像仓库。
- 不允许 shell 操作符、绝对路径或 `..` 逃逸；只接受可解析的 Python 命令，不执行 Notebook、任意 Shell、网络访问或真实发布。
- 路径逃逸、缺少 pytest 文件等容器启动前失败会返回 check 级 `status=FAILED`，但 `sandboxExecuted=false`、`contestantCodeExecuted=false`、`commandExecuted=false`，避免把配置错误误报成已经执行选手代码；命令超时会标记为容器已尝试执行。
- 输出 `CONTROLLED_DOCKER_SANDBOX_POC` 报告，`contestantCodeExecuted=true` 表示选手提交代码已经在 Docker 受控环境中运行；不代表宿主机执行或生产评分。
- 当前停止线：受控命令沙箱第一版只证明 `stdout_contains` / `pytest` 的安全样例、失败样例、超时、只读输入、输出隔离、镜像供应链审计和报告透传。后续进入评分任务队列、结果入库和真实平台复核时，复用该报告字段，不再新增同义的沙箱门禁或禁用壳。

`evidence_merge.py` 是评分证据合并器：

- `grade evidence-merge` 输入一到多份已有评分报告 JSON，优先读取 `reportDetail.checkPlans`，否则读取顶层 `checks`。
- 合并时按 `check.id` 去重，优先选择已执行 evidence；同一 check 同时出现只读 evidence 和受控 Docker evidence 时，受控 Docker evidence 排序更高。
- 输出 `GRADING_EVIDENCE_MERGE_REPORT`，包含 `summary`、`evidenceCoverage`、`checks`、`mergeWarnings` 和合并后的 `safety`。
- 可选 `--task-id <grading-task-id>` 会把合并报告 Artifact 归属到对应 Grading 审核任务，`review detail` 会在 `mergedGradingEvidence` 中展示覆盖率和安全摘要。
- 该命令只读本地 JSON 文件，不接收 `--submission`、不接收 `--image`、不启动 Docker、不运行 pytest、不执行 Notebook、不调用真实 LLM、不自动通过或发布；`manualReviewRequired=true` 和 `autoApproveAllowed=false` 固定保留。

`evidence_readiness.py` 是评分证据就绪摘要器：

- `grade evidence-readiness` 输入一到多份已有评分 evidence 报告，读取 `checkEvidenceReviewItems`、`checks` 或 `reportDetail.checkPlans`。
- 输出 `GRADING_EVIDENCE_READINESS`，包含 `summary`、check 级 `items`、`nextActions` 和只读安全声明。
- 摘要会标出每个 check 是否已有 evidence、来源是只读静态 evidence / 受控 Docker evidence / 合并 evidence，以及缺失时建议运行 `readonly_static_evidence`、`controlled_command_evidence` 或进入人工复核。
- 该命令只读已有报告，不创建评分任务、不写 Artifact、不启动 Docker、不运行 pytest、不执行 Notebook、不执行选手代码、不调用真实 LLM、不自动通过或发布。

`evidence_auto.py` 是评分 evidence 自动编排器：

- `grade evidence-auto` 总是先生成只读 evidence，再按 `--include-controlled-command` 显式选择是否运行受控 Docker command evidence，最后合并为 `GRADING_EVIDENCE_AUTO_REPORT`。
- 报告包含 `executionMatrix`、`nextCoreAction` 和 `manualReviewChecklist`。其中 `manualReviewChecklist.items[]` 会把每个 check 映射成 `recommendedReviewAction`、`recommendedDecision`、`readyForDecision` 和 evidence 模式；`decisionNoteRecommendation` 给出本轮人工审核建议记录 `approve-ready`、`needs-evidence` 或 `needs-revision`。
- 报告包含 `scorePreview`，只根据 `executionMatrix.selectedEvidence` 中已采集的 evidence 汇总 `earnedScore`、`totalScore`、`coveredScore`、`missingScore`、`coverageRatio`、`passRate` 和 `readyForDecisionNote`。它用于人工复核分数，不会触发自动通过。
- 报告包含 `gradingDslCoverageSummary`，把 Grading DSL 的 checks 与已采集 evidence 对齐，输出 `dslCheckTotal`、`evidenceReadyTotal`、`missingEvidenceTotal`、受控命令缺口、静态 evidence 缺口、`missingCheckIds`、`nextCoreActionId` 和 `decisionNoteRecommendation`，便于审核页和 Agent 演示直接解释“为什么能或不能记录 approve-ready”。
- 报告包含 `reviewerSafetySummary`，把 `scorePreview`、`executionMatrix`、`manualReviewChecklist` 和受控 Docker safety 信号折成审核员可读状态：是否已可人工记录 `approve-ready`、还缺哪些 evidence、下一条人工动作、是否曾在受控容器中执行选手代码、网络/宿主机/自动发布边界。`controlledExecutionProfile` 与 `controlledExecutionDiagnostic` 同时保留已采集、未请求、Docker 不可用或镜像缺失的统一证据与诊断；它们只读派生，不新增门禁、不自动审核、不改变 evidence 收集策略。
- 该清单只服务人工审核和评分报告页展示，固定 `manualReviewRequired=true`、`autoApproveAllowed=false`、`autoPublishAllowed=false`、`realPublishAllowed=false`，不触发自动通过或发布。

`grade-runner.contract.json.reportDetailContract` 会机器可测地声明：

- `requiredTopLevelFields`: `reportDetail` 顶层字段。
- `scoreFields`、`safetyFields`、`auditFields`: 前后端可直接展示的摘要字段。
- `checkPlanFields`: 每个评分计划必须包含的输入摘要、执行计划、沙箱执行请求、容器 dry-run 计划、Mock 证据、风险等级和执行安全标记。
- `assessmentPlanTrace`: 声明 `spec.assessmentPlan` 到 `reportDetail.checkPlans` 的追溯字段，要求每个 checkPlan 能说明来源、对齐状态、计划执行限制和 Mock 证据。
- `safetyAssertions`: Mock 阶段固定为不执行真实沙箱、不执行命令、不执行选手代码。

## 命令示例

```powershell
python lab_cli.py grade run --grading templates/grading/examples/python-pytest.yaml
python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-grading-report.json
python lab_cli.py grade sandbox-precheck --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-real-sandbox-precheck.json
python lab_cli.py grade sandbox-run --grading templates/grading/examples/readonly-sandbox.yaml --submission examples/submissions/readonly-demo --output examples/output/readonly-sandbox-report.json
python lab_cli.py grade sandbox-run --grading examples/output/mimo-real-demo-notebook-static-plan.json --submission examples/submissions/real-demo-notebook --output examples/output/mimo-real-demo-notebook-static-report.json
python lab_cli.py grade sandbox-image build
python lab_cli.py grade sandbox-image verify --output examples/output/grading-sandbox-image-verify.json
python lab_cli.py grade sandbox-run --execution-mode controlled-command --grading templates/grading/examples/controlled-command-sandbox.yaml --submission examples/submissions/controlled-command-demo --image ai-grading-python:0.1 --output examples/output/controlled-command-sandbox-report.json
python lab_cli.py grade evidence-merge --report examples/output/readonly-sandbox-report.json --report examples/output/controlled-command-sandbox-report.json --output examples/output/merged-evidence-report.json --task-id <grading-task-id>
python lab_cli.py grade evidence-readiness --report examples/output/merged-evidence-report.json --output examples/output/grading-evidence-readiness.json
python lab_cli.py grade evidence-auto --grading templates/grading/examples/controlled-command-sandbox.yaml --submission examples/submissions/controlled-command-demo --output examples/output/grading-evidence-auto-controlled.json --include-controlled-command --image ai-grading-python:0.1
python -m pytest tests/test_sandbox_mock_executor.py
python -m pytest tests/test_readonly_sandbox_executor.py
python -m pytest tests/test_controlled_command_sandbox_executor.py
python -m pytest tests/test_sandbox_execution_contract.py
python -m pytest tests/test_container_sandbox_executor.py
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- 不执行选手代码。
- 不执行 Grading DSL 中的命令。
- 不运行 pytest。
- 默认 `grade run` 和 `grade sandbox-run --execution-mode readonly` 不执行选手代码。
- `grade sandbox-run --execution-mode controlled-command` 会在本地 Docker 容器中执行 allowlist Python 命令和 pytest；该路径必须显式选择，并且不会自动拉取镜像。
- 不执行 Notebook cell。
- Mock runner 不做真实文件存在性检查。
- Mock runner 不读取真实 JSON 文件。
- 只读沙箱 PoC 仅在 `--submission` 指定目录内读取 `file_exists` / `json_field` 所需文件，禁止绝对路径和目录逃逸。
- 受控 Docker 命令 PoC 仅支持 `stdout_contains` / `pytest`，禁止未知 shell 操作符、绝对路径和目录逃逸，网络固定关闭。
- 受控 Docker 报告中的 `isolation` / `isolationQuality` / `imageSupplyChain` 是本地 PoC 的审计证据摘要，不等同于生产级容器编排、镜像签名强校验、租户隔离或平台持久化；生产化仍需任务队列、资源清理、真实镜像仓库策略和后端入库。
- 不读取真实日志文件。
- 不打开网络。
- 不访问宿主机敏感路径。
- 不创建真实容器或 VM。
- `real_sandbox_precheck.py` 只生成真实沙箱前计划预检报告；它不是执行器、不是授权开关、不会启动容器。
- `execution_contract.py` 只产出请求/结果数据模型，不执行该请求。
- `container_executor.py` 只产出容器计划，不启动容器、不调用 Docker/Podman/Kubernetes、不执行 commandPreview。
- 不产生日志中的密钥输出。
- 后续进入真实沙箱时，应优先替换 `SandboxExecutor` 实现，并按 `sandboxPolicy` 收集 stdout、stderr、exitCode、durationMs、matchedEvidence 和 auditLogRef；不要再新增同义禁用壳。
