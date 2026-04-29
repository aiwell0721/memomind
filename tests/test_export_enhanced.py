"""
MemoMind 导出服务增强测试 - PR-021
测试 Obsidian、Notion、PDF 导出功能
"""

import pytest
import os
import tempfile
import shutil
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memomind.core.database import Database
from memomind.core.export_service import ExportService


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    db = Database(db_path)
    
    # 初始化所有表
    from memomind.core.link_service import LinkService
    LinkService(db)  # This creates the note_links table
    
    # 创建测试笔记
    db.execute("""
        INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
    """, ("Python 入门", "Python 是一种编程语言", json.dumps(["编程", "Python"])))
    db.execute("""
        INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
    """, ("SQLite 指南", "SQLite 是轻量级数据库，支持 [[Python 入门]]", json.dumps(["数据库"])))
    db.execute("""
        INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)
    """, ("机器学习", "机器学习是 AI 的分支", json.dumps(["AI", "Python"])))
    
    # 创建链接
    db.execute("INSERT INTO note_links (source_note_id, target_note_id) VALUES (2, 1)")
    db.commit()
    
    yield db_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def export_service(temp_db):
    """创建导出服务实例"""
    db = Database(temp_db)
    return ExportService(db)


@pytest.fixture
def output_dir():
    """创建临时输出目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestObsidianExport:
    """测试 Obsidian 兼容导出"""

    def test_export_single_note_obsidian(self, export_service):
        """测试单条笔记导出为 Obsidian 格式"""
        md = export_service.export_note_to_markdown(1)
        assert "---" in md
        assert "title: Python 入门" in md
        assert "tags:" in md
        assert "Python" in md

    def test_export_to_obsidian(self, export_service, output_dir):
        """测试批量导出为 Obsidian 格式"""
        files = export_service.export_to_obsidian(output_dir)
        assert len(files) == 3
        
        # 检查文件名
        for f in files:
            assert f.endswith('.md')
            assert os.path.exists(f)

    def test_obsidian_frontmatter(self, export_service, output_dir):
        """测试 Obsidian frontmatter 格式"""
        export_service.export_to_obsidian(output_dir)
        
        # 读取第一个文件
        files = list(Path(output_dir).glob("*.md"))
        assert len(files) > 0
        
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查 frontmatter
        assert content.startswith("---")
        assert "tags:" in content
        assert "created:" in content
        assert "modified:" in content

    def test_obsidian_backlinks(self, export_service, output_dir):
        """测试反向链接"""
        export_service.export_to_obsidian(output_dir)
        
        files = list(Path(output_dir).glob("*.md"))
        for f in files:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
            # 应该包含反向链接部分
            assert "反向链接" in content or "无" in content


class TestNotionExport:
    """测试 Notion 兼容导出"""

    def test_export_to_notion_csv(self, export_service, output_dir):
        """测试导出为 Notion CSV"""
        csv_path = os.path.join(output_dir, 'notion_export.csv')
        result = export_service.export_to_notion_csv(csv_path)
        
        assert os.path.exists(result)
        
        with open(result, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # 检查 CSV 头部
        assert 'Name' in content
        assert 'Content' in content
        assert 'Tags' in content
        assert 'Python 入门' in content

    def test_export_to_notion_markdown(self, export_service, output_dir):
        """测试导出为 Notion Markdown"""
        files = export_service.export_to_notion_markdown(output_dir)
        
        assert len(files) == 3
        
        # 检查 Notion 格式（无 frontmatter）
        for f in files:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Notion 不用 YAML frontmatter
            assert not content.startswith("---")
            # 使用 # 标题
            assert content.startswith("#")
            # 标签用内联格式
            assert "`#" in content


class TestPDFExport:
    """测试 PDF 导出"""

    def test_export_note_to_pdf_html(self, export_service):
        """测试导出笔记为 PDF 兼容 HTML"""
        html = export_service.export_note_to_pdf_html(1)
        
        assert "<!DOCTYPE html>" in html
        assert "<h1>Python 入门</h1>" in html
        assert '<span class="tag">编程</span>' in html
        assert "Python 是一种编程语言" in html

    def test_export_all_to_pdf_html(self, export_service, output_dir):
        """测试批量导出为 PDF 兼容 HTML"""
        files = export_service.export_all_to_pdf_html(output_dir)
        
        assert len(files) == 3
        
        for f in files:
            assert f.endswith('.html')
            assert os.path.exists(f)
            
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
            
            assert "<!DOCTYPE html>" in content
            assert "tag" in content


class TestExistingExports:
    """测试现有导出功能回归"""

    def test_export_note_to_markdown(self, export_service):
        """测试 Markdown 导出"""
        md = export_service.export_note_to_markdown(1)
        assert "---" in md
        assert "Python 入门" in md
        assert "tags:" in md

    def test_export_note_to_dict(self, export_service):
        """测试字典导出"""
        note = export_service.export_note_to_dict(1)
        assert note['title'] == "Python 入门"
        assert note['tags'] == ["编程", "Python"]
        assert 'content' in note

    def test_export_all_to_json(self, export_service, output_dir):
        """测试 JSON 批量导出"""
        json_path = os.path.join(output_dir, 'export.json')
        result = export_service.export_all_to_json(json_path)
        
        assert os.path.exists(result)
        
        with open(result, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['total_notes'] == 3
        assert len(data['notes']) == 3

    def test_export_all_to_markdown_files(self, export_service, output_dir):
        """测试 Markdown 文件批量导出"""
        files = export_service.export_all_to_markdown_files(output_dir)
        
        assert len(files) == 3
        for f in files:
            assert os.path.exists(f)
            assert f.endswith('.md')
