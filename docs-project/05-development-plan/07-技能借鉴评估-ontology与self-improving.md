# 技能借鉴评估（二）：ontology 与 self-improving

> 所属类别：第 5 类 - 开发计划
> 创建日期：2026-08-14
> 状态：已决策（对应 DEC-014）

## 1. 背景

延续 [06-llm-wiki借鉴评估与演进计划](./06-llm-wiki借鉴评估与演进计划.md)，扫描 `.workbuddy/skills/` 下全部 16 个技能，识别出 **ontology**（类型化知识图谱）与 **self-improving**（自我改进记忆）两个对 MemoMind 有真实借鉴价值的技能。经头脑风暴讨论，结论如下：

- ontology → 借鉴「关系类型 + `supersedes` 替代语义」，但**采用轻量表**，不照搬重约束
- self-improving → 借鉴「晋升/降级规则」，但**维持 Skills 闭环观察项**，仅作未来参考

其余技能（summarize 外部 CLI、github/humanizer 工具封装、爬虫类）无借鉴意义。

## 2. ontology 借鉴（补 P3 交叉引用，轻量化）

### 2.1 现状与缺口

MemoMind 的 `KnowledgeGraphService.build_graph()` 仅动态计算**相似度边**（Jaccard > 0.6），无类型化关系。架构文档 02 定义了 `RelationType` 但**从未实现**。

### 2.2 决策：supersedes 替代为主，contradicts 为辅

**头脑风暴结论**：个人笔记中的"矛盾"大多数是**知识演进**（改主意），不是"两个都对"的冲突。因此：

- **`supersedes`（替代）为主导关系**：新笔记替代旧笔记，旧笔记归档 + 记替代关系，保留时间线追溯。
- **`contradicts`（矛盾）仅限少数场景**：确实两难、需人工裁决时才用。

这修正了初版草稿中「contradicts 并存标记」的倾向。

### 2.3 决策：轻量 note_links 表，不照搬重约束

**头脑风暴结论**：ontology 的完整约束系统（`cardinality`/`required`/`enum`/`forbidden`/`acyclic`）是为**多 Agent 共享状态**设计，个人工具不需要。

采用轻量表：

```sql
CREATE TABLE note_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,     -- 发起方（新笔记）
    target_id INTEGER NOT NULL,     -- 指向方（旧笔记）
    link_type TEXT NOT NULL,        -- 'supersedes' | 'contradicts' | 'references' | 'related'
    strength REAL,                  -- 强弱（可选，如相似度）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**唯一保留的护栏**：备注 `parent_id` 的循环引用检查（`acyclic`），这是真能引发死循环 bug 的约束，非投机。

### 2.4 落地要点

| 项 | 内容 |
|----|------|
| 数据模型 | 新增轻量 `note_links` 表（见上） |
| 关系写入 | Dreaming 合并时，被合并笔记 → 合并笔记，记 `supersedes` 边 |
| 关系暴露 | Lint 报告暴露 `contradicts` 供用户裁决（并入 P1） |
| 约束 | 仅备注 `parent_id` 循环检查，其余不做重校验 |

## 3. self-improving 借鉴（Skills 闭环，维持观察）

### 3.1 现状与缺口

roadmap 的「Skills 模式识别」「Skills 自动进化」为 ⏸️ 观察项，依赖 ActivityLog 埋点 + `PatternDetector`，启动门槛为「30 天 ≥3 个高频模式（各 ≥5 次）」。

### 3.2 决策：维持观察项，规则仅作未来参考

**头脑风暴结论**：当前数据量少，单人 30 天数据稀疏，`PatternDetector` 大概率空转。**维持 ⏸️ 观察项，不启动开发。**

self-improving 的晋升/降级规则作为**未来参考**记录，待数据达标后直接复用：

| 规则 | 阈值 |
|------|------|
| 晋升 HOT | 模式 7 天内重复 ≥3 次 |
| 降级 WARM | 30 天未使用 |
| 归档 COLD | 90 天未使用 |

### 3.3 关键辨析

self-improving 的 HOT/WARM/COLD 是**按访问频率的冷热存储分层**，非架构文档 02 被 DEC-007 取消的「记忆类型」三层，两者不冲突——候选技能存储可借鉴冷热分层，而非复活三层类型。

## 4. 演进计划更新

| 优先级 | 项 | 内容 | 状态 |
|--------|-----|------|------|
| P3 | `note_links` 轻量表 | `supersedes` 主导 + `contradicts` 辅助 + `references`/`related` | 待实施 |
| P3 | Dreaming 记 `supersedes` 边 | 合并时被合并笔记 → 合并笔记记替代关系 | 待实施 |
| P1 | Lint 暴露矛盾 | `contradicts` 边纳入统一健康报告 | 待实施 |
| 观察项 | Skills 闭环 | 维持 ⏸️，self-improving 阈值作未来参考 | 不启动 |

## 5. 关联文档

- 决策日志：`docs-project/02-business-logic/01-决策日志.md`（DEC-014）
- 前置评估：`docs-project/05-development-plan/06-llm-wiki借鉴评估与演进计划.md`
- 知识图谱方案：`docs-project/05-development-plan/03-知识图谱连通与去重消化方案.md`
- 记忆系统增强设计：`docs-project/03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md`
