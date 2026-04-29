"""
MemoMind 双向链接服务
"""

import re
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass
from .database import Database


@dataclass
class NoteLink:
    """笔记链接数据模型"""
    source_note_id: int
    source_title: str
    target_note_id: int
    target_title: str
    link_text: Optional[str] = None  # 链接显示文本（如果有别名）
    created_at: Optional[str] = None
    
    @classmethod
    def from_row(cls, row):
        """从数据库行创建链接对象"""
        return cls(
            source_note_id=row['source_note_id'],
            source_title=row['source_title'] if 'source_title' in row.keys() else '',
            target_note_id=row['target_note_id'],
            target_title=row['target_title'] if 'target_title' in row.keys() else '',
            link_text=row['link_text'] if 'link_text' in row.keys() else None,
            created_at=row['created_at'] if 'created_at' in row.keys() else None
        )


class LinkService:
    """双向链接管理服务"""
    
    # Wiki 链接正则：[[标题]] 或 [[标题|显示文本]]
    WIKI_LINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')
    
    def __init__(self, db: Database):
        """
        初始化链接服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库表结构"""
        cursor = self.db.conn
        
        # 创建链接关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_links (
                source_note_id INTEGER NOT NULL,
                target_note_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_note_id, target_note_id),
                FOREIGN KEY (source_note_id) REFERENCES notes(id),
                FOREIGN KEY (target_note_id) REFERENCES notes(id)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_target 
            ON note_links(target_note_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_source 
            ON note_links(source_note_id)
        """)
        
        self.db.commit()
    
    def extract_links(self, content: str) -> List[Tuple[str, Optional[str]]]:
        """
        从内容中提取 Wiki 链接
        
        Args:
            content: Markdown 内容
            
        Returns:
            [(标题，显示文本), ...] 列表
        """
        links = []
        for match in self.WIKI_LINK_PATTERN.finditer(content):
            title = match.group(1).strip()
            alias = match.group(2).strip() if match.group(2) else None
            links.append((title, alias))
        
        return links
    
    def update_note_links(self, note_id: int, content: str) -> int:
        """
        更新笔记的链接关系（解析内容并更新数据库）
        
        Args:
            note_id: 笔记 ID
            content: 笔记内容
            
        Returns:
            创建的链接数量
        """
        # 获取笔记标题
        cursor = self.db.execute("SELECT title FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            return 0
        
        source_title = row['title']
        
        # 提取链接
        links = self.extract_links(content)
        
        # 删除旧链接
        self.db.execute("DELETE FROM note_links WHERE source_note_id = ?", (note_id,))
        
        # 创建新链接
        link_count = 0
        for target_title, link_text in links:
            # 查找目标笔记
            target = self._find_note_by_title(target_title)
            if target:
                target_id = target['id']
                
                # 避免自链接
                if target_id != note_id:
                    try:
                        self.db.execute("""
                            INSERT OR REPLACE INTO note_links 
                            (source_note_id, target_note_id, created_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        """, (note_id, target_id))
                        link_count += 1
                    except Exception:
                        # 忽略重复链接
                        pass
        
        self.db.commit()
        return link_count
    
    def _find_note_by_title(self, title: str) -> Optional[Dict]:
        """
        根据标题查找笔记
        
        Args:
            title: 笔记标题
            
        Returns:
            笔记信息字典，不存在则返回 None
        """
        cursor = self.db.execute("""
            SELECT id, title FROM notes 
            WHERE title = ? COLLATE NOCASE
        """, (title,))
        
        row = cursor.fetchone()
        if row:
            return {'id': row['id'], 'title': row['title']}
        
        return None
    
    def get_outgoing_links(self, note_id: int) -> List[NoteLink]:
        """
        获取笔记的出链（我链接了谁）
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            链接列表
        """
        cursor = self.db.execute("""
            SELECT 
                nl.source_note_id,
                sn.title as source_title,
                nl.target_note_id,
                tn.title as target_title,
                nl.created_at
            FROM note_links nl
            JOIN notes sn ON nl.source_note_id = sn.id
            JOIN notes tn ON nl.target_note_id = tn.id
            WHERE nl.source_note_id = ?
            ORDER BY tn.title
        """, (note_id,))
        
        return [NoteLink.from_row(row) for row in cursor.fetchall()]
    
    def get_incoming_links(self, note_id: int) -> List[NoteLink]:
        """
        获取笔记的入链（谁链接了我）- 反向链接
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            链接列表
        """
        cursor = self.db.execute("""
            SELECT 
                nl.source_note_id,
                sn.title as source_title,
                nl.target_note_id,
                tn.title as target_title,
                nl.created_at
            FROM note_links nl
            JOIN notes sn ON nl.source_note_id = sn.id
            JOIN notes tn ON nl.target_note_id = tn.id
            WHERE nl.target_note_id = ?
            ORDER BY sn.title
        """, (note_id,))
        
        return [NoteLink.from_row(row) for row in cursor.fetchall()]
    
    def get_all_links(self, note_id: int) -> Dict[str, List[NoteLink]]:
        """
        获取笔记的所有链接（出链 + 入链）
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            {'outgoing': [...], 'incoming': [...]}
        """
        return {
            'outgoing': self.get_outgoing_links(note_id),
            'incoming': self.get_incoming_links(note_id)
        }
    
    def get_link_count(self, note_id: int) -> Dict[str, int]:
        """
        获取笔记的链接统计
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            {'outgoing': count, 'incoming': count, 'total': count}
        """
        cursor = self.db.execute("""
            SELECT 
                (SELECT COUNT(*) FROM note_links WHERE source_note_id = ?) as outgoing,
                (SELECT COUNT(*) FROM note_links WHERE target_note_id = ?) as incoming
        """, (note_id, note_id))
        
        row = cursor.fetchone()
        outgoing = row['outgoing']
        incoming = row['incoming']
        
        return {
            'outgoing': outgoing,
            'incoming': incoming,
            'total': outgoing + incoming
        }
    
    def get_orphaned_notes(self) -> List[Dict]:
        """
        获取孤立笔记（没有出链也没有入链）
        
        Returns:
            孤立笔记列表
        """
        cursor = self.db.execute("""
            SELECT n.id, n.title, n.created_at
            FROM notes n
            WHERE n.id NOT IN (SELECT source_note_id FROM note_links)
              AND n.id NOT IN (SELECT target_note_id FROM note_links)
            ORDER BY n.title
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_broken_links(self) -> List[Dict]:
        """
        获取断链（链接指向不存在的笔记）
        
        Returns:
            断链列表
        """
        # 获取所有笔记内容，检查是否有断链
        cursor = self.db.execute("SELECT id, title, content FROM notes")
        
        broken = []
        for row in cursor.fetchall():
            note_id = row['id']
            content = row['content']
            
            # 提取链接
            links = self.extract_links(content)
            
            for target_title, _ in links:
                target = self._find_note_by_title(target_title)
                if not target:
                    broken.append({
                        'source_note_id': note_id,
                        'source_title': row['title'],
                        'target_title': target_title,
                        'error': 'Target note not found'
                    })
        
        return broken
    
    def get_link_graph(self) -> Dict:
        """
        获取链接关系图数据（用于可视化）
        
        Returns:
            {'nodes': [...], 'links': [...]}
        """
        # 获取所有有链接的笔记
        cursor = self.db.execute("""
            SELECT DISTINCT id, title
            FROM notes
            WHERE id IN (SELECT source_note_id FROM note_links)
               OR id IN (SELECT target_note_id FROM note_links)
            ORDER BY title
        """)
        
        nodes = []
        node_ids = set()
        for row in cursor.fetchall():
            nodes.append({'id': row['id'], 'title': row['title']})
            node_ids.add(row['id'])
        
        # 获取所有链接
        cursor = self.db.execute("""
            SELECT source_note_id, target_note_id
            FROM note_links
            ORDER BY source_note_id
        """)
        
        links = []
        for row in cursor.fetchall():
            # 只包含两端都存在的链接
            if row['source_note_id'] in node_ids and row['target_note_id'] in node_ids:
                links.append({
                    'source': row['source_note_id'],
                    'target': row['target_note_id']
                })
        
        return {'nodes': nodes, 'links': links}
    
    def suggest_links(self, prefix: str, limit: int = 10) -> List[Dict]:
        """
        链接自动补全建议
        
        Args:
            prefix: 输入前缀
            limit: 返回数量
            
        Returns:
            笔记列表
        """
        cursor = self.db.execute("""
            SELECT id, title
            FROM notes
            WHERE title LIKE ?
            ORDER BY title
            LIMIT ?
        """, (prefix + '%', limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def remove_link(self, source_note_id: int, target_note_id: int) -> bool:
        """
        移除链接
        
        Args:
            source_note_id: 源笔记 ID
            target_note_id: 目标笔记 ID
            
        Returns:
            是否成功
        """
        cursor = self.db.execute("""
            DELETE FROM note_links
            WHERE source_note_id = ? AND target_note_id = ?
        """, (source_note_id, target_note_id))
        
        self.db.commit()
        return cursor.rowcount > 0
    
    def get_popular_links(self, limit: int = 10) -> List[Dict]:
        """
        获取最常被链接的笔记
        
        Args:
            limit: 返回数量
            
        Returns:
            笔记列表（带链接数）
        """
        cursor = self.db.execute("""
            SELECT 
                n.id,
                n.title,
                COUNT(nl.source_note_id) as link_count
            FROM notes n
            JOIN note_links nl ON n.id = nl.target_note_id
            GROUP BY n.id
            ORDER BY link_count DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
