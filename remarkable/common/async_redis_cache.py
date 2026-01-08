"""
Redis cache decorator utilities
"""

import functools
import hashlib
import json
import logging
import pickle
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar
from uuid import UUID

from remarkable.db import async_rdb

__all__ = ["redis_acache", "clear_cache", "redis_acache_with_lock"]


logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


@asynccontextmanager
async def get_cache_rdb():
    """Context manager for getting a cache store"""
    rdb = async_rdb()
    try:
        yield rdb
    finally:
        # RedisStore handles cleanup automatically
        pass


def _serialize_for_key(obj: Any) -> str:
    """Serialize an object for use in cache key generation"""
    if obj is None:
        return "None"
    elif isinstance(obj, (str, int, float, bool)):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, (list, tuple)):
        return f"[{','.join(_serialize_for_key(item) for item in obj)}]"
    elif isinstance(obj, dict):
        items = sorted(obj.items())
        return f"{{{','.join(f'{_serialize_for_key(k)}:{_serialize_for_key(v)}' for k, v in items)}}}"
    else:
        # For complex objects, use their string representation
        return str(obj)


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from function name and arguments"""
    try:
        # Create a stable string representation of arguments
        args_str = ",".join(_serialize_for_key(arg) for arg in args)
        kwargs_items = sorted(kwargs.items())
        kwargs_str = ",".join(f"{k}={_serialize_for_key(v)}" for k, v in kwargs_items)

        # Combine all parts
        full_key = f"{func_name}({args_str}){{{kwargs_str}}}"

        # Create a hash for shorter keys while keeping it readable
        args_hash = hashlib.sha256(full_key.encode()).hexdigest()[:16]

        return f"{func_name}:{args_hash}"
    except Exception as e:
        logger.warning(f"Failed to generate cache key for {func_name}: {e}")
        # Fallback to a simple hash of the function name and current timestamp
        fallback = f"{func_name}:fallback:{hash((args, tuple(sorted(kwargs.items()))))}"
        return fallback


def _serialize_value(value: Any) -> bytes:
    """Serialize a value for caching using pickle for better type support"""
    try:
        return pickle.dumps(value)
    except Exception as e:
        logger.warning(f"Failed to pickle value, falling back to JSON: {e}")
        # Fallback to JSON for simple types
        return json.dumps(value, default=str).encode()


def _deserialize_value(data: bytes) -> Any:
    """Deserialize a cached value, trying pickle first then JSON"""
    try:
        return pickle.loads(data)
    except Exception:
        try:
            # Fallback to JSON
            return json.loads(data.decode())
        except Exception as e:
            logger.warning(f"Failed to deserialize cached value: {e}")
            raise


async def clear_cache(namespace: str = "acache", pattern: str = "*") -> int:
    """
    Clear cache entries matching a pattern

    Args:
        namespace: Redis namespace to clear
        pattern: Pattern to match keys (default: "*" for all keys)

    Returns:
        Number of keys deleted
    """
    async with get_cache_rdb() as rdb:
        try:
            # Get all keys matching the pattern
            keys = await rdb.keys(f"{namespace}:{pattern}")
            if keys:
                deleted = await rdb.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries from namespace '{namespace}' with pattern '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
            return 0


def redis_acache(
    expire_seconds: int = 600,
    namespace: str = "acache",
    key_func: Callable[[str, tuple, dict], str] | None = None,
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """
    Async Redis cache decorator

    Args:
        expire_seconds: Cache expiration time in seconds (default: 600 = 10 minutes)
        namespace: Redis namespace for the cache (default: "cache")
        key_func: Optional custom function to generate cache keys

    Usage:
        @redis_acache(expire_seconds=300)
        async def my_function(arg1, arg2):
            return expensive_operation(arg1, arg2)
    """

    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Generate cache key
            try:
                if key_func:
                    cache_key = key_func(func.__name__, args, kwargs)
                else:
                    cache_key = _generate_cache_key(func.__name__, args, kwargs)
            except Exception as e:
                logger.error(f"Failed to generate cache key for {func.__name__}: {e}")
                # If key generation fails, just call the function
                return await func(*args, **kwargs)

            cache_key = f"{namespace}:{cache_key}"
            # Try to get from cache
            try:
                async with get_cache_rdb() as rdb:
                    cached_data = await rdb.get(cache_key)
                    if cached_data is not None:
                        # Cache hit - deserialize and return
                        try:
                            result = _deserialize_value(cached_data)
                            logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                            return result
                        except Exception as e:
                            logger.warning(f"Failed to deserialize cached value for {func.__name__}: {e}")
                            # Treat as cache miss and continue

                    # Cache miss - call the original function
                    logger.debug(f"Cache miss for {func.__name__} with key {cache_key}")
                    result = await func(*args, **kwargs)

                    # Cache the result
                    try:
                        serialized_result = _serialize_value(result)
                        await rdb.set(cache_key, serialized_result, ex=expire_seconds)
                        logger.debug(f"Cached result for {func.__name__} with key {cache_key}")
                    except Exception as e:
                        logger.warning(f"Failed to cache result for {func.__name__}: {e}")

                    return result

            except Exception as e:
                logger.error(f"Cache operation failed for {func.__name__}: {e}")
                # If cache fails, just call the function
                return await func(*args, **kwargs)

        return wrapper

    return decorator


@asynccontextmanager
async def redis_lock(rdb, lock_key: str, timeout: float = 30.0, wait_time: float = 0.1):
    """
    Redis分布式锁的上下文管理器

    Args:
        rdb: Redis连接实例
        lock_key: 锁的键名
        timeout: 锁的超时时间（秒）
        wait_time: 获取锁的等待间隔（秒）
    """
    lock = rdb.lock(lock_key, timeout=timeout, blocking_timeout=timeout, sleep=wait_time)

    try:
        # 获取锁
        await lock.acquire()
        yield

    finally:
        # 释放锁
        await lock.release()


def redis_acache_with_lock(
    expire_seconds: int = 600,
    namespace: str = "acache",
    key_func: Callable[[str, tuple, dict], str] | None = None,
    lock_timeout: float = 30.0,
    lock_wait_time: float = 0.1,
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """
    带分布式锁的异步Redis缓存装饰器
    在缓存未命中时，确保只有一个进程执行函数

    Args:
        expire_seconds: 缓存过期时间（秒，默认600=10分钟）
        namespace: Redis命名空间（默认"acache"）
        key_func: 自定义缓存键生成函数
        lock_timeout: 锁超时时间（秒，默认30）
        lock_wait_time: 获取锁的等待间隔（秒，默认0.1）

    Usage:
        @redis_acache_with_lock(expire_seconds=300)
        async def my_function(arg1, arg2):
            return expensive_operation(arg1, arg2)
    """

    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # 生成缓存键
            try:
                if key_func:
                    cache_key = key_func(func.__name__, args, kwargs)
                else:
                    cache_key = _generate_cache_key(func.__name__, args, kwargs)
            except Exception as e:
                logger.error(f"Failed to generate cache key for {func.__name__}: {e}")
                return await func(*args, **kwargs)

            cache_key = f"{namespace}:{cache_key}"
            lock_key = f"{cache_key}:lock"

            # 尝试从缓存获取
            try:
                async with get_cache_rdb() as rdb:
                    cached_data = await rdb.get(cache_key)
                    if cached_data is not None:
                        try:
                            result = _deserialize_value(cached_data)
                            logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                            return result
                        except Exception as e:
                            logger.warning(f"Failed to deserialize cached value for {func.__name__}: {e}")

                    # 缓存未命中 - 使用分布式锁确保只有一个进程执行函数
                    logger.debug(f"Cache miss for {func.__name__} with key {cache_key}")

                    async with redis_lock(rdb, lock_key, lock_timeout, lock_wait_time):
                        # 再次检查缓存（可能在等待锁的过程中其他进程已经写入）
                        try:
                            cached_data = await rdb.get(cache_key)
                            if cached_data is not None:
                                result = _deserialize_value(cached_data)
                                logger.debug(f"Cache hit after lock for {func.__name__} with key {cache_key}")
                                return result
                        except Exception as e:
                            logger.warning(f"Failed to check cache after lock for {func.__name__}: {e}")

                        # 执行函数并缓存结果
                        logger.debug(f"Executing {func.__name__} with lock")
                        result = await func(*args, **kwargs)

                        try:
                            ex = expire_seconds if result else max(min(expire_seconds // 5, 5), 1)
                            serialized_result = _serialize_value(result)
                            await rdb.set(cache_key, serialized_result, ex=ex)
                            logger.debug(f"Cached result for {func.__name__} with key {cache_key}")
                        except Exception as e:
                            logger.warning(f"Failed to cache result for {func.__name__}: {e}")

                        return result

            except Exception as e:
                logger.error(f"Cache operation failed for {func.__name__}: {e}")
                return await func(*args, **kwargs)

        return wrapper

    return decorator


if __name__ == "__main__":
    import asyncio

    asyncio.run(clear_cache())
