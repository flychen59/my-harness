# OpenClaw vs Hermes Agent 对比（2026年5月）

## 基本信息

| | OpenClaw | Hermes Agent |
|---|---|---|
| GitHub | openclaw/openclaw (374k ⭐) | NousResearch/hermes-agent (163k ⭐) |
| 语言 | TypeScript (Node.js) | Python |
| 赞助方 | OpenAI, GitHub, NVIDIA, Vercel | Nous Research |
| 标语 | "Your own personal AI assistant. Any OS. Any platform. The lobster way. 🦞" | "The agent that grows with you" |

## 核心差异

### OpenClaw 优势
- **渠道覆盖**: 22+ 平台（飞书、微信、QQ、iMessage、Teams、Matrix、LINE 等）+ macOS/iOS/Android 原生 App
- **Live Canvas**: agent 驱动的可视化工作空间，能渲染图表、看板、表单
- **Voice**: macOS/iOS 语音唤醒，Android 连续语音，ElevenLabs TTS
- **多 Agent 路由**: 不同渠道/账号/用户路由到隔离 agent
- **ClawHub 插件市场**
- **上手门槛低**: 不折腾就能跑

### Hermes Agent 优势
- **自我学习闭环**: 做完复杂任务自动创建 skill，skill 自我改进
- **记忆反馈循环**: 自动回顾整理记忆 + FTS5 session 搜索 + LLM 摘要
- **Honcho 用户建模**: 跨 session 构建持久用户模型
- **agentskills.io 标准**: skill 跨 agent 可移植
- **MCP 原生**: 40+ 内置工具 + RPC subagents
- **`hermes claw migrate`**: 内置 OpenClaw 迁移命令（竞争信号）

## 安全对比
- 两者都有 DM pairing、allowlist、sandbox、doctor 命令
- OpenClaw 2026年有 ClawHavoc 供应链攻击事件（ClawHub 插件市场）
- Hermes 有 MCP 认证绕过漏洞（v0.4.2 修复）
- 结论：都不是默认更安全，暴露在公网都需要严格配置

## 社区共识来源
- HN: 2645 条 OpenClaw 讨论 vs 976 条 Hermes 讨论
- DuckDuckGo: 10+ 篇专门对比文章
- 最佳对比文章: wanjohichristopher.com/blog/ai/hermes-vs-openclaw/ (2026-05-22)
- 社区普遍认为：OpenClaw 胜在体验和覆盖面，Hermes 胜在学习能力和深度

## 用户的实际感受
用户同时使用两者，认为 OpenClaw 在交互和 memory 上体验更好。
Hermes memory 有实际 bug（session_search 摘要不完整、连续消息丢失）。
