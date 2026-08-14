# lint 知识健康报告详细设计

> 所属类别：第 4 类 - 详细设计
> 创建日期：2026-08-15
> 状态：待实现

## 1. 背景与目标

整合 MemoMind 已有的知识健康检测能力（重复、陈旧）与图谱孤儿节点，收敛为一个统一的 `lint_knowledge()` 报告，输出四类建议：**该合并 / 该更新 / 该补链接 / 该删**。

对应开发计划 [06-llm-wiki借鉴评估与演进计划](../05-development-plan/06-llm-wiki借鉴评估与演进计划.md) 的 P1 项。

## 2. 设计决策

经头脑风暴对齐，确定：

| 决策点 | 结论 |
|--------|------|
| 位置 | `KnowledgeGraphService` 加 `lint_knowledge()` 方法，复用已有能力，不引入新依赖 |
| 去重来源 | 复用 `suggest_consolidation` 的 `merge_suggestions`（Jaccard）；**不并入** `scan_duplicates`（TF-IDF 保留独立 MCP 工具） |
| 删除判定 | `delete` = 孤儿节点 + 陈旧（既孤立又长期未更新） |

## 3. 四类建议判定标准

| 类别 | 语义 | 判定 | 数据来源 |
|------|------|------|----------|
| `merge` | 该合并 | 内容 Jaccard 相似度 ≥ 阈值 | `suggest_consolidation.merge_suggestions` |
| `update` | 该更新 | `updated_at` 距今 > 天数阈值 | `suggest_consolidation.stale_candidates` |
| `link` | 该补链接 | 图谱孤儿节点（无任何边相连） | `build_graph` 新算：非 source 也非 target 的节点 |
| `delete` | 该删 | 孤儿节点 **且** 陈旧 | `link` 与 `update` 的交集 |

## 4. 返回结构

```python
{
    'merge':  [{'note_ids': [1, 2], 'similarity': 0.85}, ...],
    'update': [{'note_id': 3, 'title': '...', 'days_since_update': 120}, ...],
    'link':   [{'note_id': 4, 'title': '...'}, ...],
    'delete': [{'note_id': 5, 'title': '...'}, ...],
}
```

## 5. 实现要点

```python
def lint_knowledge(
    self,
    workspace_id: Optional[int] = None,
    days_threshold: int = 90,
    similarity_threshold: float = 0.6,
    max_nodes: int = 100,
) -> Dict:
    graph = self.build_graph(workspace_id=workspace_id, max_nodes=max_nodes)
    if not graph['nodes']:
        return {'merge': [], 'update': [], 'link': [], 'delete': []}

    # 孤儿节点：既非 source 也非 target
    connected = set()
    for edge in graph['edges']:
        connected.add(edge['source'])
        connected.add(edge['target'])
    orphans = [n for n in graph['nodes'] if n['id'] not in connected]

    # 复用 suggest_consolidation 拿 merge + stale
    suggestions = self.suggest_consolidation(...)

    # delete = 孤儿 ∩ 陈旧
    stale_ids = {s['note_id'] for s in suggestions['stale_candidates']}
    ...
```

**取舍**：`lint_knowledge` 内部会两次调用 `build_graph`（一次算孤儿，一次在 `suggest_consolidation` 内），数据量 ≤ `max_nodes` 时开销可接受，不为此重构 `suggest_consolidation`。

## 6. 测试策略

| 测试 | 验证 |
|------|------|
| 方法存在 + 返回四 key | `lint_knowledge` 返回 `merge/update/link/delete` |
| 孤儿节点检测 | 无任何 tag/相似度的孤立笔记进入 `link` |
| 陈旧检测 | `updated_at` 很老的笔记进入 `update` |
| 删除候选 | 孤儿且陈旧的笔记进入 `delete` |
| 合并检测 | 高相似笔记进入 `merge` |
| 空库 | 返回空四类 |

测试命令：`python -m pytest tests/test_knowledge_graph_service.py -v --tb=short`

## 7. 关联文档

- 开发计划：`../05-development-plan/06-llm-wiki借鉴评估与演进计划.md`（P1）
- 借鉴评估：`../05-development-plan/07-技能借鉴评估-ontology与self-improving.md`
