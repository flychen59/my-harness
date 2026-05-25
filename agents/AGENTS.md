# Multi-Agent Shared Skill Framework

> 基于 gitagent-protocol + ECC + anthropics/skills 的多 agent 共享进化 skill 框架
> 适配 Hermes harness，支持飞书手机指令控制

## 目录结构

```
agents/
├── AGENTS.md              # 本文件 — 框架说明
├── agent-registry/        # Agent 定义（每个 agent 一个目录）
│   ├── researcher/        # 研究 agent
│   ├── coder/             # 编码 agent
│   ├── reviewer/          # 审查 agent
│   └── coordinator/       # 协调 agent
├── shared-skills/         # 所有 agent 共享的 skill 库
├── memory/                # 跨 session 持久记忆
│   ├── runtime/           # 运行时状态（日志、上下文）
│   └── evolution/         # skill 进化记录
├── knowledge/             # 领域知识库
└── hooks/                 # 生命周期钩子
```

## 核心设计原则

1. **SKILL.md 标准** — 所有 skill 遵循 anthropics/skills 的 YAML frontmatter 格式
2. **共享优先** — shared-skills/ 下的 skill 所有 agent 自动共享
3. **Git 版本管理** — skill 变更 = git commit，可追溯、可回滚
4. **进化循环** — 使用 → 评估 → patch → 共享，自动从使用中学习
5. **飞书控制** — 手机发消息就能创建/管理/调用 skill

## 使用方式

### 飞书指令（手机控制）
直接在飞书群发消息给 Hermes：
- `创建skill 代码审查` → 自动生成 SKILL.md
- `列出所有skill` → 显示共享 skill 列表
- `给 researcher 加上论文搜索` → 更新 agent 配置
- `进化 skill:代码审查` → 触发 skill 自我改进

### Agent 间共享
```
shared-skills/           ← 所有 agent 共享
agent-registry/researcher/skills/  ← researcher 专属
agent-registry/coder/skills/       ← coder 专属
```
专属 skill 优先级 > 共享 skill

## Skill 格式

```yaml
---
name: my-skill
description: 描述
version: 1.0.0
metadata:
  hermes:
    tags: [tag1, tag2]
    related_skills: [other-skill]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---
# Skill Instructions

具体指令内容...
```
