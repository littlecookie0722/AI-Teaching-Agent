# Phase 1 Handoff Checklist

本清单用于 Phase 1 本地 Mock 交付交接。交接只确认本地文档、静态页面、白名单命令和可再生成验收证据，不接入真实大模型，不创建真实云资源，不启动真实智能体，不执行未知 Shell，不执行选手代码，不自动发布或真实发布。

## 输入说明

- `README.md`: 项目当前能力和快速验证入口。
- `delivery/README.md`: 交付入口、输入输出、命令、测试和限制说明。
- `delivery/FAQ.md`: 常见失败场景和安全恢复步骤。
- `delivery/DEMO_SCRIPT_CHECKLIST.md`: 运营演示脚本检查清单。
- `delivery/OPERATIONS_MANUAL.md`: Phase 5 运营手册。
- `skills/operations-skill-pack/SKILL.md`: Phase 5 运营 Skill 包。
- `delivery/STANDALONE_AGENT_DELIVERY.md`: Phase 5 独立智能体 Mock 交付说明。
- `delivery/ACCESS_ENTRYPOINTS.md`: Phase 5 IP + 端口访问入口 Mock 交付说明。
- `delivery/PHASE5_MOCK_BASELINE.md`: Phase 5 Mock 基线冻结说明。
- `delivery/HIGH_RISK_MCP_HANDOFF.md`: 高风险 MCP Tool 运营交接清单。
- `delivery/FINAL_SIGNOFF.md`: Phase 5 最终运营签收包。
- `frontend/operations-presenter.html`: 运营讲解台静态页面。
- `frontend/access.html`: IP + 端口访问入口静态页面。
- `frontend/operations-signoff.html`: 运营签收总览静态页面。
- `frontend/operations-demo-script.html`: 运营演示脚本静态页面。
- `scripts/phase1-demo.runbook.md`: 本地人工演示验收步骤。
- `delivery/phase1-delivery-index.json`: 交付入口索引契约。
- `scripts/manifest.json`: 本地验证命令白名单。

## 输出说明

交接材料本身不生成真实平台内容。验收证据由白名单命令生成：

```text
examples/output/phase1-delivery-package.json
examples/output/phase1-acceptance-report.md
```

这些输出是本地可再生成文件，清理后可重新导出。

## 命令示例

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\access.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
start .\frontend\console.html
start .\frontend\delivery.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_enablement.py
python -m pytest tests/test_final_signoff.py
```

## 交接检查

1. 阅读 `README.md`，确认 Phase 1 当前能力、CLI 入口和限制说明。
2. 阅读 `delivery/README.md`，确认交付入口、生成输出和测试方式。
3. 阅读 `delivery/FAQ.md`，确认失败时只使用白名单命令恢复。
4. 阅读 `delivery/DEMO_SCRIPT_CHECKLIST.md`，确认运营演示顺序从 Launchpad 开始。
5. 阅读 `scripts/phase1-demo.runbook.md`，确认演示步骤是人工触发，不是自动执行脚本。
6. 阅读 `delivery/HIGH_RISK_MCP_HANDOFF.md`，确认高风险 MCP Tool 仍只创建审核意图或只读查询。
7. 阅读 `delivery/OPERATIONS_MANUAL.md`，确认运营流程只依赖本地页面、白名单命令和人工审核。
8. 阅读 `skills/operations-skill-pack/SKILL.md`，确认运营复用 Skill 包只组合现有 Mock 能力。
9. 阅读 `delivery/STANDALONE_AGENT_DELIVERY.md`，确认独立智能体交付仍只描述本地 Mock 编排。
10. 阅读 `delivery/ACCESS_ENTRYPOINTS.md`，确认 IP + 端口访问入口仍是本地静态说明。
11. 阅读 `delivery/PHASE5_MOCK_BASELINE.md`，确认真实 LLM PoC 前的 Mock 基线冻结和准入门禁。
12. 阅读 `delivery/FINAL_SIGNOFF.md`，确认最终签收顺序只依赖本地文件和白名单命令。
13. 打开 `frontend/operations-launchpad.html`，确认运营入口卡片、验证命令和 `MOCK_ONLY` 安全摘要展示一致。
14. 打开 `frontend/access.html`，确认本地静态入口、禁用端口占位和 `Ports Listening=0` 展示一致。
15. 打开 `frontend/operations-presenter.html`，确认 12 条 speakerCue、验收信号、175/175 交付状态和禁用动作展示一致。
16. 打开 `frontend/operations-signoff.html`，确认 6/6 门禁、175/175 交付、20/20 自检、14/14 验收和 6/6 安全断言展示一致。
17. 打开 `frontend/operations-demo-script.html`，确认 12 步演示顺序、验收信号和禁止动作展示一致。
18. 打开 `frontend/console.html`，确认统一 Mock 控制台展示 `MOCK_ONLY` 和安全禁用状态。
19. 打开 `frontend/delivery.html`，确认交付清单、验收摘要、Phase 1 Check 和安全断言展示一致。
20. 运行 `python lab_cli.py phase1 check`，确认 `success=true` 且 `data.passed=true`。
21. 运行 `phase1 export`，确认 `deliveryManifest.summary.missingRequired=0`。
22. 运行 `phase1 report`，确认 `acceptancePassed=true` 且 `safetyAssertionsPassed=true`。
23. 运行 `python -m pytest tests/test_delivery_handoff.py`，确认 handoff 契约可测试。
24. 运行 `python -m pytest tests/test_demo_script_checklist.py`，确认演示脚本检查清单可测试。
25. 运行 `python -m pytest tests/test_high_risk_mcp_handoff.py`，确认高风险 MCP 交接清单可测试。
26. 运行 `python -m pytest tests/test_operations_manual.py`，确认运营手册可测试。
27. 运行 `python -m pytest tests/test_operations_skill_pack.py`，确认运营 Skill 包可测试。
28. 运行 `python -m pytest tests/test_standalone_agent_delivery.py`，确认独立智能体交付包可测试。
29. 运行 `python -m pytest tests/test_access_entrypoints.py`，确认 IP + 端口访问入口交付包可测试。
30. 运行 `python -m pytest tests/test_phase5_mock_baseline.py`，确认 Mock 基线冻结可测试。
31. 运行 `python -m pytest tests/test_real_sdk_enablement.py`，确认真实 SDK 开关设计门禁可测试。
32. 运行 `python -m pytest tests/test_real_sdk_minimal_impl.py` 和 `python -m pytest tests/test_real_sdk_dependency_env_gate.py`，确认真实 SDK 最小实现外壳默认禁用，dependency/env gate 只做设计评审且可测试。
33. 运行 `python -m pytest tests/test_final_signoff.py`，确认最终签收包可测试。
34. 确认生成内容仍默认 `WAITING_REVIEW`，审核通过前不得 publish。
35. 确认真实 LLM、真实云资源、真实沙箱、真实 HTTP 服务、真实端口监听、未知 Shell、选手代码执行、自动发布和真实发布均保持禁用。

## 测试方式

```powershell
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_enablement.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_final_signoff.py
python -m pytest
```

## 限制说明

- 不接入真实大模型。
- 不启动真实智能体。
- 不启动真实 HTTP 服务，不绑定公网 IP、内网 IP 或真实端口监听。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不执行未知 Shell 脚本。
- 不自动发布或真实发布生成内容。
- 不上传交付包，不输出密钥，不展示选手端应隐藏的标准答案。
