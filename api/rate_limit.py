"""
令牌桶限流中间件

原理（厨房类比）：
- 令牌桶 = 一个碗，每秒放 N 个汤圆进去
- 每来一个请求 = 吃一个汤圆
- 碗空了 = 请求被拒（429 Too Many Requests）
- 碗满了就不再放汤圆（防止无限堆积）

优势 vs 固定窗口：允许突发流量，长时平均被控制。
"""
import time
import hashlib
import functools
from django.http import JsonResponse
from django.conf import settings
from .cache_protection import get_redis


class TokenBucketRateLimiter:
    """
    令牌桶限流器。
    rate: 每秒生成 token 数
    capacity: 桶容量（允许的最大突发）
    """

    def __init__(self, rate: int = 50, capacity: int = 100):
        self.rate = rate
        self.capacity = capacity

    def _get_bucket_key(self, identifier: str, endpoint: str) -> str:
        h = hashlib.md5(f'{identifier}:{endpoint}'.encode()).hexdigest()[:12]
        return f'rate_limit:{h}'

    def is_allowed(self, identifier: str, endpoint: str = 'default') -> tuple[bool, int]:
        """
        检查是否允许请求。返回 (是否允许, 剩余token数)
        - 真实 Redis: Lua 原子操作
        - fakeredis: Python 实现（不支持 Lua eval）
        """
        key = self._get_bucket_key(identifier, endpoint)
        try:
            r = get_redis()
            now = time.time()

            # 尝试 Lua 原子操作（真实 Redis）
            try:
                lua = """
                local key = KEYS[1]
                local rate = tonumber(ARGV[1])
                local capacity = tonumber(ARGV[2])
                local now = tonumber(ARGV[3])
                local tokens = tonumber(redis.call('get', key..':tokens')) or capacity
                local last_refill = tonumber(redis.call('get', key..':last')) or now
                local elapsed = math.max(0, now - last_refill)
                tokens = math.min(capacity, tokens + elapsed * rate)
                if tokens >= 1 then
                    tokens = tokens - 1
                    redis.call('set', key..':tokens', tokens)
                    redis.call('set', key..':last', now)
                    redis.call('expire', key..':tokens', 300)
                    redis.call('expire', key..':last', 300)
                    return {1, math.floor(tokens)}
                else
                    return {0, 0}
                end
                """
                result = r.eval(lua, 1, key, self.rate, self.capacity, now)
                return bool(result[0]), int(result[1])
            except Exception:
                pass  # Lua 不可用(fakeredis) → 降级到 Python

            # Python 实现（非原子，但 fakeredis 够用）
            tokens = float(r.get(f'{key}:tokens') or self.capacity)
            last_refill = float(r.get(f'{key}:last') or now)
            elapsed = max(0, now - last_refill)
            tokens = min(self.capacity, tokens + elapsed * self.rate)
            if tokens >= 1:
                tokens -= 1
                r.set(f'{key}:tokens', tokens)
                r.set(f'{key}:last', now)
                r.expire(f'{key}:tokens', 300)
                r.expire(f'{key}:last', 300)
                return True, int(tokens)
            else:
                r.set(f'{key}:last', now)
                return False, 0
        except Exception:
            return True, -1  # 彻底不可用 — fail open


class RateLimitMiddleware:
    """
    Django 中间件 — 令牌桶限流。
    针对 /api/tasks/ 等高频端点。
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # 不同端点不同限流策略
        self.limiters = {
            'tasks': TokenBucketRateLimiter(rate=20, capacity=50),   # 任务提交 20/s
            'token': TokenBucketRateLimiter(rate=10, capacity=30),   # 登录 10/s
            'default': TokenBucketRateLimiter(rate=50, capacity=100),
        }

    def __call__(self, request):
        # 获取用户标识（未登录用 IP）
        identifier = (
            request.user.username
            if hasattr(request, 'user') and request.user.is_authenticated
            else request.META.get('REMOTE_ADDR', 'unknown')
        )

        # 根据路径选限流器
        path = request.path
        if '/api/tasks/' in path:
            limiter = self.limiters['tasks']
            endpoint = 'tasks'
        elif '/api/token/' in path:
            limiter = self.limiters['token']
            endpoint = 'token'
        else:
            limiter = self.limiters['default']
            endpoint = 'default'

        allowed, remaining = limiter.is_allowed(identifier, endpoint)

        if not allowed:
            return JsonResponse({
                'error': '请求过于频繁，请稍后再试',
                'retry_after': 1,
            }, status=429)

        response = self.get_response(request)
        # 在响应头里告知剩余配额
        response['X-RateLimit-Remaining'] = remaining
        return response


def rate_limit(rate: int = 50, capacity: int = 100):
    """
    视图装饰器版本 — 给特定端点单独限流。

    @rate_limit(rate=5, capacity=10)
    def my_view(request):
        ...
    """
    limiter = TokenBucketRateLimiter(rate=rate, capacity=capacity)

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            identifier = (
                request.user.username
                if request.user.is_authenticated
                else request.META.get('REMOTE_ADDR', 'unknown')
            )
            allowed, _ = limiter.is_allowed(identifier, view_func.__name__)
            if not allowed:
                return JsonResponse({
                    'error': '请求过于频繁',
                    'retry_after': 1,
                }, status=429)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
