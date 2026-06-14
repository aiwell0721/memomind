"""验证 Database 启用的 SQLite PRAGMA。

并发写入场景下，SQLite 默认 busy_timeout=0 会立即抛 'database is locked'，
而不是等待。本测试锁定关键 PRAGMA 的预期值。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database


class TestDatabasePragmas(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.close()

    def _pragma(self, name: str):
        return self.db.conn.execute(f"PRAGMA {name}").fetchone()[0]

    def test_foreign_keys_enabled(self):
        self.assertEqual(1, self._pragma("foreign_keys"))

    def test_busy_timeout_is_set(self):
        """启用 busy_timeout，避免并发写时立即抛 'database is locked'。"""
        # 期望 ≥ 5000ms（5 秒）。具体值由实现决定，但绝不能是 0。
        self.assertGreaterEqual(self._pragma("busy_timeout"), 5000)

    def test_synchronous_normal_or_full(self):
        """synchronous 设为 NORMAL(1) 或 FULL(2)，不能是 OFF(0)。"""
        self.assertIn(self._pragma("synchronous"), (1, 2))


if __name__ == "__main__":
    unittest.main()
