# scripts

Phase 1 本地脚本安全契约目录。当前只维护允许命令白名单和禁止模式，不提供会操作生产、云资源或执行未知 Shell 的脚本。

`security_scan.py` is the public-release check. It is read-only and only
reports sanitized rule/path/line information. It checks tracked text files,
the checked-out commit identity, Notebook text, PPTX core properties, PNG text
chunks, and JPEG EXIF metadata.

`ppt artifact build` now uses the packaged Python builder in
`cli/pptx_artifact.py` with `python-pptx` and Pillow. It accepts a validated
`WAITING_REVIEW` PPT DSL and writes the PPTX, manifest, per-slide PNG previews,
and contact sheet to caller-selected paths. The CLI adds a deterministic
advisory quality report to the manifest and Artifact metadata, including title,
density, long-text, and renderer-truncation signals. The legacy
`build_pptx_from_ppt_dsl.mjs` entry remains packaged for direct-call
compatibility, but the CLI no longer requires Node.js or an external
presentations runtime. Neither path publishes the generated artifact.

## 输入说明

- `manifest.json`: 本地验证命令、演示 Runbook 引用和脚本安全限制。
- `phase1-demo.runbook.json`: Phase 1 本地演示验收 Runbook 契约，只引用白名单命令。
- `phase1-demo.runbook.md`: Phase 1 本地演示验收 Runbook 说明，供人工按步骤复现。
- `delivery/HIGH_RISK_MCP_HANDOFF.md`: 高风险 MCP Tool 运营交接清单。
- `delivery/high-risk-mcp-handoff.json`: 高风险 MCP Tool 运营交接机器契约。
- `delivery/FINAL_SIGNOFF.md`: Phase 5 最终运营签收包。
- `delivery/final-signoff.json`: Phase 5 最终运营签收包机器契约。
- `delivery/OPERATIONS_MANUAL.md`: Phase 5 运营手册。
- `delivery/operations-manual.json`: Phase 5 运营手册机器契约。
- `skills/operations-skill-pack/SKILL.md`: Phase 5 运营 Skill 包。
- `skills/operations-skill-pack.contract.json`: Phase 5 运营 Skill 包机器契约。
- `delivery/STANDALONE_AGENT_DELIVERY.md`: Phase 5 独立智能体 Mock 交付说明。
- `delivery/standalone-agent-delivery.json`: Phase 5 独立智能体 Mock 交付机器契约。
- `delivery/DEMO_SCRIPT_CHECKLIST.md`: Phase 1 运营演示脚本检查清单。
- `delivery/phase1-demo-script-checklist.json`: Phase 1 运营演示脚本检查清单机器契约。
- `frontend/operations-launchpad.html`: 本地运营 Launchpad，Runbook 推荐首个打开。
- `frontend/operations-presenter.html`: 本地运营讲解台，Runbook 人工预览目标。
- `frontend/operations-signoff.html`: 本地运营签收总览，Runbook 人工预览目标。
- `frontend/operations-demo-script.html`: 本地运营演示脚本页面，Runbook 人工预览目标。
- 允许命令必须是本地 Phase 1 验证、Mock 导出或测试命令。

## 输出说明

允许命令统一用于本地验证：

```text
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-grading-report.json
python lab_cli.py grade sandbox-image verify --output examples/output/grading-sandbox-image-verify.json
python -m pytest tests/test_sandbox_mock_executor.py
python -m pytest tests/test_frontend_manifest.py
python -m pytest
```

本地 Python 依赖见根目录 `requirements.txt`。

如果命令会写入工作区，写入范围必须限制在 `examples/output/`。

## 命令示例

```powershell
start .\frontend\operations-launchpad.html
start .\frontend\operations-presenter.html
start .\frontend\operations-signoff.html
start .\frontend\operations-demo-script.html
start .\frontend\console.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_scripts_manifest.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_standalone_agent_delivery.py
python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-grading-report.json
python lab_cli.py grade sandbox-image verify --output examples/output/grading-sandbox-image-verify.json
python -m pytest tests/test_sandbox_mock_executor.py
python -m pytest tests/test_frontend_manifest.py
```

`start .\frontend\operations-launchpad.html`、`start .\frontend\operations-presenter.html`、`start .\frontend\operations-signoff.html`、`start .\frontend\operations-demo-script.html` 和 `start .\frontend\console.html` 只作为人工本地预览动作，不作为自动化白名单命令。Runbook 中所有验证命令必须能在 `manifest.json` 的 `allowedCommands` 中找到对应 `id`。

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- 不执行未知 Shell 脚本。
- 不允许破坏性命令。
- 不访问生产数据库。
- 不调用云厂商命令。
- 不创建或删除真实资源。
- 不执行选手代码。
- 不输出密钥。
- 不把标准答案展示给选手端。
- 交付包契约测试属于本地验证命令，不调用真实 Provider。
- Provider 测试只校验 Mock 契约和本地 DSL 引用，不访问网络。
- Phase 3 Mock 评分器命令只输出计划化报告，不执行 Grading DSL 中的命令，不运行 pytest，不执行选手代码。
- `grade sandbox-image verify` 只通过 CLI 验证固定本地评分镜像是否存在并包含 pytest；不开放任意 Docker 命令、不读取密钥、不上传镜像。
