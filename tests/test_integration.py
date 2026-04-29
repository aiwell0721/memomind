"""
MemoMind Phase 3 端到端集成测试
测试所有模块协同工作：工作区/用户/成员/笔记/标签/链接/版本/活动日志/冲突/备份/REST API
"""

import pytest
import os
import tempfile
import shutil
import json
from pathlib import Path

from fastapi.testclient import TestClient

from core.database import Database
from core.workspace_service import WorkspaceService
from core.user_service import UserService
from core.activity_service import ActivityService
from core.conflict_service import ConflictService
from core.backup_service import BackupService
from core.search_service import SearchService
from core.tag_service import TagService
from core.link_service import LinkService
from core.version_service import VersionService
from core.api_server import create_app, generate_token


class TestFullWorkflow:
    """完整工作流集成测试"""
    
    def setup_method(self):
        """创建临时数据库和所有服务"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'integration.db')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        
        self.db = Database(self.db_path)
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)
        self.activity = ActivityService(self.db)
        self.conflict = ConflictService(self.db)
        self.backup = BackupService(self.db, self.backup_dir)
        self.search = SearchService(self.db)
        self.tags = TagService(self.db)
        self.links = LinkService(self.db)
        self.versions = VersionService(self.db)
    
    def teardown_method(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_team_workflow(self):
        """
        完整团队工作流：
        1. 创建用户
        2. 创建工作区
        3. 添加成员
        4. 创建笔记
        5. 添加标签
        6. 创建链接
        7. 保存版本
        8. 检测冲突
        9. 查看活动日志
        10. 备份
        """
        # 1. 创建用户
        alice_id = self.users.create_user("alice", "Alice Wang")
        bob_id = self.users.create_user("bob", "Bob Li")
        charlie_id = self.users.create_user("charlie", "Charlie Zhang")
        
        # 2. 创建工作区
        eng_ws_id = self.ws.create_workspace("工程部", "工程知识库")
        prod_ws_id = self.ws.create_workspace("产品部", "产品知识库")
        
        # 3. 添加成员
        self.users.add_member(eng_ws_id, alice_id, 'owner')
        self.users.add_member(eng_ws_id, bob_id, 'editor')
        self.users.add_member(prod_ws_id, charlie_id, 'owner')
        
        # 4. 创建笔记
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('API设计规范', 'RESTful API 设计原则...', ?)
        """, (eng_ws_id,))
        note1_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('用户认证方案', 'JWT 认证流程...', ?)
        """, (eng_ws_id,))
        note2_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('产品路线图', 'Q2 产品规划...', ?)
        """, (prod_ws_id,))
        note3_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.db.commit()
        
        # 5. 添加标签
        tag1_id = self.tags.create_tag("API")
        tag2_id = self.tags.create_tag("认证", tag1_id)  # 子标签
        tag3_id = self.tags.create_tag("产品")
        
        # 关联标签到笔记（用标签名称）
        self.tags.tag_note(note1_id, ['API'])
        self.tags.tag_note(note2_id, ['认证'])
        self.tags.tag_note(note3_id, ['产品'])
        
        # 6. 创建链接（API 设计规范 → 用户认证方案）
        self.links.update_note_links(note1_id, '参考 [[用户认证方案]] 了解更多')
        
        # 验证链接
        outgoing = self.links.get_outgoing_links(note1_id)
        assert len(outgoing) == 1
        assert outgoing[0].target_note_id == note2_id
        
        incoming = self.links.get_incoming_links(note2_id)
        assert len(incoming) == 1
        assert incoming[0].source_note_id == note1_id
        
        # 7. 保存版本
        ver1_id = self.versions.save_version(note1_id, 'API设计规范', '原始内容', [], '初始版本')
        ver2_id = self.versions.save_version(note1_id, 'API设计规范', '更新内容', [], '更新规范')
        
        versions = self.versions.get_versions(note1_id)
        assert len(versions) >= 2
        
        # 8. 检测冲突
        # 模拟：Alice 和 Bob 同时编辑同一笔记
        conflict_info = self.conflict.detect_conflict(
            note_id=note1_id,
            our_content='Alice 的修改版本',
            our_updated_at='2026-04-25 00:00:00',
            expected_updated_at='2026-04-25 01:00:00'  # Bob 已经修改过
        )
        assert conflict_info is not None
        
        conflict_id = self.conflict.record_conflict(
            note_id=note1_id, user_id=alice_id, strategy='latest-wins',
            base_content='基础版本',
            their_content='Bob 的版本',
            our_content='Alice 的版本'
        )
        
        resolved = self.conflict.resolve_latest_wins(conflict_id, use_ours=True)
        assert 'Alice' in resolved
        
        # 9. 记录活动日志
        self.activity.log('create', alice_id, eng_ws_id, note1_id, {'title': 'API设计规范'})
        self.activity.log('update', bob_id, eng_ws_id, note1_id)
        self.activity.log('tag', alice_id, eng_ws_id, note1_id, {'tag': 'API'})
        
        timeline = self.activity.get_timeline(workspace_id=eng_ws_id)
        assert len(timeline) >= 3
        
        note_history = self.activity.get_note_history(note1_id)
        assert len(note_history) >= 2
        
        # 10. 备份
        backup_result = self.backup.create_backup('集成测试备份')
        assert backup_result['note_count'] == 3
        assert backup_result['size_bytes'] > 0
        
        backups = self.backup.list_backups()
        assert len(backups) == 1
        
        # 11. 跨工作区搜索
        results = self.ws.search_across_workspaces("API")
        assert len(results) >= 1
        
        # 12. 统计验证
        stats = self.ws.get_workspace_stats(eng_ws_id)
        assert stats['note_count'] == 2
        
        user_ws = self.users.get_user_workspaces(alice_id)
        assert len(user_ws) == 1
        assert user_ws[0]['role'] == 'owner'
        
        conflict_stats = self.conflict.get_conflict_stats()
        assert conflict_stats['total'] >= 1
        assert conflict_stats['resolved'] >= 1
        
        backup_stats = self.backup.get_backup_stats()
        assert backup_stats['total_backups'] == 1
    
    def test_workspace_isolation(self):
        """工作区隔离测试"""
        # 创建两个工作区
        ws1 = self.ws.create_workspace("隔离测试A")
        ws2 = self.ws.create_workspace("隔离测试B")
        
        # 在不同工作区创建同名笔记（用英文内容，FTS5 支持）
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('test note', 'content A', ?)
        """, (ws1,))
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('test note', 'content B', ?)
        """, (ws2,))
        self.db.commit()
        
        # 验证隔离
        results_a = self.ws.search_across_workspaces("content", workspace_ids=[ws1])
        results_b = self.ws.search_across_workspaces("content", workspace_ids=[ws2])
        
        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0]['workspace_id'] == ws1
        assert results_b[0]['workspace_id'] == ws2
    
    def test_permission_check(self):
        """权限检查测试"""
        ws_id = self.ws.create_workspace("权限测试")
        owner_id = self.users.create_user("owner1")
        editor_id = self.users.create_user("editor1")
        viewer_id = self.users.create_user("viewer1")
        
        self.users.add_member(ws_id, owner_id, 'owner')
        self.users.add_member(ws_id, editor_id, 'editor')
        self.users.add_member(ws_id, viewer_id, 'viewer')
        
        # 编辑权限
        assert self.users.can_edit(owner_id, ws_id) is True
        assert self.users.can_edit(editor_id, ws_id) is True
        assert self.users.can_edit(viewer_id, ws_id) is False
        
        # 查看权限
        assert self.users.can_view(owner_id, ws_id) is True
        assert self.users.can_view(viewer_id, ws_id) is True
        
        # 非成员无权限
        stranger_id = self.users.create_user("stranger")
        assert self.users.can_view(stranger_id, ws_id) is False
        assert self.users.can_edit(stranger_id, ws_id) is False
    
    def test_backup_restore_cycle(self):
        """备份-恢复循环测试"""
        # 创建数据
        ws_id = self.ws.create_workspace("备份测试")
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('备份前笔记', '重要内容', ?)
        """, (ws_id,))
        self.db.commit()
        
        # 备份
        backup1 = self.backup.create_backup('备份1')
        assert backup1['note_count'] == 1
        
        # 修改数据
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('备份后笔记', '新增内容', ?)
        """, (ws_id,))
        self.db.commit()
        
        cursor = self.db.execute("SELECT COUNT(*) FROM notes")
        assert cursor.fetchone()[0] == 2
        
        # 恢复备份
        self.backup.restore_backup(backup1['id'])
        
        # 验证恢复（使用 backup 服务的 db 连接）
        cursor = self.backup.db.execute("SELECT COUNT(*) FROM notes")
        assert cursor.fetchone()[0] == 1  # 只有备份前的笔记
    
    def test_activity_audit_trail(self):
        """活动审计追踪测试"""
        ws_id = self.ws.create_workspace("审计测试")
        user_id = self.users.create_user("auditor")
        self.users.add_member(ws_id, user_id, 'owner')
        
        # 模拟一系列操作
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('审计笔记', '内容', ?)
        """, (ws_id,))
        note_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.db.commit()
        
        self.activity.log('create', user_id, ws_id, note_id)
        self.activity.log('update', user_id, ws_id, note_id)
        self.activity.log('tag', user_id, ws_id, note_id)
        
        # 验证审计追踪
        timeline = self.activity.get_timeline(workspace_id=ws_id)
        assert len(timeline) == 3
        
        # 按用户过滤
        user_activity = self.activity.get_user_activity(user_id)
        assert len(user_activity) == 3
        
        # 按笔记过滤
        note_history = self.activity.get_note_history(note_id)
        assert len(note_history) == 3
        
        # 按操作类型过滤
        creates = self.activity.get_timeline(action='create')
        assert len(creates) == 1
    
    def test_three_way_merge_scenarios(self):
        """三路合并场景测试"""
        base = "line1\nline2\nline3\nline4\n"
        
        # 场景1：非重叠修改
        their = "their_line1\nline2\nline3\nline4\n"
        our = "line1\nline2\nline3\nour_line4\n"
        
        cid = self.conflict.record_conflict(
            note_id=1, user_id=1, strategy='merge',
            base_content=base, their_content=their, our_content=our
        )
        resolved = self.conflict.resolve_three_way_merge(cid)
        assert len(resolved) > 0
        
        # 场景2：双方修改相同行
        their2 = "line1\ntheir_change\nline3\nline4\n"
        our2 = "line1\nour_change\nline3\nline4\n"
        
        cid2 = self.conflict.record_conflict(
            note_id=1, user_id=1, strategy='merge',
            base_content=base, their_content=their2, our_content=our2
        )
        resolved2 = self.conflict.resolve_three_way_merge(cid2)
        assert len(resolved2) > 0
    
    def test_tag_hierarchy(self):
        """标签层级测试"""
        root_id = self.tags.create_tag("技术")
        sub1_id = self.tags.create_tag("编程", root_id)
        sub2_id = self.tags.create_tag("数据库", root_id)
        sub3_id = self.tags.create_tag("SQL", sub2_id)
        
        tree = self.tags.get_tag_tree()
        assert len(tree) >= 1
        
        # 验证层级
        root = self.tags.get_tag(root_id)
        assert root.name == "技术"
        
        sub1 = self.tags.get_tag(sub1_id)
        assert sub1.parent_id == root_id


class TestRESTAPIIntegration:
    """REST API 集成测试"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'api_integration.db')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        
        self.app = create_app(self.db_path)
        self.client = TestClient(self.app)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _login(self, username="testuser"):
        """登录获取 Token"""
        self.client.post("/api/users", json={"username": username, "display_name": "Test"})
        resp = self.client.post("/api/auth/login", json={"username": username})
        return resp.json()["access_token"]
    
    def test_full_api_workflow(self):
        """完整 API 工作流"""
        token = self._login("alice")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. 创建工作区
        ws = self.client.post("/api/workspaces", json={
            "name": "API集成测试", "description": "测试工作区"
        }, headers=headers)
        assert ws.status_code == 201
        ws_id = ws.json()["id"]
        
        # 2. 注册用户并添加成员
        self.client.post("/api/users", json={"username": "bob"})
        users = self.client.get("/api/users", headers=headers).json()
        bob_id = [u for u in users if u['username'] == 'bob'][0]['id']
        
        self.client.post(f"/api/workspaces/{ws_id}/members", json={
            "user_id": bob_id, "role": "editor"
        }, headers=headers)
        
        # 3. 创建笔记
        note1 = self.client.post("/api/notes", json={
            "title": "集成测试笔记1", "content": "内容1", "workspace_id": ws_id
        }, headers=headers)
        assert note1.status_code == 201
        note1_id = note1.json()["id"]
        
        note2 = self.client.post("/api/notes", json={
            "title": "集成测试笔记2", "content": "内容2", "workspace_id": ws_id
        }, headers=headers)
        note2_id = note2.json()["id"]
        
        # 4. 创建标签
        tag = self.client.post("/api/tags", json={"name": "集成测试"}, headers=headers)
        assert tag.status_code == 201
        
        # 5. 搜索笔记
        search = self.client.post("/api/notes/search", json={
            "query": "集成", "limit": 10
        }, headers=headers)
        assert search.status_code == 200
        
        # 6. 获取活动日志
        activity = self.client.get("/api/activity", headers=headers)
        assert activity.status_code == 200
        
        # 7. 获取工作区统计
        ws_detail = self.client.get(f"/api/workspaces/{ws_id}", headers=headers)
        assert ws_detail.status_code == 200
        assert 'stats' in ws_detail.json()
        
        # 8. 创建备份
        backup = self.client.post("/api/backups", json={"description": "API测试备份"}, headers=headers)
        assert backup.status_code == 201
        
        # 9. 列出备份
        backups = self.client.get("/api/backups", headers=headers)
        assert backups.status_code == 200
        assert len(backups.json()) >= 1
        
        # 10. 获取冲突统计
        conflict_stats = self.client.get("/api/conflicts/stats", headers=headers)
        assert conflict_stats.status_code == 200
    
    def test_api_error_handling(self):
        """API 错误处理"""
        token = self._login()
        headers = {"Authorization": f"Bearer {token}"}
        
        # 不存在的笔记
        resp = self.client.get("/api/notes/9999", headers=headers)
        assert resp.status_code == 404
        
        # 不存在的用户
        resp = self.client.get("/api/users/9999", headers=headers)
        assert resp.status_code == 404
        
        # 无效 Token
        resp = self.client.get("/api/notes", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401
        
        # 无 Token
        resp = self.client.get("/api/notes")
        assert resp.status_code == 401


class TestCrossModuleInteraction:
    """跨模块交互测试"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'cross.db')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        
        self.db = Database(self.db_path)
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)
        self.activity = ActivityService(self.db)
        self.tags = TagService(self.db)
        self.links = LinkService(self.db)
        self.versions = VersionService(self.db)
    
    def teardown_method(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_note_lifecycle(self):
        """笔记生命周期：创建→标签→链接→版本→删除"""
        ws_id = self.ws.create_workspace("生命周期测试")
        user_id = self.users.create_user("lifecycle_user")
        self.users.add_member(ws_id, user_id, 'owner')
        
        # 创建
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('生命周期笔记', '初始内容', ?)
        """, (ws_id,))
        note_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.db.commit()
        
        self.activity.log('create', user_id, ws_id, note_id)
        
        # 添加标签
        tag_id = self.tags.create_tag("生命周期")
        self.tags.tag_note(note_id, ['生命周期'])
        self.activity.log('tag', user_id, ws_id, note_id)
        
        # 创建链接
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('目标笔记', '链接目标', ?)
        """, (ws_id,))
        target_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.db.commit()
        
        self.links.update_note_links(note_id, '参考 [[目标笔记]]')
        
        # 保存版本
        self.versions.save_version(note_id, '生命周期笔记', '初始内容', [], 'v1')
        
        # 更新
        self.db.execute("""
            UPDATE notes SET content = '更新内容', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (note_id,))
        self.db.commit()
        
        self.versions.save_version(note_id, '生命周期笔记', '更新内容', [], 'v2')
        self.activity.log('update', user_id, ws_id, note_id)
        
        # 验证
        versions = self.versions.get_versions(note_id)
        assert len(versions) >= 2
        
        outgoing = self.links.get_outgoing_links(note_id)
        assert len(outgoing) == 1
        
        timeline = self.activity.get_note_history(note_id)
        assert len(timeline) >= 3
        
        # 删除（先清理所有外键引用）
        self.db.execute("DELETE FROM note_links WHERE source_note_id = ? OR target_note_id = ?", (note_id, note_id))
        self.db.execute("DELETE FROM note_versions WHERE note_id = ?", (note_id,))
        self.db.execute("DELETE FROM activity_log WHERE note_id = ?", (note_id,))
        try:
            self.db.execute("DELETE FROM conflicts WHERE note_id = ?", (note_id,))
        except Exception:
            pass  # conflicts table may not exist
        self.db.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
        self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.db.commit()
        
        self.activity.log('delete', user_id, ws_id, note_id)
        
        cursor = self.db.execute("SELECT COUNT(*) FROM notes WHERE id = ?", (note_id,))
        assert cursor.fetchone()[0] == 0
    
    def test_workspace_lifecycle(self):
        """工作区生命周期：创建→添加成员→创建笔记→移动笔记→删除"""
        ws1 = self.ws.create_workspace("源工作区")
        ws2 = self.ws.create_workspace("目标工作区")
        user_id = self.users.create_user("ws_lifecycle")
        
        self.users.add_member(ws1, user_id, 'owner')
        self.users.add_member(ws2, user_id, 'owner')
        
        # 在 ws1 创建笔记
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('移动测试', '内容', ?)
        """, (ws1,))
        note_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.db.commit()
        
        # 移动笔记
        result = self.ws.move_note_to_workspace(note_id, ws2)
        assert result is True
        
        cursor = self.db.execute("SELECT workspace_id FROM notes WHERE id = ?", (note_id,))
        assert cursor.fetchone()['workspace_id'] == ws2
        
        # 删除工作区（先清理所有外键引用）
        self.db.execute("DELETE FROM activity_log WHERE workspace_id = ?", (ws1,))
        self.db.execute("DELETE FROM note_links WHERE source_note_id IN (SELECT id FROM notes WHERE workspace_id = ?)", (ws1,))
        self.db.execute("DELETE FROM note_versions WHERE note_id IN (SELECT id FROM notes WHERE workspace_id = ?)", (ws1,))
        self.ws.delete_workspace(ws1)
        
        ws = self.ws.get_workspace(ws1)
        assert ws is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
