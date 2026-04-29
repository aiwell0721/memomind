# MemoMind

**团队知识库与智能笔记系统**

基于 SQLite 的知识管理引擎，支持全文搜索、语义理解、版本控制、多工作区协作与 REST API。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-370%20passed-brightgreen.svg)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

---

## ✨ 功能特性

### 核心能力
- 🔍 **全文搜索** — SQLite FTS5 + BM25 相关度排序 + 中文分词（jieba）
- 🏷️ **标签系统** — 层级标签、别名、合并、自动标签推荐
- 🔗 **双向链接** — Wiki 语法 `[[笔记]]`、反向链接、知识图谱
- 📝 **版本历史** — 版本 CRUD、差异对比、标签、自动清理
- 📥 **导入导出** — Markdown / JSON 互转、批量操作
- 🤖 **RAG 问答** — 基于笔记库的智能问答 + 推荐问题
- 📊 **知识图谱** — 标签社区检测、GraphML 导出、图谱统计
- 📝 **自动摘要** — 笔记内容自动提炼摘要
- 🔎 **语义搜索** — TF-IDF + 余弦相似度语义理解

### 协作功能
- 🏢 **多工作区** — 工作区 CRUD、笔记迁移、跨区搜索、统计
- 👥 **用户系统** — 用户 CRUD、角色管理（admin/editor/viewer）、成员权限
- 📋 **活动日志** — 全量审计、时间线、按用户/笔记/动作过滤
- ⚡ **冲突检测** — 并发编辑检测、三路合并、三种解决策略
- 💾 **备份恢复** — SQLite 备份、gzip 压缩、JSON 导出、统计

### 开发支持
- 🌐 **REST API** — FastAPI 服务器、40+ 端点、JWT 认证、Swagger 文档
- 🐍 **Python SDK** — 完整的 API 客户端封装
- 💻 **CLI 工具** — 命令行笔记管理、搜索、问答

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/memomind.git
cd memomind

# 安装依赖
pip install -r requirements.txt
```

### 使用 Python API

```python
from core.database import Database
from core.search_service import SearchService
from core.tag_service import TagService

# 初始化
db = Database("memomind.db")
search = SearchService(db)
tags = TagService(db)

# 创建笔记
note = search.db.create_note("Python 入门", "Python 是一种编程语言...")

# 搜索
results = search.search("Python 编程")
for r in results:
    print(f"{r.note.title} (score: {r.score:.2f})")

# 标签
tags.create("Python", "Programming")
```

### 使用 CLI

```bash
# 创建笔记
python cli.py create --title "今日笔记" --content "今天学习了 MemoMind"

# 搜索
python cli.py search "MemoMind"

# 列出所有笔记
python cli.py list

# RAG 问答
python cli.py ask "什么是 MemoMind？"
```

### 启动 REST API

```bash
python -c "from core.api_server import create_app; import uvicorn; uvicorn.run(create_app('memomind.db'), host='0.0.0.0', port=8000)"

# 访问 Swagger 文档
# http://localhost:8000/docs
```

---

## 📊 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行集成测试
python -m pytest tests/test_integration.py -v

# 运行性能测试
python -m pytest tests/test_performance.py -v
```

**当前状态：** 370 个测试全部通过 ✅

---

## 🏗️ 架构

```
memomind/
├── core/                    # 核心服务
│   ├── database.py          # SQLite 数据库 + 表结构
│   ├── models.py            # 数据模型
│   ├── search_service.py    # FTS5 全文搜索
│   ├── tag_service.py       # 标签管理
│   ├── link_service.py      # 双向链接
│   ├── version_service.py   # 版本历史
│   ├── import_service.py    # 导入（Markdown/JSON）
│   ├── export_service.py    # 导出（Markdown/JSON）
│   ├── tokenizer.py         # 中文分词（jieba）
│   ├── rag_service.py       # RAG 问答
│   ├── semantic_service.py  # 语义搜索
│   ├── summarization_service.py  # 自动摘要
│   ├── knowledge_graph_service.py # 知识图谱
│   ├── auto_tag_service.py  # 自动标签
│   ├── workspace_service.py # 多工作区
│   ├── user_service.py      # 用户系统
│   ├── activity_service.py  # 活动日志
│   ├── conflict_service.py  # 冲突检测
│   ├── backup_service.py    # 备份恢复
│   ├── diff_service.py      # 差异对比
│   └── api_server.py        # REST API（FastAPI）
├── api/                     # Python SDK
│   └── client.py
├── tests/                   # 测试套件（370 个测试）
├── benchmarks/              # 性能基准测试
├── docs/                    # 文档
├── cli.py                   # 命令行工具
├── requirements.txt         # 依赖
└── docker-compose.yml       # Docker 部署
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [快速开始](docs/quick-start.md) | 安装和基本使用 |
| [用户指南](docs/user-guide.md) | 完整功能说明 |
| [API 参考](docs/api-reference.md) | Python API 文档 |
| [CLI 参考](docs/cli-reference.md) | 命令行工具文档 |
| [部署指南](docs/deployment.md) | Docker 和部署 |
| [故障排查](docs/troubleshooting.md) | 常见问题解决 |

---

## 🗺️ 路线图

- [x] Phase 1: 基础笔记 + 分类
- [x] Phase 2: 搜索/版本/导入导出/标签/链接/RAG
- [x] Phase 3: 多工作区/用户/活动日志/冲突/备份/REST API
- [ ] Phase 4: Web UI + MCP Server + 生产就绪

详细规划见 [docs/phase4-plan.md](docs/phase4-plan.md)

---

## 📝 License

MIT License — 详见 [LICENSE](./LICENSE)
