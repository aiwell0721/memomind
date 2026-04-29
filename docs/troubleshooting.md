# MemoMind 故障排查指南

## 🔍 常见问题

### 1. 数据库锁定错误

**错误信息：**
```
sqlite3.OperationalError: database is locked
```

**原因：** 多个进程同时访问数据库。

**解决方案：**
```python
# 启用 WAL 模式（已默认启用）
PRAGMA journal_mode = WAL;

# 确保只有一个进程访问数据库
# 或使用内存数据库进行测试
client = MemoMind(db_path=":memory:")
```

---

### 2. 中文搜索无结果

**原因：** jieba 分词未安装或初始化失败。

**解决方案：**
```bash
# 安装 jieba
pip install jieba

# 验证安装
python -c "import jieba; print(jieba.cut('人工智能'))"
```

---

### 3. 模块导入错误

**错误信息：**
```
ImportError: No module named 'memomind'
```

**解决方案：**
```bash
# 确保在正确目录
cd memomind

# 添加父目录到路径
export PYTHONPATH=$PYTHONPATH:/path/to/memomind

# 或直接使用相对导入
from api.client import MemoMind
```

---

### 4. 内存占用过高

**症状：** 内存占用超过 100MB。

**解决方案：**
```python
# 检查笔记数量
notes = client.notes.list(limit=100000)
print(f"总笔记数：{len(notes)}")

# 清理旧版本
client.versions.cleanup(note_id=1, keep_count=10)

# 关闭不需要的连接
client.close()
```

---

### 5. 触发器已存在错误

**错误信息：**
```
sqlite3.OperationalError: trigger notes_ai already exists
```

**原因：** 重复初始化数据库。

**解决方案：**
```python
# 使用 IF NOT EXISTS（已修复）
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes...

# 或删除旧触发器
DROP TRIGGER IF EXISTS notes_ai;
```

---

### 6. FTS5 搜索语法错误

**错误信息：**
```
sqlite3.OperationalError: near "OR": syntax error
```

**原因：** 特殊字符未转义。

**解决方案：**
```python
# 使用搜索服务（已处理转义）
results = client.notes.search("关键词")

# 避免直接使用 SQL
# cursor.execute("SELECT * FROM notes_fts WHERE notes_fts MATCH ?", (query,))
```

---

### 7. 版本恢复失败

**症状：** 恢复版本后内容未变化。

**解决方案：**
```python
# 检查版本是否存在
version = client.versions.get(version_id=1)
if not version:
    print("版本不存在")

# 检查笔记是否存在
note = client.notes.get(note_id=version['note_id'])
if not note:
    print("笔记不存在")
```

---

### 8. 链接创建失败

**症状：** 链接创建后查询不到。

**解决方案：**
```python
# 确保笔记存在
note1 = client.notes.get(source_id)
note2 = client.notes.get(target_id)

if not note1 or not note2:
    print("笔记不存在")

# 避免自链接
if source_id == target_id:
    print("不能创建自链接")
```

---

## 📊 性能问题

### 搜索缓慢

**检查：**
```bash
# 运行基准测试
python benchmarks/simple_benchmark.py --notes 1000

# 检查索引
python cli.py --db memomind.db
```

**优化：**
```sql
-- 确保索引存在
CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes(tags);
CREATE INDEX IF NOT EXISTS idx_versions_note ON note_versions(note_id);
```

---

### 导出缓慢

**检查：**
```python
import time

start = time.perf_counter()
files = client.export.export_all_to_markdown_files("./output")
end = time.perf_counter()

print(f"导出耗时：{(end - start) * 1000:.2f}ms")
```

**优化：**
```python
# 分批导出
notes = client.notes.list(limit=1000)
for note in notes:
    # 处理笔记
    pass
```

---

## 🐳 Docker 问题

### 容器无法启动

**检查：**
```bash
# 查看日志
docker-compose logs

# 检查数据目录权限
ls -la ./data

# 重建容器
docker-compose down
docker-compose up -d --build
```

### 数据丢失

**解决方案：**
```yaml
# docker-compose.yml
volumes:
  - ./data:/data  # 确保挂载正确
```

---

## 📞 获取帮助

如果以上方法无法解决问题：

1. 查看 [部署指南](deployment.md)
2. 查看 [API 参考](api-reference.md)
3. 提交 [GitHub Issue](https://github.com/your-org/memomind/issues)

---

*最后更新：2026-04-23*
