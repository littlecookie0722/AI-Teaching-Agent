# materials

Phase 1 素材分析 Mock。当前只对本地 Markdown、文本和 Shell 文件做静态分析，用于在生成 DSL 前留下可审计的输入摘要和风险标记。

## 输入说明

- 支持 `.md`、`.markdown`、`.txt`、`.sh`、`.bash`。
- 输入必须是本地文件。
- 文件大小默认限制为 256KB。

## 输出说明

输出为统一 JSON data 内的 `analysis` 对象：

```json
{
  "mode": "MOCK_ONLY",
  "inputRef": "examples/input/demo-source.md",
  "fileType": "markdown",
  "title": "Demo",
  "detectedTechnologies": ["Python"],
  "risks": [],
  "realLlmCalled": false,
  "remoteContentFetched": false,
  "unknownShellExecuted": false,
  "sandboxExecuted": false
}
```

## 命令示例

```powershell
python lab_cli.py material analyze --input examples/input/demo-source.md
```

Backend Mock：

```text
POST /api/materials/analyze body={"input":"examples/input/demo-source.md"}
```

## 测试方式

```powershell
python -m pytest tests/test_material_analyzer.py
python -m pytest
```

## 限制说明

- 不执行 Shell。
- 不调用真实大模型。
- 不抓取远程内容。
- 不创建真实资源。
- 发现风险模式时只标记 `requiresHumanReview=true`，不自动阻断或发布。
