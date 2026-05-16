# 产品概览

> 最后更新：2026-05-01

---

## 产品定位

MemoMind 是基于 SQLite 的**团队知识库与智能笔记系统**。它提供笔记管理、全文搜索、语义搜索、知识图谱、RAG 问答、版本历史、多工作区协作等完整功能。

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 数据库 | SQLite + FTS5 | 全文搜索 + BM25 排序 |
| 中文分词 | jieba | 预处理 + FTS5 索引 |
| 后端 | Python + FastAPI | REST API（40+ 端点，JWT 认证） |
| 前端 | React + Vite + Tailwind | Web Dashboard |
| AI 集成 | MCP Server | 20 个工具 |
| 部署 | Docker + docker-compose | |

## 功能模块一览

| 模块 | 功能 |
|------|------|
| 笔记管理 | CRUD、Markdown 编辑器、标签分类 |
| 全文搜索 | FTS5 + jieba 中文分词 + BM25 排序 |
| 语义搜索 | TF-IDF + 余弦相似度 + 混合搜索 |
| 标签系统 | 层级标签、别名、自动标签推荐 |
| 双向链接 | Wiki 语法 `[[笔记]]`、反向链接、知识图谱 |
| 版本历史 | 版本 CRUD、差异对比、标签、自动清理 |
| 知识图谱 | 社区检测、GraphML 导出、图谱统计 |
| RAG 问答 | 基于笔记库的智能问答 + 推荐问题 |
| 自动摘要 | 笔记内容自动提炼摘要 |
| 导入导出 | Markdown/JSON/Obsidian/Notion/PDF |
| 多工作区 | 工作区 CRUD、笔记迁移、跨区搜索 |
| 用户系统 | 用户 CRUD、角色管理（admin/editor/viewer） |
| 活动日志 | 全量审计、时间线、按用户/笔记/动作过滤 |
| 冲突检测 | 并发编辑检测、三路合并、三种解决策略 |
| 备份恢复 | SQLite 备份、gzip 压缩、JSON 导出 |
| MCP Server | 20 个工具供 AI Agent 调用 |
| REST API | 40+ 端点、JWT 认证、Swagger 文档 |
| Web Dashboard | React + Vite，完整笔记管理界面 |
| CLI 工具 | 命令行笔记管理、搜索、问答 |
| Python SDK | 完整的 API 客户端封装 |

## 接口方式

| 接口 | 说明 |
|------|------|
| WebSocket | `ws://localhost:8000/ws/notes/{note_id}` | 实时协作 |
| MCP Server | stdio 模式（本地）或 HTTP 模式（`localhost:8001`） |
| CLI | `python cli.py` 子命令 |
| Web Dashboard | `npm run dev` 启动在 `localhost:3000` |

## 当前进度

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 基础笔记 + 分类 | ✅ 完成 |
| Phase 2 | 搜索/版本/导入导出/标签/链接/RAG/摘要/图谱 | ✅ 完成 |
| Phase 3 | 多工作区/用户/活动日志/冲突/备份/REST API | ✅ 完成 |
| Phase 4 | MCP Server、Docker、导出增强、Web Dashboard、实时协作 | ✅ 100% 完成 |
| PR-020 | 实时协作（WebSocket） | ✅ 完成 |

**测试状态**：436 个测试全部通过
