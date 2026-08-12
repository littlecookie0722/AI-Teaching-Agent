---
name: exam-generation
description: Transform an approved or mock Lab DSL into Exam DSL and Grading DSL for Phase 1 review.
---

# Exam Generation Skill

## 触发场景

当用户要求把已有实验改造成考试、竞赛题或 Notebook 挖空题时使用。

## 输入

- Lab DSL
- Lab id
- 题型要求

## 输出

必须输出 Exam DSL，并关联 Grading DSL。

## 步骤

1. 读取 Lab DSL 或 Lab id。
2. 识别适合挖空的步骤。
3. 生成题干和候选答案。
4. 生成 Exam DSL。
5. 生成或关联 Grading DSL。
6. 校验 Exam DSL 和 Grading DSL。
7. 进入 WAITING_REVIEW。

## 禁止

- 不得把标准答案展示给选手端
- 不得直接发布考试
- 不得绕过人工审核
- 不得调用真实大模型
