# MemoMind 项目文档索引

> **文档分类体系**：扁平 6 类

---

## 📁 文档结构

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

## 第一层：产品概念与业务逻辑

### 第1类：产品概念及商业逻辑 (`01-product-concept/`)

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

### 第2类：产品业务逻辑 (`02-business-logic/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [决策日志](./02-business-logic/01-决策日志.md) | 产品决策记录 |
| 02 | [风险登记册](./02-business-logic/02-风险登记册.md) | 产品风险跟踪 |
| 03 | [MVP检查清单](./02-business-logic/03-MVP检查清单.md) | MVP 验证清单 |
| 04 | [工具MVP定义](./02-business-logic/04-工具MVP定义.md) | 工具 MVP 范围 |
| 05 | [记忆系统业务逻辑](./02-business-logic/05-记忆系统业务逻辑.md) | 记忆系统业务流程 |

---

## 第二层：架构与详细设计

### 第3类：产品架构设计 (`03-architecture/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [整体架构设计](./03-architecture/01-整体架构设计.md) | 系统整体架构 |
| 02 | [记忆系统架构](./03-architecture/02-记忆系统架构.md) | 记忆模块架构 |
| 03 | [工具架构设计](./03-architecture/03-工具架构设计.md) | Tool API 架构 |
| 04 | [数据模型设计](./03-architecture/04-数据模型设计.md) | 数据库模型 |
| 05 | [API架构设计](./03-architecture/05-API架构设计.md) | API 层架构 |

### 第4类：产品详细设计 (`04-detailed-design/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [API接口设计](./04-detailed-design/01-API接口设计.md) | API 详细设计 |
| 02 | [REST-API规范](./04-detailed-design/02-REST-API规范.md) | REST API 端点规范 |
| 03 | [MCP工具规范](./04-detailed-design/03-MCP工具规范.md) | MCP Server 工具定义 |
| 04 | [CLI工具设计](./04-detailed-design/04-CLI工具设计.md) | 命令行接口设计 |
| 05 | [工具API设计](./04-detailed-design/05-工具API设计.md) | Tool API 详细规范 |
| 06 | [记忆系统详细设计](./04-detailed-design/06-记忆系统详细设计.md) | 记忆系统实现细节 |
| 07 | [PRD设计评审改进点](./04-detailed-design/07-PRD设计评审改进点.md) | 设计改进清单 |

---

## 第5类：产品开发计划 (`05-development-plan/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [Phase4开发计划](./05-development-plan/01-Phase4开发计划.md) | Phase 4 Web UI + 生产就绪 |

### 第6类：测试文档 (`06-test-docs/`)

| # | 文档 | 说明 |
|---|------|------|
| 01 | [分类器v1测试报告](./06-test-docs/01-分类器v1测试报告.md) | PR 分类器 v1 测试结果 |
| 02 | [分类器v2测试报告](./06-test-docs/02-分类器v2测试报告.md) | PR 分类器 v2 测试结果 |
| 03 | [记忆系统自动化测试报告](./06-test-docs/03-记忆系统自动化测试报告.md) | 自动化脚本测试报告 |

---

## 📂 docs/ 目录（发布相关）

> `../docs/` 存放产品发布相关文档：部署指南、用户手册、API参考、快速入门、故障排查等。

| 文档 | 说明 |
|------|------|
| [README](../docs/README.md) | 文档导航 |
| [Quick Start](../docs/quick-start.md) | 快速入门 |
| [User Guide](../docs/user-guide.md) | 用户手册 |
| [API Reference](../docs/api-reference.md) | API 参考 |
| [CLI Reference](../docs/cli-reference.md) | CLI 参考 |
| [Deployment](../docs/deployment.md) | 部署指南 |
| [Troubleshooting](../docs/troubleshooting.md) | 故障排查 |
