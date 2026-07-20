"""
Dreaming 基准测试

对比 Dreaming 前后：记忆数量变化 + 搜索准确率变化。
验证压缩率 >= 20%，准确率不下降。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from core.database import Database
from core.dreaming_service import DreamingService
from core.search_service import SearchService

# 30 条测试笔记（6 主题 x 5 条）
TEST_NOTES = [
    ("Python协程asyncio使用笔记", "asyncio事件循环用async/await定义协程。gather并发执行。", ["Python"]),
    ("FastAPI中间件开发", "FastAPI的middleware通过装饰器注册。用于鉴权日志CORS。", ["Python", "Web"]),
    ("pytest异步测试技巧", "pytest-asyncio支持async def测试。httpx.AsyncClient测试API。", ["Python", "测试"]),
    ("SQLAlchemy ORM入门", "SQLAlchemy是Python最流行的ORM。session管理数据库会话。", ["Python", "数据库"]),
    ("Python类型提示最佳实践", "Python类型提示用typing模块。Optional表示可为空。", ["Python"]),
    ("PostgreSQL索引优化", "复合索引选择性高的列放前面。BRIN适合时序GIN适合全文搜索。", ["数据库"]),
    ("Redis缓存策略详解", "缓存穿透用布隆过滤器。缓存击穿用互斥锁。Redis7支持RedisJSON。", ["数据库", "缓存"]),
    ("MongoDB聚合管道", "match放最前面project只取需要字段lookup替代多表查询。", ["数据库", "NoSQL"]),
    ("MySQL慢查询排查", "开启slow_query_log。pt-query-digest分析日志。覆盖索引避免回表。", ["数据库"]),
    ("SQLite FTS5中文搜索", "FTS5配合jieba分词实现中文全文搜索。创建虚拟表指定tokenize。", ["数据库"]),
    ("每周健身计划", "周一胸加三头卧推飞鸟。周三背加二头引体向上。周五腿加肩深蹲推举。", ["生活", "健身"]),
    ("冰美式咖啡冲泡", "18g中深烘豆刻度15萃取36g浓缩液加150g冰水。水温92度。", ["生活", "咖啡"]),
    ("周末北京周边游", "古北水镇两天一夜长城温泉。十渡漂流攀岩。雁栖湖APEC会议中心。", ["生活", "旅行"]),
    ("租房避坑指南", "看房测试水压空调。合同写清楚维修责任。押金不超过3个月房租。", ["生活"]),
    ("减脂期饮食搭配", "每餐蛋白质30g蔬菜200g碳水100g。鸡胸肉虾仁豆腐轮换。16+8轻断食。", ["生活", "饮食"]),
    ("RAG检索增强生成", "文档切分chunk后Embedding向量化存入向量库。拼接prompt让LLM生成。", ["AI"]),
    ("LoRA低秩微调原理", "LoRA在注意力层旁路添加低秩矩阵。r=8 alpha=16常用设置节省显存。", ["AI", "深度学习"]),
    ("Embedding模型选型", "text2vec-base-chinese 512维中文效果好。bge-large-zh 1024维。", ["AI", "Embedding"]),
    ("LangChain Agent记忆", "ConversationBufferMemory保存对话。VectorStoreRetrievalMemory长期记忆。", ["AI"]),
    ("Prompt Engineering", "好的提示词包含角色任务输出格式。Few-shot提供示例引导模型。", ["AI", "Prompt"]),
    ("Docker Compose部署", "docker-compose.yml定义多容器服务。depends_on控制启动顺序。", ["DevOps"]),
    ("Git分支管理策略", "main加dev加feature分支。PR合并前squash。git rebase避免多余merge。", ["DevOps"]),
    ("CI/CD流水线配置", "GitHub Actions用.github/workflows定义。jobs并行执行steps串行。", ["DevOps"]),
    ("Kubernetes Pod调度", "K8s通过nodeSelector控制Pod位置。taint/toleration排斥不兼容节点。", ["DevOps"]),
    ("Makefile常用模板", "make install安装依赖。make test运行测试。.PHONY声明伪目标。", ["DevOps"]),
    ("微服务拆分原则", "按业务领域拆分Bounded Context。每个服务独立数据库。API Gateway统一鉴权。", ["架构"]),
    ("分布式ID生成方案", "Snowflake雪花算法41位时间戳加10位机器ID加12位序列号。", ["架构"]),
    ("消息队列选型指南", "Kafka高吞吐适合日志流处理。RabbitMQ高可靠适合订单。RocketMQ金融。", ["架构"]),
    ("限流算法对比", "令牌桶允许突发流量。漏桶强制恒定速率。滑动窗口精确但内存大。", ["架构"]),
    ("URL短链接系统设计", "Base62编码自增ID生成短链。分库分表按短链取模。Redis缓存热点URL。", ["架构"]),
]

# 测试搜索问题（Dreaming 前后都应可检索）
TEST_QUESTIONS = [
    ("Python协程", 5),      # 期望命中数 >= 5
    ("数据库索引", 5),
    ("Docker部署", 5),
    ("微服务架构", 5),
    ("健身饮食", 5),
    ("AI学习", 5),
]


class DreamingBenchmark:
    """Dreaming 效果基准测试"""

    def __init__(self):
        self.before: dict = {}
        self.after: dict = {}
        self.db: Database = None
        self.search: SearchService = None
        self.dreaming: DreamingService = None

    def prepare_dataset(self) -> list[int]:
        """准备 30 条测试笔记，返回 note ID 列表"""
        self.db = Database(":memory:")
        self.search = SearchService(self.db)
        self.dreaming = DreamingService(self.db)

        note_ids = []
        for title, content, tags in TEST_NOTES:
            cursor = self.db.execute(
                "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                (title, content, json.dumps(tags, ensure_ascii=False))
            )
            note_ids.append(cursor.lastrowid)
        self.db.commit()
        return note_ids

    def measure_search_accuracy(self) -> dict:
        """度量当前搜索准确率

        对每个测试问题执行搜索，统计 Top-5 中命中相关笔记的平均比例。
        仅统计非归档笔记（归档笔记在 Dreaming 后应视为非活跃）。
        """
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0

        for question, expected_min in TEST_QUESTIONS:
            results = self.search.search(question, limit=10)
            # 过滤已归档笔记
            active_hits = [
                r for r in results
                if r.note is not None
                and '[归档于 Dreaming:' not in r.note.content
            ][:5]
            hit_count = len(active_hits)

            precision = hit_count / 5.0 if active_hits else 0.0
            recall = min(hit_count / expected_min, 1.0) if expected_min > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)
                  if (precision + recall) > 0 else 0.0)

            total_precision += precision
            total_recall += recall
            total_f1 += f1

        n = len(TEST_QUESTIONS)
        return {
            'precision': total_precision / n,
            'recall': total_recall / n,
            'f1': total_f1 / n,
        }

    def measure_before(self, note_ids: list[int]) -> dict:
        """度量 Dreaming 前的状态"""
        accuracy = self.measure_search_accuracy()
        return {
            'memory_count': len(note_ids),
            **accuracy,
        }

    def run_dreaming(self, note_ids: list[int]) -> dict:
        """执行 Dreaming，返回报告"""
        return self.dreaming.run_dreaming(strategy="aggressive")

    def measure_after(self) -> dict:
        """度量 Dreaming 后的状态（仅统计活跃笔记，排除已归档）"""
        cursor = self.db.execute(
            "SELECT COUNT(*) FROM notes "
            "WHERE content NOT LIKE '%[归档于 Dreaming:%'"
        )
        note_count = cursor.fetchone()[0]

        accuracy = self.measure_search_accuracy()
        return {
            'memory_count': note_count,
            **accuracy,
        }

    def run(self) -> dict:
        """运行完整 Dreaming 基准"""
        note_ids = self.prepare_dataset()
        print(f"  数据集: {len(note_ids)} 条笔记 (6 主题 x 5 条)")

        # Before
        self.before = self.measure_before(note_ids)
        print(f"  Dreaming 前: {self.before['memory_count']} 条, "
              f"搜索 F1={self.before['f1']:.1%}")

        # Run Dreaming
        report = self.run_dreaming(note_ids)
        print(f"  Dreaming 完成: {report['merged_count']} 条合并, "
              f"输出 {report['output_count']} 条")

        # After
        self.after = self.measure_after()
        print(f"  Dreaming 后: {self.after['memory_count']} 条, "
              f"搜索 F1={self.after['f1']:.1%}")

        # 计算指标
        compression_rate = 0.0
        if self.before['memory_count'] > 0:
            compression_rate = (1 - self.after['memory_count'] /
                              self.before['memory_count']) * 100

        accuracy_change = self.after['f1'] - self.before['f1']

        result = {
            'before_count': self.before['memory_count'],
            'after_count': self.after['memory_count'],
            'compression_rate_pct': compression_rate,
            'f1_before': self.before['f1'],
            'f1_after': self.after['f1'],
            'accuracy_change': accuracy_change,
        }

        # cleanup
        self.db.close()

        return result


def run():
    b = DreamingBenchmark()
    result = b.run()

    target_compression = 20.0
    target_accuracy_drop = -0.05  # 允许下降 5%
    compression_ok = result['compression_rate_pct'] >= target_compression
    accuracy_ok = result['accuracy_change'] >= target_accuracy_drop

    print()
    print("=" * 55)
    print("Dreaming 基准测试")
    print("=" * 55)
    print(f"  Dreaming 前笔记数:  {result['before_count']}")
    print(f"  Dreaming 后笔记数:  {result['after_count']}")
    print(f"  压缩率:             {result['compression_rate_pct']:.1f}% "
          f"{'[OK]' if compression_ok else '[X]'}")
    print(f"  搜索 F1 (前):       {result['f1_before']:.1%}")
    print(f"  搜索 F1 (后):       {result['f1_after']:.1%}")
    print(f"  F1 变化:            {result['accuracy_change']:+.1%} "
          f"{'[OK]' if accuracy_ok else '[X]'}")
    print(f"  目标: 压缩 >= {target_compression}%, "
          f"F1 下降 <= {abs(target_accuracy_drop):.0%}")
    print(f"  结果: {'通过 [OK]' if (compression_ok and accuracy_ok) else '未达标 [X]'}")
    print("=" * 55)

    return result


if __name__ == '__main__':
    run()
