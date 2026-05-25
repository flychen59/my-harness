# Agent 编排框架调研（2026年5月）

## 用户需求
深度加工工作（项目迭代进化）+ 灵活搜索调研 + 动态 Agent 编排 Workflow。

## 第一梯队：最匹配的项目

### Open Multi-Agent — ⭐6,234 — **最推荐**
- GitHub: open-multi-agent/open-multi-agent
- TypeScript（跟 OpenClaw 同栈！天然兼容）
- 核心：给一个 goal，自动拆成任务 DAG，独立任务并行跑，最后合成
- 三种模式：单 Agent / 自动编排团队(`runTeam()`) / 自定义 Pipeline(`runTasks()`)
- 支持 MCP 工具、流式输出、HTML Dashboard 看任务图
- 3 个运行时依赖，极轻量
- 10 个内置 LLM provider + OpenAI 兼容（Ollama/vLLM 等）
- 有中文 README

```typescript
const result = await orchestrator.runTeam(team,
  '调研最近三个月的AI Agent融资事件，生成分析报告')
// coordinator 自动拆成 DAG: 搜索→筛选→分析→报告
```

### CrewAI — ⭐52,061 — 社区最大
- GitHub: crewAIInc/crewAI
- Python，完全独立（不依赖 LangChain）
- 定义多个"角色"Agent，给任务，自动协作
- Crews（自主协作）+ Flows（企业级事件驱动编排）
- 10万+ 开发者认证

### GPT Researcher — ⭐27,256 — 深度调研专用
- GitHub: assafelovic/gpt-researcher
- 给主题自动搜索多源信息、整理、生成报告
- 专注"调研"这一个场景

## 第二梯队：行业垂直

### ValueCell — ⭐10,704 — 金融多 Agent
- GitHub: ValueCell-ai/valuecell
- 多 Agent 金融平台：选股、研报、跟踪、自动交易
- Agent 注册市场 + 社区生态
- 支持 Binance/OKX/Hyperliquid

### FinRobot — ⭐7,030 — 金融 AI Agent
- GitHub: AI4Finance-Foundation/FinRobot
- LLM + 强化学习 + 量化分析
- 股权研究、风险评估、算法交易

### OpenBB — ⭐68,018 — 金融数据
- GitHub: OpenBB-finance/OpenBB
- 金融数据平台（数据源整合，不是 Agent 编排）

## 第三梯队：通用编排

| 项目 | Stars | 定位 |
|---|---|---|
| Dify (langgenius/dify) | ~90k+ | LLM 工作流平台，拖拽式编排 |
| Hatchet (hatchet-dev/hatchet) | 7,208 | Go 编写的后台任务 + Agent 工作流引擎 |
| Haystack (deepset-ai/haystack) | 25,358 | AI 编排框架，RAG + Pipeline |
| Khoj (khoj-ai/khoj) | 34,689 | AI 第二大脑，调度 + 自动化 |
| ZenML (zenml-io/zenml) | 5,425 | ML Pipeline 到 Agent 的一站式平台 |

## 推荐架构（跟 OpenClaw 搭配）

```
OpenClaw（日常交互 + 多平台）
    │
    └── Open Multi-Agent（任务编排层）
          ├── Agent A: 搜索调研（GPT Researcher 思路）
          ├── Agent B: 深度分析（CrewAI 协作模式）
          └── Agent C: 金融方向（接 ValueCell）
```

选择 Open Multi-Agent 的理由：
1. TypeScript 跟 OpenClaw 同栈，天然兼容
2. "给目标自动生成 DAG" = 用户要的动态编排
3. 极轻量（3 个依赖），好集成
