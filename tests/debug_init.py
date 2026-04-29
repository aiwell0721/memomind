"""测试初始化流程"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
import json

print("Creating Database...")
db = Database(":memory:")

print("Inserting test note...")
db.execute("""
    INSERT INTO notes (title, content, tags)
    VALUES (?, ?, ?)
""", ("Test Note", "Initial content", json.dumps(["test"])))
db.commit()

# 检查笔记
cursor = db.execute("SELECT * FROM notes WHERE id = ?", (1,))
row = cursor.fetchone()
print(f"Note after insert: {dict(row) if row else 'NOT FOUND'}")

print("\nCreating VersionService (this calls _init_schema)...")
from core.version_service import VersionService
versions = VersionService(db)

# 再次检查笔记
cursor = db.execute("SELECT * FROM notes WHERE id = ?", (1,))
row = cursor.fetchone()
print(f"Note after VersionService init: {dict(row) if row else 'NOT FOUND'}")

# 尝试 UPDATE
print("\nAttempting UPDATE...")
from datetime import datetime
try:
    db.execute("""
        UPDATE notes
        SET title = ?, content = ?, tags = ?, updated_at = ?
        WHERE id = ?
    """, ("New Title", "New Content", json.dumps(["new"]), datetime.now().isoformat(), 1))
    db.commit()
    print("UPDATE: SUCCESS")
    
    cursor = db.execute("SELECT * FROM notes WHERE id = ?", (1,))
    row = cursor.fetchone()
    print(f"After update: {dict(row)}")
except Exception as e:
    print(f"UPDATE Error: {e}")
    import traceback
    traceback.print_exc()

db.close()
