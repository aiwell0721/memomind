"""
MemoMind 用户系统测试 - PR-013
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.workspace_service import WorkspaceService
from core.user_service import UserService, User


class TestUserService:
    """用户服务基础测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)
    
    def teardown_method(self):
        self.db.close()
    
    def test_create_user(self):
        """注册用户"""
        user_id = self.users.create_user("alice", "Alice Wang")
        assert user_id >= 1
        
        user = self.users.get_user(user_id)
        assert user.username == "alice"
        assert user.display_name == "Alice Wang"
    
    def test_create_user_unique_username(self):
        """用户名唯一性"""
        self.users.create_user("bob")
        with pytest.raises(Exception):
            self.users.create_user("bob")
    
    def test_get_user_by_username(self):
        """根据用户名获取用户"""
        self.users.create_user("charlie", "Charlie Li")
        user = self.users.get_user_by_username("charlie")
        assert user is not None
        assert user.display_name == "Charlie Li"
    
    def test_get_user_not_found(self):
        """获取不存在的用户"""
        user = self.users.get_user(999)
        assert user is None
    
    def test_list_users(self):
        """列出所有用户"""
        self.users.create_user("user1", "User One")
        self.users.create_user("user2", "User Two")
        self.users.create_user("user3", "User Three")
        
        users = self.users.list_users()
        assert len(users) == 3
    
    def test_update_user(self):
        """更新用户信息"""
        user_id = self.users.create_user("dave", "Dave Old")
        self.users.update_user(user_id, display_name="Dave New")
        
        user = self.users.get_user(user_id)
        assert user.display_name == "Dave New"
    
    def test_update_user_noop(self):
        """更新用户（无变更）"""
        user_id = self.users.create_user("eve")
        result = self.users.update_user(user_id)
        assert result is False
    
    def test_delete_user(self):
        """删除用户"""
        user_id = self.users.create_user("frank")
        self.users.delete_user(user_id)
        
        user = self.users.get_user(user_id)
        assert user is None
    
    def test_delete_user_cleans_memberships(self):
        """删除用户清理成员关系"""
        user_id = self.users.create_user("grace")
        ws_id = self.ws.create_workspace("测试区")
        self.users.add_member(ws_id, user_id, 'editor')
        
        self.users.delete_user(user_id)
        
        member = self.users.get_member(ws_id, user_id)
        assert member is None


class TestWorkspaceMembership:
    """工作区成员管理测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)
    
    def teardown_method(self):
        self.db.close()
    
    def test_add_member(self):
        """添加成员"""
        ws_id = self.ws.create_workspace("工程部")
        user_id = self.users.create_user("alice")
        
        result = self.users.add_member(ws_id, user_id, 'editor')
        assert result is True
        
        member = self.users.get_member(ws_id, user_id)
        assert member is not None
        assert member['role'] == 'editor'
        assert member['username'] == 'alice'
    
    def test_add_member_invalid_role(self):
        """无效角色"""
        ws_id = self.ws.create_workspace("测试区")
        user_id = self.users.create_user("bob")
        
        with pytest.raises(ValueError, match="无效角色"):
            self.users.add_member(ws_id, user_id, 'admin')
    
    def test_add_member_nonexistent_workspace(self):
        """添加到不存在的工作区"""
        user_id = self.users.create_user("charlie")
        result = self.users.add_member(999, user_id)
        assert result is False
    
    def test_add_member_nonexistent_user(self):
        """添加不存在的用户"""
        ws_id = self.ws.create_workspace("测试区")
        result = self.users.add_member(ws_id, 999)
        assert result is False
    
    def test_remove_member(self):
        """移除成员"""
        ws_id = self.ws.create_workspace("产品部")
        user_id = self.users.create_user("dave")
        self.users.add_member(ws_id, user_id, 'viewer')
        
        self.users.remove_member(ws_id, user_id)
        member = self.users.get_member(ws_id, user_id)
        assert member is None
    
    def test_list_members(self):
        """列出工作区成员"""
        ws_id = self.ws.create_workspace("研发部")
        u1 = self.users.create_user("alice")
        u2 = self.users.create_user("bob")
        u3 = self.users.create_user("charlie")
        
        self.users.add_member(ws_id, u1, 'owner')
        self.users.add_member(ws_id, u2, 'editor')
        self.users.add_member(ws_id, u3, 'viewer')
        
        members = self.users.list_members(ws_id)
        assert len(members) == 3
    
    def test_get_user_workspaces(self):
        """获取用户所属工作区"""
        ws1 = self.ws.create_workspace("工作区A")
        ws2 = self.ws.create_workspace("工作区B")
        user_id = self.users.create_user("alice")
        
        self.users.add_member(ws1, user_id, 'owner')
        self.users.add_member(ws2, user_id, 'editor')
        
        workspaces = self.users.get_user_workspaces(user_id)
        assert len(workspaces) == 2
        roles = {w['role'] for w in workspaces}
        assert roles == {'owner', 'editor'}
    
    def test_update_member_role(self):
        """更新成员角色"""
        ws_id = self.ws.create_workspace("测试区")
        user_id = self.users.create_user("bob")
        self.users.add_member(ws_id, user_id, 'viewer')
        
        self.users.update_member_role(ws_id, user_id, 'editor')
        member = self.users.get_member(ws_id, user_id)
        assert member['role'] == 'editor'
    
    def test_can_edit(self):
        """权限检查 - 编辑"""
        ws_id = self.ws.create_workspace("测试区")
        u_owner = self.users.create_user("owner1")
        u_editor = self.users.create_user("editor1")
        u_viewer = self.users.create_user("viewer1")
        u_none = self.users.create_user("none1")
        
        self.users.add_member(ws_id, u_owner, 'owner')
        self.users.add_member(ws_id, u_editor, 'editor')
        self.users.add_member(ws_id, u_viewer, 'viewer')
        
        assert self.users.can_edit(u_owner, ws_id) is True
        assert self.users.can_edit(u_editor, ws_id) is True
        assert self.users.can_edit(u_viewer, ws_id) is False
        assert self.users.can_edit(u_none, ws_id) is False
    
    def test_can_view(self):
        """权限检查 - 查看"""
        ws_id = self.ws.create_workspace("测试区")
        u_member = self.users.create_user("member1")
        u_none = self.users.create_user("none1")
        
        self.users.add_member(ws_id, u_member, 'viewer')
        
        assert self.users.can_view(u_member, ws_id) is True
        assert self.users.can_view(u_none, ws_id) is False
    
    def test_get_workspace_owner(self):
        """获取工作区所有者"""
        ws_id = self.ws.create_workspace("测试区")
        u_owner = self.users.create_user("owner1")
        u_editor = self.users.create_user("editor1")
        
        self.users.add_member(ws_id, u_owner, 'owner')
        self.users.add_member(ws_id, u_editor, 'editor')
        
        owner = self.users.get_workspace_owner(ws_id)
        assert owner is not None
        assert owner.username == 'owner1'


class TestUserToDict:
    """User 模型转换测试"""
    
    def test_to_dict(self):
        user = User(id=1, username="test", display_name="Test User", created_at="2026-04-24")
        d = user.to_dict()
        assert d['id'] == 1
        assert d['username'] == "test"
        assert d['display_name'] == "Test User"
    
    def test_from_row(self):
        class FakeRow:
            def __getitem__(self, key):
                return {'id': 3, 'username': 'rowuser', 'display_name': 'Row User', 'created_at': '2026-01-01'}[key]
            def keys(self):
                return ['id', 'username', 'display_name', 'created_at']
        
        user = User.from_row(FakeRow())
        assert user.id == 3
        assert user.username == 'rowuser'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
