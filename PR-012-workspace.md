# PR-012: 多工作区 (Multi-Workspace)

**状态：** ✅ 完成  
**日期：** 2026-04-24  
**测试：** 18/18 通过

## 功能

- ✅ 工作区创建/删除/更新/查询
- ✅ 默认工作区自动创建（ID=1）
- ✅ 工作区名称唯一性约束
- ✅ 笔记按工作区隔离
- ✅ 笔记跨工作区移动
- ✅ 工作区统计（笔记数、标签笔记数）
- ✅ 跨工作区搜索（含工作区信息）
- ✅ 删除工作区级联删除笔记
- ✅ 保护默认工作区不可删除

## 新增文件

| 文件 | 说明 |
|------|------|
| `core/workspace_service.py` | 工作区管理服务（~300 行） |
| `tests/test_workspace.py` | 工作区测试（18 用例） |

## 数据库变更

```sql
CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE notes ADD COLUMN workspace_id INTEGER 
    REFERENCES workspaces(id) DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_notes_workspace 
    ON notes(workspace_id);
```

## 测试覆盖

| 测试类别 | 用例数 | 状态 |
|---------|--------|------|
| 基础 CRUD | 10 | ✅ |
| 笔记移动 | 2 | ✅ |
| 删除保护 | 2 | ✅ |
| 统计 | 1 | ✅ |
| 跨区搜索 | 1 | ✅ |
| 模型转换 | 2 | ✅ |
| **总计** | **18** | **✅** |

## 技术亮点

1. **自动迁移** - 检测 notes 表是否已有 workspace_id，避免重复 ALTER
2. **默认工作区** - 系统启动时自动创建 ID=1 的默认工作区
3. **级联删除** - 删除工作区时自动清理笔记和 FTS 索引
4. **跨区搜索** - 支持指定工作区列表或全局搜索
5. **笔记计数** - list_workspaces 自动附加 note_count

## 集成点

- `NotesAPI` 需要传入 `workspace_id` 创建笔记
- `SearchService` 需要支持 `workspace_id` 过滤
- `LinkService` 链接关系需要按工作区隔离
- `TagService` 标签需要按工作区隔离

## 后续 PR 依赖

- PR-013 用户系统（需要 workspace_id 做成员管理）
- PR-014 活动日志（需要 workspace_id 做审计）
