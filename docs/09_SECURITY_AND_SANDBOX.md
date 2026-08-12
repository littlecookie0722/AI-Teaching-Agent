# 09_SECURITY_AND_SANDBOX

# 安全红线

1. 不得无沙箱执行用户代码。
2. 不得直接执行未知 Shell。
3. 不得把密钥写入代码。
4. 不得让 AI 结果自动发布。
5. 不得把标准答案展示给选手。
6. 不得直接删除云资源。
7. 不得绕过审核流程。

# 评分沙箱要求

必须限制：

- CPU
- 内存
- 执行时间
- 文件系统
- 网络访问
- 进程数量

# 高风险操作

以下操作必须进入审核：

- 发布实验
- 发布考试
- 创建真实 VM
- 销毁环境
- 批量导入题目
- 生产配置变更

# Phase 1 环境 Mock 约束

- `lab-cli env create/start/stop/reset` 只能更新本地 JSON Mock 状态。
- 不得调用云厂商 API。
- 不得创建真实 VM 或 Notebook。
- 不得销毁真实环境。
- 后续进入真实环境管理前，必须增加人工审核和二次确认。

# Phase 1 Sandbox Mock 约束

- `sandbox/mock_executor.py` 只生成确定性 Mock 评分报告。
- `sandboxExecuted=false`。
- `contestantCodeExecuted=false`。
- 不执行 Grading DSL 中的 `command`。
- 不执行未知 Shell。
- 不访问网络。
- 不读取宿主机敏感路径。
- 不创建真实容器、VM 或 Notebook。

契约文件：

```text
sandbox/sandbox.contract.json
```

校验方式：

```powershell
python -m pytest tests/test_sandbox_mock_executor.py
```

# Phase 1 素材分析 Mock 约束

- `lab-cli material analyze` 和 `POST /api/materials/analyze` 只读取本地 UTF-8 文本素材。
- 支持 `.md`、`.markdown`、`.txt`、`.sh`、`.bash`，单文件最大 256KB。
- 不执行素材中的 Shell 命令。
- 不抓取 `curl`、`wget` 或 URL 指向的远程内容。
- 不调用真实 LLM。
- 发现 `rm -rf`、`sudo`、`docker run`、`kubectl`、`terraform` 等模式时只返回风险标记和 `requiresHumanReview=true`。

校验方式：

```powershell
python -m pytest tests/test_material_analyzer.py
```

# 后续真实沙箱准入条件

进入真实评分沙箱前，至少必须具备：

- CPU 限制
- 内存限制
- 执行超时
- 默认禁用网络
- 文件系统隔离
- 进程数量限制
- stdout / stderr 捕获
- 审计日志
- 不在宿主机直接执行选手代码

# Phase 3 Grade Runner Mock 约束

- `sandbox/grade_runner.py` 只把 Grading DSL 转成评分计划和 Mock 报告。
- 支持 `file_exists`、`stdout_contains`、`pytest`、`notebook_cell`、`json_field`、`log_keyword` 六类评分项，但只输出 `MOCK_PLAN_ONLY`。
- `notebook_cell` / `json_field` / `log_keyword` 在当前阶段只生成计划，不执行 Notebook，不读取真实 JSON 文件或日志文件。
- `file_exists` 不读取真实选手目录或宿主机敏感路径。
- `stdout_contains` 不执行 DSL 中的 `command`。
- `pytest` 不运行 pytest，不执行选手代码。
- 报告必须保持 `sandboxExecuted=false`、`commandExecuted=false`、`contestantCodeExecuted=false`。
- `MOCK_GRADING_RUN.detail` 只记录 runner、checkSummary、checkPlans 和阻断动作，必须保持 `runRealPytestEnabled=false`、`hostExecutionAllowed=false`。
- 评分报告必须输出 `sandboxPolicy`、`explainability`、`checks[].inputSummary`、`checks[].mockEvidence` 和 `checks[].executionPlan.requiredLimits`，用于后续真实沙箱实现时替换 executor 并收集真实证据。
- `grade sandbox-run --execution-mode readonly` 只执行 `file_exists` / `json_field` 只读证据采集，不执行命令或 pytest。
- `grade controlled-plan` 只生成受控 Docker 可执行子集 Grading DSL，默认从真实 Grading DSL 中提取 `stdout_contains` / `pytest`，补齐 `command`、`expected`、`path` 等字段；该命令不启动容器、不执行命令、不运行 pytest，输出状态仍为 `WAITING_REVIEW`。
- `grade sandbox-run --execution-mode controlled-command` 是当前命令类评分的最小 Docker PoC，只允许 `stdout_contains` 和 `pytest`，提交目录只读挂载，网络固定关闭，不自动 pull 镜像；报告中 `contestantCodeExecuted=true` 仅表示选手代码在 Docker 受控环境中运行。
- 受控 Docker PoC 禁止未知 Shell 操作符、绝对路径、目录逃逸、Notebook 执行、宿主机命令、网络访问和真实发布；若 Docker daemon 或本地镜像不可用，CLI 必须返回统一 JSON 错误而不是降级到宿主机执行。
- `grade evidence-auto` 复用已有评分能力：默认只运行 `readonly` evidence，再输出合并报告；只有显式传 `--include-controlled-command` 才会尝试受控 Docker `stdout_contains` / `pytest`。Docker 或镜像不可用时默认降级为只读 evidence 并记录 warning，不会改为宿主机执行；传 `--fail-on-controlled-unavailable` 才会失败返回。
- 固定评分镜像基线为 `ai-grading-python:0.1`，由 `sandbox/images/python-pytest/Dockerfile` 定义；`grade sandbox-image build/verify` 只做本地镜像构建和 pytest 可用性验证，不 push、不读取密钥。

契约文件：

```text
sandbox/grade-runner.contract.json
```

校验方式：

```powershell
python lab_cli.py grade run --grading templates/grading/examples/mixed-checks.yaml --output examples/output/phase3-grading-report.json
python lab_cli.py grade evidence-auto --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/readonly-demo --output examples/output/grading-evidence-auto.json
python -m pytest tests/test_sandbox_mock_executor.py
```

# Phase 1 Scripts 安全约束

脚本契约文件：

```text
scripts/manifest.json
```

Phase 1 只允许本地验证和 Mock 导出命令：

- `python lab_cli.py phase1 check`
- `python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json`
- `python -m pytest`

禁止模式包括：

- 递归强制删除
- `git reset --hard`
- 云厂商 CLI
- `terraform destroy`
- `kubectl delete`
- `docker run`
- 管道下载后直接执行
- `Invoke-Expression`

校验方式：

```powershell
python -m pytest tests/test_scripts_manifest.py
```

# Phase 1 配置与密钥约束

配置契约文件：

```text
config/runtime.contract.json
```

本地示例文件：

```text
.env.example
```

默认必须保持：

- `APP_MODE=MOCK_ONLY`
- `ENABLE_REAL_LLM=false`
- `ENABLE_REAL_CLOUD=false`
- `ENABLE_REAL_SANDBOX=false`
- `ENABLE_AUTO_PUBLISH=false`

密钥规则：

- `.env.example` 只能保留空密钥占位。
- 不得提交真实 `.env`。
- API Key、Token、密码只能来自环境变量或配置中心。
- 前端不得展示密钥。
- 日志不得输出密钥。

校验方式：

```powershell
python -m pytest tests/test_config_contract.py
```

# Phase 1 Provider Mock 约束

Provider 契约文件：

```text
providers/provider.contract.json
```

必须保持：

- 只有 `mock` Provider 启用。
- OpenAI、Anthropic、Local Model Provider 只作为禁用占位。
- 不读取真实 API Key。
- 不访问网络。
- 不调用真实 LLM。
- Mock 生成输出默认 `WAITING_REVIEW`。
- Prompt 只能从 `prompts/` 契约引用，不得散落在业务代码。

校验方式：

```powershell
python -m pytest tests/test_provider_contract.py tests/test_provider_mock.py
```

# Phase 1 本地产物忽略约束

忽略规则文件：

```text
.gitignore
```

契约文件：

```text
config/local-artifacts.contract.json
```

必须保持：

- 真实 `.env` 和 `.env.*` 不进入版本库。
- `.env.example` 作为安全模板保留。
- `cli/.lab_cli_store.json` 和自定义 Mock Store 不进入版本库。
- `examples/output/*.json` 为本地生成报告，不进入版本库。
- `examples/output/README.md` 作为目录说明保留。
- Python 缓存、pytest 缓存、日志、临时文件和本地交付包归档不进入版本库。

校验方式：

```powershell
python -m pytest tests/test_local_artifacts_contract.py
```

# Phase 1 交付包安全断言

交付包契约文件：

```text
config/delivery-package.contract.json
```

`phase1 export` 必须输出：

- `acceptanceChecklist`
- `acceptanceSummary`
- `deliveryManifest`
- `safetyAssertions`
- `securityLimits`

安全断言必须保持：

- 真实大模型禁用。
- 真实云资源禁用。
- 真实沙箱执行禁用。
- 自动发布禁用。
- 选手代码执行禁用。

校验方式：

```powershell
python -m pytest tests/test_delivery_package_contract.py
python -m pytest tests/test_scripts_manifest.py
```
