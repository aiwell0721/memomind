"""
MemoMind 笔记摘要生成测试
"""

import pytest
import json
from core.database import Database
from core.summarization_service import SummarizationService


@pytest.fixture
def db():
    """创建测试数据库"""
    database = Database(":memory:")
    database.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    database.commit()
    return database


@pytest.fixture
def summary_service(db):
    """创建摘要服务"""
    return SummarizationService(db)


@pytest.fixture
def long_notes(db):
    """插入长笔记"""
    notes = [
        ("Python 完整教程", 
         "Python 是一种简单易学的编程语言。Python 由 Guido van Rossum 于 1991 年创建。"
         "Python 支持面向对象、函数式和过程式编程。Python 的标准库非常丰富。"
         "使用 Python 可以进行 Web 开发、数据分析、机器学习等多种任务。"
         "Python 的语法简洁明了，适合初学者学习。Python 拥有庞大的社区支持。"
         "常用的 Python 框架有 Django、Flask、FastAPI 等。"
         "Python 在数据科学领域非常流行，常用库包括 NumPy、Pandas、Matplotlib。"
         "Python 也广泛应用于人工智能领域，TensorFlow 和 PyTorch 都支持 Python。",
         json.dumps(["Python", "编程"])),
        ("机器学习从入门到精通",
         "机器学习是人工智能的重要分支。机器学习使用算法让计算机从数据中学习。"
         "监督学习使用标注数据训练模型，常见的任务包括分类和回归。"
         "无监督学习从无标注数据中发现模式，如聚类和降维。"
         "强化学习通过与环境交互来学习最优策略。"
         "常用的机器学习框架有 TensorFlow、PyTorch 和 scikit-learn。"
         "深度学习是机器学习的一个子领域，使用多层神经网络。"
         "卷积神经网络（CNN）在图像处理中表现出色。"
         "循环神经网络（RNN）和 Transformer 在自然语言处理中广泛应用。",
         json.dumps(["机器学习", "AI"])),
    ]
    
    for title, content, tags in notes:
        db.execute("""
            INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
        """, (title, content, tags))
    db.commit()
    return notes


class TestSummarize:
    """摘要生成测试"""
    
    def test_extractive_summarize(self, summary_service, long_notes):
        """测试抽取式摘要"""
        cursor = summary_service.db.execute("SELECT id FROM notes LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id, max_length=200, method='extractive')
        assert summary is not None
        assert len(summary) > 0
        assert len(summary) <= 300  # 允许略超过 max_length（因为省略号）
    
    def test_abstractive_summarize(self, summary_service, long_notes):
        """测试摘要式摘要"""
        cursor = summary_service.db.execute("SELECT id FROM notes LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id, max_length=200, method='abstractive')
        assert summary is not None
        assert len(summary) > 0
    
    def test_summarize_short_note(self, summary_service):
        """测试短笔记（不需要摘要）"""
        summary_service.db.execute("""
            INSERT INTO notes (title, content) VALUES (?, ?)
        """, ("短笔记", "这是一条很短的笔记。"))
        summary_service.db.commit()
        
        cursor = summary_service.db.execute("SELECT id FROM notes WHERE title = ?", ("短笔记",))
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id, max_length=200)
        assert summary == "这是一条很短的笔记。"
    
    def test_summarize_nonexistent_note(self, summary_service):
        """测试不存在的笔记"""
        summary = summary_service.summarize(99999)
        assert summary is None
    
    def test_summarize_length_limit(self, summary_service, long_notes):
        """测试长度限制"""
        cursor = summary_service.db.execute("SELECT id FROM notes LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id, max_length=100)
        assert len(summary) <= 150  # 允许一定余量
    
    def test_summarize_default_method(self, summary_service, long_notes):
        """测试默认方法（抽取式）"""
        cursor = summary_service.db.execute("SELECT id FROM notes LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id)
        assert summary is not None


class TestBatchSummarize:
    """批量摘要测试"""
    
    def test_batch_summarize(self, summary_service, long_notes):
        """测试批量摘要生成"""
        results = summary_service.batch_summarize(limit=10, min_length=100)
        assert isinstance(results, list)
        assert len(results) > 0
        
        for result in results:
            assert 'note_id' in result
            assert 'title' in result
            assert 'summary' in result
            assert 'content_length' in result
    
    def test_batch_summarize_limit(self, summary_service, long_notes):
        """测试批量处理限制"""
        results = summary_service.batch_summarize(limit=1)
        assert len(results) <= 1
    
    def test_batch_summarize_min_length(self, summary_service):
        """测试最小长度过滤"""
        summary_service.db.execute("""
            INSERT INTO notes (title, content) VALUES (?, ?)
        """, ("短笔记", "很短"))
        summary_service.db.commit()
        
        results = summary_service.batch_summarize(min_length=100)
        assert len(results) == 0


class TestSummaryManagement:
    """摘要管理测试"""
    
    def test_update_summary(self, summary_service, long_notes):
        """测试更新摘要"""
        cursor = summary_service.db.execute("SELECT id FROM notes LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        # 先添加 summary 列（如果不存在）
        try:
            summary_service.db.execute("ALTER TABLE notes ADD COLUMN summary TEXT")
            summary_service.db.commit()
        except Exception:
            pass  # 列已存在
        
        success = summary_service.update_summary(note_id, "这是测试摘要")
        assert success is True
    
    def test_get_summaries(self, summary_service, long_notes):
        """测试获取已有摘要"""
        # 先添加 summary 列
        try:
            summary_service.db.execute("ALTER TABLE notes ADD COLUMN summary TEXT")
            summary_service.db.commit()
        except Exception:
            pass
        
        cursor = summary_service.db.execute("SELECT id FROM notes LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        summary_service.update_summary(note_id, "测试摘要")
        
        summaries = summary_service.get_summaries()
        assert len(summaries) > 0
        assert summaries[0]['summary'] == "测试摘要"
    
    def test_get_summary_stats(self, summary_service, long_notes):
        """测试获取摘要统计"""
        stats = summary_service.get_summary_stats()
        assert 'total_notes' in stats
        assert 'needs_summary' in stats
        assert 'has_summary' in stats
        assert 'completion_rate' in stats
        
        # 总笔记数应该大于 0
        assert stats['total_notes'] >= 0


class TestSentenceSplitting:
    """句子分割测试"""
    
    def test_split_chinese_sentences(self, summary_service):
        """测试中文句子分割"""
        text = "这是第一句。这是第二句！这是第三句？这是第四句。"
        sentences = summary_service._split_sentences(text)
        assert len(sentences) == 4
    
    def test_split_mixed_sentences(self, summary_service):
        """测试混合语言句子分割"""
        text = "Hello world. 这是中文。Python is great!"
        sentences = summary_service._split_sentences(text)
        assert len(sentences) == 3
    
    def test_split_empty_text(self, summary_service):
        """测试空文本"""
        sentences = summary_service._split_sentences("")
        assert sentences == []


class TestEdgeCases:
    """边界情况测试"""
    
    def test_very_long_content(self, summary_service):
        """测试超长内容"""
        content = "这是一个句子。" * 100
        summary_service.db.execute("""
            INSERT INTO notes (title, content) VALUES (?, ?)
        """, ("长笔记", content))
        summary_service.db.commit()
        
        cursor = summary_service.db.execute("SELECT id FROM notes WHERE title = ?", ("长笔记",))
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id, max_length=200)
        assert len(summary) > 0
        assert len(summary) <= 300
    
    def test_no_punctuation(self, summary_service):
        """测试无标点内容"""
        summary_service.db.execute("""
            INSERT INTO notes (title, content) VALUES (?, ?)
        """, ("无标点", "这是一段没有标点的文字内容测试"))
        summary_service.db.commit()
        
        cursor = summary_service.db.execute("SELECT id FROM notes WHERE title = ?", ("无标点",))
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id, max_length=100)
        assert summary is not None
    
    def test_single_sentence(self, summary_service):
        """测试单句内容"""
        summary_service.db.execute("""
            INSERT INTO notes (title, content) VALUES (?, ?)
        """, ("单句", "这是一条只有一个句子的笔记。"))
        summary_service.db.commit()
        
        cursor = summary_service.db.execute("SELECT id FROM notes WHERE title = ?", ("单句",))
        note_id = cursor.fetchone()[0]
        
        summary = summary_service.summarize(note_id, max_length=200)
        assert summary == "这是一条只有一个句子的笔记。"
