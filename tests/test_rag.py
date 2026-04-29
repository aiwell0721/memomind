"""
MemoMind RAG 问答测试
"""

import pytest
import json
from core.database import Database
from core.rag_service import RAGService, RAGAnswer


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
            workspace_id INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    database.commit()
    return database


@pytest.fixture
def rag(db):
    """创建 RAG 服务"""
    return RAGService(db)


@pytest.fixture
def knowledge_base(db):
    """创建知识库"""
    notes = [
        ("Python 入门教程", "Python 是一种简单易学的编程语言。Python 支持面向对象、函数式和过程式编程。Python 的标准库非常丰富，可以轻松实现文件操作、网络编程和数据处理。", json.dumps(["Python", "编程"])),
        ("机器学习基础", "机器学习是人工智能的重要分支。监督学习使用标注数据训练模型，无监督学习从无标注数据中发现模式。常用的机器学习算法包括线性回归、决策树和神经网络。", json.dumps(["机器学习", "AI"])),
        ("数据库设计", "数据库设计需要考虑第一范式、第二范式和第三范式。关系型数据库使用 SQL 语言进行查询。索引可以加速查询但会增加写入开销。", json.dumps(["数据库", "SQL"])),
        ("Web 开发", "Web 开发分为前端和后端。前端使用 HTML、CSS 和 JavaScript 构建用户界面。后端处理业务逻辑和数据存储，常用框架有 Django 和 Flask。", json.dumps(["Web", "开发"])),
    ]
    
    for title, content, tags in notes:
        db.execute("""
            INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
        """, (title, content, tags))
    db.commit()
    return notes


class TestRAGAnswer:
    """RAG 回答模型测试"""
    
    def test_answer_creation(self):
        """测试回答创建"""
        answer = RAGAnswer("测试回答", [{"note_id": 1}], 0.8)
        assert answer.answer == "测试回答"
        assert len(answer.sources) == 1
        assert answer.confidence == 0.8
    
    def test_answer_to_dict(self):
        """测试转换为字典"""
        answer = RAGAnswer("回答", [{"note_id": 1, "title": "测试"}], 0.5)
        d = answer.to_dict()
        assert 'answer' in d
        assert 'sources' in d
        assert 'confidence' in d


class TestAsk:
    """问答测试"""
    
    def test_basic_ask(self, rag, knowledge_base):
        """测试基本问答"""
        answer = rag.ask("Python 是什么？")
        assert isinstance(answer, RAGAnswer)
        assert len(answer.answer) > 0
        assert len(answer.sources) > 0
        assert 0 <= answer.confidence <= 1.0
    
    def test_ask_empty_question(self, rag):
        """测试空问题"""
        answer = rag.ask("")
        assert answer.answer == ""
        assert answer.sources == []
        assert answer.confidence == 0.0
    
    def test_ask_no_results(self, rag, knowledge_base):
        """测试无匹配结果"""
        answer = rag.ask("量子计算 超新星 黑洞")
        # 可能没有结果或置信度很低
        assert isinstance(answer, RAGAnswer)
    
    def test_ask_with_sources(self, rag, knowledge_base):
        """测试回答包含来源"""
        answer = rag.ask("机器学习", max_sources=3)
        assert len(answer.sources) <= 3
        
        for source in answer.sources:
            assert 'note_id' in source
            assert 'title' in source
            assert 'snippet' in source
    
    def test_ask_relevance(self, rag, knowledge_base):
        """测试回答相关性"""
        answer = rag.ask("数据库 索引")
        # 应该返回数据库相关内容
        assert any("数据库" in s['title'] or "索引" in s['title'] for s in answer.sources)
    
    def test_ask_confidence_range(self, rag, knowledge_base):
        """测试置信度范围"""
        questions = ["Python", "机器学习", "数据库", "Web"]
        for q in questions:
            answer = rag.ask(q)
            assert 0 <= answer.confidence <= 1.0


class TestExtractiveAnswer:
    """抽取式回答测试"""
    
    def test_extractive_basic(self, rag, knowledge_base):
        """测试基本抽取式回答"""
        answer, confidence = rag._extractive_answer("Python 支持哪些编程范式", [])
        # 没有结果时返回空
        assert answer == "" or confidence == 0.0
    
    def test_extractive_with_results(self, rag, knowledge_base):
        """测试有结果时的抽取式回答"""
        from core.models import SearchResult, Note
        note = Note(id=1, title="Python 入门", content="Python 是一种简单易学的编程语言，支持多种编程范式。")
        result = SearchResult(note=note, score=0.8, highlights={})
        
        answer, confidence = rag._extractive_answer("Python 是什么", [result])
        assert len(answer) > 0
        assert confidence > 0


class TestAbstractiveAnswer:
    """摘要式回答测试"""
    
    def test_abstractive_basic(self, rag, knowledge_base):
        """测试基本摘要式回答"""
        answer, confidence = rag._abstractive_answer("测试", [])
        assert answer == "" or confidence == 0.0
    
    def test_abstractive_with_results(self, rag, knowledge_base):
        """测试有结果时的摘要式回答"""
        from core.models import SearchResult, Note
        note = Note(id=1, title="Python", content="Python 是一种编程语言。Python 简单易学。")
        result = SearchResult(note=note, score=0.7, highlights={})
        
        answer, confidence = rag._abstractive_answer("Python", [result])
        assert len(answer) > 0
        assert confidence > 0


class TestAskWithTags:
    """带标签过滤的问答测试"""
    
    def test_ask_with_matching_tags(self, rag, knowledge_base):
        """测试标签匹配"""
        answer = rag.ask_with_tags("Python 编程", tags=["Python"])
        assert isinstance(answer, RAGAnswer)
    
    def test_ask_with_no_matching_tags(self, rag, knowledge_base):
        """测试无匹配标签"""
        answer = rag.ask_with_tags("测试", tags=["不存在的标签"])
        assert "没有找到" in answer.answer or len(answer.sources) == 0
    
    def test_ask_without_tags(self, rag, knowledge_base):
        """测试不传标签"""
        answer1 = rag.ask("Python")
        answer2 = rag.ask_with_tags("Python", tags=None)
        # 应该返回相同结果
        assert len(answer1.sources) == len(answer2.sources)


class TestSuggestedQuestions:
    """建议问题测试"""
    
    def test_get_suggested_questions(self, rag, knowledge_base):
        """测试获取建议问题"""
        # 找到 Python 笔记的 ID
        cursor = rag.db.execute("SELECT id FROM notes WHERE title = ?", ("Python 入门教程",))
        note_id = cursor.fetchone()[0]
        
        questions = rag.get_suggested_questions(note_id, limit=5)
        assert len(questions) > 0
        assert len(questions) <= 5
        
        # 问题应该包含问号
        for q in questions:
            assert '？' in q or '?' in q
    
    def test_get_suggested_questions_nonexistent(self, rag):
        """测试不存在的笔记"""
        questions = rag.get_suggested_questions(99999)
        assert questions == []
    
    def test_suggested_questions_format(self, rag, knowledge_base):
        """测试问题格式"""
        cursor = rag.db.execute("SELECT id FROM notes LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        questions = rag.get_suggested_questions(note_id, limit=3)
        for q in questions:
            assert isinstance(q, str)
            assert len(q) > 5


class TestEdgeCases:
    """边界情况测试"""
    
    def test_very_long_question(self, rag, knowledge_base):
        """测试超长问题"""
        question = "什么是 " + "Python " * 100
        answer = rag.ask(question)
        assert isinstance(answer, RAGAnswer)
    
    def test_special_characters(self, rag, knowledge_base):
        """测试特殊字符"""
        answer = rag.ask("<>&\"' Python")
        assert isinstance(answer, RAGAnswer)
    
    def test_max_sources_limit(self, rag, knowledge_base):
        """测试来源数量限制"""
        answer = rag.ask("Python", max_sources=1)
        assert len(answer.sources) <= 1
    
    def test_workspace_filter(self, rag, knowledge_base):
        """测试工作区过滤"""
        answer = rag.ask("Python", workspace_id=1)
        assert isinstance(answer, RAGAnswer)
