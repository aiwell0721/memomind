"""
MemoMind 工作区服务测试 - PR-012
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.workspace_service import WorkspaceService, Workspace


class TestWorkspaceService:
    """工作区服务基础测试"""
    
    def setup_method(self):
        self.db = Database(":memory:")
        self.ws = WorkspaceService(self.db)
    
    def teardown_method(self):
        self.db.close()
    
    def test_default_workspace_exists(self):
        """测试默认工作区自动创建"""
        ws = self.ws.get_workspace(1)
        assert ws is not None
        assert ws.name == "默认工作区"
    
    def test_create_workspace(self):
        """创建工作区"""
        ws_id = self.ws.create_workspace("研发团队", "研发知识库")
        assert ws_id > 1  # ID 1 是默认工作区
        
        ws = self.ws.get_workspace(ws_id)
        assert ws.name == "研发团队"
        assert ws.description == "研发知识库"
        assert ws.created_at is not None
    
    def test_create_workspace_unique_name(self):
        """工作区名称唯一性"""
        self.ws.create_workspace("测试区")
        with pytest.raises(Exception):
            self.ws.create_workspace("测试区")
    
    def test_get_workspace_by_name(self):
        """根据名称获取工作区"""
        self.ws.create_workspace("产品部", "产品知识库")
        ws = self.ws.get_workspace_by_name("产品部")
        assert ws is not None
        assert ws.description == "产品知识库"
    
    def test_get_workspace_not_found(self):
        """获取不存在的工作区"""
        ws = self.ws.get_workspace(999)
        assert ws is None
    
    def test_list_workspaces(self):
        """列出所有工作区"""
        self.ws.create_workspace("工作区A")
        self.ws.create_workspace("工作区B")
        self.ws.create_workspace("工作区C")
        
        workspaces = self.ws.list_workspaces()
        assert len(workspaces) == 4  # 默认 + 3 个新
    
    def test_list_workspaces_with_note_count(self):
        """工作区列表包含笔记计数"""
        ws_id = self.ws.create_workspace("计数测试")
        
        # 添加笔记
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('笔记1', '内容1', ?)
        """, (ws_id,))
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('笔记2', '内容2', ?)
        """, (ws_id,))
        self.db.commit()
        
        workspaces = self.ws.list_workspaces()
        target = [w for w in workspaces if w.id == ws_id][0]
        assert target.note_count == 2
    
    def test_update_workspace(self):
        """更新工作区信息"""
        ws_id = self.ws.create_workspace("旧名称", "旧描述")
        self.ws.update_workspace(ws_id, name="新名称", description="新描述")
        
        ws = self.ws.get_workspace(ws_id)
        assert ws.name == "新名称"
        assert ws.description == "新描述"
    
    def test_update_workspace_noop(self):
        """更新工作区（无变更）"""
        ws_id = self.ws.create_workspace("不变更")
        result = self.ws.update_workspace(ws_id)
        assert result is False
    
    def test_delete_workspace(self):
        """删除工作区"""
        ws_id = self.ws.create_workspace("待删除")
        self.ws.delete_workspace(ws_id)
        
        ws = self.ws.get_workspace(ws_id)
        assert ws is None
    
    def test_delete_default_workspace_raises(self):
        """不能删除默认工作区"""
        with pytest.raises(ValueError, match="不能删除默认工作区"):
            self.ws.delete_workspace(1)
    
    def test_delete_workspace_cascades_notes(self):
        """删除工作区级联删除笔记"""
        ws_id = self.ws.create_workspace("级联删除测试")
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('笔记1', '内容1', ?)
        """, (ws_id,))
        self.db.commit()
        
        self.ws.delete_workspace(ws_id)
        
        cursor = self.db.execute("SELECT COUNT(*) FROM notes WHERE workspace_id = ?", (ws_id,))
        assert cursor.fetchone()[0] == 0
    
    def test_move_note_to_workspace(self):
        """移动笔记到另一个工作区"""
        ws1_id = self.ws.create_workspace("工作区1")
        ws2_id = self.ws.create_workspace("工作区2")
        
        cursor = self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('移动笔记', '内容', ?)
        """, (ws1_id,))
        note_id = cursor.lastrowid
        self.db.commit()
        
        result = self.ws.move_note_to_workspace(note_id, ws2_id)
        assert result is True
        
        cursor = self.db.execute("SELECT workspace_id FROM notes WHERE id = ?", (note_id,))
        assert cursor.fetchone()['workspace_id'] == ws2_id
    
    def test_move_note_to_nonexistent_workspace(self):
        """移动笔记到不存在的工作区"""
        cursor = self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('笔记', '内容', 1)
        """)
        note_id = cursor.lastrowid
        self.db.commit()
        
        result = self.ws.move_note_to_workspace(note_id, 999)
        assert result is False
    
    def test_workspace_stats(self):
        """工作区统计"""
        ws_id = self.ws.create_workspace("统计测试")
        
        self.db.execute("""
            INSERT INTO notes (title, content, tags, workspace_id)
            VALUES ('笔记1', '内容1', '["tag1"]', ?)
        """, (ws_id,))
        self.db.execute("""
            INSERT INTO notes (title, content, tags, workspace_id)
            VALUES ('笔记2', '内容2', '[]', ?)
        """, (ws_id,))
        self.db.commit()
        
        stats = self.ws.get_workspace_stats(ws_id)
        assert stats['note_count'] == 2
        assert stats['tagged_count'] == 1
    
    def test_search_across_workspaces(self):
        """跨工作区搜索"""
        ws1 = self.ws.create_workspace("工作区A")
        ws2 = self.ws.create_workspace("工作区B")
        
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('test note alpha', 'some content here', ?)
        """, (ws1,))
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('test note beta', 'other content here', ?)
        """, (ws2,))
        self.db.commit()
        
        # 全部搜索
        results = self.ws.search_across_workspaces("test")
        assert len(results) == 2
        workspace_names = {r['workspace_name'] for r in results}
        assert workspace_names == {"工作区A", "工作区B"}
        
        # 指定工作区搜索
        results = self.ws.search_across_workspaces("test", workspace_ids=[ws1])
        assert len(results) == 1
        assert results[0]['workspace_name'] == "工作区A"
        
        # 指定另一个工作区
        results = self.ws.search_across_workspaces("test", workspace_ids=[ws2])
        assert len(results) == 1
        assert results[0]['workspace_name'] == "工作区B"


class TestWorkspaceToDict:
    """Workspace 模型转换测试"""
    
    def test_to_dict(self):
        ws = Workspace(id=1, name="测试", description="描述", created_at="2026-04-24")
        d = ws.to_dict()
        assert d['id'] == 1
        assert d['name'] == "测试"
        assert d['description'] == "描述"
    
    def test_from_row(self):
        class FakeRow:
            def __getitem__(self, key):
                return {'id': 5, 'name': '行测试', 'description': '行描述', 'created_at': '2026-01-01'}[key]
            def keys(self):
                return ['id', 'name', 'description', 'created_at']
        
        ws = Workspace.from_row(FakeRow())
        assert ws.id == 5
        assert ws.name == "行测试"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
