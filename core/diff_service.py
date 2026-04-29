"""
MemoMind 版本对比服务
"""

import difflib
from typing import List, Optional
from dataclasses import dataclass
from .version_service import Version


@dataclass
class Diff:
    """版本对比结果"""
    version_a_id: int
    version_b_id: int
    title_diff: List[str]  # 标题差异行
    content_diff: List[str]  # 内容差异行
    added_lines: int  # 新增行数
    removed_lines: int  # 删除行数
    
    def summary(self) -> str:
        """生成变更摘要"""
        parts = []
        if self.added_lines > 0:
            parts.append(f"新增 {self.added_lines} 行")
        if self.removed_lines > 0:
            parts.append(f"删除 {self.removed_lines} 行")
        return "，".join(parts) if parts else "无变更"


class DiffService:
    """版本对比服务"""
    
    def __init__(self):
        """初始化对比服务"""
        pass
    
    def compare_texts(self, text_a: str, text_b: str) -> List[str]:
        """
        对比两段文本
        
        Args:
            text_a: 原文本
            text_b: 新文本
            
        Returns:
            diff 结果列表（统一格式）
        """
        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile='version_a',
            tofile='version_b',
            n=3  # 上下文行数
        )
        
        return list(diff)
    
    def compare_versions(self, version_a: Version, version_b: Version) -> Diff:
        """
        对比两个版本
        
        Args:
            version_a: 版本 A
            version_b: 版本 B
            
        Returns:
            对比结果
        """
        # 对比标题
        title_diff = self.compare_texts(version_a.title, version_b.title)
        
        # 对比内容
        content_diff = self.compare_texts(version_a.content, version_b.content)
        
        # 统计变更
        added_lines = sum(1 for line in content_diff if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in content_diff if line.startswith('-') and not line.startswith('---'))
        
        return Diff(
            version_a_id=version_a.id,
            version_b_id=version_b.id,
            title_diff=title_diff,
            content_diff=content_diff,
            added_lines=added_lines,
            removed_lines=removed_lines
        )
    
    def compare_with_current(
        self,
        version: Version,
        current_title: str,
        current_content: str
    ) -> Diff:
        """
        对比版本与当前笔记
        
        Args:
            version: 历史版本
            current_title: 当前标题
            current_content: 当前内容
            
        Returns:
            对比结果
        """
        # 对比标题
        title_diff = self.compare_texts(version.title, current_title)
        
        # 对比内容
        content_diff = self.compare_texts(version.content, current_content)
        
        # 统计变更
        added_lines = sum(1 for line in content_diff if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in content_diff if line.startswith('-') and not line.startswith('---'))
        
        return Diff(
            version_a_id=version.id,
            version_b_id=0,  # 当前版本 ID 为 0
            title_diff=title_diff,
            content_diff=content_diff,
            added_lines=added_lines,
            removed_lines=removed_lines
        )
    
    def generate_summary(self, diff: Diff) -> str:
        """
        生成变更摘要
        
        Args:
            diff: 对比结果
            
        Returns:
            摘要文本
        """
        parts = []
        
        # 检查标题是否变更
        if diff.title_diff:
            parts.append("修改了标题")
        
        # 添加行数统计
        if diff.added_lines > 0:
            parts.append(f"新增 {diff.added_lines} 行")
        
        if diff.removed_lines > 0:
            parts.append(f"删除 {diff.removed_lines} 行")
        
        return "，".join(parts) if parts else "无变更"
    
    def format_diff_html(self, diff: Diff) -> str:
        """
        格式化 diff 为 HTML（带高亮）
        
        Args:
            diff: 对比结果
            
        Returns:
            HTML 字符串
        """
        html = ["<div class='version-diff'>"]
        
        # 标题差异
        if diff.title_diff:
            html.append("<h4>标题变更：</h4>")
            html.append("<pre class='diff'>")
            for line in diff.title_diff:
                if line.startswith('+'):
                    html.append(f"<span class='diff-add'>{line}</span>")
                elif line.startswith('-'):
                    html.append(f"<span class='diff-remove'>{line}</span>")
                else:
                    html.append(f"<span class='diff-context'>{line}</span>")
            html.append("</pre>")
        
        # 内容差异
        if diff.content_diff:
            html.append("<h4>内容变更：</h4>")
            html.append("<pre class='diff'>")
            for line in diff.content_diff:
                if line.startswith('+'):
                    html.append(f"<span class='diff-add'>{line}</span>")
                elif line.startswith('-'):
                    html.append(f"<span class='diff-remove'>{line}</span>")
                else:
                    html.append(f"<span class='diff-context'>{line}</span>")
            html.append("</pre>")
        
        html.append("</div>")
        return "".join(html)
    
    def format_diff_plain(self, diff: Diff) -> str:
        """
        格式化 diff 为纯文本
        
        Args:
            diff: 对比结果
            
        Returns:
            纯文本字符串
        """
        lines = ["版本对比结果：", ""]
        
        # 标题差异
        if diff.title_diff:
            lines.append("标题变更：")
            lines.extend(diff.title_diff)
            lines.append("")
        
        # 内容差异
        if diff.content_diff:
            lines.append("内容变更：")
            lines.extend(diff.content_diff)
        
        return "\n".join(lines)
