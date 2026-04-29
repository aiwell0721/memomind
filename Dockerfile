# MemoMind - Multi-stage Docker Build
# Stage 1: Dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

LABEL maintainer="MemoMind Team"
LABEL description="团队知识库与智能笔记系统 - Team Knowledge Base & Smart Notes"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /data/memomind /data/backups

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MEMOMIND_DB_PATH=/data/memomind/memomind.db
ENV MEMOMIND_BACKUP_DIR=/data/backups

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: start REST API server
CMD ["sh", "-c", "python -c \"from core.api_server import create_app; import uvicorn; uvicorn.run(create_app('${MEMOMIND_DB_PATH}'), host='0.0.0.0', port=8000)\""]
