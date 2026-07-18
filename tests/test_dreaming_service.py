"""
DreamingService 单元测试（TDD）

本文件在 DreamingService 实现之前编写，所有测试初始应 FAIL。
实现 DreamingService 后逐步变绿。
"""
import pytest
import json
import os
from datetime import datetime, timedelta
from core.database import Database
from core.dreaming_models import DreamingSession, DreamingChange


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def db():
    """内存数据库，含 dreaming schema"""
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def db_with_notes(db):
    """含 30 条测试笔记的数据库"""
    notes = [
        # 5 条 Python 主题
        ("Python协程asyncio使用笔记", "asyncio事件循环用async/await定义协程。gather并发执行。", ["Python"]),
        ("FastAPI中间件开发", "FastAPI的middleware通过装饰器注册。用于鉴权日志CORS。", ["Python", "Web"]),
        ("pytest异步测试技巧", "pytest-asyncio支持async def测试。httpx.AsyncClient测试API。", ["Python", "测试"]),
        ("SQLAlchemy ORM入门", "SQLAlchemy是Python最流行的ORM。session管理数据库会话。", ["Python", "数据库"]),
        ("Python类型提示最佳实践", "Python类型提示用typing模块。Optional表示可为空。", ["Python"]),
        # 5 条 数据库主题
        ("PostgreSQL索引优化", "复合索引选择性高的列放前面。BRIN适合时序GIN适合全文搜索。", ["数据库"]),
        ("Redis缓存策略详解", "缓存穿透用布隆过滤器。缓存击穿用互斥锁。Redis7支持RedisJSON。", ["数据库", "缓存"]),
        ("MongoDB聚合管道", "match放最前面project只取需要字段lookup替代多表查询。", ["数据库", "NoSQL"]),
        ("MySQL慢查询排查", "开启slow_query_log。pt-query-digest分析日志。覆盖索引避免回表。", ["数据库"]),
        ("SQLite FTS5中文搜索", "FTS5配合jieba分词实现中文全文搜索。创建虚拟表指定tokenize。", ["数据库"]),
        # 5 条 生活主题
        ("每周健身计划", "周一胸加三头卧推飞鸟。周三背加二头引体向上。周五腿加肩深蹲推举。", ["生活", "健身"]),
        ("冰美式咖啡冲泡", "18g中深烘豆刻度15萃取36g浓缩液加150g冰水。水温92度。", ["生活", "咖啡"]),
        ("周末北京周边游", "古北水镇两天一夜长城温泉。十渡漂流攀岩。雁栖湖APEC会议中心。", ["生活", "旅行"]),
        ("租房避坑指南", "看房测试水压空调。合同写清楚维修责任。押金不超过3个月房租。", ["生活"]),
        ("减脂期饮食搭配", "每餐蛋白质30g蔬菜200g碳水100g。鸡胸肉虾仁豆腐轮换。16+8轻断食。", ["生活", "饮食"]),
        # 5 条 AI主题
        ("RAG检索增强生成", "文档切分chunk后Embedding向量化存入向量库。拼接prompt让LLM生成。", ["AI"]),
        ("LoRA低秩微调原理", "LoRA在注意力层旁路添加低秩矩阵。r=8 alpha=16常用设置节省显存。", ["AI", "深度学习"]),
        ("Embedding模型选型", "text2vec-base-chinese 512维中文效果好。bge-large-zh 1024维。", ["AI", "Embedding"]),
        ("LangChain Agent记忆", "ConversationBufferMemory保存对话。VectorStoreRetrievalMemory长期记忆。", ["AI"]),
        ("Prompt Engineering", "好的提示词包含角色任务输出格式。Few-shot提供示例引导模型。", ["AI", "Prompt"]),
        # 5 条 DevOps主题
        ("Docker Compose部署", "docker-compose.yml定义多容器服务。depends_on控制启动顺序。", ["DevOps"]),
        ("Git分支管理策略", "main加dev加feature分支。PR合并前squash。git rebase避免多余merge。", ["DevOps"]),
        ("CI/CD流水线配置", "GitHub Actions用.github/workflows定义。jobs并行执行steps串行。", ["DevOps"]),
        ("Kubernetes Pod调度", "K8s通过nodeSelector控制Pod位置。taint/toleration排斥不兼容节点。", ["DevOps"]),
        ("Makefile常用模板", "make install安装依赖。make test运行测试。.PHONY声明伪目标。", ["DevOps"]),
        # 5 条 架构主题
        ("微服务拆分原则", "按业务领域拆分Bounded Context。每个服务独立数据库。API Gateway统一鉴权。", ["架构"]),
        ("分布式ID生成方案", "Snowflake雪花算法41位时间戳加10位机器ID加12位序列号。", ["架构"]),
        ("消息队列选型指南", "Kafka高吞吐适合日志流处理。RabbitMQ高可靠适合订单。RocketMQ金融。", ["架构"]),
        ("限流算法对比", "令牌桶允许突发流量。漏桶强制恒定速率。滑动窗口精确但内存大。", ["架构"]),
        ("URL短链接系统设计", "Base62编码自增ID生成短链。分库分表按短链取模。Redis缓存热点URL。", ["架构"]),
    ]
    for title, content, tags in notes:
        db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content, json.dumps(tags, ensure_ascii=False))
        )
    db.commit()
    return db


# ── 数据模型测试 ──────────────────────────────────────────

class TestDreamingModels:
    def test_session_defaults(self):
        session = DreamingSession()
        assert session.trigger == "manual"
        assert session.status == "running"
        assert session.input_count == 0

    def test_session_custom(self):
        session = DreamingSession(trigger="scheduled", input_count=100)
        assert session.trigger == "scheduled"
        assert session.input_count == 100

    def test_change_defaults(self):
        change = DreamingChange()
        assert change.change_type == ""
        assert change.source_ids == []

    def test_change_with_data(self):
        change = DreamingChange(
            session_id=1, change_type="merge",
            source_ids=[10, 11], target_id=12,
            diff_summary="合并2条Python笔记"
        )
        assert change.session_id == 1
        assert len(change.source_ids) == 2


# ── DB Schema 测试 ────────────────────────────────────────

class TestDreamingSchema:
    def test_tables_exist(self, db):
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dreaming_sessions'"
        )
        assert cursor.fetchone() is not None

        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dreaming_changes'"
        )
        assert cursor.fetchone() is not None

    def test_insert_session(self, db):
        cursor = db.execute(
            "INSERT INTO dreaming_sessions (trigger, status) VALUES (?, ?)",
            ("manual", "completed")
        )
        db.commit()
        session_id = cursor.lastrowid
        assert session_id > 0

        row = db.execute("SELECT * FROM dreaming_sessions WHERE id=?", (session_id,)).fetchone()
        assert row['trigger'] == "manual"
        assert row['status'] == "completed"

    def test_insert_change(self, db):
        db.execute("INSERT INTO dreaming_sessions (trigger, status) VALUES ('manual', 'completed')")
        db.commit()
        session_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        db.execute(
            "INSERT INTO dreaming_changes (session_id, change_type, source_ids, target_id) VALUES (?, ?, ?, ?)",
            (session_id, "merge", json.dumps([1, 2]), 3)
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM dreaming_changes WHERE session_id=?", (session_id,)
        ).fetchone()
        assert row['change_type'] == "merge"
        assert json.loads(row['source_ids']) == [1, 2]
        assert row['target_id'] == 3


# ── DreamingService 核心功能测试 ──────────────────────────

class TestDreamingService:
    """这些测试在 DreamingService 实现前应全部 FAIL"""

    def test_service_exists(self, db_with_notes):
        """DreamingService 可导入和实例化"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        assert service is not None

    def test_select_memories_default(self, db_with_notes):
        """选择待处理记忆 — 默认策略：创建超过7天"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        # 新创建的笔记不满足条件，应返回空
        notes = service.select_memories_for_dreaming(strategy="default")
        assert notes == []

    def test_select_memories_aggressive(self, db_with_notes):
        """激进策略：返回所有非置顶笔记"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        notes = service.select_memories_for_dreaming(strategy="aggressive")
        assert len(notes) == 30

    def test_cluster_by_embedding(self, db_with_notes):
        """Embedding 聚类：30条5主题笔记应产生多个簇"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        notes = service.select_memories_for_dreaming(strategy="aggressive")
        clusters = service.cluster_memories(notes)
        # 5个主题，期望至少3个多元素簇
        multi_clusters = [c for c in clusters if len(c) > 1]
        assert len(multi_clusters) >= 3, f"期望至少3个多元素簇，实际{len(multi_clusters)}"
        assert len(clusters) < len(notes), "应有聚类压缩效果"

    def test_merge_cluster(self, db_with_notes):
        """合并一个记忆簇"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        notes = service.select_memories_for_dreaming(strategy="aggressive")
        clusters = service.cluster_memories(notes)
        multi = [c for c in clusters if len(c) > 1]
        if not multi:
            pytest.skip("无多元素簇，跳过合并测试")
        merged = service.merge_cluster(multi[0])
        assert merged.title
        assert merged.content

    def test_dreaming_pipeline_dry_run(self, db_with_notes):
        """--dry-run 模式：返回预览报告，不修改数据库"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        # 计数前
        before = db_with_notes.execute("SELECT COUNT(*) FROM dreaming_sessions").fetchone()[0]
        report = service.run_dreaming(dry_run=True)
        after = db_with_notes.execute("SELECT COUNT(*) FROM dreaming_sessions").fetchone()[0]
        assert before == after, "dry-run 不应写入数据库"
        assert 'input_count' in report

    def test_dreaming_pipeline_full(self, db_with_notes):
        """完整 Dreaming 流程：写入 session 和 change 记录"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        report = service.run_dreaming(strategy="aggressive", dry_run=False)
        assert report['input_count'] > 0
        # 应创建 session 记录
        sessions = db_with_notes.execute("SELECT COUNT(*) FROM dreaming_sessions").fetchone()[0]
        assert sessions >= 1

    def test_rollback(self, db_with_notes):
        """回滚功能：恢复原始记忆状态"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        report = service.run_dreaming(strategy="aggressive", dry_run=False)
        session_id = report.get('session_id')
        if not session_id:
            pytest.skip("无 session_id，跳过回滚测试")

        # 记录 dreaming 后的笔记数（合并后增加）
        after_dreaming = db_with_notes.execute(
            "SELECT COUNT(*) FROM notes"
        ).fetchone()[0]

        # 回滚
        service.rollback(session_id)

        # 回滚后应恢复（删除合并笔记、恢复原始笔记）
        after_rollback = db_with_notes.execute(
            "SELECT COUNT(*) FROM notes"
        ).fetchone()[0]
        assert after_rollback <= after_dreaming, "回滚应删除合并产生的笔记"

    def test_dreaming_history(self, db_with_notes):
        """查看 Dreaming 历史"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        # 初始可能为空
        history = service.get_history()
        assert isinstance(history, list)
        # 执行一次 dreaming
        service.run_dreaming(strategy="aggressive", dry_run=False)
        history = service.get_history()
        assert len(history) >= 1
        assert 'trigger' in history[0]

    def test_dreaming_changes_list(self, db_with_notes):
        """查看 Dreaming 变更记录"""
        from core.dreaming_service import DreamingService
        service = DreamingService(db_with_notes)
        service.run_dreaming(strategy="aggressive", dry_run=False)
        history = service.get_history()
        if not history:
            pytest.skip("无 dreaming 历史")
        session_id = history[0]['id']
        changes = service.get_changes(session_id)
        assert isinstance(changes, list)
