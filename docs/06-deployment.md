# 配置与部署

> 最后更新：2026-05-01
> 版本：3.0.0

---

## 方式一：Docker（推荐）

### 快速启动

```bash
git clone https://github.com/aiwell0721/memomind.git
cd memomind
docker compose up -d
docker compose ps
```

### 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| REST API | http://localhost:8000 | 核心 API |
| Swagger 文档 | http://localhost:8000/api/docs | API 交互文档 |
| MCP Server | http://localhost:8001 | HTTP 模式 |
| Web Dashboard | http://localhost:3000 | React 前端 |

### 数据持久化

数据存储在 Docker 卷中，容器重启不丢失。

```bash
docker volume ls | grep memomind
```

### 环境变量

```bash
cp .env.example .env
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEMOMIND_SECRET_KEY` | 随机 | JWT 密钥 |
| `MEMOMIND_TOKEN_EXPIRE` | 24 | Token 有效期（小时） |
| `MEMOMIND_CORS_ORIGINS` | `*` | CORS 来源 |
| `MEMOMIND_ALLOWED_HOSTS` | 空 | 信任主机 |
| `MEMOMIND_RATE_LIMIT` | `true` | 启用速率限制 |
| `MEMOMIND_RATE_LIMIT_MAX` | 100 | 每窗口最大请求 |
| `MEMOMIND_RATE_LIMIT_WINDOW` | 60 | 速率限制窗口（秒） |

---

## 方式二：本地安装

### 环境要求

- Python 3.10+
- pip

### 安装步骤

```bash
git clone https://github.com/aiwell0721/memomind.git
cd memomind
pip install -r requirements.txt

# 启动 REST API
python -c "from core.api_server import create_app; import uvicorn; uvicorn.run(create_app('memomind.db'), host='0.0.0.0', port=8000)"

# 或启动 MCP Server
python -m mcp_server --db memomind.db
```

---

## 方式三：生产部署

### Caddy 反向代理（自动 HTTPS）

```
memomind.example.com {
    reverse_proxy localhost:8000
}
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name memomind.example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### systemd 服务

```ini
# /etc/systemd/system/memomind.service
[Unit]
Description=MemoMind Knowledge Base
After=network.target

[Service]
Type=simple
User=memomind
WorkingDirectory=/opt/memomind
ExecStart=/opt/memomind/venv/bin/python -m mcp_server --db /opt/memomind/data/memomind.db --transport http --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## MCP Server 配置

### Claude Desktop 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "memomind": {
      "command": "python",
      "args": ["-m", "mcp_server", "--db", "/path/to/memomind.db"]
    }
  }
}
```

### OpenClaw / 远程访问

使用 HTTP 模式：

```bash
python -m mcp_server --db memomind.db --transport http --port 8001
```

---

## 健康检查

```bash
curl -f http://localhost:8000/api/health
# {"status": "healthy", "version": "3.0.0", "db_path": "..."}
```

## 监控

```bash
# Docker 资源监控
docker stats memomind

# 日志查看
docker compose logs -f --tail=100
```
