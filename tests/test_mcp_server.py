"""
MemoMind MCP Server 测试 - PR-022
测试 MCP 服务器的所有工具和协议兼容性
"""

import pytest
import os
import asyncio
import tempfile
import shutil
import json
from pathlib import Path

# Add workspace root to path for memomind package imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memomind.api.client import MemoMind
from mcp_server import create_mcp_server


def _call_tool(mcp, tool_name: str, arguments: dict) -> dict:
    """同步调用 MCP 工具并解析返回结果为 dict。"""
    text = _call_tool_raw(mcp, tool_name, arguments)
    return json.loads(text)


def _call_tool_raw(mcp, tool_name: str, arguments: dict) -> str:
    """同步调用 MCP 工具并返回原始文本。"""
    async def _call():
        result = await mcp.call_tool(tool_name, arguments)
        if isinstance(result, tuple):
            content, _ = result
        else:
            content = result
        
        if isinstance(content, list) and len(content) > 0:
            first = content[0]
            if hasattr(first, 'text'):
                return first.text
            return str(first)
        return str(content)
    
    return asyncio.run(_call())


@pytest.fixture
def temp_db_path():
    """创建临时数据库路径用于测试。"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    yield db_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mcp_with_data(temp_db_path):
    """创建带有测试数据的 MCP 服务器。"""
    client = MemoMind(db_path=temp_db_path)
    
    # Create test workspace
    client.workspaces.create("Test Workspace", "For testing")
    
    # Create test notes
    n1 = client.notes.create(
        title="Python 基础教程",
        content="Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年发布。"
                "它支持多种编程范式，包括面向对象、命令式和函数式编程。",
        tags=["编程", "Python"],
    )
    n2 = client.notes.create(
        title="SQLite 使用指南",
        content="SQLite 是一个轻量级的关系型数据库，支持完整的 SQL 语法。"
                "它广泛用于移动应用和嵌入式系统。Python 内置了 sqlite3 模块。",
        tags=["数据库", "SQLite"],
    )
    n3 = client.notes.create(
        title="机器学习入门",
        content="机器学习是人工智能的一个分支，它使用算法让计算机从数据中学习。"
                "常见的机器学习算法包括线性回归、决策树和神经网络。"
                "Python 的 scikit-learn 和 TensorFlow 是流行的机器学习框架。",
        tags=["机器学习", "人工智能", "Python"],
    )
    
    # Create links between notes
    client.links.create(n1, n2)
    client.links.create(n2, n3)
    
    # Create tag hierarchy
    client.tags.create("编程/Python")
    client.tags.create("编程/Java")
    client.tags.create("数据库/SQLite")
    
    client.close()
    
    # Create MCP server with the same DB
    mcp = create_mcp_server(temp_db_path)
    return mcp


class TestMCPServerCreation:
    """测试 MCP 服务器创建。"""

    def test_create_server(self, temp_db_path):
        mcp = create_mcp_server(temp_db_path)
        assert mcp.name == "MemoMind"

    def test_tool_count(self, temp_db_path):
        mcp = create_mcp_server(temp_db_path)
        tools = mcp._tool_manager.list_tools()
        assert len(tools) == 20

    def test_core_tools_exist(self, temp_db_path):
        mcp = create_mcp_server(temp_db_path)
        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        expected = {
            "create_note", "get_note", "update_note", "delete_note",
            "list_notes", "search_notes", "list_tags", "get_links",
            "ask_question", "export_notes",
        }
        assert expected.issubset(tool_names)


class TestNoteTools:
    """测试笔记相关工具。"""

    def test_create_note(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "create_note", {
            "title": "测试笔记", "content": "这是一条测试内容", "tags": ["测试"]
        })
        assert "id" in data
        assert data["title"] == "测试笔记"

    def test_get_note(self, mcp_with_data):
        # First create a note
        note = _call_tool(mcp_with_data, "create_note", {
            "title": "获取测试", "content": "测试内容"
        })

        # Then get it
        data = _call_tool(mcp_with_data, "get_note", {"note_id": note["id"]})
        assert data["title"] == "获取测试"
        assert data["content"] == "测试内容"

    def test_get_note_not_found(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "get_note", {"note_id": 99999})
        assert "error" in data

    def test_update_note(self, mcp_with_data):
        # Create
        note = _call_tool(mcp_with_data, "create_note", {
            "title": "原始标题", "content": "原始内容"
        })

        # Update
        data = _call_tool(mcp_with_data, "update_note", {
            "note_id": note["id"], "title": "新标题", "content": "新内容"
        })
        assert data["title"] == "新标题"
        assert data["content"] == "新内容"

    def test_delete_note(self, mcp_with_data):
        # Create
        note = _call_tool(mcp_with_data, "create_note", {
            "title": "待删除", "content": "将被删除"
        })

        # Delete
        data = _call_tool(mcp_with_data, "delete_note", {"note_id": note["id"]})
        assert data["status"] == "deleted"

    def test_list_notes(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "list_notes", {"limit": 5})
        assert isinstance(data, list)
        assert len(data) >= 3  # We created 3 notes


class TestSearchTools:
    """测试搜索工具。"""

    def test_search_notes(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "search_notes", {
            "query": "Python 编程", "limit": 5
        })
        assert isinstance(data, list)
        assert len(data) > 0
        assert "score" in data[0]
        assert "highlights" in data[0]

    def test_search_empty_query(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "search_notes", {"query": ""})
        assert "error" in data

    def test_suggest_search(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "suggest_search", {"query": "Py"})
        assert isinstance(data, list)


class TestTagTools:
    """测试标签工具。"""

    def test_list_tags(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "list_tags", {})
        assert "tree" in data

    def test_create_tag(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "create_tag", {
            "name": "测试标签", "parent": "编程"
        })
        assert data["status"] == "created"


class TestLinkTools:
    """测试链接工具。"""

    def test_get_links(self, mcp_with_data):
        # Get first note
        notes = _call_tool(mcp_with_data, "list_notes", {"limit": 1})
        note_id = notes[0]["id"]

        data = _call_tool(mcp_with_data, "get_links", {"note_id": note_id})
        assert "incoming_count" in data
        assert "outgoing_count" in data

    def test_get_orphaned_notes(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "get_orphaned_notes", {})
        assert isinstance(data, list)


class TestRAGTools:
    """测试 RAG 问答工具。"""

    def test_ask_question(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "ask_question", {
            "question": "Python 是什么？", "top_k": 3
        })
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data

    def test_ask_empty_question(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "ask_question", {"question": ""})
        assert "error" in data


class TestSummarizationTool:
    """测试摘要工具。"""

    def test_summarize_note(self, mcp_with_data):
        notes = _call_tool(mcp_with_data, "list_notes", {"limit": 1})
        note_id = notes[0]["id"]

        data = _call_tool(mcp_with_data, "summarize_note", {
            "note_id": note_id, "max_length": 100
        })
        assert "summary" in data


class TestWorkspaceTools:
    """测试工作区工具。"""

    def test_list_workspaces(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "list_workspaces", {})
        assert isinstance(data, list)
        assert len(data) >= 1  # Default workspace

    def test_create_workspace(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "create_workspace", {
            "name": "新项目", "description": "测试工作区"
        })
        assert "id" in data
        assert "name" in data


class TestExportTool:
    """测试导出工具。"""

    def test_export_json(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "export_notes", {"format": "json"})
        assert isinstance(data, dict)
        assert "notes" in data

    def test_export_markdown(self, mcp_with_data):
        result = _call_tool_raw(mcp_with_data, "export_notes", {"format": "markdown"})
        # Markdown is returned as raw text, not JSON
        assert isinstance(result, str)
        assert len(result) > 0
        assert "title:" in result  # Should contain YAML frontmatter

    def test_export_unsupported_format(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "export_notes", {"format": "xml"})
        assert "error" in data


class TestActivityTool:
    """测试活动日志工具。"""

    def test_get_activity(self, mcp_with_data):
        data = _call_tool(mcp_with_data, "get_activity", {"limit": 10})
        assert isinstance(data, list)
