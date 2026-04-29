"""
MemoMind 数据库连接管理
"""

import sqlite3
from pathlib import Path
from typing import Optional


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
        # 启用 WAL 模式（更好的并发性能）
        self.conn.execute("PRAGMA journal_mode = WAL")
    
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
        
        # 创建触发器：INSERT 自动同步索引
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END
        """)
        
        # 创建触发器：DELETE 自动同步索引
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                DELETE FROM notes_fts WHERE rowid = old.id;
            END
        """)
        
        # 创建触发器：UPDATE 自动同步索引
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                DELETE FROM notes_fts WHERE rowid = old.id;
                INSERT INTO notes_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END
        """)
        
        # 创建标签索引（加速标签过滤）
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes(tags)
        """)
        
        self.conn.commit()
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行 SQL 语句"""
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor
    
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
