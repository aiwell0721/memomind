"""
MemoMind 导入服务测试
"""

import unittest
import sys
import json
import tempfile
import os
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.import_service import ImportService, ImportResult


class TestImportService(unittest.TestCase):
    """导入服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.db = Database(":memory:")
        self.importer = ImportService(self.db)
    
    def tearDown(self):
        """测试后清理"""
        self.db.close()
    
    def test_parse_markdown_frontmatter(self):
        """测试解析 Markdown Frontmatter"""
        markdown = """---
title: 测试笔记
tags: ["测试", "MemoMind"]
created_at: 2026-04-21T00:00:00
---

这是笔记内容。
"""
        note_data = self.importer._parse_markdown_frontmatter(markdown)
        
        self.assertIsNotNone(note_data)
        self.assertEqual(note_data['title'], "测试笔记")
        self.assertEqual(note_data['tags'], ["测试", "MemoMind"])
        self.assertEqual(note_data['content'], "这是笔记内容。")
    
    def test_parse_markdown_no_frontmatter(self):
        """测试解析无 Frontmatter 的 Markdown"""
        markdown = "这是没有 Frontmatter 的内容。"
        
        note_data = self.importer._parse_markdown_frontmatter(markdown)
        
        self.assertIsNone(note_data)
    
    def test_import_markdown_file(self):
        """测试导入 Markdown 文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmpfile:
            tmpfile.write("""---
title: Import Test
tags: ["import", "test"]
---

This is imported content.
""")
            tmpfilepath = tmpfile.name
        
        try:
            note_id, result = self.importer.import_markdown_file(tmpfilepath)
            
            # 检查导入结果
            self.assertGreater(note_id, 0)
            self.assertEqual(result.imported, 1)
            
            # 验证数据库内容
            cursor = self.db.execute("SELECT title, content FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            self.assertEqual(row['title'], "Import Test")
            self.assertIn("imported content", row['content'])
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)
    
    def test_import_json_file(self):
        """测试导入 JSON 文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmpfile:
            json.dump({
                'version': '1.0',
                'notes': [
                    {
                        'title': 'JSON Import Test',
                        'content': 'This is content imported from JSON',
                        'tags': ['JSON', 'import']
                    }
                ]
            }, tmpfile, ensure_ascii=False)
            tmpfilepath = tmpfile.name
        
        try:
            result = self.importer.import_json_file(tmpfilepath)
            
            # 检查导入结果
            self.assertEqual(result.imported, 1)
            
            # 验证数据库内容
            cursor = self.db.execute("SELECT title FROM notes WHERE title = ?", ("JSON Import Test",))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)
    
    def test_import_conflict_skip(self):
        """测试冲突处理：跳过"""
        import json
        # 先创建同名笔记
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Duplicate Title", "Original content", json.dumps(["original"])))
        self.db.commit()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmpfile:
            tmpfile.write("""---
title: Duplicate Title
tags: ["new"]
---

New content.
""")
            tmpfilepath = tmpfile.name
        
        try:
            note_id, result = self.importer.import_markdown_file(tmpfilepath, ImportService.CONFLICT_SKIP)
            
            # 应该跳过
            self.assertEqual(note_id, 0)
            self.assertEqual(result.skipped, 1)
            
            # 验证数据库内容未变
            cursor = self.db.execute("SELECT content FROM notes WHERE title = ?", ("Duplicate Title",))
            row = cursor.fetchone()
            self.assertEqual(row['content'], "Original content")
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)
    
    def test_import_conflict_overwrite(self):
        """测试冲突处理：覆盖"""
        import json
        # 先创建同名笔记
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Duplicate Title", "Original content", json.dumps(["original"])))
        self.db.commit()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmpfile:
            tmpfile.write("""---
title: Duplicate Title
tags: ["new"]
---

New content.
""")
            tmpfilepath = tmpfile.name
        
        try:
            note_id, result = self.importer.import_markdown_file(tmpfilepath, ImportService.CONFLICT_OVERWRITE)
            
            # 应该更新
            self.assertGreater(note_id, 0)
            
            # 验证数据库内容已更新
            cursor = self.db.execute("SELECT content, tags FROM notes WHERE title = ?", ("Duplicate Title",))
            row = cursor.fetchone()
            self.assertEqual(row['content'], "New content.")
            self.assertEqual(json.loads(row['tags']), ["new"])
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)
    
    def test_import_markdown_directory(self):
        """测试批量导入目录"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建多个 Markdown 文件
            for i in range(3):
                filepath = os.path.join(tmpdir, f"note_{i}.md")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"""---
title: Note {i}
tags: ["batch"]
---

This is note {i} content.
""")
            
            # 批量导入
            result = self.importer.import_markdown_directory(tmpdir)
            
            # 检查导入结果
            self.assertEqual(result.imported, 3)
            
            # 验证数据库内容
            cursor = self.db.execute("SELECT COUNT(*) as count FROM notes WHERE tags LIKE ?", ('%batch%',))
            row = cursor.fetchone()
            self.assertEqual(row['count'], 3)
    
    def test_import_result_summary(self):
        """测试导入结果摘要"""
        result = ImportResult()
        result.imported = 5
        result.skipped = 2
        result.updated = 1
        result.add_error("test.md", "Test error")
        
        summary = result.summary()
        
        self.assertIn("5 新增", summary)
        self.assertIn("2 跳过", summary)
        self.assertIn("1 错误", summary)
    
    def test_import_nonexistent_directory(self):
        """测试导入不存在的目录"""
        result = self.importer.import_markdown_directory("/nonexistent/path")
        
        self.assertEqual(len(result.errors), 1)
        self.assertIn("目录不存在", result.errors[0]['error'])
    
    def test_import_invalid_json(self):
        """测试导入无效 JSON"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmpfile:
            tmpfile.write('{"invalid": "format"}')  # 缺少 notes 字段
            tmpfilepath = tmpfile.name
        
        try:
            result = self.importer.import_json_file(tmpfilepath)
            
            # 应该有错误
            self.assertEqual(len(result.errors), 1)
            self.assertIn("无效的 JSON 格式", result.errors[0]['error'])
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)


class TestImportServiceWithExistingData(unittest.TestCase):
    """导入服务与现有数据测试"""
    
    def setUp(self):
        """测试前准备"""
        self.db = Database(":memory:")
        self.importer = ImportService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """测试后清理"""
        self.db.close()
    
    def _seed_data(self):
        """插入测试数据"""
        import json
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Existing Note", "Existing content", json.dumps(["existing"])))
        self.db.commit()
    
    def test_import_preserves_existing(self):
        """测试导入不影响现有笔记"""
        # 导入不同标题的笔记
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmpfile:
            tmpfile.write("""---
title: New Note
tags: ["new"]
---

New content.
""")
            tmpfilepath = tmpfile.name
        
        try:
            self.importer.import_markdown_file(tmpfilepath)
            
            # 验证现有笔记未受影响
            cursor = self.db.execute("SELECT content FROM notes WHERE title = ?", ("Existing Note",))
            row = cursor.fetchone()
            self.assertEqual(row['content'], "Existing content")
            
            # 验证新笔记已导入
            cursor = self.db.execute("SELECT COUNT(*) FROM notes")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)


if __name__ == '__main__':
    unittest.main()
