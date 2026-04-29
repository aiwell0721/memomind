"""
MemoMind 标签管理服务 - 支持层级标签和别名
"""

import json
from typing import List, Optional, Dict
from dataclasses import dataclass
from .database import Database


@dataclass
class Tag:
    """标签数据模型"""
    id: int
    name: str
    parent_id: Optional[int] = None
    alias_for: Optional[int] = None
    note_count: int = 0
    
    @classmethod
    def from_row(cls, row):
        """从数据库行创建标签对象"""
        return cls(
            id=row['id'],
            name=row['name'],
            parent_id=row['parent_id'],
            alias_for=row['alias_for'],
            note_count=row['note_count'] if 'note_count' in row.keys() else 0
        )


class TagService:
    """标签管理服务"""
    
    def __init__(self, db: Database):
        """
        初始化标签服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库表结构"""
        cursor = self.db.conn
        
        # 创建标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                parent_id INTEGER,
                alias_for INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES tags(id),
                FOREIGN KEY (alias_for) REFERENCES tags(id)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_parent 
            ON tags(parent_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_alias 
            ON tags(alias_for)
        """)
        
        # 创建 note_tags 关联表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES notes(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)
        
        self.db.commit()
    
    def create_tag(self, name: str, parent_id: Optional[int] = None) -> int:
        """
        创建标签
        
        Args:
            name: 标签名称
            parent_id: 父标签 ID（可选）
            
        Returns:
            标签 ID
        """
        cursor = self.db.execute("""
            INSERT INTO tags (name, parent_id)
            VALUES (?, ?)
        """, (name, parent_id))
        
        self.db.commit()
        return cursor.lastrowid
    
    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """
        获取标签详情
        
        Args:
            tag_id: 标签 ID
            
        Returns:
            标签对象，不存在则返回 None
        """
        cursor = self.db.execute("""
            SELECT t.*, COUNT(nt.note_id) as note_count
            FROM tags t
            LEFT JOIN note_tags nt ON t.id = nt.tag_id
            WHERE t.id = ?
            GROUP BY t.id
        """, (tag_id,))
        
        row = cursor.fetchone()
        return Tag.from_row(row) if row else None
    
    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """
        根据名称获取标签
        
        Args:
            name: 标签名称
            
        Returns:
            标签对象，不存在则返回 None
        """
        cursor = self.db.execute("""
            SELECT t.*, COUNT(nt.note_id) as note_count
            FROM tags t
            LEFT JOIN note_tags nt ON t.id = nt.tag_id
            WHERE t.name = ?
            GROUP BY t.id
        """, (name,))
        
        row = cursor.fetchone()
        return Tag.from_row(row) if row else None
    
    def get_or_create_tag(self, name: str, parent_id: Optional[int] = None) -> int:
        """
        获取或创建标签
        
        Args:
            name: 标签名称
            parent_id: 父标签 ID（可选）
            
        Returns:
            标签 ID
        """
        tag = self.get_tag_by_name(name)
        if tag:
            return tag.id
        
        return self.create_tag(name, parent_id)
    
    def update_tag(self, tag_id: int, name: str = None, parent_id: Optional[int] = None) -> bool:
        """
        更新标签
        
        Args:
            tag_id: 标签 ID
            name: 新名称（可选）
            parent_id: 新父标签 ID（可选）
            
        Returns:
            是否成功
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if parent_id is not None:
            updates.append("parent_id = ?")
            params.append(parent_id)
        
        if not updates:
            return False
        
        params.append(tag_id)
        self.db.execute(f"""
            UPDATE tags
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        self.db.commit()
        return self.db.conn.total_changes > 0
    
    def delete_tag(self, tag_id: int) -> bool:
        """
        删除标签
        
        Args:
            tag_id: 标签 ID
            
        Returns:
            是否成功
        """
        # 先删除关联关系
        self.db.execute("DELETE FROM note_tags WHERE tag_id = ?", (tag_id,))
        
        # 删除标签
        cursor = self.db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        
        self.db.commit()
        return cursor.rowcount > 0
    
    def get_all_tags(self, include_stats: bool = True) -> List[Tag]:
        """
        获取所有标签
        
        Args:
            include_stats: 是否包含统计信息
            
        Returns:
            标签列表
        """
        if include_stats:
            cursor = self.db.execute("""
                SELECT t.*, COUNT(nt.note_id) as note_count
                FROM tags t
                LEFT JOIN note_tags nt ON t.id = nt.tag_id
                GROUP BY t.id
                ORDER BY t.name
            """)
        else:
            cursor = self.db.execute("SELECT * FROM tags ORDER BY name")
        
        return [Tag.from_row(row) for row in cursor.fetchall()]
    
    def get_tag_tree(self, parent_id: Optional[int] = None) -> List[Dict]:
        """
        获取标签树（递归）
        
        Args:
            parent_id: 父标签 ID（None 表示根节点）
            
        Returns:
            标签树结构
        """
        cursor = self.db.execute("""
            SELECT t.*, COUNT(nt.note_id) as note_count
            FROM tags t
            LEFT JOIN note_tags nt ON t.id = nt.tag_id
            WHERE t.parent_id IS ?
            GROUP BY t.id
            ORDER BY t.name
        """, (parent_id,))
        
        tags = []
        for row in cursor.fetchall():
            tag = Tag.from_row(row)
            tag_dict = {
                'id': tag.id,
                'name': tag.name,
                'note_count': tag.note_count,
                'children': self.get_tag_tree(tag.id)
            }
            tags.append(tag_dict)
        
        return tags
    
    def set_tag_alias(self, tag_id: int, alias_name: str) -> int:
        """
        设置标签别名
        
        Args:
            tag_id: 主标签 ID
            alias_name: 别名
            
        Returns:
            别名标签 ID
        """
        cursor = self.db.execute("""
            INSERT INTO tags (name, alias_for)
            VALUES (?, ?)
        """, (alias_name, tag_id))
        
        self.db.commit()
        return cursor.lastrowid
    
    def resolve_alias(self, tag_name: str) -> Optional[Tag]:
        """
        解析标签别名（返回主标签）
        
        Args:
            tag_name: 标签名称或别名
            
        Returns:
            主标签对象
        """
        cursor = self.db.execute("""
            SELECT 
                CASE WHEN t.alias_for IS NOT NULL THEN t.alias_for ELSE t.id END as main_id
            FROM tags t
            WHERE t.name = ?
        """, (tag_name,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return self.get_tag(row['main_id'])
    
    def merge_tags(self, source_tag_ids: List[int], target_tag_id: int) -> int:
        """
        合并标签（将源标签的笔记转移到目标标签）
        
        Args:
            source_tag_ids: 源标签 ID 列表
            target_tag_id: 目标标签 ID
            
        Returns:
            合并的笔记数量
        """
        merged_count = 0
        
        for source_id in source_tag_ids:
            # 转移笔记关联
            cursor = self.db.execute("""
                INSERT OR IGNORE INTO note_tags (note_id, tag_id)
                SELECT note_id, ? FROM note_tags WHERE tag_id = ?
            """, (target_tag_id, source_id))
            
            merged_count += cursor.rowcount
            
            # 删除源标签
            self.delete_tag(source_id)
        
        return merged_count
    
    def get_popular_tags(self, limit: int = 10) -> List[Tag]:
        """
        获取热门标签
        
        Args:
            limit: 返回数量
            
        Returns:
            热门标签列表
        """
        cursor = self.db.execute("""
            SELECT t.*, COUNT(nt.note_id) as note_count
            FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            WHERE t.alias_for IS NULL  -- 排除别名
            GROUP BY t.id
            ORDER BY note_count DESC
            LIMIT ?
        """, (limit,))
        
        return [Tag.from_row(row) for row in cursor.fetchall()]
    
    def get_unused_tags(self) -> List[Tag]:
        """
        获取未使用的标签
        
        Returns:
            未使用标签列表
        """
        cursor = self.db.execute("""
            SELECT t.*
            FROM tags t
            LEFT JOIN note_tags nt ON t.id = nt.tag_id
            WHERE nt.note_id IS NULL
            ORDER BY t.name
        """)
        
        return [Tag.from_row(row) for row in cursor.fetchall()]
    
    def suggest_tags(self, prefix: str, limit: int = 10) -> List[Tag]:
        """
        标签搜索建议（自动补全）
        
        Args:
            prefix: 输入前缀
            limit: 返回数量
            
        Returns:
            建议标签列表
        """
        cursor = self.db.execute("""
            SELECT t.*
            FROM tags t
            WHERE t.name LIKE ? AND t.alias_for IS NULL
            ORDER BY t.name
            LIMIT ?
        """, (prefix + '%', limit))
        
        return [Tag.from_row(row) for row in cursor.fetchall()]
    
    def tag_note(self, note_id: int, tag_names: List[str]) -> List[int]:
        """
        为笔记添加标签
        
        Args:
            note_id: 笔记 ID
            tag_names: 标签名称列表
            
        Returns:
            标签 ID 列表
        """
        tag_ids = []
        
        for tag_name in tag_names:
            # 解析别名
            tag = self.resolve_alias(tag_name)
            if not tag:
                # 创建新标签
                tag_id = self.create_tag(tag_name)
            else:
                tag_id = tag.id
            
            # 添加关联
            self.db.execute("""
                INSERT OR IGNORE INTO note_tags (note_id, tag_id)
                VALUES (?, ?)
            """, (note_id, tag_id))
            
            tag_ids.append(tag_id)
        
        self.db.commit()
        return tag_ids
    
    def get_note_tags(self, note_id: int) -> List[Tag]:
        """
        获取笔记的所有标签
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            标签列表
        """
        cursor = self.db.execute("""
            SELECT t.*
            FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            WHERE nt.note_id = ?
            ORDER BY t.name
        """, (note_id,))
        
        return [Tag.from_row(row) for row in cursor.fetchall()]
    
    def remove_note_tag(self, note_id: int, tag_id: int) -> bool:
        """
        移除笔记的标签
        
        Args:
            note_id: 笔记 ID
            tag_id: 标签 ID
            
        Returns:
            是否成功
        """
        cursor = self.db.execute("""
            DELETE FROM note_tags
            WHERE note_id = ? AND tag_id = ?
        """, (note_id, tag_id))
        
        self.db.commit()
        return cursor.rowcount > 0
