---
name: code-review
description: 代码审查 — 安全、性能、可维护性三维检查
version: 1.0.0
metadata:
  hermes:
    tags: [review, quality, security, performance]
    related_skills: [tdd, debugging, security-check]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# 代码审查

## 审查维度

### 🔴 Critical（必须修复）
- 安全漏洞（SQL 注入、XSS、命令注入）
- 数据丢失风险
- 并发问题（race condition）
- 认证/授权绕过

### 🟡 Warning（建议修复）
- 性能问题（N+1 查询、内存泄漏）
- 错误处理不完整
- API 兼容性破坏
- 可维护性问题（魔法数字、过长函数）

### 🟢 Info（可选优化）
- 代码风格
- 命名改进
- 文档补充
- 测试覆盖

## 步骤

1. **获取 diff** — `git diff` 或读取变更文件
2. **逐文件审查**
   - 先看变更意图（commit message / PR description）
   - 逐行检查，标记问题
3. **运行静态检查**（如果有工具）
4. **输出审查报告**
   ```
   ## Code Review: {files_changed}
   
   ### Summary
   整体评价...
   
   ### Issues
   - 🔴 `file.py:42` — 具体问题 → 建议修复方式
   - 🟡 `file.py:88` — 具体问题
   
   ### Positive
   - 做得好的地方
   ```
5. **记录到 skill_evolution** — 如果发现新模式

## 原则
- 提供建议而非命令
- 解释为什么，不只是说"改成 X"
- 认可好的代码
