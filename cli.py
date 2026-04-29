#!/usr/bin/env python3
"""
MemoMind CLI - 命令行接口
支持终端操作笔记、搜索、标签等功能
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.database import Database
from core.search_service import SearchService
from core.semantic_service import SemanticService
from core.auto_tag_service import AutoTagService
from core.rag_service import RAGService
from core.summarization_service import SummarizationService
from core.knowledge_graph_service import KnowledgeGraphService


def get_db(db_path: str = None) -> Database:
    """获取数据库连接"""
    if db_path is None:
        db_path = str(Path.home() / ".memomind" / "memomind.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return Database(db_path)


def cmd_create(args):
    """创建笔记"""
    db = get_db(args.db)
    tags = json.dumps(args.tags, ensure_ascii=False) if args.tags else None
    
    cursor = db.execute(
        "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
        (args.title, args.content, tags)
    )
    db.commit()
    print(f"✅ 笔记已创建，ID: {cursor.lastrowid}")


def cmd_search(args):
    """搜索笔记"""
    db = get_db(args.db)
    search = SearchService(db)
    
    if args.semantic:
        semantic = SemanticService(db)
        results = semantic.semantic_search(args.query, limit=args.limit)
    else:
        results = search.search(args.query, limit=args.limit)
    
    if not results:
        print("没有找到匹配的笔记。")
        return
    
    print(f"找到 {len(results)} 条结果：\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.note.id}] {result.note.title} (score: {result.score:.3f})")
        if result.highlights.get('content'):
            print(f"   {result.highlights['content'][:100]}...")
        print()


def cmd_list(args):
    """列出笔记"""
    db = get_db(args.db)
    cursor = db.execute("SELECT id, title, created_at FROM notes ORDER BY created_at DESC LIMIT ?", (args.limit,))
    
    notes = cursor.fetchall()
    if not notes:
        print("没有笔记。")
        return
    
    print(f"共有 {len(notes)} 条笔记：\n")
    for note in notes:
        print(f"[{note[0]}] {note[1]} ({note[2]})")


def cmd_tags(args):
    """管理标签"""
    db = get_db(args.db)
    auto_tag = AutoTagService(db)
    
    if args.action == "list":
        cursor = db.execute("SELECT DISTINCT tags FROM notes WHERE tags IS NOT NULL")
        all_tags = set()
        for row in cursor.fetchall():
            if row[0]:
                try:
                    all_tags.update(json.loads(row[0]))
                except:
                    pass
        print("标签列表：")
        for tag in sorted(all_tags):
            print(f"  - {tag}")
    
    elif args.action == "auto":
        note_id = int(args.note_id)
        tags = auto_tag.auto_tag_note(note_id)
        print(f"自动标签：{', '.join(tags)}")


def cmd_ask(args):
    """RAG 问答"""
    db = get_db(args.db)
    rag = RAGService(db)
    
    answer = rag.ask(args.question)
    print(f"Q: {args.question}\n")
    print(f"A: {answer.answer}\n")
    
    if answer.sources:
        print("来源：")
        for source in answer.sources:
            print(f"  - {source['title']} (confidence: {source['score']:.2f})")


def cmd_summarize(args):
    """生成摘要"""
    db = get_db(args.db)
    summary_service = SummarizationService(db)
    
    if args.batch:
        results = summary_service.batch_summarize(limit=args.limit)
        for result in results:
            print(f"[{result['note_id']}] {result['title']}")
            print(f"  摘要：{result['summary'][:100]}...\n")
    else:
        note_id = int(args.note_id)
        summary = summary_service.summarize(note_id, max_length=args.max_length)
        print(f"摘要：\n{summary}")


def cmd_graph(args):
    """生成知识图谱"""
    db = get_db(args.db)
    kg = KnowledgeGraphService(db)
    
    graph = kg.build_graph(max_nodes=args.max_nodes)
    stats = kg.get_graph_stats(graph)
    
    print(f"知识图谱统计：")
    print(f"  节点数：{stats['node_count']}")
    print(f"  边数：{stats['edge_count']}")
    print(f"  平均度：{stats['avg_degree']:.2f}")
    print(f"  密度：{stats['density']:.4f}")
    print(f"\n边类型分布：")
    for edge_type, count in stats['edge_types'].items():
        print(f"  {edge_type}: {count}")


def main():
    parser = argparse.ArgumentParser(description="MemoMind CLI - 知识库命令行工具")
    parser.add_argument("--db", help="数据库路径")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # create
    create_parser = subparsers.add_parser("create", help="创建笔记")
    create_parser.add_argument("title", help="笔记标题")
    create_parser.add_argument("content", help="笔记内容")
    create_parser.add_argument("--tags", nargs="*", help="标签列表")
    create_parser.set_defaults(func=cmd_create)
    
    # search
    search_parser = subparsers.add_parser("search", help="搜索笔记")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--limit", type=int, default=10, help="返回数量")
    search_parser.add_argument("--semantic", action="store_true", help="使用语义搜索")
    search_parser.set_defaults(func=cmd_search)
    
    # list
    list_parser = subparsers.add_parser("list", help="列出笔记")
    list_parser.add_argument("--limit", type=int, default=20, help="返回数量")
    list_parser.set_defaults(func=cmd_list)
    
    # tags
    tags_parser = subparsers.add_parser("tags", help="管理标签")
    tags_parser.add_argument("action", choices=["list", "auto"], help="操作")
    tags_parser.add_argument("--note-id", help="笔记 ID（用于 auto）")
    tags_parser.set_defaults(func=cmd_tags)
    
    # ask
    ask_parser = subparsers.add_parser("ask", help="RAG 问答")
    ask_parser.add_argument("question", help="问题")
    ask_parser.set_defaults(func=cmd_ask)
    
    # summarize
    summarize_parser = subparsers.add_parser("summarize", help="生成摘要")
    summarize_parser.add_argument("--note-id", help="笔记 ID")
    summarize_parser.add_argument("--batch", action="store_true", help="批量模式")
    summarize_parser.add_argument("--max-length", type=int, default=200, help="最大长度")
    summarize_parser.add_argument("--limit", type=int, default=10, help="批量数量")
    summarize_parser.set_defaults(func=cmd_summarize)
    
    # graph
    graph_parser = subparsers.add_parser("graph", help="知识图谱")
    graph_parser.add_argument("--max-nodes", type=int, default=100, help="最大节点数")
    graph_parser.set_defaults(func=cmd_graph)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
