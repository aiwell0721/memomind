"""
MemoMind 冲突检测与合并服务
检测同时编辑冲突，提供三路合并策略
"""

import json
import difflib
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from .database import Database


@dataclass
class ConflictRecord:
    """冲突记录数据模型"""
    id: Optional[int] = None
    note_id: int = 0
    user_id: int = 0
    strategy: str = ''  # latest-wins / manual / merge
    base_content: str = ''
    their_content: str = ''
    our_content: str = ''
    resolved_content: str = ''
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'note_id': self.note_id,
            'user_id': self.user_id,
            'strategy': self.strategy,
            'base_content': self.base_content,
            'their_content': self.their_content,
            'our_content': self.our_content,
            'resolved_content': self.resolved_content,
            'created_at': self.created_at,
            'resolved_at': self.resolved_at
        }


class ConflictService:
    """冲突检测与合并服务"""
    
    VALID_STRATEGIES = {'latest-wins', 'manual', 'merge'}
    
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()
    
    def _init_schema(self):
        """初始化冲突记录表"""
        cursor = self.db.conn
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                strategy TEXT NOT NULL DEFAULT 'latest-wins'
                    CHECK (strategy IN ('latest-wins', 'manual', 'merge')),
                base_content TEXT NOT NULL,
                their_content TEXT NOT NULL,
                our_content TEXT NOT NULL,
                resolved_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_note
            ON conflicts(note_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_resolved
            ON conflicts(resolved_at)
        """)
        
        self.db.commit()
    
    def detect_conflict(
        self,
        note_id: int,
        our_content: str,
        our_updated_at: str,
        expected_updated_at: str
    ) -> Optional[Dict]:
        """
        检测编辑冲突
        
        当用户 A 和用户 B 同时编辑同一笔记时：
        1. 用户 A 保存时，检查笔记的 updated_at 是否与读取时一致
        2. 如果不一致，说明用户 B 已经修改过，产生冲突
        
        Args:
            note_id: 笔记 ID
            our_content: 我们的新内容
            our_updated_at: 我们读取时的 updated_at
            expected_updated_at: 数据库当前的 updated_at
            
        Returns:
            冲突信息字典，无冲突返回 None
        """
        if our_updated_at == expected_updated_at:
            return None  # 无冲突
        
        # 获取当前数据库中的内容（对方的修改）
        cursor = self.db.execute(
            "SELECT content, updated_at FROM notes WHERE id = ?", (note_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        their_content = row['content']
        
        # 获取最新保存的版本作为 base
        base_content = self._get_base_content(note_id, our_updated_at)
        
        return {
            'note_id': note_id,
            'base_content': base_content,
            'their_content': their_content,
            'our_content': our_content,
            'their_updated_at': row['updated_at'],
            'our_updated_at': our_updated_at
        }
    
    def _get_base_content(self, note_id: int, our_updated_at: str) -> str:
        """
        获取基础版本内容（我们读取时的版本）
        
        优先从版本历史中查找，找不到则返回空字符串
        """
        try:
            cursor = self.db.execute("""
                SELECT content FROM note_versions
                WHERE note_id = ? AND created_at <= ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (note_id, our_updated_at))
            row = cursor.fetchone()
            return row['content'] if row else ''
        except Exception:
            # note_versions 表不存在
            return ''
    
    def record_conflict(
        self,
        note_id: int,
        user_id: int,
        strategy: str,
        base_content: str,
        their_content: str,
        our_content: str
    ) -> int:
        """
        记录冲突
        
        Args:
            note_id: 笔记 ID
            user_id: 冲突用户 ID
            strategy: 解决策略
            base_content: 基础版本
            their_content: 对方内容
            our_content: 我们的内容
            
        Returns:
            冲突记录 ID
        """
        if strategy not in self.VALID_STRATEGIES:
            raise ValueError(f"无效策略: {strategy}")
        
        cursor = self.db.execute("""
            INSERT INTO conflicts (note_id, user_id, strategy, 
                                   base_content, their_content, our_content)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (note_id, user_id, strategy, base_content, their_content, our_content))
        self.db.commit()
        return cursor.lastrowid
    
    def resolve_latest_wins(
        self, conflict_id: int, use_ours: bool = True
    ) -> str:
        """
        latest-wins 策略：选择其中一个版本
        
        Args:
            conflict_id: 冲突记录 ID
            use_ours: True = 用我们的版本，False = 用对方的版本
            
        Returns:
            解决后的内容
        """
        cursor = self.db.execute(
            "SELECT * FROM conflicts WHERE id = ?", (conflict_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"冲突记录不存在: {conflict_id}")
        
        resolved = row['our_content'] if use_ours else row['their_content']
        
        self.db.execute("""
            UPDATE conflicts 
            SET resolved_content = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (resolved, conflict_id))
        self.db.commit()
        
        return resolved
    
    def resolve_three_way_merge(self, conflict_id: int) -> str:
        """
        三路合并：基于 base/their/our 自动合并
        
        使用 Python difflib 进行文本合并
        
        Args:
            conflict_id: 冲突记录 ID
            
        Returns:
            合并后的内容
        """
        cursor = self.db.execute(
            "SELECT * FROM conflicts WHERE id = ?", (conflict_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"冲突记录不存在: {conflict_id}")
        
        base = row['base_content']
        their = row['their_content']
        our = row['our_content']
        
        if not base:
            # 没有基础版本，fallback 到 latest-wins
            resolved = our
        else:
            resolved = self._three_way_merge_text(base, their, our)
        
        self.db.execute("""
            UPDATE conflicts 
            SET resolved_content = ?, strategy = 'merge',
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (resolved, conflict_id))
        self.db.commit()
        
        return resolved
    
    def _three_way_merge_text(self, base: str, their: str, our: str) -> str:
        """
        三路文本合并
        
        使用 difflib 的 SequenceMatcher 进行合并
        """
        base_lines = base.splitlines(keepends=True)
        their_lines = their.splitlines(keepends=True)
        our_lines = our.splitlines(keepends=True)
        
        # 确保每行以换行符结尾
        if base_lines and not base_lines[-1].endswith('\n'):
            base_lines[-1] += '\n'
        if their_lines and not their_lines[-1].endswith('\n'):
            their_lines[-1] += '\n'
        if our_lines and not our_lines[-1].endswith('\n'):
            our_lines[-1] += '\n'
        
        # 使用 difflib 的 unified_diff 来检测差异
        merger = difflib.Differ()
        
        # 简单三路合并策略：
        # 1. 如果 our 和 their 都未修改某行，保留
        # 2. 如果只有 our 修改，用 our
        # 3. 如果只有 their 修改，用 their
        # 4. 如果都修改了且不同，用 our + 冲突标记
        
        result_lines = []
        i = j = k = 0
        
        # 简化版三路合并：逐行比较
        our_diff = dict(self._get_line_diffs(base_lines, our_lines))
        their_diff = dict(self._get_line_diffs(base_lines, their_lines))
        
        # 获取所有行的索引范围
        max_len = max(len(base_lines), len(our_lines), len(their_lines))
        
        # 使用 unified merge 算法
        result = self._simple_merge(base_lines, their_lines, our_lines)
        
        return ''.join(result)
    
    def _get_line_diffs(self, base_lines: List[str], new_lines: List[str]) -> List[Tuple[int, str]]:
        """获取行级别的差异"""
        diffs = []
        sm = difflib.SequenceMatcher(None, base_lines, new_lines)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                diffs.append((i1, ''.join(new_lines[j1:j2])))
        return diffs
    
    def _simple_merge(self, base: List[str], their: List[str], our: List[str]) -> List[str]:
        """简化的三路合并"""
        # 如果 our 和 their 相同，直接返回
        if our == their:
            return our[:]
        
        # 如果没有基础，返回我们的版本
        if not base:
            return our[:]
        
        # 使用 SequenceMatcher 进行三路合并
        result = []
        
        # 比较 our 和 their 相对于 base 的修改
        our_sm = difflib.SequenceMatcher(None, base, our)
        their_sm = difflib.SequenceMatcher(None, base, their)
        
        our_ops = our_sm.get_opcodes()
        their_ops = their_sm.get_opcodes()
        
        oi = ti = 0
        
        while oi < len(our_ops) and ti < len(their_ops):
            o_tag, o_i1, o_i2, o_j1, o_j2 = our_ops[oi]
            t_tag, t_i1, t_i2, t_j1, t_j2 = their_ops[ti]
            
            # 处理 base 中的重叠区域
            if o_tag == 'equal' and t_tag == 'equal':
                # 两边都没改，取 base
                for i in range(o_i1, o_i2):
                    if i < len(base):
                        result.append(base[i])
                oi += 1
                ti += 1
            elif o_tag == 'equal':
                # 只有 their 改了
                result.extend(their[t_j1:t_j2])
                ti += 1
            elif t_tag == 'equal':
                # 只有 our 改了
                result.extend(our[o_j1:o_j2])
                oi += 1
            elif o_i1 == t_i1 and o_i2 == t_i2:
                # 两边都改了同一区域
                if our[o_j1:o_j2] == their[t_j1:t_j2]:
                    # 改的一样
                    result.extend(our[o_j1:o_j2])
                else:
                    # 冲突！用我们的版本
                    result.extend(our[o_j1:o_j2])
                oi += 1
                ti += 1
            else:
                # 修改区域不重叠，都保留
                if o_i2 <= t_i1:
                    result.extend(our[o_j1:o_j2])
                    oi += 1
                else:
                    result.extend(their[t_j1:t_j2])
                    ti += 1
        
        # 处理剩余
        while oi < len(our_ops):
            _, _, _, j1, j2 = our_ops[oi]
            result.extend(our[j1:j2])
            oi += 1
        
        while ti < len(their_ops):
            _, _, _, j1, j2 = their_ops[ti]
            result.extend(their[j1:j2])
            ti += 1
        
        return result
    
    def resolve_manual(self, conflict_id: int, resolved_content: str) -> bool:
        """
        手动解决：直接指定解决后的内容
        
        Args:
            conflict_id: 冲突记录 ID
            resolved_content: 手动解决后的内容
            
        Returns:
            是否成功
        """
        cursor = self.db.execute(
            "SELECT id FROM conflicts WHERE id = ?", (conflict_id,)
        )
        if not cursor.fetchone():
            return False
        
        self.db.execute("""
            UPDATE conflicts 
            SET resolved_content = ?, strategy = 'manual',
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (resolved_content, conflict_id))
        self.db.commit()
        return True
    
    def get_unresolved(self, note_id: int = None) -> List[Dict]:
        """
        获取未解决的冲突
        
        Args:
            note_id: 按笔记过滤（None = 全部）
            
        Returns:
            未解决冲突列表
        """
        if note_id:
            cursor = self.db.execute("""
                SELECT * FROM conflicts 
                WHERE resolved_at IS NULL AND note_id = ?
                ORDER BY created_at DESC
            """, (note_id,))
        else:
            cursor = self.db.execute("""
                SELECT * FROM conflicts 
                WHERE resolved_at IS NULL
                ORDER BY created_at DESC
            """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_conflict_history(self, note_id: int) -> List[Dict]:
        """
        获取笔记冲突历史
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            冲突记录列表
        """
        cursor = self.db.execute("""
            SELECT * FROM conflicts 
            WHERE note_id = ?
            ORDER BY created_at DESC
        """, (note_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_conflict_stats(self) -> Dict:
        """
        获取冲突统计
        
        Returns:
            统计字典
        """
        cursor = self.db.execute("""
            SELECT 
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN resolved_at IS NULL THEN 1 ELSE 0 END), 0) as unresolved,
                COALESCE(SUM(CASE WHEN strategy = 'latest-wins' THEN 1 ELSE 0 END), 0) as latest_wins_count,
                COALESCE(SUM(CASE WHEN strategy = 'merge' THEN 1 ELSE 0 END), 0) as merge_count,
                COALESCE(SUM(CASE WHEN strategy = 'manual' THEN 1 ELSE 0 END), 0) as manual_count
            FROM conflicts
        """)
        row = cursor.fetchone()
        return {
            'total': row['total'],
            'unresolved': row['unresolved'] or 0,
            'resolved': row['total'] - (row['unresolved'] or 0),
            'by_strategy': {
                'latest-wins': row['latest_wins_count'] or 0,
                'merge': row['merge_count'] or 0,
                'manual': row['manual_count'] or 0
            }
        }
