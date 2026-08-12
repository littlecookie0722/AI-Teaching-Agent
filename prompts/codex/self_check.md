---
id: self_check_v0
version: 0.1.0
phase: Phase 1
mode: MOCK_ONLY
outputKind: ReviewReport
---

请基于当前代码进行一次自检，不要直接修改代码。

检查项：
1. 是否符合 AGENTS.md；
2. 是否符合 docs/AI_PLATFORM_CODEX_FULL_GUIDE.md；
3. 是否有硬编码密钥；
4. 是否有 AI 结果绕过审核；
5. 是否有无沙箱执行代码；
6. CLI 返回格式是否统一；
7. DSL 是否经过 schema 校验；
8. 是否缺少 README；
9. 是否缺少测试；
10. 是否有高风险操作未加审核。

请输出：
- 问题清单
- 风险等级
- 建议修复顺序
- 每个问题涉及文件
