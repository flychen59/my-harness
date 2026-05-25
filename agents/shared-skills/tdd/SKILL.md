---
name: tdd
description: 测试驱动开发 — RED-GREEN-REFACTOR 循环
version: 1.0.0
metadata:
  hermes:
    tags: [testing, tdd, development, quality]
    related_skills: [code-review, debugging]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# 测试驱动开发

## 强制规则
1. **先写测试** — 在写实现代码之前必须写测试
2. **看它失败** — 运行测试确认红色
3. **最小实现** — 写刚好让测试通过的代码
4. **重构** — 测试通过后再优化
5. **提交** — 每个 RED-GREEN-REFACTOR 循环完成后提交

## 步骤

1. **理解需求** — 从 plan 中获取当前 task
2. **写失败测试**
   ```python
   def test_{feature}_{scenario}():
       # Arrange
       # Act  
       # Assert
   ```
3. **运行确认失败** — `pytest tests/test_xxx.py -v`
4. **写最小实现** — 只让测试通过，不多写
5. **运行确认通过** — 绿色
6. **重构** — DRY、命名、提取
7. **再跑一次** — 确保没破

## 陷阱
- 不要跳过"看它失败"这一步
- 不要一次写多个测试
- 不要在测试还没通过时就重构
- 不要写测试之后又改测试来适应实现
