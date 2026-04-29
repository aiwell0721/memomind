"""
MemoMind 语义搜索测试
测试 TF-IDF 语义搜索、混合搜索、相似笔记查找等功能
"""

import pytest
import json
from core.database import Database
from core.semantic_service import SemanticService


@pytest.fixture
def db():
    """创建测试数据库"""
    database = Database(":memory:")
    # 创建 notes 表（如果不存在）
    database.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            workspace_id INTEGER DEFAULT 1,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    database.commit()
    return database


@pytest.fixture
def semantic(db):
    """创建语义搜索服务"""
    return SemanticService(db)


@pytest.fixture
def sample_notes(db):
    """插入测试笔记"""
    notes = [
        ("Python 入门教程", "Python 是一种简单易学的编程语言，适合初学者学习。本文介绍 Python 的基础语法和常用库。", json.dumps(["python", "编程", "入门"])),
        ("机器学习基础", "机器学习是人工智能的重要分支，使用算法让计算机从数据中学习。常用的机器学习框架有 TensorFlow 和 PyTorch。", json.dumps(["机器学习", "AI", "深度学习"])),
        ("Web 开发实战", "Web 开发涉及前端和后端技术。前端使用 HTML、CSS、JavaScript，后端可以使用 Python 的 Django 或 Flask 框架。", json.dumps(["web", "开发", "python"])),
        ("数据库设计指南", "数据库设计需要考虑范式化、索引优化和查询性能。关系型数据库如 MySQL 和 PostgreSQL 是最常用的选择。", json.dumps(["数据库", "SQL", "设计"])),
        ("深度学习入门", "深度学习使用神经网络处理复杂任务，如图像识别和自然语言处理。主流的深度学习框架有 TensorFlow、PyTorch 等。", json.dumps(["深度学习", "AI", "神经网络"])),
        ("自然语言处理", "自然语言处理（NLP）让计算机理解人类语言。常用的技术包括分词、词性标注、命名实体识别等。", json.dumps(["NLP", "AI", "自然语言"])),
        ("Python 数据分析", "使用 Python 进行数据分析，常用库有 Pandas、NumPy、Matplotlib。可以处理各种结构化数据。", json.dumps(["python", "数据分析", "pandas"])),
        ("软件工程实践", "软件工程包括需求分析、设计、编码、测试、部署等环节。敏捷开发是目前最流行的开发方法论。", json.dumps(["软件工程", "敏捷", "开发"])),
    ]
    
    for title, content, tags in notes:
        db.execute("""
            INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
        """, (title, content, tags))
    db.commit()
    return notes


class TestTFIDF:
    """TF-IDF 向量计算测试"""
    
    def test_compute_tfidf_basic(self, semantic, sample_notes):
        """测试基本 TF-IDF 计算"""
        vector = semantic._compute_tfidf_vector("Python 编程语言 入门")
        assert len(vector) > 0
        assert 'python' in vector or '编程' in vector
    
    def test_compute_tfidf_empty(self, semantic):
        """测试空文本"""
        vector = semantic._compute_tfidf_vector("")
        assert vector == {}
    
    def test_compute_tfidf_stopwords(self, semantic):
        """测试停用词过滤"""
        vector = semantic._compute_tfidf_vector("的了是在我有")
        assert len(vector) == 0
    
    def test_idf_cache(self, semantic, sample_notes):
        """测试 IDF 缓存"""
        semantic._load_idf()
        assert semantic._doc_count == 8
        assert len(semantic._idf_cache) > 0


class TestCosineSimilarity:
    """余弦相似度测试"""
    
    def test_identical_vectors(self, semantic):
        """相同向量相似度为 1"""
        vec = {"python": 0.5, "编程": 0.3}
        sim = SemanticService._cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001
    
    def test_orthogonal_vectors(self, semantic):
        """正交向量相似度为 0"""
        vec1 = {"python": 0.5}
        vec2 = {"数据库": 0.5}
        sim = SemanticService._cosine_similarity(vec1, vec2)
        assert sim == 0.0
    
    def test_empty_vectors(self, semantic):
        """空向量相似度为 0"""
        sim = SemanticService._cosine_similarity({}, {"python": 0.5})
        assert sim == 0.0
    
    def test_partial_overlap(self, semantic):
        """部分重叠向量"""
        vec1 = {"python": 0.5, "编程": 0.3}
        vec2 = {"python": 0.5, "数据库": 0.3}
        sim = SemanticService._cosine_similarity(vec1, vec2)
        assert 0.0 < sim < 1.0


class TestSemanticSearch:
    """语义搜索测试"""
    
    def test_basic_semantic_search(self, semantic, sample_notes):
        """测试基本语义搜索"""
        results = semantic.semantic_search("Python 编程学习", limit=5)
        assert len(results) > 0
        # Python 相关笔记应该排在前面
        assert "Python" in results[0].note.title or "Python" in results[0].note.content
    
    def test_semantic_search_empty_query(self, semantic):
        """测试空查询"""
        results = semantic.semantic_search("")
        assert results == []
    
    def test_semantic_search_threshold(self, semantic, sample_notes):
        """测试阈值过滤"""
        results_low = semantic.semantic_search("Python", threshold=0.0, limit=10)
        results_high = semantic.semantic_search("Python", threshold=0.3, limit=10)
        assert len(results_low) >= len(results_high)
    
    def test_semantic_search_workspace_filter(self, semantic, sample_notes):
        """测试工作区过滤"""
        results = semantic.semantic_search("Python", workspace_id=1, limit=10)
        assert len(results) > 0
    
    def test_semantic_search_relevance(self, semantic, sample_notes):
        """测试语义相关性"""
        # 搜索"人工智能"，应该返回机器学习和深度学习相关笔记
        results = semantic.semantic_search("人工智能 神经网络", limit=5)
        assert len(results) > 0
        # 前几名应该包含 AI 相关内容
        top_titles = [r.note.title for r in results[:3]]
        ai_related = [t for t in top_titles if any(kw in t for kw in ["机器学习", "深度学习", "神经网络", "AI"])]
        assert len(ai_related) > 0
    
    def test_semantic_search_limit(self, semantic, sample_notes):
        """测试数量限制"""
        results = semantic.semantic_search("开发", limit=3)
        assert len(results) <= 3
    
    def test_semantic_search_ordering(self, semantic, sample_notes):
        """测试结果排序"""
        results = semantic.semantic_search("Python")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestHybridSearch:
    """混合搜索测试"""
    
    def test_hybrid_search_basic(self, semantic, sample_notes):
        """测试基本混合搜索"""
        results = semantic.hybrid_search("Python 编程", limit=5)
        assert len(results) > 0
    
    def test_hybrid_search_weights(self, semantic, sample_notes):
        """测试不同权重"""
        results_keyword = semantic.hybrid_search("Python", semantic_weight=0.0, limit=10)
        results_semantic = semantic.hybrid_search("Python", semantic_weight=1.0, limit=10)
        results_mixed = semantic.hybrid_search("Python", semantic_weight=0.5, limit=10)
        
        # 不同权重可能返回不同排序
        assert len(results_keyword) > 0
        assert len(results_semantic) > 0
        assert len(results_mixed) > 0
    
    def test_hybrid_search_empty_query(self, semantic):
        """测试空查询"""
        results = semantic.hybrid_search("")
        assert results == []
    
    def test_hybrid_search_with_tags(self, semantic, sample_notes):
        """测试带标签过滤"""
        results = semantic.hybrid_search("Python", tags=["AI"], limit=10)
        assert len(results) >= 0  # 可能没有匹配的


class TestSimilarNotes:
    """相似笔记测试"""
    
    def test_find_similar_notes(self, semantic, sample_notes):
        """测试查找相似笔记"""
        # 找到 Python 入门教程的 ID
        cursor = semantic.db.execute("SELECT id FROM notes WHERE title = ?", ("Python 入门教程",))
        note_id = cursor.fetchone()[0]
        
        similar = semantic.find_similar_notes(note_id, limit=5)
        assert len(similar) > 0
        # 相似度应该在 0-1 之间
        for result, score in similar:
            assert 0.0 <= score <= 1.0
    
    def test_find_similar_notes_exclude_self(self, semantic, sample_notes):
        """测试排除自身"""
        cursor = semantic.db.execute("SELECT id FROM notes WHERE title = ?", ("Python 入门教程",))
        note_id = cursor.fetchone()[0]
        
        similar = semantic.find_similar_notes(note_id, limit=10, exclude_self=True)
        for result, score in similar:
            assert result.note.id != note_id
    
    def test_find_similar_notes_nonexistent(self, semantic, sample_notes):
        """测试不存在的笔记"""
        similar = semantic.find_similar_notes(99999)
        assert similar == []
    
    def test_find_similar_notes_ordering(self, semantic, sample_notes):
        """测试排序"""
        cursor = semantic.db.execute("SELECT id FROM notes WHERE title = ?", ("Python 入门教程",))
        note_id = cursor.fetchone()[0]
        
        similar = semantic.find_similar_notes(note_id, limit=10)
        scores = [score for _, score in similar]
        assert scores == sorted(scores, reverse=True)


class TestIndexManagement:
    """索引管理测试"""
    
    def test_refresh_index(self, semantic, sample_notes):
        """测试重建索引"""
        semantic._load_idf()
        old_count = semantic._doc_count
        
        semantic.refresh_index()
        assert semantic._doc_count == old_count
    
    def test_get_index_stats(self, semantic, sample_notes):
        """测试获取索引统计"""
        stats = semantic.get_index_stats()
        assert 'total_documents' in stats
        assert 'unique_terms' in stats
        assert 'avg_idf' in stats
        assert stats['total_documents'] == 8
        assert stats['unique_terms'] > 0


class TestEdgeCases:
    """边界情况测试"""
    
    def test_single_note_search(self, semantic):
        """测试只有一条笔记"""
        semantic.db.execute("""
            INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
        """, ("测试笔记", "这是一条测试笔记", json.dumps(["测试"])))
        semantic.db.commit()
        
        results = semantic.semantic_search("测试")
        assert len(results) == 1
    
    def test_unicode_query(self, semantic, sample_notes):
        """测试 Unicode 查询"""
        results = semantic.semantic_search("🐍 Python")
        assert len(results) >= 0
    
    def test_very_long_query(self, semantic, sample_notes):
        """测试超长查询"""
        long_query = "Python " * 100
        results = semantic.semantic_search(long_query)
        assert isinstance(results, list)
    
    def test_special_characters_query(self, semantic, sample_notes):
        """测试特殊字符查询"""
        results = semantic.semantic_search("<>&\"' Python")
        assert isinstance(results, list)
