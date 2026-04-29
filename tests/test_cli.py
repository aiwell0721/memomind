"""
MemoMind CLI 测试
"""

import pytest
import json
import sys
from io import StringIO
from unittest.mock import patch
from core.database import Database
from cli import cmd_create, cmd_search, cmd_list, cmd_tags, cmd_ask, cmd_summarize, cmd_graph


@pytest.fixture
def db(tmp_path):
    """创建临时数据库"""
    db_path = str(tmp_path / "test.db")
    database = Database(db_path)
    return database, db_path


@pytest.fixture
def sample_notes(db):
    """插入测试笔记"""
    database, _ = db
    notes = [
        ("Python 入门", "Python 是编程语言", json.dumps(["Python"])),
        ("机器学习", "机器学习是 AI 分支", json.dumps(["AI"])),
    ]
    for title, content, tags in notes:
        database.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", (title, content, tags))
    database.commit()
    return notes


class TestCLI:
    """CLI 命令测试"""
    
    def test_create_note(self, db):
        """测试创建笔记"""
        database, db_path = db
        
        class Args:
            def __init__(self):
                self.title = "测试笔记"
                self.content = "这是内容"
                self.tags = ["测试"]
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_create(Args())
            output = mock_stdout.getvalue()
            assert "已创建" in output
        
        # 验证笔记已保存
        cursor = database.execute("SELECT COUNT(*) FROM notes WHERE title = ?", ("测试笔记",))
        assert cursor.fetchone()[0] == 1
    
    def test_search_notes(self, db, sample_notes):
        """测试搜索笔记"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.query = "Python"
                self.limit = 10
                self.semantic = False
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_search(Args())
            output = mock_stdout.getvalue()
            assert "Python" in output
    
    def test_list_notes(self, db, sample_notes):
        """测试列出笔记"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.limit = 10
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_list(Args())
            output = mock_stdout.getvalue()
            assert "Python" in output or "机器" in output
    
    def test_list_empty(self, db):
        """测试空列表"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.limit = 10
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_list(Args())
            output = mock_stdout.getvalue()
            assert "没有笔记" in output
    
    def test_tags_list(self, db, sample_notes):
        """测试列出标签"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.action = "list"
                self.note_id = None
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_tags(Args())
            output = mock_stdout.getvalue()
            assert "Python" in output or "AI" in output
    
    def test_ask_question(self, db, sample_notes):
        """测试问答"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.question = "Python 是什么？"
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_ask(Args())
            output = mock_stdout.getvalue()
            assert "Q:" in output
            assert "A:" in output
    
    def test_summarize_note(self, db, sample_notes):
        """测试摘要生成"""
        _, db_path = db
        
        # 插入长笔记
        database, _ = db
        database.execute("INSERT INTO notes (title, content) VALUES (?, ?)",
                        ("长笔记", "这是一条很长的笔记。" * 50))
        database.commit()
        
        class Args:
            def __init__(self):
                self.note_id = "3"
                self.batch = False
                self.max_length = 200
                self.limit = 10
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_summarize(Args())
            output = mock_stdout.getvalue()
            assert "摘要" in output
    
    def test_graph_stats(self, db, sample_notes):
        """测试知识图谱统计"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.max_nodes = 100
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_graph(Args())
            output = mock_stdout.getvalue()
            assert "节点数" in output
            assert "边数" in output
    
    def test_semantic_search(self, db, sample_notes):
        """测试语义搜索"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.query = "编程"
                self.limit = 10
                self.semantic = True
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_search(Args())
            output = mock_stdout.getvalue()
            assert "结果" in output or "没有找到" in output
    
    def test_batch_summarize(self, db):
        """测试批量摘要"""
        _, db_path = db
        
        # 插入长笔记
        database, _ = db
        database.execute("INSERT INTO notes (title, content) VALUES (?, ?)",
                        ("长笔记", "内容。" * 100))
        database.commit()
        
        class Args:
            def __init__(self):
                self.note_id = None
                self.batch = True
                self.max_length = 200
                self.limit = 5
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_summarize(Args())
            output = mock_stdout.getvalue()
            assert isinstance(output, str)


class TestCLIErrors:
    """CLI 错误处理测试"""
    
    def test_search_empty_query(self, db):
        """测试空查询"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.query = ""
                self.limit = 10
                self.semantic = False
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_search(Args())
            output = mock_stdout.getvalue()
            assert "没有" in output
    
    def test_ask_empty_question(self, db):
        """测试空问题"""
        _, db_path = db
        
        class Args:
            def __init__(self):
                self.question = ""
                self.db = db_path
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_ask(Args())
            output = mock_stdout.getvalue()
            assert "Q:" in output
