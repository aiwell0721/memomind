"""
LoCoMo 简化版基准测试

测试记忆检索准确率：插入对话记忆，查询事实，评估回答准确率。
简化版：50 Q&A pairs，度量 Single-hop 准确率。

LoCoMo 原始论文: Maharana et al., "LoCoMo: A Benchmark for Long-Context
Modeling in Multi-Party Conversations"
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import Optional
from core.database import Database
from core.search_service import SearchService
from core.semantic_service import SemanticService

# ============================================================
# 30 条模拟对话记忆
# ============================================================
CONVERSATION_MEMORIES = [
    # --- 项目技术讨论 ---
    {"title": "技术选型会议记录",
     "content": "会议决定后端用FastAPI+SQLAlchemy，前端用React+TypeScript。数据库选PostgreSQL因为需要全文搜索和JSON支持。部署用Docker Compose。王工负责后端框架搭建，李工负责前端初始化。",
     "tags": ["项目", "技术选型"]},
    {"title": "数据库Schema设计讨论",
     "content": "用户表users含id、email、password_hash、created_at。笔记表notes含id、user_id、title、content、tags(json)、created_at、updated_at。用户和笔记一对多关系。密码用bcrypt加盐哈希存储。",
     "tags": ["项目", "数据库"]},
    {"title": "API接口规范讨论",
     "content": "RESTful风格，JSON格式。POST /api/auth/register注册，POST /api/auth/login登录返回JWT token。GET /api/notes搜索笔记支持?q=关键词&tags=标签。JWT过期时间设为24小时。",
     "tags": ["项目", "API"]},
    {"title": "前端路由设计方案",
     "content": "首页/dashboard显示最近笔记和统计。搜索页/search支持全文搜索和标签过滤。笔记详情/notes/:id可编辑标题内容和标签。设置页/settings管理个人偏好和API密钥。",
     "tags": ["项目", "前端"]},
    {"title": "部署环境配置记录",
     "content": "生产服务器Ubuntu 22.04，4核16G内存100G SSD。Nginx做反向代理和HTTPS终端。Let's Encrypt免费SSL证书自动续期。应用用systemd管理服务自动重启。备份用cron每天凌晨3点执行。",
     "tags": ["项目", "运维"]},

    # --- 学习笔记 ---
    {"title": "Rust语言学习Day1",
     "content": "Rust所有权系统是核心创新：每个值只有一个所有者owner，离开作用域自动释放。引用&借用不转移所有权。可变引用&mut同一时间只能有一个。这些规则在编译期检查无运行时开销。",
     "tags": ["学习", "Rust"]},
    {"title": "Rust语言学习Day2",
     "content": "Rust的enum比C语言的更强大，可以携带数据。Option<T>表示可能为空的值有Some和None两个变体。Result<T,E>表示可能失败有Ok和Err变体。模式匹配match必须穷尽所有可能。",
     "tags": ["学习", "Rust"]},
    {"title": "Rust语言学习Day3",
     "content": "Rust的trait类似其他语言的接口interface。impl为类型实现trait。derive宏自动生成常见trait实现。泛型用trait约束T: TraitName。生命周期标注'a表示引用有效期。",
     "tags": ["学习", "Rust"]},
    {"title": "系统设计学习笔记",
     "content": "设计短链接系统：Base62编码自增ID生成短码。Redis缓存映射关系。分库分表按短码hash取模。用布隆过滤器拦截无效短码查询防止缓存穿透。QPS预估10万读1万写。",
     "tags": ["学习", "系统设计"]},
    {"title": "DDIA读书笔记第一章",
     "content": "可靠性：系统在故障时仍能正常工作。可扩展性：系统负载增长时保持性能。可维护性：代码易于理解和修改。这三者是优秀软件系统的核心目标。故障和错误是不同的概念。",
     "tags": ["学习", "读书"]},

    # --- 个人备忘录 ---
    {"title": "2026年体检预约",
     "content": "体检预约在7月20日上午8点北京协和医院体检中心。需要空腹8小时以上，前一天晚上10点后禁食。带身份证和社保卡。项目包括血常规、心电图、腹部B超和胸片。",
     "tags": ["个人", "健康"]},
    {"title": "银行卡挂失记录",
     "content": "7月15日发现招商银行卡遗失。立即致电95555挂失，客服工号3287。新卡3-5个工作日寄到。旧卡关联的自动扣款需要更新：房贷每月5号，水电费每月10号，话费每月15号。",
     "tags": ["个人", "财务"]},
    {"title": "爸妈结婚纪念日计划",
     "content": "父母结婚35周年在8月12日。计划：订淮扬府餐厅包间(已付定金500元)，准备太湖珍珠项链作为礼物(预算3000元)，邀请舅舅和小姨两家共8人。蛋糕提前一天在味多美订。",
     "tags": ["个人", "家庭"]},
    {"title": "笔记本维修记录",
     "content": "MacBook Pro 2023款屏幕出现竖条纹。7月10日送修Apple Store三里屯店。维修单号WX20260710001。诊断是显示排线问题，保内免费更换屏幕总成。预计7月17日取机。",
     "tags": ["个人", "数码"]},
    {"title": "北京居住证续签",
     "content": "居住证有效期到2026年8月30日。提前30天可续签即8月1日起。需要材料：身份证原件复印件、租房合同原件复印件、房东身份证复印件、近期一寸白底照片2张。在社区警务室办理。",
     "tags": ["个人", "证件"]},

    # --- 工作日志 ---
    {"title": "2026-07-10 工作日志",
     "content": "完成用户认证模块的JWT刷新token功能。修复了搜索接口对空查询返回500的bug改成返回空列表。协助前端联调了笔记创建和编辑接口，解决了CORS配置遗漏的问题。",
     "tags": ["工作", "开发"]},
    {"title": "2026-07-11 工作日志",
     "content": "优化了笔记搜索性能：给tags列加索引后复杂标签查询从800ms降到20ms。FTS5的BM25排序算法验证通过。和产品经理讨论了标签自动补全的需求原型。",
     "tags": ["工作", "开发"]},
    {"title": "2026-07-14 工作日志",
     "content": "MCP Server 增加了list_workspaces工具支持多工作区。修复了权限校验绕过漏洞：before/after模式匹配不完整导致部分端点未受保护。测试覆盖从240增加到260。",
     "tags": ["工作", "开发"]},
    {"title": "2026-07-16 工作日志",
     "content": "语义搜索集成完成：TF-IDF+余弦相似度支持混合排序。中文分词切换为jieba替代之前的空格分割。去重功能scan_duplicates已能自动发现相似内容。消化建议suggest_consolidation支持手动触发。",
     "tags": ["工作", "开发"]},
    {"title": "季度总结-2026Q2",
     "content": "Q2完成了Phase 2-4交付：知识图谱、MCP Server、Web UI、用户系统。测试覆盖370+用例全部通过。技术债务：Phase 1的job system需要重写为异步架构，计划Q3处理。",
     "tags": ["工作", "总结"]},

    # --- 会议记录 ---
    {"title": "产品评审会议纪要",
     "content": "参会人：产品经理张总、技术负责人刘工、设计师小林。决定下一步重点做记忆增强功能Dreaming。竞品MindMemOS已实现95%准确率的记忆检索。时间线Q3完成原型。",
     "tags": ["会议", "产品"]},
    {"title": "技术评审会议纪要",
     "content": "评审了Dreaming方案的架构设计。决定用Embedding模型做聚类而非TF-IDF因为验证实验证明了TF-IDF在中文短文本上不可用。模型选了text2vec-base-chinese约400MB。",
     "tags": ["会议", "技术"]},
    {"title": "安全审计会议记录",
     "content": "外部安全团队完成了渗透测试。发现2个中危漏洞：API速率限制缺失、JWT密钥强度不够。3个低危：版本信息泄露、cookie未设httponly。修复时间两周内。",
     "tags": ["会议", "安全"]},
    {"title": "团建策划讨论",
     "content": "Q3团建预算人均500元共30人预算15000元。方案A：京郊两日拓展训练+烧烤。方案B：室内密室逃脱+聚餐。投票结果A:18票 B:8票。定方案A，时间8月22-23日。",
     "tags": ["会议", "团建"]},
    {"title": "客户需求评审会",
     "content": "客户方代表王经理提出需要批量导入功能支持Markdown和CSV格式。多语言支持先做英文和日文。数据导出需要支持Word文档格式.docx。这三项列入Phase 6需求池。",
     "tags": ["会议", "客户"]},

    # --- 旅行笔记 ---
    {"title": "云南旅行攻略",
     "content": "行程8天：昆明(1天)石林和大观楼。大理(2天)古城洱海骑行喜洲古镇。丽江(2天)古城玉龙雪山蓝月谷。香格里拉(2天)普达措松赞林寺。最后1天返程。总预算8000元含机票。",
     "tags": ["旅行", "攻略"]},
    {"title": "日本关西自由行",
     "content": "大阪2天道顿堀吃蟹道乐和章鱼烧加环球影城。京都3天清水寺金阁寺伏见稻荷大社岚山竹林。奈良1天东大寺喂鹿。交通买JR关西广域周游券。总花费约12000元。",
     "tags": ["旅行", "攻略"]},
    {"title": "杭州周末游记",
     "content": "西湖骑行一圈约15公里2小时。灵隐寺门票45元香火券30。龙井村品明前龙井80元一杯。外婆家西湖银泰店排队1小时推荐茶香鸡和西湖醋鱼。住青芝坞民宿300元一晚。",
     "tags": ["旅行", "游记"]},
    {"title": "自驾川西环线",
     "content": "成都出发5天：D1雅安泸定康定。D2新都桥塔公草原墨石公园。D3丹巴甲居藏寨。D4四姑娘山双桥沟。D5卧龙映秀回成都。海拔最高4400米注意高反备氧气瓶。",
     "tags": ["旅行", "自驾"]},
    {"title": "出差深圳记录",
     "content": "7月5日-7日深圳出差。住南山科技园亚朵酒店协议价450元/晚。拜访了腾讯和华为两家客户。腾讯对接人张工对MCP Server方案很感兴趣。差旅费总计3200元已提交报销。",
     "tags": ["旅行", "出差"]},
]

# ============================================================
# 50 个 Single-hop Q&A pairs — 查询使用与目标笔记共享的关键词
# ============================================================
QA_PAIRS = [
    # 项目技术相关 (10题)
    ("FastAPI技术选型后端框架", "FastAPI", "技术选型会议记录"),
    ("React TypeScript前端技术栈", "React和TypeScript", "技术选型会议记录"),
    ("PostgreSQL数据库选型", "PostgreSQL", "技术选型会议记录"),
    ("bcrypt密码存储", "bcrypt加盐哈希", "数据库Schema设计讨论"),
    ("users用户表", "users", "数据库Schema设计讨论"),
    ("JWT token认证", "JWT token", "API接口规范讨论"),
    ("JWT过期时间", "24小时", "API接口规范讨论"),
    ("Ubuntu生产服务器", "Ubuntu 22.04", "部署环境配置记录"),
    ("备份cron执行", "每天凌晨3点", "部署环境配置记录"),
    ("Let's Encrypt SSL证书", "Let's Encrypt免费SSL证书", "部署环境配置记录"),

    # 学习相关 (10题)
    ("Rust所有权系统", "所有权系统", "Rust语言学习Day1"),
    ("Rust可变引用限制", "同一时间只能有一个可变引用", "Rust语言学习Day1"),
    ("Option Some None", "Some和None", "Rust语言学习Day2"),
    ("Rust trait接口", "其他语言的接口interface", "Rust语言学习Day3"),
    ("Base62短链接编码", "Base62", "系统设计学习笔记"),
    ("布隆过滤器缓存穿透", "拦截无效短码查询防止缓存穿透", "系统设计学习笔记"),
    ("DDIA可靠性可扩展性可维护性", "可靠性、可扩展性和可维护性", "DDIA读书笔记第一章"),
    ("Rust作用域释放", "自动释放", "Rust语言学习Day1"),
    ("Rust enum携带数据", "可以携带数据", "Rust语言学习Day2"),
    ("Rust泛型trait约束", "trait", "Rust语言学习Day3"),

    # 个人备忘录 (10题)
    ("体检预约协和医院", "7月20日", "2026年体检预约"),
    ("体检协和医院", "北京协和医院", "2026年体检预约"),
    ("银行卡挂失95555", "3287", "银行卡挂失记录"),
    ("结婚纪念日8月12", "8月12日", "爸妈结婚纪念日计划"),
    ("结婚纪念日礼物预算", "3000元", "爸妈结婚纪念日计划"),
    ("MacBook Apple Store维修", "Apple Store三里屯店", "笔记本维修记录"),
    ("维修单号屏幕", "WX20260710001", "笔记本维修记录"),
    ("居住证到期续签", "2026年8月30日", "北京居住证续签"),
    ("居住证照片白底", "2张", "北京居住证续签"),
    ("体检空腹协和医院", "8小时以上", "2026年体检预约"),

    # 工作相关 (10题)
    ("空查询500bug", "搜索接口对空查询返回500", "2026-07-10 工作日志"),
    ("tags索引优化20ms", "20ms", "2026-07-11 工作日志"),
    ("MCP Server list_workspaces工具", "list_workspaces", "2026-07-14 工作日志"),
    ("Q2测试覆盖370", "370+", "季度总结-2026Q2"),
    ("TF-IDF余弦相似度语义搜索", "TF-IDF加余弦相似度", "2026-07-16 工作日志"),
    ("Q3 job system异步架构技术债务", "job system重写为异步架构", "季度总结-2026Q2"),
    ("scan_duplicates去重", "scan_duplicates", "2026-07-16 工作日志"),
    ("权限校验绕过漏洞修复", "权限校验绕过漏洞", "2026-07-14 工作日志"),
    ("CORS配置遗漏联调", "CORS配置遗漏", "2026-07-10 工作日志"),
    ("产品经理标签自动补全需求", "产品经理", "2026-07-11 工作日志"),

    # 综合类 (10题)
    ("Dreaming text2vec聚类模型", "text2vec-base-chinese", "技术评审会议纪要"),
    ("安全审计中危漏洞渗透测试", "2个", "安全审计会议记录"),
    ("团建预算人均500", "500元", "团建策划讨论"),
    ("团建方案A拓展训练", "方案A", "团建策划讨论"),
    ("云南旅行8天行程", "8天", "云南旅行攻略"),
    ("日本关西自由行12000", "12000元", "日本关西自由行"),
    ("杭州灵隐寺门票45", "45元", "杭州周末游记"),
    ("川西环线海拔4400", "4400米", "自驾川西环线"),
    ("深圳出差亚朵酒店", "亚朵酒店", "出差深圳记录"),
    ("客户需求markdown CSV导入", "Markdown和CSV格式", "客户需求评审会"),
]


def evaluate_locomo(name: str, search: SearchService,
                    semantic: SemanticService | None,
                    note_ids: list[int]) -> dict:
    """评估 LoCoMo 检索准确率（混合搜索）"""
    correct = 0
    failed = []

    for i, (question, expected_answer, source_title) in enumerate(QA_PAIRS):
        # FTS5 keyword search
        try:
            results = search.search(question, limit=5)
        except Exception:
            results = []

        # 合并语义搜索结果
        if semantic:
            semantic_results = semantic.semantic_search(question, limit=5)
            seen = {r.note.id for r in results if r.note is not None}
            for sr in semantic_results:
                if sr.note is not None and sr.note.id not in seen:
                    results.append(sr)
                    seen.add(sr.note.id)

        found = False
        for r in results[:5]:
            if r.note is None:
                continue
            content = r.note.content.lower()
            title = r.note.title.lower()
            expected_lower = expected_answer.lower()
            if expected_lower in content or expected_lower in title:
                found = True
                break

        if found:
            correct += 1
        else:
            failed.append({'id': i, 'question': question,
                           'expected': expected_answer, 'source': source_title})

    accuracy = correct / len(QA_PAIRS) if QA_PAIRS else 0.0
    print(f"  {name}: {correct}/{len(QA_PAIRS)} = {accuracy:.1%}")

    return {'correct': correct, 'total': len(QA_PAIRS),
            'accuracy': accuracy, 'failed': failed}


def run():
    db = Database(":memory:")
    search = SearchService(db)
    semantic = SemanticService(db)

    print(f"插入 {len(CONVERSATION_MEMORIES)} 条对话记忆...")
    note_ids = []
    for mem in CONVERSATION_MEMORIES:
        cursor = db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (mem['title'], mem['content'],
             json.dumps(mem['tags'], ensure_ascii=False))
        )
        note_ids.append(cursor.lastrowid)
    db.commit()

    print(f"评估 {len(QA_PAIRS)} 个问题...\n")

    # FTS5 only
    fts5_result = evaluate_locomo("FTS5", search, None, note_ids)

    # FTS5 + TF-IDF
    hybrid_result = evaluate_locomo("FTS5+TF-IDF", search, semantic, note_ids)

    print("\n" + "=" * 60)
    print(f"LoCoMo 简化版结果")
    print("=" * 60)
    print(f"FTS5 基线:     {fts5_result['accuracy']:.1%}")
    print(f"FTS5+TF-IDF:   {hybrid_result['accuracy']:.1%}")
    print(f"目标: >= 70% (Local) / >= 85% (Cloud)")
    passed = hybrid_result['accuracy'] >= 0.70
    print(f"结果: {'通过 [OK]' if passed else '未达标 [X]'}")

    if hybrid_result['failed']:
        print(f"\n混合搜索未命中 ({len(hybrid_result['failed'])} 题):")
        for f in hybrid_result['failed'][:5]:
            print(f"  Q: {f['question']}")
            print(f"  期望: {f['expected']}  来源: {f['source']}")

    db.close()
    return hybrid_result


if __name__ == '__main__':
    run()
