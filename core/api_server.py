"""
MemoMind REST API 服务器 - PR-016
基于 FastAPI 的 RESTful API，支持 JWT 认证
"""

import os
import secrets
import time
import sys
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Server start time for uptime tracking
_SERVER_START = time.time()

from fastapi import FastAPI, HTTPException, Query, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from .database import Database
from .search_service import SearchService
from .version_service import VersionService
from .tag_service import TagService
from .link_service import LinkService
from .export_service import ExportService
from .import_service import ImportService
from .workspace_service import WorkspaceService
from .user_service import UserService
from .activity_service import ActivityService
from .conflict_service import ConflictService
from .backup_service import BackupService
from .collaboration_service import CollaborationService
from .ai_provider import create_provider


# ==================== Pydantic 模型 ====================

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    tags: Optional[List[str]] = []
    workspace_id: Optional[int] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None

class NoteSearch(BaseModel):
    query: str
    tags: Optional[List[str]] = None
    limit: int = Field(20, ge=1, le=100)
    workspace_id: Optional[int] = None

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[int] = None

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    display_name: str = ""

class UserUpdate(BaseModel):
    display_name: Optional[str] = None

class MemberAdd(BaseModel):
    user_id: int
    role: str = "viewer"

class MemberRoleUpdate(BaseModel):
    role: str

class LinkCreate(BaseModel):
    source_note_id: int
    target_note_id: int

class ActivityLogCreate(BaseModel):
    action: str
    user_id: Optional[int] = None
    workspace_id: Optional[int] = None
    note_id: Optional[int] = None
    details: Optional[dict] = None

class ActivityFilter(BaseModel):
    workspace_id: Optional[int] = None
    user_id: Optional[int] = None
    note_id: Optional[int] = None
    action: Optional[str] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)

class ConflictResolve(BaseModel):
    strategy: str  # latest-wins / manual / merge
    use_ours: Optional[bool] = True  # for latest-wins
    resolved_content: Optional[str] = None  # for manual

class BackupCreate(BaseModel):
    description: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ErrorResponse(BaseModel):
    detail: str


# ==================== AI 配置模型 ====================

class AiConfigModel(BaseModel):
    provider: str = Field(default="local", pattern=r"^(local|openai|anthropic)$")
    api_key: str = Field(default="")
    model: str = Field(default="")
    embed_model: str = Field(default="")


# ==================== 认证 ====================

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError


def resolve_secret_key(env: Optional[dict] = None) -> str:
    """读取 JWT 签名密钥。

    若环境变量 MEMOMIND_SECRET_KEY 未设，回退到 secrets.token_hex(32) 自动生成，
    同时发出 UserWarning——因为每次进程重启会换密钥，旧 token 集体失效。
    生产环境必须显式设置环境变量。
    """
    import warnings
    e = os.environ if env is None else env
    key = e.get("MEMOMIND_SECRET_KEY")
    if key:
        return key
    warnings.warn(
        "MEMOMIND_SECRET_KEY 未设置，已自动生成随机密钥。"
        "进程重启后所有已发 JWT 将立即失效，生产环境必须在 .env 或部署平台显式设置。",
        UserWarning,
        stacklevel=2,
    )
    return secrets.token_hex(32)


SECRET_KEY = resolve_secret_key()
TOKEN_EXPIRE_HOURS = int(os.environ.get("MEMOMIND_TOKEN_EXPIRE", 24))
ALGORITHM = "HS256"

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """验证 JWT Token"""
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效 Token"
            )
        return {"username": username}
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效 Token"
        )


def generate_token(username: str) -> str:
    """生成 JWT Token"""
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ==================== 应用初始化 ====================

def create_app(db_path: str = "~/memomind.db") -> FastAPI:
    """
    创建 FastAPI 应用
    
    Args:
        db_path: 数据库路径
    """
    db_path = os.path.expanduser(db_path)
    
    app = FastAPI(
        title="MemoMind API",
        description="MemoMind 团队知识库 REST API",
        version="3.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # ==================== 安全中间件 ====================
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("MEMOMIND_CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 信任主机
    allowed_hosts = os.environ.get("MEMOMIND_ALLOWED_HOSTS", "")
    if allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[h.strip() for h in allowed_hosts.split(",")]
        )
    
    # 速率限制中间件
    class RateLimiter(BaseHTTPMiddleware):
        """简单内存速率限制（生产环境建议使用 Redis）"""
        
        def __init__(self, app, max_requests: int = 60, window: int = 60):
            super().__init__(app)
            self.max_requests = max_requests
            self.window = window
            self.requests: Dict[str, list] = {}
        
        async def dispatch(self, request: Request, call_next):
            client_ip = request.client.host if request.client else "unknown"
            now = datetime.now().timestamp()
            
            if client_ip not in self.requests:
                self.requests[client_ip] = []
            
            # 清理过期记录
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if now - t < self.window
            ]
            
            if len(self.requests[client_ip]) >= self.max_requests:
                return await call_next(Request(
                    scope={
                        **request.scope,
                        "type": "http",
                        "method": "GET",
                        "path": "/api/health",
                        "query_string": b"",
                        "headers": [],
                    }
                ))  # Return 429
            
            self.requests[client_ip].append(now)
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, self.max_requests - len(self.requests[client_ip]))
            )
            return response
    
    # 启用速率限制（可通过环境变量关闭）
    if os.environ.get("MEMOMIND_RATE_LIMIT", "true").lower() != "false":
        rate_limit = int(os.environ.get("MEMOMIND_RATE_LIMIT_MAX", "100"))
        rate_window = int(os.environ.get("MEMOMIND_RATE_LIMIT_WINDOW", "60"))
        app.add_middleware(RateLimiter, max_requests=rate_limit, window=rate_window)
    
    # 安全头中间件
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Cache-Control"] = "no-store"
        return response
    
    # 数据库连接（应用级）
    db = Database(db_path)

    # 历史数据回填：旧版本由 SQLite 触发器写入未分词的 FTS5 索引，
    # 启动时一次性按 jieba 分词重建，确保中文搜索可用。
    try:
        reindexed = db.reindex_notes()
        if reindexed:
            print(f"Reindexed {reindexed} notes to FTS5")
    except Exception as e:
        print(f"Reindex notes warning: {e}")

    # 初始化服务
    search = SearchService(db)
    versions = VersionService(db)
    tags = TagService(db)
    links = LinkService(db)
    export = ExportService(db)
    importer = ImportService(db)
    workspaces = WorkspaceService(db)
    users = UserService(db)
    activity = ActivityService(db)
    conflict = ConflictService(db)
    backup = BackupService(db)
    collaboration = CollaborationService(db)
    
    # ==================== AI Provider 配置管理 ====================
    
    _config_path = os.path.join(os.path.dirname(db_path), "memomind.json")
    
    def _load_ai_config() -> dict:
        """从 JSON 配置文件读取 AI 设置"""
        if os.path.isfile(_config_path):
            try:
                import json
                with open(_config_path, "r") as f:
                    data = json.load(f)
                return data.get("ai", {})
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _save_ai_config(cfg: dict):
        """保存 AI 设置到 JSON 配置文件"""
        import json
        existing = {}
        if os.path.isfile(_config_path):
            try:
                with open(_config_path, "r") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        existing["ai"] = cfg
        with open(_config_path, "w") as f:
            json.dump(existing, f, indent=2)
    
    # 从配置文件加载并应用 AI 设置（优先于环境变量）
    _saved_cfg = _load_ai_config()
    if _saved_cfg.get("provider") and _saved_cfg.get("provider") != "local":
        # 用配置文件覆盖环境变量
        os.environ["MEMOMIND_AI_PROVIDER"] = _saved_cfg["provider"]
        if _saved_cfg.get("api_key"):
            if _saved_cfg["provider"] == "openai":
                os.environ["OPENAI_API_KEY"] = _saved_cfg["api_key"]
            elif _saved_cfg["provider"] == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = _saved_cfg["api_key"]
        if _saved_cfg.get("model"):
            if _saved_cfg["provider"] == "openai":
                os.environ["OPENAI_MODEL"] = _saved_cfg["model"]
            elif _saved_cfg["provider"] == "anthropic":
                os.environ["ANTHROPIC_MODEL"] = _saved_cfg["model"]
        if _saved_cfg.get("embed_model"):
            os.environ["OPENAI_EMBED_MODEL"] = _saved_cfg["embed_model"]
    
    ai_provider = create_provider()
    
    # ==================== 笔记 API ====================
    
    @app.get("/api/notes", response_model=list, summary="列出笔记")
    def list_notes(
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        workspace_id: Optional[int] = Query(None),
        _: dict = Depends(verify_token)
    ):
        """列出所有笔记"""
        if workspace_id:
            cursor = db.execute("""
                SELECT * FROM notes WHERE workspace_id = ?
                ORDER BY updated_at DESC LIMIT ? OFFSET ?
            """, (workspace_id, limit, offset))
        else:
            cursor = db.execute("""
                SELECT * FROM notes ORDER BY updated_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
        
        import json
        return [{
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'workspace_id': row['workspace_id'] if 'workspace_id' in row.keys() else 1,
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        } for row in cursor.fetchall()]
    
    @app.get("/api/notes/{note_id}", summary="获取笔记详情")
    def get_note(note_id: int, _: dict = Depends(verify_token)):
        """获取笔记详情"""
        cursor = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        import json
        return {
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'workspace_id': row['workspace_id'] if 'workspace_id' in row.keys() else 1,
            'created_by': row['created_by'] if 'created_by' in row.keys() else None,
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
    
    @app.post("/api/notes", status_code=status.HTTP_201_CREATED, summary="创建笔记")
    def create_note(note: NoteCreate, user: dict = Depends(verify_token)):
        """创建笔记"""
        import json
        cursor = db.execute("""
            INSERT INTO notes (title, content, tags, workspace_id)
            VALUES (?, ?, ?, ?)
        """, (note.title, note.content, json.dumps(note.tags), note.workspace_id))
        db.commit()
        
        note_id = cursor.lastrowid
        
        # 记录活动日志
        try:
            activity.log('create', note_id=note_id, details={'title': note.title})
        except Exception:
            pass
        
        return {'id': note_id, 'title': note.title}
    
    @app.put("/api/notes/{note_id}", summary="更新笔记")
    def update_note(note_id: int, note: NoteUpdate, user: dict = Depends(verify_token)):
        """更新笔记"""
        import json
        updates = []
        params = []
        
        if note.title:
            updates.append("title = ?")
            params.append(note.title)
        if note.content:
            updates.append("content = ?")
            params.append(note.content)
        if note.tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(note.tags))
        
        if not updates:
            raise HTTPException(status_code=400, detail="无更新内容")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(note_id)
        
        db.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
        
        # 更新链接关系
        try:
            links.update_note_links(note_id, note.content) if note.content else None
        except Exception:
            pass
        
        # 记录活动日志
        try:
            activity.log('update', note_id=note_id)
        except Exception:
            pass
        
        return {'id': note_id, 'updated': True}
    
    @app.delete("/api/notes/{note_id}", summary="删除笔记")
    def delete_note(note_id: int, user: dict = Depends(verify_token)):
        """删除笔记"""
        db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        db.commit()
        
        try:
            activity.log('delete', note_id=note_id)
        except Exception:
            pass
        
        return {'id': note_id, 'deleted': True}
    
    @app.post("/api/notes/search", summary="搜索笔记")
    def search_notes(params: NoteSearch, _: dict = Depends(verify_token)):
        """全文搜索笔记"""
        results = search.search(
            query=params.query,
            tags=params.tags,
            limit=params.limit
        )
        
        return [{
            'note': {
                'id': r.note.id,
                'title': r.note.title,
                'content': r.note.content[:200],
                'tags': r.note.tags,
                'workspace_id': getattr(r.note, 'workspace_id', 1)
            },
            'score': r.score,
            'highlights': r.highlights
        } for r in results]
    
    # ==================== 标签 API ====================
    
    @app.get("/api/tags", summary="列出标签")
    def list_tags(tree: bool = False, _: dict = Depends(verify_token)):
        """列出所有标签"""
        if tree:
            return tags.get_tag_tree()
        all_tags = tags.get_all_tags()
        return [t.__dict__ for t in all_tags]
    
    @app.post("/api/tags", status_code=status.HTTP_201_CREATED, summary="创建标签")
    def create_tag(tag: TagCreate, _: dict = Depends(verify_token)):
        """创建标签"""
        tag_id = tags.create_tag(tag.name, tag.parent_id)
        return {'id': tag_id, 'name': tag.name}
    
    @app.delete("/api/tags/{tag_id}", summary="删除标签")
    def delete_tag(tag_id: int, _: dict = Depends(verify_token)):
        """删除标签"""
        tags.delete_tag(tag_id)
        return {'id': tag_id, 'deleted': True}
    
    # ==================== 链接 API ====================
    
    @app.get("/api/links/outgoing/{note_id}", summary="获取出链")
    def get_outgoing_links(note_id: int, _: dict = Depends(verify_token)):
        """获取笔记的出链"""
        link_list = links.get_outgoing_links(note_id)
        return [l.__dict__ for l in link_list]
    
    @app.get("/api/links/incoming/{note_id}", summary="获取入链")
    def get_incoming_links(note_id: int, _: dict = Depends(verify_token)):
        """获取笔记的入链（反向链接）"""
        link_list = links.get_incoming_links(note_id)
        return [l.__dict__ for l in link_list]
    
    @app.get("/api/links/graph", summary="获取链接图谱")
    def get_link_graph(_: dict = Depends(verify_token)):
        """获取链接关系图"""
        return links.get_link_graph()
    
    @app.get("/api/links/broken", summary="获取断链")
    def get_broken_links(_: dict = Depends(verify_token)):
        """获取断链列表"""
        return links.get_broken_links()
    
    @app.get("/api/links/orphaned", summary="获取孤立笔记")
    def get_orphaned_notes(_: dict = Depends(verify_token)):
        """获取孤立笔记"""
        return links.get_orphaned_notes()
    
    # ==================== 版本 API ====================
    
    @app.get("/api/notes/{note_id}/versions", summary="获取版本历史")
    def get_versions(note_id: int, limit: int = Query(20, ge=1, le=100), _: dict = Depends(verify_token)):
        """获取笔记的版本历史"""
        version_list = versions.get_versions(note_id, limit)
        return [v.__dict__ for v in version_list]
    
    @app.post("/api/notes/{note_id}/versions", status_code=status.HTTP_201_CREATED, summary="保存版本")
    def save_version(note_id: int, summary: str = "", _: dict = Depends(verify_token)):
        """保存笔记的当前版本"""
        cursor = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        import json
        version_id = versions.save_version(
            note_id=note_id,
            title=row['title'],
            content=row['content'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            change_summary=summary
        )
        return {'id': version_id, 'saved': True}
    
    @app.post("/api/versions/{version_id}/restore", summary="恢复版本")
    def restore_version(version_id: int, _: dict = Depends(verify_token)):
        """恢复到指定版本"""
        result = versions.restore_version(version_id)
        if not result:
            raise HTTPException(status_code=404, detail="版本不存在")
        return result
    
    # ==================== 工作区 API ====================
    
    @app.get("/api/workspaces", summary="列出工作区")
    def list_workspaces(_: dict = Depends(verify_token)):
        """列出所有工作区"""
        ws_list = workspaces.list_workspaces()
        return [w.to_dict() for w in ws_list]
    
    @app.get("/api/workspaces/{workspace_id}", summary="获取工作区详情")
    def get_workspace(workspace_id: int, _: dict = Depends(verify_token)):
        """获取工作区详情"""
        ws = workspaces.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="工作区不存在")
        result = ws.to_dict()
        result['stats'] = workspaces.get_workspace_stats(workspace_id)
        return result
    
    @app.post("/api/workspaces", status_code=status.HTTP_201_CREATED, summary="创建工作区")
    def create_workspace(ws: WorkspaceCreate, user: dict = Depends(verify_token)):
        """创建工作区"""
        ws_id = workspaces.create_workspace(ws.name, ws.description)
        
        try:
            activity.log('workspace_create', workspace_id=ws_id, details={'name': ws.name})
        except Exception:
            pass
        
        return {'id': ws_id, 'name': ws.name}
    
    @app.put("/api/workspaces/{workspace_id}", summary="更新工作区")
    def update_workspace(workspace_id: int, ws: WorkspaceUpdate, _: dict = Depends(verify_token)):
        """更新工作区"""
        workspaces.update_workspace(workspace_id, ws.name, ws.description)
        return {'id': workspace_id, 'updated': True}
    
    @app.delete("/api/workspaces/{workspace_id}", summary="删除工作区")
    def delete_workspace(workspace_id: int, _: dict = Depends(verify_token)):
        """删除工作区"""
        workspaces.delete_workspace(workspace_id)
        return {'id': workspace_id, 'deleted': True}
    
    @app.post("/api/notes/{note_id}/move", summary="移动笔记")
    def move_note(note_id: int, target_workspace_id: int = Query(...), _: dict = Depends(verify_token)):
        """将笔记移动到另一个工作区"""
        result = workspaces.move_note_to_workspace(note_id, target_workspace_id)
        if not result:
            raise HTTPException(status_code=400, detail="移动失败")
        return {'note_id': note_id, 'moved_to': target_workspace_id}
    
    @app.post("/api/workspaces/search", summary="跨工作区搜索")
    def search_across_workspaces(
        query: str,
        workspace_ids: Optional[List[int]] = None,
        limit: int = Query(20, ge=1, le=100),
        _: dict = Depends(verify_token)
    ):
        """跨工作区搜索"""
        return workspaces.search_across_workspaces(query, workspace_ids, limit)
    
    # ==================== 用户 API ====================
    
    @app.get("/api/users", summary="列出用户")
    def list_users(_: dict = Depends(verify_token)):
        """列出所有用户"""
        user_list = users.list_users()
        return [u.to_dict() for u in user_list]
    
    @app.get("/api/users/{user_id}", summary="获取用户详情")
    def get_user(user_id: int, _: dict = Depends(verify_token)):
        """获取用户详情"""
        user = users.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user.to_dict()
    
    @app.post("/api/users", status_code=status.HTTP_201_CREATED, summary="注册用户")
    def create_user(user: UserCreate):
        """注册用户（无需认证）"""
        try:
            user_id = users.create_user(user.username, user.password, user.display_name)
            return {'id': user_id, 'username': user.username}
        except Exception as e:
            raise HTTPException(status_code=409, detail=str(e))
    
    @app.put("/api/users/{user_id}", summary="更新用户")
    def update_user(user_id: int, user: UserUpdate, _: dict = Depends(verify_token)):
        """更新用户信息"""
        users.update_user(user_id, user.display_name)
        return {'id': user_id, 'updated': True}
    
    @app.delete("/api/users/{user_id}", summary="删除用户")
    def delete_user(user_id: int, _: dict = Depends(verify_token)):
        """删除用户"""
        users.delete_user(user_id)
        return {'id': user_id, 'deleted': True}
    
    # ==================== 成员 API ====================
    
    @app.get("/api/workspaces/{workspace_id}/members", summary="列出成员")
    def list_members(workspace_id: int, _: dict = Depends(verify_token)):
        """列出工作区所有成员"""
        return users.list_members(workspace_id)
    
    @app.post("/api/workspaces/{workspace_id}/members", status_code=status.HTTP_201_CREATED, summary="添加成员")
    def add_member(workspace_id: int, member: MemberAdd, _: dict = Depends(verify_token)):
        """添加工作区成员"""
        try:
            users.add_member(workspace_id, member.user_id, member.role)
            return {'workspace_id': workspace_id, 'user_id': member.user_id, 'role': member.role}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.delete("/api/workspaces/{workspace_id}/members/{user_id}", summary="移除成员")
    def remove_member(workspace_id: int, user_id: int, _: dict = Depends(verify_token)):
        """移除工作区成员"""
        users.remove_member(workspace_id, user_id)
        return {'workspace_id': workspace_id, 'user_id': user_id, 'removed': True}
    
    @app.put("/api/workspaces/{workspace_id}/members/{user_id}/role", summary="更新角色")
    def update_member_role(workspace_id: int, user_id: int, role: MemberRoleUpdate, _: dict = Depends(verify_token)):
        """更新成员角色"""
        try:
            users.update_member_role(workspace_id, user_id, role.role)
            return {'workspace_id': workspace_id, 'user_id': user_id, 'role': role.role}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/users/{user_id}/workspaces", summary="用户工作区")
    def get_user_workspaces(user_id: int, _: dict = Depends(verify_token)):
        """获取用户所属的所有工作区"""
        return users.get_user_workspaces(user_id)
    
    # ==================== 活动日志 API ====================
    
    @app.get("/api/activity", summary="获取活动时间线")
    def get_activity(
        workspace_id: Optional[int] = Query(None),
        user_id: Optional[int] = Query(None),
        note_id: Optional[int] = Query(None),
        action: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        _: dict = Depends(verify_token)
    ):
        """获取活动时间线（支持过滤）"""
        return activity.get_timeline(
            workspace_id=workspace_id,
            user_id=user_id,
            note_id=note_id,
            action=action,
            limit=limit,
            offset=offset
        )
    
    @app.get("/api/notes/{note_id}/activity", summary="笔记操作历史")
    def get_note_activity(note_id: int, limit: int = Query(20, ge=1, le=100), _: dict = Depends(verify_token)):
        """获取笔记的操作历史"""
        return activity.get_note_history(note_id, limit)
    
    @app.get("/api/workspaces/{workspace_id}/activity", summary="工作区活动")
    def get_workspace_activity(workspace_id: int, limit: int = Query(50, ge=1, le=200), _: dict = Depends(verify_token)):
        """获取工作区的活动记录"""
        return activity.get_workspace_activity(workspace_id, limit)
    
    @app.get("/api/users/{user_id}/activity", summary="用户活动")
    def get_user_activity(user_id: int, limit: int = Query(50, ge=1, le=200), _: dict = Depends(verify_token)):
        """获取用户的活动记录"""
        return activity.get_user_activity(user_id, limit)
    
    @app.get("/api/workspaces/{workspace_id}/activity/stats", summary="活动统计")
    def get_activity_stats(workspace_id: int, _: dict = Depends(verify_token)):
        """获取工作区的活动统计"""
        return activity.count_by_action(workspace_id)
    
    # ==================== 冲突 API ====================
    
    @app.get("/api/notes/{note_id}/conflicts", summary="获取冲突历史")
    def get_note_conflicts(note_id: int, _: dict = Depends(verify_token)):
        """获取笔记的冲突历史"""
        return conflict.get_conflict_history(note_id)
    
    @app.get("/api/conflicts/unresolved", summary="获取未解决冲突")
    def get_unresolved_conflicts(note_id: Optional[int] = None, _: dict = Depends(verify_token)):
        """获取未解决的冲突"""
        return conflict.get_unresolved(note_id)
    
    @app.get("/api/conflicts/stats", summary="冲突统计")
    def get_conflict_stats(_: dict = Depends(verify_token)):
        """获取冲突统计"""
        return conflict.get_conflict_stats()
    
    @app.post("/api/conflicts/{conflict_id}/resolve", summary="解决冲突")
    def resolve_conflict(conflict_id: int, resolve: ConflictResolve, _: dict = Depends(verify_token)):
        """解决冲突"""
        try:
            if resolve.strategy == 'latest-wins':
                resolved = conflict.resolve_latest_wins(conflict_id, resolve.use_ours)
            elif resolve.strategy == 'merge':
                resolved = conflict.resolve_three_way_merge(conflict_id)
            elif resolve.strategy == 'manual':
                if not resolve.resolved_content:
                    raise HTTPException(status_code=400, detail="手动解决需要提供 resolved_content")
                conflict.resolve_manual(conflict_id, resolve.resolved_content)
                resolved = resolve.resolved_content
            else:
                raise HTTPException(status_code=400, detail=f"无效策略: {resolve.strategy}")
            
            return {'conflict_id': conflict_id, 'resolved': True, 'content': resolved}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    # ==================== 备份 API ====================
    
    @app.post("/api/backups", status_code=status.HTTP_201_CREATED, summary="创建备份")
    def create_backup(params: BackupCreate, _: dict = Depends(verify_token)):
        """创建数据库备份"""
        try:
            result = backup.create_backup(params.description)
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/backups", summary="列出备份")
    def list_backups(limit: int = Query(50, ge=1, le=200), _: dict = Depends(verify_token)):
        """列出所有备份"""
        backup_list = backup.list_backups(limit)
        return [b.to_dict() for b in backup_list]
    
    @app.get("/api/backups/stats", summary="备份统计")
    def get_backup_stats(_: dict = Depends(verify_token)):
        """获取备份统计"""
        return backup.get_backup_stats()
    
    @app.delete("/api/backups/{backup_id}", summary="删除备份")
    def delete_backup(backup_id: int, _: dict = Depends(verify_token)):
        """删除备份"""
        backup.delete_backup(backup_id)
        return {'id': backup_id, 'deleted': True}
    
    @app.post("/api/backups/{backup_id}/restore", summary="恢复备份")
    def restore_backup(backup_id: int, _: dict = Depends(verify_token)):
        """从备份恢复数据库"""
        try:
            backup.restore_backup(backup_id)
            return {'backup_id': backup_id, 'restored': True}
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @app.post("/api/backups/export", summary="导出 JSON")
    def export_json(output_path: Optional[str] = None, _: dict = Depends(verify_token)):
        """导出所有数据为 JSON"""
        path = backup.export_to_json(output_path)
        return {'path': path, 'exported': True}
    
    @app.post("/api/backups/cleanup", summary="清理旧备份")
    def cleanup_backups(keep_count: int = Query(10, ge=1, le=100), _: dict = Depends(verify_token)):
        """清理旧备份（保留最近 N 个）"""
        deleted = backup.cleanup_old_backups(keep_count)
        return {'deleted': deleted, 'kept': keep_count}
    
    # ==================== AI 设置 API ====================
    
    @app.get("/api/settings/ai", summary="获取 AI 配置")
    def get_ai_config(_: dict = Depends(verify_token)):
        """返回当前 AI 配置（不含 api_key）"""
        cfg = _load_ai_config()
        return {
            "provider": cfg.get("provider", "local"),
            "has_key": bool(cfg.get("api_key") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")),
            "model": cfg.get("model", ""),
            "embed_model": cfg.get("embed_model", ""),
        }
    
    @app.put("/api/settings/ai", summary="保存 AI 配置")
    def save_ai_config(cfg: AiConfigModel, _: dict = Depends(verify_token)):
        """保存 AI 配置并立即生效"""
        new_cfg = {
            "provider": cfg.provider,
            "api_key": cfg.api_key,
            "model": cfg.model,
            "embed_model": cfg.embed_model,
        }
        # 保留现有 Key（如用户未输入新 Key）
        if not cfg.api_key:
            existing = _load_ai_config()
            new_cfg["api_key"] = existing.get("api_key", "")
        _save_ai_config(new_cfg)
        
        # 立即生效：更新环境变量 + 重建 provider
        os.environ["MEMOMIND_AI_PROVIDER"] = cfg.provider
        if cfg.provider == "openai":
            if cfg.api_key:
                os.environ["OPENAI_API_KEY"] = cfg.api_key
            if cfg.model:
                os.environ["OPENAI_MODEL"] = cfg.model
            if cfg.embed_model:
                os.environ["OPENAI_EMBED_MODEL"] = cfg.embed_model
        elif cfg.provider == "anthropic":
            if cfg.api_key:
                os.environ["ANTHROPIC_API_KEY"] = cfg.api_key
            if cfg.model:
                os.environ["ANTHROPIC_MODEL"] = cfg.model
        
        # 重新创建 provider
        nonlocal ai_provider
        ai_provider = create_provider()
        
        return {"status": "ok", "provider": cfg.provider}
    
    # ==================== 认证 API ====================
    
    @app.post("/api/auth/login", response_model=TokenResponse, summary="登录")
    def login(req: LoginRequest):
        """用户登录，验证密码后返回 JWT Token"""
        user = users.verify_password(req.username, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = generate_token(req.username)
        return TokenResponse(access_token=token)
    
    @app.get("/api/auth/me", summary="获取当前用户")
    def get_current_user(user: dict = Depends(verify_token)):
        """获取当前用户信息"""
        return user
    
    # ==================== 健康检查 ====================
    
    @app.get("/api/health", summary="健康检查")
    def health_check():
        """健康检查端点（无需认证）"""
        # Database connectivity check
        db_status = "ok"
        db_stats = {}
        try:
            # Basic DB query
            cursor = db.execute("SELECT COUNT(*) as count FROM notes")
            row = cursor.fetchone()
            note_count = row['count'] if row else 0
            
            cursor = db.execute("SELECT COUNT(*) as count FROM users")
            row = cursor.fetchone()
            user_count = row['count'] if row else 0
            
            cursor = db.execute("SELECT COUNT(*) as count FROM workspaces")
            row = cursor.fetchone()
            workspace_count = row['count'] if row else 1
            
            cursor = db.execute("SELECT COUNT(*) as count FROM tags")
            row = cursor.fetchone()
            tag_count = row['count'] if row else 0
            
            db_stats = {
                'note_count': note_count,
                'user_count': user_count,
                'workspace_count': workspace_count,
                'tag_count': tag_count,
                'db_path': db_path,
                'db_size_mb': round(os.path.getsize(db_path) / (1024*1024), 2) if os.path.exists(db_path) else 0
            }
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        uptime = time.time() - _SERVER_START
        
        return {
            'status': 'healthy' if db_status == 'ok' else 'degraded',
            'version': '3.0.0',
            'uptime_seconds': round(uptime, 1),
            'uptime_human': _format_uptime(uptime),
            'database': {
                'status': db_status,
                **db_stats
            },
            'features': {
                'websocket': True,
                'rate_limit': os.environ.get("MEMOMIND_RATE_LIMIT", "true").lower() != "false"
            }
        }
    
    def _format_uptime(seconds):
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    # ==================== WebSocket 实时协作 ====================

    def verify_ws_token(token: str) -> Optional[dict]:
        """验证 WebSocket Token（复用 JWT 认证逻辑）"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return {"username": username}
        except (ExpiredSignatureError, JWTError):
            return None

    @app.websocket("/ws/notes/{note_id}")
    async def websocket_endpoint(websocket: WebSocket, note_id: int, token: str):
        """
        笔记实时协作 WebSocket 端点

        连接方式：ws://host/ws/notes/{note_id}?token={hex_token}

        消息格式：
        - 客户端发送编辑变更：{"type": "edit", "title": "...", "content": "..."}
        - 客户端心跳：{"type": "ping"}
        - 服务器心跳：{"type": "ping"}
        - 服务器广播编辑：{"type": "edit", "user_id": N, "title": "...", "content": "...", "timestamp": "..."}
        - 用户加入/离开：{"type": "user_joined"/"user_left", "user": {...}, "users": [...]}
        """
        # 验证 Token
        user = verify_ws_token(token)
        if not user:
            await websocket.close(code=4001, reason="无效或过期 Token")
            return

        # 获取用户 ID
        cursor = db.execute("SELECT id FROM users WHERE username = ?", (user['username'],))
        row = cursor.fetchone()
        if not row:
            await websocket.close(code=4002, reason="用户不存在")
            return

        user_id = row['id']
        username = user['username']

        # 检查笔记是否存在
        cursor = db.execute("SELECT id FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            await websocket.close(code=4003, reason="笔记不存在")
            return

        # 检查用户是否为工作区成员（如果 workspace_id 列存在）
        info_cursor = db.execute("PRAGMA table_info(notes)")
        columns = [col['name'] for col in info_cursor.fetchall()]
        if 'workspace_id' in columns:
            cursor = db.execute("SELECT workspace_id FROM notes WHERE id = ?", (note_id,))
            ws_row = cursor.fetchone()
            if ws_row and ws_row['workspace_id']:
                workspace_id = ws_row['workspace_id']
                cursor = db.execute(
                    "SELECT 1 FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
                    (workspace_id, user_id)
                )
                if not cursor.fetchone():
                    await websocket.close(code=4004, reason="无权访问该笔记")
                    return

        await websocket.accept()
        await collaboration.handle_connection(websocket, note_id, user_id, username, db=db)
    
    # ==================== 前端静态文件服务 ====================
    
    # 查找前端构建文件目录（相对于打包后的 exe 位置或源码目录）
    _static_dir = None
    
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后：数据文件在 _internal/ 目录
        _candidate = os.path.join(sys._MEIPASS, 'dist')
    else:
        # 开发模式：项目根目录下的 web/dist
        _candidate = os.path.join(os.getcwd(), 'web', 'dist')
    
    if os.path.isdir(_candidate) and os.path.isfile(os.path.join(_candidate, 'index.html')):
        _static_dir = os.path.abspath(_candidate)
    
    if not _static_dir:
        print(f"[MemoMind] WARNING: Frontend static files not found at: {_candidate}")
    
    if _static_dir:
        app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="assets")
        
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            # API 路径不拦截
            if full_path.startswith("api/") or full_path.startswith("ws/"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            
            file_path = os.path.join(_static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            
            # SPA fallback：所有非 API 路径返回 index.html
            return FileResponse(os.path.join(_static_dir, "index.html"))
    
    return app
