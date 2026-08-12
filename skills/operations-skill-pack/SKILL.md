---
name: operations-skill-pack
description: Use the local mock Skill pack for Phase 5 operations handoff, combining Lab, Exam, Grading, PPT, review, delivery, and high-risk MCP handoff workflows without starting real agents or providers.
---

# Operations Skill Pack

本 Skill 包面向运营复用。它不是智能体编排器，也不启动真实大模型；它只说明如何组合现有本地 Mock Skills、Prompt、Workflow、DSL Schema、CLI 和交付文档。

## 输入说明

- `examples/input/demo-source.md`: 本地演示素材。
- `templates/lab/examples/basic-lab.yaml`: Lab DSL 示例。
- `examples/notebooks/demo-lab.ipynb`: Notebook 转试题示例输入。
- `skills/manifest.json`: 基础 Skill 注册表。
- `skills/operations-skill-pack.contract.json`: 运营 Skill 包机器契约。
- `delivery/OPERATIONS_MANUAL.md`: 运营手册。
- `delivery/FINAL_SIGNOFF.md`: 最终签收包。
- `delivery/PHASE5_MOCK_BASELINE.md`: 真实 LLM PoC 前的 Mock 基线冻结说明。
- `providers/real-sdk-dependency-env-gate.contract.json`: 真实 SDK 依赖与环境变量门禁契约。

## 输出说明

运营复用输出必须先落到 DSL 或本地验收证据：

- Lab 生成输出：Lab DSL，默认 `WAITING_REVIEW`。
- Exam 转换输出：Exam DSL 和 Grading DSL，默认 `WAITING_REVIEW`。
- Grading 输出：Mock 评分报告，不执行选手代码。
- PPT 输出：Slide plan JSON 和 PPT DSL，默认 `WAITING_REVIEW`。
- 交付输出：本地交付包和验收报告。

## 使用步骤

1. 先阅读 `delivery/OPERATIONS_MANUAL.md`，确认运营目标和安全边界。
2. 使用 `lab-generation` 生成或复用 Lab DSL，输出必须通过 `templates/lab/lab.schema.json`。
3. 使用 `exam-generation` 将 Lab DSL / Notebook 转成 Exam DSL，并确保标准答案不展示给选手端。
4. 使用 `grading-script-generation` 生成或复用 Grading DSL，真实执行前必须进入沙箱；当前仅允许 Mock 计划。
5. 使用 `ppt-generation` 先生成 slide plan，再生成 PPT DSL；当前不生成真实 PPT 文件。
6. 所有生成结果进入 `WAITING_REVIEW`，审核通过前不得 publish。
7. 运行交付验证命令，确认 `missingRequired=0` 和安全断言通过。
8. 阅读 `delivery/HIGH_RISK_MCP_HANDOFF.md`，确认高风险 MCP 只创建审核意图或只读查询。
9. 阅读 `delivery/PHASE5_MOCK_BASELINE.md`，确认默认 Provider 仍为 `mock`，真实 LLM PoC 只能显式 opt-in 且先限定 Lab DSL 单链路。
10. 运行真实 SDK dependency/env gate 与 dependency install plan 测试，确认它只做设计评审，不安装 SDK、不检查密钥。
11. 阅读 `delivery/FINAL_SIGNOFF.md` 并完成最终签收测试。

## 命令示例

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json
python lab_cli.py phase2 exam-convert run --lab templates/lab/examples/basic-lab.yaml --notebook examples/notebooks/demo-lab.ipynb --reviewer teacher_1 --output examples/output/phase2-exam-conversion-report.json
python lab_cli.py phase2 ppt-generate run --input examples/input/demo-source.md --reviewer teacher_1 --slide-plan-output examples/output/phase2-ppt-slide-plan.json --output examples/output/phase2-ppt-generation-report.json
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_enablement.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
```

## 测试方式

```powershell
python -m pytest tests/test_operations_skill_pack.py
python -m pytest tests/test_skill_manifest.py
python -m pytest tests/test_operations_manual.py
python -m pytest tests/test_final_signoff.py
python -m pytest tests/test_phase5_mock_baseline.py
python -m pytest tests/test_real_sdk_enablement.py
python -m pytest tests/test_real_sdk_minimal_impl.py
python -m pytest tests/test_real_sdk_dependency_env_gate.py
python -m pytest tests/test_real_sdk_dependency_install_plan.py
python -m pytest tests/test_real_sdk_dependency_installer_audit.py
python -m pytest
```

## 限制说明

- 不启动真实 Agent。
- 不接入真实大模型或真实 Provider。
- 不安装真实 SDK，不检查或读取真实密钥环境变量。
- 不启动真实 MCP Server。
- 不创建、变更或删除真实云资源。
- 不执行未知 Shell 脚本。
- 不执行真实沙箱或选手代码。
- 不自动发布或真实发布生成内容。
- Prompt 只能引用 `prompts/`，不得散落在业务代码。
