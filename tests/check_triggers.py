"""检查触发器"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
import json

db = Database(":memory:")

# 插入笔记
db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", 
           ("Test", "Content", json.dumps(["test"])))
db.commit()

# 检查触发器
cursor = db.conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger'")
triggers = cursor.fetchall()
print("Triggers on notes table:")
for name, tbl_name, sql in triggers:
    print(f"  {name} on {tbl_name}:")
    print(f"    {sql[:200]}...")

# 检查 FTS5 表
cursor = db.conn.execute("SELECT sql FROM sqlite_master WHERE name='notes_fts'")
fts = cursor.fetchone()
print(f"\nFTS5 table: {fts}")

# 尝试 INSERT（测试写权限）
try:
    db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", 
               ("Test2", "Content2", json.dumps(["test2"])))
    db.commit()
    print("\nINSERT: SUCCESS")
except Exception as e:
    print(f"\nINSERT: FAILED - {e}")

# 尝试 DELETE
try:
    db.execute("DELETE FROM notes WHERE id=?", (2,))
    db.commit()
    print("DELETE: SUCCESS")
except Exception as e:
    print(f"DELETE: FAILED - {e}")

# 尝试 UPDATE 单个字段
try:
    db.execute("UPDATE notes SET title=? WHERE id=?", ("New", 1))
    db.commit()
    print("UPDATE (title only): SUCCESS")
except Exception as e:
    print(f"UPDATE (title only): FAILED - {e}")

# 尝试 UPDATE 不带 updated_at
try:
    db.execute("UPDATE notes SET title=?, content=? WHERE id=?", ("New2", "Content2", 1))
    db.commit()
    print("UPDATE (no updated_at): SUCCESS")
except Exception as e:
    print(f"UPDATE (no updated_at): FAILED - {e}")

db.close()
