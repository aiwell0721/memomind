# MemoMind 项目文档索引

> **文档分类体系**：扁平 6 类

## 📁 产品文档 vs 项目文档

| 类型 | 目录 | 受众 | 内容 |
|------|------|------|------|
| **产品文档** | `../docs/` | 用户、部署运维 | 部署指南、用户手册、API参考、快速入门、故障排查 |
| **项目文档** | `./` (docs-project/) | 开发团队、产品经理 | 产品概念、业务逻辑、架构设计、详细设计、开发计划、测试文档 |

---

## 📁 项目文档结构（6 类）

```
docs-project/
├── 01-product-concept/       # 第1类：产品概念及商业逻辑
├── 02-business-logic/        # 第2类：产品业务逻辑
├── 03-architecture/          # 第3类：产品架构设计
├── 04-detailed-design/       # 第4类：产品详细设计
├── 05-development-plan/      # 第5类：产品开发计划
└── 06-test-docs/             # 第6类：测试文档
```

---

## 第1类：产品概念及商业逻辑 (`01-product-concept/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [产品需求文档-PRD](./01-product-concept/01-产品需求文档-PRD.md) | AI Agent 笔记工具 PRD |
| 02 | [MemoMind PRD v2](./01-product-concept/02-MemoMind-PRD-v2.md) | MemoMind v2 版 PRD |
| 03 | [执行摘要-投资者版](./01-product-concept/03-执行摘要-投资者版.md) | 投资者执行摘要 |
| 04 | [投资者FAQ](./01-product-concept/04-投资者FAQ.md) | 投资者常见问题 |
| 05 | [财务模型](./01-product-concept/05-财务模型.md) | 商业财务模型 |
| 06 | [投资者演示文稿](./01-product-concept/06-投资者演示文稿.md) | 融资演示材料 |
| 07 | [PRD评审报告](./01-product-concept/07-PRD评审报告.md) | PRD 评审意见 |
| 08 | [竞品深度分析](./01-product-concept/08-竞品深度分析.md) | 市场竞争分析 |
| 09 | [工具竞品分析](./01-product-concept/09-工具竞品分析.md) | 工具类竞品对比 |
| 10 | [产品概述](./01-product-concept/10-产品概述.md) | 产品定位与概述 |
| 11 | [核心功能定义](./01-product-concept/11-核心功能定义.md) | 核心功能清单 |
| 12 | [竞品分析-MindMemOS](./01-product-concept/12-竞品分析-MindMemOS.md) | MindMemOS 竞品分析（2026-07） |

## 第2类：产品业务逻辑 (`02-business-logic/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [决策日志](./02-business-logic/01-决策日志.md) | 产品决策记录 |
| 02 | [风险登记册](./02-business-logic/02-风险登记册.md) | 产品风险跟踪 |
| 03 | [MVP检查清单](./02-business-logic/03-MVP检查清单.md) | MVP 验证清单 |
| 04 | [工具MVP定义](./02-business-logic/04-工具MVP定义.md) | 工具 MVP 范围 |

## 第3类：产品架构设计 (`03-architecture/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [整体架构设计](./03-architecture/01-整体架构设计.md) | 系统整体架构 |
| 02 | [记忆系统架构](./03-architecture/02-记忆系统架构.md) | 记忆模块架构 |
| 03 | [工具架构设计](./03-architecture/03-工具架构设计.md) | Tool API 架构 |
| 04 | [记忆系统增强设计-Dreaming与Skills闭环](./03-architecture/04-记忆系统增强设计-Dreaming与Skills闭环.md) | Dreaming 架构设计 + Skills 观察项（2026-07） |

## 第4类：产品详细设计 (`04-detailed-design/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [API接口设计](./04-detailed-design/01-API接口设计.md) | API 详细设计 |
| 02 | [REST-API规范](./04-detailed-design/02-REST-API规范.md) | REST API 端点规范 |
| 03 | [MCP工具规范](./04-detailed-design/03-MCP工具规范.md) | MCP Server 工具定义 |
| 04 | [CLI工具设计](./04-detailed-design/04-CLI工具设计.md) | 命令行接口设计 |
| 05 | [工具API设计](./04-detailed-design/05-工具API设计.md) | Tool API 详细规范 |
| 06 | [数据模型设计](./04-detailed-design/06-数据模型设计.md) | 数据库模型 |
| **07** | **[备注功能详细设计](./04-detailed-design/07-备注功能详细设计.md)** | **备注功能 API/前端/数据模型详细设计** |

## 第5类：产品开发计划 (`05-development-plan/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [Phase4开发计划](./05-development-plan/01-Phase4开发计划.md) | Phase 4 Web UI + 生产就绪 |
| 02 | [下次优化方向](./05-development-plan/02-下次优化方向.md) | 后续优化方向（OPT-01 ~ OPT-08） |
| 03 | [知识图谱连通与去重消化方案](./05-development-plan/03-知识图谱连通与去重消化方案.md) | KG连通 + 去重 + 知识消化 |
| 04 | [记忆增强路线图-Dreaming与Skills](./05-development-plan/04-记忆增强路线图-Dreaming与Skills.md) | Phase 5 记忆增强开发计划（2026-07） |
| **05** | **[备注功能开发计划](./05-development-plan/05-备注功能开发计划.md)** | **备注功能 Phase 1-5 开发计划** |

## 第6类：测试文档 (`06-test-docs/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [分类器v1测试报告](./06-test-docs/01-分类器v1测试报告.md) | PR 分类器 v1 测试结果 |
| 02 | [分类器v2测试报告](./06-test-docs/02-分类器v2测试报告.md) | PR 分类器 v2 测试结果 |
| 03 | [记忆系统自动化测试报告](./06-test-docs/03-记忆系统自动化测试报告.md) | 自动化脚本测试报告 |
| 04 | [记忆系统基准测试报告](./06-test-docs/04-记忆系统基准测试报告.md) | Phase 5.1 首次基线报告（2026-07） |

---

## 📂 docs/ 目录（产品文档 - 用户面向）

| 文档 | 说明 |
|------|------|
| [Quick Start](../docs/quick-start.md) | 快速入门 |
| [User Guide](../docs/user-guide.md) | 用户手册 |
| [API Reference](../docs/api-reference.md) | API 参考 |
| [CLI Reference](../docs/cli-reference.md) | CLI 参考 |
| [Deployment](../docs/deployment.md) | 部署指南 |
| [Troubleshooting](../docs/troubleshooting.md) | 故障排查 |
