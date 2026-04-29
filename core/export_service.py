"""
MemoMind 导出服务 - 支持 Markdown 和 JSON 格式
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from .database import Database


class ExportService:
    """笔记导出服务"""
    
    def __init__(self, db: Database):
        """
        初始化导出服务
        
        Args:
            db: 数据库实例
        """
        self.db = db
    
    def export_note_to_markdown(self, note_id: int, include_versions: bool = False) -> str:
        """
        导出单个笔记为 Markdown 格式
        
        Args:
            note_id: 笔记 ID
            include_versions: 是否包含版本历史
            
        Returns:
            Markdown 字符串
        """
        # 获取笔记
        cursor = self.db.execute("""
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE id = ?
        """, (note_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Note {note_id} not found")
        
        # 解析标签
        tags = json.loads(row['tags']) if row['tags'] else []
        
        # 构建 Frontmatter
        frontmatter = [
            "---",
            f"title: {self._escape_yaml(row['title'])}",
            f"tags: {json.dumps(tags, ensure_ascii=False)}",
            f"created_at: {row['created_at']}",
            f"updated_at: {row['updated_at']}",
            "---",
            ""
        ]
        
        # 添加内容
        markdown = "\n".join(frontmatter) + row['content']
        
        # 添加版本历史（可选）
        if include_versions:
            markdown += "\n\n---\n\n## 版本历史\n\n"
            versions = self._get_versions(note_id)
            for i, version in enumerate(versions, 1):
                markdown += f"### 版本 {version['version_number']} ({version['created_at']})\n\n"
                markdown += f"{version['content']}\n\n"
                if version.get('change_summary'):
                    markdown += f"> 变更说明：{version['change_summary']}\n\n"
        
        return markdown
    
    def export_note_to_dict(self, note_id: int, include_versions: bool = False) -> dict:
        """
        导出单个笔记为字典（用于 JSON 导出）
        
        Args:
            note_id: 笔记 ID
            include_versions: 是否包含版本历史
            
        Returns:
            笔记字典
        """
        cursor = self.db.execute("""
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE id = ?
        """, (note_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Note {note_id} not found")
        
        note = {
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
        
        if include_versions:
            note['versions'] = self._get_versions(note_id)
        
        return note
    
    def export_all_to_markdown_files(self, output_dir: str, include_versions: bool = False) -> List[str]:
        """
        导出所有笔记为 Markdown 文件
        
        Args:
            output_dir: 输出目录
            include_versions: 是否包含版本历史
            
        Returns:
            生成的文件路径列表
        """
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 获取所有笔记
        cursor = self.db.execute("""
            SELECT id, title FROM notes ORDER BY id
        """)
        
        files = []
        for row in cursor.fetchall():
            # 生成文件名（使用 ID 避免重名）
            safe_title = self._safe_filename(row['title'])
            filename = f"{row['id']}_{safe_title}.md"
            filepath = output_path / filename
            
            # 导出笔记
            markdown = self.export_note_to_markdown(row['id'], include_versions)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            files.append(str(filepath))
        
        return files
    
    def export_all_to_json(self, output_path: str, include_versions: bool = False) -> str:
        """
        导出所有笔记为 JSON 文件
        
        Args:
            output_path: 输出文件路径
            include_versions: 是否包含版本历史
            
        Returns:
            输出文件路径
        """
        # 获取所有笔记
        cursor = self.db.execute("""
            SELECT id FROM notes ORDER BY id
        """)
        
        notes = []
        for row in cursor.fetchall():
            note = self.export_note_to_dict(row['id'], include_versions)
            notes.append(note)
        
        # 构建导出数据结构
        export_data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'total_notes': len(notes),
            'notes': notes
        }
        
        # 写入文件
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return str(output_file)
    
    def _get_versions(self, note_id: int) -> List[dict]:
        """获取笔记的版本历史"""
        cursor = self.db.execute("""
            SELECT version_number, title, content, tags, created_at, change_summary, is_tagged, tag_name
            FROM note_versions
            WHERE note_id = ?
            ORDER BY version_number DESC
        """, (note_id,))
        
        versions = []
        for row in cursor.fetchall():
            versions.append({
                'version_number': row['version_number'],
                'title': row['title'],
                'content': row['content'],
                'tags': json.loads(row['tags']) if row['tags'] else [],
                'created_at': row['created_at'],
                'change_summary': row['change_summary'],
                'is_tagged': bool(row['is_tagged']),
                'tag_name': row['tag_name']
            })
        
        return versions
    
    def _escape_yaml(self, text: str) -> str:
        """转义 YAML 特殊字符"""
        # 简单处理：如果包含特殊字符，用引号包裹
        if ':' in text or '#' in text or text.startswith('-') or text.startswith('['):
            return f'"{text}"'
        return text
    
    def _safe_filename(self, title: str) -> str:
        """生成安全的文件名"""
        # 替换非法字符
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe_title = title
        for char in unsafe_chars:
            safe_title = safe_title.replace(char, '_')
        
        # 限制长度
        return safe_title[:50]
