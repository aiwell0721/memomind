"""
搜索延迟基准测试

测试不同数据规模下的搜索延迟 (P50/P95/P99)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json, time, random, statistics
from pathlib import Path
from core.database import Database
from core.search_service import SearchService

TAGS_POOL = ["AI", "Python", "数据库", "前端", "DevOps", "安全", "架构",
             "生活", "旅行", "学习", "工作", "笔记", "技术"]

QUERIES = [
    "Python异步编程",
    "数据库索引",
    "Docker部署",
    "React前端",
    "安全漏洞",
    "性能优化",
    "机器学习",
    "微服务架构",
    "旅行攻略",
    "学习笔记",
]


def generate_notes(db: Database, count: int):
    """生成指定数量的测试笔记"""
    for i in range(count):
        title = f"笔记{i} Python异步编程 数据库优化"
        content = f"第{i}条笔记内容。"
        # 加一些可搜索的中文内容
        content += random.choice([
            "关于Python协程和异步编程的详细说明",
            "PostgreSQL数据库索引优化策略分析",
            "Docker容器化部署最佳实践指南",
            "React前端框架组件设计模式",
            "Web应用安全漏洞扫描与防护措施",
        ])
        content += f" 编号{i}结束。"
        tags = random.sample(TAGS_POOL, random.randint(1, 3))
        db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content, json.dumps(tags, ensure_ascii=False))
        )
    db.commit()


def measure_latency(search: SearchService, query: str, warmup: int = 3,
                    iterations: int = 30) -> dict:
    """测量单次搜索延迟"""
    # 预热
    for _ in range(warmup):
        search.search(query, limit=10)

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        search.search(query, limit=10)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    times.sort()
    return {
        'p50': statistics.median(times),
        'p95': times[int(len(times) * 0.95)] if times else 0,
        'p99': times[int(len(times) * 0.99)] if times else 0,
        'avg': statistics.mean(times),
        'min': min(times),
        'max': max(times),
    }


def run():
    print("=" * 70)
    print("搜索延迟基准测试")
    print("=" * 70)

    all_results = {}

    for scale in [500, 1000, 2000]:
        db = Database(":memory:")
        search = SearchService(db)

        print(f"\n数据规模: {scale} 条笔记")
        print("-" * 50)
        generate_notes(db, scale)

        scale_results = {}
        for query in QUERIES:
            r = measure_latency(search, query)
            scale_results[query] = r

        # 汇总各查询的延迟
        p50s = [r['p50'] for r in scale_results.values()]
        p95s = [r['p95'] for r in scale_results.values()]
        p99s = [r['p99'] for r in scale_results.values()]

        summary = {
            'p50': statistics.mean(p50s),
            'p95': statistics.mean(p95s),
            'p99': statistics.mean(p99s),
        }
        all_results[scale] = summary

        print(f"  P50: {summary['p50']:.2f}ms  P95: {summary['p95']:.2f}ms  P99: {summary['p99']:.2f}ms")

        db.close()

    # 汇总表
    print(f"\n{'='*70}")
    print(f"{'规模':<10} {'P50':<10} {'P95':<10} {'P99':<10} {'目标':<12}")
    print("-" * 55)
    target = 50  # P95 < 50ms
    for scale, r in sorted(all_results.items()):
        ok = "[OK]" if r['p95'] < target else "[X]"
        print(f"{scale:<10} {r['p50']:<10.2f} {r['p95']:<10.2f} {r['p99']:<10.2f} P95<{target}ms {ok}")

    p95_2k = all_results[2000]['p95']
    passed = p95_2k < target
    print(f"\n2000条笔记 P95: {p95_2k:.2f}ms 目标 <{target}ms -> {'通过 [OK]' if passed else '未达标 [X]'}")

    return all_results


if __name__ == '__main__':
    run()
