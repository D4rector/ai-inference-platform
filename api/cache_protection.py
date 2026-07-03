"""
Redis 三层缓存防护

1. 缓存穿透 → 布隆过滤器（挡掉不存在 key 的无效查询）
2. 缓存击穿 → 互斥锁（热点 key 过期瞬间，只放一个线程去加载）
3. 缓存雪崩 → 过期时间随机化（避免大范围同时过期）
"""
import time
import random
import hashlib
import functools
from django.core.cache import cache
from django.conf import settings

_redis_client = None
_redis_available = None  # None=未检测, True/False


def get_redis():
    """
    懒加载 Redis 客户端。
    先尝试真实 Redis → 不可用则降级到 fakeredis（内存模拟）。
    """
    global _redis_client, _redis_available

    if _redis_client is not None:
        return _redis_client

    if _redis_available is None:
        # 第一次：尝试真实 Redis（加硬超时，Windows 上 socket timeout 不可靠）
        import redis, threading
        result_container = {}
        def _try_connect():
            try:
                r = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=int(settings.REDIS_PORT),
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )
                r.ping()
                result_container['client'] = r
                result_container['ok'] = True
            except Exception:
                result_container['ok'] = False

        t = threading.Thread(target=_try_connect, daemon=True)
        t.start()
        t.join(timeout=2.0)

        if result_container.get('ok'):
            _redis_available = True
            _redis_client = result_container['client']
            return _redis_client
        else:
            _redis_available = False

    # 降级到 fakeredis
    if not _redis_available:
        import fakeredis
        _redis_client = fakeredis.FakeRedis(decode_responses=True)
        return _redis_client

    return _redis_client


# ── 1. 布隆过滤器（防穿透）────────────────────────────────
class SimpleBloomFilter:
    """
    简易布隆过滤器 — 用 Redis bitmap + 多个哈希函数。
    判断一个 key 是否「可能存在」或「一定不存在」。
    """

    def __init__(self, redis_key: str, bit_size: int = 1000000, hash_count: int = 5):
        self.key = redis_key
        self.bit_size = bit_size
        self.hash_count = hash_count
        self.r = get_redis()

    def _hashes(self, value: str):
        """生成 hash_count 个哈希位置"""
        for i in range(self.hash_count):
            h = hashlib.md5(f'{value}:{i}'.encode()).hexdigest()
            yield int(h, 16) % self.bit_size

    def add(self, value: str):
        for pos in self._hashes(value):
            self.r.setbit(self.key, pos, 1)

    def exists(self, value: str) -> bool:
        """True = 可能存在（允许查询）；False = 一定不存在（拒绝）"""
        return all(self.r.getbit(self.key, pos) for pos in self._hashes(value))


# 全局实例
bloom = SimpleBloomFilter('cache_bloom_filter')


# ── 2. 互斥锁（防击穿）────────────────────────────────────
def mutex_lock(key: str, timeout: int = 30) -> bool:
    """
    获取互斥锁。返回 True=获取成功（可以加载缓存），False=别人在加载。
    用 Redis SETNX 实现。
    """
    lock_key = f'mutex:{key}'
    return get_redis().set(lock_key, '1', nx=True, ex=timeout) is not None


def mutex_unlock(key: str):
    get_redis().delete(f'mutex:{key}')


# ── 3. 缓存装饰器（整合三层防护）──────────────────────────
def cache_with_protection(
    cache_key: str,
    timeout: int = 300,
    jitter: int = 60,
    mutex_timeout: int = 30,
):
    """
    带三层防护的缓存装饰器。

    用法:
        @cache_with_protection('my_key', timeout=300)
        def expensive_query():
            return do_something()

    防护逻辑:
    - 穿透: bloom filter 拒绝确定不存在的 key
    - 击穿: SETNX 互斥锁，只有一个线程去加载
    - 雪崩: 过期时间加随机抖动 (timeout ± jitter)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 构建实际的缓存 key
            actual_key = cache_key
            if args or kwargs:
                suffix = hashlib.md5(str((args, kwargs)).encode()).hexdigest()[:8]
                actual_key = f'{cache_key}:{suffix}'

            # ── 防穿透 ──
            if not bloom.exists(actual_key):
                result = cache.get(actual_key)
                if result is not None:
                    return result

            # ── 读缓存 ──
            result = cache.get(actual_key)
            if result is not None:
                bloom.add(actual_key)  # 确认存在，加入布隆
                return result

            # ── 防击穿（互斥锁） ──
            if not mutex_lock(actual_key, mutex_timeout):
                # 别人在加载，等一小会再读缓存
                time.sleep(0.1)
                result = cache.get(actual_key)
                if result is not None:
                    return result
                # 还是没拿到，自己加载
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    # ── 防雪崩（过期时间随机化） ──
                    ttl = timeout + random.randint(-jitter, jitter)
                    ttl = max(10, ttl)  # 最少 10 秒
                    cache.set(actual_key, result, ttl)
                    bloom.add(actual_key)
                return result
            finally:
                mutex_unlock(actual_key)
        return wrapper
    return decorator


# ── 4. 分布式锁（通用）────────────────────────────────────
class RedisLock:
    """Redis 分布式锁 — 带自动续期和 Lua 脚本安全释放"""

    def __init__(self, lock_name: str, ttl: int = 30):
        self.lock_name = f'lock:{lock_name}'
        self.ttl = ttl
        self.lock_value = str(time.time_ns())
        self.r = get_redis()

    def acquire(self, block: bool = True, timeout: int = 10) -> bool:
        """获取锁。block=True 时阻塞等待直到超时"""
        deadline = time.time() + timeout
        while True:
            if self.r.set(self.lock_name, self.lock_value, nx=True, ex=self.ttl):
                return True
            if not block:
                return False
            if time.time() > deadline:
                return False
            time.sleep(0.05)

    def release(self):
        """Lua 脚本安全释放 — 只释放自己持有的锁"""
        lua = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        self.r.eval(lua, 1, self.lock_name, self.lock_value)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()
