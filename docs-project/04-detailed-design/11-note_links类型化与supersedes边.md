# note_links 类型化与 supersedes 边详细设计

> 所属类别：第 4 类 - 详细设计
> 创建日期：2026-08-15
> 状态：待实现

## 1. 背景与目标

P3 落地：给笔记关系增加类型语义，并让 Dreaming 合并时记录「替代」关系（supersedes 边），使合并笔记可追溯它替代了哪些旧笔记。

对应开发计划 [07-技能借鉴评估-ontology与self-improving](../05-development-plan/07-技能借鉴评估-ontology与self-improving.md) 的 P3 项。

## 2. 现状修正

`note_links` 表**已存在**（`LinkService` 维护的 Wiki 双向链接 `[[标题]]`），当前 schema：

```sql
CREATE TABLE note_links (
    source_note_id INTEGER NOT NULL,
    target_note_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_note_id, target_note_id)
)
```

**修正 07 文档的理想化设计**：不是新建 `note_links(source_id, target_id, link_type, strength)`，而是**扩展现有表**，保持字段名 `source_note_id/target_note_id`。

## 3. 设计决策

| 决策点 | 结论 |
|--------|------|
| 扩展方式 | `ALTER TABLE note_links ADD COLUMN link_type TEXT NOT NULL DEFAULT 'reference'` |
| 默认类型 | `'reference'`（现有 Wiki 双向链接的语义） |
| supersedes 方向 | 合并笔记（新）→ 被合并笔记（旧），`link_type='supersedes'` |
| 范围 | 仅做 link_type 扩展 + Dreaming 记 supersedes 边；`contradicts`/`related` 留待后续 |

## 4. 实现要点

### 4.1 `LinkService._init_schema`

CREATE TABLE 加 `link_type` 字段（默认 `'reference'`），并加 ALTER 迁移（旧库补字段）。

### 4.2 `DreamingService.merge_cluster`

归档原始笔记后，为每个被合并笔记记 supersedes 边：

```python
# 记 supersedes 边：合并笔记替代被合并笔记
for nid in source_ids:
    self.db.execute(
        "INSERT OR IGNORE INTO note_links (source_note_id, target_note_id, link_type) "
        "VALUES (?, ?, 'supersedes')",
        (merged_id, nid)
    )
```

用 `INSERT OR IGNORE` 避免重复边；`note_links` 表不存在时 try/except 容错（与项目现有容错风格一致）。

## 5. 范围边界

- **本次不做**：`contradicts`（矛盾）边、`related` 边、`strength` 字段、Lint 暴露 supersedes 关系。
- **注意**：`note_links` 表由 `LinkService` 初始化，CLI `dream` 命令若不先初始化 LinkService，记边会因表不存在而静默跳过（不阻塞 dreaming）。Web UI 场景（api_server 初始化 LinkService）完整工作。

## 6. 测试策略

| 测试 | 验证 |
|------|------|
| link_type 字段存在 | note_links 表含 link_type 列，默认 'reference' |
| merge_cluster 记 supersedes 边 | 合并后 note_links 有 merged_id→source_id 的 supersedes 边 |
| 单元素簇不记边 | len(cluster)==1 时无 supersedes 边 |

测试命令：`python -m pytest tests/test_link_service.py tests/test_dreaming_service.py -v --tb=short`

## 7. 关联文档

- 借鉴评估：`../05-development-plan/07-技能借鉴评估-ontology与self-improving.md`（P3）
- 知识图谱方案：`../05-development-plan/03-知识图谱连通与去重消化方案.md`
