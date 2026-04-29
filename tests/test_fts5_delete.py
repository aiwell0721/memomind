"""测试 FTS5 DELETE 语法"""

import sqlite3
import json

conn = sqlite3.connect(":memory:")

# 创建 FTS5 表
conn.execute("""
    CREATE VIRTUAL TABLE notes_fts USING fts5(title, content, tags)
""")

# 插入数据
conn.execute("INSERT INTO notes_fts(rowid, title, content, tags) VALUES (?, ?, ?, ?)",
             (1, "Title", "Content", '["tag"]'))
conn.commit()
print("1. Inserted into FTS5")

# 检查
cursor = conn.execute("SELECT * FROM notes_fts")
print(f"   Rows: {cursor.fetchall()}")

# 尝试方法 1: INSERT ... VALUES('delete', ...)
print("\n2. Trying INSERT DELETE syntax...")
try:
    conn.execute("""
        INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
        VALUES('delete', ?, ?, ?, ?)
    """, (1, "Title", "Content", '["tag"]'))
    conn.commit()
    print("   SUCCESS")
    cursor = conn.execute("SELECT * FROM notes_fts")
    print(f"   Rows: {cursor.fetchall()}")
except Exception as e:
    print(f"   FAILED: {e}")

# 重新插入
conn.execute("INSERT INTO notes_fts(rowid, title, content, tags) VALUES (?, ?, ?, ?)",
             (2, "Title2", "Content2", '["tag2"]'))
conn.commit()

# 尝试方法 2: DELETE FROM ... WHERE
print("\n3. Trying DELETE FROM syntax...")
try:
    conn.execute("DELETE FROM notes_fts WHERE rowid=?", (2,))
    conn.commit()
    print("   SUCCESS")
    cursor = conn.execute("SELECT * FROM notes_fts")
    print(f"   Rows: {cursor.fetchall()}")
except Exception as e:
    print(f"   FAILED: {e}")

conn.close()
