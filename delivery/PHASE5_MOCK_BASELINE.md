# Phase 5 Mock Baseline Freeze

本文件用于在接入真实 LLM 之前冻结当前 Mock 基线。它不是 Provider 接入实现，不读取密钥，不访问网络，不启动真实 MCP Server、真实 Agent、真实 HTTP 服务或真实云资源。

## 阶段收尾

R25 作为 Mock 门禁收口点：此前所有真实 SDK 相关模型均为安装前、调用前的禁用门禁，不再继续追加同类“安装前禁用壳”步骤。下一阶段从真实 SDK 依赖声明、SDK 安装验证、环境变量存在性边界开始；该边界只允许本地只读检查，不授权真实 LLM 调用。

## 输入说明

- `README.md`: 当前项目能力、阶段边界和快速验证入口。
- `docs/AI_PLATFORM_CODEX_FULL_GUIDE.md`: 项目总控顺序和安全红线。
- `docs/08_TESTING_AND_ACCEPTANCE.md`: 当前测试与验收标准。
- `docs/10_OPERATIONS_GUIDE.md`: 运营使用与交付说明。
- `delivery/phase1-delivery-index.json`: 本地交付入口索引。
- `config/delivery-package.contract.json`: 交付包导出契约。
- `delivery/FINAL_SIGNOFF.md`: 最终运营签收包。
- `delivery/OPERATIONS_MANUAL.md`: Phase 5 运营手册。
- `skills/operations-skill-pack/SKILL.md`: 运营 Skill 包。
- `delivery/STANDALONE_AGENT_DELIVERY.md`: 独立智能体 Mock 交付说明。
- `delivery/ACCESS_ENTRYPOINTS.md`: IP + 端口访问入口 Mock 说明。
- `providers/PHASE2_PROVIDER_PLAN.md`: Phase 2 Provider 接入规划。
- `providers/provider-adapter.contract.json`: Provider Adapter Mock 契约。
- `providers/provider-runtime-guard.contract.json`: 真实 Provider PoC 前运行时护栏契约。
- `providers/provider_runtime_guard.py`: 运行时护栏实现，检查 timeout、retry、concurrency、脱敏、Schema、审计和审核门禁。
- `providers/real-llm-poc-adapter.contract.json`: 真实 LLM PoC Adapter 禁用契约。
- `providers/real_llm_poc_adapter.py`: 真实 LLM PoC Adapter 禁用外壳，只串联本地门禁，不调用真实 SDK。
- `providers/real-llm-dry-run-plan.contract.json`: 真实 LLM dry-run 计划契约。
- `providers/real_llm_dry_run_plan.py`: 真实 LLM dry-run 计划生成器，只输出本地计划，不检查密钥是否存在，不创建 AI Task。
- `providers/real-llm-approval-gate.contract.json`: 真实 LLM SDK 批准门禁契约。
- `providers/real_llm_approval_gate.py`: 真实 LLM SDK 批准门禁实现，只检查审批编号、审核人和确认项，不授权真实调用。
- `providers/real-llm-sdk-task-blueprint.contract.json`: 真实 LLM SDK 任务蓝图契约。
- `providers/real_llm_sdk_task_blueprint.py`: 真实 LLM SDK 任务蓝图实现，只输出未来实施范围、拟改文件、测试矩阵、回滚计划和阻断条件。
- `providers/real-provider-sdk-poc.contract.json`: 真实 Provider SDK PoC harness 契约。
- `providers/real_provider_sdk_poc.py`: 真实 Provider SDK PoC harness，实现“蓝图通过后仍停在禁用门禁”的本地检查。
- `providers/real-sdk-dependency-env-gate.contract.json`: 真实 SDK 依赖与环境变量门禁契约。
- `providers/real_sdk_dependency_env_gate.py`: 真实 SDK 依赖与环境变量门禁实现，只评审未来 SDK 依赖和 env 任务，不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-install-plan.contract.json`: 真实 SDK 依赖安装计划草案契约。
- `providers/real_sdk_dependency_installer_audit.py`: 真实 SDK 依赖安装执行审计器禁用壳，`describe/audit` 只返回审计清单和阻断条件。
- `providers/real-sdk-dependency-installer-audit.contract.json`: 真实 SDK 依赖安装执行审计契约。
- `providers/real_sdk_dependency_install_plan.py`: 真实 SDK 依赖安装计划草案实现，只评审未来安装任务，不生成安装命令、不解析包版本或 hash、不修改 lockfile。
- `providers/real-sdk-dependency-installer-audit.contract.json`: 真实 SDK 依赖安装执行审计契约。
- `providers/real_sdk_dependency_installer_audit.py`: 真实 SDK 依赖安装执行审计器禁用壳，只评审未来安装执行壳，不物化命令、不安装 SDK、不修改依赖文件。
- `providers/real-sdk-dependency-change-preview.contract.json`: 真实 SDK 依赖变更预览契约。
- `providers/real_sdk_dependency_change_preview.py`: 真实 SDK 依赖变更预览禁用壳，只评审未来依赖文件和 lockfile 变更预览，不写文件、不生成 diff、不安装 SDK、不解析包、不检查密钥。
- `providers/real-sdk-dependency-patch-proposal.contract.json`: 真实 SDK 依赖 patch proposal 契约。
- `providers/real_sdk_dependency_patch_proposal.py`: 真实 SDK 依赖 patch proposal 禁用壳，只评审未来 patch 文件和补丁应用任务，不写 patch、不应用补丁、不写依赖文件、不生成 diff artifact、不安装 SDK、不解析包、不检查密钥。
- `providers/real-sdk-dependency-apply-gate.contract.json`: 真实 SDK 依赖 apply gate 契约。
- `providers/real_sdk_dependency_apply_gate.py`: 真实 SDK 依赖 apply gate 禁用壳，只评审未来补丁应用任务的最终人工批准、回滚、备份和禁止执行策略，不授权 apply、不写依赖文件、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-implementation-task-plan.contract.json`: 真实 SDK 依赖实现任务计划契约。
- `providers/real_sdk_dependency_implementation_task_plan.py`: 真实 SDK 依赖实现任务计划禁用壳，只生成未来依赖文件变更的受控施工单，不创建任务、不写依赖文件、不生成 patch、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-change-approval-package.contract.json`: 真实 SDK 依赖变更人工批准包契约。
- `providers/real_sdk_dependency_change_approval_package.py`: 真实 SDK 依赖变更人工批准包禁用壳，只生成未来依赖文件变更的本地批准包模型，不写批准文件、不授予人工批准、不创建任务、不写依赖文件、不检查密钥。
- `providers/real-sdk-dependency-readonly-diff-review.contract.json`: 真实 SDK 依赖只读差异审查契约。
- `providers/real_sdk_dependency_readonly_diff_review.py`: 真实 SDK 依赖只读差异审查禁用壳，只生成未来依赖文件变更的本地只读审查模型，不读取依赖文件、不写审查文件、不生成 patch、不写依赖文件、不检查密钥。
- `providers/real-sdk-dependency-final-execution-confirmation.contract.json`: 真实 SDK 依赖最终执行确认契约。
- `providers/real_sdk_dependency_final_execution_confirmation.py`: 真实 SDK 依赖最终执行确认禁用壳，只生成未来依赖文件变更的本地最终确认模型，不授予执行批准、不创建任务、不写依赖文件、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-execution-task-creation.contract.json`: 真实 SDK 依赖执行任务创建契约。
- `providers/real_sdk_dependency_execution_task_creation.py`: 真实 SDK 依赖执行任务创建禁用壳，只生成未来依赖文件变更的本地任务创建模型，不创建或持久化任务、不入队、不派发执行、不写依赖文件、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-executor-disabled.contract.json`: 真实 SDK 依赖执行器禁用壳契约。
- `providers/real_sdk_dependency_executor_disabled.py`: 真实 SDK 依赖执行器禁用壳，只生成未来依赖执行器的本地禁用模型，不启动执行器、不创建 executor run、不物化命令、不执行命令、不写依赖文件、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-dry-run-evidence.contract.json`: 真实 SDK 依赖 dry-run evidence 契约。
- `providers/real_sdk_dependency_dry_run_evidence.py`: 真实 SDK 依赖 dry-run evidence 禁用壳，只生成未来安装命令审阅证据模型，不写 evidence 文件、不持久化审阅记录、不物化命令、不执行 dry-run、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-target-resolver.contract.json`: 真实 SDK 依赖 target resolver 契约。
- `providers/real_sdk_dependency_target_resolver.py`: 真实 SDK 依赖 target resolver 禁用壳，只生成未来依赖清单和 lockfile 目标候选模型，不读取真实依赖文件、不写目标文件、不生成 patch、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-readonly-snapshot.contract.json`: 真实 SDK 依赖 readonly snapshot 契约。
- `providers/real_sdk_dependency_readonly_snapshot.py`: 真实 SDK 依赖 readonly snapshot 禁用壳，只生成未来依赖清单和 lockfile 快照审查模型，不读取真实依赖文件、不捕获 snapshot 内容、不写 snapshot 文件、不持久化审查记录、不生成 patch、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-content-read-approval.contract.json`: 真实 SDK 依赖 content read approval 契约。
- `providers/real_sdk_dependency_content_read_approval.py`: 真实 SDK 依赖 content read approval 禁用壳，只生成未来依赖文件内容读取审批模型，不读取依赖文件内容、不返回原文、不持久化内容或审批记录、不写审批产物、不生成 patch、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-content-read-plan.contract.json`: 真实 SDK 依赖 content read plan 契约。
- `providers/real_sdk_dependency_content_read_plan.py`: 真实 SDK 依赖 content read plan 禁用壳，只生成未来依赖文件内容读取只读审查计划模型，不读取依赖文件内容、不返回原文、不持久化内容或计划记录、不写计划产物、不生成 patch、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-content-read-final-confirmation.contract.json`: 真实 SDK 依赖 content read final confirmation 契约。
- `providers/real_sdk_dependency_content_read_final_confirmation.py`: 真实 SDK 依赖 content read final confirmation 禁用壳，只生成未来真实只读读取任务前最终确认模型，不读取依赖文件内容、不返回原文、不持久化内容或确认记录、不写确认产物、不创建执行任务、不授权读取执行、不生成 patch、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-content-read-readonly-execution.contract.json`: 真实 SDK 依赖 content read readonly execution 契约。
- `providers/real_sdk_dependency_content_read_readonly_execution.py`: 真实 SDK 依赖 content read readonly execution，只在最终确认后读取允许名单内本地依赖文件并返回脱敏预览，不返回原文、不持久化内容或记录、不写读取产物、不生成 patch、不执行命令、不安装 SDK、不检查密钥。
- `providers/real-sdk-dependency-install-change-proposal.contract.json`: 真实 SDK 依赖 install change proposal 契约。
- `providers/real_sdk_dependency_install_change_proposal.py`: 真实 SDK 依赖 install change proposal，只生成未来真实 SDK 安装变更方案和不可执行 patch 预览，不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥。
- `providers/real-sdk-dependency-install-execution-gate.contract.json`: 真实 SDK 依赖 install execution gate 契约。
- `providers/real_sdk_dependency_install_execution_gate.py`: 真实 SDK 依赖 install execution gate，只生成未来真实 SDK 安装执行门禁模型，不授权执行、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥。
- `providers/real-sdk-dependency-install-authorization-package.contract.json`: 真实 SDK 依赖 install authorization package 契约。
- `providers/real_sdk_dependency_install_authorization_package.py`: 真实 SDK 依赖 install authorization package，只生成未来真实 SDK 安装授权包模型，不授权执行、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥。
- `providers/real-sdk-dependency-install-execution-request.contract.json`: 真实 SDK 依赖 install execution request 契约。
- `providers/real_sdk_dependency_install_execution_request.py`: 真实 SDK 依赖 install execution request，只生成未来真实 SDK 安装执行请求模型，不授权执行、不派发执行器、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥。
- `providers/real-sdk-dependency-install-executor-disabled.contract.json`: 真实 SDK 依赖 install executor disabled 契约。
- `providers/real_sdk_dependency_install_executor_disabled.py`: 真实 SDK 依赖 install executor disabled，只生成未来真实 SDK 安装禁用执行器模型，不派发执行器、不启动执行器、不创建 executor run、不授权执行、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥。
- `providers/real-llm-minimal-call-send-executor-disabled.contract.json`: 真实 LLM 最小调用发送执行器禁用壳契约。
- `providers/real_llm_minimal_call_send_executor_disabled.py`: 真实 LLM 最小调用发送执行器禁用壳，只生成未来发送执行器本地模型，不创建真实发送实现、不派发、不发送请求。
- `providers/real-llm-request-send-authorization-package.contract.json`: 真实 LLM 请求发送最终授权包契约。
- `providers/real_llm_request_send_authorization_package.py`: 真实 LLM 请求发送最终授权包，只生成未来真实请求发送的本地人工授权包模型，不授予人工批准、不授权真实调用、不发送请求。
- `providers/real-llm-request-send-execution-request-disabled.contract.json`: 真实 LLM 请求发送执行请求禁用壳契约。
- `providers/real_llm_request_send_execution_request_disabled.py`: 真实 LLM 请求发送执行请求禁用壳，只生成未来真实请求发送的本地执行请求模型，不授予人工批准、不授权真实调用、不持久化/入队/派发执行请求、不发送请求。
- `providers/real-llm-request-send-executor-disabled.contract.json`: 真实 LLM 请求发送执行器禁用壳契约。
- `providers/real_llm_request_send_executor_disabled.py`: 真实 LLM 请求发送执行器禁用壳，只生成未来真实请求发送的本地执行器模型，不授予人工批准、不授权真实调用、不创建/启动/派发执行器、不创建运行记录、不发送请求。
- `providers/real-llm-request-send-final-approval-review.contract.json`: 真实 LLM 请求发送最终批准评审契约。
- `providers/real_llm_request_send_final_approval_review.py`: 真实 LLM 请求发送最终批准评审，只生成未来真实请求发送的本地最终人工批准评审模型，不授予人工批准、不授权真实调用、不写批准记录、不派发执行器、不发送请求。
- `providers/real-llm-request-send-authorization-task-disabled.contract.json`: 真实 LLM 请求发送授权任务禁用契约。
- `providers/real_llm_request_send_authorization_task_disabled.py`: 真实 LLM 请求发送授权任务禁用模型，只生成未来真实请求发送的本地授权任务禁用模型，不创建/持久化/入队/派发任务、不写授权记录、不授予人工批准、不授权真实调用、不发送请求。
- `providers/real-llm-request-send-authorization-record-write-gate.contract.json`: 真实 LLM 请求发送授权记录写入门禁契约。
- `providers/real_llm_request_send_authorization_record_write_gate.py`: 真实 LLM 请求发送授权记录写入门禁，只生成未来真实请求发送的本地授权记录写入门禁模型，不写授权记录或批准记录、不授予人工批准、不授权真实调用、不派发执行器、不发送请求。
- `providers/real-llm-request-send-runtime-gate-disabled.contract.json`: 真实 LLM 请求发送运行时门禁禁用契约。
- `providers/real_llm_request_send_runtime_gate_disabled.py`: 真实 LLM 请求发送运行时门禁禁用壳，只生成未来真实请求发送的本地运行时门禁禁用模型，不打开运行时门禁、不关闭 kill switch、不预留预算、不打开网络出口、不创建 client/执行器、不授权真实调用、不发送请求。
- `providers/real-llm-request-send-executor-creation-gate-disabled.contract.json`: 真实 LLM 请求发送执行器创建门禁禁用契约。
- `providers/real_llm_request_send_executor_creation_gate_disabled.py`: 真实 LLM 请求发送执行器创建门禁禁用壳，只生成未来真实请求发送的本地执行器创建门禁禁用模型，不物化 factory、不创建/持久化/启动执行器、不创建运行记录、不派发执行器、不授权真实调用、不发送请求。
- `providers/real-llm-request-send-executor-dispatch-gate-disabled.contract.json`: 真实 LLM 请求发送执行器派发门禁禁用契约。
- `providers/real_llm_request_send_executor_dispatch_gate_disabled.py`: 真实 LLM 请求发送执行器派发门禁禁用壳，只生成未来真实请求发送的本地执行器派发门禁禁用模型，不写派发队列、不持久化派发记录、不派发执行器、不启动执行器、不创建运行记录、不授权真实调用、不发送请求。
- `providers/real-llm-request-send-attempt-gate-disabled.contract.json`: 真实 LLM 请求发送尝试门禁禁用契约。
- `providers/real_llm_request_send_attempt_gate_disabled.py`: 真实 LLM 请求发送尝试门禁禁用壳，只生成未来真实请求发送的本地发送尝试门禁禁用模型，不持久化尝试记录、不尝试发送请求、不发送请求、不创建 client、不联网、不读取密钥、不真实调用、不创建内容、不创建任务。
- `scripts/manifest.json`: 本地验证命令白名单。

## 输出说明

- `delivery/PHASE5_MOCK_BASELINE.md`: 人工可读的 Mock 基线冻结说明。
- `delivery/phase5-mock-baseline.json`: 机器可测的 Mock 基线冻结契约。

这些输出只用于后续真实 LLM PoC 的准入判断，不生成真实平台内容，不上传远端，不发布实验、考试、评分规则或 PPT。

## 收口基线

- 交付包必须保持 `175/175` ready，`missingRequired=0`。
- Phase 1 自检必须保持 `20/20`。
- 验收摘要必须保持 `14/14`。
- 安全断言必须保持 `6/6`，且实际值均为 `false`。
- 前端静态入口必须保持 Mock-only，不需要真实后端服务。
- 真实 Provider 前置门禁必须默认拒绝，`provider real-preflight` 不调用真实 SDK、不访问网络、不读取或输出密钥值。
- Provider Runtime Guard 必须保持启用，检查 timeout、retry、concurrency、日志脱敏、Schema、审计和审核门禁，且当前固定 `readyForRealProvider=false`。
- Real LLM PoC Adapter 必须保持禁用，只能串联 Runtime Guard、真实 Provider 预检和禁用空壳，且 `realLlmCalled=false`、`sdkImported=false`、`clientCreated=false`。
- Real LLM dry-run plan 必须保持只生成计划，且 `dryRunOnly=true`、`secretPresenceChecked=false`、`secretValueRead=false`、`taskCreated=false`。
- Real LLM approval gate 必须保持只评估实现任务前批准清单，且 `realCallAuthorized=false`、`secretPresenceChecked=false`、`secretValueRead=false`、`taskCreated=false`。
- Real LLM SDK task blueprint 必须保持只生成未来任务蓝图，且 `implementationAllowed=false`、`realCallAuthorized=false`、`sdkDependencyInstalled=false`、`providerContractChangeApplied=false`、`runtimeContractChangeApplied=false`。
- Real Provider SDK PoC harness 必须保持默认禁用，且 `sdkPocEnabled=false`、`sdkImported=false`、`secretPresenceChecked=false`、`networkAccess=false`、`taskCreated=false`。
- Real SDK minimal implementation shell 必须保持默认禁用，且 `sdkImplementationEnabled=false`、`sdkImported=false`、`clientCreated=false`、`secretPresenceChecked=false`、`networkAccess=false`、`taskCreated=false`。
- Real SDK dependency/env gate 必须保持设计评审态，且 `dependencyInstallAllowed=false`、`sdkDependencyInstalled=false`、`sdkImported=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- Real SDK dependency install plan 必须保持草案态，且 `dependencyInstallCommandGenerated=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`packageHashResolved=false`、`dependencyLockfileChanged=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- Real SDK dependency installer audit 必须保持禁用审计态，且 `installerExecutionEnabled=false`、`installCommandMaterialized=false`、`dependencyFileChanged=false`、`lockfileDiffGenerated=false`、`offlineCiExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- Real SDK dependency change preview 必须保持禁用预览态，且 `dependencyFileChanged=false`、`dependencyDiffGenerated=false`、`lockfileDiffGenerated=false`、`diffArtifactWritten=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- Real SDK dependency patch proposal 必须保持禁用提案态，且 `patchFileWritten=false`、`patchApplied=false`、`dependencyPatchGenerated=false`、`dependencyFileChanged=false`、`diffArtifactWritten=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- Real SDK dependency apply gate 必须保持禁用门禁态，且 `applyAuthorized=false`、`applyApprovalMaterialized=false`、`patchApplied=false`、`dependencyFileChanged=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- Real SDK dependency implementation task plan 必须保持禁用计划态，且 `dependencyImplementationTaskCreated=false`、`dependencyFileChanged=false`、`patchMaterialized=false`、`commandExecutionAuthorized=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency change approval package 必须保持禁用批准包态，且 `approvalPackageWritten=false`、`manualApprovalGranted=false`、`dependencyFileChanged=false`、`commandExecutionAuthorized=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency readonly diff review 必须保持禁用只读审查态，且 `diffReviewArtifactWritten=false`、`dependencySnapshotReadFromFile=false`、`patchGenerated=false`、`dependencyFileChanged=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency final execution confirmation 必须保持禁用最终确认态，且 `executionApprovalGranted=false`、`executionTaskCreated=false`、`dependencyFileMutationAuthorized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency execution task creation 必须保持禁用任务创建态，且 `executionTaskCreated=false`、`taskPersisted=false`、`taskQueued=false`、`executionDispatched=false`、`dependencyFileMutationAuthorized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency executor disabled shell 必须保持禁用执行器态，且 `executorStarted=false`、`executorRunCreated=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency dry-run evidence 必须保持禁用证据态，且 `dryRunExecuted=false`、`evidenceFileWritten=false`、`commandReviewRecordPersisted=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency target resolver 必须保持禁用目标解析态，且 `targetPathResolutionExecuted=false`、`liveDependencyFileRead=false`、`targetFileWritten=false`、`patchGenerated=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency readonly snapshot 必须保持禁用快照审查态，且 `dependencySnapshotReadFromFile=false`、`dependencySnapshotContentCaptured=false`、`snapshotFileWritten=false`、`snapshotReviewRecordPersisted=false`、`patchGenerated=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency install change proposal 必须保持方案态，且 `dependencyInstallPatchPlanGenerated=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency install execution gate 必须保持禁用门禁态，且 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency install authorization package 必须保持禁用授权包态，且 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency install execution request 必须保持禁用请求态，且 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real SDK dependency install executor disabled 必须保持禁用执行器态，且 `executorDispatched=false`、`executorStarted=false`、`executorRunCreated=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- Real LLM SDK boundary 是 Mock 收口后的下一阶段入口；允许读取 `requirements.txt` 依赖声明、解析本机 `openai` 包元数据、可选检查 `OPENAI_API_KEY` 环境变量名是否存在，但必须保持 `sdkImportAttempted=false`、`sdkImported=false`、`clientCreated=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`realCallAuthorized=false`。
- Real LLM SDK client boundary 允许在显式确认后导入 SDK、读取 `OPENAI_API_KEY` 仅用于本地 client 构造，但必须保持 `secretValueReturned=false`、`secretValueLogged=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`realCallAuthorized=false`。
- Real LLM request review package 只生成首个真实请求的本地脱敏审核包；必须保持 `requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`realCallAuthorized=false`。
- Real LLM first-call approval gate 只评估首个真实请求的最终批准清单；必须保持 `manualApprovalGranted=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`realCallAuthorized=false`。
- Real LLM first-call executor disabled 只准备首个真实请求的禁用执行器计划；必须保持 `executorDispatched=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`realCallAuthorized=false`。
- Real LLM pre-send dry-run record 只生成首个真实请求发送前的本地 dry-run 审计记录模型；必须保持 `dryRunExecuted=false`、`dryRunRecordWritten=false`、`executorDispatched=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`realCallAuthorized=false`。
- Real LLM minimal call PoC review 只生成未来单次 Lab JSON 请求的本地实施评审包；必须保持 `readyForRealRequestSend=false`、`manualApprovalGranted=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`、`realCallAuthorized=false`。
- Real LLM minimal call send executor disabled 只生成未来最小真实请求发送执行器的本地禁用模型；必须保持 `readyForRealRequestSend=false`、`sendImplementationCreated=false`、`sendExecutorMaterialized=false`、`sendExecutorDispatched=false`、`manualApprovalGranted=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`、`realCallAuthorized=false`。
- Real LLM request send authorization package 只生成未来真实请求发送的本地人工授权包模型；必须保持 `manualApprovalGranted=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`approvalRecordWritten=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send execution request disabled 只生成未来真实请求发送的本地执行请求禁用模型；必须保持 `readyForRealRequestSend=false`、`executionRequestMaterialized=false`、`executionRequestPersisted=false`、`executionRequestQueued=false`、`executionRequestDispatched=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send executor disabled 只生成未来真实请求发送的本地执行器禁用模型；必须保持 `readyForRealRequestSend=false`、`sendExecutorCreated=false`、`sendExecutorStarted=false`、`sendExecutorRunCreated=false`、`sendExecutorDispatched=false`、`executorStarted=false`、`executorRunCreated=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send final approval review 只生成未来真实请求发送的本地最终人工批准评审模型；必须保持 `readyForRealRequestSend=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`finalApprovalReviewPackagePersisted=false`、`approvalRecordWritten=false`、`sendExecutorDispatched=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send authorization task disabled 只生成未来真实请求发送的本地授权任务禁用模型；必须保持 `readyForRealRequestSend=false`、`authorizationTaskCreated=false`、`authorizationTaskPersisted=false`、`authorizationTaskQueued=false`、`authorizationTaskDispatched=false`、`authorizationRecordWritten=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send authorization record write gate 只生成未来真实请求发送的本地授权记录写入门禁模型；必须保持 `readyForRealRequestSend=false`、`authorizationRecordMaterialized=false`、`authorizationRecordPersisted=false`、`authorizationRecordWritten=false`、`approvalRecordWritten=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`sendExecutorDispatched=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send runtime gate disabled 只生成未来真实请求发送的本地运行时门禁禁用模型；必须保持 `readyForRealRequestSend=false`、`runtimeGateOpened=false`、`runtimeKillSwitchDisabled=false`、`runtimeBudgetReserved=false`、`runtimeNetworkEgressOpened=false`、`clientCreated=false`、`sendExecutorCreated=false`、`realCallAuthorized=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send executor creation gate disabled 只生成未来真实请求发送的本地执行器创建门禁禁用模型；必须保持 `readyForRealRequestSend=false`、`executorFactoryMaterialized=false`、`sendExecutorCreated=false`、`sendExecutorPersisted=false`、`sendExecutorStarted=false`、`sendExecutorRunCreated=false`、`sendExecutorDispatched=false`、`clientCreated=false`、`realCallAuthorized=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send executor dispatch gate disabled 只生成未来真实请求发送的本地执行器派发门禁禁用模型；必须保持 `readyForRealRequestSend=false`、`dispatchQueueWritten=false`、`dispatchRecordPersisted=false`、`sendExecutorDispatched=false`、`executorDispatched=false`、`requestSendAttempted=false`、`requestSent=false`、`clientCreated=false`、`realCallAuthorized=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- Real LLM request send attempt gate disabled 只生成未来真实请求发送的本地发送尝试门禁禁用模型；必须保持 `readyForRealRequestSend=false`、`attemptRecordPersisted=false`、`requestSendAttempted=false`、`requestSent=false`、`clientCreated=false`、`realCallAuthorized=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- R25 后不再新增安装前或请求发送前禁用壳。`real-llm-request-send-attempt-gate-disabled` 是封口点；后续必须转入 SDK 安装执行、环境变量边界、SDK import/client 边界、最小真实 LLM 单请求 PoC 和核心业务开发。
- Lab / Exam / Grading / PPT 生成结果仍必须默认进入 `WAITING_REVIEW`。
- 高风险 MCP Tool 仍只能创建审核意图或只读查询，不得真实发布、真实销毁或绕过二次确认。

## LLM 准入门禁

真实 LLM PoC 只能在下列条件同时满足后开始：

1. 默认 Provider 仍为 `mock`，真实 Provider 必须显式 opt-in。
2. API Key 只能来自环境变量或本地未提交配置，不能写入代码、日志、前端或交付包。
3. 第一版只允许接入 `lab generate-from-source` 的 Lab DSL 生成链路。
4. 输出必须经过 Lab Schema 校验，校验失败不得创建可发布内容。
5. 真实 LLM 生成结果必须进入 `WAITING_REVIEW`。
6. 审计日志必须脱敏，不记录密钥，不把敏感输入原样展示给前端。
7. Provider Runtime Guard 必须先通过 timeout、retry、concurrency、redaction、Schema 和 review gate 检查。
8. Real LLM PoC Adapter 必须默认禁用，不能绕过 Runtime Guard 和真实 Provider 预检。
9. Real LLM dry-run plan 必须先通过本地计划验收，且不得检查密钥是否存在、不得创建 AI Task。
10. Real LLM approval gate 必须在真实 SDK 实现任务前通过，且不得授权真实调用。
11. Real LLM SDK task blueprint 必须在真实 SDK 实现任务前生成，且不得安装 SDK、修改契约、检查密钥、访问网络或创建 AI Task。
12. Real Provider SDK PoC harness 必须先要求 blueprint，通过后仍只能返回 opt-in 或 disabled-provider 安全错误，不能生成真实内容。
13. Real SDK minimal implementation shell 必须先要求 enablement，通过后仍只能返回 implementation opt-in 或 implementation-disabled 安全错误，不能导入 SDK 或生成真实内容。
14. Real SDK dependency/env gate 必须先通过本地评审，且不得安装 SDK、解析包版本、修改锁文件、检查密钥或联网。
15. Real SDK dependency install plan 必须先通过本地草案评审，且不得生成安装命令、安装 SDK、解析包版本或 hash、修改 lockfile、检查密钥或联网。
16. Real SDK dependency installer audit 必须先通过禁用态审计评审，且不得物化命令、安装 SDK、修改依赖文件、生成 lockfile diff、检查密钥或联网。
17. Real SDK dependency change preview 必须先通过禁用态预览评审，且不得写依赖文件、生成 diff、安装 SDK、解析包、检查密钥或联网。
18. Real SDK dependency patch proposal 必须先通过禁用态提案评审，且不得写 patch 文件、应用补丁、写依赖文件、生成 diff artifact、检查密钥或联网。
19. Real SDK dependency apply gate 必须先通过禁用态最终门禁评审，且不得授权 apply、写依赖文件、执行命令、检查密钥或联网。
20. Real SDK dependency implementation task plan 必须先通过禁用态任务计划评审，且不得创建任务、写依赖文件、物化 patch、执行命令、检查密钥、联网或真实调用。
21. Real SDK dependency change approval package 必须先通过禁用态批准包评审，且不得写批准文件、授予人工批准、创建任务、写依赖文件、执行命令、检查密钥、联网或真实调用。
22. Real SDK dependency readonly diff review 必须先通过禁用态只读审查，且不得读取依赖文件、写审查文件、生成 patch、写依赖文件、解析包版本或 hash、检查密钥、联网或真实调用。
23. Real SDK dependency final execution confirmation 必须先通过禁用态最终确认，且不得授予执行批准、创建任务、写依赖文件、执行命令、安装依赖、检查密钥、联网或真实调用。
24. Real SDK dependency execution task creation 必须先通过禁用态任务创建模型，且不得创建或持久化任务、入队、派发执行、写依赖文件、执行命令、安装依赖、检查密钥、联网或真实调用。
25. Real SDK dependency executor disabled shell 必须先通过禁用态执行器模型，且不得启动执行器、创建 executor run、物化命令、执行命令、写依赖文件、安装依赖、检查密钥、联网或真实调用。
26. Real SDK dependency dry-run evidence 必须先通过禁用态证据模型，且不得写 evidence 文件、持久化命令审阅记录、物化命令、执行 dry-run、执行命令、写依赖文件、安装依赖、检查密钥、联网或真实调用。
27. Real SDK dependency target resolver 必须先通过禁用态目标解析模型，且不得读取真实依赖文件、写目标文件、生成 patch、执行命令、安装依赖、检查密钥、联网或真实调用。
28. Real SDK dependency readonly snapshot 必须先通过禁用态快照审查模型，且不得读取真实依赖文件、捕获 snapshot 内容、写 snapshot 文件、持久化审查记录、生成 patch、执行命令、安装依赖、检查密钥、联网或真实调用。
29. Real SDK dependency install change proposal 必须先通过方案态模型，且不得写依赖文件、写 patch 文件、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。
30. Real SDK dependency install execution gate 必须先通过禁用门禁模型，且不得授权执行、写依赖文件、写 patch 文件、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。
31. Real SDK dependency install authorization package 必须先通过禁用授权包模型，且不得授权执行、写依赖文件、写 patch 文件、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。
32. Real SDK dependency install execution request 必须先通过禁用请求模型，且不得授权执行、派发执行器、写依赖文件、写 patch 文件、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。
33. Real SDK dependency install executor disabled 必须先通过禁用执行器模型，且不得派发执行器、启动执行器、创建 executor run、授权执行、写依赖文件、写 patch 文件、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用。
34. Real LLM SDK boundary 是下一阶段入口，只允许本地依赖声明、SDK 包元数据和环境变量名存在性检查，不导入 SDK、不创建客户端、不读取密钥值、不联网、不真实调用。
35. Real LLM SDK client boundary 只允许本地 SDK import 和 client object construction，不允许任何模型请求、网络请求、内容生成、任务创建或发布。
36. Real LLM request review package 必须先通过本地脱敏审核包评审，且不得导入 SDK、创建客户端、检查或读取密钥、发送请求、联网、真实调用、生成内容或创建任务。
37. Real LLM first-call approval gate 必须先通过本地最终批准门禁评审，且不得授予发送授权、发送请求、联网、真实调用、读取密钥、生成内容、创建任务或发布。
38. Real LLM first-call executor disabled 必须先通过本地禁用执行器评审，且不得派发执行器、发送请求、联网、真实调用、读取密钥、生成内容、创建任务或发布。
39. Real LLM pre-send dry-run record 必须先通过本地发送前审计记录评审，且不得执行 dry-run、写记录、派发执行器、发送请求、联网、真实调用、读取密钥、生成内容、创建任务或发布。
40. Real LLM minimal call PoC review 必须先通过本地实施评审包，且不得发送请求、联网、真实调用、读取密钥、生成内容、创建任务或发布。
41. Real LLM minimal call send executor disabled 必须先通过本地发送执行器禁用模型，且不得创建真实发送实现、派发执行器、发送请求、联网、真实调用、读取密钥、生成内容、创建任务或发布。
42. Real LLM request send authorization package 必须先通过本地人工授权包模型，且不得授予人工批准、授权真实调用、发送请求、联网、读取密钥、生成内容、创建任务或发布。
43. Real LLM request send execution request disabled 必须先通过本地执行请求禁用模型，且不得授予人工批准、授权真实调用、持久化/入队/派发执行请求、发送请求、联网、读取密钥、生成内容、创建任务或发布。
44. Real LLM request send executor disabled 必须先通过本地执行器禁用模型，且不得授予人工批准、授权真实调用、创建/启动/派发执行器、创建运行记录、发送请求、联网、读取密钥、生成内容、创建任务或发布。
45. Real LLM request send final approval review 必须先通过本地最终人工批准评审模型，且不得授予人工批准、授权真实调用、写批准记录、派发执行器、发送请求、联网、读取密钥、生成内容、创建任务或发布。
46. Real LLM request send authorization task disabled 必须先通过本地授权任务禁用模型，且不得创建/持久化/入队/派发任务、写授权记录、授予人工批准、授权真实调用、发送请求、联网、读取密钥、生成内容、创建任务或发布。
47. Real LLM request send authorization record write gate 必须先通过本地授权记录写入门禁模型，且不得写授权记录或批准记录、授予人工批准、授权真实调用、派发执行器、发送请求、联网、读取密钥、生成内容、创建任务或发布。
48. Real LLM request send runtime gate disabled 必须先通过本地运行时门禁禁用模型，且不得打开运行时门禁、关闭 kill switch、预留预算、打开网络出口、创建 client/执行器、授权真实调用、发送请求、联网、读取密钥、生成内容、创建任务或发布。
49. Real LLM request send executor creation gate disabled 必须先通过本地执行器创建门禁禁用模型，且不得物化 factory、创建/持久化/启动执行器、创建运行记录、派发执行器、创建 client、授权真实调用、发送请求、联网、读取密钥、生成内容、创建任务或发布。
50. Real LLM request send executor dispatch gate disabled 必须先通过本地执行器派发门禁禁用模型，且不得写派发队列、持久化派发记录、派发执行器、启动执行器、创建运行记录、创建 client、授权真实调用、发送请求、联网、读取密钥、生成内容、创建任务或发布。
51. Real LLM request send attempt gate disabled 必须先通过本地发送尝试门禁禁用模型，且不得持久化尝试记录、尝试发送请求、发送请求、创建 client、联网、读取密钥、真实调用、生成内容、创建任务或发布。
52. CLI 必须保持统一 JSON envelope。
53. 自动发布、真实发布、真实云资源、真实沙箱、真实 MCP Server、真实 Agent 继续禁用。

## 命令示例

```powershell
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_provider_gate.py
python -m pytest tests/test_provider_runtime_guard.py
python -m pytest tests/test_real_llm_poc_adapter.py
python -m pytest tests/test_real_llm_dry_run_plan.py
python -m pytest tests/test_real_llm_approval_gate.py
python -m pytest tests/test_real_llm_sdk_task_blueprint.py
python -m pytest tests/test_real_provider_sdk_poc.py
python -m pytest tests/test_real_sdk_enablement.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
python -m pytest tests/test_real_sdk_dependency_change_preview.py
python -m pytest tests/test_real_sdk_dependency_patch_proposal.py
python -m pytest tests/test_real_sdk_dependency_apply_gate.py
python -m pytest tests/test_real_sdk_dependency_implementation_task_plan.py
python -m pytest tests/test_real_sdk_dependency_change_approval_package.py
python -m pytest tests/test_real_sdk_dependency_readonly_diff_review.py
python -m pytest tests/test_real_sdk_dependency_final_execution_confirmation.py
python -m pytest tests/test_real_sdk_dependency_execution_task_creation.py
python -m pytest tests/test_real_sdk_dependency_executor_disabled.py
python -m pytest tests/test_real_sdk_dependency_dry_run_evidence.py
python -m pytest tests/test_real_sdk_dependency_target_resolver.py
python -m pytest tests/test_real_sdk_dependency_readonly_snapshot.py
python -m pytest tests/test_real_sdk_dependency_content_read_approval.py
python -m pytest tests/test_real_sdk_dependency_content_read_plan.py
python -m pytest tests/test_real_sdk_dependency_content_read_final_confirmation.py
python -m pytest tests/test_real_sdk_dependency_content_read_readonly_execution.py
python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py
python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py
python -m pytest tests/test_real_sdk_dependency_install_authorization_package.py
python -m pytest tests/test_real_sdk_dependency_install_execution_request.py
python -m pytest tests/test_real_sdk_dependency_install_executor_disabled.py
python -m pytest tests/test_real_llm_minimal_call_send_executor_disabled.py
python -m pytest tests/test_real_llm_request_send_authorization_package.py
python -m pytest tests/test_real_llm_request_send_execution_request_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_disabled.py
python -m pytest tests/test_real_llm_request_send_final_approval_review.py
python -m pytest tests/test_real_llm_request_send_authorization_task_disabled.py
python -m pytest tests/test_real_llm_request_send_authorization_record_write_gate.py
python -m pytest tests/test_real_llm_request_send_runtime_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_creation_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_dispatch_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_attempt_gate_disabled.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest
```

## 测试方式

```powershell
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_provider_gate.py
python -m pytest tests/test_provider_runtime_guard.py
python -m pytest tests/test_real_llm_poc_adapter.py
python -m pytest tests/test_real_llm_dry_run_plan.py
python -m pytest tests/test_real_llm_approval_gate.py
python -m pytest tests/test_real_llm_sdk_task_blueprint.py
python -m pytest tests/test_real_provider_sdk_poc.py
python -m pytest tests/test_real_sdk_enablement.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
python -m pytest tests/test_real_sdk_dependency_change_preview.py
python -m pytest tests/test_real_sdk_dependency_patch_proposal.py
python -m pytest tests/test_real_sdk_dependency_apply_gate.py
python -m pytest tests/test_real_sdk_dependency_implementation_task_plan.py
python -m pytest tests/test_real_sdk_dependency_change_approval_package.py
python -m pytest tests/test_real_sdk_dependency_readonly_diff_review.py
python -m pytest tests/test_real_sdk_dependency_final_execution_confirmation.py
python -m pytest tests/test_real_sdk_dependency_execution_task_creation.py
python -m pytest tests/test_real_sdk_dependency_executor_disabled.py
python -m pytest tests/test_real_sdk_dependency_target_resolver.py
python -m pytest tests/test_real_sdk_dependency_readonly_snapshot.py
python -m pytest tests/test_real_sdk_dependency_content_read_approval.py
python -m pytest tests/test_real_sdk_dependency_content_read_plan.py
python -m pytest tests/test_real_sdk_dependency_content_read_final_confirmation.py
python -m pytest tests/test_real_sdk_dependency_content_read_readonly_execution.py
python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py
python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py
python -m pytest tests/test_real_sdk_dependency_install_authorization_package.py
python -m pytest tests/test_real_sdk_dependency_install_execution_request.py
python -m pytest tests/test_real_llm_minimal_call_send_executor_disabled.py
python -m pytest tests/test_real_llm_request_send_authorization_package.py
python -m pytest tests/test_real_llm_request_send_execution_request_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_disabled.py
python -m pytest tests/test_real_llm_request_send_final_approval_review.py
python -m pytest tests/test_real_llm_request_send_authorization_task_disabled.py
python -m pytest tests/test_real_llm_request_send_authorization_record_write_gate.py
python -m pytest tests/test_real_llm_request_send_runtime_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_creation_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_dispatch_gate_disabled.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_scripts_manifest.py
python -m pytest
```

## 限制说明

- 不接入真实大模型。
- 不启用真实 Provider。
- 不读取或输出真实密钥。
- 不绕过 Provider Runtime Guard，不输出未脱敏 Provider payload。
- 不绕过 Real LLM PoC Adapter 禁用态，不从 adapter 发起真实 SDK 调用。
- 不绕过 Real LLM dry-run plan，不在 dry-run 阶段检查密钥是否存在或创建 AI Task。
- 不绕过 Real LLM approval gate，不把 `readyForImplementationTask=true` 当成真实调用授权。
- 不绕过 Real LLM SDK task blueprint，不把 `blueprintReady=true` 当成实施许可或真实调用授权。
- 不绕过 Real Provider SDK PoC harness，不把显式 opt-in 或禁用错误当成真实生成成功。
- 不绕过 Real SDK dependency/env gate，不把 `readyForDependencyImplementationTask=true` 当成安装 SDK、检查密钥或联网许可。
- 不绕过 Real SDK dependency install plan，不把 `readyForDependencyInstallImplementationReview=true` 当成生成安装命令、安装 SDK、解析包版本或 hash、修改 lockfile、检查密钥或联网许可。
- 不绕过 Real SDK dependency installer audit，不把 `readyForInstallerImplementationTask=true` 当成物化命令、安装 SDK、修改依赖文件、生成 lockfile diff、检查密钥或联网许可。
- 不绕过 Real SDK dependency change preview，不把 `readyForDependencyChangeImplementationTask=true` 当成写依赖文件、生成 diff、安装 SDK、解析包版本或 hash、检查密钥或联网许可。
- 不绕过 Real SDK dependency patch proposal，不把 `readyForDependencyPatchImplementationTask=true` 当成写 patch、应用补丁、写依赖文件、生成 diff artifact、检查密钥或联网许可。
- 不绕过 Real SDK dependency apply gate，不把 `readyForFutureDependencyPatchApplyTask=true` 当成授权 apply、写依赖文件、执行命令、检查密钥或联网许可。
- 不绕过 Real SDK dependency install change proposal，不把 `installChangeProposalModelReady=true` 当成写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency install execution gate，不把 `installExecutionGateModelReady=true` 当成授权执行、写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency install authorization package，不把 `installAuthorizationPackageModelReady=true` 当成授权执行、写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency install execution request，不把 `installExecutionRequestModelReady=true` 当成授权执行、派发执行器、写依赖文件、写 patch、应用 patch、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency install executor disabled，不把 `installExecutorDisabledModelReady=true` 当成派发执行器、启动执行器、创建 executor run、授权执行、物化或执行命令、安装依赖、解析包、检查密钥、联网或真实调用许可。
- 不绕过 Real LLM SDK boundary，不把 `readyForRealLlmSdkCallReview=true` 当成真实调用授权；该边界不导入 SDK、不创建客户端、不读取密钥值、不联网、不真实调用。
- 不绕过 Real LLM SDK client boundary，不把 `clientCreated=true` 当成真实调用授权；该边界不发起模型请求、不联网、不生成内容、不创建任务、不返回或记录密钥。
- 不绕过 Real LLM request review package，不把 `readyForManualRequestReview=true` 当成真实调用授权；该审核包不导入 SDK、不创建客户端、不检查或读取密钥、不发送请求、不联网、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM first-call approval gate，不把 `readyForDisabledFirstCallExecutor=true` 当成真实调用授权；该门禁不授予发送授权、不发送请求、不联网、不真实调用、不读取密钥、不生成内容、不创建任务。
- 不绕过 Real LLM first-call executor disabled，不把 `readyForMinimalRealCallPocReview=true` 当成真实请求发送许可；该禁用执行器不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM pre-send dry-run record，不把 `readyForMinimalRealCallPoc=true` 当成真实请求发送许可；该记录模型不执行 dry-run、不写记录、不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM minimal call PoC review，不把 `readyForMinimalRealCallImplementation=true` 当成真实请求发送许可；该评审包不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM minimal call send executor disabled，不把 `readyForExplicitRealRequestSendAuthorization=true` 当成真实请求发送许可；该禁用壳不创建真实发送实现、不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send authorization package，不把 `readyForFinalManualSendAuthorizationReview=true` 当成真实请求发送许可；该授权包不授予人工批准、不授权真实调用、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send execution request disabled，不把 `readyForDisabledRealRequestSendExecutor=true` 当成真实请求发送许可；该执行请求禁用壳不授予人工批准、不授权真实调用、不持久化/入队/派发执行请求、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send executor disabled，不把 `readyForFinalRealRequestSendApprovalReview=true` 当成真实请求发送许可；该执行器禁用壳不授予人工批准、不授权真实调用、不创建/启动/派发执行器、不创建运行记录、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send final approval review，不把 `readyForExplicitRealRequestSendAuthorizationTask=true` 当成真实请求发送许可；该最终批准评审不授予人工批准、不授权真实调用、不写批准记录、不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send authorization task disabled，不把 `readyForAuthorizationRecordWriteGate=true` 当成真实请求发送许可；该授权任务禁用模型不创建/持久化/入队/派发任务、不写授权记录、不授予人工批准、不授权真实调用、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send authorization record write gate，不把 `readyForRequestSendRuntimeGate=true` 当成真实请求发送许可；该授权记录写入门禁不写授权记录或批准记录、不授予人工批准、不授权真实调用、不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send runtime gate disabled，不把 `readyForRealRequestSendExecutorCreationGate=true` 当成真实请求发送许可；该运行时门禁禁用壳不打开运行时门禁、不关闭 kill switch、不预留预算、不打开网络出口、不创建 client/执行器、不授权真实调用、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send executor creation gate disabled，不把 `readyForRealRequestSendExecutorDispatchGate=true` 当成真实请求发送许可；该执行器创建门禁禁用壳不物化 factory、不创建/持久化/启动执行器、不创建运行记录、不派发执行器、不创建 client、不授权真实调用、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send executor dispatch gate disabled，不把 `readyForRealRequestSendAttemptGate=true` 当成真实请求发送许可；该执行器派发门禁禁用壳不写派发队列、不持久化派发记录、不派发执行器、不启动执行器、不创建运行记录、不创建 client、不授权真实调用、不发送请求、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real LLM request send attempt gate disabled，不把 `readyForFinalRealRequestSendExecution=true` 当成真实请求发送许可；该发送尝试门禁禁用壳不持久化尝试记录、不尝试发送请求、不发送请求、不创建 client、不联网、不读取密钥、不真实调用、不生成内容、不创建任务。
- 不绕过 Real SDK dependency implementation task plan，不把 `readyForReviewedDependencyImplementationTask=true` 当成创建任务、写依赖文件、物化 patch、执行命令、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency change approval package，不把 `readyForManualDependencyChangeApproval=true` 当成写批准文件、授予人工批准、创建任务、写依赖文件、执行命令、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency readonly diff review，不把 `readyForReadonlyDependencyDiffReview=true` 当成读取依赖文件、写审查文件、生成 patch、写依赖文件、解析包版本或 hash、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency final execution confirmation，不把 `readyForReviewedDependencyExecutionTask=true` 当成授予执行批准、创建任务、写依赖文件、执行命令、安装依赖、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency execution task creation，不把 `readyForDisabledDependencyExecutionTaskRecord=true` 当成创建或持久化任务、入队、派发执行、写依赖文件、执行命令、安装依赖、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency target resolver，不把 `readyForDependencyTargetReview=true` 当成读取真实依赖文件、写目标文件、生成 patch、执行命令、安装依赖、检查密钥、联网或真实调用许可。
- 不绕过 Real SDK dependency readonly snapshot，不把 `readyForReadonlyDependencySnapshotReview=true` 当成读取真实依赖文件、捕获 snapshot 内容、写 snapshot 文件、持久化审查记录、生成 patch、执行命令、安装依赖、检查密钥、联网或真实调用许可。
- 不启动真实 Agent 或真实 MCP Server。
- 不启动真实 HTTP 服务，不绑定公网 IP、内网 IP 或真实端口监听。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不执行未知 Shell 脚本。
- 不自动发布或真实发布生成内容。
- 不展示选手端应隐藏的标准答案。

## 下一步建议

下一步可以在用户明确批准真实 LLM 接入后，进入“真实 SDK 最小接入 PoC”开发；开始前必须先运行 `provider real-dry-run plan --provider openai`、`provider real-approval-gate check --provider openai ...`、`provider real-sdk-blueprint plan --provider openai ...`、`provider real-sdk-poc describe`、`provider real-sdk-enablement check --provider openai ...`、`provider real-sdk-dependency-env check --provider openai ...`、`provider real-sdk-dependency-install-plan plan --provider openai ...`、`provider real-sdk-dependency-installer-audit audit --provider openai ...`、`provider real-sdk-dependency-change-preview preview --provider openai ...`、`provider real-sdk-dependency-patch-proposal propose --provider openai ...`、`provider real-sdk-dependency-apply-gate evaluate --provider openai ...`、`provider real-sdk-dependency-implementation-task-plan plan --provider openai ...`、`provider real-sdk-dependency-change-approval-package package --provider openai ...`、`provider real-sdk-dependency-readonly-diff-review review --provider openai ...`、`provider real-sdk-dependency-final-execution-confirmation confirm --provider openai ...`、`provider real-sdk-dependency-execution-task-creation create --provider openai ...` 和对应测试，确认 dry-run、approval gate、task blueprint、SDK PoC harness、enablement 开关设计、dependency/env gate、dependency install plan、installer audit、dependency change preview、dependency patch proposal、dependency apply gate、dependency implementation task plan、dependency change approval package、readonly diff review、final execution confirmation 与 execution task creation 都仍不读取密钥、不访问网络、不创建或持久化任务、不入队、不派发执行、不修改契约、不安装 SDK、不物化安装命令、不写依赖文件、不写 patch、不应用补丁、不授权 apply、不执行命令、不生成 diff、不授予人工批准、不授予执行批准、不授权真实调用。
