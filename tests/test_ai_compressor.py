"""
AI Compressor 单元测试（TDD）

本文件先于实现编写，初始应全部 FAIL。
实现 AiCompressor 和集成后逐步变绿。
"""
import pytest
import json
from unittest.mock import patch
from core.ai_compressor import AiCompressor, CompressResult


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_notes():
    """3 条内容相似的笔记"""
    return [
        type("Note", (), {
            "id": 3, "title": "[MVP] 核心笔记功能实现",
            "content": "使用 SQLite 作为本地存储方案。支持软删除。FTS5 全文索引。",
            "tags": json.dumps(["笔记", "存储"]),
        }),
        type("Note", (), {
            "id": 4, "title": "[增强] 知识编译器实现",
            "content": "SQLite 存储知识图谱。实体提取准确率82%。规则+NLP方案。",
            "tags": json.dumps(["AI", "知识库"]),
        }),
        type("Note", (), {
            "id": 5, "title": "[MVP] 笔记搜索功能实现",
            "content": "SQLite FTS5 全文索引集成。BM25 相关度排序。中文分词优化。",
            "tags": json.dumps(["搜索", "FTS5"]),
        }),
    ]


@pytest.fixture
def compressor():
    """使用默认配置的 AiCompressor 实例"""
    return AiCompressor(api_key="test_key")


# ── AiCompressor 基础测试 ────────────────────────────────

class TestAiCompressorBasic:
    """基础结构和配置测试"""

    def test_compressor_exists(self):
        """AiCompressor 可导入和实例化"""
        from core.ai_compressor import AiCompressor
        c = AiCompressor(api_key="test")
        assert c is not None

    def test_compressor_default_config(self):
        """默认配置检查"""
        c = AiCompressor(api_key="test")
        assert c.model == "deepseek-v4-flash"
        assert c.max_input_tokens == 8000

    def test_compressor_custom_config(self):
        """自定义配置"""
        c = AiCompressor(api_key="test", model="deepseek-chat", max_input_tokens=4000)
        assert c.model == "deepseek-chat"
        assert c.max_input_tokens == 4000

    def test_compress_result_dataclass(self):
        """CompressResult 结构正确"""
        r = CompressResult(
            title="测试标题",
            content="测试内容",
            keywords=["key1", "key2"],
            token_usage=100,
        )
        assert r.title == "测试标题"
        assert r.content == "测试内容"
        assert r.keywords == ["key1", "key2"]
        assert r.token_usage == 100


# ── AiCompressor 核心功能测试 ─────────────────────────────

class TestAiCompressorCore:
    """核心压缩逻辑测试"""

    @patch("core.ai_compressor.AiCompressor._call_llm")
    def test_compress_cluster_structure(self, mock_call_llm, compressor, sample_notes):
        """压缩结果结构正确"""
        mock_call_llm.return_value = """[标题]
这是合并的标题
[精要]
这是合并后的内容
[关键词]
key1, key2, key3"""
        
        result = compressor.compress_cluster(sample_notes)
        
        assert isinstance(result, CompressResult)
        assert result.title == "这是合并的标题"
        assert result.content == "这是合并后的内容"
        assert "key1" in result.keywords
        assert result.token_usage > 0

    @patch("core.ai_compressor.AiCompressor._call_llm")
    def test_compress_cluster_malformed_response(self, mock_call_llm, compressor, sample_notes):
        """格式异常时应优雅降级，不崩溃"""
        mock_call_llm.return_value = "乱七八糟的回复，没有标题也没有精要"
        
        result = compressor.compress_cluster(sample_notes)
        
        # 即使格式异常，也应返回有效结构
        assert isinstance(result, CompressResult)
        assert result.title  # 应取第一条笔记标题
        assert result.content  # 应包含精简内容

    @patch("core.ai_compressor.AiCompressor._call_llm")
    def test_compress_cluster_api_timeout(self, mock_call_llm, compressor, sample_notes):
        """API 超时应优雅降级"""
        mock_call_llm.side_effect = TimeoutError("API timeout")
        
        result = compressor.compress_cluster(sample_notes)
        
        assert isinstance(result, CompressResult)
        assert result.title  # 降级标题
        assert result.token_usage == 0

    @patch("core.ai_compressor.AiCompressor._call_llm")
    def test_compress_cluster_empty_keywords(self, mock_call_llm, compressor, sample_notes):
        """关键词为空时返回合并标签"""
        mock_call_llm.return_value = """[标题]
测试标题
[精要]
测试内容
[关键词]
"""
        result = compressor.compress_cluster(sample_notes)
        
        assert isinstance(result, CompressResult)
        assert len(result.keywords) > 0  # 应包含笔记的原始标签

    def test_prompt_building_single_note(self, compressor):
        """生成 prompt 验证"""
        note = type("Note", (), {"id": 1, "title": "测试", "content": "内容", "tags": "[]"})
        msgs = compressor._build_prompt([note])
        all_text = " ".join(m.get("content", "") for m in msgs)
        assert "[标题]" in all_text
        assert "[精要]" in all_text
        assert "[关键词]" in all_text
        assert "测试" in all_text

    @patch("core.ai_compressor.AiCompressor._call_llm")
    def test_compress_cluster_retry_on_failure(self, mock_call_llm, compressor, sample_notes):
        """首次失败应重试"""
        mock_call_llm.side_effect = [
            RuntimeError("First attempt failed"),
            """[标题]
成功
[精要]
成功内容
[关键词]
success"""
        ]
        result = compressor.compress_cluster(sample_notes)
        
        assert result.title == "成功"
        assert mock_call_llm.call_count == 2

    @patch("core.ai_compressor.AiCompressor._call_llm")
    def test_compress_cluster_max_retries_exceeded(self, mock_call_llm, compressor, sample_notes):
        """重试耗尽后降级"""
        mock_call_llm.side_effect = [RuntimeError("fail")] * 3
        
        result = compressor.compress_cluster(sample_notes)
        
        assert isinstance(result, CompressResult)
        assert result.token_usage == 0
        assert mock_call_llm.call_count == 2  # 重试2次

    def test_truncate_long_content(self, compressor):
        """超长内容应被截断"""
        max_chars = 5000
        long_content = "a" * 20000
        note = type("Note", (), {"id": 1, "title": "长笔记", "content": long_content, "tags": "[]"})
        truncated = compressor._truncate_content(note, max_chars=max_chars)
        # 截断含省略标记，总长度 ≈ max_chars + 省略标记
        assert len(truncated.content) <= max_chars + 30


# ── DreamingService 集成测试 ──────────────────────────────

class TestDreamingServiceAI:
    """DreamingService + AiCompressor 集成测试"""

    def test_dreaming_run_with_ai_compress_parameter(self):
        """run_dreaming 应支持 ai_compress 参数"""
        from core.dreaming_service import DreamingService
        import inspect
        sig = inspect.signature(DreamingService.run_dreaming)
        # 检查参数签名
        params = {k: v.default for k, v in sig.parameters.items() if k != 'self'}
        assert 'ai_compress' in params

    def test_dreaming_session_has_ai_compressed_field(self):
        """dreaming_sessions 表应有 ai_compressed 和 token_cost 字段"""
        from core.database import Database
        db = Database(":memory:")
        cursor = db.execute("PRAGMA table_info(dreaming_sessions)")
        columns = {row['name'] for row in cursor.fetchall()}
        assert 'ai_compressed' in columns
        assert 'token_cost' in columns
        db.close()

    def test_dreaming_concentrates_table_exists(self):
        """dreaming_concentrates 表应存在"""
        from core.database import Database
        db = Database(":memory:")
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dreaming_concentrates'"
        )
        assert cursor.fetchone() is not None
        db.close()

    def test_dreaming_concentrates_schema(self):
        """dreaming_concentrates 表结构正确"""
        from core.database import Database
        db = Database(":memory:")
        cursor = db.execute("PRAGMA table_info(dreaming_concentrates)")
        columns = {row['name'] for row in cursor.fetchall()}
        expected = {'id', 'session_id', 'source_ids', 'target_note_id',
                    'ai_title', 'ai_content', 'keywords', 'created_at'}
        assert expected.issubset(columns)
        db.close()
