---
name: paper-summary
description: 论文精读和总结，提取核心贡献、方法、实验结果
version: 1.0.0
metadata:
  hermes:
    tags: [research, papers, summary, reading]
    related_skills: [arxiv-search]
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# 论文精读总结

## 使用场景
- 快速理解一篇论文的核心内容
- 提取方法、实验、贡献
- 与其他论文对比

## 步骤

1. **获取论文** — 
   - 有 PDF：用 OCR 或 vision_analyze 读取
   - 有 arXiv ID：先获取 HTML 版本（ar5iv.org）
   - 只有标题：先搜索再获取

2. **结构化提取**
   ```
   ## {title}
   
   ### 核心贡献（1-3 句话）
   
   ### 方法
   - 输入 → 处理 → 输出的完整流程
   - 关键创新点
   
   ### 实验
   - 数据集和指标
   - 主要结果（表格形式）
   - 消融实验的关键发现
   
   ### 局限性
   
   ### 与我们工作的关联
   ```

3. **深度分析**（如果用户需要）
   - 代码实现细节
   - 可复现性评估
   - 与已有方法的对比

4. **写入知识库** — 重要论文写入 `knowledge/papers/`

## 输出语言
- 默认中文输出
- 保留英文专业术语
- 公式用 LaTeX 格式
