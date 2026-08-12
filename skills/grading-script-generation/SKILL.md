---
name: grading-script-generation
description: Generate deterministic and auditable grading DSL and scripts for lab or exam submissions.
---

# Grading Script Generation Skill

## 触发场景

当用户要求为实验、考试、竞赛题目生成自动评分脚本时使用。

## 输出

必须输出 Grading DSL。

## 优先评分方式

1. 文件存在性
2. 命令输出
3. pytest
4. Notebook 执行
5. JSON 字段
6. 日志关键字

## 禁止

- 不得直接让 LLM 给最终分数
- 不得无标准答案评分
- 不得无沙箱执行代码
