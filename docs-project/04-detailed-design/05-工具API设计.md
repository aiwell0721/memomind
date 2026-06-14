# AI Agent 笔记与记忆工具 - API 设计文档

## 1. API 概览

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| **Base URL** | `http://localhost:3000/api/v1` |
| **协议** | HTTPS (生产) / HTTP (开发) |
| **数据格式** | JSON |
| **字符编码** | UTF-8 |
| **版本** | v1 |

### 1.2 API 端点分类

| 分类 | 前缀 | 描述 |
|------|------|------|
| **笔记管理** | `/notes` | 笔记的 CRUD 操作 |
| **标签管理** | `/tags` | 标签的 CRUD 操作 |
| **搜索** | `/search` | 全文搜索和语义搜索 |
| **记忆管理** | `/memories` | AI 记忆的存储和检索 |
| **会话管理** | `/sessions` | 会话上下文管理 |
| **Agent 管理** | `/agents` | AI Agent 注册和管理 |
| **系统** | `/system` | 系统信息和健康检查 |

---

## 2. 认证机制

### 2.1 认证方式

支持两种认证方式：

1. **API Key** - 用于程序访问
2. **JWT Token** - 用于用户会话

### 2.2 API Key 认证

```http
GET /api/v1/notes
Authorization: Bearer mk_live_xxxxxxxxxxxxxxxx
```

### 2.3 JWT 认证

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

后续请求：

```http
GET /api/v1/notes
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 3. 标准响应格式

### 3.1 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### 3.2 错误响应

```json
{
  "code": 1001,
  "message": "Invalid API key",
  "details": {
    "field": "api_key",
    "reason": "Key has expired"
  }
}
```

### 3.3 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | integer | 1 | 页码 |
| `limit` | integer | 20 | 每页数量 (max 100) |
| `sort` | string | "-created_at" | 排序字段，前缀 `-` 表示倒序 |

---

## 4. 笔记管理 API

### 4.1 获取笔记列表

```http
GET /api/v1/notes
```

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `workspace_id` | string | 工作空间 ID |
| `tag` | string | 标签过滤 |
| `search` | string | 标题/内容搜索 |
| `is_template` | boolean | 是否模板 |

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "note_abc123",
      "title": "项目计划",
      "path": "projects/plan.md",
      "tags": ["project", "planning"],
      "created_at": "2026-04-12T10:00:00Z",
      "updated_at": "2026-04-12T14:30:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 45
  }
}
```

### 4.2 创建笔记

```http
POST /api/v1/notes
Content-Type: application/json

{
  "title": "新笔记",
  "content": "# 标题\n\n内容...",
  "path": "folder/note.md",
  "tags": ["tag1", "tag2"],
  "workspace_id": "ws_xxx"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "note_def456",
    "title": "新笔记",
    "path": "folder/note.md",
    "content": "# 标题\n\n内容...",
    "tags": ["tag1", "tag2"],
    "created_at": "2026-04-12T15:00:00Z",
    "updated_at": "2026-04-12T15:00:00Z"
  }
}
```

### 4.3 获取笔记详情

```http
GET /api/v1/notes/:id
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "note_abc123",
    "title": "项目计划",
    "content": "# 项目计划\n\n## 目标\n...",
    "path": "projects/plan.md",
    "tags": ["project", "planning"],
    "links": {
      "outgoing": [
        {"id": "note_xyz789", "title": "资源清单", "type": "wiki"}
      ],
      "incoming": [
        {"id": "note_uvw456", "title": "周报", "type": "wiki"}
      ]
    },
    "created_at": "2026-04-12T10:00:00Z",
    "updated_at": "2026-04-12T14:30:00Z"
  }
}
```

### 4.4 更新笔记

```http
PUT /api/v1/notes/:id
Content-Type: application/json

{
  "title": "更新的标题",
  "content": "# 更新的内容",
  "tags": ["new-tag"]
}
```

### 4.5 删除笔记

```http
DELETE /api/v1/notes/:id
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "deleted": true,
    "id": "note_abc123"
  }
}
```

---

## 5. 搜索 API

### 5.1 全文搜索

```http
GET /api/v1/search?q=关键词&workspace_id=ws_xxx
```

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `q` | string | 搜索关键词 (必填) |
| `workspace_id` | string | 工作空间 ID |
| `type` | string | 搜索类型: `all`, `title`, `content` |
| `limit` | integer | 返回数量 |

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "results": [
      {
        "id": "note_abc123",
        "title": "项目计划",
        "excerpt": "...<mark>关键词</mark>出现在这里...",
        "path": "projects/plan.md",
        "score": 0.95,
        "type": "note"
      }
    ],
    "total": 12,
    "query": "关键词",
    "took_ms": 45
  }
}
```

### 5.2 语义搜索

```http
POST /api/v1/search/semantic
Content-Type: application/json

{
  "query": "人工智能在医疗领域的应用",
  "workspace_id": "ws_xxx",
  "limit": 10,
  "threshold": 0.7
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "results": [
      {
        "id": "note_ai_medical",
        "title": "AI 医疗应用研究",
        "content": "人工智能在医疗诊断中的应用...",
        "similarity": 0.89,
        "type": "note"
      },
      {
        "id": "mem_123",
        "content": "机器学习可以帮助医生更准确地诊断疾病",
        "similarity": 0.82,
        "type": "memory"
      }
    ],
    "total": 5,
    "took_ms": 120
  }
}
```

### 5.3 混合搜索

```http
POST /api/v1/search/hybrid
Content-Type: application/json

{
  "query": "项目进度",
  "workspace_id": "ws_xxx",
  "semantic_weight": 0.6,
  "keyword_weight": 0.4,
  "limit": 10
}
```

---

## 6. 记忆管理 API

### 6.1 存储记忆

```http
POST /api/v1/memories
Content-Type: application/json

{
  "content": "用户喜欢使用蓝色主题的界面",
  "agent_id": "agent_xxx",
  "session_id": "session_yyy",
  "type": "preference",
  "importance": 0.8,
  "metadata": {
    "source": "user_feedback",
    "confidence": 0.95
  }
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "mem_abc123",
    "content": "用户喜欢使用蓝色主题的界面",
    "agent_id": "agent_xxx",
    "session_id": "session_yyy",
    "type": "preference",
    "importance": 0.8,
    "embedding_id": "emb_def456",
    "created_at": "2026-04-12T15:30:00Z"
  }
}
```

### 6.2 检索记忆

```http
GET /api/v1/memories?agent_id=agent_xxx&query=用户偏好
```

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | string | Agent ID (必填) |
| `query` | string | 语义查询 |
| `session_id` | string | 会话 ID |
| `type` | string | 记忆类型过滤 |
| `min_importance` | float | 最小重要性 (0-1) |
| `limit` | integer | 返回数量 |

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "memories": [
      {
        "id": "mem_abc123",
        "content": "用户喜欢使用蓝色主题的界面",
        "type": "preference",
        "importance": 0.8,
        "similarity": 0.92,
        "metadata": {
          "source": "user_feedback"
        },
        "created_at": "2026-04-12T15:30:00Z"
      }
    ],
    "total": 15,
    "took_ms": 85
  }
}
```

### 6.3 批量存储记忆

```http
POST /api/v1/memories/batch
Content-Type: application/json

{
  "memories": [
    {
      "content": "记忆内容1",
      "type": "fact",
      "importance": 0.7
    },
    {
      "content": "记忆内容2",
      "type": "preference",
      "importance": 0.9
    }
  ],
  "agent_id": "agent_xxx"
}
```

### 6.4 删除记忆

```http
DELETE /api/v1/memories/:id
```

### 6.5 更新记忆

```http
PATCH /api/v1/memories/:id
Content-Type: application/json

{
  "importance": 0.9,
  "metadata": {
    "verified": true
  }
}
```

---

## 7. 会话管理 API

### 7.1 创建会话

```http
POST /api/v1/sessions
Content-Type: application/json

{
  "agent_id": "agent_xxx",
  "context": {
    "topic": "产品讨论",
    "participants": ["user_1", "agent_1"]
  },
  "expires_in": 3600
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "session_abc123",
    "agent_id": "agent_xxx",
    "status": "active",
    "context": {
      "topic": "产品讨论",
      "participants": ["user_1", "agent_1"]
    },
    "token_count": 0,
    "expires_at": "2026-04-12T16:30:00Z",
    "created_at": "2026-04-12T15:30:00Z"
  }
}
```

### 7.2 获取会话

```http
GET /api/v1/sessions/:id
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "session_abc123",
    "agent_id": "agent_xxx",
    "status": "active",
    "context": {
      "topic": "产品讨论",
      "messages": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的？"}
      ]
    },
    "token_count": 45,
    "memories": [
      {
        "id": "mem_xxx",
        "content": "用户询问产品功能",
        "type": "context"
      }
    ],
    "expires_at": "2026-04-12T16:30:00Z",
    "created_at": "2026-04-12T15:30:00Z"
  }
}
```

### 7.3 更新会话上下文

```http
PATCH /api/v1/sessions/:id
Content-Type: application/json

{
  "context": {
    "messages": [
      {"role": "user", "content": "新消息"}
    ]
  },
  "token_count": 120
}
```

### 7.4 关闭会话

```http
DELETE /api/v1/sessions/:id
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "session_abc123",
    "status": "closed",
    "memories_preserved": 5,
    "closed_at": "2026-04-12T16:00:00Z"
  }
}
```

---

## 8. Agent 管理 API

### 8.1 注册 Agent

```http
POST /api/v1/agents
Content-Type: application/json

{
  "name": "客服助手",
  "description": "处理客户咨询的 AI 助手",
  "type": "customer_service",
  "config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "permissions": {
    "read_notes": true,
    "write_notes": false,
    "read_memories": true,
    "write_memories": true
  }
}
```

**响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "agent_abc123",
    "name": "客服助手",
    "api_key": "mk_agent_xxxxxxxxxxxxxxxx",
    "config": {
      "model": "gpt-4",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "created_at": "2026-04-12T15:30:00Z"
  }
}
```

### 8.2 获取 Agent 列表

```http
GET /api/v1/agents
```

### 8.3 获取 Agent 详情

```http
GET /api/v1/agents/:id
```

### 8.4 获取 Agent 记忆

```http
GET /api/v1/agents/:id/memories?limit=20
```

### 8.5 更新 Agent

```http
PATCH /api/v1/agents/:id
Content-Type: application/json

{
  "config": {
    "temperature": 0.5
  }
}
```

### 8.6 删除 Agent

```http
DELETE /api/v1/agents/:id
```

---

## 9. WebSocket 协议

### 9.1 连接

```javascript
const ws = new WebSocket('ws://localhost:3000/ws');

ws.onopen = () => {
  // 发送认证
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'Bearer eyJhbGciOiJIUzI1NiIs...'
  }));
};
```

### 9.2 消息格式

```typescript
interface WebSocketMessage {
  type: 'auth' | 'subscribe' | 'unsubscribe' | 'event' | 'error';
  id?: string;           // 消息 ID，用于关联响应
  payload?: any;         // 消息内容
}
```

### 9.3 订阅事件

```javascript
// 订阅笔记变更
ws.send(JSON.stringify({
  type: 'subscribe',
  payload: {
    event: 'note.updated',
    filter: {
      workspace_id: 'ws_xxx'
    }
  }
}));

// 订阅记忆更新
ws.send(JSON.stringify({
  type: 'subscribe',
  payload: {
    event: 'memory.created',
    filter: {
      agent_id: 'agent_xxx'
    }
  }
}));
```

### 9.4 事件推送

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'event':
      console.log('收到事件:', data.payload);
      break;
    case 'error':
      console.error('错误:', data.payload);
      break;
  }
};
```

**事件示例：**

```json
{
  "type": "event",
  "payload": {
    "event": "note.updated",
    "data": {
      "id": "note_abc123",
      "title": "更新的标题",
      "updated_at": "2026-04-12T16:00:00Z"
    },
    "timestamp": "2026-04-12T16:00:00Z"
  }
}
```

### 9.5 支持的事件类型

| 事件 | 描述 |
|------|------|
| `note.created` | 笔记创建 |
| `note.updated` | 笔记更新 |
| `note.deleted` | 笔记删除 |
| `memory.created` | 记忆创建 |
| `memory.updated` | 记忆更新 |
| `memory.deleted` | 记忆删除 |
| `session.created` | 会话创建 |
| `session.closed` | 会话关闭 |
| `agent.connected` | Agent 连接 |
| `agent.disconnected` | Agent 断开 |

---

## 10. 速率限制

### 10.1 限制规则

| 端点 | 限制 |
|------|------|
| 默认 | 100 请求/分钟 |
| 认证用户 | 1000 请求/分钟 |
| `/api/v1/memories` | 500 请求/分钟 |
| `/api/v1/search` | 200 请求/分钟 |
| `/api/v1/search/semantic` | 100 请求/分钟 |

### 10.2 响应头

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1712937600
```

### 10.3 超出限制

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "code": 2001,
  "message": "Rate limit exceeded",
  "details": {
    "limit": 1000,
    "window": "1 minute",
    "retry_after": 60
  }
}
```

---

## 11. 错误码定义

### 11.1 错误码分类

| 范围 | 类别 |
|------|------|
| 1000-1099 | 认证错误 |
| 1100-1199 | 请求错误 |
| 1200-1299 | 资源错误 |
| 1300-1399 | 系统错误 |
| 2000-2099 | 限流错误 |

### 11.2 错误码列表

| 错误码 | 描述 | HTTP 状态 |
|--------|------|-----------|
| 1000 | 未授权 | 401 |
| 1001 | API Key 无效 | 401 |
| 1002 | Token 过期 | 401 |
| 1003 | 权限不足 | 403 |
| 1100 | 参数错误 | 400 |
| 1101 | 缺少必填参数 | 400 |
| 1102 | 参数格式错误 | 400 |
| 1200 | 资源不存在 | 404 |
| 1201 | 资源已存在 | 409 |
| 1202 | 资源被锁定 | 423 |
| 1300 | 内部错误 | 500 |
| 1301 | 服务不可用 | 503 |
| 2000 | 请求过于频繁 | 429 |
| 2001 | 超出配额限制 | 429 |

---

## 12. SDK 使用示例

### 12.1 Python SDK

```python
from api.client import MemoMind

# 初始化客户端
client = MemoMindClient(
    base_url="http://localhost:3000",
    api_key="mk_live_xxxxxxxxxxxxxxxx"
)

# 创建笔记
note = client.notes.create(
    title="项目计划",
    content="# 项目计划\n\n## 目标\n...",
    tags=["project"]
)
print(f"创建笔记: {note.id}")

# 搜索笔记
results = client.search.query("项目进度")
for result in results:
    print(f"{result.title}: {result.excerpt}")

# 存储记忆
memory = client.memories.store(
    content="用户偏好深色模式",
    agent_id="agent_xxx",
    type="preference",
    importance=0.8
)

# 检索记忆
memories = client.memories.retrieve(
    query="用户偏好",
    agent_id="agent_xxx",
    limit=5
)
for mem in memories:
    print(f"{mem.content} (相似度: {mem.similarity})")

# 创建会话
session = client.sessions.create(
    agent_id="agent_xxx",
    context={"topic": "产品讨论"}
)

# 更新会话
client.sessions.update(
    session.id,
    context={"messages": [{"role": "user", "content": "你好"}]}
)
```

### 12.2 Node.js SDK

```javascript
import { MemoMindClient } from '@memomind/sdk';

const client = new MemoMindClient({
  baseURL: 'http://localhost:3000',
  apiKey: 'mk_live_xxxxxxxxxxxxxxxx'
});

// 创建笔记
const note = await client.notes.create({
  title: '项目计划',
  content: '# 项目计划\n\n## 目标\n...',
  tags: ['project']
});

// 语义搜索
const results = await client.search.semantic({
  query: '人工智能应用',
  limit: 10
});

// 存储记忆
const memory = await client.memories.store({
  content: '用户偏好深色模式',
  agentId: 'agent_xxx',
  type: 'preference',
  importance: 0.8
});

// WebSocket 实时订阅
const ws = client.ws.connect();

ws.on('note.updated', (data) => {
  console.log('笔记更新:', data);
});

ws.subscribe('memory.created', {
  filter: { agentId: 'agent_xxx' }
});
```

### 12.3 cURL 示例

```bash
# 创建笔记
curl -X POST http://localhost:3000/api/v1/notes \
  -H "Authorization: Bearer mk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "项目计划",
    "content": "# 项目计划",
    "tags": ["project"]
  }'

# 搜索笔记
curl "http://localhost:3000/api/v1/search?q=项目" \
  -H "Authorization: Bearer mk_live_xxx"

# 存储记忆
curl -X POST http://localhost:3000/api/v1/memories \
  -H "Authorization: Bearer mk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "用户偏好深色模式",
    "agent_id": "agent_xxx",
    "type": "preference",
    "importance": 0.8
  }'

# 语义搜索
curl -X POST http://localhost:3000/api/v1/search/semantic \
  -H "Authorization: Bearer mk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能应用",
    "limit": 10
  }'
```

---

## 13. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-04-12 | 初始版本 |

---

*文档版本: v1.0*  
*创建日期: 2026-04-12*  
*作者: 产品助理*
