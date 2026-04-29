FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt jieba

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p /data

# 暴露端口（如需 Web API）
EXPOSE 8000

# 默认命令
CMD ["python", "cli.py", "--db", "/data/memomind.db"]
