# MemoMind API 参考文档

## 📖 概述

MemoMind 提供统一的 Python SDK，包含以下模块：

- `NotesAPI` - 笔记 CRUD 和搜索
- `TagsAPI` - 标签管理
- `LinksAPI` - 双向链接管理
- `VersionsAPI` - 版本历史管理
- `ExportService` - 导出功能
- `ImportService` - 导入功能

---

## 🚀 快速开始

```python
from memomind import MemoMind

# 初始化客户端
client = MemoMind(db_path="~/memomind.db")

# 使用上下文管理器
with MemoMind(db_path="~/memomind.db") as client:
    # 你的操作
    pass
```

---

## 📝 NotesAPI

### 创建笔记

```python
note_id = client.notes.create(
    title="笔记标题",
    content="笔记内容",
    tags=["标签 1", "标签 2"]
)
```

### 获取笔记

```python
note = client.notes.get(note_id=1)
# 返回：{'id': 1, 'title': '...', 'content': '...', 'tags': [...], ...}
```

### 更新笔记

```python
client.notes.update(
    note_id=1,
    title="新标题",
    content="新内容",
    tags=["新标签"]
)
```

### 删除笔记

```python
client.notes.delete(note_id=1)
```

### 搜索笔记

```python
results = client.notes.search(
    query="关键词",
    tags=["标签"],  # 可选
    limit=20
)
```

### 列出笔记

```python
notes = client.notes.list(limit=100, offset=0)
```

---

## 🏷️ TagsAPI

### 创建标签

```python
tag_id = client.tags.create("标签名", parent_id=None)
```

### 获取标签

```python
tag = client.tags.get(tag_id=1)
```

### 列出标签

```python
tags = client.tags.list()
```

### 获取标签树

```python
tree = client.tags.get_tree()
# 返回：[{'id': 1, 'name': '...', 'children': [...]}]
```

### 删除标签

```python
client.tags.delete(tag_id=1)
```

### 标签建议

```python
suggestions = client.tags.suggest("前缀", limit=10)
```

---

## 🔗 LinksAPI

### 创建链接

```python
client.links.create(source_id=1, target_id=2)
```

### 获取出链

```python
outgoing = client.links.get_outgoing(note_id=1)
```

### 获取入链（反向链接）

```python
incoming = client.links.get_incoming(note_id=2)
```

### 获取链接图谱

```python
graph = client.links.get_graph()
# 返回：{'nodes': [...], 'links': [...]}
```

### 获取断链

```python
broken = client.links.get_broken()
```

### 获取孤立笔记

```python
orphaned = client.links.get_orphaned()
```

---

## 📜 VersionsAPI

### 保存版本

```python
version_id = client.versions.save(
    note_id=1,
    title="标题",
    content="内容",
    tags=["标签"],
    change_summary="变更说明"
)
```

### 获取版本详情

```python
version = client.versions.get(version_id=1)
```

### 列出版本

```python
versions = client.versions.list(note_id=1, limit=10)
```

### 恢复版本

```python
result = client.versions.restore(version_id=1)
```

### 标记版本

```python
client.versions.tag(version_id=1, tag_name="重要版本")
```

### 清理旧版本

```python
deleted = client.versions.cleanup(note_id=1, keep_count=10)
```

---

## 📤 ExportService

### 导出为 Markdown

```python
files = client.export.export_all_to_markdown_files(
    output_dir="./output",
    include_versions=False
)
```

### 导出为 JSON

```python
output_file = client.export.export_all_to_json(
    output_path="./backup.json",
    include_versions=False
)
```

---

## 📥 ImportService

### 从 Markdown 导入

```python
result = client.importer.import_markdown_directory(
    dirpath="./notes",
    conflict_policy="skip"  # skip/overwrite/merge
)
```

### 从 JSON 导入

```python
result = client.importer.import_json_file(
    filepath="./backup.json",
    conflict_policy="skip"
)
```

---

## 📊 数据模型

### Note

```python
{
    'id': int,
    'title': str,
    'content': str,
    'tags': List[str],
    'created_at': str,
    'updated_at': str
}
```

### Tag

```python
{
    'id': int,
    'name': str,
    'parent_id': Optional[int],
    'note_count': int
}
```

### NoteLink

```python
{
    'source_note_id': int,
    'source_title': str,
    'target_note_id': int,
    'target_title': str
}
```

### Version

```python
{
    'id': int,
    'note_id': int,
    'version_number': int,
    'title': str,
    'content': str,
    'tags': List[str],
    'created_at': str,
    'change_summary': Optional[str],
    'is_tagged': bool,
    'tag_name': Optional[str]
}
```

---

*需要更多帮助？查看 [快速开始指南](quick-start.md) 或 [CLI 参考](cli-reference.md)*
