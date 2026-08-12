# 16_REAL_LLM_WORKFLOW_RECONNECT

状态：已实现，默认仍为 Mock。

本文件记录真实 LLM 最小单请求 PoC 接回 Phase 2 Lab DSL 生成 Workflow 的结果。它不是新的安全门禁、禁用壳或评审壳，而是第 7 步核心业务接回实现。

## 范围

已实现：

- `phase2 workflow run --provider-mode real-llm-minimal`
- 真实 LLM 只生成 Lab DSL。
- Exam / Grading / PPT 仍使用 MockProvider。
- Workflow Report、AI Task、Artifact、WorkflowRun、Provider 审计统一记录真实 Lab 调用边界。
- 所有生成 DSL 仍进入 `WAITING_REVIEW`。

未实现：

- 不把真实 Provider 设为默认值。
- 不自动发布实验或考试。
- 不创建真实云资源。
- 不启动真实 Agent。
- 不执行沙箱或选手代码。
- 不展示标准答案给选手端。

## 命令

默认 Mock 路径：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json
```

显式真实 Lab 路径：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-real-llm-workflow-report.json --provider-mode real-llm-minimal --real-lab-output examples/output/phase2-real-llm-lab.json --model <model> --explicit-real-call-opt-in --confirm-single-request --confirm-lab-only --confirm-waiting-review --confirm-no-auto-publish
```

读取报告：

```powershell
python lab_cli.py phase2 workflow report --file examples/output/phase2-real-llm-workflow-report.json
```

## 输出

真实 Lab 模式报告关键字段：

```json
{
  "mode": "REAL_LLM_MINIMAL_LAB_WORKFLOW",
  "providerMode": "real-llm-minimal",
  "generatedDsl": {
    "lab": {
      "status": "WAITING_REVIEW",
      "provider": {
        "providerId": "openai",
        "realLlmCalled": true,
        "networkAccess": true
      }
    },
    "exam": {
      "provider": {
        "providerId": "mock",
        "realLlmCalled": false
      }
    }
  },
  "safety": {
    "realLlmCalled": true,
    "realPublish": false,
    "sandboxExecuted": false,
    "contestantCodeExecuted": false
  }
}
```

## 失败路径

当前环境缺少真实 `OPENAI_API_KEY` 时，真实 Lab 路径会返回统一 JSON 失败：

```text
REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED
```

失败时不会写 Workflow Report，不会创建 AI Task，不会写 Artifact，不会发送请求。

## 验证

```powershell
python -m pytest tests/test_provider_adapter_workflow.py tests/test_phase2_workflow_orchestrator.py tests/test_real_llm_minimal_poc.py
```

本地测试使用 monkeypatch 模拟真实 LLM 返回，不依赖真实 key，不发送在线请求。

## 下一步

进入核心业务开发。Lab 生成输入参数、质量信号和审核详情证据链第一版已完成，记录见 `docs/17_LAB_GENERATION_CORE_SIGNALS.md`。

后续优先增强：

- 真实 Lab prompt 对 generation context 的严格匹配。
- 更细的素材引用覆盖、步骤粒度和风险项复核。
- 审核详情前端接入 providerSummary / qualitySignals。

建议智能模式：GPT-5.5 超高智能模式。
