---
name: lab-generation
description: Generate platform-compatible teaching lab DSL from GitHub, Markdown, Shell, or other source material.
---

# Lab Generation Skill

## 触发场景

当用户要求基于开源项目、README、Shell 脚本、课程文档生成教学实验时使用。

## 输入

- GitHub URL
- Markdown 文件
- Shell 脚本
- 课程资料
- 技术栈说明

## 输出

必须输出 Lab DSL。

## 步骤

1. 读取资料。
2. 识别技术栈。
3. 提取教学目标。
4. 生成实验步骤。
5. 生成环境配置。
6. 生成评分点。
7. 校验 Lab DSL。
8. 进入 WAITING_REVIEW。

## 禁止

- 不得直接发布
- 不得跳过 DSL
- 不得执行未知脚本
