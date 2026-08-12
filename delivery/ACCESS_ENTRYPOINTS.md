# Phase 5 Access Entrypoints Delivery

本交付说明用于描述本地 Mock 平台的可视化网页访问入口和未来 IP + 端口交付边界。当前只交付静态页面、机器契约和白名单测试，不启动真实 HTTP 服务，不绑定真实 IP，不开放外网访问，不创建真实云资源。

## 输入说明

- `frontend/access.html`: 本地访问入口静态页面。
- `frontend/console.html`: 前端 Mock 控制台入口。
- `frontend/operations-launchpad.html`: 运营演示首屏入口。
- `frontend/operations-signoff.html`: 运营签收总览页面。
- `frontend/delivery.html`: 交付验收页面。
- `frontend/ui.manifest.json`: 前端页面契约。
- `frontend/mock-data.json`: 前端 Mock 数据。
- `scripts/manifest.json`: 本地验证命令白名单。
- `config/delivery-package.contract.json`: 交付包契约。

## 输出说明

- `delivery/ACCESS_ENTRYPOINTS.md`: IP + 端口访问入口 Mock 交付说明。
- `delivery/access-entrypoints.json`: IP + 端口访问入口 Mock 交付机器契约。
- `frontend/access.html`: 本地访问入口静态原型。

这些输出只用于本地交付和人工验收，不代表真实部署地址，不包含公网 IP、域名、TLS 证书、反向代理配置或服务端口监听进程。

## Mock 访问入口

当前可交付入口是本地静态文件：

```text
frontend/access.html
frontend/operations-launchpad.html
frontend/operations-signoff.html
frontend/delivery.html
frontend/console.html
```

未来真实部署前可沿用以下占位口径，但当前全部禁用：

| 入口 | 计划地址 | 当前状态 | 限制 |
| --- | --- | --- | --- |
| Frontend 2.0 | `http://127.0.0.1:3000` | DISABLED | 不启动真实前端服务 |
| Backend Mock API | `http://127.0.0.1:8000` | DISABLED | 不监听端口，不连接生产数据 |
| MCP Server | `http://127.0.0.1:8080` | DISABLED | 不启动真实 MCP Server |
| 独立智能体 | N/A | DOCUMENTATION_ONLY | 不连接真实外部平台 |

## 命令示例

```powershell
start .\frontend\access.html
start .\frontend\operations-launchpad.html
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_frontend_manifest.py
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
```

`start .\frontend\access.html` 只作为人工本地预览动作，不属于自动化白名单命令。自动化验证仍只使用 `scripts/manifest.json` 中的 `python ...` 命令。

## 测试方式

```powershell
python -m pytest tests/test_access_entrypoints.py
python -m pytest tests/test_frontend_manifest.py
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_final_signoff.py
python -m pytest
```

## 限制说明

- 不启动真实 HTTP 服务。
- 不绑定 `0.0.0.0`、公网 IP 或内网 IP。
- 不开放外网、局域网或反向代理访问。
- 不生成公网 URL、域名、TLS 证书或部署包。
- 不连接真实外部平台。
- 不启动真实智能体或真实 MCP Server。
- 不接入真实大模型或真实 Provider。
- 不创建、变更或删除真实云资源。
- 不执行真实沙箱、未知 Shell 或选手代码。
- 不上传交付包，不自动发布或真实发布生成内容。
