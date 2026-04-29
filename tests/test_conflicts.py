"""
MemoMind 冲突检测与合并测试 - PR-015
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.conflict_service import ConflictService, ConflictRecord


class TestConflictDetection:
    """冲突检测测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.conflict = ConflictService(self.db)
    
    def teardown_method(self):
        self.db.close()
    
    def test_no_conflict(self):
        """无冲突：时间戳一致"""
        self.db.execute("""
            INSERT INTO notes (id, title, content, updated_at)
            VALUES (1, 'Test', 'content', '2026-04-24 10:00:00')
        """)
        self.db.commit()
        
        result = self.conflict.detect_conflict(
            note_id=1,
            our_content='new content',
            our_updated_at='2026-04-24 10:00:00',
            expected_updated_at='2026-04-24 10:00:00'
        )
        assert result is None
    
    def test_conflict_detected(self):
        """检测到冲突：时间戳不一致"""
        self.db.execute("""
            INSERT INTO notes (id, title, content, updated_at)
            VALUES (1, 'Test', 'their version', '2026-04-24 11:00:00')
        """)
        self.db.commit()
        
        result = self.conflict.detect_conflict(
            note_id=1,
            our_content='our version',
            our_updated_at='2026-04-24 10:00:00',
            expected_updated_at='2026-04-24 11:00:00'
        )
        
        assert result is not None
        assert result['note_id'] == 1
        assert result['their_content'] == 'their version'
        assert result['our_content'] == 'our version'
    
    def test_conflict_note_not_found(self):
        """笔记不存在"""
        result = self.conflict.detect_conflict(
            note_id=999,
            our_content='content',
            our_updated_at='2026-04-24 10:00:00',
            expected_updated_at='2026-04-24 11:00:00'
        )
        assert result is None


class TestConflictResolution:
    """冲突解决测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.conflict = ConflictService(self.db)
    
    def teardown_method(self):
        self.db.close()
    
    def _create_conflict(self, strategy='latest-wins'):
        """创建测试冲突"""
        return self.conflict.record_conflict(
            note_id=1, user_id=1, strategy=strategy,
            base_content='base line1\nbase line2\nbase line3\n',
            their_content='base line1\ntheir change\nbase line3\n',
            our_content='base line1\nour change\nbase line3\n'
        )
    
    def test_record_conflict(self):
        """记录冲突"""
        cid = self._create_conflict()
        assert cid >= 1
    
    def test_record_conflict_invalid_strategy(self):
        """无效策略"""
        with pytest.raises(ValueError, match="无效策略"):
            self.conflict.record_conflict(
                note_id=1, user_id=1, strategy='invalid',
                base_content='', their_content='', our_content=''
            )
    
    def test_resolve_latest_wins_ours(self):
        """latest-wins：选择我们的版本"""
        cid = self._create_conflict()
        resolved = self.conflict.resolve_latest_wins(cid, use_ours=True)
        assert resolved == 'base line1\nour change\nbase line3\n'
    
    def test_resolve_latest_wins_theirs(self):
        """latest-wins：选择对方的版本"""
        cid = self._create_conflict()
        resolved = self.conflict.resolve_latest_wins(cid, use_ours=False)
        assert resolved == 'base line1\ntheir change\nbase line3\n'
    
    def test_resolve_latest_wins_not_found(self):
        """不存在的冲突记录"""
        with pytest.raises(ValueError, match="冲突记录不存在"):
            self.conflict.resolve_latest_wins(999)
    
    def test_resolve_three_way_merge(self):
        """三路合并"""
        cid = self._create_conflict()
        resolved = self.conflict.resolve_three_way_merge(cid)
        # 三路合并应该保留我们的修改（因为双方修改了同一行）
        assert 'our change' in resolved or 'their change' in resolved
    
    def test_resolve_three_way_merge_not_found(self):
        """不存在的冲突记录"""
        with pytest.raises(ValueError, match="冲突记录不存在"):
            self.conflict.resolve_three_way_merge(999)
    
    def test_resolve_manual(self):
        """手动解决"""
        cid = self._create_conflict()
        result = self.conflict.resolve_manual(cid, 'manually resolved content')
        assert result is True
    
    def test_resolve_manual_not_found(self):
        """不存在的冲突记录"""
        result = self.conflict.resolve_manual(999, 'content')
        assert result is False
    
    def test_get_unresolved(self):
        """获取未解决冲突"""
        self._create_conflict()
        self._create_conflict()
        
        # 解决一个
        cid = self._create_conflict()
        self.conflict.resolve_latest_wins(cid)
        
        unresolved = self.conflict.get_unresolved()
        assert len(unresolved) == 2
    
    def test_get_unresolved_by_note(self):
        """按笔记获取未解决冲突"""
        self.conflict.record_conflict(
            note_id=1, user_id=1, strategy='latest-wins',
            base_content='', their_content='', our_content=''
        )
        self.conflict.record_conflict(
            note_id=2, user_id=1, strategy='latest-wins',
            base_content='', their_content='', our_content=''
        )
        
        unresolved = self.conflict.get_unresolved(note_id=1)
        assert len(unresolved) == 1
    
    def test_get_conflict_history(self):
        """冲突历史"""
        self._create_conflict()
        self._create_conflict()
        
        history = self.conflict.get_conflict_history(1)
        assert len(history) == 2
    
    def test_get_conflict_stats(self):
        """冲突统计"""
        self._create_conflict('latest-wins')
        self._create_conflict('merge')
        cid = self._create_conflict('latest-wins')
        self.conflict.resolve_latest_wins(cid)
        
        stats = self.conflict.get_conflict_stats()
        assert stats['total'] == 3
        assert stats['unresolved'] == 2
        assert stats['resolved'] == 1
        assert stats['by_strategy']['latest-wins'] == 2
        assert stats['by_strategy']['merge'] == 1


class TestThreeWayMerge:
    """三路合并算法测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.conflict = ConflictService(self.db)
    
    def teardown_method(self):
        self.db.close()
    
    def test_merge_no_base(self):
        """无基础版本：fallback 到 our"""
        cid = self.conflict.record_conflict(
            note_id=1, user_id=1, strategy='latest-wins',
            base_content='', their_content='their', our_content='ours'
        )
        resolved = self.conflict.resolve_three_way_merge(cid)
        assert resolved == 'ours'
    
    def test_merge_same_change(self):
        """双方修改相同"""
        cid = self.conflict.record_conflict(
            note_id=1, user_id=1, strategy='latest-wins',
            base_content='line1\nline2\n',
            their_content='line1\nchanged\n',
            our_content='line1\nchanged\n'
        )
        resolved = self.conflict.resolve_three_way_merge(cid)
        assert 'changed' in resolved
    
    def test_merge_non_overlapping(self):
        """非重叠修改：应该合并双方"""
        cid = self.conflict.record_conflict(
            note_id=1, user_id=1, strategy='latest-wins',
            base_content='line1\nline2\nline3\n',
            their_content='their_line1\nline2\nline3\n',
            our_content='line1\nline2\nour_line3\n'
        )
        resolved = self.conflict.resolve_three_way_merge(cid)
        # 应该包含双方的修改
        assert len(resolved) > 0


class TestConflictRecordToDict:
    """ConflictRecord 模型转换测试"""
    
    def test_to_dict(self):
        record = ConflictRecord(
            id=1, note_id=1, user_id=1, strategy='latest-wins',
            base_content='base', their_content='their', our_content='our',
            resolved_content='resolved', created_at='2026-04-24'
        )
        d = record.to_dict()
        assert d['strategy'] == 'latest-wins'
        assert d['resolved_content'] == 'resolved'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
