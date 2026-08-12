# Phase 1 Demo Script Checklist

本清单用于运营人员按固定顺序演示 Phase 1 本地 Mock 交付效果，模式固定为 `MOCK_ONLY`。它不是自动化脚本，不接入真实大模型、真实云资源或真实智能体，不执行未知 Shell，不执行选手代码，不上传交付包，不自动发布或真实发布。

## 输入说明

- `AGENTS.md`: 项目级 Phase 1 规则和安全红线。
- `docs/AI_PLATFORM_CODEX_FULL_GUIDE.md`: DSL -> CLI -> Mock -> Workflow -> Operation 的开发顺序。
- `frontend/operations-launchpad.html`: 演示首屏入口。
- `frontend/operations-demo-map.html`: 按角色和顺序展示页面路径。
- `frontend/operations-presenter.html`: 一页式讲解台，展示 speakerCue、验收信号、175/175 交付状态和禁用动作。
- `frontend/operations-signoff.html`: 一屏式签收总览，展示 6/6 门禁、175/175 交付、20/20 自检、14/14 验收和 6/6 安全断言。
- `frontend/operations-demo-script.html`: 本清单的静态页面版，展示 12 步顺序、验收信号和禁止动作。
- `scripts/phase1-demo.runbook.md`: 本地演示验收步骤。
- `config/delivery-package.contract.json`: 交付包和验收清单契约。
- `mcp-server/tools.manifest.json`: MCP Tool 契约，包含 `get_review_task_summary.outputContract`。
- `delivery/HANDOFF.md`: 运营交接检查清单。
- `delivery/FAQ.md`: 常见失败和安全恢复说明。

## 输出说明

本清单不生成真实平台内容。演示证据由白名单命令在本地生成：

```text
examples/output/phase1-delivery-package.json
examples/output/phase1-acceptance-report.md
```

这些输出是可再生成文件，演示结束后可以清理。

## 命令示例

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\operations-demo-map.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
start .\frontend\operations-runbook.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py
python -m pytest tests/test_cli.py
start .\frontend\operations-acceptance.html
start .\frontend\delivery.html
start .\frontend\audit-incidents.html
python -m pytest tests/test_demo_script_checklist.py
```

`start .\frontend\*.html` 只作为人工本地预览动作，不作为自动化白名单命令。验证命令必须来自 `scripts/manifest.json`。

## 演示顺序

如需先看一页式口径，可打开 `frontend/operations-presenter.html` 作为人工讲解台；如需签收总览，可打开 `frontend/operations-signoff.html`；正式 Demo Script 仍保持以下 14 步。

1. 阅读 `AGENTS.md`，先说明当前只做 Phase 1 Mock，遵循 DSL -> CLI -> Mock -> Workflow -> Operation。
2. 打开 `frontend/operations-launchpad.html`，说明它是运营首屏入口。
3. 打开 `frontend/operations-demo-map.html`，说明不同角色如何按顺序查看页面。
4. 打开 `frontend/operations-runbook.html`，说明 Runbook、白名单命令和安全红线。
5. 运行 `python lab_cli.py phase1 check`，确认 `success=true` 且 `data.passed=true`。
6. 运行 `phase1 export`，确认 `deliveryManifest.summary.missingRequired=0`。
7. 运行 `phase1 report`，确认 `acceptancePassed=true` 且 `safetyAssertionsPassed=true`。
8. 打开 `frontend/operations-acceptance.html`，说明验收项、关联页面和安全命令。
9. 打开 `frontend/delivery.html`，说明交付清单、验收摘要和安全断言。
10. 打开 `frontend/audit-incidents.html`，说明失败记录只能按 FAQ 和 Runbook 安全恢复。
11. 运行 `python -m pytest tests/test_cli.py`，说明 `review batch-summary` 返回 `reviewPriorityQueue`，包含 `priority`、`reasonCode`、`recommendedAction`，并保持 `autoApproveAllowed=false`、`batchStateChangeAllowed=false`。
12. 运行 `python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py`，说明 `GET /api/review-task-summary` 和 MCP `get_review_task_summary` 读取同源审核优先队列，只服务人工分拣。
13. 指出 Lab / Exam / Grading / PPT 生成内容默认 `WAITING_REVIEW`，审核前不得发布。
14. 收尾确认真实 LLM、真实 Agent、真实云资源、真实沙箱、未知 Shell、选手代码执行、远程上传、自动发布、真实发布和密钥展示全部禁用。

## 测试方式

```powershell
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_backend_mock_api.py tests/test_cli.py tests/test_mcp_mock_tools.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_frontend_manifest.py
python -m pytest
```

## 限制说明

- 不接入真实大模型。
- 不启动真实智能体。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不执行未知 Shell 脚本。
- 不上传交付包。
- 不自动发布或真实发布生成内容。
- 不输出密钥，不展示选手端应隐藏的标准答案。
