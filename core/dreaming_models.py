"""
Dreaming 数据模型

DreamingSession: 一次 Dreaming 会话记录
DreamingChange: 单条变更记录（追溯用）
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DreamingSession:
    """Dreaming 会话"""
    id: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    trigger: str = "manual"  # 'manual' | 'scheduled' | 'threshold'
    status: str = "running"  # 'running' | 'completed' | 'failed' | 'rolled_back'

    # 统计
    input_count: int = 0
    output_count: int = 0
    merged_count: int = 0
    archived_count: int = 0
    extracted_facts: int = 0
    error_message: Optional[str] = None


@dataclass
class DreamingChange:
    """Dreaming 变更记录（合并/归档追溯）"""
    id: int = 0
    session_id: int = 0
    change_type: str = ""  # 'merge' | 'archive' | 'extract' | 'forget'
    source_ids: list[int] = field(default_factory=list)  # JSON array
    target_id: Optional[int] = None
    diff_summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)
