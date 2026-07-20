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
    type: str = "note"               # 'note' | 'annotation' | 'summary'
    parent_id: Optional[int] = None  # 顶级备注指向 note_id，回复指向父备注 id
    ai_summary: str = ""             # AI 摘要缓存

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'type': self.type,
            'parent_id': self.parent_id,
            'ai_summary': self.ai_summary,
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'Note':
        """从数据库行创建 Note 实例。

        兼容旧查询（SELECT id,title,content,tags,created_at,updated_at）
        和新查询（SELECT * FROM notes 含 type/parent_id/ai_summary）。
        """
        import json
        n = len(row)
        return cls(
            id=row[0],
            title=row[1],
            content=row[2],
            tags=json.loads(row[3]) if row[3] else [],
            created_at=datetime.fromisoformat(row[4]) if row[4] else None,
            updated_at=datetime.fromisoformat(row[5]) if row[5] else None,
            type=row[6] if n > 6 and row[6] else "note",
            parent_id=row[7] if n > 7 and row[7] else None,
            ai_summary=row[8] if n > 8 and row[8] else "",
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
