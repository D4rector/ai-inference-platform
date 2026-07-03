# 🧠 AI 推理平台

基于 Django + Vue 3 的生产级 AI 推理平台，支持文本摘要、图像识别、代码生成等多模态任务。

## 架构

```
用户浏览器 (:80)
    │
    ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Nginx   │────▶│  Django/Gunicorn │────▶│  AI 推理服务  │
│  静态文件  │     │  (API + 业务)  │     │  (FastAPI:8080)│
└──────────┘     └──────┬───────┘     └──────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │PostgreSQL│  │  Redis   │  │  Celery  │
   │  数据持久化│  │ 缓存/消息 │  │  异步任务  │
   └──────────┘  └──────────┘  └──────────┘
```

## 快速开始

### 本地开发 (当前可用)
```bash
# 终端 1: Django 后端
cd ai-platform
.venv\Scripts\python manage.py runserver 0.0.0.0:8000

# 终端 2: Vue 前端
cd ai-platform/frontend
npm run dev

# 或者一键启动
start.bat
```
访问: http://localhost:5173
测试账号: `testuser` / `test1234` 或 `admin` / `admin123`

### Docker 部署 (需 Docker Desktop)
```bash
docker-start.bat
# 或
docker compose up -d
```
访问: http://localhost

## API 端点

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /api/register/ | 用户注册 | 否 |
| POST | /api/token/ | JWT 登录 | 否 |
| POST | /api/token/refresh/ | 刷新 Token | 否 |
| GET | /api/abilities/ | AI 能力列表 | 否 |
| GET | /api/tasks/ | 任务列表 | JWT |
| POST | /api/tasks/ | 创建任务 | JWT |
| GET | /api/tasks/{id}/ | 任务详情 | JWT |
| POST | /api/tasks/{id}/retry/ | 重试失败任务 | JWT |
| GET | /api/tasks/dashboard/ | 仪表盘统计 | JWT |
| GET | /api/models/ | 模型注册表 | JWT |

## AI 能力

| 类型 | Key | 说明 |
|------|-----|------|
| 文本摘要 | text_summary | 提取长文本核心要点 |
| 文本生成 | text_generation | 根据提示词生成内容 |
| 图像识别 | image_classify | 分类标签 + 置信度 |
| 图像生成 | image_generate | 文本 → 图像 |
| 代码生成 | code_generate | 需求 → 代码片段 |

新增能力只需在 `api/ai_service.py` 的 `ABILITIES` 字典加一行配置。

## 项目结构

```
ai-platform/
├── ai_platform/        # Django 项目配置
├── api/                # API 业务逻辑
│   ├── models.py       # AITask(状态机) + AIModel
│   ├── views.py        # ViewSet + 仪表盘
│   ├── ai_service.py   # ABILITIES 字典 + Mock 推理
│   ├── cache_protection.py  # 布隆过滤器 + 互斥锁 + 分布式锁
│   └── rate_limit.py   # 令牌桶限流
├── observability/      # 日志管道 + AI 告警 Agent
├── k8s/                # Kubernetes 部署配置
├── nginx/              # Nginx 配置
├── frontend/           # Vue 3 + TypeScript + Element Plus
├── Dockerfile          # 多阶段构建
├── docker-compose.yml  # 4 容器编排
├── start.bat           # Windows 一键启动
└── docker-start.bat    # Docker 一键部署
```

## 核心特性

- **任务状态机**: pending → processing → completed/failed
- **JWT 认证**: 双 Token 机制，自动刷新
- **多能力路由**: ABILITIES 字典，新增能力仅一行配置
- **Redis 三层防护**: 布隆过滤器(防穿透) + 互斥锁(防击穿) + TTL 随机化(防雪崩)
- **令牌桶限流**: Lua 原子操作，Redis 不可用时自动降级(fail-open)
- **Docker 一键部署**: 4 容器编排，Volume 持久化
- **Kubernetes**: Deployment + Service + Ingress，3 副本自愈
- **可观测性**: JSON 日志 + Kafka 管道 + Ollama LangChain 智能告警

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Django 6 + DRF + SimpleJWT + Celery |
| 数据库 | PostgreSQL 16 + Redis 7 |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus |
| 部署 | Docker + Nginx + Gunicorn + K8s |
| 模型 | PyTorch → ONNX → INT8 → TensorRT |
| 可观测 | Kafka + Elasticsearch + Kibana + Ollama |
