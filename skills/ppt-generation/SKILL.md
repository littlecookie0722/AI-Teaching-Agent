---
name: ppt-generation
description: Generate PPT DSL from course source material through a review-first Phase 1 mock workflow.
---

# PPT Generation Skill

## 触发场景

当用户要求基于课程资料、Markdown 或实验说明生成课件大纲或 PPT DSL 时使用。

## 输入

- Markdown 文件
- 课程资料
- 实验说明
- 目标受众

## 输出

必须输出 PPT DSL。

## 步骤

1. 读取资料。
2. 提取章节结构。
3. 生成 slide plan。
4. 生成 PPT DSL。
5. 校验 PPT DSL。
6. 进入 WAITING_REVIEW。

## 禁止

- Phase 1 不生成真实 PPT 文件
- 不得直接发布课件
- 不得跳过 DSL
- 不得调用真实大模型
