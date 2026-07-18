"""
中文搜索质量基准测试

测试 FTS5 关键词搜索 + TF-IDF 语义搜索的混合检索质量。
度量：召回率(Recall)、精确率(Precision)、F1
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from core.database import Database
from core.search_service import SearchService
from core.semantic_service import SemanticService

# 50 条测试数据
TEST_NOTES = [
    ("Python协程asyncio使用指南", "asyncio是Python的异步编程库。事件循环管理协程调度，await等待协程完成。gather并发执行多个协程，create_task创建后台任务。", ["Python", "异步编程"]),
    ("FastAPI中间件开发教程", "FastAPI中间件通过@app.middleware注册。在请求前后执行逻辑，常用于身份验证、日志记录和CORS跨域处理。", ["Python", "Web开发"]),
    ("SQLAlchemy ORM最佳实践", "SQLAlchemy是Python最流行的ORM框架。session管理数据库会话，relationship定义表关联。异步支持需用asyncpg驱动。", ["Python", "数据库"]),
    ("PostgreSQL索引优化技巧", "复合索引将选择性高的列放前面。EXPLAIN ANALYZE查看执行计划。BRIN索引适合大表时序数据，GIN适合全文搜索和JSONB。", ["数据库", "性能优化"]),
    ("Redis缓存策略详解", "Redis支持多种数据结构。缓存穿透用布隆过滤器，缓存击穿用互斥锁，缓存雪崩用随机过期时间。Redis7支持RedisJSON。", ["数据库", "缓存"]),
    ("MongoDB聚合管道优化", "match操作应放在管道最前面过滤数据。project只取需要的字段减少传输。lookup替代多表查询但注意性能。大数据量用allowDiskUse。", ["数据库", "NoSQL"]),
    ("Docker Compose生产部署", "docker-compose.yml定义多容器服务。depends_on控制启动顺序，healthcheck确保服务就绪。环境变量用.env文件统一管理。", ["DevOps", "容器化"]),
    ("Kubernetes Pod调度策略", "K8s通过nodeSelector和affinity控制Pod调度位置。taint/toleration排斥不兼容节点。resource limits防止资源争抢。", ["DevOps", "容器化"]),
    ("Git分支管理与协作流程", "Git Flow用main+develop+feature分支。PR合并前squash保持线性历史。git rebase避免多余merge commit。", ["DevOps", "版本控制"]),
    ("CI/CD流水线设计思路", "GitHub Actions通过YAML定义流水线。jobs并行执行加快速度，artifacts传递产物。matrix strategy做多环境测试。", ["DevOps", "自动化"]),
    ("React 18并发模式入门", "React 18的createRoot替代ReactDOM.render。Suspense支持Streaming SSR，useTransition标记低优先级更新，useDeferredValue延迟渲染。", ["前端", "React"]),
    ("Vue 3 Composition API实战", "Vue 3的setup()函数是组合式API入口。ref创建响应式变量，computed计算属性，watch监听变化。script setup语法糖更简洁。", ["前端", "Vue"]),
    ("TypeScript高级类型技巧", "泛型约束用extends，条件类型用T extends U ? X : Y，infer关键字推断类型变量。模板字面量类型拼接字符串。", ["前端", "TypeScript"]),
    ("Tailwind CSS实用技巧", "Tailwind用原子类组合样式。@apply抽取公共样式，theme扩展自定义设计令牌。jit模式按需生成CSS减小体积。", ["前端", "CSS"]),
    ("Next.js服务端渲染原理", "Next.js支持SSR和SSG两种预渲染。getServerSideProps每次请求执行，getStaticProps构建时执行。ISR增量静态再生成。", ["前端", "SSR"]),
    ("大模型RAG技术实现", "RAG流程分四步：文档切片、向量化存入向量库、用户查询检索相关片段、拼接提示词让LLM生成答案。chunk大小影响检索精度。", ["AI", "LLM"]),
    ("LangChain框架核心概念", "LangChain提供chains、agents、tools三大抽象。Chain串联多个LLM调用，Agent自主决策工具选择，Memory管理对话历史。", ["AI", "LLM"]),
    ("Prompt Engineering最佳实践", "好的提示词包含角色设定、任务描述、输出格式。Few-shot提供示例引导模型。Chain-of-Thought让模型展示推理过程提高准确率。", ["AI", "Prompt"]),
    ("Embedding模型选择指南", "text2vec-base-chinese 512维中文效果好。bge-large-zh 1024维MTEB榜首。m3e-base社区活跃文档齐全。选型看维度速度和语义精度。", ["AI", "Embedding"]),
    ("LoRA低秩微调原理", "LoRA在注意力层旁路添加低秩矩阵，只训练旁路参数。r=8 alpha=16是常用设置。相比全参微调节省90%以上显存。", ["AI", "深度学习"]),
    ("Linux常用命令效率提升", "grep -r递归搜索，find按名称时间查找文件。awk处理文本列，sed流式编辑。tmux分屏管理终端会话不中断任务。", ["工具", "Linux"]),
    ("Vim编辑器高效操作", "Vim模式：Normal移动编辑，Insert输入，Visual选择。hjkl方向键减少手移。宏录制q录制@回放。插件用vim-plug管理。", ["工具", "编辑器"]),
    ("Markdown写作规范", "Markdown用#分级标题。代码块指定语言高亮。表格用|分隔列。脚注[^1]添加注释。任务列表- [ ]表示待办。", ["工具", "写作"]),
    ("正则表达式速查手册", "\\d匹配数字\\w匹配字母。*零或多次+一或多次？零或一次。()分组捕获，(?:)非捕获组。前后查找(?<=)和(?=)。", ["工具", "编程"]),
    ("JSON数据处理技巧", "jq命令行处理JSON。'.field'提取字段，'.[]'迭代数组，'select()'条件过滤。Python用json.loads解析json.dumps序列化。", ["工具", "数据处理"]),
    ("健身增肌训练计划", "推拉腿三分化：推日胸肩三头，拉日背二头，腿日深蹲硬拉。每个动作4组8-12次。渐进超负荷每周加重。蛋白质每天1.6g/kg体重。", ["生活", "健身"]),
    ("减脂饮食搭配原则", "控制热量缺口每天300-500大卡。碳水蛋白质脂肪比例4:3:3。粗粮替代精制碳水。少油少盐多用香料。16+8轻断食有效控制摄入。", ["生活", "饮食"]),
    ("手冲咖啡入门指南", "粉水比1:15-1:17黄金区间。水温88-92度浅烘高深烘低。闷蒸30秒释放二氧化碳。一刀流简单稳定，三段式层次丰富。", ["生活", "咖啡"]),
    ("北京周末徒步路线", "香山到植物园穿越约4小时。长城箭扣段险峻风景好。西山森林公园步道好走适合新手。凤凰岭奇石怪峰地貌独特。", ["生活", "户外"]),
    ("租房经验与避坑总结", "看房检查水压空调隔音。合同明确维修责任和违约金条款。拍照记录现有损坏避免退房扣押金。中介费通常是一个月租金。", ["生活", "租房"]),
    ("微服务架构设计原则", "每个服务独立数据库避免耦合。API Gateway统一入口做鉴权限流。服务间异步通信用消息队列解耦。分布式链路追踪排查调用链。", ["架构", "微服务"]),
    ("分布式系统CAP理论", "CAP三者不可兼得：一致性Consistency所有节点同时看到相同数据，可用性Availability每个请求都有响应，分区容错Partition Tolerance网络故障仍运行。", ["架构", "分布式"]),
    ("消息队列Kafka核心设计", "Kafka用Topic组织消息Partition分区并行。Producer发送Consumer消费。offset记录消费位置。ISR机制保证数据可靠性。", ["架构", "消息队列"]),
    ("数据库分库分表方案", "垂直拆分按业务模块分库。水平拆分按主键hash取模分表。Sharding-JDBC中间件透明路由。全局ID用Snowflake雪花算法生成。", ["架构", "数据库"]),
    ("负载均衡Nginx配置", "upstream定义后端服务器池。轮询round-robin默认策略，least_conn最少连接，ip_hash会话保持。健康检查自动剔除故障节点。", ["架构", "负载均衡"]),
    ("产品需求文档PRD写作", "PRD包含背景目标、用户故事、功能描述、验收标准。用户故事格式：作为XX我想要XX以便XX。MoSCoW法则区分需求优先级。", ["产品", "文档"]),
    ("敏捷开发Scrum实践", "Sprint固定2周迭代周期。Daily Standup每天15分钟同步进度。Sprint Review展示成果收集反馈。Retro回顾改进过程。", ["产品", "敏捷"]),
    ("用户研究方法总结", "定性方法：用户访谈挖掘深层需求，可用性测试发现操作问题。定量方法：问卷调查统计偏好，A/B测试数据驱动决策。", ["产品", "用户研究"]),
    ("数据分析Pandas入门", "DataFrame是Pandas核心数据结构。read_csv读取文件，groupby分组聚合，merge连接表。fillna填充缺失值dropna删除空值。", ["数据", "Python"]),
    ("数据可视化Matplotlib指南", "plt.figure创建画布。折线图plot柱状图bar散点图scatter。subplot排列子图。设置标题标签图例保存图片。", ["数据", "可视化"]),
    ("网络协议HTTP详解", "HTTP是无状态协议。GET查询POST创建PUT全量更新PATCH部分更新DELETE删除。状态码2xx成功4xx客户端错误5xx服务端错误。", ["网络", "协议"]),
    ("TCP三次握手四次挥手", "连接建立三次握手：SYN同步SYN-ACK确认ACK。连接断开四次挥手：FIN结束ACK确认FIN结束ACK确认。TIME_WAIT等待2MSL。", ["网络", "TCP"]),
    ("HTTPS加密原理", "HTTPS用TLS加密HTTP。非对称加密交换会话密钥，对称加密传输数据。证书链验证服务器身份。HSTS强制浏览器使用HTTPS。", ["网络", "安全"]),
    ("WebSocket实时通信", "WebSocket全双工通信单个TCP连接。Upgrade握手从HTTP升级。心跳ping/pong保持连接。相比轮询减少延迟和带宽消耗。", ["网络", "WebSocket"]),
    ("JWT认证实现方案", "JWT三段式：Header算法类型Payload用户数据Signature签名。access_token短期15分钟refresh_token长期7天。黑名单处理登出。", ["安全", "认证"]),
    ("密码存储最佳实践", "不要存明文密码。bcrypt加盐哈希防彩虹表。Argon2id是目前最佳选择对抗GPU暴力破解。密码强度要求最少8位含大小写数字符号。", ["安全", "密码学"]),
    ("常见Web安全漏洞防御", "XSS转义用户输入防脚本注入。CSRF用token验证请求来源。SQL注入用参数化查询。点击劫持设置X-Frame-Options头。", ["安全", "Web安全"]),
    ("代码审查Checklist", "检查逻辑是否正确边界条件是否覆盖。命名是否清晰自解释。是否有不必要的复杂度。测试是否覆盖核心路径。安全漏洞是否已防范。", ["工程", "代码质量"]),
    ("技术文档写作规范", "先说结论金字塔结构。代码示例可直接运行。图表辅助复杂流程。标题具体不宽泛。定期更新保持时效性。面向目标读者选择深度。", ["工程", "文档"]),
    ("性能优化方法论", "先测量后优化找瓶颈。常见手段：缓存减少重复计算，批量减少IO次数，异步化提升吞吐，索引加速查询。过早优化是万恶之源。", ["工程", "性能"]),
]

# 使用与笔记内容共享关键词的查询（测试 FTS5 + jieba 的检索质量）
TEST_QUERIES = [
    ("asyncio协程", [0]),
    ("FastAPI中间件", [1]),
    ("SQLAlchemy ORM", [2]),
    ("PostgreSQL索引", [3]),
    ("Redis缓存", [4]),
    ("MongoDB管道", [5]),
    ("Docker Compose", [6]),
    ("Kubernetes调度", [7]),
    ("Git分支rebase", [8]),
    ("GitHub Actions CI", [9]),
    ("React并发Suspense", [10]),
    ("Vue组合式API", [11]),
    ("TypeScript泛型", [12]),
    ("Tailwind原子类", [13]),
    ("Next.js SSR", [14]),
    ("RAG文档切分", [15]),
    ("LangChain Agent", [16]),
    ("Prompt提示词", [17]),
    ("Embedding模型选型", [18]),
    ("LoRA微调", [19]),
    ("Linux grep awk", [20]),
    ("Vim编辑器Normal", [21]),
    ("Markdown写作", [22]),
    ("正则表达式", [23]),
    ("JSON jq", [24]),
    ("健身增肌", [25]),
    ("减脂饮食", [26]),
    ("手冲咖啡", [27]),
    ("北京徒步", [28]),
    ("租房合同", [29]),
    ("微服务API Gateway", [30]),
    ("CAP理论", [31]),
    ("Kafka消息队列", [32]),
    ("分库分表", [33]),
    ("Nginx负载均衡", [34]),
    ("PRD产品文档", [35]),
    ("Scrum敏捷", [36]),
    ("用户访谈", [37]),
    ("Pandas DataFrame", [38]),
    ("Matplotlib可视化", [39]),
    ("HTTP协议状态码", [40]),
    ("TCP握手挥手", [41]),
    ("HTTPS TLS加密", [42]),
    ("WebSocket实时", [43]),
    ("JWT token认证", [44]),
    ("bcrypt密码哈希", [45]),
    ("XSS CSRF防御", [46]),
    ("代码审查", [47]),
    ("技术文档写作", [48]),
    ("性能优化", [49]),
]


def build_dataset(db: Database) -> list[int]:
    note_ids = []
    for title, content, tags in TEST_NOTES:
        cursor = db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content, json.dumps(tags, ensure_ascii=False))
        )
        note_ids.append(cursor.lastrowid)
    db.commit()
    return note_ids


def search_fts5(search: SearchService, query: str, limit: int = 10) -> list[int]:
    """FTS5 关键词搜索，返回命中的 note id 列表"""
    try:
        results = search.search(query, limit=limit)
        return [r.note.id for r in results if r.note is not None]
    except Exception:
        return []


def search_hybrid(search: SearchService, semantic: SemanticService,
                  query: str, limit: int = 10) -> list[int]:
    """FTS5 + TF-IDF 混合搜索"""
    try:
        fts5_results = search.search(query, limit=20)
        fts5_ids = [r.note.id for r in fts5_results if r.note is not None]
    except Exception:
        fts5_ids = []

    try:
        semantic_results = semantic.semantic_search(query, limit=20)
        semantic_ids = [r.note.id for r in semantic_results if r.note is not None]
    except Exception:
        semantic_ids = []

    # 合并去重
    seen = set()
    merged = []
    for nid in fts5_ids:
        if nid not in seen:
            merged.append(nid)
            seen.add(nid)
    for nid in semantic_ids:
        if nid not in seen:
            merged.append(nid)
            seen.add(nid)

    return merged[:limit]


def evaluate(name: str, search_fn, note_ids: list[int]) -> dict:
    """评估搜索质量"""
    results = []
    for query, relevant in TEST_QUERIES:
        retrieved = search_fn(query)
        retrieved_set = set(retrieved) & set(note_ids)
        relevant_set = set(relevant) & set(note_ids)

        tp = len(relevant_set & retrieved_set)
        precision = tp / len(retrieved_set) if retrieved_set else 0.0
        recall = tp / len(relevant_set) if relevant_set else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        results.append({'precision': precision, 'recall': recall, 'f1': f1})

    avg_p = sum(r['precision'] for r in results) / len(results)
    avg_r = sum(r['recall'] for r in results) / len(results)
    avg_f1 = sum(r['f1'] for r in results) / len(results)

    print(f"  {name}: P={avg_p:.1%}  R={avg_r:.1%}  F1={avg_f1:.1%}")

    return {'avg_precision': avg_p, 'avg_recall': avg_r, 'avg_f1': avg_f1}


def run():
    db = Database(":memory:")
    search = SearchService(db)
    semantic = SemanticService(db)

    print("构建测试数据集...")
    note_ids = build_dataset(db)
    print(f"  已插入 {len(note_ids)} 条中文笔记\n")

    print("搜索质量对比:")
    print("-" * 45)
    fts5_result = evaluate("FTS5", lambda q: search_fts5(search, q), note_ids)
    hybrid_result = evaluate("FTS5+TF-IDF", lambda q: search_hybrid(search, semantic, q), note_ids)

    print("-" * 45)
    f1_fts5 = fts5_result['avg_f1']
    f1_hybrid = hybrid_result['avg_f1']
    target = 0.75
    passed = f1_hybrid >= target
    print(f"FTS5 基线 F1: {f1_fts5:.1%}")
    print(f"混合搜索 F1: {f1_hybrid:.1%}")
    print(f"目标: F1 >= {target:.0%}")
    print(f"结果: {'通过 [OK]' if passed else '未达标 [X]'}")

    db.close()
    return hybrid_result


if __name__ == '__main__':
    run()
