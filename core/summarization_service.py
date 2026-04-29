"""
MemoMind 笔记摘要生成服务
自动为长笔记生成摘要
"""

import json
import re
from typing import List, Optional, Dict
from collections import Counter
from .database import Database
from .tokenizer import get_tokenizer


class SummarizationService:
    """笔记摘要生成服务"""
    
    def __init__(self, db: Database):
        self.db = db
        self.tokenizer = get_tokenizer()
    
    def summarize(self, note_id: int, max_length: int = 200, method: str = 'extractive') -> Optional[str]:
        """为笔记生成摘要"""
        cursor = self.db.execute("SELECT title, content FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        title, content = row
        if len(content) <= max_length:
            return content
        
        if method == 'extractive':
            return self._extractive_summarize(title, content, max_length)
        else:
            return self._abstractive_summarize(title, content, max_length)
    
    def _extractive_summarize(self, title: str, content: str, max_length: int) -> str:
        """抽取式摘要"""
        sentences = self._split_sentences(content)
        if not sentences:
            return content[:max_length] + "..."
        
        all_words = self.tokenizer.tokenize(content)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
                     '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会',
                     '这', '那', '什么', '怎么', '可以', '通过', '使用', '进行', '我们'}
        word_freq = Counter(w for w in all_words if w not in stop_words and len(w) > 1)
        
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            words = self.tokenizer.tokenize(sentence)
            freq_score = sum(word_freq.get(w, 0) for w in words) / max(len(words), 1)
            position_score = 1.0 / (i + 1)
            title_words = set(self.tokenizer.tokenize(title))
            sentence_words = set(self.tokenizer.tokenize(sentence))
            title_score = len(title_words & sentence_words) / max(len(title_words), 1)
            total_score = freq_score * 0.5 + position_score * 0.3 + title_score * 0.2
            sentence_scores.append((sentence, total_score))
        
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        summary_parts = []
        current_length = 0
        selected_indices = set()
        for idx, (sentence, score) in enumerate(sentence_scores):
            if current_length + len(sentence) > max_length:
                break
            selected_indices.add(idx)
            summary_parts.append(sentence)
            current_length += len(sentence) + 1
        
        if 0 not in selected_indices and sentences:
            first_sentence = sentences[0]
            if len(first_sentence) <= max_length * 0.5:
                summary_parts.insert(0, first_sentence)
        
        if not summary_parts:
            return content[:max_length] + "..."
        
        summary = ' '.join(summary_parts)
        if len(content) > max_length:
            summary += "..."
        return summary
    
    def _abstractive_summarize(self, title: str, content: str, max_length: int) -> str:
        """摘要式摘要"""
        sentences = self._split_sentences(content)
        if not sentences:
            return content[:max_length] + "..."
        
        all_words = self.tokenizer.tokenize(content)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
                     '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会'}
        word_freq = Counter(w for w in all_words if w not in stop_words and len(w) > 1)
        key_terms = [term for term, _ in word_freq.most_common(5)]
        
        if not key_terms:
            return content[:max_length] + "..."
        
        summary = f"本文介绍了{', '.join(key_terms[:3])}"
        if sentences:
            first_sentence = sentences[0]
            if len(summary) + len(first_sentence) < max_length:
                summary += "。" + first_sentence
        
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        elif len(content) > max_length:
            summary += "..."
        return summary
    
    def _split_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        sentences = re.split(r'[。！？.!?\n]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def batch_summarize(self, limit: int = 50, min_length: int = 500, max_summary_length: int = 200) -> List[Dict]:
        """批量生成摘要"""
        cursor = self.db.execute(
            "SELECT id, title, length(content) as content_len FROM notes WHERE length(content) > ? LIMIT ?",
            (min_length, limit))
        
        results = []
        for row in cursor.fetchall():
            note_id, title, content_len = row
            summary = self.summarize(note_id, max_length=max_summary_length)
            results.append({
                'note_id': note_id,
                'title': title,
                'content_length': content_len,
                'summary': summary,
                'summary_length': len(summary) if summary else 0
            })
        return results
    
    def update_summary(self, note_id: int, summary: str) -> bool:
        """更新笔记的摘要"""
        try:
            self.db.execute("UPDATE notes SET summary = ? WHERE id = ?", (summary, note_id))
            self.db.commit()
            return True
        except Exception:
            return False
    
    def get_summaries(self, limit: int = 20) -> List[Dict]:
        """获取已有摘要的笔记"""
        try:
            cursor = self.db.execute(
                "SELECT id, title, summary FROM notes WHERE summary IS NOT NULL AND summary != '' LIMIT ?",
                (limit,))
            return [{'note_id': row['id'], 'title': row['title'], 'summary': row['summary']} for row in cursor.fetchall()]
        except Exception:
            return []
    
    def get_summary_stats(self) -> Dict:
        """获取摘要统计信息"""
        try:
            cursor = self.db.execute("""
                SELECT COUNT(*) as total_notes,
                    SUM(CASE WHEN length(content) > 500 THEN 1 ELSE 0 END) as needs_summary,
                    SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as has_summary
                FROM notes""")
            row = cursor.fetchone()
            return {
                'total_notes': row[0],
                'needs_summary': row[1],
                'has_summary': row[2],
                'completion_rate': row[2] / max(row[1], 1)
            }
        except Exception:
            return {'total_notes': 0, 'needs_summary': 0, 'has_summary': 0, 'completion_rate': 0}
