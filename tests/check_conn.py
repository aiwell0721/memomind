"""检查数据库连接"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
import json

# 创建数据库
db = Database(":memory:")
print(f"1. Database created, conn={id(db.conn)}")

# 插入笔记
db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", 
           ("Test", "Content", json.dumps(["test"])))
db.commit()
print("2. Note inserted")

# 检查连接状态
print(f"   conn.in_transaction={db.conn.in_transaction}")
print(f"   conn.isolation_level={db.conn.isolation_level}")

# 创建 VersionService
from core.version_service import VersionService
v = VersionService(db)
print(f"3. VersionService created, db.conn={id(db.conn)}")

# 再次检查连接状态
print(f"   conn.in_transaction={db.conn.in_transaction}")
print(f"   conn.isolation_level={db.conn.isolation_level}")

# 检查表
cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"   Tables: {[t[0] for t in tables]}")

# 尝试直接通过 conn UPDATE
try:
    db.conn.execute("UPDATE notes SET title=? WHERE id=?", ("New", 1))
    db.conn.commit()
    print("4. UPDATE via conn SUCCESS")
except Exception as e:
    print(f"4. UPDATE via conn FAILED: {e}")

# 尝试通过 db.execute UPDATE
try:
    db.execute("UPDATE notes SET title=? WHERE id=?", ("New2", 1))
    db.commit()
    print("5. UPDATE via db.execute SUCCESS")
except Exception as e:
    print(f"5. UPDATE via db.execute FAILED: {e}")

db.close()
