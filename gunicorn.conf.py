"""
Gunicorn 生产配置
启动: gunicorn -c gunicorn.conf.py ai_platform.wsgi:application
"""
import multiprocessing
import os

# 绑定
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker 进程数 = CPU 核心数 × 2 + 1
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)

# Worker 类型
worker_class = 'sync'
worker_connections = 1000

# 超时
timeout = 120
graceful_timeout = 30

# 日志
accesslog = '-'  # stdout
errorlog = '-'
loglevel = 'info'

# 进程命名
proc_name = 'ai_platform'

# 优雅重启
max_requests = 1000
max_requests_jitter = 50
