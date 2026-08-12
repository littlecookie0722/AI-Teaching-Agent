# Phase 5 Operations Manual

本手册面向运营和教学支撑人员，用于在本地 Mock 环境中复现 AI 实训平台的内容生成、审核、验收和交付流程。当前手册只描述人工操作顺序、静态页面入口、白名单 CLI 命令和安全边界，不授权真实发布或真实资源操作。

## 输入说明

- `frontend/operations-launchpad.html`: 运营入口页，优先从这里进入演示与验收。
- `frontend/access.html`: IP + 端口访问入口说明页，展示本地静态入口和禁用端口占位。
- `frontend/operations-signoff.html`: 运营签收总览页，查看门禁、交付、验收和安全状态。
- `frontend/delivery.html`: 交付验收页，查看交付项、验收摘要和安全断言。
- `delivery/HANDOFF.md`: 运营交接检查清单。
- `delivery/FINAL_SIGNOFF.md`: 最终签收包。
- `delivery/HIGH_RISK_MCP_HANDOFF.md`: 高风险 MCP Tool 交接清单。
- `scripts/phase1-demo.runbook.md`: 本地演示验收 Runbook。
- `scripts/manifest.json`: 白名单命令和安全限制。
- `skills/operations-skill-pack/SKILL.md`: Phase 5 运营 Skill 包。
- `skills/operations-skill-pack.contract.json`: Phase 5 运营 Skill 包机器契约。
- `delivery/STANDALONE_AGENT_DELIVERY.md`: Phase 5 独立智能体 Mock 交付说明。
- `delivery/standalone-agent-delivery.json`: Phase 5 独立智能体 Mock 交付机器契约。
- `delivery/ACCESS_ENTRYPOINTS.md`: Phase 5 IP + 端口访问入口 Mock 交付说明。
- `delivery/access-entrypoints.json`: Phase 5 IP + 端口访问入口 Mock 交付机器契约。
- `delivery/PHASE5_MOCK_BASELINE.md`: Phase 5 Mock 基线冻结说明，用于真实 LLM PoC 前的准入确认。
- `delivery/phase5-mock-baseline.json`: Phase 5 Mock 基线冻结机器契约。
- `config/delivery-package.contract.json`: 交付包导出契约。
- `examples/input/demo-source.md`: 本地演示素材。

## 输出说明

运营验收只生成本地证据：

```text
examples/output/phase1-delivery-package.json
examples/output/phase1-acceptance-report.md
examples/output/phase2-content-generation-report.json
examples/output/phase2-exam-conversion-report.json
examples/output/phase2-ppt-generation-report.json
```

这些输出用于人工审核、演示和交接，不代表真实平台发布结果，不上传远端，不写入生产数据库。

## 运营流程

1. 打开 `frontend/operations-launchpad.html`，确认入口卡片、验证命令和 `MOCK_ONLY` 安全摘要。
2. 运行 `python lab_cli.py phase1 check`，确认 Phase 1 自检 `success=true` 且 `data.passed=true`。
3. 运行 `phase1 export` 和 `phase1 report`，生成本地交付包和验收报告。
4. 打开 `frontend/operations-signoff.html`，确认 6/6 门禁、175/175 交付、20/20 自检、14/14 验收和 6/6 安全断言。
5. 打开 `frontend/delivery.html`，确认运营手册、运营 Skill 包、最终签收、高风险 MCP 交接和测试套件均为 `READY`。
6. 阅读 `skills/operations-skill-pack/SKILL.md`，确认 Lab / Exam / Grading / PPT 四类 Skill 的组合顺序和禁用动作。
7. 阅读 `delivery/STANDALONE_AGENT_DELIVERY.md`，确认独立智能体交付仍是 Mock 文档和契约，不连接真实平台。
8. 打开 `frontend/access.html`，确认 IP + 端口访问入口只是本地静态说明，`127.0.0.1:3000`、`127.0.0.1:8000` 和 `127.0.0.1:8080` 均为禁用占位。
9. 阅读 `delivery/PHASE5_MOCK_BASELINE.md`，确认真实 LLM PoC 前必须保持默认 Provider 为 `mock`，且只允许显式 opt-in 的 Lab DSL 单链路。
10. 按 `scripts/phase1-demo.runbook.md` 演示主链路，所有命令必须来自 `scripts/manifest.json`。
11. 生成 Lab / Exam / Grading / PPT DSL 后，只能进入 `WAITING_REVIEW`，审核通过前不得 publish。
12. 处理高风险 MCP Tool 时，只能创建审核意图或查看只读状态，不得解释为真实发布、真实销毁或二次确认执行。
13. 交接前阅读 `delivery/HANDOFF.md` 和 `delivery/FINAL_SIGNOFF.md`，确认交接和签收顺序。
14. 最后运行 `python -m pytest tests/test_operations_skill_pack.py`、`python -m pytest tests/test_standalone_agent_delivery.py`、`python -m pytest tests/test_access_entrypoints.py`、`python -m pytest tests/test_phase5_mock_baseline.py`、`python -m pytest tests/test_operations_manual.py` 和 `python -m pytest`。

## 命令示例

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\access.html
start .\frontend\operations-signoff.html
start .\frontend\delivery.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json
python lab_cli.py phase2 exam-convert run --lab templates/lab/examples/basic-lab.yaml --notebook examples/notebooks/demo-lab.ipynb --reviewer teacher_1 --output examples/output/phase2-exam-conversion-report.json
python lab_cli.py phase2 ppt-generate run --input examples/input/demo-source.md --reviewer teacher_1 --slide-plan-output examples/output/phase2-ppt-slide-plan.json --output examples/output/phase2-ppt-generation-report.json
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_enablement.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
python -m pytest tests/test_operations_manual.py
python -m pytest
```

## 测试方式

```powershell
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_delivery_handoff.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_scripts_manifest.py
python -m pytest
```

## 限制说明

- 不接入真实大模型或真实 Provider。
- 不启动真实智能体或真实 MCP Server。
- 不启动真实 HTTP 服务，不绑定公网 IP、内网 IP 或真实端口监听。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不执行未知 Shell 脚本。
- 不自动发布或真实发布生成内容。
- 不上传交付包，不输出密钥，不展示选手端应隐藏的标准答案。
