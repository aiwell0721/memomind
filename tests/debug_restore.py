"""调试 restore_version 问题"""

import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.version_service import VersionService
import json

# 创建数据库
db = Database(":memory:")
versions = VersionService(db)

# 创建测试笔记
db.execute("""
    INSERT INTO notes (title, content, tags)
    VALUES (?, ?, ?)
""", ("Test Note", "Initial content", json.dumps(["test"])))
db.commit()
note_id = 1

# 保存版本
v1 = versions.save_version(note_id, "Title V1", "Content V1", ["v1"])
print(f"Saved version: {v1}")

# 保存第二个版本
v2 = versions.save_version(note_id, "Title V2", "Content V2", ["v2"])
print(f"Saved version: {v2}")

# 检查当前笔记
cursor = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
row = cursor.fetchone()
print(f"Current note before restore: {dict(row)}")

# 获取版本详情
version = versions.get_version(v1)
print(f"Version details: id={version.id}, note_id={version.note_id}, title={version.title}")

# 检查 notes 表是否存在
cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
table = cursor.fetchone()
print(f"Notes table exists: {table is not None}")

# 直接执行 SQL 测试
print(f"\n--- Direct SQL test ---")
try:
    db.execute("""
        UPDATE notes
        SET title = ?, content = ?, tags = ?, updated_at = ?
        WHERE id = ?
    """, (version.title, version.content, json.dumps(version.tags), datetime.now().isoformat(), version.note_id))
    db.commit()
    print("Direct SQL: SUCCESS")
    
    cursor = db.execute("SELECT * FROM notes WHERE id = ?", (version.note_id,))
    row = cursor.fetchone()
    print(f"After direct SQL: {dict(row)}")
except Exception as e:
    print(f"Direct SQL Error: {e}")

# 尝试恢复
print(f"\nAttempting to restore version {v1}...")
try:
    result = versions.restore_version(v1)
    print(f"Restore result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# 检查恢复后的笔记
cursor = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
row = cursor.fetchone()
print(f"\nCurrent note after restore: {dict(row)}")

db.close()
