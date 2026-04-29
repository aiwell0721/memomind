"""
MemoMind RAG 问答服务
基于检索增强生成的自然语言问答
"""

import json
from typing import List, Optional, Dict, Tuple
from .database import Database
from .models import Note
from .semantic_service import SemanticService
from .tokenizer import get_tokenizer


class RAGAnswer:
    """RAG 回答数据模型"""
    
    def __init__(self, answer: str, sources: List[Dict], confidence: float):
        self.answer = answer
        self.sources = sources  # [{'note_id': 1, 'title': '...', 'snippet': '...'}]
        self.confidence = confidence  # 0-1 置信度
    
    def to_dict(self) -> Dict:
        return {
            'answer': self.answer,
            'sources': self.sources,
            'confidence': self.confidence
        }


class RAGService:
    """RAG 问答服务"""
    
    def __init__(self, db: Database):
        """
        初始化 RAG 服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
        self.semantic = SemanticService(db)
        self.tokenizer = get_tokenizer()
    
    def ask(
        self,
        question: str,
        workspace_id: Optional[int] = None,
        max_sources: int = 5,
        max_context_length: int = 4000
    ) -> RAGAnswer:
        """
        回答用户问题
        
        Args:
            question: 用户问题
            workspace_id: 工作区过滤
            max_sources: 最大引用来源数
            max_context_length: 最大上下文长度
            
        Returns:
            RAG 回答
        """
        question = question.strip()
        if not question:
            return RAGAnswer("", [], 0.0)
        
        # 1. 检索相关笔记
        results = self.semantic.semantic_search(
            question,
            workspace_id=workspace_id,
            limit=max_sources,
            threshold=0.05
        )
        
        if not results:
            return RAGAnswer(
                "抱歉，我在知识库中没有找到相关内容来回答这个问题。",
                [],
                0.0
            )
        
        # 2. 构建上下文
        context, sources = self._build_context(results, max_context_length)
        
        # 3. 生成回答（基于模板的抽取式回答）
        answer, confidence = self._generate_answer(question, context, results)
        
        return RAGAnswer(answer, sources, confidence)
    
    def _build_context(
        self,
        results: List,
        max_length: int
    ) -> Tuple[str, List[Dict]]:
        """
        构建回答上下文
        
        Returns:
            (上下文字符串, 来源列表)
        """
        context_parts = []
        sources = []
        current_length = 0
        
        for result in results:
            note = result.note
            snippet = self._extract_snippet(note.content, 300)
            
            source = {
                'note_id': note.id,
                'title': note.title,
                'snippet': snippet,
                'score': result.score
            }
            sources.append(source)
            
            context_part = f"【{note.title}】\n{note.content[:500]}"
            if len(note.content) > 500:
                context_part += "..."
            
            if current_length + len(context_part) > max_length:
                break
            
            context_parts.append(context_part)
            current_length += len(context_part)
        
        return "\n\n".join(context_parts), sources
    
    def _extract_snippet(self, content: str, max_length: int) -> str:
        """提取内容片段"""
        if len(content) <= max_length:
            return content
        # 尝试在句子边界截断
        for sep in ['。', '！', '？', '\n', '.']:
            idx = content[:max_length].rfind(sep)
            if idx > max_length * 0.6:
                return content[:idx + 1]
        return content[:max_length] + "..."
    
    def _generate_answer(
        self,
        question: str,
        context: str,
        results: List
    ) -> Tuple[str, float]:
        """
        生成回答（基于抽取式和生成式混合）
        
        Returns:
            (回答, 置信度)
        """
        # 方法 1：抽取式回答（直接引用相关内容）
        extractive_answer, extractive_confidence = self._extractive_answer(question, results)
        
        # 方法 2：摘要式回答（总结相关内容）
        abstractive_answer, abstractive_confidence = self._abstractive_answer(question, results)
        
        # 选择置信度更高的回答
        if extractive_confidence >= abstractive_confidence:
            return extractive_answer, extractive_confidence
        else:
            return abstractive_answer, abstractive_confidence
    
    def _extractive_answer(
        self,
        question: str,
        results: List
    ) -> Tuple[str, float]:
        """
        抽取式回答：直接从笔记中提取相关段落
        
        策略：
        1. 找到与问题关键词匹配度最高的段落
        2. 返回该段落作为回答
        """
        question_terms = set(self.tokenizer.tokenize(question))
        
        best_score = 0
        best_paragraph = ""
        best_note_title = ""
        
        for result in results:
            note = result.note
            # 将内容分段
            paragraphs = note.content.replace('\n\n', '\n').split('\n')
            
            for para in paragraphs:
                para_terms = set(self.tokenizer.tokenize(para))
                # 计算与问题的重叠度
                overlap = len(question_terms & para_terms)
                if len(question_terms) > 0:
                    overlap_score = overlap / len(question_terms)
                else:
                    overlap_score = 0
                
                # 考虑语义搜索分数
                combined_score = overlap_score * 0.5 + result.score * 0.5
                
                if combined_score > best_score and len(para) > 10:
                    best_score = combined_score
                    best_paragraph = para
                    best_note_title = note.title
        
        if best_score < 0.1 or not best_paragraph:
            return "", 0.0
        
        # 构建回答
        answer = f"根据「{best_note_title}」：{best_paragraph}"
        confidence = min(best_score * 1.5, 1.0)  # 缩放到 0-1
        
        return answer, confidence
    
    def _abstractive_answer(
        self,
        question: str,
        results: List
    ) -> Tuple[str, float]:
        """
        摘要式回答：总结多个笔记的关键信息
        
        策略：
        1. 提取所有相关笔记的标题
        2. 提取每个笔记的核心内容
        3. 生成总结性回答
        """
        if not results:
            return "", 0.0
        
        # 收集关键信息
        titles = [r.note.title for r in results[:3]]
        
        # 提取高频关键词
        all_terms = []
        for result in results:
            terms = self.tokenizer.tokenize(result.note.content[:500])
            all_terms.extend(terms)
        
        from collections import Counter
        term_freq = Counter(all_terms)
        # 过滤停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
                     '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会'}
        important_terms = [t for t, _ in term_freq.most_common(10) if t not in stop_words and len(t) > 1]
        
        if not important_terms:
            return "", 0.0
        
        # 构建摘要式回答
        if len(titles) == 1:
            answer = f"关于这个问题，「{titles[0]}」中提到：{results[0].note.content[:200]}"
        else:
            answer = f"根据知识库中的 {len(results)} 篇相关内容（包括「{titles[0]}」等），"
            answer += "主要涉及以下关键词："
            answer += "、".join(important_terms[:5])
            answer += "。"
        
        # 置信度基于搜索结果的相关性
        avg_score = sum(r.score for r in results[:3]) / min(3, len(results))
        confidence = min(avg_score * 1.2, 0.9)
        
        return answer, confidence
    
    def ask_with_tags(
        self,
        question: str,
        tags: Optional[List[str]] = None,
        max_sources: int = 5
    ) -> RAGAnswer:
        """
        带标签过滤的问答
        
        Args:
            question: 用户问题
            tags: 标签过滤
            max_sources: 最大引用来源数
            
        Returns:
            RAG 回答
        """
        if not tags:
            return self.ask(question, max_sources=max_sources)
        
        # 先用标签过滤笔记，再搜索
        tag_filter = " OR ".join([f"n.tags LIKE '%\"{tag}\"%'" for tag in tags])
        
        cursor = self.db.execute(f"""
            SELECT n.id, n.title, n.content, n.tags, n.created_at, n.updated_at
            FROM notes n
            WHERE {tag_filter}
        """)
        
        notes = []
        for row in cursor.fetchall():
            notes.append(Note.from_row(row))
        
        if not notes:
            return RAGAnswer("没有找到指定标签的相关笔记。", [], 0.0)
        
        # 在过滤后的笔记中搜索
        question_terms = set(self.tokenizer.tokenize(question))
        scored_notes = []
        
        for note in notes:
            note_terms = set(self.tokenizer.tokenize(f"{note.title} {note.content[:500]}"))
            overlap = len(question_terms & note_terms)
            score = overlap / max(len(question_terms), 1)
            scored_notes.append((note, score))
        
        scored_notes.sort(key=lambda x: x[1], reverse=True)
        
        # 构建结果
        from .models import SearchResult
        results = []
        for note, score in scored_notes[:max_sources]:
            results.append(SearchResult(
                note=note,
                score=score,
                highlights={'title': note.title, 'content': note.content[:200]}
            ))
        
        context, sources = self._build_context(results, 4000)
        answer, confidence = self._generate_answer(question, context, results)
        
        return RAGAnswer(answer, sources, confidence)
    
    def get_suggested_questions(self, note_id: int, limit: int = 5) -> List[str]:
        """
        基于笔记内容生成建议问题
        
        Args:
            note_id: 笔记 ID
            limit: 建议数量
            
        Returns:
            建议问题列表
        """
        cursor = self.db.execute("""
            SELECT title, content FROM notes WHERE id = ?
        """, (note_id,))
        
        row = cursor.fetchone()
        if not row:
            return []
        
        title, content = row
        
        # 提取关键概念
        terms = self.tokenizer.tokenize(f"{title} {content[:500]}")
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
                     '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会'}
        key_terms = [t for t in set(terms) if t not in stop_words and len(t) > 1][:10]
        
        # 生成问题模板
        questions = []
        for term in key_terms[:limit]:
            questions.append(f"什么是{term}？")
            questions.append(f"{term}有什么特点？")
        
        return questions[:limit]
