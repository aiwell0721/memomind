# MemoMind 部署指南

## 🐳 Docker 部署（推荐）

### 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/memomind.git
cd memomind

# 2. 构建并启动
docker-compose up -d

# 3. 验证
docker-compose exec memomind python cli.py notes list
```

### 数据持久化

```yaml
# docker-compose.yml
volumes:
  - ./data:/data  # 数据库文件持久化
  - ./backups:/backups  # 备份目录
```

### 备份与恢复

```bash
# 备份
docker-compose exec memomind cp /data/memomind.db /backups/memomind-backup.db

# 恢复
docker-compose exec memomind cp /backups/memomind-backup.db /data/memomind.db
```

---

## 🖥️ 本地部署

### 环境要求

- Python 3.9+
- SQLite 3.35+
- 内存：≥ 100MB

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/memomind.git
cd memomind

# 2. 安装依赖
pip install -r requirements.txt
pip install jieba

# 3. 验证安装
python cli.py --help
```

### 配置

```python
# config.py
DB_PATH = "~/memomind.db"
LOG_LEVEL = "INFO"
MAX_NOTE_SIZE = 1024 * 1024  # 1MB
```

---

## 📦 数据迁移

### 从旧版本迁移

```bash
# 导出旧数据
python cli.py export json ./backup.json

# 导入到新实例
python cli.py import json ./backup.json
```

### 从 Markdown 导入

```bash
# 批量导入 Markdown 文件
python cli.py import markdown ./notes-directory --conflict skip
```

---

## 🔧 性能优化

### 数据库优化

```sql
-- 启用 WAL 模式（已默认启用）
PRAGMA journal_mode = WAL;

-- 启用外键
PRAGMA foreign_keys = ON;

-- 优化查询
ANALYZE;
```

### 索引优化

```sql
-- 已自动创建索引
CREATE INDEX idx_notes_tags ON notes(tags);
CREATE INDEX idx_versions_note ON note_versions(note_id);
CREATE INDEX idx_links_target ON note_links(target_note_id);
```

---

## 📊 监控与日志

### 日志配置

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memomind.log'),
        logging.StreamHandler()
    ]
)
```

### 性能监控

```bash
# 运行基准测试
python benchmarks/simple_benchmark.py --notes 1000
```

---

## ❓ 故障排查

### 常见问题

**Q: 数据库锁定错误**
```
sqlite3.OperationalError: database is locked
```
A: 确保只有一个进程访问数据库。使用 WAL 模式可缓解。

**Q: 中文搜索无结果**
A: 确保已安装 jieba：`pip install jieba`

**Q: 内存占用过高**
A: 检查笔记数量。1000 条笔记约 45MB 内存。

---

*需要帮助？提交 Issue 或查看 [故障排查指南](troubleshooting.md)*
