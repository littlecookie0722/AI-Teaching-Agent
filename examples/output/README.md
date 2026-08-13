# examples/output

该目录用于保存本地生成报告，以及少量经过脱敏的只读回归夹具。

## 输入说明

通过命令的 `--output` 参数指定输出路径；不指定时默认写入本目录。

## 输出说明

报告为 JSON 文件，包含：

- `mode`: `MOCK_ONLY`
- `steps`: Mock 主链路步骤
- `reviewRequired`: 是否需要人工审核
- `publishBlockedUntilApproved`: 是否阻止未审核发布

`demo offline` 还会写出两个关联文件：`offline-demo-workflow-report.json`
和 `offline-demo-candidate-preview.json`。Demo summary 中的
`blockingIssueTotal` 必须为 0；低级质量 warning 可以保留并交给人工审核，
不会被误判为自动通过。

## 命令示例

```powershell
python lab_cli.py demo offline
python lab_cli.py grade run --grading templates/grading/examples/python-pytest.yaml --output examples/output/grading-report.json
python lab_cli.py grade report --file examples/output/grading-report.json
python lab_cli.py workflow demo --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/demo-report.json
python lab_cli.py workflow report --file examples/output/demo-report.json
python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json
```

## 测试方式

```powershell
python -m pytest
```

## 限制说明

- 仅保存 Mock 报告，不写入真实数据库。
- 本目录下新生成的 `*.json` 报告默认属于本地产物，通过 `.gitignore` 忽略。
- `.gitignore` 中逐项放行的 JSON 是经过脱敏的固定回归夹具，用于验证干净检出和 CI；其中路径必须使用仓库相对路径，不得包含密钥或本机绝对路径。
- `phase1-delivery-package.json` 必须包含验收清单、安全断言和本地推荐验证命令。
- 报告不代表真实发布结果。
- 评分报告不执行选手代码。
- Phase 1 交付包仅用于演示和运营预览，不代表真实上线材料。
