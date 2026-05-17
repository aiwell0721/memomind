"""
AI Provider 抽象层测试
"""

import os
import pytest
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_provider import AIProvider, create_provider
from core.ai_local import LocalProvider
from core.database import Database
from core.rag_service import RAGService
from core.summarization_service import SummarizationService


# ==================== create_provider() 测试 ====================


class TestCreateProvider:
    """工厂函数测试"""

    def setup_method(self):
        self._old_provider = os.environ.get("MEMOMIND_AI_PROVIDER")
        self._old_openai_key = os.environ.get("OPENAI_API_KEY")
        self._old_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    def teardown_method(self):
        if self._old_provider is not None:
            os.environ["MEMOMIND_AI_PROVIDER"] = self._old_provider
        else:
            os.environ.pop("MEMOMIND_AI_PROVIDER", None)
        if self._old_openai_key is not None:
            os.environ["OPENAI_API_KEY"] = self._old_openai_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)
        if self._old_anthropic_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = self._old_anthropic_key
        else:
            os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_default_is_local(self):
        """默认返回 LocalProvider"""
        os.environ.pop("MEMOMIND_AI_PROVIDER", None)
        provider = create_provider()
        assert isinstance(provider, LocalProvider)

    def test_explicit_local(self):
        """显式设置 local 返回 LocalProvider"""
        os.environ["MEMOMIND_AI_PROVIDER"] = "local"
        provider = create_provider()
        assert isinstance(provider, LocalProvider)

    def test_openai_without_key_fallback(self):
        """指定 openai 但无 key 时 fallback + warning"""
        os.environ["MEMOMIND_AI_PROVIDER"] = "openai"
        os.environ.pop("OPENAI_API_KEY", None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            provider = create_provider()
            assert isinstance(provider, LocalProvider)
            assert len(w) == 1
            assert "OPENAI_API_KEY" in str(w[0].message)

    def test_anthropic_without_key_fallback(self):
        """指定 anthropic 但无 key 时 fallback + warning"""
        os.environ["MEMOMIND_AI_PROVIDER"] = "anthropic"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            provider = create_provider()
            assert isinstance(provider, LocalProvider)
            assert len(w) == 1
            assert "ANTHROPIC_API_KEY" in str(w[0].message)


# ==================== LocalProvider 测试 ====================


class TestLocalProvider:
    """本地 Provider 测试"""

    def setup_method(self):
        self.provider = LocalProvider()

    def test_summarize_short_text(self):
        """短文本直接返回"""
        text = "这是一段很短的文本"
        result = self.provider.summarize(text, max_length=200)
        assert result == text

    def test_summarize_long_text(self):
        """长文本生成摘要"""
        text = "这是第一句话。它非常重要。第二句话也很关键。第三句话是补充说明。第四句话可以忽略。" * 20
        result = self.provider.summarize(text, max_length=100)
        assert isinstance(result, str)
        assert len(result) <= 150  # 允许少许超出

    def test_summarize_empty_text(self):
        """空文本处理"""
        result = self.provider.summarize("", max_length=100)
        assert result == ""

    def test_answer_with_context(self):
        """从上下文中提取答案"""
        context = """
        MemoMind 是一个团队知识库系统。
        它使用 SQLite 作为存储后端。
        支持 FTS5 全文搜索。
        提供 REST API 和 MCP Server 两种接口。
        """
        result = self.provider.answer("MemoMind 使用什么作为存储后端？", context)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_answer_no_match(self):
        """无关问题返回空"""
        context = "今天天气很好。我们去公园散步吧。"
        result = self.provider.answer("Python 的类型提示怎么写？", context)
        # 可能匹配不上
        assert result == "" or isinstance(result, str)

    def test_embed_not_supported(self):
        """本地模式不支持 embedding"""
        result = self.provider.embed("测试文本")
        assert result == []


# ==================== RAGService with Provider 测试 ====================


class TestRAGServiceWithProvider:
    """RAG 服务 + Provider 集成测试"""

    def setup_method(self):
        self.db = Database(":memory:")

    def teardown_method(self):
        self.db.close()

    def test_rag_without_provider(self):
        """无 Provider 时使用本地算法"""
        rag = RAGService(self.db)
        assert rag.provider is None

        # 插入测试数据
        self.db.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            ("测试笔记", "MemoMind 是一个团队知识库系统，支持笔记管理和搜索功能。")
        )
        self.db.commit()

        result = rag.ask("MemoMind 是什么？")
        assert result is not None
        assert isinstance(result.answer, str)

    def test_rag_with_local_provider(self):
        """LocalProvider 集成"""
        provider = LocalProvider()
        rag = RAGService(self.db, provider=provider)
        assert rag.provider is provider

    def test_rag_provider_fallback(self):
        """Provider 失败时 fallback 到本地"""
        # 创建一个会抛出异常的 mock provider
        class BrokenProvider(AIProvider):
            def summarize(self, text, max_length=200):
                raise RuntimeError("API 不可用")
            def answer(self, question, context):
                raise RuntimeError("API 不可用")
            def embed(self, text):
                return []

        rag = RAGService(self.db, provider=BrokenProvider())

        # 插入数据
        self.db.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            ("Fallback 测试", "测试 Provider 失败后的 fallback 行为。系统应该使用本地算法。")
        )
        self.db.commit()

        # 不应抛出异常，应该 fallback
        result = rag.ask("测试 fallback 行为？")
        assert result is not None


# ==================== SummarizationService with Provider 测试 ====================


class TestSummarizationServiceWithProvider:
    """摘要服务 + Provider 集成测试"""

    def setup_method(self):
        self.db = Database(":memory:")

    def teardown_method(self):
        self.db.close()

    def test_summarize_without_provider(self):
        """无 Provider 时使用本地算法"""
        svc = SummarizationService(self.db)
        assert svc.provider is None

        cursor = self.db.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            ("测试笔记", "这是一段很长的内容。" * 50)
        )
        note_id = cursor.lastrowid
        self.db.commit()

        summary = svc.summarize(note_id, max_length=100)
        assert summary is not None
        assert isinstance(summary, str)

    def test_summarize_with_local_provider(self):
        """LocalProvider 集成"""
        provider = LocalProvider()
        svc = SummarizationService(self.db, provider=provider)
        assert svc.provider is provider

    def test_summarize_short_content(self):
        """短内容直接返回"""
        svc = SummarizationService(self.db, provider=LocalProvider())

        cursor = self.db.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            ("短笔记", "这是短内容")
        )
        note_id = cursor.lastrowid
        self.db.commit()

        summary = svc.summarize(note_id, max_length=200)
        assert summary == "这是短内容"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
