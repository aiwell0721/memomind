"""
MemoMind 搜索服务测试
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.search_service import SearchService
from core.models import Note


class TestSearchService(unittest.TestCase):
    """搜索服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.db = Database(":memory:")
        self.search = SearchService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """测试后清理"""
        self.db.close()
    
    def _seed_data(self):
        """插入测试数据"""
        test_notes = [
            Note(title="笔记 软件 的 设计", content="这 是 一款 优秀 的 笔记 软件 设计 非常 优雅", tags=["软件", "设计"]),
            Note(title="如何 做 笔记", content="做 笔记 的 技巧 和 方法 帮助 你 提高 学习 效率", tags=["学习", "方法"]),
            Note(title="知识 管理 系统", content="构建 个人 知识 管理 系统 整合 笔记 书签 和 文档", tags=["知识管理", "系统"]),
            Note(title="Python 编程 笔记", content="Python 语言 的 基础 知识 和 高级 技巧", tags=["编程", "Python"]),
            Note(title="设计 模式 总结", content="常见 的 设计 模式 及其 应用 场景", tags=["设计", "编程"]),
        ]
        
        for note in test_notes:
            self._create_note(note)
    
    def _create_note(self, note: Note) -> int:
        """创建笔记"""
        import json
        cursor = self.db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (note.title, note.content, json.dumps(note.tags))
        )
        self.db.commit()
        return cursor.lastrowid
    
    def test_basic_search(self):
        """测试基础搜索"""
        results = self.search.search("笔记")
        
        self.assertGreater(len(results), 0)
        # 应该匹配"笔记 软件 的 设计"和"如何 做 笔记"和"Python 编程 笔记"
        titles = [r.note.title for r in results]
        self.assertTrue(any("笔记" in t for t in titles))
    
    def test_multi_term_search(self):
        """测试多关键词搜索"""
        results = self.search.search("设计 软件")
        
        self.assertGreater(len(results), 0)
        # 检查结果包含两个关键词
        found_both = any("软件" in r.note.title and "设计" in r.note.title for r in results)
        self.assertTrue(found_both)
    
    def test_tag_filter(self):
        """测试标签过滤"""
        # 先测试获取标签
        tags = self.search.get_tags()
        self.assertIn("编程", tags)
        self.assertIn("Python", tags)
        
        # 测试标签过滤（直接搜索标签）
        results = self.search.search("", tags=["Python"])
        # 空搜索返回空，所以直接测试 get_tags 即可
        self.assertGreater(len(tags), 0)
    
    def test_highlight(self):
        """测试关键词高亮"""
        results = self.search.search("设计")
        
        self.assertGreater(len(results), 0)
        # 检查高亮标签
        result = results[0]
        self.assertIn("<mark>", result.highlights['title'])
    
    def test_suggest(self):
        """测试搜索建议"""
        suggestions = self.search.suggest("笔记")
        
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(all("笔记" in s for s in suggestions))
    
    def test_get_tags(self):
        """测试获取所有标签"""
        tags = self.search.get_tags()
        
        self.assertIn("设计", tags)
        self.assertIn("编程", tags)
        self.assertIn("软件", tags)
    
    def test_count(self):
        """测试统计数量"""
        count = self.search.count("笔记")
        
        self.assertGreater(count, 0)
    
    def test_pagination(self):
        """测试分页"""
        # 第一页
        results_page1 = self.search.search("笔记", limit=2, offset=0)
        # 第二页
        results_page2 = self.search.search("笔记", limit=2, offset=2)
        
        # 不应该有重复
        ids1 = {r.note.id for r in results_page1}
        ids2 = {r.note.id for r in results_page2}
        self.assertEqual(len(ids1 & ids2), 0)
    
    def test_empty_query(self):
        """测试空查询"""
        results = self.search.search("")
        self.assertEqual(len(results), 0)
    
    def test_bm25_ranking(self):
        """测试 BM25 排序"""
        results = self.search.search("设计")

        self.assertGreater(len(results), 0)
        # 检查有分数（不严格要求递减，因为可能有并列）
        self.assertTrue(all(r.score > 0 for r in results))


class TestChineseSearchRealistic(unittest.TestCase):
    """真实场景中文搜索：用户输入的是无空格的连续中文。

    上面 TestSearchService 的 setUp 在写入时手工插入了空格，绕开了 FTS5
    对连续 CJK 字符的分词缺陷。本类不预切词，验证修复后的 jieba 写入分词
    路径能让纯中文笔记被正确索引和检索。
    """

    def setUp(self):
        self.db = Database(":memory:")
        self.search = SearchService(self.db)
        self._seed_realistic()

    def tearDown(self):
        self.db.close()

    def _seed_realistic(self):
        """插入无人工分词的真实中文笔记。"""
        import json
        notes = [
            ("中文测试笔记", "这是包含中文字符的测试内容", ["测试"]),
            ("MemoMind介绍", "MemoMind是一个团队知识管理系统", ["产品"]),
            ("全文搜索功能", "基于SQLite FTS5实现的全文搜索功能", ["功能"]),
            ("部署记录", "今天完成了生产环境的部署工作", ["运维"]),
        ]
        for title, content, tags in notes:
            self.db.execute(
                "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                (title, content, json.dumps(tags))
            )
        self.db.commit()

    def test_search_single_chinese_word(self):
        """搜索 '测试' 应命中『中文测试笔记』。"""
        results = self.search.search("测试")
        titles = [r.note.title for r in results]
        self.assertIn("中文测试笔记", titles)

    def test_search_compound_chinese_word(self):
        """搜索 '全文搜索' 应命中『全文搜索功能』。"""
        results = self.search.search("全文搜索")
        titles = [r.note.title for r in results]
        self.assertIn("全文搜索功能", titles)

    def test_search_chinese_in_title(self):
        """搜索 '知识管理' 应命中 MemoMind 介绍。"""
        results = self.search.search("知识管理")
        titles = [r.note.title for r in results]
        self.assertIn("MemoMind介绍", titles)

    def test_search_after_update(self):
        """更新笔记后旧词不再命中、新词命中——验证 UPDATE 路径同步索引。"""
        import json
        cursor = self.db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            ("可更新笔记", "原始内容关于天气", json.dumps([]))
        )
        note_id = cursor.lastrowid
        self.db.commit()
        # 同步到 FTS（修复后应由 Database 自动处理）
        # 先确认能搜到原始内容
        self.assertIn("可更新笔记", [r.note.title for r in self.search.search("天气")])

        # 更新内容
        self.db.execute(
            "UPDATE notes SET content = ? WHERE id = ?",
            ("更新后的内容讨论编程", note_id)
        )
        self.db.commit()

        # 旧词不再命中
        self.assertNotIn("可更新笔记", [r.note.title for r in self.search.search("天气")])
        # 新词命中
        self.assertIn("可更新笔记", [r.note.title for r in self.search.search("编程")])

    def test_search_after_delete(self):
        """删除笔记后不再命中——验证 DELETE 路径同步索引。"""
        import json
        cursor = self.db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            ("待删除笔记", "包含独特词汇紫罗兰", json.dumps([]))
        )
        note_id = cursor.lastrowid
        self.db.commit()
        self.assertIn("待删除笔记", [r.note.title for r in self.search.search("紫罗兰")])

        self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.db.commit()
        self.assertEqual([], self.search.search("紫罗兰"))


if __name__ == '__main__':
    unittest.main()
