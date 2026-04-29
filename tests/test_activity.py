"""
MemoMind 活动日志测试 - PR-014
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.workspace_service import WorkspaceService
from core.user_service import UserService
from core.activity_service import ActivityService, ActivityLog


class TestActivityService:
    """活动日志基础测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)
        self.activity = ActivityService(self.db)
    
    def teardown_method(self):
        self.db.close()
    
    def test_log_action(self):
        """记录活动"""
        log_id = self.activity.log('create', user_id=1, note_id=1, 
                                    details={'title': 'Test Note'})
        assert log_id >= 1
        
        log = self.activity.get_log(log_id)
        assert log is not None
        assert log.action == 'create'
        assert log.details['title'] == 'Test Note'
    
    def test_log_invalid_action(self):
        """无效操作类型"""
        with pytest.raises(ValueError, match="无效操作"):
            self.activity.log('invalid_action')
    
    def test_log_with_workspace(self):
        """记录带工作区的活动"""
        ws_id = self.ws.create_workspace("工程部")
        log_id = self.activity.log('workspace_create', user_id=1, 
                                    workspace_id=ws_id)
        log = self.activity.get_log(log_id)
        assert log.workspace_id == ws_id
    
    def test_log_empty_details(self):
        """无详情的日志"""
        log_id = self.activity.log('delete', note_id=5)
        log = self.activity.get_log(log_id)
        assert log.details is None
    
    def test_get_log_not_found(self):
        """获取不存在的日志"""
        log = self.activity.get_log(999)
        assert log is None


class TestActivityTimeline:
    """活动时间线测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)
        self.activity = ActivityService(self.db)
        
        # 准备数据
        self.ws_id = self.ws.create_workspace("研发部")
        self.user_id = self.users.create_user("alice", "Alice")
        self.users.add_member(self.ws_id, self.user_id, 'owner')
    
    def teardown_method(self):
        self.db.close()
    
    def test_get_timeline(self):
        """获取时间线"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('update', self.user_id, self.ws_id, 1)
        self.activity.log('tag', self.user_id, self.ws_id, 1)
        
        timeline = self.activity.get_timeline()
        assert len(timeline) == 3
    
    def test_timeline_by_workspace(self):
        """按工作区过滤"""
        ws2 = self.ws.create_workspace("产品部")
        
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('create', self.user_id, ws2, 2)
        
        timeline = self.activity.get_timeline(workspace_id=self.ws_id)
        assert len(timeline) == 1
        assert timeline[0]['workspace_id'] == self.ws_id
    
    def test_timeline_by_user(self):
        """按用户过滤"""
        user2_id = self.users.create_user("bob")
        
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('create', user2_id, self.ws_id, 2)
        
        timeline = self.activity.get_timeline(user_id=self.user_id)
        assert len(timeline) == 1
        assert timeline[0]['user_id'] == self.user_id
    
    def test_timeline_by_note(self):
        """按笔记过滤"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('update', self.user_id, self.ws_id, 1)
        self.activity.log('create', self.user_id, self.ws_id, 2)
        
        timeline = self.activity.get_timeline(note_id=1)
        assert len(timeline) == 2
    
    def test_timeline_by_action(self):
        """按操作类型过滤"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('update', self.user_id, self.ws_id, 1)
        self.activity.log('delete', self.user_id, self.ws_id, 2)
        
        timeline = self.activity.get_timeline(action='update')
        assert len(timeline) == 1
        assert timeline[0]['action'] == 'update'
    
    def test_timeline_combined_filter(self):
        """组合过滤"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('update', self.user_id, self.ws_id, 1)
        self.activity.log('update', self.user_id, self.ws_id, 2)
        
        timeline = self.activity.get_timeline(note_id=1, action='update')
        assert len(timeline) == 1
    
    def test_timeline_contains_user_info(self):
        """时间线包含用户信息"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        
        timeline = self.activity.get_timeline()
        assert timeline[0]['username'] == 'alice'
        assert timeline[0]['display_name'] == 'Alice'
    
    def test_timeline_contains_workspace_info(self):
        """时间线包含工作区信息"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        
        timeline = self.activity.get_timeline()
        assert timeline[0]['workspace_name'] == '研发部'
    
    def test_get_note_history(self):
        """笔记操作历史"""
        self.activity.log('create', self.user_id, self.ws_id, 5)
        self.activity.log('update', self.user_id, self.ws_id, 5)
        self.activity.log('tag', self.user_id, self.ws_id, 5)
        
        history = self.activity.get_note_history(5)
        assert len(history) == 3
    
    def test_get_user_activity(self):
        """用户活动记录"""
        self.activity.log('create', self.user_id)
        self.activity.log('update', self.user_id)
        
        activity = self.activity.get_user_activity(self.user_id)
        assert len(activity) == 2
    
    def test_get_workspace_activity(self):
        """工作区活动记录"""
        self.activity.log('create', self.user_id, self.ws_id)
        self.activity.log('update', self.user_id, self.ws_id)
        
        activity = self.activity.get_workspace_activity(self.ws_id)
        assert len(activity) == 2
    
    def test_count_by_action(self):
        """按操作类型统计"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('create', self.user_id, self.ws_id, 2)
        self.activity.log('update', self.user_id, self.ws_id, 1)
        
        counts = self.activity.count_by_action(self.ws_id)
        assert counts['create'] == 2
        assert counts['update'] == 1
    
    def test_count_by_action_all(self):
        """全局统计"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        self.activity.log('delete', self.user_id, self.ws_id, 2)
        
        counts = self.activity.count_by_action()
        assert counts['create'] == 1
        assert counts['delete'] == 1
    
    def test_delete_old_logs(self):
        """清理旧日志"""
        self.activity.log('create', self.user_id, self.ws_id, 1)
        
        # 所有日志都是新的，不会删除
        deleted = self.activity.delete_old_logs(days=90)
        assert deleted == 0


class TestActivityLogToDict:
    """ActivityLog 模型转换测试"""
    
    def test_to_dict(self):
        log = ActivityLog(
            id=1, user_id=1, workspace_id=1, note_id=1,
            action='create', details={'title': 'Test'},
            created_at='2026-04-24'
        )
        d = log.to_dict()
        assert d['action'] == 'create'
        assert d['details']['title'] == 'Test'
    
    def test_from_row(self):
        class FakeRow:
            def __getitem__(self, key):
                return {
                    'id': 2, 'user_id': 3, 'workspace_id': 1, 'note_id': 5,
                    'action': 'update', 'details': '{"field": "title"}',
                    'created_at': '2026-04-24'
                }[key]
            def keys(self):
                return ['id', 'user_id', 'workspace_id', 'note_id', 'action', 'details', 'created_at']
        
        log = ActivityLog.from_row(FakeRow())
        assert log.action == 'update'
        assert log.details['field'] == 'title'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
