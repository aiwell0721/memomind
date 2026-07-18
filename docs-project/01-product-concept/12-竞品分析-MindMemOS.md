# 竞品分析：MindMemOS

**分析时间**：2026-07-16  
**分析对象**：[mindscale-noah/MindMemOS](https://github.com/mindscale-noah/MindMemOS)  
**数据来源**：GitHub API + README + 项目源码结构

---

## 1. 项目概况

| 维度 | 值 |
|------|-----|
| 仓库 | `mindscale-noah/MindMemOS` |
| 创建时间 | 2026-06-23（约 3 周） |
| Stars | 240 ⭐ |
| Forks | 9 |
| 语言 | Python |
| 许可证 | MIT（README 声明，GitHub API 未识别） |
| 官网 | https://mindmemos.cn |
| 组织 | mindscale-noah（2026 年新创立，仅此一个公开仓库） |
| 主语言 | 中文（飞书社区 + 中文 README） |

---

## 2. 技术栈与架构

### 2.1 技术选型

| 层 | 技术 | 说明 |
|----|------|------|
| API 服务 | FastAPI | REST API + 自动文档 |
| 向量数据库 | Qdrant | 语义搜索 |
| 图数据库 | Neo4j | 记忆关联图谱 |
| 消息队列 | Kafka | 异步记忆处理 |
| 可观测性 | ClickHouse + OTel + Grafana | 遥测和监控 |
| 依赖管理 | uv | 现代化 Python 包管理 |
| 部署 | Docker + Makefile | 全栈容器化 |
| SDK | PyPI (`mindmemos-sdk`) | Python SDK + CLI |
| 插件 | npm (`@mindmemos/openclaw-plugin`) | OpenClaw 插件 |

### 2.2 源码结构

```
src/
├── mindmemos/          ← 核心服务
│   ├── api/            ← REST API 层
│   ├── components/     ← 业务组件
│   ├── config/         ← 配置管理
│   ├── errors/         ← 错误处理
│   ├── infra/          ← 基础设施（Qdrant, Neo4j, Kafka）
│   ├── llm/            ← LLM 调用抽象
│   ├── logging/        ← 日志/遥测
│   ├── mappers/        ← 数据映射层
│   ├── pipelines/      ← 核心管线（记忆处理编排）
│   ├── prompts/        ← Prompt 模板
│   ├── typing/         ← 类型定义
│   └── workers/        ← 后台 Worker
├── mindmemos_eval/     ← 评测框架（LoCoMo / PersonaMem / Dreaming）
└── mindmemos_sdk/      ← Python SDK + CLI
```

### 2.3 部署形态

- **Cloud API**：托管在 mindmemos.cn，Bearer Token 认证，GitHub Star 自动升级 Pro
- **本地部署**：`make dev` 启动全栈 Docker（Qdrant + Neo4j + Kafka + FastAPI）
- **轻量启动**：`make dev-core` 仅启动核心依赖（Qdrant + Neo4j + Kafka）

---

## 3. 核心特性分析

### 3.1 Benchmark 成绩

#### LoCoMo（对话记忆基准）

| 方法 | Single Hop | Multi Hop | Temporal | Open Domain | Overall |
|------|-----------|-----------|----------|-------------|---------|
| MemoryOS | 67.30 | 59.34 | 42.26 | 59.03 | 60.11 |
| Mem0 | 68.97 | 61.70 | 58.26 | 50.00 | 64.20 |
| MemU | 74.91 | 72.34 | 43.61 | 54.17 | 66.67 |
| MemOS | 85.37 | 79.43 | 75.08 | 64.58 | 80.76 |
| Zep | 90.84 | 81.91 | 77.26 | 75.00 | 85.22 |
| EverMemOS | 96.67 | 91.84 | 89.72 | 76.04 | 93.05 |
| **MindMemOS-schema** | **97.62** | **93.26** | 89.01 | 75.00 | **93.64** |

- **SOTA**：总分 93.64，领先 EverMemOS 0.6 分
- **强项**：单跳（97.62%）和多跳推理（93.26%）遥遥领先
- **弱项**：开放域（75.00%）和时序（89.01%）低于 EverMemOS

#### PersonaMem（角色记忆基准）

| 方法 | Recall Sha. | Recall Men. | Track Evo. | Revisit | Suggest | Recommend | Generalize | Overall |
|------|------------|-------------|------------|---------|---------|-----------|------------|---------|
| MemOS | 74.42% | 82.35% | 61.87% | 77.78% | 44.09% | 67.27% | 84.21% | 67.74% |
| EverMemOS | 74.42% | 64.71% | 64.03% | 85.86% | 35.48% | 65.45% | 84.21% | 67.57% |
| **MindMemOS** | 73.64% | **82.35%** | **67.63%** | 85.86% | 35.48% | **80.00%** | 78.95% | **69.61%** |

- **SOTA**：总分 69.61%，领先约 2 分
- **亮点**：推荐准确率 80%（vs 其他 65-67%），追踪演化 67.63%

#### Dreaming（记忆压缩基准）

| 管线 | Single-hop SubEM | Multi-hop SubEM | Average SubEM | 记忆数量变化 |
|------|-----------------|-----------------|---------------|-------------|
| MIRIX（基线） | 20.00% | 3.00% | 11.50% | - |
| mem0（基线） | 18.00% | 2.00% | 10.00% | - |
| Ours（Vanilla） | 83.00% | 10.75% | 46.88% | - |
| **Ours（+Dreaming）** | **88.75%** | **14.00%** | **51.38%** | **-27.9%** |

- Dreaming 使准确率 +4.5%，记忆数量 -27.9%（更少记忆、更高质量）

### 3.2 核心功能

| 功能 | 说明 | MemoMind 对标 |
|------|------|---------------|
| **跨框架可移植** | 用户画像/偏好/项目事实/工具经验可跨 OpenClaw/Hermes/Claude Code/OpenHands | ❌ 无（仅 OpenClaw） |
| **自进化记忆** | Schema 学习 + Dreaming + Feedback 持续优化 | ❌ 无 |
| **Memory-Skills 闭环** | 经验记忆 → Skill 候选 → 执行反馈 → 回喂记忆 | ❌ 无（静态 SKILL.md） |
| **Dreaming** | 记忆合并/去重/提纯，类似人类梦境巩固 | ❌ 无（仅有 suggest_consolidation） |
| **Schema Learning** | 自动学习频繁记忆模式，优化 add/search 行为 | ❌ 无 |
| **项目隔离** | project-isolated memory | ✅ 有（Workspace） |
| **Bearer Auth** | API Key 认证 + Pro 配额 | ✅ 有（JWT） |

### 3.3 规划中功能

| 功能 | 说明 |
|------|------|
| Skills 系统 | 路由/治理大型技能库，从真实使用中进化技能 |
| 文件系统记忆 | 将散落文件/文档/项目产物结构化为知识对象 |
| Agent 集成 | 与编码 Agent / OpenClaw / Codex 深度集成 |

---

## 4. 与 MemoMind 对比

| 维度 | MindMemOS | MemoMind |
|------|-----------|----------|
| **定位** | AI Agent 长期记忆系统（SaaS + 自部署） | 个人知识助手（本地优先） |
| **落地时间** | 2026-06 开源（3 周） | 已迭代 4 个 Phase |
| **开源状态** | 已开源（MIT） | 未开源 |
| **基准测试** | LoCoMo SOTA 93.64 / PersonaMem SOTA 69.61 | ❌ 未跑过基准 |
| **技术栈** | FastAPI + Qdrant + Neo4j + Kafka | Python + SQLite + jieba/FTS5 |
| **部署复杂度** | Docker 全家桶（6+ 容器） | `pip install` 零依赖 |
| **存储** | 向量数据库 + 图数据库 + 消息队列 | SQLite + JSON |
| **Dreaming** | ✅ 记忆压缩 + 性能提升（-27.9% 记忆 +4.5% 准确率） | ❌ 无 |
| **Skills 闭环** | ✅ 经验→技能→反馈循环 | ❌ 无 |
| **Schema Learning** | ✅ 自动学习记忆模式 | ❌ 无 |
| **跨框架** | OpenClaw + Hermes + Claude Code + OpenHands | 仅 OpenClaw |
| **图结构记忆** | Neo4j 图数据库 | ❌ 无（有链接图谱） |
| **MCP Server** | ❌ 无 | ✅ 有 |
| **Web UI** | ❌ 无（规划中） | ✅ 有（React + Vite） |
| **用户系统** | 单用户（user_id） | 多用户 + 工作区 |
| **商业化** | Cloud API + Pro 会员 | 无（个人使用） |

### 4.1 MemoMind 的优势

1. **轻量零依赖**：`pip install` 即用，无需 Docker/Qdrant/Neo4j
2. **Web UI 已就绪**：React Dashboard 已上线
3. **MCP Server**：可直接被 OpenClaw / Claude Desktop 调用
4. **多用户 + 工作区**：支持团队协作场景
5. **中文搜索优化**：jieba + FTS5 + 自定义词典，针对中文场景深度优化
6. **测试覆盖**：370+ 测试，质量有保障

### 4.2 MemoMind 的劣势

1. **无基准测试**：缺乏客观性能数据
2. **无 Dreaming**：记忆只增不减，长期使用后质量下降
3. **无 Skills 闭环**：技能是静态的，不能从使用中进化
4. **无 Schema Learning**：记忆模式靠人工定义
5. **无跨框架支持**：仅服务 OpenClaw 生态
6. **无向量搜索**：依赖 jieba + FTS5，语义搜索能力有限

---

## 5. 可借鉴方案

### 5.1 Dreaming 机制（优先级：🔴 P0）

**MindMemOS 做法**：
- 离线批量处理记忆，合并相似条目
- 去重 + 主题聚类 + 知识提取
- 效果：记忆数量 -27.9%，准确率 +4.5%

**MemoMind 适配方案**：
- 在现有 `suggest_consolidation()` 基础上扩展
- 新增 `DreamingService`：定期/手动触发记忆压缩
- 不需要 Kafka，用 Celery 或简单的后台线程即可
- 详见架构设计文档：[04-记忆系统增强设计-Dreaming与Skills闭环.md](../03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md)

### 5.2 Skills 闭环（优先级：🟡 P1 → ⏸️ 观察项）

**MindMemOS 做法**：
- 经验记忆 → Skill 候选 → 版本化 SKILL.md → 执行反馈 → 回喂记忆

**适用性分析**：
- MindMemOS 的 Skills 闭环依赖 SaaS + 多用户 + Cloud API 的高频使用场景，反馈密度充足
- MemoMind 是本地个人工具，单人 30 天使用数据大概率不足以检测出高频模式，整个闭环可能空转
- **结论**：先埋点记录使用模式（低成本），观察 1-2 个月数据量后再决定是否实施

**如后续实施**：
- 复用现有 `core/` 模块的笔记 + 标签体系
- 新增 `SkillEvolutionService`：从高频使用模式中提取技能
- 技能版本管理：复用 `VersionService` 基础设施

### 5.3 Schema Learning（优先级：🟢 P2）

**MindMemOS 做法**：
- 自动学习频繁记忆模式
- 优化 add/search 行为
- 使用 correction signals 调整

**MemoMind 适配方案**：
- 先收集用户 feedback（已有 `feedback` 接口）
- 分析 add → search 失败模式
- 自动调整分类器和搜索权重
- 可作为 Phase 5+ 的探索方向

### 5.4 基准测试（优先级：🔴 P0）

**MindMemOS 做法**：
- LoCoMo + PersonaMem + MemoryAgentBench 三个基准
- 提供可复现的评测配置（YAML + CLI）

**MemoMind 适配方案**：
- 移植 LoCoMo 评测到 MemoMind
- 建立基线，量化后续优化效果
- 详见开发路线图文档

---

## 6. 风险评估

| 风险 | 等级 | 说明 |
|------|------|------|
| 项目极新 | 🟡 中 | 仅 3 周，可能有大变动 |
| 商业模式 | 🟡 中 | Cloud API + Pro 会员，未来可能限制开源版本 |
| License 不严谨 | 🟢 低 | GitHub API 返回 null，但 README 写 MIT |
| 技术栈重 | 🟢 低 | 我们只借鉴设计，不引入 Qdrant/Neo4j/Kafka |
| 同名冲突 | 🟢 低 | "MindMemOS" vs "MemoMind"，命名接近但不同 |

---

## 7. 持续跟踪计划

| 频率 | 检查项 |
|------|--------|
| 月度 | GitHub Stars/Fork/Commit 趋势 |
| 月度 | 新增 Benchmark 结果 |
| 季度 | 架构变更（特别是 Dreaming 实现是否开源） |
| 触发式 | 发布新版本 / 重大 Feature / 商业模式变更 |

---

## 关联文档

- 记忆增强架构设计：[../03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md](../03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md)
- 开发路线图：[../05-development-plan/04-记忆增强路线图-Dreaming与Skills.md](../05-development-plan/04-记忆增强路线图-Dreaming与Skills.md)
- 现有记忆系统架构：[../03-architecture/02-记忆系统架构.md](../03-architecture/02-记忆系统架构.md)
- 现有竞品分析：[08-竞品深度分析.md](08-竞品深度分析.md)
