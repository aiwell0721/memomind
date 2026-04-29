"""
MemoMind 导入服务 - 支持 Markdown 和 JSON 格式
"""

import json
import re
import os
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
from .database import Database


class ImportResult:
    """导入结果"""
    def __init__(self):
        self.imported = 0  # 成功导入数量
        self.skipped = 0   # 跳过数量
        self.updated = 0   # 更新数量
        self.errors = []   # 错误列表
    
    def add_error(self, filename: str, error: str):
        """添加错误记录"""
        self.errors.append({'file': filename, 'error': error})
    
    def summary(self) -> str:
        """生成摘要"""
        return f"导入完成：{self.imported} 新增，{self.updated} 更新，{self.skipped} 跳过，{len(self.errors)} 错误"


class ImportService:
    """笔记导入服务"""
    
    CONFLICT_SKIP = 'skip'      # 跳过已存在的笔记
    CONFLICT_OVERWRITE = 'overwrite'  # 覆盖已存在的笔记
    CONFLICT_MERGE = 'merge'    # 合并（保留新版本）
    
    def __init__(self, db: Database):
        """
        初始化导入服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
    
    def import_markdown_file(self, filepath: str, conflict_policy: str = CONFLICT_SKIP) -> Tuple[int, ImportResult]:
        """
        导入单个 Markdown 文件
        
        Args:
            filepath: 文件路径
            conflict_policy: 冲突处理策略
            
        Returns:
            (笔记 ID, 导入结果)
        """
        result = ImportResult()
        
        try:
            # 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 Frontmatter
            note_data = self._parse_markdown_frontmatter(content)
            
            if not note_data:
                result.add_error(filepath, "无效的 Markdown 格式（缺少 Frontmatter）")
                return 0, result
            
            # 导入笔记
            note_id = self._import_note(note_data, conflict_policy)
            
            if note_id > 0:
                result.imported = 1
            elif note_id == 0:
                result.skipped = 1
            
            return note_id, result
            
        except Exception as e:
            result.add_error(filepath, str(e))
            return 0, result
    
    def import_json_file(self, filepath: str, conflict_policy: str = CONFLICT_SKIP) -> ImportResult:
        """
        导入 JSON 文件（可包含多个笔记）
        
        Args:
            filepath: 文件路径
            conflict_policy: 冲突处理策略
            
        Returns:
            导入结果
        """
        result = ImportResult()
        
        try:
            # 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证格式
            if 'notes' not in data:
                result.add_error(filepath, "无效的 JSON 格式（缺少 notes 字段）")
                return result
            
            # 导入每个笔记
            for note_data in data['notes']:
                try:
                    note_id = self._import_note(note_data, conflict_policy)
                    
                    if note_id > 0:
                        result.imported += 1
                    elif note_id == 0:
                        result.skipped += 1
                        
                except Exception as e:
                    result.add_error(f"Note {note_data.get('id', 'unknown')}", str(e))
            
            return result
            
        except Exception as e:
            result.add_error(filepath, str(e))
            return result
    
    def import_markdown_directory(self, dirpath: str, conflict_policy: str = CONFLICT_SKIP) -> ImportResult:
        """
        批量导入目录下的所有 Markdown 文件
        
        Args:
            dirpath: 目录路径
            conflict_policy: 冲突处理策略
            
        Returns:
            导入结果
        """
        result = ImportResult()
        
        dir_path = Path(dirpath)
        if not dir_path.exists():
            result.add_error(dirpath, "目录不存在")
            return result
        
        # 获取所有 Markdown 文件
        md_files = list(dir_path.glob("*.md"))
        
        for md_file in md_files:
            try:
                note_id, file_result = self.import_markdown_file(str(md_file), conflict_policy)
                
                result.imported += file_result.imported
                result.skipped += file_result.skipped
                result.errors.extend(file_result.errors)
                    
            except Exception as e:
                result.add_error(str(md_file), str(e))
        
        return result
    
    def _parse_markdown_frontmatter(self, content: str) -> Optional[dict]:
        """
        解析 Markdown Frontmatter
        
        格式：
        ---
        title: 标题
        tags: ["标签 1", "标签 2"]
        ---
        
        内容...
        """
        # 匹配 Frontmatter
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            return None
        
        frontmatter_str = match.group(1)
        body = match.group(2)
        
        # 解析 YAML（简化版）
        note_data = {
            'content': body.strip()
        }
        
        # 解析每个字段
        for line in frontmatter_str.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 解析值
                if value.startswith('[') and value.endswith(']'):
                    # JSON 数组
                    try:
                        value = json.loads(value)
                    except:
                        pass
                elif value.startswith('"') and value.endswith('"'):
                    # 引号字符串
                    value = value[1:-1]
                
                note_data[key] = value
        
        return note_data
    
    def _import_note(self, note_data: dict, conflict_policy: str) -> int:
        """
        导入单个笔记
        
        Args:
            note_data: 笔记数据
            conflict_policy: 冲突处理策略
            
        Returns:
            笔记 ID（0 表示跳过，-1 表示错误）
        """
        # 提取字段
        title = note_data.get('title', '无标题')
        content = note_data.get('content', '')
        tags = note_data.get('tags', [])
        created_at = note_data.get('created_at')
        updated_at = note_data.get('updated_at')
        
        # 检查是否已存在（通过标题匹配）
        cursor = self.db.execute("""
            SELECT id FROM notes WHERE title = ?
        """, (title,))
        
        existing = cursor.fetchone()
        
        if existing:
            if conflict_policy == self.CONFLICT_SKIP:
                return 0  # 跳过
            
            elif conflict_policy == self.CONFLICT_OVERWRITE:
                # 更新现有笔记
                return self._update_note(existing['id'], title, content, tags, created_at, updated_at)
            
            elif conflict_policy == self.CONFLICT_MERGE:
                # 保留较新的版本
                cursor = self.db.execute("SELECT updated_at FROM notes WHERE id = ?", (existing['id'],))
                existing_updated = cursor.fetchone()['updated_at']
                
                if updated_at and updated_at > existing_updated:
                    return self._update_note(existing['id'], title, content, tags, created_at, updated_at)
                else:
                    return 0  # 跳过
        
        # 创建新笔记
        return self._create_note(title, content, tags, created_at, updated_at)
    
    def _create_note(self, title: str, content: str, tags: list, created_at: str = None, updated_at: str = None) -> int:
        """创建新笔记"""
        if not created_at:
            created_at = datetime.now().isoformat()
        if not updated_at:
            updated_at = created_at
        
        cursor = self.db.execute("""
            INSERT INTO notes (title, content, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (title, content, json.dumps(tags, ensure_ascii=False), created_at, updated_at))
        
        self.db.commit()
        return cursor.lastrowid
    
    def _update_note(self, note_id: int, title: str, content: str, tags: list, created_at: str = None, updated_at: str = None) -> int:
        """更新现有笔记"""
        if not updated_at:
            updated_at = datetime.now().isoformat()
        
        self.db.execute("""
            UPDATE notes
            SET title = ?, content = ?, tags = ?, updated_at = ?
            WHERE id = ?
        """, (title, content, json.dumps(tags, ensure_ascii=False), updated_at, note_id))
        
        self.db.commit()
        return note_id
