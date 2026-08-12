# Phase 5 Final Signoff Package

本签收包用于 Phase 5 本地 Mock 交付收口。它把 Phase 1 到 Phase 5 形成的本地文档、静态页面、交付包、验收报告、Runbook、高风险 MCP 交接和测试命令汇总为一套人工签收顺序。

签收动作只确认本地文件和白名单命令输出，不接入真实大模型，不启动真实智能体，不启动真实 MCP Server，不创建或删除真实云资源，不执行未知 Shell，不执行选手代码，不自动发布或真实发布。

## 输入说明

- `README.md`: 项目能力、阶段边界和快速验证入口。
- `delivery/README.md`: 交付入口索引、输入输出、命令、测试和限制说明。
- `delivery/HANDOFF.md`: Phase 1 运营交接检查清单。
- `delivery/OPERATIONS_MANUAL.md`: Phase 5 运营手册。
- `skills/operations-skill-pack/SKILL.md`: Phase 5 运营 Skill 包。
- `delivery/STANDALONE_AGENT_DELIVERY.md`: Phase 5 独立智能体 Mock 交付说明。
- `delivery/ACCESS_ENTRYPOINTS.md`: Phase 5 IP + 端口访问入口 Mock 交付说明。
- `delivery/PHASE5_MOCK_BASELINE.md`: Phase 5 Mock 基线冻结说明，作为真实 LLM PoC 前的收口门禁。
- `delivery/HIGH_RISK_MCP_HANDOFF.md`: 高风险 MCP Tool 运营交接清单。
- `delivery/phase1-delivery-index.json`: 交付入口索引机器契约。
- `delivery/final-signoff.json`: 最终签收包机器契约。
- `config/delivery-package.contract.json`: 交付包导出契约。
- `scripts/manifest.json`: 本地验证命令白名单。
- `scripts/phase1-demo.runbook.md`: 人工演示验收 Runbook。
- `frontend/operations-launchpad.html`: 运营入口静态页面。
- `frontend/access.html`: IP + 端口访问入口静态页面。
- `frontend/operations-signoff.html`: 运营签收总览静态页面。
- `frontend/delivery.html`: 交付验收静态页面。

## 输出说明

签收包本身不生成真实平台内容。签收证据由白名单命令本地生成：

```text
examples/output/phase1-delivery-package.json
examples/output/phase1-acceptance-report.md
```

这些输出是本地可再生成文件，不代表真实发布结果，也不上传到远端系统。

## 命令示例

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\access.html
start .\frontend\operations-signoff.html
start .\frontend\delivery.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest
```

## 签收顺序

1. 阅读 `README.md`、`delivery/README.md` 和 `docs/10_OPERATIONS_GUIDE.md`，确认当前交付仍是本地 Mock。
2. 阅读 `delivery/HANDOFF.md`，确认交接检查顺序、生成输出和禁用动作。
3. 阅读 `delivery/OPERATIONS_MANUAL.md`，确认运营流程只依赖本地页面、白名单命令和人工审核。
4. 阅读 `skills/operations-skill-pack/SKILL.md`，确认运营复用 Skill 包不启动真实 Agent 或 Provider。
5. 阅读 `delivery/STANDALONE_AGENT_DELIVERY.md`，确认独立智能体交付不连接真实平台、不启动真实 Agent。
6. 阅读 `delivery/ACCESS_ENTRYPOINTS.md`，确认 IP + 端口访问入口只是静态说明，不授权真实服务监听或外网访问。
7. 阅读 `delivery/PHASE5_MOCK_BASELINE.md`，确认当前 Mock 交付基线冻结为 175/175，真实 LLM PoC 必须显式 opt-in 且默认 Provider 仍为 `mock`。
8. 阅读 `delivery/HIGH_RISK_MCP_HANDOFF.md`，确认高风险 MCP Tool 只创建审核意图或只读查询。
9. 打开 `frontend/operations-launchpad.html`，确认入口、白名单命令和安全摘要可见。
10. 打开 `frontend/access.html`，确认 `Ports Listening=0`，本地端口均为禁用占位。
11. 打开 `frontend/operations-signoff.html`，确认 6/6 门禁、175/175 交付、20/20 自检、14/14 验收和 6/6 安全断言。
12. 打开 `frontend/delivery.html`，确认运营手册、运营 Skill 包、独立智能体交付、访问入口交付、Mock 基线冻结、最终签收文档和契约已进入交付清单。
13. 运行 `python lab_cli.py phase1 check`，确认 `success=true` 且 `data.passed=true`。
14. 运行 `phase1 export`，确认 `deliveryManifest.summary.missingRequired=0`。
15. 运行 `phase1 report`，确认 `acceptancePassed=true` 且 `safetyAssertionsPassed=true`。
16. 运行 `python -m pytest tests/test_operations_skill_pack.py`、`python -m pytest tests/test_standalone_agent_delivery.py`、`python -m pytest tests/test_access_entrypoints.py`、`python -m pytest tests/test_phase5_mock_baseline.py`、`python -m pytest tests/test_real_sdk_minimal_impl.py`、`python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py`、`python -m pytest tests/test_operations_manual.py`、`python -m pytest tests/test_final_signoff.py` 和 `python -m pytest`，确认运营 Skill 包、独立智能体交付、访问入口交付、Mock 基线冻结、真实 SDK 最小实现外壳、dependency/env gate 与 dependency install plan、运营手册、签收契约和全量测试通过。
17. 确认所有 AI 生成内容仍默认 `WAITING_REVIEW`，审核前不得 publish。
18. 确认真实 LLM、真实云资源、真实沙箱、真实 MCP Server、真实智能体、真实 HTTP 服务、未知 Shell、选手代码执行、自动发布和真实发布均保持禁用。

## 测试方式

```powershell
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_frontend_manifest.py
python -m pytest
```

## 限制说明

- 不接入真实大模型。
- 不启动真实智能体或真实 MCP Server。
- 不启动真实 HTTP 服务，不绑定公网 IP、内网 IP 或真实端口监听。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不执行未知 Shell 脚本。
- 不自动发布或真实发布生成内容。
- 不上传交付包，不输出密钥，不展示选手端应隐藏的标准答案。
