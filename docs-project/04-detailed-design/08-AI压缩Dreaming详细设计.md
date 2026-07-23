# 01-AI 压缩 Dreaming 详细设计

> 所属类别：第 4 类 - 详细设计
> 创建日期：2026-07-23
> 状态：待实现

## 1. 背景与目标

当前 Dreaming 功能仅做简单拼接（多篇笔记内容串联），不做内容压缩。本设计引入 AI 压缩层，在保持原文可追溯的前提下，生成精炼的浓缩笔记。

**目标：**
- 相似笔记聚类后，由 AI 生成去重精简版本
- 原文保留，不删除
- 压缩率 70-90%（原文 → 浓缩版）
- 用户交互不变（预览 → 执行）

## 2. 架构变更

```
                    ┌─────────────────────┐
                    │   DreamingService    │
                    │   (核心逻辑层)        │
                    └────────┬────────────┘
                             │
               ┌─────────────┼─────────────┐
               ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Cluster  │  │   AI     │  │  Merge   │
        │  Detect  │  │ Compress │  │  Writer  │
        └──────────┘  └──────────┘  └──────────┘
                            │
                            ▼
                     ┌────────────┐
                     │ DeepSeek   │
                     │ API (HTTP) │
                     └────────────┘
```

### 新模块：AiCompressor

```python
class AiCompressor:
    """AI 压缩器：调用 DeepSeek 对笔记簇进行智能浓缩"""

    async def compress_cluster(
        self,
        notes: list[Note],
        depth: str = "standard"  # standard 或 full
    ) -> CompressResult:
        ...
```

### 返回结构

```python
@dataclass
class CompressResult:
    title: str       # AI 生成的浓缩标题
    content: str     # AI 生成的精简正文
    keywords: list[str]  # 提取的关键词/标签
    token_usage: int     # API token 消耗
```

## 3. API 接口

### 新增配置参数

```python
class DreamingConfig:
    ai_compress: bool = False       # 是否启用 AI 压缩（默认不启用）
    ai_model: str = "deepseek-v4-flash"  # AI 模型
    ai_max_input_tokens: int = 8000 # 单次输入上限
```

### Dreaming Run API 扩展

```json
POST /api/dreaming/run
{
    "strategy": "default",
    "dry_run": true,
    "ai_compress": true     // ← 新增：启用 AI 压缩
}

→ 预览时返回 AI 生成的精简版本
```

### Dreaming Session 扩展

```json
{
    "id": 1,
    "status": "completed",
    "input_count": 3,
    "output_count": 1,
    "merged_count": 3,
    "archived_count": 3,
    "ai_compressed": true,       // ← 新增
    "token_cost": 1234,          // ← 新增
    "concentrates": [            // ← 新增
        {
            "source_ids": [3,4,5],
            "target_note_id": 44,
            "ai_title": "笔记存储与知识编译架构",
            "keywords": ["SQLite", "FTS5", "知识编译器"],
            "preview": "本项目采用 SQLite..."
        }
    ]
}
```

## 4. AI 提示词设计

### System Prompt

```markdown
你是一个知识压缩助手。你的任务是将多篇内容相似的笔记合并为一篇精简的知识点。
要求：
1. 去除重复信息，保留关键技术决策、架构选型、数据和结论
2. 保持可读性，使用中文
3. 保留对读者有价值的引用和链接
4. 不要添加原文中没有的新信息
5. 输出为结构化格式：[标题]、[精要]、[关键词]
```

### User Prompt

```markdown
以下是 N 篇内容相似的笔记：

## 笔记 1: {title1}
{content1}

## 笔记 2: {title2}
{content2}

...

请输出：

[标题]
一句话概括核心主题

[精要]
去重后保留关键信息的精简版本，使读者无需再读原文。
字数控制在原文总字数的 20-30%。

[关键词]
逗号分隔的关键词，用于标签和搜索
```

## 5. 数据变更

### dreaming_sessions 表

```sql
ALTER TABLE dreaming_sessions ADD COLUMN ai_compressed INTEGER DEFAULT 0;
ALTER TABLE dreaming_sessions ADD COLUMN token_cost INTEGER DEFAULT 0;
```

### dreaming_concentrates 表（新增）

```sql
CREATE TABLE IF NOT EXISTS dreaming_concentrates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    source_ids TEXT NOT NULL,       -- JSON: [3,4,5]
    target_note_id INTEGER NOT NULL,
    ai_title TEXT DEFAULT '',
    ai_content TEXT DEFAULT '',
    keywords TEXT DEFAULT '[]',     -- JSON: ["key1","key2"]
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (session_id) REFERENCES dreaming_sessions(id)
);
```

## 6. 实现步骤

### Phase 1: AI 压缩层（本迭代）

1. [ ] 创建 `core/ai_compressor.py` — AI 压缩模块
2. [ ] 扩展 `DreamingService.run_dreaming()` — 支持 `ai_compress` 参数
3. [ ] 修改 NoteEditor 前端 — 显示 AI 压缩预览
4. [ ] 添加新表 `dreaming_concentrates`
5. [ ] 更新 `list_annotations` 返回浓缩关联

### Phase 2: 知识图谱增强（后续）

1. [ ] 将关键词写入标签系统
2. [ ] 建立源笔记→浓缩笔记的图关系
3. [ ] 支持增量更新（新笔记加入已有浓缩簇）

## 7. 测试策略

### 单元测试

| 测试 | 方式 |
|------|------|
| AiCompressor.compress_cluster | mock DeepSeek API，验证输出结构 |
| DreamingService.ai_compress 参数 | mock compressor，验证写入逻辑 |
| 预览模式 dry_run=True | 验证返回预览内容但不写入 DB |
| 真实 DeepSeek 调用 | 集成测试（可选，需 API key） |

### 测试命令

```bash
python -m pytest tests/test_ai_compressor.py -v --tb=short
python -m pytest tests/test_dreaming.py -v --tb=short
```

## 8. 错误处理

| 场景 | 行为 |
|------|------|
| DeepSeek API 超时 | 降级到拼接模式，记录日志 |
| DeepSeek 返回格式异常 | 重试 1 次，失败后退回拼接 |
| 输入超长（>8000 token） | 截断过长笔记的中间部分，保留头和尾 |
| 网络不可用 | 直接跳过 AI 压缩，使用拼接模式 |

## 9. 向后兼容

- `ai_compress` 默认 `False`，现有 Dreaming 行为不变
- 旧 sessions 的 `ai_compressed` 字段为 0
- 新增 `dreaming_concentrates` 表不影响旧查询
- 前端已知 `ai_summary` 字段已支持显示
