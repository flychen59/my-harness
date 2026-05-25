---
name: feishu-skill-manager
description: 飞书指令控制 — 手机发消息就能创建、管理、调用 skill 和 agent
version: 1.0.0
metadata:
  hermes:
    tags: [feishu, mobile, control, skill-management, agent-management]
    related_skills: [planning, web-research]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# 飞书 Skill 管理器

> 手机发消息，直接控制 agent 和 skill 系统

## 支持的指令

### Skill 管理
- `创建skill {name}` — 创建新 skill（交互式）
- `创建skill {name} 描述:xxx 标签:a,b` — 快速创建
- `列出skill` / `显示所有skill` — 列出共享 skill
- `查看skill {name}` — 查看 skill 详情
- `修改skill {name}` — 修改 skill 内容
- `删除skill {name}` — 删除 skill
- `测试skill {name} {input}` — 测试运行 skill

### Agent 管理  
- `列出agent` — 显示所有 agent 及状态
- `查看agent {name}` — 查看 agent 详情
- `给 {agent} 加上 {skill}` — 给 agent 添加 skill
- `切换agent {name}` — 切换当前 agent

### 任务管理
- `任务 {description}` — 创建任务并自动分配
- `进度` / `任务状态` — 查看任务进度
- `暂停 {task}` / `继续 {task}` — 控制任务

### 进化系统
- `进化状态` — 查看 skill 进化统计
- `进化建议` — 查看系统生成的进化建议
- `进化 skill:{name}` — 触发特定 skill 的进化

### 知识库
- `搜索 {query}` — 搜索知识库
- `记住 {content}` — 写入知识库
- `知识库` — 列出知识库条目

## 指令识别规则

解析用户消息时，按以下优先级匹配：

1. **精确指令** — 以"创建skill"、"列出skill"等关键词开头
2. **@agent 指令** — "@researcher 搜索 RL 最新论文" → agent 名称 + 任务
3. **自然语言** — 不匹配任何指令时，作为普通对话处理

## 响应格式

飞书消息用 Markdown 格式：
- ✅ 成功 / ❌ 失败 / ⚠️ 警告
- 列表用表格
- 代码用 code block
- 重要信息加粗

## 创建 Skill 的流程

当收到 `创建skill {name}` 时：

1. **确认描述** — 如果用户没提供描述，主动问：
   "你想让这个 skill 做什么？简单描述一下"
2. **生成 SKILL.md** — 按标准格式创建：
   ```yaml
   ---
   name: {name}
   description: {description}
   version: 1.0.0
   metadata:
     hermes:
       tags: [{auto_tags}]
     evolution:
       use_count: 0
       last_used: ""
       success_rate: 0.0
       auto_evolve: true
   ---
   # {name}
   {instructions}
   ```
3. **保存到 shared-skills/** — `agents/shared-skills/{name}/SKILL.md`
4. **通知用户** — "✅ Skill `{name}` 已创建！发 `测试skill {name}` 试试"

## Agent 任务分发

当收到 `@agent-name 任务描述` 时：

1. **识别 agent** — 匹配 agent-registry 中的定义
2. **加载 agent 的 SOUL.md** — 理解 agent 能力边界
3. **分配 skill** — 从 agent 配置的 skill 列表中选合适的
4. **执行任务** — 使用 delegate_task 交给子 agent
5. **记录结果** — 写入 memory/runtime/ 并记录到进化 DB

## 文件路径

- 共享 skill: `agents/shared-skills/{name}/SKILL.md`
- Agent 定义: `agents/agent-registry/{name}/SOUL.md`
- 运行时状态: `agents/memory/runtime/`
- 进化数据: `agents/memory/evolution/evolution.db`
- 知识库: `agents/knowledge/`
