"""
MemoMind 实时协作测试 - PR-020
"""

import pytest
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.collaboration_service import CollaborationService, Collaborator


class TestCollaborationService:
    """协作服务单元测试"""

    @pytest.fixture
    def db(self):
        return Database(":memory:")

    @pytest.fixture
    def service(self, db):
        return CollaborationService(db)

    def test_initial_state(self, service):
        """初始状态：无活跃房间"""
        assert service.get_active_rooms() == 0
        assert service.get_room_count(1) == 0

    def test_join_and_leave_room(self, service):
        """加入和离开房间"""
        # 模拟 WebSocket 对象（用普通对象代替）
        class FakeWs:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws1 = FakeWs()
        ws2 = FakeWs()

        async def run():
            # 用户1加入
            users = await service.join_room(1, ws1, 1, "alice")
            assert len(users) == 1
            assert users[0]['username'] == 'alice'
            assert service.get_active_rooms() == 1
            assert service.get_room_count(1) == 1

            # 用户2加入
            users = await service.join_room(1, ws2, 2, "bob")
            assert len(users) == 2
            assert service.get_room_count(1) == 2

            # 检查广播消息
            assert len(ws1.sent) > 0
            assert ws1.sent[-1]['type'] == 'user_joined'
            assert ws1.sent[-1]['user']['username'] == 'bob'

            # 用户1离开
            users = await service.leave_room(1, ws1)
            assert len(users) == 1
            assert users[0]['username'] == 'bob'
            assert service.get_room_count(1) == 1

            # 检查广播消息
            assert ws2.sent[-1]['type'] == 'user_left'
            assert ws2.sent[-1]['user']['username'] == 'alice'

            # 用户2离开，房间清理
            users = await service.leave_room(1, ws2)
            assert service.get_active_rooms() == 0

        asyncio.run(run())

    def test_broadcast_edit(self, service):
        """广播编辑变更"""
        class FakeWs:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws_sender = FakeWs()
        ws_receiver = FakeWs()

        async def run():
            await service.join_room(1, ws_sender, 1, "alice")
            await service.join_room(1, ws_receiver, 2, "bob")

            # 发送者广播编辑
            count = await service.broadcast_edit(1, ws_sender, 1, "标题", "内容")
            assert count == 1  # 只有接收者收到

            # 检查接收者收到编辑消息
            assert len(ws_receiver.sent) > 0
            edit_msg = ws_receiver.sent[-1]
            assert edit_msg['type'] == 'edit'
            assert edit_msg['title'] == '标题'
            assert edit_msg['content'] == '内容'
            assert edit_msg['user_id'] == 1

            # 发送者不应收到自己的广播
            sender_edits = [m for m in ws_sender.sent if m.get('type') == 'edit']
            assert len(sender_edits) == 0

        asyncio.run(run())

    def test_empty_room_broadcast(self, service):
        """空房间广播无影响"""
        class FakeWs:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        async def run():
            count = await service.broadcast_edit(999, FakeWs(), 1, "标题", "内容")
            assert count == 0

        asyncio.run(run())

    def test_multiple_rooms(self, service):
        """多个独立房间互不干扰"""
        class FakeWs:
            def __init__(self):
                self.sent = []
            async def send_json(self, data):
                self.sent.append(data)

        ws1 = FakeWs()
        ws2 = FakeWs()

        async def run():
            await service.join_room(1, ws1, 1, "alice")
            await service.join_room(2, ws2, 2, "bob")

            assert service.get_active_rooms() == 2
            assert service.get_room_count(1) == 1
            assert service.get_room_count(2) == 1

            # 房间1的广播不影响房间2
            count = await service.broadcast_edit(1, ws1, 1, "标题", "内容")
            assert count == 0  # 房间1只有发送者

            await service.leave_room(1, ws1)
            await service.leave_room(2, ws2)
            assert service.get_active_rooms() == 0

        asyncio.run(run())

    def test_collaborator_to_dict(self):
        """Collaborator 序列化"""
        c = Collaborator(user_id=42, username="alice")
        d = c.to_dict()
        assert d['user_id'] == 42
        assert d['username'] == 'alice'
        assert 'joined_at' in d


class TestWebSocketEndpoint:
    """WebSocket 端点集成测试"""

    @pytest.fixture
    def app(self):
        from core.api_server import create_app, generate_token
        app = create_app(":memory:")
        return app

    @pytest.fixture
    def client(self, app):
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_websocket_requires_token(self, client):
        """WebSocket 需要 Token"""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/notes/1?token=invalid"):
                pass

    def test_websocket_nonexistent_note(self, client):
        """不存在的笔记"""
        from core.api_server import generate_token
        token = generate_token("testuser")
        # 先注册用户
        client.post("/api/users", json={"username": "testuser", "display_name": "Test"})

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/notes/999?token={token}"):
                pass

    def test_websocket_connect_and_edit(self, client):
        """WebSocket 连接 + 编辑广播"""
        from core.api_server import generate_token
        # 注册用户
        client.post("/api/users", json={"username": "alice", "display_name": "Alice"})
        token = generate_token("alice")

        # 创建笔记
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/notes", json={
            "title": "测试笔记",
            "content": "初始内容",
            "tags": []
        }, headers=headers)
        note_id = resp.json()["id"]

        # WebSocket 连接
        with client.websocket_connect(f"/ws/notes/{note_id}?token={token}") as ws:
            # 发送编辑消息
            ws.send_json({"type": "edit", "title": "新标题", "content": "新内容"})

            # 收到用户加入消息
            data = ws.receive_json()
            assert data['type'] == 'user_joined'
            assert len(data['users']) == 1

            # 收到 ping 心跳
            data = ws.receive_json()
            assert data['type'] == 'ping'
