# MemoMind Phase 4 规划

**制定时间：** 2026-04-29  
**最后更新：** 2026-05-17  
**基线状态：** Phase 1-3 全部完成，安全认证升级完成，AI Provider 抽象层完成

---

## 📊 Phase 1-3 回顾

| Phase | 核心功能 | PR 数量 | 测试数 | 状态 |
|-------|----------|--------|--------|------|
| Phase 1 | 基础笔记 + 分类器 | 2 | - | ✅ |
| Phase 2 | 搜索/版本/导入导出/标签/链接/RAG/摘要 | 9 | 122 | ✅ |
| Phase 3 | 多工作区/用户/活动日志/冲突/备份/REST API | 6 | 248 | ✅ |
| **合计** | | **17** | **370** | **✅** |

## 📊 Phase 4 进展

| PR | 功能 | 测试数 | 状态 |
|----|------|--------|------|
| PR-022 | MCP Server | 25 | ✅ |
| PR-019 | Docker 部署 | - | ✅ |
| PR-021 | 导出增强 | 12 | ✅ |
| PR-023 | 安全加固 | - | ✅ |
| PR-018 | Web Dashboard | 20 | ✅ |
| PR-020 | 实时协作 | - | ⏳ |
| PR-024 | 安全认证升级（JWT + bcrypt） | 100 | ✅ |
| PR-025 | AI Provider 抽象层（混合 AI） | 16 | ✅ |
| **Phase 4** | | **173+** | **86%** |

---

## Phase 4 主题：Web UI + 生产就绪

### PR-018：Web Dashboard（前端界面）✅
**目标：** 构建基于 React + Vite 的 Web 管理界面，通过 REST API 与后端交互

- [x] 笔记列表 + 搜索 + 高亮
- [x] 笔记编辑器（Markdown）
- [x] 标签树 + 管理
- [x] 版本历史 + 差异对比
- [x] 工作区切换
- [x] 用户管理（管理员视角）
- [x] 活动日志时间线
- [x] 登录/认证
- [x] 响应式设计（移动端适配）
- [x] 20 个测试通过
- [x] 构建产物：web/dist/ (303KB JS + 24KB CSS)

### PR-019：Docker Compose 一键部署
**目标：** 完整的 Docker 部署方案

- [ ] Dockerfile（后端 + 前端多阶段构建）
- [ ] docker-compose.yml（含 Nginx 反向代理）
- [ ] 环境变量配置模板
- [ ] 数据持久化（volume 映射）
- [ ] 健康检查 + 自动重启
- [ ] HTTPS（Let's Encrypt / Caddy）

### PR-020：实时协作（WebSocket）
**目标：** 支持多人同时编辑笔记

- [ ] WebSocket 连接管理
- [ ] OT/CRDT 冲突解决算法
- [ ] 实时光标 + 选区同步
- [ ] 在线用户列表
- [ ] 编辑历史回放

### PR-021：笔记导出/导入增强
**目标：** 支持主流笔记格式

- [ ] Obsidian 兼容导出
- [ ] Logseq 兼容导出
- [ ] Notion 导入
- [ ] PDF 导出（wkhtmltopdf / WeasyPrint）
- [ ] 批量导出（zip 打包）

### PR-022：MCP Server 集成
**目标：** 将 MemoMind 作为 MCP Server，供 AI Agent 调用

- [ ] MCP Protocol 实现（stdio + http）
- [ ] tools: search_notes, get_note, create_note, update_note
- [ ] tools: list_tags, get_links, ask_question
- [ ] 资源：note:// URI 解析
- [ ] 与 OpenClaw / Claude Desktop 集成测试

### PR-023：安全加固 + 审计
**目标：** 生产级安全

- [x] JWT 认证（python-jose, HS256）— PR-024 已完成
- [x] bcrypt 密码哈希 — PR-024 已完成
- [x] 前端登录/注册页面 — PR-024 已完成
- [x] 数据库 schema 迁移兼容 — PR-024 已完成
- [ ] 速率限制（API + 登录）
- [ ] CSP 头 + XSS 防护
- [ ] SQL 注入审查（全面）
- [ ] 密码策略 + 2FA 支持
- [ ] 审计日志导出
- [ ] 依赖安全扫描

---

### PR-024：安全认证升级（JWT + bcrypt）✅
**目标：** 将认证机制从可伪造的 hex token 升级为标准 JWT + bcrypt 密码哈希

**完成内容：**
- [x] 后端：`python-jose` JWT 认证（HS256），替换原 hex token
- [x] 后端：`bcrypt` 密码哈希，替换原明文存储
- [x] 后端：`POST /api/auth/login` 增加 `password` 参数
- [x] 后端：`POST /api/users` 注册增加 `password` 参数（min_length=6）
- [x] 后端：`UserService.verify_password()` 密码验证方法
- [x] 后端：WebSocket 认证升级为 JWT token
- [x] 前端：登录页面增加密码输入框
- [x] 前端：注册/登录模式切换
- [x] 前端：注册成功后自动登录
- [x] 前端：`api.ts` 增加 `login(username, password)` 和 `register(username, password, display_name?)`
- [x] 数据库：`users` 表增加 `password_hash` 列（运行时迁移兼容）
- [x] 测试：100 个测试全部通过，覆盖用户服务、API 服务器、集成、协作、备份

**技术细节：**
- JWT claims: `sub`（用户名）、`exp`（过期时间）
- Token 有效期：24 小时（`MEMOMIND_TOKEN_EXPIRE` 环境变量）
- 密钥：`MEMOMIND_SECRET_KEY` 环境变量，默认随机生成
- 密码哈希：bcrypt ($2b$ 格式)，salt rounds=12

### PR-025：AI Provider 抽象层（混合 AI）✅
**目标：** 实现"本地默认 + 可选云端"的混合 AI 架构，通过环境变量切换 OpenAI / Anthropic 作为生成引擎

**完成内容：**
- [x] 新建 `core/ai_provider.py`：抽象基类 + 工厂函数
- [x] 新建 `core/ai_local.py`：LocalProvider（jieba + 启发式，零依赖）
- [x] 新建 `core/ai_openai.py`：OpenAIProvider（chat + embed）
- [x] 新建 `core/ai_anthropic.py`：AnthropicProvider（messages）
- [x] 修改 `core/rag_service.py`：支持 provider + fallback
- [x] 修改 `core/summarization_service.py`：支持 provider + fallback
- [x] 修改 `core/semantic_service.py`：支持 provider 参数
- [x] 修改 `core/api_server.py`：初始化 AI Provider
- [x] 修改 `api/client.py`：初始化 AI Provider
- [x] 修改 `requirements.txt`：添加可选 openai/anthropic 依赖
- [x] 新建 `tests/test_ai_provider.py`：16 个测试全部通过

**环境变量：**
- `MEMOMIND_AI_PROVIDER`：`local`（默认）/ `openai` / `anthropic`
- `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_EMBED_MODEL`
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`

**技术细节：**
- 所有云端 provider 失败时自动 fallback 到本地算法
- 缺失 API key 时自动 fallback 并产生 warning
- `embed()` 在本地/Anthropic 模式下返回 `[]`（不支持向量化）

---

## 优先级建议

| 优先级 | PR | 理由 |
|--------|-----|------|
| 🔴 P0 | PR-022 MCP Server | 直接服务于 AI Agent 场景，与 OpenClaw 生态紧密结合 |
| 🟡 P1 | PR-018 Web Dashboard | 可视化界面，提升使用体验 |
| 🟡 P1 | PR-019 Docker 部署 | 降低部署门槛 |
| 🟢 P2 | PR-021 导出增强 | 兼容主流笔记平台 |
| 🟢 P2 | PR-023 安全加固 | 生产部署前必须 |
| 🔵 P3 | PR-020 实时协作 | 锦上添花，但开发量大 |

---

## 时间预估

| PR | 预估工作量 | 计划 |
|----|-----------|------|
| PR-022 MCP Server | 2-3 天 | Week 1 |
| PR-018 Web Dashboard | 5-7 天 | Week 1-2 |
| PR-019 Docker 部署 | 1-2 天 | Week 2 |
| PR-021 导出增强 | 2-3 天 | Week 3 |
| PR-023 安全加固 | 2-3 天 | Week 3 |
| PR-020 实时协作 | 5-7 天 | Week 4+ |

---

## Phase 4 成功标准

- ✅ Web Dashboard 可正常使用（CRUD + 搜索 + 标签）
- ✅ Docker 一键部署成功
- ✅ MCP Server 可被 OpenClaw 调用
- ✅ 370 测试全部通过（+ 新增测试）
- ✅ 零安全漏洞（OWASP Top 10 无已知问题）
