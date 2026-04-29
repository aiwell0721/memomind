"""
MemoMind 导出服务 - PR-021 增强版
支持 Markdown、JSON、Obsidian、Notion、PDF 格式
"""

import json
import os
import re
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from .database import Database


class ExportService:
    """笔记导出服务"""
    
    def __init__(self, db: Database):
        self.db = db
    
    # ==================== 基础导出 ====================
    
    def export_note_to_markdown(self, note_id: int, include_versions: bool = False) -> str:
        """导出单个笔记为 Markdown 格式"""
        cursor = self.db.execute("""
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes WHERE id = ?
        """, (note_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Note {note_id} not found")
        
        tags = json.loads(row['tags']) if row['tags'] else []
        
        frontmatter = [
            "---",
            f"title: {self._escape_yaml(row['title'])}",
            f"tags: {json.dumps(tags, ensure_ascii=False)}",
            f"created_at: {row['created_at']}",
            f"updated_at: {row['updated_at']}",
            "---",
            ""
        ]
        
        markdown = "\n".join(frontmatter) + row['content']
        
        if include_versions:
            markdown += "\n\n---\n\n## 版本历史\n\n"
            versions = self._get_versions(note_id)
            for i, version in enumerate(versions, 1):
                markdown += f"### 版本 {version['version_number']} ({version['created_at']})\n\n"
                markdown += f"{version['content']}\n\n"
        
        return markdown
    
    def export_note_to_dict(self, note_id: int, include_versions: bool = False) -> dict:
        """导出单个笔记为字典"""
        cursor = self.db.execute("""
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes WHERE id = ?
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
        """导出所有笔记为 Markdown 文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        cursor = self.db.execute("SELECT id, title FROM notes ORDER BY id")
        
        files = []
        for row in cursor.fetchall():
            safe_title = self._safe_filename(row['title'])
            filename = f"{row['id']}_{safe_title}.md"
            filepath = output_path / filename
            
            markdown = self.export_note_to_markdown(row['id'], include_versions)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            files.append(str(filepath))
        
        return files
    
    def export_all_to_json(self, output_path: str, include_versions: bool = False) -> str:
        """导出所有笔记为 JSON 文件"""
        cursor = self.db.execute("SELECT id FROM notes ORDER BY id")
        
        notes = []
        for row in cursor.fetchall():
            note = self.export_note_to_dict(row['id'], include_versions)
            notes.append(note)
        
        export_data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'total_notes': len(notes),
            'notes': notes
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return str(output_file)
    
    # ==================== Obsidian 兼容导出 ====================
    
    def export_to_obsidian(self, output_dir: str, include_links: bool = True, 
                          include_tags: bool = True) -> List[str]:
        """
        导出为 Obsidian 兼容格式
        
        - 使用 [[双向链接]] 语法
        - YAML frontmatter 兼容 Obsidian
        - 保留标签系统
        
        Args:
            output_dir: 输出目录
            include_links: 是否转换链接为 [[笔记]] 格式
            include_tags: 是否保留标签
            
        Returns:
            生成的文件路径列表
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 获取所有笔记用于链接转换
        cursor = self.db.execute("SELECT id, title FROM notes")
        title_map = {}
        for row in cursor.fetchall():
            title_map[row['id']] = row['title']
        
        cursor = self.db.execute("SELECT id, title, content, tags, created_at, updated_at FROM notes ORDER BY id")
        
        files = []
        for row in cursor.fetchall():
            safe_title = self._safe_filename(row['title'])
            filename = f"{safe_title}.md"
            filepath = output_path / filename
            
            # 解析标签
            tags = json.loads(row['tags']) if row['tags'] else []
            
            # Obsidian frontmatter
            frontmatter = ["---"]
            if include_tags and tags:
                # Obsidian 标签格式：- tag 或 #tag
                frontmatter.append("tags:")
                for tag in tags:
                    frontmatter.append(f"  - {tag}")
            frontmatter.append(f"created: {row['created_at']}")
            frontmatter.append(f"modified: {row['updated_at']}")
            frontmatter.append("---")
            frontmatter.append("")
            
            # 内容处理
            content = row['content']
            if include_links:
                # 将 [[id:note_id]] 格式转换为 [[笔记标题]]
                for note_id, note_title in title_map.items():
                    if note_id != row['id']:
                        content = content.replace(
                            f"[[id:{note_id}]]", 
                            f"[[{note_title}]]"
                        )
            
            markdown = "\n".join(frontmatter) + content
            markdown += f"\n\n## 反向链接\n\n"
            
            # 添加入链（Obsidian 格式）
            if include_links:
                incoming = self._get_incoming_links(row['id'])
                if incoming:
                    for link in incoming:
                        source_title = title_map.get(link['source_id'], 'Unknown')
                        markdown += f"- [[{source_title}]]\n"
                else:
                    markdown += "无\n"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            files.append(str(filepath))
        
        return files
    
    # ==================== Notion 兼容导出 ====================
    
    def export_to_notion_csv(self, output_path: str) -> str:
        """
        导出为 Notion 兼容的 CSV 格式
        
        Notion 导入要求：
        - CSV 格式
        - 列：Name, Content, Tags, Created, Updated
        
        Args:
            output_path: 输出 CSV 路径
            
        Returns:
            输出文件路径
        """
        import csv
        
        cursor = self.db.execute("""
            SELECT title, content, tags, created_at, updated_at 
            FROM notes ORDER BY id
        """)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Content', 'Tags', 'Created', 'Updated'])
            
            for row in cursor.fetchall():
                tags = json.loads(row['tags']) if row['tags'] else []
                writer.writerow([
                    row['title'],
                    row['content'],
                    ', '.join(tags),
                    row['created_at'],
                    row['updated_at']
                ])
        
        return str(output_file)
    
    def export_to_notion_markdown(self, output_dir: str) -> List[str]:
        """
        导出为 Notion 兼容的 Markdown 格式
        
        Notion Markdown 要求：
        - 不使用 YAML frontmatter
        - 标题用 # 开头
        - 标签用内联格式
        
        Args:
            output_dir: 输出目录
            
        Returns:
            生成的文件路径列表
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        cursor = self.db.execute("SELECT id, title, content, tags FROM notes ORDER BY id")
        
        files = []
        for row in cursor.fetchall():
            safe_title = self._safe_filename(row['title'])
            filename = f"{safe_title}.md"
            filepath = output_path / filename
            
            tags = json.loads(row['tags']) if row['tags'] else []
            
            # Notion 格式：不用 frontmatter
            lines = [f"# {row['title']}", ""]
            if tags:
                tag_line = " ".join([f"`#{tag}`" for tag in tags])
                lines.append(tag_line)
                lines.append("")
            lines.append(row['content'])
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            files.append(str(filepath))
        
        return files
    
    # ==================== PDF 导出 ====================
    
    def export_note_to_pdf_html(self, note_id: int) -> str:
        """
        导出笔记为适合 PDF 转换的 HTML
        
        可用于 wkhtmltopdf 或 WeasyPrint 转换
        
        Args:
            note_id: 笔记 ID
            
        Returns:
            HTML 字符串
        """
        cursor = self.db.execute("""
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes WHERE id = ?
        """, (note_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Note {note_id} not found")
        
        tags = json.loads(row['tags']) if row['tags'] else []
        tag_html = "".join([f'<span class="tag">{tag}</span>' for tag in tags])
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{row['title']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; line-height: 1.6; }}
        h1 {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        .tags {{ margin-bottom: 20px; }}
        .tag {{ display: inline-block; background: #e0e0e0; padding: 2px 8px; border-radius: 4px; margin-right: 5px; font-size: 12px; }}
        pre {{ background: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        code {{ background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>{row['title']}</h1>
    <div class="meta">
        创建时间：{row['created_at']} | 更新时间：{row['updated_at']}
    </div>
    <div class="tags">{tag_html}</div>
    <div class="content">
        {row['content']}
    </div>
</body>
</html>"""
        
        return html
    
    def export_all_to_pdf_html(self, output_dir: str) -> List[str]:
        """导出所有笔记为 PDF 兼容 HTML 文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        cursor = self.db.execute("SELECT id FROM notes ORDER BY id")
        
        files = []
        for row in cursor.fetchall():
            safe_title = self._safe_filename(self._get_note_title(row['id']))
            filename = f"{safe_title}.html"
            filepath = output_path / filename
            
            html = self.export_note_to_pdf_html(row['id'])
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            
            files.append(str(filepath))
        
        return files
    
    # ==================== 辅助方法 ====================
    
    def _get_versions(self, note_id: int) -> List[dict]:
        """获取笔记的版本历史"""
        cursor = self.db.execute("""
            SELECT version_number, title, content, tags, created_at, change_summary
            FROM note_versions WHERE note_id = ? ORDER BY version_number DESC
        """, (note_id,))
        
        versions = []
        for row in cursor.fetchall():
            versions.append({
                'version_number': row['version_number'],
                'title': row['title'],
                'content': row['content'],
                'tags': json.loads(row['tags']) if row['tags'] else [],
                'created_at': row['created_at'],
                'change_summary': row['change_summary']
            })
        
        return versions
    
    def _get_incoming_links(self, note_id: int) -> List[dict]:
        """获取入链"""
        cursor = self.db.execute("""
            SELECT source_note_id FROM note_links WHERE target_note_id = ?
        """, (note_id,))
        return [{'source_id': row['source_note_id']} for row in cursor.fetchall()]
    
    def _get_note_title(self, note_id: int) -> str:
        """获取笔记标题"""
        cursor = self.db.execute("SELECT title FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return row['title'] if row else 'Unknown'
    
    def _escape_yaml(self, text: str) -> str:
        """转义 YAML 特殊字符"""
        if ':' in text or '#' in text or text.startswith('-') or text.startswith('['):
            return f'"{text}"'
        return text
    
    def _safe_filename(self, title: str) -> str:
        """生成安全的文件名"""
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe_title = title
        for char in unsafe_chars:
            safe_title = safe_title.replace(char, '_')
        return safe_title[:50]
