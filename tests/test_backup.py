"""
MemoMind 备份与恢复测试 - PR-017
"""

import pytest
import os
import tempfile
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.workspace_service import WorkspaceService
from core.user_service import UserService
from core.backup_service import BackupService, BackupInfo


class TestBackupService:
    """备份服务测试"""
    
    def setup_method(self):
        # 使用临时文件数据库（非内存）
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        
        self.db = Database(self.db_path)
        self.ws = WorkspaceService(self.db)
        self.users = UserService(self.db)
        self.backup = BackupService(self.db, self.backup_dir)
    
    def teardown_method(self):
        self.db.close()
        # 清理临时文件
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_backup(self):
        """创建备份"""
        # 添加一些数据
        self.db.execute("""
            INSERT INTO notes (title, content, workspace_id)
            VALUES ('Test Note', 'Content', 1)
        """)
        self.db.commit()
        
        result = self.backup.create_backup('测试备份')
        assert result['id'] >= 1
        assert result['note_count'] == 1
        assert result['size_bytes'] > 0
        assert 'memomind_backup_' in result['filename']
        
        # 验证文件存在
        assert Path(result['filepath']).exists()
    
    def test_create_backup_memory_db_raises(self):
        """不能备份内存数据库"""
        mem_db = Database(":memory:")
        mem_backup = BackupService(mem_db, self.backup_dir)
        
        with pytest.raises(ValueError, match="不能备份内存数据库"):
            mem_backup.create_backup()
        
        mem_db.close()
    
    def test_list_backups(self):
        """列出备份"""
        self.backup.create_backup('备份1')
        self.backup.create_backup('备份2')
        
        backups = self.backup.list_backups()
        assert len(backups) == 2
    
    def test_get_backup(self):
        """获取备份信息"""
        result = self.backup.create_backup('测试')
        backup = self.backup.get_backup(result['id'])
        
        assert backup is not None
        assert backup.filename == result['filename']
        assert backup.note_count == result['note_count']
    
    def test_get_backup_not_found(self):
        """获取不存在的备份"""
        backup = self.backup.get_backup(999)
        assert backup is None
    
    def test_delete_backup(self):
        """删除备份"""
        result = self.backup.create_backup('待删除')
        filepath = result['filepath']
        
        self.backup.delete_backup(result['id'])
        
        # 文件和记录都应删除
        assert not Path(filepath).exists()
        assert self.backup.get_backup(result['id']) is None
    
    def test_delete_backup_not_found(self):
        """删除不存在的备份"""
        result = self.backup.delete_backup(999)
        assert result is False
    
    def test_cleanup_old_backups(self):
        """清理旧备份"""
        for i in range(5):
            self.backup.create_backup(f'备份{i}')
        
        # 保留最近 2 个
        deleted = self.backup.cleanup_old_backups(keep_count=2)
        assert deleted == 3
        
        remaining = self.backup.list_backups()
        assert len(remaining) == 2
    
    def test_export_to_json(self):
        """导出为 JSON"""
        # 添加数据
        self.ws.create_workspace('测试区')
        self.users.create_user('alice')
        
        output = self.backup.export_to_json()
        assert output.endswith('.json')
        assert Path(output).exists()
        
        # 验证 JSON 内容
        with open(output, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'workspaces' in data
        assert 'users' in data
        assert 'notes' in data
        assert data['version'] == '3.0'
    
    def test_get_backup_stats(self):
        """备份统计"""
        self.backup.create_backup('备份1')
        self.backup.create_backup('备份2')
        
        stats = self.backup.get_backup_stats()
        assert stats['total_backups'] == 2
        assert stats['total_size_bytes'] > 0
        assert stats['latest_backup'] is not None


class TestBackupInfoToDict:
    """BackupInfo 模型转换测试"""
    
    def test_to_dict(self):
        info = BackupInfo(
            id=1, filename='test.db.gz', size_bytes=1024,
            note_count=5, created_at='2026-04-24', description='测试'
        )
        d = info.to_dict()
        assert d['filename'] == 'test.db.gz'
        assert d['size_mb'] == 0.0  # 1024 bytes = 0.000976... MB


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
