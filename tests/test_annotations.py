"""
MemoMind 备注功能测试 — TDD

先写测试，后验证代码。
对应详细设计: docs-project/04-detailed-design/07-备注功能详细设计.md
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
    app = create_app(":memory:")
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def token(app):
    """获取测试 Token"""
    from core.api_server import generate_token
    return generate_token("testuser")


@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def note_id(client, headers):
    """创建一篇测试笔记，返回其 id"""
    resp = client.post("/api/notes", json={
        "title": "测试笔记",
        "content": "这是一篇用于测试备注功能的笔记内容。",
        "tags": ["测试"],
    }, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestAnnotationSchema:
    """测试数据库 schema 迁移"""

    def test_type_field_exists(self, app):
        """notes 表应有 type 字段，默认值为 'note'"""
        from core.database import Database
        db = Database(":memory:")
        row = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='notes' AND type='table'"
        ).fetchone()
        schema = row[0] if row else ""
        assert "type" in schema, "notes 表缺少 type 字段"

    def test_parent_id_field_exists(self, app):
        """notes 表应有 parent_id 字段"""
        from core.database import Database
        db = Database(":memory:")
        row = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='notes' AND type='table'"
        ).fetchone()
        schema = row[0] if row else ""
        assert "parent_id" in schema, "notes 表缺少 parent_id 字段"

    def test_ai_summary_field_exists(self, app):
        """notes 表应有 ai_summary 字段"""
        from core.database import Database
        db = Database(":memory:")
        row = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='notes' AND type='table'"
        ).fetchone()
        schema = row[0] if row else ""
        assert "ai_summary" in schema, "notes 表缺少 ai_summary 字段"

    def test_type_index_exists(self, app):
        """应有 idx_notes_type 索引"""
        from core.database import Database
        db = Database(":memory:")
        row = db.execute(
            "SELECT name FROM sqlite_master WHERE name='idx_notes_type' AND type='index'"
        ).fetchone()
        assert row is not None, "缺少 idx_notes_type 索引"

    def test_parent_id_index_exists(self, app):
        """应有 idx_notes_parent 索引"""
        from core.database import Database
        db = Database(":memory:")
        row = db.execute(
            "SELECT name FROM sqlite_master WHERE name='idx_notes_parent' AND type='index'"
        ).fetchone()
        assert row is not None, "缺少 idx_notes_parent 索引"


class TestAnnotationAPI:
    """测试备注 API 端点"""

    def test_create_annotation(self, client, headers, note_id):
        """创建顶级备注 → 返回 201"""
        resp = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "注意：这份数据源是 2023 年的"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "annotation"
        assert data["note_id"] == note_id
        assert data["content"] == "注意：这份数据源是 2023 年的"
        assert data["parent_id"] is None
        assert "id" in data
        assert "created_at" in data

    def test_create_reply_annotation(self, client, headers, note_id):
        """创建回复备注（parent_id 指向父备注）→ 正确嵌套"""
        # 创建顶级备注
        parent = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "顶级备注"},
            headers=headers,
        ).json()
        parent_id = parent["id"]

        # 创建回复
        resp = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "回复内容", "parent_id": parent_id},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["parent_id"] == parent_id

    def test_create_annotation_no_note(self, client, headers):
        """在不存在的笔记上创建备注 → 404"""
        resp = client.post(
            "/api/notes/99999/annotations",
            json={"content": "测试"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_create_annotation_empty_content(self, client, headers, note_id):
        """空内容创建备注 → 422"""
        resp = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_list_annotations_empty(self, client, headers, note_id):
        """无备注时返回空列表"""
        resp = client.get(
            f"/api/notes/{note_id}/annotations",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_annotations_flat(self, client, headers, note_id):
        """有多个备注时返回扁平列表"""
        for i in range(3):
            client.post(
                f"/api/notes/{note_id}/annotations",
                json={"content": f"备注 {i}"},
                headers=headers,
            )
        resp = client.get(
            f"/api/notes/{note_id}/annotations",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_list_annotations_tree(self, client, headers, note_id):
        """备注和回复应构建为树形结构"""
        # 顶级备注
        p1 = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "顶级 A"},
            headers=headers,
        ).json()
        p2 = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "顶级 B"},
            headers=headers,
        ).json()

        # 回复 p1
        client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "回复 A1", "parent_id": p1["id"]},
            headers=headers,
        )
        client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "回复 A2", "parent_id": p1["id"]},
            headers=headers,
        )

        resp = client.get(
            f"/api/notes/{note_id}/annotations",
            headers=headers,
        )
        data = resp.json()
        assert len(data) == 2  # 2 个顶级

        # 找到顶级 A
        a = [d for d in data if d["content"] == "顶级 A"][0]
        assert len(a["replies"]) == 2  # 有 2 个回复
        assert a["replies"][0]["content"].startswith("回复 A")

    def test_delete_annotation(self, client, headers, note_id):
        """删除备注 → 返回 200"""
        ann = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "待删除"},
            headers=headers,
        ).json()

        resp = client.delete(f"/api/annotations/{ann['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_nonexistent_annotation(self, client, headers):
        """删除不存在的备注 → 404"""
        resp = client.delete("/api/annotations/99999", headers=headers)
        assert resp.status_code == 404

    def test_delete_cascade_replies(self, client, headers, note_id):
        """删除顶级备注应级联删除所有回复"""
        parent = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "父备注"},
            headers=headers,
        ).json()

        child = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "子回复", "parent_id": parent["id"]},
            headers=headers,
        ).json()

        # 删除父备注
        client.delete(f"/api/annotations/{parent['id']}", headers=headers)

        # 验证子备注也被删除
        resp = client.get(f"/api/notes/{note_id}/annotations", headers=headers)
        assert len(resp.json()) == 0

    def test_create_annotation_no_auth(self, client, note_id):
        """未认证创建备注 → 401"""
        resp = client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "测试"},
        )
        assert resp.status_code == 401


class TestNotesListFilter:
    """测试笔记列表过滤备注"""

    def test_list_default_excludes_annotations(self, client, headers, note_id):
        """默认 GET /api/notes 不应包含 type='annotation' 的记录"""
        # 给笔记加一条备注
        client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "测试备注"},
            headers=headers,
        )

        resp = client.get("/api/notes", headers=headers)
        assert resp.status_code == 200
        for note in resp.json():
            assert note.get("type", "note") == "note", "列表不应包含备注"

    def test_list_type_all_includes_annotations(self, client, headers, note_id):
        """type=all 应包含备注"""
        client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "测试备注"},
            headers=headers,
        )

        resp = client.get("/api/notes?type=all", headers=headers)
        assert resp.status_code == 200
        types = [n.get("type", "note") for n in resp.json()]
        assert "annotation" in types


class TestNoteDetailFields:
    """测试笔记详情新增字段"""

    def test_note_detail_has_type(self, client, headers, note_id):
        """GET /api/notes/{id} 应返回 type 字段"""
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        data = resp.json()
        assert "type" in data
        assert data["type"] == "note"

    def test_note_detail_has_annotation_count(self, client, headers, note_id):
        """GET /api/notes/{id} 应返回 annotation_count"""
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        data = resp.json()
        assert "annotation_count" in data
        assert data["annotation_count"] == 0

        # 加一条备注
        client.post(
            f"/api/notes/{note_id}/annotations",
            json={"content": "测试"},
            headers=headers,
        )
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        assert resp.json()["annotation_count"] == 1

    def test_note_detail_has_ai_summary(self, client, headers, note_id):
        """GET /api/notes/{id} 应返回 ai_summary 字段（可为空）"""
        resp = client.get(f"/api/notes/{note_id}", headers=headers)
        data = resp.json()
        assert "ai_summary" in data
