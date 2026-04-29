"""测试 FTS5 触发器问题"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
import json

# 手动创建数据库，不通过 Database 类
import sqlite3
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row

# 创建 notes 表（不带触发器）
conn.execute("""
    CREATE TABLE notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 创建 FTS5 表
conn.execute("""
    CREATE VIRTUAL TABLE notes_fts USING fts5(title, content, tags)
""")

# 插入笔记
conn.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", 
             ("Test", "Content", json.dumps(["test"])))
conn.commit()
print("1. Note inserted (no triggers)")

# 尝试 UPDATE
try:
    conn.execute("UPDATE notes SET title=? WHERE id=?", ("New", 1))
    conn.commit()
    print("2. UPDATE (no triggers): SUCCESS")
except Exception as e:
    print(f"2. UPDATE (no triggers): FAILED - {e}")

# 现在创建触发器
conn.execute("""
    CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
        INSERT INTO notes_fts(rowid, title, content, tags)
        VALUES (new.id, new.title, new.content, new.tags);
    END
""")

conn.execute("""
    CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
        INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
        VALUES('delete', old.id, old.title, old.content, old.tags);
    END
""")

conn.execute("""
    CREATE TRIGGER notes_au AFTER UPDATE ON notes BEGIN
        INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
        VALUES('delete', old.id, old.title, old.content, old.tags);
        INSERT INTO notes_fts(rowid, title, content, tags)
        VALUES (new.id, new.title, new.content, new.tags);
    END
""")

print("3. Triggers created")

# 插入新笔记（测试 INSERT 触发器）
try:
    conn.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", 
                 ("Test2", "Content2", json.dumps(["test2"])))
    conn.commit()
    print("4. INSERT (with triggers): SUCCESS")
except Exception as e:
    print(f"4. INSERT (with triggers): FAILED - {e}")

# 尝试 UPDATE
try:
    conn.execute("UPDATE notes SET title=? WHERE id=?", ("New", 1))
    conn.commit()
    print("5. UPDATE (with triggers): SUCCESS")
except Exception as e:
    print(f"5. UPDATE (with triggers): FAILED - {e}")
    # 检查 FTS5 内容
    cursor = conn.execute("SELECT * FROM notes_fts")
    rows = cursor.fetchall()
    print(f"   FTS5 contents: {len(rows)} rows")
    for row in rows:
        print(f"     {dict(row)}")

conn.close()
