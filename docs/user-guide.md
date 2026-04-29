# MemoMind 用户手册

> 从零开始使用 MemoMind 构建你的 AI 知识库

---

## 📖 什么是 MemoMind？

MemoMind 是一个基于 SQLite 的本地 AI 知识库系统，提供：

- **全文搜索** - FTS5 索引，BM25 排序，毫秒级响应
- **中文分词** - jieba 集成，支持中英文混合搜索
- **标签分类** - 无限层级标签树，支持别名和合并
- **版本历史** - 自动保存，支持 diff 对比和恢复
- **双向链接** - Wiki 语法 `[[笔记标题]]`，反向链接追踪
- **导入导出** - Markdown 和 JSON 双格式备份

---

## 🚀 快速开始

### 安装

```bash
# 方式 1：从源码
git clone <your-repo>
cd memomind
pip install -r requirements.txt
pip install jieba

# 方式 2：Docker
docker-compose up -d
```

### 创建第一个笔记

```python
from api.client import MemoMind

client = MemoMind("my_knowledge.db")

# 创建笔记
note_id = client.notes.create(
    title="AI 基础概念",
    content="人工智能是计算机科学的一个分支...",
    tags=["AI", "技术", "入门"]
)
print(f"笔记已创建，ID: {note_id}")
```

### 搜索笔记

```python
# 全文搜索
results = client.notes.search("人工智能")
for r in results:
    print(f"📝 {r['note']['title']} (相关度: {r['score']:.2f})")

# 标签过滤
results = client.notes.search("AI", tags=["技术"])
```

---

## 📚 核心功能详解

### 1. 笔记管理

#### 创建笔记

```python
note_id = client.notes.create(
    title="笔记标题",
    content="笔记内容（支持 Markdown）",
    tags=["标签1", "标签2"]
)
```

#### 更新笔记

```python
client.notes.update(
    note_id=1,
    title="新标题",
    content="新内容",
    tags=["新标签"]
)
```

#### 删除笔记

```python
client.notes.delete(note_id=1)
```

#### 列出笔记

```python
notes = client.notes.list(limit=100, offset=0)
```

### 2. 搜索功能

#### 基础搜索

```python
# 关键词搜索（支持中文分词）
results = client.notes.search("机器学习 算法")

# 标签过滤搜索
results = client.notes.search("AI", tags=["技术"])

# 限制结果数量
results = client.notes.search("Python", limit=50)
```

#### 搜索特性

| 特性 | 说明 |
|------|------|
| FTS5 全文索引 | 毫秒级搜索响应 |
| BM25 排序 | 按相关度排列结果 |
| 关键词高亮 | 匹配内容高亮显示 |
| 中文分词 | jieba 分词器支持 |
| 标签过滤 | 按标签缩小搜索范围 |
| 搜索建议 | 自动补全关键词 |

### 3. 标签系统

#### 创建标签

```python
# 顶级标签
tech_id = client.tags.create("技术")

# 子标签
ai_id = client.tags.create("AI", parent_id=tech_id)
ml_id = client.tags.create("机器学习", parent_id=ai_id)
```

#### 标签树

```python
tree = client.tags.get_tree()
# 返回嵌套的标签树结构
```

#### 标签建议

```python
suggestions = client.tags.suggest("A")
# 返回以 "A" 开头的标签列表
```

#### 合并标签

```python
# 将旧标签合并到新标签
client.tags.merge(source_id=2, target_id=1)
```

### 4. 双向链接

#### 创建链接

```python
# 手动创建链接
client.links.create(source_id=1, target_id=2)
```

#### Wiki 语法自动链接

在笔记内容中使用 `[[笔记标题]]` 或 `[[标题|别名]]`，保存时自动创建链接。

#### 查看链接

```python
# 出链（当前笔记链接到哪些笔记）
outgoing = client.links.get_outgoing(note_id=1)

# 入链/反向链接（哪些笔记链接到当前笔记）
incoming = client.links.get_incoming(note_id=2)

# 链接图谱（所有笔记和链接）
graph = client.links.get_graph()
```

#### 孤立笔记

```python
# 查找没有链接的孤立笔记
orphaned = client.links.get_orphaned()
```

### 5. 版本历史

#### 自动版本

每次更新笔记时，系统自动保存旧版本。

#### 手动保存版本

```python
version_id = client.versions.save(
    note_id=1,
    title="标题",
    content="内容",
    tags=["标签"],
    change_summary="重大更新：添加了新章节"
)
```

#### 查看版本

```python
# 列出版本
versions = client.versions.list(note_id=1, limit=10)

# 版本详情
version = client.versions.get(version_id=1)
```

#### 版本对比

```python
# 对比两个版本
diff = client.versions.diff(version_id_1=1, version_id_2=2)
```

#### 恢复版本

```python
client.versions.restore(version_id=1)
```

#### 标记重要版本

```python
client.versions.tag(version_id=1, tag_name="v1.0 正式版")
```

#### 清理旧版本

```python
# 保留最近 10 个版本
deleted = client.versions.cleanup(note_id=1, keep_count=10)
```

### 6. 导入导出

#### 导出为 Markdown

```python
files = client.export.export_all_to_markdown_files(
    output_dir="./backup",
    include_versions=False
)
```

#### 导出为 JSON

```python
output = client.export.export_all_to_json(
    output_path="./backup.json",
    include_versions=False
)
```

#### 从 Markdown 导入

```python
result = client.importer.import_markdown_directory(
    dirpath="./notes",
    conflict_policy="skip"  # skip / overwrite / merge
)
```

#### 从 JSON 导入

```python
result = client.importer.import_json_file(
    filepath="./backup.json",
    conflict_policy="skip"
)
```

---

## 🖥️ 命令行工具

### 基本用法

```bash
# 查看帮助
python cli.py --help

# 指定数据库
python cli.py --db my_knowledge.db notes list
```

### 常用命令

```bash
# 创建笔记
python cli.py notes create "标题" "内容" --tags AI,技术

# 搜索笔记
python cli.py notes search "关键词"

# 列出笔记
python cli.py notes list --limit 50

# 创建标签
python cli.py tags create "标签名" --parent 1

# 查看标签树
python cli.py tags list --tree

# 导出
python cli.py export markdown ./backup
python cli.py export json ./backup.json

# 导入
python cli.py import markdown ./notes --conflict skip
```

完整命令参考：[CLI 参考文档](cli-reference.md)

---

## 🐳 Docker 部署

### 快速启动

```bash
docker-compose up -d
```

### 数据持久化

数据存储在 `./data` 目录，备份时复制该目录即可。

### 备份与恢复

```bash
# 备份
docker-compose exec memomind cp /data/memomind.db /backups/

# 恢复
docker-compose exec memomind cp /backups/memomind.db /data/
```

---

## 📊 性能参考

| 笔记数量 | 搜索延迟 | 内存占用 | DB 文件大小 |
|----------|----------|----------|-------------|
| 1,000 | 1.35ms | 45MB | ~1.2MB |
| 10,000 | 27-32ms | ~0.02MB | ~11.5MB |
| 100,000 | ~200ms* | ~200MB* | ~115MB* |

*100K 数据为预估值，实际性能取决于笔记内容长度和硬件配置。

---

## ❓ 常见问题

### 中文搜索没有结果？

确保已安装 jieba：
```bash
pip install jieba
```

### 数据库锁定错误？

确保只有一个进程访问数据库。WAL 模式已默认启用。

### 如何迁移数据？

```bash
# 导出
python cli.py export json ./backup.json

# 导入到新实例
python cli.py import json ./backup.json
```

更多问题：[故障排查指南](troubleshooting.md)

---

## 📖 更多文档

- [快速开始指南](quick-start.md) - 5 分钟入门
- [API 参考文档](api-reference.md) - 完整 API 文档
- [CLI 参考文档](cli-reference.md) - 命令行工具参考
- [部署指南](deployment.md) - Docker 和本地部署
- [故障排查](troubleshooting.md) - 常见问题解决

---

*最后更新：2026-04-23*
