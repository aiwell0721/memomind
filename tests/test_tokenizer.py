"""MemoMind Tokenizer Tests"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tokenizer import ChineseTokenizer, get_tokenizer, tokenize_text, tokenize_for_search


class TestChineseTokenizer(unittest.TestCase):
    """Chinese Tokenizer Tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tokenizer = ChineseTokenizer()
    
    def test_tokenize_chinese(self):
        """Test tokenize Chinese text"""
        text = "人工智能是研究人类智能的理论"
        words = self.tokenizer.tokenize(text)
        
        self.assertGreater(len(words), 0)
        self.assertIn("人工智能", words)
    
    def test_tokenize_english(self):
        """Test tokenize English text"""
        text = "Machine learning is a subset of artificial intelligence"
        words = self.tokenizer.tokenize(text)
        
        self.assertGreater(len(words), 0)
        # Should have key terms
        words_lower = [w.lower() for w in words]
        self.assertTrue(any('machine' in w for w in words_lower))
        self.assertTrue(any('learning' in w for w in words_lower))
    
    def test_tokenize_mixed(self):
        """Test tokenize mixed Chinese and English"""
        text = "使用 Python 进行机器学习开发"
        words = self.tokenizer.tokenize(text)
        
        self.assertGreater(len(words), 0)
        # Check case-insensitive
        words_lower = [w.lower() for w in words]
        self.assertTrue(any('python' in w for w in words_lower))
        self.assertIn("机器学习", words)
    
    def test_tokenize_remove_stopwords(self):
        """Test stopword removal"""
        # Test with Chinese text (stopwords are Chinese)
        text = "这是一篇关于人工智能的文章"
        words = self.tokenizer.tokenize(text, remove_stopwords=True)
        
        # Should contain key terms
        self.assertIn("人工智能", words)
        # Should have fewer words with stopwords removed
        words_no_stop = self.tokenizer.tokenize(text, remove_stopwords=True)
        words_with_stop = self.tokenizer.tokenize(text, remove_stopwords=False)
        self.assertLessEqual(len(words_no_stop), len(words_with_stop))
    
    def test_tokenize_for_search(self):
        """Test tokenize for search query"""
        query = "人工智能技术"
        fts_query = self.tokenizer.tokenize_for_search(query)
        
        self.assertTrue(len(fts_query) > 0)
        # Should contain segmented terms
        self.assertIn("人工智能", fts_query) or self.assertIn("技术", fts_query)
    
    def test_tokenize_empty(self):
        """Test tokenize empty text"""
        words = self.tokenizer.tokenize("")
        self.assertEqual(len(words), 0)
        
        words = self.tokenizer.tokenize("   ")
        self.assertEqual(len(words), 0)
    
    def test_tokenize_cached(self):
        """Test cached tokenization"""
        text = "缓存测试文本"
        
        # First call
        words1 = self.tokenizer.tokenize_cached(text)
        
        # Second call (should use cache)
        words2 = self.tokenizer.tokenize_cached(text)
        
        self.assertEqual(words1, words2)
    
    def test_add_word(self):
        """Test add custom word"""
        # Add new word
        self.tokenizer.add_word("测试新词")
        
        # Should be recognized
        text = "这是一个测试新词的例子"
        words = self.tokenizer.tokenize(text)
        
        self.assertIn("测试新词", words)
    
    def test_get_keywords(self):
        """Test keyword extraction"""
        text = """
        人工智能是计算机科学的一个重要分支，
        它试图理解智能的实质，
        并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        """
        
        keywords = self.tokenizer.get_keywords(text, top_k=5)
        
        self.assertGreater(len(keywords), 0)
        # Should contain key terms
        self.assertTrue(any('人工智能' in kw or '智能' in kw for kw in keywords))
    
    def test_segment_sentence(self):
        """Test sentence segmentation"""
        sentence = "The weather is nice, let's go to the park."
        
        # Without punctuation  (basic test)
        words = self.tokenizer.segment_sentence(sentence, with_pos=False)
        self.assertGreater(len(words), 0)
        
        # With punctuation
        words_with_pos = self.tokenizer.segment_sentence(sentence, with_pos=True)
        self.assertGreater(len(words_with_pos), 0)
    
    def test_global_tokenizer(self):
        """Test global tokenizer instance"""
        tokenizer1 = get_tokenizer()
        tokenizer2 = get_tokenizer()
        
        # Should be same instance
        self.assertIs(tokenizer1, tokenizer2)
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        # tokenize_text
        words = tokenize_text("测试文本")
        self.assertGreater(len(words), 0)
        
        # tokenize_for_search
        query = tokenize_for_search("搜索测试")
        self.assertTrue(len(query) > 0)


class TestChineseTokenizerWithSearch(unittest.TestCase):
    """Tokenizer Integration Tests with Search"""
    
    def setUp(self):
        """Set up test fixtures"""
        from core.database import Database
        from core.search_service import SearchService
        
        self.db = Database(":memory:")
        self.search = SearchService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.db.close()
    
    def _seed_data(self):
        """Insert test data"""
        import json
        
        # English notes for testing
        test_notes = [
            ("AI Basics", "Artificial intelligence is the study of human intelligence", ["AI", "tech"]),
            ("Machine Learning", "Machine learning is a core area of artificial intelligence", ["AI", "ML"]),
            ("Deep Learning", "Deep learning is a branch of machine learning using neural networks", ["AI", "DL"]),
            ("Python Programming", "Python is a common programming language for machine learning", ["programming", "Python"]),
        ]
        
        for title, content, tags in test_notes:
            self.db.execute("""
                INSERT INTO notes (title, content, tags)
                VALUES (?, ?, ?)
            """, (title, content, json.dumps(tags)))
        
        self.db.commit()
    
    def test_english_search(self):
        """Test English text search"""
        results = self.search.search("artificial intelligence")
        
        self.assertGreater(len(results), 0)
        # Should match notes containing AI terms
        titles = [r.note.title for r in results]
        self.assertTrue(any("AI" in t or "intelligence" in t for t in titles))
    
    def test_mixed_search(self):
        """Test mixed search"""
        results = self.search.search("Python programming")
        
        self.assertGreater(len(results), 0)
        titles = [r.note.title for r in results]
        self.assertTrue(any("Python" in t for t in titles))
    
    def test_ml_search(self):
        """Test machine learning search"""
        results = self.search.search("machine learning")
        
        self.assertGreater(len(results), 0)
        # Should match notes about ML
        titles = [r.note.title for r in results]
        self.assertTrue(any("Learning" in t for t in titles))


if __name__ == '__main__':
    unittest.main()
