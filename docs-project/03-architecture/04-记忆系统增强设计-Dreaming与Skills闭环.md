# 记忆系统增强设计：Dreaming 与 Skills 闭环

**文档版本**：v1.0  
**日期**：2026-07-16  
**状态**：设计阶段  
**关联竞品分析**：[01-product-concept/12-竞品分析-MindMemOS.md](../01-product-concept/12-竞品分析-MindMemOS.md)  
**关联现有架构**：[03-architecture/02-记忆系统架构.md](02-记忆系统架构.md)

---

## 1. 设计背景

### 1.1 问题

MemoMind 当前记忆系统存在以下瓶颈：

1. **记忆只增不减**：笔记/记忆创建后永久保留，长期使用后检索质量下降
2. **去重依赖手动**：`SemanticService.scan_duplicates()` 只能发现问题，合并需人工
3. **技能是静态的**：SKILL.md 文件不会从使用中进化
4. **无基准量化**：缺乏客观指标衡量记忆系统质量

### 1.2 灵感来源

MindMemOS 在 LoCoMo 基准上取得 SOTA（93.64），核心创新是 **Dreaming**（记忆压缩）和 **Skills 闭环**（技能自进化）。其 Dreaming 机制实现：

- 记忆数量减少 27.9%
- 准确率提升 4.5%

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **轻量优先** | 不引入 Kafka/Qdrant/Neo4j，复用现有 SQLite 基础设施 |
| **渐进式** | 在现有 `suggest_consolidation()` 基础上扩展，不推翻重来 |
| **可量化** | 每个 enhancement 必须有可测量的成功标准 |
| **本地优先** | 所有计算在本地完成，不依赖云端 LLM（但可选） |
| **先验证后实现** | TF-IDF 聚类方案在中文短文本上的效果必须先通过小规模验证实验确认 |

---

## 2. Dreaming 机制设计

### 2.1 概念

Dreaming 是一种**离线记忆巩固过程**，模拟人类睡眠时的记忆整理：

```
碎片记忆 → 主题聚类 → 合并去重 → 知识提纯 → 更新记忆库
```

与现有的 `suggest_consolidation()` 区别：

| 维度 | 现有 suggest_consolidation | Dreaming |
|------|---------------------------|----------|
| 触发方式 | 手动调用 | 定时 / 手动 / 阈值触发 |
| 处理范围 | 仅建议，不执行 | 自动执行合并 + 记录变更 |
| 压缩深度 | 主题聚类 + 合并建议 | 聚类 + 合并 + 摘要 + 遗忘 |
| 版本追溯 | 无 | 合并前后版本可回溯 |
| 知识提纯 | 无 | 从碎片中提取结构化知识 |

### 2.2 架构

> **2026-07-17 更新**：TF-IDF 聚类方案经 5.0 验证实验确认不可行（模拟数据 50 篇全部单元素簇）。**已切换为 Embedding 方案**，再次验证确认可行：50 篇模拟数据在阈值 0.70 下达到 56% 纯度 + 46% 压缩率，Obsidian 34 篇压缩率 82.4%。

**推荐参数**：
- 默认：`text2vec-base-chinese` + 余弦相似度 + 贪心聚类，阈值 0.70
- 保守（高纯度）：阈值 0.75，纯度 77%，压缩率 28%
- 激进（高压缩）：阈值 0.65，纯度 45%，压缩率 60%

```
┌─────────────────────────────────────────────────────────────┐
│                    DreamingService                           │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Clusterer   │  │  Merger      │  │  Extractor   │      │
│  │  主题聚类    │→│  合并去重    │→│  知识提纯    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↑                ↑                ↑                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Embedding   │  │  Diff Tracker │  │  AI Provider │      │
│  │  (text2vec)  │  │  版本追溯     │  │  (Local/Cloud)│     │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   DreamingPipeline                   │   │
│  │  1. Select memories (by age / access / importance)   │   │
│  │  2. Cluster by topic similarity (Embedding + KMeans) │   │
│  │  3. Merge each cluster → consolidated memory         │   │
│  │  4. Extract structured facts                         │   │
│  │  5. Archive originals (versioned)                    │   │
│  │  6. Update search index                              │   │
│  │  7. Emit dreaming report                             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 数据模型

```python
# Dreaming 会话记录
@dataclass
class DreamingSession:
    id: int
    started_at: datetime
    finished_at: datetime | None
    trigger: str  # 'manual' | 'scheduled' | 'threshold'
    status: str   # 'running' | 'completed' | 'failed'
    
    # 统计
    input_count: int       # 输入记忆数
    output_count: int      # 输出记忆数（合并后）
    merged_count: int      # 合并的记忆数
    archived_count: int    # 归档的原始记忆数
    extracted_facts: int   # 提取的知识点数

# Dreaming 变更记录（用于回溯）
@dataclass
class DreamingChange:
    id: int
    session_id: int
    change_type: str       # 'merge' | 'archive' | 'extract' | 'forget'
    source_ids: list[int]  # 原始记忆 ID 列表
    target_id: int | None  # 合并后记忆 ID
    diff_summary: str      # 变更摘要
    created_at: datetime
```

### 2.4 核心流程

#### Step 1: 选择待处理记忆

```python
def select_memories_for_dreaming(
    self,
    workspace_id: int,
    strategy: str = "default"
) -> list[Note]:
    """选择适合 Dreaming 的记忆
    
    策略：
    - default: 创建超过 7 天 + 访问次数 < 3 + 非置顶
    - aggressive: 所有非置顶记忆
    - conservative: 创建超过 30 天 + 访问次数 < 2
    """
```

#### Step 2: 主题聚类

```python
def cluster_memories(
    self,
    notes: list[Note],
    similarity_threshold: float = 0.65
) -> list[list[Note]]:
    """基于 TF-IDF + jieba 分词的聚类
    
    算法：
    1. 对每条记忆分词 + TF-IDF 向量化
    2. 计算两两余弦相似度
    3. 贪心聚类：相似度 > threshold 的归为一组
    4. 单元素簇跳过（无合并对象）
    """
```

#### Step 3: 合并去重

```python
def merge_cluster(
    self,
    cluster: list[Note],
    workspace_id: int
) -> Note:
    """合并一个记忆簇为单条记忆
    
    流程：
    1. 提取共有关键信息
    2. 生成合并摘要（AI Provider 辅助）
    3. 创建新记忆，保留所有标签的并集
    4. 原始记忆标记为 archived（不删除，可回溯）
    5. 转移链接关系到新记忆
    """
```

#### Step 4: 知识提纯

```python
def extract_facts(
    self,
    cluster: list[Note]
) -> list[dict]:
    """从记忆簇中提取结构化知识
    
    输出示例：
    [
        {"subject": "用户", "predicate": "偏好", "object": "冰美式"},
        {"subject": "项目", "predicate": "使用", "object": "SQLite + FTS5"},
    ]
    """
```

#### Step 5: 归档与索引更新

```python
def archive_originals(
    self,
    original_ids: list[int],
    merged_id: int,
    session_id: int
) -> None:
    """归档原始记忆，保留版本追溯
    
    - 原始记忆标记 metadata: {"archived": true, "merged_into": merged_id}
    - 记录 DreamingChange
    - 更新 FTS5 索引（归档记忆从搜索结果中排除）
    """
```

### 2.5 触发机制

| 触发方式 | 条件 | 说明 |
|----------|------|------|
| 手动 | CLI `memomind dream` | 用户主动触发 |
| 定时 | 每日凌晨 3:00（可配置） | 低峰时段自动执行 |
| 阈值 | 记忆数 > 500 且上次 Dreaming > 7 天 | 防止记忆膨胀 |

### 2.6 AI Provider 集成

复用现有 `core/ai_provider.py` 抽象层：

| Provider | 聚类 | 合并摘要 | 知识提取 |
|----------|------|----------|----------|
| Local（默认） | TF-IDF + 余弦相似度 | 规则拼接（首条+共有标签） | 正则 + 启发式 |
| OpenAI | Embedding + K-Means | GPT 摘要 | GPT 结构化提取 |
| Anthropic | Embedding + K-Means | Claude 摘要 | Claude 结构化提取 |

**原则**：Local 模式必须能独立工作，Cloud 模式是增强项。

### 2.7 回溯与安全

- **版本追溯**：每次合并生成 `DreamingChange` 记录，可回溯到原始记忆
- **软删除**：原始记忆只标记 archived，不物理删除
- **回滚**：`memomind dream rollback <session_id>` 可恢复一次 Dreaming 会话的所有变更
- **预览模式**：`memomind dream --dry-run` 只输出报告不执行变更

---

## 3. Skills 闭环（观察项）

> **状态**：⏸️ 暂不实施。先在代码中埋点记录使用模式，观察 1-2 个月数据量后决策。

### 3.1 暂缓理由

Skills 闭环依赖充足的用户反馈和使用数据。MindMemOS 在 SaaS + 多用户 + Cloud API 场景下反馈密度充足，但 MemoMind 作为本地个人工具：
- 单人 30 天的搜索/分类/标签数据量小，高频模式检测可能产出极少或无产出
- 用户主动反馈（"不好用"/"很好用"）在个人工具中极为稀疏
- 在数据基础不具备的情况下投入开发，整个闭环可能空转

### 3.2 埋点方案（低成本前置工作）

在现有 `ActivityLog` 中增加以下记录类型，积累数据供后续决策：

| 埋点类型 | 记录内容 | 用途 |
|----------|----------|------|
| `search_pattern` | 搜索关键词 + 时间戳 + workspace_id | 分析搜索模式频率 |
| `tag_pattern` | 创建笔记时的标签组合 | 分析分类习惯 |
| `co_access` | 同一会话内先后访问的笔记 ID 对 | 分析关联模式 |
| `skill_feedback` | 用户对自动推荐的显式反馈 | 稀疏但高价值 |

数据积累 1-2 个月后，运行 `PatternDetector` 分析：
- 若 **≥3 个高频模式**（频次 ≥ 5/30天）→ 启动 Skills 闭环设计
- 若 **< 3 个** → 继续观察或放弃此方向

**原设计方案（暂存，供后续参考）**：完整的数据模型（SkillCandidate / SkillExecution / PatternDetector / SkillGenerator / SkillExecutor / SkillEvolver）已归档，启动 Skills 闭环时可直接复用。

### 3.3 与现有系统的关系（暂存）

| 现有模块 | Skills 闭环复用方式 |
|----------|-------------------|
| `ActivityLog` | 埋点数据源，技能执行记录 |
| `NoteService` | 技能内容存储为特殊类型的 Note |
| `VersionService` | 技能版本管理复用版本基础设施 |
| `TagService` | 技能使用 `skill` 标签标识 |
| `AI Provider` | 技能生成/进化使用 AI Provider |

---

## 4. 基准测试框架

### 4.1 目标

建立 MemoMind 的客观性能基准，量化后续优化效果。

### 4.2 测试维度

| 维度 | 基准 | 指标 |
|------|------|------|
| 记忆检索准确率 | LoCoMo（简化版） | Single-hop / Multi-hop 准确率 |
| 记忆压缩效果 | Dreaming 前后对比 | 记忆数量变化 / 准确率变化 |
| 搜索延迟 | 自建 | P50 / P95 / P99 延迟 |
| 中文搜索质量 | 自建 | 召回率 / 精确率 / F1 |

### 4.3 实施方案

```python
# benchmarks/dreaming_benchmark.py
class DreamingBenchmark:
    """Dreaming 效果基准测试
    
    流程：
    1. 准备数据集（100 条对话记忆）
    2. 运行 Dreaming
    3. 对比前后：
       - 记忆数量
       - 搜索准确率（预设 10 个问题）
       - 搜索延迟
    """
```

---

## 5. 与 MindMemOS 的差异

| 维度 | MindMemOS | MemoMind 方案 |
|------|-----------|--------------|
| Dreaming 基础设施 | Kafka + Worker | SQLite + 后台线程 |
| 聚类算法 | 向量 Embedding + K-Means | Embedding (text2vec) + K-Means（TF-IDF 已验证不可行） |
| 知识提纯 | LLM 原生 | AI Provider 抽象（Local 规则 + Cloud LLM） |
| Skills 存储 | 独立 Skill 系统 | ⏸️ 观察项（先埋点，1-2 月后决策） |
| 触发机制 | Kafka 事件驱动 | 定时 / 手动 / 阈值 |
| 回溯 | 图数据库 | DreamingChange 表 + 软删除 |
| 基准测试 | LoCoMo + PersonaMem + MemoryAgentBench | LoCoMo 简化版 + 自建中文基准 |

---

## 6. 实现优先级

| 优先级 | 模块 | 理由 |
|--------|------|------|
| ✅ 已完成 | TF-IDF 聚类验证实验 | 34篇Obsidian + 50篇模拟 → TF-IDF 不可行，切换 Embedding |
| 🔴 P0 | 基准测试框架 | 没有度量就没有优化，先建基线再动手 |
| 🔴 P0 | Dreaming - Embedding聚类 + 合并 | 基于 text2vec 的语义聚类，解决记忆膨胀痛点 |
| 🟡 P1 | Dreaming - 知识提纯 | 提升记忆质量 |
| ⏸️ 观察 | Skills 闭环 - 埋点 | 先积累 1-2 月数据，达标后再启动 |
| 🟢 P2 | Schema Learning | 需要 P0/P1 的数据基础 |
| ⏸️ 观察 | Skills 闭环 - 自动进化 | 依赖埋点数据是否达标 |

---

## 关联文档

- 竞品分析：[../01-product-concept/12-竞品分析-MindMemOS.md](../01-product-concept/12-竞品分析-MindMemOS.md)
- 开发路线图：[../05-development-plan/04-记忆增强路线图-Dreaming与Skills.md](../05-development-plan/04-记忆增强路线图-Dreaming与Skills.md)
- 现有记忆系统架构：[02-记忆系统架构.md](02-记忆系统架构.md)
- 现有数据模型设计：[../04-detailed-design/06-数据模型设计.md](../04-detailed-design/06-数据模型设计.md)
- AI Provider 设计：[../04-detailed-design/05-工具API设计.md](../04-detailed-design/05-工具API设计.md)
