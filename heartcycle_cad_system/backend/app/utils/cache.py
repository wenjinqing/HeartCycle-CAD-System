"""
简单的内存缓存实现
"""
from typing import Any, Optional, Callable
from functools import wraps
import time
import hashlib
import json


class SimpleCache:
    """简单的内存缓存"""
    
    def __init__(self, default_ttl: int = 3600):
        """
        初始化缓存
        
        Parameters:
        -----------
        default_ttl : int
            默认过期时间（秒）
        """
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Parameters:
        -----------
        key : str
            缓存键
            
        Returns:
        --------
        Any or None : 缓存值，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            return None
        
        value, expire_time = self.cache[key]
        
        if time.time() > expire_time:
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存值
        
        Parameters:
        -----------
        key : str
            缓存键
        value : Any
            缓存值
        ttl : int, optional
            过期时间（秒），如果不提供则使用默认值
        """
        ttl = ttl or self.default_ttl
        expire_time = time.time() + ttl
        self.cache[key] = (value, expire_time)
    
    def delete(self, key: str):
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """清空所有缓存"""
        self.cache.clear()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({
            'args': args,
            'kwargs': sorted(kwargs.items())
        }, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()


# 全局缓存实例
cache = SimpleCache(default_ttl=3600)


def cached(ttl: Optional[int] = None):
    """
    缓存装饰器
    
    Parameters:
    -----------
    ttl : int, optional
        缓存过期时间（秒）
        
    Example:
    --------
    @cached(ttl=3600)
    def expensive_function(x, y):
        return x + y
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache._generate_key(func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


