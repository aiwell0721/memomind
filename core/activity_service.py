"""
MemoMind 活动日志服务
记录所有笔记操作（创建/编辑/删除/恢复/标签）
支持时间线视图和按用户/工作区/类型过滤
"""

import json
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from .database import Database


@dataclass
class ActivityLog:
    """活动日志数据模型"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    workspace_id: Optional[int] = None
    note_id: Optional[int] = None
    action: str = ""  # create/update/delete/restore/tag/untag
    details: Optional[Dict] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'workspace_id': self.workspace_id,
            'note_id': self.note_id,
            'action': self.action,
            'details': self.details,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_row(cls, row) -> 'ActivityLog':
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            workspace_id=row['workspace_id'],
            note_id=row['note_id'],
            action=row['action'],
            details=json.loads(row['details']) if row['details'] else None,
            created_at=row['created_at']
        )


class ActivityService:
    """活动日志服务"""
    
    VALID_ACTIONS = {'create', 'update', 'delete', 'restore', 'tag', 'untag', 
                     'workspace_create', 'workspace_update', 'workspace_delete',
                     'member_add', 'member_remove', 'member_role_change'}
    
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()
    
    def _init_schema(self):
        """初始化活动日志表结构"""
        cursor = self.db.conn
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,  -- 操作用户（无外键，允许孤儿日志）
                workspace_id INTEGER,  -- 工作区（无外键）
                note_id INTEGER,  -- 笔记（无外键）
                action TEXT NOT NULL,
                details TEXT,  -- JSON 格式
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_user
            ON activity_log(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_workspace
            ON activity_log(workspace_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_note
            ON activity_log(note_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_action
            ON activity_log(action)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_created_at
            ON activity_log(created_at DESC)
        """)
        
        self.db.commit()
    
    def log(
        self,
        action: str,
        user_id: int = None,
        workspace_id: int = None,
        note_id: int = None,
        details: Dict = None
    ) -> int:
        """
        记录活动日志
        
        Args:
            action: 操作类型
            user_id: 操作用户 ID
            workspace_id: 工作区 ID
            note_id: 笔记 ID
            details: 额外详情（JSON）
            
        Returns:
            日志 ID
        """
        if action not in self.VALID_ACTIONS:
            raise ValueError(f"无效操作: {action}，有效值: {self.VALID_ACTIONS}")
        
        cursor = self.db.execute("""
            INSERT INTO activity_log (user_id, workspace_id, note_id, action, details)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, workspace_id, note_id, action, 
              json.dumps(details) if details else None))
        self.db.commit()
        return cursor.lastrowid
    
    def get_log(self, log_id: int) -> Optional[ActivityLog]:
        """
        获取单条日志
        
        Args:
            log_id: 日志 ID
            
        Returns:
            日志对象
        """
        cursor = self.db.execute("""
            SELECT * FROM activity_log WHERE id = ?
        """, (log_id,))
        row = cursor.fetchone()
        return ActivityLog.from_row(row) if row else None
    
    def get_timeline(
        self,
        workspace_id: int = None,
        user_id: int = None,
        note_id: int = None,
        action: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取活动时间线
        
        Args:
            workspace_id: 按工作区过滤
            user_id: 按用户过滤
            note_id: 按笔记过滤
            action: 按操作类型过滤
            limit: 返回数量
            offset: 分页偏移
            
        Returns:
            活动列表（含用户名和笔记标题）
        """
        conditions = []
        params = []
        
        if workspace_id is not None:
            conditions.append("al.workspace_id = ?")
            params.append(workspace_id)
        if user_id is not None:
            conditions.append("al.user_id = ?")
            params.append(user_id)
        if note_id is not None:
            conditions.append("al.note_id = ?")
            params.append(note_id)
        if action:
            conditions.append("al.action = ?")
            params.append(action)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        sql = f"""
            SELECT 
                al.*,
                u.username,
                u.display_name,
                n.title as note_title,
                w.name as workspace_name
            FROM activity_log al
            LEFT JOIN users u ON al.user_id = u.id
            LEFT JOIN notes n ON al.note_id = n.id
            LEFT JOIN workspaces w ON al.workspace_id = w.id
            {where_clause}
            ORDER BY al.created_at DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        cursor = self.db.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'username': row['username'],
                'display_name': row['display_name'],
                'workspace_id': row['workspace_id'],
                'workspace_name': row['workspace_name'],
                'note_id': row['note_id'],
                'note_title': row['note_title'],
                'action': row['action'],
                'details': json.loads(row['details']) if row['details'] else None,
                'created_at': row['created_at']
            })
        
        return results
    
    def get_note_history(self, note_id: int, limit: int = 20) -> List[Dict]:
        """
        获取笔记操作历史
        
        Args:
            note_id: 笔记 ID
            limit: 返回数量
            
        Returns:
            活动列表
        """
        return self.get_timeline(note_id=note_id, limit=limit)
    
    def get_user_activity(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        获取用户活动记录
        
        Args:
            user_id: 用户 ID
            limit: 返回数量
            
        Returns:
            活动列表
        """
        return self.get_timeline(user_id=user_id, limit=limit)
    
    def get_workspace_activity(self, workspace_id: int, limit: int = 50) -> List[Dict]:
        """
        获取工作区活动记录
        
        Args:
            workspace_id: 工作区 ID
            limit: 返回数量
            
        Returns:
            活动列表
        """
        return self.get_timeline(workspace_id=workspace_id, limit=limit)
    
    def count_by_action(self, workspace_id: int = None) -> Dict[str, int]:
        """
        按操作类型统计
        
        Args:
            workspace_id: 按工作区过滤（None = 全部）
            
        Returns:
            {action: count} 字典
        """
        if workspace_id:
            cursor = self.db.execute("""
                SELECT action, COUNT(*) as cnt
                FROM activity_log
                WHERE workspace_id = ?
                GROUP BY action
            """, (workspace_id,))
        else:
            cursor = self.db.execute("""
                SELECT action, COUNT(*) as cnt
                FROM activity_log
                GROUP BY action
            """)
        
        return {row['action']: row['cnt'] for row in cursor.fetchall()}
    
    def delete_old_logs(self, days: int = 90) -> int:
        """
        清理旧日志
        
        Args:
            days: 保留最近 N 天的日志
            
        Returns:
            删除的日志数量
        """
        cursor = self.db.execute("""
            DELETE FROM activity_log
            WHERE created_at < datetime('now', ?)
        """, (f'-{days} days',))
        self.db.commit()
        return cursor.rowcount
