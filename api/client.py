"""
MemoMind API 客户端
"""

import os
from pathlib import Path
from typing import List, Optional, Dict

from ..core.database import Database
from ..core.search_service import SearchService
from ..core.version_service import VersionService
from ..core.tag_service import TagService
from ..core.link_service import LinkService
from ..core.export_service import ExportService
from ..core.import_service import ImportService
from ..core.workspace_service import WorkspaceService


class NotesAPI:
    """笔记 API"""
    
    def __init__(self, db: Database, search: SearchService, versions: VersionService):
        self.db = db
        self._search = search
        self.versions = versions
    
    def create(self, title: str, content: str, tags: List[str] = None) -> int:
        """创建笔记"""
        import json
        cursor = self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, (title, content, json.dumps(tags or [])))
        self.db.commit()
        return cursor.lastrowid
    
    def get(self, note_id: int) -> Optional[Dict]:
        """获取笔记详情"""
        cursor = self.db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update(self, note_id: int, title: str = None, content: str = None, tags: List[str] = None) -> bool:
        """更新笔记"""
        import json
        updates = []
        params = []
        
        if title:
            updates.append("title = ?")
            params.append(title)
        if content:
            updates.append("content = ?")
            params.append(content)
        if tags:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        
        if not updates:
            return False
        
        params.append(note_id)
        self.db.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params)
        self.db.commit()
        return True
    
    def delete(self, note_id: int) -> bool:
        """删除笔记"""
        self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.db.commit()
        return True
    
    def search(self, query: str, tags: List[str] = None, limit: int = 20) -> List[Dict]:
        """搜索笔记"""
        results = self._search.search(query, tags=tags, limit=limit)
        return [{
            'note': {
                'id': r.note.id,
                'title': r.note.title,
                'content': r.note.content,
                'tags': r.note.tags,
                'created_at': r.note.created_at,
                'updated_at': r.note.updated_at
            },
            'score': r.score,
            'highlights': r.highlights
        } for r in results]
    
    def list(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出所有笔记"""
        cursor = self.db.execute("""
            SELECT * FROM notes ORDER BY updated_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_versions(self, note_id: int) -> List[Dict]:
        """获取版本历史"""
        versions = self.versions.get_versions(note_id)
        return [v.__dict__ for v in versions]
    
    def restore_version(self, version_id: int) -> Optional[Dict]:
        """恢复版本"""
        return self.versions.restore_version(version_id)


class WorkspacesAPI:
    """工作区 API"""
    
    def __init__(self, workspaces: WorkspaceService):
        self.workspaces = workspaces
    
    def create(self, name: str, description: str = '') -> int:
        """创建工作区"""
        return self.workspaces.create_workspace(name, description)
    
    def get(self, workspace_id: int) -> Optional[Dict]:
        """获取工作区详情"""
        ws = self.workspaces.get_workspace(workspace_id)
        return ws.to_dict() if ws else None
    
    def list(self) -> List[Dict]:
        """列出所有工作区"""
        workspaces = self.workspaces.list_workspaces()
        return [w.to_dict() for w in workspaces]
    
    def update(self, workspace_id: int, name: str = None, description: str = None) -> bool:
        """更新工作区"""
        return self.workspaces.update_workspace(workspace_id, name, description)
    
    def delete(self, workspace_id: int) -> bool:
        """删除工作区"""
        return self.workspaces.delete_workspace(workspace_id)
    
    def move_note(self, note_id: int, target_workspace_id: int) -> bool:
        """移动笔记到另一个工作区"""
        return self.workspaces.move_note_to_workspace(note_id, target_workspace_id)
    
    def stats(self, workspace_id: int) -> Dict:
        """获取工作区统计"""
        return self.workspaces.get_workspace_stats(workspace_id)
    
    def search(self, query: str, workspace_ids: List[int] = None, limit: int = 20) -> List[Dict]:
        """跨工作区搜索"""
        return self.workspaces.search_across_workspaces(query, workspace_ids, limit)


class TagsAPI:
    """标签 API"""
    
    def __init__(self, tags: TagService):
        self.tags = tags
    
    def create(self, name: str, parent_id: int = None) -> int:
        """创建标签"""
        return self.tags.create_tag(name, parent_id)
    
    def get(self, tag_id: int) -> Optional[Dict]:
        """获取标签详情"""
        tag = self.tags.get_tag(tag_id)
        return tag.__dict__ if tag else None
    
    def list(self) -> List[Dict]:
        """列出所有标签"""
        tags = self.tags.get_all_tags()
        return [t.__dict__ for t in tags]
    
    def get_tree(self) -> List[Dict]:
        """获取标签树"""
        return self.tags.get_tag_tree()
    
    def delete(self, tag_id: int) -> bool:
        """删除标签"""
        return self.tags.delete_tag(tag_id)
    
    def suggest(self, prefix: str, limit: int = 10) -> List[Dict]:
        """标签建议"""
        tags = self.tags.suggest_tags(prefix, limit)
        return [t.__dict__ for t in tags]


class LinksAPI:
    """链接 API"""
    
    def __init__(self, links: LinkService):
        self.links = links
    
    def create(self, source_id: int, target_id: int) -> bool:
        """创建链接"""
        try:
            self.links.db.execute("""
                INSERT OR REPLACE INTO note_links (source_note_id, target_note_id)
                VALUES (?, ?)
            """, (source_id, target_id))
            self.links.db.commit()
            return True
        except Exception:
            return False
    
    def get_outgoing(self, note_id: int) -> List[Dict]:
        """获取出链"""
        links = self.links.get_outgoing_links(note_id)
        return [l.__dict__ for l in links]
    
    def get_incoming(self, note_id: int) -> List[Dict]:
        """获取入链（反向链接）"""
        links = self.links.get_incoming_links(note_id)
        return [l.__dict__ for l in links]
    
    def get_graph(self) -> Dict:
        """获取链接图谱"""
        return self.links.get_link_graph()
    
    def get_broken(self) -> List[Dict]:
        """获取断链"""
        return self.links.get_broken_links()
    
    def get_orphaned(self) -> List[Dict]:
        """获取孤立笔记"""
        return self.links.get_orphaned_notes()


class VersionsAPI:
    """版本 API"""
    
    def __init__(self, versions: VersionService):
        self.versions = versions
    
    def save(self, note_id: int, title: str, content: str, tags: List[str], change_summary: str = None) -> int:
        """保存版本"""
        return self.versions.save_version(note_id, title, content, tags, change_summary)
    
    def get(self, version_id: int) -> Optional[Dict]:
        """获取版本详情"""
        version = self.versions.get_version(version_id)
        return version.__dict__ if version else None
    
    def list(self, note_id: int, limit: int = 10) -> List[Dict]:
        """列出版本"""
        versions = self.versions.get_versions(note_id, limit)
        return [v.__dict__ for v in versions]
    
    def restore(self, version_id: int) -> Optional[Dict]:
        """恢复版本"""
        return self.versions.restore_version(version_id)
    
    def tag(self, version_id: int, tag_name: str) -> bool:
        """标记版本"""
        return self.versions.tag_version(version_id, tag_name)
    
    def cleanup(self, note_id: int, keep_count: int = 10) -> int:
        """清理旧版本"""
        return self.versions.cleanup_versions(note_id, keep_count)


class MemoMind:
    """
    MemoMind 主 API 类
    
    用法：
        from memomind import MemoMind
        
        client = MemoMind(db_path="~/memomind.db")
        
        # 创建笔记
        note_id = client.notes.create("标题", "内容", tags=["tag1"])
        
        # 搜索
        results = client.notes.search("关键词")
        
        # 标签
        client.tags.create("标签名")
        
        # 链接
        client.links.create(source_id, target_id)
    """
    
    def __init__(self, db_path: str = "~/memomind.db"):
        """
        初始化 MemoMind 客户端
        
        Args:
            db_path: 数据库路径
        """
        # 展开路径
        db_path = os.path.expanduser(db_path)
        
        # 创建数据库连接
        self.db = Database(db_path)
        
        # 初始化服务
        search = SearchService(self.db)
        versions = VersionService(self.db)
        tags = TagService(self.db)
        links = LinkService(self.db)
        export = ExportService(self.db)
        importer = ImportService(self.db)
        workspaces = WorkspaceService(self.db)
        
        # 初始化 API
        self.notes = NotesAPI(self.db, search, versions)
        self.tags = TagsAPI(tags)
        self.links = LinksAPI(links)
        self.versions = VersionsAPI(versions)
        self.export = export
        self.importer = importer
        self.workspaces = WorkspacesAPI(workspaces)
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
