"""
MemoMind 版本历史服务
"""

import json
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from .database import Database


@dataclass
class Version:
    """版本数据模型"""
    id: int
    note_id: int
    version_number: int
    title: str
    content: str
    tags: List[str]
    created_at: str
    change_summary: Optional[str] = None
    is_tagged: bool = False
    tag_name: Optional[str] = None
    
    @classmethod
    def from_row(cls, row):
        """从数据库行创建版本对象"""
        return cls(
            id=row['id'],
            note_id=row['note_id'],
            version_number=row['version_number'],
            title=row['title'],
            content=row['content'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            created_at=row['created_at'],
            change_summary=row['change_summary'],
            is_tagged=bool(row['is_tagged']),
            tag_name=row['tag_name']
        )


class VersionService:
    """版本历史服务"""
    
    def __init__(self, db: Database):
        """
        初始化版本服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库表结构"""
        cursor = self.db.conn
        
        # 不禁用外键 - 测试显示这不会导致问题
        # cursor.execute("PRAGMA foreign_keys = OFF")
        
        # 创建版本历史表（不删除 notes 表！）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                change_summary TEXT,
                is_tagged INTEGER DEFAULT 0,
                tag_name TEXT,
                FOREIGN KEY (note_id) REFERENCES notes(id)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_note 
            ON note_versions(note_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_number 
            ON note_versions(note_id, version_number)
        """)
        
        self.db.commit()
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_note 
            ON note_versions(note_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_number 
            ON note_versions(note_id, version_number)
        """)
        
        self.db.commit()
    
    def save_version(
        self,
        note_id: int,
        title: str,
        content: str,
        tags: List[str],
        change_summary: str = None
    ) -> int:
        """
        保存新版本
        
        Args:
            note_id: 笔记 ID
            title: 笔记标题
            content: 笔记内容
            tags: 标签列表
            change_summary: 变更摘要（可选）
            
        Returns:
            版本号
        """
        # 获取当前最大版本号
        cursor = self.db.execute("""
            SELECT MAX(version_number) FROM note_versions
            WHERE note_id = ?
        """, (note_id,))
        
        result = cursor.fetchone()[0]
        version_number = (result or 0) + 1
        
        # 插入新版本
        cursor = self.db.execute("""
            INSERT INTO note_versions 
            (note_id, version_number, title, content, tags, change_summary)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            note_id,
            version_number,
            title,
            content,
            json.dumps(tags),
            change_summary
        ))
        
        self.db.commit()
        return version_number
    
    def get_versions(self, note_id: int, limit: int = 10) -> List[Version]:
        """
        获取历史版本列表
        
        Args:
            note_id: 笔记 ID
            limit: 返回数量限制
            
        Returns:
            版本列表（按版本号倒序）
        """
        cursor = self.db.execute("""
            SELECT * FROM note_versions
            WHERE note_id = ?
            ORDER BY version_number DESC
            LIMIT ?
        """, (note_id, limit))
        
        return [Version.from_row(row) for row in cursor.fetchall()]
    
    def get_version(self, version_id: int) -> Optional[Version]:
        """
        获取指定版本详情
        
        Args:
            version_id: 版本 ID
            
        Returns:
            版本对象，不存在则返回 None
        """
        cursor = self.db.execute("""
            SELECT * FROM note_versions
            WHERE id = ?
        """, (version_id,))
        
        row = cursor.fetchone()
        return Version.from_row(row) if row else None
    
    def restore_version(self, version_id: int) -> Optional[dict]:
        """
        恢复到指定版本
        
        Args:
            version_id: 版本 ID
            
        Returns:
            恢复后的笔记数据，版本不存在则返回 None
        """
        version = self.get_version(version_id)
        if not version:
            return None
        
        # 更新原笔记
        from datetime import datetime
        self.db.execute("""
            UPDATE notes
            SET title = ?, content = ?, tags = ?, updated_at = ?
            WHERE id = ?
        """, (version.title, version.content, json.dumps(version.tags), datetime.now().isoformat(), version.note_id))
        
        self.db.commit()
        
        return {
            'id': version.note_id,
            'title': version.title,
            'content': version.content,
            'tags': version.tags
        }
    
    def tag_version(self, version_id: int, tag_name: str) -> bool:
        """
        标记重要版本
        
        Args:
            version_id: 版本 ID
            tag_name: 标签名称
            
        Returns:
            是否成功
        """
        cursor = self.db.execute("""
            UPDATE note_versions
            SET is_tagged = 1, tag_name = ?
            WHERE id = ?
        """, (tag_name, version_id))
        
        self.db.commit()
        return cursor.rowcount > 0
    
    def cleanup_versions(self, note_id: int, keep_count: int = 10) -> int:
        """
        清理旧版本，保留最近 N 个
        
        Args:
            note_id: 笔记 ID
            keep_count: 保留数量
            
        Returns:
            删除的版本数量
        """
        # 获取要删除的版本 ID（排除标签版本）
        cursor = self.db.execute("""
            SELECT id FROM note_versions
            WHERE note_id = ? AND is_tagged = 0
            ORDER BY version_number DESC
            LIMIT -1 OFFSET ?
        """, (note_id, keep_count))
        
        ids_to_delete = [row[0] for row in cursor.fetchall()]
        
        if not ids_to_delete:
            return 0
        
        # 删除旧版本
        placeholders = ','.join('?' * len(ids_to_delete))
        self.db.execute(f"""
            DELETE FROM note_versions
            WHERE id IN ({placeholders})
        """, ids_to_delete)
        
        self.db.commit()
        return len(ids_to_delete)
    
    def get_tagged_versions(self, note_id: int) -> List[Version]:
        """
        获取所有标签版本
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            标签版本列表
        """
        cursor = self.db.execute("""
            SELECT * FROM note_versions
            WHERE note_id = ? AND is_tagged = 1
            ORDER BY version_number DESC
        """, (note_id,))
        
        return [Version.from_row(row) for row in cursor.fetchall()]
