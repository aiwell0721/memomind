"""
MemoMind AI 自动标签服务
基于内容分析自动提取和推荐标签
"""

import json
import re
from typing import List, Optional, Dict, Set, Tuple
from collections import Counter
from .database import Database
from .tokenizer import get_tokenizer


class AutoTagService:
    """自动标签服务"""
    
    def __init__(self, db: Database):
        """
        初始化自动标签服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
        self.tokenizer = get_tokenizer()
        self._tag_synonyms: Dict[str, str] = {}
        self._load_synonyms()
    
    def _load_synonyms(self):
        """加载标签同义词映射"""
        self._tag_synonyms = {
            'python': 'Python',
            '机器学习': '机器学习',
            'ml': '机器学习',
            'ai': 'AI',
            '人工智能': 'AI',
            '深度学习': '深度学习',
            'dl': '深度学习',
            'nlp': 'NLP',
            '自然语言处理': 'NLP',
            'web开发': 'Web开发',
            '前端': '前端',
            '后端': '后端',
            'javascript': 'JavaScript',
            'js': 'JavaScript',
            '数据库': '数据库',
            'sql': 'SQL',
            '算法': '算法',
            '数据结构': '数据结构',
        }
    
    def extract_tags(
        self,
        title: str,
        content: str,
        max_tags: int = 10,
        min_score: float = 0.1
    ) -> List[Tuple[str, float]]:
        """
        从笔记内容中提取标签
        
        Args:
            title: 笔记标题
            content: 笔记内容
            max_tags: 最大标签数量
            min_score: 最低分数阈值
            
        Returns:
            (标签, 分数) 列表，按分数降序排列
        """
        text = f"{title} {content}"
        
        # 方法 1：关键词提取（TF-IDF 风格）
        keyword_tags = self._extract_keyword_tags(text, max_tags * 2)
        
        # 方法 2：技术术语识别
        tech_tags = self._extract_technical_tags(text, max_tags)
        
        # 方法 3：已有标签匹配
        existing_tags = self._match_existing_tags(text)
        
        # 合并结果
        tag_scores: Dict[str, float] = {}
        
        # 关键词分数
        for tag, score in keyword_tags:
            normalized = self._normalize_tag(tag)
            tag_scores[normalized] = tag_scores.get(normalized, 0) + score
        
        # 技术术语分数（权重更高）
        for tag, score in tech_tags:
            normalized = self._normalize_tag(tag)
            tag_scores[normalized] = tag_scores.get(normalized, 0) + score * 1.5
        
        # 已有标签匹配（最高权重）
        for tag in existing_tags:
            normalized = self._normalize_tag(tag)
            tag_scores[normalized] = tag_scores.get(normalized, 0) + 2.0
        
        # 过滤、归一化和排序
        max_score = max((score for _, score in tag_scores.items()), default=1.0)
        max_score = max(max_score, 0.001)  # 避免除零
        
        filtered = [(tag, score / max_score) for tag, score in tag_scores.items() if score / max_score >= min_score]
        filtered.sort(key=lambda x: x[1], reverse=True)
        
        return filtered[:max_tags]
    
    def _extract_keyword_tags(self, text: str, max_tags: int) -> List[Tuple[str, float]]:
        """基于词频提取关键词标签"""
        # 分词
        terms = self.tokenizer.tokenize(text)
        
        # 过滤
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', 
                     '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', 
                     '着', '没有', '看', '好', '自己', '这', '那', '什么', '怎么', '为什么',
                     '可以', '通过', '使用', '进行', '我们', '他们', '这个', '那个'}
        
        # 统计词频（标题中的词权重更高）
        title_terms = set(self.tokenizer.tokenize(text[:200]))  # 假设前 200 字符是标题
        
        term_freq = Counter()
        for term in terms:
            if len(term) < 2 or term in stop_words:
                continue
            if term.isalpha():  # 纯字母或纯中文
                weight = 1.5 if term in title_terms else 1.0
                term_freq[term] += weight
        
        total = sum(term_freq.values())
        if total == 0:
            return []
        
        # 归一化分数
        tags = [(term, count / total) for term, count in term_freq.most_common(max_tags)]
        return tags
    
    def _extract_technical_tags(self, text: str, max_tags: int) -> List[Tuple[str, float]]:
        """识别技术术语标签"""
        # 技术术语模式
        tech_patterns = [
            # 编程语言和框架
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin)\b',
            r'\b(React|Vue|Angular|Django|Flask|Spring|Express|TensorFlow|PyTorch|NumPy|Pandas)\b',
            # 技术概念
            r'\b(API|REST|GraphQL|gRPC|HTTP|HTTPS|TCP/IP|DNS|SQL|NoSQL|MongoDB|Redis|PostgreSQL)\b',
            r'\b(Docker|Kubernetes|CI/CD|DevOps|AWS|Azure|GCP|Linux|Windows|macOS)\b',
            # 中文技术术语
            '机器学习', '深度学习', '人工智能', '自然语言处理', '计算机视觉',
            '数据挖掘', '数据分析', '云计算', '微服务', '分布式',
            '前端开发', '后端开发', '全栈开发', '移动端开发',
        ]
        
        tags = []
        for pattern in tech_patterns:
            if isinstance(pattern, str):
                if pattern in text:
                    tags.append((pattern, 1.0))
            else:
                matches = re.findall(pattern, text)
                for match in matches:
                    tags.append((match, 0.8))
        
        # 去重并限制数量
        seen = set()
        unique_tags = []
        for tag, score in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append((tag, score))
        
        return unique_tags[:max_tags]
    
    def _match_existing_tags(self, text: str) -> List[str]:
        """匹配数据库中已有的标签"""
        cursor = self.db.execute("SELECT DISTINCT tags FROM notes WHERE tags IS NOT NULL")
        
        all_tags = set()
        for row in cursor.fetchall():
            if row[0]:
                try:
                    tags = json.loads(row[0])
                    all_tags.update(tags)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # 检查哪些标签出现在文本中
        matched = []
        for tag in all_tags:
            if tag in text or tag.lower() in text.lower():
                matched.append(tag)
        
        return matched
    
    def _normalize_tag(self, tag: str) -> str:
        """标准化标签（处理同义词）"""
        lower = tag.lower()
        if lower in self._tag_synonyms:
            return self._tag_synonyms[lower]
        # 首字母大写（英文标签）
        if tag.isalpha() and not tag.isupper():
            return tag.capitalize() if len(tag) > 1 else tag.lower()
        return tag
    
    def auto_tag_note(self, note_id: int) -> List[str]:
        """
        自动为笔记添加标签
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            推荐标签列表
        """
        cursor = self.db.execute("""
            SELECT title, content, tags FROM notes WHERE id = ?
        """, (note_id,))
        
        row = cursor.fetchone()
        if not row:
            return []
        
        title, content, existing_tags = row
        
        # 提取新标签
        suggested = self.extract_tags(title, content)
        suggested_tags = [tag for tag, _ in suggested]
        
        # 合并已有标签
        if existing_tags:
            try:
                existing = json.loads(existing_tags)
                # 去重
                all_tags = list(dict.fromkeys(existing + suggested_tags))
            except (json.JSONDecodeError, TypeError):
                all_tags = suggested_tags
        else:
            all_tags = suggested_tags
        
        # 更新笔记标签
        self.db.execute("""
            UPDATE notes SET tags = ? WHERE id = ?
        """, (json.dumps(all_tags, ensure_ascii=False), note_id))
        self.db.commit()
        
        return all_tags
    
    def batch_auto_tag(self, limit: int = 100) -> List[Dict]:
        """
        批量自动标签
        
        Args:
            limit: 处理数量限制
            
        Returns:
            处理结果列表
        """
        # 查找没有标签的笔记
        cursor = self.db.execute("""
            SELECT id, title FROM notes WHERE tags IS NULL OR tags = '' OR tags = '[]'
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            note_id, title = row
            tags = self.auto_tag_note(note_id)
            results.append({
                'note_id': note_id,
                'title': title,
                'tags': tags,
                'tag_count': len(tags)
            })
        
        return results
    
    def merge_similar_tags(self, threshold: float = 0.8) -> Dict[str, List[str]]:
        """
        合并相似标签（同义词合并）
        
        Args:
            threshold: 相似度阈值
            
        Returns:
            {标准标签: [相似标签列表]}
        """
        # 获取所有标签
        cursor = self.db.execute("SELECT DISTINCT tags FROM notes WHERE tags IS NOT NULL")
        
        all_tags = set()
        for row in cursor.fetchall():
            if row[0]:
                try:
                    tags = json.loads(row[0])
                    all_tags.update(tags)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # 按同义词映射分组
        merged: Dict[str, List[str]] = {}
        for tag in all_tags:
            normalized = self._normalize_tag(tag)
            if normalized not in merged:
                merged[normalized] = []
            if tag != normalized:
                merged[normalized].append(tag)
        
        # 过滤掉没有相似标签的
        return {k: v for k, v in merged.items() if v}
    
    def get_tag_recommendations(
        self,
        title: str,
        content: str,
        limit: int = 10
    ) -> List[Tuple[str, float, bool]]:
        """
        获取标签推荐（包含是否已存在的信息）
        
        Args:
            title: 笔记标题
            content: 笔记内容
            limit: 推荐数量
            
        Returns:
            (标签, 分数, 是否已存在于数据库) 列表
        """
        # 获取已有标签集合
        cursor = self.db.execute("SELECT DISTINCT tags FROM notes WHERE tags IS NOT NULL")
        existing_tags = set()
        for row in cursor.fetchall():
            if row[0]:
                try:
                    tags = json.loads(row[0])
                    existing_tags.update(tags)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # 提取推荐标签
        suggested = self.extract_tags(title, content, max_tags=limit)
        
        return [
            (tag, score, tag in existing_tags)
            for tag, score in suggested
        ]
