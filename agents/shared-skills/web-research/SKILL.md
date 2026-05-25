---
name: web-research
description: 通用网络调研，搜索技术方案、API 文档、最佳实践
version: 1.0.0
metadata:
  hermes:
    tags: [research, web, search, documentation]
    related_skills: [arxiv-search, paper-summary]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# 网络调研

## 参考文件
- `references/browser-automation-tools.md` — 网页浏览器自动化工具调研（Playwright/Browser Use/Selenium/CloakBrowser 等），含反爬虫方案推荐策略
- `references/agent-orchestration-frameworks.md` — Agent 编排框架调研（Open Multi-Agent/CrewAI/GPT Researcher/ValueCell 等），含推荐架构
- `references/openclaw-vs-hermes-agent.md` — OpenClaw vs Hermes Agent 对比研究（2026-05），含社区评价、核心差异、安全对比

## 使用场景
- 调研技术方案和 API
- 搜索开源项目
- 查找文档和最佳实践

## 步骤

1. **明确调研目标** — 从用户消息提取：
   - 调研主题
   - 期望输出（列表/对比/教程）
   - 时效性要求

2. **多源搜索**
   - GitHub（项目、star 数、活跃度）
   - 官方文档（API reference）
   - 技术博客（实现细节）
   - Stack Overflow（常见问题）

3. **信息提取**
   - 每个来源提取关键信息
   - 对比不同方案的优劣
   - 注意时效性（标注日期）

4. **结构化输出**
   ```
   ## 调研结果：{topic}
   
   ### 方案对比
   | 方案 | 优势 | 劣势 | 适用场景 |
   
   ### 推荐
   基于分析推荐...
   
   ### 参考
   - [来源1](url)
   ```

5. **知识入库** — 重要发现写入 `knowledge/` 目录

## 搜索渠道优先级（实测可用）

### ✅ 高成功率
1. **GitHub API** `api.github.com/search/repositories?q=...` — 搜项目、star 数、描述。注意：未认证限制 60次/小时，超过会 403。用 `gh api` 替代 curl 可走认证提额。
2. **Hacker News Algolia** `hn.algolia.com/api/v1/search?query=...&tags=story|comment` — 无需认证，返回 JSON，评论搜索特别好使。搜 `tags=comment` 可找到讨论中的具体观点。items API 返回大 JSON 时可能需要 `strict=False` 解析。
3. **DuckDuckGo HTML** `html.duckduckgo.com/html/?q=...` — 不需要 API key，返回 HTML 可正则提取结果。Google/Bing 经常返回空（JS 渲染或被 block）。
4. **直接抓博客/文章** `curl -sL` + strip HTML — 对已知 URL 的全文抓取很靠谱。

### ❌ 低成功率
- **Reddit JSON API** (`reddit.com/search.json`) — 被 block，需要 OAuth 认证
- **Google 搜索** — curl 方式基本返回空结果（JS 渲染 + 反爬）
- **小红书/知乎** — 需要登录或 JS 渲染，curl 抓不到内容

### 多关键词组合技巧
- 对比类搜索：`A vs B comparison` 或 `A vs B 对比`（中英文都搜）
- HN 评论中同时提到两个项目：`tags=comment` + 两个关键词
- GitHub 搜索：`q=openclaw&sort=stars` 按 star 排序

## 陷阱
- 不要只看第一页结果
- 注意文章发布日期，避免过时信息
- GitHub 项目看 last commit 时间和 issue 活跃度
- GitHub API 未认证会限流（每小时60次），大量搜索时优先用 `gh api`
- JSON 解析大响应时可能遇到控制字符，用 `json.loads(text, strict=False)` 或分段处理
- delegate_task 的 web 搜索工具经常返回空结果，重要搜索直接用 terminal + curl
- DuckDuckGo 结果 URL 是重定向链接（`//duckduckgo.com/l/?uddg=...`），需要 URL decode 提取真实地址

## 用户要求"帮我找/做"时的行为准则
当用户说"帮我找工作""帮我找兼职"等需要行动的结果时：
- **不要只列平台和链接**——这是调研输出，不是用户要的
- **先判断哪些步骤我能代劳**（准备材料、写简介、筛选匹配项），**哪些必须用户自己做**（注册、实名认证、手机验证）
- **主动提出帮用户准备可操作的材料**——个人简介文案、筛选后的具体任务列表、注册步骤清单
- **一次说清楚哪些我能做哪些不能做**，别让用户反复追问才能得到下一步
