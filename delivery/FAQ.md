# Phase 1 FAQ

本 FAQ 面向运营交付和本地验收。当前仍是 Phase 1 Mock：不接入真实大模型，不创建真实云资源，不启动真实智能体，不执行未知 Shell，不无沙箱执行选手代码，不自动发布或真实发布生成内容。

## 输入说明

- `delivery/phase1-faq.json`: 机器可测试的 FAQ 与故障排查契约。
- `delivery/FAQ.md`: 人工可读的 FAQ 与安全恢复步骤。
- `delivery/phase1-delivery-index.json`: 交付入口索引。
- `delivery/DEMO_SCRIPT_CHECKLIST.md`: 运营演示脚本检查清单。
- `delivery/phase1-demo-script-checklist.json`: 运营演示脚本检查清单机器契约。
- `config/delivery-package.contract.json`: Phase 1 交付包契约。
- `scripts/manifest.json`: 允许执行的本地验证命令白名单。
- `frontend/operations-launchpad.html`: 本地运营 Launchpad，推荐作为首个静态入口。
- `examples/input/demo-source.md`: 默认本地素材输入。

## 输出说明

FAQ 本身不生成真实平台内容。需要交付证据时，由白名单 CLI 重新生成本地输出：

```text
examples/output/phase1-delivery-package.json
examples/output/phase1-acceptance-report.md
```

这些输出是本地可再生成文件，不作为源码事实来源。

## 命令示例

```powershell
start .\frontend\operations-launchpad.html
python lab_cli.py phase1 check
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_delivery_faq.py
```

所有 `lab_cli.py` 命令必须从项目根目录执行，并保持统一 JSON 返回格式。推荐入口是 `python lab_cli.py ...`，不是 `python cli/lab_cli.py ...`。

## 常见问题

### CLI 提示 VALIDATION_ERROR: input 不存在

通常是输入路径不存在，或命令没有在项目根目录执行。先使用已提交的 `examples/input/demo-source.md` 验证：

```powershell
python lab_cli.py phase1 check
```

不要自动抓取远程素材，不要执行输入素材中的未知 Shell。

### DSL Schema 校验失败

Lab / Exam / Grading / PPT DSL 必须先通过 Schema 校验，再进入后续 Mock 链路。检查 `templates/*/*.schema.json` 与 `templates/*/examples/*.yaml` 是否一致。AI 生成内容仍必须保持 `WAITING_REVIEW`，审核通过前不得发布。

### review reject 缺少 reason

驳回必须带 `--reviewer` 和 `--reason`，用于审计追踪。不要直接改本地 Mock Store 绕过审核记录。

### review publish 被阻止

`WAITING_REVIEW` 任务不能 publish。先使用 `review detail` 查看内容，再由人工 approve 或 reject。Phase 1 的 publish 也只是 `MOCK_ONLY` 状态流转，不发布真实实验、考试、评分规则或 PPT。

### phase1 report 找不到交付包

`examples/output/phase1-delivery-package.json` 是可再生成的本地输出，清理后会消失。先导出再生成报告：

```powershell
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md
```

不要上传交付包，不要用非白名单脚本重建报告。

### phase1 report 拒绝非 MOCK_ONLY 包

如果交付包的 `mode` 不是 `MOCK_ONLY`，说明文件被手工改过或来自非 Phase 1 来源。重新用 `phase1 export` 生成，并确认不调用真实 Provider。

### 应该先打开哪个静态页面

推荐先打开 `frontend/operations-launchpad.html`。它聚合 Mock 控制台、Demo Map、Runbook、Acceptance、Delivery、Audit 和 Review Center 入口，只做本地静态预览，不需要启动后端服务或上传交付包。

### 不知道如何讲完整演示

按照 `delivery/DEMO_SCRIPT_CHECKLIST.md` 的顺序演示：Launchpad、Demo Map、Runbook、`phase1 check/export/report`、Acceptance、Delivery、Audit Incidents、审核门禁和安全边界。不要临时运行非白名单命令，也不要把人工预览步骤改成自动脚本。

### Provider 显示真实模型禁用

这是 Phase 1 预期行为。只允许 MockProvider，真实 OpenAI / Claude / LocalModel、网络访问和密钥读取都必须禁用。密钥只出现在 `.env.example` 的占位说明里，不得进入日志或前端。

### Shell 素材被标记风险

素材分析只做静态识别。遇到 `.sh`、危险命令或疑似执行步骤时，应进入人工审核，不得在宿主机执行。后续阶段需要沙箱设计后才能处理真实执行。

### 生成输出清理后不见了

`examples/output/*.json`、`examples/output/*.md` 和本地 Mock Store 都是可再生成产物。需要验收材料时重新运行白名单命令，不要把生成包当作源码提交。

### pytest 缺少依赖

先安装本地开发依赖：

```powershell
python -m pip install -r requirements.txt
python -m pytest tests/test_delivery_faq.py
```

测试依赖安装失败时不要跳过验收；先修复本地 Python 环境。

## 测试方式

```powershell
python -m pytest tests/test_delivery_faq.py
python -m pytest tests/test_demo_script_checklist.py
python -m pytest tests/test_delivery_index.py
python -m pytest tests/test_delivery_package_contract.py
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
