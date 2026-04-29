"""
MemoMind 数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Note:
    """笔记数据模型"""
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> 'Note':
        """从数据库行创建 Note 实例"""
        import json
        return cls(
            id=row[0],
            title=row[1],
            content=row[2],
            tags=json.loads(row[3]) if row[3] else [],
            created_at=datetime.fromisoformat(row[4]) if row[4] else None,
            updated_at=datetime.fromisoformat(row[5]) if row[5] else None
        )


@dataclass
class SearchResult:
    """搜索结果"""
    note: Note
    score: float
    highlights: dict  # {'title': '...', 'content': '...'}
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'note': self.note.to_dict(),
            'score': self.score,
            'highlights': self.highlights
        }
