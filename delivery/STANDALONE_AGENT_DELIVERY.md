# Phase 5 Standalone Agent Delivery

本交付说明用于描述独立智能体的 Mock 交付边界。当前只交付本地文档、机器契约、白名单命令和验收规则，不创建真实智能体，不连接外部平台，不调用真实大模型，不启动真实 MCP Server，不发布真实内容。

## 输入说明

- `mcp-server/tools.manifest.json`: 本地 MCP Mock Tool 能力清单。
- `ai-workflows/workflow.manifest.json`: 本地 Mock Workflow 能力清单。
- `ai-workflows/phase2-workflow-registry.contract.json`: Phase 2 Mock Workflow 只读能力目录。
- `skills/operations-skill-pack/SKILL.md`: 运营复用 Skill 包。
- `delivery/OPERATIONS_MANUAL.md`: 运营手册。
- `delivery/FINAL_SIGNOFF.md`: 最终运营签收包。
- `delivery/HIGH_RISK_MCP_HANDOFF.md`: 高风险 MCP Tool 运营交接清单。
- `scripts/manifest.json`: 本地验证命令白名单。
- `config/delivery-package.contract.json`: 交付包契约。

## 输出说明

- `delivery/STANDALONE_AGENT_DELIVERY.md`: 独立智能体 Mock 交付说明。
- `delivery/standalone-agent-delivery.json`: 独立智能体 Mock 交付机器契约。

这些输出只作为独立智能体的本地 Mock 交付材料和验收基线，不包含外部平台凭证、真实 Agent 配置或外部平台 URL。

## Mock 智能体规格

目标：把本地操作者的自然语言请求约束为本地 Mock Tool / Mock Workflow / Skill 包的可审核执行计划。

触发方：本地操作者。当前阶段只提供文档、机器契约和本地验证，不接入外部平台。

输入：用户意图、素材路径、目标产物类型、审核人标识和可选任务 ID。所有文件必须是本地路径，不能是远程 URL。

输出：统一 JSON，包括 `success`、`code`、`message`、`data`、`traceId`。生成内容默认进入 `WAITING_REVIEW`。

允许工具：只允许引用 `mcp-server/tools.manifest.json` 中的低/中风险 Mock Tool 和只读查询工具，例如素材分析、Workflow 查询、AI Task 查询、Review Detail 查询和本地审计查询。

禁止工具：独立智能体不得直接调用 `publish_lab`、`publish_exam`、`destroy_environment`。这些高风险工具只能通过高风险 MCP 交接清单表达人工审核意图，不能被解释为真实执行授权。

状态：请求状态、持久化状态和审计状态必须写入本地 Mock 记录或交付证据，不依赖对话记忆作为唯一状态来源。

错误处理：缺少输入、Schema 校验失败、非白名单命令、风险工具、审核绕过、候选人答案泄露和真实执行企图都必须返回失败 JSON，并保留审计证据。

## 交付流程

1. 读取 `skills/operations-skill-pack/SKILL.md`，确认 Lab / Exam / Grading / PPT 生成仍由 DSL 和审核门禁承载。
2. 读取 `mcp-server/tools.manifest.json`，确认可暴露给独立智能体的工具仍是 Mock Tool。
3. 读取 `delivery/HIGH_RISK_MCP_HANDOFF.md`，确认发布和销毁类工具不能被智能体直接执行。
4. 读取 `delivery/OPERATIONS_MANUAL.md` 和 `delivery/FINAL_SIGNOFF.md`，确认运营签收仍依赖本地白名单命令。
5. 运行独立智能体交付契约测试，确认文档、契约、白名单和安全断言一致。

## 命令示例

```powershell
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_mcp_manifest.py
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_final_signoff.py
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
```

## 测试方式

```powershell
python -m pytest tests/test_standalone_agent_delivery.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_final_signoff.py
python -m pytest
```

## 限制说明

- 不连接真实外部平台。
- 不创建或启动真实 Agent。
- 不接入真实大模型或真实 Provider。
- 不启动真实 MCP Server。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱、未知 Shell 或选手代码。
- 不允许独立智能体直接发布 Lab / Exam 或销毁环境。
- 不绕过 `WAITING_REVIEW` 人工审核。
- 不上传交付包，不输出密钥，不向选手端展示标准答案。
