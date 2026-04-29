# MemoMind Phase 2 - PR-004 笔记版本历史

**优先级:** P0  
**状态:** 🟢 开发中  
**创建时间:** 2026-04-21 00:05  
**负责人:** coding  
**截止时间:** 2026-04-23  
**最新进展:** 2026-04-21 00:05 - Kickoff，开始技术方案设计

---

## 📋 需求描述

实现笔记版本历史功能，支持：
1. 自动保存每次编辑的版本
2. 查看历史版本列表
3. 版本对比（diff）
4. 版本恢复（回滚）
5. 版本标签（手动标记重要版本）
6. 版本清理策略（保留最近 N 个版本）

---

## 🏗️ 技术方案

### 核心组件

```
memomind/
├── core/
│   ├── version_service.py  # 版本管理服务
│   └── diff_service.py     # 版本对比服务
├── tests/
│   ├── test_version.py     # 版本功能测试
│   └── test_diff.py        # 对比功能测试
└── PR-004-version-history.md
```

### SQLite Schema

```sql
-- 版本历史表
CREATE TABLE note_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_summary TEXT,  -- 变更摘要（可选）
    is_tagged INTEGER DEFAULT 0,  -- 是否手动标记
    tag_name TEXT,  -- 标签名称（可选）
    FOREIGN KEY (note_id) REFERENCES notes(id)
);

-- 索引：加速版本查询
CREATE INDEX idx_versions_note ON note_versions(note_id);
CREATE INDEX idx_versions_number ON note_versions(note_id, version_number);
```

### 核心 API

```python
class VersionService:
    def save_version(self, note_id: int, title: str, content: str, tags: list, 
                     change_summary: str = None) -> int:
        """保存新版本，返回版本号"""
        
    def get_versions(self, note_id: int, limit: int = 10) -> List[Version]:
        """获取历史版本列表"""
        
    def get_version(self, version_id: int) -> Version:
        """获取指定版本详情"""
        
    def restore_version(self, version_id: int) -> Note:
        """恢复到指定版本"""
        
    def tag_version(self, version_id: int, tag_name: str):
        """标记重要版本"""
        
    def cleanup_versions(self, note_id: int, keep_count: int = 10):
        """清理旧版本，保留最近 N 个"""


class DiffService:
    def compare_versions(self, version_id_a: int, version_id_b: int) -> Diff:
        """对比两个版本"""
        
    def compare_with_current(self, note_id: int, version_id: int) -> Diff:
        """对比版本与当前笔记"""
        
    def generate_summary(self, diff: Diff) -> str:
        """生成变更摘要"""
```

---

## 📝 开发任务

### 阶段 1：基础架构（2026-04-21）

- [ ] 创建数据库表结构
- [ ] 实现 VersionService 基础 CRUD
- [ ] 实现自动保存版本（编辑时触发）

### 阶段 2：版本管理（2026-04-21）

- [ ] 实现版本列表查询
- [ ] 实现版本详情查看
- [ ] 实现版本恢复（回滚）
- [ ] 实现版本标签功能

### 阶段 3：版本对比（2026-04-22）

- [ ] 集成 diff 库（difflib）
- [ ] 实现版本对比功能
- [ ] 实现变更摘要生成
- [ ] 实现版本清理策略

### 阶段 4：测试与验收（2026-04-22-23）

- [ ] 编写单元测试（目标：10+ 测试用例）
- [ ] 性能测试（100 版本下查询延迟 < 50ms）
- [ ] 文档完善
- [ ] PR 提交

---

## 📊 验收标准

| 功能 | 测试用例 | 通过标准 |
|------|---------|---------|
| 自动保存 | 编辑笔记 3 次 | 生成 3 个版本 |
| 版本列表 | 查询历史版本 | 按时间倒序，包含版本号/时间/摘要 |
| 版本详情 | 获取指定版本 | 返回完整内容 |
| 版本恢复 | 恢复到 v2 | 当前笔记内容变为 v2 |
| 版本标签 | 标记 v3 为"重要" | 可通过标签筛选 |
| 版本对比 | 对比 v1 vs v3 | 显示增删内容（diff） |
| 变更摘要 | 自动生成 | "修改了标题，添加了 2 段内容" |
| 版本清理 | 保留最近 5 个 | 旧版本被删除 |

---

## 🔗 依赖关系

- ✅ PR-003: 笔记搜索功能（已完成）
- ⚪ PR-004: 版本历史（进行中）
- ⚪ PR-005: 导入导出（待启动）

---

## 💡 设计决策

### 1. 版本保存策略

**方案 A：每次编辑自动保存**
- ✅ 优点：不会丢失任何变更
- ⚠️ 缺点：版本数量增长快
- **选择：方案 A + 自动清理**

### 2. 版本对比实现

**方案 A：使用 difflib（Python 标准库）**
- ✅ 优点：零依赖，轻量
- ✅ 足够：个人笔记 diff 需求简单
- **选择：方案 A**

**方案 B：使用 diff-match-patch**
- ✅ 优点：更强大的 diff 算法
- ❌ 缺点：需要额外依赖
- 不选：过度设计

### 3. 版本清理策略

**默认保留：** 最近 10 个版本  
**标签版本：** 永久保留（除非手动删除）  
**清理触发：** 版本数 > 20 时自动清理

---

**最后更新:** 2026-04-21 00:05
