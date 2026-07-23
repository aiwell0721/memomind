"""
MemoMind 数据库连接管理
"""

import re
import sqlite3
from typing import Optional

from .tokenizer import get_tokenizer


class Database:
    """数据库连接管理"""

    def __init__(self, db_path: str = ":memory:"):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径，默认使用内存数据库
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()
    
    def _connect(self):
        """建立数据库连接"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # 启用外键
        self.conn.execute("PRAGMA foreign_keys = ON")
        # 启用 WAL 模式（更好的并发读性能）
        self.conn.execute("PRAGMA journal_mode = WAL")
        # 并发写时等待 5 秒再抛 'database is locked'。
        # Python sqlite3 模块当前默认就是 5000，但显式声明使行为不依赖运行时默认。
        self.conn.execute("PRAGMA busy_timeout = 5000")
    
    def _init_schema(self):
        """初始化数据库结构"""
        cursor = self.conn.cursor()
        
        # 使用 IF NOT EXISTS 避免重复创建
        pass  # 表会在下面用 CREATE TABLE IF NOT EXISTS 创建
        
        # 创建笔记主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建 FTS5 全文索引虚拟表
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                title,
                content,
                tags
            )
        """)
        
        # FTS5 同步改为 Python 端处理（见 sync_note_to_fts），原因：
        # SQLite 触发器无法调用 Python 端的 jieba 分词，导致连续中文文本
        # 被 unicode61 当作单个 token，搜索时永远 0 命中。
        # 兼容老数据库：若历史触发器存在则丢弃。
        cursor.execute("DROP TRIGGER IF EXISTS notes_ai")
        cursor.execute("DROP TRIGGER IF EXISTS notes_ad")
        cursor.execute("DROP TRIGGER IF EXISTS notes_au")
        
        # 创建标签索引（加速标签过滤）
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes(tags)
        """)

        # Dreaming 会话记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dreaming_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                trigger TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'running',
                input_count INTEGER DEFAULT 0,
                output_count INTEGER DEFAULT 0,
                merged_count INTEGER DEFAULT 0,
                archived_count INTEGER DEFAULT 0,
                extracted_facts INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)

        # Dreaming 变更追溯
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dreaming_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                source_ids TEXT NOT NULL DEFAULT '[]',
                target_id INTEGER,
                diff_summary TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES dreaming_sessions(id)
            )
        """)

        # Dreaming AI 压缩结果
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dreaming_concentrates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                source_ids TEXT NOT NULL,
                target_note_id INTEGER NOT NULL,
                ai_title TEXT DEFAULT '',
                ai_content TEXT DEFAULT '',
                keywords TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES dreaming_sessions(id)
            )
        """)

        # Dreaming AI 压缩字段迁移
        for col in ["ai_compressed", "token_cost"]:
            try:
                cursor.execute(
                    f"ALTER TABLE dreaming_sessions ADD COLUMN {col} "
                    f"{'INTEGER DEFAULT 0' if col == 'ai_compressed' else 'INTEGER DEFAULT 0'}"
                )
            except sqlite3.OperationalError:
                pass  # 已迁移

        # 备注功能支持（v2.1.0）
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN type TEXT NOT NULL DEFAULT 'note'")
        except sqlite3.OperationalError:
            pass  # 已迁移
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN parent_id INTEGER REFERENCES notes(id)")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(type)")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_parent ON notes(parent_id)")
        except sqlite3.OperationalError:
            pass

        # AI 摘要持久化
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN ai_summary TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        self.conn.commit()

        # 启动时重建 FTS5 索引，确保：
        # 1. 老版本触发器写入的未分词内容被 jieba 重新分词
        # 2. ALTER TABLE 后的行被同步到 FTS5 虚拟表
        # 重建开销与笔记数成正比，当前量级（<10000 条）可接受
        self._fts_rebuild_all()
        self.conn.commit()

    # SQL 写操作的正则：只匹配 notes 主表（含可选 schema 前缀），排除 notes_fts、
    # note_versions、note_tags、note_links 等同前缀表。\b 保证 'notes' 是完整词。
    _RE_INSERT_NOTES = re.compile(r"^\s*INSERT\s+(?:OR\s+\w+\s+)?INTO\s+notes\b(?!_)", re.IGNORECASE)
    _RE_UPDATE_NOTES = re.compile(r"^\s*UPDATE\s+notes\b(?!_)", re.IGNORECASE)
    _RE_DELETE_NOTES = re.compile(r"^\s*DELETE\s+FROM\s+notes\b(?!_)", re.IGNORECASE)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行 SQL 语句。

        notes 主表的 INSERT/UPDATE/DELETE 之后，自动 jieba 分词刷新 FTS5。
        其它表（含 notes_fts/note_versions/note_tags/note_links）不触发同步。
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self._sync_fts_if_notes_write(sql, cursor)
        return cursor

    # ---------- FTS5 同步 ----------

    def _sync_fts_if_notes_write(self, sql: str, cursor: sqlite3.Cursor) -> None:
        """SQL 是 notes 主表的写操作时刷新 FTS5。"""
        if self._RE_INSERT_NOTES.match(sql):
            note_id = cursor.lastrowid
            if note_id:
                row = self.conn.execute(
                    "SELECT title, content, tags FROM notes WHERE id = ?",
                    (note_id,)
                ).fetchone()
                if row:
                    self._fts_upsert(note_id, row[0], row[1], row[2])
        elif self._RE_UPDATE_NOTES.match(sql) or self._RE_DELETE_NOTES.match(sql):
            # SQLite 不返回 UPDATE/DELETE 受影响行的 id 列表。
            # 折中：刷新整张 FTS 表。当前 notes 量级（个人/小团队知识库）可接受；
            # 若 notes 上万行可改为：UPDATE/DELETE 前先按 WHERE 查 id 列表再增量刷。
            self._fts_rebuild_all()

    def _fts_rebuild_all(self) -> None:
        """重建整张 notes_fts。"""
        self.conn.execute("DELETE FROM notes_fts")
        rows = self.conn.execute(
            "SELECT id, title, content, tags FROM notes"
        ).fetchall()
        for r in rows:
            self._fts_upsert(r[0], r[1], r[2], r[3])

    def _tokenize_for_fts(self, text: Optional[str]) -> str:
        """对文本做 jieba 分词，返回空格分隔的 token 串供 FTS5 索引。"""
        if not text:
            return ""
        tokens = get_tokenizer().tokenize(text, remove_stopwords=False)
        return " ".join(tokens)

    def _fts_upsert(
        self,
        note_id: int,
        title: Optional[str],
        content: Optional[str],
        tags: Optional[str],
    ) -> None:
        tok_title = self._tokenize_for_fts(title)
        tok_content = self._tokenize_for_fts(content)
        self.conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (note_id,))
        self.conn.execute(
            "INSERT INTO notes_fts(rowid, title, content, tags) VALUES (?, ?, ?, ?)",
            (note_id, tok_title, tok_content, tags or "")
        )

    def _fts_delete(self, note_id: int) -> None:
        self.conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (note_id,))

    # 公开 API（供 api_server / 历史调用方使用）
    def sync_note_to_fts(
        self,
        note_id: int,
        title: Optional[str],
        content: Optional[str],
        tags: Optional[str],
    ) -> None:
        """显式同步单条笔记到 FTS5。一般无需调用——execute() 已自动处理。"""
        self._fts_upsert(note_id, title, content, tags)

    def delete_note_from_fts(self, note_id: int) -> None:
        """显式从 FTS5 删除单条笔记。一般无需调用——execute() 已自动处理。"""
        self._fts_delete(note_id)

    def reindex_notes(self) -> int:
        """重建全部笔记的 FTS5 索引，返回处理条数。

        启动时调用一次可修复历史数据（之前由旧触发器写入的未分词内容）。
        """
        self.conn.execute("DELETE FROM notes_fts")
        rows = self.conn.execute(
            "SELECT id, title, content, tags FROM notes"
        ).fetchall()
        for row in rows:
            self._fts_upsert(row[0], row[1], row[2], row[3])
        self.conn.commit()
        return len(rows)
    
    def commit(self):
        """提交事务"""
        self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
