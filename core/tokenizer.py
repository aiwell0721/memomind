"""
MemoMind 中文分词服务 - 基于 jieba
"""

import jieba
import jieba.analyse
import re
from typing import List, Optional
from functools import lru_cache


class ChineseTokenizer:
    """中文分词器"""
    
    def __init__(self):
        """初始化分词器"""
        # 配置 jieba
        jieba.initialize()
        
        # 添加常用技术词汇到词典
        self._add_custom_dictionary()
    
    def _add_custom_dictionary(self):
        """添加自定义词典"""
        custom_words = [
            # 技术词汇
            '人工智能', '机器学习', '深度学习', '神经网络',
            '自然语言处理', '计算机视觉', '强化学习',
            '大语言模型', 'Transformer', 'BERT', 'GPT',
            '知识库', '笔记软件', '全文搜索',
            
            # 产品名称
            'MemoMind', 'OpenClaw', 'SQLite',
        ]
        
        for word in custom_words:
            jieba.add_word(word)
    
    def tokenize(self, text: str, remove_stopwords: bool = True) -> List[str]:
        """
        对文本进行分词
        
        Args:
            text: 输入文本
            remove_stopwords: 是否移除停用词
            
        Returns:
            分词结果列表
        """
        if not text or not text.strip():
            return []
        
        # 使用 jieba 精确模式分词
        words = list(jieba.cut(text, cut_all=False))
        
        if remove_stopwords:
            words = self._remove_stopwords(words)
        
        # 过滤空白和单字符（保留英文单词）
        filtered = []
        for word in words:
            word = word.strip()
            if not word:
                continue
            
            # 保留英文单词（长度>=2）或中文字符
            if re.match(r'^[a-zA-Z]+$', word):
                if len(word) >= 2:
                    filtered.append(word.lower())
            elif len(word) >= 1:
                filtered.append(word)
        
        return filtered
    
    def tokenize_for_search(self, query: str) -> str:
        """
        为搜索查询分词（生成 FTS5 查询语句）
        
        Args:
            query: 搜索查询
            
        Returns:
            FTS5 查询字符串
        """
        if not query or not query.strip():
            return ""
        
        # 分词
        words = self.tokenize(query)
        
        if not words:
            return query
        
        # 构建 OR 查询（匹配任意一个词）
        # 对于英文词，使用精确匹配
        # 对于中文词，使用前缀匹配
        query_parts = []
        for word in words:
            if re.match(r'^[a-zA-Z]+$', word):
                # 英文词：精确匹配
                query_parts.append(f'"{word}"')
            else:
                # 中文词：使用 OR 连接
                query_parts.append(word)
        
        # 如果只有一个词，直接返回
        if len(query_parts) == 1:
            return query_parts[0]
        
        # 多个词：使用 OR 连接
        return ' OR '.join(query_parts)
    
    def _remove_stopwords(self, words: List[str]) -> List[str]:
        """
        移除停用词
        
        Args:
            words: 分词结果
            
        Returns:
            过滤后的词列表
        """
        # 常见中文停用词
        stopwords = {
            '的', '了', '和', '是', '在', '就', '都', '而', '及', '与',
            '着', '就', '也', '还', '个', '这', '那', '他', '她', '它',
            '我', '你', '我们', '你们', '他们', '她们', '它们',
            '这个', '那个', '什么', '怎么', '如何', '为什么',
            '可以', '可能', '应该', '必须', '能够',
            '以及', '还有', '但是', '不过', '虽然', '如果',
            '因为', '所以', '因此', '于是', '然后',
            '的', '地', '得', '着', '了', '过', '么', '嘛', '呢', '吧',
            '啊', '呀', '哦', '哎', '嗯', '哈', '嘿',
        }
        
        return [w for w in words if w not in stopwords and w.strip()]
    
    @lru_cache(maxsize=1024)
    def tokenize_cached(self, text: str) -> List[str]:
        """
        带缓存的分词（用于高频查询）
        
        Args:
            text: 输入文本
            
        Returns:
            分词结果列表
        """
        return self.tokenize(text)
    
    def add_word(self, word: str):
        """
        添加新词到词典
        
        Args:
            word: 新词
        """
        jieba.add_word(word)
        # 清除缓存
        self.tokenize_cached.cache_clear()
    
    def remove_word(self, word: str):
        """
        从词典移除词
        
        Args:
            word: 要移除的词
        """
        jieba.del_word(word)
        self.tokenize_cached.cache_clear()
    
    def get_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        提取关键词（基于 TF-IDF）
        
        Args:
            text: 输入文本
            top_k: 返回关键词数量
            
        Returns:
            关键词列表
        """
        # 使用 jieba 的 analyze 模块提取关键词
        keywords = jieba.analyse.extract_tags(text, topK=top_k)
        return keywords
    
    def segment_sentence(self, sentence: str, with_pos: bool = False) -> List[str]:
        """
        对句子进行分词（保留标点）
        
        Args:
            sentence: 输入句子
            with_pos: 是否保留标点符号
            
        Returns:
            分词结果列表
        """
        if with_pos:
            # 使用精确模式，保留标点
            words = list(jieba.cut(sentence, cut_all=False))
        else:
            words = self.tokenize(sentence)
        
        return words


# 全局分词器实例
_tokenizer: Optional[ChineseTokenizer] = None


def get_tokenizer() -> ChineseTokenizer:
    """获取全局分词器实例"""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = ChineseTokenizer()
    return _tokenizer


def tokenize_text(text: str) -> List[str]:
    """便捷函数：分词"""
    return get_tokenizer().tokenize(text)


def tokenize_for_search(query: str) -> str:
    """便捷函数：为搜索分词"""
    return get_tokenizer().tokenize_for_search(query)
