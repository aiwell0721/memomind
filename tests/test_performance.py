"""性能测试脚本"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import random
from core.database import Database
from core.search_service import SearchService

# 创建测试数据库
db = Database('test_performance.db')
search = SearchService(db)

# 清空旧数据
db.execute("DELETE FROM notes")
db.execute("DELETE FROM notes_fts")

# 生成测试数据
print("生成测试数据...")
sample_notes = [
    ("人工智能基础", "人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。", ["AI", "技术"]),
    ("机器学习入门", "机器学习是人工智能的核心，通过算法让计算机从数据中学习规律。", ["AI", "机器学习"]),
    ("深度学习教程", "深度学习是机器学习的一个分支，使用多层神经网络进行特征学习。", ["AI", "深度学习"]),
    ("自然语言处理", "自然语言处理研究如何让计算机理解和生成人类语言。", ["NLP", "AI"]),
    ("计算机视觉", "计算机视觉研究如何让计算机'看'懂图像和视频。", ["CV", "AI"]),
    ("推荐系统", "推荐系统通过分析用户行为和偏好，为用户推荐感兴趣的内容。", ["推荐", "算法"]),
    ("数据挖掘", "数据挖掘从大量数据中发现模式和知识。", ["数据", "分析"]),
    ("大数据技术", "大数据技术处理海量、高速、多样化的数据。", ["数据", "技术"]),
    ("云计算平台", "云计算提供可扩展的计算资源和服务。", ["云", "技术"]),
    ("区块链应用", "区块链是分布式数据存储、点对点传输、共识机制等技术的集成应用。", ["区块链", "技术"]),
]

# 插入 1000 条测试数据
import json
for i in range(100):
    for title, content, tags in sample_notes:
        title = f"{title}_{i}"
        db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content + f" 这是第{i}条测试数据。", json.dumps(tags))
        )

print(f"已插入 {100 * len(sample_notes)} 条测试数据")

# 性能测试
print("\n性能测试：")
print("-" * 50)

# 测试 1：基础搜索（英文 - FTS5 友好）
start = time.time()
results = search.search("AI")
end = time.time()
print(f"基础搜索（AI）: {(end-start)*1000:.2f}ms - {len(results)} 条结果")

# 测试 2：多关键词搜索
start = time.time()
results = search.search("AI 技术")
end = time.time()
print(f"多关键词搜索（AI 技术）: {(end-start)*1000:.2f}ms - {len(results)} 条结果")

# 测试 3：标签过滤
start = time.time()
results = search.search("机器学习", tags=["AI"])
end = time.time()
print(f"标签过滤搜索（AI）: {(end-start)*1000:.2f}ms - {len(results)} 条结果")

# 测试 4：自动补全
start = time.time()
suggestions = search.suggest("AI")
end = time.time()
print(f"自动补全（AI）: {(end-start)*1000:.2f}ms - {len(suggestions)} 条建议")

# 测试 5：分页查询
start = time.time()
results = search.search("技术", offset=0, limit=10)
end = time.time()
print(f"分页查询（第 1 页）: {(end-start)*1000:.2f}ms - {len(results)} 条结果")

start = time.time()
results = search.search("技术", offset=50, limit=10)
end = time.time()
print(f"分页查询（第 6 页）: {(end-start)*1000:.2f}ms - {len(results)} 条结果")

# 测试 6：统计数量
start = time.time()
count = search.count("")
end = time.time()
print(f"统计总数：{(end-start)*1000:.2f}ms - {count} 条笔记")

print("-" * 50)
print("性能测试完成！")

# 清理
db.close()
print("\n测试数据库：test_performance.db（可手动删除）")
