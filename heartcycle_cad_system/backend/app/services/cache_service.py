"""
缓存服务
"""
import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """简单的内存缓存服务"""

    def __init__(self):
        self._cache = {}
        self._ttl = {}  # 存储过期时间

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数序列化为字符串
        key_parts = [prefix]

        if args:
            key_parts.extend([str(arg) for arg in args])

        if kwargs:
            # 按键排序以确保一致性
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend([f"{k}={v}" for k, v in sorted_kwargs])

        key_string = ":".join(key_parts)

        # 如果键太长，使用哈希
        if len(key_string) > 200:
            return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"

        return key_string

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        import time

        # 检查是否过期
        if key in self._ttl:
            if time.time() > self._ttl[key]:
                # 已过期，删除
                self.delete(key)
                return None

        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        import time

        self._cache[key] = value

        if ttl:
            self._ttl[key] = time.time() + ttl
        elif key in self._ttl:
            del self._ttl[key]

        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def delete(self, key: str):
        """删除缓存"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        logger.debug(f"Cache deleted: {key}")

    def clear(self):
        """清空所有缓存"""
        self._cache.clear()
        self._ttl.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """获取缓存统计"""
        import time

        now = time.time()
        expired_count = sum(1 for exp_time in self._ttl.values() if exp_time < now)

        return {
            'total_keys': len(self._cache),
            'expired_keys': expired_count,
            'active_keys': len(self._cache) - expired_count,
            'memory_usage_estimate': sum(
                len(str(k)) + len(str(v))
                for k, v in self._cache.items()
            )
        }

    def cleanup_expired(self):
        """清理过期的缓存"""
        import time

        now = time.time()
        expired_keys = [
            key for key, exp_time in self._ttl.items()
            if exp_time < now
        ]

        for key in expired_keys:
            self.delete(key)

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


# 全局缓存实例
cache_service = CacheService()


def cached(
    prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable] = None
):
    """
    缓存装饰器

    Parameters:
    -----------
    prefix : str
        缓存键前缀
    ttl : int
        过期时间（秒），默认5分钟
    key_builder : Optional[Callable]
        自定义键生成函数
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_service._generate_key(prefix, *args, **kwargs)

            # 尝试从缓存获取
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # 缓存未命中，执行函数
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)

            # 存入缓存
            cache_service.set(cache_key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_service._generate_key(prefix, *args, **kwargs)

            # 尝试从缓存获取
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # 缓存未命中，执行函数
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)

            # 存入缓存
            cache_service.set(cache_key, result, ttl)

            return result

        # 根据函数类型返回对应的包装器
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(prefix: str, *args, **kwargs):
    """
    使缓存失效

    Parameters:
    -----------
    prefix : str
        缓存键前缀
    *args, **kwargs
        用于生成缓存键的参数
    """
    cache_key = cache_service._generate_key(prefix, *args, **kwargs)
    cache_service.delete(cache_key)
    logger.debug(f"Cache invalidated: {cache_key}")


def get_cache_service() -> CacheService:
    """获取全局缓存服务实例"""
    return cache_service
