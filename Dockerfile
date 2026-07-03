# ── 阶段 1: 构建前端 ────────────────────────────────────
FROM docker.m.daocloud.io/library/node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── 阶段 2: Django 后端 ──────────────────────────────────
FROM docker.m.daocloud.io/library/python:3.12-slim

WORKDIR /app

# 系统依赖（国内镜像加速）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（国内镜像加速）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Django 代码
COPY . .

# 前端静态文件（从阶段1复制）
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# 静态文件收集
RUN python manage.py collectstatic --noinput

# 运行
EXPOSE 8000
CMD ["gunicorn", "ai_platform.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-"]
