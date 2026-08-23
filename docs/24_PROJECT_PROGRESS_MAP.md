# 项目进度地图与防跑偏清单

> 最后更新：2026-08-23
> 当前定位：AI 教学智能体（独立精简版）。当前唯一产品目标是把一份 Markdown 教学材料转换为可人工审核、可本地导出的 Lab + Exam 教学包；Grading 是 Exam 的内部配套规则。
> 使用方式：本文件只维护当前路线、优先级和功能停止线；全局执行约束以项目根目录 `AGENTS.md` 为准。继续开发前先看本文件的“下一步路线”和相关停止线，避免在同一个功能点反复加门禁、加展示页或加运营材料。

---

## 1. 当前结论

项目已经证明更大范围的本地 PoC 可行，现在主动收敛为：

```text
一份 Markdown 教学材料
  -> 真实 LLM 生成 Lab + Exam/Grading
  -> Schema 校验与跨产物校验
  -> WAITING_REVIEW
  -> 人工批准或退回
  -> 本地教学包导出
```

已经实现的 PPT/PPTX、受控评分、内部实体、CLI、API、MCP、Agent 和多页前端能力继续保留，作为既有 PoC、兼容能力或未来候选，不再同时定义当前 MVP。后续只修复会阻断精简闭环或破坏安全/兼容边界的具体问题。

### 1.1 独立智能体定位与内部闭环

当前项目定位为面向教师备课场景的独立 AI 教学智能体，不再以建设完整实训基础设施、接入外部平台或扩张技术接口数量为核心目标。

当前智能体核心闭环链路是：

```text
Markdown 输入
→ 真实 LLM 生成 Lab + Exam/Grading
→ Schema 校验、归一化和跨产物引用校验
→ Exam 候选人安全预览
→ WAITING_REVIEW
→ 教师查看、批准或退回
→ 本地导出教学包
```

当前只保留支撑这条链路所需的最小本地状态、一个生成入口、一个审核入口和一个本地导出结果。Grading 保留为 Exam 的内部配套产物，不扩张成独立评分产品。

### 1.2 当前 MVP 验收与冻结边界

当前 MVP 的验收条件是：

1. 一份 Markdown 可稳定生成相互引用正确的 Lab + Exam/Grading。
2. 产物全部通过 Schema/契约校验并进入 `WAITING_REVIEW`。
3. 候选人预览不展示答案或内部 `gradingRef`。
4. 教师能在一条清晰流程中查看、批准或退回，并本地导出教学包。
5. Mock 正常路径和至少一个错误/回归路径可复现；真实 LLM 只按实际失败样本修复。

当前冻结且不作为 MVP 验收项：PPT/PPTX 产品化、自动评分与沙箱生产化、本地平台实体和导入流程扩张、MCP/Agent 新能力、多页面工作台扩张、外部平台、VM/Notebook 和生产部署。已有实现不删除，只做必要的兼容性、安全和阻断性缺陷修复。

MVP 达标后，下一阶段只能在 PPT 产品化和自动评分产品化中选择一项，且需要用户明确确认；不得默认并行恢复全部历史路线。

---

## 2. 复杂度标尺

| 复杂度 | 含义 |
| --- | --- |
| S | 0.5 天内，文档、命令参数、局部校验或小型补丁。 |
| M | 1-2 天，单模块完整功能，含测试和文档。 |
| L | 3-5 天，跨 CLI / 后端 / 前端 / 测试的闭环能力。 |
| XL | 1-2 周或更久，涉及真实平台、真实沙箱、权限、持久化或部署。 |

复杂度是后续排期参考，不代表当前一次 Codex 回合必须全部完成。

---

## 3. 已实现内容

| 模块 | 已实现内容 | 主要入口 / 证据 | 复杂度 | 当前状态 |
| --- | --- | --- | --- | --- |
| 项目底座 | 目录结构、Phase 文档、DSL / CLI / MCP / Sandbox 基础分层。 | `AGENTS.md`、`docs/00_START_HERE.md`、`docs/AI_PLATFORM_CODEX_FULL_GUIDE.md` | M | 已完成，可继续维护。 |
| DSL Schema | Lab / Exam / Grading / PPT DSL Schema 和示例 YAML。 | `templates/*/schemas/`、`templates/*/examples/`、`docs/04_DSL_SPEC.md` | M | 已完成，后续只按真实输出问题迭代。 |
| CLI JSON 契约 | `lab_cli.py` 统一 JSON 返回、错误码、traceId。 | `python lab_cli.py ...`、`docs/06_CLI_SPEC.md` | M | 已完成，后续保持兼容。 |
| 安装式 CLI 用户工作区 | `workspace info` 只读展示路径策略；wheel 安装后默认将 JSON 状态和 `examples/output` 产物映射到用户工作区；Lab、Exam/Grading、PPT 任务生成、审核详情、人工批准、本地 import-preview 和 PPTX Artifact 可在 checkout 外连续运行，支持 `LAB_CLI_WORKSPACE` 显式隔离；PPTX 构建脚本随 wheel 发布，临时构建目录不写入 `site-packages`。 | `cli/workspace.py`、`ai_workflows/exam_grading_generation_v1.py`、`cli/lab_cli.py`、`scripts/build_pptx_from_ppt_dsl.mjs`、`tests/test_packaging.py`、`tests/test_workspace.py` | M | 安装式核心产物边界已完成；真实 LLM 默认输出、PPTX 版式质量和完整四类 Golden Path 仍按具体产物缺陷继续扩展，不把这一项误报为真实 LLM 或生产 PPT 服务。 |
| AI Task 状态模型 | `WAITING_REVIEW`、审核通过 / 拒绝 / 发布阻断等本地状态流。 | `cli/ai_task_store.py`、`python lab_cli.py ai-task list` | M | 已完成，生产持久化未做。 |
| 人工审核 Mock | 审核列表、审核详情、批量摘要、禁止自动发布。 | `python lab_cli.py review list/detail/batch-summary` | M | 已完成，前端真实交互未生产化。 |
| Provider 抽象 | MockProvider、Provider Adapter、Provider 审计和错误上下文。 | `providers/`、`cli/provider_audit.py` | M | 已完成，真实 Provider 已开始接入。 |
| 真实 SDK 安装与 client 边界 | 安装 OpenAI SDK、SDK import、client 构造、环境变量边界。 | `docs/13_REAL_SDK_INSTALL_EXECUTION.md`、`docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md` | M | 已完成，不再扩展同义门禁。 |
| 最小真实 LLM PoC | 显式 opt-in 后发送一次真实请求生成 Lab DSL。 | `python lab_cli.py provider real-llm-minimal-poc run ...`、`docs/15_REAL_LLM_MINIMAL_POC.md` | L | 已完成，后续归入核心生成质量。 |
| 真实 LLM 四类 DSL | 真实模型生成 Lab / Exam / Grading / PPT DSL，默认等待审核。 | `python lab_cli.py phase2 workflow run --provider-mode real-llm ...` | L | 已可用，Schema 归一化仍需增强。 |
| 精简教学包生成 v0.1.6 | 既有内容生成 API 支持兼容的 `artifactProfile=teaching-core`，只生成相互关联的 Lab / Exam / Grading，创建 3 个 `WAITING_REVIEW` 任务，并返回候选人安全 Exam 预览、教学包级摘要和审核入口；默认生成页显式使用该 profile。未传字段继续执行 `legacy-all` 四类行为；真实模式不请求 PPT。 | `POST /api/phase2/workflows/content-generation/run`、`frontend/generation-workspace.html`、`tests/test_provider_adapter_workflow.py`、`tests/test_backend_mock_api.py`、`tests/test_frontend_manifest.py` | M | 已达到生成切片停止线；下一步转向同一 `workflowRun.id` 的三类审核聚合，不继续添加第二个生成 API 或同义生成页。 |
| 教学包审核聚合 v0.1.7 | `GET /api/review-task-summary?workflowRunId=...` 从已有 WorkflowRun、Artifact 和 AI Task 派生 Lab / Exam / Grading 教学包审核摘要；默认审核页展示三类路径、Schema/质量、候选人安全、审核进度和导出就绪状态，并逐项复用已有 approve/reject API。拒绝必须填写原因，不新增 TeachingPackage 实体或批量审核接口；历史 `legacy-all` 查询仍保留四类任务兼容。 | `cli/review_batch.py`、`backend/mock_api.py`、`frontend/review-center.html`、`frontend/review-center-data.js`、`frontend/review-action-data.js`、`tests/test_backend_mock_api.py`、`tests/test_frontend_manifest.py` | M-L | 已达到审核聚合停止线；下一步只实现全部三项人工批准后的本地教学包导出，不继续添加同义审核页、批量决定或发布能力。 |
| 本地教学包导出 v0.1.8 | `lab-cli teaching-package export --workflow-run-id ... --reviewer ...` 与 `POST /api/teaching-packages/export` 只对 `teaching-core` 批次开放；Lab / Exam / Grading 三项必须全部人工批准，导出前重新校验 Schema 并重新生成候选人安全预览，默认原子写出 `examples/output/teaching-packages/<workflowRunId>.zip`。ZIP 固定包含 manifest、三类 DSL、候选预览和审核摘要六个成员；不依赖平台实体、不执行评分、不联网、不改变任务状态、不发布。 | `cli/teaching_package_export.py`、`cli/lab_cli.py`、`backend/mock_api.py`、`frontend/review-center.html`、`tests/test_teaching_package_export.py`、`tests/test_backend_mock_api.py`、`tests/test_frontend_manifest.py` | S-M | 已达到本地导出切片和精简 MVP 停止线；Mock 正常、错误、状态、脱敏及全量回归已通过。等待用户明确选择下一阶段。 |
| AI 生成教学实验稳定 v1 | 第一个主功能已收敛为 Markdown 输入生成任务专属 Lab DSL：`lab generate-from-source` / `POST /api/labs/generate` 会输出 `examples/output/<task_id>-lab.json`，DSL 指向本次输入素材，至少包含 2 个学习目标和 3 个实验步骤，创建 `WAITING_REVIEW` 任务，返回 `labFeatureReadiness`，并提供审核详情、`lab import-preview`、`lab mock-import` 下一步入口；CLI 默认 Mock，也支持显式 `--provider-mode real-llm` 用 OpenAI-compatible 模型真实生成 Lab DSL 后进入同一审核链路；不调用真实平台、不发布。 | `python lab_cli.py lab generate-from-source --input examples/input/demo-source.md`、`python lab_cli.py lab generate-from-source --input examples/input/demo-source.md --provider-mode real-llm --model deepseek-v4-flash --base-url https://api.deepseek.com --explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish`、`POST /api/labs/generate`、`tests/test_cli.py::test_lab_generate_from_source_returns_json`、`tests/test_cli.py::test_lab_generate_from_source_real_llm_mode_uses_explicit_opt_in_and_stays_review_gated`、`tests/test_backend_mock_api.py::test_lab_generate_creates_waiting_review_task`、`quality regression-matrix --profile quick` | M | 已达到稳定 v1 停止线；后续不再围绕 Lab 生成页/命令追加同义展示壳，除非真实 LLM 生成 Lab 出现具体 Schema 或内容质量失败样本。 |
| Lab DSL 转 Exam+Grading 稳定 v1 | 第二个主功能已收敛为 Lab DSL 输入生成任务专属 Exam DSL、Grading DSL 和候选人安全预览：`exam generate-from-lab --lab <Lab DSL>` 会先校验 Lab DSL，输出 `examples/output/<task_id>-exam.json`、`examples/output/<task_id>-grading.json`、`examples/output/<task_id>-exam-candidate-preview.json`，创建同一个 `WAITING_REVIEW` 任务，返回 `examGradingFeatureReadiness`；CLI 保留旧 `--lab-id` Mock 兼容路径，也支持显式 `--provider-mode real-llm` 用 OpenAI-compatible 模型真实生成 Exam/Grading 后做跨产物归一化，确保题目 `gradingRef` 覆盖到 `checks` / `assessmentPlan`、总分对齐、候选端不展示 `answer` 或内部 `gradingRef`；审核通过后可继续本地 `exam import-preview` 和 `grade import-preview`，不调用真实平台、不发布。 | `python lab_cli.py exam generate-from-lab --lab templates/lab/examples/basic-lab.yaml`、`python lab_cli.py exam generate-from-lab --lab templates/lab/examples/basic-lab.yaml --provider-mode real-llm --model deepseek-v4-flash --base-url https://api.deepseek.com --explicit-real-call-opt-in --confirm-waiting-review --confirm-no-auto-publish`、`tests/test_cli.py::test_exam_generate_from_lab_real_llm_mode_outputs_task_specific_exam_grading_and_candidate_preview`、`tests/test_cli.py::test_exam_generate_from_lab_real_llm_mode_requires_lab_dsl`、`tests/test_cli.py::test_exam_and_grading_import_preview_from_approved_task`、`quality regression-matrix --profile quick` | M | 已达到稳定 v1 停止线；后续不再围绕旧 `--lab-id` Mock、候选预览或审核页追加同义展示壳，除非真实 LLM 生成 Exam/Grading 出现具体 Schema 或内容质量失败样本。 |
| 真实 LLM Demo 工作流 | 真实 DSL 输出、报告、Provider audit、token usage、review detail；真实调用失败时会在 `--output` 写 `PHASE2_WORKFLOW_FAILURE_REPORT`，保留 Provider 错误上下文和 Schema 诊断，且不创建 AI Task、不发布；`provider real-llm-runtime-config` 已返回无密钥 `commandReadiness` 和 `safeCommandTemplates`，用于减少真实调用前的 PowerShell 手工拼接错误。 | `docs/18_REAL_LLM_DEMO_WORKFLOW.md`、`examples/output/*real-llm*` | L | 已可演示，稳定性待提升。 |
| 真实输出归一化 | 已修复多类真实模型常见 Schema 偏差，如材料对象、答案字符串、资源对象、Lab grading ref 形状、Lab materials/steps、Lab step 字段别名、Exam questions、Exam question 字段别名、Grading checks/assessmentPlan 字段别名、PPT slides 字段别名和对象映射等，并建立 Schema 漂移矩阵回归入口；Schema 失败会返回不含答案/密钥原值的 `schemaFailureDiagnostic`，辅助定位 Prompt 或归一化缺口；2026-07-06 使用 DeepSeek v4 flash 跑通 Lab / Exam / Grading / PPT 四类真实 DSL 在线样本，随后又用 3 份不同输入素材连续跑通 3 轮真实四类 DSL 生成，12 份 DSL 独立校验全通过且保持 `WAITING_REVIEW`；同日 live 复核再次用 DeepSeek v4 flash 跑通四类 DSL，4/4 Schema 通过、`schemaRepairAttempted=false`、`blockingIssueTotal=0`；2026-07-12 又以 Linux 日志分析、Python 数据清洗、Web API 测试三份素材完成最终 12/12 文件级校验和候选预览脱敏验证，期间发现一次 Lab objective 数量不足，仅收紧 Prompt 为至少 2 个不同目标并复跑通过，未新增 Schema 归一化规则；`/api/workflow/report?file=...` 和 `review-center.html?agentReport=...` 已可只读读取本轮真实 workflow report。 | `phase2 workflow run --provider-mode real-llm` 的失败/成功记录、`docs/25_REAL_LLM_SCHEMA_DRIFT_MATRIX.md`、`examples/output/p0-deepseek-v4-flash-workflow-report.json`、`examples/output/p0-deepseek-v4-flash-multi-round-summary.json`、`examples/output/p0-deepseek-v4-flash-live-summary.json` | M | P0 在线稳定性已有连续通过样本；后续只按实际失败样本补归一化，否则转向自定义真实产物路径接入 Review Center / 前端 2.0 产品化，不再新增门禁或运营内容。 |
| Exam 候选人预览 | 移除答案、阻断标准答案泄漏、生成选手端预览。 | `python lab_cli.py exam candidate-preview ...` | M | 已完成，需接入真实前端。 |
| PPT DSL 与 PPTX Artifact PoC | 从 PPT DSL 生成本地 `.pptx`、manifest、预览产物，等待审核。 | `python lab_cli.py ppt artifact build ...`、`docs/22_PPTX_ARTIFACT_POC.md` | L | PoC 已完成，版式质量待产品化。 |
| Demo Bundle | 复放真实 LLM 产物，汇总 Schema 校验、候选预览、只读沙箱证据和 PPTX Artifact。 | `python lab_cli.py phase2 demo-bundle build/report ...`、`docs/21_REAL_LLM_DEMO_BUNDLE.md` | L | 已完成，可作为演示闭环入口。 |
| 可复现 Offline Demo | `demo offline` 使用本地 deterministic fixture / MockProvider，串联四类 DSL Schema 校验、候选人安全预览、`WAITING_REVIEW` 和质量摘要；默认不需要 API Key，不联网、不执行选手代码、不发布。失败时保持统一 JSON envelope，且不会落盘未通过校验的 summary 或候选人预览。 | `python lab_cli.py demo offline`、`tests/test_offline_demo.py`、`quality regression-matrix --profile quick/core`、`.github/workflows/core-regression-matrix.yml` | S-M | B1 已完成，达到无 Key 可复现停止线；后续不再新增同义 Demo 入口，转入 MCP 契约稳定化或其他核心业务缺口。 |
| 自动评分 Mock | `file_exists` / `stdout_contains` / `pytest` / `notebook_cell` / `json_field` / `log_keyword` 计划化报告。 | `sandbox/grade_runner.py`、`python lab_cli.py grade run ...` | L | Mock/计划层已完成，真实执行沙箱未生产化。 |
| 只读沙箱证据 | 只读 evidence demo、真实沙箱前预检、禁止执行选手代码。 | `docs/19_REAL_SANDBOX_PRECHECK.md`、`docs/20_READONLY_SANDBOX_POC.md` | M | 已完成，后续与受控 Docker evidence 合并使用。 |
| 受控评分沙箱 PoC | Docker 受控执行 `stdout_contains` / `pytest`，submission 只读挂载、网络关闭、只读 rootfs、资源限制、stdout/stderr 捕获、失败/超时样例、审计隔离摘要和本地镜像供应链审计；报告会透出 `imageSupplyChain`，包含本地 `docker image inspect` 的 imageId/digest、allowlist 匹配、禁止自动 pull、未使用 registry auth 和未访问生产 registry；报告还会透出 `isolationQuality`，汇总网络关闭、只读挂载、只读 rootfs、资源限制、输出捕获、本地镜像检查和 registry 网络未使用等本地质量信号。 | `sandbox/controlled_command_executor.py`、`python lab_cli.py grade sandbox-run --execution-mode controlled-command ...`、`/api/grading/controlled-evidence` | L | 本地 evidence 质量摘要已完成；不是生产队列/多租户沙箱/镜像签名强校验。后续只做真实生产化接入或具体隔离缺陷修复，不再新增同义门禁或同义质量摘要。 |
| Grading DSL 到受控评分稳定 v1 | 第三个主功能已收敛为 Grading DSL 输入、本地 submission、默认受控 command evidence、本地 `GradingJob` 同步执行、`GRADING_EVIDENCE_AUTO_REPORT`、`GradingRecord`、`reviewDetail` 与 `gradingResultPreview` 同一命令闭环：`grade stable-v1` 会创建或复用 `WAITING_REVIEW` Grading 任务，返回 `gradingStableV1Readiness`，并把下一步人工 `grade record-review --decision approve-ready` 明确暴露；2026-07-06 已用本地真实 Docker runtime 与 `ai-grading-python:0.1` 跑通 smoke，并新增 `examples/submissions/mixed-checks-pass` 满分样例验证六类检查 `6/6` 通过、总分 `100/100`；报告矩阵和结果预览已在 item 顶层展示状态、得分、来源、exitCode、stdout/stderr 尾部、检查文件和错误码；`GRADING_EVIDENCE_AUTO_REPORT` 已新增只读 `reviewerSafetySummary`，把分数预览、证据覆盖、受控容器执行状态、阻断原因和下一条人工动作折成审核员可读摘要，并写入操作审计和 Artifact metadata；不自动复核、不自动审核 AI Task、不调用真实平台、不发布。 | `python lab_cli.py grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/controlled-command-demo --output examples/output/grading-stable-v1-evidence.json --submission-id submission_001 --reviewer teacher_1`、`python lab_cli.py grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/controlled-command-demo --output examples/output/grading-stable-v1-docker-smoke-evidence.json --submission-id docker_smoke_submission_001 --reviewer teacher_1 --image ai-grading-python:0.1 --fail-on-controlled-unavailable`、`python lab_cli.py grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/mixed-checks-pass --output examples/output/grading-stable-v1-docker-full-pass-evidence.json --submission-id docker_full_pass_submission_001 --reviewer teacher_1 --image ai-grading-python:0.1 --fail-on-controlled-unavailable`、`tests/test_cli.py::test_grade_stable_v1_creates_controlled_evidence_record_review_detail_and_report`、`tests/test_cli.py::test_grade_stable_v1_mixed_checks_pass_fixture_scores_full_marks`、`tests/test_cli.py::test_grade_stable_v1_requires_submission_directory`、`quality regression-matrix --profile quick` | M | 已达到稳定 v1 停止线；后续不再重复实现 evidence-auto/job-run/record-create/review-detail/report-preview 或 reviewer summary 的同义编排壳，除非出现具体受控 Docker、隔离质量或报告可读性缺陷。 |
| Grading Job 本地任务流 | 本地 `GradingJob` 可创建 `QUEUED` 任务、同步执行 evidence-auto、生成评分报告、派生 `GradingRecord` 并进入 `WAITING_REVIEW`，审核详情可聚合 job 摘要；`backend/grading_job_service.py` 已承接 job 创建、同步运行、JSON/SQLite staging 写入、报告 Artifact 和操作审计，HTTP 路由只做 payload / response 适配。 | `python lab_cli.py grade job-create ...`、`python lab_cli.py grade job-run ...`、`POST /api/grading/jobs`、`POST /api/grading/jobs/{id}/run`、`tests/test_backend_grading_job_service.py` | M | 本地 staging job 与创建/同步运行服务层已完成；真实后台 worker、生产数据库事务和并发调度未做。后续不再重复迁移 create/run，同类工作转向 GradingRecord 复核服务层或真实数据库 adapter。 |
| Grading Record 本地记录 | 从已有评分 evidence 报告派生本地 `GradingRecord`，保存 submission、candidate、reportPath、得分、覆盖率、evidence 摘要和人工复核状态；支持单条记录人工复核为确认、补证据或需修订；`backend/grading_record_service.py` 已承接记录创建、人工复核、JSON/SQLite staging 写入和操作审计，HTTP 路由只做 payload / response 适配；`GET /api/grading/records?dbPath=...` 与 `GET /api/grading/records/{id}?dbPath=...` 已支持直接读取本地 SQLite，不依赖 JSON mirror；审核详情返回 `gradingRecords.reviewIntegration`，`core-readiness` 在已有评分记录时会把 `approve-ready` 人工复核结论作为平台复核前的只读步骤；Review Center 已新增 `GradingRecordReviewIntegration` 面板展示 recordTotal、latestRecordId、score、coverage、blockingReasons、人工 `record-review` CLI 和本地安全边界；Grading Report 页已新增 `GradingRecordReviewSummary`，通过 `GET /api/grading/records?taskId={id}` 只读展示 recordTotal、latestStatus、latestDecision、readyForPlatformReview、reviewCommand 和 `platformApiRequired=false`；`platform-entity readiness-report` 的 `grading_rule` item 已返回 `gradingRecordReviewEvidence` 和 ready/blocked 统计，把评分记录复核证据接入平台实体复核链路。 | `python lab_cli.py grade record-create ...`、`python lab_cli.py grade record-review ...`、`python lab_cli.py review core-readiness --task-id ...`、`python lab_cli.py platform-entity readiness-report --source-task-id ...`、`POST /api/grading/records`、`GET /api/grading/records?dbPath=...`、`GET /api/grading/records?taskId=...`、`GET /api/grading/records/{id}?dbPath=...`、`POST /api/grading/records/{id}/review`、`GET /api/review-tasks/{id}/core-readiness`、`frontend/review-center.html`、`frontend/review-center-data.js`、`frontend/grading-report.html`、`frontend/grading-report-data.js`、`tests/test_backend_grading_record_service.py`、`tests/test_backend_mock_api.py::test_grading_record_api_reads_records_from_sqlite_db_path_without_json_mirror`、`tests/test_backend_agent_entity_service.py::test_backend_agent_entity_service_readiness_includes_grading_record_review_evidence`、`tests/test_frontend_manifest.py` | M | 本地 mock/staging 记录、复核、SQLite staging 写穿、SQLite read-path、审核详情/核心就绪、Review Center 展示、Grading Report 展示和平台实体 readiness evidence 接入已完成；真实数据库 adapter、真实平台复核 API 和生产任务队列未做且当前暂停。后续不再重复迁移 record create/review/list/get、SQLite 查询路径、审核页展示面板、评分报告页复核面板或 readiness evidence 字段，同类工作转向镜像/隔离质量或核心回归实际运行记录。 |
| Grading SQLite 本地仓储与有限 worker | 本地 SQLite schema 初始化、`grading_jobs` / `grading_records` 表、JSON 字段 round-trip、从 JSON store 同步 job / record、计数和状态摘要；支持显式 `dbPath` / `--db-path` 的 job 创建、查询、执行读写本地 SQLite，record 列表/详情 API 也支持显式 `dbPath` 直读 SQLite；Backend Mock 支持 `LAB_BACKEND_GRADING_DB_PATH` / HTTP `--grading-db` 作为 Grading Job API 默认 SQLite staging 路径；`worker-run-once` 支持过期 `RUNNING` claim 回收、`maxAttempts` 重试上限、领取 `QUEUED` / `FAILED` job 后单次执行并镜像回 JSON store；`worker-drain-once` / `/api/grading/workers/drain-once` 可顺序执行有限批次，默认 5、最大 20，队列为空或单个 job 失败即停止，并返回 `workerDrain.quota`、`workerDrain.resourceCleanup` 和批次级 `GRADING_WORKER_DRAIN` 审计。 | `backend/grading_repository.py`、`backend/grading_worker.py`、`backend/mock_api.py`、`backend/mock_http_server.py`、`python lab_cli.py grade worker-run-once --lease-seconds 300 --max-attempts 3`、`python lab_cli.py grade worker-drain-once --limit 5`、`python -m backend.mock_http_server --grading-db examples/output/grading-local.sqlite3`、`POST /api/grading/jobs`、`GET /api/grading/records?dbPath=...`、`GET /api/grading/records/{id}?dbPath=...`、`POST /api/grading/workers/drain-once` | M | 本地持久化、SQLite job/record API read-path、SQLite job API/CLI、后端默认 SQLite staging 策略、claim lease、过期 claim 回收、重试上限、单次 worker、有限批次 drain、quota 摘要和资源保留计划已完成；不是生产数据库、生产队列、常驻后台 worker 或并发 worker，下一步只做平台复核接入、镜像供应链和真实后端 API，不再重复实现同义本地回收、默认路径、有限 drain、quota 摘要或 SQLite read-path。 |
| 平台实体本地预览 | Lab / Exam / Grading / PPT 产物进入审核和导入预览方向，四类 DSL 均可转成本地平台实体草稿并生成 import-preview、mock-import 和 import-dry-run DTO；`backend/agent_entity_service.py` 当前本地闭环只要求平台实体列表、详情、`agentEntityImportActivity`、`readiness-report`、`contract-validate` 和 `import-dry-run`；`examples/input/platform-contract.json` 只作为本地 staging 契约样例和 dry-run 字段回归输入。`import-send` / `import-status` / `import-result` / `signoff` / `final-publish-review-decision` 暂停，只保留为未来真实平台对接团队技术参考。v0.1.5 已把 PPT Generation、PPT Review 与 Platform Entities 的 `ppt_deck` 前端入口接到既有四类本地 API。 | Review Detail、Demo Bundle、`lab/exam/grade/ppt import-preview`、`lab/exam/grade/ppt mock-import`、`examples/input/platform-contract.json`、`platform-entity contract-validate --contract-config examples/input/platform-contract.json`、`platform-entity import-dry-run --contract-config examples/input/platform-contract.json`、`GET /api/agent-entities`、`GET /api/agent-entities/{id}`、`GET /api/agent-entities/readiness-report`、`POST /api/agent-entities/contract-validate`、`POST /api/agent-entities/{id}/import-dry-run`、`tests/test_backend_agent_entity_service.py`、`tests/test_backend_mock_api.py`、`tests/test_platform_api_contract.py`、`tests/test_frontend_manifest.py` | L | 本地 mock/staging mapping、只读查询服务层、readiness/activity 聚合、import-dry-run DTO、本地契约校验、四类 staging `contractConfig` 样例、字段映射 requestBody 预览和四类前端入口已完成；当前停止线是本地闭环，不要求平台 API base URL、`AGENT_API_TOKEN`、真实平台字段、平台状态、平台侧签收或真实发布。后续不再重复扩平台请求发送、状态查询、签收、最终发布复核或 HTTP adapter 门禁。 |
| MCP 本地服务 | MCP tool manifest、mock call、server info、调用审计、本地 line-delimited JSON-RPC stdio 服务，以及客户端视角 stdio smoke；`tools/call` 仍复用 Backend Mock、统一 JSON、审核边界和 `mcpToolCallRecords`；默认 `local-core-mvp` profile 已补齐本地 `GradingJob` / `GradingRecord` 核心工具，包括 `create/list/get/run_grading_job` 与 `create/list/get/review_grading_record`，并已封装本地平台实体 `list/get/contract-validate/readiness/import-dry-run` 工具；`lab-cli mcp call`、`server-call`、stdio `tools/call` 和底层 `invoke_mcp_tool()` 默认均使用 `local-core-mvp`，暂停工具必须显式 `--profile all` / `profile="all"` 才能用于历史契约回归；2026-07-12 已通过 `mcp stdio-local-core-demo` 完成真实本地客户端两阶段挂接证据：生成任务停在 `WAITING_REVIEW`，显式人工批准后才继续本地 import-preview / mock-import / dry-run、GradingRecord 读取和审计查询，最终停在 `LOCAL_CORE_MVP_STOP_LINE_REACHED`。 | `mcp-server/tools.manifest.json`、`mcp-server/server.contract.json`、`mcp_server/mock_tools.py`、`mcp_server/stdio_server.py`、`mcp_server/stdio_client_smoke.py`、`docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md`、`python lab_cli.py mcp stdio-smoke ...`、`python lab_cli.py mcp stdio-local-core-demo ...`、`python -m mcp_server.stdio_server`、`tests/test_mcp_manifest.py`、`tests/test_mcp_mock_tools.py::test_mcp_mock_tool_default_profile_blocks_paused_tools`、`tests/test_mcp_manifest.py::test_mcp_local_core_client_usage_doc_defines_default_profile_and_stop_line`、`tests/test_mcp_server_mock.py::test_mcp_server_mock_calls_grading_job_and_record_tools`、`tests/test_mcp_stdio_server.py`、`tests/test_mcp_stdio_client_smoke.py` | L | 本地 stdio MCP 服务、真实本地客户端挂接、默认核心工具 profile、评分任务流、评分记录读取、审计查询和本地 dry-run 已到当前停止线；不是网络 MCP 服务、生产权限系统、生产队列、真实平台 API 或新的 Agent 编排。后续只在新增稳定 CLI/API 后接入 profile，或转向 Agent MVP 体验，不再新增同义 mock server 壳、同义 stdio client smoke、重复评分 Job/Record MCP 壳、重复平台实体只读/契约校验壳、真实平台发送/status/signoff/final publish 默认工具或 Agent 编排空壳。 |
| Agent 编排雏形 | 单步/演示型编排设计，原则上只编排稳定 CLI / API。 | `delivery/REAL_DEMO_AGENT_WORKFLOW.md`、相关 agent 文档 | M | 设计和局部 mock 完成，真实 Agent 未做。 |
| Backend Mock | 本地 HTTP mock server、静态页面 API、审核中心可访问；`backend/app.py` 已提供框架无关 `BackendApiApp` / `BackendAppResponse`，统一承接 `/api/*` 转发、静态文件读取、JSON 错误响应和 HTTP 状态映射，`backend/mock_http_server.py` 只保留标准库 HTTP 读写适配；`backend/asgi_app.py` 已提供无第三方依赖的 `backend.asgi_app:app` ASGI 入口，支持 lifespan、GET/POST、header 透传和 JSON object body 校验，供后续 FastAPI / ASGI server 挂载；`backend/deployment.manifest.json` 已登记本地 HTTP、`BackendApiApp` 和 ASGI 三类后端入口、环境变量名称、CI smoke、核心回归矩阵 workflow、ASGI 挂载 smoke 与安全停止线；`/api/backend/core-readiness` 可只读汇总 AI Task、Artifact、Review、导入预览、Grading Job / Record / Worker 和 Audit 八类核心 API 的本地 contract、staging 数据和真实后端迁移缺口；Backend Core 本地 SQLite 已支持 `ai_tasks`、`artifacts`、`review_audit_events`、`operation_audit_events`、`platform_entities` 五张核心表初始化、JSON store 同步、只读摘要、`coreDbPath` 只读查询，并已支持 Lab / Exam / PPT 生成与 AI Task approve/reject 的 `coreDbPath` 写穿；`backend/core_contract.py` 已定义 repository contract、config、factory、SQLite adapter 和 adapter registry，`backend/core_service.py` 已依赖 factory + contract 承接路径解析、语义化只读查询、读写 staging、写穿摘要、`sqlite` / `postgresql` / `mysql` database URL 识别和脱敏摘要，路由不再直接拼接 Backend Core 表名；`backend/core_postgres_repository.py` 和 `backend/core_mysql_repository.py` 已提供 PostgreSQL / MySQL repository adapter 最小真实 driver 边界，支持 lazy driver import、可注入 connector、schema 初始化、AI Task / Artifact / Review Audit / Operation Audit / Platform Entity round-trip、summary 统计和密钥脱敏错误；`backend/core_postgres_migration.py` 与 `backend-core postgresql plan|init|summary|smoke` 已提供 PostgreSQL 测试库迁移和实跑证据入口；`backend/core_mysql_migration.py` 与 `backend-core mysql plan|init|summary|smoke` 已提供 MySQL 测试库迁移和实跑证据入口；两者都会显式注册 adapter、初始化 schema、读取摘要、写入 smoke 任务并验证审核 round-trip，同时保持连接串脱敏；`tests/test_backend_core_postgres_real_smoke.py` / `tests/test_backend_core_mysql_real_smoke.py` 可在显式 smoke 环境变量开启时作为真实测试库可选 CI smoke；`.github/workflows/backend-core-postgresql-smoke.yml` 已提供 GitHub Actions 临时 PostgreSQL service smoke；`.github/workflows/core-regression-matrix.yml` 已作为 PR 前核心回归矩阵 workflow 登记进部署清单，但远端实际运行结果仍需后续记录；`tests/test_backend_asgi_mount_smoke.py` 已用 in-process ASGI 覆盖 health、Backend Core DB/readiness、MCP server info/call 和最小 Bearer token 鉴权；默认 HTTP mock 不自动注册外部 adapter，部署或测试环境需显式注册后才连接 PostgreSQL / MySQL；`backend/core_task_service.py` 已作为第一条真实后端任务服务化入口，直接基于 repository contract 创建 `WAITING_REVIEW` AI Task、Artifact、Review Audit、Operation Audit 并执行人工 approve / reject 状态流转；`POST /api/backend/core-tasks` 与 `POST /api/backend/core-tasks/{id}/approve|reject|review` 已接入该服务，响应返回 `backendCoreTaskService` 并确认不写 JSON store、不自动审核、不发布；`backend/grading_job_service.py` 和 `backend/grading_record_service.py` 已分别承接评分 job 创建/同步运行与评分记录创建/人工复核；`backend/audit_query_service.py` 已承接 Provider / Review / Operation 三类审计查询、过滤校验和 JSON/Core repository 只读分支；`backend/agent_entity_service.py` 已承接平台实体只读查询、活动摘要、readiness 聚合、本地 `import-dry-run` 服务边界；`LAB_BACKEND_CORE_DATABASE_URL` 可作为本地 SQLite URL 或未来真实数据库 URL 入口，外部数据库 URL 未注册 adapter 时只返回 `BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE` 且不连接；`LAB_BACKEND_API_TOKEN` 可选开启最小 Bearer token 鉴权，`/api/health` 豁免。 | `python -m backend.mock_http_server --host 127.0.0.1 --port 8000`、`backend.asgi_app:app`、`backend/deployment.manifest.json`、`python lab_cli.py backend-core postgresql plan`、`python lab_cli.py backend-core postgresql init --confirm-test-database`、`python lab_cli.py backend-core postgresql summary`、`python lab_cli.py backend-core postgresql smoke --confirm-test-database`、`.github/workflows/backend-core-postgresql-smoke.yml`、`.github/workflows/core-regression-matrix.yml`、`LAB_BACKEND_CORE_POSTGRESQL_SMOKE=1 python -m pytest tests/test_backend_core_postgres_real_smoke.py -q`、`python -m pytest tests/test_backend_asgi_mount_smoke.py -q`、`POST /api/backend/core-tasks`、`POST /api/backend/core-tasks/{id}/review`、`POST /api/grading/records/{id}/review`、`GET /api/provider-audit-events`、`GET /api/review-audit-events?coreDbPath=...`、`GET /api/audit-events?coreDbPath=...`、`GET /api/agent-entities?coreDbPath=...`、`GET /api/agent-entities/{id}?coreDbPath=...`、`GET /api/agent-entities/readiness-report`、`POST /api/agent-entities/{id}/import-dry-run`、`tests/test_backend_deployment_manifest.py`、`tests/test_backend_agent_entity_service.py`、`tests/test_backend_core_postgres_repository.py`、`tests/test_backend_core_postgres_migration.py`、`tests/test_backend_core_postgres_real_smoke.py`、`tests/test_backend_asgi_mount_smoke.py`、`tests/test_backend_core_task_service.py`、`tests/test_backend_grading_record_service.py`、`tests/test_backend_audit_query_service.py`、`tests/test_backend_mock_api.py::test_backend_core_db_api_init_sync_summary_and_readiness`、`tests/test_backend_mock_api.py::test_backend_core_db_api_reports_unregistered_external_database_adapter_without_secret_leak`、`tests/test_backend_asgi_app.py`、`tests/test_backend_app.py`、`tests/test_backend_core_service.py`、`tests/test_backend_core_contract.py` | L | 可演示，非生产服务；readiness、core SQLite 读写 staging、factory/contract/adapter 服务边界、PostgreSQL / MySQL adapter 可注入实现、PostgreSQL / MySQL 测试库迁移 CLI、PostgreSQL / MySQL 可选真实库 smoke 入口、GitHub Actions 临时 PostgreSQL CI smoke 配置、core regression matrix workflow 登记、后端部署注册清单、ASGI in-process 挂载 smoke、platform_entities 本地 SQLite staging、最小 token 鉴权、本地 sqlite URL 默认入口、外部 DB URL 识别与脱敏、未注册 adapter 不连接、后端 app/ASGI 适配边界、repository-backed 任务服务、评分 job 服务、评分记录复核服务、审计查询服务、平台实体查询服务和本地 import-dry-run 服务边界已到位；下一步应做本地评分记录闭环、审核详情/前端展示和核心回归实际运行记录；真实平台 API 字段映射、平台发送/status、平台侧签收和真实发布当前暂停，不再扩展同义 mock shell、HTTP handler 路由壳、ASGI 壳、部署入口清单壳、重复评分记录服务层、重复审计查询服务层、重复平台实体只读查询壳、重复导入记录写路径、重复 send/status 服务迁移、重复迁移入口、重复 smoke 入口、同义 CI 壳或 database URL 门禁壳。 |
| Frontend 静态页 | Review Center、Grading Report、Audit、Labs/PPT 等静态/Mock 页面；`ai-tasks.html` 已引入 `frontend/ai-tasks-data.js`，在同源 Backend Mock 启动时只读加载 `GET /api/ai-tasks`、`GET /api/ai-tasks?status=WAITING_REVIEW`、`GET /api/ai-tasks/{id}` 和 `GET /api/review-task-summary`，刷新任务数量、待审核队列、优先级摘要和选中任务 JSON，接口不可用时保留 `STATIC_HTML_FALLBACK`；`lab-generate.html` 已作为 `LocalCoreGenerationWorkspace` 引入 `frontend/lab-generate-data.js`，在同源 Backend Mock 启动时可调用 `POST /api/labs/generate`，基于本地 Markdown 创建 `WAITING_REVIEW` Lab 任务并展示 Lab DSL、素材分析、Provider 审计和发布阻断摘要，接口不可用时保留静态预览，页面自身不读取密钥、不直接调用真实 LLM；`exam-generate.html` 已作为 `LocalCoreGenerationWorkspace` 引入 `frontend/exam-generate-data.js`，在同源 Backend Mock 启动时可调用 `POST /api/exams/generate-from-lab`，基于 Lab ID 创建 `WAITING_REVIEW` Exam / Grading 任务摘要，并只展示候选安全题目、评分计划数量、Provider 审计和标准答案/评分引用隐藏状态，页面自身不读取密钥、不直接调用真实 LLM；`grading-report.html` 已引入 `frontend/grading-report-data.js`，在带 `file` 参数打开时调用 `GET /api/grading/report?file={file}&taskId={id}`，刷新首屏总分、得分、评分项、执行数、报告路径、`reportDetail.sandboxPolicy`、`explainability` 和 evidence/decision 只读摘要，并调用 `GET /api/grading/records?taskId={id}` 展示评分记录复核状态；Review Center 已支持 `agentReport` 查询参数只读加载真实 workflow report，并能把自定义真实输出批次的 Lab / Exam / Grading / PPT 路径映射到 Review Queue、DSL preview、DSL artifact link、Workflow Report artifact link 和 Exam 候选安全预览；带 taskId 和仅 path-only 的轻量 report 都已覆盖；独立 `lab-review.html` / `exam-review.html` / `grading-review.html` / `ppt-review.html` 会继承 URL 中的 `agentReport` 与 `coreDbPath`，继续读取同一份真实 workflow report synthetic detail；Review Center 的静态和动态“打开 Lab / Exam / Grading / PPT 审核”入口也会保留 `agentReport` 与 `coreDbPath`。 | `frontend/*.html`、`frontend/mock-data.json`、`frontend/ai-tasks-data.js`、`frontend/lab-generate-data.js`、`frontend/exam-generate-data.js`、`frontend/grading-report-data.js`、`frontend/review-detail-data.js`、`tests/test_frontend_manifest.py`、`tests/test_backend_mock_api.py::test_review_center_maps_agent_report_batch_to_queue_and_synthetic_detail` | L | 演示可用，AI Task 页只读 API 渐进增强、Lab Generate 页本地核心生成入口、Exam Generate 页 Lab → Exam/Grading 本地核心生成入口、Grading Report 页本地只读报告加载与评分记录复核状态展示、Review Center 自定义真实输出批次映射、独立审核页 agentReport 参数继承和 Review Center 到独立审核页链接透传已完成；后续只做真实前端 2.0 视觉/交互产品化或真实 API 挂载后的具体兼容修正，不再围绕 agentReport 队列、DSL preview、artifact path 映射、独立详情页 query passthrough 或审核入口链接透传追加同义展示壳。 |
| 文档与防循环规则 | 阶段封口、运营暂停、真实 SDK 后进入核心业务。 | `AGENTS.md`、`docs/12_PHASE_CUTOVER_AND_CORE_BUSINESS.md` | M | 已完成，本文件作为后续导航。 |
| 运营交付材料 | 既有运营页、交付包、Runbook 已收尾归档。 | `delivery/`、`frontend/operations-*.html` | M | 暂停扩展，只允许勘误。 |

---

### Backend API 执行锚点

- ASGI 测试环境挂载已补齐本地 in-process smoke 证据：`tests/test_backend_asgi_mount_smoke.py` 覆盖 `backend.asgi_app:app`、health、Backend Core DB init/summary/readiness、MCP server info/call 和最小 Bearer token 鉴权边界；`python lab_cli.py backend-core asgi-smoke --output examples/output/backend-asgi-smoke-report.json` 可把同一组检查落盘为 JSON evidence，供本地验收、CI artifact 或测试环境挂载记录复用。
- `backend/deployment.manifest.json.testEnvironmentMount.status=IN_PROCESS_ASGI_SMOKE_READY` 是当前测试环境挂载停止线；后续如果继续做“测试环境挂载”，只记录外部测试环境真实服务挂载结果、网关配置或具体兼容性修复，不再新增同义 ASGI shell、重复 smoke 入口或部署壳。
- `POST /api/agent-entities/{id}/import-dry-run` 已支持 `coreDbPath` repository-backed 路径：从 Backend Core `platform_entities` 读取实体，复用同一 dry-run DTO 构建逻辑，并把 dry-run Artifact 与 `PLATFORM_ENTITY_IMPORT_DRY_RUN` 操作审计写回同一 repository；dry-run 会输出 `contractValidation`，CLI 与 HTTP 分别提供 `platform-entity contract-validate --contract-config ...` 和 `POST /api/agent-entities/contract-validate`，用于本地校验正式平台字段配置、endpoint、状态别名和 request body 映射；该能力不发送真实平台请求、不读取平台 token、不发布。后续不要重复实现“从 repository 读平台实体再生成 dry-run”或“平台契约配置本地校验”的同义迁移，除非真实平台 API 字段契约明确要求补新的业务字段映射。
- `POST /api/agent-entities/{id}/import-result` 已支持 `coreDbPath` repository-backed 路径：从 Backend Core `platform_entities` 读取实体，读取已发送的 `AgentEntityImportSendResult` 报告后登记人工确认的平台侧状态，并把更新后的平台实体、结果 Artifact 与 `PLATFORM_ENTITY_IMPORT_RESULT_RECORD` 操作审计写回同一 repository；该能力不查询真实平台、不读取平台 token、不发送请求、不发布。后续不要重复实现“从 repository 读平台实体再登记 import-result”的同义迁移，除非真实平台 API 字段契约明确要求补新的业务字段映射。
- `GET /api/agent-entities/{id}?coreDbPath=...` 与 `GET /api/agent-entities/readiness-report?sourceTaskId=...&coreDbPath=...` 已支持 repository-backed 活动摘要和 readiness 聚合：详情会读取 Backend Core 中的 `platform_entities`、`artifacts`、`operation_audit_events`，readiness 会汇总 preview、mock-import、dry-run、import-result 和人工导入进度；该能力只读，不发送平台请求、不发布。后续不要再追加同义“Backend Core readiness 只读壳”，除非真实平台 API 字段契约需要补正式业务字段。
- `GET /api/agent-entities/readiness-report?sourceTaskId=...&coreDbPath=...&gradingDbPath=...` 已支持把 Backend Core 的平台实体 / Artifact / 操作审计与 Grading SQLite 的 `grading_records` 只读拼接，输出 `LOCAL_SQLITE_GRADING_RECORD_READINESS_BRIDGE`、`gradingRecordExternalSourceUsed` 和 GradingRecord 复核 ready/blocked 统计；`gradingDbPath` 不存在时只返回 `available=false`，不会创建 SQLite 文件。后续不要再围绕“平台实体 readiness 读取评分记录证据”追加同义桥接或只读壳，除非真实平台 API 字段契约需要补正式业务字段。

### Frontend API 渐进增强锚点

- `review-center.html` 已支持 `coreDbPath` 只读补充：详情读取会保留原有 `GET /api/review-tasks/{id}` 聚合审核详情，同时在 URL 带 `coreDbPath` 时调用 `GET /api/backend/core-tasks/{id}?coreDbPath=...` 作为 repository-backed 任务基本信息 fallback；该能力只填充标题、状态、artifact 计数和发布阻断摘要，不创建任务、不审核、不发布。后续不要继续为审核页追加同义 Backend Core 只读壳，除非真实前端 2.0 或真实后端 API 挂载明确需要新的业务字段。
- `lab-generate.html` 与 `exam-generate.html` 已收敛为 `LocalCoreGenerationWorkspace`：Lab 生成页的 `LabGenerationCloseLoopAction` 会在页面初始化和 `POST /api/labs/generate` 成功后刷新审核中心、Lab 审核页和本地导入预览深链；Exam 生成页的 `ExamGenerationCloseLoopAction` 会在页面初始化和 `POST /api/exams/generate-from-lab` 成功后刷新审核中心、Exam 审核页、Grading 审核页、Exam 导入预览和 Grading 导入预览深链。两个页面都会从 URL 读取 `coreDbPath`、`gradingDbPath`、`agentReport`，生成请求 body 只写入 `coreDbPath` 以便任务和 Artifact 进入同一本地 Backend Core repository，后续 Review Center、独立审核页和 Platform Entities 深链继续保留三类本地上下文。两个工作区都只读取本次生成响应，不新增 API，不自动审核、不发布、不调用真实平台；前端自身不读取密钥、不直接调用真实 LLM，真实 LLM 产物仍通过 CLI / one-click / 后端既有链路进入同一审核闭环；Exam 固定 `answerVisibleToCandidate=false` 与 `gradingRefVisibleToCandidate=false`。后续不要再围绕生成页追加同义“生成成功下一步/上下文透传/结果导航”壳，除非真实 API 返回字段变化导致深链错误。
- `ppt-generate.html` 已补齐同一条本地核心生成工作台：页面通过 `PptGenerateDataLoader` 调用 `POST /api/ppt/generate`，从本地 Markdown 创建 `WAITING_REVIEW` PPT DSL 任务，并将 `taskId`、`pptDslPath`、`coreDbPath`、`gradingDbPath`、`agentReport` 透传到 Review Center、PPT 审核页和 `entityKind=ppt` 本地导入预览入口。三类生成页的同源 HTTP 回归均覆盖“页面资源可加载 -> 发起 Mock 生成 -> 生成 DSL 路径 -> 审核详情仍为 WAITING_REVIEW”；PPT 页面不输入或保存模型密钥，不生成真实 PPT 文件，不发布，也不出现真实平台发送入口。该生成工作台已达到当前停止线，后续只修复具体 API、可用性或视觉交互缺陷，不再新增同义生成导航壳。
- `generation-workspace.html` 已收敛为精简教学包生成入口：页面只调用一次 `POST /api/phase2/workflows/content-generation/run` 并固定传 `artifactProfile=teaching-core`，从同一本地教学素材生成 Lab / Exam / Grading DSL，消费 `createdTasks`、`generatedDsl`、`workflowRun`、候选安全预览和教学包摘要，展示三类进度、Schema/内容质量状态、产物路径和审核入口；成功批次固定产生 3 个 `WAITING_REVIEW` 任务，不创建 PPT 任务。默认 Mock，真实模式需要显式确认且密钥只由同源后端读取；前端固定 `frontendDirectRealLlmCall=false`、`answerVisibleToCandidate=false`、`autoPublishAllowed=false`。该精简生成入口已达到当前停止线，下一步按同一 `workflowRun.id` 聚合审核，不再新增第二个批次生成页或同义后端编排接口。
- `grading-workspace.html` 已补齐本地自动评分工作台：使用已有 GradingJob / GradingRecord HTTP 服务执行“创建任务 -> 运行受控评分 -> 读取评分记录 -> 人工记录 approve-ready / needs-evidence / needs-revision”的同步闭环；页面从 AI Task 与 Grading Report 进入时保留 `taskId`、`coreDbPath`、`gradingDbPath`、`agentReport`，运行后回到 Grading Report、Review Center 和 AI Task。页面执行仅限已有本地受控评分 API，记录复核不改变 AI Task 状态，不自动审核、不发布、不发送真实平台请求。后续只处理实际评分执行、隔离、报告可读性或复核交互缺陷，不再创建同义评分工作台或门禁。
- `ai-tasks.html` 已新增 `TaskExecutionWorkspace` 本地闭环导航工作区：复用 `GET /api/ai-tasks`、`GET /api/backend/core-tasks?coreDbPath=...`、`GET /api/ai-tasks/{id}`、`GET /api/review-task-summary` 和当前任务的 `GET /api/grading/records` 只读数据，在页面初始化、静态 fallback 和选中任务时刷新审核中心、评分报告和本地导入预览入口。Exam / Grading 生成任务只要已关联 `GradingRecord.reportPath`，即可打开同一份本地评分报告和评分工作台；所有跳转保留 `coreDbPath`、`gradingDbPath`、`agentReport` 上下文，并展示候选答案保护、下一步人工动作和 `method=GET only` 边界；长状态、本地路径和 report 参数会在卡片内换行，避免 1280px 宽度下横向滚动。该工作区不新增 API、不发送 POST、不 approve/reject、不批量变更、不启动 Agent、不发布。后续不要再围绕 AI Task 首屏追加同义“任务导航/状态总览”壳，下一步前端产品化应转向生成页、导入预览页或具体视觉/交互缺陷。
- `review-center.html` 已新增 `MVP Review Workspace` 首屏工作区：复用 `GET /api/review-task-summary`、`GET /api/review-tasks/{id}` 和 `GET /api/review-tasks/{id}/core-readiness`，汇总四类真实 DSL 批次校验数、当前任务、评分证据、本地导入预览、当前审核入口、评分报告入口和下一步人工动作；页面初始化、详情 404 或静态兜底时也会把首屏审核页和评分报告入口刷新为带 `coreDbPath`、`gradingDbPath`、`agentReport` 的本地深链，长状态、路径和 `entryHref` 会在卡片内换行，避免 1280px 宽度下横向滚动；首屏使用 `LOCAL_CORE_MVP`，明确真实 LLM 产物为只读加载且页面不直接发起 LLM 请求，避免把已加载真实产物误标为 Mock。评分报告入口只在 `mergedGradingEvidence.latestReportPath` 存在时启用，防止将 Lab / Exam / PPT DSL 路径误传到评分报告页。该工作区不新增 API、不执行 CLI、不 approve/reject/publish，只减少演示时在队列、证据、导入预览和报告入口之间来回查找。后续不要再围绕 Review Center 首屏追加同义“总览/工作台/摘要”壳，下一步前端产品化应转向 Grading Report、AI Task、生成页或导入预览页的具体体验缺陷。
- `grading-report.html` 已新增 `ReviewerReportWorkspace` 首屏审核工作区，并标注为 `LOCAL_CORE_MVP`：复用 `GET /api/grading/report`、`GET /api/grading/result-preview`、`GET /api/grading/evidence-readiness`、`GET /api/grading/records` 和 `GET /api/review-tasks/{id}` 已有只读数据，汇总评分、evidence readiness、decision note、GradingRecord 复核状态、候选答案保护和审核中心记录结论入口；页面已消费 `GET /api/grading/report?file={file}.report.reviewerSafetySummary`，用 `ReviewerSafetySummary` 展示是否可人工记录 `approve-ready`、阻断原因、人工检查项、受控容器执行状态和自动发布边界；返回审核中心记录结论时会保留 `coreDbPath`、`gradingDbPath`、`agentReport` 上下文；长状态、路径和本地 report 参数会在卡片内换行，避免 1280px 宽度下横向滚动。页面读取真实本地评分 evidence 时不再误标为 Mock，接口不可用时才保留静态 fallback；不新增 API、不执行评分、不创建记录、不 approve/reject/publish、不调用真实平台。后续不要再围绕 Grading Report 首屏追加同义“审核摘要/工作台”壳，下一步前端产品化应转向 AI Task、生成页、导入预览页或具体视觉/交互缺陷。
- `agent-entities.html` 当前默认只做本地导入闭环：读取 `GET /api/agent-entities/{id}` 与 `GET /api/agent-entities/readiness-report`，展示实体详情、导入核查报告、本地 mock-import、`POST /api/agent-entities/contract-validate`、`POST /api/agent-entities/{id}/import-dry-run` 和四步 stepper（mock-import、dry-run、返回审核中心、未来平台对接暂停说明）；页面 URL 支持 `entityKind=lab|exam|grading|ppt`、`coreDbPath`、`gradingDbPath`、`agentReport`，列表、详情、readiness、已审核任务候选查询、手动 dry-run 和“准备演示草稿”的四类 import-preview / mock-import / import-dry-run 使用同一 Backend Core repository。审核详情页的人工 approve/reject 同样把 `coreDbPath` 写回本地任务仓储，避免导入页读取默认 JSON store 后误报 `NO_APPROVED_TASKS`。`gradingDbPath` 会传给 readiness 以只读拼接评分记录复核证据，返回审核中心时也保留这些本地上下文。“准备演示草稿”还会复用页面 `contractConfig` 生成本地 dry-run DTO，避免 Core/SQLite 演示链路写入默认 JSON store。页面会优先匹配 URL 中的 `sourceTaskId + entityKind`，若本地尚无对应实体草稿则显示 `LOCAL_ENTITY_NOT_PREPARED` / `RequestedEntityPlaceholder` 占位详情并保持返回审核中心指向当前任务，不自动选中历史实体，导入动作区会提示 `nextLocalAction=prepare_demo_draft_or_run_mock_import` 且不把占位实体当作可 dry-run 实体；长状态标签和左侧实体列表的 `entityType/sourceTaskId/status` 长标签会在卡片内换行，避免 1280px 宽度下横向滚动或内部挤出。页面不提供 `import-send`、`import-status`、`import-result`、平台侧 `signoff` 或最终发布按钮，不绑定这些 POST 路径，也不要求平台 API base URL 或平台 token。这是导入预览页当前的产品化停止线。后续不再围绕该页追加同义展示壳、契约校验页、重复 contractConfig 输入或真实平台发送/状态/签收/发布入口，除非用户明确恢复真实平台后端对接。

## 4. 当前 MVP 完成状态

当前 MVP 默认开发范围已全部达到停止线，暂无可自动继续展开的 P0：

| 功能 | 完成证据 | 状态 |
| --- | --- | --- |
| Lab + Exam/Grading 质量 | 固定离线样本、Schema 校验、归一化和跨产物引用回归通过；在线仍只按实际失败样本修复。 | 已完成 |
| 单一审核流程 | 默认审核入口可按同一 `workflowRun.id` 查看三类产物并逐项批准或退回。 | 已完成 |
| 本地教学包导出 | 三项全部批准后可确定性导出六成员 ZIP；阻断路径无半包、无外部发送或自动发布。 | 已完成 |
| 精简闭环回归 | Mock 正常、输入/Schema 错误、审核状态、候选人脱敏、CLI/API/前端契约及全量回归通过。 | 已完成 |

### 历史能力候选（默认冻结）

下表记录已经实现或曾规划的更大范围能力。表内原有优先级仅用于历史追踪，不覆盖本文件第 1.2 节和上面的 MVP 完成边界；除非用户明确恢复，否则全部视为冻结或兼容维护。

| 功能 | 还缺什么 | 复杂度 | 历史优先级 | 做到什么就停 |
| --- | --- | --- | --- | --- |
| 真实 LLM 输出稳定性 | 针对真实模型常见 Schema 偏差做归一化、重试/修复、错误报告聚合。 | M-L | P0 | DeepSeek v4 flash 已连续多输入生成 Lab / Exam / Grading / PPT 并通过 12/12 DSL 校验；后续只有出现真实失败样本才补归一化和诊断。 |
| 一键真实演示闭环 | 把真实生成、校验、审核详情、PPTX、评分证据、导入预览串成一条明确命令或脚本；`real-dsl-demo one-click` 已输出 `entryRoutes` 导航索引，指向审核中心、四类审核页、平台实体页、评分报告页和产物文件；`real-dsl-demo close-loop` 的平台实体 readiness 统计明确限定为 Lab / Exam / Grading 三类可导入实体，PPT 继续停留在 `WAITING_REVIEW` 页级审核，不计入三类导入闭环。 | M | P0 | 用户按一份说明和 `oneClick.entryRoutes` 能从输入 Markdown 得到可审核成果包并找到复核入口；三类导入闭环通过后切到后端/API/前端产品化，不围绕 PPT 是否计入 close-loop 或入口索引反复改统计。 |
| 审核详情真实化 | Review Center 已从真实输出/本地 API 加载任务、DSL preview、quality signals 和 artifact；`reviewPage.dslPreview` 会读取本地 Lab / Exam / Grading / PPT DSL 文件并展示 `contentLoaded`、`schemaValidated`、标题、summary、safePreview、candidateSafety 和 reviewSafety，Exam 预览不展开答案或 gradingRef。 | L | P0 | 本地真实 DSL 摘要、质量信号、Artifact 和审核阻断状态已可展示；后续只做 UI 产品化、真实 API 挂载后的视觉/交互修正，不再追加同义 DSL 摘要壳。 |
| 平台实体本地闭环 | 将 DSL 转为本地 Lab / Exam / Grading / PPT 实体草稿、import-preview、mock-import 和 import-dry-run DTO；四类前端入口已在 v0.1.5 接通。`import-send` / `import-status` / 真实平台字段映射当前暂停，只作为未来其他团队对接真实平台的技术参考。 | M-L | P1 | 本地 staging/mock target、四类本地实体 import-preview、mock-import、dry-run DTO 与前端入口已覆盖后即停止；不得要求平台 API base URL / token，不继续执行真实平台发送、状态查询或平台侧签收。 |
| 本地后端 API 与仓储 staging | 已有 `/api/backend/core-readiness`、Backend Core SQLite、PostgreSQL / MySQL adapter 测试边界、ASGI 入口、核心任务服务、评分 job/record 服务、审计查询服务和平台实体本地服务。真实平台正式接口、真实平台字段、生产认证和外部测试环境挂载当前暂停，不作为默认下一步。 | L-XL | P1 | 本地 API / SQLite staging / ASGI smoke / 核心服务边界可支撑本地演示即可停止；后续优先补真实 LLM 质量、评分记录、审核页和本地前端，不继续推进真实平台 API 对接。 |
| 前端 2.0 | 用真实 API 做实验生成、试题生成、评分报告、审核中心和 AI Task 页面；AI Task 页已完成普通任务 / Backend Core 只读 loader，并在 v0.1.4 增加 `agentReport` 真实批次摘要、四类产物 synthetic task card 和带上下文的 Review Detail 加载。 | XL | P1 | 先完成核心 5 页，不继续堆运营页；AI Task 页已达到普通任务、Backend Core 和自定义真实报告批次的只读列表/详情加载停止线，下一步转生成页、审核页、评分报告页或导入预览页的具体产品化缺陷。 |
| 受控评分沙箱生产化 | 已有本地 Docker PoC、本地 `GradingJob`、本地 `GradingRecord`、显式/后端默认本地 SQLite 仓储、claim lease、过期 claim 回收、重试上限、单次 worker、有限批次 drain、quota 摘要、资源保留计划、本地人工复核、审核详情/核心就绪接入、平台实体 readiness 的 GradingRecord 复核证据接入和本地镜像供应链审计；2026-07-12 已收口 `local-python-pytest-controlled-v1` 执行画像，报告/评分记录保留网络、只读挂载、资源限制、输出策略、镜像 labels/tag/digest 与 Docker/镜像不可用诊断。还缺真实后端 API、真实平台复核 API、生产镜像仓库/签名策略和更严格隔离策略。 | XL | P1 | 支持一类题型进入真实后端任务流和人工复核，并能在 `grading_rule` 平台实体 readiness 中看到评分记录复核证据；本地 Python/pytest 路径达到上述画像、诊断、测试和文档后停止，不再重复实现同义 PoC、默认 SQLite 策略、claim 回收、有限 drain、quota 摘要、镜像审计透传、readiness evidence 字段或新增禁用壳。 |
| 自动评分生产化 | 从 Grading DSL 到评分任务队列、结果入库、人工复核、选手不可见答案保护。 | XL | P1 | 支持一类语言/题型先闭环，不一次性覆盖所有题型。 |
| PPT 质量提升 | 版式模板、主题、图片/图表、导出预览质量、人工调整入口。 | L | P2 | 先让 5-8 页教学 PPT 达到可演示，不做复杂在线编辑器。 |
| MCP Server 真部署 | 启动真实 MCP Server，暴露稳定工具，接入工具权限、审计、审核；本地 stdio 客户端配置和 `local-core-mvp` 调用顺序已记录。 | L-XL | P2 | 只封装已稳定 CLI/API，不把业务规则藏到 Agent prompt；当前本地停止线是 stdio + local-core profile + 人工审核点，不做网络 MCP 服务或真实平台工具。 |
| 智能体 MVP | Agent 根据目标调用核心 MCP 工具，生成任务计划并停在审核点。 | L-XL | P2 | 能完成一条演示链路，不允许自动发布或自动销毁资源。 |
| VM / Notebook 环境管理 | 实验环境镜像、Notebook 启停、资源配额、回收、审计。 | XL | P3 | 先对接测试环境，不碰生产云资源。 |
| CI / 回归测试 | 已新增本地固定回归测试矩阵：`quality regression-profiles` 可列出 `quick`、`core`、`backend-core`、`real-llm-offline`、`mcp` profile；`quality regression-matrix` 可运行预定义 pytest 子集并输出 JSON evidence，默认排除 `integration` 和 `real_llm_online`，不接受任意命令、不使用 shell；`.github/workflows/core-regression-matrix.yml` 已在 PR / 手动触发时先运行 `demo offline`，再调用同一个 `core` profile，并上传离线 Demo 与矩阵 JSON artifact，CLI 返回 `success=false` 时会显式失败；`grading_core` 已纳入受控 Docker evidence、evidence merge、评分 job/record 和 SQLite staging；`quick` / `core` profile 已包含 Lab 生成、Exam/Grading 生成、`offline_demo`、Grading stable v1、Backend ASGI、MCP stdio 和 Frontend core manifest；2026-07-04 已完成历史本地 `core` profile 实跑，`commandTotal=9`、`executedTotal=9`、`passedTotal=9`、`failedTotal=0`；新增离线 Demo 后的当前实跑结果记录在 `docs/26_CORE_REGRESSION_RUN_EVIDENCE.md`。 | `quality/regression_matrix.py`、`.github/workflows/core-regression-matrix.yml`、`python lab_cli.py demo offline`、`python lab_cli.py quality regression-matrix --profile quick/core --stop-on-failure`、`examples/output/regression-matrix-quick.json`、`docs/26_CORE_REGRESSION_RUN_EVIDENCE.md`、`tests/test_offline_demo.py`、`tests/test_quality_regression_matrix.py` | M | 本地 PR 前回归矩阵入口、离线 Demo CLI/测试和 GitHub Actions 配置已完成；后续只记录实际远端 workflow artifact，或在新增核心能力时向现有 profile 增补必要测试文件，不再新增同义测试矩阵壳、同义 CI 壳或任意命令执行器。 |
| 部署与运维 | Docker/服务部署、配置、日志、监控、密钥管理、告警。 | XL | P3 | 先部署开发/测试环境，不做生产 SLA 承诺。 |

### 4.1 可复现 DSL 质量基线

2026-08-13 新增 `quality dsl-eval`：用 20 个脱敏 case 覆盖 5 个教学领域、
中英文和 normal/boundary 变体，并对实际渲染后的 Lab / Exam / Grading / PPT
DSL 执行 Draft 2020-12、`WAITING_REVIEW`、跨产物引用/总分、候选人脱敏和
最小内容质量检查。它不接受任意命令，也不运行 pytest、真实 LLM 或选手代码，
因此是内容质量基线而不是第二套 regression runner。做到默认 corpus 20/20 通过、
破坏性 fixture 能稳定报错、CLI/CI 可复现后即停止；后续只加入经过脱敏的真实失败
样本，不继续堆同义 runner 或虚构质量规则。

### 4.2 可复现 Offline Demo

2026-08-13 新增 `demo offline` 作为无 API Key 的最短本地闭环入口。它复用
现有 Phase 2 Mock Workflow 和正式 Exam 候选人预览构建器，不复制生成、审核或
脱敏业务逻辑。入口输出四类 DSL 校验摘要、候选人预览路径、质量阻塞/告警数量、
`WAITING_REVIEW` 审核状态和本地安全标记；候选人预览与 summary 只有在校验通过后
才写入指定路径。

B1 停止线：默认 fixture 可稳定返回 `status=PASS`，四类 DSL Schema 通过，候选人
预览无答案泄漏，`blockingIssueTotal=0`，并由固定 quick/core 回归与 GitHub Actions
调用同一入口。达到该停止线后，不再新增第二个 offline runner、同义安全壳或展示页。

### 4.3 v0.1.3 PPT 质量预检切片

2026-08-16，PPTX Artifact 构建增加了本地 `quality.ppt_preflight`：在已通过
PPT Schema 校验、仍为 `WAITING_REVIEW` 的 DSL 上，逐页报告空标题、正文密度、
长文本、估算溢出和 renderer 最多显示 6 个 bullet 的截断风险。结果写入构建
JSON、manifest、`PPTX_FILE` Artifact metadata、Demo Bundle 和页级 `qaSignals`，
并加入 quick/core 固定回归矩阵。

该报告明确标记 `advisoryOnly=true`，不修改 DSL、不自动批准、不发布，也不把
启发式检查误报为像素级渲染验证。PPT 质量切片达到“正常样例无 issue、异常样例
可稳定报告 warning/blocking、PPTX 仍保持人工审核”停止线后，不继续扩展同义
展示壳；下一步回到 P1 评分隔离/报告缺口或具体前端交互缺陷。

### 4.4 v0.1.4 AI Task Center 真实报告批次回接

2026-08-22，`frontend/ai-tasks-data.js` 将 URL 中的 `agentReport` 转发给
`GET /api/review-task-summary?limit=5&detailMode=light&agentReport=...`。
当返回的 `realDemoReviewQueue.sourceMode` 为
`AGENT_REPORT_REAL_LLM_ARTIFACTS` 且本地任务列表为空时，Lab / Exam / Grading /
PPT 四类产物会被映射为 synthetic `WAITING_REVIEW` task card；点击卡片后，
loader 通过带 `agentReport`、`coreDbPath` 和 `gradingDbPath` 的
`GET /api/review-tasks/{id}` 加载同一批次的只读审核详情。

该切片只恢复真实工作流报告到 AI Task Center 的导航上下文，不创建任务、不
写入本地 store、不自动审核、不发布、不执行沙箱，也不展示 Exam `answer` 或
内部 `gradingRef`。普通 `/api/ai-tasks`、Backend Core SQLite 和 GradingRecord
路径保持兼容。达到“自定义报告无本地任务时四类卡片可见、详情可加载、上下文
保留、候选安全和 GET-only 边界通过固定契约测试”的停止线后，后续转向生成页、
审核页、评分报告页或导入预览页的具体交互缺陷，不继续扩展同义任务中心壳。

### 4.5 v0.1.5 PPT Deck 本地导入预览闭环

2026-08-22，PPT Generation 新增带本地上下文的 `entityKind=ppt` 深链，PPT
Review 复用 `frontend/review-import-preview-data.js` 调用既有
`POST /api/ppt/import-preview` 和 `POST /api/ppt/mock-import`。Platform Entities
的“准备演示草稿”也新增 `PPT_GENERATION` / `ppt_deck` 映射，可继续生成本地
import-dry-run DTO；`coreDbPath`、`gradingDbPath` 与 `agentReport` 跨页保留。

该切片只补齐已有四类后端能力的前端缺口。任务仍须先人工批准，所有操作固定
`databaseWritten=false`、`requestSent=false`、`realAgentImport=false`、
`realPublish=false`，到本地 dry-run 即停止。达到“四类生成/审核入口都能进入同一
Platform Entities 本地闭环、PPT 不再误回落到 Lab API、固定契约与浏览器回归通过”
停止线后，不继续围绕导入预览页增加同义步骤或真实平台操作。

### 4.6 v0.1.6 精简教学包生成

2026-08-23，既有 `POST /api/phase2/workflows/content-generation/run` 增加
`artifactProfile=teaching-core`。该 profile 在 Provider 层只生成 Lab / Exam /
Grading，创建 3 个 `WAITING_REVIEW` 任务，并在落任务前构建候选人安全 Exam
预览；响应同时返回以 `workflowRun.id` 关联三类任务的只读教学包摘要和审核入口。
`frontend/generation-workspace.html` 已显式使用该 profile，并只展示三类产物。

未传 profile 时继续按 `legacy-all` 生成历史四类产物。真实 LLM 的
`teaching-core` 路径只发送三类请求，不生成空 PPT 任务或 Artifact。非法 profile、
Provider/Schema 失败和候选预览脱敏失败都在创建审核任务前停止。达到“一份
Markdown 生成三类相互关联、Schema 已验证、候选安全且等待人工审核的产物”停止线
后，下一步进入同一批次的审核聚合，不继续增加同义生成 API、页面或门禁。

### 4.7 v0.1.7 教学包审核聚合

2026-08-23，`GET /api/review-task-summary` 增加可选 `workflowRunId`，从该运行
关联的 Artifact 与当前 AI Task 状态派生 `TeachingPackageReviewSummary`。摘要固定
聚合 Lab / Exam / Grading 的任务、路径、Schema/内容质量、候选人安全和逐项动作契约；
任一拒绝派生 `NEEDS_REVISION`，三项均批准派生 `APPROVED` 与
`exportReady=true`，其余保持 `WAITING_REVIEW`。未知运行返回 `NOT_FOUND`，历史
`legacy-all` 运行仍可按批次读取四类任务，但不启用教学包摘要。

`frontend/review-center.html` 已用 `workflowRunId` 展示三行审核流程，并逐项复用
已有 approve/reject API；拒绝必须填写 reason，动作完成后回读同一批次。页面只展示
Exam 候选人安全状态，不展示答案或内部 `gradingRef`，也不提供批量决定、自动发布或
本地导出动作。达到“同一批次三类产物可集中查看并逐项记录人工决定”停止线后，
下一步只进入本地教学包导出，不继续追加同义审核总览或批量状态接口。

### 4.8 v0.1.8 本地教学包导出

2026-08-23，新增 `lab-cli teaching-package export --workflow-run-id <id> --reviewer <name>`
与 `POST /api/teaching-packages/export`。两个入口复用同一本地导出服务，只接受
`teaching-core` WorkflowRun，并要求关联 Lab / Exam / Grading AI Task 均为
`APPROVED`。默认输出 `examples/output/teaching-packages/<workflowRunId>.zip`；只有 CLI
可用 `--output` 覆盖本地 ZIP 路径，API 固定使用默认路径，传入 `output` 返回
`VALIDATION_ERROR`。

导出前重新读取三类 Artifact、执行现有 DSL Schema 校验并重新构建候选人安全 Exam
预览；ZIP 固定且仅包含 `manifest.json`、`lab.json`、`exam.json`、`grading.json`、
`exam-candidate-preview.json` 和 `review-summary.json`。未知运行、历史 `legacy-all`、
未全部批准、Artifact 缺失、Schema/契约失败、候选泄漏或输出冲突都会返回统一错误，
且不留下部分包。`manifest.json` 不写导出人或时间，易变信息只进入 operation audit，
保持相同输入的 ZIP 确定性。该切片不新增 TeachingPackage 实体，不调用平台导入、网络、评分沙箱
或发布，也不改变审核任务状态。达到“全批准后可原子导出六成员本地 ZIP，任何阻断路径
无半包”的停止线后，不继续增加压缩格式、导出页、云上传或发布能力。

---

## 5. 后续推荐路线

### P0：已完成精简教学包闭环

1. 默认生成入口已选定为 `frontend/generation-workspace.html`，默认审核入口已选定为 `frontend/review-center.html`；盘点与兼容决策见 `docs/28_SIMPLIFIED_MVP_ENTRYPOINTS.md`。
2. `artifactProfile=teaching-core` 精简生成切片已完成；未传字段保持历史四类行为。
3. 默认审核入口按同一 `workflowRun.id` 展示三类产物、校验结果并支持逐项批准或退回的切片已完成。
4. 本地教学包导出已完成：只导出已审核闭环需要的六个 ZIP 成员，不发送外部平台、不自动发布。
5. Mock 正常、错误、状态和脱敏回归已完成；真实输出归一化仍只处理 Lab + Exam/Grading 的实际失败样本。

### P1：MVP 验收后单选

当前 MVP 五项验收条件已全部满足。下一阶段只有在用户明确选择后才允许进入以下一项：

1. PPT 产品化：把教学包扩展为 5-8 页可演示 PPT，不做在线编辑器。
2. 自动评分产品化：只支持一种语言/题型的受控执行、可解释证据和人工复核。

不得同时选择两项。未选择的一项继续冻结。

### 冻结路线

以下内容不是当前 P0/P1：本地平台实体与导入流程扩张、MCP/Agent 新能力、多页面工作台、数据库 adapter 扩张、真实平台、VM/Notebook、生产部署和运营材料。已有能力可做兼容性或安全修复，但不得以“补齐平台”名义继续产品化。

---

## 6. 地图专属停止线（全局约束见 `AGENTS.md`）

1. 本文件中的每个功能只做到对应“做到什么就停”，达到停止线后转入下一项，不在同一功能上追加同义壳、展示页或验收页。
2. Mock、真实 LLM、真实平台和真实云资源必须分层说明；演示通过不等于生产完成。
3. 真实 LLM 失败只优先修复 Lab + Exam/Grading 实际失败样本对应的 Prompt、归一化、Schema 或错误报告，不预先发明大量规则。
4. 当前前端只收敛一个生成入口和一个审核入口；不得继续并行产品化 AI Task、评分报告、导入预览等多个工作台。
5. 当前导出只落本地教学包；平台实体、`import-send`、`import-status`、平台签收和发布不作为下一步。
6. MCP、Agent、PPT、受控评分和数据库 adapter 保持已有兼容性，不新增产品能力，直到用户在 MVP 验收后明确选择下一阶段。

---

## 7. 近期建议任务清单

| 顺序 | 任务 | 复杂度 |
| --- | --- | --- |
| 1 | 已完成：默认生成入口选定 `generation-workspace.html`，默认审核入口选定 `review-center.html`；复用边界、兼容策略和差距记录在 `docs/28_SIMPLIFIED_MVP_ENTRYPOINTS.md`。 | S |
| 2 | 已完成：既有内容生成 API 增加 `artifactProfile=teaching-core`，默认生成入口只产出 Lab + Exam/Grading，并返回教学包级摘要、候选人安全预览和审核入口；未传字段保持历史四类行为。 | M |
| 3 | 已完成：默认审核入口在一条流程中展示三类关联产物、校验结果，并支持逐项批准或退回；拒绝必填原因，不提供批量决定。 | M-L |
| 4 | 已完成：增加不依赖平台实体的本地教学包导出；三项全部人工批准后原子写出固定六成员 ZIP，审核前或校验失败时不落部分包。 | S-M |
| 5 | 已完成：上述闭环的 Mock 正常路径、错误路径、状态和脱敏回归已覆盖；真实 LLM 仍仅追加实际失败样本。 | M |

当前状态：Markdown → Lab + Exam/Grading → 人工审核 → 本地 ZIP 导出已达到 MVP 停止线。必须等待用户在 PPT 产品化与自动评分产品化中明确选择一个下一阶段；此前四类 DSL 一键 Demo、PPTX、评分 evidence、平台实体、MCP 和 Agent 仍可回归或演示，但不再决定当前产品范围。
