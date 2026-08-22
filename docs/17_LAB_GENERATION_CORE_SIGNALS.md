# 17_LAB_GENERATION_CORE_SIGNALS

状态：已实现第一版。

本文件记录 Phase 2 Lab 生成核心业务参数与审核质量信号。它不是新的门禁，也不是新的禁用壳；后续不应因为本文件继续追加安装前、请求前或执行器禁用步骤。

## 范围

已实现：

- `phase2 workflow run` 支持 Lab 生成业务参数：目标用户、课时、难度、技术标签、教学风格。
- Workflow Report 输出 `labGenerationContext`。
- Workflow Report 输出 `qualitySignals`，包含整体审核状态、Lab 结构摘要、素材引用覆盖、素材风险复核、Schema 摘要和审核重点。
- `qualitySignals.lab.matching` 输出目标用户、课时、难度、技术标签、步骤粒度和教学风格的匹配信号；这些信号只辅助人工审核，不自动驳回或发布。
- `qualitySignals.materialCoverage` 会检查 Lab DSL `spec.materials[].path` 是否引用本次输入素材，并输出 `riskReview`。
- Lab Artifact metadata 记录 generation context 与 quality signals。
- `review detail` 的 `reviewPage` 输出 generationProfile、qualitySignals、providerSummary；真实 Demo 模式下 providerSummary 会包含 responseId、usage、Provider 审计摘要和调用摘要。
- 真实 Lab 最小单请求输入会携带 generation context；仍只发一次请求。
- 真实 Lab prompt 已升级为 `real-llm-minimal-poc-v2`，并在 `prompts/workflows/lab_generation.md` 中明确 generation context 到 Lab DSL 字段的映射。

未实现：

- 不把真实 LLM 设为默认 Provider。
- 不自动发布。
- 不执行真实 Agent。
- 不创建真实云资源。
- 不执行沙箱或选手代码。

## 命令

默认 Mock：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-content-generation-report.json --target-users "高职学生,教师" --duration-minutes 90 --difficulty intermediate --tech-tags "Python,Notebook" --teaching-style project_based
```

显式真实 Lab：

```powershell
python lab_cli.py phase2 workflow run --input examples/input/demo-source.md --reviewer teacher_1 --output examples/output/phase2-real-llm-workflow-report.json --provider-mode real-llm-minimal --real-lab-output examples/output/phase2-real-llm-lab.json --model <model> --target-users "平台开发者" --duration-minutes 45 --tech-tags "LLM" --explicit-real-call-opt-in --confirm-single-request --confirm-lab-only --confirm-waiting-review --confirm-no-auto-publish
```

## 输出

关键字段：

```json
{
  "labGenerationContext": {
    "targetUsers": ["高职学生", "教师"],
    "durationMinutes": 90,
    "difficulty": "intermediate",
    "techTags": ["Python", "Notebook"],
    "teachingStyle": "project_based"
  },
  "qualitySignals": {
    "overall": {
      "status": "READY_FOR_HUMAN_REVIEW",
      "reviewRequired": true,
      "publishBlockedUntilApproved": true
    },
    "lab": {
      "matching": {
        "status": "NEEDS_REVIEW",
        "targetUsers": {"matched": false},
        "durationMinutes": {"matched": false},
        "difficulty": {"matched": false},
        "techTags": {"matched": false},
        "stepGranularity": {"matched": true},
        "teachingStyle": {"matched": false}
      },
      "teachingStyleSignal": {
        "status": "NEEDS_REVIEW",
        "requestedStyle": "project_based",
        "matched": false
      }
    },
    "materialCoverage": {
      "status": "LINKED",
      "sourceReferencedInDsl": true,
      "referencedPaths": ["examples/input/demo-source.md"],
      "riskReview": {
        "status": "CLEAR",
        "riskCount": 0,
        "unknownShellExecuted": false
      }
    },
    "reviewHighlights": []
  }
}
```

## 验证

```powershell
python -m pytest tests/test_provider_adapter_workflow.py tests/test_phase2_workflow_orchestrator.py tests/test_real_llm_minimal_poc.py
```

## 下一步

- 将审核详情中的 providerSummary、candidatePreview 和 qualitySignals 接入前端审核页展示。
- 扩展 Exam/Grading 生成质量信号：标准答案隐藏、评分点覆盖、自动评分计划可解释性。
- 在有真实 `OPENAI_API_KEY` 和模型名时执行一次在线 Lab 生成，人工复核 v2 prompt 的字段匹配效果。
