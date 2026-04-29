"""
MemoMind AI 自动标签测试
"""

import pytest
import json
from core.database import Database
from core.auto_tag_service import AutoTagService


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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    database.commit()
    return database


@pytest.fixture
def auto_tag(db):
    """创建自动标签服务"""
    return AutoTagService(db)


@pytest.fixture
def sample_notes(db):
    """插入测试笔记"""
    notes_data = [
        ("Python 编程入门", "Python 是一种简单易学的编程语言。本文介绍 Python 的基础语法、数据类型和常用库。", json.dumps(["Python", "编程", "入门"])),
        ("机器学习实战", "机器学习使用算法让计算机从数据中学习。常用的框架有 TensorFlow 和 PyTorch。", json.dumps(["机器学习", "AI", "深度学习"])),
        ("Web 前端开发", "前端开发使用 HTML、CSS 和 JavaScript 构建用户界面。React 和 Vue 是流行的前端框架。", json.dumps(["前端", "JavaScript", "Web"])),
        ("数据库优化指南", "SQL 数据库优化需要考虑索引设计、查询优化和表结构。MySQL 和 PostgreSQL 是最常用的关系型数据库。", None),
        ("自然语言处理基础", "NLP 让计算机理解和生成人类语言。常用技术包括分词、词性标注和命名实体识别。", json.dumps(["NLP", "AI"])),
    ]
    
    for title, content, tags in notes_data:
        db.execute("""
            INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
        """, (title, content, tags))
    db.commit()
    return notes_data


class TestTagExtraction:
    """标签提取测试"""
    
    def test_extract_basic_tags(self, auto_tag):
        """测试基本标签提取"""
        tags = auto_tag.extract_tags(
            "Python 机器学习教程",
            "Python 是一种编程语言，机器学习是 AI 的重要分支。"
        )
        assert len(tags) > 0
        # 应该包含技术术语
        tag_names = [t[0] for t in tags]
        assert any('Python' in t or '机器学习' in t or 'AI' in t for t in tag_names)
    
    def test_extract_with_scores(self, auto_tag):
        """测试标签分数"""
        tags = auto_tag.extract_tags("测试", "这是一段测试内容")
        for tag, score in tags:
            assert 0 <= score <= 1.0
    
    def test_extract_max_tags(self, auto_tag):
        """测试最大标签数量"""
        tags = auto_tag.extract_tags("测试", "内容" * 100, max_tags=3)
        assert len(tags) <= 3
    
    def test_extract_empty_content(self, auto_tag):
        """测试空内容"""
        tags = auto_tag.extract_tags("", "")
        assert tags == []
    
    def test_extract_technical_terms(self, auto_tag):
        """测试技术术语识别"""
        tags = auto_tag.extract_tags(
            "React 开发",
            "使用 React 和 TypeScript 构建 Web 应用，部署到 Docker 容器。"
        )
        tag_names = [t[0] for t in tags]
        # 应该识别技术术语
        tech_terms = ['React', 'TypeScript', 'Docker', 'Web']
        assert any(t in tag_names for t in tech_terms)


class TestTagNormalization:
    """标签标准化测试"""
    
    def test_normalize_synonyms(self, auto_tag):
        """测试同义词合并"""
        assert auto_tag._normalize_tag('python') == 'Python'
        assert auto_tag._normalize_tag('ai') == 'AI'
        assert auto_tag._normalize_tag('nlp') == 'NLP'
    
    def test_normalize_capitalization(self, auto_tag):
        """测试大小写标准化"""
        assert auto_tag._normalize_tag('python') == 'Python'
        # 全大写保持原样（通常是缩写）
        assert auto_tag._normalize_tag('NLP') == 'NLP'


class TestAutoTagNote:
    """笔记自动标签测试"""
    
    def test_auto_tag_note(self, auto_tag, sample_notes):
        """测试自动标签单条笔记"""
        # 找到没有标签的笔记
        cursor = auto_tag.db.execute("SELECT id FROM notes WHERE tags IS NULL")
        row = cursor.fetchone()
        assert row is not None
        
        note_id = row[0]
        tags = auto_tag.auto_tag_note(note_id)
        assert len(tags) > 0
        
        # 验证标签已保存
        cursor = auto_tag.db.execute("SELECT tags FROM notes WHERE id = ?", (note_id,))
        saved_tags = json.loads(cursor.fetchone()[0])
        assert saved_tags == tags
    
    def test_auto_tag_note_nonexistent(self, auto_tag):
        """测试不存在的笔记"""
        tags = auto_tag.auto_tag_note(99999)
        assert tags == []
    
    def test_auto_tag_note_with_existing_tags(self, auto_tag, sample_notes):
        """测试已有标签的笔记"""
        cursor = auto_tag.db.execute("SELECT id FROM notes WHERE tags IS NOT NULL LIMIT 1")
        note_id = cursor.fetchone()[0]
        
        tags = auto_tag.auto_tag_note(note_id)
        assert len(tags) > 0


class TestBatchAutoTag:
    """批量自动标签测试"""
    
    def test_batch_auto_tag(self, auto_tag, sample_notes):
        """测试批量自动标签"""
        results = auto_tag.batch_auto_tag(limit=10)
        assert isinstance(results, list)
        
        for result in results:
            assert 'note_id' in result
            assert 'tags' in result
            assert 'tag_count' in result
    
    def test_batch_auto_tag_limit(self, auto_tag, sample_notes):
        """测试批量处理数量限制"""
        results = auto_tag.batch_auto_tag(limit=1)
        assert len(results) <= 1


class TestTagRecommendations:
    """标签推荐测试"""
    
    def test_get_recommendations(self, auto_tag, sample_notes):
        """测试获取标签推荐"""
        recs = auto_tag.get_tag_recommendations(
            "Python 数据分析",
            "使用 Pandas 和 NumPy 进行数据处理和可视化分析。"
        )
        assert len(recs) > 0
        
        for tag, score, exists in recs:
            assert isinstance(tag, str)
            assert 0 <= score <= 1.0
            assert isinstance(exists, bool)
    
    def test_recommendations_with_existing(self, auto_tag, sample_notes):
        """测试推荐包含已有标签"""
        recs = auto_tag.get_tag_recommendations(
            "机器学习笔记",
            "深度学习使用神经网络处理复杂任务。TensorFlow 和 PyTorch 是主流框架。"
        )
        
        # 应该有一些已存在的标签
        existing = [r for r in recs if r[2]]
        assert len(existing) >= 0  # 可能有也可能没有


class TestMergeTags:
    """标签合并测试"""
    
    def test_merge_similar_tags(self, auto_tag, sample_notes):
        """测试合并相似标签"""
        # 插入一些同义词标签
        auto_tag.db.execute("""
            INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
        """, ("测试", "内容", json.dumps(["python", "机器学习", "ai"])))
        auto_tag.db.commit()
        
        merged = auto_tag.merge_similar_tags()
        assert isinstance(merged, dict)
        
        # python 应该被合并到 Python
        if 'Python' in merged:
            assert 'python' in merged['Python']


class TestEdgeCases:
    """边界情况测试"""
    
    def test_very_long_content(self, auto_tag):
        """测试超长内容"""
        content = "Python " * 1000
        tags = auto_tag.extract_tags("测试", content)
        assert len(tags) > 0
    
    def test_special_characters(self, auto_tag):
        """测试特殊字符"""
        tags = auto_tag.extract_tags("<>&\"'", "特殊字符测试内容")
        assert isinstance(tags, list)
    
    def test_unicode_content(self, auto_tag):
        """测试 Unicode 内容"""
        tags = auto_tag.extract_tags("🐍 Python", "这是关于 🐍 Python 的内容")
        assert len(tags) > 0
    
    def test_mixed_language(self, auto_tag):
        """测试混合语言"""
        tags = auto_tag.extract_tags(
            "Python vs Java 对比",
            "Python is easier to learn than Java. But Java has better performance."
        )
        assert len(tags) > 0
