# providers

Phase 1 Provider Mock 抽象目录。当前只实现 `MockProvider`，用于预留后续 LLM Provider 接口形状，不接入真实大模型、不读取 API Key、不访问网络。

## 输入说明

- `providers/provider.contract.json`：Provider 契约，声明 `mock` 为唯一启用 Provider，`openai`、`anthropic`、`local` 均为禁用占位。
- `providers/PHASE2_PROVIDER_PLAN.md`：Phase 2 Provider 接入规划，定义 MockProvider-first、`LLMProvider` 接口、真实 Provider 占位和安全门禁。
- `providers/phase2-provider-plan.contract.json`：Provider 接入规划机器契约，供交付包和测试校验。
- `providers/adapter.py`：Mock-only Provider Adapter，提供 `LLMProvider` 风格调用边界，只路由到 `MockProvider`。
- `providers/provider-adapter.contract.json`：Provider Adapter 机器契约，声明 `generateText`、`generateJson`、`health` 和暂缓的 `streamGenerate`。
- `providers/real_provider_gate.py`：真实 Provider PoC 前置门禁，只做本地预检，默认拒绝，不调用 SDK，不访问网络，不返回密钥值。
- `providers/real-provider-gate.contract.json`：真实 Provider PoC 前置门禁机器契约，声明显式 opt-in、默认禁用、首批 Lab DSL 范围和安全上下文。
- `providers/real_provider_shell.py`：OpenAI / Anthropic / Local Model 的禁用适配器空壳，只保留类名、配置摘要和安全错误路径，不导入 SDK、不创建客户端、不读取密钥、不访问网络。
- `providers/real-provider-shell.contract.json`：真实 Provider 空壳机器契约，约束 `health` 只能返回禁用摘要，`generateText/generateJson/streamGenerate` 必须安全失败。
- `providers/provider_runtime_guard.py`：真实 Provider PoC 前的运行时护栏，检查 timeout、retry、concurrency、日志脱敏、Schema、审计和审核要求，不导入 SDK、不读取密钥、不访问网络。
- `providers/provider-runtime-guard.contract.json`：Provider Runtime Guard 机器契约，约束护栏上下文必须保持 `readyForRealProvider=false`、`realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`。
- `providers/real_llm_poc_adapter.py`：真实 LLM PoC Adapter 禁用外壳，只串联 Runtime Guard、真实 Provider 预检和禁用空壳，不导入 SDK、不创建客户端、不读取密钥、不访问网络、不生成内容。
- `providers/real-llm-poc-adapter.contract.json`：真实 LLM PoC Adapter 机器契约，约束 adapter 当前只能返回禁用摘要或安全失败上下文。
- `providers/real_llm_dry_run_plan.py`：真实 LLM PoC dry-run 计划生成器，只检查首批 Lab DSL 范围和 Runtime Guard，输出可审核计划，不检查密钥是否存在、不调用 SDK、不访问网络、不创建 AI Task。
- `providers/real-llm-dry-run-plan.contract.json`：真实 LLM dry-run 计划机器契约，约束计划必须保持 `dryRunOnly=true`、`readyForRealProvider=false`、`realLlmCalled=false`、`secretValueRead=false`。
- `providers/real_llm_approval_gate.py`：真实 LLM SDK 接入前批准门禁，检查 dry-run、运行时护栏、Schema、人工审核和审计脱敏确认项；即使通过也不授权真实调用。
- `providers/real-llm-approval-gate.contract.json`：真实 LLM SDK 批准门禁机器契约，约束 `realCallAuthorized=false`、`secretValueRead=false`、`networkAccess=false`、`taskCreated=false`。
- `providers/real_llm_sdk_task_blueprint.py`：真实 LLM SDK 最小接入任务蓝图，只输出未来实现范围、拟改文件、测试矩阵、回滚计划和阻断条件，不安装 SDK、不改启用态、不读取密钥、不访问网络。
- `providers/real-llm-sdk-task-blueprint.contract.json`：真实 LLM SDK 任务蓝图机器契约，约束 `implementationAllowed=false`、`realCallAuthorized=false`、`sdkDependencyInstalled=false`、`providerContractChangeApplied=false`、`runtimeContractChangeApplied=false`。
- `providers/real_provider_sdk_poc.py`：真实 Provider SDK PoC harness，要求先通过 SDK 任务蓝图，再进入禁用 PoC Adapter；当前不安装 SDK、不导入 SDK、不检查密钥、不联网、不创建任务。
- `providers/real-provider-sdk-poc.contract.json`：真实 Provider SDK PoC harness 机器契约，约束 `sdkPocEnabled=false`、`sdkImported=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- `providers/real_sdk_enablement.py`：真实 SDK 最终开关设计门禁，检查蓝图、SDK 依赖审查、Provider/Runtime 契约审查、密钥注入审查、网络审查和回滚确认；当前不应用契约变更、不安装 SDK、不检查密钥、不联网、不授权真实调用。
- `providers/real-sdk-enablement.contract.json`：真实 SDK 开关设计机器契约，约束 `switchDesignReady` 只代表未来实现任务可评审，`implementationAllowed=false`、`realCallAuthorized=false`。
- `providers/real_sdk_minimal_impl.py`：真实 SDK 最小实现外壳，要求先通过 enablement 和显式 implementation opt-in；当前仍默认禁用，不导入 SDK、不创建客户端、不检查密钥、不联网、不生成内容。
- `providers/real-sdk-minimal-impl.contract.json`：真实 SDK 最小实现外壳机器契约，约束 `sdkImplementationEnabled=false`、`sdkImported=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- `providers/real_sdk_dependency_env_gate.py`：真实 SDK 依赖与环境变量门禁，只评估 SDK 包名、版本 pin、license/hash、环境变量名和 CI 安装策略确认；当前不安装依赖、不导入 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-env-gate.contract.json`：真实 SDK 依赖与环境变量门禁机器契约，约束 `dependencyInstallAllowed=false`、`sdkDependencyInstalled=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- `providers/real_sdk_dependency_install_plan.py`：真实 SDK 依赖安装计划草案，只评估 package manager、lockfile、version pin、hash 校验、回滚文件和 CI cache 策略；当前不生成安装命令、不安装依赖、不解析包版本或 hash、不改 lockfile、不联网。
- `providers/real-sdk-dependency-install-plan.contract.json`：真实 SDK 依赖安装计划草案机器契约，约束 `dependencyInstallCommandGenerated=false`、`dependencyInstallExecuted=false`、`dependencyLockfileChanged=false`、`packageVersionResolved=false`、`packageHashResolved=false`。
- `providers/real_sdk_dependency_installer_audit.py`：真实 SDK 依赖安装执行审计器禁用壳，只评估未来安装命令、依赖文件、lockfile diff、离线 CI 和回滚命令审查；当前不物化命令、不安装 SDK、不改文件、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-installer-audit.contract.json`：真实 SDK 依赖安装执行审计机器契约，约束 `installerExecutionEnabled=false`、`installCommandMaterialized=false`、`dependencyInstallExecuted=false`、`dependencyFileChanged=false`、`lockfileDiffGenerated=false`。
- `providers/real_sdk_dependency_change_preview.py`：真实 SDK 依赖变更预览禁用壳，只输出未来 pyproject/requirements、lockfile、rollback 和测试矩阵的本地预览；当前不写依赖文件、不生成 diff、不安装 SDK、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-change-preview.contract.json`：真实 SDK 依赖变更预览机器契约，约束 `dependencyFileChanged=false`、`dependencyDiffGenerated=false`、`lockfileDiffGenerated=false`、`diffArtifactWritten=false`、`dependencyInstallExecuted=false`。
- `providers/real_sdk_dependency_patch_proposal.py`：真实 SDK 依赖 patch proposal 禁用壳，只输出未来 patch 计划、应用策略和测试矩阵；当前不写 patch 文件、不应用补丁、不写依赖文件、不生成 diff artifact、不安装 SDK、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-patch-proposal.contract.json`：真实 SDK 依赖 patch proposal 机器契约，约束 `patchFileWritten=false`、`patchApplied=false`、`dependencyPatchGenerated=false`、`diffArtifactWritten=false`、`dependencyFileChanged=false`。
- `providers/real_sdk_dependency_apply_gate.py`：真实 SDK 依赖 apply gate 禁用壳，只评估未来补丁应用任务的最终人工批准、回滚、备份和禁止执行策略；当前不授权 apply、不写文件、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-apply-gate.contract.json`：真实 SDK 依赖 apply gate 机器契约，约束 `applyAuthorized=false`、`applyApprovalMaterialized=false`、`patchApplied=false`、`dependencyFileChanged=false`、`secretPresenceChecked=false`。
- `providers/real_sdk_dependency_implementation_task_plan.py`：真实 SDK 依赖实现任务计划禁用壳，只生成未来依赖文件变更的受控施工单；当前不创建任务、不写依赖文件、不生成 patch、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-implementation-task-plan.contract.json`：真实 SDK 依赖实现任务计划机器契约，约束 `dependencyImplementationTaskCreated=false`、`dependencyFileChanged=false`、`patchMaterialized=false`、`commandExecutionAuthorized=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_change_approval_package.py`：真实 SDK 依赖变更人工批准包禁用壳，只生成未来依赖文件变更的本地批准包模型；当前不写批准文件、不授予人工批准、不创建任务、不写依赖文件、不检查密钥、不联网。
- `providers/real-sdk-dependency-change-approval-package.contract.json`：真实 SDK 依赖变更人工批准包机器契约，约束 `approvalPackageWritten=false`、`manualApprovalGranted=false`、`dependencyFileChanged=false`、`commandExecutionAuthorized=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_readonly_diff_review.py`：真实 SDK 依赖只读差异审查禁用壳，只生成未来依赖文件变更的本地只读审查模型；当前不读取依赖文件、不写审查文件、不生成 patch、不写依赖文件、不检查密钥、不联网。
- `providers/real-sdk-dependency-readonly-diff-review.contract.json`：真实 SDK 依赖只读差异审查机器契约，约束 `diffReviewArtifactWritten=false`、`dependencySnapshotReadFromFile=false`、`patchGenerated=false`、`dependencyFileChanged=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_final_execution_confirmation.py`：真实 SDK 依赖最终执行确认禁用壳，只生成未来依赖文件变更的本地最终确认模型；当前不授予执行批准、不创建任务、不写依赖文件、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-final-execution-confirmation.contract.json`：真实 SDK 依赖最终执行确认机器契约，约束 `executionApprovalGranted=false`、`executionTaskCreated=false`、`dependencyFileMutationAuthorized=false`、`commandExecuted=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_execution_task_creation.py`：真实 SDK 依赖执行任务创建禁用壳，只生成未来依赖文件变更的本地任务创建模型；当前不创建或持久化任务、不入队、不派发执行、不写依赖文件、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-execution-task-creation.contract.json`：真实 SDK 依赖执行任务创建机器契约，约束 `executionTaskCreated=false`、`taskPersisted=false`、`taskQueued=false`、`executionDispatched=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_executor_disabled.py`：真实 SDK 依赖执行器禁用壳，只生成未来依赖执行器的本地禁用模型；当前不启动执行器、不创建 executor run、不物化命令、不执行命令、不写依赖文件、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-executor-disabled.contract.json`：真实 SDK 依赖执行器禁用壳机器契约，约束 `executorStarted=false`、`executorRunCreated=false`、`commandMaterialized=false`、`commandExecuted=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_dry_run_evidence.py`：真实 SDK 依赖 dry-run evidence 禁用壳，只生成未来安装命令审阅证据模型；当前不写 evidence 文件、不持久化审阅记录、不物化命令、不执行 dry-run、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-dry-run-evidence.contract.json`：真实 SDK 依赖 dry-run evidence 机器契约，约束 `dryRunExecuted=false`、`evidenceFileWritten=false`、`commandReviewRecordPersisted=false`、`commandMaterialized=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_target_resolver.py`：真实 SDK 依赖 target resolver 禁用壳，只生成未来依赖清单和 lockfile 目标候选模型；当前不读取真实依赖文件、不写目标文件、不生成 patch、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-target-resolver.contract.json`：真实 SDK 依赖 target resolver 机器契约，约束 `targetPathResolutionExecuted=false`、`liveDependencyFileRead=false`、`targetFileWritten=false`、`patchGenerated=false`、`commandExecuted=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_readonly_snapshot.py`：真实 SDK 依赖 readonly snapshot 禁用壳，只生成未来依赖清单和 lockfile 快照审查模型；当前不读取真实依赖文件、不捕获 snapshot 内容、不写 snapshot 文件、不持久化审查记录、不生成 patch、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-readonly-snapshot.contract.json`：真实 SDK 依赖 readonly snapshot 机器契约，约束 `dependencySnapshotReadFromFile=false`、`dependencySnapshotContentCaptured=false`、`snapshotFileWritten=false`、`snapshotReviewRecordPersisted=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_content_read_approval.py`：真实 SDK 依赖 content read approval 禁用壳，只生成未来依赖文件内容读取审批模型；当前不读取依赖文件内容、不返回原文、不持久化内容或审批记录、不写审批产物、不生成 patch、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-content-read-approval.contract.json`：真实 SDK 依赖 content read approval 机器契约，约束 `dependencyContentReadAuthorized=false`、`dependencyContentReadExecuted=false`、`dependencyContentReturned=false`、`contentReadApprovalArtifactWritten=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_content_read_plan.py`：真实 SDK 依赖 content read plan 禁用壳，只生成未来依赖文件内容读取只读审查计划模型；当前不读取依赖文件内容、不返回原文、不持久化内容或计划记录、不写计划产物、不生成 patch、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-content-read-plan.contract.json`：真实 SDK 依赖 content read plan 机器契约，约束 `dependencyContentReadAuthorized=false`、`dependencyContentReadExecuted=false`、`dependencyContentReturned=false`、`contentReadPlanArtifactWritten=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_content_read_final_confirmation.py`：真实 SDK 依赖 content read final confirmation 禁用壳，只生成未来依赖文件内容只读读取前最终确认模型；当前不读取依赖文件内容、不返回原文、不持久化内容或确认记录、不写确认产物、不创建执行任务、不授权读取执行、不生成 patch、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-content-read-final-confirmation.contract.json`：真实 SDK 依赖 content read final confirmation 机器契约，约束 `dependencyContentReadAuthorized=false`、`dependencyContentReadExecuted=false`、`dependencyContentReturned=false`、`contentReadFinalConfirmationArtifactWritten=false`、`contentReadExecutionTaskCreated=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_content_read_readonly_execution.py`：真实 SDK 依赖 content read readonly execution，只在最终确认后读取允许名单内本地依赖文件并返回脱敏预览；当前不返回原文、不持久化内容或记录、不写读取产物、不生成 patch、不执行命令、不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-content-read-readonly-execution.contract.json`：真实 SDK 依赖 content read readonly execution 机器契约，允许本地只读脱敏预览，并约束 `rawDependencyContentReturned=false`、`dependencyContentPersisted=false`、`contentReadReadonlyExecutionArtifactWritten=false`、`dependencyInstallExecuted=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_install_change_proposal.py`：真实 SDK 依赖 install change proposal，只基于只读脱敏预览生成未来安装变更方案和不可执行 patch 预览；当前不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-install-change-proposal.contract.json`：真实 SDK 依赖 install change proposal 机器契约，约束 `dependencyInstallPatchPlanGenerated=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_install_execution_gate.py`：真实 SDK 依赖 install execution gate，只基于已审核安装变更方案生成未来安装执行门禁模型；当前不授权执行、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-install-execution-gate.contract.json`：真实 SDK 依赖 install execution gate 机器契约，约束 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_install_authorization_package.py`：真实 SDK 依赖 install authorization package，只基于安装执行门禁生成未来安装授权包模型；当前不授权执行、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-install-authorization-package.contract.json`：真实 SDK 依赖 install authorization package 机器契约，约束 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_install_execution_request.py`：真实 SDK 依赖 install execution request，只基于安装授权包生成未来安装执行请求模型；当前不授权执行、不派发执行器、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-install-execution-request.contract.json`：真实 SDK 依赖 install execution request 机器契约，约束 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_sdk_dependency_install_executor_disabled.py`：真实 SDK 依赖 install executor disabled，只基于安装执行请求生成禁用执行器模型；当前不派发执行器、不启动执行器、不创建 executor run、不授权执行、不写依赖文件、不写 patch 文件、不应用 patch、不物化命令、不执行命令、不安装 SDK、不解析包、不检查密钥、不联网。
- `providers/real-sdk-dependency-install-executor-disabled.contract.json`：真实 SDK 依赖 install executor disabled 机器契约，约束 `executorDispatched=false`、`executorStarted=false`、`executorRunCreated=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_llm_sdk_boundary.py`：真实 LLM SDK 安装和环境变量边界检查，只读取 `requirements.txt` 依赖声明、解析本地 `openai` 包元数据、可选检查 `OPENAI_API_KEY` 环境变量名是否存在；不导入 SDK、不创建客户端、不读取密钥值、不联网、不真实调用。
- `providers/real-llm-sdk-boundary.contract.json`：真实 LLM SDK 边界检查机器契约，约束 `sdkImportAttempted=false`、`sdkImported=false`、`clientCreated=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_llm_sdk_client_boundary.py`：真实 LLM SDK client 构造边界，显式确认后允许导入 `openai` SDK、读取 `OPENAI_API_KEY` 仅用于构造本地 client；不返回或记录密钥、不发起模型请求、不联网、不生成内容。
- `providers/real-llm-sdk-client-boundary.contract.json`：真实 LLM SDK client 构造边界契约，约束 `clientCreated=true` 也不代表真实调用授权，`networkAccess=false`、`realLlmCalled=false`、`secretValueReturned=false`。
- `providers/real_llm_runtime_config.py`：真实 LLM 运行时配置只读摘要，可汇总 `OPENAI_API_KEY` 是否存在以及模型名 / base URL 的环境变量或 CLI 参数来源，并返回 `commandReadiness` 与无密钥 `safeCommandTemplates` 供操作者复制检查命令和 workflow 参数；不接受 key 参数、不返回密钥值、不导入 SDK、不创建 client、不发送请求。
- `providers/real_llm_minimal_poc.py`：真实 LLM 最小单请求 PoC，显式 opt-in 后读取 `OPENAI_API_KEY`、创建 OpenAI client、发送一次 Responses API 请求，返回 Lab DSL JSON；本地校验 schema 和 `WAITING_REVIEW` 状态，不 batch、不 streaming、不发布。
- `providers/real_llm_request_review_package.py`：真实 LLM 首个请求审核包，只生成本地脱敏 request shape、schema/timeout/retry 配置和人工审核 checklist；不导入 SDK、不创建 client、不检查或读取密钥、不发送请求。
- `providers/real-llm-request-review-package.contract.json`：真实 LLM 请求审核包机器契约，约束 `requestReviewPackageReady=true` 也不代表真实调用授权，`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_llm_first_call_approval_gate.py`：真实 LLM 首次调用最终批准门禁，只评估本地批准清单和未来执行器准入；不授予发送授权、不发送请求、不联网、不真实调用、不创建任务。
- `providers/real-llm-first-call-approval-gate.contract.json`：真实 LLM 首次调用最终批准门禁契约，约束 `readyForDisabledFirstCallExecutor=true` 也不代表真实调用授权，`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_llm_first_call_executor_disabled.py`：真实 LLM 首次调用禁用执行器，只准备本地执行器计划；不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不创建任务。
- `providers/real-llm-first-call-executor-disabled.contract.json`：真实 LLM 首次调用禁用执行器契约，约束 `disabledFirstCallExecutorReady=true` 也不代表真实请求发送许可，`readyForRealRequestSend=false`、`executorDispatched=false`、`requestSent=false`、`realLlmCalled=false`。
- `providers/real_llm_pre_send_dry_run_record.py`：真实 LLM 发送前 dry-run 记录，只生成本地审计记录模型；不执行 dry-run、不写记录、不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不创建任务。
- `providers/real-llm-pre-send-dry-run-record.contract.json`：真实 LLM 发送前 dry-run 记录契约，约束 `preSendDryRunRecordReady=true` 也不代表真实请求发送许可，`readyForRealRequestSend=false`、`dryRunExecuted=false`、`dryRunRecordWritten=false`、`requestSent=false`、`realLlmCalled=false`。
- `providers/real_llm_minimal_call_poc_review.py`：真实 LLM 最小调用 PoC 实现评审，只生成未来单次 Lab JSON 请求的本地评审包；不发送请求、不联网、不读取密钥、不真实调用、不创建任务、不发布。
- `providers/real-llm-minimal-call-poc-review.contract.json`：真实 LLM 最小调用 PoC 实现评审契约，约束 `minimalCallPocReviewReady=true` 也不代表真实发送许可，`readyForRealRequestSend=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_llm_minimal_call_send_executor_disabled.py`：真实 LLM 最小调用发送执行器禁用壳，只生成未来发送执行器的本地禁用模型；不创建真实发送实现、不派发执行器、不发送请求、不联网、不读取密钥、不真实调用、不创建任务、不发布。
- `providers/real-llm-minimal-call-send-executor-disabled.contract.json`：真实 LLM 最小调用发送执行器禁用壳契约，约束 `minimalCallSendExecutorDisabledReady=true` 也不代表真实请求发送许可，`readyForRealRequestSend=false`、`sendExecutorDispatched=false`、`requestSent=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`。
- `providers/real_llm_request_send_authorization_package.py`：真实 LLM 请求发送最终授权包，只生成未来真实请求发送的本地人工授权包模型；不授予人工批准、不授权真实调用、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-authorization-package.contract.json`：真实 LLM 请求发送最终授权包契约，约束 `requestSendAuthorizationPackageReady=true` 也不代表真实请求发送许可，`manualApprovalGranted=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`requestSent=false`。
- `providers/real_llm_request_send_execution_request_disabled.py`：真实 LLM 请求发送执行请求禁用壳，只生成未来真实请求发送的本地执行请求模型；不授予人工批准、不授权真实调用、不持久化/入队/派发执行请求、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-execution-request-disabled.contract.json`：真实 LLM 请求发送执行请求禁用壳契约，约束 `requestSendExecutionRequestDisabledReady=true` 也不代表真实请求发送许可，`readyForRealRequestSend=false`、`executionRequestPersisted=false`、`executionRequestDispatched=false`、`requestSent=false`。
- `providers/real_llm_request_send_executor_disabled.py`：真实 LLM 请求发送执行器禁用壳，只生成未来真实请求发送的本地执行器模型；不授予人工批准、不授权真实调用、不创建/启动/派发执行器、不创建运行记录、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-executor-disabled.contract.json`：真实 LLM 请求发送执行器禁用壳契约，约束 `requestSendExecutorDisabledReady=true` 也不代表真实请求发送许可，`readyForRealRequestSend=false`、`sendExecutorStarted=false`、`sendExecutorDispatched=false`、`requestSent=false`。
- `providers/real_llm_request_send_final_approval_review.py`：真实 LLM 请求发送最终批准评审，只生成未来真实请求发送的本地最终人工批准评审模型；不授予人工批准、不授权真实调用、不写批准记录、不派发执行器、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-final-approval-review.contract.json`：真实 LLM 请求发送最终批准评审契约，约束 `requestSendFinalApprovalReviewReady=true` 也不代表真实请求发送许可，`manualApprovalGranted=false`、`realCallAuthorized=false`、`approvalRecordWritten=false`、`requestSent=false`。
- `providers/real_llm_request_send_authorization_task_disabled.py`：真实 LLM 请求发送授权任务禁用模型，只生成未来真实请求发送的本地授权任务禁用模型；不创建/持久化/入队/派发任务、不写授权记录、不授予人工批准、不授权真实调用、不发送请求、不联网、不读取密钥、不创建内容、不发布。
- `providers/real-llm-request-send-authorization-task-disabled.contract.json`：真实 LLM 请求发送授权任务禁用契约，约束 `requestSendAuthorizationTaskDisabledReady=true` 也不代表真实请求发送许可，`authorizationTaskCreated=false`、`authorizationRecordWritten=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`requestSent=false`。
- `providers/real_llm_request_send_authorization_record_write_gate.py`：真实 LLM 请求发送授权记录写入门禁，只生成未来真实请求发送的本地授权记录写入门禁模型；不写授权记录或批准记录、不授予人工批准、不授权真实调用、不派发执行器、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-authorization-record-write-gate.contract.json`：真实 LLM 请求发送授权记录写入门禁契约，约束 `authorizationRecordWriteGateReady=true` 也不代表真实请求发送许可，`authorizationRecordWritten=false`、`approvalRecordWritten=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`requestSent=false`。
- `providers/real_llm_request_send_runtime_gate_disabled.py`：真实 LLM 请求发送运行时门禁禁用壳，只生成未来真实请求发送的本地运行时门禁模型；不打开运行时门禁、不关闭 kill switch、不预留预算、不打开网络出口、不创建 client/执行器、不授权真实调用、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-runtime-gate-disabled.contract.json`：真实 LLM 请求发送运行时门禁禁用契约，约束 `requestSendRuntimeGateDisabledReady=true` 也不代表真实请求发送许可，`runtimeGateOpened=false`、`runtimeKillSwitchDisabled=false`、`runtimeBudgetReserved=false`、`runtimeNetworkEgressOpened=false`、`realCallAuthorized=false`、`requestSent=false`。
- `providers/real_llm_request_send_executor_creation_gate_disabled.py`：真实 LLM 请求发送执行器创建门禁禁用壳，只生成未来真实请求发送的本地执行器创建门禁模型；不物化 factory、不创建/持久化/启动执行器、不创建运行记录、不派发执行器、不创建 client、不授权真实调用、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-executor-creation-gate-disabled.contract.json`：真实 LLM 请求发送执行器创建门禁禁用契约，约束 `requestSendExecutorCreationGateDisabledReady=true` 也不代表真实请求发送许可，`executorFactoryMaterialized=false`、`sendExecutorCreated=false`、`sendExecutorDispatched=false`、`realCallAuthorized=false`、`requestSent=false`。
- `providers/real_llm_request_send_executor_dispatch_gate_disabled.py`：真实 LLM 请求发送执行器派发门禁禁用壳，只生成未来真实请求发送的本地执行器派发门禁模型；不写派发队列、不持久化派发记录、不派发执行器、不启动执行器、不创建运行记录、不创建 client、不授权真实调用、不发送请求、不联网、不读取密钥、不创建任务、不发布。
- `providers/real-llm-request-send-executor-dispatch-gate-disabled.contract.json`：真实 LLM 请求发送执行器派发门禁禁用契约，约束 `requestSendExecutorDispatchGateDisabledReady=true` 也不代表真实请求发送许可，`dispatchQueueWritten=false`、`dispatchRecordPersisted=false`、`sendExecutorDispatched=false`、`requestSendAttempted=false`、`requestSent=false`。
- `providers/real_llm_request_send_attempt_gate_disabled.py`：真实 LLM 请求发送尝试门禁禁用壳，只生成未来真实请求发送的本地发送尝试门禁模型；不持久化尝试记录、不尝试发送请求、不发送请求、不创建 client、不联网、不读取密钥、不真实调用、不创建内容、不创建任务、不发布。
- `providers/real-llm-request-send-attempt-gate-disabled.contract.json`：真实 LLM 请求发送尝试门禁禁用契约，约束 `requestSendAttemptGateDisabledReady=true` 也不代表真实请求发送许可，`attemptRecordPersisted=false`、`requestSendAttempted=false`、`requestSent=false`、`clientCreated=false`、`realLlmCalled=false`。
- `providers/provider-adapter-errors.contract.json`：Provider Adapter 错误矩阵契约，声明禁用 Provider、缺少 Prompt、未知 Prompt、outputKind 不匹配和 streamGenerate 暂缓等安全失败路径。
- `providers/provider-audit.contract.json`：Provider Adapter 调用审计契约，声明 registry、health、generateJson 的成功/失败本地审计要求。
- `cli/provider_audit.py`：Provider 调用审计事件模型，写入本地 `providerCallAuditEvents`。
- `ai-workflows/provider-audit-workflow.contract.json`：Workflow 级 Provider 审计契约，要求单步生成和 `phase1_main_demo` 生成步骤写入同一套审计事件。
- `ai_workflows/provider_adapter_workflow.py`：Workflow 侧 helper，让 Lab / Exam / Grading / PPT Mock 生成统一通过 Adapter。
- `prompts/manifest.json`：Provider 只读取 Prompt 元数据和 Prompt 文件路径，不在业务代码里内嵌 Prompt。
- `templates/*/examples/*.yaml`：Mock 输出使用本地 DSL 示例，并进行 Schema 校验。

## 输出说明

Provider Mock 返回统一结构：

```json
{
  "providerId": "mock",
  "mode": "MOCK_ONLY",
  "promptId": "lab_generation_v0",
  "outputKind": "Lab",
  "generatedStatus": "WAITING_REVIEW",
  "reviewRequired": true,
  "realLlmCalled": false,
  "secretsRead": false,
  "networkAccess": false
}
```

Provider Adapter 失败响应会额外返回 `providerErrorContext`，用于确认失败路径仍保持 `MOCK_ONLY`，且 `realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`、`generatedContentCreated=false`、`taskCreated=false`。

真实 Provider 预检失败响应会返回 `providerGateContext`，用于确认即使传入 `openai`、`anthropic` 或 `local`，当前也只做本地门禁判断，不读取或输出密钥值，不发起真实调用：

```json
{
  "providerId": "openai",
  "defaultProvider": "mock",
  "readyForRealProvider": false,
  "realLlmCalled": false,
  "secretsRead": false,
  "networkAccess": false,
  "secretValueReturned": false
}
```

真实 Provider 空壳的 `health` 只返回禁用摘要；生成命令失败时会返回 `providerShellContext`：

```json
{
  "providerId": "openai",
  "shellImplementationStatus": "disabled_shell",
  "readyForRealProvider": false,
  "sdkImported": false,
  "clientCreated": false,
  "realLlmCalled": false,
  "secretsRead": false,
  "networkAccess": false
}
```

Provider Runtime Guard 成功只代表本地护栏配置完整，不代表真实 Provider 可调用；CLI 会返回 `providerRuntimeGuardContext` 或 `data` 中的安全上下文：

```json
{
  "guardId": "provider_runtime_guard",
  "providerId": "openai",
  "timeoutConfigured": true,
  "retryConfigured": true,
  "concurrencyLimitConfigured": true,
  "redactionApplied": true,
  "schemaValidationRequired": true,
  "generatedStatus": "WAITING_REVIEW",
  "readyForRealProvider": false,
  "realLlmCalled": false,
  "secretsRead": false,
  "networkAccess": false
}
```

真实 LLM PoC Adapter 只串联本地门禁和禁用空壳，`describe` 返回禁用摘要；`generate-json` 当前必须安全失败并返回 `realLlmPocAdapterContext`：

```json
{
  "adapterId": "real_llm_poc_adapter",
  "defaultProvider": "mock",
  "adapterEnabled": false,
  "readyForRealProvider": false,
  "sdkImported": false,
  "clientCreated": false,
  "realLlmCalled": false,
  "secretsRead": false,
  "networkAccess": false
}
```

真实 LLM dry-run 计划用于接入前验收，成功只代表本地计划和护栏通过，仍固定不发起真实调用：

```json
{
  "planId": "real_llm_dry_run_plan",
  "dryRunOnly": true,
  "runtimeGuardPassed": true,
  "readyForRealProvider": false,
  "secretPresenceChecked": false,
  "secretValueRead": false,
  "realLlmCalled": false,
  "taskCreated": false
}
```

真实 LLM 最小单请求 PoC 成功后会标记真实调用审计：

```json
{
  "mode": "REAL_LLM_MINIMAL_SINGLE_REQUEST",
  "providerId": "openai",
  "requestCount": 1,
  "singleRequestOnly": true,
  "realLlmCalled": true,
  "networkAccess": true,
  "schemaValidated": true,
  "generatedStatus": "WAITING_REVIEW",
  "taskCreated": true,
  "autoPublishAllowed": false,
  "realPublish": false
}
```

真实 LLM SDK 批准门禁用于真实 SDK 实现任务前的本地检查；完整确认后只表示“可以进入实现任务评审”，仍不会授权真实调用：

```json
{
  "gateId": "real_llm_approval_gate",
  "approvalChecklistPassed": true,
  "readyForImplementationTask": true,
  "realCallAuthorized": false,
  "secretValueRead": false,
  "realLlmCalled": false,
  "networkAccess": false
}
```

真实 LLM SDK 任务蓝图用于把批准门禁结果转成未来实现任务清单；即使 `blueprintReady=true`，当前也不会安装 SDK、修改运行时契约或授权真实调用：

```json
{
  "blueprintId": "real_llm_sdk_task_blueprint",
  "blueprintReady": true,
  "readyForImplementationTask": true,
  "implementationAllowed": false,
  "realCallAuthorized": false,
  "sdkDependencyInstalled": false,
  "providerContractChangeApplied": false,
  "runtimeContractChangeApplied": false,
  "networkAccess": false
}
```

真实 Provider SDK PoC harness 用于验证“蓝图通过后仍停在禁用门禁”的本地路径；`describe` 返回禁用摘要，`generate-json` 当前必须返回安全错误和 `realProviderSdkPocContext`：

```json
{
  "pocId": "real_provider_sdk_poc",
  "blueprintRequired": true,
  "sdkPocEnabled": false,
  "sdkImported": false,
  "secretPresenceChecked": false,
  "realLlmCalled": false,
  "networkAccess": false,
  "taskCreated": false
}
```

真实 SDK enablement 用于最终开关设计评审；即使所有确认项通过，也只允许进入未来实现任务评审，不会修改契约或授权真实调用：

```json
{
  "enablementId": "real_sdk_enablement",
  "switchDesignReady": true,
  "readyForRealSdkImplementationTask": true,
  "implementationAllowed": false,
  "realCallAuthorized": false,
  "providerContractChangeApplied": false,
  "runtimeContractChangeApplied": false,
  "secretPresenceChecked": false,
  "networkAccess": false
}
```

真实 SDK 最小实现外壳用于验证未来 SDK implementation 的命令形态；即使 enablement 与显式 opt-in 都满足，也仍停在默认禁用门禁：

```json
{
  "implementationId": "real_sdk_minimal_impl",
  "enablementReady": true,
  "explicitImplementationOptIn": true,
  "sdkImplementationEnabled": false,
  "sdkImported": false,
  "clientCreated": false,
  "secretPresenceChecked": false,
  "networkAccess": false,
  "realLlmCalled": false,
  "taskCreated": false
}
```

真实 SDK 依赖与环境变量门禁用于评审未来依赖安装和环境变量存在性检查任务；即使全部确认项满足，也只表示可进入后续独立任务，不安装 SDK、不解析版本、不检查密钥：

```json
{
  "gateId": "real_sdk_dependency_env_gate",
  "dependencyEnvChecklistPassed": true,
  "readyForDependencyImplementationTask": true,
  "dependencyInstallAllowed": false,
  "sdkDependencyInstalled": false,
  "sdkImported": false,
  "secretPresenceChecked": false,
  "networkAccess": false
}
```

真实 SDK 依赖安装计划用于评审未来依赖安装实现任务；即使全部确认项满足，也只表示可进入后续独立任务评审，不生成安装命令、不安装 SDK、不解析包版本或 hash、不修改 lockfile、不检查密钥：

```json
{
  "planId": "real_sdk_dependency_install_plan",
  "dependencyEnvGateReady": true,
  "installPlanChecklistPassed": true,
  "readyForDependencyInstallImplementationReview": true,
  "dependencyInstallCommandGenerated": false,
  "dependencyInstallExecuted": false,
  "packageVersionResolved": false,
  "packageHashResolved": false,
  "dependencyLockfileChanged": false,
  "secretPresenceChecked": false,
  "networkAccess": false
}
```

真实 SDK 依赖安装执行审计用于评审未来“禁用安装执行壳”实现任务；即使全部确认项满足，也只表示可进入后续实现任务评审，不物化命令、不安装 SDK、不解析包版本或 hash、不修改文件、不检查密钥：

```json
{
  "auditId": "real_sdk_dependency_installer_audit",
  "installPlanReady": true,
  "installerAuditChecklistPassed": true,
  "readyForInstallerImplementationTask": true,
  "installerExecutionEnabled": false,
  "installCommandMaterialized": false,
  "dependencyInstallExecuted": false,
  "dependencyFileChanged": false,
  "lockfileDiffGenerated": false,
  "secretPresenceChecked": false,
  "networkAccess": false
}
```

真实 SDK 依赖变更预览用于评审未来“依赖清单和锁文件变更实现任务”；即使全部确认项满足，也只表示可进入后续实现任务评审，不写文件、不生成 diff、不安装 SDK、不解析包版本或 hash、不检查密钥：

```json
{
  "previewId": "real_sdk_dependency_change_preview",
  "installerAuditReady": true,
  "changePreviewChecklistPassed": true,
  "readyForDependencyChangeImplementationTask": true,
  "dependencyFileChanged": false,
  "dependencyDiffGenerated": false,
  "lockfileDiffGenerated": false,
  "diffArtifactWritten": false,
  "dependencyInstallExecuted": false,
  "secretPresenceChecked": false,
  "networkAccess": false
}
```

真实 SDK 依赖 patch proposal 用于评审未来“补丁文件和补丁应用实现任务”；即使全部确认项满足，也只表示可进入后续实现任务评审，不写 patch 文件、不应用补丁、不写依赖文件、不生成 diff artifact、不安装 SDK、不解析包版本或 hash、不检查密钥：

```json
{
  "proposalId": "real_sdk_dependency_patch_proposal",
  "changePreviewReady": true,
  "patchProposalChecklistPassed": true,
  "readyForDependencyPatchImplementationTask": true,
  "patchFileWritten": false,
  "patchApplied": false,
  "dependencyPatchGenerated": false,
  "diffArtifactWritten": false,
  "dependencyFileChanged": false,
  "secretPresenceChecked": false,
  "networkAccess": false
}
```

真实 SDK 依赖 apply gate 用于评审未来“真正应用依赖补丁任务”的最终门禁；即使全部确认项满足，也只表示可进入单独的后续 apply 任务评审，不授权 apply、不写依赖文件、不执行命令、不检查密钥：

```json
{
  "gateId": "real_sdk_dependency_apply_gate",
  "gateMode": "DEPENDENCY_APPLY_GATE_DISABLED_ONLY",
  "patchProposalRequired": true,
  "applyGateChecklistPassed": false,
  "readyForFutureDependencyPatchApplyTask": false,
  "applyAuthorized": false,
  "patchApplied": false,
  "dependencyFileChanged": false,
  "secretPresenceChecked": false,
  "networkAccess": false
}
```

Provider 调用审计返回 `providerCallAuditEvent`，并可按 Provider、操作、状态、Prompt、Trace、人员过滤：

```json
{
  "operation": "generateJson",
  "providerId": "mock",
  "status": "FAILED",
  "errorCode": "NOT_FOUND",
  "mode": "MOCK_ONLY",
  "realLlmCalled": false,
  "secretsRead": false,
  "networkAccess": false
}
```

## 命令示例

```powershell
python lab_cli.py provider list
python lab_cli.py provider health
python lab_cli.py provider mock-generate --prompt-id lab_generation_v0
python lab_cli.py provider mock-generate --prompt-id exam_generation_v0 --output-kind Exam
python lab_cli.py provider mock-generate --prompt-id missing_prompt
python lab_cli.py provider real-preflight --provider openai
python lab_cli.py provider real-preflight --provider openai --explicit-opt-in
python lab_cli.py provider real-shell list
python lab_cli.py provider real-shell health --provider openai
python lab_cli.py provider real-shell generate-json --provider openai
python lab_cli.py provider real-shell generate-json --provider openai --explicit-opt-in
python lab_cli.py provider runtime-guard --provider openai
python lab_cli.py provider runtime-guard --provider openai --payload "{\"apiKey\":\"demo-redacted-value\"}"
python lab_cli.py provider real-poc-adapter describe
python lab_cli.py provider real-poc-adapter generate-json --provider openai
python lab_cli.py provider real-poc-adapter generate-json --provider openai --explicit-opt-in
python lab_cli.py provider real-dry-run plan --provider openai
python lab_cli.py provider real-dry-run plan --provider openai --payload "{\"apiKey\":\"demo-redacted-value\"}"
python lab_cli.py provider real-approval-gate check --provider openai
python lab_cli.py provider real-approval-gate check --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction
python lab_cli.py provider real-sdk-blueprint plan --provider openai
python lab_cli.py provider real-sdk-blueprint plan --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction
python lab_cli.py provider real-sdk-poc describe
python lab_cli.py provider real-sdk-poc generate-json --provider openai
python lab_cli.py provider real-sdk-poc generate-json --provider openai --explicit-opt-in --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction
python lab_cli.py provider real-sdk-enablement describe
python lab_cli.py provider real-sdk-enablement check --provider openai
python lab_cli.py provider real-sdk-enablement check --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan
python lab_cli.py provider real-sdk-impl describe
python lab_cli.py provider real-sdk-impl generate-json --provider openai
python lab_cli.py provider real-sdk-impl generate-json --provider openai --explicit-implementation-opt-in --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan
python lab_cli.py provider real-sdk-dependency-env describe
python lab_cli.py provider real-sdk-dependency-env check --provider openai
python lab_cli.py provider real-sdk-dependency-env check --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy
python lab_cli.py provider real-sdk-dependency-install-plan describe
python lab_cli.py provider real-sdk-dependency-install-plan plan --provider openai
python lab_cli.py provider real-sdk-dependency-install-plan plan --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy --confirm-package-manager-review --confirm-lockfile-strategy-review --confirm-version-pin-strategy --confirm-hash-verification-strategy --confirm-rollback-files-review --confirm-ci-cache-policy --confirm-no-install-execution --confirm-no-network-policy --confirm-no-secret-policy
python lab_cli.py provider real-sdk-dependency-installer-audit describe
python lab_cli.py provider real-sdk-dependency-installer-audit audit --provider openai
python lab_cli.py provider real-sdk-dependency-installer-audit audit --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy --confirm-package-manager-review --confirm-lockfile-strategy-review --confirm-version-pin-strategy --confirm-hash-verification-strategy --confirm-rollback-files-review --confirm-ci-cache-policy --confirm-no-install-execution --confirm-no-network-policy --confirm-no-secret-policy --confirm-command-review --confirm-dependency-file-review --confirm-lockfile-diff-review --confirm-offline-ci-review --confirm-rollback-command-review --confirm-execution-disabled
python lab_cli.py provider real-sdk-dependency-change-preview describe
python lab_cli.py provider real-sdk-dependency-change-preview preview --provider openai
python lab_cli.py provider real-sdk-dependency-change-preview preview --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy --confirm-package-manager-review --confirm-lockfile-strategy-review --confirm-version-pin-strategy --confirm-hash-verification-strategy --confirm-rollback-files-review --confirm-ci-cache-policy --confirm-no-install-execution --confirm-no-network-policy --confirm-no-secret-policy --confirm-command-review --confirm-dependency-file-review --confirm-lockfile-diff-review --confirm-offline-ci-review --confirm-rollback-command-review --confirm-execution-disabled --confirm-preview-scope --confirm-manifest-preview --confirm-lockfile-preview --confirm-rollback-preview --confirm-no-diff-generation --confirm-no-file-write
python lab_cli.py provider real-sdk-dependency-patch-proposal describe
python lab_cli.py provider real-sdk-dependency-patch-proposal propose --provider openai
python lab_cli.py provider real-sdk-dependency-patch-proposal propose --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy --confirm-package-manager-review --confirm-lockfile-strategy-review --confirm-version-pin-strategy --confirm-hash-verification-strategy --confirm-rollback-files-review --confirm-ci-cache-policy --confirm-no-install-execution --confirm-no-network-policy --confirm-no-secret-policy --confirm-command-review --confirm-dependency-file-review --confirm-lockfile-diff-review --confirm-offline-ci-review --confirm-rollback-command-review --confirm-execution-disabled --confirm-preview-scope --confirm-manifest-preview --confirm-lockfile-preview --confirm-rollback-preview --confirm-no-diff-generation --confirm-no-file-write --confirm-patch-scope --confirm-patch-plan-review --confirm-no-patch-file-write --confirm-no-patch-apply --confirm-no-diff-artifact
python lab_cli.py provider real-sdk-dependency-apply-gate describe
python lab_cli.py provider real-sdk-dependency-apply-gate evaluate --provider openai
python lab_cli.py provider real-sdk-dependency-apply-gate evaluate --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy --confirm-package-manager-review --confirm-lockfile-strategy-review --confirm-version-pin-strategy --confirm-hash-verification-strategy --confirm-rollback-files-review --confirm-ci-cache-policy --confirm-no-install-execution --confirm-no-network-policy --confirm-no-secret-policy --confirm-command-review --confirm-dependency-file-review --confirm-lockfile-diff-review --confirm-offline-ci-review --confirm-rollback-command-review --confirm-execution-disabled --confirm-preview-scope --confirm-manifest-preview --confirm-lockfile-preview --confirm-rollback-preview --confirm-no-diff-generation --confirm-no-file-write --confirm-patch-scope --confirm-patch-plan-review --confirm-no-patch-file-write --confirm-no-patch-apply --confirm-no-diff-artifact --confirm-apply-scope --confirm-final-manual-approval --confirm-dependency-patch-proposal-review --confirm-dependency-file-backup-review --confirm-rollback-rehearsal-review --confirm-no-apply-execution --confirm-no-dependency-file-write --confirm-no-command-execution
python lab_cli.py provider real-sdk-dependency-implementation-task-plan describe
python lab_cli.py provider real-sdk-dependency-implementation-task-plan plan --provider openai
python lab_cli.py provider real-sdk-dependency-implementation-task-plan plan --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy --confirm-package-manager-review --confirm-lockfile-strategy-review --confirm-version-pin-strategy --confirm-hash-verification-strategy --confirm-rollback-files-review --confirm-ci-cache-policy --confirm-no-install-execution --confirm-no-network-policy --confirm-no-secret-policy --confirm-command-review --confirm-dependency-file-review --confirm-lockfile-diff-review --confirm-offline-ci-review --confirm-rollback-command-review --confirm-execution-disabled --confirm-preview-scope --confirm-manifest-preview --confirm-lockfile-preview --confirm-rollback-preview --confirm-no-diff-generation --confirm-no-file-write --confirm-patch-scope --confirm-patch-plan-review --confirm-no-patch-file-write --confirm-no-patch-apply --confirm-no-diff-artifact --confirm-apply-scope --confirm-final-manual-approval --confirm-dependency-patch-proposal-review --confirm-dependency-file-backup-review --confirm-rollback-rehearsal-review --confirm-no-apply-execution --confirm-no-dependency-file-write --confirm-no-command-execution --confirm-implementation-task-scope --confirm-change-window-review --confirm-dependency-manifest-target --confirm-lockfile-update-strategy --confirm-rollback-owner --confirm-post-change-test-owner --confirm-no-dependency-file-change --confirm-no-patch-materialization --confirm-no-task-creation --confirm-no-real-call-after-plan
python lab_cli.py provider real-sdk-dependency-change-approval-package describe
python lab_cli.py provider real-sdk-dependency-change-approval-package package --provider openai
python lab_cli.py provider real-sdk-dependency-change-approval-package package --provider openai --approval-ref APPROVAL-001 --reviewer teacher_1 --confirm-dry-run-plan --confirm-runtime-guard --confirm-schema-review --confirm-human-review-policy --confirm-audit-redaction --confirm-sdk-dependency-review --confirm-provider-contract-review --confirm-runtime-contract-review --confirm-secret-injection-review --confirm-network-access-review --confirm-rollback-plan --confirm-minimal-impl-review --confirm-sdk-package-review --confirm-sdk-version-pin-review --confirm-dependency-license-review --confirm-dependency-hash-review --confirm-env-var-name-review --confirm-env-example-review --confirm-secret-non-read-policy --confirm-ci-install-policy --confirm-package-manager-review --confirm-lockfile-strategy-review --confirm-version-pin-strategy --confirm-hash-verification-strategy --confirm-rollback-files-review --confirm-ci-cache-policy --confirm-no-install-execution --confirm-no-network-policy --confirm-no-secret-policy --confirm-command-review --confirm-dependency-file-review --confirm-lockfile-diff-review --confirm-offline-ci-review --confirm-rollback-command-review --confirm-execution-disabled --confirm-preview-scope --confirm-manifest-preview --confirm-lockfile-preview --confirm-rollback-preview --confirm-no-diff-generation --confirm-no-file-write --confirm-patch-scope --confirm-patch-plan-review --confirm-no-patch-file-write --confirm-no-patch-apply --confirm-no-diff-artifact --confirm-apply-scope --confirm-final-manual-approval --confirm-dependency-patch-proposal-review --confirm-dependency-file-backup-review --confirm-rollback-rehearsal-review --confirm-no-apply-execution --confirm-no-dependency-file-write --confirm-no-command-execution --confirm-implementation-task-scope --confirm-change-window-review --confirm-dependency-manifest-target --confirm-lockfile-update-strategy --confirm-rollback-owner --confirm-post-change-test-owner --confirm-no-dependency-file-change --confirm-no-patch-materialization --confirm-no-task-creation --confirm-no-real-call-after-plan --confirm-approver --confirm-approval-record-location --confirm-dependency-change-summary --confirm-rollback-evidence --confirm-test-evidence-plan --confirm-security-owner --confirm-maintenance-window --confirm-no-approval-artifact-write --confirm-no-dependency-change-execution --confirm-no-real-call-before-approval
python lab_cli.py provider real-sdk-dependency-readonly-diff-review describe
python lab_cli.py provider real-sdk-dependency-readonly-diff-review review --provider openai
python lab_cli.py provider real-sdk-dependency-final-execution-confirmation describe
python lab_cli.py provider real-sdk-dependency-final-execution-confirmation confirm --provider openai
python lab_cli.py provider real-sdk-dependency-execution-task-creation describe
python lab_cli.py provider real-sdk-dependency-execution-task-creation create --provider openai
python lab_cli.py provider real-sdk-dependency-executor-disabled describe
python lab_cli.py provider real-sdk-dependency-executor-disabled prepare --provider openai
python lab_cli.py provider real-llm-sdk-boundary describe
python lab_cli.py provider real-llm-sdk-boundary check --provider openai --explicit-sdk-boundary-opt-in --check-secret-presence
python lab_cli.py provider real-llm-sdk-client-boundary describe
python lab_cli.py provider real-llm-request-review describe
python lab_cli.py provider real-llm-first-call-approval describe
python lab_cli.py provider real-llm-first-call-executor-disabled describe
python lab_cli.py provider real-llm-pre-send-dry-run-record describe
python lab_cli.py provider real-llm-minimal-call-poc-review describe
python lab_cli.py provider real-llm-minimal-call-send-executor-disabled describe
python lab_cli.py provider real-llm-request-send-authorization-package describe
python lab_cli.py provider real-llm-request-send-execution-request-disabled describe
python lab_cli.py provider real-llm-request-send-executor-disabled describe
python lab_cli.py provider real-llm-request-send-final-approval-review describe
python lab_cli.py provider real-llm-request-send-authorization-task-disabled describe
python lab_cli.py provider real-llm-request-send-authorization-record-write-gate describe
python lab_cli.py provider real-llm-request-send-runtime-gate-disabled describe
python lab_cli.py provider real-llm-request-send-executor-creation-gate-disabled describe
python lab_cli.py provider real-llm-request-send-executor-dispatch-gate-disabled describe
python lab_cli.py provider real-llm-request-send-attempt-gate-disabled describe
python lab_cli.py provider real-sdk-dependency-dry-run-evidence describe
python lab_cli.py provider real-sdk-dependency-dry-run-evidence record --provider openai
python lab_cli.py provider real-sdk-dependency-target-resolver describe
python lab_cli.py provider real-sdk-dependency-target-resolver resolve --provider openai
python lab_cli.py provider real-sdk-dependency-readonly-snapshot describe
python lab_cli.py provider real-sdk-dependency-readonly-snapshot snapshot --provider openai
python lab_cli.py provider real-sdk-dependency-content-read-approval describe
python lab_cli.py provider real-sdk-dependency-content-read-approval approve-read --provider openai
python lab_cli.py provider real-sdk-dependency-content-read-plan describe
python lab_cli.py provider real-sdk-dependency-content-read-plan plan-read --provider openai
python lab_cli.py provider audit --operation generateJson
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1
python -m pytest tests/test_real_provider_gate.py
python -m pytest tests/test_real_provider_shell.py
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
python -m pytest tests/test_real_llm_sdk_boundary.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_phase2_provider_plan.py
```

Backend Mock 对应接口：

```text
GET /api/providers
GET /api/providers/mock/health
POST /api/providers/mock/generate
GET /api/provider-audit-events
```

## 测试方式

```powershell
python -m pytest tests/test_provider_contract.py tests/test_provider_mock.py
python -m pytest tests/test_real_provider_gate.py
python -m pytest tests/test_real_provider_shell.py
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
python -m pytest tests/test_real_llm_request_send_authorization_task_disabled.py
python -m pytest tests/test_real_llm_request_send_authorization_record_write_gate.py
python -m pytest tests/test_real_llm_request_send_runtime_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_creation_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_executor_dispatch_gate_disabled.py
python -m pytest tests/test_real_llm_request_send_attempt_gate_disabled.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest
```

## 限制说明

- Phase 1 只允许 `mock` Provider 启用。
- 不实例化 OpenAI、Anthropic 或本地真实模型 Provider。
- `OpenAIProvider`、`AnthropicProvider`、`LocalModelProvider` 当前只是禁用空壳，不导入真实 SDK、不创建真实客户端。
- 不读取 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 等密钥环境变量。
- 不访问网络，不调用真实 LLM。
- `provider real-sdk-dependency-env` 只做依赖与环境变量设计评审，不安装 SDK、不读取或检查 `OPENAI_API_KEY`、不修改 `.env.example` 或依赖锁文件。
- `provider real-sdk-dependency-install-plan` 只做依赖安装计划草案评审，不生成或执行安装命令、不安装 SDK、不解析包版本或 hash、不修改依赖清单或 lockfile、不检查密钥、不联网。
- `provider real-sdk-dependency-installer-audit` 只做安装执行前审计器禁用壳评审，不物化安装命令、不安装 SDK、不生成 lockfile diff、不修改依赖文件、不检查密钥、不联网。
- `provider real-sdk-dependency-change-preview` 只做依赖清单和锁文件变更预览评审，不写 `pyproject.toml`、`requirements.txt` 或 lockfile、不生成 diff artifact、不安装 SDK、不解析包版本或 hash、不检查密钥、不联网。
- `provider real-sdk-dependency-patch-proposal` 只做依赖 patch proposal 评审，不写 patch 文件、不应用补丁、不写依赖文件、不生成 diff artifact、不安装 SDK、不解析包版本或 hash、不检查密钥、不联网。
- `provider real-sdk-dependency-apply-gate` 只做未来补丁应用任务的最终门禁评审，不授权 apply、不写依赖文件、不执行命令、不安装 SDK、不检查密钥、不联网。
- `provider real-sdk-dependency-implementation-task-plan` 只做未来依赖文件变更任务的受控计划，不创建任务、不写依赖文件、不物化 patch、不执行命令、不安装 SDK、不检查密钥、不联网、不真实调用。
- `provider real-sdk-dependency-change-approval-package` 只生成未来依赖文件变更的人工批准包模型，不写批准文件、不授予人工批准、不创建任务、不写依赖文件、不执行命令、不安装 SDK、不检查密钥、不联网、不真实调用。
- `provider real-sdk-dependency-readonly-diff-review` 只生成未来依赖文件变更的只读差异审查模型，不读取依赖文件、不写审查文件、不生成 patch、不写依赖文件、不解析包版本或 hash、不执行命令、不安装 SDK、不检查密钥、不联网、不真实调用。
- `provider real-sdk-dependency-final-execution-confirmation` 只生成未来依赖文件变更的最终执行确认模型；完整确认后也只返回 `readyForReviewedDependencyExecutionTask=true`，仍固定 `executionApprovalGranted=false`、`executionTaskCreated=false`、`dependencyFileMutationAuthorized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-execution-task-creation` 只生成未来依赖文件变更的执行任务创建模型；完整确认后也只返回 `readyForDisabledDependencyExecutionTaskRecord=true`，仍固定 `executionTaskCreated=false`、`taskPersisted=false`、`taskQueued=false`、`executionDispatched=false`、`dependencyFileMutationAuthorized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-executor-disabled` 只生成未来依赖执行器的禁用模型；完整确认后也只返回 `readyForDisabledDependencyExecutor=true`，仍固定 `executorStarted=false`、`executorRunCreated=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-dry-run-evidence` 只生成未来安装命令 dry-run 的审阅证据模型；完整确认后也只返回 `readyForCommandReviewEvidence=true`，仍固定 `dryRunExecuted=false`、`evidenceFileWritten=false`、`commandReviewRecordPersisted=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-target-resolver` 只生成未来依赖清单和 lockfile 目标候选模型；完整确认后也只返回 `readyForDependencyTargetReview=true`，仍固定 `targetPathResolutionExecuted=false`、`liveDependencyFileRead=false`、`targetFileWritten=false`、`patchGenerated=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-readonly-snapshot` 只生成未来依赖清单和 lockfile 快照审查模型；完整确认后也只返回 `readyForReadonlyDependencySnapshotReview=true`，仍固定 `dependencySnapshotReadFromFile=false`、`dependencySnapshotContentCaptured=false`、`snapshotFileWritten=false`、`snapshotReviewRecordPersisted=false`、`patchGenerated=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-content-read-approval` 只生成未来依赖文件内容读取审批模型；完整确认后也只返回 `readyForFutureDependencyContentReadReview=true`，仍固定 `dependencyContentReadAuthorized=false`、`dependencyContentReadExecuted=false`、`dependencyManifestContentRead=false`、`dependencyLockfileContentRead=false`、`dependencyContentReturned=false`、`contentReadApprovalArtifactWritten=false`、`patchGenerated=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-content-read-plan` 只生成未来依赖文件内容读取只读审查计划模型；完整确认后也只返回 `readyForFutureDependencyContentReadExecutionReview=true`，仍固定 `dependencyContentReadAuthorized=false`、`dependencyContentReadExecuted=false`、`dependencyManifestContentRead=false`、`dependencyLockfileContentRead=false`、`dependencyContentReturned=false`、`contentReadPlanArtifactWritten=false`、`patchGenerated=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-install-change-proposal` 只生成未来真实 SDK 安装变更方案和不可执行 patch 预览；完整确认后也只返回 `installChangeProposalModelReady=true`，仍固定 `dependencyInstallPatchPlanGenerated=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-install-execution-gate` 只生成未来真实 SDK 安装执行门禁模型；完整确认后也只返回 `installExecutionGateModelReady=true`，仍固定 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-install-authorization-package` 只生成未来真实 SDK 安装授权包模型；完整确认后也只返回 `installAuthorizationPackageModelReady=true`，仍固定 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-install-execution-request` 只生成未来真实 SDK 安装执行请求模型；完整确认后也只返回 `installExecutionRequestModelReady=true`，仍固定 `dependencyInstallExecutionAuthorized=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`patchGenerated=false`、`patchFileWritten=false`、`patchApplied=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-sdk-dependency-install-executor-disabled` 只生成未来真实 SDK 安装禁用执行器模型；完整确认后也只返回 `installExecutorDisabledModelReady=true`，仍固定 `executorDispatched=false`、`executorStarted=false`、`executorRunCreated=false`、`executionAuthorized=false`、`dependencyFileWriteAuthorized=false`、`commandMaterialized=false`、`commandExecuted=false`、`dependencyInstallExecuted=false`、`packageVersionResolved=false`、`secretPresenceChecked=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-llm-sdk-boundary` 只做真实 SDK 安装后的本地边界检查；完整检查后也只返回 SDK/环境变量边界状态，仍固定 `realCallAuthorized=false`、`sdkImportAttempted=false`、`sdkImported=false`、`clientCreated=false`、`secretValueRead=false`、`networkAccess=false`、`realLlmCalled=false`。
- `provider real-llm-sdk-client-boundary` 只做真实 SDK client 构造边界；显式确认后允许导入 SDK、读取 `OPENAI_API_KEY` 并构造本地 client，但仍固定 `realCallAuthorized=false`、`networkAccess=false`、`realLlmCalled=false`、`generatedContentCreated=false`，且不返回或记录密钥值。
- `provider real-llm-request-review` 只生成首个真实请求的本地脱敏审核包；完整确认后也只返回 `readyForManualRequestReview=true`，仍固定 `readyForFirstRealCallApproval=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-first-call-approval` 只评估首个真实请求的最终批准门禁；完整确认后也只返回 `readyForDisabledFirstCallExecutor=true`，仍固定 `readyForFirstRealCallApproval=false`、`manualApprovalGranted=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-first-call-executor-disabled` 只准备首个真实请求的禁用执行器计划；完整确认后也只返回 `readyForMinimalRealCallPocReview=true`，仍固定 `readyForRealRequestSend=false`、`executorDispatched=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-pre-send-dry-run-record` 只生成首个真实请求发送前的本地 dry-run 审计记录模型；完整确认后也只返回 `readyForMinimalRealCallPoc=true`，仍固定 `readyForRealRequestSend=false`、`dryRunExecuted=false`、`dryRunRecordWritten=false`、`executorDispatched=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-minimal-call-poc-review` 只生成未来单次 Lab JSON 真实请求的本地实施评审包；完整确认后也只返回 `readyForMinimalRealCallImplementation=true`，仍固定 `readyForRealRequestSend=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`、`autoPublishAllowed=false`。
- `provider real-llm-minimal-call-send-executor-disabled` 只生成未来最小真实请求发送执行器的本地禁用模型；完整确认后也只返回 `readyForExplicitRealRequestSendAuthorization=true`，仍固定 `readyForRealRequestSend=false`、`sendImplementationCreated=false`、`sendExecutorMaterialized=false`、`sendExecutorDispatched=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`。
- `provider real-llm-request-send-authorization-package` 只生成未来真实请求发送的本地人工授权包模型；完整确认后也只返回 `readyForFinalManualSendAuthorizationReview=true`，仍固定 `manualApprovalGranted=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-execution-request-disabled` 只生成未来真实请求发送的本地执行请求禁用模型；完整确认后也只返回 `readyForDisabledRealRequestSendExecutor=true`，仍固定 `readyForRealRequestSend=false`、`executionRequestPersisted=false`、`executionRequestQueued=false`、`executionRequestDispatched=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-executor-disabled` 只生成未来真实请求发送的本地执行器禁用模型；完整确认后也只返回 `readyForFinalRealRequestSendApprovalReview=true`，仍固定 `readyForRealRequestSend=false`、`sendExecutorCreated=false`、`sendExecutorStarted=false`、`sendExecutorRunCreated=false`、`sendExecutorDispatched=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-final-approval-review` 只生成未来真实请求发送的本地最终人工批准评审模型；完整确认后也只返回 `readyForExplicitRealRequestSendAuthorizationTask=true`，仍固定 `manualApprovalGranted=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`approvalRecordWritten=false`、`sendExecutorDispatched=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-authorization-task-disabled` 只生成未来真实请求发送的本地授权任务禁用模型；完整确认后也只返回 `readyForAuthorizationRecordWriteGate=true`，仍固定 `authorizationTaskCreated=false`、`authorizationTaskPersisted=false`、`authorizationTaskQueued=false`、`authorizationTaskDispatched=false`、`authorizationRecordWritten=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-authorization-record-write-gate` 只生成未来真实请求发送的本地授权记录写入门禁模型；完整确认后也只返回 `readyForRequestSendRuntimeGate=true`，仍固定 `authorizationRecordWritten=false`、`approvalRecordWritten=false`、`manualApprovalGranted=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`sendExecutorDispatched=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-runtime-gate-disabled` 只生成未来真实请求发送的本地运行时门禁禁用模型；完整确认后也只返回 `readyForRealRequestSendExecutorCreationGate=true`，仍固定 `runtimeGateOpened=false`、`runtimeKillSwitchDisabled=false`、`runtimeBudgetReserved=false`、`runtimeNetworkEgressOpened=false`、`clientCreated=false`、`sendExecutorCreated=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-executor-creation-gate-disabled` 只生成未来真实请求发送的本地执行器创建门禁禁用模型；完整确认后也只返回 `readyForRealRequestSendExecutorDispatchGate=true`，仍固定 `executorFactoryMaterialized=false`、`sendExecutorCreated=false`、`sendExecutorPersisted=false`、`sendExecutorStarted=false`、`sendExecutorRunCreated=false`、`sendExecutorDispatched=false`、`clientCreated=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`requestSent=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-executor-dispatch-gate-disabled` 只生成未来真实请求发送的本地执行器派发门禁禁用模型；完整确认后也只返回 `readyForRealRequestSendAttemptGate=true`，仍固定 `dispatchQueueWritten=false`、`dispatchRecordPersisted=false`、`sendExecutorDispatched=false`、`executorDispatched=false`、`requestSendAttempted=false`、`requestSent=false`、`clientCreated=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-llm-request-send-attempt-gate-disabled` 只生成未来真实请求发送的本地发送尝试门禁禁用模型；完整确认后也只返回 `readyForFinalRealRequestSendExecution=true`，仍固定 `attemptRecordPersisted=false`、`requestSendAttempted=false`、`requestSent=false`、`clientCreated=false`、`realCallAuthorized=false`、`readyForRealRequestSend=false`、`networkAccess=false`、`realLlmCalled=false`、`secretValueRead=false`、`generatedContentCreated=false`、`taskCreated=false`。
- `provider real-preflight` 只做本地门禁判断；默认必须失败，显式 opt-in 后仍因真实 Provider 契约禁用而失败。
- `provider real-shell generate-json` 会复用真实 Provider 前置门禁；当前必须失败，不会创建 AI Task 或生成真实内容。
- `provider runtime-guard` 只做本地运行时护栏检查和 payload 脱敏预览；即使通过也固定 `readyForRealProvider=false`，不会发起真实调用。
- `provider real-poc-adapter` 只串联 Runtime Guard、真实 Provider 预检和禁用空壳；当前 `generate-json` 必须失败，不会调用 SDK、不会创建 AI Task、不会生成真实内容。
- `provider real-dry-run plan` 只生成真实 LLM PoC 前的本地计划；即使成功也固定 `dryRunOnly=true`、`readyForRealProvider=false`，不会检查密钥是否存在，不会读取密钥值，不会创建 AI Task。
- `provider real-approval-gate check` 只评估真实 SDK 实现任务前的批准清单；即使 `readyForImplementationTask=true` 也固定 `realCallAuthorized=false`，不会导入 SDK、读取密钥、访问网络或创建 AI Task。
- `provider real-sdk-blueprint plan` 只生成未来真实 SDK 最小接入任务蓝图；即使 `blueprintReady=true` 也固定 `implementationAllowed=false`、`realCallAuthorized=false`，不会安装 SDK、修改 Provider/Runtime 契约、检查密钥是否存在、访问网络或创建 AI Task。
- `provider real-sdk-impl generate-json` 只验证真实 SDK 最小实现外壳；即使 enablement 与显式 implementation opt-in 都满足，也固定 `sdkImplementationEnabled=false`，不会导入 SDK、创建客户端、检查密钥、访问网络、生成内容或创建 AI Task。
- `provider real-sdk-poc describe/generate-json` 只验证默认禁用的 SDK PoC harness；即使蓝图通过和显式 opt-in，也会被 Provider 禁用契约拦截，不导入 SDK、不检查密钥、不联网、不生成内容、不创建 AI Task。
- `provider real-sdk-enablement describe/check` 只评估最终开关设计；即使 `switchDesignReady=true`，也固定 `implementationAllowed=false`、`realCallAuthorized=false`，不会修改 Provider/Runtime 契约、不会检查密钥是否存在、不会访问网络。
- 真实 Provider 预检只允许首批 `generateJson` + `lab_generation_v0` + `Lab` 范围，生成结果仍必须 `WAITING_REVIEW`。
- 生成类 Mock 输出默认 `WAITING_REVIEW`，审核通过前不得发布。
- Provider 错误路径不得创建 AI Task、不得生成平台内容、不得绕过审核。
- Provider 调用审计只记录本地 Mock 事件，不调用真实 Provider，不读取密钥，不访问网络，不自动发布。
