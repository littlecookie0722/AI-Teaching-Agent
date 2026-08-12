---
id: phase1_bootstrap_v0
version: 0.1.0
phase: Phase 1
mode: MOCK_ONLY
outputKind: DevelopmentPlan
---

请先阅读 AGENTS.md 和 docs/AI_PLATFORM_CODEX_FULL_GUIDE.md。

当前只做 Phase 1：项目底座。

不要接入真实大模型。
不要接入真实云资源。
不要做真实发布。
不要无沙箱执行代码。

请完成：
1. 创建 docs、cli、mcp-server、ai-workflows、templates、prompts、skills、sandbox、examples、scripts 目录；
2. 每个目录添加 README.md；
3. 创建 lab / exam / grading / ppt 四类 DSL schema；
4. 创建每类 DSL 的 examples；
5. 创建 lab-cli Mock 框架；
6. CLI 支持 lab、exam、grade、ppt、ai-task、review 命令组；
7. 所有 CLI 统一返回 JSON；
8. 创建 AI Task 状态模型；
9. 实现 WAITING_REVIEW、APPROVED、REJECTED 状态流转；
10. 添加基础测试；
11. 输出修改文件、验证方式、风险、下一步建议。

请先给出执行计划，再开始修改文件。
