# Phase 2 Readiness Gate

本门禁用于判断 Phase 1 本地 Mock 交付是否具备进入 Phase 2 规划和 Mock Workflow 设计的条件。当前模式固定为 `MOCK_ONLY`。通过门禁不代表可以接入真实大模型、真实云资源、真实智能体、真实沙箱或真实发布；这些能力仍需单独任务、人工确认和安全设计。

## 输入说明

- `config/delivery-package.contract.json`: Phase 1 交付包契约。
- `delivery/phase1-delivery-index.json`: 运营交付入口索引。
- `delivery/phase1-handoff.json`: 运营交接清单契约。
- `delivery/phase1-faq.json`: FAQ 与故障排查契约。
- `scripts/manifest.json`: 本地验证命令白名单。

## 输出说明

门禁本身不生成真实平台内容。需要验收证据时，仍由白名单 CLI 生成：

```text
examples/output/phase1-delivery-package.json
examples/output/phase1-acceptance-report.md
```

这些输出是本地可再生成文件，不上传、不发布、不作为真实平台实体。

## 命令示例

```powershell
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
```

## 准入条件

1. `phase1 check` 返回 `success=true` 且 `data.passed=true`。
2. 交付包 `deliveryManifest.summary.missingRequired=0`。
3. 交付包 `acceptanceSummary.passed=true`。
4. 交付包 `acceptanceSummary.safetyAssertionsPassed=true`。
5. Workflow 报告 `reviewRequired=true`。
6. Workflow 报告 `publishBlockedUntilApproved=true`。
7. `delivery/phase1-handoff.json` 和 `delivery/phase1-faq.json` 存在且可测试。
8. `tests/test_phase2_readiness_gate.py` 通过。

## 允许下一步

- 设计 Phase 2 Provider 接入方案，但仍先保持 MockProvider 优先。
- 阅读 `providers/PHASE2_PROVIDER_PLAN.md`，只按规划推进 `LLMProvider` 接口和 MockProvider-first 契约。
- 通过 `providers/adapter.py` 统一 Mock Provider 调用边界，但不得启用真实 Provider。
- 细化 Prompt / Workflow 设计，并继续要求输出经过 DSL Schema 校验。
- 扩展 Mock Workflow 测试，再考虑真实集成。

## 阻断项

- 不允许直接启用真实 LLM Provider。
- 不允许创建真实 VM / Notebook 或云资源。
- 不允许执行真实沙箱或选手代码。
- 不允许自动发布 AI 生成内容。
- 不允许启动真实自主智能体。

## 测试方式

```powershell
python -m pytest tests/test_phase2_readiness_gate.py
python -m pytest tests/test_phase2_provider_plan.py
python -m pytest tests/test_provider_adapter.py
python -m pytest tests/test_provider_adapter_workflow.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_scripts_manifest.py
python -m pytest
```

## 限制说明

- 不接入真实大模型。
- 不启动真实智能体。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱或选手代码。
- 不执行未知 Shell 脚本。
- 不自动发布或真实发布生成内容。
- 不上传交付包，不输出密钥，不展示选手端应隐藏的标准答案。
