"""
MemoMind 性能基准测试框架
"""

import time
import json
import os
import random
import string
import tracemalloc
from typing import List, Dict, Optional
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入避免包路径问题
from api.client import MemoMind as MemoMindClient


class Benchmark:
    """性能基准测试框架"""
    
    def __init__(self, db_path: str = ":memory:"):
        """
        初始化基准测试
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.client: Optional[MemoMind] = None
        self.results: Dict = {}
    
    def setup(self, note_count: int = 1000):
        """
        生成测试数据
        
        Args:
            note_count: 笔记数量
        """
        print(f"📊 生成 {note_count} 条测试笔记...")
        
        # 启动内存追踪
        tracemalloc.start()
        
        # 创建数据库
        self.client = MemoMind(db_path=self.db_path)
        
        # 生成测试数据
        tags_pool = ["AI", "技术", "编程", "Python", "机器学习", "深度学习", 
                     "数据库", "搜索", "标签", "版本", "链接", "笔记"]
        
        for i in range(note_count):
            # 随机生成标题和内容
            title = f"笔记 {i}: {''.join(random.choices(string.ascii_letters, k=10))}"
            content = f"这是第 {i} 条笔记的内容。"
            content += " ".join(random.choices(tags_pool, k=random.randint(2, 5)))
            content += "\n" + "Lorem ipsum dolor sit amet. " * random.randint(5, 20)
            
            # 随机标签
            tags = random.sample(tags_pool, random.randint(1, 4))
            
            self.client.notes.create(title, content, tags)
            
            if (i + 1) % 1000 == 0:
                print(f"  已生成 {i + 1}/{note_count} 条笔记")
        
        # 创建标签
        for tag in tags_pool:
            self.client.tags.create(tag)
        
        # 创建版本
        for i in range(min(note_count, 100)):
            self.client.versions.save(i + 1, f"笔记 {i}", f"内容 {i}", [])
        
        # 创建链接
        for i in range(min(note_count - 1, 50)):
            self.client.links.create(i + 1, i + 2)
        
        print(f"✅ 测试数据生成完成")
    
    def measure(self, name: str, func, *args, **kwargs) -> float:
        """
        测量函数执行时间
        
        Args:
            name: 测试名称
            func: 被测函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            执行时间（毫秒）
        """
        # 预热
        func(*args, **kwargs)
        
        # 正式测量
        times = []
        iterations = 10
        
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # 转换为毫秒
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        self.results[name] = {
            'avg_ms': avg_time,
            'min_ms': min_time,
            'max_ms': max_time,
            'iterations': iterations
        }
        
        print(f"  {name}: {avg_time:.2f}ms (min: {min_time:.2f}ms, max: {max_time:.2f}ms)")
        
        return avg_time
    
    def test_search_performance(self):
        """测试搜索性能"""
        print("\n🔍 搜索性能测试:")
        
        # 基础搜索
        self.measure("基础搜索 (AI)", self.client.notes.search, "AI")
        
        # 多关键词搜索
        self.measure("多关键词搜索", self.client.notes.search, "AI 技术")
        
        # 标签过滤搜索
        self.measure("标签过滤搜索", self.client.notes.search, "技术", tags=["AI"])
        
        # 空查询
        self.measure("空查询", self.client.notes.search, "")
    
    def test_version_performance(self):
        """测试版本历史性能"""
        print("\n📝 版本历史性能测试:")
        
        note_id = 1
        self.measure("版本保存", self.client.versions.save, 
                    note_id, "Title", "Content", ["tag"])
        
        self.measure("版本列表", self.client.versions.list, note_id)
        
        self.measure("版本详情", self.client.versions.get, 1)
    
    def test_export_performance(self):
        """测试导出性能"""
        print("\n📤 导出性能测试:")
        
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            self.measure("Markdown 导出", 
                        self.client.export.export_all_to_markdown_files, tmpdir)
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            tmpfile = f.name
        
        try:
            self.measure("JSON 导出", self.client.export.export_all_to_json, tmpfile)
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
    
    def test_tag_performance(self):
        """测试标签性能"""
        print("\n🏷️ 标签性能测试:")
        
        self.measure("标签列表", self.client.tags.list)
        
        self.measure("标签树", self.client.tags.get_tree)
        
        self.measure("标签建议", self.client.tags.suggest, "AI")
    
    def test_link_performance(self):
        """测试链接性能"""
        print("\n🔗 链接性能测试:")
        
        note_id = 1
        self.measure("出链查询", self.client.links.get_outgoing, note_id)
        
        self.measure("入链查询", self.client.links.get_incoming, note_id)
        
        self.measure("链接图谱", self.client.links.get_graph)
    
    def get_memory_usage(self) -> Dict:
        """
        获取内存使用情况
        
        Returns:
            {'current_mb': float, 'peak_mb': float}
        """
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            'current_mb': current / (1024 * 1024),
            'peak_mb': peak / (1024 * 1024)
        }
    
    def run_all(self, note_count: int = 1000):
        """
        运行所有基准测试
        
        Args:
            note_count: 笔记数量
        """
        print("=" * 60)
        print(f"MemoMind 性能基准测试")
        print(f"笔记数量：{note_count}")
        print("=" * 60)
        
        # 设置测试数据
        self.setup(note_count)
        
        # 运行各项测试
        self.test_search_performance()
        self.test_version_performance()
        self.test_export_performance()
        self.test_tag_performance()
        self.test_link_performance()
        
        # 获取内存使用
        memory = self.get_memory_usage()
        self.results['memory'] = memory
        
        # 打印汇总
        print("\n" + "=" * 60)
        print("性能测试结果汇总:")
        print("=" * 60)
        
        for name, data in self.results.items():
            if name == 'memory':
                print(f"  内存使用: {data['current_mb']:.2f}MB (峰值: {data['peak_mb']:.2f}MB)")
            else:
                print(f"  {name}: {data['avg_ms']:.2f}ms")
        
        print("=" * 60)
        
        # 清理
        self.client.close()
        
        return self.results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MemoMind 性能基准测试')
    parser.add_argument('--notes', type=int, default=1000, help='笔记数量')
    parser.add_argument('--db', default=':memory:', help='数据库路径')
    parser.add_argument('--output', help='输出报告文件')
    
    args = parser.parse_args()
    
    benchmark = Benchmark(db_path=args.db)
    results = benchmark.run_all(note_count=args.notes)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 报告已保存到 {args.output}")


if __name__ == '__main__':
    main()
