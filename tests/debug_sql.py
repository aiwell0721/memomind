"""直接测试 SQL 语句"""

import sqlite3
import json
from datetime import datetime

# 创建内存数据库
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row

# 创建表
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

# 插入数据
conn.execute("""
    INSERT INTO notes (title, content, tags)
    VALUES (?, ?, ?)
""", ("Test Note", "Initial content", json.dumps(["test"])))
conn.commit()

# 检查数据
cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (1,))
row = cursor.fetchone()
print(f"Before update: {dict(row)}")

# 尝试 UPDATE（使用 CURRENT_TIMESTAMP）
print("\n--- Testing with CURRENT_TIMESTAMP ---")
try:
    conn.execute("""
        UPDATE notes
        SET title = ?, content = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, ("New Title", "New Content", json.dumps(["new"]), 1))
    conn.commit()
    print("UPDATE with CURRENT_TIMESTAMP: SUCCESS")
    
    cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (1,))
    row = cursor.fetchone()
    print(f"After update: {dict(row)}")
except Exception as e:
    print(f"Error: {e}")

# 重置数据
conn.execute("""
    UPDATE notes SET title = 'Test Note', content = 'Initial content', tags = ?
    WHERE id = 1
""", (json.dumps(["test"]),))
conn.commit()

# 尝试 UPDATE（使用 ISO 格式字符串）
print("\n--- Testing with ISO format string ---")
try:
    conn.execute("""
        UPDATE notes
        SET title = ?, content = ?, tags = ?, updated_at = ?
        WHERE id = ?
    """, ("New Title 2", "New Content 2", json.dumps(["new2"]), datetime.now().isoformat(), 1))
    conn.commit()
    print("UPDATE with ISO format: SUCCESS")
    
    cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (1,))
    row = cursor.fetchone()
    print(f"After update: {dict(row)}")
except Exception as e:
    print(f"Error: {e}")

conn.close()
