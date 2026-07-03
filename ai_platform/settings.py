"""
Django settings for AI 推理平台.
兼容本地开发(SQLite) 和生产部署(PostgreSQL/Redis)。
"""
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ── Application ──────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 三方
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # 业务
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',          # CORS 放最前面
    'observability.RequestLogMiddleware',            # 请求日志
    'api.rate_limit.RateLimitMiddleware',            # 令牌桶限流 (fakeredis)
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ai_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend' / 'dist'],  # Vue SPA 入口
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ai_platform.wsgi.application'

# ── Database ─────────────────────────────────────────────
# 默认 SQLite（无需 Docker 即可开发），生产用 PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}

# ── Redis / Cache ────────────────────────────────────────
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'{REDIS_URL}/0',
    }
}

# ── Celery ───────────────────────────────────────────────
CELERY_BROKER_URL = f'{REDIS_URL}/1'
CELERY_RESULT_BACKEND = f'{REDIS_URL}/2'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'

# ── DRF ──────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ── SimpleJWT ────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS ─────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',     # Vite dev server
    'http://localhost:3000',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

# ── Password validation ──────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalization ─────────────────────────────────
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# ── Static & Media ───────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'frontend' / 'dist',  # Vue 构建产物
]

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 前端 dist 中的 assets 目录
FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── AI 推理服务地址 ──────────────────────────────────────
AI_INFERENCE_URL = os.getenv('AI_INFERENCE_URL', 'http://localhost:8080')

# ── 日志 ──────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'observability.JsonLogFormatter',
        },
    },
    'handlers': {
        'redis_stream': {
            '()': 'observability.RedisStreamHandler',
            'stream': 'ai-platform-logs',
            'formatter': 'json',
            'level': 'INFO',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'redis_stream'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'level': 'INFO', 'propagate': True},
        'ai_platform': {'level': 'INFO', 'propagate': True},
    },
}
