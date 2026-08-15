# Query 回写半自动详细设计

> 所属类别：第 4 类 - 详细设计
> 创建日期：2026-08-15
> 状态：待实现

## 1. 背景与目标

借鉴 llm-wiki 的「Query 回写」——把有价值的问答结果沉淀为笔记，补上 MemoMind「记忆只减不增」的缺口。

**目标**：RAG 问答后，用 AI 把「问题 + 答案」提炼成候选笔记，用户确认后保存，实现半自动回写。

对应开发计划 [06-llm-wiki借鉴评估与演进计划](../05-development-plan/06-llm-wiki借鉴评估与演进计划.md) 的 P2 项。

## 2. 设计决策

经头脑风暴对齐，确定：

| 决策点 | 结论 |
|--------|------|
| 交互形式 | **CLI 首发**（`memomind ask` 后提示保存），Web/MCP 后续接入 |
| AI 提炼 | **云端 provider**（`create_provider()`，OpenAI/Anthropic） |
| 半自动语义 | AI 提炼候选 → 用户确认（AI 不判断"值不值得"，判断权留给用户） |

## 3. `suggest_note()` 设计

在 `RAGService` 新增方法，用 provider 将问答结果提炼为候选笔记：

```python
def suggest_note(self, question: str, answer: str) -> Optional[Dict]:
    """用 AI 将问答结果提炼为候选笔记（回写的"建议"环节）"""
    if not self.provider:
        return None
    # 复用 provider.answer()，结构化输出：第一行标题，其余为内容
    ...
    return {'title': ..., 'content': ...}
```

**行为约定**：

| 场景 | 返回 |
|------|------|
| provider 为 None（本地模式） | `None`（跳过回写） |
| provider 调用异常 | `None` |
| provider 返回空 | `None` |
| 标题为空 | 兜底用 `question[:50]` |
| 内容为空 | 兜底用 `answer` |

## 4. `cmd_ask` 改动

`cli.py` 的 `cmd_ask`：

1. 用 `create_provider()` 初始化云端 provider，传入 `RAGService(db, provider=provider)`
2. 问答后调 `suggest_note(question, answer)`
3. 若返回候选，打印「是否保存为笔记？」+ 候选标题，`input()` 确认
4. 用户确认（y）后 `INSERT INTO notes`，保存 title + content

## 5. 范围边界

- **本次不做**：Web UI 保存按钮、MCP 工具、自动打标签（tags 留空，后续用 auto_tag）。
- **本次不做**：AI 判断"值不值得记住"（那是全自动的语义，半自动由用户裁决）。

## 6. 测试策略

| 测试 | 验证 |
|------|------|
| provider 可用时返回候选 | Fake provider 返回结构化文本，解析出 title + content |
| provider 为 None | 返回 `None` |
| provider 异常 | 返回 `None` |
| provider 返回空 | 返回 `None` |
| 标题/内容兜底 | 空标题用 question，空内容用 answer |

测试命令：`python -m pytest tests/test_rag_service.py -v --tb=short`

## 7. 关联文档

- 开发计划：`../05-development-plan/06-llm-wiki借鉴评估与演进计划.md`（P2）
- 前置评估：`../05-development-plan/07-技能借鉴评估-ontology与self-improving.md`
