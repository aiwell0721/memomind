# MemoMind Phase 3 规划：团队知识库 & 协作

**启动时间：** 2026-04-24  
**目标：** 从单用户笔记工具升级为团队协作知识库

## Phase 3 PR 列表

### PR-012: 多工作区 (Multi-Workspace)
**优先级：** 🔴 最高（基础设施）

**功能：**
- 工作区创建/删除/切换
- 笔记按工作区隔离
- 全局搜索（跨工作区）
- 工作元数据（名称、描述、创建时间）

**数据库变更：**
```sql
CREATE TABLE workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE notes ADD COLUMN workspace_id INTEGER DEFAULT 1
    REFERENCES workspaces(id);
```

**测试：** 15 个用例

---

### PR-013: 用户系统 (User System)
**优先级：** 🔴 最高（基础设施）

**功能：**
- 用户注册/登录（简单 SQLite 表）
- 用户角色：owner / editor / viewer
- 笔记创建者追踪
- 工作区成员管理

**数据库变更：**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workspace_members (
    workspace_id INTEGER REFERENCES workspaces(id),
    user_id INTEGER REFERENCES users(id),
    role TEXT DEFAULT 'viewer',  -- owner/editor/viewer
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id)
);

ALTER TABLE notes ADD COLUMN created_by INTEGER REFERENCES users(id);
```

**测试：** 18 个用例

---

### PR-014: 活动日志 (Activity Log)
**优先级：** 🟡 高

**功能：**
- 记录所有笔记操作（创建/编辑/删除/恢复）
- 时间线视图
- 按用户/工作区/类型过滤
- 操作详情（谁在什么时间做了什么）

**数据库变更：**
```sql
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    workspace_id INTEGER REFERENCES workspaces(id),
    note_id INTEGER REFERENCES notes(id),
    action TEXT NOT NULL,  -- create/update/delete/restore/tag
    details TEXT,  -- JSON 格式详情
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**测试：** 14 个用例

---

### PR-015: 冲突检测与合并 (Conflict Detection & Merge)
**优先级：** 🟡 高

**功能：**
- 编辑冲突检测（同时编辑同一笔记）
- 三路合并（three-way merge）
- 冲突解决策略：latest-wins / manual / merge
- 冲突历史记录

**测试：** 16 个用例

---

### PR-016: REST API 服务器
**优先级：** 🟢 中

**功能：**
- FastAPI 服务器
- RESTful 端点（CRUD + 搜索 + 标签 + 链接）
- JWT 认证
- API 文档（Swagger）

**测试：** 20 个用例

---

### PR-017: 自动备份与恢复
**优先级：** 🟢 中

**功能：**
- 定时备份（cron 或手动触发）
- 备份文件压缩
- 从备份恢复
- 备份历史管理

**测试：** 12 个用例

---

## 实施顺序

```
Phase 3 Kickoff
    │
    ├── PR-012 多工作区（基础设施）──→ ✅ 完成（18 测试）
    ├── PR-013 用户系统（基础设施）──→ ✅ 完成（22 测试）
    ├── PR-014 活动日志 ────────────→ ✅ 完成（21 测试）
    ├── PR-015 冲突检测与合并 ───────→ ✅ 完成（20 测试）
    ├── PR-016 REST API 服务器 ──────→ ✅ 完成（26 测试）
    └── PR-017 自动备份与恢复 ───────→ ✅ 完成（11 测试）
    │
Phase 3 收尾（集成测试 + 文档）──→ ✅ 完成
```

## Phase 3 总结

**完成 PR：** 6/6（PR-012 ~ PR-017）  
**新增测试：** 118 个  
**总测试数：** 240（122 原有 + 118 新增）  
**测试通过率：** 100% ✅

**新增核心模块：**
- `workspace_service.py` - 多工作区管理
- `user_service.py` - 用户与权限管理
- `activity_service.py` - 活动日志与审计
- `conflict_service.py` - 冲突检测与三路合并
- `backup_service.py` - 备份恢复与导出
- `api_server.py` - FastAPI REST API 服务器

**数据库新增表：**
- `workspaces` - 工作区
- `workspace_members` - 工作区成员
- `users` - 用户
- `activity_log` - 活动日志
- `conflicts` - 冲突记录
- `backups` - 备份记录
- `notes.workspace_id` - 笔记工作区字段
- `notes.created_by` - 笔记创建者字段

## 预期成果

- 支持多用户协作的知识库
- 完整的工作区隔离
- 操作可追溯（审计日志）
- 冲突安全处理
- REST API 供外部系统集成

## 总测试数预估：~95 个
