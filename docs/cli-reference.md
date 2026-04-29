# MemoMind CLI 参考文档

## 📖 概述

MemoMind 提供完整的命令行工具，支持所有核心功能。

```bash
# 基本用法
python cli.py [命令] [子命令] [参数]

# 指定数据库
python cli.py --db ~/memomind.db [命令]
```

---

## 📝 notes 命令

### 创建笔记

```bash
python cli.py notes create "标题" "内容" --tags tag1,tag2
```

### 搜索笔记

```bash
python cli.py notes search "关键词" --tags tag1 --limit 20
```

### 列出笔记

```bash
python cli.py notes list --limit 100
```

### 获取笔记详情

```bash
python cli.py notes get <笔记 ID>
```

---

## 🏷️ tags 命令

### 创建标签

```bash
python cli.py tags create "标签名" --parent <父标签 ID>
```

### 列出标签

```bash
# 平面列表
python cli.py tags list

# 树形显示
python cli.py tags list --tree
```

---

## 🔗 links 命令

### 获取反向链接

```bash
python cli.py links incoming <笔记 ID>
```

### 获取出链

```bash
python cli.py links outgoing <笔记 ID>
```

### 导出链接图谱

```bash
python cli.py links graph
```

### 获取断链

```bash
python cli.py links broken
```

### 获取孤立笔记

```bash
python cli.py links orphaned
```

---

## 📜 versions 命令

### 列出版本

```bash
python cli.py versions list <笔记 ID> --limit 10
```

### 恢复版本

```bash
python cli.py versions restore <版本 ID>
```

---

## 📤 export 命令

### 导出为 Markdown

```bash
python cli.py export markdown ./output --versions
```

### 导出为 JSON

```bash
python cli.py export json ./backup.json --versions
```

---

## 📥 import 命令

### 从 Markdown 导入

```bash
python cli.py import markdown ./notes --conflict skip
```

### 从 JSON 导入

```bash
python cli.py import json ./backup.json --conflict overwrite
```

---

## 📊 完整命令列表

| 命令 | 子命令 | 说明 |
|------|--------|------|
| `notes` | `create` | 创建笔记 |
| `notes` | `search` | 搜索笔记 |
| `notes` | `list` | 列出笔记 |
| `notes` | `get` | 获取笔记详情 |
| `tags` | `create` | 创建标签 |
| `tags` | `list` | 列出标签 |
| `links` | `incoming` | 获取反向链接 |
| `links` | `outgoing` | 获取出链 |
| `links` | `graph` | 导出链接图谱 |
| `links` | `broken` | 获取断链 |
| `links` | `orphaned` | 获取孤立笔记 |
| `versions` | `list` | 列出版本 |
| `versions` | `restore` | 恢复版本 |
| `export` | `markdown` | 导出为 Markdown |
| `export` | `json` | 导出为 JSON |
| `import` | `markdown` | 从 Markdown 导入 |
| `import` | `json` | 从 JSON 导入 |

---

## 💡 使用示例

### 工作流示例

```bash
# 1. 创建笔记
python cli.py notes create "AI 基础" "人工智能是..." --tags AI,技术

# 2. 搜索笔记
python cli.py notes search "人工智能"

# 3. 创建标签
python cli.py tags create "AI"

# 4. 查看反向链接
python cli.py links incoming 1

# 5. 导出笔记
python cli.py export markdown ./backup
```

---

*需要更多帮助？查看 [快速开始指南](quick-start.md) 或 [API 参考](api-reference.md)*
