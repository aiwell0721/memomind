# REST API 参考

> 最后更新：2026-05-01
> API 版本：3.0.0
> 基础路径：`http://localhost:8000`
> Swagger 文档：`/api/docs`，Redoc：`/api/redoc`

---

## 认证

大部分端点需要 Bearer Token 认证。Token 通过 `POST /api/auth/login` 获取。

**请求头：**
```
Authorization: Bearer <token>
```

**Token 格式：** hex 编码的 `username:expire_timestamp`，默认有效期 24 小时。

**环境变量：**
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEMOMIND_SECRET_KEY` | 随机生成 | 密钥 |
| `MEMOMIND_TOKEN_EXPIRE` | 24 | Token 有效期（小时） |
| `MEMOMIND_CORS_ORIGINS` | `*` | CORS 允许的来源 |
| `MEMOMIND_ALLOWED_HOSTS` | 空 | 信任的主机列表 |
| `MEMOMIND_RATE_LIMIT` | `true` | 是否启用速率限制 |
| `MEMOMIND_RATE_LIMIT_MAX` | 100 | 每窗口最大请求数 |
| `MEMOMIND_RATE_LIMIT_WINDOW` | 60 | 速率限制窗口（秒） |

**安全头：** 所有响应自动添加 `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`X-XSS-Protection: 1; mode=block`、`Strict-Transport-Security`、`Content-Security-Policy: default-src 'self'`、`Cache-Control: no-store`。

---

## 健康检查

### `GET /api/health`

无需认证。

**响应：**
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "db_path": "/path/to/memomind.db"
}
```

---

## 认证 API

### `POST /api/auth/login`

无需认证。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | ✅ | 用户名 |

**响应：**
```json
{
  "access_token": "hex_encoded_token",
  "token_type": "bearer"
}
```

### `GET /api/auth/me`

需要认证。返回当前用户信息。

---

## 笔记 API

### `GET /api/notes`

需要认证。列出笔记列表。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | int | 否 | 100 | 返回数量（1-500） |
| `offset` | int | 否 | 0 | 偏移量 |
| `workspace_id` | int | 否 | - | 按工作区过滤 |

返回按 `updated_at DESC` 排序的笔记列表。

### `GET /api/notes/{note_id}`

需要认证。获取笔记详情。

### `POST /api/notes`

需要认证。创建笔记。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 笔记标题（1-500 字符） |
| `content` | string | ✅ | 笔记内容 |
| `tags` | string[] | 否 | 标签列表 |
| `workspace_id` | int | 否 | 工作区 ID（默认 1） |

返回 `{"id": <id>, "title": "<title>"}`。

### `PUT /api/notes/{note_id}`

需要认证。更新笔记（仅更新提供的字段）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 新标题 |
| `content` | string | 否 | 新内容 |
| `tags` | string[] | 否 | 新标签 |

自动更新链接关系（如果内容变化）和活动日志。

### `DELETE /api/notes/{note_id}`

需要认证。删除笔记。

### `POST /api/notes/search`

需要认证。全文搜索。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 搜索关键词 |
| `tags` | string[] | 否 | - | 按标签过滤 |
| `limit` | int | 否 | 20 | 返回数量（1-100） |
| `workspace_id` | int | 否 | - | 按工作区过滤 |

返回包含 `note`、`score`、`highlights` 的搜索结果列表。

---

## 标签 API

### `GET /api/tags`

需要认证。列出所有标签。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `tree` | bool | 否 | 返回树形结构 |

### `POST /api/tags`

需要认证。创建标签。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 标签名（1-100 字符） |
| `parent_id` | int | 否 | 父标签 ID（层级标签） |

### `DELETE /api/tags/{tag_id}`

需要认证。删除标签。

---

## 链接 API

### `GET /api/links/outgoing/{note_id}`

需要认证。获取笔记的出链（该笔记链接到其他笔记）。

### `GET /api/links/incoming/{note_id}`

需要认证。获取笔记的入链（反向链接，哪些笔记链接了该笔记）。

### `GET /api/links/graph`

需要认证。获取完整链接关系图。

### `GET /api/links/broken`

需要认证。获取断链列表（链接到不存在的笔记）。

### `GET /api/links/orphaned`

需要认证。获取孤立笔记（没有链接关系的笔记）。

---

## 版本 API

### `GET /api/notes/{note_id}/versions`

需要认证。获取笔记的版本历史。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | int | 否 | 20 | 返回数量（1-100） |

### `POST /api/notes/{note_id}/versions`

需要认证。保存笔记当前版本。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `summary` | string | 否 | 变更说明 |

### `POST /api/versions/{version_id}/restore`

需要认证。恢复到指定版本。

---

## 工作区 API

### `GET /api/workspaces`

需要认证。列出所有工作区。

### `GET /api/workspaces/{workspace_id}`

需要认证。获取工作区详情 + 统计信息。

### `POST /api/workspaces`

需要认证。创建工作区。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 工作区名（1-200 字符） |
| `description` | string | 否 | 描述 |

### `PUT /api/workspaces/{workspace_id}`

需要认证。更新工作区。

### `DELETE /api/workspaces/{workspace_id}`

需要认证。删除工作区。

### `POST /api/notes/{note_id}/move`

需要认证。将笔记移动到另一个工作区。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target_workspace_id` | int | ✅ (query) | 目标工作区 ID |

### `POST /api/workspaces/search`

需要认证。跨工作区搜索。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 搜索关键词 |
| `workspace_ids` | int[] | 否 | - | 指定工作区列表 |
| `limit` | int | 否 | 20 | 返回数量（1-100） |

---

## 用户 API

### `GET /api/users`

需要认证。列出所有用户。

### `GET /api/users/{user_id}`

需要认证。获取用户详情。

### `POST /api/users`

**无需认证**。注册用户。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | ✅ | 用户名（3-100 字符） |
| `display_name` | string | 否 | 显示名 |

返回 409 如果用户名已存在。

### `PUT /api/users/{user_id}`

需要认证。更新用户信息。

### `DELETE /api/users/{user_id}`

需要认证。删除用户。

### `GET /api/users/{user_id}/workspaces`

需要认证。获取用户所属的所有工作区。

---

## 成员 API

### `GET /api/workspaces/{workspace_id}/members`

需要认证。列出工作区所有成员。

### `POST /api/workspaces/{workspace_id}/members`

需要认证。添加工作区成员。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | int | ✅ | 用户 ID |
| `role` | string | 否 | 角色（owner/editor/viewer，默认 viewer） |

### `DELETE /api/workspaces/{workspace_id}/members/{user_id}`

需要认证。移除工作区成员。

### `PUT /api/workspaces/{workspace_id}/members/{user_id}/role`

需要认证。更新成员角色。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `role` | string | ✅ | 新角色（owner/editor/viewer） |

---

## 活动日志 API

### `GET /api/activity`

需要认证。获取活动时间线。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `workspace_id` | int | 否 | - | 按工作区过滤 |
| `user_id` | int | 否 | - | 按用户过滤 |
| `note_id` | int | 否 | - | 按笔记过滤 |
| `action` | string | 否 | - | 按操作类型过滤 |
| `limit` | int | 否 | 50 | 返回数量（1-200） |
| `offset` | int | 否 | 0 | 偏移量 |

### `GET /api/notes/{note_id}/activity`

需要认证。获取笔记的操作历史。

### `GET /api/workspaces/{workspace_id}/activity`

需要认证。获取工作区的活动记录。

### `GET /api/users/{user_id}/activity`

需要认证。获取用户的活动记录。

### `GET /api/workspaces/{workspace_id}/activity/stats`

需要认证。获取工作区的活动统计（按操作类型计数）。

---

## 冲突 API

### `GET /api/notes/{note_id}/conflicts`

需要认证。获取笔记的冲突历史。

### `GET /api/conflicts/unresolved`

需要认证。获取未解决的冲突。

### `GET /api/conflicts/stats`

需要认证。获取冲突统计。

### `POST /api/conflicts/{conflict_id}/resolve`

需要认证。解决冲突。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `strategy` | string | ✅ | 解决策略：`latest-wins` / `merge` / `manual` |
| `use_ours` | bool | 否 | `latest-wins` 策略时使用哪方内容 |
| `resolved_content` | string | 否 | `manual` 策略时提供的合并后内容 |

---

## 备份 API

### `POST /api/backups`

需要认证。创建数据库备份（gzip 压缩）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `description` | string | 否 | 备份描述 |

### `GET /api/backups`

需要认证。列出所有备份。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | int | 否 | 50 | 返回数量（1-200） |

### `GET /api/backups/stats`

需要认证。获取备份统计。

### `DELETE /api/backups/{backup_id}`

需要认证。删除备份。

### `POST /api/backups/{backup_id}/restore`

需要认证。从备份恢复数据库。

### `POST /api/backups/export`

需要认证。导出所有数据为 JSON。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `output_path` | string | 否 | 输出路径 |

### `POST /api/backups/cleanup`

需要认证。清理旧备份（保留最近 N 个）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `keep_count` | int | 否 | 10 | 保留数量（1-100） |
