# 数据模型

> 最后更新：2026-05-01

---

## 数据库总览

MemoMind 使用 SQLite 作为持久化存储，包含以下 10 张表：

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `notes` | 笔记主表 | id, title, content, tags, workspace_id, created_by |
| `notes_fts` | FTS5 全文索引虚拟表 | title, content, tags |
| `tags` | 标签定义表 | id, name, parent_id, alias_for |
| `note_tags` | 笔记-标签关联表 | note_id, tag_id |
| `note_links` | 笔记双向链接表 | source_note_id, target_note_id |
| `note_versions` | 版本历史表 | id, note_id, version_number, title, content |
| `workspaces` | 工作区表 | id, name, description |
| `users` | 用户表 | id, username, display_name |
| `workspace_members` | 工作区成员表 | workspace_id, user_id, role |
| `activity_log` | 活动日志表 | id, user_id, workspace_id, note_id, action |
| `conflicts` | 冲突记录表 | id, note_id, user_id, strategy, resolved_content |
| `backups` | 备份记录表 | id, filename, size_bytes, note_count |

---

## 表结构详述

### `notes` — 笔记主表

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,                          -- JSON 数组字符串
    workspace_id INTEGER REFERENCES workspaces(id) DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 自增主键 |
| `title` | string | 笔记标题 |
| `content` | string | 笔记内容（支持 Markdown + `[[Wiki]]` 语法） |
| `tags` | string (JSON) | 标签 JSON 数组，如 `["python", "fastapi"]` |
| `workspace_id` | int | 所属工作区 ID |
| `created_by` | int | 创建者用户 ID |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 最后更新时间 |

### `notes_fts` — FTS5 全文索引

```sql
CREATE VIRTUAL TABLE notes_fts USING fts5(title, content, tags)
```

虚拟表，通过触发器自动同步。笔记增删改时触发 `notes_ai`、`notes_ad`、`notes_au` 触发器更新索引。

### `tags` — 标签定义表

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    parent_id INTEGER REFERENCES tags(id),    -- 层级标签
    alias_for INTEGER REFERENCES tags(id),    -- 标签别名/合并
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 自增主键 |
| `name` | string | 标签名（唯一） |
| `parent_id` | int | 父标签 ID，用于层级标签 |
| `alias_for` | int | 指向主标签，用于标签别名/合并 |

### `note_tags` — 笔记-标签关联表

```sql
CREATE TABLE note_tags (
    note_id INTEGER REFERENCES notes(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (note_id, tag_id)
)
```

### `note_links` — 笔记双向链接表

```sql
CREATE TABLE note_links (
    source_note_id INTEGER REFERENCES notes(id),
    target_note_id INTEGER REFERENCES notes(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_note_id, target_note_id)
)
```

通过解析笔记内容中的 `[[目标笔记]]` Wiki 语法自动维护。

### `note_versions` — 版本历史表

```sql
CREATE TABLE note_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL REFERENCES notes(id),
    version_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,                          -- JSON 数组
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_summary TEXT,                -- 变更说明
    is_tagged INTEGER DEFAULT 0,        -- 是否标记重要版本
    tag_name TEXT                       -- 版本标签名
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 版本 ID |
| `note_id` | int | 关联笔记 ID |
| `version_number` | int | 版本号（从 1 递增） |
| `title` | string | 快照标题 |
| `content` | string | 快照内容 |
| `tags` | string (JSON) | 快照标签 |
| `change_summary` | string | 变更描述 |
| `is_tagged` | bool | 是否标记 |
| `tag_name` | string | 版本标签（如 "v1.0", "发布版"） |

### `workspaces` — 工作区表

```sql
CREATE TABLE workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### `users` — 用户表

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### `workspace_members` — 工作区成员表

```sql
CREATE TABLE workspace_members (
    workspace_id INTEGER REFERENCES workspaces(id),
    user_id INTEGER REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('owner', 'editor', 'viewer')),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id)
)
```

角色权限：
| 角色 | 权限 |
|------|------|
| `owner` | 工作区全部权限（包括删除工作区、管理成员） |
| `editor` | 笔记 CRUD、搜索、导入导出 |
| `viewer` | 只读（查看笔记、搜索） |

### `activity_log` — 活动日志表

```sql
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    workspace_id INTEGER,
    note_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,                     -- JSON 格式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `action` | string | 操作类型：`create` / `update` / `delete` / `tag` / `workspace_create` 等 |
| `details` | string (JSON) | 操作详情 |

### `conflicts` — 冲突记录表

```sql
CREATE TABLE conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    strategy TEXT NOT NULL DEFAULT 'latest-wins'
        CHECK (strategy IN ('latest-wins', 'manual', 'merge')),
    base_content TEXT NOT NULL,
    their_content TEXT NOT NULL,
    our_content TEXT NOT NULL,
    resolved_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
)
```

### `backups` — 备份记录表

```sql
CREATE TABLE backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    note_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT DEFAULT ''
)
```

---

## 代码层数据模型

### Note (dataclass)

```python
@dataclass
class Note:
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

### SearchResult (dataclass)

```python
@dataclass
class SearchResult:
    note: Note
    score: float
    highlights: dict  # {'title': '...', 'content': '...'}
```

### API Pydantic 模型

| 模型 | 用途 |
|------|------|
| `NoteCreate` | 创建笔记请求体 |
| `NoteUpdate` | 更新笔记请求体 |
| `NoteSearch` | 搜索请求体 |
| `TagCreate` | 创建标签请求体 |
| `WorkspaceCreate` | 创建工作区请求体 |
| `WorkspaceUpdate` | 更新工作区请求体 |
| `UserCreate` | 注册用户请求体 |
| `UserUpdate` | 更新用户请求体 |
| `MemberAdd` | 添加成员请求体 |
| `MemberRoleUpdate` | 更新成员角色请求体 |
| `LinkCreate` | 创建链接请求体 |
| `ActivityLogCreate` | 创建活动日志请求体 |
| `ActivityFilter` | 活动过滤请求体 |
| `ConflictResolve` | 冲突解决请求体 |
| `BackupCreate` | 创建备份请求体 |
| `LoginRequest` | 登录请求体 |
| `TokenResponse` | 登录响应体 |
| `ErrorResponse` | 错误响应体 |
