# config

Phase 1 运行配置契约目录。当前只声明 Mock 默认值、环境变量来源和密钥安全规则，不接入真实 Provider。

## 输入说明

- `runtime.contract.json`: Phase 1 配置契约。
- `providers/provider.contract.json`: Provider Mock 契约，位于 `providers/` 目录。
- `local-artifacts.contract.json`: 本地产物忽略契约。
- `delivery-package.contract.json`: Phase 1 Mock 交付包和验收清单契约。
- `.env.example`: 根目录本地配置示例。

## 输出说明

配置默认值必须保持：

```text
APP_PHASE=Phase 1
APP_MODE=MOCK_ONLY
ENABLE_REAL_LLM=false
ENABLE_REAL_CLOUD=false
ENABLE_REAL_SANDBOX=false
ENABLE_AUTO_PUBLISH=false
```

## 命令示例

```powershell
python -m pytest tests/test_config_contract.py
python -m pytest tests/test_local_artifacts_contract.py
python -m pytest tests/test_delivery_package_contract.py
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- `.env.example` 只能包含空值或安全占位值。
- 不得提交真实 `.env`。
- 不得提交本地 Mock Store、生成报告、测试缓存或交付包归档。
- `examples/output/README.md` 可保留，`examples/output/*.json` 为本地生成物。
- `phase1 export` 的交付包必须包含验收清单、安全断言和本地可复现命令。
- 不得把 API Key、Token、密码写进代码或文档。
- Phase 1 禁用真实 LLM、真实云资源、真实沙箱和自动发布。
- Provider 契约只允许 `mock` 启用，真实 Provider 为禁用占位。
- 真实密钥只能在后续阶段通过环境变量或配置中心注入。
