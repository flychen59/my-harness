---
name: arxiv-search
description: 搜索和获取 arXiv 论文，支持关键词、作者、领域筛选
version: 1.0.0
metadata:
  hermes:
    tags: [research, papers, arxiv, academic]
    related_skills: [paper-summary, web-research]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# arXiv 论文搜索

## 使用场景
- 搜索特定方向的最新论文
- 按关键词/作者/时间范围筛选
- 获取论文摘要和关键信息

## 步骤

1. **解析查询** — 从用户消息中提取：
   - 关键词（英文为主）
   - 时间范围（默认最近 30 天）
   - 领域（cs.AI, cs.CL, cs.CV 等）
   - 最大返回数（默认 10）

2. **构建搜索 URL**
   ```
   https://arxiv.org/search/?query={keywords}&searchtype=all&start=0&order=-announced_date_first
   ```

3. **抓取结果** — 使用 browser 工具：
   - 导航到搜索页
   - 提取论文列表（标题、作者、日期、arXiv ID、摘要）
   - 过滤时间范围

4. **格式化输出**
   ```
   📄 **{title}**
   Authors: {authors}
   Date: {date} | ID: {arxiv_id}
   {abstract_truncated}
   [Link](https://arxiv.org/abs/{arxiv_id})
   ---
   ```

5. **记录使用** — 调用 skill_evolution.record_usage()

## 常见问题
- 如果搜索结果为空，扩大时间范围或换关键词
- 优先返回有代码仓库的论文（看摘要中是否有 GitHub 链接）
- 用户要求翻译时用中文输出标题和摘要
