"""
Dreaming API 集成测试
"""
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from core.api_server import create_app


@pytest.fixture
def app():
    """创建测试应用（使用内存数据库）"""
    return create_app(":memory:")


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def token(app):
    from core.api_server import generate_token
    return generate_token("testuser")


@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_notes(client, headers):
    """插入 12 条测试笔记，3 个主题各 4 条，供 Dreaming 聚类"""
    notes = [
        # Python 主题 4 条
        ("Python协程asyncio使用笔记", "asyncio事件循环用async和await定义协程。gather可以并发执行多个协程提高效率。", ["Python"]),
        ("FastAPI中间件开发教程", "FastAPI框架通过@app.middleware装饰器注册中间件。在请求前后执行逻辑。", ["Python", "Web"]),
        ("pytest异步测试最佳实践", "pytest-asyncio支持async def测试函数。httpx.AsyncClient测试FastAPI应用。", ["Python", "测试"]),
        ("SQLAlchemy ORM入门教程", "SQLAlchemy是Python最流行的ORM框架。session管理数据库会话和事务。", ["Python", "数据库"]),
        # 数据库主题 4 条
        ("PostgreSQL索引优化技巧", "复合索引选择性高的列放最前面。BRIN索引适合大表的时序数据查询。", ["数据库"]),
        ("Redis缓存策略详解", "缓存穿透使用布隆过滤器防御。缓存击穿用互斥锁保护热点数据。", ["数据库", "缓存"]),
        ("MongoDB聚合管道优化", "match操作放在管道最前面过滤数据。project只选取需要的字段减少传输量。", ["数据库", "NoSQL"]),
        ("SQLite FTS5全文搜索", "FTS5配合jieba分词实现中文全文搜索。创建虚拟表并指定tokenize分词器。", ["数据库"]),
        # DevOps 主题 4 条
        ("Docker Compose生产部署", "docker-compose定义多容器服务。depends_on控制启动顺序确保依赖就绪。", ["DevOps"]),
        ("Git分支管理策略", "main加dev加feature分支结构。PR合并前squash保持线性历史。", ["DevOps"]),
        ("CI/CD流水线配置", "GitHub Actions通过YAML定义流水线。jobs并行执行加快整体构建速度。", ["DevOps"]),
        ("Kubernetes Pod调度", "K8s通过nodeSelector控制Pod位置。taint和toleration排斥不兼容节点。", ["DevOps"]),
    ]
    for title, content, tags in notes:
        client.post("/api/notes", json={"title": title, "content": content, "tags": tags}, headers=headers)
    return len(notes)


class TestDreamingAPI:
    """Dreaming API 端点测试"""

    def test_run_dreaming_dry_run(self, client, headers, setup_notes):
        """预览模式：不写入数据库"""
        res = client.post("/api/dreaming/run", json={"strategy": "aggressive", "dry_run": True}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["dry_run"] is True
        assert data["session_id"] is None
        assert data["input_count"] == 12

    def test_run_dreaming_full(self, client, headers, setup_notes):
        """完整 Dreaming：写入 session 和变更"""
        res = client.post("/api/dreaming/run", json={"strategy": "aggressive", "dry_run": False}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["session_id"] is not None
        assert data["merged_count"] > 0
        assert data["archived_count"] > 0

    def test_run_dreaming_requires_auth(self, client):
        """未认证请求应被拒绝"""
        res = client.post("/api/dreaming/run", json={"strategy": "default"})
        assert res.status_code in (401, 403)

    def test_get_history(self, client, headers, setup_notes):
        """查看 Dreaming 历史"""
        # 先执行一次 Dreaming 产生记录
        client.post("/api/dreaming/run", json={"strategy": "aggressive", "dry_run": False}, headers=headers)

        res = client.get("/api/dreaming/history", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "id" in data[0]
        assert "status" in data[0]
        assert data[0]["status"] == "completed"

    def test_get_history_requires_auth(self, client):
        res = client.get("/api/dreaming/history")
        assert res.status_code in (401, 403)

    def test_get_changes(self, client, headers, setup_notes):
        """查看 Dreaming 变更详情"""
        res_run = client.post("/api/dreaming/run", json={"strategy": "aggressive", "dry_run": False}, headers=headers)
        session_id = res_run.json()["session_id"]

        res = client.get(f"/api/dreaming/{session_id}/changes", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["change_type"] == "merge"

    def test_get_changes_empty_session(self, client, headers):
        """不存在的 session 返回空列表"""
        res = client.get("/api/dreaming/9999/changes", headers=headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_rollback(self, client, headers, setup_notes):
        """回滚应恢复原始笔记"""
        res_run = client.post("/api/dreaming/run", json={"strategy": "aggressive", "dry_run": False}, headers=headers)
        session_id = res_run.json()["session_id"]

        res = client.post(f"/api/dreaming/{session_id}/rollback", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["restored_notes"] > 0
        assert data["deleted_merged_notes"] > 0

    def test_rollback_requires_auth(self, client):
        res = client.post("/api/dreaming/1/rollback")
        assert res.status_code in (401, 403)

    def test_invalid_strategy_rejected(self, client, headers):
        """无效策略应返回 422"""
        res = client.post("/api/dreaming/run", json={"strategy": "invalid"}, headers=headers)
        assert res.status_code == 422


class TestDreamingScheduler:
    """调度器单元测试"""

    def test_scheduler_create(self, app):
        """调度器可创建"""
        from core.dreaming_scheduler import DreamingScheduler
        from core.dreaming_service import DreamingService
        # app 的 db 可以复用
        db_path = ":memory:"
        from core.database import Database
        db = Database(db_path)
        dreaming = DreamingService(db)
        sched = DreamingScheduler(dreaming)
        assert sched is not None
        sched.stop()
        db.close()

    def test_scheduler_start_stop(self, app):
        """调度器启动/停止"""
        from core.dreaming_scheduler import DreamingScheduler
        from core.dreaming_service import DreamingService
        from core.database import Database
        db = Database(":memory:")
        dreaming = DreamingService(db)
        sched = DreamingScheduler(dreaming)
        sched.start(target_hour=3)
        assert sched._running
        sched.stop()
        assert not sched._running
        db.close()

    def test_scheduler_run_now(self, app):
        """立即执行应返回报告"""
        from core.dreaming_scheduler import DreamingScheduler
        from core.dreaming_service import DreamingService
        from core.database import Database
        db = Database(":memory:")
        dreaming = DreamingService(db)
        sched = DreamingScheduler(dreaming)
        result = sched.run_now()
        assert "input_count" in result
        sched.stop()
        db.close()
