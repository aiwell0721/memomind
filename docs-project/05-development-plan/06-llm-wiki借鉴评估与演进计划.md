# llm-wiki 借鉴评估与演进计划

> 所属类别：第 5 类 - 开发计划
> 创建日期：2026-08-14
> 状态：已决策（对应 DEC-013）

## 1. 背景

对标对象 `llm-wiki`（Karpathy LLM Wiki，marketplace 技能）提出了一套"LLM 增量维护个人知识库"的方法论，核心理念是**用持久化编译替代 RAG 检索**——LLM 读源文档 → 增量写 wiki → 维护交叉引用 → 健康检查。

本评估的目标：筛出对 MemoMind 有**真实增量价值**的机制，明确哪些不适用（YAGNI），并排定演进优先级。

## 2. 评估结论总览

| 机制 | 判定 | 优先级 | 理由 |
|------|------|--------|------|
| Query 回写（正和） | ✅ 借鉴 | P2 | 补上 MemoMind"记忆只减不增"的缺口 |
| Lint 健康检查 | ✅ 借鉴 | P1 | 已有 scan_duplicates / stale_candidates 雏形，收拢成统一报告 |
| 显式交叉引用持久化 | ✅ 借鉴 | P3 | Phase 2 知识图谱增强的具体化 |
| 归档物理隔离 | ✅ 借鉴 | P0 | 修复 rollback 靠字符串切割的脆弱性（bug） |
| 纯 markdown + git 存储 | ❌ 不借 | — | 架构倒退，SQLite+FTS5 已更优 |
| index.md / log.md 文件化 | ❌ 不借 | — | dreaming_sessions/changes 表 + ActivityLog 已覆盖 |
| WIKI-SCHEMA.md 协同演化 | ❌ 不借 | — | CLAUDE.md + docs-project 文档体系已覆盖 |
| 一次 ingest 改 10-15 页广度模式 | ❌ 不借 | — | MemoMind 是单条笔记存储，非 wiki 多页结构 |
| frontmatter 完整元数据 | ⚠️ 部分借 | P3 | 仅缺"溯源"一项，已在 tags/ai_summary/type 之外补齐 |

## 3. 详细借鉴点

### 3.1 P2 — Query 回写（半自动）

**llm-wiki 做法**：query 后把好答案"file back"成新页，知识库越用越富。

**MemoMind 现状**：Dreaming 是负和（N→1），检索/问答结果从不沉淀。

**方案**：检索/问答流程末尾，AI 提炼出"值得记住"的候选 → **用户确认** → 存为新笔记。半自动（AI 建议 + 用户确认），避免 AI 误判污染检索质量。

### 3.2 P1 — Lint 统一知识健康报告

**llm-wiki 做法**：巡检矛盾、过时声明、孤儿页、缺失交叉引用。

**MemoMind 现状**：已有两个独立 MCP 工具——`scan_duplicates()`（重复）与 `suggest_consolidation()` 的 `stale_candidates`（陈旧）。

**方案**：整合去重 + 陈旧 + 图谱孤儿节点（入度=0）为一个 `lint_knowledge()` 报告，输出"该合并 / 该更新 / 该补链接 / 该删"四类建议。

### 3.3 P3 — 显式交叉引用持久化

**llm-wiki 做法**：`[[wiki-links]]` + See Also 持久化显式图。

**MemoMind 现状**：`KnowledgeGraphService.build_graph()` 每次动态计算相似度边，不持久化；`parent_id` 仅表达备注层级。

**方案**：新增轻量 `note_links` 表（source_id, target_id, link_type, strength），支持 AI 压缩后维护"浓缩笔记 ← 源笔记"inbound links、Lint 查孤儿/悬空引用、检索沿链接扩展。对应 Phase 2"知识图谱增强"。

### 3.4 P0 — 归档物理隔离（本次落地）

见第 5 节。

## 4. 不借鉴清单（YAGNI）

| 机制 | 不借理由 |
|------|----------|
| 纯 markdown + git 存储 | 已选 SQLite+FTS5，重构是架构倒退 |
| index.md / log.md 文件化 | 已有结构化表 + ActivityLog，追溯优于 grep 文件 |
| WIKI-SCHEMA.md 协同演化 | 已有 CLAUDE.md + docs-project 文档体系 |
| 一次 ingest 改 10-15 页广度模式 | 单条笔记存储，非 wiki 多页结构 |

## 5. P0 归档物理隔离方案

### 5.1 问题

当前 `merge_cluster()` 归档方式是在原笔记 content 末尾追加字符串：

```python
UPDATE notes SET content = content || '\n\n[归档于 Dreaming: 已合并到 note#X]' WHERE id=?
```

`rollback()` 靠字符串切割还原：

```python
cleaned = content.split("\n\n[归档于 Dreaming:")[0]
```

**脆弱点**：用户手动编辑过被归档笔记的内容后，切割会错位，导致回滚失败或内容丢失。

### 5.2 目标方案

将归档状态从"正文字符串标记"改为"独立字段 `is_archived`"，回滚从"字符串手术"变为"字段翻转"。

### 5.3 改动清单

| # | 文件 | 函数/位置 | 改动 |
|---|------|-----------|------|
| 1 | `core/database.py` | `_init_db()` | notes 表加 `is_archived INTEGER DEFAULT 0`（迁移） |
| 2 | `core/dreaming_service.py` | `merge_cluster()` | 归档改为 `UPDATE notes SET is_archived=1 WHERE id=?`，不再追加字符串 |
| 3 | `core/dreaming_service.py` | `rollback()` | 恢复改为 `UPDATE notes SET is_archived=0 WHERE id=?`，不再切割字符串 |
| 4 | `core/dreaming_service.py` | `select_memories_for_dreaming()` / `_get_all_notes()` | SQL 加 `AND is_archived=0`，排除已归档笔记 |

### 5.4 验收标准

- 归档后的笔记 content 保持原样（无 `[归档于 Dreaming]` 标记）
- 回滚后原笔记 content 精确还原（即使归档后内容被编辑过）
- 已归档笔记不再被 `select_memories_for_dreaming` 重复选中
- 现有 `tests/test_dreaming_service.py` 全部通过

### 5.5 范围边界

- **本次不做**：搜索/笔记列表 API 排除 `is_archived=1` 笔记（归档笔记仍出现在搜索结果中，与当前字符串标记版本行为一致）。这是独立话题，纳入 P3 交叉引用一并处理。

## 6. 演进优先级

```
P0  归档隔离（is_archived 标志位）   ← 修 rollback 脆弱性，本次落地
P1  Lint 统一报告                    ← 收拢已有 scan_duplicates + stale_candidates
P2  Query 回写（半自动）             ← 补"正和"
P3  显式 note_links 表 + 溯源字段     ← Phase 2 知识图谱增强
```

## 7. 关联文档

- 决策日志：`docs-project/02-business-logic/01-决策日志.md`（DEC-013）
- 记忆系统增强设计：`docs-project/03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md`
- AI 压缩详细设计：`docs-project/04-detailed-design/08-AI压缩Dreaming详细设计.md`
- 知识图谱方案：`docs-project/05-development-plan/03-知识图谱连通与去重消化方案.md`
