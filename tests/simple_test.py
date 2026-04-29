"""最简测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.version_service import VersionService
import json
from datetime import datetime

# 创建数据库
db = Database(":memory:")
print("1. Database created")

# 插入笔记
db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", 
           ("Test", "Content", json.dumps(["test"])))
db.commit()
print("2. Note inserted")

# 创建 VersionService
v = VersionService(db)
print("3. VersionService created")

# 尝试 UPDATE
try:
    db.execute("UPDATE notes SET title=? WHERE id=?", ("New", 1))
    db.commit()
    print("4. UPDATE SUCCESS")
except Exception as e:
    print(f"4. UPDATE FAILED: {e}")
    
db.close()
