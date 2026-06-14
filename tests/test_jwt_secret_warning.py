"""验证 JWT 密钥来源告警。

MEMOMIND_SECRET_KEY 未设时，进程会自动生成随机密钥——这意味着每次重启
所有已发 token 失效。生产环境必须看到明显告警。
"""

import os
import sys
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.api_server import resolve_secret_key


class TestJwtSecretWarning(unittest.TestCase):
    def test_env_var_set_no_warning(self):
        """显式设置环境变量时，不应有警告。"""
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            secret = resolve_secret_key(env={"MEMOMIND_SECRET_KEY": "x" * 32})
        self.assertEqual(secret, "x" * 32)
        self.assertEqual(0, len([w for w in ws if issubclass(w.category, UserWarning)]))

    def test_env_var_missing_warns(self):
        """未设环境变量时，必须发 UserWarning 提醒生产环境配置。"""
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            secret = resolve_secret_key(env={})
        # 密钥仍然返回（保持可用），但产生告警
        self.assertTrue(len(secret) >= 32)
        user_warnings = [w for w in ws if issubclass(w.category, UserWarning)]
        self.assertEqual(1, len(user_warnings),
                         f"期望 1 条 UserWarning，实际 {len(user_warnings)}")
        msg = str(user_warnings[0].message)
        self.assertIn("MEMOMIND_SECRET_KEY", msg)


if __name__ == "__main__":
    unittest.main()
