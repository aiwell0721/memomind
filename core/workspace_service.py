"""
MemoMind 多工作区服务
支持笔记按工作区隔离、跨工作区搜索、工作区元数据管理
"""

import json
from typing import List, Optional, Dict
from dataclasses import dataclass
from .database import Database


@dataclass
class Workspace:
    """工作区数据模型"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_row(cls, row) -> 'Workspace':
        return cls(
            id=row['id'],
            name=row['name'],
            description=row['description'] or '',
            created_at=row['created_at']
        )


class WorkspaceService:
    """工作区管理服务"""
    
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()
    
    def _init_schema(self):
        """初始化工作区相关表结构"""
        cursor = self.db.conn
        
        # 创建工作区表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 检查 notes 表是否已有 workspace_id 列
        info_cursor = self.db.conn.cursor()
        info_cursor.execute("PRAGMA table_info(notes)")
        columns = [col['name'] for col in info_cursor.fetchall()]
        
        if 'workspace_id' not in columns:
            cursor.execute("""
                ALTER TABLE notes ADD COLUMN workspace_id INTEGER 
                REFERENCES workspaces(id) DEFAULT 1
            """)
            # 为已有笔记设置默认工作区
            cursor.execute("""
                UPDATE notes SET workspace_id = 1 
                WHERE workspace_id IS NULL
            """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_workspace 
            ON notes(workspace_id)
        """)
        
        # 确保默认工作区存在
        row = self.db.execute("SELECT id FROM workspaces WHERE id = 1").fetchone()
        if not row:
            self.db.execute("""
                INSERT INTO workspaces (id, name, description) 
                VALUES (1, '默认工作区', '系统自动创建的默认工作区')
            """)
        
        self.db.commit()
    
    def create_workspace(self, name: str, description: str = '') -> int:
        """
        创建工作区
        
        Args:
            name: 工作区名称（唯一）
            description: 工作区描述
            
        Returns:
            新工作区 ID
        """
        cursor = self.db.execute("""
            INSERT INTO workspaces (name, description)
            VALUES (?, ?)
        """, (name, description))
        self.db.commit()
        return cursor.lastrowid
    
    def get_workspace(self, workspace_id: int) -> Optional[Workspace]:
        """
        获取工作区详情
        
        Args:
            workspace_id: 工作区 ID
            
        Returns:
            工作区对象，不存在返回 None
        """
        cursor = self.db.execute("""
            SELECT * FROM workspaces WHERE id = ?
        """, (workspace_id,))
        row = cursor.fetchone()
        return Workspace.from_row(row) if row else None
    
    def get_workspace_by_name(self, name: str) -> Optional[Workspace]:
        """
        根据名称获取工作区
        
        Args:
            name: 工作区名称
            
        Returns:
            工作区对象，不存在返回 None
        """
        cursor = self.db.execute("""
            SELECT * FROM workspaces WHERE name = ?
        """, (name,))
        row = cursor.fetchone()
        return Workspace.from_row(row) if row else None
    
    def list_workspaces(self, limit: int = 100) -> List[Workspace]:
        """
        列出所有工作区
        
        Args:
            limit: 返回数量限制
            
        Returns:
            工作区列表
        """
        cursor = self.db.execute("""
            SELECT w.*, 
                   (SELECT COUNT(*) FROM notes n WHERE n.workspace_id = w.id) as note_count
            FROM workspaces w
            ORDER BY w.created_at DESC
            LIMIT ?
        """, (limit,))
        
        result = []
        for row in cursor.fetchall():
            ws = Workspace.from_row(row)
            # 附加 note_count
            ws.__dict__['note_count'] = row['note_count']
            result.append(ws)
        
        return result
    
    def update_workspace(self, workspace_id: int, name: str = None, 
                         description: str = None) -> bool:
        """
        更新工作区信息
        
        Args:
            workspace_id: 工作区 ID
            name: 新名称
            description: 新描述
            
        Returns:
            是否成功
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if not updates:
            return False
        
        params.append(workspace_id)
        self.db.execute(f"""
            UPDATE workspaces SET {', '.join(updates)} WHERE id = ?
        """, params)
        self.db.commit()
        return True
    
    def delete_workspace(self, workspace_id: int) -> bool:
        """
        删除工作区（级联删除笔记）
        
        ⚠️ 不能删除默认工作区（ID=1）
        
        Args:
            workspace_id: 工作区 ID
            
        Returns:
            是否成功
        """
        if workspace_id == 1:
            raise ValueError("不能删除默认工作区")
        
        # 先删除该工作区下笔记的链接关系（作为源和目标都要删除）
        try:
            self.db.execute("""
                DELETE FROM note_links WHERE source_note_id IN (
                    SELECT id FROM notes WHERE workspace_id = ?
                ) OR target_note_id IN (
                    SELECT id FROM notes WHERE workspace_id = ?
                )
            """, (workspace_id, workspace_id))
        except Exception:
            pass  # note_links table may not exist
        
        # 删除标签关联
        try:
            self.db.execute("""
                DELETE FROM note_tags WHERE note_id IN (
                    SELECT id FROM notes WHERE workspace_id = ?
                )
            """, (workspace_id,))
        except Exception:
            pass  # note_tags table may not exist
        
        # 删除版本历史
        try:
            self.db.execute("""
                DELETE FROM note_versions WHERE note_id IN (
                    SELECT id FROM notes WHERE workspace_id = ?
                )
            """, (workspace_id,))
        except Exception:
            pass  # note_versions table may not exist
        
        # 删除活动日志
        try:
            self.db.execute("DELETE FROM activity_log WHERE workspace_id = ?", (workspace_id,))
        except Exception:
            pass  # activity_log table may not exist
        
        # 删除成员关系
        try:
            self.db.execute("DELETE FROM workspace_members WHERE workspace_id = ?", (workspace_id,))
        except Exception:
            pass  # workspace_members table may not exist
        
        # 先删除该工作区下的所有笔记（FTS 触发器会自动清理）
        self.db.execute("""
            DELETE FROM notes WHERE workspace_id = ?
        """, (workspace_id,))
        
        # 删除工作区
        self.db.execute("""
            DELETE FROM workspaces WHERE id = ?
        """, (workspace_id,))
        
        self.db.commit()
        return True
    
    def move_note_to_workspace(self, note_id: int, target_workspace_id: int) -> bool:
        """
        将笔记移动到另一个工作区
        
        Args:
            note_id: 笔记 ID
            target_workspace_id: 目标工作区 ID
            
        Returns:
            是否成功
        """
        # 验证目标工作区存在
        ws = self.get_workspace(target_workspace_id)
        if not ws:
            return False
        
        self.db.execute("""
            UPDATE notes SET workspace_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (target_workspace_id, note_id))
        self.db.commit()
        return True
    
    def get_workspace_stats(self, workspace_id: int) -> Dict:
        """
        获取工作区统计信息
        
        Args:
            workspace_id: 工作区 ID
            
        Returns:
            统计字典
        """
        cursor = self.db.execute("""
            SELECT 
                COUNT(*) as note_count,
                COUNT(DISTINCT CASE WHEN tags IS NOT NULL AND tags != '[]' THEN 1 END) as tagged_count
            FROM notes
            WHERE workspace_id = ?
        """, (workspace_id,))
        
        row = cursor.fetchone()
        return {
            'workspace_id': workspace_id,
            'note_count': row['note_count'],
            'tagged_count': row['tagged_count']
        }
    
    def search_across_workspaces(
        self, 
        query: str, 
        workspace_ids: List[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        跨工作区搜索
        
        Args:
            query: 搜索关键词
            workspace_ids: 指定工作区列表（None = 全部）
            limit: 返回数量
            
        Returns:
            搜索结果（包含工作区信息）
        """
        workspace_filter = ""
        params = []
        
        if workspace_ids:
            placeholders = ','.join('?' * len(workspace_ids))
            workspace_filter = f"AND n.workspace_id IN ({placeholders})"
            params = list(workspace_ids)
        
        # 先做 FTS 搜索，再关联工作区信息
        # 如果查询只包含 ASCII 字符，用短语匹配避免 jieba 拆分
        if query.strip().isascii():
            fts_query = '"' + query.strip().replace('"', '') + '"'
        else:
            from .tokenizer import get_tokenizer
            tokenizer = get_tokenizer()
            fts_query = tokenizer.tokenize_for_search(query)
        
        sql = f"""
            SELECT 
                n.id, n.title, n.content, n.tags, n.created_at, n.updated_at,
                n.workspace_id,
                w.name as workspace_name,
                bm25(notes_fts) as score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            JOIN workspaces w ON n.workspace_id = w.id
            WHERE notes_fts MATCH ?
            {workspace_filter}
            ORDER BY score DESC
            LIMIT ?
        """
        
        params = [fts_query] + params + [limit]
        cursor = self.db.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'title': row['title'],
                'content': row['content'][:200] + ('...' if len(row['content']) > 200 else ''),
                'tags': json.loads(row['tags']) if row['tags'] else [],
                'workspace_id': row['workspace_id'],
                'workspace_name': row['workspace_name'],
                'score': -row['score'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        return results
