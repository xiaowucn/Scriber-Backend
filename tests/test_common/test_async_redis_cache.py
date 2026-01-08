import pytest
from unittest.mock import AsyncMock, patch

from remarkable.common.async_redis_cache import redis_acache_with_lock, clear_cache, _generate_cache_key


@pytest.fixture
def mock_redis():
    """Mock Redis连接"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_rdb_context(mock_redis):
    """Mock Redis数据库上下文"""
    with patch("remarkable.common.async_redis_cache.get_cache_rdb") as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_redis
        mock_context.return_value.__aexit__.return_value = None
        yield mock_context


class TestRedisAcacheWithLock:
    """测试带锁的Redis缓存装饰器"""

    @pytest.mark.gen_test
    def test_cache_hit(self, mock_rdb_context, mock_redis):
        """测试缓存命中"""
        # 设置mock返回缓存数据
        mock_redis.get.return_value = b"pickled_data"

        with patch("remarkable.common.async_redis_cache._deserialize_value") as mock_deserialize:
            mock_deserialize.return_value = "cached_result"

            @redis_acache_with_lock(expire_seconds=60)
            async def test_func(x, y):
                return f"result_{x}_{y}"

            result = yield test_func(1, 2)

            assert result == "cached_result"
            mock_redis.get.assert_called_once()
            mock_deserialize.assert_called_once_with(b"pickled_data")

    @pytest.mark.gen_test
    def test_cache_miss_with_lock(self, mock_rdb_context, mock_redis):
        """测试缓存未命中，使用锁执行函数"""
        # 设置缓存未命中
        mock_redis.get.return_value = None

        with (
            patch("remarkable.common.async_redis_cache._serialize_value") as mock_serialize,
            patch("remarkable.common.async_redis_cache.redis_lock") as mock_lock,
        ):
            mock_serialize.return_value = b"serialized_result"
            mock_lock_context = AsyncMock()
            mock_lock.return_value.__aenter__.return_value = mock_lock_context
            mock_lock.return_value.__aexit__.return_value = None

            @redis_acache_with_lock(expire_seconds=60)
            async def test_func(x, y):
                return f"result_{x}_{y}"

            result = yield test_func(1, 2)

            assert result == "result_1_2"
            # 验证Redis操作
            assert mock_redis.get.call_count == 2  # 第一次检查，锁内再次检查
            mock_redis.set.assert_called_once()
            mock_lock.assert_called_once()

    @pytest.mark.gen_test
    def test_cache_hit_after_lock(self, mock_rdb_context, mock_redis):
        """测试在获取锁后发现缓存已存在"""
        # 第一次返回None，第二次返回缓存数据
        mock_redis.get.side_effect = [None, b"cached_data"]

        with (
            patch("remarkable.common.async_redis_cache._deserialize_value") as mock_deserialize,
            patch("remarkable.common.async_redis_cache.redis_lock") as mock_lock,
        ):
            mock_deserialize.return_value = "cached_result"
            mock_lock_context = AsyncMock()
            mock_lock.return_value.__aenter__.return_value = mock_lock_context
            mock_lock.return_value.__aexit__.return_value = None

            call_count = 0

            async def test_func(x, y):
                nonlocal call_count
                call_count += 1
                return f"result_{x}_{y}"

            @redis_acache_with_lock(expire_seconds=60)
            async def cached_test_func(x, y):
                return test_func(x, y)

            result = yield cached_test_func(1, 2)

            assert result == "cached_result"
            assert call_count == 0  # 函数不应该被调用
            assert mock_redis.get.call_count == 2

    @pytest.mark.gen_test
    def test_key_generation_error(self, mock_rdb_context, mock_redis):
        """测试键生成错误时的处理"""
        with patch("remarkable.common.async_redis_cache._generate_cache_key") as mock_gen_key:
            mock_gen_key.side_effect = Exception("Key generation failed")

            call_count = 0

            async def test_func(x, y):
                nonlocal call_count
                call_count += 1
                return f"result_{x}_{y}"

            @redis_acache_with_lock(expire_seconds=60)
            async def cached_test_func(x, y):
                return await test_func(x, y)

            result = yield cached_test_func(1, 2)

            assert result == "result_1_2"
            assert call_count == 1
            # Redis不应该被调用
            mock_redis.get.assert_not_called()

    @pytest.mark.gen_test
    def test_deserialization_error(self, mock_rdb_context, mock_redis):
        """测试反序列化错误时的处理"""
        mock_redis.get.return_value = b"invalid_data"

        with (
            patch("remarkable.common.async_redis_cache._deserialize_value") as mock_deserialize,
            patch("remarkable.common.async_redis_cache.redis_lock") as mock_lock,
        ):
            mock_deserialize.side_effect = Exception("Deserialization failed")
            mock_lock_context = AsyncMock()
            mock_lock.return_value.__aenter__.return_value = mock_lock_context
            mock_lock.return_value.__aexit__.return_value = None

            @redis_acache_with_lock(expire_seconds=60)
            async def test_func(x, y):
                return f"result_{x}_{y}"

            result = yield test_func(1, 2)

            assert result == "result_1_2"
            assert mock_redis.get.call_count == 2  # 第一次检查，锁内再次检查
            mock_lock.assert_called_once()

    @pytest.mark.gen_test
    def test_custom_key_func(self, mock_rdb_context, mock_redis):
        """测试自定义键生成函数"""
        mock_redis.get.return_value = None

        def custom_key_func(func_name, args, kwargs):
            return f"custom_{func_name}_{args[0]}"

        with (
            patch("remarkable.common.async_redis_cache._serialize_value") as mock_serialize,
            patch("remarkable.common.async_redis_cache.redis_lock") as mock_lock,
        ):
            mock_serialize.return_value = b"serialized_result"
            mock_lock_context = AsyncMock()
            mock_lock.return_value.__aenter__.return_value = mock_lock_context
            mock_lock.return_value.__aexit__.return_value = None

            @redis_acache_with_lock(expire_seconds=60, key_func=custom_key_func)
            async def test_func(x, y):
                return f"result_{x}_{y}"

            yield test_func(1, 2)

            # 验证使用了自定义键
            expected_key = "acache:custom_test_func_1"
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert call_args[0][0] == expected_key

    @pytest.mark.gen_test
    def test_custom_namespace(self, mock_rdb_context, mock_redis):
        """测试自定义命名空间"""
        mock_redis.get.return_value = None

        with (
            patch("remarkable.common.async_redis_cache._serialize_value") as mock_serialize,
            patch("remarkable.common.async_redis_cache.redis_lock") as mock_lock,
        ):
            mock_serialize.return_value = b"serialized_result"
            mock_lock_context = AsyncMock()
            mock_lock.return_value.__aenter__.return_value = mock_lock_context
            mock_lock.return_value.__aexit__.return_value = None

            @redis_acache_with_lock(expire_seconds=60, namespace="custom_namespace")
            async def test_func(x, y):
                return f"result_{x}_{y}"

            yield test_func(1, 2)

            # 验证使用了自定义命名空间
            call_args = mock_redis.set.call_args
            assert call_args[0][0].startswith("custom_namespace:")

    @pytest.mark.gen_test
    def test_lock_parameters(self, mock_rdb_context, mock_redis):
        """测试锁参数传递"""
        mock_redis.get.return_value = None

        with (
            patch("remarkable.common.async_redis_cache._serialize_value") as mock_serialize,
            patch("remarkable.common.async_redis_cache.redis_lock") as mock_lock,
        ):
            mock_serialize.return_value = b"serialized_result"
            mock_lock_context = AsyncMock()
            mock_lock.return_value.__aenter__.return_value = mock_lock_context
            mock_lock.return_value.__aexit__.return_value = None

            @redis_acache_with_lock(expire_seconds=60, lock_timeout=60.0, lock_wait_time=0.5)
            async def test_func(x, y):
                return f"result_{x}_{y}"

            yield test_func(1, 2)

            # 验证锁参数正确传递
            mock_lock.assert_called_once()
            call_args = mock_lock.call_args
            assert call_args[0][2] == 60.0  # timeout
            assert call_args[0][3] == 0.5  # wait_time


class TestCacheKeyGeneration:
    """测试缓存键生成"""

    def test_generate_cache_key_simple(self):
        """测试简单参数的键生成"""
        key = _generate_cache_key("test_func", (1, 2), {})
        assert key.startswith("test_func:")
        assert len(key) == 26  # "test_func:" + 16位hash

    def test_generate_cache_key_with_kwargs(self):
        """测试带关键字参数的键生成"""
        key1 = _generate_cache_key("test_func", (1,), {"y": 2})
        key2 = _generate_cache_key("test_func", (1,), {"y": 2})
        key3 = _generate_cache_key("test_func", (1,), {"y": 3})

        assert key1 == key2  # 相同参数应该生成相同键
        assert key1 != key3  # 不同参数应该生成不同键

    def test_generate_cache_key_different_order(self):
        """测试参数顺序不影响键生成"""
        key1 = _generate_cache_key("test_func", (), {"a": 1, "b": 2})
        key2 = _generate_cache_key("test_func", (), {"b": 2, "a": 1})

        assert key1 == key2  # 参数顺序不应该影响键

    def test_generate_cache_key_error_handling(self):
        """测试键生成错误处理"""
        # 模拟键生成失败
        with patch("hashlib.sha256") as mock_hash:
            mock_hash.side_effect = Exception("Hash failed")

            key = _generate_cache_key("test_func", (1, 2), {})
            assert key.startswith("test_func:fallback:")


class TestCacheClear:
    """测试缓存清理"""

    @pytest.mark.gen_test
    def test_clear_cache_success(self, mock_rdb_context, mock_redis):
        """测试成功清理缓存"""
        mock_redis.keys.return_value = ["key1", "key2", "key3"]
        mock_redis.delete.return_value = 3

        result = yield clear_cache("test_namespace", "pattern*")

        assert result == 3
        mock_redis.keys.assert_called_once_with("test_namespace:pattern*")
        mock_redis.delete.assert_called_once_with("key1", "key2", "key3")

    @pytest.mark.gen_test
    def test_clear_cache_no_keys(self, mock_rdb_context, mock_redis):
        """测试清理空缓存"""
        mock_redis.keys.return_value = []

        result = yield clear_cache("test_namespace", "pattern*")

        assert result == 0
        mock_redis.keys.assert_called_once_with("test_namespace:pattern*")
        mock_redis.delete.assert_not_called()

    @pytest.mark.gen_test
    def test_clear_cache_error(self, mock_rdb_context, mock_redis):
        """测试清理缓存错误处理"""
        mock_redis.keys.side_effect = Exception("Redis error")

        result = yield clear_cache("test_namespace", "pattern*")

        assert result == 0  # 错误时返回0
