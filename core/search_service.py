"""
MemoMind 搜索服务 - 基于 SQLite FTS5 的全文搜索
支持中文分词（jieba）
"""

import re
import json
from typing import List, Optional
from .database import Database
from .models import Note, SearchResult
from .tokenizer import get_tokenizer


class SearchService:
    """搜索服务"""
    
    def __init__(self, db: Database):
        """
        初始化搜索服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
    
    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[SearchResult]:
        """
        全文搜索
        
        Args:
            query: 搜索关键词
            tags: 标签过滤列表
            limit: 返回数量限制
            offset: 分页偏移量
            
        Returns:
            搜索结果列表（按 BM25 相关度排序）
        """
        # 清理查询
        query = query.strip()
        if not query:
            return []
        
        # 构建 FTS5 查询
        fts_query = self._build_fts_query(query)
        
        # 构建标签过滤条件
        tag_filter = ""
        params = []
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("n.tags LIKE ?")
                params.append('%"' + tag + '"%')
            tag_filter = "AND (" + " OR ".join(tag_conditions) + ")"
        
        # FTS5 搜索（带 BM25 排序）
        sql = f"""
            SELECT 
                n.id,
                n.title,
                n.content,
                n.tags,
                n.created_at,
                n.updated_at,
                bm25(notes_fts) as score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
            {tag_filter}
            ORDER BY score DESC
            LIMIT ? OFFSET ?
        """
        
        params = [fts_query] + params + [limit, offset]
        cursor = self.db.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            note = Note.from_row(row)
            # 生成高亮
            highlights = self._highlight(note, query)
            results.append(SearchResult(
                note=note,
                score=-row[6],  # bm25 返回负值，取反使高分在前
                highlights=highlights
            ))
        
        return results
    
    def _build_fts_query(self, query: str) -> str:
        """
        构建 FTS5 查询语句
        
        FTS5 支持：
        - 精确短语："exact phrase"
        - AND 逻辑：term1 term2（默认）
        - OR 逻辑：term1 OR term2
        - 前缀匹配：term*
        
        支持中文分词（jieba）
        """
        # 转义特殊字符
        special_chars = ['"', '*', '(', ')', '+', '-', '~']
        for char in special_chars:
            query = query.replace(char, '\\' + char)
        
        # 使用 jieba 分词
        tokenizer = get_tokenizer()
        fts_query = tokenizer.tokenize_for_search(query)
        
        return fts_query
    
    def _highlight(self, note: Note, query: str) -> dict:
        """
        生成关键词高亮
        
        Args:
            note: 笔记对象
            query: 搜索关键词
            
        Returns:
            {'title': '高亮后的标题', 'content': '高亮后的内容'}
        """
        # 使用 jieba 分词提取关键词
        tokenizer = get_tokenizer()
        terms = tokenizer.tokenize(query)
        
        def highlight_text(text: str) -> str:
            for term in terms:
                if len(term) < 1:
                    continue
                # 不区分大小写替换（中英文都支持）
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                text = pattern.sub('<mark>' + term + '</mark>', text)
            return text
        
        # 截取内容片段（前 200 字）
        content_snippet = note.content[:200] + "..." if len(note.content) > 200 else note.content
        
        return {
            'title': highlight_text(note.title),
            'content': highlight_text(content_snippet)
        }
    
    def suggest(self, prefix: str, limit: int = 10) -> List[str]:
        """
        搜索建议（自动补全）
        
        Args:
            prefix: 输入前缀
            limit: 返回数量限制
            
        Returns:
            建议词列表
        """
        if not prefix or len(prefix) < 2:
            return []
        
        # 使用 FTS5 的 prefix 查询
        cursor = self.db.execute("""
            SELECT DISTINCT title FROM notes_fts
            WHERE title MATCH ?
            LIMIT ?
        """, (prefix + "*", limit))
        
        suggestions = [row[0] for row in cursor.fetchall()]
        return suggestions
    
    def get_tags(self) -> List[str]:
        """
        获取所有标签
        
        Returns:
            标签列表
        """
        cursor = self.db.execute("SELECT DISTINCT tags FROM notes WHERE tags IS NOT NULL")
        
        all_tags = set()
        for row in cursor.fetchall():
            if row[0]:
                tags = json.loads(row[0])
                all_tags.update(tags)
        
        return sorted(list(all_tags))
    
    def count(self, query: str, tags: Optional[List[str]] = None) -> int:
        """
        统计搜索结果数量
        
        Args:
            query: 搜索关键词
            tags: 标签过滤
            
        Returns:
            匹配数量
        """
        # 空查询返回所有笔记
        if not query or not query.strip():
            sql = "SELECT COUNT(*) FROM notes"
            params = []
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append('%"' + tag + '"%')
                sql += " WHERE " + " OR ".join(tag_conditions)
            cursor = self.db.execute(sql, params)
            return cursor.fetchone()[0]
        
        fts_query = self._build_fts_query(query)
        
        tag_filter = ""
        params = []
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("n.tags LIKE ?")
                params.append('%"' + tag + '"%')
            tag_filter = "AND (" + " OR ".join(tag_conditions) + ")"
        
        sql = f"""
            SELECT COUNT(*) FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
            {tag_filter}
        """
        
        params = [fts_query] + params
        cursor = self.db.execute(sql, params)
        return cursor.fetchone()[0]
