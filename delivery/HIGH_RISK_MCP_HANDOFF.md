# High-Risk MCP Handoff

本清单用于运营和审核人员交接 Phase 4 高风险 MCP Mock 工具。它只确认安全矩阵、审核意图、二次确认只读状态和前端可视化证据，不启动真实 MCP Server，不启动真实智能体，不执行真实发布或真实环境销毁。

## 输入说明

- `mcp-server/high-risk-tool-safety.contract.json`: 高风险 MCP Tool 安全矩阵契约。
- `mcp-server/tools.manifest.json`: MCP Tool manifest，声明 `publish_lab`、`publish_exam`、`destroy_environment` 和 `get_second_confirmation_status`。
- `frontend/review-center.html`: 审核中心静态页，展示高风险 MCP 意图和二次确认只读状态。
- `frontend/audit.html`: 审计可观测静态页，展示 MCP Tool 调用记录和安全标记。
- `docs/07_MCP_SPEC.md`: MCP 规范和安全要求。
- `docs/10_OPERATIONS_GUIDE.md`: 运营手册中的 MCP Mock 检查与交接说明。

## 输出说明

本清单不生成真实平台内容。交接输出只是本地人工确认结果：

```text
确认高风险 MCP 工具仍为 MOCK_ONLY
确认 publish_lab / publish_exam / destroy_environment 只创建审核意图
确认 get_second_confirmation_status 只读查询二次确认状态
确认真实发布、真实销毁、二次确认通过动作和绕过审核全部禁用
```

## 命令示例

```powershell
python -m pytest tests/test_high_risk_mcp_safety_contract.py
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_mcp_manifest.py
python -m pytest tests/test_mcp_mock_tools.py
python -m pytest tests/test_frontend_manifest.py
```

## 交接检查

1. 阅读 `mcp-server/high-risk-tool-safety.contract.json`，确认 scope 覆盖 `publish_lab`、`publish_exam`、`destroy_environment` 和 `get_second_confirmation_status`。
2. 确认 `publish_lab` 和 `publish_exam` 的 `reviewIntentOnly=true`、`realPublish=false`、`autoPublishAllowed=false`。
3. 确认 `destroy_environment` 的 `requiresSecondConfirmation=true`、`realCloudResourceChanged=false`、`environmentDestroyed=false`。
4. 确认 `get_second_confirmation_status` 的 `readOnly=true`、`confirmationActionAvailable=false`、`confirmationEndpointEnabled=false`、`destroyRealEnvironmentEnabled=false`。
5. 打开 `frontend/review-center.html`，确认只展示高风险意图和只读二次确认状态，不出现真实执行按钮。
6. 打开 `frontend/audit.html`，确认 `mcpToolCallRecords` 只展示 Mock 调用记录，不重试真实 MCP 调用。
7. 运行白名单测试命令，确认安全矩阵、MCP manifest、前端 Mock 和本交接清单一致。
8. 如需进入真实 MCP Server、真实 Agent、真实发布或真实销毁设计，必须另开明确任务并重新评审安全边界。

## 测试方式

```powershell
python -m pytest tests/test_high_risk_mcp_handoff.py
python -m pytest tests/test_high_risk_mcp_safety_contract.py
python -m pytest tests/test_scripts_manifest.py
python -m pytest
```

## 限制说明

- 不启动真实 MCP Server。
- 不启动真实智能体。
- 不调用真实大模型。
- 不创建、变更或删除真实云资源。
- 不执行真实发布。
- 不确认真实二次因子。
- 不销毁真实环境。
- 不绕过人工审核。
