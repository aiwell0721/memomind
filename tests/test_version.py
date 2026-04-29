"""
MemoMind 版本历史服务测试
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.version_service import VersionService
from core.diff_service import DiffService


class TestVersionService(unittest.TestCase):
    """版本服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.db = Database(":memory:")
        self.versions = VersionService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """测试后清理"""
        self.db.close()
    
    def _seed_data(self):
        """插入测试数据"""
        # 创建测试笔记（确保 notes 表存在）
        import json
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Test Note", "This is initial content", json.dumps(["test"])))
        self.db.commit()
        self.note_id = 1
    
    def test_save_version(self):
        """测试保存版本"""
        version_num = self.versions.save_version(
            note_id=self.note_id,
            title="测试笔记",
            content="这是初始内容",
            tags=["测试"]
        )
        
        self.assertEqual(version_num, 1)
    
    def test_save_multiple_versions(self):
        """测试保存多个版本"""
        v1 = self.versions.save_version(self.note_id, "标题 1", "内容 1", ["标签 1"])
        v2 = self.versions.save_version(self.note_id, "标题 2", "内容 2", ["标签 2"])
        v3 = self.versions.save_version(self.note_id, "标题 3", "内容 3", ["标签 3"])
        
        self.assertEqual(v1, 1)
        self.assertEqual(v2, 2)
        self.assertEqual(v3, 3)
    
    def test_get_versions(self):
        """测试获取版本列表"""
        # 保存 3 个版本
        self.versions.save_version(self.note_id, "标题 1", "内容 1", ["标签 1"])
        self.versions.save_version(self.note_id, "标题 2", "内容 2", ["标签 2"])
        self.versions.save_version(self.note_id, "标题 3", "内容 3", ["标签 3"])
        
        # 获取版本列表
        versions = self.versions.get_versions(self.note_id, limit=10)
        
        self.assertEqual(len(versions), 3)
        # 检查倒序排列
        self.assertEqual(versions[0].version_number, 3)
        self.assertEqual(versions[1].version_number, 2)
        self.assertEqual(versions[2].version_number, 1)
    
    def test_get_version(self):
        """测试获取指定版本"""
        v1 = self.versions.save_version(self.note_id, "标题 1", "内容 1", ["标签 1"])
        
        version = self.versions.get_version(v1)
        
        self.assertIsNotNone(version)
        self.assertEqual(version.title, "标题 1")
        self.assertEqual(version.content, "内容 1")
        self.assertEqual(version.tags, ["标签 1"])
    
    def test_get_version_not_found(self):
        """测试获取不存在的版本"""
        version = self.versions.get_version(999)
        self.assertIsNone(version)
    
    def test_restore_version(self):
        """测试恢复版本"""
        # 保存初始版本
        v1 = self.versions.save_version(self.note_id, "Original Title", "Original Content", ["original"])
        
        # 保存第二个版本（模拟修改）
        v2 = self.versions.save_version(self.note_id, "New Title", "New Content", ["new"])
        
        # 恢复到第一个版本
        result = self.versions.restore_version(v1)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], "Original Title")
        self.assertEqual(result['content'], "Original Content")
        self.assertEqual(result['tags'], ["original"])
    
    def test_tag_version(self):
        """测试标记版本"""
        v1 = self.versions.save_version(self.note_id, "标题", "内容", ["标签"])
        
        success = self.versions.tag_version(v1, "重要版本")
        
        self.assertTrue(success)
        
        # 验证标记
        version = self.versions.get_version(v1)
        self.assertTrue(version.is_tagged)
        self.assertEqual(version.tag_name, "重要版本")
    
    def test_get_tagged_versions(self):
        """测试获取标签版本"""
        v1 = self.versions.save_version(self.note_id, "标题 1", "内容 1", ["标签 1"])
        v2 = self.versions.save_version(self.note_id, "标题 2", "内容 2", ["标签 2"])
        v3 = self.versions.save_version(self.note_id, "标题 3", "内容 3", ["标签 3"])
        
        # 标记 v1 和 v3
        self.versions.tag_version(v1, "初始版本")
        self.versions.tag_version(v3, "重要版本")
        
        tagged = self.versions.get_tagged_versions(self.note_id)
        
        self.assertEqual(len(tagged), 2)
        tag_names = [v.tag_name for v in tagged]
        self.assertIn("初始版本", tag_names)
        self.assertIn("重要版本", tag_names)
    
    def test_cleanup_versions(self):
        """测试清理版本"""
        # 创建 15 个版本
        for i in range(15):
            self.versions.save_version(
                self.note_id,
                f"标题{i}",
                f"内容{i}",
                [f"标签{i}"]
            )
        
        # 清理，保留 10 个
        deleted = self.versions.cleanup_versions(self.note_id, keep_count=10)
        
        self.assertEqual(deleted, 5)
        
        # 验证剩余版本
        versions = self.versions.get_versions(self.note_id, limit=20)
        self.assertEqual(len(versions), 10)
        # 应该保留最新的 10 个（版本 6-15）
        self.assertEqual(versions[0].version_number, 15)
        self.assertEqual(versions[-1].version_number, 6)
    
    def test_cleanup_preserves_tagged(self):
        """测试清理保留标签版本"""
        # 创建 15 个版本
        for i in range(15):
            v = self.versions.save_version(
                self.note_id,
                f"标题{i}",
                f"内容{i}",
                [f"标签{i}"]
            )
            # 标记前 3 个版本
            if i < 3:
                self.versions.tag_version(v, f"重要{i}")
        
        # 清理，保留 10 个
        deleted = self.versions.cleanup_versions(self.note_id, keep_count=10)
        
        # 应该只删除 2 个（版本 4 和 5），前 3 个标签版本保留
        self.assertEqual(deleted, 2)
        
        # 验证标签版本还在
        tagged = self.versions.get_tagged_versions(self.note_id)
        self.assertEqual(len(tagged), 3)


class TestDiffService(unittest.TestCase):
    """版本对比服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.diff_service = DiffService()
    
    def test_compare_texts_no_change(self):
        """测试对比无变更文本"""
        diff = self.diff_service.compare_texts("相同内容", "相同内容")
        
        # 应该没有差异（或者只有很少的上下文行）
        self.assertLessEqual(len(diff), 5)
    
    def test_compare_texts_with_changes(self):
        """测试对比有变更文本"""
        text_a = "第一行\n第二行\n第三行"
        text_b = "第一行\n修改的第二行\n第三行\n第四行"
        
        diff = self.diff_service.compare_texts(text_a, text_b)
        
        # 应该有差异
        self.assertGreater(len(diff), 2)
    
    def test_compare_versions(self):
        """测试对比版本"""
        from core.version_service import Version
        
        version_a = Version(
            id=1, note_id=1, version_number=1,
            title="标题 A", content="内容 A\n第二行",
            tags=["标签"], created_at="2026-04-20",
            change_summary=None, is_tagged=False, tag_name=None
        )
        
        version_b = Version(
            id=2, note_id=1, version_number=2,
            title="标题 B", content="内容 B\n第二行\n第三行",
            tags=["标签"], created_at="2026-04-21",
            change_summary=None, is_tagged=False, tag_name=None
        )
        
        diff = self.diff_service.compare_versions(version_a, version_b)
        
        self.assertEqual(diff.version_a_id, 1)
        self.assertEqual(diff.version_b_id, 2)
        self.assertGreater(diff.added_lines, 0)
    
    def test_generate_summary(self):
        """测试生成变更摘要"""
        from core.diff_service import Diff
        
        diff = Diff(
            version_a_id=1, version_b_id=2,
            title_diff=["- 旧标题", "+ 新标题"],
            content_diff=["+ 新增行"],
            added_lines=1, removed_lines=0
        )
        
        summary = self.diff_service.generate_summary(diff)
        
        self.assertIn("标题", summary)
        self.assertIn("新增", summary)
    
    def test_generate_summary_no_change(self):
        """测试生成无变更摘要"""
        from core.diff_service import Diff
        
        diff = Diff(
            version_a_id=1, version_b_id=2,
            title_diff=[], content_diff=[],
            added_lines=0, removed_lines=0
        )
        
        summary = self.diff_service.generate_summary(diff)
        
        self.assertEqual(summary, "无变更")


if __name__ == '__main__':
    unittest.main()
