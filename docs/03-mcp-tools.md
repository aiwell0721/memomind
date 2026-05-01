# MCP Server 工具列表

> 最后更新：2026-05-01

MemoMind MCP Server 提供 **20 个工具**，供 AI Agent（Claude Desktop、OpenClaw 等）调用。

## 启动方式

```bash
# stdio 模式（本地，用于 Claude Desktop、OpenClaw）
python -m mcp_server --db memomind.db

# HTTP 模式（网络访问）
python -m mcp_server --db memomind.db --transport http --port 8001
```

---

## 笔记工具（5 个）

### `create_note`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 笔记标题 |
| `content` | string | ✅ | 笔记内容（支持 Markdown） |
| `tags` | string[] | 否 | 标签列表 |

返回创建的笔记 JSON。

### `get_note`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `note_id` | int | ✅ | 笔记 ID |

返回笔记完整内容、标签和元数据。

### `update_note`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `note_id` | int | ✅ | 笔记 ID |
| `title` | string | 否 | 新标题 |
| `content` | string | 否 | 新内容 |
| `tags` | string[] | 否 | 新标签列表 |

更新笔记，仅更新指定的字段。

### `delete_note`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `note_id` | int | ✅ | 笔记 ID |

永久删除笔记。

### `list_notes`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | int | 否 | 返回数量（默认 20） |
| `offset` | int | 否 | 偏移量（默认 0） |

返回按更新时间排序的笔记列表。

---

## 搜索工具（2 个）

### `search_notes`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 搜索关键词 |
| `limit` | int | 否 | 返回数量（默认 10） |

基于 FTS5 全文搜索 + BM25 排序。

### `suggest_search`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 部分搜索词 |
| `limit` | int | 否 | 返回数量（默认 5） |

搜索建议（自动补全）。

---

## 标签工具（3 个）

### `list_tags`

返回标签树结构。

### `create_tag`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 标签名称 |
| `parent_id` | int | 否 | 父标签 ID（层级标签） |

### `add_tag_to_note`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `note_id` | int | ✅ | 笔记 ID |
| `tag_id` | int | ✅ | 标签 ID |

---

## 链接工具（2 个）

### `get_links`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `note_id` | int | ✅ | 笔记 ID |

返回笔记的出链和入链。

### `get_orphaned_notes`

返回没有链接关系的孤立笔记列表。

---

## RAG 工具（2 个）

### `ask_question`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | ✅ | 问题 |
| `top_k` | int | 否 | 参考笔记数量（默认 3） |

基于笔记库的 RAG 智能问答，返回答案 + 来源 + 置信度。

### `get_suggested_questions`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `note_id` | int | ✅ | 笔记 ID |
| `limit` | int | 否 | 返回数量（默认 5） |

根据笔记内容生成推荐问题。

---

## 摘要工具（1 个）

### `summarize_note`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `note_id` | int | ✅ | 笔记 ID |
| `max_length` | int | 否 | 摘要最大长度（默认 200） |

自动为长笔记生成摘要。

---

## 工作区工具（2 个）

### `list_workspaces`

返回所有工作区及其笔记数量。

### `create_workspace`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 工作区名称 |
| `description` | string | 否 | 工作区描述 |

---

## 导出工具（1 个）

### `export_notes`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `format` | string | 否 | 导出格式：`json` 或 `markdown`（默认 `json`） |
| `note_id` | int | 否 | 指定笔记 ID，不指定则导出全部 |

---

## 导入工具（1 个）

### `import_notes_from_json`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `json_content` | string | ✅ | JSON 格式的笔记内容 |
| `strategy` | string | 否 | 导入策略：`overwrite` 或 `merge`（默认 `overwrite`） |

---

## 活动工具（1 个）

### `get_activity`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | int | 否 | 返回数量（默认 20） |
| `action` | string | 否 | 过滤操作类型（create/update/delete/tag） |

返回最近活动日志。
