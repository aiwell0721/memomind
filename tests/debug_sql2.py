"""测试外键约束问题"""

import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row

# 启用外键
conn.execute("PRAGMA foreign_keys = ON")

# 创建 notes 表
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

# 创建 note_versions 表（带外键）
conn.execute("""
    CREATE TABLE note_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        version_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (note_id) REFERENCES notes(id)
    )
""")

# 插入笔记
conn.execute("""
    INSERT INTO notes (title, content, tags)
    VALUES (?, ?, ?)
""", ("Test Note", "Initial content", json.dumps(["test"])))
conn.commit()

print(f"Inserted note with id=1")

# 插入版本
conn.execute("""
    INSERT INTO note_versions (note_id, version_number, title, content, tags)
    VALUES (?, ?, ?, ?, ?)
""", (1, 1, "Version 1", "Content v1", json.dumps(["v1"])))
conn.commit()

print(f"Inserted version with note_id=1")

# 检查外键状态
cursor = conn.execute("PRAGMA foreign_keys")
print(f"Foreign keys enabled: {cursor.fetchone()[0]}")

# 检查笔记
cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (1,))
row = cursor.fetchone()
print(f"Note exists: {row is not None}")

# 尝试 UPDATE
print("\nAttempting UPDATE...")
try:
    conn.execute("""
        UPDATE notes
        SET title = ?, content = ?, tags = ?, updated_at = ?
        WHERE id = ?
    """, ("New Title", "New Content", json.dumps(["new"]), datetime.now().isoformat(), 1))
    conn.commit()
    print("UPDATE: SUCCESS")
    
    cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (1,))
    row = cursor.fetchone()
    print(f"After update: {dict(row)}")
except Exception as e:
    print(f"UPDATE Error: {e}")
    import traceback
    traceback.print_exc()

# 禁用外键再试
print("\n--- Disabling foreign keys ---")
conn.execute("PRAGMA foreign_keys = OFF")
cursor = conn.execute("PRAGMA foreign_keys")
print(f"Foreign keys enabled: {cursor.fetchone()[0]}")

try:
    conn.execute("""
        UPDATE notes
        SET title = ?, content = ?, tags = ?, updated_at = ?
        WHERE id = ?
    """, ("New Title 2", "New Content 2", json.dumps(["new2"]), datetime.now().isoformat(), 1))
    conn.commit()
    print("UPDATE (FK off): SUCCESS")
    
    cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (1,))
    row = cursor.fetchone()
    print(f"After update: {dict(row)}")
except Exception as e:
    print(f"UPDATE (FK off) Error: {e}")

conn.close()
