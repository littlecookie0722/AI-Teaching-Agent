# Phase 1 本地演示验收 Runbook

本 Runbook 用于人工演示和验收 Phase 1 Mock 交付物。它不是自动化执行脚本，不接入真实大模型、真实云资源或真实智能体，不执行未知 Shell，不发布真实实验或考试。

## 输入说明

- `examples/input/demo-source.md`: 本地演示素材。
- `scripts/manifest.json`: 允许命令白名单与禁止模式。
- `config/delivery-package.contract.json`: Phase 1 交付包契约。
- `delivery/HIGH_RISK_MCP_HANDOFF.md`: 高风险 MCP Tool 运营交接清单。
- `delivery/high-risk-mcp-handoff.json`: 高风险 MCP Tool 运营交接机器契约。
- `mcp-server/high-risk-tool-safety.contract.json`: 高风险 MCP Tool 安全矩阵。
- `delivery/FINAL_SIGNOFF.md`: Phase 5 最终运营签收包。
- `delivery/final-signoff.json`: Phase 5 最终运营签收包机器契约。
- `delivery/OPERATIONS_MANUAL.md`: Phase 5 运营手册。
- `delivery/operations-manual.json`: Phase 5 运营手册机器契约。
- `skills/operations-skill-pack/SKILL.md`: Phase 5 运营 Skill 包。
- `skills/operations-skill-pack.contract.json`: Phase 5 运营 Skill 包机器契约。
- `delivery/STANDALONE_AGENT_DELIVERY.md`: Phase 5 独立智能体 Mock 交付说明。
- `delivery/standalone-agent-delivery.json`: Phase 5 独立智能体 Mock 交付机器契约。
- `delivery/ACCESS_ENTRYPOINTS.md`: Phase 5 IP + 端口访问入口说明，限定为本地静态入口和禁用的未来端口规划。
- `delivery/access-entrypoints.json`: Phase 5 IP + 端口访问入口机器契约。
- `delivery/PHASE5_MOCK_BASELINE.md`: Phase 5 Mock 基线冻结说明，作为真实 LLM PoC 前的收口门禁。
- `delivery/phase5-mock-baseline.json`: Phase 5 Mock 基线冻结机器契约。
- `delivery/DEMO_SCRIPT_CHECKLIST.md`: 运营演示脚本检查清单。
- `delivery/phase1-demo-script-checklist.json`: 运营演示脚本检查清单机器契约。
- `frontend/operations-launchpad.html`: 本地运营 Launchpad，推荐首个打开。
- `frontend/access.html`: 本地 IP + 端口访问入口页，仅展示静态页面和禁用的规划端口。
- `frontend/operations-presenter.html`: 本地运营讲解台，展示 speakerCue、验收信号和禁用动作。
- `frontend/operations-signoff.html`: 本地运营签收总览，展示 6/6 门禁、175/175 交付、20/20 自检、14/14 验收和 6/6 安全断言。
- `frontend/operations-demo-script.html`: 本地运营演示脚本页面，展示固定顺序和安全边界。
- `frontend/console.html`: 本地静态 Mock 控制台。
- `frontend/delivery.html`: 本地静态交付验收页面。

## 输出说明

- `examples/output/phase1-delivery-package.json`: `phase1 export` 生成的本地 Mock 交付包。
- `examples/output/phase1-acceptance-report.md`: `phase1 report` 生成的本地 Mock 验收报告。
- `frontend/operations-presenter.html`: 人工预览的讲解台静态页面。
- `frontend/access.html`: 人工预览的访问入口静态页面。
- `frontend/operations-signoff.html`: 人工预览的签收总览静态页面。
- `frontend/operations-demo-script.html`: 人工预览的演示脚本静态页面。
- CLI 输出必须保持统一 JSON envelope。
- 页面预览仅打开本地静态 HTML，不请求真实服务。

## 命令示例

按顺序手动执行：

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\access.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
start .\frontend\console.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_faq.py
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_cli.py
python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_mcp_mock_tools.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py
python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_frontend_manifest.py
python -m pytest
```

`start .\frontend\operations-launchpad.html`、`start .\frontend\access.html`、`start .\frontend\operations-presenter.html`、`start .\frontend\operations-signoff.html`、`start .\frontend\operations-demo-script.html` 和 `start .\frontend\console.html` 是人工预览动作，不在 `allowedCommands` 白名单中作为自动化命令执行。所有验证命令必须来自 `scripts/manifest.json` 的 `allowedCommands`。

## 验收检查

- `phase1 check` 返回 `success=true` 且 `data.passed=true`。
- `phase1 export` 返回 `success=true`，并生成本地交付包。
- `phase1 report` 返回 `success=true`，并生成本地 Markdown 验收报告。
- 交付包中的 `deliveryManifest.summary.missingRequired` 为 `0`。
- 交付包中的 `acceptanceSummary.passed` 为 `true`。
- 交付包中的 `safetyAssertions[*].passed` 全部为 `true`。
- `delivery/HIGH_RISK_MCP_HANDOFF.md` 确认高风险 MCP Tool 只创建审核意图或只读查询，不执行真实发布、真实销毁或二次确认通过动作。
- `delivery/OPERATIONS_MANUAL.md` 确认运营流程只依赖本地页面、白名单命令、人工审核和本地生成证据。
- `skills/operations-skill-pack/SKILL.md` 确认运营复用 Skill 包只组合现有 Mock Skill、Prompt、Workflow、Schema 和 CLI。
- `delivery/STANDALONE_AGENT_DELIVERY.md` 确认独立智能体交付只描述本地 Mock Tool 和 Mock Workflow 编排，不连接真实外部平台。
- `delivery/ACCESS_ENTRYPOINTS.md` 确认访问方式只包含本地静态 HTML 和禁用的规划端口，不启动真实 HTTP 服务、不绑定公网或局域网 IP。
- `delivery/PHASE5_MOCK_BASELINE.md` 确认 Mock 基线冻结为 175/175，真实 LLM PoC 必须默认关闭并显式 opt-in。
- `review batch-summary`、`GET /api/review-task-summary` 和 MCP `get_review_task_summary` 确认 `reviewPriorityQueue` 三链路同源，且只用于人工分拣，`autoApproveAllowed=false`、`batchStateChangeAllowed=false`。
- `tests/test_real_sdk_minimal_impl.py` 确认真实 SDK 最小实现外壳即使通过 enablement 和显式 implementation opt-in，也仍默认禁用。
- `delivery/FINAL_SIGNOFF.md` 确认最终签收顺序只引用本地文件、静态预览、生成证据和白名单命令。
- `frontend/operations-launchpad.html`、`frontend/access.html`、`frontend/operations-presenter.html`、`frontend/operations-signoff.html`、`frontend/operations-demo-script.html`、`frontend/console.html` 和 `frontend/delivery.html` 均只展示 Mock 状态。

## 测试方式

```powershell
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_faq.py
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_cli.py
python -m pytest tests/test_backend_mock_api.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_mcp_mock_tools.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py
python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py
python -m pytest tests/test_final_signoff.py
python -m pytest
```

## 限制说明

- 不执行未知 Shell 脚本。
- 不运行输入素材中的 Shell 内容。
- 不接入真实大模型或真实 Provider。
- 不启动真实智能体。
- 不创建、修改或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不自动发布或真实发布生成内容。
- 不输出密钥，不展示选手端应隐藏的标准答案。
