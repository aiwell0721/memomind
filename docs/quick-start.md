# MemoMind 快速开始指南

> 5 分钟创建你的第一个 AI 知识库

## 📦 安装

### 方式 1：pip 安装（推荐）

```bash
pip install memomind
```

### 方式 2：从源码安装

```bash
git clone https://github.com/your-org/memomind.git
cd memomind
pip install -r requirements.txt
pip install jieba
```

### 方式 3：Docker 部署

```bash
docker pull memomind:latest
docker run -v ./data:/data memomind:latest
```

---

## 🚀 5 分钟快速入门

### 步骤 1：创建数据库

```python
from memomind import MemoMind

# 创建客户端（自动创建数据库）
client = MemoMind(db_path="~/memomind.db")
```

### 步骤 2：创建第一个笔记

```python
# 创建笔记
note_id = client.notes.create(
    title="AI 基础概念",
    content="人工智能是计算机科学的一个分支...",
    tags=["AI", "技术", "入门"]
)
print(f"笔记已创建：ID={note_id}")
```

### 步骤 3：搜索笔记

```python
# 搜索笔记
results = client.notes.search("人工智能")

for r in results:
    print(f"📝 {r['note']['title']}")
    print(f"   相关度：{r['score']:.2f}")
```

### 步骤 4：创建标签

```python
# 创建标签
tag_id = client.tags.create("AI")
child_id = client.tags.create("机器学习", parent_id=tag_id)

# 查看标签树
tree = client.tags.get_tree()
print(tree)
```

### 步骤 5：创建链接

```python
# 创建笔记间链接
client.links.create(source_id=1, target_id=2)

# 查看反向链接
incoming = client.links.get_incoming(note_id=2)
print(incoming)
```

---

## 📋 CLI 快速使用

### 创建笔记

```bash
memomind notes create "标题" "内容" --tags tag1,tag2
```

### 搜索笔记

```bash
memomind notes search "关键词"
```

### 列出标签

```bash
memomind tags list --tree
```

### 导出笔记

```bash
memomind export markdown ./output
```

---

## 🎯 下一步

- [API 参考文档](api-reference.md) - 完整 API 文档
- [CLI 参考文档](cli-reference.md) - 命令行工具参考
- [部署指南](deployment.md) - Docker 和本地部署
- [故障排查](troubleshooting.md) - 常见问题解决

---

*需要帮助？查看 [故障排查指南](troubleshooting.md) 或提交 Issue*
