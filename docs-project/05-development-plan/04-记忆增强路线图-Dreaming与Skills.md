# 记忆增强路线图：Dreaming 与 Skills 闭环

**制定时间**：2026-07-16  
**状态**：规划中  
**关联竞品分析**：[../01-product-concept/12-竞品分析-MindMemOS.md](../01-product-concept/12-竞品分析-MindMemOS.md)  
**关联架构设计**：[../03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md](../03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md)

---

## 背景

基于 MindMemOS 竞品分析，Dreaming 机制和 Skills 闭环是 MemoMind 记忆系统下一步升级的核心方向。本文档规划具体的实施阶段、交付物和成功标准。

**前置条件**：
- Phase 1-4 已完成（370+ 测试通过）
- AI Provider 抽象层已就绪（PR-025）
- `suggest_consolidation()` 已实现（可作为 Dreaming 的基础）

---

## Phase 5：记忆增强

### 5.1 阶段总览

| 阶段 | 主题 | 工作量 | 优先级 | 依赖 |
|------|------|--------|--------|------|
| ✅ 5.0 | TF-IDF 聚类验证实验 | 已完成 | 🔴 P0 | — |
| ✅ 5.1 | 基准测试框架 | 已完成 | 🔴 P0 | 无 |
| ✅ 5.2 | Dreaming 基础（Embedding 聚类） | 已完成 | 🔴 P0 | 5.0, 5.1 |
| 5.3 | Dreaming 增强 | 2-3 天 | 🟡 P1 | 5.2 |
| ⏸️ | Skills 模式识别 | — | 观察项 | 埋点数据达标后启动 |
| ⏸️ | Skills 自动进化 | — | 观察项 | Skills 模式识别 |

---

### ✅ 5.0 TF-IDF 聚类验证实验（已完成）

**实验日期**：2026-07-17
**数据**：34 篇 Obsidian 真实笔记 + 50 篇模拟多主题笔记（10 主题 x 5 篇）
**脚本**：`scripts/tfidf_cluster_validate.py`

#### TF-IDF 实验结果（失败）

| 数据集 | 阈值 0.45 聚类数 | 多元素簇 | 压缩率 |
|--------|-----------------|---------|--------|
| Obsidian（34篇） | 29 簇 | 3 个（仅靠关键词重叠） | 14.7% |
| 模拟数据（50篇） | **50 簇** | **0 个** | **0.0%** |

**TF-IDF 完全无法识别同主题笔记的语义相似性。**

#### Embedding 实验结果（通过）

| 阈值 | 簇数 | 多元素簇 | 纯度 | 压缩率 |
|------|------|---------|------|--------|
| 0.65 | 20 | 10 | 45% | 60% |
| **0.70** | **27** | **11** | **56%** | **46%** |
| 0.75 | 36 | 12 | 77% | 28% |

#### 结论

**切换到 `text2vec-base-chinese` Embedding 方案。** 推荐默认阈值 0.70，保守模式 0.75。

---

### 5.1 基准测试框架（P0）

**目标**：建立客观性能基准，量化后续优化效果

#### 交付物

| # | 交付物 | 说明 |
|---|--------|------|
| 1 | `benchmarks/locomo_simplified.py` | LoCoMo 简化版评测 |
| 2 | `benchmarks/dreaming_benchmark.py` | Dreaming 前后对比（框架先建，数据等 5.2 完成后填入） |
| 3 | `benchmarks/chinese_search_benchmark.py` | 中文搜索质量基准 |
| 4 | `benchmarks/latency_benchmark.py` | 搜索延迟基准 |
| 5 | `benchmarks/run_all.py` | 一键运行所有基准 |
| 6 | 测试报告：`docs-project/06-test-docs/04-记忆系统基准测试报告.md` | 首次基准结果 |

#### 测试维度

| 维度 | 数据集 | 指标 | 目标 |
|------|--------|------|------|
| 检索准确率 | LoCoMo 简化版（50 Q&A） | Single-hop 准确率 | ≥ 70%（Local）/ ≥ 85%（Cloud） |
| Dreaming 效果 | 100 条对话记忆 | 压缩率 / 准确率变化 | 压缩 ≥ 20%，准确率不降 |
| 中文搜索 | 50 条中文笔记 + 20 个查询 | 召回率 / 精确率 / F1 | F1 ≥ 0.75 |
| 搜索延迟 | 500 / 1000 / 2000 条记忆 | P50 / P95 / P99 | P95 < 50ms |

#### 实施步骤

1. **LoCoMo 简化版** -> 验证：能跑通完整评测流程
2. **Dreaming 对比** -> 验证：Dreaming 前后有量化对比
3. **中文搜索** -> 验证：jieba + FTS5 的召回/精确率
4. **延迟基准** -> 验证：不同数据规模下的延迟数据
5. **生成首次报告** -> 验证：报告含基线数据 + 优化建议

#### 成功标准

- ✅ 所有基准可一键运行（`python benchmarks/run_all.py`）
- ✅ 产出首次基准测试报告（含当前基线数据）
- ✅ 基线数据存档，后续可对比

---

### 5.2 Dreaming 基础（P0）

**目标**：实现基于 Embedding 的记忆压缩管线，解决记忆膨胀问题

**前置条件**：5.1 基线数据已建立 + `pip install sentence-transformers`（text2vec-base-chinese）

**聚类方案**：`text2vec-base-chinese` Embedding + 余弦相似度 + 贪心聚类
- 默认阈值 0.70（纯度 56%/压缩率 46%）
- 保守模式阈值 0.75（纯度 77%/压缩率 28%）
- 激进模式阈值 0.65（纯度 45%/压缩率 60%）

#### 交付物

| # | 交付物 | 说明 |
|---|--------|------|
| 1 | `core/dreaming_service.py` | DreamingService 核心实现 |
| 2 | `core/dreaming_models.py` | DreamingSession / DreamingChange 数据模型 |
| 3 | DB 迁移：`dreaming_sessions` 表 | Dreaming 会话记录 |
| 4 | DB 迁移：`dreaming_changes` 表 | Dreaming 变更追溯 |
| 5 | CLI：`memomind dream` | 手动触发 Dreaming |
| 6 | CLI：`memomind dream --dry-run` | 预览模式 |
| 7 | CLI：`memomind dream rollback <session_id>` | 回滚 Dreaming |
| 8 | 测试：`tests/test_dreaming_service.py` | ≥ 15 个测试 |

#### 核心功能

```
memomind dream                    # 执行 Dreaming
memomind dream --dry-run          # 预览（只出报告不执行）
memomind dream --strategy aggressive  # 激进策略
memomind dream --workspace 2      # 指定工作区
memomind dream rollback 5         # 回滚第 5 次 Dreaming
memomind dream history            # 查看 Dreaming 历史
```

#### 实施步骤

1. **数据模型** -> 验证：DB 表创建成功，CRUD 测试通过
2. **聚类器**（Embedding + 余弦相似度 + 贪心聚类） -> 验证：同主题记忆能被正确聚类
3. **合并器** -> 验证：合并后记忆包含原始记忆的关键信息
4. **归档器** -> 验证：原始记忆标记 archived，搜索结果中不出现
5. **回滚机制** -> 验证：回滚后原始记忆恢复，合并记忆删除
6. **CLI 集成** -> 验证：端到端流程通过
7. **更新基准** -> 验证：用 5.1 的基准框架跑 Dreaming 前后对比

#### 成功标准

- ✅ Dreaming 能将 100 条记忆压缩到 60-80 条（≥20% 压缩率）
- ✅ 压缩后搜索准确率不下降（预设 10 个问题回答正确率 ≥ 90%）
- ✅ 回滚功能 100% 恢复原始状态
- ✅ ≥ 15 个测试全部通过
- ✅ `--dry-run` 模式不产生任何副作用

---

### 5.3 Dreaming 增强（P1）

**目标**：在基础 Dreaming 之上增加知识提纯和定时触发

#### 交付物

| # | 交付物 | 说明 |
|---|--------|------|
| 1 | `core/dreaming_extractor.py` | 知识提纯模块 |
| 2 | `core/dreaming_scheduler.py` | 定时触发器 |
| 3 | API：`POST /api/dreaming/trigger` | REST API 触发 |
| 4 | API：`GET /api/dreaming/sessions` | 查看历史 |
| 5 | API：`POST /api/dreaming/rollback/{id}` | API 回滚 |
| 6 | 前端：Dreaming 面板 | Web UI 中查看 Dreaming 历史和报告 |

#### 增强功能

- **知识提纯**：从记忆簇中提取 (subject, predicate, object) 三元组
- **AI 增强**：Cloud AI Provider 模式下，使用 LLM 生成更好的合并摘要
- **定时触发**：每日凌晨 3:00 自动执行（可配置）
- **阈值触发**：记忆数 > 500 且上次 Dreaming > 7 天时自动触发
- **报告生成**：每次 Dreaming 产出结构化报告

#### 成功标准

- ✅ 知识提纯能从 10 条记忆中提取 ≥ 5 个有效三元组
- ✅ 定时触发正确执行（测试模拟）
- ✅ REST API 接口完整
- ✅ 前端可查看 Dreaming 历史和报告
- ✅ ≥ 10 个新测试通过

---

### ⏸️ Skills 模式识别（观察项）

> **暂不排期**。先在 ActivityLog 中埋点记录使用模式（见架构设计文档 3.2 节），积累 1-2 个月数据后评估：
> - 若 **≥3 个高频模式**（频次 ≥ 5/30天）→ 启动本阶段
> - 若 **< 3 个** → 继续观察或放弃此方向

### ⏸️ Skills 自动进化（观察项）

> **暂不排期**。依赖 Skills 模式识别产出足够候选技能后方可启动。

---

## 时间线

| 阶段 | 预估工作量 | 建议时间 |
|------|-----------|----------|
| 5.0 TF-IDF 聚类验证 | 0.5 天 | Week 1 首日 |
| 5.1 基准测试框架 | 2-3 天 | Week 1 |
| 5.2 Dreaming 基础 | 3-4 天 | Week 1-2 |
| 5.3 Dreaming 增强 | 2-3 天 | Week 2-3 |
| **合计** | **8-10.5 天** | **约 2.5 周** |

---

## 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| TF-IDF 聚类质量差（已验证） | ✅ 已排除 | 切换为 text2vec Embedding 方案 |
| Embedding 模型加载开销 | 🟡 中 | 使用 text2vec-base-chinese（~400MB），支持 CPU，加载一次后常驻 |
| Dreaming 合并质量低 | 🟡 中 | 先用 --dry-run 预览，保留回滚能力 |
| 基准测试数据不真实 | 🟡 中 | 从真实使用中采集，不合成数据 |
| DB 迁移影响现有数据 | 🟢 低 | 只新增表，不改现有表结构 |

---

## 与现有 Phase 4 的关系

| Phase 4 未完成项 | 与 Phase 5 的关系 |
|------------------|------------------|
| PR-020 实时协作 | 不阻塞 Phase 5，可并行 |
| PR-019 Docker 部署 | 不阻塞 Phase 5 |
| PR-021 导出增强 | 不阻塞 Phase 5 |
| PR-023 安全加固 | 不阻塞 Phase 5 |

**结论**：Phase 5 可与 Phase 4 剩余项并行推进，无阻塞依赖。

---

## 关联文档

- 竞品分析：[../01-product-concept/12-竞品分析-MindMemOS.md](../01-product-concept/12-竞品分析-MindMemOS.md)
- 架构设计：[../03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md](../03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md)
- Phase 4 计划：[01-Phase4开发计划.md](01-Phase4开发计划.md)
- 下次优化方向：[02-下次优化方向.md](02-下次优化方向.md)
- 知识图谱方案：[03-知识图谱连通与去重消化方案.md](03-知识图谱连通与去重消化方案.md)
