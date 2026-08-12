# Phase 2 Provider Plan

本文件是 Phase 2 LLM Provider 抽象的接入规划，不是启用真实 Provider 的实现说明。当前仍保持 `MOCK_ONLY`：不接入真实大模型、不读取真实密钥、不访问网络、不启动真实智能体。

## 输入说明

- `providers/provider.contract.json`: Phase 1 Provider 契约，当前只启用 `MockProvider`。
- `providers/mock_provider.py`: 当前唯一可执行的 Provider Mock 实现。
- `providers/provider-adapter-errors.contract.json`: Provider Adapter 错误矩阵，约束失败路径不创建任务、不生成内容、不读密钥、不访问网络。
- `providers/provider-audit.contract.json`: Provider Adapter 调用审计契约，约束 registry、health、generateJson 的成功和失败路径必须写入本地 Mock 审计事件。
- `providers/real_provider_gate.py`: 真实 Provider PoC 前置门禁，仅做本地预检，不调用真实 SDK。
- `providers/real-provider-gate.contract.json`: 真实 Provider PoC 前置门禁机器契约。
- `providers/real_provider_shell.py`: OpenAI / Anthropic / Local Model 的禁用 Provider 空壳，只定义类、配置摘要和安全失败路径。
- `providers/real-provider-shell.contract.json`: 真实 Provider 空壳机器契约，约束不导入 SDK、不读取密钥、不访问网络、不生成真实内容。
- `providers/provider_runtime_guard.py`: 真实 Provider PoC 前运行时护栏，检查 timeout、retry、concurrency、日志脱敏、Schema、审计和审核要求。
- `providers/provider-runtime-guard.contract.json`: Provider Runtime Guard 机器契约，约束本地护栏通过也不得调用真实 Provider。
- `providers/real_llm_poc_adapter.py`: 真实 LLM PoC Adapter 禁用外壳，只串联 Runtime Guard、真实 Provider 预检和禁用空壳。
- `providers/real-llm-poc-adapter.contract.json`: 真实 LLM PoC Adapter 机器契约，约束当前不得导入 SDK、不得创建客户端、不得读取密钥、不得访问网络、不得生成真实内容。
- `providers/real_llm_dry_run_plan.py`: 真实 LLM PoC dry-run 计划生成器，只检查首批 Lab DSL 范围和运行时护栏，不检查密钥是否存在、不读取密钥、不访问网络、不创建 AI Task。
- `providers/real-llm-dry-run-plan.contract.json`: 真实 LLM dry-run 计划机器契约，约束计划必须保持 `dryRunOnly=true`、`readyForRealProvider=false`、`secretValueRead=false`、`realLlmCalled=false`。
- `providers/real_llm_approval_gate.py`: 真实 LLM SDK 接入前批准门禁，只评估审批编号、审核人和本地确认项，不授权真实调用。
- `providers/real-llm-approval-gate.contract.json`: 真实 LLM SDK 批准门禁机器契约，约束 `realCallAuthorized=false`、`secretValueRead=false`、`networkAccess=false`。
- `providers/real_llm_sdk_task_blueprint.py`: 真实 LLM SDK 最小接入任务蓝图，只输出未来实现范围、拟改文件、测试矩阵、回滚计划和阻断条件，不实施真实调用。
- `providers/real-llm-sdk-task-blueprint.contract.json`: 真实 LLM SDK 任务蓝图机器契约，约束 `implementationAllowed=false`、`realCallAuthorized=false`、`sdkDependencyInstalled=false`。
- `providers/real_provider_sdk_poc.py`: 真实 Provider SDK PoC harness，要求先通过 SDK 任务蓝图，再进入禁用 adapter；当前仍不安装 SDK、不导入 SDK、不检查密钥、不联网、不创建任务。
- `providers/real-provider-sdk-poc.contract.json`: 真实 Provider SDK PoC harness 机器契约，约束 `sdkPocEnabled=false`、`sdkImported=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- `providers/real_sdk_enablement.py`: 真实 SDK 最终开关设计门禁，检查蓝图、SDK 依赖审查、Provider/Runtime 契约审查、密钥注入审查、网络审查和回滚确认；当前不应用契约变更、不安装 SDK、不检查密钥、不联网、不授权真实调用。
- `providers/real-sdk-enablement.contract.json`: 真实 SDK 开关设计机器契约，约束 `switchDesignReady` 不等于真实调用授权。
- `providers/real_sdk_minimal_impl.py`: 真实 SDK 最小实现外壳，要求 enablement 和显式 implementation opt-in 先通过；当前仍默认禁用，不导入 SDK、不创建客户端、不检查密钥、不联网。
- `providers/real-sdk-minimal-impl.contract.json`: 真实 SDK 最小实现外壳机器契约，约束 `sdkImplementationEnabled=false`、`sdkImported=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- `providers/real_sdk_dependency_env_gate.py`: 真实 SDK 依赖与环境变量门禁，只评审 SDK 包名、版本 pin、license/hash、环境变量名、`.env.example` 和 CI 安装策略，不安装 SDK、不检查密钥、不联网。
- `providers/real-sdk-dependency-env-gate.contract.json`: 真实 SDK 依赖与环境变量门禁机器契约，约束 `dependencyInstallAllowed=false`、`sdkDependencyInstalled=false`、`secretPresenceChecked=false`、`networkAccess=false`。
- `providers/real_sdk_dependency_install_plan.py`: 真实 SDK 依赖安装计划草案，只评审 package manager、lockfile、版本 pin、hash、回滚文件和 CI cache 策略，不生成安装命令、不安装 SDK、不改 lockfile。
- `providers/real-sdk-dependency-install-plan.contract.json`: 真实 SDK 依赖安装计划草案机器契约，约束 `dependencyInstallCommandGenerated=false`、`dependencyInstallExecuted=false`、`dependencyLockfileChanged=false`、`packageVersionResolved=false`、`packageHashResolved=false`。
- `providers/real_sdk_dependency_installer_audit.py`: 真实 SDK 依赖安装执行审计器禁用壳，只评审未来安装命令、依赖文件、lockfile diff、离线 CI 和回滚命令，不物化命令、不安装 SDK、不改文件、不联网。
- `providers/real-sdk-dependency-installer-audit.contract.json`: 真实 SDK 依赖安装执行审计契约，约束 `installerExecutionEnabled=false`、`installCommandMaterialized=false`、`dependencyFileChanged=false`、`lockfileDiffGenerated=false`、`offlineCiExecuted=false`。
- `prompts/manifest.json`: Prompt 元数据、路径、输出类型和审核要求。
- `config/runtime.contract.json`: 运行时开关、密钥来源、超时和安全限制契约。
- `.env.example`: 本地环境变量示例，只声明变量名，不包含真实密钥。
- `delivery/phase2-readiness-gate.json`: 进入下一阶段规划前必须满足的门禁。

## 输出说明

- `providers/phase2-provider-plan.contract.json`: 机器可校验的 Provider 接入规划契约。
- `providers/PHASE2_PROVIDER_PLAN.md`: 人工可读的 Provider 接入规划。
- `providers/adapter.py`: Mock-only Provider Adapter，给 Workflow 提供 `LLMProvider` 风格调用边界。
- `providers/provider-adapter.contract.json`: Provider Adapter 机器契约。
- `providers/real_provider_gate.py`: 真实 Provider 本地预检门禁，默认拒绝，显式 opt-in 后仍受契约禁用状态限制。
- `providers/real-provider-gate.contract.json`: 真实 Provider 本地预检门禁契约。
- `providers/real_provider_shell.py`: 禁用真实 Provider 实现空壳，`health` 返回 `DISABLED` 摘要，生成类操作安全失败。
- `providers/real-provider-shell.contract.json`: 禁用真实 Provider 空壳契约。
- `providers/provider_runtime_guard.py`: Provider Runtime Guard 本地检查实现，返回脱敏后的 payload preview 和安全上下文。
- `providers/provider-runtime-guard.contract.json`: Provider Runtime Guard 契约。
- `providers/real_llm_poc_adapter.py`: 真实 LLM PoC Adapter 禁用实现，`describe` 返回禁用摘要，`generate-json` 串联门禁后仍安全失败。
- `providers/real-llm-poc-adapter.contract.json`: 真实 LLM PoC Adapter 契约。
- `providers/real_llm_dry_run_plan.py`: 真实 LLM dry-run 计划实现，成功返回一份不执行的单链路计划。
- `providers/real-llm-dry-run-plan.contract.json`: 真实 LLM dry-run 计划契约。
- `providers/real_llm_approval_gate.py`: 真实 LLM SDK 批准门禁实现，完整确认后只允许进入实现任务评审。
- `providers/real-llm-approval-gate.contract.json`: 真实 LLM SDK 批准门禁契约。
- `providers/real_llm_sdk_task_blueprint.py`: 真实 LLM SDK 任务蓝图实现，完整确认后只输出未来任务清单。
- `providers/real-llm-sdk-task-blueprint.contract.json`: 真实 LLM SDK 任务蓝图契约。
- `providers/real_provider_sdk_poc.py`: 真实 Provider SDK PoC harness，`describe` 返回禁用摘要，`generate-json` 必须停在蓝图、opt-in 或 Provider 禁用门禁。
- `providers/real-provider-sdk-poc.contract.json`: 真实 Provider SDK PoC harness 契约。
- `providers/real_sdk_enablement.py`: 真实 SDK enablement 门禁，`describe/check` 返回最终开关设计和阻断条件。
- `providers/real-sdk-enablement.contract.json`: 真实 SDK enablement 契约。
- `providers/real_sdk_minimal_impl.py`: 真实 SDK 最小实现外壳，`describe/generate-json` 必须停在 enablement、implementation opt-in 或 implementation-disabled 门禁。
- `providers/real-sdk-minimal-impl.contract.json`: 真实 SDK 最小实现外壳契约。
- `providers/real_sdk_dependency_env_gate.py`: 真实 SDK 依赖与环境变量门禁，`describe/check` 只返回设计评审结果和阻断条件。
- `providers/real-sdk-dependency-env-gate.contract.json`: 真实 SDK 依赖与环境变量门禁契约。
- `providers/real_sdk_dependency_install_plan.py`: 真实 SDK 依赖安装计划草案，`describe/plan` 只返回安装计划草案和阻断条件。
- `providers/real-sdk-dependency-install-plan.contract.json`: 真实 SDK 依赖安装计划草案契约。
- `providers/real_sdk_dependency_installer_audit.py`: 真实 SDK 依赖安装执行审计器禁用壳，`describe/audit` 只返回审计清单和阻断条件。
- `providers/real-sdk-dependency-installer-audit.contract.json`: 真实 SDK 依赖安装执行审计契约。
- `cli/provider_audit.py`: Provider 调用审计事件模型，记录 `providerCallAuditEvents`，不读取密钥、不访问网络。
- `ai_workflows/provider_adapter_workflow.py`: Workflow 侧 Provider Adapter helper，统一生成 Lab / Exam / Grading / PPT DSL Mock。
- 后续 Provider 调用仍必须返回统一结构，包含 `providerId`、`mode`、`promptId`、`promptVersion`、`generatedStatus`、`realLlmCalled`、`secretsRead`、`networkAccess` 和 `traceId`。
- 生成类输出默认进入 `WAITING_REVIEW`，审核通过前不得发布。

## 接口设计

建议在 Phase 2 引入统一 `LLMProvider` 接口：

```text
LLMProvider
  - generateText(promptId, input, options) -> ProviderResult
  - generateJson(promptId, input, schema, options) -> ProviderJsonResult
  - streamGenerate(promptId, input, options) -> ProviderStreamResult
```

`generateJson` 必须执行 DSL Schema 校验，失败时返回统一错误，不创建 AI Task。`streamGenerate` 暂时只做接口预留，等 MockProvider、Prompt manifest、超时、重试、日志脱敏和审核门禁稳定后再实现。

## MockProvider 优先策略

1. `MockProvider` 继续作为默认 Provider。
2. 新增输出类型时，先补 Prompt manifest、DSL 示例、Schema 校验和 MockProvider 测试。
3. Workflow 先依赖 `MockProvider` 的确定性输出跑通审核链路。
4. 所有生成结果必须标记 `WAITING_REVIEW`。
5. 真实 Provider 只能在单独任务中显式开启，且必须先通过 Phase 2 准入门禁。

## 真实 Provider 预留

预留以下 Provider 占位，但当前全部禁用：

| Provider | 环境变量 | 当前状态 |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | 禁用 |
| Anthropic Claude | `ANTHROPIC_API_KEY` | 禁用 |
| Local Model | `LOCAL_MODEL_ENDPOINT` | 禁用 |

真实 Provider 接入前必须完成：

- 禁用空壳类先存在，且 `sdkImported=false`、`clientCreated=false`、`generationOperationsEnabled=false`。
- 密钥只从环境变量或配置中心读取。
- 日志脱敏覆盖 API Key、Token、候选答案和请求片段。
- 超时、重试、并发限制可配置。
- 网络访问显式门控。
- 输出经过 Schema 校验。
- 失败路径返回安全错误上下文，不创建 AI Task 或平台内容。
- 成功和失败调用写入 Provider 调用审计，便于后续真实 Provider 接入前做追踪和验收。
- AI Task 和人工审核流保持强制。
- `provider real-preflight` 是首个真实 Provider 前置门禁命令；默认没有 `--explicit-opt-in` 必须返回 `REAL_PROVIDER_OPT_IN_REQUIRED`。
- 即使传入 `--explicit-opt-in`，只要契约仍为 `enabled=false`，也必须返回 `REAL_PROVIDER_DISABLED`，且 `realLlmCalled=false`、`secretsRead=false`、`networkAccess=false`。
- 首批 PoC 范围只允许 `generateJson`、`lab_generation_v0`、`Lab` DSL，生成结果仍必须进入 `WAITING_REVIEW`。
- `provider real-shell list/health` 只能返回禁用摘要；`provider real-shell generate-json` 当前必须复用门禁并失败，不创建任务、不生成真实内容。
- `provider runtime-guard` 必须在真实调用前检查 timeout、retry、concurrency、redaction、Schema、审计和审核门禁；当前只做本地检查并固定 `readyForRealProvider=false`。
- `provider real-poc-adapter` 必须先经过 Runtime Guard 和真实 Provider 预检；当前 adapter 本身仍禁用，不能导入 SDK、创建客户端、发起网络请求、创建 AI Task 或生成真实内容。
- `provider real-dry-run plan` 必须在真实 LLM PoC 前通过；当前只输出本地计划，成功也固定 `readyForRealProvider=false`、`dryRunOnly=true`、`secretPresenceChecked=false`、`taskCreated=false`。
- `provider real-approval-gate check` 必须在真实 SDK 实现任务前通过；当前只评估本地批准清单，即使通过也固定 `realCallAuthorized=false`。
- `provider real-sdk-blueprint plan` 必须在真实 SDK 实现任务前生成；当前只输出未来实施蓝图，即使 `blueprintReady=true` 也固定 `implementationAllowed=false`、`realCallAuthorized=false`、`sdkDependencyInstalled=false`、`providerContractChangeApplied=false`、`runtimeContractChangeApplied=false`。
- `provider real-sdk-poc describe/generate-json` 必须要求 SDK 任务蓝图先通过；当前即使蓝图通过也仍固定 `sdkPocEnabled=false`、`realLlmCalled=false`、`secretPresenceChecked=false`、`networkAccess=false`、`taskCreated=false`。
- `provider real-sdk-enablement describe/check` 必须在任何真实 SDK 开关变更前通过；当前即使 `switchDesignReady=true` 也固定 `implementationAllowed=false`、`realCallAuthorized=false`、`providerContractChangeApplied=false`、`runtimeContractChangeApplied=false`。
- `provider real-sdk-dependency-env describe/check` 必须在任何 SDK 依赖或 env 任务前通过；当前即使 `readyForDependencyImplementationTask=true` 也不安装 SDK、不检查密钥、不联网。
- `provider real-sdk-dependency-install-plan describe/plan` 必须在任何 SDK 依赖安装实现任务前通过；当前即使 `readyForDependencyInstallImplementationReview=true` 也不生成安装命令、不安装 SDK、不解析包版本或 hash、不修改 lockfile。
- `provider real-sdk-dependency-installer-audit describe/audit` 必须在任何 SDK 安装执行壳实现任务前通过；当前即使 `readyForInstallerImplementationTask=true` 也不物化命令、不安装 SDK、不生成 lockfile diff、不修改依赖文件。

## 安全与配置

- 不接入真实大模型。
- 不读取真实密钥。
- 不访问网络。
- 不跳过 Provider Runtime Guard。
- 不绕过真实 LLM PoC Adapter 的禁用态。
- 不绕过真实 LLM dry-run 计划，不在 dry-run 阶段检查密钥是否存在或创建 AI Task。
- 不绕过真实 LLM SDK 批准门禁，不把 `readyForImplementationTask` 当成真实调用授权。
- 不绕过真实 LLM SDK 任务蓝图，不把 `blueprintReady` 当成实施许可或真实调用授权。
- 不绕过真实 Provider SDK PoC harness，不把蓝图通过或显式 opt-in 当成真实生成成功。
- 不绕过真实 SDK enablement 开关设计，不把 `switchDesignReady` 当成真实调用授权或契约变更许可。
- 不绕过真实 SDK dependency/env gate，不把 `readyForDependencyImplementationTask` 当成安装 SDK、检查密钥或联网许可。
- 不绕过真实 SDK dependency install plan，不把 `readyForDependencyInstallImplementationReview` 当成生成安装命令、安装 SDK、解析包版本或 hash、修改 lockfile 的许可。
- 不绕过真实 SDK dependency installer audit，不把 `readyForInstallerImplementationTask` 当成物化命令、安装 SDK、修改依赖文件、生成 lockfile diff、检查密钥或联网的许可。
- 不在业务代码中内嵌 Prompt。
- 不在日志、前端、交付包中展示密钥。
- 不绕过 Schema 校验。
- 不跳过 Provider 调用审计。
- 不绕过 `WAITING_REVIEW` 人工审核。
- 不自动发布 Lab、Exam、Grading 或 PPT。

## 命令示例

```powershell
python lab_cli.py provider list
python lab_cli.py provider health
python lab_cli.py provider mock-generate --prompt-id lab_generation_v0
python lab_cli.py provider real-preflight --provider openai
python lab_cli.py provider real-preflight --provider openai --explicit-opt-in
python lab_cli.py provider real-shell list
python lab_cli.py provider real-shell health --provider openai
python lab_cli.py provider real-shell generate-json --provider openai
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
python lab_cli.py provider audit --operation generateJson
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
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_provider_contract.py tests/test_provider_mock.py
python -m pytest tests/test_phase2_readiness_gate.py
```

## 测试方式

```powershell
python -m pytest tests/test_provider_adapter.py
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
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_provider_contract.py tests/test_provider_mock.py
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest
```

## 限制说明

- 当前文件只定义 Phase 2 Provider 接入规划，不实现 OpenAI、Anthropic 或 Local Model Provider。
- 当前 `OpenAIProvider`、`AnthropicProvider`、`LocalModelProvider` 只是禁用空壳，不是真实 Provider 接入。
- 当前 Provider Runtime Guard 只验证本地护栏和脱敏预览，不代表真实 Provider 已可用。
- 当前真实 LLM PoC Adapter 只验证本地串联路径，不代表真实 LLM 已可调用。
- 当前真实 SDK 依赖与环境变量门禁只验证未来依赖/env 任务是否具备评审前置条件，不代表允许安装 SDK、解析包版本、检查密钥或访问网络。
- 当前真实 SDK 依赖安装计划只验证未来依赖安装任务是否具备评审前置条件，不代表允许生成安装命令、安装 SDK、解析包版本或 hash、修改 lockfile、检查密钥或访问网络。
- 当前真实 SDK 依赖安装执行审计器只验证未来禁用安装执行壳是否具备评审前置条件，不代表允许物化命令、安装 SDK、修改依赖文件、生成 lockfile diff、检查密钥或访问网络。
- 当前真实 LLM dry-run plan 只生成本地执行计划，不代表真实 LLM 已可调用，也不会检查密钥是否存在或创建 AI Task。
- 当前真实 LLM approval gate 只评估实现任务前批准清单，不代表真实 LLM 已可调用，也不会授权真实调用。
- 当前真实 LLM SDK task blueprint 只生成未来实现任务蓝图，不代表真实 LLM 已可调用，也不会安装 SDK、修改契约、检查密钥、访问网络或创建 AI Task。
- 当前真实 Provider SDK PoC harness 只验证“蓝图通过后仍被禁用门禁拦住”的本地路径，不代表真实 SDK 已接入，也不会导入 SDK、检查密钥、访问网络、生成内容或创建 AI Task。
- 当前真实 SDK enablement 只评估最终开关设计，不代表真实 SDK 已接入，也不会修改 Provider/Runtime 契约、安装 SDK、检查密钥、访问网络或授权真实调用。
- 当前真实 SDK minimal implementation shell 只验证未来实现形态，不代表真实 SDK 已接入；即使 enablement 和显式 implementation opt-in 都满足，也不会导入 SDK、创建客户端、检查密钥、访问网络、生成内容或创建 AI Task。
- 当前不新增真实网络请求，不读取 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`LOCAL_MODEL_ENDPOINT` 的真实值。
- 当前不改变 `providers/provider.contract.json` 的启用态，`mock` 仍是唯一启用 Provider。
- 当前不启动真实 Agent，不创建真实云资源，不执行真实沙箱，不发布真实平台内容。
