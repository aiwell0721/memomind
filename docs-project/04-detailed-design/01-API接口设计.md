# AI Agent 笔记与记忆工具 - API 设计文档

**文档版本**: v1.0  
**日期**: 2026-04-12  
**API版本**: v1  
**Base URL**: `https://api.mindweaver.app/v1` (云端) / `http://localhost:8080/v1` (本地)  

---

## 1. API 概述

### 1.1 设计原则

1. **RESTful**: 遵循RESTful设计规范
2. **资源导向**: 以资源为中心，URL表示资源
3. **一致性**: 统一的请求/响应格式
4. **版本化**: URL中包含API版本
5. **可扩展**: 支持未来功能扩展

### 1.2 认证方式

#### API Key 认证（推荐用于服务器端）

```http
Authorization: Bearer {api_key}
```

**获取方式**：
- 登录后访问 Settings → API → Generate Key
- 支持设置权限范围和过期时间

#### OAuth 2.0（推荐用于第三方应用）

**授权流程**：
```
1. 引导用户到授权页面
GET https://api.mindweaver.app/oauth/authorize?
    client_id={client_id}&
    redirect_uri={redirect_uri}&
    scope=notes:read notes:write&
    state={state}

2. 用户授权后重定向
GET {redirect_uri}?
    code={authorization_code}&
    state={state}

3. 交换访问令牌
POST https://api.mindweaver.app/oauth/token
Content-Type: application/json

{
  "grant_type": "authorization_code",
  "client_id": "{client_id}",
  "client_secret": "{client_secret}",
  "code": "{authorization_code}",
  "redirect_uri": "{redirect_uri}"
}

4. 返回令牌
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### 1.3 请求格式

**标准请求头**：
```http
Content-Type: application/json
Authorization: Bearer {token}
X-Request-ID: {uuid}           # 可选，用于追踪
X-Client-Version: 1.0.0       # 可选，客户端版本
```

**请求体**：JSON格式

### 1.4 响应格式

**成功响应**：
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "requestId": "req_xxx",
    "timestamp": "2026-04-12T10:00:00Z",
    "version": "v1"
  }
}
```

**列表响应**：
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "perPage": 20,
    "total": 100,
    "totalPages": 5,
    "hasNext": true,
    "hasPrev": false
  },
  "meta": { ... }
}
```

**错误响应**：
```json
{
  "success": false,
  "error": {
    "code": "invalid_request",
    "message": "The request is invalid",
    "details": [
      {
        "field": "title",
        "message": "Title is required"
      }
    ]
  },
  "meta": { ... }
}
```

### 1.5 HTTP状态码

| 状态码 | 含义 | 场景 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功，无返回内容 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 认证失败 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如重复创建） |
| 422 | Unprocessable | 语义错误（如验证失败） |
| 429 | Too Many Requests | 请求频率限制 |
| 500 | Internal Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

### 1.6 错误码

| 错误码 | 描述 | HTTP状态 |
|--------|------|----------|
| `invalid_request` | 请求格式错误 | 400 |
| `missing_field` | 缺少必填字段 | 400 |
| `invalid_field` | 字段值无效 | 400 |
| `unauthorized` | 未授权 | 401 |
| `token_expired` | 令牌过期 | 401 |
| `forbidden` | 禁止访问 | 403 |
| `not_found` | 资源不存在 | 404 |
| `already_exists` | 资源已存在 | 409 |
| `rate_limit` | 请求过于频繁 | 429 |
| `internal_error` | 内部错误 | 500 |
| `service_unavailable` | 服务不可用 | 503 |
| `ai_service_error` | AI服务错误 | 502 |

### 1.7 限流策略

| 端点类型 | 限制 | 说明 |
|----------|------|------|
| 普通API | 1000/分钟 | 笔记CRUD等 |
| 搜索API | 100/分钟 | 搜索端点 |
| AI API | 60/分钟 | AI相关端点 |
| 导出API | 10/分钟 | 导出端点 |

**限流响应**：
```json
{
  "success": false,
  "error": {
    "code": "rate_limit",
    "message": "Rate limit exceeded",
    "retryAfter": 30  // 秒后重试
  }
}
```

---

## 2. 笔记 API

### 2.1 获取笔记列表

```http
GET /notes
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `folderId` | string | 否 | 文件夹ID筛选 |
| `tag` | string | 否 | 标签筛选（可多次） |
| `q` | string | 否 | 关键词搜索 |
| `sort` | string | 否 | 排序：created, updated, title, relevance |
| `order` | string | 否 | 顺序：asc, desc |
| `page` | integer | 否 | 页码，默认1 |
| `perPage` | integer | 否 | 每页数量，默认20，最大100 |

**请求示例**：
```http
GET /notes?folderId=folder_xxx&tag=AI&sort=updated&order=desc&page=1&perPage=20
Authorization: Bearer sk_live_xxx
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": "note_xxx",
      "title": "Agent架构设计",
      "content": "## 核心概念\n\nAgent是...",
      "contentType": "markdown",
      "folderId": "folder_xxx",
      "tags": ["AI", "架构"],
      "createdAt": "2026-04-10T08:00:00Z",
      "updatedAt": "2026-04-12T10:00:00Z",
      "authorId": "user_xxx",
      "metadata": {
        "wordCount": 1500,
        "readingTime": 6
      }
    }
  ],
  "pagination": {
    "page": 1,
    "perPage": 20,
    "total": 156,
    "totalPages": 8,
    "hasNext": true,
    "hasPrev": false
  },
  "meta": {
    "requestId": "req_xxx",
    "timestamp": "2026-04-12T10:00:00Z"
  }
}
```

### 2.2 创建笔记

```http
POST /notes
```

**请求体**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 标题，最大200字符 |
| `content` | string | 是 | Markdown内容 |
| `contentType` | string | 否 | 类型：markdown, code, canvas，默认markdown |
| `folderId` | string | 否 | 文件夹ID |
| `tags` | string[] | 否 | 标签数组 |
| `metadata` | object | 否 | 元数据 |

**请求示例**：
```json
POST /notes
Content-Type: application/json
Authorization: Bearer sk_live_xxx

{
  "title": "多Agent协作架构",
  "content": "## 概述\n\n多Agent协作是...",
  "contentType": "markdown",
  "folderId": "folder_xxx",
  "tags": ["AI", "架构", "Agent"],
  "metadata": {
    "source": "https://example.com/article"
  }
}
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "id": "note_new",
    "title": "多Agent协作架构",
    "content": "## 概述\n\n多Agent协作是...",
    "contentType": "markdown",
    "folderId": "folder_xxx",
    "tags": ["AI", "架构", "Agent"],
    "createdAt": "2026-04-12T10:30:00Z",
    "updatedAt": "2026-04-12T10:30:00Z",
    "authorId": "user_xxx",
    "version": 1,
    "metadata": {
      "wordCount": 120,
      "readingTime": 1,
      "source": "https://example.com/article",
      "aiGenerated": false
    }
  },
  "meta": {
    "requestId": "req_xxx",
    "timestamp": "2026-04-12T10:30:00Z"
  }
}
```

### 2.3 获取笔记详情

```http
GET /notes/{id}
```

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | string | 笔记ID |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `include` | string | 否 | 额外包含：embeddings, related, history |

**响应示例**：
```json
{
  "success": true,
  "data": {
    "id": "note_xxx",
    "title": "Agent架构设计",
    "content": "## 核心概念...",
    "contentType": "markdown",
    "folderId": "folder_xxx",
    "tags": ["AI", "架构"],
    "createdAt": "2026-04-10T08:00:00Z",
    "updatedAt": "2026-04-12T10:00:00Z",
    "authorId": "user_xxx",
    "version": 5,
    "metadata": {
      "wordCount": 1500,
      "readingTime": 6,
      "aiGenerated": false,
      "lastAccessedAt": "2026-04-12T09:00:00Z",
      "accessCount": 42
    },
    "relatedNotes": [
      {
        "id": "note_related",
        "title": "相关笔记",
        "similarity": 0.85
      }
    ]
  },
  "meta": { ... }
}
```

### 2.4 更新笔记

```http
PUT /notes/{id}
```

**请求体**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 标题 |
| `content` | string | 否 | 内容 |
| `folderId` | string | 否 | 文件夹ID |
| `tags` | string[] | 否 | 标签（会覆盖原有标签） |
| `metadata` | object | 否 | 元数据（部分更新） |

**注意**：使用 `PATCH` 进行部分更新，`PUT` 要求完整资源

**请求示例**：
```json
PATCH /notes/note_xxx
Content-Type: application/json

{
  "title": "更新后的标题",
  "tags": ["AI", "架构", "更新"]
}
```

### 2.5 删除笔记

```http
DELETE /notes/{id}
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `permanent` | boolean | 否 | 是否永久删除，默认false（移入回收站） |

**响应**：204 No Content

---

## 3. 搜索 API

### 3.1 语义搜索

```http
POST /search
```

**请求体**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索查询 |
| `type` | string | 否 | 搜索类型：semantic, keyword, hybrid，默认hybrid |
| `filters` | object | 否 | 过滤条件 |
| `sort` | string | 否 | 排序：relevance, date, title |
| `limit` | integer | 否 | 返回数量，默认20，最大100 |
| `offset` | integer | 否 | 偏移量，默认0 |

**请求示例**：
```json
POST /search
Content-Type: application/json

{
  "query": "多Agent协作的最佳实践",
  "type": "hybrid",
  "limit": 10
}
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "note": {
        "id": "note_xxx",
        "title": "Agent架构设计",
        "content": "...",
        "tags": ["AI", "架构"]
      },
      "score": 0.92,
      "highlights": ["多<mark>Agent协作</mark>需要..."]
    }
  ]
}
```

### 3.2 AI问答

```http
POST /ask
```

**请求体**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 问题 |
| `context` | object | 否 | 上下文限制 |
| `stream` | boolean | 否 | 是否流式返回，默认false |

**响应示例**：
```json
{
  "success": true,
  "data": {
    "answer": "根据您的笔记...",
    "sources": [
      {
        "noteId": "note_1",
        "title": "Agent架构设计",
        "relevanceScore": 0.95
      }
    ],
    "confidence": 0.92
  }
}
```

---

## 4. 文件夹 API

### 4.1 获取文件夹列表

```http
GET /folders
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": "folder_xxx",
      "name": "工作",
      "parentId": null,
      "noteCount": 42
    }
  ]
}
```

### 4.2 创建文件夹

```http
POST /folders
```

```json
{
  "name": "新项目",
  "parentId": "folder_xxx",
  "icon": "📁",
  "color": "#3b82f6"
}
```

---

## 5. 标签 API

### 5.1 获取标签列表

```http
GET /tags
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": "tag_xxx",
      "name": "AI",
      "color": "#ef4444",
      "noteCount": 156
    }
  ]
}
```

---

## 6. Webhook

### 6.1 配置Webhook

```http
POST /webhooks
```

```json
{
  "url": "https://example.com/webhook",
  "events": ["note.created", "note.updated"],
  "secret": "whsec_xxx"
}
```

### 6.2 Webhook事件格式

```json
{
  "event": "note.created",
  "timestamp": "2026-04-12T10:00:00Z",
  "data": {
    "noteId": "note_xxx",
    "title": "新笔记"
  }
}
```

---

## 7. SDK

### 7.1 JavaScript/TypeScript SDK

```bash
npm install @mindweaver/sdk
```

```typescript
import { MindWeaverClient } from '@mindweaver/sdk';

const client = new MindWeaverClient({
  apiKey: 'sk_live_xxx',
  baseUrl: 'https://api.mindweaver.app/v1'
});

// 创建笔记
const note = await client.notes.create({
  title: '新笔记',
  content: '内容'
});

// 搜索
const results = await client.search({
  query: 'Agent架构',
  type: 'semantic'
});

// AI问答
const answer = await client.ai.ask({
  question: '总结我的AI笔记'
});
```

### 7.2 Python SDK

```bash
pip install mindweaver
```

```python
from mindweaver import Client

client = Client(api_key="sk_live_xxx")

# 创建笔记
note = client.notes.create(
    title="新笔记",
    content="内容"
)

# 搜索
results = client.search(
    query="Agent架构",
    type="semantic"
)
```

---

## 8. 变更日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-04-12 | 初始版本 |

---

*文档完成时间：2026-04-12*