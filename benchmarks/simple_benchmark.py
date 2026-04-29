"""
MemoMind 简单性能基准测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import random
import string
import tracemalloc
from pathlib import Path

from core.database import Database
from core.search_service import SearchService
from core.version_service import VersionService
from core.tag_service import TagService
from core.link_service import LinkService
from core.export_service import ExportService


class SimpleBenchmark:
    """简单基准测试"""
    
    def __init__(self):
        self.db = Database(":memory:")
        self.search = SearchService(self.db)
        self.versions = VersionService(self.db)
        self.tags = TagService(self.db)
        self.links = LinkService(self.db)
        self.export = ExportService(self.db)
        
        tracemalloc.start()
    
    def setup(self, note_count: int = 1000):
        """生成测试数据"""
        print(f"Generating {note_count} test notes...")
        
        tags_pool = ["AI", "技术", "编程", "Python", "机器学习", "深度学习", 
                     "数据库", "搜索", "标签", "版本", "链接", "笔记"]
        
        for i in range(note_count):
            title = f"Note {i}"
            content = f"Content about {' '.join(random.choices(tags_pool, k=3))}."
            content += " Lorem ipsum dolor sit amet. " * random.randint(5, 15)
            
            tags = random.sample(tags_pool, random.randint(1, 4))
            
            self.db.execute("""
                INSERT INTO notes (title, content, tags)
                VALUES (?, ?, ?)
            """, (title, content, json.dumps(tags)))
            
            if (i + 1) % 1000 == 0:
                print(f"  已生成 {i + 1}/{note_count} 条笔记")
        
        self.db.commit()
        
        # 创建标签
        for tag in tags_pool:
            self.tags.create_tag(tag)
        
        # 创建版本
        for i in range(min(note_count, 100)):
            self.versions.save_version(i + 1, f"Title {i}", f"Content {i}", [])
        
        # 创建链接
        for i in range(min(note_count - 1, 50)):
            self.links.db.execute("""
                INSERT INTO note_links (source_note_id, target_note_id)
                VALUES (?, ?)
            """, (i + 1, i + 2))
        self.links.db.commit()
        
        print(f"Test data generation complete")
    
    def measure(self, name: str, func, *args, **kwargs) -> float:
        """测量函数执行时间"""
        # 预热
        func(*args, **kwargs)
        
        # 正式测量
        times = []
        iterations = 10
        
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"  {name}: {avg_time:.2f}ms (min: {min_time:.2f}ms, max: {max_time:.2f}ms)")
        
        return avg_time
    
    def run(self, note_count: int = 1000):
        """运行基准测试"""
        print("=" * 60)
        print(f"MemoMind 性能基准测试")
        print(f"笔记数量：{note_count}")
        print("=" * 60)
        
        # 设置数据
        self.setup(note_count)
        
        # 搜索性能
        print("\nSearch Performance Tests:")
        self.measure("Basic search", self.search.search, "AI")
        self.measure("Multi-keyword search", self.search.search, "AI technology")
        
        # 版本性能
        print("\nVersion History Performance Tests:")
        self.measure("Version list", self.versions.get_versions, 1)
        
        # 标签性能
        print("\nTag Performance Tests:")
        self.measure("Tag list", self.tags.get_all_tags)
        self.measure("Tag tree", self.tags.get_tag_tree)
        
        # 链接性能
        print("\nLink Performance Tests:")
        self.measure("Outgoing links", self.links.get_outgoing_links, 1)
        self.measure("Incoming links", self.links.get_incoming_links, 1)
        
        # 内存使用
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print("\n" + "=" * 60)
        print("性能测试结果汇总:")
        print("=" * 60)
        print(f"  内存使用: {current / (1024*1024):.2f}MB (峰值: {peak / (1024*1024):.2f}MB)")
        print("=" * 60)
        
        self.db.close()


if __name__ == '__main__':
    benchmark = SimpleBenchmark()
    benchmark.run(note_count=1000)
