# MemoMind 部署指南

## 方式一：Docker（推荐）

### 快速启动

```bash
# 克隆仓库
git clone https://github.com/aiwell0721/memomind.git
cd memomind

# 一键启动
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| REST API | http://localhost:8000 | 核心 API |
| Swagger 文档 | http://localhost:8000/docs | API 交互文档 |
| MCP Server | http://localhost:8001 | HTTP 模式 |

### 数据持久化

数据存储在 Docker 卷中，容器重启不会丢失：

```bash
# 查看数据卷
docker volume ls | grep memomind

# 备份数据
docker run --rm -v memomind_memomind_data:/data -v $(pwd):/backup alpine tar czf /backup/memomind-backup.tar.gz /data

# 恢复数据
docker run --rm -v memomind_memomind_data:/data -v $(pwd):/backup alpine tar xzf /backup/memomind-backup.tar.gz -C /
```

### 自定义配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
nano .env

# 重启生效
docker compose up -d
```

### 使用 Makefile

```bash
# 查看所有命令
make help

# 构建镜像
make docker-build

# 启动
make docker-up

# 停止
make docker-down

# 进入容器
make docker-shell
```

---

## 方式二：本地安装

### 环境要求

- Python 3.10+
- pip

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/aiwell0721/memomind.git
cd memomind

# 安装依赖
pip install -r requirements.txt

# 启动 REST API
python -c "from core.api_server import create_app; import uvicorn; uvicorn.run(create_app('memomind.db'), host='0.0.0.0', port=8000)"

# 或启动 MCP Server
python -m mcp_server --db memomind.db
```

---

## 方式三：生产部署

### 使用 Caddy 反向代理（HTTPS）

```bash
# 安装 Caddy
apt install -y caddy

# 配置 /etc/caddy/Caddyfile
memomind.example.com {
    reverse_proxy localhost:8000
}

# 重启 Caddy
systemctl restart caddy
```

### 使用 Nginx 反向代理

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

### 系统服务（systemd）

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

```bash
# 启用服务
systemctl enable memomind
systemctl start memomind
systemctl status memomind
```

---

## 故障排查

### 容器无法启动

```bash
# 查看日志
docker compose logs memomind

# 检查健康状态
docker compose ps

# 重新构建
docker compose build --no-cache
docker compose up -d
```

### 数据库连接失败

```bash
# 检查数据卷权限
docker compose exec memomind ls -la /data/memomind/

# 重新初始化
docker compose down -v
docker compose up -d
```

### API 无响应

```bash
# 检查健康端点
curl http://localhost:8000/health

# 检查端口占用
lsof -i :8000
```

---

## 监控

### Docker 内置监控

```bash
# 查看资源使用
docker stats memomind

# 查看日志
docker compose logs -f --tail=100
```

### 健康检查

```bash
# 手动检查
curl -f http://localhost:8000/health

# 预期响应
# {"status": "ok", "database": "connected"}
```
