"""验证 notes 表关键查询字段的索引覆盖。

workspace_id 通过 ALTER TABLE 添加（见 workspace_service.py），如果不显式建索引，
``WHERE workspace_id = ?`` 会走全表扫描。本测试用 EXPLAIN QUERY PLAN 锁定索引存在。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.workspace_service import WorkspaceService


class TestNotesIndexes(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        # WorkspaceService 的 __init__ 会 ALTER TABLE notes ADD COLUMN workspace_id
        WorkspaceService(self.db)

    def tearDown(self):
        self.db.close()

    def test_workspace_id_query_uses_index(self):
        """``WHERE workspace_id = ?`` 必须命中索引，不能走 SCAN（全表扫描）。

        现状：workspace_service.py 启动时已建 idx_notes_workspace。
        本测试锁定该索引存在，防止后续 PR 误删时静默退化为全表扫描。
        """
        plan = self.db.execute(
            "EXPLAIN QUERY PLAN SELECT id FROM notes WHERE workspace_id = ?",
            (1,)
        ).fetchall()
        detail = " | ".join(str(row[3]) for row in plan).upper()
        # EXPLAIN 输出形如 'SEARCH notes USING (COVERING )?INDEX idx_notes_workspace (...)'
        # 关键判定：用了 INDEX 而非 'SCAN TABLE'
        self.assertIn("INDEX", detail, f"workspace_id 查询未命中索引: {detail}")
        self.assertNotIn("SCAN TABLE", detail, f"workspace_id 走了全表扫描: {detail}")


if __name__ == "__main__":
    unittest.main()
