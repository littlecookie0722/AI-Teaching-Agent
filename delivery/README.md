# delivery

Phase 1 运营交付入口索引目录。当前只维护本地 Mock 交付入口、静态预览、Runbook、验收报告命令和安全边界，不发布真实实验、考试或环境。

## 输入说明

- `phase1-delivery-index.json`: Phase 1 本地交付入口索引契约。
- `phase1-faq.json`: Phase 1 FAQ 与故障排查机器契约。
- `FAQ.md`: Phase 1 FAQ 与故障排查手册。
- `phase1-handoff.json`: Phase 1 运营交接清单机器契约。
- `HANDOFF.md`: Phase 1 运营交接检查清单。
- `phase1-demo-script-checklist.json`: Phase 1 运营演示脚本检查清单机器契约。
- `DEMO_SCRIPT_CHECKLIST.md`: Phase 1 运营演示脚本检查清单。
- `real-demo-script.json`: 真实 LLM 产出成果演示脚本机器契约。
- `REAL_DEMO_SCRIPT.md`: 真实 LLM 产出成果演示脚本。
- `real-demo-quick-commands.json`: 真实 LLM Demo 快速命令机器契约，串联复放、审核队列、MCP 退回修改和 Mock 修订稿生成。
- `REAL_DEMO_QUICK_COMMANDS.md`: 真实 LLM Demo 快速命令清单。
- `real-demo-agent-workflow.json`: 真实 LLM Demo Agent Workflow 设计契约，描述未来演示智能体可调用的 MCP 工具、状态检查和人工审核停点。
- `REAL_DEMO_AGENT_WORKFLOW.md`: 真实 LLM Demo Agent Workflow 设计说明。
- `phase2-readiness-gate.json`: Phase 2 准入门禁机器契约。
- `PHASE2_READINESS.md`: Phase 2 准入门禁说明。
- `OPERATIONS_MANUAL.md`: Phase 5 运营手册。
- `operations-manual.json`: Phase 5 运营手册机器契约。
- `skills/operations-skill-pack/SKILL.md`: Phase 5 运营 Skill 包。
- `skills/operations-skill-pack.contract.json`: Phase 5 运营 Skill 包机器契约。
- `STANDALONE_AGENT_DELIVERY.md`: Phase 5 独立智能体 Mock 交付说明。
- `standalone-agent-delivery.json`: Phase 5 独立智能体 Mock 交付机器契约。
- `ACCESS_ENTRYPOINTS.md`: Phase 5 IP + 端口访问入口 Mock 交付说明。
- `access-entrypoints.json`: Phase 5 IP + 端口访问入口 Mock 交付机器契约。
- `PHASE5_MOCK_BASELINE.md`: Phase 5 Mock 基线冻结说明，作为真实 LLM PoC 前置门禁。
- `phase5-mock-baseline.json`: Phase 5 Mock 基线冻结机器契约。
- `HIGH_RISK_MCP_HANDOFF.md`: 高风险 MCP Tool 运营交接清单。
- `high-risk-mcp-handoff.json`: 高风险 MCP Tool 运营交接机器契约。
- `FINAL_SIGNOFF.md`: Phase 5 最终运营签收包。
- `final-signoff.json`: Phase 5 最终运营签收包机器契约。
- `mcp-server/high-risk-tool-safety.contract.json`: 高风险 MCP Tool 安全矩阵。
- `providers/PHASE2_PROVIDER_PLAN.md`: Phase 2 Provider 接入规划，保持 MockProvider-first。
- `providers/phase2-provider-plan.contract.json`: Phase 2 Provider 接入规划机器契约。
- `providers/adapter.py`: Mock-only Provider Adapter 实现。
- `providers/provider-adapter.contract.json`: Mock-only Provider Adapter 机器契约。
- `ai_workflows/provider_adapter_workflow.py`: Workflow 侧 Provider Adapter helper。
- `frontend/operations-launchpad.html`: 本地运营 Launchpad，作为交付交接首选入口。
- `frontend/access.html`: 本地 IP + 端口访问入口说明页，只展示静态入口和禁用端口占位。
- `frontend/operations-presenter.html`: 本地运营 Presenter View，一页式展示讲解提示、验收信号和禁止动作。
- `frontend/operations-signoff.html`: 本地运营签收总览，一屏展示 6/6 门禁、175/175 交付、20/20 自检、14/14 验收和 6/6 安全断言。
- `frontend/operations-demo-script.html`: 本地运营演示脚本页面，展示固定演示顺序和安全边界。
- `frontend/real-demo.html`: 真实 LLM Demo 静态演示入口，展示 `RealDemoOneClickChecklist`。
- `frontend/review-center.html`: 真实 Demo 审核队列入口。
- `frontend/ppt-review.html`: PPT 页级审核入口。
- `frontend/grading-report.html`: 真实 Demo 评分 evidence 解释页。
- `frontend/console.html`: 本地 Mock 控制台入口。
- `frontend/delivery.html`: 本地交付验收页面。
- `scripts/phase1-demo.runbook.md`: 人工演示验收步骤。
- `config/delivery-package.contract.json`: 交付包契约。

## 输出说明

索引本身不生成真实平台内容。推荐输出由 CLI 生成：

```text
examples/output/phase1-delivery-package.json
examples/output/phase1-acceptance-report.md
```

这些输出是本地可再生成文件，不进入源码跟踪。

## 命令示例

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\access.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
start .\frontend\real-demo.html
start .\frontend\review-center.html
start .\frontend\ppt-review.html
start .\frontend\grading-report.html
start .\frontend\console.html
start .\frontend\delivery.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_faq.py
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_real_demo_script.py
python -m pytest tests/test_real_demo_quick_commands.py
python -m pytest tests/test_real_demo_agent_workflow.py
python -m pytest tests/test_real_demo_agent_runner.py
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_final_signoff.py
```

## 测试方式

```powershell
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_delivery_faq.py
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_real_demo_script.py
python -m pytest tests/test_real_demo_quick_commands.py
python -m pytest tests/test_real_demo_agent_workflow.py
python -m pytest tests/test_real_demo_agent_runner.py
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_final_signoff.py
```

## 限制说明

- 不接入真实大模型。
- 真实 Demo 脚本只复放已有真实 LLM 产物，不发送新的真实 LLM 请求。
- 不启动真实智能体。
- 不启动真实 HTTP 服务，不绑定公网 IP、内网 IP 或真实端口监听。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不执行未知 Shell 脚本。
- 不自动发布或真实发布生成内容。
- 不上传交付包，不输出密钥，不展示选手端应隐藏的标准答案。
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
