"""
MemoMind MCP Server - PR-022
Model Context Protocol server for MemoMind knowledge base.

Allows AI agents (Claude Desktop, OpenClaw, etc.) to:
- Search, create, read, update, delete notes
- Manage tags and links
- Ask RAG questions
- Browse knowledge graph
- Import/export notes

Usage:
    # stdio mode (for Claude Desktop, OpenClaw)
    python -m mcp_server --db memomind.db

    # http mode (for network access)
    python -m mcp_server --db memomind.db --transport http --port 8001
"""

import os
import sys
import json
import argparse
from typing import List, Optional
from pathlib import Path
from datetime import datetime

# Add workspace root to path for memomind package imports
_workspace_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, _workspace_root)

from memomind.api.client import MemoMind


def _to_json(obj, **kwargs) -> str:
    """序列化对象为 JSON，处理 datetime 等特殊类型。"""
    defaults = {"ensure_ascii": False, "indent": 2, "default": _json_default}
    defaults.update(kwargs)
    return json.dumps(obj, **defaults)


def _json_default(obj):
    """JSON 序列化助手，处理 datetime 等特殊类型。"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def create_mcp_server(db_path: str = "memomind.db"):
    """Create and configure the MemoMind MCP server."""

    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        name="MemoMind",
        instructions="团队知识库与智能笔记系统 - Team Knowledge Base & Smart Notes",
    )

    # Lazy client initialization
    _client = None

    def get_client():
        nonlocal _client
        if _client is None:
            _client = MemoMind(db_path=db_path)
        return _client

    # ==================== Notes ====================

    @mcp.tool()
    def create_note(
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create a new note in the knowledge base."""
        client = get_client()
        note_id = client.notes.create(title=title, content=content, tags=tags or [])
        note = client.notes.get(note_id)
        return _to_json(note)

    @mcp.tool()
    def get_note(note_id: int) -> str:
        """Get a note by ID with full content, tags, and metadata."""
        client = get_client()
        note = client.notes.get(note_id)
        if not note:
            return _to_json({"error": f"Note {note_id} not found"})
        return _to_json(note)

    @mcp.tool()
    def update_note(
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Update an existing note. Only specified fields will be updated."""
        client = get_client()
        note = client.notes.get(note_id)
        if not note:
            return _to_json({"error": f"Note {note_id} not found"})

        client.notes.update(note_id, title=title, content=content, tags=tags)
        note = client.notes.get(note_id)
        return _to_json(note)

    @mcp.tool()
    def delete_note(note_id: int) -> str:
        """Delete a note permanently from the knowledge base."""
        client = get_client()
        note = client.notes.get(note_id)
        if not note:
            return _to_json({"error": f"Note {note_id} not found"})

        client.notes.delete(note_id)
        return _to_json({"status": "deleted", "note_id": note_id})

    @mcp.tool()
    def list_notes(
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """List notes sorted by update time."""
        client = get_client()
        notes = client.notes.list(limit=limit, offset=offset)
        return _to_json(notes)

    # ==================== Search ====================

    @mcp.tool()
    def search_notes(
        query: str,
        limit: int = 10,
    ) -> str:
        """Search notes using full-text search with BM25 ranking."""
        if not query.strip():
            return _to_json({"error": "Query cannot be empty"})

        client = get_client()
        results = client.notes.search(query=query, limit=limit)
        return _to_json(results)

    @mcp.tool()
    def suggest_search(query: str, limit: int = 5) -> str:
        """Get search suggestions (autocomplete) for a partial query."""
        client = get_client()
        suggestions = client.notes.suggest(query, limit=limit)
        return _to_json(suggestions)

    # ==================== Tags ====================

    @mcp.tool()
    def list_tags() -> str:
        """List all tags in the knowledge base, as a tree structure."""
        client = get_client()
        tree = client.tags.get_tree()
        return _to_json({"tree": tree})

    @mcp.tool()
    def create_tag(name: str, parent_id: Optional[int] = None) -> str:
        """Create a new tag, optionally under a parent tag."""
        client = get_client()
        tag_id = client.tags.create(name, parent_id=parent_id)
        return _to_json({"status": "created", "tag_id": tag_id, "name": name})

    @mcp.tool()
    def add_tag_to_note(note_id: int, tag: str) -> str:
        """Add a tag to a note."""
        client = get_client()
        client.tags.add(note_id, tag)
        return _to_json({"status": "added", "note_id": note_id, "tag": tag})

    # ==================== Links ====================

    @mcp.tool()
    def get_links(note_id: int) -> str:
        """Get incoming and outgoing links for a note."""
        client = get_client()
        incoming = client.links.get_incoming(note_id)
        outgoing = client.links.get_outgoing(note_id)
        return _to_json({
            "note_id": note_id,
            "incoming_count": len(incoming),
            "outgoing_count": len(outgoing),
            "incoming": incoming,
            "outgoing": outgoing,
        })

    @mcp.tool()
    def get_orphaned_notes() -> str:
        """Find notes that have no incoming or outgoing links."""
        client = get_client()
        orphans = client.links.get_orphaned()
        return _to_json([{"id": n["id"], "title": n["title"]} for n in orphans])

    # ==================== RAG ====================

    @mcp.tool()
    def ask_question(question: str, top_k: int = 3) -> str:
        """Ask a question and get an answer based on the knowledge base."""
        if not question.strip():
            return _to_json({"error": "Question cannot be empty"})

        client = get_client()
        answer = client.rag.ask(question, top_k=top_k)
        return _to_json(answer)

    @mcp.tool()
    def get_suggested_questions(note_id: int, limit: int = 5) -> str:
        """Get suggested follow-up questions based on a note."""
        client = get_client()
        questions = client.rag.suggested_questions(note_id, limit=limit)
        return _to_json(questions)

    # ==================== Summarization ====================

    @mcp.tool()
    def summarize_note(note_id: int, max_length: int = 200) -> str:
        """Generate a summary of a note."""
        client = get_client()
        summary = client.summarizer.summarize(note_id, max_length=max_length)
        if summary is None:
            return _to_json({"error": f"Note {note_id} not found"})
        return _to_json({"note_id": note_id, "summary": summary})

    # ==================== Workspaces ====================

    @mcp.tool()
    def list_workspaces() -> str:
        """List all workspaces with note counts."""
        client = get_client()
        workspaces = client.workspaces.list()
        return _to_json(workspaces)

    @mcp.tool()
    def create_workspace(name: str, description: str = "") -> str:
        """Create a new workspace."""
        client = get_client()
        ws_id = client.workspaces.create(name, description=description)
        return _to_json({"id": ws_id, "name": name, "description": description})

    # ==================== Export ====================

    @mcp.tool()
    def export_notes(
        format: str = "json",
        note_id: Optional[int] = None,
    ) -> str:
        """Export notes as JSON or Markdown."""
        client = get_client()
        if format == "json":
            if note_id:
                result = client.export.export_note_to_dict(note_id)
            else:
                all_notes = client.notes.list(limit=1000)
                result = {
                    "notes": [
                        client.export.export_note_to_dict(n["id"]) 
                        for n in all_notes
                    ]
                }
            return _to_json(result)
        elif format == "markdown":
            if note_id:
                md = client.export.export_note_to_markdown(note_id)
            else:
                all_notes = client.notes.list(limit=1000)
                md = "\n\n---\n\n".join(
                    client.export.export_note_to_markdown(n["id"]) 
                    for n in all_notes
                )
            return md
        else:
            return _to_json({"error": f"Unsupported format: {format}"})

    # ==================== Import ====================

    @mcp.tool()
    def import_notes_from_json(json_content: str, strategy: str = "overwrite") -> str:
        """Import notes from JSON content."""
        client = get_client()
        result = client.importer.import_json(json_content, strategy=strategy)
        return _to_json(result)

    # ==================== Activity ====================

    @mcp.tool()
    def get_activity(
        limit: int = 20,
        action: Optional[str] = None,
    ) -> str:
        """Get recent activity log entries."""
        client = get_client()
        logs = client.activity.get_timeline(limit=limit, action=action)
        return _to_json(logs)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="MemoMind MCP Server")
    parser.add_argument(
        "--db",
        default="memomind.db",
        help="Path to SQLite database (default: memomind.db)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--port", type=int, default=8001, help="HTTP port (default: 8001)"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)"
    )
    args = parser.parse_args()

    mcp = create_mcp_server(args.db)

    if args.transport == "http":
        print(f"Starting MemoMind MCP Server on http://{args.host}:{args.port}")
        print(f"Database: {args.db}")
        print(f"Docs: http://{args.host}:{args.port}/docs")
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        print(f"Starting MemoMind MCP Server (stdio mode)", file=sys.stderr)
        print(f"Database: {args.db}", file=sys.stderr)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
