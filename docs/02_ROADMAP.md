# 02_ROADMAP

> 文档角色：路线导航索引。当前执行路线以 [`24_PROJECT_PROGRESS_MAP.md`](24_PROJECT_PROGRESS_MAP.md) 为唯一状态源；本文件不重复维护阶段封口或运营暂停规则。

## 当前入口

继续开发时按以下顺序读取：

1. [`../AGENTS.md`](../AGENTS.md)：全局执行约束、安全边界和交付要求。
2. [`24_PROJECT_PROGRESS_MAP.md`](24_PROJECT_PROGRESS_MAP.md)：当前优先级、已完成项和停止线。
3. 目标模块的 API、Schema、README 或专项技术文档。

## 当前路线摘要

项目已经越过 Phase 1 Mock 底座、真实 SDK 边界和最小真实 LLM PoC。默认路线是：

```text
真实 LLM 输出质量与归一化
→ 审核详情 / 导入预览 / Grading Report 产品化
→ 本地实体、状态和评分闭环
→ 稳定 CLI / API / MCP 工具化
→ Agent 只编排稳定工具
```

真实平台 API、平台 token/字段映射、`import-send`、`import-status`、平台签收发布和运营交付扩展当前暂停；具体例外以用户明确任务为准。

## 历史阶段参考

- SDK 与最小 PoC 边界：[`12_PHASE_CUTOVER_AND_CORE_BUSINESS.md`](12_PHASE_CUTOVER_AND_CORE_BUSINESS.md)
- 完整架构、DSL、API、Phase 任务和历史提示词：[`AI_PLATFORM_CODEX_FULL_GUIDE.md`](AI_PLATFORM_CODEX_FULL_GUIDE.md)
- 演示启动与本地使用：[`23_DEMO_USAGE_GUIDE.md`](23_DEMO_USAGE_GUIDE.md)

这些文档用于查背景和技术细节；如果其中的“当前下一步”与进度地图不一致，以进度地图为准。
