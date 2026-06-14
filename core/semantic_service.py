"""
MemoMind 语义搜索服务
基于 TF-IDF + 余弦相似度的语义搜索
支持混合搜索（FTS5 关键词 + 语义相似度）
"""

import json
import math
import re
import numpy as np
from typing import List, Optional, Dict, Tuple
from collections import Counter
from .database import Database
from .models import Note, SearchResult
from .tokenizer import get_tokenizer


class SemanticService:
    """语义搜索服务（TF-IDF + 余弦相似度）"""
    
    def __init__(self, db: Database, provider=None):
        """
        初始化语义搜索服务

        Args:
            db: 数据库实例
            provider: AI Provider（可选，支持 embedding 增强）
        """
        self.db = db
        self.tokenizer = get_tokenizer()
        self.provider = provider
        # IDF 缓存
        self._idf_cache: Dict[str, float] = {}
        self._doc_count: int = 0
        self._idf_loaded = False
    
    def _has_column(self, table: str, column: str) -> bool:
        """检查表是否包含指定列"""
        try:
            cursor = self.db.execute(f"PRAGMA table_info({table})")
            columns = [row['name'] for row in cursor.fetchall()]
            return column in columns
        except Exception:
            return False
    
    def _load_idf(self):
        """从数据库加载 IDF 统计"""
        if self._idf_loaded:
            return
        
        # 获取所有文档的词汇
        cursor = self.db.execute("SELECT title, content, tags FROM notes")
        
        # 统计每个词的文档频率
        doc_freq: Counter = Counter()
        total_docs = 0
        
        for row in cursor.fetchall():
            title, content, tags = row
            text = self._extract_text(title, content, tags)
            terms = set(self.tokenizer.tokenize(text))
            for term in terms:
                if len(term) >= 1:
                    doc_freq[term] += 1
            total_docs += 1
        
        self._doc_count = total_docs
        
        # 计算 IDF: log(N / df)
        if total_docs > 0:
            for term, freq in doc_freq.items():
                self._idf_cache[term] = math.log((total_docs + 1) / (freq + 1)) + 1
        
        self._idf_loaded = True
    
    def _extract_text(self, title: str, content: str, tags: str = None) -> str:
        """提取笔记的完整文本"""
        text = f"{title} {content}"
        if tags:
            try:
                tag_list = json.loads(tags) if isinstance(tags, str) else tags
                text += " " + " ".join(tag_list)
            except (json.JSONDecodeError, TypeError):
                pass
        return text
    
    def _tokenize_and_filter(self, text: str) -> List[str]:
        """分词并过滤停用词"""
        terms = self.tokenizer.tokenize(text)
        # 过滤单字符和常见停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        return [t for t in terms if len(t) > 1 and t not in stop_words]
    
    def _compute_tfidf_vector(self, text: str) -> Dict[str, float]:
        """计算 TF-IDF 向量"""
        self._load_idf()
        
        terms = self._tokenize_and_filter(text)
        if not terms:
            return {}
        
        # 计算词频
        term_freq = Counter(terms)
        total_terms = len(terms)
        
        # 计算 TF-IDF
        tfidf = {}
        for term, freq in term_freq.items():
            tf = freq / total_terms  # 归一化词频
            idf = self._idf_cache.get(term, 1.0)
            tfidf[term] = tf * idf
        
        return tfidf
    
    @staticmethod
    def _cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算两个 TF-IDF 向量的余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        # 获取所有词
        all_terms = set(vec1.keys()) | set(vec2.keys())
        
        # 计算点积和模长
        dot_product = 0.0
        norm1 = 0.0
        norm2 = 0.0
        
        for term in all_terms:
            v1 = vec1.get(term, 0.0)
            v2 = vec2.get(term, 0.0)
            dot_product += v1 * v2
            norm1 += v1 * v1
            norm2 += v2 * v2
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (math.sqrt(norm1) * math.sqrt(norm2))
    
    def semantic_search(
        self,
        query: str,
        workspace_id: Optional[int] = None,
        limit: int = 20,
        threshold: float = 0.0
    ) -> List[SearchResult]:
        """
        语义搜索
        
        Args:
            query: 搜索查询
            workspace_id: 工作区过滤（可选）
            limit: 返回数量
            threshold: 最低相似度阈值
            
        Returns:
            按语义相似度排序的搜索结果
        """
        self._load_idf()
        query = query.strip()
        if not query:
            return []
        
        # 计算查询的 TF-IDF 向量
        query_vector = self._compute_tfidf_vector(query)
        if not query_vector:
            return []
        
        # 获取所有笔记（检查 workspace_id 列是否存在）
        has_workspace = self._has_column('notes', 'workspace_id')
        
        if workspace_id and has_workspace:
            cursor = self.db.execute("""
                SELECT id, title, content, tags, created_at, updated_at 
                FROM notes WHERE workspace_id = ?
            """, (workspace_id,))
        else:
            cursor = self.db.execute("""
                SELECT id, title, content, tags, created_at, updated_at 
                FROM notes
            """)
        
        results = []
        for row in cursor.fetchall():
            note = Note.from_row(row)
            text = self._extract_text(note.title, note.content, note.tags)
            note_vector = self._compute_tfidf_vector(text)
            
            similarity = self._cosine_similarity(query_vector, note_vector)
            
            if similarity >= threshold:
                highlights = self._highlight(note, query)
                results.append(SearchResult(
                    note=note,
                    score=similarity,
                    highlights=highlights
                ))
        
        # 按相似度排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def hybrid_search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        workspace_id: Optional[int] = None,
        limit: int = 20,
        semantic_weight: float = 0.5,
        offset: int = 0
    ) -> List[SearchResult]:
        """
        混合搜索（FTS5 关键词 + 语义相似度）
        
        Args:
            query: 搜索查询
            tags: 标签过滤
            workspace_id: 工作区过滤
            limit: 返回数量
            semantic_weight: 语义权重（0-1，0=纯关键词，1=纯语义）
            offset: 分页偏移
            
        Returns:
            混合排序的搜索结果
        """
        query = query.strip()
        if not query:
            return []
        
        # 1. 获取 FTS5 关键词搜索结果
        from .search_service import SearchService
        fts_service = SearchService(self.db)
        fts_results = fts_service.search(query, tags=tags, limit=limit * 2)
        
        # 2. 获取语义搜索结果
        semantic_results = self.semantic_search(query, workspace_id=workspace_id, limit=limit * 2)
        
        # 3. 合并结果（按 note ID 去重）
        note_scores: Dict[int, Dict] = {}
        
        # FTS5 分数归一化
        fts_max = max((r.score for r in fts_results), default=1.0)
        fts_max = max(fts_max, 0.001)  # 避免除零
        
        for r in fts_results:
            normalized = r.score / fts_max
            note_scores[r.note.id] = {
                'note': r.note,
                'fts_score': normalized,
                'semantic_score': 0.0,
                'highlights': r.highlights
            }
        
        # 语义分数
        for r in semantic_results:
            if r.note.id in note_scores:
                note_scores[r.note.id]['semantic_score'] = r.score
                # 保留 FTS5 的高亮（通常更准确）
            else:
                note_scores[r.note.id] = {
                    'note': r.note,
                    'fts_score': 0.0,
                    'semantic_score': r.score,
                    'highlights': r.highlights
                }
        
        # 4. 计算混合分数
        for note_id, data in note_scores.items():
            data['combined_score'] = (
                (1 - semantic_weight) * data['fts_score'] +
                semantic_weight * data['semantic_score']
            )
        
        # 5. 排序并返回
        sorted_results = sorted(
            note_scores.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        final_results = []
        for data in sorted_results[offset:offset + limit]:
            final_results.append(SearchResult(
                note=data['note'],
                score=data['combined_score'],
                highlights=data['highlights']
            ))
        
        return final_results
    
    def find_similar_notes(
        self,
        note_id: int,
        limit: int = 10,
        exclude_self: bool = True
    ) -> List[Tuple[SearchResult, float]]:
        """
        查找与给定笔记相似的笔记
        
        Args:
            note_id: 参考笔记 ID
            limit: 返回数量
            exclude_self: 是否排除自身
            
        Returns:
            (搜索结果, 相似度) 列表
        """
        # 获取参考笔记
        cursor = self.db.execute("""
            SELECT id, title, content, tags, created_at, updated_at 
            FROM notes WHERE id = ?
        """, (note_id,))
        
        row = cursor.fetchone()
        if not row:
            return []
        
        ref_note = Note.from_row(row)
        ref_text = self._extract_text(ref_note.title, ref_note.content, ref_note.tags)
        ref_vector = self._compute_tfidf_vector(ref_text)
        
        # 搜索所有其他笔记
        cursor = self.db.execute("""
            SELECT id, title, content, tags, created_at, updated_at 
            FROM notes WHERE id != ?
        """, (note_id,) if exclude_self else (0,))
        
        results = []
        for row in cursor.fetchall():
            note = Note.from_row(row)
            text = self._extract_text(note.title, note.content, note.tags)
            note_vector = self._compute_tfidf_vector(text)
            
            similarity = self._cosine_similarity(ref_vector, note_vector)
            
            if similarity > 0:
                highlights = {
                    'title': note.title,
                    'content': note.content[:200] + "..." if len(note.content) > 200 else note.content
                }
                results.append(SearchResult(
                    note=note,
                    score=similarity,
                    highlights=highlights
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return [(r, r.score) for r in results[:limit]]
    
    def _highlight(self, note: Note, query: str) -> dict:
        """生成关键词高亮"""
        terms = self._tokenize_and_filter(query)
        
        def highlight_text(text: str) -> str:
            for term in terms:
                if len(term) < 1:
                    continue
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                text = pattern.sub('<mark>' + term + '</mark>', text)
            return text
        
        content_snippet = note.content[:200] + "..." if len(note.content) > 200 else note.content
        
        return {
            'title': highlight_text(note.title),
            'content': highlight_text(content_snippet)
        }
    
    def refresh_index(self):
        """重建 IDF 索引"""
        self._idf_cache.clear()
        self._doc_count = 0
        self._idf_loaded = False
        self._load_idf()
    
    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        self._load_idf()
        return {
            'total_documents': self._doc_count,
            'unique_terms': len(self._idf_cache),
            'avg_idf': sum(self._idf_cache.values()) / len(self._idf_cache) if self._idf_cache else 0
        }

    def scan_duplicates(
        self,
        workspace_id: Optional[int] = None,
        threshold: float = 0.6,
        limit: int = 50
    ) -> List[Dict]:
        """
        全库扫描疑似重复的笔记组

        策略：计算所有笔记的 TF-IDF 向量 → 两两比较余弦相似度 →
              超过阈值的对用并查集分组 → 返回每组信息和共同标签

        Args:
            workspace_id: 工作区过滤（可选，None 表示扫描全部）
            threshold: 相似度阈值（0-1，默认 0.6）
            limit: 最多扫描的笔记数

        Returns:
            [{
                'notes': [Note, ...],
                'max_similarity': float,
                'common_tags': [str, ...]
            }, ...]
        """
        self._load_idf()

        # 1. 获取笔记列表
        has_workspace = self._has_column('notes', 'workspace_id')
        if workspace_id is not None and has_workspace:
            cursor = self.db.execute(
                "SELECT id, title, content, tags, created_at, updated_at "
                "FROM notes WHERE workspace_id = ? LIMIT ?",
                (workspace_id, limit))
        else:
            cursor = self.db.execute(
                "SELECT id, title, content, tags, created_at, updated_at "
                "FROM notes LIMIT ?", (limit,))

        notes = []
        for row in cursor.fetchall():
            notes.append(Note.from_row(row))

        if len(notes) < 2:
            return []

        # 2. 一次性计算所有 TF-IDF 向量（避免重复计算）
        vectors: Dict[int, Dict[str, float]] = {}
        for note in notes:
            text = self._extract_text(note.title, note.content, note.tags)
            vec = self._compute_tfidf_vector(text)
            if vec:
                vectors[note.id] = vec

        # 3. 两两比较，收集超过阈值的对
        pairs: List[Tuple[int, int, float]] = []
        for i in range(len(notes)):
            for j in range(i + 1, len(notes)):
                id1, id2 = notes[i].id, notes[j].id
                v1, v2 = vectors.get(id1), vectors.get(id2)
                if not v1 or not v2:
                    continue
                sim = self._cosine_similarity(v1, v2)
                if sim >= threshold:
                    pairs.append((id1, id2, sim))

        if not pairs:
            return []

        # 4. 并查集分组
        parent: Dict[int, int] = {}

        def find(x: int) -> int:
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        pair_scores: Dict[Tuple[int, int], float] = {}
        for id1, id2, sim in pairs:
            union(id1, id2)
            key = (min(id1, id2), max(id1, id2))
            if key not in pair_scores or sim > pair_scores[key]:
                pair_scores[key] = sim

        # 5. 聚合组信息
        groups_map: Dict[int, List[Note]] = {}
        for note in notes:
            root = find(note.id)
            if root not in groups_map:
                groups_map[root] = []
            groups_map[root].append(note)

        result = []
        note_map = {n.id: n for n in notes}
        for group_notes in groups_map.values():
            if len(group_notes) < 2:
                continue

            # 计算组内最高相似度
            max_sim = 0.0
            for i in range(len(group_notes)):
                for j in range(i + 1, len(group_notes)):
                    key = (min(group_notes[i].id, group_notes[j].id),
                           max(group_notes[i].id, group_notes[j].id))
                    max_sim = max(max_sim, pair_scores.get(key, 0.0))

            # 共同标签
            tag_sets = [set(n.tags) for n in group_notes]
            common_tags = list(tag_sets[0].intersection(*tag_sets[1:])) if len(tag_sets) > 1 else list(tag_sets[0])

            result.append({
                'notes': group_notes,
                'max_similarity': round(max_sim, 4),
                'common_tags': common_tags
            })

        # 按最高相似度降序排列
        result.sort(key=lambda g: g['max_similarity'], reverse=True)
        return result
