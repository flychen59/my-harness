---
name: planning
description: 任务规划和拆分 — 将复杂需求拆解为可执行的子任务
version: 1.0.0
metadata:
  hermes:
    tags: [planning, task-management, coordination]
    related_skills: [task-split, progress-track]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# 任务规划

## 步骤

1. **理解需求**
   - 用户想要什么？
   - 有什么约束？
   - 期望什么输出？

2. **拆分为子任务**
   ```
   ## Plan: {title}
   
   ### Task 1: {name} → @researcher
   - 目标: ...
   - 输出: ...
   - 验证: ...
   
   ### Task 2: {name} → @coder  
   - 依赖: Task 1
   - 目标: ...
   - 输出: ...
   - 验证: ...
   
   ### Task 3: {name} → @reviewer
   - 依赖: Task 2
   - 目标: 审查 Task 2 输出
   - 输出: 审查报告
   ```

3. **评估可行性**
   - 每个任务 2-5 分钟可完成？
   - 依赖关系清晰？
   - 有回退方案？

4. **写入任务队列** — `memory/runtime/task-queue.md`

## 分配规则
- 调研/搜索 → @researcher
- 编码/实现 → @coder
- 审查/检查 → @reviewer
- 不确定 → @coordinator 先分析

## 原则
- 每个任务只做一件事
- 明确输入和输出
- 验证步骤不可省
