"""
MemoMind L1 角色场景流转测试 - PR-026
基于 docs-project/02-business-logic/ 中的业务规则和用户角色定义
覆盖：完整用户生命周期、多角色权限边界、工作区协作流转
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.workspace_service import WorkspaceService
from core.user_service import UserService


class TestUserLifecycleFlow:
    """L1: 用户完整生命周期流转"""

    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)

    def teardown_method(self):
        self.db.close()

    def test_register_login_delete_lifecycle(self):
        """用户注册 → 验证信息 → 删除 → 验证清理"""
        # 注册
        user_id = self.users.create_user("alice", "pass123", "Alice")
        assert user_id >= 1

        # 查询验证
        user = self.users.get_user(user_id)
        assert user.username == "alice"
        assert user.display_name == "Alice"

        # 列出验证
        all_users = self.users.list_users()
        assert any(u.id == user_id for u in all_users)

        # 删除
        self.users.delete_user(user_id)

        # 验证清理
        assert self.users.get_user(user_id) is None
        assert self.users.get_user_by_username("alice") is None

    def test_duplicate_username_rejection(self):
        """重复用户名拒绝"""
        self.users.create_user("bob", "pass123")
        with pytest.raises(Exception):
            self.users.create_user("bob", "different_pass")

    def test_password_hashing_isolation(self):
        """密码哈希隔离：相同密码产生不同哈希"""
        self.users.create_user("user1", "same_password")
        self.users.create_user("user2", "same_password")

        u1 = self.users.get_user_by_username("user1")
        u2 = self.users.get_user_by_username("user2")

        # 两个用户的密码哈希应该不同（bcrypt 使用随机 salt）
        assert u1.password_hash != u2.password_hash


class TestRolePermissionFlow:
    """L1: 多角色权限边界流转"""

    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)

    def teardown_method(self):
        self.db.close()

    def test_owner_full_access(self):
        """owner：创建/编辑/删除工作区 + 管理成员"""
        ws_id = self.ws.create_workspace("Owner Workspace")
        owner_id = self.users.create_user("owner", "pass123")
        self.users.add_member(ws_id, owner_id, 'owner')

        # owner 可编辑工作区
        self.ws.update_workspace(ws_id, name="Updated Workspace")
        ws = self.ws.get_workspace_by_name("Updated Workspace")
        assert ws is not None

        # owner 可添加/移除成员
        editor_id = self.users.create_user("editor", "pass123")
        self.users.add_member(ws_id, editor_id, 'editor')
        assert self.users.get_member(ws_id, editor_id) is not None

        self.users.remove_member(ws_id, editor_id)
        assert self.users.get_member(ws_id, editor_id) is None

        # owner 可更新成员角色
        viewer_id = self.users.create_user("viewer", "pass123")
        self.users.add_member(ws_id, viewer_id, 'viewer')
        self.users.update_member_role(ws_id, viewer_id, 'editor')
        member = self.users.get_member(ws_id, viewer_id)
        assert member['role'] == 'editor'

    def test_editor_cannot_delete_workspace(self):
        """editor：可编辑笔记但不可删除工作区"""
        ws_id = self.ws.create_workspace("Editor Workspace")
        editor_id = self.users.create_user("editor", "pass123")
        self.users.add_member(ws_id, editor_id, 'editor')

        # editor 可以查看工作区
        assert self.users.can_view(editor_id, ws_id) is True
        # editor 可以编辑
        assert self.users.can_edit(editor_id, ws_id) is True

        # 但 editor 不是工作区成员时不可查看/编辑
        other_id = self.users.create_user("other", "pass123")
        assert self.users.can_view(other_id, ws_id) is False
        assert self.users.can_edit(other_id, ws_id) is False

    def test_viewer_readonly(self):
        """viewer：只读，不可编辑"""
        ws_id = self.ws.create_workspace("Viewer Workspace")
        viewer_id = self.users.create_user("viewer", "pass123")
        self.users.add_member(ws_id, viewer_id, 'viewer')

        # viewer 可查看
        assert self.users.can_view(viewer_id, ws_id) is True
        # viewer 不可编辑
        assert self.users.can_edit(viewer_id, ws_id) is False

    def test_non_member_no_access(self):
        """非成员：无任何权限"""
        ws_id = self.ws.create_workspace("Private Workspace")
        self.users.create_user("owner", "pass123")
        outsider_id = self.users.create_user("outsider", "pass123")

        assert self.users.can_view(outsider_id, ws_id) is False
        assert self.users.can_edit(outsider_id, ws_id) is False

    def test_role_escalation(self):
        """角色升级：viewer → editor → owner 权限逐步扩展"""
        ws_id = self.ws.create_workspace("Escalation Workspace")
        user_id = self.users.create_user("escalator", "pass123")

        # viewer 阶段
        self.users.add_member(ws_id, user_id, 'viewer')
        assert self.users.can_view(user_id, ws_id) is True
        assert self.users.can_edit(user_id, ws_id) is False

        # editor 阶段
        self.users.update_member_role(ws_id, user_id, 'editor')
        assert self.users.can_view(user_id, ws_id) is True
        assert self.users.can_edit(user_id, ws_id) is True

        # owner 阶段
        self.users.update_member_role(ws_id, user_id, 'owner')
        assert self.users.can_view(user_id, ws_id) is True
        assert self.users.can_edit(user_id, ws_id) is True


class TestWorkspaceCollaborationFlow:
    """L1: 工作区协作场景流转"""

    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)

    def teardown_method(self):
        self.db.close()

    def test_full_collaboration_flow(self):
        """完整协作：创建者 → 邀请成员 → 不同角色权限验证"""
        # Step 1: 创建工作区
        ws_id = self.ws.create_workspace("协作空间")
        ws = self.ws.get_workspace_by_name("协作空间")
        assert ws is not None
        assert ws.name == "协作空间"

        # Step 2: 创建用户
        owner_id = self.users.create_user("creator", "pass123", "创建者")
        editor_id = self.users.create_user("writer", "pass123", "编辑者")
        viewer_id = self.users.create_user("reader", "pass123", "查看者")
        outsider_id = self.users.create_user("stranger", "pass123", "局外人")

        # Step 3: 添加成员
        self.users.add_member(ws_id, owner_id, 'owner')
        self.users.add_member(ws_id, editor_id, 'editor')
        self.users.add_member(ws_id, viewer_id, 'viewer')

        # Step 4: 验证权限矩阵
        # Owner: 全部权限
        assert self.users.can_edit(owner_id, ws_id) is True
        assert self.users.can_view(owner_id, ws_id) is True

        # Editor: 可查看和编辑
        assert self.users.can_edit(editor_id, ws_id) is True
        assert self.users.can_view(editor_id, ws_id) is True

        # Viewer: 只可查看
        assert self.users.can_edit(viewer_id, ws_id) is False
        assert self.users.can_view(viewer_id, ws_id) is True

        # Outsider: 无权限
        assert self.users.can_edit(outsider_id, ws_id) is False
        assert self.users.can_view(outsider_id, ws_id) is False

        # Step 5: 成员列表正确
        members = self.users.list_members(ws_id)
        assert len(members) == 3
        member_ids = {m['user_id'] for m in members}
        assert owner_id in member_ids
        assert editor_id in member_ids
        assert viewer_id in member_ids

        # Step 6: 用户获取自己的工作区
        owner_workspaces = self.users.get_user_workspaces(owner_id)
        assert len(owner_workspaces) == 1
        assert owner_workspaces[0]['workspace_name'] == "协作空间"
        assert owner_workspaces[0]['role'] == 'owner'

    def test_multi_workspace_user(self):
        """用户同时属于多个工作区"""
        ws1 = self.ws.create_workspace("项目A")
        ws2 = self.ws.create_workspace("项目B")
        ws3 = self.ws.create_workspace("项目C")

        user_id = self.users.create_user("multi", "pass123")

        self.users.add_member(ws1, user_id, 'owner')
        self.users.add_member(ws2, user_id, 'editor')
        self.users.add_member(ws3, user_id, 'viewer')

        workspaces = self.users.get_user_workspaces(user_id)
        assert len(workspaces) == 3

        # 每个工作区角色不同
        roles = {w['workspace_name']: w['role'] for w in workspaces}
        assert roles["项目A"] == 'owner'
        assert roles["项目B"] == 'editor'
        assert roles["项目C"] == 'viewer'

        # 在每个工作区的权限正确
        assert self.users.can_edit(user_id, ws1) is True
        assert self.users.can_edit(user_id, ws2) is True
        assert self.users.can_edit(user_id, ws3) is False

    def test_workspace_deletion_cascades(self):
        """工作区删除时级联清理笔记和成员关系"""
        ws_id = self.ws.create_workspace("临时空间")
        user_id = self.users.create_user("temp", "pass123")
        self.users.add_member(ws_id, user_id, 'owner')

        # 删除工作区
        self.ws.delete_workspace(ws_id)

        # 成员关系被清理
        member = self.users.get_member(ws_id, user_id)
        assert member is None

    def test_delete_user_removes_memberships(self):
        """删除用户时自动移除所有成员关系"""
        ws1 = self.ws.create_workspace("空间A")
        ws2 = self.ws.create_workspace("空间B")

        user_id = self.users.create_user("leaver", "pass123")
        self.users.add_member(ws1, user_id, 'owner')
        self.users.add_member(ws2, user_id, 'editor')

        # 删除用户
        self.users.delete_user(user_id)

        # 所有成员关系被清理
        assert self.users.get_member(ws1, user_id) is None
        assert self.users.get_member(ws2, user_id) is None

    def test_workspace_name_uniqueness(self):
        """工作区名称唯一约束"""
        self.ws.create_workspace("UniqueWS")
        with pytest.raises(Exception):
            self.ws.create_workspace("UniqueWS")

    def test_workspace_not_found(self):
        """查询不存在的工作区"""
        ws = self.ws.get_workspace_by_name("NonExistent")
        assert ws is None

    def test_invalid_role_rejection(self):
        """无效角色被拒绝"""
        ws_id = self.ws.create_workspace("StrictWS")
        user_id = self.users.create_user("strict", "pass123")

        with pytest.raises(ValueError, match="无效角色"):
            self.users.add_member(ws_id, user_id, 'admin')

        with pytest.raises(ValueError, match="无效角色"):
            self.users.add_member(ws_id, user_id, 'superuser')


class TestCrossWorkspaceFlow:
    """L1: 跨工作区场景流转"""

    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)

    def teardown_method(self):
        self.db.close()

    def test_search_across_workspaces(self):
        """跨工作区搜索返回结果（使用 ASCII 关键词验证跨区逻辑）"""
        ws1 = self.ws.create_workspace("技术部")
        ws2 = self.ws.create_workspace("产品部")

        # 在不同工作区创建笔记（包含 ASCII 关键词以匹配 FTS5）
        self.db.execute(
            "INSERT INTO notes (title, content, tags, workspace_id) VALUES (?, ?, ?, ?)",
            ("技术笔记", "Python FastAPI SQLite", "[]", ws1)
        )
        self.db.execute(
            "INSERT INTO notes (title, content, tags, workspace_id) VALUES (?, ?, ?, ?)",
            ("产品笔记", "user requirements market analysis", "[]", ws2)
        )
        self.db.commit()

        # 跨工作区搜索 - 技术关键词
        results = self.ws.search_across_workspaces("Python")
        assert len(results) >= 1
        assert results[0]['title'] == "技术笔记"
        assert results[0]['workspace_name'] == "技术部"

        # 跨工作区搜索 - 产品关键词
        results2 = self.ws.search_across_workspaces("user")
        assert len(results2) >= 1
        assert results2[0]['title'] == "产品笔记"
        assert results2[0]['workspace_name'] == "产品部"

        # 搜索结果包含工作区信息
        assert 'workspace_id' in results[0]
        assert 'workspace_name' in results[0]

    def test_move_note_between_workspaces(self):
        """笔记在不同工作区之间移动"""
        ws1 = self.ws.create_workspace("源工作区")
        ws2 = self.ws.create_workspace("目标工作区")

        # 在源工作区创建笔记
        cursor = self.db.execute(
            "INSERT INTO notes (title, content, tags, workspace_id) VALUES (?, ?, ?, ?)",
            ("移动笔记", "内容", "[]", ws1)
        )
        note_id = cursor.lastrowid
        self.db.commit()

        # 验证初始位置
        row = self.db.execute("SELECT workspace_id FROM notes WHERE id = ?", (note_id,)).fetchone()
        assert row['workspace_id'] == ws1

        # 移动到目标工作区
        self.ws.move_note_to_workspace(note_id, ws2)

        # 验证新位置
        row = self.db.execute("SELECT workspace_id FROM notes WHERE id = ?", (note_id,)).fetchone()
        assert row['workspace_id'] == ws2

    def test_move_note_to_nonexistent_workspace(self):
        """移动到不存在的工作区"""
        cursor = self.db.execute(
            "INSERT INTO notes (title, content, tags, workspace_id) VALUES (?, ?, ?, ?)",
            ("孤立笔记", "内容", "[]", None)
        )
        note_id = cursor.lastrowid
        self.db.commit()

        with pytest.raises(Exception):
            self.ws.move_note(note_id, 99999)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
