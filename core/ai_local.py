"""
本地 AI Provider — 基于 jieba + 启发式算法
零外部依赖，零 API 调用。
"""

from typing import List
from collections import Counter
from .ai_provider import AIProvider
from .tokenizer import get_tokenizer


class LocalProvider(AIProvider):
    """本地 AI 提供者（默认）"""

    def __init__(self):
        self.tokenizer = get_tokenizer()

    def summarize(self, text: str, max_length: int = 200) -> str:
        """
        抽取式摘要：按句子重要性排序，选 Top 句子直到 max_length。
        重要性 = 词频(0.5) + 位置偏好(0.3) + 首句权重(0.2)。
        """
        if len(text) <= max_length:
            return text

        sentences = self._split_sentences(text)
        if not sentences:
            return text[:max_length]

        # 词频统计
        all_words = []
        for s in sentences:
            all_words.extend(self.tokenizer.tokenize(s))
        word_freq = Counter(all_words)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
                     '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会'}

        # 句子评分
        scored = []
        for i, sent in enumerate(sentences):
            words = self.tokenizer.tokenize(sent)
            freq_score = sum(word_freq.get(w, 0) for w in words if w not in stop_words) / max(len(words), 1)
            pos_score = 1.0 / (i + 1)
            first_score = 1.0 if i == 0 else 0.0
            score = freq_score * 0.5 + pos_score * 0.3 + first_score * 0.2
            scored.append((sent.strip(), score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # 选取 Top 句子（按原文顺序）
        selected = {s for s, _ in scored[:max(1, max_length // 50)]}
        result = []
        for sent, _ in scored:
            if sent in selected:
                if len("\n".join(result)) + len(sent) > max_length:
                    break
                result.append(sent)

        return "\n".join(result) if result else text[:max_length]

    def answer(self, question: str, context: str) -> str:
        """
        从上下文中提取最相关的答案片段。
        策略：将上下文分段，找到与问题关键词匹配度最高的段落。
        """
        question_terms = set(self.tokenizer.tokenize(question))

        paragraphs = context.replace('\n\n', '\n').split('\n')
        best_score = 0.0
        best_para = ""

        for para in paragraphs:
            para_terms = set(self.tokenizer.tokenize(para))
            overlap = len(question_terms & para_terms)
            if len(question_terms) > 0:
                score = overlap / len(question_terms)
            else:
                score = 0
            if score > best_score and len(para) > 10:
                best_score = score
                best_para = para

        if best_score < 0.15 or not best_para:
            return ""

        return best_para

    def embed(self, text: str) -> List[float]:
        """本地模式不支持向量化"""
        return []

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """按中英文句子边界分割"""
        import re
        sentences = re.split(r'[。！？\.\!\?]+', text)
        return [s.strip() for s in sentences if s.strip()]
