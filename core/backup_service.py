"""
MemoMind 自动备份与恢复服务
支持定时备份、备份文件压缩、从备份恢复、备份历史管理
"""

import os
import json
import shutil
import gzip
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from .database import Database


@dataclass
class BackupInfo:
    """备份信息数据模型"""
    id: Optional[int] = None
    filename: str = ""
    size_bytes: int = 0
    note_count: int = 0
    created_at: Optional[str] = None
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'filename': self.filename,
            'size_bytes': self.size_bytes,
            'size_mb': round(self.size_bytes / (1024 * 1024), 2),
            'note_count': self.note_count,
            'created_at': self.created_at,
            'description': self.description
        }
    
    @classmethod
    def from_row(cls, row) -> 'BackupInfo':
        return cls(
            id=row['id'],
            filename=row['filename'],
            size_bytes=row['size_bytes'],
            note_count=row['note_count'],
            created_at=row['created_at'],
            description=row['description']
        )


class BackupService:
    """备份与恢复服务"""
    
    def __init__(self, db: Database, backup_dir: str = None):
        self.db = db
        self.backup_dir = Path(backup_dir) if backup_dir else Path.cwd() / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    def _init_schema(self):
        """初始化备份记录表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                note_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT DEFAULT ''
            )
        """)
        self.db.commit()
    
    def create_backup(self, description: str = '') -> Dict:
        """
        创建数据库备份（压缩为 .gz 文件）
        
        Args:
            description: 备份描述
            
        Returns:
            备份信息字典
        """
        if self.db.db_path == ':memory:':
            raise ValueError("不能备份内存数据库")
        
        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'memomind_backup_{timestamp}.db.gz'
        filepath = self.backup_dir / filename
        
        # 使用 SQLite 的 backup API 创建一致快照
        import sqlite3
        uncompressed_path = str(filepath).replace('.gz', '')
        backup_conn = sqlite3.connect(uncompressed_path)
        self.db.conn.backup(backup_conn)
        backup_conn.close()
        
        # 压缩备份文件
        with open(uncompressed_path, 'rb') as f_in:
            with gzip.open(filepath, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(uncompressed_path)
        
        # 统计笔记数
        cursor = self.db.execute("SELECT COUNT(*) FROM notes")
        note_count = cursor.fetchone()[0]
        
        # 记录备份信息
        size_bytes = filepath.stat().st_size
        cursor = self.db.execute("""
            INSERT INTO backups (filename, size_bytes, note_count, description)
            VALUES (?, ?, ?, ?)
        """, (filename, size_bytes, note_count, description))
        self.db.commit()
        
        return {
            'id': cursor.lastrowid,
            'filename': filename,
            'filepath': str(filepath),
            'size_bytes': size_bytes,
            'note_count': note_count,
            'description': description
        }
    
    def list_backups(self, limit: int = 50) -> List[BackupInfo]:
        """
        列出所有备份
        
        Args:
            limit: 返回数量限制
            
        Returns:
            备份信息列表
        """
        cursor = self.db.execute("""
            SELECT * FROM backups
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [BackupInfo.from_row(row) for row in cursor.fetchall()]
    
    def get_backup(self, backup_id: int) -> Optional[BackupInfo]:
        """
        获取备份信息
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            备份信息
        """
        cursor = self.db.execute("""
            SELECT * FROM backups WHERE id = ?
        """, (backup_id,))
        row = cursor.fetchone()
        return BackupInfo.from_row(row) if row else None
    
    def restore_backup(self, backup_id: int) -> bool:
        """
        从备份恢复数据库
        
        ⚠️ 会覆盖当前数据库！
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            是否成功
        """
        cursor = self.db.execute("""
            SELECT * FROM backups WHERE id = ?
        """, (backup_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"备份不存在: {backup_id}")
        
        filepath = self.backup_dir / row['filename']
        if not filepath.exists():
            raise FileNotFoundError(f"备份文件不存在: {filepath}")
        
        if self.db.db_path == ':memory:':
            raise ValueError("不能恢复到内存数据库")
        
        # 解压备份文件
        uncompressed_path = str(filepath).replace('.gz', '')
        with gzip.open(filepath, 'rb') as f_in:
            with open(uncompressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 恢复数据库 - 直接替换数据库文件
        self.db.close()
        # 删除旧数据库
        if Path(self.db.db_path).exists():
            Path(self.db.db_path).unlink()
        # 复制备份文件
        shutil.copy2(uncompressed_path, self.db.db_path)
        os.remove(uncompressed_path)
        # 重新创建数据库连接
        self.db = Database(self.db.db_path)
        
        return True
    
    def delete_backup(self, backup_id: int) -> bool:
        """
        删除备份（同时删除文件）
        
        Args:
            backup_id: 备份 ID
            
        Returns:
            是否成功
        """
        cursor = self.db.execute("""
            SELECT filename FROM backups WHERE id = ?
        """, (backup_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        # 删除备份文件
        filepath = self.backup_dir / row['filename']
        if filepath.exists():
            filepath.unlink()
        
        # 删除记录
        self.db.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
        self.db.commit()
        return True
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        清理旧备份（保留最近 N 个）
        
        Args:
            keep_count: 保留数量
            
        Returns:
            删除的备份数量
        """
        cursor = self.db.execute("""
            SELECT id, filename FROM backups
            ORDER BY created_at DESC
            LIMIT -1 OFFSET ?
        """, (keep_count,))
        
        old_backups = cursor.fetchall()
        deleted = 0
        
        for backup in old_backups:
            filepath = self.backup_dir / backup['filename']
            if filepath.exists():
                filepath.unlink()
            self.db.execute("DELETE FROM backups WHERE id = ?", (backup['id'],))
            deleted += 1
        
        self.db.commit()
        return deleted
    
    def export_to_json(self, output_path: str = None) -> str:
        """
        导出所有数据为 JSON（人类可读）
        
        Args:
            output_path: 输出路径
            
        Returns:
            输出文件路径
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = str(self.backup_dir / f'memomind_export_{timestamp}.json')
        
        # 导出所有表数据
        data = {
            'exported_at': datetime.now().isoformat(),
            'version': '3.0',
            'workspaces': [],
            'users': [],
            'notes': [],
            'tags': [],
            'links': [],
            'versions': [],
            'workspace_members': []
        }
        
        tables = {
            'workspaces': 'workspaces',
            'users': 'users',
            'notes': 'notes',
            'workspace_members': 'workspace_members'
        }
        
        for key, table in tables.items():
            try:
                cursor = self.db.execute(f"SELECT * FROM {table}")
                data[key] = [dict(row) for row in cursor.fetchall()]
            except Exception:
                data[key] = []
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def get_backup_stats(self) -> Dict:
        """
        获取备份统计
        
        Returns:
            统计字典
        """
        cursor = self.db.execute("""
            SELECT 
                COUNT(*) as total,
                COALESCE(SUM(size_bytes), 0) as total_size,
                MAX(created_at) as latest_backup
            FROM backups
        """)
        row = cursor.fetchone()
        
        return {
            'total_backups': row['total'],
            'total_size_bytes': row['total_size'],
            'total_size_mb': round(row['total_size'] / (1024 * 1024), 2),
            'latest_backup': row['latest_backup']
        }
