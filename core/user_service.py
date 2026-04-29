"""
MemoMind 用户系统服务
支持用户注册、角色管理、工作区成员管理
"""

import json
from typing import List, Optional, Dict
from dataclasses import dataclass
from .database import Database


@dataclass
class User:
    """用户数据模型"""
    id: Optional[int] = None
    username: str = ""
    display_name: str = ""
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_row(cls, row) -> 'User':
        return cls(
            id=row['id'],
            username=row['username'],
            display_name=row['display_name'] or '',
            created_at=row['created_at']
        )


class UserService:
    """用户管理服务"""
    
    VALID_ROLES = {'owner', 'editor', 'viewer'}
    
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()
    
    def _init_schema(self):
        """初始化用户相关表结构"""
        cursor = self.db.conn
        
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建工作区成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspace_members (
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                role TEXT NOT NULL DEFAULT 'viewer'
                    CHECK (role IN ('owner', 'editor', 'viewer')),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (workspace_id, user_id)
            )
        """)
        
        # 检查 notes 表是否已有 created_by 列
        info_cursor = self.db.conn.cursor()
        info_cursor.execute("PRAGMA table_info(notes)")
        columns = [col['name'] for col in info_cursor.fetchall()]
        
        if 'created_by' not in columns:
            cursor.execute("""
                ALTER TABLE notes ADD COLUMN created_by INTEGER 
                REFERENCES users(id)
            """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workspace_members_user
            ON workspace_members(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_created_by
            ON notes(created_by)
        """)
        
        self.db.commit()
    
    def create_user(self, username: str, display_name: str = '') -> int:
        """
        注册用户
        
        Args:
            username: 用户名（唯一）
            display_name: 显示名称
            
        Returns:
            新用户 ID
        """
        cursor = self.db.execute("""
            INSERT INTO users (username, display_name)
            VALUES (?, ?)
        """, (username, display_name))
        self.db.commit()
        return cursor.lastrowid
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        获取用户详情
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户对象，不存在返回 None
        """
        cursor = self.db.execute("""
            SELECT * FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        return User.from_row(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户对象，不存在返回 None
        """
        cursor = self.db.execute("""
            SELECT * FROM users WHERE username = ?
        """, (username,))
        row = cursor.fetchone()
        return User.from_row(row) if row else None
    
    def list_users(self, limit: int = 100) -> List[User]:
        """
        列出所有用户
        
        Args:
            limit: 返回数量限制
            
        Returns:
            用户列表
        """
        cursor = self.db.execute("""
            SELECT * FROM users
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [User.from_row(row) for row in cursor.fetchall()]
    
    def update_user(self, user_id: int, display_name: str = None) -> bool:
        """
        更新用户信息
        
        Args:
            user_id: 用户 ID
            display_name: 新显示名称
            
        Returns:
            是否成功
        """
        if display_name is None:
            return False
        
        self.db.execute("""
            UPDATE users SET display_name = ? WHERE id = ?
        """, (display_name, user_id))
        self.db.commit()
        return True
    
    def delete_user(self, user_id: int) -> bool:
        """
        删除用户（级联清理成员关系）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            是否成功
        """
        # 清理成员关系
        self.db.execute("""
            DELETE FROM workspace_members WHERE user_id = ?
        """, (user_id,))
        
        # 将用户创建的笔记的 created_by 设为 NULL
        self.db.execute("""
            UPDATE notes SET created_by = NULL WHERE created_by = ?
        """, (user_id,))
        
        # 删除用户
        self.db.execute("""
            DELETE FROM users WHERE id = ?
        """, (user_id,))
        
        self.db.commit()
        return True
    
    def add_member(self, workspace_id: int, user_id: int, role: str = 'viewer') -> bool:
        """
        添加工作区成员
        
        Args:
            workspace_id: 工作区 ID
            user_id: 用户 ID
            role: 角色（owner/editor/viewer）
            
        Returns:
            是否成功
        """
        if role not in self.VALID_ROLES:
            raise ValueError(f"无效角色: {role}，有效值: {self.VALID_ROLES}")
        
        # 验证工作区和用户存在
        ws = self.db.execute("SELECT id FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
        user = self.db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not ws or not user:
            return False
        
        self.db.execute("""
            INSERT OR REPLACE INTO workspace_members (workspace_id, user_id, role)
            VALUES (?, ?, ?)
        """, (workspace_id, user_id, role))
        self.db.commit()
        return True
    
    def remove_member(self, workspace_id: int, user_id: int) -> bool:
        """
        移除工作区成员
        
        Args:
            workspace_id: 工作区 ID
            user_id: 用户 ID
            
        Returns:
            是否成功
        """
        self.db.execute("""
            DELETE FROM workspace_members 
            WHERE workspace_id = ? AND user_id = ?
        """, (workspace_id, user_id))
        self.db.commit()
        return True
    
    def get_member(self, workspace_id: int, user_id: int) -> Optional[Dict]:
        """
        获取成员信息
        
        Args:
            workspace_id: 工作区 ID
            user_id: 用户 ID
            
        Returns:
            成员信息字典
        """
        cursor = self.db.execute("""
            SELECT wm.*, u.username, u.display_name
            FROM workspace_members wm
            JOIN users u ON wm.user_id = u.id
            WHERE wm.workspace_id = ? AND wm.user_id = ?
        """, (workspace_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_members(self, workspace_id: int) -> List[Dict]:
        """
        列出工作区所有成员
        
        Args:
            workspace_id: 工作区 ID
            
        Returns:
            成员列表
        """
        cursor = self.db.execute("""
            SELECT wm.*, u.username, u.display_name
            FROM workspace_members wm
            JOIN users u ON wm.user_id = u.id
            WHERE wm.workspace_id = ?
            ORDER BY wm.joined_at
        """, (workspace_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_workspaces(self, user_id: int) -> List[Dict]:
        """
        获取用户所属的所有工作区
        
        Args:
            user_id: 用户 ID
            
        Returns:
            工作区列表（含角色信息）
        """
        cursor = self.db.execute("""
            SELECT wm.role, wm.joined_at,
                   w.id, w.name, w.description, w.created_at
            FROM workspace_members wm
            JOIN workspaces w ON wm.workspace_id = w.id
            WHERE wm.user_id = ?
            ORDER BY wm.joined_at
        """, (user_id,))
        
        result = []
        for row in cursor.fetchall():
            result.append({
                'workspace_id': row['id'],
                'workspace_name': row['name'],
                'description': row['description'],
                'role': row['role'],
                'joined_at': row['joined_at']
            })
        return result
    
    def update_member_role(self, workspace_id: int, user_id: int, role: str) -> bool:
        """
        更新成员角色
        
        Args:
            workspace_id: 工作区 ID
            user_id: 用户 ID
            role: 新角色
            
        Returns:
            是否成功
        """
        if role not in self.VALID_ROLES:
            raise ValueError(f"无效角色: {role}")
        
        self.db.execute("""
            UPDATE workspace_members SET role = ?
            WHERE workspace_id = ? AND user_id = ?
        """, (role, workspace_id, user_id))
        self.db.commit()
        return True
    
    def can_edit(self, user_id: int, workspace_id: int) -> bool:
        """
        检查用户是否可编辑工作区
        
        Args:
            user_id: 用户 ID
            workspace_id: 工作区 ID
            
        Returns:
            是否可编辑
        """
        member = self.get_member(workspace_id, user_id)
        if not member:
            return False
        return member['role'] in ('owner', 'editor')
    
    def can_view(self, user_id: int, workspace_id: int) -> bool:
        """
        检查用户是否可查看工作区
        
        Args:
            user_id: 用户 ID
            workspace_id: 工作区 ID
            
        Returns:
            是否可查看
        """
        member = self.get_member(workspace_id, user_id)
        return member is not None
    
    def get_workspace_owner(self, workspace_id: int) -> Optional[User]:
        """
        获取工作区所有者
        
        Args:
            workspace_id: 工作区 ID
            
        Returns:
            所有者用户对象
        """
        cursor = self.db.execute("""
            SELECT u.* FROM users u
            JOIN workspace_members wm ON u.id = wm.user_id
            WHERE wm.workspace_id = ? AND wm.role = 'owner'
            LIMIT 1
        """, (workspace_id,))
        row = cursor.fetchone()
        return User.from_row(row) if row else None
