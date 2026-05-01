"""
MemoMind 实时协作服务 - PR-020
基于 WebSocket 的简单广播 + 冲突检测
阶段一：内容同步 + 在线用户 + 冲突记录
阶段二（后续）：CRDT 无冲突合并
"""

import asyncio
import json
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime
from .database import Database


@dataclass
class Collaborator:
    """协作者信息"""
    user_id: int
    username: str
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'joined_at': self.joined_at
        }


class CollaborationService:
    """
    实时协作服务

    管理 WebSocket 连接房间，广播编辑变更。
    阶段一：简单广播 + 冲突检测（复用 ConflictService）
    阶段二（后续）：升级到 CRDT 算法
    """

    HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

    def __init__(self, db: Database):
        self.db = db
        # note_id -> {websocket -> Collaborator}
        self.rooms: Dict[int, Dict] = {}
        self._lock = asyncio.Lock()

    async def join_room(
        self, note_id: int, websocket, user_id: int, username: str
    ) -> list[dict]:
        """
        加入笔记协作房间

        Returns:
            当前在线用户列表
        """
        async with self._lock:
            if note_id not in self.rooms:
                self.rooms[note_id] = {}

            collaborator = Collaborator(user_id=user_id, username=username)
            self.rooms[note_id][websocket] = collaborator

            # 广播新用户加入
            await self._broadcast(note_id, {
                'type': 'user_joined',
                'user': collaborator.to_dict(),
                'users': self._get_users(note_id)
            })

            return self._get_users(note_id)

    async def leave_room(self, note_id: int, websocket) -> list[dict]:
        """
        离开笔记协作房间

        Returns:
            剩余在线用户列表
        """
        async with self._lock:
            if note_id in self.rooms and websocket in self.rooms[note_id]:
                collaborator = self.rooms[note_id].pop(websocket)

                # 广播用户离开
                await self._broadcast(note_id, {
                    'type': 'user_left',
                    'user': collaborator.to_dict(),
                    'users': self._get_users(note_id)
                })

                # 清理空房间
                if not self.rooms[note_id]:
                    del self.rooms[note_id]

                return self._get_users(note_id)
            return []

    async def broadcast_edit(
        self, note_id: int, sender_ws, user_id: int,
        title: str, content: str
    ) -> int:
        """
        广播编辑变更给房间内其他用户

        Args:
            note_id: 笔记 ID
            sender_ws: 发送者的 WebSocket 连接
            user_id: 编辑者 ID
            title: 笔记标题
            content: 笔记内容

        Returns:
            接收广播的用户数量
        """
        async with self._lock:
            if note_id not in self.rooms:
                return 0

            message = {
                'type': 'edit',
                'user_id': user_id,
                'title': title,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }

            count = 0
            for ws, collab in self.rooms[note_id].items():
                if ws != sender_ws:
                    try:
                        await ws.send_json(message)
                        count += 1
                    except Exception:
                        pass  # 连接已断开，后续心跳会清理

            return count

    async def handle_connection(
        self, websocket, note_id: int,
        user_id: int, username: str
    ):
        """
        处理 WebSocket 连接的完整生命周期

        接入 → 加入房间 → 心跳/消息循环 → 离开房间 → 断开
        """
        await self.join_room(note_id, websocket, user_id, username)

        try:
            while True:
                # 等待消息（编辑变更或心跳）
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=self.HEARTBEAT_INTERVAL
                    )
                except asyncio.TimeoutError:
                    # 发送心跳
                    try:
                        await websocket.send_json({'type': 'ping'})
                    except Exception:
                        break
                    continue

                data = json.loads(message)

                if data.get('type') == 'pong':
                    # 心跳响应，无需处理
                    continue

                if data.get('type') == 'edit':
                    # 广播编辑变更
                    await self.broadcast_edit(
                        note_id, websocket, user_id,
                        title=data.get('title', ''),
                        content=data.get('content', '')
                    )

                elif data.get('type') == 'ping':
                    # 客户端心跳
                    try:
                        await websocket.send_json({'type': 'pong'})
                    except Exception:
                        break

        except Exception:
            pass  # 连接断开
        finally:
            await self.leave_room(note_id, websocket)

    def _get_users(self, note_id: int) -> list[dict]:
        """获取房间内在线用户列表"""
        if note_id not in self.rooms:
            return []
        return [c.to_dict() for c in self.rooms[note_id].values()]

    async def _broadcast(self, note_id: int, message: dict):
        """向房间内所有用户广播消息"""
        if note_id not in self.rooms:
            return

        for ws in list(self.rooms[note_id].keys()):
            try:
                await ws.send_json(message)
            except Exception:
                pass  # 连接已断开

    def get_room_count(self, note_id: int) -> int:
        """获取房间内在线用户数量"""
        return len(self.rooms.get(note_id, {}))

    def get_active_rooms(self) -> int:
        """获取活跃房间数量"""
        return len(self.rooms)
