"""
MemoMind REST API 测试 - PR-016
"""

import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from core.api_server import create_app


@pytest.fixture
def app():
    """创建测试应用（使用内存数据库）"""
    app = create_app(":memory:")
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def token(app):
    """获取测试 Token"""
    from core.api_server import generate_token
    return generate_token("testuser")


@pytest.fixture
def setup_data(client, token):
    """设置测试数据：注册用户、创建工作区、添加成员"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 注册用户
    client.post("/api/users", json={"username": "alice", "display_name": "Alice"})
    client.post("/api/users", json={"username": "bob", "display_name": "Bob"})
    
    # 创建工作区
    ws = client.post("/api/workspaces", json={"name": "工程部", "description": "工程知识库"}, headers=headers)
    ws_id = ws.json()["id"]
    
    # 添加成员
    alice = client.get("/api/users?limit=100", headers=headers).json()
    alice_id = [u for u in alice if u['username'] == 'alice'][0]['id']
    bob_id = [u for u in alice if u['username'] == 'bob'][0]['id']
    
    client.post(f"/api/workspaces/{ws_id}/members", json={"user_id": alice_id, "role": "owner"}, headers=headers)
    client.post(f"/api/workspaces/{ws_id}/members", json={"user_id": bob_id, "role": "editor"}, headers=headers)
    
    return {"ws_id": ws_id, "alice_id": alice_id, "bob_id": bob_id, "headers": headers}


class TestHealthAndAuth:
    """健康检查和认证测试"""
    
    def test_health_check(self, client):
        """健康检查（无需认证）"""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'healthy'
        assert data['version'] == '3.0.0'
    
    def test_login(self, client):
        """登录"""
        # 先注册用户
        client.post("/api/users", json={"username": "testuser", "display_name": "Test"})
        
        resp = client.post("/api/auth/login", json={"username": "testuser"})
        assert resp.status_code == 200
        data = resp.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'
    
    def test_login_nonexistent_user(self, client):
        """登录不存在的用户"""
        resp = client.post("/api/auth/login", json={"username": "nobody"})
        assert resp.status_code == 401
    
    def test_unauthorized_access(self, client):
        """未认证访问"""
        resp = client.get("/api/notes")
        assert resp.status_code == 401
    
    def test_invalid_token(self, client):
        """无效 Token"""
        resp = client.get("/api/notes", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401


class TestNotesAPI:
    """笔记 API 测试"""
    
    def test_create_note(self, client, setup_data):
        """创建笔记"""
        headers = setup_data["headers"]
        resp = client.post("/api/notes", json={
            "title": "测试笔记",
            "content": "这是测试内容",
            "tags": ["test", "api"],
            "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert 'id' in data
        assert data['title'] == "测试笔记"
    
    def test_list_notes(self, client, setup_data):
        """列出笔记"""
        headers = setup_data["headers"]
        
        # 先创建笔记
        client.post("/api/notes", json={
            "title": "笔记1", "content": "内容1", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        client.post("/api/notes", json={
            "title": "笔记2", "content": "内容2", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        
        resp = client.get("/api/notes", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
    
    def test_get_note(self, client, setup_data):
        """获取笔记详情"""
        headers = setup_data["headers"]
        
        create_resp = client.post("/api/notes", json={
            "title": "详情笔记", "content": "详细内容", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        note_id = create_resp.json()["id"]
        
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['title'] == "详情笔记"
        assert data['content'] == "详细内容"
    
    def test_get_note_not_found(self, client, setup_data):
        """获取不存在的笔记"""
        resp = client.get("/api/notes/999", headers=setup_data["headers"])
        assert resp.status_code == 404
    
    def test_update_note(self, client, setup_data):
        """更新笔记"""
        headers = setup_data["headers"]
        
        create_resp = client.post("/api/notes", json={
            "title": "旧标题", "content": "旧内容", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        note_id = create_resp.json()["id"]
        
        resp = client.put(f"/api/notes/{note_id}", json={
            "title": "新标题", "content": "新内容"
        }, headers=headers)
        assert resp.status_code == 200
        
        # 验证更新
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        data = resp.json()
        assert data['title'] == "新标题"
        assert data['content'] == "新内容"
    
    def test_delete_note(self, client, setup_data):
        """删除笔记"""
        headers = setup_data["headers"]
        
        create_resp = client.post("/api/notes", json={
            "title": "待删除", "content": "内容", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        note_id = create_resp.json()["id"]
        
        resp = client.delete(f"/api/notes/{note_id}", headers=headers)
        assert resp.status_code == 200
        
        # 验证删除
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        assert resp.status_code == 404
    
    def test_search_notes(self, client, setup_data):
        """搜索笔记"""
        headers = setup_data["headers"]
        
        client.post("/api/notes", json={
            "title": "Python Tutorial", "content": "Learn Python programming", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        client.post("/api/notes", json={
            "title": "Java Tutorial", "content": "Learn Java programming", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        
        resp = client.post("/api/notes/search", json={
            "query": "Python", "limit": 10
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


class TestTagsAPI:
    """标签 API 测试"""
    
    def test_create_tag(self, client, setup_data):
        """创建标签"""
        headers = setup_data["headers"]
        resp = client.post("/api/tags", json={"name": "API测试", "parent_id": None}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == "API测试"
    
    def test_list_tags(self, client, setup_data):
        """列出标签"""
        headers = setup_data["headers"]
        client.post("/api/tags", json={"name": "标签1"}, headers=headers)
        client.post("/api/tags", json={"name": "标签2"}, headers=headers)
        
        resp = client.get("/api/tags", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
    
    def test_delete_tag(self, client, setup_data):
        """删除标签"""
        headers = setup_data["headers"]
        create_resp = client.post("/api/tags", json={"name": "待删除标签"}, headers=headers)
        tag_id = create_resp.json()["id"]
        
        resp = client.delete(f"/api/tags/{tag_id}", headers=headers)
        assert resp.status_code == 200


class TestWorkspacesAPI:
    """工作区 API 测试"""
    
    def test_list_workspaces(self, client, setup_data):
        """列出工作区"""
        resp = client.get("/api/workspaces", headers=setup_data["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2  # 默认 + 工程部
    
    def test_get_workspace(self, client, setup_data):
        """获取工作区详情"""
        resp = client.get(f"/api/workspaces/{setup_data['ws_id']}", headers=setup_data["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data['name'] == "工程部"
        assert 'stats' in data
    
    def test_update_workspace(self, client, setup_data):
        """更新工作区"""
        headers = setup_data["headers"]
        ws_id = setup_data["ws_id"]
        
        resp = client.put(f"/api/workspaces/{ws_id}", json={
            "name": "新工程部", "description": "新描述"
        }, headers=headers)
        assert resp.status_code == 200
        
        # 验证更新
        resp = client.get(f"/api/workspaces/{ws_id}", headers=headers)
        assert resp.json()['name'] == "新工程部"
    
    def test_move_note(self, client, setup_data):
        """移动笔记"""
        headers = setup_data["headers"]
        
        # 创建第二个工作区
        ws2 = client.post("/api/workspaces", json={"name": "产品部"}, headers=headers)
        ws2_id = ws2.json()["id"]
        
        # 创建笔记
        note = client.post("/api/notes", json={
            "title": "移动笔记", "content": "内容", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        note_id = note.json()["id"]
        
        # 移动笔记
        resp = client.post(f"/api/notes/{note_id}/move?target_workspace_id={ws2_id}", headers=headers)
        assert resp.status_code == 200
        
        # 验证移动
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        assert resp.json()['workspace_id'] == ws2_id


class TestMembersAPI:
    """成员 API 测试"""
    
    def test_list_members(self, client, setup_data):
        """列出成员"""
        resp = client.get(f"/api/workspaces/{setup_data['ws_id']}/members", headers=setup_data["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
    
    def test_add_member(self, client, setup_data):
        """添加成员"""
        headers = setup_data["headers"]
        
        # 创建新用户
        client.post("/api/users", json={"username": "charlie"})
        users = client.get("/api/users", headers=headers).json()
        charlie_id = [u for u in users if u['username'] == 'charlie'][0]['id']
        
        # 创建新工作区
        ws = client.post("/api/workspaces", json={"name": "测试区"}, headers=headers)
        ws_id = ws.json()["id"]
        
        resp = client.post(f"/api/workspaces/{ws_id}/members", json={
            "user_id": charlie_id, "role": "viewer"
        }, headers=headers)
        assert resp.status_code == 201
    
    def test_remove_member(self, client, setup_data):
        """移除成员"""
        headers = setup_data["headers"]
        
        resp = client.delete(
            f"/api/workspaces/{setup_data['ws_id']}/members/{setup_data['bob_id']}",
            headers=headers
        )
        assert resp.status_code == 200
    
    def test_update_member_role(self, client, setup_data):
        """更新成员角色"""
        headers = setup_data["headers"]
        
        resp = client.put(
            f"/api/workspaces/{setup_data['ws_id']}/members/{setup_data['bob_id']}/role",
            json={"role": "viewer"},
            headers=headers
        )
        assert resp.status_code == 200


class TestActivityAPI:
    """活动日志 API 测试"""
    
    def test_get_activity(self, client, setup_data):
        """获取活动时间线"""
        resp = client.get("/api/activity", headers=setup_data["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
    
    def test_get_note_activity(self, client, setup_data):
        """笔记操作历史"""
        headers = setup_data["headers"]
        
        # 创建笔记
        note = client.post("/api/notes", json={
            "title": "活动测试", "content": "内容", "workspace_id": setup_data["ws_id"]
        }, headers=headers)
        note_id = note.json()["id"]
        
        resp = client.get(f"/api/notes/{note_id}/activity", headers=headers)
        assert resp.status_code == 200


class TestBackupAPI:
    """备份 API 测试（内存数据库不支持备份）"""
    
    def test_health_check_no_auth(self, client):
        """健康检查无需认证"""
        resp = client.get("/api/health")
        assert resp.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
